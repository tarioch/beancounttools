from datetime import datetime
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from tariochbctools.plugins.prices import ibkr

POSITIONS = b"""<FlexQueryResponse queryName="q" type="AF">
<FlexStatements count="1">
<FlexStatement accountId="U1234567" fromDate="20260101" toDate="20260131" period="LastMonth" whenGenerated="20260201;120000">
<OpenPositions>
<OpenPosition accountId="U1234567" currency="USD" symbol="VWRLz" markPrice="105.25" reportDate="20260131" />
<OpenPosition accountId="U1234567" currency="CHF" symbol="NESN.SW" markPrice="92.5" reportDate="20260131" />
</OpenPositions>
</FlexStatement>
</FlexStatements>
</FlexQueryResponse>"""


@pytest.fixture(name="source")
def source_fixture(monkeypatch):
    monkeypatch.setenv("IBKR_TOKEN", "tok")
    monkeypatch.setenv("IBKR_QUERY_ID", "123")
    with patch.object(ibkr.client, "download", return_value=POSITIONS) as download:
        yield ibkr.Source(), download


@pytest.mark.parametrize(
    "ticker, price, currency",
    [("VWRL", Decimal("105.25"), "USD"), ("NESN", Decimal("92.5"), "CHF")],
)
def test_latest_price_matches_the_cleaned_up_symbol(source, ticker, price, currency):
    source, download = source

    result = source.get_latest_price(ticker)

    download.assert_called_once_with("tok", "123")
    assert result.price == price
    assert result.quote_currency == currency
    assert result.time.tzinfo is not None


def test_latest_price_of_an_unknown_ticker(source):
    source, _ = source

    assert source.get_latest_price("UNKNOWN") is None


def test_historical_price_is_not_supported(source):
    source, _ = source

    assert source.get_historical_price("VWRL", None) is None


def test_positions_without_symbol_are_skipped(source):
    source, download = source
    download.return_value = POSITIONS.replace(b'symbol="VWRLz" ', b"", 1)

    assert source.get_latest_price("VWRL") is None
    assert source.get_latest_price("NESN").price == Decimal("92.5")


def test_matching_position_without_report_date_is_reported(source):
    source, download = source
    download.return_value = POSITIONS.replace(b' reportDate="20260131"', b"", 1)

    with pytest.raises(ValueError, match="reportDate"):
        source.get_latest_price("VWRL")


@pytest.mark.parametrize(
    "reportDate, utcOffset", [("20260131", "+01:00"), ("20260731", "+02:00")]
)
def test_latest_price_time_is_midnight_in_zurich(source, reportDate, utcOffset):
    source, download = source
    download.return_value = POSITIONS.replace(b"20260131", reportDate.encode())

    result = source.get_latest_price("VWRL")

    year, month, day = int(reportDate[:4]), int(reportDate[4:6]), int(reportDate[6:])
    assert result.time == datetime(year, month, day, tzinfo=ZoneInfo("Europe/Zurich"))
    assert (
        result.time.isoformat() == f"{year}-{month:02d}-{day:02d}T00:00:00{utcOffset}"
    )
