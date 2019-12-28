from beancount.core import prices, amount


class PriceLookup:
    def __init__(self, existing_entries, baseCcy):
        self.priceMap = prices.build_price_map(existing_entries)
        self.baseCcy = baseCcy

    def fetchPriceAmount(self, instrument, date):
        price = prices.get_price(self.priceMap, tuple([instrument, self.baseCcy]), date)
        return price[1]

    def fetchPrice(self, instrument, date):
        if instrument == self.baseCcy:
            return None

        return amount.Amount(self.fetchPriceAmount(instrument, date), self.baseCcy)
