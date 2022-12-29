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
from inat2wiki.get_all_observations import get_all_observations
from inat2wiki.parse_observation import get_commons_url, request_observation_data

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


@app.route("/parse/", methods=["GET", "POST"])
@app.route("/parse", methods=["GET", "POST"])
def parse_obs_base():
    return render_template("parse.html")


@app.route("/parse/<observation_id>", methods=["GET", "POST"])
def parse_obs(observation_id):

    observation_data = request_observation_data(observation_id)
    photo_data_list = observation_data["photos"]

    for i, photo_data in enumerate(photo_data_list):
        upload_url = get_commons_url(observation_data, photo_data, observation_id)
        observation_data["photos"][i]["url"] = observation_data["photos"][i]["url"].replace(
            "square", "original"
        )

        observation_data["photos"][i]["upload_url"] = upload_url

    return render_template("parse.html", observation_data=observation_data)


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
