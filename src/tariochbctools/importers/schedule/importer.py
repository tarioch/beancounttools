import datetime
from os import path

import yaml
from beancount.core import amount, data
from beancount.core.number import D
from beancount.ingest import importer
from dateutil.relativedelta import relativedelta


class Importer(importer.ImporterProtocol):
    """An importer for Scheduled/Recurring Transactions."""

    def identify(self, file):
        return "schedule.yaml" == path.basename(file.name)

    def file_account(self, file):
        return ""

    def extract(self, file, existing_entries):
        with open(file.name, "r") as f:
            config = yaml.safe_load(f)
        self.transactions = config["transactions"]

        result = []
        for trx in config["transactions"]:
            for i in reversed(range(1, 6)):
                date = datetime.date.today() + relativedelta(months=-i, day=31)
                result.append(self.createForDate(trx, date))

        return result

    def createForDate(self, trx, date):
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
