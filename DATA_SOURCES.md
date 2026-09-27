# Data sources for world_city_sim.py (10-city comparison)

Same rule as before: **verify every number yourself before it goes in the paper.**
"Verified" below means I found the figure directly in a primary report or a
source that quotes it precisely. "Approximate" means I could only find it via
a secondary source, an older baseline year, or a different monitoring body
than IQAir/TomTom — usable for an exploratory figure, not for a citation.

## PM2.5 (ug/m3, annual average)

| City | Value | Confidence | Source |
|---|---:|---|---|
| Fremont, CA | 8.5 | verified | IQAir World Air Quality Report 2023 (carried over from the original 5-city run) |
| Delhi, India | 92.7 | verified | IQAir World Air Quality Report 2023 |
| Los Angeles, CA | 10.2 | verified | IQAir World Air Quality Report 2023 |
| Singapore | 13.6 | verified | IQAir World Air Quality Report 2023 |
| Oslo, Norway | 5.4 | verified | IQAir World Air Quality Report 2023 |
| Jakarta, Indonesia | 37.3 | verified | IQAir 2023 report; widely reported as the most polluted capital city that year (e.g. Mongabay, Filantra) |
| London, UK | 8.4 | verified | IQAir 2023 data, as reported by Statista |
| Mexico City, Mexico | 22.3 | approximate | Secondary source citing IQAir 2023 ranking Mexico City ~14th most polluted city globally |
| Beijing, China | 32.0 | approximate | Beijing Municipal Ecology & Environment Bureau official 2023 annual average (NOT IQAir) — a US Embassy sensor cited elsewhere read ~39 for the same year, so treat 32 as a lower-bound estimate |
| Zurich, Switzerland | 10.9 | approximate | Older Switzerland-level figure (~2019 baseline); could not confirm a 2023 IQAir figure specific to Zurich in this pass |

## Congestion (TomTom Traffic Index 2025 report, covering 2024 driving data)

The original 5 cities use TomTom's "% extra travel time" metric (Fremont 22%,
Delhi 46%, LA 28%, Singapore 19%, Oslo 22% — as set up in the earlier session,
not re-verified here). TomTom's public city pages did not yield the same %
metric for the 5 new cities in this pass, so `world_city_sim.py` instead
records their **travel-time-per-10km** figures (a real, uniform metric TomTom
also publishes), cross-checked against an aggregated third-party table:

| City | Travel time / 10km (2024) | Source |
|---|---|---|
| Mexico City | 32:33 | TomTom Traffic Index 2025 report, via statranker.org aggregation |
| Beijing | 29:10 | same |
| Jakarta | 32:29 | same |
| London | 33:17 | same |
| Zurich | 28:22 | same |
| (for reference) LA / Singapore / Oslo | 29:48 / 29:02 / 28:10 | same table, consistent with the cities already in use |

Note: Delhi and Fremont are not in that top-100 table (Fremont is too small to
rank globally; Delhi's absence is unexplained — possibly a different name/city
boundary in TomTom's dataset). Their original %-based figures were kept as-is.

## Tier 2 cities (continent-coverage expansion: Africa, East Asia, South America, Oceania)

| City | PM2.5 (ug/m3) | Confidence | Source | Congestion (TomTom, min:sec/10km, 2024) |
|---|---:|---|---|---|
| Cairo, Egypt | 42.4 | verified | IQAir 2023 report; Egypt ranked ~9th most-polluted country, Cairo ~10th city globally that year | 26:46 |
| Tokyo, Japan | 11.7 | approximate | IQAir figure is a 2019 baseline; could not confirm a 2023-specific IQAir figure for Tokyo in this pass (Japan's 2023 national average was 9.6 ug/m3 per Statista, for rough context) | 29:18 |
| Sao Paulo, Brazil | 15.3 | approximate | IQAir figure is a 2019 baseline; CETESB (Sao Paulo state environmental agency) publishes an official 2023 report but the exact capital-city PM2.5 figure could not be extracted from it in this pass -- see https://cetesb.sp.gov.br/ar/wp-content/uploads/sites/28/2024/08/Relatorio-de-Qualidade-do-Ar-no-Estado-de-Sao-Paulo-2023.pdf if you want the real number | not found |
| Sydney, Australia | 10.1 | approximate | IQAir figure is a 2019 baseline; NSW EPA's official 2023 annual air quality statement shows a network-wide range of 4.3-8.6 ug/m3, suggesting Sydney's air quality has likely improved since 2019, but no Sydney-specific 2023 figure could be isolated from the report text in this pass | not found |

## Known limitation

`demand_base` (the traffic-volume multiplier each city's simulation runs on)
is a hand-set ordinal estimate for the 5 new cities, ranked by the congestion
and PM2.5 numbers above — it is **not** independently derived from real
vehicle-count data, same as it wasn't for the original 5. This is a
simulation calibration knob, not a validated demand model.
