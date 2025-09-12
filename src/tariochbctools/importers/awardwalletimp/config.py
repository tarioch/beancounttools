import argparse
import sys
import uuid
from typing import Any

import yaml
from awardwallet import AwardWalletClient
from awardwallet.client import AccessLevel


def get_link_url(client):
    connection_url = client.get_connection_link(
        platform="desktop",
        access_level=AccessLevel.READ_ALL_EXCEPT_PASSWORDS,
        state=str(uuid.uuid4()),
    )
    print(  # noqa: T201
        "Redirect your user to this URL to authorize the connection."
        "\nThis link expires in 10 minutes:"
    )
    print(connection_url)  # noqa: T201


def generate(client):
    """
    Generate a config for a user including user_id and account_id list.
    Output in yaml format.
    """
    config = {}
    config["api_key"] = client.api_key
    config["users"] = {}

    connected_users = client.list_connected_users()

    for user in connected_users:
        user_details = client.get_connected_user_details(user.user_id)
        account_config = {}

        for account in user_details.accounts:
            account_config[account.account_id] = {
                "provider": account.display_name,
                "account": "Assets:Current:Points",  # Placeholder, user should adjust
                "currency": "POINTS",
            }

        config["users"][user.user_id] = {
            "name": user.user_name,
            "all_history": False,
            "accounts": account_config,
        }

    yaml.dump(config, sys.stdout, sort_keys=False)


def parse_args(args: Any) -> Any:
    parser = argparse.ArgumentParser(description="awardwallet-config")
    sub_parsers = parser.add_subparsers(dest="mode", required=True)

    parser.add_argument(
        "--api-key",
        required=True,
        help="API key, can be generated on AwardWallet Business interface",
    )

    sub_parsers.add_parser(
        "get_link_url", help="Generate a connection link URL for user authorization"
    )
    sub_parsers.add_parser(
        "generate", help="Generate a configuration template for connected users"
    )

    return parser.parse_args(args)


def main(args: Any) -> None:
    args = parse_args(args)

    client = AwardWalletClient(args.api_key)

    if args.mode == "get_link_url":
        get_link_url(client)
    elif args.mode == "generate":
        generate(client)


def run() -> None:
    """Entry point for console_scripts"""
    main(sys.argv[1:])


if __name__ == "__main__":
    main(sys.argv[1:])
