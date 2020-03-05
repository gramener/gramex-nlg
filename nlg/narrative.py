#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""The Narrative class."""
import json
import re
import warnings

from spacy.tokens import Token, Span, Doc
from tornado.template import Template

from nlg import utils, grammar

t_templatize = lambda x: '{{ ' + x + ' }}'  # noqa: E731
nlp = utils.load_spacy_model()


def _templatizer_factory(bold, italic, underline):
    def templatizer(x):
        x = t_templatize(x)
        if bold:
            x = f"<strong>{x}</strong>"
        if italic:
            x = f"<em>{x}</em>"
        if underline:
            x = f"<u>{x}</u>"
        return x
    return templatizer


def _check_unique_token(t, doc):
    if len([c for c in doc if c.text == t]) > 1:
        msg = f'There is more than one token in the document that matches the text "{t}".' \
            + " Using the first match." \
            + " Please use a `spacy.token.Token` instance for searching."
        warnings.warn(msg)


class Variable(object):
    """
    NLG Variable

    A variable is a piece of text which can change with the data or the operations performed on it.
    Each variable has two defining components:

       * a source text, as initially provided by the user, and
       * one or more *formulae*, which compute the value of the variable for a
         specific instance of the data.

    The source text of a variable may be found in multiple places within a dataset, and as such,
    a variable may have multiple formulae - one of which will have to be preferred by the user.
    A variable may additionally have other attributes, like:

       * a set of linguistic inflections which determine the form of the rendered variable text -
         these are distinct from the formula itself, in that the formula creates the base form
         of the text and inflections modify the base form.
       * a *name* used to identify the variable within the template of the nugget
    """

    def __init__(self, token, sources=None, varname='', inflections=None):
        self._token = token
        if sources is None:
            sources = []
        self.sources = sources
        self.varname = varname
        if inflections is None:
            inflections = []
        self.inflections = inflections
        self.templatizer = t_templatize

    def to_dict(self):
        """Serialize the variable to dict."""
        payload = {'text': self._token.text}
        token = self._token
        if isinstance(token, Token):
            payload['index'] = token.i
            payload['idx'] = token.idx
        elif isinstance(token, Span):
            payload['index'] = token.start, token.end
            payload['idx'] = token[0].idx
        elif isinstance(token, Doc):
            payload['index'] = 0
            payload['idx'] = 0
        payload['sources'] = self.sources
        payload['varname'] = self.varname
        payload['inflections'] = self.inflections
        return payload

    def set_expr(self, expr):
        """Change the formula or expression for the variable.

        Parameters
        ----------
        expr : str
            Python expression used to determine the value of the variable.
        """
        tmpl = self.enabled_source
        tmpl['tmpl'] = expr

    @property
    def enabled_source(self):
        for tmpl in self.sources:
            if tmpl.get('enabled', False):
                return tmpl

    def enable_source(self, tmpl):
        if isinstance(tmpl, int):
            for source in self.sources:
                source['enabled'] = False
            self.sources[tmpl]['enabled'] = True
        elif tmpl in [c['tmpl'] for c in self.sources]:
            for source in self.sources:
                if source['tmpl'] == tmpl:
                    source['enabled'] = True
                else:
                    source['enabled'] = False
        else:
            raise ValueError('Variable source not found.')

    @property
    def template(self):
        tmpl = self.enabled_source
        tmplstr = tmpl['tmpl']

        for i in self.inflections:
            tmplstr = self._add_inflection(tmplstr, i)

        varname = tmpl.get('varname', '')
        if varname:
            return tmplstr

        return self.templatizer(tmplstr)

    def _add_inflection(self, tmplstr, infl):
        func = infl['func_name']
        source = infl['source']
        if source == 'str':
            tmplstr += f'.{func}()'
        else:
            tmplstr = f'{source}.{func}({tmplstr})'
        return tmplstr

    def __repr__(self):
        return self.template


