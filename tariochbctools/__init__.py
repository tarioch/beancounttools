# -*- coding: utf-8 -*-
from pkg_resources import get_distribution, DistributionNotFound

"""Importers, plugins and price fetchers for beancount."""

try:
    dist_name = __name__ 
    __version__ = get_distribution(dist_name).version
except DistributionNotFound:
    __version__ = 'unknown'
finally:
    del get_distribution, DistributionNotFound
