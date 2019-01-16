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


class TestSearch(unittest.TestCase):
    def test_lemmatized_df_search(self):
        df = pd.DataFrame.from_dict(
            {
                "singer": ["Kishore", "Kishore", "Kishore"],
                "partner": ["Lata", "Asha", "Rafi"],
                "songs": [20, 5, 15],
            }
        )
        doc = utils.nlp("Kishore Kumar sang the most songs with Lata Mangeshkar.")
        self.assertDictEqual(
            search.lemmatized_df_search([doc], df.columns), {"songs": "df.columns[2]"}
        )

    def test_search_args(self):
        args = {"?_sort": ["-votes"]}
        doc = utils.nlp("James Stewart is the top voted actor.")
        ents = utils.ner(doc)
        self.assertDictEqual(
            search.search_args(ents, args), {"voted": "args['?_sort'][0]"}
        )

    def test_search_df(self):
        fpath = op.join(op.dirname(__file__), "data", "actors.csv")
        df = pd.read_csv(fpath)
        df.sort_values("votes", ascending=False, inplace=True)
        df.reset_index(inplace=True, drop=True)
        doc = utils.nlp("Spencer Tracy is the top voted actor.")
        ents = utils.ner(doc)
        self.assertDictEqual(
            search.search_df(ents, df),
            {"Spencer Tracy": "df.iloc[0]['name']", "voted": "df.columns[3]"},
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
