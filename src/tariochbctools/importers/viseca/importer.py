import re
from datetime import datetime

import beangulp
import camelot
from beancount.core import amount, data
from beancount.core.number import D


class Importer(beangulp.Importer):
    """An importer for Viseca One Card Statement PDF files."""

    def __init__(self, filepattern: str, account: data.Account):
        self._filepattern = filepattern
        self._account = account
        self.currency = "CHF"

    def identify(self, filepath: str) -> bool:
        return re.search(self._filepattern, filepath) is not None

    def account(self, filepath: str) -> data.Account:
        return self._account

    def createEntry(
        self, filepath: str, date: str, entryAmount: str | None, text: str
    ) -> data.Transaction:
        amt = None
        if not entryAmount:
            entryAmount = ""
        entryAmount = entryAmount.replace("'", "")
        if "-" in entryAmount:
            amt = amount.Amount(D(entryAmount.strip(" -")), "CHF")
        else:
            amt = -amount.Amount(D(entryAmount), "CHF")

        book_date = datetime.strptime(date, "%d.%m.%y").date()

        meta = data.new_metadata(filepath, 0)
        return data.Transaction(
            meta,
            book_date,
            "*",
            "",
            text.strip(),
            data.EMPTY_SET,
            data.EMPTY_SET,
            [
                data.Posting(self._account, amt, None, None, None, None),
            ],
        )

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        entries = []

        p = re.compile(r"^\d\d\.\d\d\.\d\d$")

        columns = ["100,132,400,472,523"]

        firstPageTables = camelot.read_pdf(
            filepath,
            flavor="stream",
            pages="1",
            table_areas=["65,435,585,100"],
            columns=columns,
            split_text=True,
        )
        otherPageTables = camelot.read_pdf(
            filepath,
            flavor="stream",
            pages="2-end",
            table_areas=["65,670,585,100"],
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
                            self.createEntry(
                                filepath, lastTrxDate, lastAmount, lastDetails
                            )
                        )

                    lastTrxDate = trxDate
                    lastAmount = amountChf
                    lastDetails = ""

                lastDetails += details + " "

            if lastTrxDate:
                entries.append(
                    self.createEntry(filepath, lastTrxDate, lastAmount, lastDetails)
                )

        return entries
