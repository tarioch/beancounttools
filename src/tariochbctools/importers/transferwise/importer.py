import base64
import json
from datetime import date, datetime, timezone
from os import path
from typing import Any
from urllib.parse import urlencode

import beangulp
import dateutil.parser
import requests
import rsa
import urllib3
import yaml
from beancount.core import amount, data
from beancount.core.number import D
from dateutil.relativedelta import relativedelta

from tariochbctools.importers.general.deduplication import ReferenceDuplicatesComparator

http = urllib3.PoolManager()


class Importer(beangulp.Importer):
    """An importer for Transferwise using the API."""

    def identify(self, filepath: str) -> bool:
        return path.basename(filepath).endswith("transferwise.yaml")

    def account(self, filepath: str) -> data.Account:
        return ""

    def __init__(self, *args: Any, **kwargs: Any):
        if "profileId" in kwargs:
            self.profileId = kwargs.pop("profileId")
        if "startDate" in kwargs:
            self.startDate = kwargs.pop("startDate")
        else:
            self.startDate = datetime.combine(
                date.today() + relativedelta(months=-3),
                datetime.min.time(),
                timezone.utc,
            ).isoformat()
        if "endDate" in kwargs:
            self.endDate = kwargs.pop("endDate")
        else:
            self.endDate = datetime.combine(
                date.today(), datetime.max.time(), timezone.utc
            ).isoformat()
        super().__init__(*args, **kwargs)

    # Based on the Transferwise official example provided under the
    # MIT license
    def _get_statement(
        self,
        currency: str,
        base_url: str,
        statement_type: str = "FLAT",
    ) -> Any:
        params = urlencode(
            {
                "currency": currency,
                "type": statement_type,
                "intervalStart": self.startDate,
                "intervalEnd": self.endDate,
            }
        )

        url = (
            base_url
            + "/v3/profiles/"
            + str(self.profileId)
            + "/borderless-accounts/"
            + str(self.accountId)
            + "/statement.json?"
            + params
        )

        headers = {
            "Authorization": "Bearer " + self.api_token,
            "User-Agent": "tw-statements-sca",
            "Content-Type": "application/json",
        }
        if hasattr(self, "one_time_token"):
            headers["x-2fa-approval"] = self.one_time_token  # type: ignore
            headers["X-Signature"] = self.signature  # type: ignore

        r = http.request("GET", url, headers=headers, retries=False)

        if r.status == 200 or r.status == 201:
            return json.loads(r.data)
        elif r.status == 403 and r.getheader("x-2fa-approval") is not None:
            self.one_time_token = r.getheader("x-2fa-approval")
            self.signature = self._do_sca_challenge()
            return self._get_statement(
                currency=currency,
                base_url=base_url,
                statement_type=statement_type,
            )
        else:
            raise Exception("Failed to get transactions.")

    def _do_sca_challenge(self):
        # Read the private key file as bytes.
        with open(self.private_key_path, "rb") as f:
            private_key_data = f.read()

        private_key = rsa.PrivateKey.load_pkcs1(private_key_data, "PEM")

        # Use the private key to sign the one-time-token that was returned
        # in the x-2fa-approval header of the HTTP 403.
        signed_token = rsa.sign(
            self.one_time_token.encode("ascii"), private_key, "SHA-256"
        )

        # Encode the signed message as friendly base64 format for HTTP
        # headers.
        signature = base64.b64encode(signed_token).decode("ascii")

        return signature

    def extract(self, filepath, existing):
        with open(filepath, "r") as f:
            config = yaml.safe_load(f)
        self.api_token = config["token"]
        baseAccount = config["baseAccount"]
        self.private_key_path = config["privateKeyPath"]

        headers = {"Authorization": "Bearer " + self.api_token}
        if not self.profileId:
            r = requests.get(
                "https://api.transferwise.com/v1/profiles", headers=headers
            )
            profiles = r.json()
            self.profileId = profiles[0]["id"]

        r = requests.get(
            "https://api.transferwise.com/v1/borderless-accounts",
            params={"profileId": self.profileId},
            headers=headers,
        )
        accounts = r.json()
        self.accountId = accounts[0]["id"]

        entries = []
        base_url = "https://api.transferwise.com"
        for account in accounts[0]["balances"]:
            accountCcy = account["currency"]
            if isinstance(baseAccount, dict):
                account_name = baseAccount[accountCcy]
            else:
                account_name = baseAccount + accountCcy
            transactions = self._get_statement(
                currency=accountCcy,
                base_url=base_url,
                statement_type="FLAT",
            )

            for transaction in transactions["transactions"]:
                metakv = {
                    "ref": transaction["referenceNumber"],
                }
                meta = data.new_metadata("", 0, metakv)
                entry = data.Transaction(
                    meta,
                    dateutil.parser.parse(transaction["date"]).date(),
                    "*",
                    "",
                    transaction["details"]["description"],
                    data.EMPTY_SET,
                    data.EMPTY_SET,
                    [
                        data.Posting(
                            account_name,
                            amount.Amount(
                                D(str(transaction["amount"]["value"])),
                                transaction["amount"]["currency"],
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
