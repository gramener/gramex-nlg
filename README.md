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

1. [](http://localhost:9988/narrate-1?data=data/assembly.csv&metadata=data/desc_metadata.json)
2. [](http://localhost:9988/narrate-2?data=data/voteshare.csv&metadata=data/super_metadata.json)
