from beancount.prices import source
from dateutil import tz
from dateutil.parser import parse
from beancount.core.number import D
import requests


class Source(source.Source):
    def get_latest_price(self, ticker):
        resp = requests.get(url='https://api.ratesapi.io/latest?base=' + ticker + '&symbols=CHF')
        data = resp.json()

        price = D(str(data['rates']['CHF']))
        date = parse(data['date'])

        us_timezone = tz.gettz("Europe/Zurich")
        time = date.astimezone(us_timezone)
        return source.SourcePrice(price, time, 'CHF')

    def get_historical_price(self, ticker, time):
        us_timezone = tz.gettz("Europe/Zurich")
        reqdate = time.astimezone(us_timezone).date()

        resp = requests.get(url='https://api.ratesapi.io/' + str(reqdate) + '?base=' + ticker + '&symbols=CHF')
        data = resp.json()

        price = D(str(data['rates']['CHF']))
        date = parse(data['date'])

        time = date.astimezone(us_timezone)
        return source.SourcePrice(price, time, 'CHF')
