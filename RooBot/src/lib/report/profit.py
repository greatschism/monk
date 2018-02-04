
#!/usr/bin/env python

# Changed complete by AJV 01/28/2018

# core
import io
import json
import logging
import traceback

# 3rd party
from retry import retry
import meld3

# local
import lib.config
from ..db import db
from .. import emailer
from .. import mybinance


LOGGER = logging.getLogger(__name__)

def open_order(order):

    # pprint(result['IsOpen'])
    if (order['status'] == 'PARTIALLY_FILLED' or order['status'] == 'NEW')
        is_open = True
    # print("\tOrder is open={}".format(is_open))
    return is_open


def close_date(ms_time):
    from datetime import datetime
    datetime_format = '%Y-%m-%dT%H:%M:%S'

    _dt = datetime.datetime.fromtimestamp(ms_time//1000.0)
    return _dt.date()


def percent(a, b):
    return (a/b)*100


class ReportError(Exception):
    """Base class for exceptions in this module."""
    pass

#TODO How should I do this for Binance?
class GetTickerError(ReportError):
    """Exception raised for when exchange does not return a result for a ticker
    (normally due to a network glitch).

    Attributes:
        market -- market in which the error occurred
    """

    def __init__(self, market):
        super().__init__()
        self.market = market
        self.message = "Unable to obtain ticker for {}".format(market)

#TODO How should I do this for Binance?
class NullTickerError(ReportError):
    """Exception raised for when exchange does not return a result for a ticker
    (normally due to a network glitch).

    Attributes:
        market -- market in which the error occurred
    """

    def __init__(self, market):
        super().__init__()
        self.market = market
        self.message = "None price values in ticker for {}".format(market)


def numeric(p):
    if p is None:
        return 0
    return p


#Changed by AJV 01/23/2018
@retry(exceptions=GetTickerError, tries=10, delay=5)
def obtain_ticker(exchange, order):

    market = order['symbol']
    ticker = exchange.get_ticker(market)
    if ticker['bidPrice'] is None:
        print("Got no result from get_ticker")
        raise GetTickerError(market)
    else:
        return ticker


#Changed by AJV 01/23/2018
@retry(exceptions=json.decoder.JSONDecodeError, tries=3, delay=5)
def obtain_order(exchange, market, orderId):
    order = exchange.get_order(symbol = market, orderID=orderId)
    # print("Order = {}".format(order))
    return order



def report_profit(user_config, exchange, on_date=None, skip_markets=None):


    #Changed by AJV 01/23/2018
    def profit_from(buy_order, sell_order):
        "Calculate profit given the related buy and sell order."

        exchange_fee = 0.05 # 0.05% on Binance
        sell_proceeds = sell_order['price'] * (1 - exchange_fee)
        buy_proceeds = buy_order['price'] * (1 + exchange_fee)
        # print("sell_proceeds={}. buy Order={}. buy proceeds = {}".format(sell_proceeds, bo, buy_proceeds))
        profit = sell_proceeds - buy_proceeds
        return profit

    def best_bid(sell_order):
        ticker = obtain_ticker(exchange, sell_order)
        _ = ticker['bidPrice']
        print("ticker = {}".format(ticker))
        return _

    def in_skip_markets(market, skip_markets):
        "Decide if market should be skipped"

        if skip_markets:
            for _skip_market in skip_markets:
                # print("Testing {} against {}".format(_skip_market, buy.market))
                if _skip_market in market:
                    print("{} is being skipped for this report".format(_skip_market))
                    return True

        return False

    def should_skip(buy_row):
        if buy_row.config_file != user_config.basename:
            print("\tconfig file != {}... skipping".format(user_config.basename))
            return True

        if (not buy_row.sell_id) or (len(buy_row.sell_id) < 12):
            print("\tNo sell id ... skipping")
            return True

        if in_skip_markets(buy_row.market, skip_markets):
            print("\tin {}".format(skip_markets))
            return True

        return False

    def get_balance(symbol):
        balances = exchange.get_account()['balances']
        for i in balances:
            if i['asset'] == symbol:
                return i
                break


    html_template = open('lib/report/profit.html', 'r').read()
    html_template = meld3.parse_htmlstring(html_template)
    html_outfile = open("tmp/" + user_config.basename + ".html", 'wb')

    locked_capital = 0
    open_orders = list()
    closed_orders = list()

    for buy in db().select(
        db.buy.ALL,
        orderby=~db.buy.timestamp
    ):

        if should_skip(buy):
            print("\tSkipping buy order {}".format(buy))
            continue


        print("--------------------- {} {}".format(buy.market, buy.order_id))

        so = obtain_order(exchange, buy.market, buy.sell_id)

        print("\t{}".format(so))

        print("\tDate checking {} against {}".format(on_date, so['time']))

        #Changed by AJV 01/26/2018
        #TODO Figure out how to know if a trade has closed and should be included in this report
        if on_date:
            if open_order(so):
                print("\t\tOpen order")
                so['status'] = 'n/a'
            else:
                _close_date = close_date(so['time'])
                # print("Ondate={}. CloseDate={}".format(pformat(on_date), pformat(_close_date)))

                if type(on_date) is list:
                    if _close_date < on_date[0]:
                        print("\t\tTrade is too old for report.")
                        continue
                    elif _close_date > on_date[1]:
                        print("\t\tTrade is too new for report.")
                        continue
                elif _close_date != on_date:
                    print("\t\tclose date of trade {} != {}".format(_close_date, on_date))
                    continue


        bo = exchange.get_order(symbol = buy.market, orderId = buy.order_id)

        # print("For buy order id ={}, Sell order={}".format(buy.order_id, so))

        if open_order(so):
            so['origQty'] = "{:d}%".format(int(
                 percent(so['executedQty'], so['origQty'])
            ))

        calculations = {
            'sell_closed': datetime.datetime.fromtimestamp(so['time']//1000.0),
            'buy_opened': datetime.datetime.fromtimestamp(bo['Opened'//1000.0)],
            'market': so['symbol'],
            'units_sold': so['origQty'],
            'sell_price': so['price'],
            'sell_commission': so['commission'],
            'units_bought': bo['qty'],
            'buy_price': numeric(bo['price']),
            'buy_commission': bo['commission'],
            'profit': profit_from(bo, so)
        }

        print("\tCalculations")
        if open_order(so):
            del calculations['sell_commission']
            del calculations['sell_price']
            calculations['sell_closed'] = 'n/a'
            print("\tOpen order...")

            _ = best_bid(so)
            difference = calculations['buy_price'] - _
            calculations['best_bid'] = _
            calculations['difference'] = '{:.2f}'.format(100 * (difference / calculations['buy_price']))
            open_orders.append(calculations)
            locked_capital += calculations['units_bought'] * calculations['buy_price']

        else:
            print("\tClosed order: {}".format(calculations))
            if so['price'] is None:
                raise Exception("Order closed but did not sell: {}\t\trelated buy order={}".format(so, bo))
            closed_orders.append(calculations)


    # open_orders.sort(key=lambda r: r['difference'])

    html_template.findmeld('acctno').content(user_config.filename)
    html_template.findmeld('name').content(user_config.client_name)
    html_template.findmeld('date').content("Transaction Log for Previous Day")


    def satoshify(f):
        return '{:.8f}'.format(f)


    def render_row(element, data, append=None):
        for field_name, field_value in data.items():
            if field_name == 'units_bought':
                continue
            if field_name in 'units_sold best_bid sell_price sell_commission buy_price buy_commission':
                field_value = str(field_value)
            if field_name == 'profit':
                profit = field_value
                field_value = satoshify(field_value)

            if append:
                field_name += append

            # print("Field_value={}. Looking for {} in {}".format(field_value, field_name, element))

            element.findmeld(field_name).content(str(field_value))

        return profit

    total_profit = 0
    data = dict()
    iterator = html_template.findmeld('closed_orders').repeat(closed_orders)
    for element, data in iterator:
        total_profit += render_row(element, data)

    deposit = float(user_config.trade_deposit)
    percent_profit = percent(total_profit, deposit)
    pnl = "{} ({:.2f} % of {})".format(
        satoshify(total_profit), percent_profit, deposit)
    html_template.findmeld('pnl').content(pnl)

    s = html_template.findmeld('closed_orders_sample')
    if not total_profit:
        s.replace("No closed trades!")
    else:
        render_row(s, data, append="2")

    print("Open Orders={}".format(open_orders))
    open_orders_element = html_template.findmeld('open_orders')
    print("Open Orders Element={}".format(vars(open_orders_element)))
    for child in open_orders_element.__dict__['_children']:
        print("\t{}".format(vars(child)))


    iterator = open_orders_element.repeat(open_orders)
    for i, (element, data) in enumerate(iterator):
        data["sell_number"] = i+1
        render_row(element, data, append="3")

    for setting in 'deposit trade top takeprofit preserve'.split():
        elem = html_template.findmeld(setting)
        val = user_config.config.get('trade', setting)
        # print("In looking for {} we found {} with setting {}".format(
        # setting, elem, val))
        elem.content(val)

    elem = html_template.findmeld('available')
    bal = exchange.get_balance("BTC")
    LOG.debug("bal={}".format(bal))
    btc = bal['free'] + bal['locked']
    val = "Balance={}BTC, Available={}BTC".format(bal['free'] + bal['locked'], bal['free'])
    elem.content(val)

    elem = html_template.findmeld('locked')
    val = "{}BTC".format(locked_capital)
    elem.content(val)

    elem = html_template.findmeld('operating')
    val = "{}BTC".format(locked_capital + btc)
    elem.content(val)

    print("HTML OUTFILE: {}".format(html_outfile))
    strfs = io.BytesIO()
    html_template.write_html(html_outfile)
    html_template.write_html(strfs)
    #for output_stream in (html_outfile, strfs):

    return strfs, total_profit

def system_config():
    import configparser
    config = configparser.RawConfigParser()
    config.read("system.ini")
    return config


def notify_admin(msg, sys_config):

    print("Notifying admin about {}".format(msg))

    subject = "RooBOT aborted execution on exception"
    sender = sys_config.email_sender
    recipient = sys_config.email_bcc
    emailer.send(subject,
                 text=msg, html=None,
                 sender=sender,
                 recipient=recipient,
                 bcc=None
                 )



@retry(exceptions=json.decoder.JSONDecodeError, tries=600, delay=5)
def main(config_file, english_date, _date=None, email=True, skip_markets=None):

    print("profit.main.SKIP MARKETS={}".format(skip_markets))

    USER_CONFIG = lib.config.User(config_file)
    SYS_CONFIG = lib.config.System()

    exchange = mybinance.make_binance(USER_CONFIG.config)
    try:
        html, _ = report_profit(USER_CONFIG, exchange, _date, skip_markets)

        if email:
            subject = "{}'s Profit Report for {}".format(english_date, config_file)
            emailer.send(subject,
                         text='hi my name is slim shady', html=html.getvalue(),
                         sender=SYS_CONFIG.email_sender,
                         recipient=USER_CONFIG.client_email,
                         bcc=SYS_CONFIG.email_bcc
                         )

    except Exception:
        error_msg = traceback.format_exc()
        print('Aborting: {}'.format(error_msg))
        if email:
            print("Notifying admin via email")
            notify_admin(error_msg, SYS_CONFIG)



if __name__ == '__main__':
    ts = '2017-10-15T21:28:21.05'
    dt = close_date(ts)
    print(dt)
