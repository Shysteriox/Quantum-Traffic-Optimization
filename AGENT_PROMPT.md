# Quantum Traffic Optimization — Agent Task Prompt

## Context
I'm writing a research paper on applying quantum computing (specifically quantum annealing
and QUBO formulation) to optimize urban traffic signals to reduce vehicle idling and CO2
emissions. I need you to build and run a complete simulation experiment for me.

---

## Your Task

Build and run a **multi-city, multi-year quantum traffic optimization simulation** in Python.
Save all outputs to a folder called `QuantumTrafficOptimization` on this machine.

---

## Requirements

### Cities (5 total)
Simulate traffic for these 5 cities using **real road networks from OpenStreetMap**
(use the `osmnx` Python library, ~400-600m radius around city center):

1. **Fremont, CA, USA** — center: (37.5485, -121.9886)
2. **Delhi, India** — center: (28.6139, 77.2090)
3. **Los Angeles, CA, USA** — center: (34.0522, -118.2437)
4. **Singapore** — center: (1.3521, 103.8198)
5. **Oslo, Norway** — center: (59.9139, 10.7522)

If osmnx download fails for any city, fall back to a synthetic 5x5 grid.

---

### Years: 2025–2030
- **2025–2026**: Baseline only (no quantum deployment) — use to validate against real data
- **2027**: 20% of intersections use QA-QUBO
- **2028**: 50% adoption
- **2029**: 80% adoption
- **2030**: 100% adoption

Traffic demand grows **2% per year** (vehicle growth).

---

### 3 Controllers to Compare
1. **Fixed-Time** — alternating fixed schedule (current standard)
2. **Local-Greedy** — each intersection independently picks the direction with the longer queue
3. **QA-QUBO** — Quadratic Unconstrained Binary Optimization solved via simulated quantum
   annealing; binary variable x_i=1 (NS green) or x_i=0 (EW green) per intersection;
   QUBO matrix minimizes total queue length while maximizing green-wave synchronization
   along corridors and penalizing unnecessary signal switches

For each road link (i,j): classify as NS (bearing 0±45° or 180±45°) or EW otherwise.
QUBO matrix terms:
- Diagonal: Q[i,i] = w_q * (eff_ew[i] - eff_ns[i])   (reward NS green when NS queue is heavier)
- Off-diagonal NS link: Q[i,j] -= w_sync              (reward both NS-green)
- Off-diagonal EW link: Q[i,i] += w_sync, Q[j,j] += w_sync, Q[i,j] -= w_sync
- Switch penalty: Q[i,i] += w_switch * x_prev[i]      (penalize changing state)
- Use w_q=1.0, w_sync=0.45, w_switch=1.8

Solve QUBO via simulated quantum annealing (you can use dwave-neal or implement your own
with transverse-field Ising annealing or standard simulated annealing as a stand-in).

---

### Simulation Parameters
- Each "run": 48 timesteps (representing a 12-hour peak period, 15-min intervals)
- Rush-hour demand envelope: Gaussian peak around timestep 10
- Emission factors per vehicle per 15-min idle step:
  - CO2: 0.038 kg
  - NOx: 0.047 g
  - Fuel: 0.016 L
- Run **3 trials** per (city × year × controller) for statistical averaging
- Scale to annual figures: multiply by 250 workdays × 2 peak periods

---

### Real Data for Validation (2025 baseline)
Compare your simulated Fixed-Time congestion to these real values:

| City         | TomTom Index 2024 (% extra time) | IQAir PM2.5 2023 (μg/m³) |
|--------------|----------------------------------|---------------------------|
| Fremont, CA  | 22%                              | 8.5                       |
| Delhi        | 46%                              | 92.7                      |
| Los Angeles  | 28%                              | 10.2                      |
| Singapore    | 19%                              | 13.6                      |
| Oslo         | 22%                              | 5.4                       |

Sources:
- TomTom Traffic Index: https://www.tomtom.com/traffic-index/
- IQAir World Air Quality Report 2023: https://www.iqair.com/world-air-quality-report

---

### Required Output Figures (publication-quality, 300 DPI, save as PNG)

**Fig A — Multi-City Impact Comparison**
Bar chart: 5 cities on x-axis, grouped bars for Fixed-Time 2025 vs QA-QUBO 2030
Show 3 metrics side by side: CO2, NOx, average wait time. Annotate % reduction.

**Fig B — Year-by-Year Emission Trend (2025–2030)**
Line chart: each city gets 2 lines (Fixed-Time=dashed, QA-QUBO=solid), normalized to
their 2025 baseline. Shade the 2027–2030 deployment era in green.

**Fig C — Model Validation Scatter Plot**
X-axis: real TomTom index (listed above). Y-axis: your simulated congestion index
(convert avg wait time to % above free-flow). Plot R² value. Show best-fit line.

**Fig D — Health Impact Projection**
Left panel: annual CO2 saved per city (Fixed-Time 2025 → QA-QUBO 2030).
Right panel: stacked bar showing current PM2.5 baseline + traffic-attributable reduction
with QA-QUBO. Draw WHO guideline (5 μg/m³) as horizontal red line.

---

### Also Build: Mini Motorways-Style Animation (YouTube video)

Create a dark-mode city traffic animation for **Fremont, CA** showing the real OSM road
network. Split-screen: Fixed-Time (left) vs QA-QUBO (right). Include:
- Road links colored by congestion level (green=flowing, red=gridlocked)
- Intersection nodes that pulse/glow based on queue size
- Day/night sky gradient (background color cycles)
- Year counter (2025 → 2030) and live CO2 counter
- Seasonal variation in traffic demand
- Save as MP4 (use ffmpeg) or animated GIF fallback

---

### Save Everything To
```
QuantumTrafficOptimization/
├── real_city_sim.py       ← main simulation script
├── city_video.py          ← animation script
├── city_results.json      ← all numerical results
├── osm_cache/             ← cached OSM downloads
└── figures/
    ├── figA_city_comparison.png
    ├── figB_yearly_trend.png
    ├── figC_validation.png
    ├── figD_health_impact.png
    └── fremont_traffic_animation.mp4 (or .gif)
```

---

### Notes
- Use serif fonts, clean academic style for all figures
- Include error bars (std dev) on bar charts
- All print statements must use ASCII (avoid Unicode special characters in console output
  to prevent Windows cp1252 encoding errors)
- Cache OSM downloads to disk so re-runs are fast
- Print progress as the simulation runs (city name, year, etc.)

Run the simulation after building it and show me all the output figures when done.
