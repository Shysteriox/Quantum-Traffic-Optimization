"""
animate_traffic.py
==================
Generates a dark-mode animated traffic dashboard comparing three signal
controllers (Fixed-Time, Local-Greedy, QA-QUBO) running simultaneously on
a 4x4 urban intersection grid during a simulated 30-minute rush hour.

Output: figures/traffic_animation.gif  (YouTube-uploadable via any MP4 converter)

Visual elements:
  • Each intersection node: glowing circle sized by queue depth
  • Color: green (#00e676) = NS green phase, orange (#ff6d00) = EW green phase
  • Road links: bright when adjacent phases are coordinated (green wave)
  • Live CO2 counter and emissions bar chart
  • Rush-hour demand heatmap waveform
"""

import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from matplotlib.collections import LineCollection
from matplotlib.gridspec import GridSpec

sys.path.insert(0, r"C:\QuantumTrafficOptimization")
from simulate_qubo_traffic import (
    build_grid_adjacency, construct_qubo_matrix,
    solve_qubo_simulated_quantum_annealing
)

OUTPUT_DIR = r"C:\QuantumTrafficOptimization"
FIG_DIR = os.path.join(OUTPUT_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

# ── simulation constants ────────────────────────────────────────────────────
L, N, DT, T = 4, 16, 15.0, 120
SEED = 77

DARK_BG   = "#080c14"
GRID_COL  = "#1a2035"
NS_ON     = "#00e676"   # bright green  – NS phase is green
EW_ON     = "#ff6d00"   # deep orange   – EW phase is green
LINK_SYNC = "#00bcd4"   # cyan          – synchronized corridor (green wave)
LINK_OFF  = "#1e2d45"   # dark blue     – non-synchronized link
TEXT_COL  = "#cfd8dc"

CONTROLLERS = ["Fixed-Time", "Local-Greedy", "QA-QUBO"]
CTRL_COLORS = {"Fixed-Time": "#ff5252", "Local-Greedy": "#7c4dff", "QA-QUBO": "#00e676"}
CTRL_LABELS = {
    "Fixed-Time":  "Fixed-Time Schedule",
    "Local-Greedy":"Local Actuated (Uncoordinated)",
    "QA-QUBO":     "Quantum Annealing QUBO"
}


def run_with_history(controller: str, seed: int = SEED):
    """Run one 30-min simulation and capture full state history."""
    rng = np.random.default_rng(seed)
    edges, neighbors = build_grid_adjacency(L)

    q_ns = rng.uniform(2.0, 6.0, size=N)
    q_ew = rng.uniform(2.0, 6.0, size=N)
    platoon_ns = np.zeros(N)
    platoon_ew = np.zeros(N)
    x_prev = np.array([(r + c) % 2 for r in range(L) for c in range(L)], dtype=int)

    sat = 10.0; sw_loss = 0.25; co2_idle = 2.79; nox_idle = 0.0035
    co2_stop = 22.0

    hist = dict(q_ns=[], q_ew=[], x=[], co2=[], nox=[], departed=[],
                sync_links=[])   # list of (step, link_set_in_sync)
    total_co2 = total_nox = total_dep = 0.0

    for t in range(T):
        rf = 0.80 + 0.55 * np.sin(np.pi * t / T)
        base = 2.15 * rf
        nsw = 1.0 + 0.35 * np.sin(2.0 * np.pi * t / 16.0)
        eww = 1.0 - 0.35 * np.sin(2.0 * np.pi * t / 16.0)

        for r in range(L):
            for c in range(L):
                i = r * L + c
                q_ns[i] += rng.poisson(base * (1.25 if c in (1,2) else 0.85) * nsw)
                q_ew[i] += rng.poisson(base * (1.25 if r in (1,2) else 0.85) * eww)

        eff_ns = q_ns + 1.45 * platoon_ns
        eff_ew = q_ew + 1.45 * platoon_ew

        if controller == "Fixed-Time":
            ph = (t // 2) % 2
            x = np.array([(ph + r + c) % 2 for r in range(L) for c in range(L)], dtype=int)
        elif controller == "Local-Greedy":
            x = (q_ns >= q_ew).astype(int)
        else:
            Q = construct_qubo_matrix(eff_ns, eff_ew, x_prev, edges, w_sync=0.55, w_switch=1.8)
            x, _ = solve_qubo_simulated_quantum_annealing(Q, rng, num_reads=30, num_sweeps=22)

        switched = (x != x_prev).astype(float)

        # record synced links
        sync = set()
        for (i, j, axis) in edges:
            if (axis == "NS" and x[i] == 1 and x[j] == 1) or \
               (axis == "EW" and x[i] == 0 and x[j] == 0):
                sync.add((min(i,j), max(i,j)))
        hist['sync_links'].append(sync)
        hist['q_ns'].append(q_ns.copy())
        hist['q_ew'].append(q_ew.copy())
        hist['x'].append(x.copy())

        # platoon process
        stop_pl = 0.0
        for i in range(N):
            if x[i] == 1:
                q_ns[i] += 0.35 * platoon_ns[i]; total_dep += 0.65 * platoon_ns[i]
                q_ew[i] += platoon_ew[i];         stop_pl  += platoon_ew[i]
            else:
                q_ew[i] += 0.35 * platoon_ew[i]; total_dep += 0.65 * platoon_ew[i]
                q_ns[i] += platoon_ns[i];         stop_pl  += platoon_ns[i]

        npl_ns = np.zeros(N); npl_ew = np.zeros(N)
        for i in range(N):
            cap = sat * (1.0 - sw_loss * switched[i])
            snb = [nb for (nb,ax) in neighbors[i]
                   if (ax=="NS" and x[i]==1 and x[nb]==1) or
                      (ax=="EW" and x[i]==0 and x[nb]==0)]
            if snb: cap *= 1.0 + 0.10 * len(snb)
            if x[i] == 1:
                dep = min(q_ns[i], cap); q_ns[i] -= dep; total_dep += dep
                ns_nb = [nb for nb,ax in neighbors[i] if ax=="NS"]
                if dep and ns_nb:
                    for nb in ns_nb: npl_ns[nb] += 0.32*dep/len(ns_nb)
            else:
                dep = min(q_ew[i], cap); q_ew[i] -= dep; total_dep += dep
                ew_nb = [nb for nb,ax in neighbors[i] if ax=="EW"]
                if dep and ew_nb:
                    for nb in ew_nb: npl_ew[nb] += 0.32*dep/len(ew_nb)

        platoon_ns, platoon_ew = npl_ns, npl_ew
        idle = float(np.sum(q_ns + q_ew))
        sw_s = float(np.sum(switched * np.minimum(q_ns + q_ew, 5.0)))
        total_co2 += idle*DT*co2_idle + (stop_pl + sw_s)*co2_stop
        total_nox += idle*DT*nox_idle + (stop_pl + sw_s)*0.025
        hist['co2'].append(total_co2 / 1000.0)
        hist['nox'].append(total_nox)
        hist['departed'].append(total_dep)
        x_prev = x.copy()

    return hist


# ── pre-run all histories ─────────────────────────────────────────────────
print("Pre-running simulations…")
histories = {c: run_with_history(c) for c in CONTROLLERS}
print("Simulations done. Building animation frames…")

# ── intersection positions (normalized) ──────────────────────────────────
pos = {}
for r in range(L):
    for c in range(L):
        pos[r*L+c] = (c, L-1-r)   # (x, y), y flipped so row 0 is top

edges_list, _ = build_grid_adjacency(L)

# ── compute global queue max for consistent node scaling ──────────────────
q_max = 1.0
for h in histories.values():
    for qn, qe in zip(h['q_ns'], h['q_ew']):
        q_max = max(q_max, float(np.max(qn + qe)))
co2_max = max(h['co2'][-1] for h in histories.values()) * 1.05

# ── figure layout ─────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor": DARK_BG, "axes.facecolor": DARK_BG,
    "text.color": TEXT_COL, "axes.labelcolor": TEXT_COL,
    "xtick.color": TEXT_COL, "ytick.color": TEXT_COL,
    "axes.edgecolor": "#2a3a55", "grid.color": "#1a2035",
    "font.family": "monospace", "font.size": 9,
})

