#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Module for gramex exposure. This shouldn't be imported anywhere, only for use
with gramex.
"""
from urllib import parse
from nlg import templatize
from nlg import grammar as G
from nlg import Narrative
from nlg.utils import NARRATIVE_TEMPLATE
from tornado.template import Template
import pandas as pd
import json


def render_template(handler):
    payload = parse.parse_qsl(handler.request.body.decode("utf8"))
    payload = dict(payload)
    text = payload["text"]
    df = pd.read_json(payload["data"], orient="records")
    args = parse.parse_qs(payload.get("args", {}))
    return Template(text).generate(df=df, args=args, G=G)


def process_template(handler):
    payload = parse.parse_qsl(handler.request.body.decode("utf8"))
    payload = dict(payload)
    text = payload["text"]
    df = pd.read_json(payload["data"], orient="records")
    args = parse.parse_qs(payload.get("args", {}))
    template, replacements = templatize(text, args, df)
    return {"text": template, "tokenmap": replacements}


def download_template(handler):
    tmpl = json.loads(parse.unquote(handler.args["tmpl"][0]))
    conditions = json.loads(parse.unquote(handler.args["condts"][0]))
    args = json.loads(parse.unquote(handler.args["args"][0]))
    args = parse.parse_qs(args)
    template = Narrative(tmpl, conditions).templatize()
    t_template = Template(NARRATIVE_TEMPLATE)
    return t_template.generate(tmpl=template, args=args, G=G).decode("utf8")
