import yaml
from os import path
from ibflex import client, parser, Types, enums
from datetime import date

from beancount.query import query
from beancount.parser import options
from beancount.ingest import importer
from beancount.core import data, amount
from beancount.core.number import D

from tariochbctools.importers.general.priceLookup import PriceLookup


class Importer(importer.ImporterProtocol):
    """An importer for Interactive Broker using the flex query service."""

    def identify(self, file):
        return 'ibkr.yaml' == path.basename(file.name)

    def file_account(self, file):
        return ''

    def extract(self, file, existing_entries):
        with open(file.name, 'r') as f:
            config = yaml.safe_load(f)
        token = config['token']
        queryId = config['queryId']

        priceLookup = PriceLookup(existing_entries, config['baseCcy'])

        response = client.download(token, queryId)
        statement = parser.parse(response)
        assert isinstance(statement, Types.FlexQueryResponse)

        result = []
        for divAccrual in statement.FlexStatements[0].ChangeInDividendAccruals:
            if divAccrual.code[0] != enums.Code.REVERSE and divAccrual.payDate <= date.today():
                asset = divAccrual.symbol.replace('z', '')
                exDate = divAccrual.exDate
                payDate = divAccrual.payDate
                totalPayout = divAccrual.netAmount
                totalWithholding = divAccrual.tax
                currency = divAccrual.currency

                _, rows = query.run_query(
                    existing_entries,
                    options.OPTIONS_DEFAULTS,
                    'select sum(number) as quantity, account where currency="' + asset + '" and date<#"' + str(exDate) + '" group by account;')
                totalQuantity = D(0)
                for row in rows:
                    totalQuantity += row.quantity
                if totalQuantity != divAccrual.quantity:
                    raise Exception(f"Different Total Quantities Dividend: {divAccrual.quantity} vs Ours: {totalQuantity}")

                remainingPayout = totalPayout
                remainingWithholding = totalWithholding
                for row in rows[:-1]:
                    myAccount = row.account
                    myQuantity = row.quantity

                    myPayout = round(totalPayout * myQuantity / totalQuantity, 2)
                    remainingPayout -= myPayout
                    myWithholding = round(totalWithholding * myQuantity / totalQuantity, 2)
                    remainingWithholding -= myWithholding
                    result.append(self.createSingle(myPayout, myWithholding, myQuantity, myAccount, asset, currency, payDate, priceLookup))

                lastRow = rows[-1]
                result.append(self.createSingle(remainingPayout, remainingWithholding, lastRow.quantity, lastRow.account, asset, currency, payDate, priceLookup))

        return result

    def createSingle(self, payout, withholding, quantity, assetAccount, asset, currency, date, priceLookup):
        narration = "Dividend for " + str(quantity)
        liquidityAccount = self.getLiquidityAccount(assetAccount, asset, currency)
        incomeAccount = self.getIncomeAccount(assetAccount, asset)

        price = priceLookup.fetchPrice(currency, date)

        postings = [
            data.Posting(assetAccount, amount.Amount(D(0), asset), None, None, None, None),
            data.Posting(liquidityAccount, amount.Amount(payout, currency), None, price, None, None),
        ]
        if withholding > 0:
            receivableAccount = self.getReceivableAccount(assetAccount, asset)
            postings.append(
                data.Posting(receivableAccount, amount.Amount(withholding, currency), None, None, None, None)
            )
        postings.append(
            data.Posting(incomeAccount, None, None, None, None, None)
        )

        meta = data.new_metadata('dividend', 0)
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

    def getLiquidityAccount(self, assetAccount, asset, currency):
        return assetAccount.replace(':Investment:', ':Liquidity:').replace(':' + asset, ':' + currency)

    def getReceivableAccount(self, assetAccount, asset):
        parts = assetAccount.split(':')
        return 'Assets:' + parts[1] + ':Receivable:Verrechnungssteuer'

    def getIncomeAccount(self, assetAccount, asset):
        parts = assetAccount.split(':')
        return 'Income:' + parts[1] + ':Interest'
