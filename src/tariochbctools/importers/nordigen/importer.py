from datetime import date
from os import path

import requests
import yaml
from beancount.core import amount, data
from beancount.core.number import D
from beancount.ingest import importer


class HttpServiceException(Exception):
    pass


class Importer(importer.ImporterProtocol):
    """An importer for Nordigen API (e.g. for Revolut)."""

    def identify(self, file):
        return "nordigen.yaml" == path.basename(file.name)

    def file_account(self, file):
        return ""

    def extract(self, file, existing_entries):
        with open(file.name, "r") as f:
            config = yaml.safe_load(f)

        r = requests.post(
            "https://ob.nordigen.com/api/v2/token/new/",
            data={
                "secret_id": config["secret_id"],
                "secret_key": config["secret_key"],
            },
        )
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise HttpServiceException(e, e.response.text)

        token = r.json()["access"]
        headers = {"Authorization": "Bearer " + token}

        entries = []
        for account in config["accounts"]:
            accountId = account["id"]
            assetAccount = account["asset_account"]
            r = requests.get(
                f"https://ob.nordigen.com/api/v2/accounts/{accountId}/transactions/",
                headers=headers,
            )
            try:
                r.raise_for_status()
            except requests.exceptions.HTTPError as e:
                raise HttpServiceException(e, e.response.text)

            transactions = sorted(
                r.json()["transactions"]["booked"], key=lambda trx: trx["bookingDate"]
            )
            for trx in transactions:
                metakv = {
                    "nordref": trx["transactionId"],
                }
                if "creditorName" in trx:
                    metakv["creditorName"] = trx["creditorName"]
                if "debtorName" in trx:
                    metakv["debtorName"] = trx["debtorName"]
                if "currencyExchange" in trx:
                    instructedAmount = trx["currencyExchange"]["instructedAmount"]
                    metakv["original"] = (
                        instructedAmount["currency"] + " " + instructedAmount["amount"]
                    )
                meta = data.new_metadata("", 0, metakv)
                trxDate = date.fromisoformat(trx["bookingDate"])
                narration = ""
                if "remittanceInformationUnstructured" in trx:
                    narration += trx["remittanceInformationUnstructured"]
                if "remittanceInformationUnstructuredArray" in trx:
                    narration += " ".join(trx["remittanceInformationUnstructuredArray"])
                entry = data.Transaction(
                    meta,
                    trxDate,
                    "*",
                    "",
                    narration,
                    data.EMPTY_SET,
                    data.EMPTY_SET,
                    [
                        data.Posting(
                            assetAccount,
                            amount.Amount(
                                D(str(trx["transactionAmount"]["amount"])),
                                trx["transactionAmount"]["currency"],
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
