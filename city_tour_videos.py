# -*- coding: utf-8 -*-
"""
city_tour_videos.py
====================
One MP4 per city (not one giant GIF) -- real, seekable video files with
normal player controls. Redesigned for comprehensibility after feedback
that the first version (world_tour_animation.py) was confusing:

  - Roads are drawn using their REAL curved OpenStreetMap geometry, with
    the full surrounding street network as a muted backdrop, so it reads
    as an actual map rather than an abstract node-and-line diagram.
  - Traffic is shown with the familiar Google-Maps-style convention:
    green = flowing, yellow = moderate, red = jammed. This replaces the
    old rapidly-flipping node color (which is what read as "flashing
    lights") with one slow-changing, universally-understood signal.
  - A permanent on-screen legend explains every color, for a viewer who
    has never seen this project before.
  - Colors/sizes are linearly interpolated between simulation steps and
    rendered at a real video frame rate, so motion is smooth, not a slide
    show. Each city's video is ~19 seconds (a ~2s title card + ~15s of
    2025-2030 + a ~2s ending comparison card), not a few rushed seconds.

Requires imageio-ffmpeg (installed this session) for real MP4 export --
this machine has no system ffmpeg otherwise.

Output: figures/city_tours/<city>.mp4  (one file per city)
"""
import os, sys, pickle
import numpy as np
import matplotlib
import imageio_ffmpeg
matplotlib.rcParams['animation.ffmpeg_path'] = imageio_ffmpeg.get_ffmpeg_exe()
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as mpatches

sys.path.insert(0, r"C:\QuantumTrafficOptimization")
from simulate_qubo_traffic import (
    build_grid_adjacency, construct_qubo_matrix,
    solve_qubo_simulated_quantum_annealing,
)
from world_city_sim import ALL_CITIES
from real_city_sim import NON_SIGNAL_HIGHWAY_CLASSES, _highway_tag, _select_connected_core

OUTPUT_DIR = r"C:\QuantumTrafficOptimization"
FIG_DIR = os.path.join(OUTPUT_DIR, "figures")
VIDEO_DIR = os.path.join(FIG_DIR, "city_tours")
CACHE_DIR = os.path.join(OUTPUT_DIR, "osm_cache")
os.makedirs(VIDEO_DIR, exist_ok=True)

YEARS = [2025, 2026, 2027, 2028, 2029, 2030]
QUBO_ADOPTION = {2025: 0.0, 2026: 0.0, 2027: 0.20, 2028: 0.50, 2029: 0.80, 2030: 1.00}
POP_GROWTH = 0.02
MAX_NODES = 100000   # effectively uncapped -- use every real connected intersection

T_YEAR = 10          # simulation steps per year
SUBFRAMES = 5        # interpolated render frames per simulation step (smoothness)
FPS = 20
INTRO_FRAMES = int(2.2 * FPS)
OUTRO_FRAMES = int(2.6 * FPS)

BG = "#0a0e16"
STREET_MUTED = "#33465c"
TEXT_COL = "#e8eef2"
SYNC_COLOR = "#26e0e0"
CTRL_COLORS = {"Fixed-Time": "#ff6a5c", "QA-QUBO": "#26e07f"}

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": BG,
    "text.color": TEXT_COL, "font.family": "sans-serif", "font.size": 10,
})


def congestion_color(frac):
    """0 (flowing) -> green, 0.5 -> yellow, 1 (gridlocked) -> red."""
    frac = min(max(frac, 0.0), 1.0)
    green = np.array([46, 204, 113]); yellow = np.array([241, 196, 15]); red = np.array([231, 76, 60])
    if frac < 0.5:
        c = green * (1 - frac / 0.5) + yellow * (frac / 0.5)
    else:
        t = (frac - 0.5) / 0.5
        c = yellow * (1 - t) + red * t
    return tuple(c / 255.0)


