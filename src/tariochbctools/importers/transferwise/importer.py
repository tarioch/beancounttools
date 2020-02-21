import yaml
from datetime import date, datetime, timezone
import dateutil.parser
from dateutil.relativedelta import relativedelta
from os import path
import requests

from beancount.ingest import importer
from beancount.core import data
from beancount.core import amount
from beancount.core.number import D


class Importer(importer.ImporterProtocol):
    """An importer for Transferwise using the API."""

    def identify(self, file):
        return 'transferwise.yaml' == path.basename(file.name)

    def file_account(self, file):
        return ''

    def extract(self, file, existing_entries):
        with open(file.name, 'r') as f:
            config = yaml.safe_load(f)
        token = config['token']
        baseAccount = config['baseAccount']
        startDate = datetime.combine(date.today() + relativedelta(months=-3), datetime.min.time(), timezone.utc).isoformat()
        endDate = datetime.combine(date.today(), datetime.max.time(), timezone.utc).isoformat()

        headers = {'Authorization': 'Bearer ' + token}
        r = requests.get('https://api.transferwise.com/v1/profiles', headers=headers)
        profiles = r.json()
        profileId = profiles[0]['id']

        r = requests.get('https://api.transferwise.com/v1/borderless-accounts', params={'profileId': profileId}, headers=headers)
        accounts = r.json()
        accountId = accounts[0]['id']

        entries = []
        for account in accounts[0]['balances']:
            accountCcy = account['currency']

            r = requests.get(f"https://api.transferwise.com/v3/profiles/{profileId}/borderless-accounts/{accountId}/statement.json", params={'currency': accountCcy, 'intervalStart': startDate, 'intervalEnd': endDate}, headers=headers)
            transactions = r.json()

            for transaction in transactions['transactions']:
                metakv = {
                    'ref': transaction['referenceNumber'],
                }
                meta = data.new_metadata('', 0, metakv)
                entry = data.Transaction(
                    meta,
                    dateutil.parser.parse(transaction['date']).date(),
                    '*',
                    '',
                    transaction['details']['description'],
                    data.EMPTY_SET,
                    data.EMPTY_SET,
                    [
                        data.Posting(baseAccount + accountCcy, amount.Amount(D(str(transaction['amount']['value'])), transaction['amount']['currency']), None, None, None, None),
                    ]
                )
                entries.append(entry)

        return entries
