import json
from unittest.mock import MagicMock, patch

import pytest
from beancount.core.number import D

from tariochbctools.importers.awardwalletimp import importer as awimp

# pylint: disable=protected-access

TEST_CONFIG = b"""
    api_key: deadc0dedeadc0dedeadc0dedeadc0de
    users:
      12:
        name: John Smith
        all_history: false
        accounts:
          7654321:
            provider: "British Airways Club"
            account: Assets:Current:Points
            currency: AVIOS
          6543210:
            provider: "Virgin Atlantic Club"
            account: Assets:Current:Points
            currency: VIRGINPTS
      34:
        name: User with dummy account
        accounts:
          0:
"""

TEST_TRX = b"""
    {
      "fields": [
        {
          "name": "Transaction Date",
          "code": "PostingDate",
          "value": {"value": "9/30/12", "type": "string"}
        },
        {
          "name": "Description",
          "code": "Description",
          "value": {"value": "Expired Points", "type": "string"}
        },
        {
          "name": "Type",
          "code": "Info",
          "value": {"value": "Adjustments", "type": "string"}
        },
        {
          "name": "Points",
          "code": "Miles",
          "value": {"value": "-1,042", "type": "miles"}
        }
      ]
    }
"""

TEST_USER_DETAILS = b"""
    {
      "userId": 12,
      "fullName": "John Smith",
      "status": "Free",
      "userName": "JSmith",
      "email": "JSmith@email.com",
      "forwardingEmail": "JSmith@AwardWallet.com",
      "accessLevel": "Regular",
      "connectionType": "Connected",
      "accountsAccessLevel": "Full control",
      "accountsSharedByDefault": true,
      "editConnectionUrl": "https://business.awardwallet.com/members/connection/112233",
      "accountListUrl": "https://business.awardwallet.com/account/list#/?agentId=112233",
      "timelineUrl": "https://business.awardwallet.com/timeline/?agentId=166765#/112233",
      "bookingRequestsUrl": "https://business.awardwallet.com/awardBooking/queue?user_filter=332211",
      "accounts": [
        {
          "accountId": 7654321,
          "code": "british",
          "displayName": "British Airways (Executive Club)",
          "kind": "Airlines",
          "login": "johnsmith",
          "autologinUrl": "https://business.awardwallet.com/account/redirect?ID=7654321",
          "updateUrl": "https://business.awardwallet.com/account/edit/7654321?autosubmit=1",
          "editUrl": "https://business.awardwallet.com/account/edit/7654321",
          "balance": "146,780",
          "balanceRaw": 146780,
          "owner": "John Smith",
          "errorCode": 1,
          "lastDetectedChange": "+750",
          "expirationDate": "2018-12-10T00:00:00+00:00",
          "lastRetrieveDate": "2016-01-15T00:00:00+00:00",
          "lastChangeDate": "2016-01-15T00:49:33+00:00",
          "properties": [
            {
              "name": "Next Elite Level",
              "value": {"value": "Bronze", "type": "string"},
              "kind": 9
            },
            {
              "name": "Date of joining the club",
              "value": {"value": "20 Jun 2013", "type": "string"},
              "kind": 5
            },
            {
              "name": "Lifetime Tier Points",
              "value": {"value": "35,000", "type": "string"}
            },
            {
              "name": "Executive Club Tier Points",
              "value": {"value": "35,000", "type": "string"}
            },
            {
              "name": "Card expiry date",
              "value": {"value": "31 Mar 2017", "type": "string"}
            },
            {
              "name": "Membership year ends",
              "value": {"value": "08 Feb 2016", "type": "string"}
            },
            {
              "name": "Last Activity",
              "value": {"value": "10-Dec-15", "type": "string"},
              "kind": 13
            },
            {
              "name": "Name",
              "value": {"value": "Mr Smith", "type": "string"},
              "kind": 12
            },
            {
              "name": "Level",
              "value": {"value": "Blue", "type": "string"},
              "rank": 0,
              "kind": 3
            },
            {
              "name": "Membership no",
              "value": {"value": "1122334455", "type": "string"},
              "kind": 1
            }
          ],
          "history": [
            {
              "fields": [
                {
                  "name": "Transaction Date",
                  "code": "PostingDate",
                  "value": {"value": "3/31/14", "type": "string"}
                },
                {
                  "name": "Description",
                  "code": "Description",
                  "value": {"value": "Expired Points", "type": "string"}
                },
                {
                  "name": "Type",
                  "code": "Info",
                  "value": {"value": "Adjustments", "type": "string"}
                },
                {
                  "name": "Points",
                  "code": "Miles",
                  "value": {"value": "-100", "type": "miles"}
                }
              ]
            },
            {
              "fields": [
                {
                  "name": "Transaction Date",
                  "code": "PostingDate",
                  "value": {"value": "12/11/13", "type": "string"}
                },
                {
                  "name": "Description",
                  "code": "Description",
                  "value": {"value": "Google Wallet", "type": "string"}
                },
                {
                  "name": "Type",
                  "code": "Info",
                  "value": {"value": "Other Earning", "type": "string"}
                },
                {
                  "name": "Points",
                  "code": "Miles",
                  "value": {"value": "+100", "type": "miles"}
                }
              ]
            },
            {
              "fields": [
                {
                  "name": "Transaction Date",
                  "code": "PostingDate",
                  "value": {"value": "9/30/12", "type": "string"}
                },
                {
                  "name": "Description",
                  "code": "Description",
                  "value": {"value": "Expired Points", "type": "string"}
                },
                {
                  "name": "Type",
                  "code": "Info",
                  "value": {"value": "Adjustments", "type": "string"}
                },
                {
                  "name": "Points",
                  "code": "Miles",
                  "value": {"value": "-1,042", "type": "miles"}
                }
              ]
            }
          ]
        },
        {
          "accountId": 6543210,
          "code": "virgin",
          "displayName": "Virgin Atlantic (Flying Club)",
          "kind": "Airlines",
          "balance": "146,780",
          "balanceRaw": 146780,
          "owner": "John Smith",
          "errorCode": 1,
          "lastDetectedChange": "+750",
          "properties": [
            {
              "name": "Next Elite Level",
              "value": {"value": "Bronze", "type": "string"},
              "kind": 9
            }
          ],
          "history": [
          ]
        }
      ]
    }
"""


