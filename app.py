__author__ = 'erickaltman'
import os
import re
import mimetypes
import subprocess
from flask import Flask, Blueprint, redirect, request, url_for, Response
from flask import render_template, send_file, jsonify
from database import DatabaseManager as dbm
from schema import (
    GAME_CITE_REF,
    PERF_CITE_REF,
    GAME_SCHEMA_VERSION,
    PERF_SCHEMA_VERSION,
    generate_cite_ref
)


app = Flask(__name__)
data_source = Blueprint('data_source', __name__, static_folder='./data')
app.register_blueprint(data_source)

@app.route("/")
def start_page():
    return "Main page coming soon..."

@app.route('/data/<source_hash>/<filename>')
def data(source_hash, filename):
    return send_file_partial("./data/{}/{}".format(source_hash, filename))

@app.route("/citation/<uuid>")
def citation_page(uuid):
    dbm.connect_to_db()
    game_ref = dbm.retrieve_game_ref(uuid)
    perf_ref = dbm.retrieve_perf_ref(uuid)
    derived_performances = dbm.retrieve_derived_performances(uuid)
    previous_performances = dbm.retrieve_performance_chain(uuid)[:-1]
    dbm.db.close()
    if game_ref:
        return render_template('citation.html',
                               citeref=game_ref,
                               is_game=True,
                               is_performance=False,
                               derived_performances=derived_performances)
    elif perf_ref:
        performance_video = "/data/{}/{}".format(perf_ref['replay_source_file_ref'],
                                                 perf_ref['replay_source_file_name'])
        return render_template('citation.html',
                               citeref=perf_ref,
                               is_game=False,
                               is_performance=True,
                               previous_performances=previous_performances,
                               performance_video=performance_video)
    return "No record found, sorry."


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

    location_info = {'gif_location': '/data/{0}/gif/{1}_{2}/{3}_{1}_{2}.gif'.format(
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