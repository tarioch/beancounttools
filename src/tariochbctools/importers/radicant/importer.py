import re
from datetime import datetime, timedelta

import beangulp
import camelot
from beancount.core import amount, data
from beancount.core.number import D


class Importer(beangulp.Importer):
    """An importer for radicant Account Statement PDF files."""

    def __init__(self, filepattern: str, account: data.Account):
        self._filepattern = filepattern
        self._account = account
        self.currency = "CHF"

    def identify(self, filepath: str) -> bool:
        return re.search(self._filepattern, filepath) is not None

    def account(self, filepath: str) -> data.Account:
        return self._account

    def cleanAmount(
        self, debit: str | None, credit: str | None
    ) -> amount.Amount | None:
        if debit:
            return -amount.Amount(D(debit.replace("'", "")), self.currency)
        elif credit:
            return amount.Amount(D(credit.replace("'", "")), self.currency)
        else:
            return None

    def createEntry(
        self,
        filepath: str,
        date: str,
        amt: amount.Amount,
        text: str,
        conversionOriginal: str | None,
        conversionRate: str | None,
    ) -> data.Transaction:

        book_date = datetime.strptime(date, "%d.%m.%y").date()

        if conversionOriginal and conversionRate:
            kv = {"original": conversionOriginal, "rate": conversionRate}
            text = text.replace("Amount: " + conversionOriginal, "")
            # handle decimal seperated original amounts
            [originalCcy, originalAmt] = conversionOriginal.split(" ")
            text = text.replace(
                "Amount: " + f"{originalCcy} {float(originalAmt):,}", ""
            )
        else:
            kv = None

        meta = data.new_metadata(filepath, 0, kv)
        return data.Transaction(
            meta,
            book_date,
            "*",
            "",
            text.strip(),
            data.EMPTY_SET,
            data.EMPTY_SET,
            [
                data.Posting(self._account, amt, None, None, None, None),
            ],
        )

    def createBalance(
        self,
        filepath: str,
        date: str,
        amt: amount.Amount,
    ) -> data.Balance:
        meta = data.new_metadata(filepath, 0, None)
        return data.Balance(
            meta,
            datetime.strptime(date, "%d.%m.%Y").date() + timedelta(days=1),
            self._account,
            amt,
            None,
            None,
        )

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        entries = []

        conversionPattern = re.compile(r"(?P<original>.+) at the rate of (?P<rate>.+)")
        balancePattern = re.compile(r"Balance as of (?P<date>\d\d\.\d\d\.\d\d\d\d)")

        tables = camelot.read_pdf(
            filepath,
            flavor="stream",
            pages="all",
            table_regions=["40,600,580,32"],
            columns=["110,305,370,440,500"],
            strip_text="\n",
            layout_kwargs={"word_margin": 0.50},
            split_text=True,
        )

        for table in tables:
            df = table.df

            lastTrxDate = None
            lastAmount = None
            lastDetails = ""
            beforeStart = True
            conversionOriginal = None
            conversionRate = None
            for _, row in df.iterrows():
                date, text, _, debit, credit, bal = tuple(row)

                # skip stuff before
                if beforeStart and "Date" != date:
                    continue
                elif "Date" == date:
                    beforeStart = False
                    continue

                # create balance and skip stuff after
                balanceMatch = balancePattern.match(text)
                if balanceMatch:
                    entries.append(
                        self.createBalance(
                            filepath,
                            balanceMatch.group("date"),
                            amount.Amount(D(bal.replace("'", "")), self.currency),
                        )
                    )
                    break

                trxDate = date
                details = text.strip()
                amt = self.cleanAmount(debit, credit)

                if amt:
                    if lastTrxDate:
                        entries.append(
                            self.createEntry(
                                filepath,
                                lastTrxDate,
                                lastAmount,
                                lastDetails,
                                conversionOriginal,
                                conversionRate,
                            )
                        )

                    lastTrxDate = trxDate
                    lastAmount = amt
                    lastDetails = ""
                    conversionOriginal = None
                    conversionRate = None

                match = conversionPattern.match(details)
                if match:
                    conversionOriginal = match.group("original")
                    conversionRate = match.group("rate")
                else:
                    lastDetails += details + " "

            if lastTrxDate:
                entries.append(
                    self.createEntry(
                        filepath,
                        lastTrxDate,
                        lastAmount,
                        lastDetails,
                        conversionOriginal,
                        conversionRate,
                    )
                )

        return entries