fig = plt.figure(figsize=(22, 11), facecolor=DARK_BG)
gs  = GridSpec(2, 4, figure=fig,
               left=0.03, right=0.97, top=0.91, bottom=0.08,
               wspace=0.30, hspace=0.38)

grid_axes = [fig.add_subplot(gs[0, k]) for k in range(3)]
co2_ax    = fig.add_subplot(gs[0, 3])
queue_ax  = fig.add_subplot(gs[1, :3])
demand_ax = fig.add_subplot(gs[1, 3])

# title
fig.text(0.5, 0.965, "URBAN TRAFFIC SIGNAL OPTIMIZATION  •  QUANTUM ANNEALING vs. CLASSICAL CONTROLLERS",
         ha='center', va='top', fontsize=13, fontweight='bold',
         color='#90caf9', family='monospace')
fig.text(0.5, 0.945, "4×4 Urban Grid  |  16 Intersections  |  30-Minute Rush Hour Simulation",
         ha='center', va='top', fontsize=9, color=TEXT_COL)

# ── static axes setup ────────────────────────────────────────────────────
for k, (ax, ctrl) in enumerate(zip(grid_axes, CONTROLLERS)):
    ax.set_xlim(-0.7, L-0.3); ax.set_ylim(-0.7, L-0.3)
    ax.set_aspect('equal'); ax.axis('off')
    ax.set_facecolor(GRID_BG := "#0d1525")
    for spine in ax.spines.values():
        spine.set_edgecolor(CTRL_COLORS[ctrl]); spine.set_linewidth(1.5)
        spine.set_visible(True)
    ax.set_title(CTRL_LABELS[ctrl], color=CTRL_COLORS[ctrl],
                 fontsize=10, fontweight='bold', pad=6)

