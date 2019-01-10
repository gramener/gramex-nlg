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

from nlg import grammar as G

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


class NLGTemplate(object):
    def __init__(
        self,
        template="",
        data=None,
        struct=None,
        tmpl_weights=None,
        tornado_tmpl=False,
        **fmt_kwargs
    ):
        self.tornado_tmpl = tornado_tmpl
        self.fmt = Formatter()
        if struct is None:
            struct = {}
        if data is None:
            self.data = struct.get("data")
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
            intent = struct.get("intent", False)
            if intent:
                self.intent = intent
                self.template = TEMPLATES[self.intent]
            else:
                if "template" not in struct:
                    raise KeyError("Either intent or template must be specified.")
                self.template = struct["template"]
            self.metadata = struct["metadata"]

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
        template = spec.get("template")
        if isinstance(template, str):
            fieldnames = [f for _, f, _, _ in self.fmt.parse(template) if f]
            kwargs = spec.get("kwargs", {})
            if kwargs:
                return all([f in kwargs for f in fieldnames])
            return all([f in template for f in fieldnames])
        return False

    def get_template_kwargs(self, spec):
        """Parse a template dict and find the fieldname kwargs."""
        tmpl = spec.get("template")
        fieldnames = [f for _, f, _, _ in self.fmt.parse(tmpl) if f]
        kwargs = spec.get("kwargs", False)
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
        tmpl = spec["template"]
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
        return all([c in spec for c in ("_type", "colname", "_filter")])

    def process_filter_dict(self, colname, _filter):
        by = _filter["colname"]
        subfilter = _filter["filter"]
        ix = getattr(self.data[by], "idx" + subfilter)()
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
        return ("_type" in spec) and ("expr" in spec)

    def eval_quant(self, _type, expr):
        if _type != "operation":
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
        _, kw, _, _ = list(self.fmt.parse("{{{}}}".format(kw)))[0]
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
        subject = self.metadata.get("subject", False)
        if subject:
            return self.process_pos(subject)
        raise KeyError("Subject not found.")

    @property
    def quant(self):
        quant = self.metadata.get("quant", False)
        if quant:
            return self.process_pos(quant)
        raise KeyError("quant not found.")

    @property
    def verb(self):
        verb = self.metadata.get("verb", False)
        if verb:
            return self.process_pos(verb)
        raise KeyError("verb not found.")

    @property
    def adjective(self):
        adjective = self.metadata.get("adjective", False)
        if adjective:
            return self.process_pos(adjective)
        raise KeyError("adjective not found.")

    @property
    def object(self):
        obj = self.metadata.get("object", False)
        if obj:
            return self.process_pos(obj)
        raise KeyError("Object not found.")

    def is_data_ref(self, s):
        fnames = set([f for _, f, _, _ in self.fmt.parse(s) if f])
        if len(fnames) != 1:
            return False
        _, field = self.fmt.get_field(fnames.pop(), (), {"data": self.data})
        return field == "data"

    def has_fieldname(self, s):
        """Check if a string has a fieldname left in it."""
        return any([f for _, f, _, _ in self.fmt.parse(s) if f])

    def render(self):
        if self.tornado_tmpl:
            return Template(self.template).generate(**self.fmt_kwargs).decode("utf-8")
        try:
            s = self.template.format(**self.fmt_kwargs)
            if not self.has_fieldname(s):
                return s
        except KeyError:
            pass

        fmt_kwargs = {}
        if not hasattr(self, "intent"):
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
    if method == "mode":
        value = value.iloc[0]
    return value


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
    data = struct["data"]
    results = struct["metadata"]["results"]
    colname = results["colname"]
    items = getattr(data[colname], results["method"])()
    return G.concatenate_items(items)


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

    template = "{subject} {verb} {object} {preposition} {prep_object}"
    fmt_kwargs = {}
    for _, fieldname, _, _ in Formatter().parse(template):
        if not fieldname.startswith("_"):
            func = getattr(G, "make_" + fieldname, G.keep_fieldname)
            fmt_kwargs[fieldname] = func(struct)
    fmt_kwargs.update(kwargs)
    sentence = template.format(**fmt_kwargs)
    if not append_results:
        return sentence
    results = get_literal_results(struct)
    return sentence + ": " + results


def _process_urlparams(handler):
    df = pd.read_csv(handler.args["data"][0])
    with open(handler.args["metadata"][0], "r") as f_in:
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
    return descriptive({"data": data, "metadata": metadata})


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
    template = "{subject} {verb} {superlative} {object} {preposition} {prep_object}"
    fmt_kwargs = {}
    for _, fieldname, _, _ in Formatter().parse(template):
        if not fieldname.startswith("_"):
            func = getattr(G, "make_" + fieldname, G.keep_fieldname)
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
    return superlative({"data": data, "metadata": metadata})


if __name__ == "__main__":
    df = pd.read_csv("data/assembly.csv")
    df["vote_share"] = (
        df.pop("Vote share").apply(lambda x: x.replace("%", "")).astype(float)
    )
    tmpl = """BJP won a voteshare of {x}% in {y}, followed by {a}% in {b} and
    {c}% in {d}."""
    N = NLGTemplate(
        tmpl,
        data=df,
        x="{data.vote_share[0]}",
        y="{data.AC[0]}",
        a="{data.vote_share[1]}",
        b="{data.AC[1]}",
        c="{data.vote_share[2]}",
        d="{data.AC[2]}",
    )
    print(N)
