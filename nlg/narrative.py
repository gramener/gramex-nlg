#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""The Narrative class."""
import json
import re

from tornado.template import Template

from nlg import utils, grammar

t_templatize = lambda x: '{{ ' + x + ' }}'  # noqa: E731
nlp = utils.load_spacy_model()


class Variable(object):
    """Token"""

    def __init__(self, token, sources=None, varname='', inflections=None):
        self._token = token
        if sources is None:
            sources = []
        self.sources = sources
        self.varname = varname
        if inflections is None:
            inflections = []
        self.inflections = inflections

    @property
    def enabled_source(self):
        for tmpl in self.sources:
            if tmpl.get('enabled', False):
                return tmpl

    @property
    def template(self):
        tmpl = self.enabled_source
        tmplstr = tmpl['tmpl']

        for i in self.inflections:
            tmplstr = self.add_inflection(tmplstr, i)

        varname = tmpl.get('varname', '')
        if varname:
            return tmplstr

        return t_templatize(tmplstr)

    def add_inflection(self, tmplstr, infl):
        func = infl['func_name']
        source = infl['source']
        if source == 'str':
            tmplstr += f'.{func}()'
        else:
            tmplstr = f'{source}.{func}({tmplstr})'
        return tmplstr


class Nugget(object):
    def __init__(self, text, tokenmap=None, inflections=None, fh_args=None,
                 condition=False, template="", name=""):
        self.doc = text
        self.tokenmap = {}
        if inflections is None:
            inflections = {}
        if tokenmap is not None:
            for tk, tkobj in tokenmap.items():
                token = Variable(tk, tkobj, inflections=inflections.get(tk))
                if not isinstance(tkobj, list):
                    token.template = tkobj['template']
                self.tokenmap[tk] = token
        if fh_args is not None:
            self.fh_args = fh_args
        else:
            self.fh_args = {}
        self._template = template
        self.condition = condition
        self.name = name

    @property
    def variables(self):
        return self.tokenmap

    def get_variable(self, t):
        for token in self.doc:
            if token.text == t:
                variable = self.tokenmap.get(token, False)
                if variable:
                    return variable

    @property
    def template(self):
        sent = self.doc.text
        for tk, tkobj in self.tokenmap.items():
            tmpl = tkobj.template
            sent = sent.replace(tk.text, tmpl)
            if tkobj.varname:
                pattern = re.escape(tmpl)
                sent = re.sub(pattern, t_templatize(tkobj.varname), sent)
                sent = f'{{% set {tkobj.varname} = {tmpl} %}}\n' + sent
        if self.condition:
            sent = f'{{% if {self.condition} %}}\n' + sent + '\n{% end %}'
        return self.add_fh_args(sent)

    def __repr__(self):
        return self.template

    def render(self, df, fh_args=None):
        if fh_args is not None:
            self.fh_args = fh_args
        return Template(self.template, whitespace='oneline').generate(orgdf=df, U=utils, G=grammar)

    def add_fh_args(self, sent):
        if self.fh_args:
            fh_args = json.dumps(self.fh_args)
            tmpl = f'{{% set fh_args = {fh_args}  %}}\n'
            tmpl += f'{{% set df = U.gfilter(orgdf, fh_args.copy()) %}}\n'
            return tmpl + sent
        return sent

    def set_variable(self, token, varname='', expr=''):
        if not (varname or expr):
            raise ValueError('One of `varname` or `expr` must be provided.')
        if isinstance(token, int):
            token = self.doc[token]
        source = [{'tmpl': expr, 'type': 'user', 'enabled': True}]
        self.tokenmap[token] = Variable(token, sources=source, varname=varname)


class Narrative(object):
    def __init__(self, sentences=None, conditions=None):
        if sentences is None:
            sentences = []
        self.sentences = sentences
        if conditions is None:
            conditions = []
        self.conditions = conditions

    @property
    def sdict(self):
        return {k: i for i, k in enumerate(self.sentences)}

    def templatize(self, sep="\n\n"):
        newsents = []
        for i, sent in enumerate(self.sentences):
            if str(i) in self.conditions:
                newsent = """
                {{ % if df.eval(\'{expr}\').any() % }}
                    {sent}
                {{ % end % }}
                """.format(
                    expr=self.conditions[str(i)], sent=sent
                )
            else:
                newsent = sent
            newsents.append(newsent)
        return sep.join(newsents)

    def append(self, sent):
        self.sentences.append(sent)

    add = append

    def prepend(self, sent):
        self.sentences.insert(0, sent)

    def insert(self, sent, ix):
        self.sentences.insert(ix, sent)

    def _move(self, key, pos):
        if isinstance(key, str):
            key = self.sdict[key]
        self.sentences.insert(key + pos, self.sentences.pop(key))

    def move_up(self, key):
        self._move(key, 1)

    def move_down(self, key):
        self._move(key, -1)