co2_ax.set_facecolor("#0d1525")
co2_ax.set_xlim(0, len(CONTROLLERS)-1); co2_ax.set_ylim(0, co2_max)
co2_ax.set_title("Cumulative CO₂ (kg)", color="#90caf9", fontsize=10)
co2_ax.set_xticks(range(len(CONTROLLERS)))
co2_ax.set_xticklabels(["Fixed", "Local", "QA-QUBO"], fontsize=8)
co2_ax.set_ylabel("kg CO₂", color=TEXT_COL, fontsize=8)
co2_ax.grid(axis='y', alpha=0.2)
co2_bars = co2_ax.bar(range(len(CONTROLLERS)), [0]*3,
                       color=[CTRL_COLORS[c] for c in CONTROLLERS],
                       alpha=0.85, width=0.6, edgecolor='none')

queue_ax.set_xlim(0, T); queue_ax.set_ylim(0, q_max * L**2 / 2)
queue_ax.set_xlabel("Simulation step (× 15 s)", color=TEXT_COL, fontsize=9)
queue_ax.set_ylabel("Total network queue (vehicles)", color=TEXT_COL, fontsize=9)
queue_ax.set_title("Live Network-Wide Queue", color="#90caf9", fontsize=10)
queue_ax.grid(alpha=0.2)
queue_lines = {c: queue_ax.plot([], [], color=CTRL_COLORS[c],
                                 lw=2.2, label=CTRL_LABELS[c])[0]
               for c in CONTROLLERS}
queue_ax.legend(loc='upper left', fontsize=7.5, framealpha=0.3,
                facecolor=DARK_BG, edgecolor='#2a3a55')

demand_ax.set_xlim(0, T); demand_ax.set_ylim(0, 1.55)
demand_ax.set_xlabel("Simulation step", color=TEXT_COL, fontsize=9)
demand_ax.set_ylabel("Demand λ/λ₀", color=TEXT_COL, fontsize=9)
demand_ax.set_title("Traffic Demand Wave", color="#90caf9", fontsize=10)
demand_ax.grid(alpha=0.2)
demand_curve = 0.80 + 0.55 * np.sin(np.pi * np.arange(T) / T)
demand_ax.fill_between(range(T), demand_curve, alpha=0.18, color="#ffca28")
demand_ax.plot(range(T), demand_curve, color="#ffca28", lw=1.5)
demand_vline, = demand_ax.plot([0,0], [0, 2.0], color='white', lw=1.0, alpha=0.6)
time_text = fig.text(0.5, 0.015,
    "t = 0 min  |  Step 0/120",
    ha='center', color='#90caf9', fontsize=10, family='monospace')

