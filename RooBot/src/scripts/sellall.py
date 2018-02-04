#!/usr/bin/env python

#Reviewed by AJV 02/03/2018

import configparser
import argh
import collections
import logging
import pprint
from retry import retry

from src.lib import mybinance

#from bittrex.bittrex import SELL_ORDERBOOK
from pprint import pprint

def loop_forever():
    while True:
        pass


logger = logging.getLogger(__name__)


def cancelall(b):
    orders = b.get_open_orders()

    for order in orders:
        pprint(order)
        r = b.cancel_order(symbol = order['symbol'], orderId = order['orderId'])
        pprint(r)


def sellall(b):
    cancelall(b)
    balances = b.get_account()["balances"]
    for balance in balances:
        print("-------------------- {}".format(balance['asset']))
        pprint(balance)

        if not balance['free'] or balance['asset'] == 'BTC':
            print("\tno balance or this is BTC")
            continue

        #TODO See if I need to do more than this
        skipcoin = "CRYPT TIT GHC BCC"
        if balance['asset'] in skipcoin:
            print("\tthis is a skipcoin")
            continue

        market = balance['asset'] + "BTC"

        pprint(balance)

        ticker = b.get_ticker(symbol = market)
        pprint(ticker)

        my_ask = ticker['bidPrice'] - 5e-8

        print("My Ask = {}".format(my_ask))

        r = b.sell_limit(symbol = market, quantity = balance['Balance'], price = my_ask)
        pprint(r)


def main(ini):

    config_file = ini
    config = configparser.RawConfigParser()
    config.read(config_file)

    b = mybinance.make_binance(config)
    sellall(b)

if __name__ == '__main__':
    argh.dispatch_command(main)
