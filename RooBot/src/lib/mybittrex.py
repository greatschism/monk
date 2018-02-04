#Reviewed by AJV 01/23/2018
#TODO: Replace completely with mybinance.py
# core
import configparser

# 3rd party

# local
from bittrex.bittrex import Bittrex


def make_binance(config):


    b = Bittrex(config.get('api', 'key'), config.get('api', 'secret'))

    return b
