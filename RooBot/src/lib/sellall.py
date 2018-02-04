# #!/usr/bin/env python

#Reviewed by AJV 01/28/2018
#Changed by AJV 01/23/2018

import configparser
import argh
import collections
import logging
import pprint
from retry import retry
from .db import db
from . import mybinance
#from bittrex.bittrex import SELL_ORDERBOOK
from pprint import pprint

def loop_forever():
    while True:
        pass


logger = logging.getLogger(__name__)


#Changed by AJV 01/23/2018
def cancelall(b):
    orders = b.get_open_orders()

    for order in orders:
        pprint(order)
        market = order['symbol']
        sell_id = order['orderId']
        r = b.cancel_order(symbol = market, orderId = sell_id)
        pprint(r)
        db(db.buy.sell_id == sell_id).delete()
        db.commit()



def sellall(b):
    cancelall(b)
    balances = b.get_account()['balances']
    for balance in balances:
        print("-------------------- {}".format(balance['asset']))
        pprint(balance)

        if not balance['free'] or balance['asset'] == 'BTC':
            print("\tno balance or this is BTC")
            continue

        skipcoin = "CRYPT TIT GHC UNO DAR ARDR DGD MTL SNGLS SWIFT TIME TKN XAUR BCC"
        if balance['asset'] in skipcoin:
            print("\tthis is a skipcoin")
            continue

        market = balance['asset'] + "BTC"

        pprint(balance)

        ticker = b.get_ticker(market)
        pprint(ticker)

        my_ask = ticker['bidPrice'] - 1e-8

        print(("My Ask = {}".format(my_ask)))

        r = b.order_limit_sell(symbol = market, quantity = balance['free'], price = my_ask)
        pprint(r)


def main(ini):

    config_file = ini
    config = configparser.RawConfigParser()
    config.read(config_file)

    b = mybinance.make_binance(config)
    sellall(b)

if __name__ == '__main__':
    argh.dispatch_command(main)
