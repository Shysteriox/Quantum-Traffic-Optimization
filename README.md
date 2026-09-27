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
real_city_sim.py         5-city core simulation engine + Fixed-Time/Greedy/QUBO controllers
world_city_sim.py        Extends to 14 cities across every continent (imports real_city_sim)
network_scale_test.py    Does QUBO's edge over Greedy grow with network size (more intersections)?
simulate_qubo_traffic.py QUBO matrix construction + simulated-annealing solver (shared engine)
phase_transition.py      Gridlock phase-transition / bifurcation experiments (synthetic grids)
animate_traffic.py       Mini-Motorways-style animation renderer
fix_figures.py           Regenerates same-year-corrected comparison figures
plot_grid_qubo_diagram.py  QUBO structure diagram for a synthetic grid

figures/                 All generated PNGs/GIFs/MP4s
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
python network_scale_test.py  # network-size scaling test
python phase_transition.py    # gridlock phase-transition experiments (synthetic grids)
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
