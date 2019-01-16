#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
"""
NLG Setup.
"""

from setuptools import setup, find_packages

install_requires = [
    'gramex',
    'humanize',
    'inflect',
    'pandas',
    'tornado',
    'spacy',
]

setup(name='nlg',
      version='0.1.0',
      packages=find_packages(),
      install_requires=install_requires,
      test_suite='tests',
      tests_require=[
          'nose',
          'coverage',
          'pytest'
      ]
      )
