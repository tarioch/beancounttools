Importers
=========

The importers normally all work very well together with `Smart Importer <https://github.com/beancount/smart_importer/>`__
and are also usable in `Fava <https://github.com/beancount/fava/>`__.

Bitstamp
--------

Import transactions from `Bitstamp <https://www.bitstamp.com/>`__

Create a file called bitstamp.yaml in your import location (e.g. downloads folder).

.. code-block:: yaml

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

.. code-block:: python

  from tariochbctools.importers.bitst import importer as bitstimp

  CONFIG = [bitstimp.Importer()]


QuickFile
--------------
Import from `QuickFile <https://www.quickfile.co.uk/>`__ using their API services.
Supports a `range of (mostly UK) banks <https://www.quickfile.co.uk/openbanking/providers>`__.

Requires a QuickFile account (any pricing plan, including free) but with a paid
Automated Bank Feed subscription (`small annual fee <https://www.quickfile.co.uk/home/pricing>`__).

It is assumed you already have automated bank feeds configured within QuickFile
for the accounts of interest and are able to browse transactions within the QuickFile dashboard.

.. code-block:: python

  from tariochbctools.importers.quickfile import importer as qfimp

  CONFIG = [qfimp.Importer()]

Create a file called ``quickfile.yaml`` in your import location (e.g. download folder).

.. code-block:: yaml

  account_number: "YOUR_ACCOUNT_NUMBER"
  api_key: YOUR_API_KEY
  app_id: YOUR_APP_ID
  from_date: 2020-12-13
  to_date: 2020-12-20
  accounts:
      1200: Assets:Other
      1201: Assets:Savings
  transaction_count: 200

from_date and to_date are both optional

To obtain an API key you must create an app in the `Account Settings | 3rd
Party Integration | API` section of your account dashboard.

The only permissions it needs to have is "Invoices.Bank_Search"

your api_key is for your account, you can find it on "Settings - My Apps" or in the quickfile sandbox

Accounts are indexed in the config by their ``nominal code`` (typically: ~1200)
visible in each account's settings. Only accounts listed in the config will be
queried.


Revolut
-------

Import CSV from `Revolut <https://www.revolut.com/>`__

.. code-block:: python

  from tariochbctools.importers.revolut import importer as revolutimp

  CONFIG = [revolutimp.Importer("/Revolut-CHF.*\.csv", "Assets:Revolut:CHF", "CHF")]


Wise (formerly Transferwise)
----------------------------

Import from `Wise <https://www.wise.com/>`__ using their api.

First, generate a personal API token by logging on and going to settings.
Next, you need to generate a public/private key pair and then upload the public
key part to your account. To generate the keys, execute (e.g. in your ``.ssh`` folder)

.. code-block:: bash

   openssl genrsa -out wise.pem
   openssl rsa -pubout -in wise.pem -out wise_public.pem
   openssl pkey -in wise.pem -traditional > wise_traditional.pem

The final command makes a traditional private key for compatibility with the python rsa library. This may stop being necessary at some point. See `this page https://github.com/sybrenstuvel/python-rsa/issues/80` for details.

Now upload the *public* key part to your Wise account.

You can then create an import config for beancount, or add Wise to your existing one.

.. code-block:: python

  from tariochbctools.importers.transferwise import importer as twimp

  CONFIG = [twimp.Importer()]

Create a file called transferwise.yaml in your import location (e.g. download folder).

.. code-block:: yaml

  token: <your api token>
  baseAccount: <Assets:Transferwise:>
  privateKeyPath: /path/to/wise_traditional.pem


Optionally, you can provide a dictionary of account names mapped by currency. In this case
you must provide a name for every currency in your Wise account, otherwise the import will
fail.


.. code-block:: yaml

  token: <your api token>
  baseAccount:
    SEK: "Assets:MySwedishWiseAccount"
    GBP: "Assets:MyUKWiseAccount"
  privateKeyPath: /path/to/wise_traditional.pem

TrueLayer
---------

Import from `TrueLayer <https://www.truelayer.com/>`__ using their api services. e.g. supports Revolut.
You need to create a dev account and see their documentation about how to get a refresh token.

.. code-block:: python

  from tariochbctools.importers.truelayer import importer as tlimp

  CONFIG = [tlimp.Importer()]

Create a file called truelayer.yaml in your import location (e.g. download folder).

.. code-block:: yaml

  account: <Assets:MyBank>
  client_id: <CLIENT ID>
  client_secret: <CLIENT SECRET>
  refresh_token: <REFRESH TOKEN>

Instead of a single ``account``, the configuration may include a *mapping* from
TrueLayer account IDs to beancount accounts. e.g.:

.. code-block:: yaml

  accounts:
    1aacb3110398ec5a2334fb0ffc2fface: Assets:Revolut:GBP
    ec34db160c61d468dc1cedde8bedb1f1: Liabilities:Visa

If it is present, transactions for *only these accounts* will be imported.


Nordigen
--------

Import from `Nordigen <http://nordigen.com/>`__ using their api services. e.g. supports Revolut.
You need to create a free account and create a token. I've included a small cli to allow to hook up
to different banks with nordigen. If you're country is not supported you can play around with other countries
e.g. CH is not allowed but things like revolut still work. You can also create multiple links and they will
all be listed in the end.

