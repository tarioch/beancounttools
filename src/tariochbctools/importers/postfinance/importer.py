import csv
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from beancount.core import data
from beancount.ingest.importers.mixins.identifier import IdentifyMixin
from beancount.ingest.importer import ImporterProtocol


class Importer(IdentifyMixin, ImporterProtocol):
    """An importer for PostFinance CSV."""

    def __init__(self, regexps, account, currency='CHF'):
        IdentifyMixin.__init__(self, matchers=[
            ('filename', regexps)
        ])
        self.account = account
        self.currency = currency

    def file_account(self, file):
        return self.account

    def extract(self, file, existing_entries):
        csvfile = open(file=file.name, encoding='windows_1252')
        reader = csv.reader(csvfile, delimiter=';')
        meta = data.new_metadata(file.name, 0)
        entries = []

        for row in reader:

            try:
                book_date, text, credit, debit, val_date, balance = tuple(row)
                book_date = datetime.strptime(book_date, '%Y-%m-%d').date()
                if credit:
                    amount = data.Amount(Decimal(credit), self.currency)
                elif debit:
                    amount = data.Amount(Decimal(debit), self.currency)
                else:
                    amount = None
                if balance:
                    balance = data.Amount(Decimal(balance), self.currency)
                else:
                    balance = None
            except Exception as e:
                logging.debug(e)
            else:
                logging.debug((book_date, text, amount, val_date, balance))
                posting = data.Posting(self.account, amount, None, None, None, None)
                entry = data.Transaction(meta, book_date, '*', '', text, data.EMPTY_SET, data.EMPTY_SET, [posting])
                entries.append(entry)
                # only add balance on SOM
                book_date = book_date + timedelta(days=1)
                if balance and book_date.day == 1:
                    entry = data.Balance(meta, book_date, self.account, balance, None, None)
                    entries.append(entry)

        csvfile.close()
        entries = data.sorted(entries)
        return entries
