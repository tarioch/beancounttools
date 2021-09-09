import argparse
import requests
import sys


def build_header(token):
    return {'Authorization': 'Token ' + token}


def check_result(result):
    try:
        result.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise Exception(e, e.response.text)


def list_bank(token, country):
    r = requests.get('https://ob.nordigen.com/api/aspsps/', params={'country': country}, headers=build_header(token))
    check_result(r)

    for asp in r.json():
        print(asp['name'] + ': ' + asp['id'])


def create_link(token, userId, bank):
    if not bank:
        raise Exception('Please specify --bank it is required for create_link')
    headers = build_header(token)
    requisitionId = _find_requisition_id(token, userId)
    if not requisitionId:
        r = requests.post('https://ob.nordigen.com/api/requisitions/', data={
            'redirect': 'http://localhost',
            'enduser_id': userId,
            'reference': userId,
        }, headers=build_header(token))
        check_result(r)
        requisitionId = r.json()['id']

    r = requests.post(f'https://ob.nordigen.com/api/requisitions/{requisitionId}/links/', data={'aspsp_id': bank}, headers=headers)
    check_result(r)
    link = r.json()['initiate']
    print(f'Go to {link} for connecting to your bank.')


def list_accounts(token):
    headers = build_header(token)
    r = requests.get('https://ob.nordigen.com/api/requisitions/', headers=headers)
    check_result(r)
    for req in r.json()['results']:
        print(req['enduser_id'] + ': ' + req['id'])
        for account in req['accounts']:
            ra = requests.get(f'https://ob.nordigen.com/api/accounts/{account}', headers=headers)
            check_result(ra)
            acc = ra.json()
            asp = acc['aspsp_identifier']
            iban = acc['iban']

            ra = requests.get(f'https://ob.nordigen.com/api/accounts/{account}/details', headers=headers)
            check_result(ra)
            accDetails = ra.json()['account']

            currency = accDetails['currency']
            owner = accDetails['ownerName'] if 'ownerName' in accDetails else '-'
            print(f'{account}: {asp} {owner} {iban} {currency}')


def delete_user(token, userId):
    requisitionId = _find_requisition_id(token, userId)
    if requisitionId:
        r = requests.delete(f'https://ob.nordigen.com/api/requisitions/{requisitionId}', headers=build_header(token))
        check_result(r)


def _find_requisition_id(token, userId):
    headers = build_header(token)
    r = requests.get('https://ob.nordigen.com/api/requisitions/', headers=headers)
    check_result(r)
    for req in r.json()['results']:
        if req['enduser_id'] == userId:
            return req['id']

    return None


def parse_args(args):
    parser = argparse.ArgumentParser(
        description="nordigen-config"
    )
    parser.add_argument(
        '--token',
        required=True,
        help='API Token, can be generated on Nordigen website',
    )
    parser.add_argument(
        '--country',
        default='GB',
        help='Country Code for list_bank',
    )
    parser.add_argument(
        '--userId',
        default='beancount',
        help='UserId for create_link and delete_user',
    )
    parser.add_argument(
        '--bank',
        help='Bank to connect to, see list_banks',
    )
    parser.add_argument(
        'mode',
        choices=[
            'list_banks',
            'create_link',
            'list_accounts',
            'delete_user',
        ],
    )
    return parser.parse_args(args)


def main(args):
    args = parse_args(args)

    if args.mode == 'list_banks':
        list_bank(args.token, args.country)
    elif args.mode == 'create_link':
        create_link(args.token, args.userId, args.bank)
    elif args.mode == 'list_accounts':
        list_accounts(args.token)
    elif args.mode == 'delete_user':
        delete_user(args.token, args.userId)


def run():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])
