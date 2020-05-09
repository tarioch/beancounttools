import os
from io import StringIO
from beancount.parser import printer
from beancount import loader
import pytest


@pytest.mark.parametrize("testCase", [
    "normal",
    "missing_fx",
    "entry_already_exists"
])
def test_data(testCase):
    dataDir = os.path.join(
        os.path.dirname(__file__), "data", "generate_base_ccy_prices"
    )
    inputPath = os.path.join(dataDir, testCase + "_input.beancount")
    expectedPath = os.path.join(dataDir, testCase + "_expected.beancount")

    entries, errors, _ = loader.load_file(inputPath)
    if errors:
        printer.print_errors(errors)
        assert False

    actualStrIo = StringIO()
    printer.print_entries(entries, file=actualStrIo)
    actual = actualStrIo.getvalue()

    if os.path.isfile(expectedPath):
        with open(expectedPath, 'r') as expectedFile:
            expected = expectedFile.read()
            assert actual == expected
    else:
        with open(expectedPath, 'w') as expectedFile:
            expectedFile.write(actual)
