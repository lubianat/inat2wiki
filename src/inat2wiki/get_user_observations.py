#!/usr/bin/env python3

import json
import urllib.parse
from collections import OrderedDict
from operator import getitem
from pathlib import Path

import click
import requests
from wdcuration import query_wikidata

HERE = Path(__file__).parent.resolve()
RESULTS = HERE.parent.joinpath("results").resolve()


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


@click.command(name="all")
@click.argument("user_id")
def click_get_observations_with_wiki_info(user_id, langcode=None):
    """Command line wraper to get_observations_with_wiki_info()"""
    core_information = get_observations_with_wiki_info(user_id, langcode=langcode, limit=200)
    RESULTS.joinpath(f"candidates_{user_id}.json").write_text(
        json.dumps(core_information, indent=3)
    )


def get_observations_with_wiki_info(
    inaturalist_id, limit=200, quality_grade="research", license="cc0,cc-by,cc-by-sa", type="user"
):
    """Gets observations for an iNaturalist user.
    Args:
      inaturalist_id (str): Either the user or project identifier.
      limit (int): The maximum number of observations to retrieve.
      type (int): Either 'project' or 'user'. Defaults to 'user'.
      quality_grade (str): The quality grade to filter for. Only takes one of ["research","needs_id", "casual"]
    """
    core_information, inaturalist_taxon_ids = extract_core_information(
        id=inaturalist_id, license=license, limit=limit, quality_grade=quality_grade, type=type
    )

    inaturalist_chunks = chunks(inaturalist_taxon_ids, 30)
    for chunk in inaturalist_chunks:
        r = requests.get(f"https://api.inaturalist.org/v1/taxa/{','.join(chunk)}")
        for taxon_info in r.json()["results"]:
            try:
                core_information[str(taxon_info["id"])]["number_of_observations"] = taxon_info[
                    "observations_count"
                ]
            except KeyError:
                print(f"Key not found: {taxon_info['id']}")

    core_information = OrderedDict(
        sorted(
            core_information.items(),
            key=lambda x: getitem(x[1], "number_of_observations"),
        )
    )

    taxa_ids_for_query = list(core_information.keys())[0:100]

    query_for_taxa_missing_images = get_query_for_tax_missing_images(taxa_ids_for_query)

    url_query_for_taxa_missing_images = "https://query.wikidata.org/#" + urllib.parse.quote(
        query_for_taxa_missing_images
    )

    wikidata_taxa_and_images = query_wikidata(query_for_taxa_missing_images)

    for taxon_id in core_information:
        for taxon in wikidata_taxa_and_images:
            if taxon["id"] == taxon_id:
                core_information[taxon_id]["wikidata_id"] = taxon["qid"]
                if "image" not in taxon:
                    if "wikipages_missing" not in core_information[taxon_id]:
                        core_information[taxon_id]["wikipages_missing"] = []
                    if "wikidata_image" not in core_information[taxon_id]["wikipages_missing"]:
                        core_information[taxon_id]["wikipages_missing"].append("wikidata_image")

    print(url_query_for_taxa_missing_images)

    print("--------------- Query for observations missing wiki pages -----------")
    langcode_list = ["en", "pt"]
    for langcode in langcode_list:
        core_information = add_missing_wikipages(langcode, core_information, taxa_ids_for_query)

    return core_information


def add_missing_wikipages(langcode, core_information, taxa_ids_for_query) -> dict:
    """Adds missing wikipages to the core_information object."""
    query_for_missing_pt_wiki = get_query_for_taxa_missing_wikipages(taxa_ids_for_query, langcode)

    url_query_for_missing_pt_wiki = "https://query.wikidata.org/#" + urllib.parse.quote(
        query_for_missing_pt_wiki
    )
    taxa_missing_images = query_wikidata(query_for_missing_pt_wiki)

    for taxon_id in core_information:
        if "wikipages_missing" not in core_information[taxon_id]:
            core_information[taxon_id]["wikipages_missing"] = []
        for taxon_missing_image in taxa_missing_images:
            if taxon_missing_image["id"] == taxon_id:
                if langcode not in core_information[taxon_id]["wikipages_missing"]:
                    core_information[taxon_id]["wikipages_missing"].append(langcode)

    print(url_query_for_missing_pt_wiki)
    return core_information


