from inflect import engine
from tornado.template import Template
from math import floor  # noqa: F401

from nlg.utils import load_spacy_model, set_nlg_gramopt, get_lemmatizer

infl = engine()
nlp = load_spacy_model()


def is_plural_noun(text):
    """Whether given text is a plural noun."""
    doc = load_spacy_model()(text)
    for t in list(doc)[::-1]:
        if not t.is_punct:
            return t.tag_ in ('NNS', 'NNPS')
    return False


is_singular_noun = lambda x: not is_plural_noun(x)  # NOQA: E731


@set_nlg_gramopt(source='G', fe_name='Concate Items')
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
        return ""
    if len(items) == 1:
        return items[0]
    items = list(map(str, items))
    if sep == ', ':
        s = sep.join(items[:-1])
        s += ' and ' + items[-1]
    else:
        s = sep.join(items)
    return s


@set_nlg_gramopt(source='G', fe_name='Pluralize')
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


@set_nlg_gramopt(source='G', fe_name='Singularize')
def singular(word):
    """
    Singularize a word.

    Parameters
    ----------
    word : str
        Word to singularize.

    Returns
    -------
    str
        Singular of `word`.
    """
    if is_plural_noun(word):
        word = infl.singular_noun(word)
    return word


# @set_nlg_gramopt(source='G', fe_name='Pluralize by')
def pluralize_by(word, by):
    """
    Pluralize a word depending on another argument.

    Parameters
    ----------
    word : str
        Word to pluralize
    by : any
        Any object checked for a pluralish value. If a sequence, it must have
        length greater than 1 to qualify as plural.

    Returns
    -------
    str
        Plural or singular of `word`.
    """
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


# @set_nlg_gramopt(source='G', fe_name='Pluralize like')
def pluralize_like(x, y):
    """
    Pluralize a word if another is a plural.

    Parameters
    ----------
    x : str
        The word to pluralize.
    y : str
        The word to check.

    Returns
    -------
    str
        Plural of `x` if `y` is plural, else singular.
    """
    if not is_plural_noun(y):
        return singular(x)
    return plural(x)


@set_nlg_gramopt(source='str', fe_name='Capitalize')
def capitalize(word):
    return word.capitalize()


@set_nlg_gramopt(source='str', fe_name='Lowercase')
def lower(word):
    return word.lower()


@set_nlg_gramopt(source='str', fe_name='Swapcase')
def swapcase(word):
    return word.swapcase()


@set_nlg_gramopt(source='str', fe_name='Title')
def title(word):
    return word.title()


@set_nlg_gramopt(source='str', fe_name='Uppercase')
def upper(word):
    return word.upper()


# @set_nlg_gramopt(source='G', fe_name='Lemmatize')
def lemmatize(word, target_pos):
    return get_lemmatizer()(word, target_pos)


def _token_inflections(x, y):
    """
    If two words share the same root, find lexical changes required for turning
    one into another.

    Parameters
    ----------
    x : spacy.token.Tokens
    y : spacy.token.Tokens

    Examples
    --------
    >>> _token_inflections('language', 'Language')
    ['upper']
    >>> _token_inflections('language', 'languages')
    ['plural']
    """
    if x.lemma_ != y.lemma_:
        return []

    inflections = []

    # check if x and y are singulars or plurals of each other.
    number_infl = _number_inflection(x, y)
    if number_infl:
        inflections.append(number_infl)

    shp_infl = _shape_inflection(x, y, prev=number_infl)
    if shp_infl:
        inflections.append(shp_infl)

    # Disable detecting inflections until they can be
    # processed without intervention.
    # if x.pos_ != y.pos_:
    #     return lemmatize
    return inflections


def _shape_inflection(x, y, prev=False):
    if not prev:
        prev = lambda x: x  # noqa: E731
    if len(prev(x.text)) == len(y.text):
        for methname in ['capitalize', 'lower', 'swapcase', 'title', 'upper']:
            func = lambda x: getattr(x, methname)()  # NOQA: E731
            if func(prev(x.text)) == y.text:
                return globals()[methname]
    return False


def _number_inflection(x, y):
    if is_singular_noun(y.text):
        if singular(x.text).lower() == y.text.lower():
            return singular
    elif is_plural_noun(y.text):
        if plural(x.text).lower() == y.text.lower():
            return plural
    return False


def find_inflections(search, fh_args, df):
    """
    Find lexical inflections between words in input text and the search results
    obtained from FormHandler arguments and dataframes.

    Parameters
    ----------
    search : nlg.search.DFSearchResults
        The DFSearchResults object corresponding to `text` and `df`
    fh_args : dict
        FormHandler arguments.
    df : pandas.DataFrame
        The source dataframe.

    Returns
    -------
    dict
        With keys as tokens found in the dataframe or FH args, and values as
        list of inflections applied on them to make them closer match tokens in `text`.
    """
    inflections = {}
    for token, tklist in search.items():
        tmpl = [t['tmpl'] for t in tklist if t.get('enabled', False)][0]
        rendered = Template('{{{{ {} }}}}'.format(tmpl)).generate(
            df=df, fh_args=fh_args).decode('utf8')
        if rendered != token.text:
            x = nlp(rendered)[0]
            infl = _token_inflections(x, token)
            if infl:
                inflections[token] = infl
    return inflections


def get_gramopts():
    """Find all Grammar and token inflection options from the NLG library.
    Primarily used for creating the select box in the template settings dialog."""
    funcs = {}
    module = globals().copy()
    for attrname in module:
        obj = module[attrname]
        if obj and getattr(obj, 'gramopt', False):
            funcs[obj.fe_name] = {
                'fe_name': obj.fe_name, 'source': obj.source, 'func_name': attrname
            }
    return funcs


if __name__ == "__main__":
    print(get_gramopts())  # noqa
