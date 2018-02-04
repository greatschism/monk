#Reviewed by AJV 01-28-2018
# core
import configparser

# 3rd party

# local

#Changed AJV 01/22/2018
from binance.client import Client


def make_binance(config):

    b = Client(config.get('api', 'key'), config.get('api', 'secret'))

    return b