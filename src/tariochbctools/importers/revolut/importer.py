from dateutil.parser import parse
from datetime import timedelta
from io import StringIO

from beancount.ingest import importer
from beancount.core import data
from beancount.core import amount
from beancount.core.number import D
from beancount.ingest.importers.mixins import identifier

import csv
import logging


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
        has_balance = False

        with StringIO(file.contents()) as csvfile:
            reader = csv.DictReader(csvfile, ['Date', 'Reference', 'PaidOut', 'PaidIn', 'ExchangeOut', 'ExchangeIn', 'Balance', 'Category'], delimiter=';', skipinitialspace=True)
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

                book_date = parse(row['Date'].strip()).date()

                try:
                    credit = D(row['PaidIn'].replace('\'', '').strip())
                    debit = D(row['PaidOut'].replace('\'', '').strip())
                    bal = D(row['Balance'].replace('\'', '').strip())
                    amt = amount.Amount(credit - debit, self.currency)
                    balance = amount.Amount(bal, self.currency)
                except Exception as e:
                    logging.warning(e)
                    continue

                meta = data.new_metadata(file.name, 0, metakv)
                entry = data.Transaction(
                    meta,
                    book_date,
                    '*',
                    '',
                    row['Reference'].strip(),
                    data.EMPTY_SET,
                    data.EMPTY_SET,
                    [
                        data.Posting(self.account, amt, None, None, None, None),
                    ]
                )
                entries.append(entry)

                # only add balance after the top (newest) transaction
                if not has_balance:
                    book_date = book_date + timedelta(days=1)
                    entry = data.Balance(meta, book_date, self.account, balance, None, None)
                    entries.append(entry)
                    has_balance = True

        return entries
