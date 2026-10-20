# Canonical data

The duplicate `pois.json`, `locations.json` and `facts.json` files were removed:
they contained manual additions that could not be reproduced from the collected
sources. There is one dataset for the application and the preview launcher.

- `data/current.json` selects the POI snapshot, including its raw OpenStreetMap
  response, normalized places, starting locations and manifest.
- `data/enrichment/current.json` selects reviewed facts from primary sources,
  with attribution, dates and a manifest checksum.
- `data/walking/current.json` selects the collected OpenStreetMap walking graph.

Refresh these datasets with `python scripts/refresh_data.py`. Do not edit published
snapshot records in place: rerun the collector so the sources, records and
manifests stay consistent.
