# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Module for gramex exposure. This shouldn't be imported anywhere, only for use
with gramex.
"""
import glob
import json
import os
import os.path as op

from gramex.config import variables
from gramex.config import app_log  # noqa: F401
import pandas as pd
from tornado.template import Loader

from nlg import utils, templatize, grammar_options
from nlg.narrative import Narrative

DATAFILE_EXTS = {'.csv', '.xls', '.xlsx', '.tsv'}
NARRATIVE_CACHE = {}

nlg_path = op.join(variables['GRAMEXDATA'], 'nlg')
nlp = utils.load_spacy_model()
tmpl_loader = Loader(op.join(op.dirname(__file__), "app", "templates"), autoescape=None)

if not op.isdir(nlg_path):
    os.mkdir(nlg_path)


def get_config_modal(handler):
    return tmpl_loader.load("init-config-modal.tmpl").generate(handler=handler)


def get_narrative_cache(handler):
    narrative = NARRATIVE_CACHE.get(handler.current_user.id, Narrative())
    return json.dumps(narrative.to_dict())


download_narrative = get_narrative_cache
load_narrative = get_narrative_cache


def new_variable_tmpl(handler):
    nugget_id = int(handler.path_args[0])
    variable_ix = handler.path_args[1]
    nugget = NARRATIVE_CACHE[handler.current_user.id][nugget_id]
    start, end = map(int, variable_ix.split(','))
    span = nugget.doc.text[start:end]
    return tmpl_loader.load("new-variable.tmpl").generate(
        nugget_id=nugget_id, text=span, variable_ix=variable_ix)


def add_new_variable(handler):
    nugget = NARRATIVE_CACHE[handler.current_user.id][int(handler.path_args[0])]
    start, end = map(int, handler.path_args[1].split(','))
    nugget.add_var([start, end], expr=handler.args['expr'][0])
    return nugget.template


def get_preview_html(template, interactive=False):
    """get_preview_html

    Parameters
    ----------
        template : {{_type_}}


    Returns
    -------

    Example
    -------
    """
    text = template['text']
    if interactive:
        html = '<span style="background-color:#c8f442" class="cursor-pointer">{}</span>'
    else:
        html = '<span style="background-color:#c8f442">{}</span>'
    l_offset = len(html.format(''))
    offset = 0
    tokenmap = sorted(template['tokenmap'], key=lambda x: x['idx'])
    for token in tokenmap:
        start = token['idx'] + offset
        end = start + len(token['text'])
        prefix = text[:start]
        suffix = text[end:]
        text = prefix + html.format(token['text']) + suffix
        offset += l_offset
    return text


def get_variable_settings_tmpl(handler):
    nugget_id, variable_ix = handler.path_args
    nugget = NARRATIVE_CACHE[handler.current_user.id][int(nugget_id)]
    if not variable_ix.isdigit():
        start, stop = map(int, variable_ix.split(","))
        variable = nugget.get_var((start, stop)).to_dict()
    else:
        variable_i = int(variable_ix)
        variable = nugget.get_var(variable_i).to_dict()
    tmpl = tmpl_loader.load("variable-settings.tmpl")
    return tmpl.generate(
        variable=variable, nugget_id=nugget_id, variable_id=variable_ix,
        grammar_options=grammar_options)


def set_variable_settings_tmpl(handler):
    nugget_id, variable_ix = handler.path_args
    nugget = NARRATIVE_CACHE[handler.current_user.id][int(nugget_id)]
    if not variable_ix.isdigit():
        variable_i = map(int, variable_ix.split(","))
    else:
        variable_i = int(variable_ix)
    variable = nugget.get_var(variable_i)
    # handler.args will be something like
    # {'sourcetext': [''], 'sources': ['0'], 'expr': ['foo'], 'inflections': ['Singularize']}

    expr = handler.args['expr'][0]
    if expr:  # Ignore the default value of the sources dropdown if expression is present
        variable.set_expr(expr)
    else:
        source = int(handler.args['sources'][0])
        if variable.sources[source]['tmpl'] != variable.enabled_source:
            variable.enable_source(source)

    inflections = handler.args.get('inflections', False)
    if inflections:
        variable.inflections = [grammar_options[i] for i in inflections]
    else:
        variable.inflections = []
    return nugget.template


def get_nugget_settings_tmpl(handler):
    nugget = get_nugget(handler)
    return tmpl_loader.load("template-settings.tmpl").generate(template=nugget)


def get_nugget(handler):
    nugget_id = int(handler.path_args[0])
    if 'delete' in handler.args:
        del NARRATIVE_CACHE[handler.current_user.id][nugget_id]
        return NARRATIVE_CACHE[handler.current_user.id].to_dict()
    else:
        nugget = NARRATIVE_CACHE[handler.current_user.id][nugget_id]
        nugget = nugget.to_dict()
        nugget['previewHTML'] = get_preview_html(nugget, True)
        return nugget


def clean_anonymous_files():
    """Remove all files uploaded by anonymous users.
    This may be used at startup when deploying the app."""
    import shutil
    anon_dir = op.join(nlg_path, 'anonymous')
    if op.isdir(anon_dir):
        shutil.rmtree(anon_dir)


def is_user_authenticated(handler):
    """Check if the current user is authenticated."""
    current_user = getattr(handler, 'current_user', False)
    return bool(current_user)


def get_user_dir(handler):
    if is_user_authenticated(handler):
        dirpath = op.join(nlg_path, handler.current_user.id)
    else:
        dirpath = op.join(nlg_path, 'anonymous')
    return dirpath


def render_live_template(handler):
    """Given a narrative ID and df records, render the template."""
    payload = json.loads(handler.request.body)
    df = pd.DataFrame.from_records(payload['data'])
    nrid = payload['nrid']
    if not nrid.endswith('.json'):
        nrid += '.json'
    with open(op.join(get_user_dir(handler), nrid), 'r', encoding='utf8') as fin:
        narrative = json.load(fin)
    narrative = Narrative.from_json(narrative)
    return narrative.to_html(**narrative.html_style, df=df)


def get_style_kwargs(handler_args):
    style_kwargs = {
        'style': handler_args.pop('style', ['para'])[0],
        'liststyle': handler_args.pop('liststyle', ['html'])[0],
    }
    style_kwargs.update({k: json.loads(v[0]) for k, v in handler_args.items()})
    return style_kwargs


def render_narrative(handler):
    orgdf = get_original_df(handler)
    narrative = NARRATIVE_CACHE.get(handler.current_user.id, False)
    if narrative:
        style_kwargs = get_style_kwargs(handler.args)
        pl = {'render': narrative.to_html(**style_kwargs, df=orgdf),
              'style': narrative.html_style}
    else:
        pl = {'render': '', 'style': Narrative.default_style}
    return pl


def get_original_df(handler):
    """Get the original dataframe which was uploaded to the webapp."""
    data_dir = get_user_dir(handler)
    meta_path = op.join(data_dir, 'meta.cfg')
    if op.isfile(meta_path):
        with open(meta_path, 'r') as fout:  # noqa: No encoding for json
            meta = json.load(fout)
        dataset_path = op.join(data_dir, meta['dsid'])
        return pd.read_csv(dataset_path, encoding='utf-8')


def render_template(handler):
    """Render a set of templates against a dataframe and formhandler actions on it."""
    orgdf = get_original_df(handler)
    nugget = NARRATIVE_CACHE[handler.current_user.id][int(handler.path_args[0])]
    return nugget.render(orgdf)


def save_nugget(sid, nugget):
    narrative = NARRATIVE_CACHE.get(sid, Narrative())
    narrative.append(nugget)
    if len(narrative) > 0:
        NARRATIVE_CACHE[sid] = narrative
    # outpath = op.join(nlg_path, sid + ".json")
    # with open(outpath, 'w', encoding='utf8') as fout:
    #     json.dump([n.to_dict() for n in narrative], fout, indent=4)


def process_text(handler):
    """Process English text in the context of a df and formhandler arguments
    to templatize it."""
    payload = json.loads(handler.request.body.decode('utf8'))
    df = pd.DataFrame.from_records(payload['data'])
    args = payload.get('args', {}) or {}
    nugget = templatize(nlp(payload['text']), args.copy(), df)
    save_nugget(handler.current_user.id, nugget)
    nugget = nugget.to_dict()
    nugget['previewHTML'] = get_preview_html(nugget)
    return nugget


def read_current_config(handler):
    """Read the current data and narrative IDs written to the session file."""
    user_dir = get_user_dir(handler)
    meta_path = op.join(user_dir, 'meta.cfg')
    if not op.isdir(user_dir):
        os.mkdir(user_dir)
    if not op.isfile(meta_path):
        return {}
    with open(meta_path, 'r') as fout:  # noqa: No encoding for json
        meta = json.load(fout)
    return meta


def get_dataset_files(handler):
    """Get all filenames uploaded by the user.

    Parameters
    ----------
    handler : tornado.RequestHandler

    Returns
    -------
    list
        List of filenames.
    """
    files = glob.glob('{}/*'.format(get_user_dir(handler)))
    return [f for f in files if op.splitext(f)[-1].lower() in DATAFILE_EXTS]


def get_narrative_config_files(handler):
    """Get list of narrative config files generated by the user.

    Parameters
    ----------
    handler : tornado.RequestHandler

    Returns
    -------
    list
        List of narrative configurations.
    """
    return glob.glob('{}/*.json'.format(get_user_dir(handler)))


def init_form(handler):
    """Process input from the landing page and write the current session config."""
    meta = {}
    data_dir = get_user_dir(handler)
    if not op.isdir(data_dir):
        os.makedirs(data_dir)

    # handle dataset
    data_file = handler.request.files.get('data-file', [{}])[0]
    if data_file:
        # TODO: Unix filenames may not be valid Windows filenames.
        outpath = op.join(data_dir, data_file['filename'])
        with open(outpath, 'wb') as fout:
            fout.write(data_file['body'])
    else:
        dataset = handler.args['dataset'][0]
        outpath = op.join(data_dir, dataset)
    # shutil.copy(outpath, fh_fpath)
    meta['dsid'] = op.basename(outpath)

    # handle config
    config_name = handler.get_argument('narrative', '')
    if config_name:
        outpath = op.join(data_dir, config_name)
        # shutil.copy(config_path, op.join(local_data_dir, 'config.json'))
    else:
        conf_file = handler.request.files.get('config-file', [{}])[0]
        if conf_file:
            outpath = op.join(data_dir, conf_file['filename'])
            with open(outpath, 'wb') as fout:
                fout.write(conf_file['body'])
        else:
            outpath = False
    if outpath:
        meta['nrid'] = op.basename(outpath)

    # write meta config
    with open(op.join(data_dir, 'meta.cfg'), 'w') as fout:  # NOQA
        json.dump(meta, fout, indent=4)


def get_init_config(handler):
    """Get the initial default configuration for the current user."""
    user_dir = get_user_dir(handler)
    metapath = op.join(user_dir, 'meta.cfg')
    if op.isfile(metapath):
        with open(metapath, 'r') as fout:  # NOQA: no encoding for JSON
            meta = json.load(fout)
        config_file = op.join(user_dir, meta.get('nrid', ''))
        if op.isfile(config_file):
            with open(config_file, 'r') as fout:  # NOQA: no encoding for JSON
                meta['config'] = json.load(fout)
            global NARRATIVE_CACHE
            NARRATIVE_CACHE = {}
            NARRATIVE_CACHE[handler.current_user.id] = \
                Narrative.from_json(meta['config'])
            app_log.debug('Initial config loaded from {}'.format(config_file))
            return {'style': NARRATIVE_CACHE[handler.current_user.id].html_style}
    return {}


def save_narrative(handler):
    name = handler.path_args[0]
    if not name.endswith('.json'):
        name += '.json'
    outpath = op.join(get_user_dir(handler), name)
    with open(outpath, 'w', encoding='utf8') as fout:
        json.dump(NARRATIVE_CACHE[handler.current_user.id].to_dict(),
                  fout, indent=4)


def move_nuggets(handler):
    pop, drop = map(int, handler.path_args)
    narrative = NARRATIVE_CACHE[handler.current_user.id]
    popped = narrative.pop(pop)
    narrative.insert(drop, popped)
