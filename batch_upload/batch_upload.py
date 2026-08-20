#!/usr/bin/env python3

import os
import json
import tempfile
import textwrap
from pathlib import Path

import requests
from tqdm import tqdm
from prompt_toolkit import prompt
from prompt_toolkit import print_formatted_text as print

HERE = Path(__file__).parent.resolve()

CACHE_FILE = HERE / "uploaded_photos_cache.json"

INATURALIST_PROJECT = "wikiconcurso-fotografico-inaturalist-2026"

COMMONS_CATEGORY = "Wikiconcurso iNaturalist 2026"
TOTAL_OBS = 10

# Wikimedia strongly requires a descriptive User-Agent identifying the tool
# and a contact. Edit the contact URL/email to point at you or your project.
USER_AGENT = (
    "WikiconcursoINaturalistUploader/1.0 "
    "(https://commons.wikimedia.org/wiki/Category:Wikiconcurso_iNaturalist_2026; "
    "contact: tiago.lubiana@rbnaturalistas.org) python-requests"
)

COMMONS_API = "https://commons.wikimedia.org/w/api.php"


def main():
    project_slug = INATURALIST_PROJECT

    # Load cache (uploaded photos) from file
    cache = load_cache()

    # Prompt for Wikimedia Commons username and password
    username = prompt("Enter your Wikimedia Commons username: ")
    password = prompt("Enter your Wikimedia Commons password: ", is_password=True)

    # Log in ONCE and reuse the authenticated session for every upload.
    session = login_to_commons(username, password)

    # Get observations from the project
    observations = get_all_observations_from_project(project_slug, TOTAL_OBS)

    # Process each observation with tqdm progress bar
    with tqdm(total=len(observations), desc="Uploading photos") as pbar:
        for observation in observations:
            process_observation(observation, session, cache)
            pbar.update(1)
            save_cache(cache)

    # Save updated cache to file
    save_cache(cache)


def make_session():
    """Create a requests session with a proper Wikimedia User-Agent."""
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def safe_json(response, context=""):
    """Parse JSON, raising a readable error if the body isn't JSON.

    This turns the cryptic 'Expecting value: line 1 column 1 (char 0)' into
    something that tells you what actually came back (rate-limit page, HTML
    error, empty body, etc.).
    """
    try:
        return response.json()
    except ValueError:
        raise Exception(
            f"Non-JSON response ({context}), status {response.status_code}: "
            f"{response.text[:300]!r}"
        )


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


def get_all_observations_from_project(project_slug, TOTAL_OBS=None):
    total_obs = 0
    observations = []
    page = 1
    per_page = 200

    # A session here too, so iNaturalist also sees a proper User-Agent.
    inat = make_session()

    if TOTAL_OBS is not None:
        limit_obs = TOTAL_OBS
    else:
        limit_obs = float("inf")

    while True:
        url = (
            f"https://api.inaturalist.org/v1/observations"
            f"?project_id={project_slug}&per_page={per_page}&page={page}"
        )
        response = inat.get(url)
        data = safe_json(response, context="iNaturalist observations")
        if "results" not in data:
            print(f"Error fetching observations: {data}")
            break
        observations.extend(data["results"])
        total_obs += len(data["results"])
        if total_obs >= limit_obs:
            break
        if len(data["results"]) < per_page:
            break
        page += 1

    # Respect the fetch limit exactly, even though the API returns in pages.
    if TOTAL_OBS is not None:
        observations = observations[:TOTAL_OBS]

    return observations


def process_observation(observation, session, cache):
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
        print(
            f"Skipping photo {photo.get('id')} due to unacceptable license: {license_code}"
        )
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
        download_photo(photo_url, filename, session)
    except Exception as e:
        print(f"Error downloading photo {photo_url}: {e}")
        return

    # Upload photo to Wikimedia Commons
    try:
        upload_file_to_commons(
            filename, title, description, session, license_code=license_code
        )
        print(f"Uploaded {title} successfully.")
        # Update cache with uploaded photo ID
        cache[str(photo.get("id"))] = True
    except Exception as e:
        print(f"Error uploading {title}: {e}")

    # Delete the temporary file
    if os.path.exists(filename):
        os.remove(filename)


def download_photo(url, filename, session):
    response = session.get(url, stream=True)
    if response.status_code == 200:
        with open(filename, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
    else:
        raise Exception(
            f"Failed to download image from {url} (status {response.status_code})"
        )


def build_description(observation, photo, upload_params):
    switcher = {"cc-by": "cc-by-4.0", "cc-by-sa": "cc-by-sa-4.0", "cc0": "Cc-zero"}
    license_code = switcher.get(upload_params["photo_license"])

    extra_category = f"""
        [[Category:{COMMONS_CATEGORY}]]"""
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
        + f"""

        {{{{iNaturalist|{observation['id']}}}}}
        {{{{{license_code}}}}}
        {{{{INaturalistreview}}}}
        [[Category:{upload_params["taxon"]}]]"""
        + extra_category
    )
    return summary


def login_to_commons(username, password):
    """Log in once and return an authenticated session.

    Doing this a single time (instead of per-photo) is what prevents the
    rate-limited empty responses that caused the JSON decode errors.
    """
    S = make_session()

    # Step 1: Retrieve a login token
    token_resp = S.get(
        url=COMMONS_API,
        params={"action": "query", "meta": "tokens", "type": "login", "format": "json"},
    )
    login_token = safe_json(token_resp, context="login token")["query"]["tokens"][
        "logintoken"
    ]

    # Step 2: Send a POST request to log in
    login_response = S.post(
        COMMONS_API,
        data={
            "action": "login",
            "lgname": username,
            "lgpassword": password,
            "lgtoken": login_token,
            "format": "json",
        },
    )
    result = safe_json(login_response, context="login").get("login", {})
    if result.get("result") != "Success":
        print(f"Login failed: {result}")
        raise SystemExit(1)

    return S


def upload_file_to_commons(file_path, filename, description, session, license_code):
    S = session

    # Get the CSRF token (session is already authenticated)
    csrf_resp = S.get(
        url=COMMONS_API,
        params={"action": "query", "meta": "tokens", "format": "json"},
    )
    csrf_token = safe_json(csrf_resp, context="csrf token")["query"]["tokens"][
        "csrftoken"
    ]

    # Upload the file
    with open(file_path, "rb") as file:
        response = S.post(
            COMMONS_API,
            files={"file": (filename, file)},
            data={
                "action": "upload",
                "filename": filename,
                "token": csrf_token,
                "format": "json",
                "comment": "Uploading image from iNaturalist",
                "text": description,
                "ignorewarnings": 1,  # ignore any warnings
            },
        )

    result = safe_json(response, context="upload").get("upload", {})
    if result.get("result") == "Success":
        print(f"Successfully uploaded {filename}")
        return
    else:
        raise Exception(f"Could not upload {filename}. Response: {result}")


if __name__ == "__main__":
    main()
