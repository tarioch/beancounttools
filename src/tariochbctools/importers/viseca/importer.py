import re
from datetime import datetime

import camelot
from beancount.core import amount, data
from beancount.core.number import D
from beancount.ingest import importer
from beancount.ingest.importers.mixins import identifier


class Importer(identifier.IdentifyMixin, importer.ImporterProtocol):
    """An importer for Viseca One Card Statement PDF files."""

    def __init__(self, regexps, account):
        identifier.IdentifyMixin.__init__(self, matchers=[("filename", regexps)])
        self.account = account
        self.currency = "CHF"

    def file_account(self, file):
        return self.account

    def createEntry(self, file, date, amt, text):
        meta = data.new_metadata(file.name, 0)
        return data.Transaction(
            meta,
            date,
            "*",
            "",
            text,
            data.EMPTY_SET,
            data.EMPTY_SET,
            [
                data.Posting(self.account, amt, None, None, None, None),
            ],
        )

    def extract(self, file, existing_entries):
        entries = []

        p = re.compile(
            r"^(?P<bookingDate>\d\d\.\d\d\.\d\d) (?P<valueDate>\d\d\.\d\d\.\d\d) (?P<detail>.*)$"
        )

        tables = camelot.read_pdf(
            file.name, flavor="stream", table_areas=["65,450,575,100"]
        )
        for table in tables:
            df = table.df

            # skip incompatible tables
            if df.columns.size != 4:
                continue

            lastTrxDate = None
            lastAmount = None
            lastDetails = ""
            for _, row in df.iterrows():
                dateValutaDetails, currency, amountCcy, amountChf = tuple(row)

                if (
                    "XX XXXX" in dateValutaDetails
                    or "Kartenlimite" in dateValutaDetails
                ):
                    continue

                trxDate = None
                detail = ""
                m = p.match(dateValutaDetails)
                if m:
                    trxDate = m.group("valueDate")
                    detail = m.group("detail").strip() + " "
                else:
                    detail = dateValutaDetails.strip() + " "

                if amountChf:
                    if lastTrxDate:
                        amt = None
                        if "-" in lastAmount:
                            amt = -amount.Amount(D(lastAmount.strip(" -")), "CHF")
                        else:
                            amt = amount.Amount(D(lastAmount), "CHF")

                        book_date = datetime.strptime(lastTrxDate, "%d.%m.%y").date()

                        entries.append(
                            self.createEntry(file, book_date, amt, lastDetails.strip())
                        )

                    lastTrxDate = trxDate
                    lastAmount = amountChf
                    lastDetails = ""

                lastDetails += detail + " "

        return entries
