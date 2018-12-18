#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Templates used in Gramex NLG.
"""
import json
import random
from string import Formatter

import pandas as pd

from nlg import grammar

TEMPLATES = {
    'extreme': '{subject} {verb} the {adjective} {object}.',
    'comparison': '{subject} {verb} {quant} {adjective} than {object}.'
}


class Narrative(object):

    def __init__(self, struct):
        self.intent = struct['intent']
        self.template = TEMPLATES[self.intent]
        self.metadata = struct['metadata']
        self.data = struct['data']

    @property
    def subject(self):
        subject = self.metadata['subject']
        if isinstance(subject, str):
            return subject
        if isinstance(subject, dict):
            tmpl = subject.get('template', False)
            if tmpl:
                fmt_kwargs = {}
                for _, fname, _, _, in Formatter().parse(tmpl):
                    if fname:
                        fmt_kwargs[fname] = self.kwarg_from_df(
                            **subject['kwargs'][fname])
                return tmpl.format(**fmt_kwargs)
            return self.kwarg_from_df(**subject)
        raise TypeError('Subject not found.')

    @property
    def quant(self):
        quant = self.metadata['quant']
        if isinstance(quant, str):
            return quant
        if isinstance(quant, dict):
            tmpl = quant.get('template', False)
            if tmpl:
                fmt_kwargs = {}
                for _, fname, _, _ in Formatter().parse(tmpl):
                    if fname:
                        fmt_kwargs[fname] = self.eval_quant(
                            **quant['kwargs'][fname])
            return tmpl.format(**fmt_kwargs)
        raise TypeError('Quant not found.')

    @property
    def verb(self):
        verb = self.metadata['verb']
        if isinstance(verb, str):
            return verb
        if isinstance(verb, (list, tuple)):
            return random.choice(verb)

    @property
    def adjective(self):
        adj = self.metadata['adjective']
        if isinstance(adj, str):
            return adj
        if isinstance(adj, (list, tuple)):
            return random.choice(adj)

    @property
    def object(self):
        obj = self.metadata['object']
        if isinstance(obj, str):
            return obj
        if isinstance(obj, dict):
            tmpl = obj['template']
            fmt_kwargs = {}
            for _, fname, _, _ in Formatter().parse(tmpl):
                if fname:
                    fmt_kwargs[fname] = self.kwarg_from_df(
                        **obj['kwargs'][fname])
            return tmpl.format(**fmt_kwargs)

    def eval_quant(self, _type, expr):
        if _type != 'operation':
            return 0
        return pd.eval(expr.format(data=self.data))

    def kwarg_from_df(self, _type, colname, _filter):
        value = None
        if isinstance(_filter, str):
            value = get_series_extreme(self.data[colname], _filter)
        elif isinstance(_filter, dict):
            by = _filter['colname']
            subfilter = _filter['filter']
            ix = getattr(self.data[by], 'idx' + subfilter)()
            value = self.data.iloc[ix][colname]
        return value

    def render(self):
        fmt_kwargs = {}
        for _, fieldname, _, _ in Formatter().parse(self.template):
            if fieldname:
                fmt_kwargs[fieldname] = getattr(self, fieldname,
                                                '{{}}'.format(fieldname))
        return self.template.format(**fmt_kwargs)


def get_series_extreme(s, method):
    value = getattr(s, method)()
    if method == 'mode':
        value = value.iloc[0]
    return value


def concatenate_items(items, sep=', ', oxford_comma=False):
    """Concatenate a sequence of tokens into an English string.

    Parameters
    ----------

    items : list-like
        List / sequence of items to be printed.
    sep : str, optional
        Separator to use when generating the string
    oxford_comma : bool, optional
        Whether to use the Oxford comma.

    Returns
    -------

    """
    s = sep.join(list(items)[:-1])
    if sep == ', ':
        appendix = ' and ' + items[-1]
        if oxford_comma:
            appendix = sep.rstrip() + appendix
        s = s + appendix
    return s


def get_literal_results(struct):
    """Enumerate raw data as a results string from an insight structure.

    Parameters
    ----------

    struct : dict
        The insight structure.

    Returns
    -------
    str
        An English string containing pluralized items.

    """
    data = struct['data']
    results = struct['metadata']['results']
    colname = results['colname']
    items = getattr(data[colname], results['method'])()
    return concatenate_items(items)


def descriptive(struct, append_results=True, **kwargs):
    """Template for describing a univariate result or insight.

    Parameters
    ----------

    struct : dict
        the insight structure.
    append_results : bool, optional
        whether to append verbose results from the source data to the generated
        string.
    **kwargs : arbitrary keyword arguments
        These are assumed to be literal string formatting arguments for the
        template string.

    Returns
    -------
    str
        The generated narrative.

    """

    template = '{subject} {verb} {object} {preposition} {prep_object}'
    fmt_kwargs = {}
    for _, fieldname, _, _ in Formatter().parse(template):
        if not fieldname.startswith('_'):
            func = getattr(grammar, 'make_' + fieldname,
                           grammar.keep_fieldname)
            fmt_kwargs[fieldname] = func(struct)
    fmt_kwargs.update(kwargs)
    sentence = template.format(**fmt_kwargs)
    if not append_results:
        return sentence
    results = get_literal_results(struct)
    return sentence + ': ' + results


def _process_urlparams(handler):
    df = pd.read_csv(handler.args['data'][0])
    with open(handler.args['metadata'][0], 'r') as f_in:
        metadata = json.load(f_in)
    return df, metadata


def g_descriptive(handler):
    """Wrapper to be used with gramex FunctionHandler to expose the `descriptive`
    template.

    Parameters
    ----------

    handler : vartype
        handler is
    *args : vartype
        *args is
    **kwargs : vartype
        **kwargs is

    Returns
    -------

    """
    data, metadata = _process_urlparams(handler)
    return descriptive({'data': data, 'metadata': metadata})


def superlative(struct, *args, **kwargs):
    """Template for describing a superlative result in the data.

    Parameters
    ----------

    struct : dict
        the insight structure.
    *args : vartype
        *args is
    **kwargs : arbitrary keyword arguments
        These are assumed to be literal string formatting arguments for the
        template string.

    Returns
    -------

    """
    template = '{subject} {verb} {superlative} {object} {preposition} {prep_object}'
    fmt_kwargs = {}
    for _, fieldname, _, _ in Formatter().parse(template):
        if not fieldname.startswith('_'):
            func = getattr(grammar, 'make_' + fieldname,
                           grammar.keep_fieldname)
            fmt_kwargs[fieldname] = func(struct)
    fmt_kwargs.update(kwargs)
    return template.format(**fmt_kwargs)


def g_superlative(handler):
    """Wrapper to be used with gramex FunctionHandler to expose the
    `superlative`
    template.

    Parameters
    ----------

    handler : vartype
        handler is
    *args : vartype
        *args is
    **kwargs : vartype
        **kwargs is

    Returns
    -------

    """
    data, metadata = _process_urlparams(handler)
    return superlative({'data': data, 'metadata': metadata})
