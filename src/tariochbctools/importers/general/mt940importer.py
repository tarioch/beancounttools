from beancount.ingest import importer
from beancount.core import data
from beancount.core import amount
from beancount.core.number import D
from beancount.ingest.importers.mixins import identifier

import mt940


class Importer(identifier.IdentifyMixin, importer.ImporterProtocol):
    """An importer for MT940 files."""

    def __init__(self, regexps, account):
        identifier.IdentifyMixin.__init__(self, matchers=[
            ('filename', regexps)
        ])
        self.account = account

    def identify(self, file):
        if file.mimetype() != 'text/plain':
            return False

        return super().identify(file)

    def file_account(self, file):
        return self.account

    def extract(self, file, existing_entries):
        entries = []
        transactions = mt940.parse(file.contents())
        for trx in transactions:
            trxdata = trx.data
            ref = trxdata['bank_reference']
            if ref:
                metakv = {'ref': ref}
            else:
                metakv = None
            meta = data.new_metadata(file.name, 0, metakv)
            if 'entry_date' in trxdata:
                date = trxdata['entry_date']
            else:
                date = trxdata['date']
            entry = data.Transaction(
                meta,
                date,
                '*',
                self.prepare_payee(trxdata),
                self.prepare_narration(trxdata),
                data.EMPTY_SET,
                data.EMPTY_SET,
                [
                    data.Posting(self.account, amount.Amount(D(trxdata['amount'].amount), trxdata['amount'].currency), None, None, None, None),
                ]
            )
            entries.append(entry)

        return entries

    def prepare_payee(self, trxdata):
        return ''

    def prepare_narration(self, trxdata):
        return trxdata['transaction_details'] + ' ' + trxdata['extra_details']
