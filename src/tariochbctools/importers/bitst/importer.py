from datetime import date
from os import path
from typing import Any

import beangulp
import bitstamp.client
import yaml
from beancount.core import amount, data
from beancount.core.number import MISSING, D
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta

from tariochbctools.importers.general.deduplication import ReferenceDuplicatesComparator
from tariochbctools.importers.general.priceLookup import PriceLookup


class Importer(beangulp.Importer):
    """An importer for Bitstamp."""

    def identify(self, filepath: str) -> bool:
        return path.basename(filepath).endswith("bitstamp.yaml")

    def account(self, filepath: str) -> data.Account:
        return ""

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        self.priceLookup = PriceLookup(existing, "CHF")

        with open(filepath) as file:
            config = yaml.safe_load(file)
        self.config = config
        self.client = bitstamp.client.Trading(
            username=config["username"], key=config["key"], secret=config["secret"]
        )
        self.currencies = config["currencies"]
        self._account = config["account"]
        self.otherExpensesAccount = config["otherExpensesAccount"]
        self.capGainAccount = config["capGainAccount"]

        dateCutoff = date.today() + relativedelta(months=-config["monthCutoff"])

        trxs = self.client.user_transactions()
        trxs.reverse()
        result = []
        for trx in trxs:
            entry = self.fetchSingle(trx)
            if entry.date > dateCutoff:
                result.append(entry)

        return result

    def fetchSingle(self, trx: dict[str, Any]) -> data.Transaction:
        id = int(trx["id"])
        type = int(trx["type"])
        date = parse(trx["datetime"]).date()

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
            narration = "Deposit"
            if posCcy:
                cost = data.CostSpec(
                    self.priceLookup.fetchPriceAmount(posCcy, date),
                    None,
                    "CHF",
                    None,
                    None,
                    False,
                )
            postings = [
                data.Posting(
                    self._account + ":" + posCcy,
                    amount.Amount(posAmt, posCcy),
                    cost,
                    None,
                    None,
                    None,
                ),
            ]
        elif type == 1:
            narration = "Withdrawal"
            postings = [
                data.Posting(
                    self._account + ":" + negCcy,
                    amount.Amount(negAmt, negCcy),
                    None,
                    None,
                    None,
                    None,
                ),
            ]
        elif type == 2:
            fee = D(trx["fee"])
            if posCcy and negCcy and posCcy.lower() + "_" + negCcy.lower() in trx:
                feeCcy = negCcy
                negAmt -= fee
            else:
                feeCcy = posCcy
                posAmt -= fee

            if feeCcy:
                rateFiatCcy = self.priceLookup.fetchPriceAmount(feeCcy, date)
            if feeCcy == posCcy:
                posCcyCost = None
                posCcyPrice = amount.Amount(rateFiatCcy, "CHF")
                negCcyCost = data.CostSpec(MISSING, None, MISSING, None, None, False)
                negCcyPrice = None
            else:
                posCcyCost = data.CostSpec(
                    None, D(-negAmt * rateFiatCcy), "CHF", None, None, False
                )
                posCcyPrice = None
                negCcyCost = None
                negCcyPrice = amount.Amount(rateFiatCcy, "CHF")

            narration = "Trade"

            postings = [
                data.Posting(
                    self._account + ":" + posCcy,
                    amount.Amount(posAmt, posCcy),
                    posCcyCost,
                    posCcyPrice,
                    None,
                    None,
                ),
                data.Posting(
                    self._account + ":" + negCcy,
                    amount.Amount(negAmt, negCcy),
                    negCcyCost,
                    negCcyPrice,
                    None,
                    None,
                ),
            ]
            if float(fee) > 0:
                postings.append(
                    data.Posting(
                        self.otherExpensesAccount,
                        amount.Amount(round(fee * rateFiatCcy, 2), "CHF"),
                        None,
                        None,
                        None,
                        None,
                    )
                )
            postings.append(
                data.Posting(self.capGainAccount, None, None, None, None, None)
            )

        else:
            raise ValueError("Transaction type " + str(type) + " is not handled")

        meta = data.new_metadata("bitstamp", id, {"ref": str(id)})
        return data.Transaction(
            meta, date, "*", "", narration, data.EMPTY_SET, data.EMPTY_SET, postings
        )

    cmp = ReferenceDuplicatesComparator()
