import re
from typing import Any

from tariochbctools.importers.general import mt940importer


def strip_newline(string: str) -> str:
    return string.replace("\n", "").replace("\r", "")


class BCGEImporter(mt940importer.Importer):
    def prepare_payee(self, trxdata: dict[str, Any]) -> str:
        transaction_details = strip_newline(trxdata["transaction_details"])
        payee = re.search(r"ORDP/([^/]+)", transaction_details)
        if payee is None:
            return ""
        else:
            return payee.group(1)

    def prepare_narration(self, trxdata: dict[str, Any]) -> str:
        transaction_details = strip_newline(trxdata["transaction_details"])
        extra_details = strip_newline(trxdata["extra_details"])
        beneficiary = re.search(r"/BENM/([^/]+)", transaction_details)
        remittance = re.search(r"/REMI/([^/]+)", transaction_details)
        narration = []
        if beneficiary is not None:
            narration.append("Beneficiary: %s" % beneficiary.group(1))
        if remittance is not None:
            narration.append("Remittance: %s" % remittance.group(1))
        return "%s - %s" % (extra_details, ",".join(narration))
