#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Module for gramex exposure. This shouldn't be imported anywhere, only for use
with gramex.
"""
import json
import os.path as op
from urllib import parse

import pandas as pd
from tornado.template import Template

from nlg import Narrative
from nlg import grammar as G
from nlg import templatize
from nlg import utils as U

fpath = 'app/gramupload/file.csv'

if op.isfile(fpath):
    orgdf = pd.read_csv(fpath)


def _watchfile_loader(event):
    global orgdf
    if op.isfile(event.src_path):
        orgdf = pd.read_csv(event.src_path)


def render_template(handler):
    payload = parse.parse_qsl(handler.request.body.decode("utf8"))
    payload = dict(payload)
    templates = json.loads(payload["template"])
    df = pd.read_json(payload["data"], orient="records")
    fh_args = json.loads(payload.get("args", {}))
    # fh_args = {k: [x.lstrip('-') for x in v] for k, v in fh_args.items()}
    resp = []
    for t in templates:
        rendered = Template(t).generate(
            orgdf=orgdf, df=df, fh_args=fh_args, G=G, U=U).decode('utf8')
        rendered = rendered.replace('-', '')
        grmerr = U.check_grammar(rendered)
        resp.append({'text': rendered, 'grmerr': grmerr})
    return json.dumps(resp)


def process_template(handler):
    payload = parse.parse_qsl(handler.request.body.decode("utf8"))
    payload = dict(payload)
    text = json.loads(payload["text"])
    df = pd.read_json(payload["data"], orient="records")
    args = json.loads(payload.get("args", {}))
    if args is None:
        args = {}
    resp = []
    for t in text:
        grammar_errors = U.check_grammar(t)
        replacements, t, infl = templatize(t, args.copy(), df)
        resp.append({
            "text": t, "tokenmap": replacements, 'inflections': infl,
            "fh_args": args, "setFHArgs": False, "grmerr": grammar_errors})
    return json.dumps(resp)


def download_template(handler):
    tmpl = json.loads(parse.unquote(handler.args["tmpl"][0]))
    conditions = json.loads(parse.unquote(handler.args["condts"][0]))
    fh_args = json.loads(parse.unquote(handler.args["args"][0]))
    template = Narrative(tmpl, conditions).templatize()
    t_template = Template(U.NARRATIVE_TEMPLATE)
    return t_template.generate(tmpl=template, fh_args=fh_args, G=G).decode("utf8")


def download_config(handler):
    payload = {}
    payload['config'] = json.loads(parse.unquote(handler.args['config'][0]))
    payload['data'] = json.loads(parse.unquote(handler.args.get('data', [None])[0]))
    payload['name'] = parse.unquote(handler.args['name'][0])
    return json.dumps(payload, indent=4)


def get_gramopts(handler):
    funcs = {}
    for attrname in dir(G):
        obj = getattr(G, attrname)
        if getattr(obj, 'gramopt', False):
            funcs[obj.fe_name] = {'source': obj.source, 'func_name': attrname}
    return funcs
