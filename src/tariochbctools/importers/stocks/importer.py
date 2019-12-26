from dateutil.parser import parse
import yaml
from os import path

from beancount.ingest import importer
from beancount.core import data
from beancount.core import amount
from beancount.core.number import D
from beancount.query import query
from beancount.parser import options


class DividendImporter(importer.ImporterProtocol):
    """An importer for Dividend payments."""

    def identify(self, file):
        return 'dividend.yaml' == path.basename(file.name)

    def file_account(self, file):
        return ''

    def extract(self, file, existing_entries):
        config = yaml.safe_load(file.contents())
        self.config = config

        asset = input('Enter the asset:')
        date = input('Enter the date:')
        totalPayout = D(input('Enter the payout amount:'))
        totalWithholding = D(input('Enter the witholding amount:'))

        _, rows = query.run_query(
            existing_entries,
            options.OPTIONS_DEFAULTS,
            'select sum(number) as quantity, account where currency="' + asset + '" and date<=#"' + date + '" group by account;')
        totalQuantity = D(0)
        for row in rows:
            totalQuantity += row.quantity

        result = []
        remainingPayout = totalPayout
        remainingWithholding = totalWithholding
        for row in rows[:-1]:
            myAccount = row.account
            myQuantity = row.quantity

            myPayout = round(totalPayout * myQuantity / totalQuantity, 2)
            remainingPayout -= myPayout
            myWithholding = round(totalWithholding * myQuantity / totalQuantity, 2)
            remainingWithholding -= myWithholding
            result.append(self.createSingle(myPayout, myWithholding, myQuantity, myAccount, asset, date))

        lastRow = rows[-1]
        result.append(self.createSingle(remainingPayout, remainingWithholding, lastRow.quantity, lastRow.account, asset, date))

        return result

    def createSingle(self, payout, withholding, quantity, assetAccount, asset, date):
        narration = "Dividend for " + str(quantity)
        liquidityAccount = self.getLiquidityAccount(assetAccount, asset)
        incomeAccount = self.getIncomeAccount(assetAccount, asset)

        postings = [
            data.Posting(assetAccount, amount.Amount(D(0), asset), None, None, None, None),
            data.Posting(liquidityAccount, amount.Amount(payout, 'CHF'), None, None, None, None),
        ]
        if withholding > 0:
            receivableAccount = self.getReceivableAccount(assetAccount, asset)
            postings.append(
                data.Posting(receivableAccount, amount.Amount(withholding, 'CHF'), None, None, None, None)
            )
        postings.append(
            data.Posting(incomeAccount, None, None, None, None, None)
        )

        meta = data.new_metadata('dividend', 0)
        return data.Transaction(
            meta,
            parse(date).date(),
            '*',
            '',
            narration,
            data.EMPTY_SET,
            data.EMPTY_SET,
            postings
        )

    def getLiquidityAccount(self, assetAccount, asset):
        return assetAccount.replace(':Investment:', ':Liquidity:').replace(':' + asset, ':CHF')

    def getReceivableAccount(self, assetAccount, asset):
        parts = assetAccount.split(':')
        return 'Assets:' + parts[1] + ':Receivable:Verrechnungssteuer'

    def getIncomeAccount(self, assetAccount, asset):
        parts = assetAccount.split(':')
        return 'Income:' + parts[1] + ':Interest'
