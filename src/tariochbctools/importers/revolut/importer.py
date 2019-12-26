from dateutil.parser import parse
from io import StringIO

from beancount.ingest import importer
from beancount.core import data
from beancount.core import amount
from beancount.core.number import D
from beancount.ingest.importers.mixins import identifier

import csv


class Importer(identifier.IdentifyMixin, importer.ImporterProtocol):
    """An importer for Revolut CSV files."""

    def __init__(self, regexps, account, currency):
        identifier.IdentifyMixin.__init__(self, matchers=[
            ('filename', regexps)
        ])
        self.account = account
        self.currency = currency

    def name(self):
        return super().name() + self.account

    def file_account(self, file):
        return self.account

    def extract(self, file, existing_entries):
        entries = []

        with StringIO(file.contents()) as csvfile:
            reader = csv.DictReader(csvfile, ['Date', 'Reference', 'PaidOut', 'PaidIn', 'ExchangeOut', 'ExchangeIn', 'Balance', 'Category', 'Notes'], delimiter=';', skipinitialspace=True)
            next(reader)
            for row in reader:
                metakv = {
                    'category': row['Category'].strip(),
                }
                exchangeIn = row['ExchangeIn'].strip()
                exchangeOut = row['ExchangeOut'].strip()
                if exchangeIn and exchangeOut:
                    metakv['originalIn'] = exchangeIn
                    metakv['originalOut'] = exchangeOut
                elif exchangeIn:
                    metakv['original'] = exchangeIn
                elif exchangeOut:
                    metakv['original'] = exchangeOut

                meta = data.new_metadata(file.name, 0, metakv)
                entry = data.Transaction(
                    meta,
                    parse(row['Date'].strip()).date(),
                    '*',
                    '',
                    (row['Reference'].strip() + ' ' + row['Notes'].strip()).strip(),
                    data.EMPTY_SET,
                    data.EMPTY_SET,
                    [
                        data.Posting(self.account, amount.Amount(D(row['PaidIn'].strip()) - D(row['PaidOut'].strip()), self.currency), None, None, None, None),
                    ]
                )
                entries.append(entry)
        return entries
