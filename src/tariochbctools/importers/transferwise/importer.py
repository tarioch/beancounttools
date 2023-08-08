from datetime import date, datetime, timezone
from os import path

import dateutil.parser
import requests
import yaml
import base64
from beancount.core import amount, data
from beancount.core.number import D
from beancount.ingest import importer
from dateutil.relativedelta import relativedelta
import urllib3
from urllib.parse import urlencode
import rsa
import json

http = urllib3.PoolManager()


class Importer(importer.ImporterProtocol):
    """An importer for Transferwise using the API."""

    def identify(self, file):
        return "transferwise.yaml" == path.basename(file.name)

    def file_account(self, file):
        return ""

    # Based on the Transferwise official example provided under the
    # MIT license
    def _get_statement(
        self,
        api_token,
        interval_start,
        interval_end,
        currency,
        base_url,
        private_key_path,
        profile_id,
        account_id,
        one_time_token="",
        signature="",
        statement_type="FLAT",
    ):
        params = urlencode(
            {
                "currency": currency,
                "type": statement_type,
                "intervalStart": interval_start,
                "intervalEnd": interval_end,
            }
        )

        url = (
            base_url
            + "/v3/profiles/"
            + profile_id
            + "/borderless-accounts/"
            + account_id
            + "/statement.json?"
            + params
        )

        headers = {
            "Authorization": "Bearer " + api_token,
            "User-Agent": "tw-statements-sca",
            "Content-Type": "application/json",
        }
        if one_time_token != "":
            headers["x-2fa-approval"] = one_time_token
            headers["X-Signature"] = signature
            print(headers["x-2fa-approval"], headers["X-Signature"])

        print("GET", url)

        r = http.request("GET", url, headers=headers, retries=False)

        print("status:", r.status)

        if r.status == 200 or r.status == 201:
            return json.loads(r.data)
        elif r.status == 403 and r.getheader("x-2fa-approval") is not None:
            one_time_token = r.getheader("x-2fa-approval")
            signature = Importer._do_sca_challenge(
                one_time_token=one_time_token, private_key_path=private_key_path
            )
            return self._get_statement(
                api_token=api_token,
                one_time_token=one_time_token,
                signature=signature,
                interval_start=interval_start,
                interval_end=interval_end,
                currency=currency,
                base_url=base_url,
                private_key_path=private_key_path,
                account_id=account_id,
                profile_id=profile_id,
                statement_type=statement_type,
            )
        else:
            print("failed: ", r.status)
            print(r.data)
            sys.exit(0)

    @staticmethod
    def _do_sca_challenge(one_time_token, private_key_path):
        print("doing sca challenge")

        # Read the private key file as bytes.
        with open(private_key_path, "rb") as f:
            private_key_data = f.read()

        private_key = rsa.PrivateKey.load_pkcs1(private_key_data, "PEM")

        # Use the private key to sign the one-time-token that was returned
        # in the x-2fa-approval header of the HTTP 403.
        signed_token = rsa.sign(one_time_token.encode("ascii"), private_key, "SHA-256")

        # Encode the signed message as friendly base64 format for HTTP
        # headers.
        signature = base64.b64encode(signed_token).decode("ascii")

        return signature

    def extract(self, file, existing_entries):
        with open(file.name, "r") as f:
            config = yaml.safe_load(f)
        token = config["token"]
        baseAccount = config["baseAccount"]
        private_key_path = config["privateKeyPath"]
        startDate = datetime.combine(
            date.today() + relativedelta(months=-3), datetime.min.time(), timezone.utc
        ).isoformat()
        endDate = datetime.combine(
            date.today(), datetime.max.time(), timezone.utc
        ).isoformat()

        headers = {"Authorization": "Bearer " + token}
        r = requests.get("https://api.transferwise.com/v1/profiles", headers=headers)
        profiles = r.json()
        profileId = profiles[0]["id"]

        r = requests.get(
            "https://api.transferwise.com/v1/borderless-accounts",
            params={"profileId": profileId},
            headers=headers,
        )
        accounts = r.json()
        accountId = accounts[0]["id"]

        entries = []
        base_url = "https://api.transferwise.com"
        for account in accounts[0]["balances"]:
            accountCcy = account["currency"]

            #             r = requests.get(
            #                 f"https://api.transferwise.com/v3/profiles/{profileId}/borderless-accounts/{accountId}/statement.json",
            #                 params={
            #                     "currency": accountCcy,
            #                     "intervalStart": startDate,
            #                     "intervalEnd": endDate,
            #                 },
            #                 headers=headers,
            #             )
            #             transactions = r.json()
            transactions = self._get_statement(
                api_token=token,
                interval_start=startDate,
                interval_end=endDate,
                currency=accountCcy,
                base_url=base_url,
                private_key_path=private_key_path,
                profile_id=str(profileId),
                account_id=str(accountId),
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
                            baseAccount + accountCcy,
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
