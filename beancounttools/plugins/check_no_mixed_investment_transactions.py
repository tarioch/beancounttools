import collections

from beancount.core import getters
from beancount.core import data

__plugins__ = ['check']

MixedInvestAssets = collections.namedtuple('MixedInvestAssets', 'source message entry')

def check(entries, options_map):
    errors = []

    commodity_map = getters.get_commodity_map(entries, create_missing=True)
    commodity_type_map = getters.get_values_meta(commodity_map, 'type')

    for entry in data.filter_txns(entries):
        ccys = set()
        for posting in entry.postings:
            ccy = posting.units.currency
            if commodity_type_map[ccy] == 'invest':
                ccys.add(ccy)

        if len(ccys) > 1:
            errors.append(MixedInvestAssets(
                entry.meta,
                "Transaction with two or more different investment postings",
                entry
            ))

    return entries, errors

