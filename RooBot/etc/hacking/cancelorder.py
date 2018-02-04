#Changed by AJV 01/23/2018
#from bittrex.bittrex import Bittrex, SELL_ORDERBOOK
from . import mybinance
import json
import logging
import pprint

market = 'LTCBTC'
order_id = '6gCrw2kRUAF9CvJDGP16IP'

exchange = mybinance.make_binance(user_config.config)

openorders = exchange.get_open_orders();
for order in openorders:
    print order

result = exchange.cancel_order(symbol = market, orderId = order_id)
print("\tResult of clearing profit: {}".format(pprint.pformat(result)))
