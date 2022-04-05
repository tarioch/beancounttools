from os import path

import yaml
from beancount.ingest import importer

# https://api.quickfile.co.uk/method/bank


class Importer(importer.ImporterProtocol):
    """An importer for QuickFile"""

    def __init__(self):
        self.config = None
        self.existing_entries = None

    def _configure(self, file, existing_entries):
        with open(file.name, "r") as config_file:
            self.config = yaml.safe_load(config_file)
        self.existing_entries = existing_entries

    def identify(self, file):
        return path.basename(file.name) == "quickfile.yaml"

    def file_account(self, file):
        return ""

    def extract(self, file, existing_entries=None):
        self._configure(file, existing_entries)

        entries = []
        return entries
