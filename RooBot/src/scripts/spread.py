#!/usr/bin/env python

#Reviewed by AJV 02/03/2018

import argh
import collections
import logging
import pprint
from retry import retry
from db import db
import mybinance
#from bittrex.bittrex import SELL_ORDERBOOK


logger = logging.getLogger(__name__)
b = mybinance.make_binance()

#TODO Should I expand this?
ignore_by_in = 'BTCUSDT ZECBTC ETHBTC BTCETH MTRBTC UTCBTC XRPBTC BCCBTC'
ignore_by_find = 'ETH'
max_orders_per_market = 2


def percent_gain(new, old):
    increase = (new - old)
    if increase:
        percent_gain = increase / old
    else:
        percent_gain = 0
    return percent_gain


def number_of_open_orders_in(market):
    orders = list()
    oo = b.get_open_orders(symbol = market)
    if oo:
        # pprint.pprint(oo)
        for order in oo:
            if order['symbol'] == market:
                orders.append(order)
        return len(orders)
    else:
        return 0


def ignorable_market(bid, name):
    if bid < 100e-8:
        return True

    if name in ignore_by_in:
        return True

    if name.find(ignore_by_find) != -1:
        return True

    return False


#Changed AJV 01/22/2018
def analyze_spread():

    Market = collections.namedtuple('Market',
                                    'name spread volume')
    markets = list()

    for market in b.get_ticker():

        if ignorable_market(market['bidPrice'], market['symbol']):
            continue

        btc_volume = market['bidPrice'] * market['volume']
        markets.append(
            Market(
                market['symbol'],
                market['askPrice'] - market['bidPrice'],
                btc_volume
            )
        )

    markets.sort(key=lambda m: (-m.volume, m.spread,))

    pprint.pprint(markets)

    return markets


def report_btc_balance():
    bal = b.get_asset_balance(asset='BTC')
    pprint.pprint(bal)
    return bal


def available_btc():
    bal = report_btc_balance()
    avail = bal['free']
    print "Available btc={0}".format(avail)
    return avail


#TODO: Make sure that the indexes match and it returns the right rate
#Changed by AJV 01/23/2018
def rate_for(market, btc):
    "Return the rate that works for a particular amount of BTC."

    coin_amount = 0
    btc_spent = 0
    orders = b.get_order_book(symbol = market, limit = 1000)
    for order in orders['asks']:
        btc_spent += order[0] * order[1]
        if btc_spent > btc:
            break

    coin_amount = btc / order[0]
    return order[0], coin_amount


@retry()
def record_buy(market, rate, amount):
    db.buy.insert(market=market, purchase_price=rate, amount=amount)
    db.commit()


def _buycoin(market, btc):
    "Buy into market using BTC. Current allocately 2% of BTC to each trade."

    print "I have {0} BTC available.".format(btc)

    btc *= 0.02

    print "I will trade {0} BTC.".format(btc)

    rate, amount_of_coin = rate_for(market, btc)

    print "I get {0} unit of {1} at the rate of {2} BTC per coin.".format(
        amount_of_coin, market, rate)

    r = b.buy_limit(symbol = market, quantity = amount_of_coin, price = rate)
    if r['success']:
        record_buy(market, rate, amount_of_coin)
    pprint.pprint(r)


def buycoin(n):
    "Buy top N cryptocurrencies."

    top = analyze_gain()[:n]
    print 'TOP {0}: {1}'.format(n, top)
    avail = available_btc()
    for market in top:
        print 'market: {0}'.format(market)
        _buycoin(market[0], avail)


def main(my_btc=False, buy=0):
    if my_btc:
        report_btc_balance()
    elif buy:
        buycoin(buy)
    else:
        analyze_spread()


if __name__ == '__main__':
    argh.dispatch_command(main)
