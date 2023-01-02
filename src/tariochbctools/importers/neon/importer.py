import csv
from io import StringIO

from beancount.core import amount, data
from beancount.core.number import D
from beancount.ingest import importer
from beancount.ingest.importers.mixins import identifier
from dateutil.parser import parse


class Importer(identifier.IdentifyMixin, importer.ImporterProtocol):
    """An importer for Neon CSV files."""

    def __init__(self, regexps, account):
        identifier.IdentifyMixin.__init__(self, matchers=[("filename", regexps)])
        self.account = account

    def name(self):
        return super().name() + self.account

    def file_account(self, file):
        return self.account

    def extract(self, file, existing_entries):
        entries = []

        with StringIO(file.contents()) as csvfile:
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

                meta = data.new_metadata(file.name, 0, metakv)
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
                        data.Posting(self.account, amt, None, None, None, None),
                    ],
                )
                entries.append(entry)

        return entries
