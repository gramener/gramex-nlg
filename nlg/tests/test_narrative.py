#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Tests for the nlg.narrative module.
"""

import os
import re
import unittest

import pandas as pd
from spacy.tokens import Doc

from nlg import templatize
from nlg.narrative import Nugget, Narrative
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

    def test_serialize(self):
        pl = self.nugget.to_dict()
        self.assertEqual(pl['text'], self.text.text)
        self.assertDictEqual(pl['fh_args'], {'_sort': ['-rating']})
        tokenmap = pl['tokenmap']
        ideal = [
            {
                'index': (0, 2), 'idx': 0, 'text': 'James Stewart',
                'sources': [
                    {
                        'location': 'cell', 'tmpl': 'df["name"].iloc[0]', 'type': 'ne',
                        'enabled': True
                    }
                ],
                'varname': '', 'inflections': []
            },
            {
                'index': 4, 'idx': 21, 'text': 'actor',
                'sources': [
                    {
                        'location': 'cell', 'tmpl': 'df["category"].iloc[-2]', 'type': 'token',
                        'enabled': True
                    }
                ],
                'varname': '',
                'inflections': [
                    {'source': 'G', 'fe_name': 'Singularize', 'func_name': 'singular'},
                    {'source': 'str', 'fe_name': 'Lowercase', 'func_name': 'lower'}
                ]
            }
        ]
        self.assertListEqual(ideal, tokenmap)

    def test_deserialize(self):
        pl = self.nugget.to_dict()
        nugget = Nugget.from_json(pl)
        actual = nugget.render(self.df).lstrip().decode('utf8')
        self.assertEqual(actual, self.text.text)

    def test_doc_serialize(self):
        nugget = templatize(nlp('Humphrey Bogart'), {}, self.df)
        pl = nugget.to_dict()
        self.assertEqual(len(pl['tokenmap']), 1)
        var = nugget.get_var(0)
        self.assertTrue(isinstance(var._token, Doc))
        self.assertEqual(var._token.text, 'Humphrey Bogart')
        var_serialized = pl['tokenmap'][0]
        self.assertEqual(var_serialized['text'], 'Humphrey Bogart')
        self.assertEqual(var_serialized['idx'], 0)
        self.assertEqual(len(var_serialized['sources']), 1)
        source = var_serialized['sources'][0]
        self.assertEqual(source['tmpl'], 'df["name"].iloc[0]')

    def test_narrative_html(self):
        text = nlp('Katharine Hepburn is the actress with the least rating.')
        fh_args = {'_sort': ['-rating']}
        nugget = templatize(text, fh_args, self.df)
        narrative = Narrative([self.nugget, nugget])

        # test default render
        actual = narrative.to_html(df=self.df)
        actual = re.sub(r'\s+', ' ', actual)
        ideal = ' <strong>James Stewart</strong> is the <strong>actor</strong> ' \
            + 'with the highest rating. <strong>Katharine Hepburn</strong> is ' \
            + 'the <strong>actress</strong> with the least rating.'
        self.assertEqual(ideal, actual)

        # test other options
        actual = narrative.to_html(bold=False, df=self.df)
        actual = re.sub(r'\s+', ' ', actual)
        no_bold = ideal.replace('<strong>', '')
        no_bold = no_bold.replace('</strong>', '')
        self.assertEqual(actual, no_bold)

        actual = narrative.to_html(italic=True, df=self.df)
        actual = re.sub(r'\s+', ' ', actual)
        italic = ideal.replace('<strong>', '<em><strong>')
        italic = italic.replace('</strong>', '</strong></em>')
        self.assertEqual(actual, italic)

        actual = narrative.to_html(underline=True, df=self.df)
        actual = re.sub(r'\s+', ' ', actual)
        italic = ideal.replace('<strong>', '<u><strong>')
        italic = italic.replace('</strong>', '</strong></u>')
        self.assertEqual(actual, italic)

    def test_parastyle(self):
        text = nlp('Katharine Hepburn is the actress with the least rating.')
        fh_args = {'_sort': ['-rating']}
        nugget = templatize(text, fh_args, self.df)
        narrative = Narrative([self.nugget, nugget])

        actual = narrative.to_html(style='list', df=self.df)
        actual = re.sub(r'\s+', ' ', actual)
        ideal = '<ul><li> <strong>James Stewart</strong> is the <strong>actor</strong> ' \
            + 'with the highest rating.</li><li> <strong>Katharine Hepburn</strong> is ' \
            + 'the <strong>actress</strong> with the least rating.</li></ul>'
        self.assertEqual(actual, ideal)

        actual = narrative.to_html(bold=False, style='list', liststyle='markdown', df=self.df)
        actual = [re.sub(r'\s+', ' ', c) for c in actual.splitlines()]
        ideal = [
            '* James Stewart is the actor with the highest rating.',
            '* Katharine Hepburn is the actress with the least rating.'
        ]
        self.assertListEqual(actual, ideal)
