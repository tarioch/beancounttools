import logging
from datetime import timedelta
from os import path

import dateutil.parser
import requests
import yaml
from beancount.core import amount, data
from beancount.core.number import D
from beancount.ingest import importer

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


class Importer(importer.ImporterProtocol):
    """An importer for Truelayer API (e.g. for Revolut)."""

    def __init__(self):
        self.config = None
        self.clientId = None
        self.clientSecret = None
        self.refreshToken = None
        self.sandbox = None
        self.existing_entries = None
        self.domain = "truelayer.com"

    def _configure(self, file, existing_entries):
        with open(file.name, "r") as f:
            self.config = yaml.safe_load(f)
        self.clientId = self.config["client_id"]
        self.clientSecret = self.config["client_secret"]
        self.refreshToken = self.config["refresh_token"]
        self.sandbox = self.clientId.startswith("sandbox")
        self.existing_entries = existing_entries

        if self.sandbox:
            self.domain = "truelayer-sandbox.com"

        if "account" not in self.config and "accounts" not in self.config:
            raise KeyError("At least one of `account` or `accounts` must be specified")

    def identify(self, file):
        return "truelayer.yaml" == path.basename(file.name)

    def file_account(self, file):
        return ""

    def extract(self, file, existing_entries=None):
        self._configure(file, existing_entries)

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

    def _get_account_for_account_id(self, account_id):
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

    def _extract_endpoint_transactions(self, endpoint, headers, invert_sign=False):
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

    def _extract_transaction(self, trx, local_account, transactions, invert_sign):
        entries = []
        metakv = {}

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

        if trx["transaction_id"] == transactions[-1]["transaction_id"]:
            balDate = trxDate + timedelta(days=1)
            metakv = {}
            if self.existing_entries is not None:
                for exEntry in self.existing_entries:
                    if (
                        isinstance(exEntry, data.Balance)
                        and exEntry.date == balDate
                        and exEntry.account == local_account
                    ):
                        metakv["__duplicate__"] = True

            meta = data.new_metadata("", 0, metakv)

            # Only if the 'balance' permission is present
            if "running_balance" in trx:
                tx_balance = D(str(trx["running_balance"]["amount"]))
                # avoid pylint invalid-unary-operand-type
                signed_balance = -1 * tx_balance if invert_sign else tx_balance

                entries.append(
                    data.Balance(
                        meta,
                        balDate,
                        local_account,
                        amount.Amount(
                            signed_balance, trx["running_balance"]["currency"]
                        ),
                        None,
                        None,
                    )
                )

        return entries
