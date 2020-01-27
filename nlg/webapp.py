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
import pandas as pd
from six.moves.urllib import parse
from tornado.template import Loader, Template

from nlg import grammar, utils, templatize, grammar_options

DATAFILE_EXTS = {'.csv', '.xls', '.xlsx', '.tsv'}
NARRATIVE_CACHE = {}

nlg_path = op.join(variables['GRAMEXDATA'], 'nlg')
nlp = utils.load_spacy_model()
tmpl_loader = Loader(op.join(op.dirname(__file__), "app", "templates"), autoescape=None)

if not op.isdir(nlg_path):
    os.mkdir(nlg_path)


def get_narrative_cache(handler):
    return {k: [n.to_dict() for n in v] for k, v in NARRATIVE_CACHE.items()}


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
    nugget = NARRATIVE_CACHE[handler.session['id']][int(nugget_id)]
    if not variable_ix.isdigit():
        variable_i = map(int, variable_ix.split(","))
    else:
        variable_i = int(variable_ix)
    variable = nugget.get_var(variable_i).to_dict()
    tmpl = tmpl_loader.load("variable-settings.tmpl")
    return tmpl.generate(
        variable=variable, nugget_id=nugget_id, variable_id=variable_ix,
        grammar_options=grammar_options)


def set_variable_settings_tmpl(handler):
    nugget_id, variable_ix = handler.path_args
    nugget = NARRATIVE_CACHE[handler.session['id']][int(nugget_id)]
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
    nugget = NARRATIVE_CACHE[handler.session['id']][int(handler.path_args[0])]
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
    orgdf = get_original_df(handler)
    nrid = payload['nrid']
    if not nrid.endswith('.json'):
        nrid += '.json'
    df = pd.DataFrame.from_records(payload['data'])
    nrpath = op.join(nlg_path, handler.current_user.id, nrid)
    with open(nrpath, 'r') as fout:  # noqa: No encoding for json
        templates = json.load(fout)
    narratives = []
    for t in templates['config']:
        tmpl = utils.add_html_styling(t['template'], payload['style'])
        s = Template(tmpl).generate(df=df, fh_args=t.get('fh_args', {}),
                                    G=grammar, U=utils, orgdf=orgdf)
        rendered = s.decode('utf8')
        narratives.append(rendered)
    return '\n'.join(narratives)


def get_original_df(handler):
    """Get the original dataframe which was uploaded to the webapp."""
    data_dir = get_user_dir(handler)
    with open(op.join(data_dir, 'meta.cfg'), 'r') as fout:  # noqa: No encoding for json
        meta = json.load(fout)
    dataset_path = op.join(data_dir, meta['dsid'])
    return pd.read_csv(dataset_path, encoding='utf-8')


def render_template(handler):
    """Render a set of templates against a dataframe and formhandler actions on it."""
    orgdf = get_original_df(handler)
    nugget = NARRATIVE_CACHE[handler.session['id']][int(handler.path_args[0])]
    return nugget.render(orgdf)


def save_nugget(sid, nugget):
    narrative = NARRATIVE_CACHE.get(sid, [])
    narrative.append(nugget)
    if len(narrative) > 0:
        NARRATIVE_CACHE[sid] = narrative
    outpath = op.join(nlg_path, sid + ".json")
    with open(outpath, 'w', encoding='utf8') as fout:
        json.dump([n.to_dict() for n in narrative], fout, indent=4)


def process_text(handler):
    """Process English text in the context of a df and formhandler arguments
    to templatize it."""
    payload = json.loads(handler.request.body.decode('utf8'))
    df = pd.DataFrame.from_records(payload['data'])
    args = payload.get('args', {}) or {}
    nugget = templatize(nlp(payload['text']), args.copy(), df)
    save_nugget(handler.session['id'], nugget)
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


def save_config(handler):
    """Save the current narrative config.
    (to $GRAMEXDATA/{{ handler.current_user.id }})"""
    payload = {}
    for k in ['config', 'name', 'dataset']:
        payload[k] = parse.unquote(handler.args[k][0])
    payload['config'] = json.loads(payload['config'])
    nname = payload['name']
    if not nname.endswith('.json'):
        nname += '.json'
    payload['dataset'] = parse.unquote(handler.args['dataset'][0])
    fpath = op.join(get_user_dir(handler), nname)
    with open(fpath, 'w') as fout:  # noqa: No encoding for json
        json.dump(payload, fout, indent=4)


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
        config_path = op.join(data_dir, config_name)
        # shutil.copy(config_path, op.join(local_data_dir, 'config.json'))
        meta['nrid'] = op.basename(config_path)

    # write meta config
    with open(op.join(data_dir, 'meta.cfg'), 'w') as fout:  # NOQA
        json.dump(meta, fout, indent=4)


def edit_narrative(handler):
    """Set the handler's narrative and dataset ID to the current session."""
    user_dir = op.join(nlg_path, handler.current_user.id)
    dataset_name = handler.args.get('dsid', [''])[0]
    narrative_name = handler.args.get('nrid', [''])[0] + '.json'
    with open(op.join(user_dir, 'meta.cfg'), 'w') as fout:  # NOQA: no encoding for JSON
        json.dump({'dsid': dataset_name, 'nrid': narrative_name}, fout, indent=4)


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
        return meta
    return {}
