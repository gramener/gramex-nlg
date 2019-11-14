#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Tests for the nlg.grammar module.
"""
import unittest
import nlg.grammar as G  # noqa: N812


class TestGrammar(unittest.TestCase):

    def test_is_plural(self):
        self.assertTrue(G.is_plural_noun("languages"))
        # self.assertTrue(G.is_plural("geese"))
        self.assertTrue(G.is_plural_noun("bacteria"))
        self.assertTrue(G.is_plural_noun("Office supplies"))

    def test_concatenate_items(self):
        self.assertEqual(G.concatenate_items("abc"), "a, b and c")
        self.assertEqual(G.concatenate_items([1, 2, 3], sep=""), "123")
        self.assertFalse(G.concatenate_items([]))

    def test_pluralize(self):
        self.assertEqual(G.plural("language"), "languages")
        self.assertEqual(G.plural("languages"), "languages")
        self.assertEqual(G.plural("bacterium"), "bacteria")
        self.assertEqual(G.plural("goose"), "geese")

    def test_singular(self):
        self.assertEqual(G.singular("languages"), "language")
        self.assertEqual(G.singular("language"), "language")
        self.assertEqual(G.singular("bacteria"), "bacterium")
        # self.assertEqual(G.singular("geese"), "goose")

    def test_pluralize_by(self):
        self.assertEqual(G.pluralize_by("language", [1, 2]), "languages")
        self.assertEqual(G.pluralize_by("languages", [1]), "language")
        self.assertEqual(G.pluralize_by("language", []), "language")
        self.assertEqual(G.pluralize_by("language", 1), "language")
        self.assertEqual(G.pluralize_by("language", 2), "languages")
