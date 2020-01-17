#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Tests for the nlg.narrative module.
"""

import os
import unittest

import pandas as pd

from nlg import templatize
from nlg.utils import load_spacy_model

op = os.path
nlp = load_spacy_model()


class TestNarrative(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.df = pd.read_csv(op.join(op.dirname(__file__), "data", "actors.csv"),
                             encoding='utf8')
        fh_args = {'_sort': ['-rating']}
        cls.text = nlp('James Stewart is the actor with the highest rating.')
        cls.nugget = templatize(cls.text, fh_args, cls.df)

    def test_nugget_variables(self):
        varnames = set([c.text for c in self.nugget.variables])
        self.assertSetEqual(varnames, {'James Stewart', 'actor'})

    def test_nugget_get_var(self):
        with self.assertRaises(KeyError):
            self.nugget.get_var('James Stewart')
        var = self.nugget.get_var('actor')
        self.assertEqual(str(var), '{{ G.singular(df["category"].iloc[-2]).lower() }}')

    def test_nugget_render(self):
        df = self.df
        rendered = self.nugget.render(self.df)
        self.assertEqual(rendered.lstrip().decode('utf8'), self.text.text)
        xdf = df[df['category'] == 'Actors'].copy()
        xdf['rating'] = 1 - df.loc[xdf.index, 'rating']
        rendered = self.nugget.render(xdf)
        self.assertEqual(rendered.lstrip().decode('utf8'),
                         'Marlon Brando is the actor with the highest rating.')

    def test_set_expr(self):
        var = self.nugget.get_var('actor')
        org_exp = var.enabled_source['tmpl']
        try:
            var.set_expr('df["category"].iloc[0]')
            self.assertEqual(str(var), '{{ G.singular(df["category"].iloc[0]).lower() }}')
            xdf = self.df[self.df['category'] == 'Actresses']
            rendered = self.nugget.render(xdf)
            self.assertEqual(rendered.lstrip().decode('utf8'),
                             'Ingrid Bergman is the actress with the highest rating.')
        finally:
            var.set_expr(org_exp)

    def test_add_var(self):
        var = self.nugget.get_var('actor')
        org_exp = var.enabled_source['tmpl']
        var_token, var_exp = self.text[-2], 'fh_args["_sort"][0]'

        try:
            var.set_expr('df["category"].iloc[0]')

            self.nugget.add_var(var_token, expr=var_exp)

            # sort by votes
            self.nugget.fh_args = {'_sort': ['-votes']}
            rendered = self.nugget.render(self.df)
            self.assertEqual(rendered.lstrip().decode('utf8'),
                             'Spencer Tracy is the actor with the highest votes.')
            xdf = self.df[self.df['category'] == 'Actresses']
            rendered = self.nugget.render(xdf)
            self.assertEqual(rendered.lstrip().decode('utf8'),
                             'Audrey Hepburn is the actress with the highest votes.')

            # Set the ratings back
            self.nugget.fh_args = {'_sort': ['-rating']}
            rendered = self.nugget.render(self.df)
            self.assertEqual(rendered.lstrip().decode('utf8'),
                             'James Stewart is the actor with the highest rating.')
            xdf = self.df[self.df['category'] == 'Actresses']
            rendered = self.nugget.render(xdf)
            self.assertEqual(rendered.lstrip().decode('utf8'),
                             'Ingrid Bergman is the actress with the highest rating.')
        finally:
            var.set_expr(org_exp)
            if var_token in self.nugget.tokenmap:
                del self.nugget.tokenmap[var_token]
