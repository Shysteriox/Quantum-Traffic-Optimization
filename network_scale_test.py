# -*- coding: utf-8 -*-
"""
network_scale_test.py  -  Does QA-QUBO's edge over Local-Greedy grow with
network size (more intersections)?
============================================================================
Downloads the SAME city center at increasing OSM radii (more real
intersections pulled in each time), runs one representative demand level
per size, and plots % CO2 improvement vs. N (number of intersections).

Cache is keyed by (city, radius) -- separate from real_city_sim.py's cache,
which only stores one fixed radius per city.

Cities chosen to span the spectrum already validated: Fremont (moderate
demand) and Delhi (already-saturated demand) -- the two ends of the
phase-transition story from the earlier bifurcation experiment.
"""

import sys, os, json, pickle, warnings, time
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

try:
    import osmnx as ox
    HAS_OSMNX = True
except ImportError:
    HAS_OSMNX = False

from real_city_sim import (
    CITIES,
    osm_to_qubo_structure,
    run_simulation,
    OUTPUT_DIR,
    FIG_DIR,
    CONTROLLERS,
    POP_GROWTH,
)

SIZED_CACHE_DIR = os.path.join(OUTPUT_DIR, 'osm_cache_sized')
os.makedirs(SIZED_CACHE_DIR, exist_ok=True)

MAX_NODES = 160          # raised from real_city_sim's default 70 for this test
N_TRIALS = 6              # more trials since we're only running 1 demand level now
RADII = [500, 1000, 1500, 2200]   # meters; 500 reuses/refetches at same size as before
TEST_CITIES = ['Fremont, CA', 'Delhi, India']

plt.rcParams.update({
    'font.family': 'serif', 'font.size': 10,
    'axes.labelsize': 11, 'axes.titlesize': 12,
    'figure.dpi': 200, 'savefig.dpi': 200,
})


def download_osm_sized(city_name, center, radius, max_attempts=3, wait_s=25):
    """Radius-aware OSM download+cache. Retries with backoff on Overpass timeout."""
    if not HAS_OSMNX:
        return None
    safe = city_name.replace(', ', '_').replace(' ', '_')
    cache_path = os.path.join(SIZED_CACHE_DIR, f"{safe}_r{radius}.pkl")
    if os.path.exists(cache_path):
        print(f"    Loaded cache: {city_name} @ r={radius}m")
        with open(cache_path, 'rb') as f:
            return pickle.load(f)

    for attempt in range(1, max_attempts + 1):
        print(f"    Downloading OSM: {city_name} @ r={radius}m (attempt {attempt}/{max_attempts})...", flush=True)
        try:
            G = ox.graph_from_point(center, dist=radius, network_type='drive',
                                     retain_all=False, simplify=True)
            G = ox.bearing.add_edge_bearings(G)
            G_und = ox.convert.to_undirected(G)
            with open(cache_path, 'wb') as f:
                pickle.dump(G_und, f)
            return G_und
        except Exception as e:
            print(f"      failed ({e})")
            if attempt < max_attempts:
                print(f"      waiting {wait_s}s before retry...")
                time.sleep(wait_s)
    print(f"    Giving up on {city_name} @ r={radius}m -- using synthetic fallback.")
    return None


def run_one_size(city_name, cfg, radius):
    G = download_osm_sized(city_name, cfg['center'], radius)
    N, edges, neighbors = osm_to_qubo_structure(G, f"{city_name} r={radius}", max_nodes=MAX_NODES)
    is_synthetic = (G is None)

    # representative demand: city's base demand grown to ~2028 equivalent, full QUBO adoption
    demand = cfg['demand_base'] * (1 + POP_GROWTH) ** 3

    metrics = {}
    for ctrl in CONTROLLERS:
        trial_vals = []
        for trial in range(N_TRIALS):
            seed = 77000 + radius + CONTROLLERS.index(ctrl) * 500 + trial
            qfrac = 1.0 if ctrl == 'QA-QUBO' else 0.0
            r = run_simulation(N, edges, neighbors, demand, ctrl, seed, qfrac)
            trial_vals.append(r['co2_kg'])
        metrics[ctrl] = {'mean': float(np.mean(trial_vals)), 'std': float(np.std(trial_vals))}

    return {
        'N': N,
        'n_edges': len(edges),
        'synthetic_fallback': is_synthetic,
        'metrics': metrics,
    }


