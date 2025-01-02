import datetime
import re
from datetime import timedelta

import beangulp
import camelot
from beancount.core import amount, data
from beancount.core.number import D


class Importer(beangulp.Importer):
    """An importer for Cembra Card Statement PDF files."""

    def __init__(self, filepattern: str, account: data.Account):
        self._filepattern = filepattern
        self._account = account
        self.currency = "CHF"

    def identify(self, filepath: str) -> bool:
        return re.search(self._filepattern, filepath) is not None

    def account(self, filepath: str) -> data.Account:
        return self._account

    def createEntry(
        self, filepath: str, date: datetime.date, amt: data.Decimal, text: str
    ) -> data.Transaction:
        meta = data.new_metadata(filepath, 0)
        return data.Transaction(
            meta,
            date,
            "*",
            "",
            text,
            data.EMPTY_SET,
            data.EMPTY_SET,
            [
                data.Posting(self._account, amt, None, None, None, None),
            ],
        )

    def createBalanceEntry(
        self, filepath: str, date: datetime.date, amt: data.Decimal
    ) -> data.Balance:
        meta = data.new_metadata(filepath, 0)
        return data.Balance(meta, date, self._account, amt, None, None)

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        entries = []

        tables = camelot.read_pdf(
            filepath, pages="2-end", flavor="stream", table_areas=["50,700,560,50"]
        )
        for table in tables:
            df = table.df

            # skip incompatible tables
            if df.columns.size != 5:
                continue

            for index, row in df.iterrows():
                trx_date, book_date, text, credit, debit = tuple(row)
                trx_date, book_date, text, credit, debit = (
                    trx_date.strip(),
                    book_date.strip(),
                    text.strip(),
                    credit.strip(),
                    debit.strip(),
                )

                # Transaction entry
                try:
                    book_date = datetime.datetime.strptime(book_date, "%d.%m.%Y").date()
                except Exception:
                    book_date = None

                if book_date:
                    amount = self.getAmount(debit, credit)

                    if amount:
                        entries.append(
                            self.createEntry(filepath, book_date, amount, text)
                        )
                    continue

                # Balance entry
                try:
                    m = re.search(
                        r"Saldo per (\d\d\.\d\d\.\d\d\d\d) zu unseren Gunsten CHF",
                        text,
                    )
                    if m:
                        book_date = m.group(1)
                        book_date = datetime.datetime.strptime(
                            book_date, "%d.%m.%Y"
                        ).date()
                        # add 1 day: cembra provides balance at EOD, but beancount checks it at SOD
                        book_date = book_date + timedelta(days=1)
                except Exception:
                    book_date = None

                if book_date:
                    amount = self.getAmount(debit, credit)

                    if amount:
                        entries.append(
                            self.createBalanceEntry(filepath, book_date, amount)
                        )

        return entries

    def cleanDecimal(self, formattedNumber: str) -> data.Decimal:
        return D(formattedNumber.replace("'", ""))

    def getAmount(self, debit: str, credit: str) -> data.Amount:
        amt = -self.cleanDecimal(debit) if debit else self.cleanDecimal(credit)
        if amt:
            return amount.Amount(amt, self.currency)
