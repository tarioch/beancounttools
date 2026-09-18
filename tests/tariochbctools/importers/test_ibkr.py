from unittest.mock import MagicMock, _Call
from urllib.parse import parse_qsl, urlsplit

import pytest
import requests
from ibflex import client

from tariochbctools.importers.ibkr import flexclient

REQUEST_OK = b"""<FlexStatementResponse timestamp="28 August, 2026 09:33 PM EDT">
<Status>Success</Status>
<ReferenceCode>REF123</ReferenceCode>
<Url>https://example.com/GetStatement</Url>
</FlexStatementResponse>"""

REQUEST_ERROR = b"""<FlexStatementResponse timestamp="28 August, 2026 09:33 PM EDT">
<Status>Fail</Status>
<ErrorCode>1015</ErrorCode>
<ErrorMessage>Token is invalid.</ErrorMessage>
</FlexStatementResponse>"""

STATEMENT = b'<FlexQueryResponse queryName="q" type="AF"></FlexQueryResponse>'


def response(content: bytes) -> requests.Response:
    result = requests.Response()
    result._content = content  # pylint: disable=protected-access
    result.status_code = 200
    return result


@pytest.fixture
def get(monkeypatch):
    mock = MagicMock(side_effect=[response(REQUEST_OK), response(STATEMENT)])
    monkeypatch.setattr(requests, "get", mock)
    return mock


def sentQuery(call: _Call) -> tuple[str, dict[str, str]]:
    """The endpoint and query as requests would really send them."""
    prepared = requests.Request(
        "GET", call.args[0], params=call.kwargs["params"]
    ).prepare()
    assert prepared.url
    url = urlsplit(str(prepared.url))
    return url.path.rsplit("/", 1)[-1], dict(parse_qsl(url.query))


def test_download_sends_period_with_statement_request(get):
    assert flexclient.download("tok", "123", period=90) == STATEMENT

    request, poll = get.call_args_list
    assert sentQuery(request) == (
        "SendRequest",
        {"v": "3", "t": "tok", "q": "123", "p": "90"},
    )
    assert sentQuery(poll) == (
        "GetStatement",
        {"v": "3", "t": "tok", "q": "REF123"},
    )


def test_download_without_period_is_plain_ibflex(get):
    assert flexclient.download("tok", "123") == STATEMENT

    request, _ = get.call_args_list
    assert sentQuery(request) == (
        "SendRequest",
        {"v": "3", "t": "tok", "q": "123"},
    )


def test_download_restores_request_url(get):
    original = client.REQUEST_URL

    flexclient.download("tok", "123", period=90)

    assert client.REQUEST_URL == original


def test_download_restores_request_url_on_error(get):
    original = client.REQUEST_URL
    get.side_effect = [response(REQUEST_ERROR)]

    with pytest.raises(client.ResponseCodeError, match="Token is invalid"):
        flexclient.download("tok", "123", period=90)

    assert client.REQUEST_URL == original


def test_download_rejects_non_numeric_period(get):
    with pytest.raises(ValueError):
        flexclient.download("tok", "123", period="90&x=1")  # type: ignore[arg-type]

    get.assert_not_called()
