from unittest.mock import MagicMock, patch

from tariochbctools.importers.general import pdf


def readFollowingPages(pageCount: int):
    with (
        patch.object(pdf, "PdfReader", return_value=MagicMock(pages=[0] * pageCount)),
        patch.object(pdf.camelot, "read_pdf", return_value=["table"]) as readPdf,
    ):
        tables = pdf.readFollowingPages("statement.pdf", flavor="stream")
    return tables, readPdf


def test_following_pages_reads_page_two_to_end():
    tables, readPdf = readFollowingPages(3)

    assert tables == ["table"]
    readPdf.assert_called_once_with("statement.pdf", pages="2-end", flavor="stream")


def test_following_pages_of_single_page_pdf_are_empty():
    tables, readPdf = readFollowingPages(1)

    assert len(tables) == 0
    readPdf.assert_not_called()
