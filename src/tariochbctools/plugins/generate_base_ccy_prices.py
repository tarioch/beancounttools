from beancount.core import data, prices, amount

__plugins__ = ['generate']


def generate(entries, options_map, baseCcy):
    errors = []
    priceMap = prices.build_price_map(entries)

    additionalEntries = []
    for entry in entries:
        if isinstance(entry, data.Price) and entry.amount.currency != baseCcy:
            fxRate = prices.get_price(priceMap, tuple([entry.amount.currency, baseCcy]), entry.date)
            priceInBaseCcy = amount.Amount(entry.amount.number * fxRate[1], baseCcy)

            additionalEntries.append(data.Price(
                entry.meta,
                entry.date,
                entry.currency,
                priceInBaseCcy
            ))

    entries.extend(additionalEntries)

    return entries, errors
