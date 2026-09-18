from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pandas as pd
from beancount.core import data

from tariochbctools.importers.zak import importer as zakimp

HEADER = ["Text", "Valuta", "Belastung", "Gutschrift", "Saldo"]


def table(*rows: list[str]) -> MagicMock:
    """A camelot table, the first row holds the column names."""
    result = MagicMock()
    result.df = pd.DataFrame([HEADER, *rows])
    return result


def extract(firstPage: list[MagicMock], otherPages: list[MagicMock]) -> data.Entries:
    importer = zakimp.Importer(r".*\.pdf", "Assets:Zak")
    with patch.object(
        zakimp.camelot, "read_pdf", side_effect=[firstPage, otherPages]
    ) as readPdf:
        entries = importer.extract("statement.pdf", [])

    assert readPdf.call_count == 2
    return entries


def test_extract_with_tables():
    entries = extract(
        [
            table(
                [
                    "Kartenzahlung BC Buchungsnr. 111",
                    "02.03.2020",
                    "12.50",
                    "",
                    "1'000.00",
                ],
                [
                    "Zahlung Kunde BC Buchungsnr. 222",
                    "03.03.2020",
                    "",
                    "100.00",
                    "1'100.00",
                ],
            )
        ],
        [table(["Saldo per 03.03.2020", "", "", "", "1'100.00"])],
    )

    purchase, payment, balance = entries

    assert isinstance(purchase, data.Transaction)
    assert purchase.date == date(2020, 3, 2)
    assert purchase.narration == "Kartenzahlung"
    assert purchase.meta["zakref"] == "111"
    assert purchase.postings[0].account == "Assets:Zak"
    assert purchase.postings[0].units.number == Decimal("-12.50")

    assert isinstance(payment, data.Transaction)
    assert payment.date == date(2020, 3, 3)
    assert payment.narration == "Zahlung Kunde"
    assert payment.meta["zakref"] == "222"
    assert payment.postings[0].units.number == Decimal("100.00")

    assert isinstance(balance, data.Balance)
    assert balance.date == date(2020, 3, 4)
    assert balance.account == "Assets:Zak"
    assert balance.amount.number == Decimal("1100.00")


def test_extract_without_tables():
    assert extract([], []) == []
