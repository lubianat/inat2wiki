[Repository in construction - sorry for the mess!]

https://api.inaturalist.org/v1/docs/

"The iNaturalist technology infrastructure and open source software is administered by the California Academy of Sciences as part of their mission to explore, explain, and sustain life on Earth."

Code for commons import adapted from: https://github.com/kaldari/iNaturalist2Commons/blob/main/inat2commons.js

# Basic usage

To add an observation via its iNaturalist id:

```bash
chmod +x parse_observation_in_cli
./parse_observation_in_cli observationidhere
```

Then, just click the link to upload the image to commons.


To get personalized curation queries
```bash
python3 list_user_observations.py
```

And then type in your username of interest and langcode for Wikipedia query. 

Cheers!

