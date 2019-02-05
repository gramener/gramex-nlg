import random
import re
from inflect import engine
from spacy.lang.en import LEMMA_INDEX, LEMMA_EXC, LEMMA_RULES
from spacy.lemmatizer import Lemmatizer
from tornado.template import Template

from nlg.utils import set_nlg_gramopt, nlp

infl = engine()
L = Lemmatizer(LEMMA_INDEX, LEMMA_EXC, LEMMA_RULES)

QUANT_FILTER_TOKENS = {
    ">=": ["at least", "more than", "over"],
    "<=": ["at most", "less than", "below"],
    "==": ["of"],
    "<": ["less than"],
    ">": ["more than"],
}


keep_fieldname = lambda x: "{{}}".format(x)  # NOQA: E731


def is_plural_noun(text):
    doc = nlp(text)
    for t in list(doc)[::-1]:
        if not t.is_punct:
            return t.tag_ in ('NNS', 'NNPS')
    return False


is_singular_noun = lambda x: not is_plural_noun(x)  # NOQA: E731


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


@set_nlg_gramopt(source='G', fe_name="Concate Items")
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


@set_nlg_gramopt(source='G', fe_name="Pluralize")
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
    if not is_plural_noun(word):
        word = infl.plural(word)
    return word


@set_nlg_gramopt(source='G', fe_name="Singularize")
def singular(word):
    if is_plural_noun(word):
        word = infl.singular_noun(word)
    return word


@set_nlg_gramopt(source='G', fe_name="Pluralize by")
def pluralize_by(word, by):
    """Pluralize a word depending on another argument."""
    if hasattr(by, '__iter__'):
        if len(by) > 1:
            word = plural(word)
        else:
            word = singular(word)
    else:
        if by > 1:
            word = plural(word)
        else:
            word = singular(word)
    return word


@set_nlg_gramopt(source='G', fe_name="Pluralize like")
def pluralize_like(x, y):
    if not is_plural_noun(y):
        return singular(x)
    return plural(x)


@set_nlg_gramopt(source='str', fe_name="Capitalize")
def capitalize(word):
    return word.capitalize()


@set_nlg_gramopt(source='str', fe_name="Lowercase")
def lower(word):
    return word.lower()


@set_nlg_gramopt(source='str', fe_name="Swapcase")
def swapcase(word):
    return word.swapcase()


@set_nlg_gramopt(source='str', fe_name="Title")
def title(word):
    return word.title()


@set_nlg_gramopt(source='str', fe_name="Uppercase")
def upper(word):
    return word.upper()


@set_nlg_gramopt(source="G", fe_name="Lemmatize")
def lemmatize(word, target_pos):
    return L(word, target_pos)


def _token_inflections(x, y):
    """
    Make changes in x lexically to turn it into y.

    Parameters
    ----------
    x : [type]
        [description]
    y : [type]
        [description]
    """
    if x.lemma_ != y.lemma_:
        return False
    if len(x.text) == len(y.text):
        for methname in ['capitalize', 'lower', 'swapcase', 'title', 'upper']:
            func = lambda x: getattr(x, methname)()  # NOQA: E731
            if func(x.text) == y.text:
                return globals()[methname]
    # check if x and y are singulars or plurals of each other.
    if is_singular_noun(y.text):
        if singular(x.text).lower() == y.text.lower():
            return singular
    elif is_plural_noun(y.text):
        if plural(x.text).lower() == y.text.lower():
            return plural
    if x.pos_ != y.pos_:
        return lemmatize
    return False


def find_inflections(text, search, fh_args, df):
    text = nlp(text)
    inflections = {}
    for token, tklist in search.items():
        tmpl = [t['tmpl'] for t in tklist if t.get('enabled', False)][0]
        rendered = Template('{{{{ {} }}}}'.format(tmpl)).generate(
            df=df, fh_args=fh_args).decode('utf8')
        if rendered != token:
            x = nlp(rendered)[0]
            y = text[[c.text for c in text].index(token)]
            infl = _token_inflections(x, y)
            if infl:
                inflections[token] = [infl]
    return inflections