class Nugget(object):
    """
    Gramex-NLG Nugget

    A nugget is ideally a single sentence which conveys an insight about the data.
    It is created by searching the source dataframe and operations performed on it
    for entities found in the input text.

    Note: This class is not meant to be instantiated directly. Please use `nlg.templatize`.
    """

    def __init__(self, text, tokenmap=None, inflections=None, fh_args=None,
                 condition=None, template="", name=""):
        self.doc = text
        self.tokenmap = {}
        if inflections is None:
            inflections = {}
        if tokenmap is not None:
            for tk, tkobj in tokenmap.items():
                if isinstance(tkobj, Variable):
                    token = tkobj
                elif isinstance(tkobj, list):
                    token = Variable(tk, tkobj, inflections=inflections.get(tk))
                self.tokenmap[tk] = token
        if fh_args is not None:
            self.fh_args = fh_args
        else:
            self.fh_args = {}
        self._template = template
        self.condition = condition
        self.name = name
        self.templatizer = t_templatize

    def to_dict(self):
        """Serialze the nugget to dict."""
        payload = {}
        payload['text'] = self.doc.text
        tokenmap = []
        for _, variable in self.tokenmap.items():
            tokenmap.append(variable.to_dict())
        payload['tokenmap'] = tokenmap
        payload['fh_args'] = self.fh_args
        payload['condition'] = self.condition
        payload['name'] = self.name
        payload['template'] = self.template
        return payload

    @classmethod
    def from_json(cls, obj):
        if isinstance(obj, str):
            obj = json.loads(obj)

        text = obj.pop('text')
        obj['text'] = nlp(text)

        tokenlist = obj.pop('tokenmap')
        tokenmap = {}
        for tk in tokenlist:
            index = tk.pop('index')
            if isinstance(index, int):
                token = obj['text'][index]
            elif isinstance(index, (list, tuple)):
                start, end = index
                token = obj['text'][start:end]
            tk.pop('idx')
            tk.pop('text')
            tokenmap[token] = Variable(token, **tk)
        obj['tokenmap'] = tokenmap

        return cls(**obj)

    @property
    def variables(self):
        return self.tokenmap

    def get_var(self, t):
        """Get a variable from the nugget.

        Parameters
        ----------
        t : any
            The string, or token corresponding to the variable.
            Using strings is discouraged, since the nugget may have
            more than one variable which renders to the same string form.
            Using spacy tokens is unambiguous.

        Returns
        -------
        nlg.narrative.Variable

        Example
        -------
        >>> from nlg import templatize
        >>> df = pd.read_csv('actors.csv')
        >>> text = nlp("Charlie Chaplin has 76 votes.")
        >>> nugget = templatize(text, {}, df)
        >>> nugget.get_var('Charlie Chaplin')
        {{ df["name"].iloc[-1] }}
        """
        if len(self.tokenmap) == 1:
            token, var = tuple(self.tokenmap.items())[0]
            if isinstance(token, Doc):
                variable = var
        elif isinstance(t, Token):
            variable = self.tokenmap.get(t, False)
        elif isinstance(t, str):
            _check_unique_token(t, self.doc)
            variable = False
            for token in self.doc:
                if token.text == t:
                    variable = self.tokenmap.get(token, False)
        else:
            if isinstance(t, int):
                token = self.doc[t]
            elif isinstance(t, (list, tuple)):
                start, end = t
                token = self.doc[start:end]
            variable = self.tokenmap.get(token, False)
        if variable:
            return variable
        raise KeyError('Variable not found.')

    @property
    def template(self):
        sent = self.doc.text
        for tk, tkobj in self.tokenmap.items():
            tmpl = tkobj.template
            sent = sent.replace(tk.text, tmpl)
            if tkobj.varname:
                pattern = re.escape(tmpl)
                sent = re.sub(pattern, self.templatizer(tkobj.varname), sent)
                sent = f'{{% set {tkobj.varname} = {tmpl} %}}\n' + sent
        if self.condition:
            sent = f'{{% if {self.condition} %}}\n' + sent + '\n{% end %}'
        return self.add_fh_args(sent)

    def _set_templatizer(self, func):
        self.templatizer = func
        for _, variable in self.tokenmap.items():
            variable.templatizer = self.templatizer

    def _reset_templatizer(self):
        self._set_templatizer(t_templatize)

    def to_html(self, bold=True, italic=False, underline=False, **kwargs):
        self._set_templatizer(_templatizer_factory(bold, italic, underline))
        try:
            s = self.render(**kwargs)
            return s
        finally:
            self._reset_templatizer()

    def __repr__(self):
        return self.template

    def render(self, df, fh_args=None, **kwargs):
        """Render the template for the given set of arguments.

        Parameters
        ----------
        df : pandas.DataFrame
            The dataframe to use in the new rendering.

        fh_args : dict
            FormHandler arguments to use to transform the dataframe.

        **kwargs : dict
            Arguments passed to the `tornado.template.Template.generate` method.

        Returns
        -------
        str
            Rendered string.

        Example
        -------
        >>> from nlg import templatize
        >>> df = pd.read_csv('actors.csv')
        >>> text = nlp("Humphrey Bogart is at the top of the list.")
        >>> nugget = templatize(text, {}, df)
        >>> nugget.render(df.iloc[1:])
        b'Cary Grant is at the top of the list'
        """
        if fh_args is not None:
            self.fh_args = fh_args
        else:
            fh_args = {}
        kwargs['fh_args'] = fh_args
        return Template(
            self.template, whitespace='oneline').generate(
                df=df, orgdf=df, U=utils, G=grammar, **kwargs)

    def add_fh_args(self, sent):
        if self.fh_args:
            fh_args = json.dumps(self.fh_args)
            tmpl = f'{{% set fh_args = {fh_args}  %}}\n'
            tmpl += f'{{% set df = U.gfilter(orgdf, fh_args.copy()) %}}\n'
            tmpl += f'{{% set fh_args = U.sanitize_fh_args(fh_args, orgdf) %}}\n'
            tmpl += '{# Do not edit above this line. #}\n'
            return tmpl + sent
        return sent

    def add_var(self, token, varname='', expr=''):
        """Set a token within the source document as a variable.

        Parameters
        ----------
        token : int or spacy.tokens.Token or spacy.tokens.Span
            If `token` is an integer, it is interpreted as the position of the token
            in the source document.

        varname : str, optional
            Optional variable name used to refer to the variable within the Tornado template.

        expr : str, optional
            Python expression used to determine the value of the variable.
            Note that if `expr` is not provided, it has to be passed at the time of rendering the
            template. (See the `nlg.narrative.Nugget.render` method)

        Example
        -------
        >>> from nlg import templatize
        >>> df = pd.read_csv('actors.csv')
        >>> fh_args = {'_sort': ['-rating']}
        >>> text = nlp("James Stewart is the actor with the highest rating.")
        >>> nugget = templatize(text, fh_args, df)
        >>> nugget.add_var(-2, 'sort_col', 'fh_args["_sort"][0]')
        """
        if not (varname or expr):
            raise ValueError('One of `varname` or `expr` must be provided.')
        if isinstance(token, int):
            token = self.doc[token]
        elif isinstance(token, (list, tuple)):
            token = self.doc.char_span(*token)
        try:
            if any([token in c for c in self.tokenmap if isinstance(c, (Span, Doc))]):
                raise ValueError('Token is already contained in another variable.')
        except TypeError:
            pass
        source = [{'tmpl': expr, 'type': 'user', 'enabled': True}]
        self.tokenmap[token] = Variable(token, sources=source, varname=varname)


