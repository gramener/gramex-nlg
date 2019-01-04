import random
import re


QUANT_FILTER_TOKENS = {
    '>=': ['at least', 'more than', 'over'],
    '<=': ['at most', 'less than', 'below'],
    '==': ['of'],
    '<': ['less than'],
    '>': ['more than']
}


keep_fieldname = lambda x: '{{}}'.format(x)  # NOQA: E731


def get_quant_qualifier_value(value):
    for k, v in QUANT_FILTER_TOKENS.items():
        if re.match('^' + k, value):
            return random.choice(v), value.lstrip(k)


def make_verb(struct):
    verb = struct['metadata']['verb']
    if not isinstance(verb, str) and len(verb) > 1:
        return random.choice(verb)
    return verb


def make_subject(struct, use_colname=True):
    '''Find the subject of the insight and return as a standalone phrase.
    '''
    tokens = ['The']
    metadata = struct['metadata']
    subject = metadata['subject']['value']
    tokens.append(subject)
    colname = metadata['subject'].get('column')
    if colname and use_colname:
        tokens.append(colname)
    return ' '.join(tokens)


def make_object(struct, *args, **kwargs):
    '''
    '''
    tokens = ['a']
    filters = struct['metadata']['filters']
    for i, f in enumerate(filters):
        tokens.append(f['column'])
        tokens.append('of')
        tokens.extend(get_quant_qualifier_value(f['filter']))
        if i < len(filters) - 1:
            tokens.append('and')
    return ' '.join(tokens)


def make_superlative(struct, *args, **kwargs):
    '''
    '''
    tokens = ['the']
    mdata = struct['metadata']
    tokens.append(random.choice(mdata['superlative']))
    return ' '.join(tokens)
