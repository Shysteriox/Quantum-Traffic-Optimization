# Quantum Traffic Optimization

A simulation project comparing three traffic-signal controllers — Fixed-Time,
Local-Greedy, and a QUBO-based controller solved with simulated annealing
("QA-QUBO") — across real OpenStreetMap road networks in cities on every
populated continent, 2025-2030.

`DATA_SOURCES.md` documents the source and confidence level for every
real-world statistic used (PM2.5, congestion index). Several are marked
`approximate` (an older baseline year, or a secondary source rather than
the primary report).

## Framing notes

`QA-QUBO` refers to classical simulated annealing solving a QUBO
formulation, not real quantum-annealer hardware — this project does not
have D-Wave access. That stand-in is standard practice in the published
literature on this topic (see `REFERENCES.md`); the naming should not be
read as implying a demonstrated quantum speedup.

Two independently-built versions of this simulation (this one, and a
separately-built comparison) reached opposite conclusions about whether
QA-QUBO beats a simple Local-Greedy baseline — this implementation shows
QUBO winning in most cities, the other shows Greedy winning in all of
them. That disagreement is itself a result worth reporting: it indicates
the "QUBO beats greedy" outcome is sensitive to implementation detail
rather than a settled finding. Figures and summaries in this project
report all three controllers rather than only QUBO-vs-Fixed-Time.

## Structure

```
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
fix_figures.py           Regenerates the same-year-corrected comparison figures
plot_grid_qubo_diagram.py  QUBO structure diagram for a synthetic grid

figures/                 Generated PNGs (city_tours/ subfolder holds the per-city MP4s,
                          not tracked in git)
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
python real_city_sim.py       # original 5-city run (writes uncorrected fig08/fig09 + fig10/fig11)
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
