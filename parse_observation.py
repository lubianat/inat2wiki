#!/usr/bin/env python3
import requests

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

print("https://commons.wikimedia.org/wiki/Special:Upload")


print("====== Photo URL =====")
print(photo_url)

print("====== Title ======")
print(upload_params["taxon"] + " " + str(upload_params["photo_id"]) + ".jpeg")

print("====== Summary ======")
print(
    """
{{Information
|description={{en|"""
    + upload_params["taxon"]
    + """}}
|date="""
    + upload_params["date"]
    + """
|source=https://www.inaturalist.org/photos/"""
    + str(upload_params["photo_id"])
    + """
|author=[https://www.inaturalist.org/users/"""
    + str(upload_params["user_id"])
    + " "
    + upload_params["user_name"]
    + """ ]
|permission=
|other versions=
}}

[[Category:"""
    + upload_params["taxon"]
    + """]]
"""
)
