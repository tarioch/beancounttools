import collections

from beancount.core import data, convert
from collections import defaultdict
from decimal import Decimal
from math import isclose

__plugins__ = ['check']

NonZeroWeightPerPortfolio = collections.namedtuple('NonZeroWeightPerPortfolio', 'source message entry')
DifferentWeightPerPortfolio = collections.namedtuple('DifferentWeightPerPortfolio', 'source message entry')


def check(entries, options_map):
    errors = []

    for entry in data.filter_txns(entries):
        positivePortfolioSums = defaultdict(Decimal)
        negativePortfolioSums = defaultdict(Decimal)
        for posting in entry.postings:
            if posting.meta and 'portfolio_check_weight' in posting.meta:
                weight = Decimal(posting.meta['portfolio_check_weight'])
            else:
                weight = round(convert.get_weight(posting).number, 2)
            account = posting.account
            portfolio = account.split(':')[1]
            if weight > 0:
                positivePortfolioSums[portfolio] += weight
            else:
                negativePortfolioSums[portfolio] += weight

        portfolios = set(list(positivePortfolioSums.keys()) + list(negativePortfolioSums.keys()))
        weight = None
        for portfolio in portfolios:
            positiveWeight = positivePortfolioSums[portfolio]
            negativeWeight = -negativePortfolioSums[portfolio]
            if (not isclose(positiveWeight, negativeWeight, abs_tol=0.05)):
                errors.append(
                    NonZeroWeightPerPortfolio(
                        entry.meta,
                        f'Weights for portfolio {portfolio} don\'t equal zero {positiveWeight} != {-negativeWeight}',
                        entry
                    )
                )
            if weight and weight != positiveWeight and 'skip_cross_portfolio_check' not in entry.meta:
                errors.append(
                    DifferentWeightPerPortfolio(
                        entry.meta,
                        'Not all portfolios have the same weight',
                        entry
                    )
                )
            weight = positiveWeight

    return entries, errors
