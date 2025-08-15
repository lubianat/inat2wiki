# iNat2Wiki

**iNat2Wiki** is a tool that helps bridge biodiversity data from [iNaturalist](https://www.inaturalist.org/) to Wikimedia projects like Wikipedia and Wikimedia Commons.

Code for Commons import adapted from: [iNaturalist2Commons by @kaldari](https://github.com/kaldari/iNaturalist2Commons/blob/main/inat2commons.js)

## Development

The tool is currently being **rebuilt** at:  
* [inat2wiki-dev.toolforge.org](https://inat2wiki-dev.toolforge.org/)  
* Source code: [inat2wiki-dev GitHub repository](https://github.com/lubianat/inat2wiki-dev)

Please submit **feature requests and bug reports** to the [inat2wiki-dev issue tracker](https://github.com/lubianat/inat2wiki-dev/issues).

---

##  Basic Usage

### Add an Observation via iNaturalist ID

chmod +x parse_observation_in_cli
./parse_observation_in_cli observationidhere

Then, just click the generated link to upload the image to Wikimedia Commons.

---

### Get Personalized Curation Queries

    python3 list_user_observations.py

You'll be prompted to enter:

- Your iNaturalist username
- A language code for the Wikipedia query

---

##  Core Logic

Core functionality is implemented in a shared Python module:  
* [inat2wiki-module](https://github.com/lubianat/inat2wiki-module)

---

##  Browser Add-on

There's also a [Google Chrome extension](https://github.com/lubianat/addon_inat2wiki) to simplify workflows and upload directly from iNaturalist.
