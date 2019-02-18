#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Module for gramex exposure. This shouldn't be imported anywhere, only for use
with gramex.
"""
import json
import os
import os.path as op
import shutil
from urllib import parse

from gramex.config import variables
from gramex import conf
import pandas as pd
from tornado.template import Template

from nlg import Narrative
from nlg import grammar as G
from nlg import templatize
from nlg import utils as U

local_data_dir = op.join(op.dirname(__file__), "app/gramupload")
if not op.isdir(local_data_dir):
    os.mkdir(local_data_dir)

fh_fpath = op.join(local_data_dir, 'file.csv')
grx_data_dir = variables['GRAMEXDATA']
nlg_path = op.join(grx_data_dir, 'nlg')

if not op.isdir(nlg_path):
    os.mkdir(nlg_path)

if op.isfile(fh_fpath):
    orgdf = pd.read_csv(fh_fpath)


def _watchfile_loader(event):
    global orgdf
    if op.isfile(event.src_path):
        orgdf = pd.read_csv(event.src_path)


def copy_file_to_user_dir(meta, handler):
    for k, v in conf['url'].items():
        if 'nlg-uploadhandler' in k:
            break
    src_dir = v['kwargs']['path']
    dest_dir = op.join(nlg_path, handler.current_user.email)
    if not op.isdir(dest_dir):
        os.mkdir(dest_dir)
    dest_path = op.join(dest_dir, meta.filename)
    shutil.copy(op.join(src_dir, 'file.csv'), dest_path)


def get_dataset_files(handler):
    user_dir = op.join(nlg_path, handler.current_user.email)
    if op.isdir(user_dir):
        return [f for f in os.listdir(user_dir) if not f.endswith('.json')]
    return []


def get_narrative_config_files(handler):
    user_dir = op.join(nlg_path, handler.current_user.email)
    if op.isdir(user_dir):
        return [f for f in os.listdir(user_dir) if f.endswith('.json')]
    return []


def make_dataset_narrative_list(content, handler):
    t = Template(content)
    return t.generate(
        handler=handler,
        NLG_DATASETS=get_dataset_files(handler),
        NLG_NARRATIVES=get_narrative_config_files(handler)).decode('utf-8')


def render_live_template(handler):
    nrid = handler.args['nrid'][0]
    if not nrid.endswith('.json'):
        nrid += '.json'
    data = json.loads(handler.args['data'][0])
    df = pd.DataFrame.from_records(data)
    nrpath = op.join(nlg_path, handler.current_user.email, nrid)
    with open(nrpath, 'r') as fout:
        templates = json.load(fout)
    narratives = []
    for t in templates['config']:
        s = Template(t['template']).generate(df=df, fh_args=t.get('fh_args', {}))
        narratives.append(s.decode('utf-8'))
    return '\n'.join(narratives)


def render_template(handler):
    payload = parse.parse_qsl(handler.request.body.decode("utf8"))
    if not payload:
        payload = json.loads(handler.request.body.decode("utf8"))
        fh_args = payload['args']
        templates = payload['template']
        df = pd.DataFrame.from_records(payload['data'])
    else:
        payload = dict(payload)
        fh_args = json.loads(payload.get("args", {}))
        templates = json.loads(payload["template"])
        df = pd.read_json(payload["data"], orient="records")
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


def save_config(handler):
    payload = {}
    payload['config'] = json.loads(parse.unquote(handler.args['config'][0]))
    payload['name'] = parse.unquote(handler.args['name'][0])
    nname = payload['name']
    if not nname.endswith('.json'):
        nname += '.json'
    payload['dataset'] = parse.unquote(handler.args['dataset'][0])
    fpath = op.join(nlg_path, handler.current_user.email, nname)
    with open(fpath, 'w') as fout:
        json.dump(payload, fout, indent=4)


def get_gramopts(handler):
    funcs = {}
    for attrname in dir(G):
        obj = getattr(G, attrname)
        if getattr(obj, 'gramopt', False):
            funcs[obj.fe_name] = {'source': obj.source, 'func_name': attrname}
    return funcs


def use_existing_file(handler):
    fname = handler.args['dataset'][0]
    user_dir = op.join(nlg_path, handler.current_user.email)
    shutil.copy(op.join(user_dir, fname), fh_fpath)


def init_form(handler):
    meta = {}
    # prioritize files first
    data_dir = op.join(nlg_path, handler.current_user.email)
    if not op.isdir(data_dir):
        os.makedirs(data_dir)

    # handle dataset
    data_file = handler.request.files.get('data-file', [{}])[0]
    if data_file:
        outpath = op.join(data_dir, data_file['filename'])
        with open(outpath, 'wb') as fout:
            fout.write(data_file['body'])
    else:
        dataset = handler.args['dataset'][0]
        outpath = op.join(data_dir, dataset)
    shutil.copy(outpath, fh_fpath)
    meta['dsid'] = op.basename(outpath)

    # handle config
    config_name = handler.args.get('narrative', ['None'])[0]
    if config_name != 'None':
        config_path = op.join(data_dir, config_name)
        shutil.copy(config_path, op.join(local_data_dir, 'config.json'))
        meta['nrid'] = op.basename(config_path)

    # write meta config
    with open(op.join(local_data_dir, 'meta.json'), 'w') as fout:
        json.dump(meta, fout, indent=4)


def edit_narrative(handler):
    user_dir = op.join(nlg_path, handler.current_user.email)

    dataset_name = handler.args.get('dsid', [''])[0]
    if dataset_name:
        shutil.copy(op.join(user_dir, dataset_name), fh_fpath)

    narrative_name = handler.args.get('nrid', [''])[0] + '.json'
    if narrative_name:
        shutil.copy(op.join(user_dir, narrative_name), op.join(local_data_dir, 'config.json'))

    with open(op.join(local_data_dir, 'meta.json'), 'w') as fout:
        json.dump({'dsid': dataset_name, 'nrid': narrative_name}, fout, indent=4)
