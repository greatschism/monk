#!/usr/bin/env python

#Reviewed by AJV 02/03/2018
#Changed by AJV 01/23/2018

import argh
import collections
import logging
import pprint
from retry import retry
from db import db
import mybinance
from pprint import pprint


logger = logging.getLogger(__name__)
b = mybinance.make_binance()

orders = b.get_open_orders()

#TODO Make sure that orders below does not need an identifier
for order in orders:
    pprint(order)
    r = b.cancel_order(symbol = order['symbol'], orderId = order['orderId'])
    pprint(r)
