#!/usr/bin/env python3
import sys
import requests
import json


def main():
    try:
        id = sys.argv[1]
    except:
        id = input("Enter the user id:")

    observations = requests.get(
        f"https://api.inaturalist.org/v1/observations?user_id={id}&only_id=false&per_page=1000"
    )

    observations = observations.json()
    print(observations)

    core_information = {}

    inaturalist_taxon_ids = []
    for obs in observations["results"]:
        print("-----------")
        quality_grade = obs["quality_grade"]

        tax_info = obs["taxon"]
        print(tax_info)

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

    print("Possible taxa:")
    print(inaturalist_taxon_ids)

    with open("candidates.json", "w") as outfile:
        json.dump(core_information, outfile, indent=3)

    formatted_values = '{ "' + '" "'.join(inaturalist_taxon_ids) + '" }'

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
    }
    """
    )
    print(query_for_taxa_missing_images)


if __name__ == "__main__":
    main()
