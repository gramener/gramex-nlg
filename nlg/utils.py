#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Miscellaneous utilities.
"""
from random import choice
from inflect import engine
import humanize  # NOQA: F401

infl = engine()
is_plural = infl.singular_noun


def humanize_timeperiod(start, end='now', resolution='days'):
    """

    Parameters
    ----------

    start : vartype
        start is
    end : vartype
        end is
    resolution : vartype
        resolution is

    Returns
    -------

    """


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
    if len(items) == 0:
        return ''
    if len(items) == 1:
        return items[0]
    items = list(map(str, items))
    if sep == ', ':
        s = sep.join(items[:-1])
        s += ' and ' + items[-1]
    else:
        s = sep.join(items)
    return s


def plural(word):
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


def singular(word):
    if is_plural(word):
        word = infl.singular_noun(word)
    return word


def pluralize_by_seq(word, by):
    """Pluralize a word depending on a sequence."""
    if len(by) > 1:
        return plural(word)
    return singular(word)


def humanize_comparison(x, y, bit, lot):
    if x == y:
        return choice(['the same', 'identical'])
    if x > y:
        comparative = choice(['higher', 'more', 'greater'])
    else:
        comparative = choice(['less', 'lower'])
    if lot(x, y):
        adj = choice(['a lot', 'much'])
    elif bit(x, y):
        adj = choice(['a little', 'a bit'])
    else:
        adj = ''
    return ' '.join([adj, comparative])
