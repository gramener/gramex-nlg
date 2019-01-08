#! /bin/sh
#
# setup.sh
# Copyright (C) 2019 jaidevd <jaidevd@brainiac>
#
# Distributed under terms of the MIT license.
#


/home/anaconda3/bin/python setup.py develop
/home/anaconda3/bin/python -m spacy download en
