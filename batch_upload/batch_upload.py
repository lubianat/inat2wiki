#!/usr/bin/env python3

import sys
import requests
import tempfile
import os
import getpass
import textwrap
import json
from pathlib import Path
from tqdm import tqdm
from prompt_toolkit import prompt
from prompt_toolkit import print_formatted_text as print

HERE = Path(__file__).parent.resolve()

CACHE_FILE = HERE / "uploaded_photos_cache.json"


def main():
    # Parse command-line arguments
    project_slug = "wikiconcurso-fotografico-inaturalist-2024"

    # Load cache (uploaded photos) from file
    cache = load_cache()

    # Prompt for Wikimedia Commons username and password
    username = prompt("Enter your Wikimedia Commons username: ")
    password = prompt("Enter your Wikimedia Commons password: ", is_password=True)

    # Get observations from the project
    observations = get_all_observations_from_project(project_slug)

    # Process each observation with tqdm progress bar
    with tqdm(total=len(observations), desc="Uploading photos") as pbar:
        for observation in observations:
            process_observation(observation, username, password, cache)
            pbar.update(1)
            save_cache(cache)

    # Save updated cache to file
    save_cache(cache)


def load_cache():
    """Load the cache of uploaded photos from the cache file."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    """Save the cache to a file."""
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


def get_all_observations_from_project(project_slug):
    observations = []
    page = 1
    per_page = 200
    while True:
        url = f"https://api.inaturalist.org/v1/observations?project_id={project_slug}&per_page={per_page}&page={page}"
        response = requests.get(url)
        data = response.json()
        if "results" not in data:
            print(f"Error fetching observations: {data}")
            break
        observations.extend(data["results"])
        if len(data["results"]) < per_page:
            break
        page += 1
    return observations


def process_observation(observation, username, password, cache):
    # Check if observation is valid (quality_grade == 'research')
    if observation.get("quality_grade") != "research":
        return

    # Get the first photo
    photos = observation.get("photos", [])
    if not photos:
        return

    photo = photos[0]

    # Skip if photo already uploaded (check cache)
    if str(photo.get("id")) in cache:
        print(f"Photo {photo.get('id')} already uploaded, skipping.")
        return

    # Check if photo has acceptable license
    acceptable_licenses = ["cc-by", "cc-by-sa", "cc0"]
    license_code = photo.get("license_code")
    if license_code not in acceptable_licenses:
        print(f"Skipping photo {photo.get('id')} due to unacceptable license: {license_code}")
        return

    # Build upload_params
    upload_params = {}

    upload_params["photo_id"] = photo.get("id")
    upload_params["photo_license"] = license_code
    upload_params["user_id"] = observation["user"]["id"]
    if observation["user"].get("name"):
        upload_params["user_name"] = observation["user"]["name"]
    else:
        upload_params["user_name"] = observation["user"]["login"]

    upload_params["date"] = observation.get("observed_on")
    upload_params["taxon"] = observation["taxon"]["name"]
    upload_params["place_guess"] = observation.get("place_guess", "")

    # Build filename
    title = (
        upload_params["taxon"]
        + " - "
        + upload_params["user_name"]
        + " - "
        + str(upload_params["photo_id"])
        + ".jpeg"
    )

    # Build description text
    description = build_description(observation, photo, upload_params)

    # Get photo URL
    photo_url = photo["url"].replace("square", "original")

    # Download photo to a temporary file
    temp_dir = tempfile.gettempdir()
    filename = os.path.join(temp_dir, title)
    try:
        download_photo(photo_url, filename)
    except Exception as e:
        print(f"Error downloading photo {photo_url}: {e}")
        return

    # Upload photo to Wikimedia Commons
    try:
        upload_file_to_commons(
            filename, title, description, username, password, license_code=license_code
        )

        print(f"Uploaded {title} successfully.")
        # Update cache with uploaded photo ID
        cache[str(photo.get("id"))] = True
    except Exception as e:
        print(f"Error uploading {title}: {e}")

    # Delete the temporary file
    os.remove(filename)


def download_photo(url, filename):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(filename, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
    else:
        raise Exception(f"Failed to download image from {url}")


def build_description(observation, photo, upload_params):

    switcher = {"cc-by": "cc-by-4.0", "cc-by-sa": "cc-by-sa-4.0", "cc0": "Cc-zero"}

    license_code = switcher.get(upload_params["photo_license"])
    # Build location_template
    location_template = ""
    if observation.get("geojson") and observation.get("geoprivacy") is None:
        lat = observation["geojson"]["coordinates"][1]
        lon = observation["geojson"]["coordinates"][0]
        location_template = f"\n{{{{Location|{lat}|{lon}|source:iNaturalist}}}}"

    extra_category = """
        [[Category:Wikiconcurso iNaturalist 2024]]"""
    summary = textwrap.dedent(
        f"""
        {{{{Information
        |description={upload_params["taxon"]}, {upload_params.get("place_guess", '')}, {upload_params["date"]} (iNaturalist).
        |date={upload_params["date"]}
        |source=https://www.inaturalist.org/photos/{str(upload_params["photo_id"])}
        |author=[https://www.inaturalist.org/users/{str(upload_params["user_id"])} {upload_params["user_name"]}]
        |permission=
        |other versions=
        }}}}"""
        + location_template
        + f"""

        {{{{iNaturalist|{observation['id']}}}}}
        {{{{{license_code}}}}}
        {{{{INaturalistreview}}}}
        [[Category:{upload_params["taxon"]}]]"""
        + extra_category
    )
    return summary


def upload_file_to_commons(file_path, filename, description, username, password, license_code):
    S = requests.Session()

    # Step 1: Retrieve a login token
    login_token = S.get(
        url="https://commons.wikimedia.org/w/api.php",
        params={"action": "query", "meta": "tokens", "type": "login", "format": "json"},
    ).json()["query"]["tokens"]["logintoken"]

    # Step 2: Send a post request to log in
    login_response = S.post(
        "https://commons.wikimedia.org/w/api.php",
        data={
            "action": "login",
            "lgname": username,
            "lgpassword": password,
            "lgtoken": login_token,
            "format": "json",
        },
    )
    if login_response.json().get("login", {}).get("result") != "Success":
        print(f"Login failed: {login_response.json()}")
        exit(1)
        return

    # Step 3: Get the CSRF token
    csrf_token = S.get(
        url="https://commons.wikimedia.org/w/api.php",
        params={"action": "query", "meta": "tokens", "format": "json"},
    ).json()["query"]["tokens"]["csrftoken"]

    # Step 4: Upload the file
    with open(file_path, "rb") as file:
        response = S.post(
            "https://commons.wikimedia.org/w/api.php",
            files={"file": (filename, file)},
            data={
                "action": "upload",
                "filename": filename,
                "token": csrf_token,
                "format": "json",
                "comment": "Uploading image from iNaturalist",
                "text": description,
                "ignorewarnings": 1,  # add this to ignore any warnings
            },
        )

    # Check if upload was successful
    if response.json().get("upload", {}).get("result") == "Success":
        print(f"Successfully uploaded {filename}")
        return
    else:
        print(f"Could not upload {filename}. Response: {response.json()}")


if __name__ == "__main__":
    main()
