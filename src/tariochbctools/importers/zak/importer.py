import re
from datetime import timedelta

import beangulp
import camelot
import pandas as pd
from beancount.core import amount, data
from beancount.core.number import D
from dateutil.parser import parse

from tariochbctools.importers.general.deduplication import ReferenceDuplicatesComparator


class Importer(beangulp.Importer):
    """An importer for Bank Cler ZAK PDF files files."""

    def __init__(self, filepattern: str, account: data.Account):
        self._filepattern = filepattern
        self._account = account

    def account(self, filepath: str) -> data.Account:
        return self._account

    def identify(self, filepath: str) -> bool:
        return re.search(self._filepattern, filepath) is not None

    def createEntry(
        self, filepath: str, date: str, amt: str, text: str
    ) -> data.Transaction:
        bookingNrRgexp = re.compile(r"BC Buchungsnr. (?P<bookingRef>\d+)$")
        m = bookingNrRgexp.search(text)
        if m:
            bookingRef = m.group("bookingRef")
            text = re.sub(bookingNrRgexp, "", text)

        meta = data.new_metadata(filepath, 0, {"zakref": bookingRef})
        return data.Transaction(
            meta,
            parse(date.strip(), dayfirst=True).date(),
            "*",
            "",
            text.strip(),
            data.EMPTY_SET,
            data.EMPTY_SET,
            [
                data.Posting(
                    self._account, amount.Amount(D(amt), "CHF"), None, None, None, None
                ),
            ],
        )

    def createBalanceEntry(self, filepath: str, date: str, amt: str) -> data.Balance:
        meta = data.new_metadata(filepath, 0)
        return data.Balance(
            meta,
            parse(date.strip(), dayfirst=True).date() + timedelta(days=1),
            self._account,
            amount.Amount(D(amt), "CHF"),
            None,
            None,
        )

    def cleanNumber(self, number: str | data.Decimal) -> data.Decimal:
        if isinstance(number, str):
            return D(number.replace("'", ""))
        else:
            return number

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        entries = []

        firstPageTables = camelot.read_pdf(
            filepath, flavor="stream", pages="1", table_regions=["60,450,600,170"]
        )
        otherPageTables = camelot.read_pdf(
            filepath, flavor="stream", pages="2-end", table_regions=["60,630,600,170"]
        )

        tables = [*firstPageTables, *otherPageTables]

        df: pd.DataFrame | None = None
        for table in tables:
            cur_df = table.df
            new_header = cur_df.iloc[0]
            cur_df = cur_df[1:]
            cur_df.columns = new_header

            if df is None:
                df = cur_df
            else:
                df = pd.concat([df, cur_df])

        date = None
        text = ""
        amount = None
        saldo = None
        if df:
            for row in df.itertuples():
                if row.Saldo:
                    if date and amount:
                        entries.append(self.createEntry(filepath, date, amount, text))

                    date = None
                    amount = None
                    text = ""

                if row.Valuta:
                    date = row.Valuta

                if row.Text:
                    text += " " + row.Text

                if row.Belastung:
                    amount = -self.cleanNumber(row.Belastung)

                if row.Gutschrift:
                    amount = self.cleanNumber(row.Gutschrift)

                if row.Saldo:
                    saldo = self.cleanNumber(row.Saldo)

            if date and amount:
                entries.append(self.createEntry(filepath, date, amount, text))

            dateRegexp = re.compile(r"\d\d\.\d\d\.\d\d\d\d")
            m = dateRegexp.search(text)
            if m and saldo:
                date = m.group()
                entries.append(self.createBalanceEntry(filepath, date, saldo))

        return entries

    cmp = ReferenceDuplicatesComparator(["zakref"])
