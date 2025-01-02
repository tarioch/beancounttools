import re
from typing import Any

from tariochbctools.importers.general import mt940importer


class RaiffeisenCHImporter(mt940importer.Importer):
    """An importer for MT940 from Raiffeisen CH"""

    """To get the correct file, choose SWIFT -> 'Période prédéfinie du relevé de compte' -> Sans détails"""

    def prepare_payee(self, trxdata: dict[str, Any]) -> str:
        return ""

    def prepare_narration(self, trxdata: dict[str, Any]) -> str:
        extra = trxdata["extra_details"]
        details = trxdata["transaction_details"]

        detailsReplacements = {}
        detailsReplacements[r"\n"] = ", "

        for pattern, replacement in detailsReplacements.items():
            details = re.sub(pattern, replacement, details)

        if extra:
            narration = extra.strip() + ": " + details.strip()
        else:
            narration = details.strip()

        return narration
