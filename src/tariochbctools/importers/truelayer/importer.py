import yaml
import dateutil.parser
from datetime import timedelta
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
            transactions = sorted(r.json()['results'], key=lambda trx: trx['timestamp'])
            for trx in transactions:
                metakv = {
                    'tlref': trx['meta']['provider_id'],
                }
                if trx['transaction_classification']:
                    metakv['category'] = trx['transaction_classification'][0]
                meta = data.new_metadata('', 0, metakv)
                trxDate = dateutil.parser.parse(trx['timestamp']).date()
                account = baseAccount + accountCcy
                entry = data.Transaction(
                    meta,
                    trxDate,
                    '*',
                    '',
                    trx['description'],
                    data.EMPTY_SET,
                    data.EMPTY_SET,
                    [
                        data.Posting(account, amount.Amount(D(str(trx['amount'])), trx['currency']), None, None, None, None),
                    ]
                )
                entries.append(entry)

                if trx['transaction_id'] == transactions[-1]['transaction_id']:
                    balDate = trxDate + timedelta(days=1)
                    metakv = {}
                    if existing_entries is not None:
                        for exEntry in existing_entries:
                            if isinstance(exEntry, data.Balance) and exEntry.date == balDate and exEntry.account == account:
                                metakv['__duplicate__'] = True

                    meta = data.new_metadata('', 0, metakv)
                    entries.append(data.Balance(
                        meta,
                        balDate,
                        account,
                        amount.Amount(D(str(trx['running_balance']['amount'])), trx['running_balance']['currency']),
                        None,
                        None,
                    ))

        return entries
