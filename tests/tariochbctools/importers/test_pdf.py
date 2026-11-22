from unittest.mock import patch

import pytest

from tariochbctools.importers.general import pdf


def test_following_pages_reads_page_two_to_end():
    with patch.object(pdf.camelot, "read_pdf", return_value=["table"]) as readPdf:
        assert pdf.readFollowingPages("statement.pdf", flavor="stream") == ["table"]

    readPdf.assert_called_once_with("statement.pdf", pages="2-end", flavor="stream")


def test_following_pages_of_single_page_pdf_are_empty():
    error = ValueError(
        "Page 2 is out of range: pages are numbered from 1 and this PDF has 1"
    )
    with patch.object(pdf.camelot, "read_pdf", side_effect=error):
        assert len(pdf.readFollowingPages("statement.pdf")) == 0


def test_following_pages_reraises_other_errors():
    with (
        patch.object(pdf.camelot, "read_pdf", side_effect=ValueError("broken")),
        pytest.raises(ValueError, match="broken"),
    ):
        pdf.readFollowingPages("statement.pdf")
