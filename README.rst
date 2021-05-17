.. image:: https://img.shields.io/pypi/l/tariochbctools.svg
   :target: https://pypi.python.org/pypi/tariochbctools
.. image:: https://img.shields.io/pypi/v/tariochbctools.svg
   :target: https://pypi.python.org/pypi/tariochbctools

tariochbctools
==============


Some importers, plugins and price fetchers for the double-entry bookkeeping software `Beancount <http://furius.ca/beancount/>`__.

Install it with

::

   pip install tariochbctools


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

**alphavantagefx**

Fetches fx rates from `Alphavantage <https://www.alphavantage.co/>`_
Requires the environment variable ``ALPHAVANTAGE_API_KEY`` to be set with your personal api key.

::

  2019-01-01 commodity BTC
    price: "CHF:tariochbctools.plugins.prices.alphavantagefx/BTC"


**bitstamp**

Fetches prices from `Bitstamp <https://www.bitstamp.com/>`_

::

  2019-01-01 commodity BTC
    price: "EUR:tariochbctools.plugins.prices.bitstamp/BTC"

**exchangeratesapi**

Fetches prices from `ratesapi.io <https://ratesapi.io>`_

::

  2019-01-01 commodity EUR
    price: "CHF:tariochbctools.plugins.prices.exchangeratesapi/EUR"

**interactivebrokers**

Fetches prices from `interactivebrokers <https://www.interactivebrokers.com/>`_
Only works if you have open positions with the symbols.
Requires the environment variables ``IBKR_TOKEN`` to be set with your flex query token and ``IBKR_QUERY_ID``
with a flex query that contains the open positions.

::

  2019-01-01 commodity VWRL
    price: "CHF:tariochbctools.plugins.prices.ibkr/VWRL"

**coinmarketcap**

Fetches prices from `coinmarketcap <https://coinmarketcap.com/>`_
Requires the environment variable ``COINMARKETCAP_API_KEY`` to be set to your api key.

::

  2019-01-01 commodity BTC
    price: "CHF:tariochbctools.plugins.prices.coinmarketcap/BTC"


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

Import from `Transferwise <https://www.transferwise.com/>`_ using their api

::

  from tariochbctools.importers.transferwise import importer as twimp
  CONFIG = [twimp.Importer()]

Create a file called transferwise.yaml in your import location (e.g. download folder).

::

  token: <your api token>
  baseAccount: <Assets:Transferwise:>

**TrueLayer**

Import from `TrueLayer <https://www.truelayer.com/>`_ using their api services. e.g. supports Revolut.
You need to create a dev account and see their documentation about how to get a refresh token.

::

  from tariochbctools.importers.truelayer import importer as tlimp
  CONFIG = [tlimp.Importer()]

Create a file called truelayer.yaml in your import location (e.g. download folder).

::

  baseAccount: <Assets:MyBank:>
  client_id: <CLIENT ID>
  client_secret: <CLIENT SECRET>
  refresh_token: <REFRESH TOKEN>

**zkb**

Import mt940 from `Zürcher Kantonalbank <https://www.zkb.ch/>`_

::

  from tariochbctools.importers.zkb import importer as zkbimp
  CONFIG = [zkbimp.ZkbImporter('/\d+\.mt940', 'Assets:ZKB')]

**ibkr**

Import dividends from `Interactive Brokers <https://www.interactivebrokers.com/>`_

Create a file called ibkr.yaml in your import location (e.g. downloads folder).

::

  token: <flex web query token>
  queryId: <flex query id>
  baseCcy: CHF

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

**Cembra Mastercard Montly Statement**

Import Monthly Statement PDF from Cembra Money Bank (e.g. Cumulus Mastercard).
Requires the dependencies for camelot to be installed. See https://camelot-py.readthedocs.io/en/master/user/install-deps.html#install-deps


::

  from tariochbctools.importers.cembrastatement import importer as cembrastatementimp
  CONFIG = [cembrastatementimp.Importer('\d+.pdf', 'Liabilities:Cembra:Mastercard')]


**blockchain**

Import transactions from Blockchain

Create a file called blockchain.yaml in your import location (e.g. downloads folder).


::

  base_ccy: CHF
  addresses:
    - address: 'SOMEADDRESS'
      currency: 'BTC'
      narration: 'Some Narration'
      asset_account: 'Assets:MyCrypto:BTC'
    - address: 'SOMEOTHERADDRESS'
      currency: 'LTC'
      narration: 'Some Narration'
      asset_account: 'Assets:MyCrypto:LTC'


::

  from tariochbctools.importers.blockchain import importer as bcimp
  CONFIG = [bcimp.Importer()]

**mail adapter**

Instead of expecting files to be in a local directory.
Connect per imap to a mail account and search for attachments to import using other importers.

Create a file called mail.yaml in your import location (e.g. downloads folder).


::

  host: "imap.example.tld"
  user: "myuser"
  password: "mypassword"
  folder: "INBOX"
  targetFolder: "Archive"


The targetFolder is optional, if present, mails that had attachments which were valid, will be moved to this folder.


::

  from tariochbctools.importers.general.mailAdapterImporter import MailAdapterImporter
  CONFIG = [MailAdapterImporter([MyImporter1(), MyImporter2()])]

**neon**

Import CSV from `Neon <https://www.neon-free.ch/>`_

::

  from tariochbctools.importers.neon import importer as neonimp
  CONFIG = [neonimp.Importer('\d\d\d\d_account_statements\.csv', 'Assets:Neon:CHF')]


Syncing a fork
--------------

Details: https://docs.github.com/en/free-pro-team@latest/github/collaborating-with-issues-and-pull-requests/syncing-a-fork

::

  git remote add upstream https://github.com/tarioch/beancounttools.git
  git remote -v
  git fetch upstream
  git checkout master
  git merge upstream/master
  git push
