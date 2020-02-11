# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Search tools.
"""

from itertools import chain
import warnings

import numpy as np
import pandas as pd
from tornado.template import Template

from nlg import grammar
from nlg import narrative
from nlg import utils

SEARCH_PRIORITIES = [
    # {'type': 'doc'},
    {'type': 'ne'},  # A match which is a named entity gets the highest priority
    {'location': 'fh_args'},  # than one that is a formhandler arg
    {'location': 'colname'},  # than one that is a column name
    {'type': 'quant'},  # etc
    {'location': 'cell'}
]


def _sort_search_results(items, priorities=SEARCH_PRIORITIES):
    """
    Sort a list of search results by `priorities`.

    Parameters
    ----------
    items : dict
        Dictionary containing search results, where keys are tokens and values
        are lists of locations where the token was found. Preferably this should
        be a `DFSearchResults` object.
    priorities : list, optional
        List of rules that allow sorting of search results. A `rule` is any
        subset of a search result dictionary. Lower indices indicate higher priorities.

    Returns
    -------
    dict
        Prioritized search results - for each {token: search_matches} pair, sort
        search_matches such that a higher priority search result is enabled.
    """
    if len(items) > 1:
        match_ix = [[p.items() <= item.items() for p in priorities] for item in items]
        min_match = [m.index(True) for m in match_ix]
        items[min_match.index(min(min_match))]['enabled'] = True
    else:
        items[0]['enabled'] = True
    return items


def _preprocess_array_search(text, array, literal=False, case=False, lemmatize=True,
                             nround=False):
    nlp = utils.load_spacy_model()
    if case or nround:
        raise NotImplementedError

    if literal and lemmatize:
        warnings.warn('Ignoring lemmatization.')

    if not (literal or lemmatize):
        warnings.warn(
            'One of `literal` or `lemmatize` must be True. Falling back to lemmatize=True')
        literal, lemmatize = False, True

    if literal:  # ignore every other flag else
        tokens = pd.Series([c.text for c in text], index=text)

    elif lemmatize:
        tokens = pd.Series([c.lemma_ for c in text], index=text)
        if array.ndim == 1:
            array = array.map(nlp)
            array = pd.Series([token.lemma_ for doc in array for token in doc])
        elif array.ndim == 2:
            for col in array.columns[array.dtypes == np.dtype('O')]:
                s = [c if isinstance(c, str) else str(c) for c in array[col]]
                s = [nlp(c) for c in s]
                try:
                    array[col] = [token.lemma_ for doc in s for token in doc]
                except ValueError:
                    warnings.warn('Cannot lemmatize multi-word cells.')
                    if not case:  # still need to respect the `case` param
                        array[col] = array[col].str.lower()

    return tokens, array


def _remerge_span_tuples(results):
    # re-merge span objects that end up as tuples; see issue #25
    unmerged_spans = [k for k in results if isinstance(k, tuple)]
    for span in unmerged_spans:
        start, end = span[0].idx, span[-1].idx + len(span[-1])
        new_span = span[0].doc.char_span(start, end)
        results[new_span] = results.pop(span)
    return results


def _text_search_array(text, array, case=False):
    array = array.astype(str)
    if not case:
        stext = text.lower()
        if array.ndim == 1:
            array = array.map(lambda x: x.lower())
        elif array.ndim == 2:
            for col in array:
                array[col] = array[col].str.lower()
    else:
        stext = text
    mask = array == stext
    if not mask.any(axis=None):
        return []
    indices = mask.values.nonzero()
    if array.ndim == 1:
        return indices[0]
    if array.ndim == 2:
        return indices


def _search_1d_array(text, array, literal=False, case=False, lemmatize=True,
                     nround=False):
    tokens, array = _preprocess_array_search(text, array, literal, case, lemmatize, nround)
    mask = array.isin(tokens)
    if not mask.any():
        return {}
    if isinstance(mask, pd.Series):
        nz = mask.to_numpy().nonzero()[0]
    else:
        nz = mask.nonzero()[0]
    indices = {array[i]: i for i in nz}
    tk = tokens[tokens.isin(array)]
    return _remerge_span_tuples({token: indices[s] for token, s in tk.items()})


def _search_2d_array(text, array, literal=False, case=False, lemmatize=True, nround=False):
    array = array.astype(str)
    tokens, array = _preprocess_array_search(text, array, literal, case, lemmatize, nround)
    mask = array.isin(tokens.values)
    if not mask.any().any():
        return {}
    indices = {array.iloc[i, j]: (i, j) for i, j in zip(*mask.values.nonzero())}
    tk = tokens[tokens.isin(array.values.ravel())]
    return _remerge_span_tuples({token: indices[s] for token, s in tk.items()})


def _df_maxlen(df):
    # Find the length of the longest string present in the columns, indices or values of a df
    col_max = max([len(c) for c in df.columns.astype(str)])
    ix_max = max([len(c) for c in df.index.astype(str)])
    array_max = max([df[c].astype(str).apply(len).max() for c in df])
    return max(col_max, ix_max, array_max)


# TODO: Can this be done with defaultdict?
class DFSearchResults(dict):
    """A convenience wrapper around `dict` to collect search results.

    Different from `dict` in that values are always lists, and setting to
    existing key appends to the list.
    """

    def __setitem__(self, key, value):
        if key not in self:
            super(DFSearchResults, self).__setitem__(key, [value])
        elif self[key][0] != value:
            self[key].append(value)

    def update(self, other):
        # Needed because the default update method doesn't seem to use setitem
        for k, v in other.items():
            self[k] = v

    def clean(self):
        """Sort the search results for each token by priority and un-overlap tokens."""
        for k, v in self.items():
            _sort_search_results(v)
        # unoverlap the keys
        to_remove = []
        for k in self:
            to_search = self.keys() - {k}
            if utils.is_overlap(k, to_search):
                to_remove.append(k)
        for i in to_remove:
            del self[i]


class DFSearch(object):
    """Make a dataframe searchable."""

    def __init__(self, df, nlp=None, **kwargs):
        """Default constrictor.

        Parameters
        ----------
        df : pd.DataFrame
            The dataframe to search.
        nlp : A `spacy.lang` model, optional
        """
        self.df = df
        # What do results contain?
        # A map of tokens to list of search results.
        self.results = DFSearchResults()
        if not nlp:
            nlp = utils.load_spacy_model()
        self.matcher = kwargs.get('matcher', utils.make_np_matcher(nlp))
        self.ents = []

    def search(self, text, colname_fmt='df.columns[{}]',
               cell_fmt='df["{}"].iloc[{}]', **kwargs):
        """
        Search the dataframe.

        Parameters
        ----------
        text : spacy.Doc
            The text to search.
        colname_fmt : str, optional
            String format to describe dataframe columns in the search results,
            can be one of 'df.columns[{}]' or 'df[{}]'.
        cell_fmt : str, optional
            String format to describe dataframe values in the search results.
            Can be one of 'df.iloc[{}, {}]', 'df.loc[{}, {}]', 'df[{}][{}]', etc.

        Returns
        -------
        dict
            A dictionary who's keys are tokens from `text` found in
            the source dataframe, and values are a list of locations in the df
            where they are found.
        """
        self.search_nes(text)
        if len(text.text) <= _df_maxlen(self.df):
            for i in _text_search_array(text.text, self.df.columns):
                self.results[text] = {'location': 'colname', 'tmpl': colname_fmt.format(i),
                                      'type': 'doc'}
            for x, y in zip(*_text_search_array(text.text, self.df)):
                x = utils.sanitize_indices(self.df.shape, x, 0)
                y = utils.sanitize_indices(self.df.shape, y, 1)
                self.results[text] = {
                    'location': 'cell', 'tmpl': cell_fmt.format(self.df.columns[y], x),
                    'type': 'doc'}

        else:
            for token, ix in self.search_columns(text, **kwargs).items():
                ix = utils.sanitize_indices(self.df.shape, ix, 1)
                self.results[token] = {'location': 'colname', 'tmpl': colname_fmt.format(ix),
                                       'type': 'token'}

            for token, (x, y) in self.search_table(text, **kwargs).items():
                x = utils.sanitize_indices(self.df.shape, x, 0)
                y = utils.sanitize_indices(self.df.shape, y, 1)
                self.results[token] = {
                    'location': 'cell', 'tmpl': cell_fmt.format(self.df.columns[y], x),
                    'type': 'token'}
            self.search_quant([c for c in text if c.pos_ == 'NUM'])
        # self.search_derived_quant([c.text for c in selfdoc if c.pos_ == 'NUM'])

        return self.results

    def search_nes(self, doc, colname_fmt='df.columns[{}]', cell_fmt='df["{}"].iloc[{}]'):
        """Find named entities in text, and search for them in the dataframe.

        Parameters
        ----------
        text : str
            The text to search.
        """
        self.ents = utils.ner(doc, self.matcher)
        for token, ix in self.search_columns(self.ents, literal=True).items():
            ix = utils.sanitize_indices(self.df.shape, ix, 1)
            self.results[token] = {
                'location': 'colname',
                'tmpl': colname_fmt.format(ix), 'type': 'ne'
            }
        for token, (x, y) in self.search_table(self.ents, literal=True).items():
            x = utils.sanitize_indices(self.df.shape, x, 0)
            y = utils.sanitize_indices(self.df.shape, y, 1)
            self.results[token] = {
                'location': 'cell',
                'tmpl': cell_fmt.format(self.df.columns[y], x), 'type': 'ne'}

    def search_table(self, text, **kwargs):
        """Search the `.values` attribute of the dataframe for tokens in `text`."""
        kwargs['array'] = self.df.copy()
        return self._search_array(text, **kwargs)

    def search_columns(self, text, **kwargs):
        """Search df columns for tokens in `text`."""
        kwargs['array'] = self.df.columns
        return self._search_array(text, **kwargs)

    def search_quant(self, quants, nround=2, cell_fmt='df["{}"].iloc[{}]'):
        """Search the dataframe for a set of quantitative values.

        Parameters
        ----------
        quants : list / array like
            The values to search.
        nround : int, optional
            Numeric values in the dataframe are rounded to these many
            significant digits before searching.
        """
        dfclean = utils.sanitize_df(self.df, nround)
        qarray = np.array([c.text for c in quants])
        quants = np.array(quants)
        n_quant = qarray.astype('float').round(nround)
        for x, y in zip(*dfclean.isin(n_quant).values.nonzero()):
            x = utils.sanitize_indices(dfclean.shape, x, 0)
            y = utils.sanitize_indices(dfclean.shape, y, 1)
            tk = quants[n_quant == dfclean.iloc[x, y]][0]
            self.results[tk] = {
                'location': 'cell', 'tmpl': cell_fmt.format(self.df.columns[y], x),
                'type': 'quant'}

    def search_derived_quant(self, quants, nround=2):
        """Search the common derived dataframe parameters for a set of quantitative values.

        Parameters
        ----------
        quants : list / array like
            The values to search.
        nround : int, optional
            Numeric values in the dataframe are rounded to these many
            significant digits before searching.
        """
        dfclean = utils.sanitize_df(self.df, nround)
        quants = np.array(quants)
        #  n_quant = quants.astype('float').round(2)

        for num in quants:
            if int(num) == len(dfclean):
                self.results[num] = {
                    'location': 'cell', 'tmpl': "len(df)",
                    'type': 'quant'}

    def _search_array(self, text, array, literal=False,
                      case=False, lemmatize=True, nround=False):
        """Search for tokens in text within an array.

        Parameters
        ----------
        text : str or spacy document
            Text to search
        array : array-like
            Array to search in.
        literal : bool, optional
            Whether to match tokens to values literally.
        case : bool, optional
            If true, run a case sensitive search.
        lemmatize : bool, optional
            If true (default), search on lemmas of tokens and values.
        nround : int, optional
            Significant digits used to round `array` before searching.

        Returns
        -------
        dict
            Mapping of tokens to a sequence of indices within `array`.

        Example
        -------
        >>> _search_array('3', np.arange(5))
        {'3': [3]}
        >>> df = pd.DataFrame(np.eye(3), columns='one punch man'.split())
        >>> _search_array('1', df.values)
        {'1': [(0, 0), (1, 1), (2, 2)]}
        >>> _search_array('punched man', df.columns)
        {'punched': [1], 'man': [2]}
        >>> _search_array('1 2 buckle my shoe', df.index)
        {'1': [1], '2': [2]}
        """
        if array.ndim == 1:
            func = _search_1d_array
        else:
            func = _search_2d_array
        return func(text, array, literal, case, lemmatize, nround)
        # if len(res) == 0:  # Fall back on searching the whole string, not just the entities
        #     res = func([text], array, literal, case, lemmatize, nround)
        # return res


def _search_fh_args(entities, args, key, lemmatized):
    colnames = args.get(key, False)
    if not colnames:
        return {}
    nlp = utils.load_spacy_model()
    argtokens = list(chain(*[nlp(c) for c in colnames]))
    res = {}
    for i, token in enumerate(argtokens):
        for ent in entities:
            if lemmatized and (token.lemma_ == ent.lemma_):
                match = True
            elif token.text == ent.text:
                match = True
            else:
                match = False
            if match:
                res[ent] = {
                    'type': 'token', 'tmpl': f"fh_args['{key}'][{i}]",
                    'location': 'fh_args'
                }
    return res


def _search_groupby(entities, args, lemmatized=True):
    return _search_fh_args(entities, args, key='_by', lemmatized=lemmatized)


def _search_sort(entities, args, lemmatized=True):
    return _search_fh_args(entities, args, key='_sort', lemmatized=lemmatized)


def _search_select(entities, args, lemmatized=True):
    return _search_fh_args(entities, args, key='_c', lemmatized=lemmatized)


def search_args(entities, args, lemmatized=True, fmt='fh_args["{}"][{}]',
                argkeys=('_sort', '_by', '_c')):
    """
    Search formhandler arguments provided as URL query parameters.

    Parameters
    ----------
    entities : list
        list of named entities found in the source text
    args : dict
        FormHandler args as parsed by g1.url.parse(...).searchList
    lemmatized : bool, optional
        whether to search on lemmas of text values
    fmt : str, optional
        String format used to describe FormHandler arguments in the template
    argkeys : list, optional
        Formhandler argument keys to be considered for the search. Any key not
        present in this will be ignored.
        # TODO: Column names can be keys too!!

    Returns
    -------
    dict
        Mapping of entities / tokens to objects describing where they are found
        in Formhandler arguemnts. Each search result object has the following
        structure:
        {
            'type': 'some token',
            'location': 'fh_args',
            'tmpl': 'fh_args['_by'][0]'  # The template that gets this token from fh_args
        }
    """
    args = {k: v for k, v in args.items() if k in argkeys}
    search_res = {}
    entities = list(chain(*entities))
    search_res.update(_search_groupby(entities, args, lemmatized=lemmatized))
    search_res.update(_search_sort(entities, args, lemmatized=lemmatized))
    search_res.update(_search_select(entities, args, lemmatized=lemmatized))
    return search_res


def _search(text, args, df, copy=False):
    """Construct a tornado template which regenerates some
    text from a dataframe and formhandler arguments.

    The pipeline consists of:
    1. cleaning the text and the dataframe
    2. searching the dataframe and FH args for tokens in the text
    3. detecting inflections on the tokens.

    Parameters
    ----------
    text : spacy.Doc
        Input text
    args : dict
        Formhandler arguments
    df : pd.DataFrame
        Source dataframe.

    Returns
    --------
    tuple
        of search results, cleaned text and token inflections. The webapp uses
        these to construct a tornado template.
    """
    # utils.load_spacy_model()
    if copy:
        df = df.copy()
    df = utils.gfilter(df, args.copy())
    # Do this only if needed:
    # clean_text = utils.sanitize_text(text.text)
    args = utils.sanitize_fh_args(args, df)
    # Is this correct?
    dfs = DFSearch(df)
    dfix = dfs.search(text)
    dfix.update(search_args(dfs.ents, args))
    dfix.clean()
    inflections = grammar.find_inflections(dfix, args, df)
    _infl = {}
    for token, funcs in inflections.items():
        _infl[token] = []
        for func in funcs:
            _infl[token].append({
                'source': func.source,
                'fe_name': func.fe_name,
                'func_name': func.__name__
            })
    # FIXME: Why return text if it's unchanged?
    return dfix, text, _infl


def _make_inflection_string(tmpl, infl):
    source = infl['source']
    func_name = infl['func_name']
    if source == 'str':
        tmpl += f'.{func_name}()'
    else:
        tmpl = f'{source}.{func_name}({tmpl})'
    return tmpl


def templatize_token(token, results, inflection):
    for r in results:
        if r.get('enabled', False):
            break
    tmpl = r['tmpl']
    if inflection:
        for i in inflection:
            tmpl = _make_inflection_string(tmpl, i)
    return narrative.t_templatize(tmpl)


def templatize(text, args, df):
    """Construct an NLG Nugget which templatizes the given text in
    the context of a dataframe, and FormHandler operations on it.

    Parameters
    ----------
    text : spacy.tokens.Doc
        Input document
    args : dict
        Formhandler arguments
    df : pd.DataFrame
        Source dataframe.

    Returns
    -------
    nlg.narrative.Nugget
        An NLG Nugget object containing the template for the input text.

    Example
    -------
    >>> from gramex import data
    >>> from nlg.utils import load_spacy_model
    >>> df = pd.read_csv('iris.csv')
    >>> fh_args = {'_by': ['species']}
    >>> df = data.filter(df, fh_args.copy())
    >>> nlp = load_spacy_model()
    >>> text = 'The iris dataset has 3 species - setosa, versicolor and virginica.'
    >>> nugget = templatize(text, fh_args, df)
    >>> print(template)
    {% set fh_args = {"_by": ["species"]}  %}
    {% set df = U.gfilter(orgdf, fh_args.copy()) %}
    The iris dataset has 3 {{ df.columns[0] }} - {{ df["species"].iloc[0] }}, \
{{ df["species"].iloc[1] }} and {{ df["species"].iloc[-1] }}.
    """
    dfix, clean_text, infl = _search(text, args, df)
    return narrative.Nugget(clean_text, dfix, infl, args)


def add_manual_template(input_template, manual_template=None):
    """Append user defined template for any word in the original text.

    Parameters
    ----------
    input_template : str
        Input text
    manual_template : dict
        Doct to add with key=word in the text, valu=dataframe expression


    Returns
    -------
    str
        Tornado template corresponding to the text and data.

    Example
    -------
    input_template = "The iris dataset has 3 {{ df.columns[0] }} - {{ df["species"].iloc[0] }}, \
{{ df["species"].iloc[1] }} and {{ df["species"].iloc[-1] }}."
    manual_template = {"3" :  "{{ "+ len(df["species"].unique()) + " }}" }

    output_template = "The iris dataset has  "{{ "+ len(df["species"].unique()) + \
        " }}"  {{ df.columns[0] }} - {{ df["species"].iloc[0] }}, \
        {{ df["species"].iloc[1] }} and {{ df["species"].iloc[-1] }}."

    """
    if manual_template is None:
        return input_template

    for key in manual_template:
        replace_with = "{{ " + manual_template[key][0]['tmpl'] + " }}"
        input_template = input_template.replace(key, replace_with)
    return input_template


def render(df, template):
    return Template(template).generate(orgdf=df, U=utils, G=grammar)
