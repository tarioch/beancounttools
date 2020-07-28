from beancount.prices import source
from dateutil import tz
from beancount.core.number import D
from os import environ
from ibflex import client, parser
from datetime import datetime
from time import sleep


class Source(source.Source):
    def get_latest_price(self, ticker):
        token = environ['IBKR_TOKEN']
        queryId = environ['IBKR_QUERY_ID']

        try:
            response = client.download(token, queryId)
        except client.ResponseCodeError as e:
            if e.code == '1018':
                sleep(10)
                response = client.download(token, queryId)
            else:
                raise e

        statement = parser.parse(response)
        for position in statement.FlexStatements[0].OpenPositions:
            if position.symbol.rstrip('z') == ticker:
                price = D(position.markPrice)
                timezone = tz.gettz("Europe/Zurich")
                time = datetime.combine(position.reportDate, datetime.min.time()).astimezone(timezone)

                return source.SourcePrice(price, time, position.currency)

        return None

    def get_historical_price(self, ticker, time):
        return None
