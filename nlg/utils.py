#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Miscellaneous utilities.
"""
from random import choice
import re

import humanize  # NOQA: F401
from inflect import engine
import numpy as np
from spacy import load
from spacy.matcher import Matcher, PhraseMatcher

infl = engine()
is_plural = infl.singular_noun
nlp = load("en_core_web_sm")

NP_MATCHER = Matcher(nlp.vocab)
NP_MATCHER.add("NP1", None, [{"POS": "PROPN", "OP": "+"}])
NP_MATCHER.add("NP2", None, [{"POS": "NOUN", "OP": "+"}])
NP_MATCHER.add("NP3", None, [{"POS": "ADV", "OP": "+"}, {"POS": "VERB", "OP": "+"}])
NP_MATCHER.add("NP4", None, [{"POS": "ADJ", "OP": "+"}, {"POS": "VERB", "OP": "+"}])
NP_MATCHER.add("QUANT", None, [{"POS": "NUM", "OP": "+"}])

NARRATIVE_TEMPLATE = """
{% autoescape None %}
from nlg import NLGTemplate as N
import pandas as pd

df = None  # set your dataframe here.
narrative = N(\"\"\"
              {{ tmpl }}
              \"\"\",
              tornado_tmpl=True, df=df, args={{ args }})
print(narrative.render())
"""


def get_phrase_matcher(df):
    matcher = PhraseMatcher(nlp.vocab)
    for col in df.columns[df.dtypes == np.dtype("O")]:
        for val in df[col].unique():
            matcher.add(val, None, nlp(val))
    return matcher


def is_overlap(x, y):
    """Whether the token x is contained within any span in the sequence y."""
    if "NUM" in [c.pos_ for c in x]:
        return False
    return any([x.text in yy for yy in y])


def unoverlap(tokens):
    """From a set of tokens, remove all tokens that are contained within
    others."""
    textmap = {c.text: c for c in tokens}
    text_tokens = textmap.keys()
    newtokens = []
    for token in text_tokens:
        if not is_overlap(textmap[token], text_tokens - {token}):
            newtokens.append(token)
    return [textmap[t] for t in newtokens]


def ner(doc, matcher=NP_MATCHER, match_ids=False, remove_overlap=True):
    """Find all NEs and other nouns in a spacy doc.

    Parameters
    ----------
    doc: spacy.tokens.doc.Doc
        The document in which to search for entities.
    match_ids: list, optional
        IDs from the spacy matcher to filter from the matches.
    remove_overlap: bool, optional
        Whether to remove overlapping tokens from the result.

    Returns
    -------
    list
        List of spacy.token.span.Span objects.
    """
    entities = set(doc.ents)
    if not match_ids:
        entities = [doc[start:end] for _, start, end in matcher(doc)]
    else:
        for m_id, start, end in matcher(doc):
            if NP_MATCHER.vocab.strings[m_id] in match_ids:
                entities.add(doc[start:end])
    if remove_overlap:
        entities = unoverlap(entities)
    return entities


def sanitize_indices(shape, i, axis=0):
    n = shape[axis]
    if i <= n // 2:
        return i
    return -(n - i)


def sanitize_text(text, d_round=2):
    """All text cleaning and standardization logic goes here."""
    nums = re.findall(r"\d+\.\d+", text)
    for num in nums:
        text = re.sub(num, str(round(float(num), d_round)), text)
    return text


def sanitize_df(df, d_round=2, **options):
    """All dataframe cleaning and standardizing logic goes here."""
    for c in df.columns[df.dtypes == float]:
        df[c] = df[c].round(d_round)
    return df


def concatenate_items(items, sep=", "):
    """Concatenate a sequence of tokens into an English string.

    Parameters
    ----------

    items : list-like
        List / sequence of items to be printed.
    sep : str, optional
        Separator to use when generating the string

    Returns
    -------
    str
    """
    if len(items) == 0:
        return ""
    if len(items) == 1:
        return items[0]
    items = list(map(str, items))
    if sep == ", ":
        s = sep.join(items[:-1])
        s += " and " + items[-1]
    else:
        s = sep.join(items)
    return s


def plural(word):
    """Pluralize a word.

    Parameters
    ----------

    word : str
        word to pluralize

    Returns
    -------
    str
        Plural of `word`
    """
    if not is_plural(word):
        word = infl.plural(word)
    return word


def singular(word):
    if is_plural(word):
        word = infl.singular_noun(word)
    return word


def pluralize_by_seq(word, by):
    """Pluralize a word depending on a sequence."""
    if len(by) > 1:
        return plural(word)
    return singular(word)


def humanize_comparison(x, y, bit, lot):
    if x == y:
        return choice(["the same", "identical"])
    if x < y:
        comparative = choice(["higher", "more", "greater"])
    else:
        comparative = choice(["less", "lower"])
    if lot(x, y):
        adj = choice(["a lot", "much"])
    elif bit(x, y):
        adj = choice(["a little", "a bit"])
    else:
        adj = ""
    return " ".join([adj, comparative])
