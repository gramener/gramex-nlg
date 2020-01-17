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

from nlg.search import templatize
from nlg.narrative import Template
from nlg.utils import load_spacy_model

op = os.path
nlp = load_spacy_model()


class TestTemplate(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.df = pd.read_csv(op.join(op.dirname(__file__), 'data', 'actors.csv'),
                             encoding='utf-8')
        cls.fh_args = {'_sort': ['-rating']}
        cls.text = nlp(
            "James Stewart is the highest rated actor" +  # noqa: W504
            " and Katharine Hepburn is the lowest rated actress.")
        cls.tmpl = templatize(cls.text, cls.fh_args.copy(), cls.df)

    def test_template_generation(self):
        actual = self.tmpl.template
        ideal = "{% set fh_args = {'_sort': ['-rating']} %}"
        self.assertEqual(ideal, actual)

    def test_render(self):
        self.assertEqual(self.text, self.tmpl.render(self.df))
        df = self.df.sort_values('rating', ascending=False).iloc[1:-1]
        ideal = "Humphrey Bogart is the highest rated actor " \
            + "and Marlon Brando is the lowest rated actor."
        self.assertEqual(ideal, self.tmpl.render(df))

    def test_varname_assignment(self):
        text = nlp('The value of pi rounded to 3 decimal places is 3.412')
        token = text[6]
        tmpl = Template(text)
        tmpl.set_variable(token, 'n_dec')
        self.assertEqual(tmpl.template,
                         re.sub('3', r'{{ n_dec }}', text.text, count=1))
