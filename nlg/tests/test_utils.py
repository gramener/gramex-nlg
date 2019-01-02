#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""Tests for nlg.utils"""

import random
import unittest
from nlg import utils


class TestUtils(unittest.TestCase):

    def test_concatenate_items(self):
        self.assertEqual(utils.concatenate_items('abc'), 'a, b and c')
        self.assertEqual(utils.concatenate_items([1, 2, 3], sep=''), '123')
        self.assertFalse(utils.concatenate_items([]))

    def test_pluralize(self):
        self.assertEqual(utils.plural('language'), 'languages')
        self.assertEqual(utils.plural('languages'), 'languages')
        self.assertEqual(utils.plural('bacterium'), 'bacteria')
        self.assertEqual(utils.plural('goose'), 'geese')

    def test_singular(self):
        self.assertEqual(utils.singular('languages'), 'language')
        self.assertEqual(utils.singular('language'), 'language')
        self.assertEqual(utils.singular('bacteria'), 'bacterium')
        self.assertEqual(utils.singular('geese'), 'goose')

    def test_pluralize_by_seq(self):
        self.assertEqual(utils.pluralize_by_seq('language', [1, 2]), 'languages')
        self.assertEqual(utils.pluralize_by_seq('languages', [1]), 'language')
        self.assertEqual(utils.pluralize_by_seq('language', []), 'language')

    def test_humanize_comparison(self):
        x = y = random.randint(0, 100)
        self.assertIn(utils.humanize_comparison(x, y, lambda x, y: True,
                                                lambda x, y: True),
                      ['the same', 'identical'])
        bit = lambda x, y: abs((x - y) / x) > 0.1
        lot = lambda x, y: abs((x - y) / x) > 0.5
        self.assertRegex(utils.humanize_comparison(0.1, 0.12, bit, lot),
                         r'(a little|a bit) (higher|more|greater)')
        self.assertRegex(utils.humanize_comparison(0.1, 0.16, bit, lot),
                         r'(a lot|much) (higher|more|greater)')
        self.assertRegex(utils.humanize_comparison(0.12, 0.1, bit, lot),
                         r'(a little|a bit) (less|lower)')
        self.assertRegex(utils.humanize_comparison(0.16, 0.07, bit, lot),
                         r'(a lot|much) (less|lower)')
