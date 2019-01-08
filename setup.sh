#! /bin/sh
#
# setup.sh
# Copyright (C) 2019 jaidevd <jaidevd@brainiac>
#
# Distributed under terms of the MIT license.
#

set -ex

python setup.py develop
python -m spacy download en
