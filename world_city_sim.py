# -*- coding: utf-8 -*-
"""
world_city_sim.py  -  10-city global quantum traffic simulation (2025-2030)
============================================================================
Extends real_city_sim.py's 5-city run (Fremont, Delhi, LA, Singapore, Oslo)
with 5 more cities spanning other continents and the low-pollution end of
the spectrum: Mexico City, Beijing, Jakarta, London, Zurich.

Reuses real_city_sim.py's simulation engine untouched (imported, not copied)
so results for the original 5 cities are byte-identical to before.

IMPORTANT - data honesty note (see DATA_SOURCES below and DATA_SOURCES.md):
Every real-world statistic used for validation/context is tagged with an
explicit source and a confidence level ('verified' vs 'approximate').
Do not cite an 'approximate' figure in the paper without checking the
underlying source yourself first -- same rule as before.
"""

import sys, os, json, copy, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from real_city_sim import (
    CITIES as ORIGINAL_CITIES,
    download_osm,
    osm_to_qubo_structure,
    run_city,
    YEARS,
    CONTROLLERS,
    OUTPUT_DIR,
    FIG_DIR,
)

# =============================================================================
# NEW CITIES -- real sourced data, each tagged with source + confidence
# =============================================================================
# Congestion figures are TomTom Traffic Index 2025 report (covers 2024 driving
# data), aggregated travel-time-per-10km metric, cross-checked via
# https://statranker.org/mobility/top-100-cities-by-traffic-congestion-index-2025/
# PM2.5 figures are IQAir 2023 World Air Quality Report unless noted otherwise.

NEW_CITIES = {
    'Mexico City, Mexico': {
        'center': (19.4326, -99.1332),
        'radius': 500,
        'demand_base': 3.9,
        'tomtom_2024': None,                 # no directly comparable %-index found
        'congestion_10km_2024': '32:33',
        'pm25_2023': 22.3,
        'color': '#d35400',
        'short': 'Mexico City\nMexico',
        'source_confidence': 'approximate',  # PM2.5 via secondary source citing IQAir rank #14 globally
    },
    'Beijing, China': {
        'center': (39.9042, 116.4074),
        'radius': 500,
        'demand_base': 3.4,
        'tomtom_2024': None,
        'congestion_10km_2024': '29:10',
        'pm25_2023': 32.0,                   # Beijing Municipal Ecology & Environment Bureau, 2023 official avg (NOT IQAir)
        'color': '#8e44ad',
        'short': 'Beijing\nChina',
        'source_confidence': 'approximate',  # official gov't monitoring, not IQAir; US embassy sensor read ~39
    },
    'Jakarta, Indonesia': {
        'center': (-6.2088, 106.8456),
        'radius': 400,
        'demand_base': 4.2,
        'tomtom_2024': None,
        'congestion_10km_2024': '32:29',
        'pm25_2023': 37.3,                   # IQAir 2023, ranked most-polluted capital city that year
        'color': '#e67e22',
        'short': 'Jakarta\nIndonesia',
        'source_confidence': 'verified',
    },
    'London, UK': {
        'center': (51.5074, -0.1278),
        'radius': 500,
        'demand_base': 2.7,
        'tomtom_2024': None,
        'congestion_10km_2024': '33:17',
        'pm25_2023': 8.4,                    # IQAir 2023 via Statista
        'color': '#2980b9',
        'short': 'London\nUK',
        'source_confidence': 'verified',
    },
    'Zurich, Switzerland': {
        'center': (47.3769, 8.5417),
        'radius': 500,
        'demand_base': 1.6,
        'tomtom_2024': None,
        'congestion_10km_2024': '28:22',
        'pm25_2023': 10.9,                   # Switzerland-level figure, older baseline -- lowest-confidence number in this set
        'color': '#16a085',
        'short': 'Zurich\nSwitzerland',
        'source_confidence': 'approximate',
    },
}

