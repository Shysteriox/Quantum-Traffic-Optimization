# Quantum Traffic Optimization

> **Current results: `sim_10seeds/` (900 runs). Everything else in this repo is superseded.**
>
> - **Local-Greedy beat SA-QUBO in 50 of 50 paired runs** (5 networks x 10 seeds). This is a negative result for the QUBO controller.
> - **No quantum hardware was used.** "SA-QUBO" is classical simulated annealing (dwave-neal) solving a QUBO. Nothing here shows a quantum advantage.
> - SA-QUBO beat Fixed-Time clearly only in Fremont (28.5% less delay) and Oslo (18.5%). Delhi is inconclusive (4.4%, 6 of 10 seeds); Los Angeles is -3.8% and the synthetic 5x5 grid ("Grid-25 (synthetic)" in the paper) is -8.7%. That grid is not real Singapore; `results.csv` and the code only use "Singapore" as its internal key.
> - **Superseded:** the 3-trial, 14-city results, `phase_transition.py`, the city-tour videos and the JSON results at the repo root. They came from an earlier, biased toy model; claims like "QUBO wins in most cities" or a "phase transition" should not be cited. Their emission factors were also roughly 14x (CO2) and 15.7x (fuel) too small, and the CO2/NOx/fuel percentages simply equal the delay percentage. Use delay (vehicle-hours) as the metric.
> - Paper figures: `figures_paper/` (Figure 1 and Figure 2). The paper points readers to `sim_10seeds/` for the code and data (see its README and METHODS.md). From the repo root, `make_figures.py` rebuilds the figures, `paper_numbers.py` prints the headline numbers and `verify_headline.py` re-checks them, all from `sim_10seeds/results.csv`.
> - Map data: © OpenStreetMap contributors, available under the Open Database License (ODbL), https://www.openstreetmap.org/copyright. `osm_cache/` and `sim_10seeds/osm_cache/` hold cached extracts.
>
> Convention: "% less delay than Fixed-Time, positive = better, mean of per-trial values". `sim_10seeds/RESULTS.md` shows 29.3% / 19.2% / 4.9% (Fremont / Oslo / Delhi) because it pools the trials first; the paper averages per-trial values (28.5% / 18.5% / 4.4%). Both are correct. Whether SA-QUBO could overtake Greedy under other QUBO weights, demand levels, real signal data, larger or more coupled networks, or real quantum hardware is untested; those are hypotheses, not findings.

*Superseded description of the earlier version (see the banner above):* a
simulation project comparing three traffic-signal controllers — Fixed-Time,
Local-Greedy, and a QUBO-based controller solved with simulated annealing
("QA-QUBO") — across OpenStreetMap road networks in 14 cities, 2025-2030.

`DATA_SOURCES.md` documents the sources of the real-world statistics used by
that earlier version (including PM2.5 and congestion index). The current
paper does not use them and makes no health or PM2.5 claims.

## Framing notes

`QA-QUBO` refers to classical simulated annealing solving a QUBO
formulation, not real quantum-annealer hardware — this project does not
have D-Wave access. That stand-in is standard practice in the published
literature on this topic (see `REFERENCES.md`); the naming should not be
read as implying a demonstrated quantum speedup.

Earlier versions of this project (the code at the repo root) reported QUBO
winning in most cities. The 10-seed rerun in `sim_10seeds/` does not support
that: Greedy won every paired run. The root-level code and results are kept
only for history.

## Structure

