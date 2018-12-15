#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Parts of speech usually referenced in templates.
"""


class Noun(object):
    """A Standard noun."""
    def __init__(self, token):
        self.multiple = False
        if isinstance(token, list):
            self.multiple = True
        self.token = token

    @property
    def pluralize(self):
        if self.multiple:
            return ', '.join(self.token[:-1]) + ' and ' + self.token[-1]
        return self.token

    __repr__ = pluralize
    __str__ = pluralize
