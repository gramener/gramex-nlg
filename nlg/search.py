#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Search tools.
"""

import re
from itertools import chain

import numpy as np
import pandas as pd
from spacy import load
from spacy.matcher import PhraseMatcher

from nlg import utils
from nlg.grammar import concatenate_items

default_nlp = load("en_core_web_sm")

SEARCH_PRIORITIES = {"args": 0, "colname": 1, "cell": 2}


class dfsearchres(dict):

    def __setitem__(self, key, value):
        if key not in self:
            super(dfsearchres, self).__setitem__(key, [value])
        elif self[key][0] != value:
            self[key].append(value)

    def clean(self):
        results = {}
        for k, v in self.items():
            column_results = [r[1] for r in v if r[0] == "colname"]
            if len(column_results) > 0:
                results[k] = column_results[0]
            else:
                cell_results = [r[1] for r in v if r[0] == "cell"]
                if len(cell_results) > 0:
                    results[k] = cell_results[0]
        return results


class DFSearch(object):

    def __init__(self, df, nlp=default_nlp, **kwargs):
        self.df = df
        # What do results contain?
        # A map of tokens to pandas slices
        self.results = dfsearchres()
        self.nlp = nlp

    def search(self, text, colname_fmt="df.columns[{}]",
               cell_fmt="df['{}'].iloc[{}]", **kwargs):
        self.search_nes(text)
        for token, ix in self.search_columns(text, **kwargs).items():
            ix = utils.sanitize_indices(self.df.shape, ix, 1)
            self.results[token] = ("colname", colname_fmt.format(ix))
        for token, (x, y) in self.search_table(text, **kwargs).items():
            x = utils.sanitize_indices(self.df.shape, x, 0)
            y = utils.sanitize_indices(self.df.shape, y, 1)
            self.results[token] = ("cell", cell_fmt.format(self.df.columns[y], x))
        self.search_quant([c.text for c in self.doc if c.pos_ == 'NUM'])
        return self.results.clean()

    def search_nes(self, text, colname_fmt="df.columns[{}]", cell_fmt="df['{}'].iloc[{}]"):
        self.doc = self.nlp(text)
        self.ents = utils.ner(self.doc)
        ents = [c.text for c in self.ents]
        for token, ix in self.search_columns(ents, literal=True).items():
            ix = utils.sanitize_indices(self.df.shape, ix, 1)
            self.results[token] = ("colname", colname_fmt.format(ix))
        for token, (x, y) in self.search_table(ents, literal=True).items():
            x = utils.sanitize_indices(self.df.shape, x, 0)
            y = utils.sanitize_indices(self.df.shape, y, 1)
            self.results[token] = ("cell", cell_fmt.format(self.df.columns[y], x))

    def search_table(self, text, **kwargs):
        kwargs['array'] = self.df.copy()
        return self._search_array(text, **kwargs)

    def search_columns(self, text, **kwargs):
        kwargs['array'] = self.df.columns
        return self._search_array(text, **kwargs)

    def search_quant(self, quants, nround=2, cell_fmt="df['{}'].iloc[{}]"):
        dfclean = utils.sanitize_df(self.df, nround)
        quants = np.array(quants)
        n_quant = quants.astype('float').round(2)
        for x, y in zip(*dfclean.isin(n_quant).values.nonzero()):
            x = utils.sanitize_indices(dfclean.shape, x, 0)
            y = utils.sanitize_indices(dfclean.shape, y, 1)
            tk = quants[n_quant == dfclean.iloc[x, y]][0].item()
            self.results[tk] = ("cell", cell_fmt.format(self.df.columns[y], x))

    def _search_array(self, text, array, literal=False,
                      case=False, lemmatize=True, nround=2):
        """Search for tokens in text within a pandas array.
        Return {token: array_int_index}"""
        if literal:
            # Expect text to be a list of strings, no preprocessing on anything.
            if not isinstance(text, list):
                raise TypeError('text is expected to be list of strs when literal=True.')
            if not set([type(c) for c in text]).issubset({str, float, int}):
                raise TypeError('text can contain only strings or numbers when literal=True.')
            tokens = {c: str(c) for c in text}
        elif lemmatize:
            tokens = {c.lemma_: c.text for c in self.nlp(text)}
            if array.ndim == 1:
                array = [self.nlp(c) for c in array]
                array = pd.Series([token.lemma_ for doc in array for token in doc])
            else:
                for col in array.columns[array.dtypes == np.dtype('O')]:
                    s = [self.nlp(c) for c in array[col]]
                    try:
                        array[col] = [token.lemma_ for doc in s for token in doc]
                    except ValueError:
                        # You cannot lemmatize columns that have multi-word values
                        if not case:  # still need to respect the `case` param
                            array[col] = array[col].str.lower()
        else:
            if not case:
                tokens = {c.text.lower(): c.text for c in self.nlp(text)}
                if array.ndim == 1:
                    array = array.str.lower()
                else:
                    for col in array.columns[array.dtypes == np.dtype('O')]:
                        array[col] = array[col].str.lower()
            else:
                tokens = {c.text: c.text for c in self.nlp(text)}
        mask = array.isin(tokens.keys())
        if mask.ndim == 1:
            if mask.any():
                ix = mask.nonzero()[0]
                return {tokens[array[i]]: i for i in ix}
            return {}
        else:
            if mask.any().any():
                ix, iy = mask.values.nonzero()
                return {tokens[array.iloc[x, y]]: (x, y) for x, y in zip(ix, iy)}
        return {}


def search_concatenations(text, df):
    doc = default_nlp(text)
    matcher = PhraseMatcher(default_nlp.vocab)
    patterns = []
    for _, series in df.items():
        if series.dtype == np.dtype('O'):
            patterns.extend([default_nlp(x) for x in series])
    matcher.add("cell", None, *patterns)
    spans = []
    for _, start, end in matcher(doc):
        spans.append(doc[start:end].text)
    ideal = concatenate_items(spans)
    if ideal not in text:
        return ''
    mask = df.isin(spans)
    if mask.sum().sum() < 2:
        return ''
    # search for columns:
    col = df.columns[mask.any(0)][0]
    y = mask[col].nonzero()[0]
    if set(np.diff(y)) == {1}:
        return {ideal: "df.iloc[{}:{}, '{}']".format(y.min(), y.max(), col)}


def lemmatized_df_search(x, y, fmt_string="df.columns[{}]"):
    search_res = {}
    tokens = list(chain(*x))
    colnames = list(chain(*[default_nlp(c) for c in y]))
    for i, xx in enumerate(colnames):
        for yy in tokens:
            if xx.lemma_ == yy.lemma_:
                search_res[yy.text] = fmt_string.format(i)
    return search_res


def search_args(entities, args, lemmatized=True, fmt="args['{}'][{}]",
                argkeys=('_sort',)):
    """
    Search formhandler arguments.

    Parameters
    ----------
    entities : list
        list of spacyy entities
    args : Formhandler args
        [description]
    lemmatized : bool, optional
        whether to lemmatize search (the default is True, which [default_description])
    fmt : str, optional
        format used in the template (the default is "args['{}'][{}]", which [default_description])
    argkeys : list, optional
        keys to be considered for the search (the default is None, which [default_description])

    Returns
    -------
    [type]
        [description]
    """
    args = {k: v for k, v in args.items() if k in argkeys}
    search_res = {}
    ent_tokens = list(chain(*entities))
    for k, v in args.items():
        # key = k.lstrip("?")
        argtokens = list(chain(*[re.findall(r"\w+", f) for f in v]))
        argtokens = list(chain(*[default_nlp(c) for c in argtokens]))
        for i, x in enumerate(argtokens):
            for y in ent_tokens:
                if lemmatized:
                    if x.lemma_ == y.lemma_:
                        search_res[y.text] = fmt.format(k, i)
                else:
                    if x.text == y.text:
                        search_res[y.text] = fmt.format(k, i)
    return search_res


def search_df(tokens, df):
    """Search a dataframe for tokens and return the coordinates."""
    search_res = {}
    txt_tokens = np.array([c.text for c in tokens])
    coltype = df.columns.dtype
    ixtype = df.index.dtype

    # search in columns
    column_ix = np.arange(df.shape[1])[df.columns.astype(str).isin(txt_tokens)]
    for ix in column_ix:
        token = df.columns[ix]
        ix = utils.sanitize_indices(df.shape, ix, 1)
        search_res[token] = "df.columns[{}]".format(ix)

    # search in index
    index_ix = df.index.astype(str).isin(txt_tokens)
    for token in df.index[index_ix]:
        if token not in search_res:
            if ixtype == np.dtype("O"):
                indexer = "df.loc['{}']".format(token)
            else:
                indexer = "df.loc[{}]".format(token)
            search_res[token] = indexer

    # search in table
    for token in txt_tokens:
        if token not in search_res:
            mask = df.values.astype(str) == token
            try:
                column = df.columns[mask.sum(0).astype(bool)][0]
                # don't sanitize column
                index = df.index[mask.sum(1).astype(bool)][0]
                index = utils.sanitize_indices(df.shape, index, 0)
            except IndexError:
                continue
            if coltype == np.dtype("O"):
                col_indexer = "'{}'".format(column)
            else:
                col_indexer = str(column)
            if ixtype == np.dtype("O"):
                ix_indexer = "'{}'".format(index)
            else:
                ix_indexer = str(index)
            search_res[token] = "df.iloc[{}][{}]".format(ix_indexer, col_indexer)

    unfound = [token for token in tokens if token.text not in search_res]
    search_res.update(lemmatized_df_search(unfound, df.columns))
    return search_res


def templatize(text, args, df):
    """Process a piece of text and templatize it according to a dataframe."""
    text = utils.sanitize_text(text)
    df = utils.sanitize_df(df)
    args = utils.sanitize_fh_args(args)
    dfs = DFSearch(df)
    dfix = dfs.search(text)
    dfix.update(search_args(dfs.ents, args))
    for token, ixpattern in dfix.items():
        text = re.sub("\\b" + token + "\\b", "{{{{ {} }}}}".format(ixpattern), text)
    return text, dfix
