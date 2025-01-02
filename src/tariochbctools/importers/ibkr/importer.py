import re
from datetime import date
from decimal import Decimal
from os import path
from typing import Any

import beangulp
import yaml
from beancount.core import amount, data
from beancount.core.number import D
from ibflex import Types, client, parser
from ibflex.enums import CashAction

from tariochbctools.importers.general.priceLookup import PriceLookup


class Importer(beangulp.Importer):
    """An importer for Interactive Broker using the flex query service."""

    def identify(self, filepath: str) -> bool:
        return path.basename(filepath).endswith("ibkr.yaml")

    def account(self, filepath: str) -> data.Account:
        return ""

    def matches(
        self, trx: Types.CashTransaction, t: Any, account: data.Account
    ) -> bool:
        p = re.compile(r".* (?P<perShare>\d+\.?\d+) PER SHARE")

        trxPerShareGroups = p.search(trx.description)
        tPerShareGroups = p.search(t["description"])

        trxPerShare = trxPerShareGroups.group("perShare") if trxPerShareGroups else ""
        tPerShare = tPerShareGroups.group("perShare") if tPerShareGroups else ""

        return (
            t["date"] == trx.dateTime
            and t["symbol"] == trx.symbol
            and trxPerShare == tPerShare
            and t["account"] == account
        )

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        with open(filepath, "r") as f:
            config = yaml.safe_load(f)
        token = config["token"]
        queryId = config["queryId"]

        priceLookup = PriceLookup(existing, config["baseCcy"])

        response = client.download(token, queryId)
        statement = parser.parse(response)
        assert isinstance(statement, Types.FlexQueryResponse)

        result = []
        for stmt in statement.FlexStatements:
            transactions: list = []
            account = stmt.accountId
            for trx in stmt.Trades:
                result.append(
                    self.createBuy(
                        trx.tradeDate,
                        account,
                        trx.symbol.rstrip("z"),
                        trx.quantity,
                        trx.currency,
                        trx.tradePrice,
                        amount.Amount(
                            round(-trx.ibCommission, 2), trx.ibCommissionCurrency
                        ),
                        amount.Amount(round(trx.netCash, 2), trx.currency),
                        config["baseCcy"],
                        trx.fxRateToBase,
                    )
                )

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
                        amt = 0
                        whAmount = trx.amount
                    else:
                        amt = trx.amount
                        whAmount = 0

                    transactions.append(
                        {
                            "date": trx.dateTime,
                            "symbol": trx.symbol,
                            "currency": trx.currency,
                            "amount": amt,
                            "whAmount": whAmount,
                            "description": trx.description,
                            "type": trx.type,
                            "account": account,
                        }
                    )

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
    ) -> data.Transaction:
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

    def createBuy(
        self,
        date: date,
        account: data.Account,
        asset: str,
        quantity: Decimal,
        currency: str,
        price: Decimal,
        commission: amount.Amount,
        netCash: amount.Amount,
        baseCcy: str,
        fxRateToBase: Decimal,
    ) -> data.Transaction:
        narration = "Buy"
        feeAccount = self.getFeeAccount(account)
        liquidityAccount = self.getLiquidityAccount(account, currency)
        assetAccount = self.getAssetAccount(account, asset)

        liquidityPrice = None
        if currency != baseCcy:
            price = price * fxRateToBase
            commission = amount.Amount(
                round(commission.number * fxRateToBase, 2), baseCcy
            )
            liquidityPrice = amount.Amount(fxRateToBase, baseCcy)

        postings = [
            data.Posting(
                assetAccount,
                amount.Amount(quantity, asset),
                data.CostSpec(price, None, baseCcy, None, None, False),
                None,
                None,
                None,
            ),
            data.Posting(feeAccount, commission, None, None, None, None),
            data.Posting(
                liquidityAccount,
                netCash,
                None,
                liquidityPrice,
                None,
                None,
            ),
        ]

        meta = data.new_metadata("buy", 0, {"account": account})
        return data.Transaction(
            meta, date, "*", "", narration, data.EMPTY_SET, data.EMPTY_SET, postings
        )

    def getAssetAccount(self, account: str, asset: str) -> data.Account:
        return f"Assets:{account}:Investment:IB:{asset}"

    def getLiquidityAccount(self, account: str, currency: str) -> data.Account:
        return f"Assets:{account}:Liquidity:IB:{currency}"

    def getReceivableAccount(self, account: str) -> data.Account:
        return f"Assets:{account}:Receivable:Verrechnungssteuer"

    def getIncomeAccount(self, account: str) -> data.Account:
        return f"Income:{account}:Interest"

    def getFeeAccount(self, account: str) -> data.Account:
        return f"Expenses:{account}:Fees"
