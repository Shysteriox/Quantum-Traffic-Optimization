# QuantumTrafficOptimization

An exploratory traffic-control experiment using classical simulated annealing to solve a quadratic unconstrained binary optimization (QUBO) model. This is a starting point for a research project, not evidence of quantum advantage or a validated city forecast.

## Run

Python 3.13.5 was used for the paper runs. From this folder:

```sh
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows alternative: .venv\Scripts\activate
python -m pip install -r requirements.txt
python real_city_sim.py
python check_model.py
python city_video.py
```

The included cached networks make subsequent runs independent of OSM downloads. Delete a city's JSON and GraphML cache to request a new network. Download failures produce an explicitly labeled synthetic grid with the error recorded. Do not describe fallback networks as real roads.

## Files

- `real_city_sim.py`: network retrieval, experiment, figures and results summary.
- `city_video.py`: split-screen MP4 from the saved Fremont trial-zero trajectories.
- `city_results.json`, `results.csv`: all 900 individual run results (5 networks x 6 years x 3 controllers x 10 seeds).
- `RESULTS.md`: actual results and comparison with the greedy baseline.
- `METHODS.md`: assumptions, corrected equations and limitations.
- `check_model.py`: objective algebra, vehicle conservation, matched inputs, and no-adoption checks.
- `osm_cache/`: downloaded networks, simplified simulation network and provenance.
- The paper's two figures are in `../figures_paper/`; `../make_figures.py` regenerates them from `results.csv`.

Read RESULTS.md and METHODS.md before using the graphics in a paper. The figures report sampled-network outcomes; none are whole-city estimates. Positive reduction means improvement; negative reduction means deterioration. No parameters were fitted to force QUBO to outperform the baselines.
