#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
"""
NLG Setup.
"""

import builtins
from setuptools import setup, find_packages


builtins.__NLG_SETUP__ = True

# Setuptools config
NAME = "nlg"
DESCRIPTION = "Natural Language Generation framework for Python."
with open('README.rst', encoding='utf-8') as f:
    LONG_DESCRIPTION = f.read()
MAINTAINER = 'Jaidev Deshpande'
MAINTAINER_EMAIL = 'jaidev.deshpande@gramener.com'
URL = "https://github.com/gramener/gramex-nlg"
DOWNLOAD_URL = 'https://pypi.org/project/nlg/#files'
LICENSE = 'MIT'
PROJECT_URLS = {
    'Bug Tracker': 'https://github.com/gramener/gramex-nlg/issues',
    'Documentation': 'https://learn.gramener.com/guide/nlg',
    'Source Code': 'https://github.com/gramener/gramex-nlg'
}

# Requirements
install_requires = [
    'gramex',
    'humanize',
    'inflect',
    'spacy==2.1.8',
]

# Setup
import nlg  # NOQA: E402
setup(
    name=NAME,
    maintainer=MAINTAINER,
    maintainer_email=MAINTAINER_EMAIL,
    description=DESCRIPTION,
    license=LICENSE,
    url=URL,
    download_url=DOWNLOAD_URL,
    include_package_data=True,
    version=nlg.__version__,
    long_description=LONG_DESCRIPTION,
    packages=find_packages(),
    install_requires=install_requires
)
