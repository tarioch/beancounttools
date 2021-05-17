from dateutil.parser import parse
from io import StringIO

from beancount.ingest import importer
from beancount.core import data
from beancount.core import amount
from beancount.core.number import D
from beancount.ingest.importers.mixins import identifier

import csv


class Importer(identifier.IdentifyMixin, importer.ImporterProtocol):
    """An importer for Neon CSV files."""

    def __init__(self, regexps, account):
        identifier.IdentifyMixin.__init__(self, matchers=[
            ('filename', regexps)
        ])
        self.account = account

    def name(self):
        return super().name() + self.account

    def file_account(self, file):
        return self.account

    def extract(self, file, existing_entries):
        entries = []

        with StringIO(file.contents()) as csvfile:
            print(file.name)
            print(file.contents())
            reader = csv.DictReader(csvfile, ['date', 'amount', 'description'], delimiter=';', skipinitialspace=True)
            next(reader)
            for row in reader:
                book_date = parse(row['date'].strip()).date()
                amt = amount.Amount(D(row['amount']), 'CHF')

                meta = data.new_metadata(file.name, 0)
                entry = data.Transaction(
                    meta,
                    book_date,
                    '*',
                    '',
                    row['description'].strip(),
                    data.EMPTY_SET,
                    data.EMPTY_SET,
                    [
                        data.Posting(self.account, amt, None, None, None, None),
                    ]
                )
                entries.append(entry)

        return entries
