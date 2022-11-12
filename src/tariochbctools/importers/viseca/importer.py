import re
from datetime import datetime

import camelot
from beancount.core import amount, data
from beancount.core.number import D
from beancount.ingest import importer
from beancount.ingest.importers.mixins import identifier


class Importer(identifier.IdentifyMixin, importer.ImporterProtocol):
    """An importer for Viseca One Card Statement PDF files."""

    def __init__(self, regexps, account):
        identifier.IdentifyMixin.__init__(self, matchers=[("filename", regexps)])
        self.account = account
        self.currency = "CHF"

    def file_account(self, file):
        return self.account

    def createEntry(self, file, date, entryAmount, text):
        amt = None
        entryAmount = entryAmount.replace("'", "")
        if "-" in entryAmount:
            amt = amount.Amount(D(entryAmount.strip(" -")), "CHF")
        else:
            amt = -amount.Amount(D(entryAmount), "CHF")

        book_date = datetime.strptime(date, "%d.%m.%y").date()

        meta = data.new_metadata(file.name, 0)
        return data.Transaction(
            meta,
            book_date,
            "*",
            "",
            text.strip(),
            data.EMPTY_SET,
            data.EMPTY_SET,
            [
                data.Posting(self.account, amt, None, None, None, None),
            ],
        )

    def extract(self, file, existing_entries):
        entries = []

        p = re.compile(r"^\d\d\.\d\d\.\d\d$")

        columns = ["100,132,400,472,523"]

        firstPageTables = camelot.read_pdf(
            file.name,
            flavor="stream",
            pages="1",
            table_regions=["65,450,585,50"],
            columns=columns,
            split_text=True,
        )
        otherPageTables = camelot.read_pdf(
            file.name,
            flavor="stream",
            pages="2-end",
            table_regions=["65,650,585,50"],
            columns=columns,
            split_text=True,
        )

        tables = [*firstPageTables, *otherPageTables]

        for table in tables:
            df = table.df

            # skip incompatible tables
            if df.columns.size != 6:
                continue

            lastTrxDate = None
            lastAmount = None
            lastDetails = ""
            for _, row in df.iterrows():
                date, valueDate, details, _, _, amountChf = tuple(row)

                if date and not p.match(date) or "Totalbetrag" in details:
                    continue

                trxDate = valueDate
                details = details.strip()

                if amountChf:
                    if lastTrxDate:
                        entries.append(
                            self.createEntry(file, lastTrxDate, lastAmount, lastDetails)
                        )

                    lastTrxDate = trxDate
                    lastAmount = amountChf
                    lastDetails = ""

                lastDetails += details + " "

            if lastTrxDate:
                entries.append(
                    self.createEntry(file, lastTrxDate, lastAmount, lastDetails)
                )

        return entries
