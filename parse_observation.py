#!/usr/bin/env python3
import requests
import urllib.parse


id = input("Enter the iNaturalist observation id:")


base_url = "https://api.inaturalist.org/v1/"
observation_url = base_url + f"observations/{id}"

result = requests.get(observation_url)

data = result.json()
observation_data = data["results"][0]

upload_params = {}

photo_data = observation_data["photos"][0]
photo_url = photo_data["url"].replace("square", "original")

user_data = observation_data["user"]
upload_params["photo_id"] = photo_data["id"]
upload_params["photo_license"] = photo_data["license_code"]
upload_params["user_id"] = user_data["id"]
upload_params["user_name"] = observation_data["user"]["name"]
upload_params["date"] = observation_data["observed_on"]
upload_params["taxon"] = observation_data["taxon"]["name"]


switcher = {"cc-by": "cc-by-4.0", "cc-by-sa": "cc-by-sa-4.0", "cc0": "Cc-zero"}


print("https://commons.wikimedia.org/wiki/Special:Upload")


print("====== Photo URL =====")
print(photo_url)

print("====== Title ======")
title = upload_params["taxon"] + " " + str(upload_params["photo_id"]) + ".jpeg"

print(title)

print("====== Summary ======")
license = switcher[upload_params["photo_license"]]
print("License: " + license)
summary = (
    """{{Information"""
    + f"""
|description={upload_params["taxon"]}
|date={upload_params["date"]}
|source=https://www.inaturalist.org/photos/{str(upload_params["photo_id"])}
|author=[https://www.inaturalist.org/users/{str(upload_params["user_id"])} {upload_params["user_name"]}]
|permission=
|other versions=
"""
    + """}}
    
{{"""
    + f"iNaturalist|{id}"
    + "}}"
    + f"""

[[Category:{upload_params["taxon"]}]]"""
)


print(summary)
upload_page = "https://commons.wikimedia.org/wiki/Special:Upload"

summary_for_url = urllib.parse.quote(summary)
title_for_url = urllib.parse.quote(title)
upload_url = (
    upload_page
    + f"?wpUploadDescription={summary_for_url}&wpLicense={license}&wpDestFile={title_for_url}&wpSourceType=url&wpUploadFileURL={photo_url}"
)
print(upload_url)