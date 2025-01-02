import tempfile
from os import path

import yaml
from beancount.core import data
from beangulp import Importer
from imap_tools import MailBox


class MailAdapterImporter(Importer):
    """An importer adapter that fetches file from mails and then calls another importer."""

    def __init__(self, importers: list[Importer]):
        self.importers = importers

    def identify(self, filepath: str) -> bool:
        return "mail.yaml" == path.basename(filepath)

    def account(self, filepath: str) -> data.Account:
        return ""

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        with open(filepath) as file:
            config = yaml.safe_load(file)

        with MailBox(config["host"]).login(
            config["user"], config["password"], initial_folder=config["folder"]
        ) as mailbox:
            result = []
            for msg in mailbox.fetch():
                processed = False
                for att in msg.attachments:
                    with tempfile.TemporaryDirectory() as tmpdirname:
                        attFileName = path.join(tmpdirname, att.filename)
                        with open(attFileName, "wb") as attFile:
                            attFile.write(att.payload)
                            attFile.flush()

                            for delegate in self.importers:
                                if delegate.identify(attFileName):
                                    newEntries = delegate.extract(attFileName, existing)
                                    result.extend(newEntries)
                                    processed = True

                if processed and "targetFolder" in config:
                    mailbox.move(msg.uid, config["targetFolder"])

        return result
