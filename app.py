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
    performance_video = "/{}/{}.mov".format(perf_ref['replay_source_file_ref'], perf_ref['title'])
    dbm.db.close()
    if game_ref:
        return render_template('citation.html',
                               citeref=game_ref,
                               is_game=True,
                               is_performance=False,
                               derived_performances=derived_performances)
    elif perf_ref:
        return render_template('citation.html',
                               citeref=perf_ref,
                               is_game=False,
                               is_performance=True,
                               previous_performances=previous_performances,
                               performance_video=performance_video)
    return "No record found, sorry."

if __name__ == '__main__':
    app.run()
