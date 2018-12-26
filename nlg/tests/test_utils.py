#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""Tests for nlg.utils"""

import unittest
from nlg import utils


class TestUtils(unittest.TestCase):

    def test_concatenate_items(self):
        self.assertEqual(utils.concatenate_items('abc'), 'a, b and c')
        self.assertEqual(utils.concatenate_items([1, 2, 3], sep=''), '123')
        self.assertFalse(utils.concatenate_items([]))

    def test_pluralize(self):
        self.assertEqual(utils.pluralize('language'), 'languages')
        self.assertEqual(utils.pluralize('languages'), 'languages')
        self.assertEqual(utils.pluralize('bacterium'), 'bacteria')
        self.assertEqual(utils.pluralize('goose'), 'geese')
