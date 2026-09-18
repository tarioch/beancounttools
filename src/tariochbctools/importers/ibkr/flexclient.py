"""Flex query download with support for the `period` override.

ibflex up to 1.1 (latest release) has no way to pass `period` to client.download().
The statement request is sent to client.REQUEST_URL and requests merges a query string in the url
with the other params, so the period is added to that url for the duration of the download.
Can be replaced by client.download(token, queryId, period=period) once a newer ibflex is released.
"""

from ibflex import client


def download(
    token: str, queryId: str, max_tries: int | None = 5, period: int | None = None
) -> bytes:
    if period is None:
        return client.download(token, queryId, max_tries)

    requestUrl = client.REQUEST_URL
    client.REQUEST_URL = f"{requestUrl}?p={int(period)}"
    try:
        return client.download(token, queryId, max_tries)
    finally:
        client.REQUEST_URL = requestUrl
