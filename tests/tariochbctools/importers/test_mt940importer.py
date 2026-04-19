import datetime
from collections import namedtuple
from unittest.mock import patch

import pytest

from tariochbctools.importers.general import mt940importer

MockAmount = namedtuple("MockAmount", ["amount", "currency"])


class MockTrx:
    def __init__(self):
        self.data = {
            "bank_reference": "ref123",
            "date": datetime.date(2021, 6, 14),
            "amount": MockAmount("20.5", "CHF"),
            "transaction_details": "DETAIL \nLINE",
            "extra_details": "EXTRA \nLINE",
        }


@pytest.fixture(name="importer")
def importer_fixture():
    return mt940importer.Importer(".*\\.mt940", "Assets:Bank:CHF")


def test_extract_removes_newlines(importer):
    mock_trx = MockTrx()
    with patch("mt940.parse", return_value=[mock_trx]):
        entries = importer.extract("test.mt940", [])
        assert len(entries) == 1

        entry = entries[0]
        # Verify payee has no newlines (prepare_payee returns empty string in base class)
        assert "\n" not in entry.payee

        # Verify narration has no newlines
        assert "\n" not in entry.narration
        assert "DETAIL LINE EXTRA LINE" == entry.narration
