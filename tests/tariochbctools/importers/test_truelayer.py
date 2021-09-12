import json

import pytest
from beancount.core.amount import Decimal as D

from tariochbctools.importers.truelayer import importer as tlimp

# pylint: disable=protected-access

TEST_CONFIG = b"""
    baseAccount: Liabilities:Other
    client_id: sandbox-random
    client_secret: deadc0de-dead-c0de-dead-c0dedeadc0de
    refresh_token: 98D124C0E677865CB2F7D9DE91DC394CEED31DA3469C681B41FB7831F2F9B089
    access_token: eyJhbGciOiJSUzI1NiIsImtpZsomethingSomethingsomethingDarkSideOEJBNk
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


@pytest.fixture(name="importer")
def truelayer_importer_fixture():
    importer = tlimp.Importer()
    # TODO: _configure the importer
    importer.baseAccount = "Liabilities:Other"
    yield importer


@pytest.fixture(name="tmp_config")
def tmp_config_fixture(tmp_path):
    config = tmp_path / "truelayer.yaml"
    config.write_bytes(TEST_CONFIG)
    yield config


@pytest.fixture(name="tmp_trx")
def tmp_trx_fixture():
    yield json.loads(TEST_TRX)


def test_identify(importer, tmp_config):
    assert importer.identify(tmp_config)


def test_extract_transaction_simple(importer, tmp_trx):
    entries = importer._extract_transaction(
        tmp_trx, "GBP", [tmp_trx], invert_sign=False
    )
    assert entries[0].postings[0].units.number == D(str(tmp_trx["amount"]))


def test_extract_transaction_with_balance(importer, tmp_trx):
    entries = importer._extract_transaction(
        tmp_trx, "GBP", [tmp_trx], invert_sign=False
    )
    # one entry, one balance
    assert len(entries) == 2
    assert entries[1].amount.number == D(str(tmp_trx["running_balance"]["amount"]))


def test_extract_transaction_invert_sign(importer, tmp_trx):
    """Show that sign inversion works"""
    entries = importer._extract_transaction(tmp_trx, "GBP", [tmp_trx], invert_sign=True)
    assert entries[0].postings[0].units.number == -D(str(tmp_trx["amount"]))


@pytest.mark.parametrize("id_field", tlimp.TX_MANDATORY_ID_FIELDS)
def test_extract_transaction_has_transaction_id(importer, tmp_trx, id_field):
    """Ensure mandatory IDs are in extracted transactions."""
    entries = importer._extract_transaction(
        tmp_trx, "GBP", [tmp_trx], invert_sign=False
    )
    assert entries[0].meta[id_field] == tmp_trx[id_field]


@pytest.mark.parametrize("id_field", tlimp.TX_OPTIONAL_ID_FIELDS)
def test_trx_id(importer, tmp_trx, id_field):
    entries = importer._extract_transaction(
        tmp_trx, "GBP", [tmp_trx], invert_sign=False
    )
    assert entries[0].meta[id_field] == tmp_trx[id_field]


@pytest.mark.parametrize("id_field", tlimp.TX_OPTIONAL_ID_FIELDS)
def test_trx_id_is_optional(importer, id_field):
    tmp_trx = json.loads(TEST_TRX_WITHOUT_IDS)
    entries = importer._extract_transaction(
        tmp_trx, "GBP", [tmp_trx], invert_sign=False
    )
    assert entries[0].meta.get(id_field) is None


@pytest.mark.parametrize("id_field", tlimp.TX_OPTIONAL_META_ID_FIELDS)
def test_trx_meta_id(importer, tmp_trx, id_field):
    entries = importer._extract_transaction(
        tmp_trx, "GBP", [tmp_trx], invert_sign=False
    )
    assert entries[0].meta[id_field] == tmp_trx["meta"][id_field]


@pytest.mark.parametrize("id_field", tlimp.TX_OPTIONAL_META_ID_FIELDS)
def test_trx_meta_id_is_optional(importer, id_field):
    tmp_trx = json.loads(TEST_TRX_WITHOUT_IDS)
    entries = importer._extract_transaction(
        tmp_trx, "GBP", [tmp_trx], invert_sign=False
    )
    assert entries[0].meta.get(id_field) is None
