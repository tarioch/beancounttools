import json
from datetime import timedelta

import dateutil.parser
import pytest
import yaml
from beancount.core.amount import Decimal as D

from tariochbctools.importers.truelayer import importer as tlimp

# pylint: disable=protected-access

TEST_CONFIG = b"""
    account: DefaultAccount
    client_id: sandbox-random
    client_secret: deadc0de-dead-c0de-dead-c0dedeadc0de
    refresh_token: 98D124C0E677865CB2F7D9DE91DC394CEED31DA3469C681B41FB7831F2F9B089
    access_token: eyJhbGciOiJSUzI1NiIsImtpZsomethingSomethingsomethingDarkSideOEJBNk
    accounts:
      hex-account-id-1: Assets:Other
      hex-account-id-2: Assets:Savings
      hex-account-id-3: Liabilities:Mastercard
      hex-account-id-4: Liabilities:Visa
"""

# Example from the truelayer Mock bank
TEST_TRX = b"""
{
  "timestamp": "2021-06-14T00:00:00Z",
  "description": "MT SECURETRADE LIM",
  "transaction_type": "CREDIT",
  "transaction_category": "PURCHASE",
  "transaction_classification": [],
  "amount": -20.5,
  "currency": "GBP",
  "transaction_id": "mandatory-transaction-id-value",
  "provider_transaction_id": "6906e4ecbf4a9775e3",
  "normalised_provider_transaction_id": "txn-4912996e337e5b5f3",
  "running_balance": {
    "currency": "GBP",
    "amount": 332.94
  },
  "meta": {
    "provider_id": "SOME-PROVIDER-ID",
    "provider_reference": "SOME-PROVIDER-REFERENCE",
    "provider_transaction_category": "DEB"
  }
}
"""

# Example from the truelayer Mock bank
TEST_TRX_WITHOUT_IDS = b"""
{
  "timestamp": "2021-06-14T00:00:00Z",
  "description": "MT SECURETRADE LIM",
  "transaction_type": "CREDIT",
  "transaction_category": "PURCHASE",
  "transaction_classification": [],
  "amount": -20.5,
  "currency": "GBP",
  "transaction_id": "81cd222c77f49eb11b72a82478a07dbd",
  "running_balance": {
    "currency": "GBP",
    "amount": 332.94
  },
  "meta": {
    "provider_transaction_category": "DEB"
  }
}
"""

TEST_BALANCE_SIMPLE = b"""
{
  "currency": "GBP",
  "current": 20.0,
  "update_timestamp": "2017-02-24T17:29:24.740Z"
}
"""

TEST_BALANCE_OPTIONAL = b"""
{
  "available": 3279.0,
  "currency": "GBP",
  "current": 20.0,
  "credit_limit": 3300,
  "last_statement_balance": 226,
  "last_statement_date": "2017-01-28",
  "payment_due": 5.0,
  "payment_due_date": "2017-02-24",
  "update_timestamp": "2017-02-24T17:29:24.740Z"
}
"""


@pytest.fixture(name="tmp_config")
def tmp_config_fixture(tmp_path):
    config = tmp_path / "truelayer.yaml"
    config.write_bytes(TEST_CONFIG)
    yield config


@pytest.fixture(name="importer")
def truelayer_importer_fixture(tmp_config):
    importer = tlimp.Importer()
    importer._configure(tmp_config, [])
    yield importer


@pytest.fixture(name="importer_factory")
def truelayer_importer_factory(tmp_path):
    """A truelayer importer factory for
    generating an importer with a custom config
    """

    def _importer_with_config(custom_config):
        config = tmp_path / "truelayer.yaml"
        config.write_bytes(custom_config)
        importer = tlimp.Importer()
        importer._configure(config, [])
        return importer

    yield _importer_with_config


@pytest.fixture(name="tmp_trx")
def tmp_trx_fixture():
    yield json.loads(TEST_TRX)


def test_identify(importer, tmp_config):
    assert importer.identify(tmp_config)


def test_extract_transaction_simple(importer, tmp_trx):
    entries = importer._extract_transaction(
        tmp_trx, "Assets:Other", [tmp_trx], invert_sign=False
    )
    assert entries[0].postings[0].units.number == D(str(tmp_trx["amount"]))


