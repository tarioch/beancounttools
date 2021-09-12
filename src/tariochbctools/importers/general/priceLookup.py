from datetime import date

from beancount.core import amount, prices


class PriceLookup:
    def __init__(self, existing_entries, baseCcy: str):
        self.priceMap = prices.build_price_map(existing_entries)
        self.baseCcy = baseCcy

    def fetchPriceAmount(self, instrument: str, date: date):
        price = prices.get_price(self.priceMap, tuple([instrument, self.baseCcy]), date)
        return price[1]

    def fetchPrice(self, instrument: str, date: date):
        if instrument == self.baseCcy:
            return None

        return amount.Amount(self.fetchPriceAmount(instrument, date), self.baseCcy)
