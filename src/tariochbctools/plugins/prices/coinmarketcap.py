from beancount.prices import source
from dateutil.parser import parse
from beancount.core.number import D
import requests
from os import environ


class Source(source.Source):
    def get_latest_price(self, ticker):
        baseCcy = 'CHF'
        headers = {
            'X-CMC_PRO_API_KEY': environ['COINMARKETCAP_API_KEY'],
        }
        params = {
            'symbol': ticker,
            'convert': baseCcy,
        }

        resp = requests.get(url='https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest', params=params, headers=headers)
        data = resp.json()

        quote = data['data'][ticker]['quote'][baseCcy]
        price = D(str(quote['price']))
        date = parse(quote['last_updated'])

        return source.SourcePrice(price, date, baseCcy)

    def get_historical_price(self, ticker, time):
        return None
