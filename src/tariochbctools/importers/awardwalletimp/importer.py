import logging
from os import path
from typing import Any

import beangulp
import dateutil.parser
import yaml
from awardwallet import AwardWalletClient
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
        client = AwardWalletClient(self.api_key)
        entries = []

        for user_id, user in self.config["users"].items():
            user_details = client.get_connected_user_details(user_id)

            if user.get("accounts"):
                if user.get("all_history", False):
                    entries.extend(self._extract_account_history(user, client))
                else:
                    entries.extend(self._extract_user_history(user, user_details))
            else:
                logging.warning(
                    "Ignoring user ID %s: no accounts configured",
                    user_id,
                )

        return entries

    def _extract_user_history(
        self, user: dict, user_details: dict
    ) -> list[data.Transaction]:
        """
        User history is limited to the last 10 history elements per account
        """
        entries = []
        for account in user_details["accounts"]:
            account_id = account["accountId"]

            if account_id in user["accounts"]:
                logging.info("Extracting account ID %s", account_id)
                account_config = user["accounts"][account_id]

                entries.extend(
                    self._extract_transactions(
                        account["history"], account_config, account_id
                    )
                )
            else:
                logging.warning(
                    "Ignoring account ID %s: %s", account_id, account["displayName"]
                )
        return entries

    def _extract_account_history(
        self, user: dict, client: AwardWalletClient
    ) -> list[data.Transaction]:
        entries = []
        for account_id, account_config in user["accounts"].items():
            logging.info("Extracting account ID %s", account_id)
            account = client.get_account_details(account_id)["account"]

            entries.extend(
                self._extract_transactions(
                    account["history"], account_config, account_id
                )
            )
        return entries

    def _extract_transactions(
        self,
        history: list,
        account_config: dict,
        account_id: str,
    ) -> list[data.Transaction]:
        local_account = account_config["account"]
        currency = account_config["currency"]

        logging.debug(
            "Extracting %i transactions for account %s",
            len(history),
            account_id,
        )

        entries = []
        for trx in history:
            entries.extend(
                self._extract_transaction(trx, local_account, currency, account_id)
            )
        return entries

    def _extract_transaction(
        self,
        trx: dict[str, Any],
        local_account: data.Account,
        currency: str,
        account_id: str,
    ) -> list[data.Transaction]:
        entries = []
        metakv = {"account-id": str(account_id)}

        trx_date = None
        trx_description = None
        trx_amount = None

        for f in trx.get("fields", []):
            if f["code"] == "PostingDate":
                trx_date = dateutil.parser.parse(f["value"]["value"]).date()
            if f["code"] == "Description":
                trx_description = f["value"]["value"].replace("\n", " ")
            if f["code"] == "Miles":
                trx_amount = D(f["value"]["value"])
            if f["code"] == "Info":
                name = f["name"].lower().replace(" ", "-")
                metakv[name] = f["value"]["value"].replace("\n", " ")

        assert trx_date
        assert trx_description
        assert trx_amount is not None, f"No amount in trx: {trx}"

        meta = data.new_metadata("", 0, metakv)
        entry = data.Transaction(
            meta,
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
