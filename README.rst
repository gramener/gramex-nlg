|Build Status|

nlg
===

Natural Language Generation component for
`Gramex <https://github.com/gramener/gramex>`__. The NLG module is
designed to work as a Python library, as well as a `Gramex
application <https://learn.gramener.com/guide/apps/#gramex-apps>`__.

The library:

1. Automatically creates tornado templates from English text in the
   context of a dataset.
2. Allows for modification and generalization of these templates.
3. Renders these templates as a unified narrative.

Installation
------------

The NLG library can be installed from PyPI as follows:

.. code:: bash

    $ pip install nlg
    $ gramex setup nlg/app

or from source as follows:

.. code:: bash

    $ git clone https://github.com/gramener/gramex-nlg.git
    $ cd gramex-nlg
    $ pip install -e .
    $ gramex setup ./app

Usage
-----

Using the Python library
~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    >>> import pandas as pd
    >>> from gramex import data

    >>> # load some data
    >>> df = pd.read_csv('iris.csv')

    >>> # specify a FormHandler operation - find the average sepal_width per species
    >>> fh_args = {'_by': ['species'], '_c': ['sepal_width|avg'], '_sort': ['sepal_width|avg']}

    >>> # Draw a sample
    >>> xdf = df.sample(frac=0.1, random_state=10)

    >>> # perform the FormHandler operation on the data
    >>> print(data.filter(xdf, fh_args.copy()))
          species  sepal_width|avg
    2   virginica             2.70
    1  versicolor             2.92
    0      setosa             3.15

    >>> # Write something about the output
    >>> text = "The virginica species has the least average sepal_width."

    >>> # Generate a template
    >>> from nlg.search import templatize, render
    >>> tmpl = templatize(text, fh_args, xdf)
    >>> print(tmpl)
    {% set fh_args = {"_by": ["species"], "_c": ["sepal_width|avg"], "_sort": ["sepal_width|avg"]}  %}
    {% set df = U.grmfilter(orgdf, fh_args.copy()) %}
    The {{ df["species"].iloc[0] }} species has the least average {{ fh_args["_sort"][0].lower() }}.

    >>> # Render the same template with new data.
    >>> print(render(df, tmpl).decode('utf8'))
    The versicolor species has the least average sepal_width|avg.

Using the NLG IDE
~~~~~~~~~~~~~~~~~

The NLG module ships with an IDE. The IDE is a `Gramex
application <https://learn.gramener.com/guide/apps/>`__.

To use it, install the NLG module as indicated above, and add the
following to your ``gramex.yaml``:

.. code:: yaml

    variables:
      NLG_ROOT:
        function: nlg.utils._locate_app_config()

    import:
      nlg:
        path: $NLG_ROOT
        YAMLURL: $YAMLURL/nlg/

This configuration mounts the app at the ``/nlg`` resource.

The Gramex NLG IDE
------------------

The NLG component depends on two sources of information:

1. A source dataset, which can be uploaded on to the IDE. A dataset is
   uniquely identified with its filename. Once uploaded, the file
   persists and is available for selection from the app. Any *file* that
   makes a valid URL for
   `FormHandler <http://learn.gramener.com/guide/formhandler>`__ can be
   used with the NLG app.
2. A *narrative*, which is a collection of templates and rules around
   them. The narrative consists of the configuration which governs the
   rendered text. An existing narrative can be uploaded through the "Add
   Data" button, or can be created through the IDE. Once created, the
   narrative can be named and becomes available for selection from the
   "Add Data" modal.

The NLG IDE
-----------

The primary purpose of the IDE is to create or edit narratives based on
a dataset. Once a dataset has been selected, it is exposed in the IDE as
a `FormHandler
table <https://learn.gramener.com/guide/formhandler/#formhandler-tables>`__.

.. figure:: doc/images/nlg-ide-input.png
   :alt: 

Users can now type English text into the IDE and add it to the
narrative. This automatically templatizes the text, and adds the
template to the narrative. For example, typing "Humphrey Bogart is at
the top of the list." does this:

.. figure:: doc/images/nlg-ide-toplist.gif
   :alt: 

This means that the input statement has been templatized and added to
the narrative. The part of the input text that was successfully
templatized is highlighted in green. Clicking on the spanner button next
to a template opens the `Template Settings <#template-settings>`__
modal.

Template Settings
-----------------

.. figure:: doc/images/nlg-template-settings.png
   :alt: 

This dialog provides configuration options for all template attributes:

1. **Template Name** - Each template can optionally be named.
2. **Condition** - Any Python expression which evaluates to a boolean
   may be set as a condition, which controls whether the template is
   rendered.
3. The actual Tornado template itself can be edited. Any valid Tornado
   template is acceptable.
4. **Token Settings** - Every token from the input text that finds a
   match in the dataset or in FormHandler arguments (i.e. every token
   that is highlighted in the preview) is converted into a `template
   expression <https://www.tornadoweb.org/en/stable/template.html#syntax-reference>`__.
   Such tokens have their own attributes, as follows:

   -  **Token search results** - if a token is found in more than one
      place (say, a dataframe cell as well as a FormHandler argument),
      this setting allows the user to select the right result.
   -  **Grammar options** - the NLG engine may automatically apply
      certain string formatting or lexical operations to the template
      expression to make it match the input text. Any number of these
      operations can be enabled / disabled through this setting.
   -  **Make variable** - a token may be set as a local variable within
      the template.
   -  **Ignore** - the template expression corresponding to the token
      may be ignored, and set back to the literal input text.

5. **Run Template** - Run the current template against the dataframe and
   preview its output.
6. **Save Template** - Save the template. Note that this is required if
   the template has been manually edited in the textarea.

Naming and Saving a Narrative
-----------------------------

Once a narrative has been fully configured, it can be named and saved.
Doing so causes it to appear the narrative dropdown menu on the app.

Sharing a Narrative
-------------------

After a narrative has been named and saved, it be shared in two modes:

1. **IDE mode** - This option lets users copy a URL that redirects to
   the IDE, with the current dataset and the current narrative set in
   the session.
2. **Embed mode** - Copy an HTML snippet to embed into a page which
   contains a Formhandler table. The template will render live as the
   table changes.

.. |Build Status| image:: https://travis-ci.org/gramener/gramex-nlg.svg?branch=dev
   :target: https://travis-ci.org/gramener/gramex-nlg
