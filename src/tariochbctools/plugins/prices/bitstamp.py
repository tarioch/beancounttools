from beancount.prices import source
import datetime
from dateutil import tz
from beancount.core.number import D
import requests


class Source(source.Source):
    def get_latest_price(self, ticker):
        resp = requests.get(url='https://www.bitstamp.net/api/v2/ticker/' + ticker.lower() + 'eur/')
        data = resp.json()

        price = D(data['last'])
        date = datetime.datetime.fromtimestamp(int(data['timestamp']))

        us_timezone = tz.gettz("Europe/Zurich")
        time = date.astimezone(us_timezone)
        return source.SourcePrice(price, time, 'EUR')

    def get_historical_price(self, ticker, time):
        return None
