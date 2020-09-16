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

        tables = camelot.read_pdf(file.name, pages='2-end', flavor='stream', table_areas=['60,670,600,100'])
        df = tables[0].df
        new_header = df.iloc[0]
        df = df[1:]
        df.columns = new_header

        for index, row in df.iterrows():
            try:
                date = parse(row[1].strip(), dayfirst=True).date()
            except ValueError:
                date = None

            if date:
                text = row[2]
                credit = row[3]
                debit = row[4]
                amount = -self.cleanDecimal(debit) if debit else self.cleanDecimal(credit)

                if amount:
                    entries.append(self.createEntry(file, date, amount, text))

        return entries

    def cleanDecimal(self, formattedNumber):
        return D(formattedNumber.replace("'", ""))
