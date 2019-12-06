from beancount.prices import source
import datetime
from dateutil import tz
from dateutil.parser import parse
from beancount.core.number import D
import requests
from os import environ
from time import sleep

import tabula
import tempfile

class Source(source.Source):
    def get_latest_price(self, ticker):

        with tempfile.NamedTemporaryFile() as temp:

            resp = requests.get(url='https://www.swisslife.ch/content/dam/slam/documents_publications/investment_foundation/de/r/d_tageskurse.pdf')
            temp.write(resp.content)

            data = tabula.read_pdf(temp.name, area=[190,82,740,1130], lattice=True)
            row = data.query('Valor==' + ticker)
            price = D(str(row['Inventarwert *'].values[0]))
            date = parse(row['Abschluss-\rdatum'].values[0], dayfirst=True)

            us_timezone = tz.gettz("Europe/Zurich")
            time = date.astimezone(us_timezone)
            return source.SourcePrice(price, time, 'USD')

    def get_historical_price(self, ticker, time):
        return None
