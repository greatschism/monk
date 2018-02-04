#!/usr/bin/env python

#Reviewed by AJV 01-28-2018
#Changed by AJV 01-22-2018

# Core
from datetime import datetime
import logging
import pprint


# 3rd Party
import argh
from retry import retry

# Local
from .db import db
#from . import mybinance
from . import mybinance

logger = logging.getLogger(__name__)

try:
    import simplejson as json
    try:
        JSONDecodeError = json.JSONDecodeError
    except AttributeError:
        # simplejson < 2.1.0 does not have the JSONDecodeError exception class
        JSONDecodeError = ValueError
except ImportError:
    import json
    JSONDecodeError = ValueError


@retry(exceptions=json.decoder.JSONDecodeError, tries=600, delay=5)

def main(ini):

    config_file = ini
    from users import users

    config = users.read(config_file)

    #b = mybinance.make_binance(config)
    b = mybinance.make_binance(config)


    print("Getting market summaries")
    markets = b.get_ticker()

    with open("tmp/markets.json", "w") as markets_file:
        markets_file.write(pprint.pformat(markets['result']))

    print("Populating database")
    for market in markets['result']:

        db.market.insert(
            name=market['symbol'],
            ask=market['askPrice'],
            timestamp=datetime.now()
        )

    db.commit()

if __name__ == '__main__':
    argh.dispatch_command(main)