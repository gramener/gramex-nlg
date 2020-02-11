# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Miscellaneous utilities.
"""
import os.path as op
import re

import pandas as pd
from spacy.tokens import Token, Doc, Span
from tornado.template import Template

from gramex.data import filter as gfilter  # NOQA: F401
from gramex.data import (
    _filter_groupby_columns, _filter_select_columns, _filter_sort_columns, _filter_col,
    _agg_sep
)

NP_RULES = {
    'NP1': [{'POS': 'PROPN', 'OP': '+'}],
    'NP2': [{'POS': 'NOUN', 'OP': '+'}],
    'NP3': [{'POS': 'ADV', 'OP': '+'}, {'POS': 'VERB', 'OP': '+'}],
    'NP4': [{'POS': 'ADJ', 'OP': '+'}, {'POS': 'VERB', 'OP': '+'}],
    'QUANT': [{'POS': 'NUM', 'OP': '+'}]
}
QUANT_PATTERN = re.compile(r'(^\.d+|^d+\.?(d?)+)')
_spacy = {
    'model': False,
    'lemmatizer': False,
    'matcher': False
}


def _locate_app_config():
    return op.join(op.dirname(__file__), 'app', 'gramex.yaml')


def load_spacy_model():
    """Load the spacy model when required."""
    if not _spacy['model']:
        from spacy import load
        nlp = load('en_core_web_sm')
        _spacy['model'] = nlp
    else:
        nlp = _spacy['model']
    return nlp


def get_lemmatizer():
    if not _spacy['lemmatizer']:
        from spacy.lang.en import LEMMA_INDEX, LEMMA_EXC, LEMMA_RULES
        from spacy.lemmatizer import Lemmatizer
        lemmatizer = Lemmatizer(LEMMA_INDEX, LEMMA_EXC, LEMMA_RULES)
        _spacy['lemmatizer'] = lemmatizer
    else:
        lemmatizer = _spacy['lemmatizer']
    return lemmatizer


def make_np_matcher(nlp, rules=NP_RULES):
    """Make a rule based noun phrase matcher.

    Parameters
    ----------
    nlp : `spacy.lang`
        The spacy model to use.
    rules : dict, optional
        Mapping of rule IDS to spacy attribute patterns, such that each mapping
        defines a noun phrase structure.

    Returns
    -------
    `spacy.matcher.Matcher`
    """
    if not _spacy['matcher']:
        from spacy.matcher import Matcher
        matcher = Matcher(nlp.vocab)
        for k, v in rules.items():
            matcher.add(k, None, v)
        _spacy['matcher'] = matcher
    else:
        matcher = _spacy['matcher']
    return matcher


def render_search_result(text, results, **kwargs):
    for token, tokenlist in results.items():
        tmpl = [t for t in tokenlist if t.get('enabled', False)][0]
        text = text.replace(token, '{{{{ {} }}}}'.format(tmpl['tmpl']))
    return Template(text).generate(**kwargs).decode('utf-8')


def join_words(x, sep=' '):
    return sep.join(re.findall(r'\w+', x, re.IGNORECASE))


class set_nlg_gramopt(object):  # noqa: class to be used as a decorator
    """Decorator for adding callables to grammar options of the webapp.
    """
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __call__(self, func):
        func.gramopt = True
        for k, v in self.kwargs.items():
            if not getattr(func, k, False):
                setattr(func, k, v)
        return func


def is_overlap(x, y):
    """Whether the token x is contained within any span in the sequence y."""
    if len(y) == 0:
        return False
    if isinstance(x, Token):
        if x.pos_ == "NUM":
            return False
    elif 'NUM' in [c.pos_ for c in x]:
        return False
    if len(y) > 1:
        return any([x.text in yy.text for yy in y])
    y = y.pop()
    if isinstance(x, (Token, Span)) and isinstance(y, Doc):
        return x.doc == y
    return False


def unoverlap(tokens):
    """From a set of tokens, remove all tokens that are contained within
    others."""
    textmap = {c: c for c in tokens}
    newtokens = []
    for token in tokens:
        if not is_overlap(textmap[token], set(tokens) - {token}):
            newtokens.append(token)
    return [textmap[t] for t in newtokens]


def ner(doc, matcher, match_ids=False, remove_overlap=True):
    """Find all NEs and other nouns in a spacy doc.

    Parameters
    ----------
    doc: spacy.tokens.doc.Doc
        The document in which to search for entities.
    matcher: spacy.matcher.Matcher
        The rule based matcher to use for finding noun phrases.
    match_ids: list, optional
        IDs from the spacy matcher to filter from the matches.
    remove_overlap: bool, optional
        Whether to remove overlapping tokens from the result.

    Returns
    -------
    list
        List of spacy.token.span.Span objects.
    """
    entities = set()
    for span in doc.ents:
        newtokens = [c for c in span if not c.is_space]
        if newtokens:
            newspan = doc[newtokens[0].i: (newtokens[-1].i + 1)]
            entities.add(newspan)
    if not match_ids:
        entities.update([doc[start:end] for _, start, end in matcher(doc)])
    else:
        for m_id, start, end in matcher(doc):
            if matcher.vocab.strings[m_id] in match_ids:
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
    nums = re.findall(r'\d+\.\d+', text)
    for num in nums:
        text = re.sub(num, str(round(float(num), d_round)), text)
    return text


def sanitize_df(df, d_round=2, **options):
    """All dataframe cleaning and standardizing logic goes here."""
    for c in df.columns[df.dtypes == float]:
        df[c] = df[c].round(d_round)
    return df


def sanitize_fh_args(args, df):
    columns = df.columns
    meta = {
        'filters': [],      # Applied filters as [(col, op, val), ...]
        'ignored': [],      # Ignored filters as [(col, vals), ...]
        'sort': [],         # Sorted columns as [(col, asc), ...]
        'offset': 0,        # Offset as integer
        'limit': None,      # Limit as integer - None if not applied
        'by': [],           # Group by columns as [col, ...]
    }
    res = {}
    if '_by' in args:
        res['_by'] = _filter_groupby_columns(args['_by'], columns, meta)
        col_list = args.get('_c', False)
        if not col_list:
            col_list = [col + _agg_sep + 'sum' for col in columns # noqa
                        if pd.api.types.is_numeric_dtype(df[col])]
        res['_c'] = []
        for c in col_list:
            res['_c'].append(_filter_col(c, df.columns)[0])
        columns = col_list
    elif '_c' in args:
        selected, _ = _filter_select_columns(args['_c'], columns, meta)
        res['_c'] = [c[0] for c in selected]
    if '_sort' in args:
        sort, _ = _filter_sort_columns(args['_sort'], columns)
        res['_sort'] = [c[0] for c in sort]
    return res


def add_html_styling(template, style):
    """Add HTML styling spans to template elements.

    Parameters
    ----------
    template : str
        A tornado template
    style : dict or bool
        If False, no styling is added.
        If True, a default bgcolor is added to template variables.
        If dict, expected to contain HTML span styling elements.

    Returns
    -------
    str
        Modified template with each variabled stylized.

    Example
    -------
    >>> t = 'Hello, {{ name }}!'
    >>> add_html_styling(t, True)
    'Hello, <span style='background-color:#c8f442'>{{ name }}</span>!'
    >>> add_html_styling(t, False)
    'Hello, {{ name }}!'
    >>> add_html_style(t, {'background-color': '#ffffff', 'font-family': 'monospace'})
    'Hello, <span style='background-color:#c8f442;font-family:monospace'>{{ name }}</span>!'
    """

    if not style:
        return template
    pattern = re.compile(r'\{\{[^\{\}]+\}\}')
    if isinstance(style, dict):
        # convert the style dict into a stylized HTML span
        spanstyle = ';'.join(['{}:{}'.format(k, v) for k, v in style.items()])
    else:
        spanstyle = 'background-color:#c8f442'
    for m in re.finditer(pattern, template):
        token = m.group()
        repl = '<span style="{ss}">{token}</span>'.format(
            ss=spanstyle, token=token)
        template = re.sub(re.escape(token), repl, template, 1)
    return '<p>{template}</p>'.format(template=template)


def infer_quant(token):
    """Infer the quantitative value from a token which has POS == 'NUM' or is like_num.

    Parameters
    ----------
    token : `spacy.tokens.Token`
        A spacy token representing a number / scalar. This can be anything with a POS attribute of
        'NUM' or is like_nnum

    Returns
    -------
    float or int

    Example
    -------
    >>> doc = nlp('Aryabhatta invented the zero.')
    >>> infer_quant(doc[-2])
    0
    """
    if re.fullmatch(QUANT_PATTERN, token.shape_):
        if "." in token.text:
            return float(token.text)
        return int(token.text)