.. code-block:: console

  nordigen-conf list_banks --secret_id YOURSECRET_ID --secret_key YOURSECRET_KEY --country DE
  nordigen-conf create_link --secret_id YOURSECRET_ID --secret_key YOURSECRET_KEY --bank REVOLUT_REVOGB21 --reference myref
  nordigen-conf list_accounts --secret_id YOURSECRET_ID --secret_key YOURSECRET_KEY
  nordigen-conf delete_link --secret_id YOURSECRET_ID --secret_key YOURSECRET_KEY --reference myref


.. code-block:: python

  from tariochbctools.importers.nordigen import importer as nordimp

  CONFIG = [nordimp.Importer()]

Create a file called nordigen.yaml in your import location (e.g. download folder).

.. code-block:: yaml

  secret_id: <YOURSECRET_ID>
  secret_key: <YOURSECRET_KEY>

  accounts:
    - id: <ACCOUNT-ID>
      asset_account: "Assets:MyAccount:CHF"


ZKB
---

Import mt940 from `Zürcher Kantonalbank <https://www.zkb.ch/>`__

.. code-block:: python

  from tariochbctools.importers.zkb import importer as zkbimp

  CONFIG = [zkbimp.ZkbImporter("/\d+\.mt940", "Assets:ZKB")]


Interactivebrokers
------------------

Import dividends and buys from `Interactive Brokers <https://www.interactivebrokers.com/>`__

Create a file called ibkr.yaml in your import location (e.g. downloads folder).

.. code-block:: yaml

  token: <flex web query token>
  queryId: <flex query id>
  baseCcy: CHF

.. code-block:: python

  from tariochbctools.importers.ibkr import importer as ibkrimp

  CONFIG = [ibkrimp.Importer()]


ZAK
---

Import PDF from `Bank Cler ZAK <https://www.cler.ch/de/info/zak/>`__

.. code-block:: python

  from tariochbctools.importers.zak import importer as zakimp

  CONFIG = [zakimp.Importer(r"Kontoauszug.*\.pdf", "Assets:ZAK:CHF")]


mt940
-----

Import Swift mt940 files.


Schedule
--------

Generate scheduled transactions.

Define a file called schedule.yaml in your import location (e.g. downloads folder). That describes the schedule transactions. They will be added each month at the end of the month.

.. code-block:: yaml

  transactions:
    - narration: 'Save'
      postings:
          - account: 'Assets:Normal'
            amount: '-10'
            currency: CHF
          - account: 'Assets:Saving'


.. code-block:: python

  from tariochbctools.importers.schedule import importer as scheduleimp

  CONFIG = [scheduleimp.Importer()]


Cembra Mastercard Montly Statement
----------------------------------

Import Monthly Statement PDF from Cembra Money Bank (e.g. Cumulus Mastercard).
Requires the dependencies for camelot to be installed. See https://camelot-py.readthedocs.io/en/master/user/install-deps.html#install-deps


.. code-block:: python

  from tariochbctools.importers.cembrastatement import importer as cembrastatementimp

  CONFIG = [cembrastatementimp.Importer("\d+.pdf", "Liabilities:Cembra:Mastercard")]


Blockchain
----------

Import transactions from Blockchain

Create a file called blockchain.yaml in your import location (e.g. downloads folder).


.. code-block:: yaml

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


.. code-block:: python

  from tariochbctools.importers.blockchain import importer as bcimp

  CONFIG = [bcimp.Importer()]


Mail Adapter
------------

Instead of expecting files to be in a local directory.
Connect per imap to a mail account and search for attachments to import using other importers.

Create a file called mail.yaml in your import location (e.g. downloads folder).


.. code-block:: yaml

  host: "imap.example.tld"
  user: "myuser"
  password: "mypassword"
  folder: "INBOX"
  targetFolder: "Archive"


The targetFolder is optional, if present, mails that had attachments which were valid, will be moved to this folder.


.. code-block:: python

  from tariochbctools.importers.general.mailAdapterImporter import MailAdapterImporter

  CONFIG = [MailAdapterImporter([MyImporter1(), MyImporter2()])]


Neon
----

Import CSV from `Neon <https://www.neon-free.ch/>`__

.. code-block:: python

  from tariochbctools.importers.neon import importer as neonimp

  CONFIG = [neonimp.Importer("\d\d\d\d_account_statements\.csv", "Assets:Neon:CHF")]


Viseca One
----------

Import PDF from `Viseca One <https://one-digitalservice.ch/>`__

.. code-block:: python

  from tariochbctools.importers.viseca import importer as visecaimp

  CONFIG = [visecaimp.Importer(r"Kontoauszug.*\.pdf", "Assets:Viseca:CHF")]

BCGE
----

Import mt940 from `BCGE <https://www.bcge.ch/>`__

.. code-block:: python

  from tariochbctools.importers.bcge import importer as bcge

  CONFIG = [bcge.BCGEImporter("/\d+\.mt940", "Assets:BCGE")]

Swisscard cards
---------------

Import Swisscard's `Cashback Cards <https://www.cashback-cards.ch/>` transactions from a CSV export.__

.. code-block:: python

  from tariochbctools.importers.swisscard import importer as swisscard

  CONFIG = [swisscard.SwisscardImporter("swisscard/.*\.csv", "Liabilities:Cashback")]
