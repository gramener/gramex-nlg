#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Templates used in Gramex NLG.
"""
import json
import random
import re
from string import Formatter

import pandas as pd

from nlg import grammar

TEMPLATES = {
    'extreme': '{subject} {verb} the {adjective} {object}.',
    'comparison': '{subject} {verb} {quant} {adjective} than {object}.'
}

FUNC_EXPR = re.compile(r'^(?P<filter>[a-z|A-Z]{1}[a-z|A-Z|_|\d]+)\((?P<colname>.*)\)')


def parse_func_expr(expr):
    m = re.match(FUNC_EXPR, expr)
    if m is None:
        raise ValueError('Invalid Expression')
    return {'colname': m.group('colname'), 'filter': m.group('filter')}


class Narrative(object):

    def __init__(self, struct):
        intent = struct.get('intent', False)
        if intent:
            self.intent = intent
            self.template = TEMPLATES[self.intent]
        else:
            if 'template' not in struct:
                raise KeyError('Either intent or template must be specified.')
            self.template = struct['template']
        self.metadata = struct['metadata']
        self.data = struct['data']

    def is_template(self, spec):
        """Check if a spec contains a template and the information required to
        render that template.

        Parameters
        ----------
        spec : dict

        Returns
        -------
        bool
            Whether the given spec contains a template.
        """
        template = spec.get('template')
        if isinstance(template, str):
            fieldnames = [f for _, f, _, _ in Formatter().parse(template) if f]
            kwargs = spec.get('kwargs', {})
            if kwargs:
                return all([f in kwargs for f in fieldnames])
            return all([f in template for f in fieldnames])
        return False

    def get_template_kwargs(self, spec):
        """Parse a template dict and find the fieldname kwargs."""
        tmpl = spec.get('template')
        fieldnames = [f for _, f, _, _ in Formatter().parse(tmpl) if f]
        kwargs = spec.get('kwargs', False)
        if kwargs:
            for f in fieldnames:
                if f not in kwargs:
                    raise KeyError("Fieldname '{}' not found in kwargs.".format(f))
            return {f: kwargs[f] for f in fieldnames}
        else:
            for f in fieldnames:
                if f not in spec:
                    raise KeyError("Fieldname '{}' not found in spec.".format(f))
            return {f: spec[f] for f in fieldnames}

    def process_template(self, spec):
        """Process a template."""
        tmpl = spec['template']
        kwargs = self.get_template_kwargs(spec)
        fmt_kwargs = {}
        for k, v in kwargs.items():
            if self.is_filter(v):
                fmt_kwargs[k] = self.process_filter(**v)
            elif self.is_quant_operation(v):
                fmt_kwargs[k] = self.eval_quant(**v)
        return tmpl.format(**fmt_kwargs)

    def is_filter(self, spec):
        """Check if a spec represents a filter."""
        return all([c in spec for c in ('_type', 'colname', '_filter')])

    def process_filter_dict(self, colname, _filter):
        by = _filter['colname']
        subfilter = _filter['filter']
        ix = getattr(self.data[by], 'idx' + subfilter)()
        return self.data.iloc[ix][colname]

    def process_filter(self, _type, colname, _filter):
        value = None
        if isinstance(_filter, str):
            try:
                _filter = parse_func_expr(_filter)
                value = self.process_filter_dict(colname, _filter)
            except ValueError:
                value = get_series_extreme(self.data[colname], _filter)
        elif isinstance(_filter, dict):
            value = self.process_filter_dict(colname, _filter)
        return value

    def is_quant_operation(self, spec):
        return ('_type' in spec) and ('expr' in spec)

    def eval_quant(self, _type, expr):
        if _type != 'operation':
            return 0
        return pd.eval(expr.format(data=self.data))

    def process_pos(self, spec):
        """Process the specification for an arbitrary part of speech.

        Parameters
        ----------
        spec : string or dict
            The specification for a given part of speech. If string, it is
            assumed to be a literal. If dict, it is expected to contain filters
            which allow it's calculation.


        Returns
        -------
        str
            Rendered string representation of the PoS.
        """
        if isinstance(spec, str):  # literal string
            return spec
        if isinstance(spec, (list, tuple)):
            return random.choice(spec)
        if self.is_template(spec):  # template
            return self.process_template(spec)
        if self.is_filter(spec):  # literal, but inferred from a filter
            return self.process_filter(**spec)

    @property
    def subject(self):
        subject = self.metadata.get('subject', False)
        if subject:
            return self.process_pos(subject)
        raise KeyError('Subject not found.')

    @property
    def quant(self):
        quant = self.metadata.get('quant', False)
        if quant:
            return self.process_pos(quant)
        raise KeyError('quant not found.')

    @property
    def verb(self):
        verb = self.metadata.get('verb', False)
        if verb:
            return self.process_pos(verb)
        raise KeyError('verb not found.')

    @property
    def adjective(self):
        adjective = self.metadata.get('adjective', False)
        if adjective:
            return self.process_pos(adjective)
        raise KeyError('adjective not found.')

    @property
    def object(self):
        obj = self.metadata.get('object', False)
        if obj:
            return self.process_pos(obj)
        raise KeyError('Object not found.')

    def render(self):
        fmt_kwargs = {}
        for _, fieldname, _, _ in Formatter().parse(self.template):
            if fieldname:
                field_args = getattr(self, fieldname, False)
                if not field_args:
                    spec = self.metadata.get(fieldname, False)
                    if not spec:
                        raise KeyError("Cannot find {}.".format(fieldname))
                    fmt_kwargs[fieldname] = self.process_pos(spec)
                else:
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
