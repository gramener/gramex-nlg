#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Miscellaneous utilities.
"""
from inflect import engine

infl = engine()


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
    s = sep.join(list(items)[:-1])
    if sep == ', ':
        s += ' and ' + items[-1]
    return s


def pluralize(word):
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
    if not infl.singular_noun(word):
        word = infl.plural(word)
    return word
