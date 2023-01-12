from dataclasses import dataclass
from flask_bootstrap import Bootstrap5
from flask_wtf import FlaskForm
from taxon2wikipedia.render_page import get_pt_wikipage_from_qid
from wdcuration import get_statement_values, lookup_id
from wtforms import BooleanField, IntegerField, RadioField, StringField, TextAreaField
from wtforms.validators import InputRequired, Length, Optional

import flask
from flask import Flask, redirect, render_template, request
from inat2wiki.get_user_observations import get_observations_with_wiki_info
from inat2wiki.parse_observation import get_commons_url, request_observation_data

app = Flask(__name__)

# Configure application

app = Flask(__name__)

app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
Bootstrap5(app)

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
    qid = lookup_id(observation_data["taxon"]["min_species_taxon_id"], "P3151", default="")
    for i, photo_data in enumerate(photo_data_list):
        upload_url = get_commons_url(observation_data, photo_data, observation_id)
        observation_data["photos"][i]["url"] = observation_data["photos"][i]["url"].replace(
            "square", "original"
        )

        observation_data["photos"][i]["upload_url"] = upload_url

    return render_template("parse.html", observation_data=observation_data, qid=qid)


class iNaturalistForm(FlaskForm):
    limit = IntegerField("limit of observations (defaults to 200)", validators=[Optional()])
    quality = BooleanField("Research grade only?", default="checked")
    license = BooleanField("Open license only?", default="checked")


class iNaturalistUserForm(iNaturalistForm):
    name = StringField("username", validators=[InputRequired()])


class iNaturalistProjectForm(iNaturalistForm):
    name = StringField("Project name:", validators=[InputRequired()])


@app.route("/projectlist/", methods=["GET", "POST"])
@app.route("/projectlist", methods=["GET", "POST"])
def projectlist_base():

    form = iNaturalistProjectForm()
    if form.validate_on_submit():
        return create_redirect_from_form(form, base_route="/projectlist")

    return render_template("projectlist.html", form=form)


@app.route("/projectlist/<project_id>", methods=["GET", "POST"])
def projectlist(project_id):
    form = iNaturalistProjectForm()

    search_config = parse_requests_into_search_config(request)
    project_info = get_observations_with_wiki_info(
        inaturalist_id=project_id,
        limit=search_config.limit,
        quality_grade=search_config.quality_grade,
        license=search_config.license,
        type="project",
        starting_page=search_config.page,
    )
    return render_template(
        "projectlist.html",
        project_info=project_info,
        project_name=project_id,
        search_config=search_config,
        form=form,
    )


def create_redirect_from_form(form, base_route):
    name = form.name.data
    if form.limit.data:
        limit = form.limit.data
    else:
        limit = 200
    if form.quality.data:
        quality_grade = "research"
    else:
        quality_grade = "any"

    if form.quality.data:
        license = "cc0,cc-by,cc-by-sa"
    else:
        license = "any"
    redirect_object = redirect(
        f"{base_route}/{name}?limit={str(limit)}&quality_grade={str(quality_grade)}&license={license}"
    )
    return redirect_object


@app.route("/userlist/", methods=["GET", "POST"])
@app.route("/userlist", methods=["GET", "POST"])
def userlist_base():

    form = iNaturalistUserForm()
    if form.validate_on_submit():

        return create_redirect_from_form(form, base_route="/userlist")

    return render_template("userlist.html", form=form)


@dataclass
class iNaturalistSearchConfiguration:
    page: int = 1
    limit: int = 200
    quality_grade: str = "research"
    license: str = "cc0,cc-by,cc-by-sa"


@app.route("/userlist/<user_id>", methods=["GET", "POST"])
def userlist(user_id):
    form = iNaturalistUserForm()
    search_config = parse_requests_into_search_config(request)
    user_info = get_observations_with_wiki_info(
        user_id,
        search_config.limit,
        search_config.quality_grade,
        search_config.license,
        starting_page=search_config.page,
    )
    return render_template(
        "userlist.html",
        user_info=user_info,
        username=user_id,
        form=form,
        search_config=search_config,
    )


def parse_requests_into_search_config(request):
    search_config = iNaturalistSearchConfiguration()
    if "page" in request.args:
        search_config.page = int(request.args["page"])
    if "limit" in request.args:
        search_config.limit = int(request.args["limit"])
    if "quality_grade" in request.args:
        search_config.quality_grade = request.args["quality_grade"]
    if "license" in request.args:
        search_config.license = request.args["license"]
    return search_config


@app.route("/ptwikistub/", methods=["GET", "POST"])
@app.route("/ptwikistub", methods=["GET", "POST"])
def ptwikistub_base():

    if request.method == "POST":
        qid = request.form.get("taxon_qid")
        return redirect(f"/ptwikistub/{qid}")

    return render_template("ptwikistub.html")


@app.route("/ptwikistub/<taxon_qid>", methods=["GET", "POST"])
def ptwikistub(taxon_qid):
    ptwikistub = get_pt_wikipage_from_qid(taxon_qid)

    taxon_name = get_statement_values(taxon_qid, "P225")[0]
    return render_template(
        "ptwikistub.html", qid=taxon_qid, ptwikistub=ptwikistub, taxon_name=taxon_name
    )
