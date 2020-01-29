#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Tests for the nlg.grammar module.
"""
import os
import unittest

import pandas as pd

import nlg.grammar as G  # noqa: N812
from nlg import utils
from nlg.search import search_args, DFSearch

nlp = utils.load_spacy_model()
op = os.path


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

    def test_number_inflection(self):
        text = nlp('Actors and actors.')
        x, y = text[0], text[-2]
        infl = G._number_inflection(x, y)
        self.assertEqual(infl, G.plural)

        text = nlp('Actors and dancers.')
        x, y = text[0], text[-2]
        infl = G._number_inflection(x, y)
        self.assertFalse(infl)

    def test_shape_inflections(self):
        text = nlp('Actors is plural of actors.')
        x, y = text[0], text[-2]
        infl = G._shape_inflection(x, y)
        self.assertEqual(infl, G.lower)

    def test_inflections(self):
        text = nlp('James Stewart is the actor with the highest rating.')
        df = pd.read_csv(op.join(op.dirname(__file__), "data", "actors.csv"),
                         encoding='utf8')
        fh_args = {'_sort': ['-rating']}
        df = utils.gfilter(df, fh_args.copy())
        args = utils.sanitize_fh_args(fh_args, df)
        dfs = DFSearch(df)
        dfix = dfs.search(text)
        dfix.update(search_args(dfs.ents, args))
        dfix.clean()
        infl = G.find_inflections(dfix, fh_args, df)
        x, y = infl[text[4]]
        self.assertEqual(x, G.singular)
        self.assertEqual(y, G.lower)
