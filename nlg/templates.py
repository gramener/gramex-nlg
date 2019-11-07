#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Templates used in Gramex NLG.
"""
import random
import re


from nlg import grammar as G  # noqa: N812

TEMPLATES = {
    "extreme": "{subject} {verb} the {adjective} {object}.",
    "comparison": "{subject} {verb} {quant} {adjective} than {object}.",
}

FUNC_EXPR = re.compile(r"^(?P<filter>[a-z|A-Z]{1}[a-z|A-Z|_|\d]+)\((?P<colname>.*)\)")


def parse_func_expr(expr):
    m = re.match(FUNC_EXPR, expr)
    if m is None:
        raise ValueError("Invalid Expression")
    return {"colname": m.group("colname"), "filter": m.group("filter")}


class Description(object):
    """Generate general purpose natural language descriptions of dataframes."""

    prefixes = ["This dataset contains "]
    metadata_tmpl = "{rowname} for {n_rows} {entities}."

    def __init__(self, df, entity="", attributes=""):
        """

        Parameters
        ----------
        df : `pandas.DataFrame`
            The source dataframe
        entity : str
            A named entity to represent the rows in the dataframe. For example,
            in Fisher's Iris dataset, the entity would be 'Iris flower
            samples', and in the Boston house pricing dataset it would be
            'Houses in Boston'.
        attributes : str
            A collective name to represent which attributes of `entity` are
            captured in the columns of the dataframe. For example, in the iris
            dataset, this would be 'petal and sepal measurements' and in the
            Boston house pricing dataset this would be 'real estate details'.
        """
        self.df = df
        self.attributes = attributes
        self.entity = entity
        # self.clean()
        self.categoricals = [
            c
            for c, d in df.dtypes.iteritems()
            if d.name in ("object", "bool", "category")
        ]
        self.numericals = [c for c, d in df.dtypes.iteritems() if d in (float, int)]
        self.desc = df[self.numericals].describe()
        self.indices = self.find_possible_indices()

    def find_possible_indices(self):
        """Find columns from the dataframe which can serve as indices.

        Any categorical column from the dataset which contains as many unique
        elements as the length of the dataframe can be used as an index."""
        indices = []
        for col in self.categoricals:
            if self.df[col].nunique() == self.df.shape[0]:
                indices.append(col)
        return indices

    def sentences(self):
        """Get the final narrative as a list of sentences."""
        return (
            self.get_metadata()
            + self.narrate_categoricals()  # NOQA: W503
            + self.narrate_numericals()  # NOQA: W503
        )

    def render(self, sep="\n", *args, **kwargs):
        """Generate the narration string.

        Parameters
        ----------
        sep : str
            Separator used to join individual sentences.

        Returns
        -------
        str
            The final narration.
        """
        return sep.join(self.sentences())

    def clean(self):
        self.df.dropna(inplace=True)
        self.df.drop_duplicates(inplace=True)

    def get_metadata(self):
        """Get the metadata of the dataframe as an English sentence. It
        contains details like the entity, attributes and the size of the
        dataset."""
        if self.indices and not self.entity:
            self.entity = random.choice(self.indices)
        entity = G.plural(self.entity)
        prefix = [random.choice(self.prefixes)]
        prefix.append(
            self.metadata_tmpl.format(
                rowname=self.attributes, n_rows=self.df.shape[0], entities=entity
            )
        )
        return prefix

    def common_categoricals(self, top_n=5):
        """Find the most common occurences of each categorical feature.

        Parameters
        ----------
        top_n : int
            Number of most frequent values to count.

        Returns
        -------
        dict
            A dictionary with keys as the column names and values as lists of
            the most common occurences of the feature.
        """
        results = {}
        if isinstance(top_n, int):
            top_n = [top_n] * len(self.categoricals)
        for i, colname in zip(top_n, self.categoricals):
            if colname not in self.indices:
                vcs = self.df[colname].value_counts()
                results[colname] = vcs[:i].index
        return results

    def narrate_categoricals(self, top_n=5):
        """Generate sentences that describe categorical variables.

        Parameters
        ----------
        top_n : int
            Number of most frequent values to count.

        Returns
        -------
        list
            A list of sentences.
        """
        sentences = []
        for k, v in self.common_categoricals(top_n).items():
            k = G.plural(k)
            n_items = len(v)
            values = G.concatenate_items(v)
            if n_items < top_n:
                top_n = n_items
                sent = "The {0} unique {1} are {2}."
            else:
                sent = "The top {0} {1} are {2}."
            sentences.append(sent.format(top_n, k, values))
        return sentences

    def narrate_numericals(self):
        """Generate sentences that describe numerical variables.

        Returns
        -------
        list
            A list of sentences.
        """
        sentences = []
        tmpl = "{colname} {verb} between {min} and {max} at an average of {mean}."
        for col in self.desc:
            colname = col.capitalize() if not col.isupper() else col
            verb = "vary" if G.is_plural(col) else "varies"
            sentences.append(
                tmpl.format(
                    colname=colname,
                    min=self.desc[col]["min"],
                    max=self.desc[col]["max"],
                    mean=self.desc[col]["mean"],
                    verb=verb,
                )
            )
        return sentences
