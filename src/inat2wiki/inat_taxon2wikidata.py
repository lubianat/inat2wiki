import requests
from wdcuration import lookup_id, render_qs_url


def main():
    taxon_id = "605531"

    url = f"https://api.inaturalist.org/v1/taxa/{taxon_id}"

    r = requests.get(url)

    data = r.json()

    taxon_info = data["results"][0]

    parent_id = taxon_info["parent_id"]
    parent_qid = lookup_id(parent_id, property="P3151")

    taxon_name = taxon_info["name"]

    rank_dict = {"species": "Q7432"}

    rank_qid = rank_dict[taxon_info["rank"]]

    # As per https://forum.inaturalist.org/t/where-does-the-inat-gbif-taxonomy-cross-reference-live/35372/7:

    gbif_search_url = f"https://api.gbif.org/v1/species?name={taxon_name}"

    r_gbif = requests.get(gbif_search_url).json()
    gbif_taxon_data = r_gbif["results"][0]
    gbif_id = gbif_taxon_data["key"]
    authorship = gbif_taxon_data["authorship"]
    qs = (
        "CREATE\n"
        f'LAST|Len|"{taxon_name}"\n'
        f'LAST|Aen|"{taxon_name} ({authorship})"\n'
        f'LAST|Lpt|"{taxon_name}"\n'
        'LAST|Den|"species"\n'
        "LAST|P31|Q16521|S248|Q16958215\n"
        f"LAST|P171|{parent_qid}|S248|Q16958215\n"
        f'LAST|P225|"{taxon_name}"|S248|Q16958215\n'
        f"LAST|P105|{rank_qid}|S248|Q16958215\n"
        f'LAST|P3151|"{taxon_id}"\n'
        f'LAST|P846|"{gbif_id}"\n'
    )

    print(qs)
    print(render_qs_url(qs))


if __name__ == "__main__":
    main()
