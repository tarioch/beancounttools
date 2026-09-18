from datetime import date
from decimal import Decimal

from beancount.core import amount, data, prices


class PriceLookup:
    def __init__(self, existing: data.Entries, baseCcy: str):
        if existing:
            self.priceMap = prices.build_price_map(existing)
        else:
            self.priceMap = None
        self.baseCcy = baseCcy

    def fetchPriceAmount(self, instrument: str, date: date) -> Decimal | None:
        if self.priceMap:
            price = prices.get_price(
                self.priceMap, tuple([instrument, self.baseCcy]), date
            )
            return price[1]
        else:
            return Decimal(1)

    def fetchPrice(self, instrument: str, date: date) -> amount.Amount | None:
        if instrument == self.baseCcy:
            return None

        # without a price the amount has no number
        return amount.Amount(self.fetchPriceAmount(instrument, date), self.baseCcy)  # type: ignore[arg-type]