def get_query_for_taxa_missing_wikipages(inaturalist_taxon_ids, langcode):
    formatted_values = '{ "' + '""'.join(inaturalist_taxon_ids) + '" }'

    query_for_missing_pt_wiki = (
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
    return query_for_missing_pt_wiki


def get_query_for_tax_missing_images(inaturalist_taxon_ids):
    formatted_values = '{ "' + '""'.join(inaturalist_taxon_ids) + '" }'

    print("------------- Query for taxa missing images ---------- ")
    query_for_taxa_missing_images = (
        """
    SELECT DISTINCT 
    (REPLACE(STR(?item), ".*Q", "Q") AS ?qid) 
    ?id
    ?image
    ?cc0_url
    ?ccby_url
    WHERE{
        VALUES ?id """
        + formatted_values
        + """
        ?item wdt:P3151 ?id .
        OPTIONAL {?item wdt:P18 ?image} . 
        ?item rdfs:label ?itemLabel . 
        FILTER ( LANG(?itemLabel) = "en" )
        BIND(IRI(CONCAT(CONCAT("https://www.inaturalist.org/taxa/", ?id), "/browse_photos?photo_license=cc0")) AS ?cc0_url)
        BIND(IRI(CONCAT(CONCAT("https://www.inaturalist.org/taxa/", ?id), "/browse_photos?photo_license=cc-by")) AS ?ccby_url)
    }
    """
    )
    return query_for_taxa_missing_images


def extract_core_information(
    id, limit, quality_grade, license="cc0,cc-by,cc-by-sa", type="user", page=1
):
    if type == "user":
        url = f"https://api.inaturalist.org/v1/observations?user_id={id}&only_id=false&per_page=200&page={str(page)}"
    elif type == "project":
        url = f"https://api.inaturalist.org/v1/observations?project_id={id}&only_id=false&per_page=200&page={str(page)}"
    else:
        raise Exception("Parameter type must be either 'user' or 'project'.")

    if quality_grade in ["research", "needs_id", "casual"]:
        url += "&quality_grade=" + quality_grade
    if license in ["cc0", "cc-by", "cc-by-sa", "cc0,cc-by,cc-by-sa"]:
        url += "&photo_license=" + license
    observations = requests.get(url)

    observations = observations.json()
    core_information = {}

    inaturalist_taxon_ids = []
    total_n = 0
    for obs in observations["results"]:
        quality_grade = obs["quality_grade"]
        if "taxon" not in obs:
            continue
        tax_info = obs["taxon"]
        if tax_info is None:
            continue
        if "iconic_taxon_name" in tax_info:
            iconic_taxon_name = tax_info["iconic_taxon_name"]
        else:
            iconic_taxon_name = "None"
        license_code = obs["license_code"]
        try:
            species_id = str(tax_info["min_species_taxon_id"])
            inaturalist_taxon_ids.append(species_id)
            obs_info = {"id": obs["id"], "quality_grade": quality_grade, "license": license_code}
            if species_id in core_information:
                core_information[species_id]["observations"].append(obs_info)

            else:
                core_information[species_id] = {
                    "iconic_name": iconic_taxon_name,
                    "name": tax_info["name"],
                    "quality": quality_grade,
                    "taxon_id": tax_info["min_species_taxon_id"],
                    "observations": [obs_info],
                }
        except:
            with open("log.txt", "a") as f:
                f.write(str(obs) + "/n")
    total_n += len(observations["results"])
    if len(observations["results"]) > 0 and total_n < limit:
        next_page = page + 1
        next_core_information, next_inaturalist_taxon_ids = extract_core_information(
            id, limit, quality_grade=quality_grade, license=license, type=type, page=next_page
        )
        core_information.update(next_core_information)
        inaturalist_taxon_ids.extend(next_inaturalist_taxon_ids)

    inaturalist_taxon_ids = inaturalist_taxon_ids[0:limit]

    core_information = {k: v for k, v in core_information.items() if k in inaturalist_taxon_ids}
    return core_information, inaturalist_taxon_ids


if __name__ == "__main__":
    click_get_observations_with_wiki_info()
