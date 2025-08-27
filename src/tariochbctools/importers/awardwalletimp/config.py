import argparse
import json
import sys
import uuid
from typing import Any

import yaml
from awardwallet.api import (
    AccessLevel,
    AwardWalletAPI,
    ProviderKind,
)


def list_users(client):
    connected_users = client.list_connected_users()
    users = {}
    for user in connected_users:
        users[user["userId"]] = user["userName"]

    yaml.dump(users, sys.stdout, sort_keys=False)


def account_details(client, account_id):
    account_details = client.get_account_details(account_id)
    print(json.dumps(account_details, indent=2))  # noqa: T201


def get_link_url(client):
    connection_url = client.get_connection_link(
        platform="desktop",
        access_level=AccessLevel.READ_ALL_EXCEPT_PASSWORDS,
        state=str(uuid.uuid4()),
    )
    print(  # noqa: T201
        "Redirect your user to this URL to authorize the connection (expires in 10 minutes):"
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
        user_id = user["userId"]
        user_details = client.get_connected_user_details(user_id)
        account_config = {}

        for account in user_details.get("accounts", []):
            account_config[account["accountId"]] = {
                "provider": account["displayName"],
                "account": "Assets:Current:Points",  # Placeholder, user should adjust
                "currency": "POINTS",
            }

        config["users"][user_id] = {
            "name": user["userName"],
            "all_history": False,
            "accounts": account_config,
        }

    yaml.dump(config, sys.stdout, sort_keys=False)


def list_providers(client):
    providers = client.list_providers()

    providers_filtered = {
        p["code"]: {
            "displayName": p["displayName"],
            "kind": ProviderKind(p["kind"]).name,
        }
        for p in sorted(providers, key=lambda d: d["displayName"])
    }

    yaml.dump(providers_filtered, sys.stdout, sort_keys=False, allow_unicode=True)


def parse_args(args: Any) -> Any:
    parser = argparse.ArgumentParser(description="awardwallet-config")
    parser.add_argument(
        "--api-key",
        required=True,
        help="API key, can be generated on AwardWallet Business interface",
    )
    parser.add_argument(
        "--account-id",
        required=False,
        help="Account ID for account-specific operations",
    )
    parser.add_argument(
        "mode",
        choices=[
            "get_link_url",
            "generate",
            "list_providers",
            "list_users",
            "account_details",
        ],
    )
    return parser.parse_args(args)


def main(args: Any) -> None:
    args = parse_args(args)

    client = AwardWalletAPI(args.api_key)

    if args.mode == "get_link_url":
        get_link_url(client)
    elif args.mode == "generate":
        generate(client)
    elif args.mode == "list_providers":
        list_providers(client)
    elif args.mode == "list_users":
        list_users(client)
    elif args.mode == "account_details":
        account_details(client, args.account_id)


def run() -> None:
    """Entry point for console_scripts"""
    main(sys.argv[1:])


if __name__ == "__main__":
    main(sys.argv[1:])
