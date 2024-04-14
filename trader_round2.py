import json
#from datamodel import OrderDepth, UserId, TradingState, Order
from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState, ConversionObservation

from typing import List
from typing import Any
import string
import math
import numpy as np
#from logger import logger  # Assuming Logger is properly defined and imported

AMETHYSTS = 'AMETHYSTS'
STARFRUIT = 'STARFRUIT'
ORCHIDS= 'ORCHIDS'
SUBMISSION = 'SUBMISSION'  # Used for identifying trades involving this submission

PRODUCTS = [AMETHYSTS, STARFRUIT, ORCHIDS]

DEFAULT_PRICES = {
    AMETHYSTS: 10_000,
    STARFRUIT: 5_000,
    ORCHIDS: 1_100
}


class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(self.to_json([
            self.compress_state(state, ""),
            self.compress_orders(orders),
            conversions,
            "",
            "",
        ]))

        # We truncate state.traderData, trader_data, and self.logs to the same max. length to fit the log limit
        max_item_length = (self.max_log_length - base_length) // 3

        print(self.to_json([
            self.compress_state(state, self.truncate(state.traderData, max_item_length)),
            self.compress_orders(orders),
            conversions,
            self.truncate(trader_data, max_item_length),
            self.truncate(self.logs, max_item_length),
        ]))

        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> list[Any]:
        return [
            state.timestamp,
            trader_data,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations),
        ]

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        compressed = []
        for listing in listings.values():
            compressed.append([listing["symbol"], listing["product"], listing["denomination"]])

        return compressed

    def compress_order_depths(self, order_depths: dict[Symbol, OrderDepth]) -> dict[Symbol, list[Any]]:
        compressed = {}
        for symbol, order_depth in order_depths.items():
            compressed[symbol] = [order_depth.buy_orders, order_depth.sell_orders]

        return compressed

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        compressed = []
        for arr in trades.values():
            for trade in arr:
                compressed.append([
                    trade.symbol,
                    trade.price,
                    trade.quantity,
                    trade.buyer,
                    trade.seller,
                    trade.timestamp,
                ])

        return compressed

    def compress_observations(self, observations: Observation) -> list[Any]:
        conversion_observations = {}
        for product, observation in observations.conversionObservations.items():
            conversion_observations[product] = [
                observation.bidPrice,
                observation.askPrice,
                observation.transportFees,
                observation.exportTariff,
                observation.importTariff,
                observation.sunlight,
                observation.humidity,
            ]

        return [observations.plainValueObservations, conversion_observations]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        compressed = []
        for arr in orders.values():
            for order in arr:
                compressed.append([order.symbol, order.price, order.quantity])

        return compressed

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        if len(value) <= max_length:
            return value

        return value[:max_length - 3] + "..."

logger = Logger()

