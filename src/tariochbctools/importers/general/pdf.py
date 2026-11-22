from typing import Any

import camelot
from pypdf import PdfReader


def readFollowingPages(filepath: str, **kwargs: Any) -> camelot.core.TableList:
    """Read the tables from page 2 up to the last page of a PDF.

    Newer camelot versions raise a ValueError for the page range ``2-end`` when the PDF has
    only one page, this returns no tables in that case.
    """
    if len(PdfReader(filepath).pages) < 2:
        return camelot.core.TableList([])
    return camelot.read_pdf(filepath, pages="2-end", **kwargs)
