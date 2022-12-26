#!/usr/bin/env python3

import json
import sys
import urllib.parse
from collections import OrderedDict
from operator import getitem

import click
import requests
from wdcuration import query_wikidata
from pathlib import Path

HERE = Path(__file__).parent.resolve()
RESULTS = HERE.parent.joinpath("results").resolve()


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


@click.command(name="all")
@click.argument("user_id")
def click_get_all_observations(user_id, langcode=None):
    get_all_observations(user_id, langcode=langcode)


def get_all_observations(user_id, langcode=None):
    print(user_id)
    core_information, inaturalist_taxon_ids = extract_core_information(user_id)

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

    taxa_missing_images = query_wikidata(query_for_taxa_missing_images)

    for taxon_id in core_information:
        for taxon_missing_image in taxa_missing_images:
            if taxon_missing_image["id"] == taxon_id:
                core_information[taxon_id]["wikidata_id"] = taxon_missing_image["item"]
                core_information[taxon_id]["missing_image"] = True

    print(url_query_for_taxa_missing_images)

    print("--------------- Query for observations missing wiki pages -----------")
    if langcode is None:
        langcode = input("Enter your lang code of interest:")

    query_for_missing_pt_wiki = get_query_for_taxa_missing_wikipages(taxa_ids_for_query, langcode)

    url_query_for_missing_pt_wiki = "https://query.wikidata.org/#" + urllib.parse.quote(
        query_for_missing_pt_wiki
    )
    taxa_missing_images = query_wikidata(query_for_missing_pt_wiki)

    for taxon_id in core_information:
        core_information[taxon_id]["wikipages_missing"] = []
        for taxon_missing_image in taxa_missing_images:

            if taxon_missing_image["id"] == taxon_id:
                core_information[taxon_id]["wikipages_missing"].append(langcode)

    print(url_query_for_missing_pt_wiki)
    RESULTS.joinpath(f"candidates_{user_id}.json").write_text(
        json.dumps(core_information, indent=3)
    )
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
    return query_for_taxa_missing_images


def extract_core_information(id, page=1):
    print(page)
    observations = requests.get(
        f"https://api.inaturalist.org/v1/observations?user_id={id}&only_id=false&per_page=200&page={str(page)}"
    )

    observations = observations.json()
    core_information = {}

    inaturalist_taxon_ids = []

    for obs in observations["results"]:
        quality_grade = obs["quality_grade"]
        tax_info = obs["taxon"]

        try:
            species_id = str(tax_info["min_species_taxon_id"])
            inaturalist_taxon_ids.append(species_id)
            obs_id = obs["id"]
            if species_id in core_information:
                core_information[species_id]["observations"].append(obs_id)

            else:
                core_information[species_id] = {
                    "name": tax_info["name"],
                    "quality": quality_grade,
                    "taxon_id": tax_info["min_species_taxon_id"],
                    "observations": [obs_id],
                }
        except:
            with open("log.txt", "a") as f:
                f.write(str(obs) + "/n")
    if len(observations["results"]) > 0:
        next_page = page + 1
        next_core_information, next_inaturalist_taxon_ids = extract_core_information(
            id, page=next_page
        )
        core_information.update(next_core_information)
        inaturalist_taxon_ids.extend(next_inaturalist_taxon_ids)
    return core_information, inaturalist_taxon_ids


if __name__ == "__main__":
    click_get_all_observations()
