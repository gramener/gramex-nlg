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

import numpy as np
import pandas as pd
from tornado.template import Template

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

    def __init__(self, template='', data=None, struct=None, tmpl_weights=None,
                 tornado_tmpl=False, **fmt_kwargs):
        self.tornado_tmpl = tornado_tmpl
        self.fmt = Formatter()
        if struct is None:
            struct = {}
        if data is None:
            self.data = struct.get('data')
        else:
            self.data = data
        if isinstance(template, str):
            self.template = template
        elif isinstance(template, (list, tuple)):
            if tmpl_weights is not None:
                self.template = np.random.choice(template, 1, p=tmpl_weights)[0]
            else:
                self.template = random.choice(template)
        self.fmt_kwargs = fmt_kwargs
        if struct:
            intent = struct.get('intent', False)
            if intent:
                self.intent = intent
                self.template = TEMPLATES[self.intent]
            else:
                if 'template' not in struct:
                    raise KeyError('Either intent or template must be specified.')
                self.template = struct['template']
            self.metadata = struct['metadata']

    @property
    def tmpl_fnames(self):
        return [f for _, f, _, _ in self.fmt.parse(self.template) if f]

    def __repr__(self):
        return self.render()

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
            fieldnames = [f for _, f, _, _ in self.fmt.parse(template) if f]
            kwargs = spec.get('kwargs', {})
            if kwargs:
                return all([f in kwargs for f in fieldnames])
            return all([f in template for f in fieldnames])
        return False

    def get_template_kwargs(self, spec):
        """Parse a template dict and find the fieldname kwargs."""
        tmpl = spec.get('template')
        fieldnames = [f for _, f, _, _ in self.fmt.parse(tmpl) if f]
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

    def get_native_fmt_field(self, kw, spec):
        """Given a field name and a field spec, see if the pair evaluate to a
        native Python string format.

        Parameters
        ----------

        kw : str
            Format field.
        spec : any
            Format field specification
        """
        _, kw, _, _ = list(self.fmt.parse('{{{}}}'.format(kw)))[0]
        obj, _ = self.fmt.get_field(kw, (), {kw: spec})
        return obj

    def process_pos(self, kw, spec):
        """Process the specification for an arbitrary part of speech.

        Parameters
        ----------
        kw : str
            The format string keyword corresponding to the spec.
        spec : string or dict
            The specification for a given part of speech. If string, it is
            assumed to be a literal. If dict, it is expected to contain filters
            which allow it's calculation.


        Returns
        -------
        str
            Rendered string representation of the PoS.
        """
        # check if the kw and the spec evaluate to native Python string
        # formatting
        obj = self.get_native_fmt_field(kw, spec)
        if isinstance(obj, str):
            return obj
        if isinstance(spec, (str, int, float)):  # literal string
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

    def is_data_ref(self, s):
        fnames = set([f for _, f, _, _ in self.fmt.parse(s) if f])
        if len(fnames) != 1:
            return False
        _, field = self.fmt.get_field(fnames.pop(), (), {'data': self.data})
        return field == 'data'

    def has_fieldname(self, s):
        """Check if a string has a fieldname left in it."""
        return any([f for _, f, _, _ in self.fmt.parse(s) if f])

    def render(self):
        if self.tornado_tmpl:
            return Template(self.template).generate(**self.fmt_kwargs).decode('utf-8')
        try:
            s = self.template.format(**self.fmt_kwargs)
            if not self.has_fieldname(s):
                return s
        except KeyError:
            pass

        fmt_kwargs = {}
        if not hasattr(self, 'intent'):
            for k, v in self.fmt_kwargs.items():
                if not isinstance(v, str):
                    fmt_kwargs[k] = self.process_pos(k, v)
                else:
                    if self.is_data_ref(v):
                        fmt_kwargs[k] = v.format(data=self.data)
                    else:
                        fmt_kwargs[k] = v
        else:
            for k, v in self.metadata.items():
                fmt_kwargs[k] = self.process_pos(k, v)
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


if __name__ == '__main__':
    df = pd.read_csv('data/assembly.csv')
    df['vote_share'] = df.pop(
        'Vote share').apply(lambda x: x.replace('%', '')).astype(float)
    tmpl = """BJP won a voteshare of {x}% in {y}, followed by {a}% in {b} and
    {c}% in {d}."""
    N = Narrative(tmpl, data=df,
                  x='{data.vote_share[0]}', y='{data.AC[0]}',
                  a='{data.vote_share[1]}', b='{data.AC[1]}',
                  c='{data.vote_share[2]}', d='{data.AC[2]}')
    print(N)
