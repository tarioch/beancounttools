import json

import pytest
from beancount.core.amount import Decimal as D
from beancount.ingest import cache

from tariochbctools.importers.quickfile import importer as qfimp

# pylint: disable=protected-access

TEST_CONFIG = b"""
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


@pytest.fixture(name="tmp_config")
def tmp_config_fixture(tmp_path):
    config = tmp_path / "quickfile.yaml"
    config.write_bytes(TEST_CONFIG)
    yield cache.get_file(config)  # a FileMemo, not a Path


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
        importer._configure(cache.get_file(config), [])
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
    assert entries[0].postings[0].units.number == D(str(tmp_trx["Amount"]))
