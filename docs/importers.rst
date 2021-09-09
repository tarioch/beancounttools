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


Revolut
-------

Import CSV from `Revolut <https://www.revolut.com/>`__

.. code-block:: python

  from tariochbctools.importers.revolut import importer as revolutimp

  CONFIG = [revolutimp.Importer("/Revolut-CHF.*\.csv", "Assets:Revolut:CHF", "CHF")]


Transferwise
------------

Import from `Transferwise <https://www.transferwise.com/>`__ using their api

.. code-block:: python

  from tariochbctools.importers.transferwise import importer as twimp

  CONFIG = [twimp.Importer()]

Create a file called transferwise.yaml in your import location (e.g. download folder).

.. code-block:: yaml

  token: <your api token>
  baseAccount: <Assets:Transferwise:>


TrueLayer
---------

Import from `TrueLayer <https://www.truelayer.com/>`__ using their api services. e.g. supports Revolut.
You need to create a dev account and see their documentation about how to get a refresh token.

.. code-block:: python

  from tariochbctools.importers.truelayer import importer as tlimp

  CONFIG = [tlimp.Importer()]

Create a file called truelayer.yaml in your import location (e.g. download folder).

.. code-block:: yaml

  baseAccount: <Assets:MyBank:>
  client_id: <CLIENT ID>
  client_secret: <CLIENT SECRET>
  refresh_token: <REFRESH TOKEN>


Nordigen
--------

Import from `Nordigen <http://nordigen.com/>`__ using their api services. e.g. supports Revolut.
You need to create a free account and create a token. I've included a small cli to allow to hook up
to different banks with nordigen. If you're country is not supported you can play around with other countries
e.g. CH is not allowed but things like revolut still work. You can also create multiple links and they will
all be listed in the end.

.. code-block:: console

  nordigen-conf list_banks --token YOURTOKEN --country DE
  nordigen-conf create_link --token YOURTOKEN --bank REVOLUT_REVOGB21
  nordigen-conf list_accounts --token YOURTOKEN list_accounts


.. code-block:: python

  from tariochbctools.importers.nordigen import importer as nordimp

  CONFIG = [nordimp.Importer()]

Create a file called nordigen.yaml in your import location (e.g. download folder).

.. code-block:: yaml

  token: <TOKEN>

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

Import dividends from `Interactive Brokers <https://www.interactivebrokers.com/>`__

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