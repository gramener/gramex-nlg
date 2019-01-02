#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Miscellaneous utilities.
"""
import re
from random import choice
import numpy as np
import pandas as pd
from inflect import engine
import humanize  # NOQA: F401
from spacy import load
from spacy.matcher import Matcher
from tornado.web import RequestHandler

infl = engine()
is_plural = infl.singular_noun
nlp = load('en_core_web_sm')

NP_MATCHER = Matcher(nlp.vocab)
NP_MATCHER.add('NP', None, [{'POS': 'PROPN', 'OP': '+'}])
NP_MATCHER.add('NP', None, [{'POS': 'NOUN', 'OP': '+'}])


def process_template(request, dfpath):
    s = request.get_argument('textbox')
    df = pd.read_csv(dfpath)
    return templatize(s, df)


def unoverlap(tokens):
    """From a set of tokens, remove all tokens that are contained within
    others."""
    is_overlap = lambda x, y: any([x in yy for yy in y])
    newtokens = []
    for token in tokens:
        if not is_overlap(token, tokens - {token}):
            newtokens.append(token)
    return newtokens


def ner(doc):
    """Find all NEs and other nouns in a spacy doc."""
    entities = {c.text for c in doc.ents}
    for _, start, end in NP_MATCHER(doc):
        entities.add(doc[start:end].text)
    return unoverlap(entities)


def search_df(tokens, df):
    """Search a dataframe for tokens and return the coordinates."""
    search_res = {}
    tokens = np.array(tokens)
    coltype = df.columns.dtype
    ixtype = df.index.dtype

    # search in columns
    column_ix = np.arange(df.shape[1])[df.columns.astype(str).isin(tokens)]
    for ix in column_ix:
        token = df.columns[ix]
        search_res[token] = 'df.columns[{}]'.format(ix)

    # search in index
    index_ix = df.index.astype(str).isin(tokens)
    for token in df.index[index_ix]:
        if token not in search_res:
            if ixtype == np.dtype('O'):
                indexer = 'df.loc[\'{}\']'.format(token)
            else:
                indexer = 'df.loc[{}]'.format(token)
            search_res[token] = indexer

    # search in table
    for token in tokens:
        if token not in search_res:
            mask = df.values.astype(str) == token
            column = df.columns[mask.sum(0).astype(bool)][0]
            index = df.index[mask.sum(1).astype(bool)][0]
            if coltype == np.dtype('O'):
                col_indexer = '\'{}\''.format(column)
            else:
                col_indexer = str(column)
            if ixtype == np.dtype('O'):
                ix_indexer = '\'{}\''.format(index)
            else:
                ix_indexer = str(index)
            search_res[token] = 'df.loc[{}, {}]'.format(ix_indexer, col_indexer)

    return search_res


def templatize(x, df):
    """Process a piece of text and templatize it according to a dataframe."""
    if isinstance(x, RequestHandler):
        text = x.get_argument('textbox')
    else:
        text = str(x)
    doc = nlp(text)
    entities = ner(doc)
    dfix = search_df(entities, df)
    for token, ixpattern in dfix.items():
        text = re.sub(token, '{{{{ {} }}}}'.format(ixpattern), text)
    return text


def concatenate_items(items, sep=', '):
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
        return ''
    if len(items) == 1:
        return items[0]
    items = list(map(str, items))
    if sep == ', ':
        s = sep.join(items[:-1])
        s += ' and ' + items[-1]
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
        return choice(['the same', 'identical'])
    if x < y:
        comparative = choice(['higher', 'more', 'greater'])
    else:
        comparative = choice(['less', 'lower'])
    if lot(x, y):
        adj = choice(['a lot', 'much'])
    elif bit(x, y):
        adj = choice(['a little', 'a bit'])
    else:
        adj = ''
    return ' '.join([adj, comparative])