def main():
    print('=' * 66)
    print('  NETWORK-SIZE SCALING TEST: does QUBO\'s edge grow with N?')
    print('=' * 66)

    all_results = {}
    for city_name in TEST_CITIES:
        cfg = CITIES[city_name]
        all_results[city_name] = []
        print(f"\n--- {city_name} ---")
        for radius in RADII:
            res = run_one_size(city_name, cfg, radius)
            res['radius'] = radius
            all_results[city_name].append(res)
            ft = res['metrics']['Fixed-Time']['mean']
            gr = res['metrics']['Local-Greedy']['mean']
            qa = res['metrics']['QA-QUBO']['mean']
            tag = ' [SYNTHETIC FALLBACK]' if res['synthetic_fallback'] else ''
            print(f"    r={radius:5d}m  N={res['N']:4d}  "
                  f"Fixed={ft:7.1f}  Greedy={gr:7.1f}  QUBO={qa:7.1f}  "
                  f"QUBOvsGreedy={100*(gr-qa)/gr:+5.1f}%{tag}")
            time.sleep(6)   # be polite to Overpass between successive queries

    out_path = os.path.join(OUTPUT_DIR, 'network_scale_results.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved: {out_path}")

    # =========================================================================
    # FIGURE: % improvement vs N, one panel per city
    # =========================================================================
    fig, axes = plt.subplots(1, len(TEST_CITIES), figsize=(7 * len(TEST_CITIES), 5.5))
    if len(TEST_CITIES) == 1:
        axes = [axes]

    for ax, city_name in zip(axes, TEST_CITIES):
        rows = all_results[city_name]
        rows_sorted = sorted(rows, key=lambda r: r['N'])
        Ns = [r['N'] for r in rows_sorted]
        qa_vs_gr = [100 * (r['metrics']['Local-Greedy']['mean'] - r['metrics']['QA-QUBO']['mean'])
                    / r['metrics']['Local-Greedy']['mean'] for r in rows_sorted]
        qa_vs_ft = [100 * (r['metrics']['Fixed-Time']['mean'] - r['metrics']['QA-QUBO']['mean'])
                    / r['metrics']['Fixed-Time']['mean'] for r in rows_sorted]
        gr_vs_ft = [100 * (r['metrics']['Fixed-Time']['mean'] - r['metrics']['Local-Greedy']['mean'])
                    / r['metrics']['Fixed-Time']['mean'] for r in rows_sorted]

        ax.axhline(0, color='gray', lw=1)
        ax.plot(Ns, qa_vs_ft, 'o-', color='#8e44ad', lw=2, ms=8, label='QA-QUBO vs Fixed-Time')
        ax.plot(Ns, gr_vs_ft, 's--', color='#7f8c8d', lw=2, ms=7, label='Local-Greedy vs Fixed-Time')
        ax.plot(Ns, qa_vs_gr, '^-', color='#e74c3c', lw=2, ms=8, label='QA-QUBO vs Local-Greedy')

        for r in rows_sorted:
            if r['synthetic_fallback']:
                ax.axvline(r['N'], color='red', ls=':', alpha=0.3)

        ax.set_xlabel('Intersections in sampled network (N)')
        ax.set_ylabel('% CO2 improvement (positive = better)')
        ax.set_title(f'{city_name}\n(radii tested: {RADII} m)', fontsize=11)
        ax.legend(fontsize=8.5)
        ax.grid(True, ls='--', alpha=0.4)

    fig.suptitle(
        "Does QA-QUBO's advantage grow with network size?\n"
        "Same city center, increasing OSM download radius -> more real intersections per run",
        fontsize=12, y=1.03)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig14_network_scale.png'), bbox_inches='tight')
    plt.close(fig)
    print('  Saved fig14_network_scale.png')
    print('\nDONE.')


if __name__ == '__main__':
    main()
