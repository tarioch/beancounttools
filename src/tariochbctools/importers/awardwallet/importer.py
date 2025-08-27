from os import path
from typing import Any

import beangulp
import dateutil.parser
import yaml
from awardwallet.api import AwardWalletAPI
from beancount.core import amount, data
from beancount.core.number import D


class Importer(beangulp.Importer):
    """An importer for AwardWallet"""

    def _configure(self, filepath: str, existing: data.Entries) -> None:
        with open(filepath, "r") as f:
            self.config = yaml.safe_load(f)
        self.api_key = self.config["api_key"]

    def identify(self, filepath: str) -> bool:
        return path.basename(filepath).endswith("awardwallet.yaml")

    def account(self, filepath: str) -> data.Account:
        return ""

    def extract(self, filepath: str, existing: data.Entries = None) -> data.Entries:
        self._configure(filepath, existing)
        client = AwardWalletAPI(self.api_key)
        entries = []

        for user_id, user in self.config["users"].items():
            user_details = client.get_connected_user_details(user_id)
            entries.extend(self._extract_account(user, user_details))

    def _extract_account(self, user: dict, user_details: dict) -> data.Account:
        entries = []
        for account in user_details["accounts"]:
            if account["accountId"] in user["accounts"]:
                account_config = user["accounts"][account["accountId"]]
                for trx in account["history"]:
                    local_account = account_config["account"]
                    currency = account_config["currency"]

                    entries.extend(
                        self._extract_transaction(trx, local_account, currency)
                    )
        return entries

    def _extract_transaction(
        self,
        trx: dict[str, Any],
        local_account: data.Account,
        currency: str,
    ) -> data.Transaction:
        entries = []
        trx_date = None
        trx_description = None
        trx_amount = None

        for f in trx.get("fields", []):
            if f["code"] == "PostingDate":
                trx_date = dateutil.parser.parse(f["value"]).date()
            if f["code"] == "Description":
                trx_description = f["value"]
            if f["code"] == "Miles":
                trx_amount = D(f["value"])

        entry = data.Transaction(
            {},
            trx_date,
            "*",
            "",
            trx_description,
            data.EMPTY_SET,
            data.EMPTY_SET,
            [
                data.Posting(
                    local_account,
                    amount.Amount(trx_amount, currency),
                    None,
                    None,
                    None,
                    None,
                ),
            ],
        )
        entries.append(entry)
        return entries
