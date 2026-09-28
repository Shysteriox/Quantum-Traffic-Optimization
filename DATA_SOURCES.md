# Data sources for world_city_sim.py (14-city comparison)

Every real-world statistic below is tagged "verified" or "approximate."
"Verified" means the figure was found directly in a primary report or a
source that quotes it precisely. "Approximate" means it was found only via
a secondary source, an older baseline year, or a monitoring body other
than IQAir/TomTom; suitable for an exploratory figure, not for a citation
without independent confirmation.

## PM2.5 (ug/m3, annual average)

| City | Value | Confidence | Source |
|---|---:|---|---|
| Fremont, CA | 8.5 | verified | IQAir World Air Quality Report 2023 |
| Delhi, India | 92.7 | verified | IQAir World Air Quality Report 2023 |
| Los Angeles, CA | 10.2 | verified | IQAir World Air Quality Report 2023 |
| Singapore | 13.6 | verified | IQAir World Air Quality Report 2023 |
| Oslo, Norway | 5.4 | verified | IQAir World Air Quality Report 2023 |
| Jakarta, Indonesia | 37.3 | verified | IQAir 2023 report; widely reported as the most polluted capital city that year (e.g. Mongabay, Filantra) |
| London, UK | 8.4 | verified | IQAir 2023 data, as reported by Statista |
| Mexico City, Mexico | 22.3 | approximate | Secondary source citing an IQAir 2023 ranking of Mexico City as roughly 14th most polluted city globally |
| Beijing, China | 32.0 | approximate | Beijing Municipal Ecology & Environment Bureau official 2023 annual average (not IQAir); a separately cited US Embassy sensor reading for the same year was approximately 39, so 32 should be treated as a lower-bound estimate |
| Zurich, Switzerland | 10.9 | approximate | Switzerland-level figure from an approximately 2019 baseline; a 2023 IQAir figure specific to Zurich was not located |
| Cairo, Egypt | 42.4 | verified | IQAir 2023 report; Egypt ranked approximately 9th most-polluted country, Cairo approximately 10th city globally that year |
| Tokyo, Japan | 11.7 | approximate | IQAir figure from an approximately 2019 baseline; a 2023-specific IQAir figure for Tokyo was not located (Japan's 2023 national average was 9.6 ug/m3 per Statista, for rough context) |
| Sao Paulo, Brazil | 15.3 | approximate | IQAir figure from an approximately 2019 baseline; CETESB (Sao Paulo state environmental agency) publishes an official 2023 report, but the exact capital-city PM2.5 figure was not extracted from it in this pass -- see https://cetesb.sp.gov.br/ar/wp-content/uploads/sites/28/2024/08/Relatorio-de-Qualidade-do-Ar-no-Estado-de-Sao-Paulo-2023.pdf |
| Sydney, Australia | 10.1 | approximate | IQAir figure from an approximately 2019 baseline; NSW EPA's official 2023 annual air quality statement shows a network-wide range of 4.3-8.6 ug/m3, suggesting an improvement since 2019, but no Sydney-specific 2023 figure was isolated from the report text |

## Congestion (TomTom Traffic Index 2025 report, covering 2024 driving data)

The original 5 cities use TomTom's "% extra travel time" metric (Fremont
22%, Delhi 46%, LA 28%, Singapore 19%, Oslo 22%), set up in an earlier
session and not independently re-verified here. TomTom's public city pages
did not yield the same percentage metric for the additional cities added
later, so `world_city_sim.py` instead records their travel-time-per-10km
figures (a metric TomTom also publishes), cross-checked against an
aggregated third-party table:

| City | Travel time / 10km (2024) | Source |
|---|---|---|
| Mexico City | 32:33 | TomTom Traffic Index 2025 report, via statranker.org aggregation |
| Beijing | 29:10 | same |
| Jakarta | 32:29 | same |
| London | 33:17 | same |
| Zurich | 28:22 | same |
| Cairo | 26:46 | same |
| Tokyo | 29:18 | same |
| LA / Singapore / Oslo (for reference) | 29:48 / 29:02 / 28:10 | same table, consistent with the cities already in use |

Delhi and Fremont do not appear in that top-100 table (Fremont is likely
too small to rank globally; Delhi's absence is unexplained, and may
reflect a different name or city boundary in TomTom's dataset). Their
original percentage-based figures were kept as-is. Sao Paulo and Sydney do
not have a travel-time-per-10km figure located in this pass.

## Known limitation

`demand_base` (the traffic-volume multiplier each city's simulation runs
on) is a hand-set ordinal estimate for cities added after the original
five, ranked using the congestion and PM2.5 numbers above. It is not
independently derived from real vehicle-count data, consistent with the
original five. This is a simulation calibration knob, not a validated
demand model.
