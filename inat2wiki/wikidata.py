import requests

WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"

def get_inat_taxon_id(scientific_name):
    """
    Queries the iNaturalist API to fetch the taxon ID for a given scientific name.
    """
    url = "https://api.inaturalist.org/v1/taxa"
    params = {"q": scientific_name}
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if data.get("results"):
        taxon = data["results"][0]
        return taxon["id"], taxon["name"]
    else:
        return None, None

def get_inat_taxon_id_from_wikidata(qid):
    """
    Queries Wikidata to fetch the iNaturalist Taxon ID (P3151) for a given Wikidata entity (QID).
    
    :param qid: The Wikidata item ID (e.g., "Q219702" for Monarch butterfly)
    :return: The iNaturalist Taxon ID as a string, or None if not found.
    """
    params = {
        "action": "wbgetclaims",
        "entity": qid,
        "property": "P3151",
        "format": "json"
    }

    response = requests.get(WIKIDATA_API_URL, params=params)
    data = response.json()

    # Check if the property P3151 exists in the claims
    if "claims" in data and "P3151" in data["claims"]:
        return data["claims"]["P3151"][0]["mainsnak"]["datavalue"]["value"]

    return None

def get_csrf_token(session):
    """Fetches a CSRF token required for editing Wikidata."""
    response = session.get(WIKIDATA_API_URL, params={
        "action": "query",
        "meta": "tokens",
        "type": "csrf",
        "format": "json"
    })
    return response.json().get("query", {}).get("tokens", {}).get("csrftoken")

def add_inat_taxon_id_to_wikidata(qid, taxon_id, oauth_token):
    """
    Adds an iNaturalist Taxon ID (P3151) to a Wikidata item (QID).

    :param qid: Wikidata entity ID (e.g., "Q219702" for Monarch butterfly).
    :param taxon_id: iNaturalist Taxon ID to add (e.g., "47651").
    :param oauth_token: OAuth token for authentication.
    :return: Response from Wikidata API.
    """
    
    session = requests.Session()
    
    # Authenticate using OAuth
    session.headers.update({"Authorization": f"Bearer {oauth_token}"})

    # Get CSRF Token
    csrf_token = get_csrf_token(session)
    if not csrf_token:
        return {"error": "Failed to retrieve CSRF token"}
    
    # Create the claim
    response = session.post(WIKIDATA_API_URL, data={
        "action": "wbcreateclaim",
        "entity": qid,
        "property": "P3151",
        "snaktype": "value",
        "value": f'"{taxon_id}"',
        "token": csrf_token,
        "format": "json"
    })

    return response.json()
