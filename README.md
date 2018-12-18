Natual Language Generation Library
==================================

Installation
------------

Download this repository and run the following:

```bash
$ python setup.py install
```

Basic Usage
-----------

Please check [the examples notebook](https://code.gramener.com/cto/nlg/blob/master/examples.ipynb).


Usage with Gramex
-----------------

NLG functions are currently exposed to gramex via [`gramex.handlers.FunctionHandler`](https://learn.gramener.com/guide/functionhandler/). As an example, see the [`gramex.yaml`](https://code.gramener.com/cto/nlg/blob/master/examples.ipynb). Run the following from the nlg directory

```bash
$ gramex init
```

After gramex starts running, try these links:

1. http://localhost:9988/narrate-1?data=data/assembly.csv&metadata=data/desc_metadata.json
2. http://localhost:9988/narrate-2?data=data/voteshare.csv&metadata=data/super_metadata.json


Glossary
--------

1. Nugget - A Python dictionary that is meant to be consumed by a tokenizer.
   (See below)
2. Tokenizer - A Python callable which takes a nugget as an input parameter and
   returns a string. Depending on the type of tokenizer called, it may produce
   a sentence or a phrase.
3. Template - A `string.Template` (or similar) instance which has a preset
   structure for rendering tokenizer outputs.

Writing a *Nugget*
------------------

A *nugget* is a Python dictionary that is meant to be consumed by a tokenizer.
It is supposed to contain at least the following three keys:
* `'intent'`: Refers to the intent of the narrative and has to be one of
  `'extreme'`, `'comparison'` or `'exception'`.
* `'data'`: This can be any Python object holding the source data which is to
  be narrated. Preferably this should be one or more pandas objects. If it is a
  list of dicts, it is interpreted as records (passed to
  `pd.DataFrame.from_records`). If it is a dict of lists, it is passed to
  `pd.DataFrame.from_dict`.
* `'metadata'`: This is a dictionary that contains further details required to
  generate the narrative.


Writing the Nugget Metadata
---------------------------