```
sim_10seeds/             CURRENT. The 10-seed run behind the paper: 5 networks x 6 years x
                          3 controllers x 10 seeds = 900 runs. results.csv has every run;
                          README.md, METHODS.md and RESULTS.md explain how to reproduce it.
figures_paper/           CURRENT. Figure 1 (2030 comparison) and Figure 2 (adoption by year)
make_figures.py          CURRENT. Rebuilds the two paper figures from sim_10seeds/results.csv
paper_numbers.py         CURRENT. Prints the paper's headline numbers from results.csv
verify_headline.py       CURRENT. Independent re-check of the headline numbers

Everything below is the earlier, superseded version, kept for history:

real_city_sim.py         5-city core simulation engine + Fixed-Time/Greedy/QUBO controllers +
                          osm_to_qubo_structure() (real-OSM-graph -> QUBO adjacency, excludes
                          freeway-grade roads -- see NETWORK_PROVENANCE.md)
world_city_sim.py        Extends to 14 cities across every continent (imports real_city_sim)
network_scale_test.py    Built but not yet run. Intended to test whether QUBO's edge over
                          Greedy grows with network size using real OSM data at increasing
                          radii; that question was instead answered using existing
                          synthetic-grid data (fig05_phase_diagram.png). Running this script
                          would answer the same question using real road networks specifically.
simulate_qubo_traffic.py QUBO matrix construction + simulated-annealing solver (shared engine)
phase_transition.py      Gridlock phase-transition / bifurcation experiments (synthetic grids)
animate_traffic.py       Original single-synthetic-grid 3-panel animation, superseded by
                          city_tour_videos.py below, kept for reference
world_tour_animation.py  Superseded by city_tour_videos.py. A single combined GIF cycling
                          through all 14 cities (56MB, no seek controls, abstract node-graph
                          layout, rapidly-changing colors) proved harder to follow than one
                          MP4 per city. Kept for reference, not the recommended path.
city_tour_videos.py      Per-city animation: one MP4 per city, real curved OSM road geometry,
                          green/yellow/red congestion coloring, an on-screen legend, and a
                          continuous 2025-2030 simulation per city (both panels identical until
                          2027, diverging as QA-QUBO adoption ramps up). Requires imageio-ffmpeg
                          (`pip install imageio-ffmpeg`), since this project has no system
                          ffmpeg dependency otherwise. `python city_tour_videos.py` renders all
                          14; `python city_tour_videos.py "Delhi"` renders one (substring
                          match). Output goes to figures/city_tours/, not tracked in git.
                          All 14 rendered videos are attached to the
                          [city-tours-v1 release](https://github.com/Shysteriox/Quantum-Traffic-Optimization/releases/tag/city-tours-v1).
fix_figures.py           Regenerates the same-year-corrected comparison figures
plot_grid_qubo_diagram.py  QUBO structure diagram for a synthetic grid

figures/                 Generated PNGs from the superseded runs (city_tours/ subfolder holds
                          the per-city MP4s, not tracked in git). The health-impact and
                          pollution figures were removed: the paper makes no health claims.
osm_cache/               Cached real road networks (tracked in git; avoids re-hitting
                          Overpass, which has been unreliable during development)
city_results.json, world_results.json, network_scale_results.json, simulation_results.json
                         Raw numeric results
DATA_SOURCES.md          Sourcing and confidence level for every real-world statistic used
NETWORK_PROVENANCE.md    Which cities' figures use a real OSM road network vs. a synthetic
                          fallback grid, and why
REFERENCES.md            16 independently-verified citations for the paper
```

## Running it

```
pip install -r requirements.txt
python real_city_sim.py       # original 5-city run (writes uncorrected fig08/fig09 + fig10)
python fix_figures.py         # run after real_city_sim.py -- overwrites fig08/fig09 with the
                               # same-year-comparison corrected versions (see "Framing notes")
python world_city_sim.py      # 14-city world run (imports real_city_sim, no need to run it first)
python network_scale_test.py  # network-size scaling test (not yet run, see note above)
python phase_transition.py    # gridlock phase-transition experiments (synthetic grids)

pip install imageio-ffmpeg    # one-time, for real MP4 export (no system ffmpeg otherwise)
python city_tour_videos.py    # all 14 per-city MP4s -> figures/city_tours/
```

Each city's first run needs internet access (OpenStreetMap via the
Overpass API); results are cached to `osm_cache/` afterward. If Overpass is
unreachable, a city falls back to a synthetic 5x5 grid automatically, which
is logged in the console output. `NETWORK_PROVENANCE.md` records which
cities that affected on the most recent run.

## References

`REFERENCES.md` lists 16 citations, each checked directly against its
source rather than accepted on the strength of the citation string alone.
An earlier reference list for this project included entries that did not
match their cited sources on verification; this list replaces it.
