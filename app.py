__author__ = 'erickaltman'
from flask import Flask, Blueprint
from flask import render_template
from database import DatabaseManager as dbm
from schema import GAME_CITE_REF, PERF_CITE_REF


app = Flask(__name__)
data_source = Blueprint('data_source', __name__, static_folder='./data')
app.register_blueprint(data_source)

@app.route("/")
def start_page():
    return "Main page coming soon..."

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
        performance_video = "/data/{}/{}.mov".format(perf_ref['replay_source_file_ref'], perf_ref['title'])
        return render_template('citation.html',
                               citeref=perf_ref,
                               is_game=False,
                               is_performance=True,
                               previous_performances=previous_performances,
                               performance_video=performance_video)
    return "No record found, sorry."

@app.route("/citations")
def citations_all_page():
    dbm.connect_to_db()
    all_game_cites = [dbm.create_cite_ref_from_db(GAME_CITE_REF, x) for x in dbm.run_query('select * from game_citation')]
    all_perf_cites = [dbm.create_cite_ref_from_db(PERF_CITE_REF, x) for x in dbm.run_query('select * from performance_citation')]
    return render_template('citations_main.html',
                           all_game_cites=all_game_cites,
                           all_perf_cites=all_perf_cites,
                           perf_headers=all_perf_cites[0].get_element_names(),
                           game_headers=all_game_cites[0].get_element_names())

if __name__ == '__main__':
    app.run()
