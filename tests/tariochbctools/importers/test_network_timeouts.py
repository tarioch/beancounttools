"""Every network access has a timeout, otherwise a stalled server blocks an import forever."""

from unittest.mock import MagicMock, patch

from tariochbctools.importers.general import mailAdapterImporter
from tariochbctools.importers.general.network import (
    CONNECT_TIMEOUT,
    READ_TIMEOUT,
    REQUEST_TIMEOUT,
)
from tariochbctools.importers.nordigen import importer as nordimp
from tariochbctools.importers.nordigen import nordigen_config
from tariochbctools.importers.quickfile import importer as qfimp
from tariochbctools.importers.transferwise import importer as twimp
from tariochbctools.importers.truelayer import importer as tlimp


def response(payload):
    result = MagicMock()
    result.json.return_value = payload
    return result


def test_timeouts_are_finite():
    assert REQUEST_TIMEOUT == (CONNECT_TIMEOUT, READ_TIMEOUT)
    assert 0 < CONNECT_TIMEOUT < 3600
    assert 0 < READ_TIMEOUT < 3600


def test_nordigen_importer(tmp_path):
    config = tmp_path / "nordigen.yaml"
    config.write_text(
        "secret_id: id\nsecret_key: key\naccounts:\n  - id: acc1\n    asset_account: Assets:Bank\n",
        encoding="utf-8",
    )

    with (
        patch.object(
            nordimp.requests, "post", return_value=response({"access": "tok"})
        ) as post,
        patch.object(
            nordimp.requests,
            "get",
            return_value=response({"transactions": {"booked": []}}),
        ) as get,
    ):
        nordimp.Importer().extract(str(config), [])

    assert post.call_args.kwargs["timeout"] == REQUEST_TIMEOUT
    assert get.call_args.kwargs["timeout"] == REQUEST_TIMEOUT


def test_nordigen_config():
    with patch.object(
        nordigen_config.requests, "post", return_value=response({"access": "tok"})
    ) as post:
        assert nordigen_config.get_token("id", "key") == "tok"

    assert post.call_args.kwargs["timeout"] == REQUEST_TIMEOUT


def test_quickfile():
    quickfile = qfimp.QuickFile("1", "key", "app")

    with patch.object(qfimp.requests, "post", return_value=response({})) as post:
        quickfile._post("bank/search", {})

    assert post.call_args.kwargs["timeout"] == REQUEST_TIMEOUT


def test_truelayer_token_refresh():
    importer = tlimp.Importer()
    importer.accessToken = None
    importer.authCommand = None
    importer.clientId = "client"
    importer.clientSecret = "secret"
    importer.refreshToken = "refresh"

    with patch.object(
        tlimp.requests, "post", return_value=response({"access_token": "tok"})
    ) as post:
        assert importer._get_access_token() == "tok"

    assert post.call_args.kwargs["timeout"] == REQUEST_TIMEOUT


def test_truelayer_endpoint_requests():
    importer = tlimp.Importer()
    importer.config = {"account": "Assets:Bank"}
    responses = [
        response({"results": [{"account_id": "acc1"}]}),
        response({"results": []}),  # balances
        response({"results": []}),  # transactions
    ]

    with patch.object(tlimp.requests, "get", side_effect=responses) as get:
        importer._extract_endpoint_transactions(
            "accounts", {"Authorization": "Bearer tok"}
        )

    assert get.call_count == 3
    assert [call.kwargs["timeout"] for call in get.call_args_list] == [
        REQUEST_TIMEOUT
    ] * 3


def test_transferwise_pool():
    timeout = twimp.http.connection_pool_kw["timeout"]

    assert timeout.connect_timeout == CONNECT_TIMEOUT
    assert timeout.read_timeout == READ_TIMEOUT


def test_mail_adapter(tmp_path):
    config = tmp_path / "mail.yaml"
    config.write_text(
        "host: imap.example.com\nuser: user\npassword: secret\nfolder: INBOX\n",
        encoding="utf-8",
    )

    with patch.object(mailAdapterImporter, "MailBox") as mailbox:
        mailbox.return_value.login.return_value.__enter__.return_value.fetch.return_value = []
        mailAdapterImporter.MailAdapterImporter([]).extract(str(config), [])

    mailbox.assert_called_once_with("imap.example.com", timeout=READ_TIMEOUT)
