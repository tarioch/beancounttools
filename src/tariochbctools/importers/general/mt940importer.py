import re
from typing import Any

import beangulp
import mt940
from beancount.core import amount, data
from beancount.core.number import D

from tariochbctools.importers.general.deduplication import ReferenceDuplicatesComparator


class Importer(beangulp.Importer):
    """An importer for MT940 files."""

    def __init__(self, filepattern: str, account: data.Account):
        self._filepattern = filepattern
        self._account = account

    def identify(self, filepath: str) -> bool:
        return re.search(self._filepattern, filepath) is not None

    def account(self, filepath: str) -> data.Account:
        return self._account

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        entries = []
        transactions = mt940.parse(filepath)
        for trx in transactions:
            trxdata = trx.data
            ref = trxdata["bank_reference"]
            if ref:
                metakv = {"ref": ref}
            else:
                metakv = None
            meta = data.new_metadata(filepath, 0, metakv)
            if "entry_date" in trxdata:
                date = trxdata["entry_date"]
            else:
                date = trxdata["date"]
            entry = data.Transaction(
                meta,
                date,
                "*",
                self.prepare_payee(trxdata),
                self.prepare_narration(trxdata),
                data.EMPTY_SET,
                data.EMPTY_SET,
                [
                    data.Posting(
                        self._account,
                        amount.Amount(
                            D(trxdata["amount"].amount), trxdata["amount"].currency
                        ),
                        None,
                        None,
                        None,
                        None,
                    ),
                ],
            )
            entries.append(entry)

        return entries

    cmp = ReferenceDuplicatesComparator()

    def prepare_payee(self, trxdata: dict[str, Any]) -> str:
        return ""

    def prepare_narration(self, trxdata: dict[str, Any]) -> str:
        return trxdata["transaction_details"] + " " + trxdata["extra_details"]
