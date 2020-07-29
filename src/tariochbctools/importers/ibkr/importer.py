import yaml
import re
from os import path
from ibflex import client, parser, Types
from ibflex.enums import CashAction

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

    def matches(self, trx, t):
        p = re.compile(r'.* (?P<perShare>\d+\.?\d+) PER SHARE')
        trxPerShare = p.search(trx.description).group('perShare')
        tPerShare = p.search(t['description']).group('perShare')

        return t['date'] == trx.dateTime and t['symbol'] == trx.symbol and trxPerShare == tPerShare

    def extract(self, file, existing_entries):
        with open(file.name, 'r') as f:
            config = yaml.safe_load(f)
        token = config['token']
        queryId = config['queryId']

        priceLookup = PriceLookup(existing_entries, config['baseCcy'])

        response = client.download(token, queryId)
        statement = parser.parse(response)
        assert isinstance(statement, Types.FlexQueryResponse)

        transactions = []
        for trx in statement.FlexStatements[0].CashTransactions:
            existingEntry = None
            if CashAction.DIVIDEND == trx.type or CashAction.WHTAX == trx.type:
                existingEntry = next((t for t in transactions if self.matches(trx, t)), None)

            if existingEntry:
                if CashAction.WHTAX == trx.type:
                    existingEntry['whAmount'] += trx.amount
                else:
                    existingEntry['amount'] += trx.amount
                    existingEntry['description'] = trx.description
                    existingEntry['type'] = trx.type
            else:
                if CashAction.WHTAX == trx.type:
                    amount = 0
                    whAmount = trx.amount
                else:
                    amount = trx.amount
                    whAmount = 0

                transactions.append({
                    'date': trx.dateTime,
                    'symbol': trx.symbol,
                    'currency': trx.currency,
                    'amount': amount,
                    'whAmount': whAmount,
                    'description': trx.description,
                    'type': trx.type
                })

        result = []
        for trx in transactions:
            if trx['type'] == CashAction.DIVIDEND:
                asset = trx['symbol'].rstrip('z')
                payDate = trx['date'].date()
                totalDividend = trx['amount']
                totalWithholding = -trx['whAmount']
                totalPayout = totalDividend - totalWithholding
                currency = trx['currency']

                _, rows = query.run_query(
                    existing_entries,
                    options.OPTIONS_DEFAULTS,
                    'select sum(number) as quantity, account where currency="' + asset + '" and date<#"' + str(payDate) + '" group by account;')
                totalQuantity = D(0)
                for row in rows:
                    totalQuantity += row.quantity

                remainingPayout = totalPayout
                remainingWithholding = totalWithholding
                for row in rows[:-1]:
                    myAccount = row.account
                    myQuantity = row.quantity

                    myPayout = round(totalPayout * myQuantity / totalQuantity, 2)
                    remainingPayout -= myPayout
                    myWithholding = round(totalWithholding * myQuantity / totalQuantity, 2)
                    remainingWithholding -= myWithholding
                    result.append(self.createSingle(myPayout, myWithholding, myQuantity, myAccount, asset, currency, payDate, priceLookup, trx['description']))

                lastRow = rows[-1]
                result.append(self.createSingle(remainingPayout, remainingWithholding, lastRow.quantity, lastRow.account, asset, currency, payDate, priceLookup, trx['description']))

        return result

    def createSingle(self, payout, withholding, quantity, assetAccount, asset, currency, date, priceLookup, description):
        narration = "Dividend for " + str(quantity) + " : " + description
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
