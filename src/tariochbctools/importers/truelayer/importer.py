from datetime import timedelta
from os import path

import dateutil.parser
import requests
import yaml
from beancount.core import amount, data
from beancount.core.number import D
from beancount.ingest import importer


class Importer(importer.ImporterProtocol):
    """An importer for Truelayer API (e.g. for Revolut)."""

    def __init__(self):
        self.config = None
        self.baseAccount = None
        self.clientId = None
        self.clientSecret = None
        self.refreshToken = None
        self.sandbox = None
        self.existing_entries = None
        self.domain = "truelayer.com"

    def _configure(self, file, existing_entries):
        with open(file.name, "r") as f:
            self.config = yaml.safe_load(f)
        self.baseAccount = self.config["baseAccount"]
        self.clientId = self.config["client_id"]
        self.clientSecret = self.config["client_secret"]
        self.refreshToken = self.config["refresh_token"]
        self.sandbox = self.clientId.startswith("sandbox")
        self.existing_entries = existing_entries

        if self.sandbox:
            self.domain = "truelayer-sandbox.com"

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

        return entries

    def _extract_endpoint_transactions(self, endpoint, headers):
        entries = []
        r = requests.get(f"https://api.{self.domain}/data/v1/{endpoint}", headers=headers)

        for account in r.json()["results"]:
            accountId = account["account_id"]
            accountCcy = account["currency"]
            r = requests.get(
                f"https://api.{self.domain}/data/v1/{endpoint}/{accountId}/transactions",
                headers=headers,
            )
            transactions = sorted(r.json()["results"], key=lambda trx: trx["timestamp"])

            for trx in transactions:
                entries.extend(self._extract_transaction(trx, accountCcy, transactions))

        return entries

    def _extract_transaction(self, trx, accountCcy, transactions):
        entries = []
        metakv = {}
        # sandbox Mock bank doesn't have a provider_id
        if "meta" in trx and "provider_id" in trx["meta"]:
            metakv["tlref"] = trx["meta"]["provider_id"]

        if trx["transaction_classification"]:
            metakv["category"] = trx["transaction_classification"][0]

        meta = data.new_metadata("", 0, metakv)
        trxDate = dateutil.parser.parse(trx["timestamp"]).date()
        account = self.baseAccount + accountCcy
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
                    account,
                    amount.Amount(D(str(trx["amount"])), trx["currency"]),
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
                        and exEntry.account == account
                    ):
                        metakv["__duplicate__"] = True

            meta = data.new_metadata("", 0, metakv)

            # Only if the 'balance' permission is present
            if "running_balance" in trx:
                entries.append(
                    data.Balance(
                        meta,
                        balDate,
                        account,
                        amount.Amount(
                            D(str(trx["running_balance"]["amount"])),
                            trx["running_balance"]["currency"],
                        ),
                        None,
                        None,
                    )
                )

        return entries
