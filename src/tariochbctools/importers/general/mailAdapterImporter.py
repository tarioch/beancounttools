import yaml
from os import path
from beancount.ingest import importer, cache
from imap_tools import MailBox
import tempfile


class MailAdapterImporter(importer.ImporterProtocol):
    """An importer adapter that fetches file from mails and then calls another importer."""

    def __init__(self, importers):
        self.importers = importers

    def identify(self, file):
        return 'mail.yaml' == path.basename(file.name)

    def extract(self, file, existing_entries):
        config = yaml.safe_load(file.contents())

        with MailBox(config['host']).login(config['user'], config['password'], initial_folder=config['folder']) as mailbox:
            result = []
            for msg in mailbox.fetch():
                processed = False
                for att in msg.attachments:
                    with tempfile.TemporaryDirectory() as tmpdirname:
                        attFileName = path.join(tmpdirname, att.filename)
                        with open(attFileName, 'wb') as attFile:
                            attFile.write(att.payload)
                            attFile.flush()
                            fileMemo = cache.get_file(attFileName)

                            for delegate in self.importers:
                                if delegate.identify(fileMemo):
                                    newEntries = delegate.extract(fileMemo, existing_entries)
                                    result.extend(newEntries)
                                    processed = True

                if processed and 'targetFolder' in config:
                    mailbox.move(msg.uid, config['targetFolder'])

        return result
