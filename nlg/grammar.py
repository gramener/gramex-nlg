import random
import re
from inflect import engine

infl = engine()
is_plural = infl.singular_noun

QUANT_FILTER_TOKENS = {
    ">=": ["at least", "more than", "over"],
    "<=": ["at most", "less than", "below"],
    "==": ["of"],
    "<": ["less than"],
    ">": ["more than"],
}


keep_fieldname = lambda x: "{{}}".format(x)  # NOQA: E731


def get_quant_qualifier_value(value):
    for k, v in QUANT_FILTER_TOKENS.items():
        if re.match("^" + k, value):
            return random.choice(v), value.lstrip(k)


def make_verb(struct):
    verb = struct["metadata"]["verb"]
    if not isinstance(verb, str) and len(verb) > 1:
        return random.choice(verb)
    return verb


def make_subject(struct, use_colname=True):
    """Find the subject of the insight and return as a standalone phrase.
    """
    tokens = ["The"]
    metadata = struct["metadata"]
    subject = metadata["subject"]["value"]
    tokens.append(subject)
    colname = metadata["subject"].get("column")
    if colname and use_colname:
        tokens.append(colname)
    return " ".join(tokens)


def make_object(struct, *args, **kwargs):
    """
    """
    tokens = ["a"]
    filters = struct["metadata"]["filters"]
    for i, f in enumerate(filters):
        tokens.append(f["column"])
        tokens.append("of")
        tokens.extend(get_quant_qualifier_value(f["filter"]))
        if i < len(filters) - 1:
            tokens.append("and")
    return " ".join(tokens)


def make_superlative(struct, *args, **kwargs):
    """
    """
    tokens = ["the"]
    mdata = struct["metadata"]
    tokens.append(random.choice(mdata["superlative"]))
    return " ".join(tokens)


def concatenate_items(items, sep=", "):
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
        return ""
    if len(items) == 1:
        return items[0]
    items = list(map(str, items))
    if sep == ", ":
        s = sep.join(items[:-1])
        s += " and " + items[-1]
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
