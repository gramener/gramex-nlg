#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""Tests for nlg.utils"""

import random
import re
import unittest
from nlg import utils
import pandas as pd
import os.path as op


class TestUtils(unittest.TestCase):
    def test_concatenate_items(self):
        self.assertEqual(utils.concatenate_items("abc"), "a, b and c")
        self.assertEqual(utils.concatenate_items([1, 2, 3], sep=""), "123")
        self.assertFalse(utils.concatenate_items([]))

    def test_pluralize(self):
        self.assertEqual(utils.plural("language"), "languages")
        self.assertEqual(utils.plural("languages"), "languages")
        self.assertEqual(utils.plural("bacterium"), "bacteria")
        self.assertEqual(utils.plural("goose"), "geese")

    def test_singular(self):
        self.assertEqual(utils.singular("languages"), "language")
        self.assertEqual(utils.singular("language"), "language")
        self.assertEqual(utils.singular("bacteria"), "bacterium")
        self.assertEqual(utils.singular("geese"), "goose")

    def test_pluralize_by_seq(self):
        self.assertEqual(utils.pluralize_by_seq("language", [1, 2]), "languages")
        self.assertEqual(utils.pluralize_by_seq("languages", [1]), "language")
        self.assertEqual(utils.pluralize_by_seq("language", []), "language")

    def test_humanize_comparison(self):
        x = y = random.randint(0, 100)
        self.assertIn(
            utils.humanize_comparison(x, y, lambda x, y: True, lambda x, y: True),
            ["the same", "identical"],
        )
        bit = lambda x, y: abs((x - y) / x) > 0.1  # NOQA: E731
        lot = lambda x, y: abs((x - y) / x) > 0.5  # NOQA: E731
        self.assertRegex(
            utils.humanize_comparison(0.1, 0.12, bit, lot),
            r"(a little|a bit) (higher|more|greater)",
        )
        self.assertRegex(
            utils.humanize_comparison(0.1, 0.16, bit, lot),
            r"(a lot|much) (higher|more|greater)",
        )
        self.assertRegex(
            utils.humanize_comparison(0.12, 0.1, bit, lot),
            r"(a little|a bit) (less|lower)",
        )
        self.assertRegex(
            utils.humanize_comparison(0.16, 0.07, bit, lot),
            r"(a lot|much) (less|lower)",
        )

    def test_unoverlap(self):
        sent = utils.nlp(
            """
            United States President Donald Trump is an entrepreneur and
            used to run his own reality show named 'The Apprentice'."""
        )
        ents = [sent[:i] for i in range(5)]
        self.assertListEqual(utils.unoverlap(ents), ents[-1:])

    def test_ner(self):
        sent = utils.nlp(
            """
            US President Donald Trump is an entrepreneur and
            used to run his own reality show named 'The Apprentice'."""
        )
        ents = utils.ner(sent)
        self.assertSetEqual(
            set([c.text for c in utils.unoverlap(ents)]),
            {
                "US President",
                "President Donald",
                "Donald Trump",
                "entrepreneur",
                "reality show",
                "Apprentice",
            },
        )

    def test_sanitize_indices(self):
        self.assertEqual(utils.sanitize_indices((3, 3), 0), 0)
        self.assertEqual(utils.sanitize_indices((3, 3), 1), 1)
        self.assertEqual(utils.sanitize_indices((3, 3), 2), -1)
        self.assertEqual(utils.sanitize_indices((3, 3), 0, 1), 0)
        self.assertEqual(utils.sanitize_indices((3, 3), 1, 1), 1)
        self.assertEqual(utils.sanitize_indices((3, 3), 2, 1), -1)

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
        {{ df.loc[0, 'name'] }} is the top {{ args['_sort'][0] }}
        actor, followed by {{ df.loc[1, 'name'] }}. The least {{ args['_sort'][0] }}
        actress is {{ df.loc[-1, 'name'] }}, trailing at only {{ df.loc[-1, 'votes'] }}
        {{ args['_sort'][0] }}, followed by {{ df.loc[-2, 'name'] }} at a {{ df.columns[2] }}
        of {{ df.loc[-2, 'rating'] }}.
        """
        args = {"?_sort": ["-votes"]}
        actual, _ = utils.templatize(doc, args, df)
        cleaner = lambda x: re.sub(r"\s+", " ", x)  # NOQA: E731
        self.assertEqual(*map(cleaner, (ideal, actual)))


if __name__ == "__main__":
    unittest.main()
