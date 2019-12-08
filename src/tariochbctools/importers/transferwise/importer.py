from dateutil.parser import parse
from io import StringIO

from beancount.ingest import importer
from beancount.core import data
from beancount.core import amount
from beancount.core.number import D
from beancount.ingest.importers.mixins import identifier

import csv

class Importer(identifier.IdentifyMixin, importer.ImporterProtocol):
    """An importer for Transferwise CSV files."""

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
            reader = csv.DictReader(csvfile)
            for row in reader:
                metakv = {
                    'ref': row['TransferWise ID'],
                }
                meta = data.new_metadata(file.name, 0, metakv)
                entry = data.Transaction(
                    meta,
                    parse(row['Date'], dayfirst=True).date(),
                    '*',
                    '',
                    row['Description'],
                    data.EMPTY_SET,
                    data.EMPTY_SET,
                    [
                        data.Posting(self.account, amount.Amount(D(row['Amount']), row['Currency']), None, None, None, None),
                    ]
                )
                entries.append(entry)
        return entries

