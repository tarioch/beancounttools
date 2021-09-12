Plugins
=======

generate_base_ccy_prices
------------------------

Dynamically generates prices to the base ccy by applying the fx rate to the base ccy for non base ccy prices

.. code-block::

  plugin "tariochbctools.plugins.generate_base_ccy_prices" "CHF"


check_portfolio_sum
-------------------

For ledger files that contain multiple "portfolios", the plugin verifies that on each transaction, all the "portfolios" have
the same weight. Portfolio is the second part of the account name. e.g. Asset:**Peter**:Bank1


.. code-block::

    plugin "tariochbctools.plugins.check_portfolio_sum"
