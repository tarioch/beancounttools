"""A plugin that inserts an additional price to the base rate by applying
fx rate to a price.
"""

import datetime
from typing import Any

from beancount.core import amount, data, prices

__plugins__ = ["generate"]


def generate(
    entries: data.Entries, options_map: dict[str, Any], baseCcy: str
) -> tuple[data.Entries, list[Any]]:
    errors: list[Any] = []
    priceMap = prices.build_price_map(entries)

    additionalEntries = []
    for entry in entries:
        if (
            isinstance(entry, data.Price)
            and entry.amount.currency != baseCcy
            and entry.currency != baseCcy
        ):
            fxTuple = tuple([entry.amount.currency, baseCcy])
            fxRate = prices.get_price(priceMap, fxTuple, entry.date)
            if fxRate[1] and not _alreadyExistingPrice(
                priceMap, tuple([entry.currency, baseCcy]), entry.date
            ):
                priceInBaseCcy = amount.Amount(entry.amount.number * fxRate[1], baseCcy)

                additionalEntries.append(
                    data.Price(entry.meta, entry.date, entry.currency, priceInBaseCcy)
                )

    entries.extend(additionalEntries)

    return entries, errors


def _alreadyExistingPrice(
    priceMap: dict[Any, Any], fxTuple: tuple[str, str], date: datetime.date
) -> bool:
    if fxTuple in priceMap:
        for alreadyExistingPriceDates in priceMap[fxTuple]:
            if date == alreadyExistingPriceDates[0]:
                return True

    return False
