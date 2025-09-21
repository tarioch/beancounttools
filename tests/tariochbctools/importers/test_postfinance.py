import pytest
from beancount.core.amount import Amount
from beancount.core.number import D

from tariochbctools.importers.postfinance import importer as pfimp

TEST_CSV = """
Booking date;Notification text;Credit in CHF;Debit in CHF;Value;Balance in CHF
31.12.2022;"Preis für Bankpaket Smart";;-5;31.12.2022;7881.98
"""

TEST_CSV_2021 = """
Booking date;Notification text;Credit in CHF;Debit in CHF;Value;Balance in CHF
2022-12-31;"Preis für Bankpaket Smart";;-5;2022-12-31;7881.98
"""


@pytest.fixture(name="importer")
def importer_fixture():
    importer = pfimp.Importer(".*.csv", "Assets:PostFinance:CHF")
    yield importer


@pytest.fixture
def tmp_csv(tmp_path, request):
    csv = tmp_path / "test.csv"
    csv.write_text(request.param)
    yield csv


@pytest.mark.parametrize("tmp_csv", [TEST_CSV], indirect=True)
def test_identify(importer, tmp_csv):
    assert importer.identify(str(tmp_csv))


@pytest.mark.parametrize(
    "tmp_csv",
    (TEST_CSV, TEST_CSV_2021),
    ids=("dd.mm.yyyy", "yyyy-mm-dd"),
    indirect=True,
)
def test_extract(importer, tmp_csv):
    entries = importer.extract(str(tmp_csv), [])
    assert entries
    assert entries[0].postings[-1].units == Amount(D(-5), "CHF")
    assert entries[0].date.year == 2022
