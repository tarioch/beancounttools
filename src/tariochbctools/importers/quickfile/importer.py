import logging
import uuid
from datetime import datetime
from hashlib import md5
from os import path
from typing import Dict, List, NamedTuple

import beangulp
import requests
import yaml
from beancount.core import amount, data
from beancount.core.number import D
from undictify import type_checked_constructor


@type_checked_constructor(skip=True, convert=True)
class QuickFileTransaction(NamedTuple):
    """Transaction data from QuickFile transaction API"""

    TransactionDate: str
    Reference: str
    Amount: str  # otherwise tiny conversion losses
    TagStatus: str
    TransactionId: str

    def to_beancount_transaction(self, local_account, currency, invert_sign=False):
        tx_amount = D(self.Amount)
        # avoid pylint invalid-unary-operand-type
        signed_amount = -1 * tx_amount if invert_sign else tx_amount

        metakv = {
            "quickfile_id": self.TransactionId,
        }

        meta = data.new_metadata("", 0, metakv)
        date = datetime.fromisoformat(self.TransactionDate).date()

        entry = data.Transaction(
            meta,
            date,
            "*",
            "",
            self.Reference,
            data.EMPTY_SET,
            data.EMPTY_SET,
            [
                data.Posting(
                    local_account,
                    amount.Amount(signed_amount, currency),
                    None,
                    None,
                    None,
                    None,
                ),
            ],
        )
        return entry


@type_checked_constructor(skip=True, convert=True)
class QuickFileResponseMetaData(NamedTuple):
    RecordsetCount: int
    ReturnCount: int
    BankName: str
    BankType: str
    AccountNo: str
    SortCode: str
    Currency: str
    CurrentBalance: str


@type_checked_constructor(skip=True, convert=True)
class QuickFileBankSearch(NamedTuple):
    MetaData: QuickFileResponseMetaData
    Transactions: Dict[str, List[QuickFileTransaction]]


class QuickFile:
    """Encapsulate QuickFile API protocol and data types"""

    DOMAIN = "quickfile.co.uk"
    API_VERSION_SLUG = "1_2"

    def __init__(self, account_number, api_key, app_id):
        self.account_number = account_number
        self.api_key = api_key
        self.app_id = app_id
        self._update_submission_number()

    @staticmethod
    def auth_md5(account_number, api_key, submission_number):
        md5_str = (account_number + api_key + str(submission_number)).encode("utf-8")

        return md5(md5_str).hexdigest()

    def request_header(self):
        auth_md5 = self.auth_md5(
            self.account_number, self.api_key, self.submission_number
        )

        header = {
            "MessageType": "Request",
            "SubmissionNumber": str(self.submission_number),
            "Authentication": {
                "AccNumber": str(self.account_number),
                "MD5Value": auth_md5,
                "ApplicationID": str(self.app_id),
            },
        }
        return header

    def _update_submission_number(self):
        self.submission_number = uuid.uuid4()

    def _post(self, endpoint, endpoint_data):
        header = self.request_header()
        post_data = {"payload": {"Header": header, "Body": endpoint_data}}

        r = requests.post(
            f"https://api.{self.DOMAIN}/{self.API_VERSION_SLUG}/{endpoint}",
            json=post_data,
        )

        if not r:
            try:
                r.raise_for_status()
            except requests.HTTPError as e:
                logging.warning(e)

        self._update_submission_number()

        return r.json()

    def bank_search(
        self, account_number, transaction_count, from_date=None, to_date=None
    ):
        endpoint_data = {
            "SearchParameters": {
                "ReturnCount": str(transaction_count),
                "Offset": "0",
                "OrderResultsBy": "TransactionDate",
                "OrderDirection": "DESC",
                "NominalCode": str(account_number),
            }
        }
        if from_date:
            endpoint_data["SearchParameters"]["FromDate"] = str(from_date)
        if to_date:
            endpoint_data["SearchParameters"]["ToDate"] = str(to_date)
        response = self._post("bank/search", endpoint_data)
        body = response["Bank_Search"]["Body"]
        return QuickFileBankSearch(**body)


class Importer(beangulp.Importer):
    """An importer for QuickFile"""

    def __init__(self):
        self.quickfile = None
        self.config = None
        self.existing = None

    def _configure(self, filepath, existing):
        with open(filepath, "r") as config_file:
            self.config = yaml.safe_load(config_file)
            self.quickfile = QuickFile(
                account_number=self.config["account_number"],
                api_key=self.config["api_key"],
                app_id=self.config["app_id"],
            )
        self.existing = existing

    def identify(self, filepath):
        return path.basename(filepath) == "quickfile.yaml"

    def account(self, filepath):
        return ""

    def extract(self, filepath, existing=None):
        self._configure(filepath, existing)
        entries = []

        for bank_account in self.config["accounts"].keys():
            entries.extend(self._extract_bank_transactions(bank_account))

        return entries

    def _extract_bank_transactions(self, bank_account, invert_sign=False):
        entries = []
        transaction_count = self.config["transaction_count"]  # [0..200]
        from_date = self.config.get("from_date", None)
        to_date = self.config.get("to_date", None)
        response = self.quickfile.bank_search(
            bank_account, transaction_count, from_date, to_date
        )
        metadata = response.MetaData
        transactions = response.Transactions["Transaction"]
        local_account = self.config["accounts"].get(bank_account)

        for trx in transactions:
            entries.extend(
                self._extract_transaction(
                    trx, local_account, metadata, transactions, invert_sign
                )
            )

        return entries

    def _extract_transaction(
        self, trx, local_account, metadata, transactions, invert_sign
    ):
        entries = []

        entry = trx.to_beancount_transaction(
            local_account, metadata.Currency, invert_sign
        )
        entries.append(entry)

        return entries
