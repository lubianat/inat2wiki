"""
Creates a QuickStatements command to add an iNaturalist taxon to Wikidata.

Uses the iNaturalist and GBIF APIs to gather taxon details and IDs.
"""

import requests
from wdcuration import lookup_id, render_qs_url


def main():
    """Generates QuickStatements for a given iNaturalist taxon ID."""
    taxon_id = "605531"
    taxon_info = requests.get(f"https://api.inaturalist.org/v1/taxa/{taxon_id}").json()["results"][
        0
    ]

    parent_qid = lookup_id(taxon_info["parent_id"], property="P3151")
    taxon_name = taxon_info["name"]
    rank_qid = {"species": "Q7432"}[taxon_info["rank"]]

    gbif_data = requests.get(f"https://api.gbif.org/v1/species?name={taxon_name}").json()[
        "results"
    ][0]
    gbif_id, authorship = gbif_data["key"], gbif_data["authorship"]

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
