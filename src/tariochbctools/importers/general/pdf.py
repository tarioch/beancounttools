from typing import Any

import camelot


def readFollowingPages(filepath: str, **kwargs: Any) -> camelot.core.TableList:
    """Read the tables from page 2 up to the last page of a PDF.

    Newer camelot versions raise a ValueError for the page range ``2-end`` when the PDF has
    only one page, this returns no tables in that case.
    """
    try:
        return camelot.read_pdf(filepath, pages="2-end", **kwargs)
    except ValueError as e:
        if "out of range" not in str(e):
            raise
        return camelot.core.TableList([])
