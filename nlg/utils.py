#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Miscellaneous utilities.
"""
from inflect import engine

infl = engine()
is_plural = infl.singular_noun


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
    if not items:
        return ''
    items = list(map(str, items))
    if sep == ', ':
        s = sep.join(items[:-1])
        s += ' and ' + items[-1]
    else:
        s = sep.join(items)
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
    if not is_plural(word):
        word = infl.plural(word)
    return word
