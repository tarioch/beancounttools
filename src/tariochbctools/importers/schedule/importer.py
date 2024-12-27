import datetime
from os import path
from typing import Any

import beangulp
import yaml
from beancount.core import amount, data
from beancount.core.number import D
from dateutil.relativedelta import relativedelta


class Importer(beangulp.Importer):
    """An importer for Scheduled/Recurring Transactions."""

    def identify(self, filepath: str) -> bool:
        return path.basename(filepath).endswith("schedule.yaml")

    def account(self, filepath: str) -> data.Account:
        return ""

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        with open(filepath, "r") as f:
            config = yaml.safe_load(f)
        self.transactions = config["transactions"]

        result = []
        for trx in config["transactions"]:
            for i in reversed(range(1, 6)):
                date = datetime.date.today() + relativedelta(months=-i, day=31)
                result.append(self.createForDate(trx, date))

        return result

    def createForDate(
        self, trx: dict[str, Any], date: datetime.date
    ) -> data.Transaction:
        postings = []
        for post in trx["postings"]:
            amt = None
            if "amount" in post and "currency" in post:
                amt = amount.Amount(D(post["amount"]), post["currency"])

            postings.append(data.Posting(post["account"], amt, None, None, None, None))
        meta = data.new_metadata("schedule", 0)
        return data.Transaction(
            meta,
            date,
            "*",
            "",
            trx["narration"],
            data.EMPTY_SET,
            data.EMPTY_SET,
            postings,
        )
