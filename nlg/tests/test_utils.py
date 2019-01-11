#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""Tests for nlg.utils"""

import random
import unittest
from nlg import utils


class TestUtils(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
