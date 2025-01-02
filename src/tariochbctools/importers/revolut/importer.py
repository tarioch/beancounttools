import csv
import logging
import re
from datetime import timedelta
from typing import Any

import beangulp
from beancount.core import amount, data
from beancount.core.number import ZERO, D
from dateutil.parser import parse


class Importer(beangulp.Importer):
    """An importer for Revolut CSV files."""

    def __init__(
        self, filepattern: str, account: data.Account, currency: str, fee: Any = None
    ):
        self._filepattern = filepattern
        self._account = account
        self.currency = currency
        self._fee = fee

    def name(self) -> str:
        return super().name() + self._account

    def identify(self, filepath: str) -> bool:
        return re.search(self._filepattern, filepath) is not None

    def account(self, filepath: str) -> data.Account:
        return self._account

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        entries = []

        with open(filepath) as csvfile:
            reader = csv.DictReader(
                csvfile,
                [
                    "Type",
                    "Product",
                    "Started Date",
                    "Completed Date",
                    "Description",
                    "Amount",
                    "Fee",
                    "Currency",
                    "State",
                    "Balance",
                ],
                delimiter=",",
                skipinitialspace=True,
            )
            next(reader)
            is_fee_mode = self._fee is not None
            for row in reader:
                try:
                    bal = D(row["Balance"].replace("'", "").strip())
                    amount_raw = D(row["Amount"].replace("'", "").strip())
                    amt = amount.Amount(amount_raw, row["Currency"])
                    balance = amount.Amount(bal, self.currency)
                    book_date = parse(row["Completed Date"].strip()).date()
                    fee_amt_raw = D(row["Fee"].replace("'", "").strip())
                    fee = amount.Amount(-fee_amt_raw, row["Currency"])
                except Exception as e:
                    logging.warning(e)
                    continue

                if is_fee_mode and fee_amt_raw == ZERO:
                    continue

                postings = [
                    data.Posting(self._account, amt, None, None, None, None),
                ]
                description = row["Description"].strip()
                if is_fee_mode:
                    postings = [
                        data.Posting(self._account, fee, None, None, None, None),
                        data.Posting(
                            self._fee["account"], -fee, None, None, None, None
                        ),
                    ]
                    description = f"Fees for {description}"

                assert isinstance(
                    description, str
                ), "Actual type of description is " + str(type(description))

                entry = data.Transaction(
                    data.new_metadata(filepath, 0, {}),
                    book_date,
                    "*",
                    "",
                    description,
                    data.EMPTY_SET,
                    data.EMPTY_SET,
                    postings,
                )
                entries.append(entry)

            if not is_fee_mode:
                # only add balance after the last (newest) transaction
                try:
                    book_date = book_date + timedelta(days=1)
                    entry = data.Balance(
                        data.new_metadata(filepath, 0, {}),
                        book_date,
                        self._account,
                        balance,
                        None,
                        None,
                    )
                    entries.append(entry)
                except NameError:
                    pass

        return entries
