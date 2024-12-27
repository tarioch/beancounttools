import csv
import re

from beancount.core import amount, data
from beancount.core.number import D
from beangulp import Importer
from dateutil.parser import parse


class SwisscardImporter(Importer):
    """An importer for Swisscard's cashback CSV files."""

    def __init__(self, filepattern: str, account: data.Account):
        self._filepattern = filepattern
        self._account = account

    def name(self) -> str:
        return super().name() + self._account

    def identify(self, filepath: str) -> bool:
        return re.search(self._filepattern, filepath) is not None

    def account(self, filepath: str) -> data.Account:
        return self._account

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        entries = []
        with open(filepath) as csvfile:
            reader = csv.DictReader(
                csvfile,
                delimiter=",",
                skipinitialspace=True,
            )
            for row in reader:
                book_date = parse(row["Transaction date"].strip(), dayfirst=True).date()
                amt = amount.Amount(-D(row["Amount"]), row["Currency"])
                metakv = {
                    "merchant": row["Merchant Category"],
                    "category": row["Registered Category"],
                }
                meta = data.new_metadata(filepath, 0, metakv)
                description = row["Description"].strip()
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
