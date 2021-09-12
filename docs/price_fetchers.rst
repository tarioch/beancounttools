Price fetchers
==============

See the official `Beanprice <https://github.com/beancount/beanprice>`__ for a lot of price fetchers.
Also most of the price fetchers which used to be in this repository have been migrated there.

Interactivebrokers
------------------

Fetches prices from `Interactivebrokers <https://www.interactivebrokers.com/>`__
Only works if you have open positions with the symbols.
Requires the environment variables ``IBKR_TOKEN`` to be set with your flex query token and ``IBKR_QUERY_ID``
with a flex query that contains the open positions.

.. code-block::

  2019-01-01 commodity VWRL
    price: "CHF:tariochbctools.plugins.prices.ibkr/VWRL"