TIER2_CITIES = {
    # Continent coverage completion: Africa, East Asia (Tokyo), South America, Oceania.
    # See DATA_SOURCES.md for full sourcing notes on every number below.
    'Cairo, Egypt': {
        'center': (30.0444, 31.2357),
        'radius': 500,
        'demand_base': 3.6,
        'tomtom_2024': None,
        'congestion_10km_2024': '26:46',   # TomTom 2025 report (2024 data), via statranker.org
        'pm25_2023': 42.4,                  # IQAir 2023, ranked ~10th most polluted city globally that year
        'color': '#a04000',
        'short': 'Cairo\nEgypt',
        'source_confidence': 'verified',
    },
    'Tokyo, Japan': {
        'center': (35.6762, 139.6503),
        'radius': 500,
        'demand_base': 3.0,
        'tomtom_2024': None,
        'congestion_10km_2024': '29:18',   # TomTom 2025 report (2024 data), via statranker.org
        'pm25_2023': 11.7,                  # IQAir figure is a 2019 baseline -- could not confirm a 2023-specific figure
        'color': '#f4d03f',
        'short': 'Tokyo\nJapan',
        'source_confidence': 'approximate',
    },
    'Sao Paulo, Brazil': {
        'center': (-23.5505, -46.6333),
        'radius': 500,
        'demand_base': 3.7,
        'tomtom_2024': None,
        'congestion_10km_2024': None,       # not found in the aggregated TomTom table pass
        'pm25_2023': 15.3,                  # IQAir figure is a 2019 baseline -- could not confirm a 2023-specific figure
        'color': '#6c3483',
        'short': 'Sao Paulo\nBrazil',
        'source_confidence': 'approximate',
    },
    'Sydney, Australia': {
        'center': (-33.8688, 151.2093),
        'radius': 500,
        'demand_base': 2.2,
        'tomtom_2024': None,
        'congestion_10km_2024': None,       # not found in the aggregated TomTom table pass
        'pm25_2023': 10.1,                  # IQAir figure is a 2019 baseline; NSW EPA's 2023 network-wide range
                                             # (4.3-8.6 ug/m3) suggests it has likely improved somewhat since
        'color': '#48c9b0',
        'short': 'Sydney\nAustralia',
        'source_confidence': 'approximate',
    },
}

ALL_CITIES = {**ORIGINAL_CITIES, **NEW_CITIES, **TIER2_CITIES}

# tag originals as verified/previously-used (unchanged from real_city_sim.py)
for c in ORIGINAL_CITIES:
    ALL_CITIES[c] = dict(ALL_CITIES[c])
    ALL_CITIES[c]['source_confidence'] = 'verified'
    ALL_CITIES[c].setdefault('congestion_10km_2024', None)

plt.rcParams.update({
    'font.family': 'serif', 'font.size': 10,
    'axes.labelsize': 11, 'axes.titlesize': 12,
    'figure.dpi': 200, 'savefig.dpi': 200,
})


def _sec(mmss):
    """Parse 'MM:SS' -> total seconds. None passthrough."""
    if mmss is None:
        return None
    m, s = mmss.split(':')
    return int(m) * 60 + int(s)


