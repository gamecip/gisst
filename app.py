__author__ = 'erickaltman'
from flask import Flask
from flask import render_template
from database import DatabaseManager as dbm

app = Flask(__name__)


@app.route("/")
def start_page():
    return "Main page coming soon..."

@app.route("/citation/<uuid>")
def citation_page(uuid):
    pass


if __name__ == '__main__':
    app.run()
