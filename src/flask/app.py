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
    username = StringField("username", validators=[InputRequired()])


class iNaturalistProjectForm(iNaturalistForm):
    project_name = StringField("Project name:", validators=[InputRequired()])


@app.route("/projectlist/", methods=["GET", "POST"])
@app.route("/projectlist", methods=["GET", "POST"])
def projectlist_base():

    form = iNaturalistProjectForm()
    if form.validate_on_submit():
        project_name = form.project_name.data
        print(form.limit.data)
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
        return redirect(
            f"/projectlist/{project_name}?limit={str(limit)}&quality_grade={str(quality_grade)}&license={license}"
        )

    return render_template("projectlist.html", form=form)


@app.route("/projectlist/<project_id>", methods=["GET", "POST"])
def projectlist(project_id):
    form = iNaturalistProjectForm()

    if "page" in request.args:
        page = int(request.args["page"])
    else:
        page = 1
    if "limit" in request.args:
        print(request.args["limit"])
        limit = int(request.args["limit"])
    else:
        limit = 200
    if "quality_grade" in request.args:
        quality_grade = request.args["quality_grade"]
    else:
        quality_grade = "any"
    if "license" in request.args:
        license = request.args["license"]
    else:
        license = "any"
    project_info = get_observations_with_wiki_info(
        inaturalist_id=project_id,
        limit=limit,
        quality_grade=quality_grade,
        license=license,
        type="project",
        starting_page=page,
    )
    return render_template(
        "projectlist.html",
        project_info=project_info,
        project_name=project_id,
        quality_grade=quality_grade,
        license=license,
        form=form,
        limit=str(limit),
        page=page,
    )


@app.route("/userlist/", methods=["GET", "POST"])
@app.route("/userlist", methods=["GET", "POST"])
def userlist_base():

    form = iNaturalistUserForm()
    if form.validate_on_submit():
        username = form.username.data
        print(form.limit.data)
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
        return redirect(
            f"/userlist/{username}?limit={str(limit)}&quality_grade={str(quality_grade)}&license={license}"
        )

    return render_template("userlist.html", form=form)


@app.route("/userlist/<user_id>", methods=["GET", "POST"])
def userlist(user_id):
    form = iNaturalistUserForm()

    print(user_id)

    if "page" in request.args:
        page = int(request.args["page"])
    else:
        page = 1
    if "limit" in request.args:
        print(request.args["limit"])
        limit = int(request.args["limit"])
    else:
        limit = 200
    if "quality_grade" in request.args:
        quality_grade = request.args["quality_grade"]
    else:
        quality_grade = "any"
    if "license" in request.args:
        license = request.args["license"]
    else:
        license = "any"
    user_info = get_observations_with_wiki_info(
        user_id, limit, quality_grade, license, starting_page=page
    )
    return render_template(
        "userlist.html",
        user_info=user_info,
        username=user_id,
        form=form,
        limit=str(limit),
        page=page,
        quality_grade=quality_grade,
        license=license,
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
