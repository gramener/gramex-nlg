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

from nlg import search, utils


class TestDFSearch(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        fpath = op.join(op.dirname(__file__), "data", "actors.csv")
        cls.df = pd.read_csv(fpath)
        cls.dfs = search.DFSearch(cls.df)

    def test__search_array(self):
        sent = "The votes, names and ratings of artists."
        res = self.dfs._search_array(sent, self.df.columns, lemmatize=False)
        self.assertDictEqual(res, {'votes': 3})

        res = self.dfs._search_array(sent, self.df.columns)
        self.assertDictEqual(res, {'votes': 3, 'names': 1, 'ratings': 2})

        sent = "The votes, NAME and ratings of artists."
        res = self.dfs._search_array(sent, self.df.columns,
                                     lemmatize=False)
        self.assertDictEqual(res, {'votes': 3, 'NAME': 1})
        res = self.dfs._search_array(sent, self.df.columns, lemmatize=False,
                                     case=True)
        self.assertDictEqual(res, {'votes': 3})

    def test_dfsearch_lemmatized(self):
        df = pd.DataFrame.from_dict(
            {
                "partner": ["Lata", "Asha", "Rafi"],
                "song": [20, 5, 15],
            }
        )
        sent = "Kishore Kumar sang the most songs with Lata Mangeshkar."
        dfs = search.DFSearch(df)
        self.assertDictEqual(dfs.search(sent, lemmatize=True),
                             {'songs': "df.columns[1]", 'Lata': "df['partner'][0]"})

    def test_search_df(self):
        fpath = op.join(op.dirname(__file__), "data", "actors.csv")
        df = pd.read_csv(fpath)
        df.sort_values("votes", ascending=False, inplace=True)
        df.reset_index(inplace=True, drop=True)
        dfs = search.DFSearch(df)
        sent = "Spencer Tracy is the top voted actor."
        self.assertDictEqual(dfs.search(sent),
                             {"Spencer Tracy": "df['name'][0]",
                              "voted": "df.columns[3]", 'actor': "df['category'][7]"})


class TestSearch(unittest.TestCase):
    def test_dfsearches(self):
        x = search.dfsearchres()
        x['hello'] = 'world'
        x['hello'] = 'world'
        self.assertDictEqual(x, {'hello': ['world']})
        x = search.dfsearchres()
        x['hello'] = 'world'
        x['hello'] = 'underworld'
        self.assertDictEqual(x, {'hello': ['world', 'underworld']})

    def test_search_args(self):
        args = {"?_sort": ["-votes"]}
        doc = utils.nlp("James Stewart is the top voted actor.")
        ents = utils.ner(doc)
        self.assertDictEqual(
            search.search_args(ents, args), {"voted": "args['?_sort'][0]"}
        )

    def test_templatize(self):
        fpath = op.join(op.dirname(__file__), "data", "actors.csv")
        df = pd.read_csv(fpath)
        df.sort_values("votes", ascending=False, inplace=True)
        df.reset_index(inplace=True, drop=True)

        doc = """
        Spencer Tracy is the top voted actor, followed by Cary Grant.
        The least voted actress is Bette Davis, trailing at only 14 votes, followed by
        Ingrid Bergman at a rating of 0.29614.
        """
        ideal = """
        {{ df.iloc[0]['name'] }} is the top {{ args['?_sort'][0] }}
        actor, followed by {{ df.iloc[1]['name'] }}. The least {{ args['?_sort'][0] }}
        actress is {{ df.iloc[-1]['name'] }}, trailing at only {{ df.iloc[-1]['votes'] }}
        {{ args['?_sort'][0] }}, followed by {{ df.iloc[-2]['name'] }} at a {{ df.columns[2] }}
        of {{ df.iloc[-2]['rating'] }}.
        """
        args = {"?_sort": ["-votes"]}
        actual, _ = search.templatize(doc, args, df)
        cleaner = lambda x: re.sub(r"\s+", " ", x)  # NOQA: E731
        self.assertEqual(*map(cleaner, (ideal, actual)))


if __name__ == "__main__":
    unittest.main()
