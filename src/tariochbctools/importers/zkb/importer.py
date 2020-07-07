from tariochbctools.importers.general import mt940importer
import re


class ZkbImporter(mt940importer.Importer):
    def prepare_payee(self, trxdata):
        return ''

    def prepare_narration(self, trxdata):
        extra = trxdata['extra_details']
        details = trxdata['transaction_details']

        extraReplacements = {}
        extraReplacements[r'Einkauf ZKB Maestro Karte'] = ''
        extraReplacements[r'LSV:.*'] = 'LSV'
        extraReplacements[r'Gutschrift:.*'] = 'Gutschrift'
        extraReplacements[r'eBanking:.*'] = 'eBanking'
        extraReplacements[r'eBanking Mobile:.*'] = 'eBanking Mobile'
        extraReplacements[r'E-Rechnung:.*'] = 'E-Rechnung'
        extraReplacements[r'Kontouebertrag:.*'] = 'Kontouebertrag:'
        extraReplacements[r'\?ZKB:\d+ '] = ''

        detailsReplacements = {}
        detailsReplacements[r'\?ZI:\?9:\d'] = ''
        detailsReplacements[r'\?ZKB:\d+'] = ''
        detailsReplacements[r'Einkauf ZKB Maestro Karte Nr. \d+,'] = 'Maestro'

        for pattern, replacement in extraReplacements.items():
            extra = re.sub(pattern, replacement, extra)

        for pattern, replacement in detailsReplacements.items():
            details = re.sub(pattern, replacement, details)

        if extra:
            narration = extra.strip() + ': ' + details.strip()
        else:
            narration = details.strip()

        return narration
