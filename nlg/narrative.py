#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""WIP: The Narrative class."""
import json
import re

t_templatize = lambda x: '{{ ' + x + ' }}'  # noqa: E731


class Token(object):
    """Token"""

    def __init__(self, token, templates=None, inflections=None, varname=None):
        self._token = token
        if templates is not None:
            self.templates = templates
        else:
            self.templates = []
        if inflections is not None:
            self.inflections = inflections
        else:
            self.inflections = []
        self.varname = varname

    @property
    def enabled_template(self):
        for tmpl in self.templates:
            if tmpl.get('enabled', False):
                return tmpl

    def make_template(self):
        tmplstr = self.enabled_template['tmpl']
        if self.inflections:
            for i in self.inflections:
                tmplstr = self.add_inflection(tmplstr, i)
        if self.varname:
            return tmplstr
        return t_templatize(tmplstr)

    def add_inflection(self, tmplstr, infl):
        func = infl['func_name']
        source = infl['source']
        if source == 'str':
            tmplstr += f'.{func}()'
        else:
            tmplstr += f'{source}.{func}(tmplstr)'
        return tmplstr


class Template(object):
    def __init__(self, text, tokenmap, inflections, fh_args,
                 condition=False, template="", name=""):
        self.source_text = text
        self.tokenmap = {}
        for tk, tkobj in tokenmap.items():
            token = Token(tk, **tkobj)
            if not isinstance(tkobj, list):
                token.template = tkobj['template']
            self.tokenmap[tk] = token
        self.fh_args = fh_args
        self.inflections = inflections
        self.template = template
        self.condition = condition
        self.name = name

    def make_template(self):
        sent = self.source_text
        for tk, tkobj in self.tokenmap.items():
            tmpl = tkobj.make_template()
            sent = sent.replace(tk, tmpl)
            if tkobj.varname:
                pattern = re.escape(tmpl)
                sent = re.sub(pattern, t_templatize(tkobj.varname), sent)
                sent = f'{{% set {tkobj.varname} = {tkobj.make_template()} %}}\n\t' + sent
        if self.condition:
            sent = f'{{% if {self.condition} %}}\n\t' + sent + '\n{% end %}'
        return self.add_fh_args(sent)

    def add_fh_args(self, sent):
        fh_args = json.dumps(self.fh_args)
        tmpl = f'{{% set fh_args = {fh_args}  %}}\n'
        tmpl += f'{{% set df = U.grmfilter(orgdf, fh_args.copy()) %}}\n'
        return tmpl + sent


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
