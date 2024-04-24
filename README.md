# Prosperity 2 

## Introduction
This repository contains Python code for implementing various algorithmic trading strategies. Each strategy is implemented as a separate function within a class and is designed to execute specific trading actions based on market conditions.

## Getting Started
To use these trading strategies, follow these steps:

1. Clone this repository to your local machine.
2. Install the required dependencies. You can do this by running `pip install -r requirements.txt`.
3. Import the trading strategy functions into your project.
4. Initialize the trading environment and provide necessary parameters such as trading state, market data, and any additional indicators required by the strategy.
5. Call the desired trading strategy function with the appropriate parameters.
6. Execute the returned orders generated by the trading strategy.

## Strategies

### Amethyst Strategy
- **Description:** Executes trades based on the bid-ask spread of a specific asset.
- **Function:** `amethyst_strategy(self, state: TradingState)`
- **Parameters:** `state` - The current trading state containing market data.
- **Logic:** Determines whether to buy or sell based on the bid-ask spread relative to a default price.

### Starfruit Strategy
- **Description:** Implements trades based on the position and exponential moving average (EMA) of an asset.
- **Function:** `starfruit_strategy(self, state: TradingState)`
- **Parameters:** `state` - The current trading state containing market data.
- **Logic:** Adjusts buy and sell orders based on the position and EMA of the asset.

### Orchids Strategy
- **Description:** Executes trades based on the derivatives of sunlight and humidity.
- **Function:** `orchids_strategy(self, state: TradingState, sunlight, humidity)`
- **Parameters:** `state` - The current trading state containing market data, `sunlight` - Time series data for sunlight, `humidity` - Time series data for humidity.
- **Logic:** Buys or sells based on the derivatives of sunlight and humidity, resetting the position if they become discordant.

### Choco Straw Rose Bask Strategy
- **Description:** Implements trades based on the spread between a gift basket and its components.
- **Function:** `choco_straw_rose_bask_strategy(self, state: TradingState)`
- **Parameters:** `state` - The current trading state containing market data.
- **Logic:** Determines whether to buy or sell the gift basket based on the spread between its price and the combined price of its components.

### Coco Strategy
- **Description:** Executes trades based on the spread between coconut and coconut_coupon.
- **Function:** `coco_strategy(self, state: TradingState)`
- **Parameters:** `state` - The current trading state containing market data.
- **Logic:** Waits for enough data points to estimate the mean and standard deviation of the spread, then buys or sells based on predefined thresholds.

## Contributing
Contributions to this repository are welcome! If you have ideas for additional trading strategies or improvements to existing ones, feel free to submit a pull request.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
