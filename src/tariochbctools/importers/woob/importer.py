import yaml
from os import path

from beancount.ingest import importer
from beancount.core import data
from beancount.core import amount

from woob.core import Woob
from woob.capabilities.bank import CapBank


class Importer(importer.ImporterProtocol):
    """An importer using woob for accessing statements."""

    def identify(self, file):
        return 'woob.yaml' == path.basename(file.name)

    def file_account(self, file):
        return ''

    def extract(self, file, existing_entries):
        with open(file.name, 'r') as f:
            config = yaml.safe_load(f)

        configDir = path.dirname(file.name)

        if 'workdir' in config:
            workdir = path.normpath(path.join(configDir, config['workdir']))
        else:
            workdir = None

        if 'datadir' in config:
            datadir = path.normpath(path.join(configDir, config['datadir']))
        else:
            datadir = None

        try:
            w = Woob(workdir=workdir, datadir=datadir)
            w.load_backends(CapBank)

            entries = []
            for account in config['accounts']:
                assetAccount = account['asset_account']
                woobAccount = next(iter(w.get_account(account['account'])))
                for trx in w.iter_history(woobAccount):
                    meta = data.new_metadata('', 0, {
                        'woobref': trx.unique_id()
                    })
                    entry = data.Transaction(
                        meta,
                        trx.date,
                        '*',
                        '',
                        trx.label,
                        data.EMPTY_SET,
                        data.EMPTY_SET,
                        [
                            data.Posting(assetAccount, amount.Amount(trx.amount, woobAccount.currency), None, None, None, None),
                        ]
                    )
                    entries.append(entry)
        finally:
            w.deinit()

        return entries
