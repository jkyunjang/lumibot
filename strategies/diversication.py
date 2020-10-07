import logging

from .strategy import Strategy
from data_sources import Yahoo

class Diversication(Strategy):
    # =====Overloading lifecycle methods=============

    def initialize(self):
        # canceling open orders
        self.api.cancel_open_orders()

        # setting the waiting period (in days) and the counter
        self.period = 1
        self.counter = 0

        # there is only one trading operation per day
        # no need to sleep betwwen iterations
        self.sleeptime = 0

        # initializing the portfolio variable
        self.initialized = False
        self.portfolio = [
            {
                'symbol': 'SPY',  # Stocks
                'weight': 0.3
            },
            {
                'symbol': 'SPY',  # Long Term Bond
                'weight': 0.4
            },
            {
                'symbol': 'SPY',  # Intermediate Term Bond
                'weight': 0.15
            },
            {
                'symbol': 'SPY',  # Gold
                'weight': 0.075
            },
            {
                'symbol': 'DJP',  # Commidities
                'weight': 0.075
            }
        ]

    def on_trading_iteration(self):
        if self.counter == self.period or self.counter == 0:
            self.counter = 0
            self.rebalance_portfolio()
            logging.info("Next portfolio rebalancing will be on %d day(s)" % self.period)

        self.counter += 1
        self.api.await_market_to_close()

    # =============Helper methods====================

    def get_portfolio_value(self):
        """Update the shares prices and recalculate the current portfolio value"""
        if not self.initialized: return self.budget

        value = 0
        symbols = [a.get('symbol') for a in self.portfolio]
        prices = self.api.get_last_prices(symbols)
        for asset in self.portfolio:
            symbol = asset.get('symbol')
            quantity = asset.get('quantity') if asset.get('quantity') else 0
            price = prices.get(symbol)
            asset['last_price'] = price
            value += quantity * price

        return value

    def rebalance_portfolio(self):
        """Rebalance the portfolio and cretae orders"""
        portfolio_value = self.get_portfolio_value()
        if not self.initialized:
            self.initialized = True
            logging.info("Total initial budget: %.2f$" % self.budget)
        else:
            logging.info("Total portfolio value: %.2f$" % portfolio_value)

        orders = []
        for asset in self.portfolio:
            symbol = asset.get('symbol')
            weight = asset.get('weight')
            quantity = asset.get('quantity') if asset.get('quantity') else 0
            last_price = asset.get('last_price')
            if not last_price: last_price = self.api.get_last_price(symbol)
            shares_value = portfolio_value * weight
            logging.info(
                "Asset %s shares value: %.2f$. %.2f$ per %d shares." %
                (symbol, quantity * last_price, last_price, quantity)
            )
            new_quantity = shares_value // last_price
            quantity_difference = new_quantity - quantity
            logging.info(
                "Weighted %s shares value with %.2f%% weight: %.2f$. %.2f$ per %d shares." %
                (symbol, shares_value, weight * 100, last_price, new_quantity)
            )

            if quantity_difference > 0:
                order = {
                    'symbol': symbol,
                    'quantity': quantity_difference,
                    'side': 'buy',
                    'price': last_price,
                }
                orders.append(order)
                asset['quantity'] = new_quantity
            elif quantity_difference < 0:
                order = {
                    'symbol': symbol,
                    'quantity': abs(quantity_difference),
                    'side': 'sell',
                    'price': last_price,
                }
                orders.append(order)
                asset['quantity'] = new_quantity

        self.api.submit_orders(orders)
