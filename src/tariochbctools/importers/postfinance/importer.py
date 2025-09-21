import csv
import logging
import re
from datetime import timedelta
from decimal import Decimal

import beangulp
import dateutil.parser
from beancount.core import data


class Importer(beangulp.Importer):
    """An importer for PostFinance CSV."""

    def __init__(self, filepattern: str, account: data.Account, currency: str = "CHF"):
        self._filepattern = filepattern
        self._account = account
        self.currency = currency

    def identify(self, filepath: str) -> bool:
        return re.search(self._filepattern, filepath) is not None

    def account(self, filepath: str) -> data.Account:
        return self._account

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        csvfile = open(file=filepath, encoding="windows_1252")
        reader = csv.reader(csvfile, delimiter=";")
        meta = data.new_metadata(filepath, 0)
        entries = []

        for row in reader:
            try:
                book_date_str, text, credit, debit, val_date, balance_str = tuple(row)
                book_date = dateutil.parser.parse(book_date_str).date()
                if credit:
                    amount = data.Amount(Decimal(credit), self.currency)
                elif debit:
                    amount = data.Amount(Decimal(debit), self.currency)
                else:
                    amount = None
                if balance_str:
                    balance = data.Amount(Decimal(balance_str), self.currency)
                else:
                    balance = None
            except Exception as e:
                logging.debug(e)
            else:
                logging.debug((book_date, text, amount, val_date, balance))
                posting = data.Posting(self._account, amount, None, None, None, None)
                entry = data.Transaction(
                    meta,
                    book_date,
                    "*",
                    "",
                    text,
                    data.EMPTY_SET,
                    data.EMPTY_SET,
                    [posting],
                )
                entries.append(entry)
                # only add balance on SOM
                book_date = book_date + timedelta(days=1)
                if balance and book_date.day == 1:
                    entry = data.Balance(
                        meta, book_date, self._account, balance, None, None
                    )
                    entries.append(entry)

        csvfile.close()
        entries = data.sorted(entries)
        return entries
