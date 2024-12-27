from datetime import date

from beancount.core import amount, data, prices
from beancount.core.number import D


class PriceLookup:
    def __init__(self, existing: data.Entries, baseCcy: str):
        if existing:
            self.priceMap = prices.build_price_map(existing)
        else:
            self.priceMap = None
        self.baseCcy = baseCcy

    def fetchPriceAmount(self, instrument: str, date: date) -> data.Amount:
        if self.priceMap:
            price = prices.get_price(
                self.priceMap, tuple([instrument, self.baseCcy]), date
            )
            return price[1]
        else:
            return D(1)

    def fetchPrice(self, instrument: str, date: date) -> data.Amount:
        if instrument == self.baseCcy:
            return None

        return amount.Amount(self.fetchPriceAmount(instrument, date), self.baseCcy)
