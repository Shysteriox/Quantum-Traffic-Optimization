# Quantum Traffic Optimization

Simulation project comparing three traffic-signal controllers — Fixed-Time,
Local-Greedy, and a QUBO-based controller solved with simulated annealing
("QA-QUBO") — across real OpenStreetMap road networks in cities on every
populated continent, 2025-2030.

**Read this before citing any number from this project in a paper:**
[DATA_SOURCES.md](DATA_SOURCES.md) documents exactly where every real-world
statistic (PM2.5, congestion index) came from and how confident that number
is. Several are flagged `approximate` (older baseline year, or a secondary
source rather than the primary report) — verify those yourself before
citing them, the same way you'd want a journal reviewer to.

## Important framing note

`QA-QUBO` is **classical simulated annealing solving a QUBO formulation**,
not real quantum-annealer hardware — this project doesn't have D-Wave
access. That's the standard stand-in used in the actual published literature
on this topic too (see references below), but don't let the name imply a
demonstrated quantum speedup, because it isn't one.

Two independently-built versions of this simulation (this one, and a
separately-built comparison run) reached **opposite conclusions** about
whether QA-QUBO beats a simple Local-Greedy baseline — this one shows QUBO
winning in most cities, the other shows Greedy winning in all of them. That
instability is itself a real, honest finding: it means the "QUBO beats
greedy" result is sensitive to implementation details, not a settled
physical fact. Report all three controllers, always — never just
QUBO-vs-Fixed-Time, which hides this.

## Structure

```
real_city_sim.py         5-city core simulation engine + Fixed-Time/Greedy/QUBO controllers +
                          osm_to_qubo_structure() (real-OSM-graph -> QUBO adjacency, excludes
                          freeway-grade roads -- see NETWORK_PROVENANCE.md)
world_city_sim.py        Extends to 14 cities across every continent (imports real_city_sim)
network_scale_test.py    Built but NOT YET RUN -- was going to test whether QUBO's edge over
                          Greedy grows with network size using real OSM data at increasing radii;
                          the question ended up answered instead using existing synthetic-grid
                          data (fig5_phase_diagram.png). Re-run this if you want the same question
                          answered with real road networks specifically.
simulate_qubo_traffic.py QUBO matrix construction + simulated-annealing solver (shared engine)
phase_transition.py      Gridlock phase-transition / bifurcation experiments (synthetic grids)
animate_traffic.py       Original single-synthetic-grid 3-panel animation (superseded by
                          city_tour_videos.py below, kept for reference)
world_tour_animation.py  Superseded by city_tour_videos.py -- one combined GIF cycling through
                          all 14 cities turned out to be a bad format (56MB, no seek controls,
                          abstract node-graph layout, rapidly-flipping colors read as
                          "flashing lights"). Kept for reference, not the recommended path.
city_tour_videos.py      THE recommended per-city animation: one MP4 per city, real curved OSM
                          road geometry, Google-Maps-style green/yellow/red congestion coloring,
                          on-screen legend, continuous 2025-2030 simulation per city (both panels
                          identical until 2027, diverging as QA-QUBO adoption ramps up). Needs
                          imageio-ffmpeg (`pip install imageio-ffmpeg`) since this project has no
                          system ffmpeg dependency otherwise. Run `python city_tour_videos.py` for
                          all 14, or `python city_tour_videos.py "Delhi"` for just one (substring
                          match). Outputs to figures/city_tours/, not tracked in git (*.mp4 is
                          gitignored -- ~3-5MB per city, re-run to regenerate).
fix_figures.py           Regenerates same-year-corrected comparison figures
plot_grid_qubo_diagram.py  QUBO structure diagram for a synthetic grid

figures/                 All generated PNGs (city_tours/ subfolder holds the per-city MP4s,
                          not tracked in git)
osm_cache/               Cached real road networks (tracked in git -- small, avoids re-hitting
                          Overpass, which has been unreliable during development)
city_results.json, world_results.json, network_scale_results.json, simulation_results.json
                         Raw numeric results
DATA_SOURCES.md          Sourcing + confidence for every real-world statistic used
NETWORK_PROVENANCE.md    Which cities' figures use a real OSM road network vs. a synthetic
                          fallback grid, and why
REFERENCES.md            16 independently-verified real citations for the paper
```

## Running it

```
pip install -r requirements.txt
python real_city_sim.py       # original 5-city run (writes uncorrected fig08/fig09 + fig10/fig11)
python fix_figures.py         # MUST run after real_city_sim.py -- overwrites fig08/fig09 with the
                               # same-year-comparison corrected versions (see "Important framing note")
python world_city_sim.py      # 14-city world run (imports real_city_sim, no need to run it first)
python network_scale_test.py  # network-size scaling test (see note above -- not yet run)
python phase_transition.py    # gridlock phase-transition experiments (synthetic grids)

pip install imageio-ffmpeg    # needed once, for real MP4 export (no system ffmpeg on this project)
python city_tour_videos.py    # all 14 per-city MP4s -> figures/city_tours/
```

Needs internet access for the first run per city (OpenStreetMap via the
Overpass API); results are cached to `osm_cache/` afterward. If Overpass is
unreachable, cities fall back to a synthetic 5x5 grid automatically (this is
logged clearly in the console output) -- check `NETWORK_PROVENANCE.md` for
which cities that affected on the last run.

## References

`REFERENCES.md` has 16 independently-verified real citations (each checked
against the actual source, not just a citation string that looks right) --
do not reuse the original draft's bibliography, it contained fabricated
citations that have since been caught and removed.