def test_extract_transaction_invert_sign(importer, tmp_trx):
    """Show that sign inversion works"""
    entries = importer._extract_transaction(
        tmp_trx, "Assets:Other", [tmp_trx], invert_sign=True
    )
    assert entries[0].postings[0].units.number == -D(str(tmp_trx["amount"]))


def test_extract_balance(importer, tmp_trx):
    tmp_balance = json.loads(TEST_BALANCE_SIMPLE)

    entries = importer._extract_balance(tmp_balance, "Assets:Other", invert_sign=False)

    assert len(entries) == 1
    assert entries[-1].amount.number == D(str(tmp_balance["current"]))
    assert (
        entries[-1].date - timedelta(days=1)
        == dateutil.parser.parse(tmp_balance["update_timestamp"]).date()
    ), "balance date should be one day after update_timestamp"


def test_extract_statement_balance(importer, tmp_trx):
    tmp_balance = json.loads(TEST_BALANCE_OPTIONAL)

    entries = importer._extract_balance(tmp_balance, "Assets:Other", invert_sign=False)

    assert len(entries) == 2
    assert entries[-1].amount.number == D(str(tmp_balance["last_statement_balance"]))
    assert (
        entries[-1].date
        == dateutil.parser.parse(tmp_balance["last_statement_date"]).date()
    )


@pytest.mark.parametrize("id_field", tlimp.TX_MANDATORY_ID_FIELDS)
def test_extract_transaction_has_transaction_id(importer, tmp_trx, id_field):
    """Ensure mandatory IDs are in extracted transactions."""
    entries = importer._extract_transaction(
        tmp_trx, "Assets:Other", [tmp_trx], invert_sign=False
    )
    assert entries[0].meta[id_field] == tmp_trx[id_field]


@pytest.mark.parametrize("id_field", tlimp.TX_OPTIONAL_ID_FIELDS)
def test_trx_id(importer, tmp_trx, id_field):
    entries = importer._extract_transaction(
        tmp_trx, "Assets:Other", [tmp_trx], invert_sign=False
    )
    assert entries[0].meta[id_field] == tmp_trx[id_field]


@pytest.mark.parametrize("id_field", tlimp.TX_OPTIONAL_ID_FIELDS)
def test_trx_id_is_optional(importer, id_field):
    tmp_trx = json.loads(TEST_TRX_WITHOUT_IDS)
    entries = importer._extract_transaction(
        tmp_trx, "Assets:Other", [tmp_trx], invert_sign=False
    )
    assert entries[0].meta.get(id_field) is None


@pytest.mark.parametrize("id_field", tlimp.TX_OPTIONAL_META_ID_FIELDS)
def test_trx_meta_id(importer, tmp_trx, id_field):
    entries = importer._extract_transaction(
        tmp_trx, "Assets:Other", [tmp_trx], invert_sign=False
    )
    assert entries[0].meta[id_field] == tmp_trx["meta"][id_field]


@pytest.mark.parametrize("id_field", tlimp.TX_OPTIONAL_META_ID_FIELDS)
def test_trx_meta_id_is_optional(importer, id_field):
    tmp_trx = json.loads(TEST_TRX_WITHOUT_IDS)
    entries = importer._extract_transaction(
        tmp_trx, "Assets:Other", [tmp_trx], invert_sign=False
    )
    assert entries[0].meta.get(id_field) is None


@pytest.mark.parametrize("account_id", yaml.safe_load(TEST_CONFIG)["accounts"].keys())
def test_get_account_for_account_id(importer, account_id):
    assert (
        importer._get_account_for_account_id(account_id)
        == importer.config["accounts"][account_id]
    )


def test_get_account_for_account_id_returns_none(importer):
    assert importer._get_account_for_account_id("unknown-account-id") is None


def test_accounts_config_is_optional(importer_factory):
    TEST_CONFIG_WITHOUT_ACCOUNTS = b"""
        account: DefaultAccount
        client_id: sandbox-random
        client_secret: deadc0de-dead-c0de-dead-c0dedeadc0de
        refresh_token: 98D124C0E677865CB2F7D9DE91DC394CEED31DA3469C681B41FB7831F2F9B089
        access_token: eyJhbGciOiJSUzI1NiIsImtpZsomethingSomethingsomethingDarkSideOEJBNk
    """

    importer = importer_factory(TEST_CONFIG_WITHOUT_ACCOUNTS)
    assert importer._get_account_for_account_id("any-account-id-1") == "DefaultAccount"
