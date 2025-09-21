import logging
from datetime import timedelta
from os import path
from typing import Any

import beangulp
import dateutil.parser
import requests
import yaml
from beancount.core import amount, data
from beancount.core.number import D

from tariochbctools.importers.general.deduplication import ReferenceDuplicatesComparator

# https://docs.truelayer.com/#retrieve-account-transactions

TX_MANDATORY_ID_FIELDS = ("transaction_id",)

TX_OPTIONAL_ID_FIELDS = (
    "normalised_provider_transaction_id",
    "provider_transaction_id",
)

TX_OPTIONAL_META_ID_FIELDS = (
    "provider_id",
    "provider_reference",
)


class Importer(beangulp.Importer):
    """An importer for Truelayer API (e.g. for Revolut)."""

    def __init__(self):
        self.config = None
        self.clientId = None
        self.clientSecret = None
        self.refreshToken = None
        self.sandbox = None
        self.existing = None
        self.domain = "truelayer.com"

    def _configure(self, filepath: str, existing: data.Entries) -> None:
        with open(filepath, "r") as f:
            self.config = yaml.safe_load(f)
        self.clientId = self.config["client_id"]
        self.clientSecret = self.config["client_secret"]
        self.refreshToken = self.config["refresh_token"]
        self.sandbox = self.clientId.startswith("sandbox")
        self.existing = existing

        if self.sandbox:
            self.domain = "truelayer-sandbox.com"

        if "account" not in self.config and "accounts" not in self.config:
            raise KeyError("At least one of `account` or `accounts` must be specified")

    def identify(self, filepath: str) -> bool:
        return path.basename(filepath).endswith("truelayer.yaml")

    def account(self, filepath: str) -> data.Account:
        return ""

    def extract(self, filepath: str, existing: data.Entries = None) -> data.Entries:
        self._configure(filepath, existing)

        r = requests.post(
            f"https://auth.{self.domain}/connect/token",
            data={
                "grant_type": "refresh_token",
                "client_id": self.clientId,
                "client_secret": self.clientSecret,
                "refresh_token": self.refreshToken,
            },
        )
        tokens = r.json()
        accessToken = tokens["access_token"]
        headers = {"Authorization": "Bearer " + accessToken}

        entries = []
        entries.extend(self._extract_endpoint_transactions("accounts", headers))
        entries.extend(
            self._extract_endpoint_transactions("cards", headers, invert_sign=True)
        )

        return entries

    def _get_account_for_account_id(self, account_id: str) -> data.Account:
        """
        Find a matching account for the account ID.
        If the user hasn't specified any in the config, return
        the base account.

        Otherwise return None.
        """
        if "accounts" not in self.config:
            return self.config["account"]

        # Empty `accounts` will generate warnings for all accounts
        #  including their account IDs
        if self.config["accounts"] is None:
            return None

        return self.config["accounts"].get(account_id, None)

    def _extract_endpoint_transactions(
        self, endpoint: str, headers: dict[str, str], invert_sign: bool = False
    ) -> data.Entries:
        entries = []
        r = requests.get(
            f"https://api.{self.domain}/data/v1/{endpoint}", headers=headers
        )

        if not r:
            try:
                r.raise_for_status()
            except requests.HTTPError as e:
                logging.warning(e)

            return []

        for account in r.json()["results"]:
            accountId = account["account_id"]

            local_account = self._get_account_for_account_id(accountId)

            if not local_account:
                logging.warning("Ignoring account ID %s", accountId)
                continue

            r = requests.get(
                f"https://api.{self.domain}/data/v1/{endpoint}/{accountId}/balance",
                headers=headers,
            )
            balances = r.json()["results"]

            for balance in balances:
                entries.extend(
                    self._extract_balance(balance, local_account, invert_sign)
                )

            r = requests.get(
                f"https://api.{self.domain}/data/v1/{endpoint}/{accountId}/transactions",
                headers=headers,
            )
            transactions = sorted(r.json()["results"], key=lambda trx: trx["timestamp"])

            for trx in transactions:
                entries.extend(
                    self._extract_transaction(
                        trx, local_account, transactions, invert_sign
                    )
                )

        return entries

    def _extract_transaction(
        self,
        trx: dict[str, Any],
        local_account: data.Account,
        transactions: list[Any],
        invert_sign: bool,
    ) -> data.Transaction:
        entries = []
        metakv: dict[str, Any] = {}

        id_meta_kvs = {
            k: trx["meta"][k] for k in TX_OPTIONAL_META_ID_FIELDS if trx["meta"].get(k)
        }
        metakv.update(id_meta_kvs)

        id_kvs = {
            k: trx[k]
            for k in TX_MANDATORY_ID_FIELDS + TX_OPTIONAL_ID_FIELDS
            if trx.get(k)
        }
        metakv.update(id_kvs)

        if trx["transaction_classification"]:
            metakv["category"] = trx["transaction_classification"][0]

        meta = data.new_metadata("", 0, metakv)
        trxDate = dateutil.parser.parse(trx["timestamp"]).date()

        tx_amount = D(str(trx["amount"]))
        # avoid pylint invalid-unary-operand-type
        signed_amount = -1 * tx_amount if invert_sign else tx_amount

        entry = data.Transaction(
            meta,
            trxDate,
            "*",
            "",
            trx["description"],
            data.EMPTY_SET,
            data.EMPTY_SET,
            [
                data.Posting(
                    local_account,
                    amount.Amount(signed_amount, trx["currency"]),
                    None,
                    None,
                    None,
                    None,
                ),
            ],
        )
        entries.append(entry)

        return entries

    def _extract_balance(
        self,
        result: dict[str, Any],
        local_account: data.Account,
        invert_sign: bool,
    ) -> data.Transaction:
        entries = []

        meta = data.new_metadata("", 0)

        balance = D(str(result["current"]))
        # avoid pylint invalid-unary-operand-type
        signed_balance = -1 * balance if invert_sign else balance
        balance_date = dateutil.parser.parse(result["update_timestamp"]).date()

        entries.append(
            data.Balance(
                meta,
                balance_date + timedelta(days=1),
                local_account,
                amount.Amount(signed_balance, result["currency"]),
                None,
                None,
            )
        )

        if "last_statement_balance" in result:
            statement_balance = D(str(result["last_statement_balance"]))
            signed_statement_balance = (
                -1 * statement_balance if invert_sign else statement_balance
            )
            statement_date = dateutil.parser.parse(result["last_statement_date"]).date()

            entries.append(
                data.Balance(
                    meta,
                    statement_date,
                    local_account,
                    amount.Amount(signed_statement_balance, result["currency"]),
                    None,
                    None,
                )
            )

        return entries

    cmp = ReferenceDuplicatesComparator(TX_MANDATORY_ID_FIELDS)
