import datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from beancount.core import data

from tariochbctools.importers.ibkr import flexclient
from tariochbctools.importers.ibkr import importer as ibkrimp

# a synthetic flex statement: a buy in a foreign currency, a buy in the base currency (without a fxRateToBase),
# a dividend with the matching withholding tax, a dividend without tax and a cash transaction that is not a dividend
STATEMENT = b"""<FlexQueryResponse queryName="q" type="AF">
<FlexStatements count="1">
<FlexStatement accountId="U1234567" fromDate="20260101" toDate="20260131" period="LastMonth" whenGenerated="20260201;120000">
<Trades>
<Trade accountId="U1234567" currency="USD" symbol="VWRLz" tradeDate="20260115" quantity="10" tradePrice="100.5" ibCommission="-1.5" ibCommissionCurrency="USD" netCash="-1006.5" fxRateToBase="0.9" />
<Trade accountId="U1234567" currency="CHF" symbol="NESN.SW" tradeDate="20260116" quantity="5" tradePrice="90" ibCommission="-1" ibCommissionCurrency="CHF" netCash="-451" />
</Trades>
<CashTransactions>
<CashTransaction accountId="U1234567" currency="USD" symbol="VWRLz" dateTime="20260120;120000" amount="25" type="Dividends" description="VWRL(IE00BK5BQT80) CASH DIVIDEND USD 0.25 PER SHARE (Ordinary Dividend)" />
<CashTransaction accountId="U1234567" currency="USD" symbol="VWRLz" dateTime="20260120;120000" amount="-3.75" type="Withholding Tax" description="VWRL(IE00BK5BQT80) CASH DIVIDEND USD 0.25 PER SHARE - US TAX" />
<CashTransaction accountId="U1234567" currency="USD" symbol="AAPL" dateTime="20260125;120000" amount="10" type="Dividends" description="AAPL(US0378331005) CASH DIVIDEND USD 0.10 PER SHARE (Ordinary Dividend)" />
<CashTransaction accountId="U1234567" currency="USD" symbol="AAPL" dateTime="20260126;120000" amount="-1" type="Other Fees" description="AAPL some fee" />
</CashTransactions>
</FlexStatement>
</FlexStatements>
</FlexQueryResponse>"""


def extract(tmp_path, statement=STATEMENT, config="", existing=None):
    configFile = tmp_path / "ibkr.yaml"
    configFile.write_text(
        f"token: tok\nqueryId: '123'\nbaseCcy: CHF\n{config}", encoding="utf-8"
    )
    with patch.object(flexclient, "download", return_value=statement) as download:
        entries = ibkrimp.Importer().extract(str(configFile), existing or [])
    return entries, download


def summary(entry):
    """date, narration and the postings as (account, units, cost per unit, price)"""
    postings = [
        (
            p.account,
            str(p.units) if p.units is not None else None,
            str(p.cost.number_per) if p.cost is not None else None,
            str(p.price) if p.price is not None else None,
        )
        for p in entry.postings
    ]
    return entry.date, entry.narration, postings


def test_extract_buys_and_dividends(tmp_path):
    entries, _ = extract(tmp_path)

    assert [summary(e) for e in entries] == [
        (
            datetime.date(2026, 1, 15),
            "Buy",
            [
                ("Assets:U1234567:Investment:IB:VWRL", "10 VWRL", "90.45", None),
                ("Expenses:U1234567:Fees", "1.35 CHF", None, None),
                ("Assets:U1234567:Liquidity:IB:USD", "-1006.50 USD", None, "0.9 CHF"),
            ],
        ),
        (
            datetime.date(2026, 1, 16),
            "Buy",
            [
                ("Assets:U1234567:Investment:IB:NESN", "5 NESN", "90", None),
                ("Expenses:U1234567:Fees", "1.00 CHF", None, None),
                ("Assets:U1234567:Liquidity:IB:CHF", "-451.00 CHF", None, None),
            ],
        ),
        (
            datetime.date(2026, 1, 20),
            "Dividend: VWRL(IE00BK5BQT80) CASH DIVIDEND USD 0.25 PER SHARE (Ordinary Dividend)",
            [
                ("Assets:U1234567:Investment:IB:VWRL", "0 VWRL", None, None),
                ("Assets:U1234567:Liquidity:IB:USD", "21.25 USD", None, "1 CHF"),
                (
                    "Assets:U1234567:Receivable:Verrechnungssteuer",
                    "3.75 USD",
                    None,
                    None,
                ),
                ("Income:U1234567:Interest", None, None, None),
            ],
        ),
        (
            datetime.date(2026, 1, 25),
            "Dividend: AAPL(US0378331005) CASH DIVIDEND USD 0.10 PER SHARE (Ordinary Dividend)",
            [
                ("Assets:U1234567:Investment:IB:AAPL", "0 AAPL", None, None),
                ("Assets:U1234567:Liquidity:IB:USD", "10 USD", None, "1 CHF"),
                ("Income:U1234567:Interest", None, None, None),
            ],
        ),
    ]
    assert all(isinstance(entry, data.Transaction) for entry in entries)


def test_extract_uses_the_price_from_the_existing_entries(tmp_path):
    existing = [
        data.Price(
            {}, datetime.date(2026, 1, 1), "USD", data.Amount(Decimal("0.8"), "CHF")
        )
    ]

    entries, _ = extract(tmp_path, existing=existing)

    dividend = entries[2]
    assert str(dividend.postings[1].price) == "0.8 CHF"


def test_extract_passes_the_period_to_the_download(tmp_path):
    _, download = extract(tmp_path, config="period: 90\n")

    download.assert_called_once_with("tok", "123", period=90)


def test_extract_without_period(tmp_path):
    _, download = extract(tmp_path)

    download.assert_called_once_with("tok", "123", period=None)


@pytest.mark.parametrize(
    "symbol, expected",
    [("VWRLz", "VWRL"), ("NESN.SW", "NESN"), ("AAPL", "AAPL"), ("ABCz.US", "ABCz")],
)
def test_cleanup_symbol(symbol, expected):
    assert ibkrimp.Importer().cleanupSymbol(symbol) == expected


def test_missing_field_is_reported(tmp_path):
    # the first trade has no symbol
    statement = STATEMENT.replace(b'symbol="VWRLz" tradeDate', b"tradeDate", 1)

    with pytest.raises(ValueError, match="symbol"):
        extract(tmp_path, statement)


def test_foreign_currency_buy_needs_the_fx_rate(tmp_path):
    statement = STATEMENT.replace(b' fxRateToBase="0.9"', b"")

    with pytest.raises(ValueError, match="fxRateToBase"):
        extract(tmp_path, statement)
