import os
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from datetime import datetime
import requests
import urllib.parse
import flask
import os
from wbib import wbib
import yaml
from pynaturalist2commons.get_all_observations import get_all_observations

# Configure application

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    return flask.render_template("index.html")


@app.route("/about")
def about():
    return flask.render_template("about.html")


@app.route("/userlist/", methods=["GET", "POST"])
@app.route("/userlist", methods=["GET", "POST"])
def userlist_base():

    if request.method == "POST":
        userlist = request.form.get("userlist")
        return redirect(f"/userlist/{userlist}")

    return render_template("userlist.html")


@app.route("/userlist/<user_id>", methods=["GET", "POST"])
def userlist(user_id):
    print(user_id)
    user_info = get_all_observations(user_id, "pt")
    return render_template("userlist.html", user_info=user_info, username=user_id)