@pytest.fixture(name="tmp_config")
def tmp_config_fixture(tmp_path):
    config = tmp_path / "awardwallet.yaml"
    config.write_bytes(TEST_CONFIG)
    yield config


@pytest.fixture(name="importer")
def awardwallet_importer_fixture(tmp_config):
    importer = awimp.Importer()
    importer._configure(tmp_config, [])
    yield importer


@pytest.fixture(name="importer_factory")
def awardwallet_importer_factory(tmp_path):
    """A awardwallet importer factory for
    generating an importer with a custom config
    """

    def _importer_with_config(custom_config):
        config = tmp_path / "awardwallet.yaml"
        config.write_bytes(custom_config)
        importer = awimp.Importer()
        importer._configure(config, [])
        return importer

    yield _importer_with_config


@pytest.fixture(name="tmp_trx")
def tmp_trx_fixture():
    yield json.loads(TEST_TRX)


@pytest.fixture(name="tmp_user_details")
def tmp_user_details_fixture():
    yield json.loads(TEST_USER_DETAILS, strict=False)


def test_identify(importer, tmp_config):
    assert importer.identify(tmp_config)


def test_extract_transaction_simple(importer, tmp_trx):
    entries = importer._extract_transaction(tmp_trx, "Assets:Other", "POINTS", 7654321)
    assert entries[0].postings[0].units.number == D(
        tmp_trx["fields"][3]["value"]["value"]
    )


def test_extract_user_history(importer, tmp_user_details):
    entries = importer._extract_user_history(
        importer.config["users"][12],
        tmp_user_details,
    )
    assert len(entries) == 3


@patch("tariochbctools.importers.awardwalletimp.importer.AwardWalletClient")
def test_extract_all_users(mock_api, importer, tmp_config, tmp_user_details):
    importer._extract_user_history = MagicMock()

    importer.extract(tmp_config)
    assert importer._extract_user_history.call_count == 2


@patch("tariochbctools.importers.awardwalletimp.importer.AwardWalletClient")
def test_extract_all_accounts(mock_api, importer, tmp_config, tmp_user_details):
    importer._extract_transactions = MagicMock()
    mock_api.return_value.get_connected_user_details.return_value = tmp_user_details

    importer.extract(tmp_config)
    assert importer._extract_transactions.call_count == 2
