from datetime import datetime
from os import environ

from beancount.core.number import D
from beanprice import source
from dateutil import tz
from ibflex import client, parser


class Source(source.Source):
    def get_latest_price(self, ticker: str) -> source.SourcePrice | None:
        token: str = environ["IBKR_TOKEN"]
        queryId: str = environ["IBKR_QUERY_ID"]

        response = client.download(token, queryId)

        statement = parser.parse(response)
        for custStatement in statement.FlexStatements:
            for position in custStatement.OpenPositions:
                symbol = position.symbol
                symbol = symbol.rstrip("z")
                symbol, _, _ = symbol.partition(".")
                if symbol == ticker:
                    price = D(position.markPrice)
                    timezone = tz.gettz("Europe/Zurich")
                    time = datetime.combine(
                        position.reportDate, datetime.min.time()
                    ).astimezone(timezone)

                    return source.SourcePrice(price, time, position.currency)

        return None

    def get_historical_price(
        self, ticker: str, time: datetime
    ) -> source.SourcePrice | None:
        return None
