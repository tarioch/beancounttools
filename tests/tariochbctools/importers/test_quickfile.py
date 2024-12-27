import json
from unittest.mock import MagicMock, call

import pytest
from beancount.core import data
from beancount.core.number import D

from tariochbctools.importers.quickfile import importer as qfimp

# pylint: disable=protected-access

TEST_CONFIG = b"""
account_number: "YOUR_ACCOUNT_NUMBER"
api_key: SOME_API_KEY
app_id: SOME_APP_ID
accounts:
    1200: Assets:Other
    1201: Assets:Savings
transaction_count: 200
"""

# Example from the quickfile API docs
TEST_TRX = b"""
{
    "TransactionDate": "2017-01-04T12:34:56",
    "Reference": "WATERSTONES REF 364 2177333010 BCC",
    "Amount": -4.75,
    "TagStatus": null,
    "TransactionId": 666
}
"""

TEST_META_DATA = b"""
{
    "RecordsetCount": 6853,
    "ReturnCount": 1,
    "BankName": "Current Account",
    "BankType": "CURRENT",
    "AccountNo": "90145741",
    "SortCode": "208246",
    "Currency": "GBP",
    "CurrentBalance": 3164.97
}
"""

TEST_BANK_SEARCH = b"""
{
  "Bank_Search": {
    "Header": {
      "MessageType": "Response",
      "SubmissionNumber": "8ebba60a-95ce-44af-a8c7-e827ac1ae117"
    },
    "Body": {
      "MetaData": {
        "RecordsetCount": 6853,
        "ReturnCount": 1,
        "BankName": "Current Account",
        "BankType": "CURRENT",
        "AccountNo": "90145741",
        "SortCode": "208246",
        "Currency": "GBP",
        "CurrentBalance": 3164.97
      },
      "Transactions": {
        "Transaction": [
          {
            "TransactionDate": "2017-01-04T00:00:00",
            "Reference": "WATERSTONES REF 364 2177333010 BCC",
            "Amount": -4.75,
            "TagStatus": null,
            "TransactionId": 0
          }
        ]
      }
    }
  }
}
"""


@pytest.fixture(name="tmp_config")
def tmp_config_fixture(tmp_path):
    config = tmp_path / "quickfile.yaml"
    config.write_bytes(TEST_CONFIG)
    yield config


@pytest.fixture(name="importer")
def quickfile_importer_fixture(tmp_config):
    importer = qfimp.Importer()
    importer._configure(tmp_config, [])
    yield importer


@pytest.fixture(name="importer_factory")
def quickfile_importer_factory(tmp_path):
    """A quickfile importer factory for
    generating an importer with a custom config
    """

    def _importer_with_config(custom_config):
        config = tmp_path / "quickfile.yaml"
        config.write_bytes(custom_config)
        importer = qfimp.Importer()
        importer._configure(config, [])
        return importer

    yield _importer_with_config


@pytest.fixture(name="tmp_trx")
def tmp_trx_fixture():
    j = json.loads(TEST_TRX)
    yield qfimp.QuickFileTransaction(**j)


@pytest.fixture(name="tmp_metadata")
def tmp_metadata_fixture():
    j = json.loads(TEST_META_DATA)
    metadata = qfimp.QuickFileResponseMetaData(**j)
    yield metadata


def test_identify(importer, tmp_config):
    assert importer.identify(tmp_config)


def test_extract_transaction_simple(importer, tmp_trx, tmp_metadata):
    entries = importer._extract_transaction(
        tmp_trx, "Assets:Other", tmp_metadata, [tmp_trx], invert_sign=False
    )
    data.sanity_check_types(entries[0])


def test_extract_transaction_invert_sign(importer, tmp_trx, tmp_metadata):
    """Show that sign inversion works"""
    entries = importer._extract_transaction(
        tmp_trx, "Assets:Other", tmp_metadata, [tmp_trx], invert_sign=True
    )
    assert entries[0].postings[0].units.number == -D(str(tmp_trx.Amount))


def test_extract_transaction_has_quickfile_id(importer, tmp_trx, tmp_metadata):
    """Ensure mandatory IDs are in extracted transactions."""
    entries = importer._extract_transaction(
        tmp_trx, "Assets:Other", tmp_metadata, [tmp_trx], invert_sign=False
    )
    assert "quickfile_id" in entries[0].meta


def test_request_header_auth(importer, tmp_config):
    header = importer.quickfile.request_header()
    auth = header.get("Authentication")

    config = importer.config

    assert auth["AccNumber"] == config["account_number"]
    assert auth["MD5Value"] == importer.quickfile.auth_md5(
        config["account_number"],
        config["api_key"],
        importer.quickfile.submission_number,
    )
    assert auth["ApplicationID"] == config["app_id"]


def test_bank_search():
    response = json.loads(TEST_BANK_SEARCH)
    body = response["Bank_Search"]["Body"]
    bs = qfimp.QuickFileBankSearch(**body)
    assert len(bs.Transactions["Transaction"]) == 1


def test_extract_all_accounts(importer, tmp_config):
    importer._extract_bank_transactions = MagicMock()
    importer.extract(tmp_config)
    calls = [call(1200), call(1201)]
    importer._extract_bank_transactions.assert_has_calls(calls, any_order=True)


def test_bank_search_with_dates():
    account_number = "37823"
    transaction_count = 13
    from_date = "2017-01-01"
    to_date = "2017-01-31"
    under_test = qfimp.QuickFile(account_number, "an_api_key", "an_app_id")
    under_test._post = MagicMock()
    under_test._post.return_value = json.loads(TEST_BANK_SEARCH)
    under_test.bank_search(account_number, transaction_count, from_date, to_date)
    expected_search_parameters = {
        "SearchParameters": {
            "ReturnCount": str(transaction_count),
            "Offset": "0",
            "OrderResultsBy": "TransactionDate",
            "OrderDirection": "DESC",
            "NominalCode": str(account_number),
            "FromDate": from_date,
            "ToDate": to_date,
        }
    }
    under_test._post.assert_called_with("bank/search", expected_search_parameters)
