.. image:: https://img.shields.io/pypi/l/tariochbctools.svg
   :target: https://pypi.python.org/pypi/tariochbctools
.. image:: https://img.shields.io/pypi/v/tariochbctools.svg
   :target: https://pypi.python.org/pypi/tariochbctools

tariochbctools
==============


Some importers, plugins and price fetchers for the double-entry bookkeeping software `Beancount <http://furius.ca/beancount/>`__.

plugins
-------
**generate_base_ccy_prices**

Dynamically generates prices to the base ccy by applying the fx rate to the base ccy for non base ccy prices

::

  plugin "tariochbctools.plugins.generate_base_ccy_prices" "CHF"


price fetchers
--------------
**alphavantage**

Fetches prices from `Alphavantage <https://www.alphavantage.co/>`_
Requires the environment variable ``ALPHAVANTAGE_API_KEY`` to be set with your personal api key.

::

  2019-01-01 commodity VWRL
    price: "CHF:tariochbctools.plugins.prices.alphavantage/VWRL.SW"

**bitstamp**

Fetches prices from `Bitstamp <https://www.bitstamp.com/>`_

::

  2019-01-01 commodity BTC
    price: "EUR:tariochbctools.plugins.prices.bitstamp/BTC"

**exchangeratesapi**

Fetches prices from `exchangeratesapi.io <https://exchangeratesapi.io//>`_

::

  2019-01-01 commodity EUR
    price: "CHF:tariochbctools.plugins.prices.exchangeratesapi/EUR"


importers
---------
**bitstamp**

Import transactions from `Bitstamp <https://www.bitstamp.com/>`_

Create a file called bitstamp.yaml in your import location (e.g. downloads folder).

::

  username: "12345"
  key: "MyKey"
  secret: "MySecret"
  account: 'Assets:Bitstamp'
  otherExpensesAccount: 'Expenses:Fee'
  capGainAccount: 'Income:Capitalgain'
  monthCutoff: 3
  currencies:
    - eur
    - btc

::

  from tariochbctools.importers.bitst import importer as bitstimp
  CONFIG = [bitstimp.Importer()]

**revolut**

Import CSV from `Revolut <https://www.revolut.com/>`_

::

  from tariochbctools.importers.revolut import importer as revolutimp
  CONFIG = [revolutimp.Importer('/Revolut-CHF.*\.csv', 'Assets:Revolut:CHF', 'CHF')]

**transferwise**

Import CSV from `Transferwise <https://www.transferwise.com/>`_

::

  from tariochbctools.importers.transferwiseimport importer as twimp
  CONFIG = [twimp.Importer('/statement_CHF.*\.csv', 'Assets:Transferwise:CHF')]

**zkb**

Import mt940 from `Zürcher Kantonalbank <https://www.zkb.ch/>`_

::

  from tariochbctools.importers.zkb import importer as zkbimp
  CONFIG = [zkbimp.ZkbImporter('/\d+\.mt940', 'Assets:ZKB')]

**zak**

**Currently not working reliably**. Import PDF from `Bank Cler ZAK <https://www.cler.ch/de/info/zak/>`_

**mt940**

Import Swift mt940 files.

**schedule**

Generate scheduled transactions.

Define a file called schedule.yaml in your import location (e.g. downloads folder). That describes the schedule transactions. They will be added each month at the end of the month.

::

  transactions:
    - narration: 'Save'
      postings:
          - account: 'Assets:Normal'
            amount: '-10'
            currency: CHF
          - account: 'Assets:Saving'


::

  from tariochbctools.importers.schedule import importer as scheduleimp
  CONFIG = [ scheduleimp.Importer() ]

**stocks**

**Planned rewrite**. Generate transaction for dividend payments based on entering values in the command line.

