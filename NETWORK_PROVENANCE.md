# Which cities used real road networks vs. synthetic fallback

**Update: as of the latest run, all 14 cities have real OpenStreetMap data.**
The Overpass outage documented below (every city that fell back to a
synthetic grid) has resolved -- Overpass recovered mid-session, and a
re-run picked up real data for every remaining city. The synthetic-fallback
mechanism itself is still there and still used automatically if Overpass
is ever unreachable again; nothing here was removed, it's just not
currently in use.

## Highway-grade road filtering (a real correctness fix, not just this doc)

Before this fix, `osm_to_qubo_structure()` ranked and selected intersections
by degree on the *raw* OSM graph, which includes motorway/trunk-class roads.
Those don't have ordinary 2-phase cross-traffic signals (they're grade-
separated or ramp/merge-controlled), so modeling them as regular
signal-controlled intersections wasn't physically realistic. Checked and
fixed for every city -- the number excluded varied a lot:

| City | Freeway-grade edges excluded |
|---|---:|
| Oslo, Norway | 67 (36% of its network) |
| Cairo, Egypt | 38 |
| Singapore | 13 |
| Sao Paulo, Brazil | 11 |
| Beijing, China | 6 |
| Sydney, Australia | 2 |
| Los Angeles, CA | 1 |
| Fremont, Delhi, Mexico City, Jakarta, London, Zurich, Tokyo | 0 |

Oslo's and Singapore's actual simulation results changed as a result (Oslo's
same-year CO2 reduction: 33.4% -> 32.8%; Singapore: 22.9% -> 21.0% -- same
direction, not a dramatic swing, but a real change, not noise).

## Current network size per city (after the highway filter, real OSM for all)

| City | Intersections simulated | Notes |
|---|---:|---|
| Fremont, CA | 70 | raw graph at 500m radius is only 97 nodes total -- genuinely a low-density suburban grid, not a bug |
| Delhi, India | 42 | raw graph unexpectedly small (44 nodes) -- likely thinner OSM mapping detail in that specific area, not lower real-world density |
| Los Angeles, CA | 44 | |
| Singapore | 43 | after excluding 13 freeway edges |
| Oslo, Norway | 70 | after excluding 67 freeway edges (raw graph is 138 nodes, one of the densest raw samples) |
| Mexico City, Mexico | 65 | |
| Beijing, China | 30 | |
| Jakarta, Indonesia | 47 | |
| London, UK | 70 | |
| Zurich, Switzerland | 70 | raw graph is 136 nodes, very dense |
| Cairo, Egypt | 70 | after excluding 38 freeway edges |
| Tokyo, Japan | 70 | |
| Sao Paulo, Brazil | 70 | after excluding 11 freeway edges |
| Sydney, Australia | 65 | after excluding 2 freeway edges |

70 is the current `max_nodes` cap in `osm_to_qubo_structure()` -- most cities
hit that cap, meaning the real intersection count within their 500m radius is
at or above 70; only Fremont, Delhi, LA, Singapore, Beijing, Jakarta, and
Sydney have fewer real intersections than the cap allows.
