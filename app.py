__author__ = 'erickaltman'
import os
import re
import mimetypes
import subprocess
import json
import base64
import datetime
import calendar
import shutil
import dateutil.parser
from collections import OrderedDict
from flask import Flask, Blueprint, redirect, request, url_for, Response
from flask import render_template, send_file, jsonify
from database import DatabaseManager as dbm
from database import (
    LOCAL_GAME_DATA_STORE
)
from schema import (
    GAME_CITE_REF,
    PERF_CITE_REF,
    GAME_SCHEMA_VERSION,
    PERF_SCHEMA_VERSION,
    generate_cite_ref
)
from extractors import (
    save_byte_array_to_store,
    get_byte_array_hash
)


app = Flask(__name__)
local_cite_data_path = os.path.expanduser("~/Library/Application Support/citetool-editor/cite_data")
local_game_data_path = os.path.expanduser("~/Library/Application Support/citetool-editor/game_data")
cite_data_source = Blueprint('cite_data_source', __name__, static_url_path='/cite_data', static_folder=local_cite_data_path)
game_data_source = Blueprint('game_data_source', __name__, static_url_path='/game_data', static_folder=local_game_data_path)
app.register_blueprint(cite_data_source)
app.register_blueprint(game_data_source)

@app.route("/")
def start_page():
    return "Main page coming soon..."

@app.route('/cite_data/<source_hash>/<filename>')
def cite_data(source_hash, filename):
    return send_file_partial("{}/{}/{}".format(local_cite_data_path, source_hash, filename))

@app.route('/game_data/<source_hash>/<filename>')
def game_data(source_hash, filename):
    return send_file_partial("{}/{}/{}".format(local_game_data_path, source_hash, filename))

@app.route('/search')
def search():
    search_string = request.args.get('search_query', '')
    search_type = request.args.get('search_type', '')
    if search_string:
        search_json = json.dumps({'start_index':0, 'description':{'title': search_string}})
        if not search_type or search_type == 'all':
            proc_args = ['citetool_editor', '--no_prompts', 'search', search_json]
        elif search_type == 'game':
            proc_args = ['citetool_editor', '--no_prompts', 'search', '--game_only', search_json]
        elif search_type == 'performance':
            proc_args = ['citetool_editor', '--no_prompts', 'search', '--perf_only', search_json]


        results = json.loads(subprocess.check_output(proc_args))
        results['games'] = map(lambda d: dict((i, d[i]) for i in d if i != 'schema_version'), results['games'])
        results['performances'] = map(lambda d: dict((i, d['performance'][i]) for i in d['performance'] if i != 'schema_version'), results['performances'])
        game_results = map(lambda x: generate_cite_ref(GAME_CITE_REF, GAME_SCHEMA_VERSION, **x), results['games'])
        performance_results = map(lambda x: generate_cite_ref(PERF_CITE_REF, PERF_SCHEMA_VERSION, **x), results['performances'])
    else:
        game_results = []
        performance_results = []

    return render_template('search.html',
                           game_results=game_results,
                           performance_results=performance_results,
                           source_type=search_type,
                           prev_query=search_string,
                           total_results=len(game_results) + len(performance_results))


@app.route("/citation/<uuid>")
def citation_page(uuid):
    dbm.connect_to_db()
    game_ref = dbm.retrieve_game_ref(uuid)
    perf_ref = dbm.retrieve_perf_ref(uuid)
    derived_performances = dbm.retrieve_derived_performances(uuid)
    previous_performances = dbm.retrieve_performance_chain(uuid)[:-1]
    save_states = dbm.retrieve_save_state(game_uuid=uuid)
    extra_files = dbm.retrieve_file_path(game_uuid=uuid)
    dbm.db.close()

    if game_ref:
        return render_template('citation.html',
                               citeref=game_ref,
                               is_game=True,
                               is_performance=False,
                               derived_performances=derived_performances,
                               extra_files=extra_files,
                               save_states=save_states)
    elif perf_ref:
        performance_video = "/cite_data/{}/{}".format(perf_ref['replay_source_file_ref'],
                                                      perf_ref['replay_source_file_name'])
        return render_template('citation.html',
                               citeref=perf_ref,
                               is_game=False,
                               is_performance=True,
                               previous_performances=previous_performances,
                               performance_video=performance_video)
    return "No record found, sorry."