class Narrative(list):
    """A list to hold only Nuggets."""

    default_style = dict(style='para', liststyle='html', bold=True, italic=False, underline=False)

    def render(self, sep=' ', **kwargs):
        return sep.join([c.render(**kwargs).decode('utf8') for c in self])

    def to_html(self, style='para', liststyle='html', bold=True, italic=False, underline=False,
                **kwargs):
        self.html_style = {
            'bold': bold, 'italic': italic, 'underline': underline,
            'style': style, 'liststyle': liststyle
        }
        rendered = [c.to_html(bold, italic, underline, **kwargs).decode('utf8') for c in self]
        if style == 'para':
            s = ' '.join(rendered)
        elif style == 'list':
            if liststyle == "html":
                l_render = "".join(["<li>{}</li>".format(r) for r in rendered])
                s = f"<ul>{l_render}</ul>"
            elif liststyle == 'markdown':
                s = "\n".join(["* " + r for r in rendered])
            else:
                raise ValueError('Unknown liststyle.')
        return s

    def move(self, x, y):
        raise NotImplementedError

    def to_dict(self):
        return {'narrative': [c.to_dict() for c in self],
                'style': getattr(self, 'html_style', self.default_style)}

    @classmethod
    def from_json(cls, obj):
        narrative = cls()
        for nugget in obj['narrative']:
            narrative.append(Nugget.from_json(nugget))
        narrative.html_style = obj['style']
        return narrative
