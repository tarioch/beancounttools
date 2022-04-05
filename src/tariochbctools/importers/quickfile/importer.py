from datetime import datetime
from os import path
from typing import NamedTuple

import yaml
from beancount.core import amount, data
from beancount.core.number import D
from beancount.ingest import importer
from undictify import type_checked_constructor

# https://api.quickfile.co.uk/method/bank


@type_checked_constructor(skip=True, convert=True)
class QuickFileTransaction(NamedTuple):
    """Transaction data from QuickFile transaction API"""

    TransactionDate: str
    Reference: str
    Amount: float
    TagStatus: str
    TransactionId: int

    def to_beancount_transaction(self, local_account, currency, invert_sign=False):
        tx_amount = D(self.Amount)
        # avoid pylint invalid-unary-operand-type
        signed_amount = -1 * tx_amount if invert_sign else tx_amount

        metakv = {
            "quickfile_id": self.TransactionId,
        }

        meta = data.new_metadata("", 0, metakv)
        date = datetime.fromisoformat(self.TransactionDate)

        entry = data.Transaction(
            meta,
            date,
            "*",
            "",
            self.Reference,
            data.EMPTY_SET,
            data.EMPTY_SET,
            [
                data.Posting(
                    local_account,
                    amount.Amount(signed_amount, currency),
                    None,
                    None,
                    None,
                    None,
                ),
            ],
        )
        return entry


class Importer(importer.ImporterProtocol):
    """An importer for QuickFile"""

    def __init__(self):
        self.config = None
        self.existing_entries = None

    def _configure(self, file, existing_entries):
        with open(file.name, "r") as config_file:
            self.config = yaml.safe_load(config_file)
        self.existing_entries = existing_entries

    def identify(self, file):
        return path.basename(file.name) == "quickfile.yaml"

    def file_account(self, file):
        return ""

    def extract(self, file, existing_entries=None):
        self._configure(file, existing_entries)
        headers = {}
        entries = []
        entries.extend(self._extract_bank_transactions("account_one", headers))
        return entries

    def _extract_bank_transactions(self, bank_account, headers, invert_sign=False):
        entries = []
        response = {}
        transactions = response

        for trx in response:
            entries.extend(
                self._extract_transaction(trx, bank_account, transactions, invert_sign)
            )

        return entries

    def _extract_transaction(self, trx, local_account, transactions, invert_sign):
        entries = []
        currency = ""  # TODO: extract from metadata

        t = QuickFileTransaction(**trx)
        entry = t.to_beancount_transaction(local_account, currency, invert_sign)
        entries.append(entry)

        return entries
