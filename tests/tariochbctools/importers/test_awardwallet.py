import json

import pytest
from beancount.core.number import D

from tariochbctools.importers.awardwallet import importer as awimp

# pylint: disable=protected-access

TEST_CONFIG = b"""
    api_key: deadc0dedeadc0dedeadc0dedeadc0de
    users:
      12345:
        name: John Smith
        accounts:
          7654321:
            provider: "British Airways Club"
            account: Assets:Current:Points
            currency: AVIOS
"""

TEST_TRX = b"""
    {
      "fields": [
        {
          "name": "Transaction Date",
          "code": "PostingDate",
          "value": "9/30/12"
        },
        {
          "name": "Description",
          "code": "Description",
          "value": "Expired Points"
        },
        {
          "name": "Type",
          "code": "Info",
          "value": "Adjustments"
        },
        {
          "name": "Points",
          "code": "Miles",
          "value": "-1,042"
        }
      ]
    }
"""

TEST_USER_DETAILS = b"""
    {
      "userId": 12345,
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
              "value": "Bronze",
              "kind": 9
            },
            {
              "name": "Date of joining the club",
              "value": "20 Jun 2013",
              "kind": 5
            },
            {
              "name": "Lifetime Tier Points",
              "value": "35,000"
            },
            {
              "name": "Executive Club Tier Points",
              "value": "35,000"
            },
            {
              "name": "Card expiry date",
              "value": "31 Mar 2017"
            },
            {
              "name": "Membership year ends",
              "value": "08 Feb 2016"
            },
            {
              "name": "Last Activity",
              "value": "10-Dec-15",
              "kind": 13
            },
            {
              "name": "Name",
              "value": "Mr Smith",
              "kind": 12
            },
            {
              "name": "Level",
              "value": "Blue",
              "rank": 0,
              "kind": 3
            },
            {
              "name": "Membership no",
              "value": "1122334455",
              "kind": 1
            }
          ],
          "history": [
            {
              "fields": [
                {
                  "name": "Transaction Date",
                  "code": "PostingDate",
                  "value": "3/31/14"
                },
                {
                  "name": "Description",
                  "code": "Description",
                  "value": "Expired Points"
                },
                {
                  "name": "Type",
                  "code": "Info",
                  "value": "Adjustments"
                },
                {
                  "name": "Points",
                  "code": "Miles",
                  "value": "-100"
                }
              ]
            },
            {
              "fields": [
                {
                  "name": "Transaction Date",
                  "code": "PostingDate",
                  "value": "12/11/13"
                },
                {
                  "name": "Description",
                  "code": "Description",
                  "value": "Google Wallet"
                },
                {
                  "name": "Type",
                  "code": "Info",
                  "value": "Other Earning"
                },
                {
                  "name": "Points",
                  "code": "Miles",
                  "value": "+100"
                }
              ]
            },
            {
              "fields": [
                {
                  "name": "Transaction Date",
                  "code": "PostingDate",
                  "value": "9/30/12"
                },
                {
                  "name": "Description",
                  "code": "Description",
                  "value": "Expired Points"
                },
                {
                  "name": "Type",
                  "code": "Info",
                  "value": "Adjustments"
                },
                {
                  "name": "Points",
                  "code": "Miles",
                  "value": "-1,042"
                }
              ]
            }
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
    yield json.loads(TEST_USER_DETAILS)


def test_identify(importer, tmp_config):
    assert importer.identify(tmp_config)


def test_extract_transaction_simple(importer, tmp_trx):
    entries = importer._extract_transaction(tmp_trx, "Assets:Other", "POINTS")
    assert entries[0].postings[0].units.number == D(tmp_trx["fields"][3]["value"])


def test_extract_account(importer, tmp_user_details):
    entries = importer._extract_account(
        importer.config["users"][12345],
        tmp_user_details,
    )
    assert entries
