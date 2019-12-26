from dateutil.parser import parse

from beancount.ingest import importer
from beancount.core import data
from beancount.core import amount
from beancount.core.number import D
from beancount.ingest.importers.mixins import identifier

import tabula
import pandas as pd
import re


class Importer(identifier.IdentifyMixin, importer.ImporterProtocol):
    """An importer for Bank Cler ZAK PDF files files."""

    def __init__(self, regexps, account, currency):
        identifier.IdentifyMixin.__init__(self, matchers=[
            ('filename', regexps)
        ])
        self.account = account
        self.currency = currency

    def file_account(self, file):
        return self.account

    def createEntry(self, file, date, amt, text):
        meta = data.new_metadata(file.name, 0)
        return data.Transaction(
            meta,
            parse(date.strip(), dayfirst=True).date(),
            '*',
            '',
            text.strip(),
            data.EMPTY_SET,
            data.EMPTY_SET,
            [
                data.Posting(self.account, amount.Amount(D(amt), self.currency), None, None, None, None),
            ]
        )

    def createBalanceEntry(self, file, date, amt):
        meta = data.new_metadata(file.name, 0)
        return data.Balance(
            meta,
            parse(date.strip(), dayfirst=True).date(),
            self.account,
            amount.Amount(D(amt), self.currency),
            None,
            None,
        )

    def cleanNumber(self, number):
        if isinstance(number, str):
            return D(number.replace('\'', ''))
        else:
            return number

    def extract(self, file, existing_entries):
        entries = []

        dfFirst = tabula.read_pdf(file.name, pages=1, area=[340, 70, 700, 565], guess=False)
        dfRest = tabula.read_pdf(file.name, pages=2, area=[185, 70, 610, 565], guess=False)
        df = pd.concat([dfFirst, dfRest])

        date = None
        text = ''
        amount = None
        saldo = None

        for row in df.itertuples():
            if row.Saldo == row.Saldo:
                if date and amount:
                    entries.append(self.createEntry(file, date, amount, text))

                date = None
                amount = None
                text = ''

            if row.Datum == row.Datum:
                date = row.Datum

            if row.Text == row.Text:
                text += ' ' + row.Text

            if row.Belastung == row.Belastung:
                amount = -self.cleanNumber(row.Belastung)

            if row.Gutschrift == row.Gutschrift:
                amount = self.cleanNumber(row.Gutschrift)

            if row.Saldo == row.Saldo:
                saldo = self.cleanNumber(row.Saldo)

        if date and amount:
            entries.append(self.createEntry(file, date, amount, text))

        p = re.compile(r'\d\d.\d\d.\d\d\d\d')
        m = p.search(text)
        date = m.group()
        entries.append(self.createBalanceEntry(file, date, saldo))

        return entries
