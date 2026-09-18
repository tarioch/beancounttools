"""A plugin that verifies that on each transaction, all the "portfolios" have
the same weight.
"""

import collections
from collections import defaultdict
from decimal import Decimal
from math import isclose
from typing import Any

from beancount.core import convert, data

__plugins__ = ["check"]

NonZeroWeightPerPortfolio = collections.namedtuple(
    "NonZeroWeightPerPortfolio", "source message entry"
)
DifferentWeightPerPortfolio = collections.namedtuple(
    "DifferentWeightPerPortfolio", "source message entry"
)


def check(
    entries: data.Entries, options_map: dict[str, Any]
) -> tuple[data.Entries, list[Any]]:
    errors: list[Any] = []

    for entry in data.filter_txns(entries):
        positivePortfolioSums: defaultdict[str, Decimal] = defaultdict(Decimal)
        negativePortfolioSums: defaultdict[str, Decimal] = defaultdict(Decimal)
        for posting in entry.postings:
            if posting.meta and "portfolio_check_weight" in posting.meta:
                postingWeight = Decimal(posting.meta["portfolio_check_weight"])
            else:
                postingWeight = round(convert.get_weight(posting).number, 2)
            account = posting.account
            portfolio = account.split(":")[1]
            if postingWeight > 0:
                positivePortfolioSums[portfolio] += postingWeight
            else:
                negativePortfolioSums[portfolio] += postingWeight

        portfolios = set(
            list(positivePortfolioSums.keys()) + list(negativePortfolioSums.keys())
        )
        weight: Decimal | None = None
        for portfolio in portfolios:
            positiveWeight = positivePortfolioSums[portfolio]
            negativeWeight = -negativePortfolioSums[portfolio]
            if not isclose(positiveWeight, negativeWeight, abs_tol=0.05):
                errors.append(
                    NonZeroWeightPerPortfolio(
                        entry.meta,
                        f"Weights for portfolio {portfolio} don't equal zero {positiveWeight} != {-negativeWeight}",
                        entry,
                    )
                )
            if (
                weight
                and weight != positiveWeight
                and "skip_cross_portfolio_check" not in entry.meta
            ):
                errors.append(
                    DifferentWeightPerPortfolio(
                        entry.meta, "Not all portfolios have the same weight", entry
                    )
                )
            weight = positiveWeight

    return entries, errors
