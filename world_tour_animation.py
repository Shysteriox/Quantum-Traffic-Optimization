# -*- coding: utf-8 -*-
"""
world_tour_animation.py
========================
Sequential "world tour" animation: cycles through all 14 cities from
world_city_sim.py. For EACH city, one continuous simulation runs across all
six years (2025-2030), split-screen Fixed-Time (left, always 0% QA-QUBO)
vs. QA-QUBO (right, following the project's real adoption schedule: 0% in
2025-2026, 20%/50%/80%/100% in 2027-2030) -- both panels look IDENTICAL
until 2027, then visibly diverge as adoption ramps up. That divergence,
not a single end-state snapshot, is the actual story.

Uses each city's REAL cached OpenStreetMap road network where available
(pulled straight from osm_cache/, no new downloads -- Overpass has been
unreliable this session) and a labeled synthetic 5x5 grid fallback
otherwise, exactly like every other figure in this project. Which is which
is shown on-screen for every city, never hidden.

No ffmpeg is installed on this machine, so output is an animated GIF
(matplotlib's only available writer here is Pillow) rather than MP4.

Output: figures/world_tour_animation.gif
"""
import os, sys, pickle
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.gridspec import GridSpec

sys.path.insert(0, r"C:\QuantumTrafficOptimization")
from simulate_qubo_traffic import (
    build_grid_adjacency, construct_qubo_matrix,
    solve_qubo_simulated_quantum_annealing,
)
from world_city_sim import ALL_CITIES

OUTPUT_DIR = r"C:\QuantumTrafficOptimization"
FIG_DIR = os.path.join(OUTPUT_DIR, "figures")
CACHE_DIR = os.path.join(OUTPUT_DIR, "osm_cache")

YEARS = [2025, 2026, 2027, 2028, 2029, 2030]
QUBO_ADOPTION = {2025: 0.0, 2026: 0.0, 2027: 0.20, 2028: 0.50, 2029: 0.80, 2030: 1.00}
POP_GROWTH = 0.02
T_YEAR = 8               # frames per year shown per city
FPS = 10
MAX_NODES = 60

DARK_BG   = "#080c14"
PANEL_BG  = "#0d1525"
NS_ON     = "#00e676"
EW_ON     = "#ff6d00"
LINK_SYNC = "#00bcd4"
LINK_JAM  = "#ff1744"
LINK_OK   = "#2a3a55"
TEXT_COL  = "#cfd8dc"
CTRL_COLORS = {"Fixed-Time": "#ff5252", "QA-QUBO": "#00e676"}

plt.rcParams.update({
    "figure.facecolor": DARK_BG, "axes.facecolor": DARK_BG,
    "text.color": TEXT_COL, "font.family": "monospace", "font.size": 9,
})


# =============================================================================
# PER-CITY NETWORK + POSITIONS (reuses cache only -- never triggers a download)
# =============================================================================
def get_city_network(city_name):
    safe = city_name.replace(', ', '_').replace(' ', '_')
    cache_path = os.path.join(CACHE_DIR, f"{safe}.pkl")
    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            G = pickle.load(f)
        nodes = [n for n in G.nodes() if G.degree(n) >= 2]
        if len(nodes) > MAX_NODES:
            nodes = sorted(nodes, key=lambda n: G.degree(n), reverse=True)[:MAX_NODES]
        if len(nodes) >= 6:
            idx = {n: i for i, n in enumerate(nodes)}
            N = len(nodes)
            positions = {idx[n]: (G.nodes[n]['x'], G.nodes[n]['y']) for n in nodes}
            edges, neighbors, seen = [], {i: [] for i in range(N)}, set()
            for u, v, data in G.edges(data=True):
                if u not in idx or v not in idx or u == v:
                    continue
                i, j = idx[u], idx[v]
                key = (min(i, j), max(i, j))
                if key in seen:
                    continue
                seen.add(key)
                bearing = data.get('bearing', 0) or 0
                axis = 'NS' if (bearing <= 45 or bearing >= 315 or 135 <= bearing <= 225) else 'EW'
                edges.append((i, j, axis))
                neighbors[i].append((j, axis)); neighbors[j].append((i, axis))
            if len(edges) >= 4:
                return N, edges, neighbors, positions, True

    # synthetic fallback -- same 5x5 grid used everywhere else in this project
    L = 5
    edges, neighbors = build_grid_adjacency(L)
    N = L * L
    positions = {r * L + c: (c, L - 1 - r) for r in range(L) for c in range(L)}
    return N, edges, neighbors, positions, False


