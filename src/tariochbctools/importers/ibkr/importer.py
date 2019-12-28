import yaml
from os import path
from ibflex import client, parser, Types, enums
import xml.etree.ElementTree as ET

from beancount import loader
from beancount.core import prices
from beancount.core.number import MISSING

from beancount.ingest import importer
from beancount.core import data
from beancount.core import amount
from beancount.core.number import D

import datetime
from dateutil.relativedelta import relativedelta


class Importer(importer.ImporterProtocol):
    """An importer for Interactive Broker using the flex query service."""

    def identify(self, file):
        return 'ibkr.yaml' == path.basename(file.name)

    def file_account(self, file):
        return ''

    def extract(self, file, existing_entries):
        with open(file.name, 'r') as f:
            config = yaml.safe_load(f)
        token = config['token']
        queryId = config['queryId']

        response = client.download(token, queryId)

        root = ET.fromstring(response)
        statement = parser.parse_element(root)
        assert isinstance(statement, Types.FlexQueryResponse)

        for divAccrual in statement.FlexStatements[0].ChangeInDividendAccruals:
            if divAccrual.code[0] != enums.Code.REVERSE:
                print(divAccrual)
                print(divAccrual.exDate)
                print(divAccrual.payDate)
                print(divAccrual.quantity)
                print(divAccrual.symbol)
                print(divAccrual.currency)
                print(divAccrual.grossAmount)
                print(divAccrual.tax)
                print(divAccrual.fee)
                print(divAccrual.fxRateToBase)

        return []
