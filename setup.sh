#! /bin/sh
#
# setup.sh
# Copyright (C) 2019 jaidevd <jaidevd@brainiac>
#
# Distributed under terms of the MIT license.
#

set -x

git clean -fdx
/home/ubuntu/anaconda3/bin/pip install -e .
/home/ubuntu/anaconda3/bin/python -m spacy download en_core_web_sm