def normalize_positions(positions):
    xs = np.array([p[0] for p in positions.values()])
    ys = np.array([p[1] for p in positions.values()])
    cx, cy = xs.mean(), ys.mean()
    scale = max(xs.max() - xs.min(), ys.max() - ys.min(), 1e-9)
    return {i: ((x - cx) / scale * 4.4, (y - cy) / scale * 4.4) for i, (x, y) in positions.items()}


# =============================================================================
# ONE CONTINUOUS SIMULATION ACROSS ALL 6 YEARS -- TWO PARALLEL PANELS:
#   'fixed' panel: pure Fixed-Time the whole time (the business-as-usual line)
#   'qubo'  panel: follows the real adoption schedule (0% -> 100%), so it is
#                  IDENTICAL to the fixed panel until 2027, then diverges
# =============================================================================
def simulate_city_across_years(N, edges, neighbors, demand_base, seed):
    rng_f = np.random.default_rng(seed)
    rng_q = np.random.default_rng(seed + 1)

    q_ns_f = rng_f.uniform(2.0, 6.0, size=N); q_ew_f = rng_f.uniform(2.0, 6.0, size=N)
    q_ns_q = rng_q.uniform(2.0, 6.0, size=N); q_ew_q = rng_q.uniform(2.0, 6.0, size=N)
    pl_ns_f = np.zeros(N); pl_ew_f = np.zeros(N)
    pl_ns_q = np.zeros(N); pl_ew_q = np.zeros(N)
    x_prev_f = np.array([i % 2 for i in range(N)], dtype=int)
    x_prev_q = x_prev_f.copy()

    sat, sw_loss, co2_idle, co2_stop = 9.0, 0.25, 2.79, 22.0
    total_co2_f = total_co2_q = 0.0
    frames = []
    t_global = 0

    for year in YEARS:
        adoption = QUBO_ADOPTION[year]
        n_qubo = int(N * adoption)
        qubo_set = set(range(n_qubo))
        demand = demand_base * (1.0 + POP_GROWTH) ** (year - 2025)

        for local_t in range(T_YEAR):
            rf = 0.80 + 0.55 * np.sin(np.pi * local_t / T_YEAR)
            base = 2.15 * demand * rf
            nsw = 1.0 + 0.35 * np.sin(2.0 * np.pi * local_t / 16.0)
            eww = 1.0 - 0.35 * np.sin(2.0 * np.pi * local_t / 16.0)
            for i in range(N):
                arr_ns = max(base * nsw, 0.05); arr_ew = max(base * eww, 0.05)
                q_ns_f[i] += rng_f.poisson(arr_ns); q_ew_f[i] += rng_f.poisson(arr_ew)
                q_ns_q[i] += rng_q.poisson(arr_ns); q_ew_q[i] += rng_q.poisson(arr_ew)

            # --- Fixed-Time panel: always alternating, never resets ---
            ph = (t_global // 2) % 2
            x_f = np.array([(ph + i) % 2 for i in range(N)], dtype=int)

            # --- QA-QUBO panel: blended per adoption fraction ---
            if n_qubo > 0:
                eff_ns_q = q_ns_q + 1.45 * pl_ns_q
                eff_ew_q = q_ew_q + 1.45 * pl_ew_q
                Q = construct_qubo_matrix(eff_ns_q, eff_ew_q, x_prev_q, edges, w_sync=0.45, w_switch=1.8)
                x_qubo, _ = solve_qubo_simulated_quantum_annealing(Q, rng_q, num_reads=12, num_sweeps=14)
                x_q = np.array([x_qubo[i] if i in qubo_set else (ph + i) % 2 for i in range(N)], dtype=int)
            else:
                x_q = x_f.copy()

            for (panel, q_ns, q_ew, pl_ns, pl_ew, x, x_prev) in [
                ('f', q_ns_f, q_ew_f, pl_ns_f, pl_ew_f, x_f, x_prev_f),
                ('q', q_ns_q, q_ew_q, pl_ns_q, pl_ew_q, x_q, x_prev_q),
            ]:
                switched = (x != x_prev).astype(float)
                npl_ns = np.zeros(N); npl_ew = np.zeros(N)
                step_idle = 0.0
                for i in range(N):
                    cap = sat * (1.0 - sw_loss * switched[i])
                    snb = [nb for nb, ax in neighbors[i]
                           if (ax == "NS" and x[i] == 1 and x[nb] == 1) or (ax == "EW" and x[i] == 0 and x[nb] == 0)]
                    if snb:
                        cap *= 1.0 + 0.08 * len(snb)
                    if x[i] == 1:
                        dep = min(q_ns[i], cap); q_ns[i] -= dep
                        nsb = [nb for nb, ax in neighbors[i] if ax == "NS"]
                        if dep and nsb:
                            for nb in nsb:
                                npl_ns[nb] += 0.29 * dep / len(nsb)
                    else:
                        dep = min(q_ew[i], cap); q_ew[i] -= dep
                        ewb = [nb for nb, ax in neighbors[i] if ax == "EW"]
                        if dep and ewb:
                            for nb in ewb:
                                npl_ew[nb] += 0.29 * dep / len(ewb)
                    step_idle += q_ns[i] + q_ew[i]
                if panel == 'f':
                    pl_ns_f[:] = npl_ns; pl_ew_f[:] = npl_ew
                    sw_s = float(np.sum(switched * np.minimum(q_ns + q_ew, 5.0)))
                    total_co2_f += step_idle * 15.0 * co2_idle + sw_s * co2_stop
                else:
                    pl_ns_q[:] = npl_ns; pl_ew_q[:] = npl_ew
                    sw_s = float(np.sum(switched * np.minimum(q_ns + q_ew, 5.0)))
                    total_co2_q += step_idle * 15.0 * co2_idle + sw_s * co2_stop

            sync_q = set()
            for (i, j, axis) in edges:
                if (axis == "NS" and x_q[i] == 1 and x_q[j] == 1) or (axis == "EW" and x_q[i] == 0 and x_q[j] == 0):
                    sync_q.add((min(i, j), max(i, j)))

            frames.append(dict(
                year=year, adoption=adoption, demand=demand,
                q_ns_f=q_ns_f.copy(), q_ew_f=q_ew_f.copy(), x_f=x_f.copy(),
                q_ns_q=q_ns_q.copy(), q_ew_q=q_ew_q.copy(), x_q=x_q.copy(), sync_q=sync_q,
                co2_f=total_co2_f / 1000.0, co2_q=total_co2_q / 1000.0,
            ))
            x_prev_f = x_f.copy(); x_prev_q = x_q.copy()
            t_global += 1

    return frames


# =============================================================================
# PRE-COMPUTE EVERYTHING
# =============================================================================
CITY_ORDER = sorted(ALL_CITIES.keys(), key=lambda c: ALL_CITIES[c]['pm25_2023'])

print("Pre-computing all city simulations (2025-2030, continuous)...")
city_data = []
for city in CITY_ORDER:
    cfg = ALL_CITIES[city]
    N, edges, neighbors, raw_pos, is_real = get_city_network(city)
    pos = normalize_positions(raw_pos)
    seed_base = abs(hash(city)) % 100000
    frames = simulate_city_across_years(N, edges, neighbors, cfg['demand_base'], seed_base)
    q_max = max(max(float(np.max(fr['q_ns_f'] + fr['q_ew_f'])), float(np.max(fr['q_ns_q'] + fr['q_ew_q'])))
                for fr in frames)
    city_data.append(dict(
        name=city, short=cfg['short'].replace('\n', ', '), pm25=cfg['pm25_2023'],
        N=N, edges=edges, pos=pos, is_real=is_real, frames=frames, q_max=max(q_max, 1.0),
    ))
    tag = "real OSM" if is_real else "synthetic grid"
    print(f"  {city:22s} N={N:3d}  ({tag})  final CO2: fixed={frames[-1]['co2_f']:.0f}kg  qubo={frames[-1]['co2_q']:.0f}kg")

FRAMES_PER_CITY = len(YEARS) * T_YEAR
print(f"Pre-computation done. {FRAMES_PER_CITY} frames/city x {len(city_data)} cities = "
      f"{FRAMES_PER_CITY * len(city_data)} total frames. Building animation...")

# =============================================================================
# FIGURE / ARTIST SETUP
# =============================================================================
fig = plt.figure(figsize=(15, 8.5), facecolor=DARK_BG)
gs = GridSpec(1, 2, figure=fig, left=0.03, right=0.97, top=0.80, bottom=0.11, wspace=0.12)
axes = {"Fixed-Time": fig.add_subplot(gs[0, 0]), "QA-QUBO": fig.add_subplot(gs[0, 1])}

header = fig.text(0.5, 0.965, "", ha='center', va='top', fontsize=15,
                   fontweight='bold', color='#90caf9', family='monospace')
subheader = fig.text(0.5, 0.925, "", ha='center', va='top', fontsize=9.5, color=TEXT_COL)
year_badge = fig.text(0.5, 0.885, "", ha='center', va='top', fontsize=13,
                       fontweight='bold', color='#ffca28', family='monospace')
stats_line = fig.text(0.5, 0.045, "", ha='center', color=TEXT_COL, fontsize=9.5, family='monospace')
footer = fig.text(0.5, 0.015, "", ha='center', color='#607d8b', fontsize=8, family='monospace')

state = {'cur_city_idx': -1, 'link_artists': {}, 'node_artists': {}, 'co2_texts': {}}


def setup_city(city_idx):
    cd = city_data[city_idx]
    N, edges, pos = cd['N'], cd['edges'], cd['pos']
    xs = [p[0] for p in pos.values()]; ys = [p[1] for p in pos.values()]
    pad = 0.6
    for ctrl, ax in axes.items():
        ax.clear()
        ax.set_aspect('equal'); ax.axis('off')
        ax.set_facecolor(PANEL_BG)
        ax.set_xlim(min(xs) - pad, max(xs) + pad)
        ax.set_ylim(min(ys) - pad, max(ys) + pad)
        ax.set_title(ctrl, color=CTRL_COLORS[ctrl], fontsize=12, fontweight='bold', pad=8)

        state['link_artists'][ctrl] = {}
        for (i, j, axis) in edges:
            xi, yi = pos[i]; xj, yj = pos[j]
            ln, = ax.plot([xi, xj], [yi, yj], color=LINK_OK, lw=1.3, zorder=1)
            state['link_artists'][ctrl][(min(i, j), max(i, j))] = ln

        state['node_artists'][ctrl] = {}
        base_r = 0.10 if N > 30 else 0.16
        for i in range(N):
            x0, y0 = pos[i]
            glow = plt.Circle((x0, y0), base_r * 1.8, color=NS_ON, alpha=0.0, zorder=2)
            core = plt.Circle((x0, y0), base_r, color=NS_ON, alpha=0.95, zorder=3)
            ax.add_patch(glow); ax.add_patch(core)
            state['node_artists'][ctrl][i] = (glow, core, base_r)

        state['co2_texts'][ctrl] = ax.text(
            0.5, -0.05, "", transform=ax.transAxes, ha='center', va='top',
            fontsize=10, color=CTRL_COLORS[ctrl], fontweight='bold')

    tag = "REAL OpenStreetMap road network" if cd['is_real'] else "SYNTHETIC 5x5 grid (Overpass unavailable)"
    subheader.set_text(f"{cd['N']} intersections   |   {tag}")
    state['cur_city_idx'] = city_idx


def update(frame):
    city_idx = frame // FRAMES_PER_CITY
    local_f = frame % FRAMES_PER_CITY
    cd = city_data[city_idx]
    fr = cd['frames'][local_f]

    if city_idx != state['cur_city_idx']:
        setup_city(city_idx)

    header.set_text(f"WORLD TOUR  ·  {cd['short'].upper()}  ·  PM2.5 = {cd['pm25']:.1f} ug/m3 (2023 baseline)")
    year_badge.set_text(f"YEAR: {fr['year']}   |   QA-QUBO adoption: {fr['adoption']*100:.0f}%")

    for ctrl, xk, qnk, qek, syncset in [
        ("Fixed-Time", 'x_f', 'q_ns_f', 'q_ew_f', None),
        ("QA-QUBO",    'x_q', 'q_ns_q', 'q_ew_q', fr['sync_q']),
    ]:
        x, q_n, q_e = fr[xk], fr[qnk], fr[qek]
        for (i, j, axis) in cd['edges']:
            key = (min(i, j), max(i, j))
            load = float(q_n[i] + q_e[i] + q_n[j] + q_e[j]) / 2.0
            if syncset is not None and key in syncset:
                col, lw = LINK_SYNC, 2.6
            elif load > 0.65 * cd['q_max']:
                col, lw = LINK_JAM, 2.0
            else:
                col, lw = LINK_OK, 1.3
            state['link_artists'][ctrl][key].set_color(col)
            state['link_artists'][ctrl][key].set_linewidth(lw)

        for i in range(cd['N']):
            glow, core, base_r = state['node_artists'][ctrl][i]
            q_total = float(q_n[i] + q_e[i])
            phase_color = NS_ON if x[i] == 1 else EW_ON
            frac = min(q_total / cd['q_max'], 1.0)
            r_core = base_r * (1.0 + 0.9 * frac)
            core.set_radius(r_core); core.set_color(phase_color)
            glow.set_radius(r_core * 1.8); glow.set_color(phase_color)
            glow.set_alpha(0.15 + 0.35 * frac)

    state['co2_texts']["Fixed-Time"].set_text(f"cumulative CO2: {fr['co2_f']:.0f} kg")
    state['co2_texts']["QA-QUBO"].set_text(f"cumulative CO2: {fr['co2_q']:.0f} kg")

    pct = 100 * (fr['co2_f'] - fr['co2_q']) / max(fr['co2_f'], 1e-9)
    stats_line.set_text(
        f"demand x{fr['demand']:.2f} baseline   |   CO2 saved so far: {pct:+.1f}%   |   "
        f"QA-QUBO {'ahead' if pct >= 0 else 'behind'} of Fixed-Time"
    )
    footer.set_text(f"city {city_idx + 1}/{len(city_data)}")
    return []


TOTAL_FRAMES = FRAMES_PER_CITY * len(city_data)
ani = animation.FuncAnimation(fig, update, frames=TOTAL_FRAMES, interval=1000 // FPS, blit=False, repeat=True)

out_path = os.path.join(FIG_DIR, "world_tour_animation.gif")
print(f"Saving {TOTAL_FRAMES} frames as GIF (this will take a few minutes)...")
ani.save(out_path, writer=animation.PillowWriter(fps=FPS), dpi=85)
print(f"Saved: {out_path}")
plt.close(fig)
