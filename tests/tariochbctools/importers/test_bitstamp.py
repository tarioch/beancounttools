import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from beancount.core import data
from beancount.core.number import MISSING

from tariochbctools.importers.bitst import importer as bitstimp


class FixedDate(datetime.date):
    @classmethod
    def today(cls):
        return datetime.date(2026, 9, 19)


# bitstamp returns the newest transaction first: a trade of btc for eur where the fee is in eur, a trade of usd for btc
# where the fee is in usd, a withdrawal, a deposit and a transaction that is older than the month cutoff
TRANSACTIONS = [
    {
        "id": 4,
        "type": "2",
        "datetime": "2026-09-05 10:00:00",
        "usd": "0",
        "btc": "-0.5",
        "eur": "1000.00",
        "fee": "2.5",
        "btc_eur": "2000",
    },
    {
        "id": 3,
        "type": "2",
        "datetime": "2026-09-03 10:00:00",
        "usd": "-1000.00",
        "btc": "0.01",
        "eur": "0",
        "fee": "0.05",
        "btc_usd": "100000",
    },
    {
        "id": 2,
        "type": "1",
        "datetime": "2026-09-02 10:00:00",
        "usd": "-200.00",
        "btc": "0",
        "eur": "0",
        "fee": "0",
    },
    {
        "id": 1,
        "type": "0",
        "datetime": "2026-09-01 10:00:00",
        "usd": "500.00",
        "btc": "0",
        "eur": "0",
        "fee": "0",
    },
    {
        "id": 0,
        "type": "0",
        "datetime": "2024-01-01 10:00:00",
        "usd": "1.00",
        "btc": "0",
        "eur": "0",
        "fee": "0",
    },
]

CONFIG = """username: '123'
key: k
secret: s
account: Assets:Bitstamp
otherExpensesAccount: Expenses:Fee
capGainAccount: Income:Capitalgain
monthCutoff: 3
currencies:
  - usd
  - btc
  - eur
"""


def price(currency, number):
    return data.Price(
        {}, datetime.date(2026, 9, 1), currency, data.Amount(Decimal(number), "CHF")
    )


def extract(tmp_path, transactions=TRANSACTIONS, existing=None):
    config = tmp_path / "bitstamp.yaml"
    config.write_text(CONFIG, encoding="utf-8")
    client = MagicMock()
    client.user_transactions.return_value = list(transactions)
    with (
        patch.object(bitstimp.bitstamp.client, "Trading", return_value=client),
        patch.object(bitstimp, "date", FixedDate),
    ):
        return bitstimp.Importer().extract(str(config), existing or [])


def summary(entry):
    """ref, date, narration and the postings as (account, units, cost as (per unit, total, currency), price)"""

    def name(value):
        return "MISSING" if value is MISSING else None if value is None else str(value)

    postings = [
        (
            p.account,
            str(p.units) if p.units is not None else None,
            (name(p.cost.number_per), name(p.cost.number_total), name(p.cost.currency))
            if p.cost is not None
            else None,
            str(p.price) if p.price is not None else None,
        )
        for p in entry.postings
    ]
    return entry.meta["ref"], entry.date, entry.narration, postings


def test_extract_without_prices(tmp_path):
    entries = extract(tmp_path)

    assert [summary(e) for e in entries] == [
        (
            "1",
            datetime.date(2026, 9, 1),
            "Deposit",
            [("Assets:Bitstamp:USD", "500.00 USD", ("1", None, "CHF"), None)],
        ),
        (
            "2",
            datetime.date(2026, 9, 2),
            "Withdrawal",
            [("Assets:Bitstamp:USD", "-200.00 USD", None, None)],
        ),
        (
            "3",
            datetime.date(2026, 9, 3),
            "Trade",
            [
                ("Assets:Bitstamp:BTC", "0.01 BTC", (None, "1000.05", "CHF"), None),
                ("Assets:Bitstamp:USD", "-1000.05 USD", None, "1 CHF"),
                ("Expenses:Fee", "0.05 CHF", None, None),
                ("Income:Capitalgain", None, None, None),
            ],
        ),
        (
            "4",
            datetime.date(2026, 9, 5),
            "Trade",
            [
                ("Assets:Bitstamp:EUR", "997.50 EUR", None, "1 CHF"),
                ("Assets:Bitstamp:BTC", "-0.5 BTC", ("MISSING", None, "MISSING"), None),
                ("Expenses:Fee", "2.50 CHF", None, None),
                ("Income:Capitalgain", None, None, None),
            ],
        ),
    ]
    assert all(isinstance(entry, data.Transaction) for entry in entries)


