from flask import Flask, redirect, render_template, request
import flask
from inat2wiki.get_all_observations import get_all_observations
from inat2wiki.parse_observation import get_commons_url, request_observation_data
from taxon2wikipedia.render_page import get_pt_wikipage_from_qid
from wdcuration import get_statement_values

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
    if request.method == "POST":
        obs_id = request.form.get("obs_id")
        return redirect(f"/parse/{obs_id}")

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
        username = request.form.get("username")
        return redirect(f"/userlist/{username}")

    return render_template("userlist.html")


@app.route("/userlist/<user_id>", methods=["GET", "POST"])
def userlist(user_id):
    print(user_id)
    if "limit" in request.args:
        print(request.args["limit"])
        limit = int(request.args["limit"])
    else:
        limit = 200
    user_info = get_all_observations(user_id, "pt", limit)
    return render_template("userlist.html", user_info=user_info, username=user_id)


@app.route("/ptwikistub/", methods=["GET", "POST"])
@app.route("/ptwikistub", methods=["GET", "POST"])
def ptwikistub_base():

    if request.method == "POST":
        qid = request.form.get("taxon_qid")
        return redirect(f"/ptwikistub/{qid}")

    return render_template("ptwikistub.html")


@app.route("/ptwikistub/<taxon_qid>", methods=["GET", "POST"])
def ptwikistub(taxon_qid):
    print(taxon_qid)
    ptwikistub = get_pt_wikipage_from_qid(taxon_qid)

    taxon_name = get_statement_values(taxon_qid, "P225")[0]
    return render_template(
        "ptwikistub.html", qid=taxon_qid, ptwikistub=ptwikistub, taxon_name=taxon_name
    )
