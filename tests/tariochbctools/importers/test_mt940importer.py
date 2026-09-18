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


def test_extract_removes_newlines(importer, tmp_path):
    statement = tmp_path / "test.mt940"
    statement.write_bytes(b"")
    mock_trx = MockTrx()
    with patch("mt940.parse", return_value=[mock_trx]):
        entries = importer.extract(str(statement), [])
        assert len(entries) == 1

        entry = entries[0]
        # Verify payee has no newlines (prepare_payee returns empty string in base class)
        assert "\n" not in entry.payee

        # Verify narration has no newlines
        assert "\n" not in entry.narration
        assert "DETAIL LINE EXTRA LINE" == entry.narration


STATEMENT = (
    ":20:STARTUMS\n"
    ":25:CH9300762011623852957\n"
    ":28C:1/1\n"
    ":60F:C200101CHF1000,00\n"
    ":61:2001020102D10,00NMSCNONREF//REF1\n"
    ":86:Zahlung an Müller\n"
    ":62F:C200102CHF990,00\n"
)


@pytest.mark.parametrize("encoding", ["utf-8", "cp1252"])
def test_extract_keeps_umlauts(importer, tmp_path, encoding):
    statement = tmp_path / "statement.mt940"
    statement.write_bytes(STATEMENT.encode(encoding))

    entries = importer.extract(str(statement), [])

    assert [entry.narration for entry in entries] == ["Zahlung an Müller"]


@pytest.mark.parametrize(
    "content, encoding",
    [
        ("Zahlung an Müller".encode(), "utf-8"),
        (b"Zahlung an M\xfcller", "cp1252"),
        # neither valid utf-8 nor cp1252 (0x81 is undefined there)
        (b"Zahlung an M\xfcller\x81", "latin-1"),
    ],
)
def test_detect_encoding(tmp_path, content, encoding):
    statement = tmp_path / "statement.mt940"
    statement.write_bytes(content)

    assert mt940importer.detect_encoding(str(statement)) == encoding
