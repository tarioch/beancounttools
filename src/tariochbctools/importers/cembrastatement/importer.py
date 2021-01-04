from dateutil.parser import parse

from beancount.ingest import importer
from beancount.core import data
from beancount.core import amount
from beancount.core.number import D
from beancount.ingest.importers.mixins import identifier

import camelot


class Importer(identifier.IdentifyMixin, importer.ImporterProtocol):
    """An importer for Cembra Card Statement PDF files."""

    def __init__(self, regexps, account):
        identifier.IdentifyMixin.__init__(self, matchers=[
            ('filename', regexps)
        ])
        self.account = account

    def file_account(self, file):
        return self.account

    def createEntry(self, file, date, amt, text):
        meta = data.new_metadata(file.name, 0)
        return data.Transaction(
            meta,
            date,
            '*',
            '',
            text.strip(),
            data.EMPTY_SET,
            data.EMPTY_SET,
            [
                data.Posting(self.account, amount.Amount(amt, 'CHF'), None, None, None, None),
            ]
        )

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

                try:
                    book_date = parse(book_date.strip(), dayfirst=True).date()
                except (ValueError, OverflowError):
                    book_date = None

                if book_date:
                    amount = -self.cleanDecimal(debit) if debit else self.cleanDecimal(credit)

                    if amount:
                        entries.append(self.createEntry(file, book_date, amount, text))

        return entries

    def cleanDecimal(self, formattedNumber):
        return D(formattedNumber.replace("'", ""))
