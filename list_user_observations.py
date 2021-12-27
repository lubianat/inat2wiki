#!/usr/bin/env python3
import sys
import requests


def main():
    try:
        id = sys.argv[1]
    except:
        id = input("Enter the user id:")

    observations = requests.get(
        f"https://api.inaturalist.org/v1/observations?user_id={id}&only_id=false"
    )

    observations = observations.json()
    print(observations)

    inaturalist_taxon_ids = []
    for obs in observations["results"]:
        print("-----------")
        quality_grade = obs["quality_grade"]

        if quality_grade != "needs_id":
            print("-----------")

            tax_info = obs["taxon"]

            print(tax_info)

            try:
                inaturalist_taxon_ids.append(tax_info["min_species_taxon_id"])
            except:
                with open("log.txt", "a") as f:
                    f.write(str(obs))

    print("Possible taxa:")
    print(inaturalist_taxon_ids)


if __name__ == "__main__":
    main()
