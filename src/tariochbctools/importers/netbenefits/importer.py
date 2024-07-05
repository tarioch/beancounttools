import csv
from collections.abc import Iterable
from datetime import date
from io import StringIO

from beancount.core import amount, data
from beancount.core.number import D
from beancount.core.position import CostSpec
from beancount.ingest import importer
from beancount.ingest.importers.mixins import identifier
from dateutil.parser import parse

from tariochbctools.importers.general.priceLookup import PriceLookup


class Importer(identifier.IdentifyMixin, importer.ImporterProtocol):
    """An importer for Fidelity Netbenefits Activity CSV files."""

    def __init__(
        self,
        regexps: str | Iterable[str],
        cashAccount: str,
        investmentAccount: str,
        dividendAccount: str,
        taxAccount: str,
        capGainAccount: str,
        symbol: str,
        ignoreTypes: Iterable[str],
        baseCcy: str,
    ):
        identifier.IdentifyMixin.__init__(self, matchers=[("filename", regexps)])
        self.cashAccount = cashAccount
        self.investmentAccount = investmentAccount
        self.dividendAccount = dividendAccount
        self.taxAccount = taxAccount
        self.capGainAccount = capGainAccount
        self.symbol = symbol
        self.ignoreTypes = ignoreTypes
        self.baseCcy = baseCcy

    def name(self):
        return super().name() + self.cashAccount

    def file_account(self, file):
        return self.cashAccount

    def extract(self, file, existing_entries):
        entries = []

        self.priceLookup = PriceLookup(existing_entries, self.baseCcy)

        with StringIO(file.contents()) as csvfile:
            reader = csv.DictReader(
                csvfile,
                [
                    "Transaction date",
                    "Transaction type",
                    "Investment name",
                    "Shares",
                    "Amount",
                ],
                delimiter=",",
                skipinitialspace=True,
            )
            next(reader)
            for row in reader:
                if not row["Transaction type"]:
                    break

                if row["Transaction type"] in self.ignoreTypes:
                    continue

                book_date = parse(row["Transaction date"].strip()).date()
                amt = amount.Amount(D(row["Amount"].replace("$", "")), "USD")
                shares = None
                if row["Shares"] != "-":
                    shares = amount.Amount(D(row["Shares"]), self.symbol)

                metakv = {}

                if not amt and not shares:
                    continue

                meta = data.new_metadata(file.name, 0, metakv)
                description = row["Transaction type"].strip()

                if "TAX" in description:
                    postings = self.__createDividend(amt, book_date, self.taxAccount)
                elif "DIVIDEND" in description:
                    postings = self.__createDividend(
                        amt, book_date, self.dividendAccount
                    )
                elif "YOU BOUGHT" in description:
                    postings = self.__createBuy(amt, shares, book_date)
                elif "YOU SOLD" in description:
                    postings = self.__createSell(amt, shares, book_date)
                else:
                    postings = [
                        data.Posting(self.cashAccount, amt, None, None, None, None),
                    ]

                    if shares is not None:
                        postings.append(
                            data.Posting(
                                self.investmentAccount, shares, None, None, None, None
                            ),
                        )

                entry = data.Transaction(
                    meta,
                    book_date,
                    "*",
                    "",
                    description,
                    data.EMPTY_SET,
                    data.EMPTY_SET,
                    postings,
                )
                entries.append(entry)

        return entries

    def __createBuy(self, amt: amount, shares: amount, book_date: date):
        price = self.priceLookup.fetchPrice("USD", book_date)
        cost = CostSpec(
            number_per=None,
            number_total=round(-amt.number * price.number, 2),
            currency=self.baseCcy,
            date=None,
            label=None,
            merge=None,
        )
        postings = [
            data.Posting(self.investmentAccount, shares, cost, None, None, None),
            data.Posting(self.cashAccount, amt, None, price, None, None),
        ]

        return postings

    def __createSell(self, amt: amount, shares: amount, book_date: date):
        price = self.priceLookup.fetchPrice("USD", book_date)
        cost = CostSpec(
            number_per=None,
            number_total=None,
            currency=None,
            date=None,
            label=None,
            merge=None,
        )
        postings = [
            data.Posting(self.investmentAccount, shares, cost, None, None, None),
            data.Posting(self.cashAccount, amt, None, price, None, None),
            data.Posting(self.capGainAccount, None, None, None, None, None),
        ]

        return postings

    def __createDividend(self, amt: amount, book_date: date, incomeAccount: str):
        price = self.priceLookup.fetchPrice("USD", book_date)
        postings = [
            data.Posting(
                self.investmentAccount,
                amount.Amount(D(0), self.symbol),
                None,
                None,
                None,
                None,
            ),
            data.Posting(self.cashAccount, amt, None, price, None, None),
            data.Posting(incomeAccount, None, None, None, None, None),
        ]

        return postings