@app.route("/json/emulation_info/state/<uuid>")
def emulation_info_state(uuid):
    emu_info = {}
    dbm.connect_to_db()
    state_ref = dbm.retrieve_save_state(uuid=uuid)
    state_extra_files = dbm.retrieve_file_path(save_state_uuid=uuid)
    emu_info['extraFiles'] = {k: os.path.join('/game_data', v, k.split('/')[-1]) for k, v in map(lambda x: (x['file_path'], x['source_data']),
                                                                                      state_extra_files)} if state_extra_files else None
    #TODO: add state filename to the database
    state_epoch_time = calendar.timegm(dateutil.parser.parse(state_ref['created']).timetuple())
    emu_info['freezeFile'] = os.path.join('/cite_data',
                                          state_ref['save_state_source_data'],
                                          '{}_{}'.format(state_ref['game_uuid'], state_epoch_time))
    if state_extra_files:
        main_exec = dbm.retrieve_file_path(save_state_uuid=uuid, main_executable=True)
        emu_info['gameFile'] = os.path.join('/game_data', main_exec['source_data'], main_exec['file_path'].split('/')[-1])
    else:
        game_ref = dbm.retrieve_game_ref(state_ref['game_uuid'])
        emu_info['gameFile'] = os.path.join('/game_data', game_ref['source_data'], game_ref['source_data_image'])
    return jsonify(emu_info)

@app.route("/json/emulation_info/game/<uuid>")
def emulation_info_game(uuid):
    emu_info = {}
    dbm.connect_to_db()
    game_ref = dbm.retrieve_game_ref(uuid)
    game_extra_files = dbm.retrieve_file_path(game_uuid=uuid, save_state_uuid=None)

    if game_ref and (game_ref['data_image_source'] or game_extra_files):
        gis = game_ref['data_image_source']
        gsd = game_ref['source_data']
        main_exec = dbm.retrieve_file_path(game_uuid=uuid, save_state_uuid=None)
        main_sd = main_exec['source_data'] if main_exec else None
        main_fp = main_exec['file_path'].split('/')[-1] if main_exec else None
        emu_info['gameFile'] = os.path.join('/game_data', gis, gsd) if gis else os.path.join('/game_data', main_sd, main_fp)
        emu_info['extraFiles'] = {k: os.path.join('/game_data', v, k.split('/')[-1]) for k, v in map(lambda x: (x['file_path'], x['source_data']),
                                                                                     game_extra_files)}
        emu_info['freezeFile'] = None
    dbm.db.close()
    return jsonify(emu_info)



@app.route("/play/<uuid>")
def play_page(uuid):
    init_state = request.values.get('init_state')
    dbm.connect_to_db()
    cite_ref = dbm.retrieve_game_ref(uuid)
    state_dicts = dbm.retrieve_save_state(game_uuid=uuid)
    dbm.db.close()

    for state in state_dicts:
        state_epoch_time = calendar.timegm(dateutil.parser.parse(state['created']).timetuple())
        state['load_path'] = "/cite_data/{}/{}_{}".format(state['save_state_source_data'],
                                                          state['game_uuid'],
                                                          state_epoch_time)

    if init_state:
        init_state = [state for state in state_dicts if state['uuid'] == init_state][0]

    if cite_ref and cite_ref['data_image_source']:
        return render_template('play.html',
                               init_state=init_state,
                               cite_ref=cite_ref,
                               state_dicts=state_dicts,
                               state_headers=dbm.headers[dbm.GAME_SAVE_TABLE])
    return "No game data image source found, sorry!"


@app.route("/save_extra_file/<uuid>/add", methods=['POST'])
def add_extra_file(uuid):
    extra_file_b64 = request.form.get('extra_file_data')
    file_name = request.form.get('file_name')
    rel_file_path = request.form.get('rel_file_path')
    is_executable = True if request.form.get('is_executable') else False
    main_executable = True if request.form.get('main_executable') else False
    extra_b_array = bytearray(base64.b64decode(extra_file_b64))

    hash_check = get_byte_array_hash(extra_b_array)

    dbm.connect_to_db()

    #   If file with current hash and path already exists, add a new record for save state but
    #   do not create a duplicate file
    file_id = dbm.check_for_existing_file(rel_file_path, hash_check)
    if file_id:
        dbm.link_existing_file_to_save_state(uuid, file_id)
    else:
        source_data_hash, file_name = save_byte_array_to_store(extra_b_array,
                                                               file_name=file_name,
                                                               store_path=LOCAL_GAME_DATA_STORE)
        fields = OrderedDict(
            game_uuid=None,
            save_state_uuid=uuid,
            is_executable=is_executable,
            main_executable=main_executable,
            file_path=rel_file_path,
            source_data=source_data_hash
        )
        state_ref = dbm.retrieve_save_state(uuid=uuid)[0]
        fields['game_uuid'] = state_ref['game_uuid']
        dbm.add_to_file_path_table(**fields)

    file_path = dbm.retrieve_file_path(save_state_uuid=uuid, file_path=rel_file_path)[0]
    dbm.db.close()
    return jsonify(file_path)


