from os import path

import beangulp
import blockcypher
import yaml
from beancount.core import amount, data
from beancount.core.number import D

from tariochbctools.importers.general.deduplication import ReferenceDuplicatesComparator
from tariochbctools.importers.general.priceLookup import PriceLookup


class Importer(beangulp.Importer):
    """An importer for Blockchain data."""

    def identify(self, filepath: str) -> bool:
        return path.basename(filepath).endswith("blockchain.yaml")

    def account(self, filepath: str) -> data.Entries:
        return ""

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        with open(filepath) as file:
            config = yaml.safe_load(file)
        self.config = config
        baseCcy = config["base_ccy"]
        priceLookup = PriceLookup(existing, baseCcy)

        entries = []
        for address in self.config["addresses"]:
            currency = address["currency"]
            addressDetails = blockcypher.get_address_details(
                address["address"], coin_symbol=currency.lower()
            )
            for trx in addressDetails["txrefs"]:
                metakv = {
                    "ref": trx["tx_hash"],
                }
                meta = data.new_metadata(file.name, 0, metakv)

                date = trx["confirmed"].date()
                price = priceLookup.fetchPriceAmount(currency, date)
                cost = data.CostSpec(price, None, baseCcy, None, None, False)

                outputType = "ether" if currency.lower() == "eth" else "btc"
                amt = blockcypher.from_base_unit(trx["value"], outputType)

                entry = data.Transaction(
                    meta,
                    date,
                    "*",
                    "",
                    address["narration"],
                    data.EMPTY_SET,
                    data.EMPTY_SET,
                    [
                        data.Posting(
                            address["asset_account"],
                            amount.Amount(D(str(amt)), currency),
                            cost,
                            None,
                            None,
                            None,
                        ),
                    ],
                )
                entries.append(entry)

        return entries

    cmp = ReferenceDuplicatesComparator()