def test_extract_with_prices(tmp_path):
    existing = [price("BTC", "90000"), price("EUR", "0.95"), price("USD", "0.8")]

    entries = extract(tmp_path, existing=existing)

    assert [summary(e) for e in entries] == [
        (
            "1",
            datetime.date(2026, 9, 1),
            "Deposit",
            [("Assets:Bitstamp:USD", "500.00 USD", ("0.8", None, "CHF"), None)],
        ),
        (
            "2",
            datetime.date(2026, 9, 2),
            "Withdrawal",
            [("Assets:Bitstamp:USD", "-200.00 USD", None, None)],
        ),
        (
            "3",
            datetime.date(2026, 9, 3),
            "Trade",
            [
                ("Assets:Bitstamp:BTC", "0.01 BTC", (None, "800.040", "CHF"), None),
                ("Assets:Bitstamp:USD", "-1000.05 USD", None, "0.8 CHF"),
                ("Expenses:Fee", "0.04 CHF", None, None),
                ("Income:Capitalgain", None, None, None),
            ],
        ),
        (
            "4",
            datetime.date(2026, 9, 5),
            "Trade",
            [
                ("Assets:Bitstamp:EUR", "997.50 EUR", None, "0.95 CHF"),
                ("Assets:Bitstamp:BTC", "-0.5 BTC", ("MISSING", None, "MISSING"), None),
                ("Expenses:Fee", "2.38 CHF", None, None),
                ("Income:Capitalgain", None, None, None),
            ],
        ),
    ]


def test_extract_skips_transactions_before_the_cutoff(tmp_path):
    entries = extract(tmp_path)

    assert "0" not in [entry.meta["ref"] for entry in entries]


def test_unhandled_transaction_type(tmp_path):
    transactions = [
        {
            "id": 9,
            "type": "14",
            "datetime": "2026-09-05 10:00:00",
            "usd": "0",
            "btc": "0",
            "eur": "0",
            "fee": "0",
        }
    ]

    with pytest.raises(ValueError, match="Transaction type 14 is not handled"):
        extract(tmp_path, transactions)


def test_deposit_without_positive_amount_is_reported(tmp_path):
    transactions = [
        {
            "id": 7,
            "type": "0",
            "datetime": "2026-09-05 10:00:00",
            "usd": "0",
            "btc": "0",
            "eur": "0",
            "fee": "0",
        }
    ]

    with pytest.raises(ValueError, match="Transaction 7 has no positive amount"):
        extract(tmp_path, transactions)


def test_withdrawal_without_negative_amount_is_reported(tmp_path):
    transactions = [
        {
            "id": 8,
            "type": "1",
            "datetime": "2026-09-05 10:00:00",
            "usd": "0",
            "btc": "0",
            "eur": "0",
            "fee": "0",
        }
    ]

    with pytest.raises(ValueError, match="Transaction 8 has no negative amount"):
        extract(tmp_path, transactions)


def test_trade_with_only_one_side_is_reported(tmp_path):
    transactions = [
        {
            "id": 9,
            "type": "2",
            "datetime": "2026-09-05 10:00:00",
            "usd": "0",
            "btc": "0.5",
            "eur": "0",
            "fee": "0",
        }
    ]

    with pytest.raises(ValueError, match="Transaction 9 has no negative amount"):
        extract(tmp_path, transactions)


def test_trade_without_a_price_is_reported(tmp_path):
    # prices exist, but none for the currency of the fee (usd)
    existing = [price("BTC", "90000")]

    with pytest.raises(ValueError, match="There is no price for USD"):
        extract(tmp_path, existing=existing)
