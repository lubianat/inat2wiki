#!/usr/bin/env python3
import sys
import textwrap
import urllib.parse

import click
import requests


@click.command(name="parse")
@click.argument("observation_id")
def parse_observation_in_cli(observation_id):
    observation_data = request_observation_data(observation_id)
    photo_data_list = observation_data["photos"]

    print(f"====== Links for observation {observation_id} ======")

    for i, photo_data in enumerate(photo_data_list):

        print(f"====== Link for uploading photo {str(i+1)} ======")
        upload_url = get_commons_url(observation_data, photo_data, observation_id)
        print(upload_url)
        print("====== // ======")


def request_observation_data(observation_id):
    base_url = "https://api.inaturalist.org/v1/"
    observation_url = base_url + f"observations/{observation_id}"

    result = requests.get(observation_url)
    data = result.json()
    observation_data = data["results"][0]
    return observation_data


def get_commons_url(observation_data, photo_data, inaturalist_id):
    upload_params = {}
    print(photo_data)
    photo_url = photo_data["url"].replace("square", "original")

    user_data = observation_data["user"]
    upload_params["photo_id"] = photo_data["id"]
    upload_params["photo_license"] = photo_data["license_code"]
    upload_params["user_id"] = user_data["id"]
    upload_params["user_name"] = observation_data["user"]["name"]
    upload_params["date"] = observation_data["observed_on"]
    upload_params["taxon"] = observation_data["taxon"]["name"]
    switcher = {"cc-by": "cc-by-4.0", "cc-by-sa": "cc-by-sa-4.0", "cc0": "Cc-zero"}
    title = upload_params["taxon"] + " " + str(upload_params["photo_id"]) + ".jpeg"

    license_code = upload_params["photo_license"]
    license = switcher[license_code]

    summary = textwrap.dedent(
        f"""
        {{{{Information
        |description={{{{en|Picture of {upload_params["taxon"]} from iNaturalist. }}}}
        |date={upload_params["date"]}
        |source=https://www.inaturalist.org/photos/{str(upload_params["photo_id"])}
        |author=[https://www.inaturalist.org/users/{str(upload_params["user_id"])} {upload_params["user_name"]}]
        |permission=
        |other versions=
        }}}}
        {{{{  iNaturalist|{inaturalist_id} }}}}
        {{{{INaturalistreview}}}}
        {{{{{license_code}}}}}

        [[Category:{upload_params["taxon"]}]]"""
    )
    upload_page = "https://commons.wikimedia.org/wiki/Special:Upload"

    summary_for_url = urllib.parse.quote(summary)
    title_for_url = urllib.parse.quote(title)
    upload_url = (
        upload_page
        + f"?wpUploadDescription={summary_for_url}&wpLicense={license}&wpDestFile={title_for_url}&wpSourceType=url&wpUploadFileURL={photo_url}"
    )
    return upload_url


if __name__ == "__main__":
    parse_observation_in_cli()
