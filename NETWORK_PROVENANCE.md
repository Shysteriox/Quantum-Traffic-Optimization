# Which cities used real road networks vs. synthetic fallback

Overpass (the OpenStreetMap query service osmnx uses) had a sustained outage
during this run -- every single retry attempt (12+ across two different
mirrors: overpass-api.de and overpass.kumi.systems) failed at an identical
180-second connect timeout. That's an infrastructure problem on their end (or
the network path to it), not per-city rate-limiting -- confirmed because it
failed identically regardless of which city was requested. Cities that had
already been downloaded and cached in an earlier session before the outage
still have real data; everything requested during the outage fell back to a
synthetic 5x5 grid (25 nodes), exactly as the original task spec allowed.

| City | Network source | Nodes | Notes |
|---|---|---:|---|
| Fremont, CA | **real OSM** | 70 | cached before outage |
| Delhi, India | **real OSM** | 42 | cached before outage |
| Los Angeles, CA | **real OSM** | 44 | cached before outage |
| Oslo, Norway | **real OSM** | 70 | cached before outage |
| Mexico City, Mexico | **real OSM** | 65 | downloaded successfully before outage began |
| Zurich, Switzerland | **real OSM** | 70 | downloaded successfully before outage began |
| Singapore | **real OSM** | 53 | fixed -- old center point (1.3521, 103.8198) had no roads in the search polygon; moved to Raffles Place (1.2838, 103.8511), a dense real intersection cluster |
| Beijing, China | synthetic | 25 | Overpass outage |
| Jakarta, Indonesia | synthetic | 25 | Overpass outage |
| London, UK | synthetic | 25 | Overpass outage |
| Cairo, Egypt | synthetic | 25 | Overpass outage |
| Tokyo, Japan | synthetic | 25 | Overpass outage |
| Sao Paulo, Brazil | synthetic | 25 | Overpass outage |
| Sydney, Australia | synthetic | 25 | Overpass outage |

**7 of 14 cities are on real road networks; 7 are on the synthetic fallback** (Singapore's center point has since been fixed and re-downloaded successfully -- see row above).
This is reported here rather than left implicit because every figure and
number derived from a synthetic-grid city is a statement about "a generic
5x5 grid with this city's real pollution stats and demand assumption
attached," not "this city's actual streets" -- an important distinction if
any of this goes into the paper's methodology section.

## To get real data for the fallback cities later

Nothing needs to change in the code -- `download_osm()` in `real_city_sim.py`
already caches successful downloads and only re-attempts cities that don't
have a cache file yet. Just re-running `world_city_sim.py` once Overpass is
reachable again will pick up real data for whichever of the 8 fallback
cities succeed, without re-downloading or re-simulating the other 6.
Singapore's failure needs an actual fix (a different center point/radius),
independent of Overpass being up or down.
