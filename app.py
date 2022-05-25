from flask import Flask, render_template
from data import fast_apr

app = Flask(__name__)


@app.route("/")
def index():
    return render_template('index.html')


@app.route("/fast_apr")
def apr():
    return fast_apr()
