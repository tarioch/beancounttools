import argparse
import sys

import requests


def build_header(token):
    return {"Authorization": "Bearer " + token}


def check_result(result):
    try:
        result.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise Exception(e, e.response.text)


def get_token(secret_id, secret_key):
    r = requests.post(
        "https://ob.nordigen.com/api/v2/token/new/",
        data={
            "secret_id": secret_id,
            "secret_key": secret_key,
        },
    )
    check_result(r)

    return r.json()["access"]


def list_bank(token, country):
    r = requests.get(
        "https://ob.nordigen.com/api/v2/institutions/",
        params={"country": country},
        headers=build_header(token),
    )
    check_result(r)

    for asp in r.json():
        print(asp["name"] + ": " + asp["id"])  # noqa: T201


def create_link(token, reference, bank):
    if not bank:
        raise Exception("Please specify --bank it is required for create_link")
    requisitionId = _find_requisition_id(token, reference)
    if requisitionId:
        print(f"Link for for reference {reference} already exists.")  # noqa: T201
    else:
        r = requests.post(
            "https://ob.nordigen.com/api/v2/requisitions/",
            data={
                "redirect": "http://localhost",
                "institution_id": bank,
                "reference": reference,
            },
            headers=build_header(token),
        )
        check_result(r)
        link = r.json()["link"]
        print(f"Go to {link} for connecting to your bank.")  # noqa: T201


def list_accounts(token):
    headers = build_header(token)
    r = requests.get("https://ob.nordigen.com/api/v2/requisitions/", headers=headers)
    print(r.json())  # noqa: T201
    check_result(r)
    for req in r.json()["results"]:
        reference = req["reference"]
        print(f"Reference: {reference}")  # noqa: T201
        for account in req["accounts"]:
            ra = requests.get(
                f"https://ob.nordigen.com/api/v2/accounts/{account}", headers=headers
            )
            check_result(ra)
            acc = ra.json()
            asp = acc["institution_id"]
            iban = acc["iban"]

            ra = requests.get(
                f"https://ob.nordigen.com/api/v2/accounts/{account}/details",
                headers=headers,
            )
            check_result(ra)
            accDetails = ra.json()["account"]

            currency = accDetails["currency"]
            owner = accDetails["ownerName"] if "ownerName" in accDetails else "-"
            print(f"{account}: {asp} {owner} {iban} {currency}")  # noqa: T201


def delete_link(token, reference):
    requisitionId = _find_requisition_id(token, reference)
    if requisitionId:
        r = requests.delete(
            f"https://ob.nordigen.com/api/v2/requisitions/{requisitionId}",
            headers=build_header(token),
        )
        check_result(r)


def _find_requisition_id(token, userId):
    headers = build_header(token)
    r = requests.get("https://ob.nordigen.com/api/v2/requisitions/", headers=headers)
    check_result(r)
    for req in r.json()["results"]:
        if req["reference"] == userId:
            return req["id"]

    return None


def parse_args(args):
    parser = argparse.ArgumentParser(description="nordigen-config")
    parser.add_argument(
        "--secret_id",
        required=True,
        help="API secret id, can be generated on Nordigen website",
    )
    parser.add_argument(
        "--secret_key",
        required=True,
        help="API secret key, can be generated on Nordigen website",
    )
    parser.add_argument(
        "--country",
        default="GB",
        help="Country Code for list_bank",
    )
    parser.add_argument(
        "--reference",
        default="beancount",
        help="reference for add_bank and delete_bank, needs to be unique",
    )
    parser.add_argument(
        "--bank",
        help="Bank to connect to, see list_banks",
    )
    parser.add_argument(
        "mode",
        choices=[
            "list_banks",
            "create_link",
            "list_accounts",
            "delete_link",
        ],
    )
    return parser.parse_args(args)


def main(args):
    args = parse_args(args)

    token = get_token(args.secret_id, args.secret_key)

    if args.mode == "list_banks":
        list_bank(token, args.country)
    elif args.mode == "create_link":
        create_link(token, args.reference, args.bank)
    elif args.mode == "list_accounts":
        list_accounts(token)
    elif args.mode == "delete_link":
        delete_link(token, args.reference)


def run():
    """Entry point for console_scripts"""
    main(sys.argv[1:])
