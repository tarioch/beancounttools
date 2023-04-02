import re
from datetime import date
from decimal import Decimal
from os import path

import yaml
from beancount.core import amount, data
from beancount.core.number import D
from beancount.ingest import importer
from ibflex import Types, client, parser
from ibflex.enums import CashAction

from tariochbctools.importers.general.priceLookup import PriceLookup


class Importer(importer.ImporterProtocol):
    """An importer for Interactive Broker using the flex query service."""

    def identify(self, file):
        return "ibkr.yaml" == path.basename(file.name)

    def file_account(self, file):
        return ""

    def matches(self, trx, t, account):
        p = re.compile(r".* (?P<perShare>\d+\.?\d+) PER SHARE")
        trxPerShare = p.search(trx.description).group("perShare")
        tPerShare = p.search(t["description"]).group("perShare")

        return (
            t["date"] == trx.dateTime
            and t["symbol"] == trx.symbol
            and trxPerShare == tPerShare
            and t["account"] == account
        )

    def extract(self, file, existing_entries):
        with open(file.name, "r") as f:
            config = yaml.safe_load(f)
        token = config["token"]
        queryId = config["queryId"]

        priceLookup = PriceLookup(existing_entries, config["baseCcy"])

        response = client.download(token, queryId)
        statement = parser.parse(response)
        assert isinstance(statement, Types.FlexQueryResponse)

        transactions = []
        for stmt in statement.FlexStatements:
            for trx in stmt.CashTransactions:
                existingEntry = None
                if CashAction.DIVIDEND == trx.type or CashAction.WHTAX == trx.type:
                    existingEntry = next(
                        (
                            t
                            for t in transactions
                            if self.matches(trx, t, stmt.accountId)
                        ),
                        None,
                    )

                if existingEntry:
                    if CashAction.WHTAX == trx.type:
                        existingEntry["whAmount"] += trx.amount
                    else:
                        existingEntry["amount"] += trx.amount
                        existingEntry["description"] = trx.description
                        existingEntry["type"] = trx.type
                else:
                    if CashAction.WHTAX == trx.type:
                        amount = 0
                        whAmount = trx.amount
                    else:
                        amount = trx.amount
                        whAmount = 0

                    transactions.append(
                        {
                            "date": trx.dateTime,
                            "symbol": trx.symbol,
                            "currency": trx.currency,
                            "amount": amount,
                            "whAmount": whAmount,
                            "description": trx.description,
                            "type": trx.type,
                            "account": stmt.accountId,
                        }
                    )

            result = []
            for trx in transactions:
                if trx["type"] == CashAction.DIVIDEND:
                    asset = trx["symbol"].rstrip("z")
                    payDate = trx["date"].date()
                    totalDividend = trx["amount"]
                    totalWithholding = -trx["whAmount"]
                    totalPayout = totalDividend - totalWithholding
                    currency = trx["currency"]
                    account = trx["account"]

                    result.append(
                        self.createDividen(
                            totalPayout,
                            totalWithholding,
                            asset,
                            currency,
                            payDate,
                            priceLookup,
                            trx["description"],
                            account,
                        )
                    )

        return result

    def createDividen(
        self,
        payout: Decimal,
        withholding: Decimal,
        asset: str,
        currency: str,
        date: date,
        priceLookup: PriceLookup,
        description: str,
        account: str,
    ):
        narration = "Dividend: " + description
        liquidityAccount = self.getLiquidityAccount(account, currency)
        incomeAccount = self.getIncomeAccount(account)
        assetAccount = self.getAssetAccount(account, asset)

        price = priceLookup.fetchPrice(currency, date)

        postings = [
            data.Posting(
                assetAccount, amount.Amount(D(0), asset), None, None, None, None
            ),
            data.Posting(
                liquidityAccount,
                amount.Amount(payout, currency),
                None,
                price,
                None,
                None,
            ),
        ]
        if withholding > 0:
            receivableAccount = self.getReceivableAccount(account)
            postings.append(
                data.Posting(
                    receivableAccount,
                    amount.Amount(withholding, currency),
                    None,
                    None,
                    None,
                    None,
                )
            )
        postings.append(data.Posting(incomeAccount, None, None, None, None, None))

        meta = data.new_metadata("dividend", 0, {"account": account})
        return data.Transaction(
            meta, date, "*", "", narration, data.EMPTY_SET, data.EMPTY_SET, postings
        )

    def getAssetAccount(self, account: str, asset: str):
        return f"Asset:{account}:Investment:IB:{asset}"

    def getLiquidityAccount(self, account: str, currency: str):
        return f"Asset:{account}:Liquidity:IB:{currency}"

    def getReceivableAccount(self, account: str):
        return f"Assets:{account}:Receivable:Verrechnungssteuer"

    def getIncomeAccount(self, account: str):
        return f"Income:{account}:Interest"
