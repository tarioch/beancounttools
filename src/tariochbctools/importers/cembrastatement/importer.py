from datetime import datetime, timedelta

from beancount.ingest import importer
from beancount.core import data
from beancount.core import amount
from beancount.core.number import D
from beancount.ingest.importers.mixins import identifier

import camelot
import re


class Importer(identifier.IdentifyMixin, importer.ImporterProtocol):
    """An importer for Cembra Card Statement PDF files."""

    def __init__(self, regexps, account):
        identifier.IdentifyMixin.__init__(self, matchers=[
            ('filename', regexps)
        ])
        self.account = account
        self.currency = 'CHF'

    def file_account(self, file):
        return self.account

    def createEntry(self, file, date, amt, text):
        meta = data.new_metadata(file.name, 0)
        return data.Transaction(
            meta,
            date,
            '*',
            '',
            text,
            data.EMPTY_SET,
            data.EMPTY_SET,
            [
                data.Posting(self.account, amt, None, None, None, None),
            ]
        )

    def createBalanceEntry(self, file, date, amt):
        meta = data.new_metadata(file.name, 0)
        return data.Balance(meta, date, self.account, amt, None, None)

    def extract(self, file, existing_entries):
        entries = []

        tables = camelot.read_pdf(file.name, pages='2-end', flavor='stream', table_areas=['50,700,560,50'])
        for table in tables:
            df = table.df

            # skip incompatible tables
            if df.columns.size != 5:
                continue

            for index, row in df.iterrows():

                trx_date, book_date, text, credit, debit = tuple(row)
                trx_date, book_date, text, credit, debit = trx_date.strip(), book_date.strip(), text.strip(), credit.strip(), debit.strip()

                # Transaction entry
                try:
                    book_date = datetime.strptime(book_date, '%d.%m.%Y').date()
                except Exception:
                    book_date = None

                if book_date:
                    amount = self.getAmount(debit, credit)

                    if amount:
                        entries.append(self.createEntry(file, book_date, amount, text))
                    continue

                # Balance entry
                try:
                    book_date = re.search(r'Saldo per (\d\d\.\d\d\.\d\d\d\d) zu unseren Gunsten CHF', text).group(1)
                    book_date = datetime.strptime(book_date, '%d.%m.%Y').date()
                    # add 1 day: cembra provides balance at EOD, but beancount checks it at SOD
                    book_date = book_date + timedelta(days=1)
                except Exception:
                    book_date = None

                if book_date:
                    amount = self.getAmount(debit, credit)

                    if amount:
                        entries.append(self.createBalanceEntry(file, book_date, amount))

        return entries

    def cleanDecimal(self, formattedNumber):
        return D(formattedNumber.replace("'", ""))

    def getAmount(self, debit, credit):
        amt = -self.cleanDecimal(debit) if debit else self.cleanDecimal(credit)
        if amt:
            return amount.Amount(amt, self.currency)
