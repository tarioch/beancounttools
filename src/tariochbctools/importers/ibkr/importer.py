import re
from datetime import date
from decimal import Decimal
from os import path
from typing import Any, TypeVar

import beangulp
import yaml
from beancount.core import amount, data
from beancount.core.number import D
from ibflex import Types, parser
from ibflex.enums import CashAction

from tariochbctools.importers.general.priceLookup import PriceLookup
from tariochbctools.importers.ibkr import flexclient

T = TypeVar("T")


def required(value: T | None, field: str) -> T:
    """ibflex declares every field of a flex statement as optional, which ones are there depends on the flex query."""
    if value is None:
        raise ValueError(f"The flex query does not include the field {field}")
    return value


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

        trxPerShareGroups = p.search(required(trx.description, "description"))
        tPerShareGroups = p.search(t["description"])

        trxPerShare = trxPerShareGroups.group("perShare") if trxPerShareGroups else ""
        tPerShare = tPerShareGroups.group("perShare") if tPerShareGroups else ""

        return (
            t["date"] == trx.dateTime
            and t["symbol"] == self.cleanupSymbol(required(trx.symbol, "symbol"))
            and trxPerShare == tPerShare
            and t["account"] == account
        )

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        with open(filepath) as f:
            config = yaml.safe_load(f)
        token = config["token"]
        queryId = config["queryId"]
        period = config["period"] if "period" in config else None

        priceLookup = PriceLookup(existing, config["baseCcy"])

        response = flexclient.download(token, queryId, period=period)

        statement = parser.parse(response)
        assert isinstance(statement, Types.FlexQueryResponse)

        result: data.Entries = []
        for stmt in statement.FlexStatements:
            transactions: list = []
            account = stmt.accountId
            for trade in stmt.Trades:
                currency = required(trade.currency, "currency")
                result.append(
                    self.createBuy(
                        required(trade.tradeDate, "tradeDate"),
                        account,
                        self.cleanupSymbol(required(trade.symbol, "symbol")),
                        required(trade.quantity, "quantity"),
                        currency,
                        required(trade.tradePrice, "tradePrice"),
                        amount.Amount(
                            round(-required(trade.ibCommission, "ibCommission"), 2),
                            required(
                                trade.ibCommissionCurrency, "ibCommissionCurrency"
                            ),
                        ),
                        amount.Amount(
                            round(required(trade.netCash, "netCash"), 2), currency
                        ),
                        config["baseCcy"],
                        trade.fxRateToBase,
                    )
                )

            for cash in stmt.CashTransactions:
                existingEntry = None
                if CashAction.DIVIDEND == cash.type or CashAction.WHTAX == cash.type:
                    existingEntry = next(
                        (
                            t
                            for t in transactions
                            if self.matches(cash, t, stmt.accountId)
                        ),
                        None,
                    )

                if existingEntry:
                    if CashAction.WHTAX == cash.type:
                        existingEntry["whAmount"] += cash.amount
                    else:
                        existingEntry["amount"] += cash.amount
                        existingEntry["description"] = cash.description
                        existingEntry["type"] = cash.type
                else:
                    amt: Decimal | int | None
                    whAmount: Decimal | int | None
                    if CashAction.WHTAX == cash.type:
                        amt = 0
                        whAmount = cash.amount
                    else:
                        amt = cash.amount
                        whAmount = 0

                    transactions.append(
                        {
                            "date": cash.dateTime,
                            "symbol": self.cleanupSymbol(
                                required(cash.symbol, "symbol")
                            ),
                            "currency": cash.currency,
                            "amount": amt,
                            "whAmount": whAmount,
                            "description": cash.description,
                            "type": cash.type,
                            "account": account,
                        }
                    )

            for trx in transactions:
                if trx["type"] == CashAction.DIVIDEND:
                    asset = trx["symbol"]
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
                assetAccount, amount.Amount(D("0"), asset), None, None, None, None
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
        fxRateToBase: Decimal | None,
    ) -> data.Transaction:
        narration = "Buy"
        feeAccount = self.getFeeAccount(account)
        liquidityAccount = self.getLiquidityAccount(account, currency)
        assetAccount = self.getAssetAccount(account, asset)

        liquidityPrice = None
        if currency != baseCcy:
            # only needed for other currencies than the base currency
            fxRate = required(fxRateToBase, "fxRateToBase")
            price = price * fxRate
            commission = amount.Amount(
                round(required(commission.number, "ibCommission") * fxRate, 2),
                baseCcy,
            )
            liquidityPrice = amount.Amount(fxRate, baseCcy)

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

    def cleanupSymbol(self, symbol: str) -> str:
        result = symbol
        result = result.rstrip("z")
        result, _, _ = result.partition(".")

        return result
