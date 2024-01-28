import re

from tariochbctools.importers.general import mt940importer


class RaiffeisenCHImporter(mt940importer.Importer):
    """An importer for MT940 from Raiffeisen CH"""

    """To get the correct file, choose SWIFT -> 'Période prédéfinie du relevé de compte' -> Sans détails"""

    def prepare_payee(self, trxdata):
        return ""

    def prepare_narration(self, trxdata):
        extra = trxdata["extra_details"]
        details = trxdata["transaction_details"]

        extraReplacements = {}

        detailsReplacements = {}
        detailsReplacements[r"\n"] = ", "

        for pattern, replacement in extraReplacements.items():
            extra = re.sub(pattern, replacement, extra)

        for pattern, replacement in detailsReplacements.items():
            details = re.sub(pattern, replacement, details)

        if extra:
            narration = extra.strip() + ": " + details.strip()
        else:
            narration = details.strip()

        return narration
