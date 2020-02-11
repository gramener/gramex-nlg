#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Tests of the nlg.search module
"""

import os.path as op
import re
import unittest

import pandas as pd
from tornado.template import Template

from nlg import search, utils

nlp = utils.load_spacy_model()
matcher = utils.make_np_matcher(nlp)


class TestDFSearch(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        fpath = op.join(op.dirname(__file__), "data", "actors.csv")
        cls.df = pd.read_csv(fpath, encoding='utf-8')
        cls.dfs = search.DFSearch(cls.df)

    def test__search_1d_array_literal(self):
        text = nlp('The votes, name and rating of the artists.')
        res = search._search_1d_array(text, self.df.columns, literal=True)
        ideal = {text[1]: 3, text[3]: 1, text[5]: 2}
        self.assertDictEqual(res, ideal)

    def test__search_1d_array_lemmatize(self):
        text = nlp('The votes, names and ratings of the artists.')
        res = search._search_1d_array(text, self.df.columns)
        ideal = {text[1]: 3, text[3]: 1, text[5]: 2}
        self.assertDictEqual(res, ideal)

    def test__search_2d_array_literal(self):
        text = nlp(
            "James Stewart is the actor with the highest rating of 0.988373838 and 120 votes.")
        xdf = self.df.sort_values('rating', ascending=False)
        res = search._search_2d_array(text, xdf, literal=True)
        ideal = {text[-5]: (0, 2), text[-3]: (0, 3)}
        self.assertDictEqual(res, ideal)

    def test__search_2d_array_lemmatize(self):
        text = nlp(
            "James Stewart is the actor with the highest rating of 0.988373838 and 120 votes.")
        xdf = self.df.sort_values('rating', ascending=False)
        res = search._search_2d_array(text, xdf)
        ideal = {text[-5]: (0, 2), text[-3]: (0, 3), text[4]: (9, 0)}
        self.assertDictEqual(res, ideal)

    def test__search_array(self):
        sent = nlp("The votes, names and ratings of artists.")
        res = self.dfs._search_array(sent, self.df.columns, literal=True)
        self.assertDictEqual(res, {sent[1]: 3})

        res = self.dfs._search_array(sent, self.df.columns)
        self.assertDictEqual(res, {sent[1]: 3, sent[3]: 1, sent[5]: 2})

    def test_dfsearch_lemmatized(self):
        df = pd.DataFrame.from_dict(
            {
                "partner": ["Lata Mangeshkar", "Asha Bhosale", "Mohammad Rafi"],
                "song": [20, 5, 15],
            }
        )
        sent = nlp("Kishore Kumar sang the most songs with Lata Mangeshkar.")
        dfs = search.DFSearch(df)
        self.assertDictEqual(
            dfs.search(sent, lemmatize=True),
            {
                sent[5]: [{"location": "colname", "type": "token", "tmpl": "df.columns[1]"}],
                sent[-3:-1]: [
                    {'location': 'cell', 'tmpl': 'df["partner"].iloc[0]', 'type': 'ne'}],
            }
        )

    def test_search_df(self):
        fpath = op.join(op.dirname(__file__), "data", "actors.csv")
        df = pd.read_csv(fpath, encoding='utf-8')
        df.sort_values("votes", ascending=False, inplace=True)
        df.reset_index(inplace=True, drop=True)
        dfs = search.DFSearch(df)
        sent = nlp("Spencer Tracy is the top voted actor.")
        self.assertDictEqual(
            dfs.search(sent),
            {
                sent[:2]: [
                    {'location': 'cell', 'tmpl': 'df["name"].iloc[0]', 'type': 'ne'}
                ],
                sent[-3]: [{'location': 'colname', 'tmpl': 'df.columns[-1]', 'type': 'token'}],
                sent[-2]: [
                    {'location': 'cell', 'tmpl': 'df["category"].iloc[-4]', 'type': 'token'}]
            }
        )


class TestSearch(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        fpath = op.join(op.dirname(__file__), "data", "actors.csv")
        cls.df = pd.read_csv(fpath, encoding='utf-8')
        fpath = op.join(op.dirname(__file__), "data", "imdb_ratings.csv")
        cls.imdb = pd.read_csv(fpath, encoding='utf-8')

    def test_dfsearches(self):
        x = search.DFSearchResults()
        x['hello'] = 'world'
        x['hello'] = 'world'
        self.assertDictEqual(x, {'hello': ['world']})
        x = search.DFSearchResults()
        x['hello'] = 'world'
        x['hello'] = 'underworld'
        self.assertDictEqual(x, {'hello': ['world', 'underworld']})

    def test_search_args(self):
        args = utils.sanitize_fh_args({"_sort": ["-votes"]}, self.df)
        doc = nlp("James Stewart is the top voted actor.")
        ents = utils.ner(doc, matcher)
        self.assertDictEqual(
            search.search_args(ents, args),
            {
                doc[-3]: {
                    "tmpl": "fh_args['_sort'][0]",
                    "type": "token",
                    "location": "fh_args"
                }
            }
        )

    def test_search_args_literal(self):
        args = utils.sanitize_fh_args({"_sort": ["-rating"]}, self.df)
        doc = nlp("James Stewart has the highest rating.")
        ents = utils.ner(doc, matcher)
        self.assertDictEqual(search.search_args(ents, args, lemmatized=False),
                             {doc[-2]: {
                                 "tmpl": "fh_args['_sort'][0]",
                                 "location": "fh_args",
                                 "type": "token"}})

    def test_templatize(self):
        df = self.df.sort_values("votes", ascending=False)
        df.reset_index(inplace=True, drop=True)

        doc = nlp("""
        Spencer Tracy is the top votes actor, followed by Cary Grant.
        The least votes actress is Bette Davis, trailing at only 14 votes, followed by
        Ingrid Bergman at a rating of 0.296140198.
        """)
        ideal = """
        {{ df['name'].iloc[0] }} is the top {{ fh_args['_sort'][0] }}
        {{ df['category'].iloc[-4] }}, followed by {{ df['name'].iloc[1] }}.
        The least {{ fh_args['_sort'][0] }} {{ df['category'].iloc[-1] }} is
        {{ df['name'].iloc[-1] }}, trailing at only {{ df['votes'].iloc[-1] }}
        {{ df.columns[-1] }}, followed by {{ df['name'].iloc[-2] }} at a {{ df.columns[2] }}
        of {{ df['rating'].iloc[-2] }}.
        """
        args = {"_sort": ["-votes"]}
        tokenmap, text, inflections = search._search(doc, args, df, copy=True)
        actual = text.text
        for token, tmpls in tokenmap.items():
            tmpl = [t for t in tmpls if t.get('enabled', False)][0]
            actual = actual.replace(token.text,
                                    '{{{{ {} }}}}'.format(tmpl['tmpl']))
        cleaner = lambda x: re.sub(r"\s+", " ", x)  # NOQA: E731
        ideal, actual = map(cleaner, (ideal, actual))
        args = utils.sanitize_fh_args(args, df)
        ideal = Template(ideal).generate(df=df, fh_args=args)
        actual = Template(actual).generate(df=df, fh_args=args)
        self.assertEqual(ideal, actual)
        self.assertDictEqual(
            inflections,
            {
                doc[7]: [{'fe_name': 'Singularize', 'source': 'G', 'func_name': 'singular'},
                         {'fe_name': 'Lowercase', 'source': 'str', 'func_name': 'lower'}],
                doc[18]: [  # noqa: E912
                    {'fe_name': 'Singularize', 'source': 'G', 'func_name': 'singular'},
                    {'fe_name': 'Lowercase', 'source': 'str', 'func_name': 'lower'}]
            }
            # Don't detect inflections until they can be processed without intervention
            # 'voted': [{'source': 'G', 'fe_name': 'Lemmatize', 'func_name': 'lemmatize'}]}
        )

    def test_search_sort(self):
        results = [
            {'tmpl': 'df.loc[0, "name"]', 'type': 'ne', 'location': 'cell'},
            {'tmpl': 'df.columns[0]', 'type': 'token', 'location': 'colname'},
            {'tmpl': 'args["_sort"][0]', 'type': 'token', 'location': 'fh_args'}
        ]
        _sorted = search._sort_search_results(results)
        enabled = [c for c in _sorted if c.get('enabled', False)]
        self.assertListEqual(enabled, results[:1])

        results = [
            {'tmpl': 'df.columns[0]', 'type': 'token', 'location': 'colname'},
            {'tmpl': 'args["_sort"][0]', 'type': 'token', 'location': 'fh_args'},
            {'tmpl': 'df["foo"].iloc[0]', 'type': 'token', 'location': 'cell'}
        ]
        _sorted = search._sort_search_results(results)
        enabled = [c for c in _sorted if c.get('enabled', False)]
        self.assertListEqual(enabled, results[1:2])

        results = [
            {'tmpl': 'df.columns[0]', 'type': 'token', 'location': 'colname'},
            {'tmpl': 'args["_sort"][0]', 'type': 'token', 'location': 'cell'},
            {'tmpl': 'df["foo"].iloc[0]', 'type': 'quant', 'location': 'cell'}
        ]
        _sorted = search._sort_search_results(results)
        enabled = [c for c in _sorted if c.get('enabled', False)]
        self.assertListEqual(enabled, results[:1])

        results = [
            {'tmpl': 'args["_sort"][0]', 'type': 'token', 'location': 'cell'},
            {'tmpl': 'df["foo"].iloc[0]', 'type': 'quant', 'location': 'cell'}
        ]
        _sorted = search._sort_search_results(results)
        enabled = [c for c in _sorted if c.get('enabled', False)]
        self.assertListEqual(enabled, results[1:])

    def test_single_entity_search(self):
        text = nlp("Humphrey Bogart")
        nugget = search.templatize(text, {}, self.df)
        self.assertEqual(len(nugget.tokenmap), 1)
        for token, variable in nugget.tokenmap.items():
            break
        self.assertEqual(token.text, text.ents[0].text)
        self.assertEqual(variable.template, '{{ df["name"].iloc[0] }}')

    def test_literal_search(self):
        texts = ['How I Met Your Mother', 'Sherlock', 'Dexter', 'Breaking Bad']
        for t in texts:
            doc = nlp(t)
            nugget = search.templatize(doc, {}, self.imdb)
            self.assertEqual(len(nugget.tokenmap), 1)
            for token, variable in nugget.tokenmap.items():
                self.assertEqual(token.text, t)
                self.assertRegex(nugget.template, r'{{ df\["name"\].iloc\[-*\d+\] }}')

    def test_search_short_strings(self):
        # Check strings that are shorter than the max length of the df,
        # but still not a literal match
        nugget = search.templatize(nlp('Dexter is a good show'), {}, self.imdb)
        self.assertEqual(len(nugget.tokenmap), 1)
        token, variable = nugget.tokenmap.popitem()
        self.assertRegex(variable.enabled_source['tmpl'], r'df\["name"\].iloc\[-*\d+\]')


if __name__ == "__main__":
    unittest.main()
