#!/usr/bin/env python

"""
    Braintree Django Setup
"""

from distutils.core import setup

import btdjango

setup(
    name='btdjango',
    version=btdjango.VERSION,
    packages=['btdjango'],
)