# ── per-grid artist containers ────────────────────────────────────────────
node_artists   = [{} for _ in CONTROLLERS]   # i → (glow_patch, core_patch)
link_artists   = [{} for _ in CONTROLLERS]   # (i,j) → line
phase_texts    = [{} for _ in CONTROLLERS]
co2_subtexts   = [None]*3
queue_data     = {c: [] for c in CONTROLLERS}

NODE_BASE = 0.18   # base radius
NODE_SCALE = 0.014  # extra radius per vehicle in queue

for k, (ax, ctrl) in enumerate(zip(grid_axes, CONTROLLERS)):
    # links
    for (i, j, axis) in edges_list:
        xi, yi = pos[i]; xj, yj = pos[j]
        ln, = ax.plot([xi,xj],[yi,yj], color=LINK_OFF, lw=1.5, zorder=1)
        link_artists[k][(min(i,j),max(i,j))] = ln

    for i in range(N):
        x0, y0 = pos[i]
        glow = plt.Circle((x0,y0), NODE_BASE*1.9, color=NS_ON, alpha=0.0, zorder=2)
        core = plt.Circle((x0,y0), NODE_BASE,     color=NS_ON, alpha=0.95, zorder=3)
        ax.add_patch(glow); ax.add_patch(core)
        txt = ax.text(x0, y0, f"{i+1}", ha='center', va='center',
                      fontsize=7.5, color='#000', fontweight='bold', zorder=4)
        node_artists[k][i] = (glow, core, txt)

    # CO2 subtext inside panel
    co2_subtexts[k] = ax.text(
        (L-1)/2, -0.55, "CO₂: 0 kg", ha='center', va='center',
        fontsize=9, color=CTRL_COLORS[ctrl], fontweight='bold')


def update(frame):
    t = frame
    mins = t * DT / 60.0

    for k, ctrl in enumerate(CONTROLLERS):
        h = histories[ctrl]
        if t >= T: t_use = T - 1
        else: t_use = t

        q_n = h['q_ns'][t_use]
        q_e = h['q_ew'][t_use]
        x   = h['x'][t_use]
        sync = h['sync_links'][t_use]

        # update links
        for (i, j, axis) in edges_list:
            key = (min(i,j), max(i,j))
            col = LINK_SYNC if key in sync else LINK_OFF
            lw  = 2.8 if key in sync else 1.2
            link_artists[k][key].set_color(col)
            link_artists[k][key].set_linewidth(lw)

        # update nodes
        for i in range(N):
            glow, core, txt = node_artists[k][i]
            q_total = float(q_n[i] + q_e[i])
            phase_color = NS_ON if x[i] == 1 else EW_ON
            r_core = NODE_BASE + NODE_SCALE * min(q_total, 30.0)
            r_glow = r_core * 1.7

            core.set_radius(r_core); core.set_color(phase_color)
            glow.set_radius(r_glow); glow.set_color(phase_color)
            glow.set_alpha(0.22 + 0.012 * min(q_total, 20.0))

            label = "↑↓" if x[i] == 1 else "←→"
            txt.set_text(f"{label}\n{int(q_total)}")
            txt.set_fontsize(6.5 if q_total > 25 else 7)

        # CO2 subtext
        co2_val = h['co2'][t_use]
        co2_subtexts[k].set_text(f"CO₂: {co2_val:.0f} kg")

        # CO2 bar
        co2_bars[k].set_height(co2_val)

        # queue line
        total_q = float(np.sum(np.array(h['q_ns'][t_use]) + np.array(h['q_ew'][t_use])))
        queue_data[ctrl].append(total_q)
        queue_lines[ctrl].set_data(range(len(queue_data[ctrl])), queue_data[ctrl])

    # demand vline
    demand_vline.set_xdata([t, t])
    time_text.set_text(
        f"t = {mins:.1f} min  |  Step {t+1}/{T}  "
        f"|  Rush peak at t = 15.0 min"
    )
    return []


ani = animation.FuncAnimation(
    fig, update, frames=T,
    interval=120, blit=False, repeat=False
)

print("Saving animation as GIF (this may take 1–2 minutes)…")
ani.save(
    os.path.join(FIG_DIR, "traffic_animation.gif"),
    writer=animation.PillowWriter(fps=8),
    dpi=90
)
print(f"Saved: {FIG_DIR}\\traffic_animation.gif")
plt.close(fig)
