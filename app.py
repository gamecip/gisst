__author__ = 'erickaltman'
import os
import re
import mimetypes
import subprocess
import json
import base64
import datetime
import fnmatch
import shutil
import hashlib
from collections import OrderedDict
from flask import Flask, Blueprint, redirect, request, url_for, Response
from flask import render_template, send_file, jsonify
from database import DatabaseManager as dbm
from database import (
    LOCAL_GAME_DATA_STORE,
    LOCAL_DATA_ROOT
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
    save_file_to_store,
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
    game_ref = dbm.retrieve_game_ref(uuid)
    perf_ref = dbm.retrieve_perf_ref(uuid)
    derived_performances = dbm.retrieve_derived_performances(uuid)
    previous_performances = dbm.retrieve_performance_chain(uuid)[:-1]
    save_states = dbm.retrieve_save_state(game_uuid=uuid)
    extra_files = dbm.retrieve_file_path(game_uuid=uuid)

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


@app.route("/json/state_info/<uuid>")
def emulation_info_state(uuid):
    state_info = {}
    state_ref = dbm.retrieve_save_state(uuid=uuid)[0]
    other_save_states = dbm.retrieve_save_state(game_uuid=state_ref['game_uuid'])
    state_extra_files = dbm.retrieve_file_path(save_state_uuid=uuid)
    state_info['record'] = state_ref
    state_info['availableStates'] = filter(lambda s: True if s.get('save_state_source_data') else False, other_save_states)
    state_info['fileMapping'] = {k: os.path.join('/game_data', v, k.split('/')[-1]) for k, v in map(lambda x: (x['file_path'], x['source_data']),
                                                                                      state_extra_files)} if state_extra_files else None
    state_info['fileInformation'] = {f['file_path']: f for f in state_extra_files}
    #   Save data is singular, and probably LZMA compressed
    if state_ref['save_state_source_data']:
        state_info['stateFileURL'] = os.path.join('/cite_data', state_ref['save_state_source_data'], '{}'.format(state_ref['uuid']))

    #   Save data is multiple and probably run length encoded
    if state_ref['rl_starts_data'] and state_ref['rl_lengths_data']:
        state_info['rlStartsURL'] = os.path.join('/cite_data', state_ref['rl_starts_data'], '{}'.format(state_ref['uuid']))
        state_info['rlLengthsURL'] = os.path.join('/cite_data', state_ref['rl_lengths_data'], '{}'.format(state_ref['uuid']))

    if state_extra_files:
        main_exec = dbm.retrieve_file_path(save_state_uuid=uuid, main_executable=True)[0]
        state_info['gameFileURL'] = os.path.join('/game_data', main_exec['source_data'], main_exec['file_path'].split('/')[-1])
    else:
        game_ref = dbm.retrieve_game_ref(state_ref['game_uuid'])
        state_info['gameFileURL'] = os.path.join('/game_data', game_ref['source_data'], game_ref['data_image_source'])
    return jsonify(state_info)

@app.route("/json/game_info/<uuid>")
def emulation_info_game(uuid):
    game_info = {}
    game_ref = dbm.retrieve_game_ref(uuid)
    game_extra_files = dbm.retrieve_file_path(game_uuid=uuid, save_state_uuid=None)

    if game_ref and (game_ref['data_image_source'] or game_extra_files):
        gis = game_ref['data_image_source']
        gsd = game_ref['source_data']
        main_exec = dbm.retrieve_file_path(game_uuid=uuid, save_state_uuid=None, main_executable=True)
        main_fp = main_exec[0]['file_path'].split('/')[-1] if main_exec else None
        game_info['gameFileURL'] = os.path.join('/game_data', gsd, gis) if gis else main_fp
        if game_extra_files:
            game_info['fileMapping'] = {k: os.path.join('/game_data', v, k.split('/')[-1]) for k, v in map(lambda x: (x['file_path'], x['source_data']),
                                                                                     game_extra_files)}
            game_info['fileInformation'] = {f['file_path']: f for f in game_extra_files}
        game_info['stateFileURL'] = None
        game_info['record'] = game_ref.elements
        game_info['availableStates'] = filter(lambda s: True if s.get('save_state_source_data') or s.get('rl_starts_data') else False, dbm.retrieve_save_state(game_uuid=uuid))
    return jsonify(game_info)

@app.route("/json/performance_info/<uuid>")
def performance_info(uuid):
    perf_info = {}
    perf_ref = dbm.retrieve_perf_ref(uuid)
    perf_info['record'] = perf_ref.elements
    perf_info['linkedStates'] = dbm.retrieve_all_state_perf_links(uuid)
    return jsonify(perf_info)


@app.route("/play/<uuid>")
def play_page(uuid):
    init_state = request.values.get('init_state')
    cite_ref = dbm.retrieve_game_ref(uuid)
    state_dicts = dbm.retrieve_save_state(game_uuid=uuid)

    if init_state:
        init_state = dbm.retrieve_save_state(uuid=init_state)[0]
        has_exec = dbm.retrieve_file_path(save_state_uuid=init_state['uuid'], main_executable=True)
    else:
        has_exec = dbm.retrieve_file_path(game_uuid=uuid, save_state_uuid=None, main_executable=True)

    if cite_ref and (cite_ref['data_image_source'] or has_exec):
        return render_template('play.html',
                               init_state=init_state,
                               cite_ref=cite_ref,
                               state_dicts=state_dicts,
                               state_headers=dbm.headers[dbm.GAME_SAVE_TABLE])
    return "No game data source found, sorry!"


@app.route("/extra_file/<uuid>/add", methods=['POST'])
def add_extra_file(uuid):
    extra_file_b64 = request.form.get('extra_file_data')
    sha1_hash = request.form.get('sha1_hash')
    data_length = int(request.form.get('data_length'))
    file_name = request.form.get('file_name')
    rel_file_path = request.form.get('rel_file_path')
    is_executable = request.form.get('is_executable')
    main_executable = request.form.get('main_executable')
    decoded_b64 = base64.b64decode(extra_file_b64)
    extra_b_array = bytearray(decoded_b64)

    if len(extra_b_array) != data_length:
        extra_b_array.extend([0 for _ in range(len(extra_b_array), data_length)])

    hash_check = get_byte_array_hash(extra_b_array)
    if hash_check != sha1_hash:
        print "{} hash: {} not equal to client hash: {}".format(file_name, hash_check, sha1_hash)

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
    return jsonify(file_path)


@app.route("/state/<uuid>/add", methods=['POST'])
def add_save_state(uuid):
    performance_uuid = request.form.get('performance_uuid')
    performance_time_index = request.form.get('performance_time_index')

    #   Save State File to DB
    fields = OrderedDict(
        description=request.form.get('description'),
        game_uuid=uuid,
        save_state_type='state',
        emulator_name=request.form.get('emulator'),
        emulator_version=request.form.get('emulator_version'),
        emt_stack_pointer=request.form.get('emt_stack_pointer'),
        stack_pointer=request.form.get('stack_pointer'),
        system_time=request.form.get('time'),
        created_on=None,
        created=datetime.datetime.now()
    )
    state_uuid = dbm.add_to_save_state_table(fts=True, **fields)

    #   Attach performance information if present
    if performance_uuid:
        #   Sometimes a state maybe linked to a performance without a specific index?
        if performance_time_index:
            dbm.link_save_state_to_performance(uuid, performance_uuid, performance_time_index)
        else:
            dbm.link_save_state_to_performance(uuid, performance_uuid, 0)

    #   Retrieve save state information to get uuid and ignore blank fields
    save_state = dbm.retrieve_save_state(uuid=state_uuid)[0]
    return jsonify({'record': save_state})

@app.route("/state/<uuid>/add_data", methods=['POST'])
def add_save_state_data(uuid):
    save_state_data = request.form.get('buffer')
    compressed = True if request.form.get('compressed') == u'true' else False
    data_length = int(request.form.get('data_length'))

    save_state_b_array = bytearray(base64.b64decode(save_state_data))

    #   The base64 library will interpret trailing zeros as padding and remove them, this adds them back in
    if len(save_state_b_array) != data_length:
        save_state_b_array.extend([0 for _ in range(len(save_state_b_array), data_length)])

    source_data_hash, file_name = save_byte_array_to_store(save_state_b_array, file_name=uuid)
    dbm.update_table(dbm.GAME_SAVE_TABLE,
                     ['save_state_source_data', 'compressed'],
                     [source_data_hash, compressed],
                     ['uuid'], [uuid])
    return jsonify({'record': dbm.retrieve_save_state(uuid=uuid)[0]})

@app.route("/state/<uuid>/add_rl_data", methods=['POST'])
def add_rl_save_state_data(uuid):
    rl_starts_b64 = request.form.get('rl_starts')
    rl_lengths_b64 = request.form.get('rl_lengths')
    rl_total_length = int(request.form.get('rl_total_length'))
    rl_lengths_length = int(request.form.get('rl_lengths_length'))
    rl_starts_length = int(request.form.get('rl_starts_length'))

    rl_starts_b_array = bytearray(base64.b64decode(rl_starts_b64))
    rl_lengths_b_array = bytearray(base64.b64decode(rl_lengths_b64))

    if len(rl_starts_b_array) != rl_starts_length:
        rl_starts_b_array.extend([0 for _ in range(len(rl_starts_b_array), rl_starts_length)])

    if len(rl_lengths_b_array) != rl_lengths_length:
        rl_lengths_b_array.extend([0 for _ in range(len(rl_lengths_b_array), rl_lengths_length)])

    rl_start_hash, file_name = save_byte_array_to_store(rl_starts_b_array, file_name=uuid)
    rl_lengths_hash, file_name = save_byte_array_to_store(rl_lengths_b_array, file_name=uuid)

    dbm.update_table(dbm.GAME_SAVE_TABLE,
                     ['rl_starts_data','rl_lengths_data','rl_total_length','compressed'],
                     [rl_start_hash, rl_lengths_hash, rl_total_length, True],
                     ['uuid'], [uuid])

    return jsonify({'record': dbm.retrieve_save_state(uuid=uuid)[0]})


@app.route("/state/<uuid>/update", methods=['POST'])
def update_save_state(uuid):
    update_fields = json.loads(request.form.get('update_fields'))

    #   if linking to a performance, do that and then throw away since GAME_SAVE_TABLE doesn't refer to performance
    if 'performance_uuid' in update_fields:
        performance_uuid = update_fields['performance_uuid']
        performance_time_index = update_fields['performance_time_index']
        dbm.link_save_state_to_performance(uuid, performance_uuid, performance_time_index)
        del update_fields['performance_uuid']
        del update_fields['performance_time_index']

    #   make sure that there are still fields to update
    if len(update_fields.keys()) > 0:
        dbm.update_table(dbm.GAME_SAVE_TABLE, update_fields.keys(),update_fields.values, ['uuid'], [uuid])
    return jsonify({'record': dbm.retrieve_save_state(uuid=uuid)[0]})

@app.route("/performance/<uuid>/add", methods=['POST'])
def performance_add(uuid):
    game_ref = dbm.retrieve_game_ref(uuid)
    title = request.form.get('title', 'A performance of {}'.format(game_ref['title']))
    description = request.form.get('description')
    perf_ref = generate_cite_ref(PERF_CITE_REF, PERF_SCHEMA_VERSION,
                                 game_uuid=uuid, title=title, description=description)
    dbm.add_to_citation_table(perf_ref, fts=True)
    return jsonify({'record': perf_ref.elements})

@app.route("/performance/<uuid>/add_video_data", methods=['POST'])
def performance_add_data(uuid):
    sha1_hash = request.form.get('sha1_hash')
    chunk_id = request.form.get('chunk_id')
    total_chunks = int(request.form.get('total_chunks'))
    chunk_data = request.form.get('chunk_data')
    chunk_size = int(request.form.get('chunk_size'))

    save_state_b_array = bytearray(base64.b64decode(chunk_data))

    #   The base64 library will interpret trailing zeros as padding and remove them, this adds them back in
    if len(save_state_b_array) != chunk_size:
        save_state_b_array.extend([0 for _ in range(len(save_state_b_array), chunk_size)])

    #   If there isn't a temp directory for this hash, create one
    temp_path = os.path.join(LOCAL_DATA_ROOT, "tmp_{}".format(sha1_hash))
    if not os.path.exists(temp_path):
        os.makedirs(temp_path)

    #   Write the chunk of data to a temp file
    with open("{}/{}_of_{}".format(temp_path, (int(chunk_id) + 1), total_chunks), "wb") as temp:
        temp.write(save_state_b_array)

    chunk_paths = [chunk for chunk in fnmatch.filter(os.listdir(temp_path), "*_of_*")]

    #   See if all the chunks are written, if so concatenate into final file and add that to storage
    if total_chunks == len(chunk_paths):
        final_name = "final_{}.mp4".format(sha1_hash)
        final_path = os.path.join(temp_path, final_name)
        final_file = open(final_path, "ab")

        for cp in sorted(chunk_paths, key=lambda p: int(p.split("_")[0])):
            with open("{}/{}".format(temp_path, cp), "rb") as cf:
                final_file.write(cf.read())

        final_file.close()
        final_hash = save_file_to_store(final_path)
        shutil.rmtree(temp_path)

        #   Attach data to performance record
        dbm.update_table(dbm.PERFORMANCE_CITATION_TABLE,
                         ['replay_source_file_ref', 'replay_source_file_name'],
                         [final_hash, final_name],
                         ["uuid"], [uuid])
    return "OK"


@app.route("/performance/<uuid>/update", methods=['POST'])
def performance_update(uuid):
    update_fields = json.dumps(request.form.get('updateFields'))
    dbm.update_table(dbm.PERFORMANCE_CITATION_TABLE, update_fields.keys(), update_fields.values(), ["uuid"], [uuid])
    perf_ref = dbm.retrieve_perf_ref(uuid)
    dbm.update_table(dbm.FTS_INDEX_TABLE, ['content'], [perf_ref.to_json_string()],["uuid"], [uuid])
    return perf_ref.to_json_string()


@app.route("/citation/<cite_type>/add", methods=['POST'])
def citation_add(cite_type):
    clean_params = dict([(k, v) for k, v in request.form.items() if not v or v != 'None'])
    if cite_type == GAME_CITE_REF:
        cite = generate_cite_ref(GAME_CITE_REF, GAME_SCHEMA_VERSION, **clean_params)
    elif cite_type == PERF_CITE_REF:
        cite = generate_cite_ref(PERF_CITE_REF, PERF_SCHEMA_VERSION, **clean_params)
    dbm.add_to_citation_table(cite, fts=True)
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
    all_game_cites = [dbm.create_cite_ref_from_db(GAME_CITE_REF, x) for x in dbm.retrieve_all_from_table(dbm.GAME_CITATION_TABLE)]
    all_perf_cites = [dbm.create_cite_ref_from_db(PERF_CITE_REF, x) for x in dbm.retrieve_all_from_table(dbm.PERFORMANCE_CITATION_TABLE)]
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