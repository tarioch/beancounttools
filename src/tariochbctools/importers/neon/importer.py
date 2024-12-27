import csv
import re

import beangulp
from beancount.core import amount, data
from beancount.core.number import D
from dateutil.parser import parse


class Importer(beangulp.Importer):
    """An importer for Neon CSV files."""

    def __init__(self, filepattern: str, account: data.Account):
        self._filepattern = filepattern
        self._account = account

    def identify(self, filepath: str) -> bool:
        return re.search(self._filepattern, filepath) is not None

    def name(self) -> str:
        return super().name() + self._account

    def account(self, filepath: str) -> data.Account:
        return self._account

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        entries = []

        with open(filepath) as csvfile:
            reader = csv.DictReader(
                csvfile,
                [
                    "Date",
                    "Amount",
                    "Original amount",
                    "Original currency",
                    "Exchange rate",
                    "Description",
                    "Subject",
                    "Category",
                    "Tags",
                    "Wise",
                    "Spaces",
                ],
                delimiter=";",
                skipinitialspace=True,
            )
            next(reader)
            for row in reader:
                book_date = parse(row["Date"].strip()).date()
                amt = amount.Amount(D(row["Amount"]), "CHF")
                metakv = {
                    "category": row["Category"],
                }
                if row["Original currency"] != "":
                    metakv["original_currency"] = row["Original currency"]
                    metakv["original_amount"] = row["Original amount"]
                    metakv["exchange_rate"] = row["Exchange rate"]

                meta = data.new_metadata(filepath, 0, metakv)
                description = row["Description"].strip()
                if row["Subject"].strip() != "":
                    description = description + ": " + row["Subject"].strip()

                entry = data.Transaction(
                    meta,
                    book_date,
                    "*",
                    "",
                    description,
                    data.EMPTY_SET,
                    data.EMPTY_SET,
                    [
                        data.Posting(self._account, amt, None, None, None, None),
                    ],
                )
                entries.append(entry)

        return entries
