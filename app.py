import flask
import urllib.parse
import requests

# Configure application
app = flask.Flask(__name__)
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


@app.route("/search", methods = ['GET'])
def search():

      return('Add "/search/yourusername" to the end of the url.')


@app.route("/search/<user_id>", methods=["GET", "POST"])
def search_with_topic(user_id):

    observations = requests.get( f"https://api.inaturalist.org/v1/observations?user_id={user_id}&only_id=false&per_page=1000"
    )

    observations = observations.json()
    print(observations)

    core_information = {}

    inaturalist_taxon_ids = []
    for obs in observations["results"]:

        quality_grade = obs["quality_grade"]

        tax_info = obs["taxon"]

        try:
            inaturalist_taxon_ids.append(str(tax_info["min_species_taxon_id"]))

            obs_id = obs["id"]
            core_information[obs_id] = {
                "name": tax_info["name"],
                "quality": quality_grade,
                "taxon_id": tax_info["min_species_taxon_id"],
            }
        except:
            with open("log.txt", "a") as f:
                f.write(str(obs) + "/n")

    formatted_values = '{ "' + '""'.join(inaturalist_taxon_ids) + '" }'

    query_for_taxa_missing_images = (
        """
    
    SELECT DISTINCT * WHERE{

        VALUES ?id """
        + formatted_values
        + """

        ?item wdt:P3151 ?id .

        MINUS {?item wdt:P18 ?image} . 
  
        ?item rdfs:label ?itemLabel . 
        FILTER ( LANG(?itemLabel) = "en" )

                BIND(IRI(CONCAT(CONCAT("https://www.inaturalist.org/taxa/", ?id), "/browse_photos?photo_license=cc0")) AS ?cc0_url)
        BIND(IRI(CONCAT(CONCAT("https://www.inaturalist.org/taxa/", ?id), "/browse_photos?photo_license=cc-by")) AS ?ccby_url)
    }
    """
    )

    url_query_for_taxa_missing_images = (
        "https://query.wikidata.org/embed.html#"
        + urllib.parse.quote(query_for_taxa_missing_images)
    )

    
    # Langcode provisorily set to English

    langcode = "en"

    query_for_missing_en_wiki = (
        """

        
    SELECT DISTINCT * WHERE{

        VALUES ?id """
        + formatted_values
        + """

    
            ?item wdt:P3151 ?id .

        ?item rdfs:label ?itemLabel . 
        FILTER ( LANG(?itemLabel) = "en" )

        MINUS{
        {?sitelink schema:about ?item .
        ?sitelink schema:isPartOf ?site.
        ?sitelink schema:isPartOf/wikibase:wikiGroup "wikipedia" .

        FILTER(CONTAINS(STR(?sitelink), """
        + f'"{langcode}.wiki"'
        + """))}
                 }
        }    """
    )

    url_query_for_missing_en_wiki = "https://query.wikidata.org/embed.html#" + urllib.parse.quote(
        query_for_missing_en_wiki
    )

    sections = [
        {"legend": "Observations missing an image on Wikidata",
         "query": url_query_for_taxa_missing_images
        }, 

        {"legend": "Observations missing a page on en wiki",
         "query": url_query_for_missing_en_wiki
        }, 

    ]

    

    return flask.render_template(
        "search.html",
        sections=sections
    )