# =============================================================================
# NETWORK LOADING: simulated subset (for the physics) + full street backdrop
# (for realism), both using real curved OSM geometry where available.
# =============================================================================
def get_city_network(city_name):
    safe = city_name.replace(', ', '_').replace(' ', '_')
    cache_path = os.path.join(CACHE_DIR, f"{safe}.pkl")
    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            G = pickle.load(f)
        # Simulated/colored roads exclude freeway-grade edges (not realistically
        # modeled as a 2-phase signal intersection) -- same fix as real_city_sim.py.
        # The full unfiltered graph is still used for the muted background map.
        G_signal = G.edge_subgraph(
            [(u, v, k) for u, v, k, data in G.edges(keys=True, data=True)
             if _highway_tag(data) not in NON_SIGNAL_HIGHWAY_CLASSES]
        ).copy()
        # Connected-core selection (not independent top-N by degree, which can
        # strand a high-degree node whose real neighbors didn't make the cut,
        # rendering as a disconnected dot with no road linking it to anything).
        nodes = list(_select_connected_core(G_signal, MAX_NODES))
        if len(nodes) >= 6:
            idx = {n: i for i, n in enumerate(nodes)}
            N = len(nodes)
            positions = {idx[n]: (G.nodes[n]['x'], G.nodes[n]['y']) for n in nodes}
            edges, neighbors, seen, edge_geom = [], {i: [] for i in range(N)}, set(), {}
            for u, v, data in G_signal.edges(data=True):
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
                geom = data.get('geometry')
                if geom is not None:
                    edge_geom[key] = np.array(geom.coords)
                else:
                    edge_geom[key] = np.array([positions[i], positions[j]])
            if len(edges) >= 4:
                backdrop = [np.array(data['geometry'].coords) if data.get('geometry') is not None
                            else np.array([(G.nodes[u]['x'], G.nodes[u]['y']), (G.nodes[v]['x'], G.nodes[v]['y'])])
                            for u, v, data in G.edges(data=True)]
                return N, edges, neighbors, positions, edge_geom, backdrop, True

    # synthetic fallback -- same 5x5 grid used everywhere else in this project
    L = 5
    edges, neighbors = build_grid_adjacency(L)
    N = L * L
    positions = {r * L + c: (c, L - 1 - r) for r in range(L) for c in range(L)}
    edge_geom = {(min(i, j), max(i, j)): np.array([positions[i], positions[j]]) for (i, j, _) in edges}
    return N, edges, neighbors, positions, edge_geom, [], False


def normalize_all(positions, edge_geom, backdrop):
    xs = np.array([p[0] for p in positions.values()])
    ys = np.array([p[1] for p in positions.values()])
    cx, cy = xs.mean(), ys.mean()
    scale = max(xs.max() - xs.min(), ys.max() - ys.min(), 1e-9)

    def tf(pt):
        return ((pt[0] - cx) / scale * 4.6, (pt[1] - cy) / scale * 4.6)

    pos2 = {i: tf(p) for i, p in positions.items()}
    geom2 = {k: np.array([tf(pt) for pt in line]) for k, line in edge_geom.items()}
    backdrop2 = [np.array([tf(pt) for pt in line]) for line in backdrop]
    return pos2, geom2, backdrop2


