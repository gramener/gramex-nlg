import sys

__version__ = '0.1.2'

try:
    __NLG_SETUP__
except NameError:
    __NLG_SETUP__ = False


if __NLG_SETUP__:
    sys.stderr.write('Partial import of nlg during the build process.\n')
else:
    from .search import templatize  # NOQA: F401
    from .grammar import get_gramopts
    grammar_options = get_gramopts()
    __all__ = ['templatize', 'grammar_options']
