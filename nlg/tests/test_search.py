#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Tests of the nlg.search module
"""

import os.path as op
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
            search.search_args(ents, args), {"voted": "args['_sort'][0]"}
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
            {"Spencer Tracy": "df.loc[0, 'name']", "voted": "df.columns[3]"},
        )
