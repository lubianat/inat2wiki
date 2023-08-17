""" A flask app to connect iNaturalist to Wikidata."""

from dataclasses import dataclass
from flask_bootstrap import Bootstrap5
from flask_wtf import FlaskForm
from taxon2wikipedia.render_page import get_pt_wikipage_from_qid
from wdcuration import get_statement_values, lookup_id
from wtforms import BooleanField, IntegerField, StringField
from wtforms.validators import InputRequired, Optional

import flask
from flask import Flask, redirect, render_template, request
from inat2wiki.get_user_observations import get_observations_with_wiki_info
from inat2wiki.parse_observation import get_commons_url, request_observation_data

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
    project_info = search_config.get_wiki_info(project_id, type="project")

    return render_template(
        "projectlist.html",
        project_info=project_info,
        project_name=project_id,
        search_config=search_config,
        form=form,
    )


@app.route("/userlist/", methods=["GET", "POST"])
@app.route("/userlist", methods=["GET", "POST"])
def userlist_base():
    form = iNaturalistUserForm()
    if form.validate_on_submit():
        return create_redirect_from_form(form, base_route="/userlist")
    return render_template("userlist.html", form=form)


@app.route("/userlist/<user_id>", methods=["GET", "POST"])
def userlist(user_id):
    form = iNaturalistUserForm()
    search_config = parse_requests_into_search_config(request)
    user_info = search_config.get_wiki_info(user_id)
    return render_template(
        "userlist.html",
        user_info=user_info,
        username=user_id,
        form=form,
        search_config=search_config,
    )


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


# Helper functions


def parse_requests_into_search_config(request):
    """Parse a POST request into a search configuration object."""
    search_config = iNaturalistSearchConfiguration()
    if "page" in request.args:
        search_config.page = int(request.args["page"])
    if "limit" in request.args:
        search_config.limit = int(request.args["limit"])
    if "quality_grade" in request.args:
        search_config.quality_grade = request.args["quality_grade"]
    if "license" in request.args:
        search_config.license = request.args["license"]
    if "langcodes" in request.args:
        search_config.langcodes = request.args["langcodes"]
    return search_config


def create_redirect_from_form(form, base_route):
    """Creates a flask redirect route using information on a WTForm."""
    name = form.name.data
    if form.limit.data:
        limit = form.limit.data
    else:
        limit = 200
    if form.quality.data:
        quality_grade = "research"
    else:
        quality_grade = "any"
    if form.license.data:
        license = "cc0,cc-by,cc-by-sa"
    else:
        license = "any"
    if form.langcodes.data:
        langcodes = form.langcodes.data
    else:
        langcodes = "pt,en"
    redirect_object = redirect(
        f"{base_route}/{name}?limit={str(limit)}&quality_grade={str(quality_grade)}&license={license}&langcodes={langcodes}"
    )
    return redirect_object


class iNaturalistForm(FlaskForm):
    limit = IntegerField("Limit of observations (defaults to 200):", validators=[Optional()])
    quality = BooleanField("Research grade only?", default="checked")
    license = BooleanField("Open license only?", default="checked")
    langcodes = StringField("Wikipedia langcodes (defaults to 'en,pt'):", validators=[Optional()])


class iNaturalistUserForm(iNaturalistForm):
    name = StringField("Username:", validators=[InputRequired()])


class iNaturalistProjectForm(iNaturalistForm):
    name = StringField("Project name:", validators=[InputRequired()])


@dataclass
class iNaturalistSearchConfiguration:
    """
    The configuration info for the iNaturalist API call to retrieve observations.
    """

    page: int = 1
    limit: int = 200
    quality_grade: str = "research"
    license: str = "cc0,cc-by,cc-by-sa"
    langcodes: str = "en,pt"

    def get_wiki_info(self, inaturalist_id, type="user"):
        return get_observations_with_wiki_info(
            inaturalist_id,
            limit=self.limit,
            quality_grade=self.quality_grade,
            license=self.license,
            type=type,
            starting_page=self.page,
            langcode_list=self.langcodes.split(","),
        )

@app.errorhandler(404)
def not_found_error(error):
  return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
  return render_template('500.html'), 500