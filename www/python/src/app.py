"""A flask app to connect iNaturalist to Wikidata."""

from dataclasses import dataclass
from flask_bootstrap import Bootstrap5
from flask_wtf import FlaskForm
from taxon2wikipedia.render_page import run_pipeline_for_wikipage
from wdcuration import get_statement_values, lookup_id
from wtforms import BooleanField, IntegerField, StringField
from wtforms.validators import InputRequired, Optional

import flask
from flask import Flask, redirect, render_template, request
import requests

from inat2wiki.get_user_observations import get_observations_with_wiki_info
from inat2wiki.parse_observation import get_commons_url, request_observation_data

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
Bootstrap5(app)

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
        if upload_url == "License not supported":
            observation_data["photos"][i]["upload_url"] = "License not supported"
    return render_template("parse.html", observation_data=observation_data, qid=qid)


@app.route("/projectlist/", methods=["GET", "POST"])
@app.route("/projectlist", methods=["GET", "POST"])
def project_list_form():
    form = iNaturalistProjectForm()
    if form.validate_on_submit():
        return create_redirect_from_form(form, base_route="/projectlist")
    return render_template("projectlist.html", form=form)


@app.route("/projectlist/<project_id>", methods=["GET", "POST"])
def project_list_results(project_id):
    form = iNaturalistProjectForm()
    try:
        search_config = parse_requests_into_search_config(request)
        project_info = search_config.get_wiki_info(project_id, type="project")

    except KeyError:
        flask.flash(
            f"Something wrong happened! Maybe the project with id '{project_id}' does not exist?",
            "error",
        )
        return render_template("projectlist.html", form=form)

    return render_template(
        "projectlist.html",
        project_info=project_info,
        project_name=project_id,
        search_config=search_config,
        form=form,
    )


@app.route("/userlist/", methods=["GET", "POST"])
@app.route("/userlist", methods=["GET", "POST"])
def user_list_form():
    form = iNaturalistUserForm()
    if form.validate_on_submit():
        return create_redirect_from_form(form, base_route="/userlist")
    return render_template("userlist.html", form=form)


@app.route("/userlist/<user_id>", methods=["GET", "POST"])
def user_list_results(user_id):
    form = iNaturalistUserForm()
    try:
        search_config = parse_requests_into_search_config(request)
        user_info = search_config.get_wiki_info(user_id)

    except KeyError:
        flask.flash(
            f"Something wrong happened! Maybe the user with id '{user_id}' does not exist?",
            "error",
        )
        return render_template("projectlist.html", form=form)

    return render_template(
        "userlist.html",
        user_info=user_info,
        username=user_id,
        form=form,
        search_config=search_config,
    )


def get_qid_from_name(scientific_name):
    # SPARQL query to find QID based on scientific name
    query = f"""
    SELECT ?item WHERE {{
      ?item wdt:P225 "{scientific_name}" .
    }}
    LIMIT 1
    """
    print(query)

    # URL for Wikidata SPARQL endpoint
    url = "https://query.wikidata.org/sparql"
    headers = {"Accept": "application/json"}
    params = {"query": query}

    # Execute the request
    response = requests.get(url, headers=headers, params=params)

    # Check if the response is valid and parse the QID
    if response.status_code == 200:
        data = response.json()
        results = data.get("results", {}).get("bindings", [])
        if results:
            qid = results[0]["item"]["value"].split("/")[-1]  # Extract QID from URI
            return qid

    # Return None if QID is not found
    return None


@app.route("/wikistub/<lang>/", methods=["GET", "POST"])
@app.route("/wikistub/<lang>", methods=["GET", "POST"])
def wikistub_base(lang):
    if request.method == "POST":
        identifier = request.form.get("taxon_identifier")
        return redirect(f"/wikistub/{lang}/{identifier}")

    return render_template("wikistub.html", lang=lang)


import re


@app.route("/wikistub/<lang>/<identifier>", methods=["GET", "POST"])
def wikistub(lang, identifier):
    # Check if the identifier matches a valid QID pattern (e.g., "Q" followed by digits)
    if re.match(r"^Q\d+$", identifier):
        taxon_qid = identifier
    else:
        # Treat as scientific name and attempt to find QID
        taxon_qid = get_qid_from_name(identifier)
        if not taxon_qid:
            # Handle case where QID is not found for the scientific name
            return render_template("wikistub.html", error="Scientific name not found.", lang=lang)

        # Redirect to the correct URL with the resolved QID
        return redirect(f"/wikistub/{lang}/{taxon_qid}")

    # Proceed with the QID to retrieve information
    ptwikistub_content = run_pipeline_for_wikipage(taxon_qid, lang)
    taxon_name = get_statement_values(taxon_qid, "P225")[0]
    return render_template(
        "wikistub.html",
        qid=taxon_qid,
        ptwikistub=ptwikistub_content,
        taxon_name=taxon_name,
        lang=lang,
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
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500
