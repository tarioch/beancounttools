from datetime import date
from os import path

import beangulp
import requests
import yaml
from beancount.core import amount, data
from beancount.core.number import D

from tariochbctools.importers.general.deduplication import ReferenceDuplicatesComparator


class HttpServiceException(Exception):
    pass


class Importer(beangulp.Importer):
    """An importer for Nordigen API (e.g. for Revolut)."""

    def identify(self, filepath: str) -> bool:
        return path.basename(filepath).endswith("nordigen.yaml")

    def account(self, filepath: str) -> data.Entries:
        return ""

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        with open(filepath, "r") as f:
            config = yaml.safe_load(f)

        r = requests.post(
            "https://bankaccountdata.gocardless.com/api/v2/token/new/",
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
                f"https://bankaccountdata.gocardless.com/api/v2/accounts/{accountId}/transactions/",
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
                if "transactionId" in trx:
                    metakv = {
                        "nordref": trx["transactionId"],
                    }
                else:
                    metakv = {}

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

    cmp = ReferenceDuplicatesComparator(["nordref"])
