#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""Tests for nlg.utils"""

import unittest
from nlg import utils


nlp = utils.load_spacy_model()
matcher = utils.make_np_matcher(nlp)


class TestUtils(unittest.TestCase):

    def test_join_words(self):
        sent = 'The quick brown fox jumps over the lazy dog.'
        self.assertEqual(utils.join_words(sent), sent.rstrip('.'))
        self.assertEqual(utils.join_words(sent, ''), sent.rstrip('.').replace(' ', ''))
        self.assertEqual(utils.join_words('-Office supplies'), 'Office supplies')

    def test_sanitize_args(self):
        self.assertDictEqual(utils.sanitize_fh_args({'_sort': ['-Office supplies']}),
                             {'_sort': ['Office supplies']})

    @unittest.skip('NER is unstable.')
    def test_ner(self):
        sent = nlp(
            """
            US President Donald Trump is an entrepreneur and
            used to run his own reality show named 'The Apprentice'."""
        )
        ents = utils.ner(sent, matcher)
        self.assertSetEqual(
            set([c.text for c in utils.unoverlap(ents)]),
            {
                "Donald Trump",
                "Apprentice",
                "US President",
                "President Donald",
                "entrepreneur",
                "reality show"
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