class Trader:
    def __init__(self) -> None:
        self.logger = Logger()  # Initialize the logger
        print("Initialize Trader ...")
        self.position_limit = {
            AMETHYSTS: 20,
            STARFRUIT: 20,
            ORCHIDS: 100
        }

        self.round = 0
        self.cash = 0
        self.past_prices = {product: [] for product in PRODUCTS}
        self.ema_prices = {product: None for product in PRODUCTS}
        self.ema_param = 0.5
        self.theta=[ 9.758,  6.402, -5.561, 3.320, 1.501,  1.753]
        self.sunlight = [] #here we will store the sunlight time series for orchids
        self.humidity = [] #here we will store the humidity time series for orchids

    #ROUND 1 UTILS
    def get_position(self, product, state: TradingState):
        return state.position.get(product, 0)
    
    def get_mid_price(self, product, state : TradingState):
        """
        Given a product and a state objects, it returns the mid_price.
        The mid_price consists of the price in between the best bid and the best ask.
        If there are no bids or asks, it returns the DEFAULT_PRICE consisting of the exponential moving average (EMA) of all the previous prices.
        """

        default_price = self.ema_prices[product]
        if default_price is None:
            default_price = DEFAULT_PRICES[product] #at the beginning of the series, just set the default price to DEFAULT_PRICE

        if product not in state.order_depths:
            return default_price
        
        market_bids = state.order_depths[product].buy_orders #save here all the BIDS present in the market for a product at a certain state in time
        if len(market_bids) == 0:
            return default_price #if there are no BID orders, set the mid_price to be the EMA of the previous prices
        
        market_asks = state.order_depths[product].sell_orders
        if len(market_asks) == 0:
            return default_price #if there are no ASK orders, set the mid_price to be the EMA of the previous prices
        
        #in all the other cased, the mid_price of a product at a given state in time is defined as
        #the average between the best bid and the best ask
        best_bid = max(market_bids)
        best_ask = max(market_asks)

        return (best_bid + best_ask)/2
    
    def get_value_on_product(self, product, state: TradingState):
        return self.get_position(product, state) * self.get_mid_price(product, state)
    
    def get_best_bid_ask(self, product, state: TradingState):
        if product not in state.order_depths:
            return None, None
        market_bids = state.order_depths[product].buy_orders
        market_asks = state.order_depths[product].sell_orders
        if len(market_bids) == 0 or len(market_asks) == 0:
            return None, None
        best_bid = max(market_bids)
        best_ask = min(market_asks)
        return best_bid, best_ask
    
    def update_ema_price(self, state: TradingState):
        for product in PRODUCTS:
            mid_price = self.get_mid_price(product, state)
            if mid_price is None:
                continue
            if self.ema_prices[product] is None:
                self.ema_prices[product] = mid_price
            else:
                self.ema_prices[product] = self.ema_param * mid_price + (1 - self.ema_param) * self.ema_prices[product]
        self.logger.print(f"Updated EMA Prices: {self.ema_prices}")

    #ROUND 2 UTILS


    #ROUND 1 STRATEGIES
    def amethyst_strategy(self, state: TradingState):

        self.logger.print("Executing Amethyst strategy")
        position_amethysts = self.get_position(AMETHYSTS, state) #get the position we currently have in AMETHYSTS

        bid_volume = self.position_limit[AMETHYSTS] - position_amethysts #find the bid volume as the position limit (20) - the current position we have in AMETHYSTS 
        ask_volume = - self.position_limit[AMETHYSTS] - position_amethysts # NOTE: This is a negative value bc enters into the SELL orders

        best_bid, best_ask = self.get_best_bid_ask(AMETHYSTS, state) #get the best bid and ask currently in hte orderbook

        orders = []
        
        if best_bid > DEFAULT_PRICES[AMETHYSTS] and best_ask > DEFAULT_PRICES[AMETHYSTS]:
            orders.append(Order(AMETHYSTS, DEFAULT_PRICES[AMETHYSTS], bid_volume)) #buy at 10K
            orders.append(Order(AMETHYSTS, best_bid, ask_volume)) #sell at best_bid

        elif best_bid < DEFAULT_PRICES[AMETHYSTS] and best_ask < DEFAULT_PRICES[AMETHYSTS]:
            orders.append(Order(AMETHYSTS, best_ask, bid_volume)) #buy at best_ask
            orders.append(Order(AMETHYSTS, DEFAULT_PRICES[AMETHYSTS], ask_volume)) #sell at 10K

        else: # make the market at with the largest spread between our buy and sell orders
            bid_diff = abs(best_bid - DEFAULT_PRICES[AMETHYSTS])
            ask_diff = abs(DEFAULT_PRICES[AMETHYSTS] - best_ask)
            min_diff = min(bid_diff, ask_diff)

            orders.append(Order(AMETHYSTS, DEFAULT_PRICES[AMETHYSTS] - min_diff + 1, bid_volume)) #buy
            orders.append(Order(AMETHYSTS, DEFAULT_PRICES[AMETHYSTS] + min_diff - 1, ask_volume)) #sell
            
        return orders
    
    
    def starfruit_strategy(self, state: TradingState):

        self.logger.print("Executing Starfruit strategy")

        position_starfruit = self.get_position(STARFRUIT, state) #get the position we currently have in STARFRUIT
        
        bid_volume = self.position_limit[STARFRUIT] - position_starfruit #find the bid volume as the position limit (20) - the current position we have in STARFRUIT 
        ask_volume = - self.position_limit[STARFRUIT] - position_starfruit # NOTE: This is a negative value bc enters into the SELL orders

        orders = [] #initialize an empty list containing the BUY and SELL orders

        if position_starfruit == 0:
            # Not long nor short
            orders.append(Order(STARFRUIT, math.floor(self.ema_prices[STARFRUIT] - 1), bid_volume))
            orders.append(Order(STARFRUIT, math.ceil(self.ema_prices[STARFRUIT] + 1), ask_volume))
        
        if position_starfruit > 0:
            # Long position
            orders.append(Order(STARFRUIT, math.floor(self.ema_prices[STARFRUIT] - 2), bid_volume))
            orders.append(Order(STARFRUIT, math.ceil(self.ema_prices[STARFRUIT]), ask_volume))

        if position_starfruit < 0:
            # Short position
            orders.append(Order(STARFRUIT, math.floor(self.ema_prices[STARFRUIT]), bid_volume))
            orders.append(Order(STARFRUIT, math.ceil(self.ema_prices[STARFRUIT] + 2), ask_volume))

        return orders


    #ROUND 2 STRATEGIES
    def orchids_strategy(self, state: TradingState, sunlight, humidity):
        self.logger.print("Executing Orchids strategy")

        position_orchids = self.get_position(ORCHIDS, state)
        bid_volume = self.position_limit[ORCHIDS] - position_orchids
        ask_volume = -self.position_limit[ORCHIDS] - position_orchids



        best_bid, best_ask = self.get_best_bid_ask(ORCHIDS, state)

        mid_price = int(round(self.get_mid_price(ORCHIDS, state)))

        sunlight_deriv = None
        humidity_deriv = None

        # Calculate derivatives if there are enough data points
        if len(sunlight) >= 10:
            sunlight_deriv = sunlight[-1] - sunlight[-10]
        if len(humidity) >= 10:
            humidity_deriv = humidity[-1] - humidity[-10]

        orders = []

        # If both sunlight and humidity are increasing significantly
        if sunlight_deriv is not None and humidity_deriv is not None:
            if sunlight_deriv > 0 and humidity_deriv > 0:
                orders.append(Order(ORCHIDS, best_ask, bid_volume)) 

            # If both sunlight and humidity are decreasing significantly
            elif sunlight_deriv < 0 and humidity_deriv < 0:
                orders.append(Order(ORCHIDS, best_bid, ask_volume))

            
            # If sunlight and humidity changes have different signs
            elif sunlight_deriv * humidity_deriv < 0:
        
                orders.append(Order(ORCHIDS, best_bid + 1, bid_volume))
                orders.append(Order(ORCHIDS, best_ask - 1, max(ask_volume,-100)))
            

        # If conditions are relatively stable or there's insufficient data
        if len(sunlight) < 10 or len(humidity) < 10 or sunlight_deriv is None or humidity_deriv is None:
            pass

        return orders
   

    '''
    def orchids_strategy(self, state: TradingState):
        self.logger.print("Executing ORCHID strategy")
            #conversion_obs = state.ConversionObservation
        conversion_obs = state.observations.conversionObservations['ORCHIDS']


        
        X = np.array([
            1, 
            conversion_obs.exportTariff,
            conversion_obs.transportFees,
            conversion_obs.importTariff,
            conversion_obs.sunlight,
            conversion_obs.humidity])
            
            # Predict next price
        predicted_price = np.dot(X, self.theta)

            # Current market price
        current_price = self.get_mid_price(ORCHIDS, state)

            # Get current position and calculate order volumes
        position_orchids = self.get_position(ORCHIDS, state)
        bid_volume = self.position_limit[ORCHIDS] - position_orchids
        ask_volume = -self.position_limit[ORCHIDS] - position_orchids

        orders = []
            
        if current_price < predicted_price and bid_volume > 0:
        
            orders.append(Order(ORCHIDS, current_price, bid_volume))
        elif current_price > predicted_price and position_orchids > 0:
            orders.append(Order(ORCHIDS, current_price, ask_volume))

        return orders
        '''

    '''        
    def orchids_strategy(self, state: TradingState):
        try:
            self.logger.print("Starting ORCHID strategy execution.")
            # Check if ORCHIDS is correctly set and accessible
            self.logger.print(f"Using ORCHIDS identifier: {ORCHIDS}")
            
            # Access the conversion observations for 'ORCHIDS'
            if ORCHIDS in state.observations.conversionObservations:
                conversion_obs = state.observations.conversionObservations[ORCHIDS]
                self.logger.print(f"Conversion Observations: {conversion_obs}")
            else:
                raise ValueError("ORCHIDS data not found in conversion observations")

            # Prepare the feature array for prediction
            X = np.array([
                1,  # Intercept term for linear regression
                conversion_obs.exportTariff,
                conversion_obs.transportFees,
                conversion_obs.importTariff,
                conversion_obs.sunlight,
                conversion_obs.humidity
            ])

            # Predict the next price
            predicted_price = np.dot(X, self.theta)

            # Obtain the current market price
            current_price = self.get_mid_price(ORCHIDS, state)
            position_orchids = self.get_position(ORCHIDS, state)
            bid_volume = self.position_limit[ORCHIDS] - position_orchids
            ask_volume = -self.position_limit[ORCHIDS] - position_orchids

            orders = []
            if current_price < predicted_price and bid_volume > 0:
                orders.append(Order(ORCHIDS, int(round(current_price)), bid_volume))
            elif current_price > predicted_price and position_orchids > 0:
                orders.append(Order(ORCHIDS, int(round(current_price)), ask_volume))

            self.logger.print("ORCHID strategy executed successfully.")
            return orders

        except Exception as e:
            self.logger.print(f"Error in ORCHID strategy: {e}")
            raise  # Re-raise the exception after logging for further analysis
        '''
    
    


    def run(self, state: TradingState):
        self.round += 1
        self.logger.print(f"Round: {self.round}, Timestamp: {state.timestamp}")
        
        self.update_ema_price(state)
        
        #append to self.sunlight and self.humidity the current values of sunlight and humidity
        self.sunlight.append(state.observations.conversionObservations[ORCHIDS].sunlight)
        self.humidity.append(state.observations.conversionObservations[ORCHIDS].humidity)
        
        result = {}
        
            # Implementing AMETHYSTS Strategy

      
        try:
            result[AMETHYSTS] = self.amethyst_strategy(state)
        except Exception as e:
            self.logger.print(f"Error in AMETHYSTS strategy: {e}")
        
        # Implementing STARFRUIT Strategy
        try:
            result[STARFRUIT] = self.starfruit_strategy(state)
        except Exception as e:
            self.logger.print(f"Error in STARFRUIT strategy: {e}")
     
        try:
            result[ORCHIDS] = self.orchids_strategy(state, self.sunlight, self.humidity)
        except Exception as e:
            self.logger.print(f"Error in ORCHIDS strategy: {e}")
        



        conversions = 0 
        trader_data = "SAMPLE"
        
        # Flush logs to output
        self.logger.flush(state, result, conversions, trader_data)
        
        return result, conversions, trader_data
