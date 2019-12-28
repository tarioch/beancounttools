from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from datetime import date

import yaml
from os import path

import bitstamp.client

from beancount.core.number import MISSING

from beancount.ingest import importer
from beancount.core import data
from beancount.core import amount
from beancount.core.number import D
from tariochbctools.importers.general.priceLookup import PriceLookup


class Importer(importer.ImporterProtocol):
    """An importer for Bitstamp."""

    def identify(self, file):
        return 'bitstamp.yaml' == path.basename(file.name)

    def file_account(self, file):
        return ''

    def extract(self, file, existing_entries):
        self.priceLookup = PriceLookup(existing_entries, 'CHF')

        config = yaml.safe_load(file.contents())
        self.config = config
        self.client = bitstamp.client.Trading(
            username=config['username'],
            key=config['key'],
            secret=config['secret'])
        self.currencies = config['currencies']
        self.account = config['account']
        self.otherExpensesAccount = config['otherExpensesAccount']
        self.capGainAccount = config['capGainAccount']

        dateCutoff = date.today() + relativedelta(months=-config['monthCutoff'])

        trxs = self.client.user_transactions()
        trxs.reverse()
        result = []
        for trx in trxs:
            entry = self.fetchSingle(trx)
            if entry.date > dateCutoff:
                result.append(entry)

        return result

    def fetchSingle(self, trx):
        id = int(trx['id'])
        type = int(trx['type'])
        date = parse(trx['datetime']).date()

        posAmt = 0
        posCcy = None
        negAmt = 0
        negCcy = None
        for ccy in self.currencies:
            if ccy in trx:
                amt = D(trx[ccy])
                if amt > 0:
                    posAmt = amt
                    posCcy = ccy.upper()
                elif amt < 0:
                    negAmt = amt
                    negCcy = ccy.upper()

        if type == 0:
            narration = 'Deposit'
            cost = data.Cost(
                self.priceLookup.fetchPriceAmount(posCcy, date),
                'CHF',
                None,
                None
            )
            postings = [
                data.Posting(self.account + ':' + posCcy, amount.Amount(posAmt, posCcy), cost, None, None, None),
            ]
        elif type == 1:
            narration = 'Withdrawal'
            postings = [
                data.Posting(self.account + ':' + negCcy, amount.Amount(negAmt, negCcy), None, None, None, None),
            ]
        elif type == 2:
            fee = D(trx['fee'])
            if posCcy.lower() + '_' + negCcy.lower() in trx:
                feeCcy = negCcy
                negAmt -= fee
            else:
                feeCcy = posCcy
                posAmt -= fee

            rateFiatCcy = self.priceLookup.fetchPriceAmount(feeCcy, date)
            if feeCcy == posCcy:
                posCcyCost = None
                posCcyPrice = amount.Amount(rateFiatCcy, 'CHF')
                negCcyCost = data.CostSpec(
                    MISSING,
                    None,
                    MISSING,
                    None,
                    None,
                    False
                )
                negCcyPrice = None
            else:
                posCcyCost = data.CostSpec(
                    None,
                    D(-negAmt * rateFiatCcy),
                    'CHF',
                    None,
                    None,
                    False
                )
                posCcyPrice = None
                negCcyCost = None
                negCcyPrice = amount.Amount(rateFiatCcy, 'CHF')

            narration = 'Trade'

            postings = [
                data.Posting(self.account + ':' + posCcy, amount.Amount(posAmt, posCcy), posCcyCost, posCcyPrice, None, None),
                data.Posting(self.account + ':' + negCcy, amount.Amount(negAmt, negCcy), negCcyCost, negCcyPrice, None, None)
            ]
            if float(fee) > 0:
                postings.append(
                    data.Posting(self.otherExpensesAccount, amount.Amount(round(fee * rateFiatCcy, 2), 'CHF'), None, None, None, None)
                )
            postings.append(
                data.Posting(self.capGainAccount, None, None, None, None, None)
            )

        else:
            raise ValueError('Transaction type ' + str(type) + ' is not handled')

        meta = data.new_metadata('bitstamp', id, {'ref': str(id)})
        return data.Transaction(
            meta,
            date,
            '*',
            '',
            narration,
            data.EMPTY_SET,
            data.EMPTY_SET,
            postings
        )