def main():
    print('=' * 66)
    print('  WORLD CITY SIMULATION: 10 cities, 4 continents, 2025-2030')
    print('=' * 66)

    all_results = {}
    for city_name, cfg in ALL_CITIES.items():
        print(f"\n{'='*58}\n  CITY: {city_name}\n{'='*58}")
        G = download_osm(city_name, cfg['center'], cfg['radius'])
        city_res = run_city(city_name, cfg, G)
        all_results[city_name] = city_res
        ft25 = city_res[2025]['Fixed-Time']['co2_kg']['mean']
        qa30 = city_res[2030]['QA-QUBO']['co2_kg']['mean']
        gr30 = city_res[2030]['Local-Greedy']['co2_kg']['mean']
        print(f"    CO2 (kg/run): Fixed-Time 2025={ft25:.1f}  ->  "
              f"2030: Greedy={gr30:.1f}  QA-QUBO={qa30:.1f}")

    results_path = os.path.join(OUTPUT_DIR, 'world_results.json')
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved: {results_path}")

    # =========================================================================
    # FULL CONTROLLER COMPARISON TABLE (Fixed-Time / Local-Greedy / QA-QUBO)
    # Printed explicitly so QUBO-vs-Greedy is never hidden behind a
    # QUBO-vs-Fixed-Time-only headline number.
    # =========================================================================
    print('\n' + '=' * 100)
    print('FULL 2030 CONTROLLER COMPARISON (same-year, 100% QA-QUBO adoption) -- CO2 kg/run')
    print('=' * 100)
    print(f"{'City':22s} {'Fixed-Time':>11s} {'Local-Greedy':>13s} {'QA-QUBO':>10s} "
          f"{'Greedy vs Fixed':>16s} {'QUBO vs Fixed':>14s} {'QUBO vs Greedy':>15s}")
    summary_rows = []
    for city in ALL_CITIES:
        ft = all_results[city][2030]['Fixed-Time']['co2_kg']['mean']
        gr = all_results[city][2030]['Local-Greedy']['co2_kg']['mean']
        qa = all_results[city][2030]['QA-QUBO']['co2_kg']['mean']
        gr_vs_ft = 100 * (ft - gr) / ft
        qa_vs_ft = 100 * (ft - qa) / ft
        qa_vs_gr = 100 * (gr - qa) / gr
        summary_rows.append((city, ft, gr, qa, gr_vs_ft, qa_vs_ft, qa_vs_gr))
        print(f"{city:22s} {ft:11.1f} {gr:13.1f} {qa:10.1f} "
              f"{gr_vs_ft:15.1f}% {qa_vs_ft:13.1f}% {qa_vs_gr:14.1f}%")
    n_qubo_wins = sum(1 for r in summary_rows if r[6] > 0)
    print(f"\nQA-QUBO beats Local-Greedy in {n_qubo_wins}/{len(summary_rows)} cities "
          f"(this figure is unstable across independent implementations -- see chat notes).")

    # =========================================================================
    # FIG 12: WORLD RANKING -- all 10 cities, sorted by real-world PM2.5,
    # all 3 controllers shown (2030, same-year) so Greedy is never hidden.
    # =========================================================================
    print('\nGenerating world figures ...')
    ordered = sorted(ALL_CITIES.keys(), key=lambda c: ALL_CITIES[c]['pm25_2023'])
    short = [ALL_CITIES[c]['short'] for c in ordered]
    colors = [ALL_CITIES[c]['color'] for c in ordered]

    fig, ax = plt.subplots(figsize=(15, 6.5))
    x = np.arange(len(ordered))
    width = 0.26

    ft_vals = [all_results[c][2030]['Fixed-Time']['co2_kg']['mean'] for c in ordered]
    gr_vals = [all_results[c][2030]['Local-Greedy']['co2_kg']['mean'] for c in ordered]
    qa_vals = [all_results[c][2030]['QA-QUBO']['co2_kg']['mean'] for c in ordered]

    ax.bar(x - width, ft_vals, width, label='Fixed-Time', color='#7f8c8d', edgecolor='black', lw=0.6)
    ax.bar(x,          gr_vals, width, label='Local-Greedy', color=colors, alpha=0.55, edgecolor='black', lw=0.6)
    ax.bar(x + width,  qa_vals, width, label='QA-QUBO', color=colors, alpha=0.95, edgecolor='black', lw=0.6)

    for i, c in enumerate(ordered):
        pm = ALL_CITIES[c]['pm25_2023']
        conf = ALL_CITIES[c]['source_confidence']
        mark = '' if conf == 'verified' else '*'
        ax.text(x[i], -max(ft_vals) * 0.06, f'{pm:.1f}{mark}', ha='center', va='top',
                fontsize=8, color='#c0392b' if pm > 30 else '#27ae60', fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels(short, fontsize=8)
    ax.set_ylabel('CO2 (kg per 12-hour peak-period run)')
    ax.set_title(
        '10-City World Comparison, 2030 (100% deployment): Fixed-Time vs Local-Greedy vs QA-QUBO\n'
        'Cities sorted left-to-right by real 2023 PM2.5 (annotated below bars, μg/m³; '
        '* = approximate/secondary-source figure, see DATA_SOURCES.md)', fontsize=10.5)
    ax.legend(fontsize=9)
    ax.grid(True, axis='y', ls='--', alpha=0.35)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig12_world_ranking.png'), bbox_inches='tight')
    plt.close(fig)
    print('  Saved fig12_world_ranking.png')

    # =========================================================================
    # FIG 13: DOES THE BENEFIT SCALE WITH BASELINE POLLUTION?
    # Scatter: real PM2.5 (x) vs % CO2 change 2025-Fixed -> 2030-controller (y),
    # one series per controller, both Greedy and QUBO shown honestly.
    # =========================================================================
    import matplotlib.patches as mpatches
    fig, ax = plt.subplots(figsize=(10.5, 7))
    legend_handles = []
    for city in ALL_CITIES:
        pm = ALL_CITIES[city]['pm25_2023']
        col = ALL_CITIES[city]['color']
        ft25 = all_results[city][2025]['Fixed-Time']['co2_kg']['mean']
        gr30 = all_results[city][2030]['Local-Greedy']['co2_kg']['mean']
        qa30 = all_results[city][2030]['QA-QUBO']['co2_kg']['mean']
        pct_gr = 100 * (ft25 - gr30) / ft25
        pct_qa = 100 * (ft25 - qa30) / ft25
        ax.scatter(pm, pct_qa, s=170, color=col, edgecolors='black', lw=1.1,
                   marker='o', zorder=5)
        ax.scatter(pm, pct_gr, s=170, color=col, edgecolors='black', lw=1.1,
                   marker='^', zorder=5, alpha=0.55)
        legend_handles.append(mpatches.Patch(color=col, label=ALL_CITIES[city]['short'].replace('\n', ', ')))

    ax.axhline(0, color='gray', lw=1, ls='-')
    marker_legend = [
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='gray',
                   markeredgecolor='black', markersize=11, label='QA-QUBO'),
        plt.Line2D([0], [0], marker='^', color='w', markerfacecolor='gray',
                   markeredgecolor='black', markersize=11, alpha=0.55, label='Local-Greedy'),
    ]
    leg1 = ax.legend(handles=marker_legend, loc='lower right', fontsize=9.5,
                      title='Controller', framealpha=0.95)
    ax.add_artist(leg1)
    ax.legend(handles=legend_handles, loc='center left', bbox_to_anchor=(1.01, 0.5),
              fontsize=8, title='City', framealpha=0.95)

    ax.set_xlabel('Real 2023 PM2.5 baseline (μg/m³) -- proxy for how congested/polluted the city already is')
    ax.set_ylabel('% CO2 change, 2025 Fixed-Time → 2030 full deployment\n(demand growth included; positive = improvement)')
    ax.set_title(
        f'Does controller benefit scale with baseline pollution? ({len(ALL_CITIES)} cities)\n'
        '(Includes 2%/yr demand growth 2025-2030 -- a city can show a net INCREASE\n'
        'if traffic growth outpaces the controller\'s efficiency gain)', fontsize=10.5)
    ax.grid(True, ls='--', alpha=0.4)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig13_pollution_vs_benefit.png'), bbox_inches='tight')
    plt.close(fig)
    print('  Saved fig13_pollution_vs_benefit.png')

    print('\n' + '=' * 66)
    print('WORLD SIMULATION COMPLETE.')
    print(f'Figures: {FIG_DIR}')
    print('=' * 66)


if __name__ == '__main__':
    main()
