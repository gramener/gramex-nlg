import os
from unittest import TestCase

import pandas as pd

from nlg import templatize
from nlg.utils import load_spacy_model
from nlg import webapp as app


nlp = load_spacy_model()
op = os.path


class TestWebApp(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.df = pd.read_csv(op.join(op.dirname(__file__), "data", "actors.csv"),
                             encoding='utf8')
        fh_args = {'_sort': ['-rating']}
        cls.text = nlp('James Stewart is the actor with the highest rating.')
        cls.nugget = templatize(cls.text, fh_args, cls.df)

    def test_preview_html(self):
        html = '<span style="background-color:#c8f442" class="cursor-pointer">{}</span>'
        ideal = html.format("James Stewart") + " is the "
        ideal += html.format('actor') + " with the highest rating."
        template = self.nugget.to_dict()
        self.assertEqual(app.get_preview_html(template, True), ideal)

        text = nlp("James Stewart, Humphrey Bogart, Marlon Brando and Ingrid Bergman are actors.")
        names = ['James Stewart', 'Humphrey Bogart', 'Marlon Brando', 'Ingrid Bergman']
        ideal = ", ".join([html.format(name) for name in names[:-1]])
        ideal += " and " + html.format(names[-1]) + " are " + html.format('actors') + "."
        nugget = templatize(text, {}, self.df)
        template = nugget.to_dict()
        actual = app.get_preview_html(template, True)
        self.assertEqual(actual, ideal)

    def test_preview_html_noninteractive(self):
        html = '<span style="background-color:#c8f442">{}</span>'
        ideal = html.format("James Stewart") + " is the "
        ideal += html.format('actor') + " with the highest rating."
        template = self.nugget.to_dict()
        self.assertEqual(app.get_preview_html(template), ideal)

        text = nlp("James Stewart, Humphrey Bogart, Marlon Brando and Ingrid Bergman are actors.")
        names = ['James Stewart', 'Humphrey Bogart', 'Marlon Brando', 'Ingrid Bergman']
        ideal = ", ".join([html.format(name) for name in names[:-1]])
        ideal += " and " + html.format(names[-1]) + " are " + html.format('actors') + "."
        nugget = templatize(text, {}, self.df)
        template = nugget.to_dict()
        actual = app.get_preview_html(template)
        self.assertEqual(actual, ideal)
