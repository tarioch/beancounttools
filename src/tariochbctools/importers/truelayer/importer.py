import yaml
import dateutil.parser
from os import path
import requests

from beancount.ingest import importer
from beancount.core import data
from beancount.core import amount
from beancount.core.number import D


class Importer(importer.ImporterProtocol):
    """An importer for Truelayer API (e.g. for Revolut)."""

    def identify(self, file):
        return 'truelayer.yaml' == path.basename(file.name)

    def file_account(self, file):
        return ''

    def extract(self, file, existing_entries):
        with open(file.name, 'r') as f:
            config = yaml.safe_load(f)
        baseAccount = config['baseAccount']
        clientId = config['client_id']
        clientSecret = config['client_secret']
        refreshToken = config['refresh_token']

        r = requests.post('https://auth.truelayer.com/connect/token', data={
            "grant_type": "refresh_token",
            "client_id": clientId,
            "client_secret": clientSecret,
            "refresh_token": refreshToken,
        })
        tokens = r.json()
        accessToken = tokens['access_token']
        headers = {'Authorization': 'Bearer ' + accessToken}

        entries = []
        r = requests.get('https://api.truelayer.com/data/v1/accounts', headers=headers)
        for account in r.json()['results']:
            accountId = account['account_id']
            accountCcy = account['currency']
            r = requests.get(f'https://api.truelayer.com/data/v1/accounts/{accountId}/transactions', headers=headers)
            for trx in r.json()['results']:
                metakv = {
                    'ref': trx['meta']['provider_id'],
                }
                if trx['transaction_classification']:
                    metakv['category'] = trx['transaction_classification'][0]
                meta = data.new_metadata('', 0, metakv)
                entry = data.Transaction(
                    meta,
                    dateutil.parser.parse(trx['timestamp']).date(),
                    '*',
                    '',
                    trx['description'],
                    data.EMPTY_SET,
                    data.EMPTY_SET,
                    [
                        data.Posting(baseAccount + accountCcy, amount.Amount(D(str(trx['amount'])), trx['currency']), None, None, None, None),
                    ]
                )
                entries.append(entry)

        return entries