@app.route("/save_state/<uuid>/add", methods=['POST'])
def add_save_state(uuid):
    save_state_b_array = bytearray(base64.b64decode(request.form.get('save_state_data')))
    created_time = datetime.datetime.utcnow()
    current_time_epoch = calendar.timegm(created_time.timetuple())
    source_data_hash, file_name = save_byte_array_to_store(save_state_b_array,
                                                           file_name="{}_{}".format(uuid, current_time_epoch))

    #   Save State File to DB
    fields = OrderedDict(
        description=request.form.get('description'),
        game_uuid=uuid,
        performance_uuid=request.form.get('performance_uuid'),
        performance_time_index=request.form.get('performance_time_index'),
        save_state_source_data=source_data_hash,
        save_state_type='state',
        emulator_name=request.form.get('emulator'),
        emulator_version=request.form.get('emulator_version'),
        created_on=None,
        created=created_time
    )
    dbm.connect_to_db()
    dbm.add_to_save_state_table(fts=True, **fields)
    #   Retrieve save state information to get uuid and ignore blank fields
    save_state = dbm.retrieve_save_state(**dict([(k, v) for k, v in fields.items() if v]))[0]
    fields['uuid'] = save_state['uuid']
    fields['id'] = save_state['id']
    fields['epoch_time'] = current_time_epoch
    fields['headers'] = dbm.headers[dbm.GAME_SAVE_TABLE]
    dbm.db.close()
    return jsonify(fields)


@app.route("/citation/<cite_type>/add", methods=['POST'])
def citation_add(cite_type):
    clean_params = dict([(k, v) for k, v in request.form.items() if not v or v != 'None'])
    if cite_type == GAME_CITE_REF:
        cite = generate_cite_ref(GAME_CITE_REF, GAME_SCHEMA_VERSION, **clean_params)
    elif cite_type == PERF_CITE_REF:
        cite = generate_cite_ref(PERF_CITE_REF, PERF_SCHEMA_VERSION, **clean_params)
    dbm.connect_to_db()
    dbm.add_to_citation_table(cite, fts=True)
    dbm.db.close()
    return redirect(url_for('citation_page', uuid=cite['uuid']))


@app.route("/citation/<cite_type>/new")
def citation_new(cite_type):
    if cite_type == GAME_CITE_REF:
        cite = generate_cite_ref(GAME_CITE_REF, GAME_SCHEMA_VERSION)
    elif cite_type == PERF_CITE_REF:
        cite = generate_cite_ref(PERF_CITE_REF, PERF_SCHEMA_VERSION)
    return render_template('citation_new.html', cite_ref=cite, action_url=url_for('citation_add',
                                                                                  cite_type=cite.ref_type))


@app.route("/citations")
def citations_all_page():
    dbm.connect_to_db()
    all_game_cites = [dbm.create_cite_ref_from_db(GAME_CITE_REF, x) for x in dbm.run_query('select * from game_citation')]
    all_perf_cites = [dbm.create_cite_ref_from_db(PERF_CITE_REF, x) for x in dbm.run_query('select * from performance_citation')]
    return render_template('citations_main.html',
                           all_game_cites=all_game_cites,
                           all_perf_cites=all_perf_cites,
                           perf_headers=all_perf_cites[0].get_element_names() if all_perf_cites else [],
                           game_headers=all_game_cites[0].get_element_names() if all_game_cites else [])

@app.route("/gif", methods=["POST"])
def gif():
    start = request.form['startTime']
    end = request.form['endTime']
    uuid = request.form['uuid']
    source_hash = request.form['source_hash']

    subprocess.call(["citetool_editor", "gif_performance", "--regenerate", uuid, start, end])

    location_info = {'gif_location': '/cite_data/{0}/gif/{1}_{2}/{3}_{1}_{2}.gif'.format(
        source_hash,
        start,
        end,
        uuid
    )}

    return jsonify(**location_info)

if __name__ == '__main__':
    app.run()

#   From http://blog.asgaard.co.uk/2012/08/03/http-206-partial-content-for-flask-python
#   Needed to serve video in streaming form expected by browsers
@app.after_request
def after_request(response):
    response.headers.add('Accept-Ranges', 'bytes')
    return response
#   Ditto to above source
def send_file_partial(path):
    """
        Simple wrapper around send_file which handles HTTP 206 Partial Content
        (byte ranges)
        TODO: handle all send_file args, mirror send_file's error handling
        (if it has any)
    """
    range_header = request.headers.get('Range', None)
    if not range_header: return send_file(path)

    size = os.path.getsize(path)
    byte1, byte2 = 0, None

    m = re.search('(\d+)-(\d*)', range_header)
    g = m.groups()

    if g[0]: byte1 = int(g[0])
    if g[1]: byte2 = int(g[1])

    length = size - byte1
    if byte2 is not None:
        length = byte2 - byte1

    data = None
    with open(path, 'rb') as f:
        f.seek(byte1)
        data = f.read(length)

    rv = Response(data,
        206,
        mimetype=mimetypes.guess_type(path)[0],
        direct_passthrough=True)
    rv.headers.add('Content-Range', 'bytes {0}-{1}/{2}'.format(byte1, byte1 + length - 1, size))

    return rv