# =============================================================================
# SIMULATION ACROSS ALL 6 YEARS (same physics as world_tour_animation.py)
# =============================================================================
def simulate_city_across_years(N, edges, neighbors, demand_base, seed):
    rng_f = np.random.default_rng(seed); rng_q = np.random.default_rng(seed + 1)
    q_ns_f = rng_f.uniform(2.0, 6.0, size=N); q_ew_f = rng_f.uniform(2.0, 6.0, size=N)
    q_ns_q = rng_q.uniform(2.0, 6.0, size=N); q_ew_q = rng_q.uniform(2.0, 6.0, size=N)
    pl_ns_f = np.zeros(N); pl_ew_f = np.zeros(N); pl_ns_q = np.zeros(N); pl_ew_q = np.zeros(N)
    x_prev_f = np.array([i % 2 for i in range(N)], dtype=int); x_prev_q = x_prev_f.copy()

    sat, sw_loss, co2_idle, co2_stop = 9.0, 0.25, 2.79, 22.0
    total_co2_f = total_co2_q = 0.0
    frames = []; t_global = 0

    for year in YEARS:
        adoption = QUBO_ADOPTION[year]
        n_qubo = int(N * adoption); qubo_set = set(range(n_qubo))
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

            ph = (t_global // 2) % 2
            x_f = np.array([(ph + i) % 2 for i in range(N)], dtype=int)

            if n_qubo > 0:
                eff_ns_q = q_ns_q + 1.45 * pl_ns_q; eff_ew_q = q_ew_q + 1.45 * pl_ew_q
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
                npl_ns = np.zeros(N); npl_ew = np.zeros(N); step_idle = 0.0
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
                sw_s = float(np.sum(switched * np.minimum(q_ns + q_ew, 5.0)))
                if panel == 'f':
                    pl_ns_f[:] = npl_ns; pl_ew_f[:] = npl_ew
                    total_co2_f += step_idle * 15.0 * co2_idle + sw_s * co2_stop
                else:
                    pl_ns_q[:] = npl_ns; pl_ew_q[:] = npl_ew
                    total_co2_q += step_idle * 15.0 * co2_idle + sw_s * co2_stop

            sync_q = set()
            for (i, j, axis) in edges:
                if (axis == "NS" and x_q[i] == 1 and x_q[j] == 1) or (axis == "EW" and x_q[i] == 0 and x_q[j] == 0):
                    sync_q.add((min(i, j), max(i, j)))

            frames.append(dict(
                year=year, adoption=adoption, demand=demand,
                q_ns_f=q_ns_f.copy(), q_ew_f=q_ew_f.copy(),
                q_ns_q=q_ns_q.copy(), q_ew_q=q_ew_q.copy(), sync_q=sync_q,
                co2_f=total_co2_f / 1000.0, co2_q=total_co2_q / 1000.0,
            ))
            x_prev_f = x_f.copy(); x_prev_q = x_q.copy(); t_global += 1

    return frames


def lerp(a, b, t):
    return a * (1 - t) + b * t


# =============================================================================
# RENDER ONE CITY
# =============================================================================
def render_city(cd):
    N, edges, edge_geom, backdrop = cd['N'], cd['edges'], cd['edge_geom'], cd['backdrop']
    frames = cd['frames']; q_max = cd['q_max']

    fig = plt.figure(figsize=(16, 8.6), facecolor=BG)
    ax_f = fig.add_axes([0.02, 0.10, 0.46, 0.72])
    ax_q = fig.add_axes([0.52, 0.10, 0.46, 0.72])
    axes = {"Fixed-Time": ax_f, "QA-QUBO": ax_q}

    all_x = [p[0] for line in (backdrop or edge_geom.values()) for p in line]
    all_y = [p[1] for line in (backdrop or edge_geom.values()) for p in line]
    pad = 0.5
    xlim = (min(all_x) - pad, max(all_x) + pad); ylim = (min(all_y) - pad, max(all_y) + pad)

    for ctrl, ax in axes.items():
        ax.set_xlim(xlim); ax.set_ylim(ylim); ax.set_aspect('equal'); ax.axis('off')
        for line in backdrop:
            ax.plot(line[:, 0], line[:, 1], color=STREET_MUTED, lw=0.7, alpha=0.55, zorder=1)
        ax.set_title(ctrl, color=CTRL_COLORS[ctrl], fontsize=15, fontweight='bold', pad=10)

    header = fig.text(0.5, 0.965, f"{cd['short']}", ha='center', va='top',
                       fontsize=19, fontweight='bold', color=TEXT_COL)
    tagline = fig.text(0.5, 0.925, "", ha='center', va='top', fontsize=10.5, color="#9fb3c8")
    year_badge = fig.text(0.5, 0.885, "", ha='center', va='top', fontsize=13.5,
                           fontweight='bold', color='#ffd54a')
    stats_line = fig.text(0.5, 0.055, "", ha='center', color=TEXT_COL, fontsize=10.5)

    legend_items = [
        ("Flowing traffic", congestion_color(0.05)),
        ("Moderate congestion", congestion_color(0.5)),
        ("Heavy congestion / near gridlock", congestion_color(0.95)),
        ("Green-wave coordinated (QA-QUBO only)", SYNC_COLOR),
    ]
    handles = [mpatches.Patch(color=c, label=l) for l, c in legend_items]
    fig.legend(handles=handles, loc='lower center', ncol=4, fontsize=8.7,
               frameon=False, bbox_to_anchor=(0.5, 0.005), labelcolor=TEXT_COL)

    edge_lines = {ctrl: {} for ctrl in axes}
    node_dots = {ctrl: {} for ctrl in axes}
    co2_texts = {}
    for ctrl, ax in axes.items():
        for key, geom in edge_geom.items():
            ln, = ax.plot(geom[:, 0], geom[:, 1], color=congestion_color(0), lw=2.0, zorder=2, solid_capstyle='round')
            edge_lines[ctrl][key] = ln
        for i in range(N):
            x0, y0 = cd['pos'][i]
            dot, = ax.plot([x0], [y0], marker='o', markersize=6, color=congestion_color(0),
                           markeredgecolor='black', markeredgewidth=0.4, zorder=3)
            node_dots[ctrl][i] = dot
        co2_texts[ctrl] = ax.text(0.5, -0.03, "", transform=ax.transAxes, ha='center', va='top',
                                   fontsize=11.5, color=CTRL_COLORS[ctrl], fontweight='bold')

    tag = "REAL OpenStreetMap road network" if cd['is_real'] else "Illustrative synthetic grid (Overpass unavailable for this city)"
    tagline.set_text(f"{N} intersections   |   {tag}")

    def render_state(local_f):
        """local_f is a float frame index across the whole 2025-2030 arc, in units
        of simulation steps -- fractional part blends between two real states."""
        k = int(np.floor(local_f))
        t = local_f - k
        k2 = min(k + 1, len(frames) - 1)
        fr0, fr1 = frames[k], frames[k2]

        year_badge.set_text(f"{lerp(fr0['year'], fr1['year'], t):.0f}   |   "
                             f"QA-QUBO adoption: {lerp(fr0['adoption'], fr1['adoption'], t) * 100:.0f}%")

        for ctrl, qnk, qek, synck in [
            ("Fixed-Time", 'q_ns_f', 'q_ew_f', None),
            ("QA-QUBO", 'q_ns_q', 'q_ew_q', 'sync_q'),
        ]:
            q0 = fr0[qnk] + fr0[qek]; q1 = fr1[qnk] + fr1[qek]
            q_now = lerp(q0, q1, t)
            for (i, j, axis) in edges:
                key = (min(i, j), max(i, j))
                load = float(q_now[i] + q_now[j]) / 2.0 / q_max
                sync_now = 0.0
                if synck is not None:
                    s0 = 1.0 if key in fr0[synck] else 0.0
                    s1 = 1.0 if key in fr1[synck] else 0.0
                    sync_now = lerp(s0, s1, t)
                base_col = congestion_color(load)
                if sync_now > 0.05:
                    col = tuple(np.array(base_col) * (1 - sync_now) + np.array(matplotlib.colors.to_rgb(SYNC_COLOR)) * sync_now)
                    lw = 2.0 + 1.6 * sync_now
                else:
                    col, lw = base_col, 2.0
                edge_lines[ctrl][key].set_color(col)
                edge_lines[ctrl][key].set_linewidth(lw)
            for i in range(N):
                load_i = float(q_now[i]) / q_max
                node_dots[ctrl][i].set_color(congestion_color(load_i))
                node_dots[ctrl][i].set_markersize(5.5 + 5.0 * min(load_i, 1.0))

        co2_f = lerp(fr0['co2_f'], fr1['co2_f'], t)
        co2_q = lerp(fr0['co2_q'], fr1['co2_q'], t)
        co2_texts["Fixed-Time"].set_text(f"cumulative CO2: {co2_f:.0f} kg")
        co2_texts["QA-QUBO"].set_text(f"cumulative CO2: {co2_q:.0f} kg")
        pct = 100 * (co2_f - co2_q) / max(co2_f, 1e-9)
        stats_line.set_text(f"demand \u00d7{lerp(fr0['demand'], fr1['demand'], t):.2f} baseline   |   "
                             f"CO2 saved so far: {pct:+.1f}%")

    total_sim_frames = (len(frames) - 1) * SUBFRAMES
    TOTAL = INTRO_FRAMES + total_sim_frames + OUTRO_FRAMES

    def update(frame):
        if frame < INTRO_FRAMES:
            render_state(0.0)
            year_badge.set_text(f"{YEARS[0]}   |   Both panels start identical (0% QA-QUBO adoption)")
        elif frame < INTRO_FRAMES + total_sim_frames:
            local_f = (frame - INTRO_FRAMES) / SUBFRAMES
            render_state(local_f)
        else:
            render_state(len(frames) - 1)
            final = frames[-1]
            pct = 100 * (final['co2_f'] - final['co2_q']) / max(final['co2_f'], 1e-9)
            year_badge.set_text(f"2030, full deployment   |   QA-QUBO net CO2 change: {pct:+.1f}%")
        return []

    ani = animation.FuncAnimation(fig, update, frames=TOTAL, interval=1000 // FPS, blit=False, repeat=True)
    out_path = os.path.join(VIDEO_DIR, cd['safe'] + ".mp4")
    ani.save(out_path, writer=animation.FFMpegWriter(fps=FPS, bitrate=2400), dpi=110)
    plt.close(fig)
    return out_path, TOTAL


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    only = sys.argv[1:] if len(sys.argv) > 1 else None
    CITY_ORDER = sorted(ALL_CITIES.keys(), key=lambda c: ALL_CITIES[c]['pm25_2023'])
    if only:
        CITY_ORDER = [c for c in CITY_ORDER if any(o.lower() in c.lower() for o in only)]

    for city in CITY_ORDER:
        cfg = ALL_CITIES[city]
        print(f"=== {city} ===", flush=True)
        N, edges, neighbors, raw_pos, edge_geom, backdrop, is_real = get_city_network(city)
        pos, edge_geom, backdrop = normalize_all(raw_pos, edge_geom, backdrop)
        seed_base = abs(hash(city)) % 100000
        frames = simulate_city_across_years(N, edges, neighbors, cfg['demand_base'], seed_base)
        q_max = max(max(float(np.max(fr['q_ns_f'] + fr['q_ew_f'])), float(np.max(fr['q_ns_q'] + fr['q_ew_q'])))
                    for fr in frames)
        cd = dict(
            name=city, short=cfg['short'].replace('\n', ', '), safe=city.replace(', ', '_').replace(' ', '_'),
            N=N, edges=edges, edge_geom=edge_geom, backdrop=backdrop, pos=pos,
            is_real=is_real, frames=frames, q_max=max(q_max, 1.0),
        )
        print(f"  N={N}  real_osm={is_real}  rendering...", flush=True)
        out_path, total_frames = render_city(cd)
        print(f"  saved {out_path} ({total_frames} frames, {total_frames/FPS:.1f}s)", flush=True)

    print("ALL CITY VIDEOS DONE.")
