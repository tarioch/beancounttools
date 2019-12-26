from beancount.prices import source
from dateutil import tz
from dateutil.parser import parse
from beancount.core.number import D
import requests
from os import environ
from time import sleep


class Source(source.Source):
    def get_latest_price(self, ticker):
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': ticker,
            'apikey': environ['ALPHAVANTAGE_API_KEY'],
        }

        resp = requests.get(url='https://www.alphavantage.co/query', params=params)
        data = resp.json()
        if 'Note' in data:
            sleep(60)
            resp = requests.get(url='https://www.alphavantage.co/query', params=params)
            data = resp.json()

        priceData = data['Global Quote']

        price = D(priceData['05. price'])
        date = parse(priceData['07. latest trading day'])

        us_timezone = tz.gettz("Europe/Zurich")
        time = date.astimezone(us_timezone)
        return source.SourcePrice(price, time, 'USD')

    def get_historical_price(self, ticker, time):
        return None
