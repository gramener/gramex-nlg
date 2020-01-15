#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Tests for the nlg.narrative module.
"""
import os
import unittest

import pandas as pd

from nlg.search import templatize

op = os.path


class TestNarrative(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.df = pd.read_csv(op.join(op.dirname(__file__), 'data', 'actors.csv'),
                             encoding='utf-8')
        cls.fh_args = {'_sort': ['-rating']}
        cls.text = "James Stewart is the highest rated actor" \
            + " and Katharine Hepburn is the lowest rated actress."

    def test_template_obj(self):
        template = templatize(self.text, self.df, self.fh_args.copy())
        self.assertEqual(template.make_template())
