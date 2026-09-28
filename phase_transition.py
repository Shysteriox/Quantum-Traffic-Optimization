"""
phase_transition.py
===================
Novel experiment: maps the CONGESTION PHASE TRANSITION for each traffic controller.

Real traffic networks undergo a physics-like phase transition:
  - Below critical demand λ* → "free flow" regime: queues are bounded and stable
  - Above λ* → "congested" regime: queues grow without bound (gridlock)

This script finds λ* for each controller by sweeping demand λ/λ₀ from 0.4 → 2.2
and computing the mean final-step queue. The critical threshold is where the
queue diverges sharply — analogous to a second-order phase transition.

NOVEL CONTRIBUTION: No prior study has published this bifurcation diagram for
quantum annealing vs. classical traffic controllers. The QUBO controller should
push λ* to a higher value, meaning it can sustain free flow under heavier demand.

Output:
  figures/fig05_phase_diagram.png   — 2D heatmap: improvement vs (grid size, demand)
  figures/fig06_bifurcation.png     — bifurcation diagram showing critical λ* per controller
  figures/fig07_greenwave_coherence.png — green-wave spatial coherence length vs demand
"""

import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d

sys.path.insert(0, r"C:\QuantumTrafficOptimization")
from simulate_qubo_traffic import (
    build_grid_adjacency, construct_qubo_matrix,
    solve_qubo_simulated_quantum_annealing, solve_qubo_exact
)

OUTPUT_DIR = r"C:\QuantumTrafficOptimization"
FIG_DIR = os.path.join(OUTPUT_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif", "font.size": 11,
    "axes.labelsize": 12, "axes.titlesize": 13,
    "figure.dpi": 300, "xtick.labelsize": 10, "ytick.labelsize": 10,
})

COLORS = {
    "Fixed-Time":  "#d95f02",
    "Local-Greedy":"#7570b3",
    "QA-QUBO":     "#1b9e77",
}
MARKERS = {"Fixed-Time": "o", "Local-Greedy": "s", "QA-QUBO": "^"}


# ────────────────────────────────────────────────────────────────────────────
# CORE FAST SIMULATION (T=80 steps = 20 min, returns final-10-step avg queue)
# ────────────────────────────────────────────────────────────────────────────
def fast_sim(L, demand_mult, controller, seed):
    N = L * L
    T = 80
    rng = np.random.default_rng(seed)
    edges, neighbors = build_grid_adjacency(L)

    q_ns = rng.uniform(2.0, 5.0, size=N)
    q_ew = rng.uniform(2.0, 5.0, size=N)
    platoon_ns = np.zeros(N)
    platoon_ew = np.zeros(N)
    x_prev = np.array([(r+c)%2 for r in range(L) for c in range(L)], dtype=int)

    sat = 10.0; sw_loss = 0.25
    final_qs = []
    sync_counts = []  # for green-wave coherence

    for t in range(T):
        rf = 0.80 + 0.55 * np.sin(np.pi * t / T)
        base = 2.15 * demand_mult * rf
        nsw = 1.0 + 0.35 * np.sin(2.0 * np.pi * t / 16.0)
        eww = 1.0 - 0.35 * np.sin(2.0 * np.pi * t / 16.0)

        for r in range(L):
            for c in range(L):
                i = r*L + c
                q_ns[i] += rng.poisson(base * (1.25 if c in (1,2) else 0.85) * nsw)
                q_ew[i] += rng.poisson(base * (1.25 if r in (1,2) else 0.85) * eww)

        eff_ns = q_ns + 1.45 * platoon_ns
        eff_ew = q_ew + 1.45 * platoon_ew

        if controller == "Fixed-Time":
            ph = (t // 2) % 2
            x = np.array([(ph+r+c)%2 for r in range(L) for c in range(L)], dtype=int)
        elif controller == "Local-Greedy":
            x = (q_ns >= q_ew).astype(int)
        else:
            Q = construct_qubo_matrix(eff_ns, eff_ew, x_prev, edges, w_sync=0.55, w_switch=1.8)
            x, _ = solve_qubo_simulated_quantum_annealing(Q, rng, num_reads=20, num_sweeps=18)

        switched = (x != x_prev).astype(float)

        # count synchronized links
        n_sync = sum(
            1 for (i,j,ax) in edges
            if (ax=="NS" and x[i]==1 and x[j]==1) or (ax=="EW" and x[i]==0 and x[j]==0)
        )
        n_links = len(edges)

        stop_pl = 0.0
        npl_ns = np.zeros(N); npl_ew = np.zeros(N)

        for i in range(N):
            if x[i] == 1:
                q_ns[i] += 0.35*platoon_ns[i]; q_ew[i] += platoon_ew[i]
                stop_pl += platoon_ew[i]
            else:
                q_ew[i] += 0.35*platoon_ew[i]; q_ns[i] += platoon_ns[i]
                stop_pl += platoon_ns[i]

        for i in range(N):
            cap = sat * (1.0 - sw_loss * switched[i])
            snb = [nb for nb,ax in neighbors[i]
                   if (ax=="NS" and x[i]==1 and x[nb]==1) or
                      (ax=="EW" and x[i]==0 and x[nb]==0)]
            if snb: cap *= 1.0 + 0.10*len(snb)
            if x[i]==1:
                dep = min(q_ns[i], cap); q_ns[i] -= dep
                for nb in [nb for nb,ax in neighbors[i] if ax=="NS"]:
                    npl_ns[nb] += 0.32*dep
            else:
                dep = min(q_ew[i], cap); q_ew[i] -= dep
                for nb in [nb for nb,ax in neighbors[i] if ax=="EW"]:
                    npl_ew[nb] += 0.32*dep

        platoon_ns = npl_ns; platoon_ew = npl_ew
        x_prev = x.copy()

        if t >= T - 15:
            final_qs.append(float(np.mean(q_ns + q_ew)))
            sync_counts.append(n_sync / max(n_links, 1))

    return np.mean(final_qs), np.mean(sync_counts)


# ════════════════════════════════════════════════════════════════════════════
# EXPERIMENT A: BIFURCATION DIAGRAM  (4×4 grid, sweep demand 0.40 → 2.20)
# ════════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("EXPERIMENT A: Phase Transition / Bifurcation Diagram")
print("=" * 60)

DEMANDS_A = np.linspace(0.40, 2.20, 22)
N_TRIALS_A = 15
CONTROLLERS = ["Fixed-Time", "Local-Greedy", "QA-QUBO"]

bif_mean = {c: [] for c in CONTROLLERS}
bif_std  = {c: [] for c in CONTROLLERS}
bif_sync = {c: [] for c in CONTROLLERS}

for d_idx, dm in enumerate(DEMANDS_A):
    print(f"  Demand {dm:.2f}  ({d_idx+1}/{len(DEMANDS_A)})", flush=True)
    for ctrl in CONTROLLERS:
        vals = []; syncs = []
        for trial in range(N_TRIALS_A):
            q, s = fast_sim(4, dm, ctrl, seed=3000 + d_idx*100 + trial)
            vals.append(q); syncs.append(s)
        bif_mean[ctrl].append(np.mean(vals))
        bif_std[ctrl].append(np.std(vals))
        bif_sync[ctrl].append(np.mean(syncs))

# ── estimate critical λ* via max second-derivative (inflection point) ──────
def find_critical_lambda(demands, means):
    """Critical demand = inflection point of the queue-vs-demand curve."""
    sm = gaussian_filter1d(means, sigma=1.5)
    d2 = np.gradient(np.gradient(sm, demands), demands)
    idx = int(np.argmax(d2))
    return demands[idx]

critical = {c: find_critical_lambda(DEMANDS_A, bif_mean[c]) for c in CONTROLLERS}
print("\n  Critical demand thresholds (lambda*):")
for c, lam in critical.items():
    print(f"    {c:20s}: lam* = {lam:.2f} x lam0")

# ── FIGURE 6: Bifurcation Diagram ─────────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.0, 4.8))

for ctrl in CONTROLLERS:
    mn = np.array(bif_mean[ctrl])
    sd = np.array(bif_std[ctrl])
    sm = gaussian_filter1d(mn, sigma=1.2)
    ax1.plot(DEMANDS_A, sm, marker=MARKERS[ctrl], color=COLORS[ctrl],
             lw=2.2, markersize=5, label=ctrl)
    ax1.fill_between(DEMANDS_A, sm-sd, sm+sd, alpha=0.15, color=COLORS[ctrl])
    ax1.axvline(critical[ctrl], color=COLORS[ctrl], lw=1.2, ls='--', alpha=0.7)

ax1.set_xlabel("Traffic Demand Multiplier (λ/λ₀)")
ax1.set_ylabel("Mean Residual Queue per Intersection\n(last 225 s of simulation)")
ax1.set_title("Network Congestion Phase Transition\n(4×4 grid, n=15 trials)")
ax1.grid(True, ls='--', alpha=0.4)
ax1.set_xlim(DEMANDS_A[0], DEMANDS_A[-1])

# Phase annotation: shade free-flow and congested regions
y_top = ax1.get_ylim()[1]
ax1.axvspan(DEMANDS_A[0], critical["QA-QUBO"],   alpha=0.05, color='#1b9e77')
ax1.axvspan(critical["QA-QUBO"], DEMANDS_A[-1], alpha=0.05, color='#d95f02')
ax1.text(0.20, 0.93, "FREE FLOW", transform=ax1.transAxes,
         ha='center', fontsize=9, color='#1b9e77', alpha=0.85)
ax1.text(0.93, 0.93, "CONGESTED", transform=ax1.transAxes,
         ha='center', fontsize=9, color='#d95f02', alpha=0.85)

# Critical-threshold values: one clean stacked legend box (upper-left, clear of all
# data curves and the phase-transition zone) instead of rotated inline labels that
# used to collide with the curves and with each other.
lam_lines = "\n".join(f"λ*({c}) = {critical[c]:.2f}" for c in CONTROLLERS)
ax1.text(0.02, 0.80, lam_lines, transform=ax1.transAxes, ha='left', va='top',
         fontsize=8.5, linespacing=1.6,
         bbox=dict(boxstyle='round,pad=0.4', facecolor='white', edgecolor='gray', alpha=0.9))

# QUBO advantage: how much higher is λ*_QUBO vs Fixed-Time? -- placed low and to the
# right, well clear of both the λ* box and the curves/legend above it.
delta_lam = critical["QA-QUBO"] - critical["Fixed-Time"]
ax1.annotate(
    f"QUBO raises λ* by +{delta_lam:.2f}×λ₀ vs Fixed-Time",
    xy=(critical["QA-QUBO"], y_top*0.06),
    xytext=(0.98, 0.18), textcoords='axes fraction',
    ha='right', va='bottom',
    arrowprops=dict(arrowstyle="->", color="#1b9e77", lw=1.5),
    fontsize=9, color="#1b9e77"
)

ax1.legend(fontsize=9, loc='center left', bbox_to_anchor=(0.02, 0.55))

# Right panel: Green-wave synchronization vs demand
for ctrl in CONTROLLERS:
    sm_sync = gaussian_filter1d(bif_sync[ctrl], sigma=1.2)
    ax2.plot(DEMANDS_A, 100*sm_sync, marker=MARKERS[ctrl], color=COLORS[ctrl],
             lw=2.2, markersize=5, label=ctrl)

ax2.set_xlabel("Traffic Demand Multiplier (λ/λ₀)")
ax2.set_ylabel("Green-Wave Synchronization Rate (%)\n(fraction of links with coordinated phase)")
ax2.set_title("Corridor Synchronization vs. Congestion")
ax2.legend(fontsize=9.5)
ax2.grid(True, ls='--', alpha=0.4)
ax2.set_xlim(DEMANDS_A[0], DEMANDS_A[-1])
ax2.set_ylim(0, 100)

fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "fig06_bifurcation.png"), bbox_inches="tight")
plt.close(fig)
print("  Saved fig06_bifurcation.png")


# ════════════════════════════════════════════════════════════════════════════
# EXPERIMENT B: PHASE DIAGRAM  (vary grid size L × demand multiplier)
#   Color = % CO2 improvement of QA-QUBO over Fixed-Time
# ════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("EXPERIMENT B: 2D Phase Diagram  (Grid Size x Demand)")
print("=" * 60)

GRID_SIZES = [2, 3, 4, 5, 6]
DEMANDS_B  = [0.5, 0.7, 0.9, 1.1, 1.3, 1.5, 1.8, 2.1]
N_TRIALS_B = 10

# Co2 estimation: proportional to mean residual queue × dt × idle_rate × N × T
CO2_FACTOR = 15.0 * 2.79 / 1000.0  # kg per (vehicle × step)

pct_improve_qubo_vs_fixed = np.zeros((len(GRID_SIZES), len(DEMANDS_B)))
pct_improve_qubo_vs_local = np.zeros((len(GRID_SIZES), len(DEMANDS_B)))

for li, L_val in enumerate(GRID_SIZES):
    for di, dm in enumerate(DEMANDS_B):
        print(f"  L={L_val}, lambda={dm:.1f}", flush=True)
        vals = {"Fixed-Time": [], "Local-Greedy": [], "QA-QUBO": []}
        for ctrl in ["Fixed-Time", "Local-Greedy", "QA-QUBO"]:
            for trial in range(N_TRIALS_B):
                q, _ = fast_sim(L_val, dm, ctrl, seed=5000 + li*200 + di*10 + trial)
                vals[ctrl].append(q)

        m_fixed = np.mean(vals["Fixed-Time"])
        m_local = np.mean(vals["Local-Greedy"])
        m_qubo  = np.mean(vals["QA-QUBO"])

        pct_improve_qubo_vs_fixed[li, di] = (
            100.0 * (m_fixed - m_qubo) / max(m_fixed, 0.1)
        )
        pct_improve_qubo_vs_local[li, di] = (
            100.0 * (m_local - m_qubo) / max(m_local, 0.1)
        )

# ── FIGURE 5: 2D Phase Diagram ────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13.0, 4.8))

for ax, data, title, cmap in zip(
    axes,
    [pct_improve_qubo_vs_fixed, pct_improve_qubo_vs_local],
    ["QA-QUBO vs Fixed-Time\n(% Reduction in Residual Queue → CO₂ Proxy)",
     "QA-QUBO vs Local-Greedy\n(% Reduction in Residual Queue → CO₂ Proxy)"],
    ["RdYlGn", "PuOr"]
):
    vmin, vmax = data.min(), max(data.max(), 1.0)
    im = ax.imshow(data, aspect='auto', cmap=cmap,
                   vmin=vmin, vmax=vmax,
                   origin='lower')
    norm = plt.Normalize(vmin=vmin, vmax=vmax)
    cmap_obj = plt.get_cmap(cmap)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label("% Queue Reduction\n(positive = QUBO is better)", fontsize=9)
    ax.set_xticks(range(len(DEMANDS_B)))
    ax.set_xticklabels([f"{d:.1f}" for d in DEMANDS_B], fontsize=8)
    ax.set_yticks(range(len(GRID_SIZES)))
    ax.set_yticklabels([f"{L_val}×{L_val}\n(N={L_val**2})" for L_val in GRID_SIZES], fontsize=8)
    ax.set_xlabel("Traffic Demand Multiplier (λ/λ₀)", fontsize=10)
    ax.set_ylabel("Urban Grid Size (intersections)", fontsize=10)
    ax.set_title(title, fontsize=11)

    # annotate cells -- pick black/white text from the ACTUAL rendered cell
    # color's perceived luminance, not a guessed numeric threshold (a fixed
    # threshold tuned for one colormap/data-range silently breaks on another,
    # which is exactly what made several cells here unreadable before)
    for li in range(len(GRID_SIZES)):
        for di in range(len(DEMANDS_B)):
            val = data[li, di]
            r, g, b, _ = cmap_obj(norm(val))
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            ax.text(di, li, f"{val:.1f}%",
                    ha='center', va='center', fontsize=7.5,
                    color='black' if luminance > 0.55 else 'white',
                    fontweight='bold')

    # Mark the critical boundary: where QUBO improvement crosses 10%
    threshold_line_y = []
    for di in range(len(DEMANDS_B)):
        for li in range(len(GRID_SIZES)-1, -1, -1):
            if data[li, di] >= 10.0:
                threshold_line_y.append(li)
                break
        else:
            threshold_line_y.append(-0.5)

    ax.plot(range(len(DEMANDS_B)), threshold_line_y,
            'w--', lw=2.0, alpha=0.8, label=">10% improvement boundary")
    ax.legend(loc='upper left', fontsize=7.5, framealpha=0.5)

fig.suptitle(
    "Phase Diagram: Where Does Quantum Annealing Signal Control Outperform Classical Controllers?\n"
    "(n=10 trials per cell; color = % queue reduction by QA-QUBO)",
    fontsize=11, y=1.02
)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "fig05_phase_diagram.png"), bbox_inches="tight")
plt.close(fig)
print("  Saved fig05_phase_diagram.png")


# ════════════════════════════════════════════════════════════════════════════
# EXPERIMENT C: GREEN-WAVE SPATIAL COHERENCE LENGTH
#   For each controller × demand level, measure the average length of
#   consecutive intersections sharing the same green phase along a corridor.
#   Longer = more coordinated platoon flow.
# ════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("EXPERIMENT C: Green-Wave Coherence Length Analysis")
print("=" * 60)

def measure_coherence_length(x_history, L):
    """
    For each time step, find the longest consecutive run of same-phase
    intersections along any row or column corridor.
    Returns mean over all steps.
    """
    coherence_lens = []
    for x in x_history:
        X = np.array(x).reshape(L, L)
        max_run = 1
        # rows (EW corridors)
        for r in range(L):
            run = 1
            for c in range(1, L):
                if X[r, c] == X[r, c-1]:
                    run += 1; max_run = max(max_run, run)
                else:
                    run = 1
        # cols (NS corridors)
        for c in range(L):
            run = 1
            for r in range(1, L):
                if X[r, c] == X[r-1, c]:
                    run += 1; max_run = max(max_run, run)
                else:
                    run = 1
        coherence_lens.append(max_run)
    return np.mean(coherence_lens)


DEMANDS_C = np.linspace(0.4, 2.0, 17)
N_TRIALS_C = 12
coherence_results = {c: {"mean": [], "std": []} for c in CONTROLLERS}

for di, dm in enumerate(DEMANDS_C):
    print(f"  Coherence sweep: lambda={dm:.2f}", flush=True)
    for ctrl in CONTROLLERS:
        runs = []
        for trial in range(N_TRIALS_C):
            rng = np.random.default_rng(7000 + di*50 + trial)
            N_val = 16
            T_val = 80
            edges_c, neighbors_c = build_grid_adjacency(4)

            q_ns = rng.uniform(2.0, 5.0, size=N_val)
            q_ew = rng.uniform(2.0, 5.0, size=N_val)
            platoon_ns = np.zeros(N_val); platoon_ew = np.zeros(N_val)
            x_prev_c = np.array([(r+c)%2 for r in range(4) for c in range(4)], dtype=int)
            x_hist = []

            for t in range(T_val):
                rf = 0.80 + 0.55 * np.sin(np.pi * t / T_val)
                base = 2.15 * dm * rf
                nsw = 1.0 + 0.35 * np.sin(2.0 * np.pi * t / 16.0)
                eww = 1.0 - 0.35 * np.sin(2.0 * np.pi * t / 16.0)
                for r in range(4):
                    for c_i in range(4):
                        i = r*4 + c_i
                        q_ns[i] += rng.poisson(base*(1.25 if c_i in (1,2) else 0.85)*nsw)
                        q_ew[i] += rng.poisson(base*(1.25 if r in (1,2) else 0.85)*eww)

                eff_ns = q_ns + 1.45 * platoon_ns
                eff_ew = q_ew + 1.45 * platoon_ew

                if ctrl == "Fixed-Time":
                    ph = (t // 2) % 2
                    x = np.array([(ph+r+c_i)%2 for r in range(4) for c_i in range(4)], dtype=int)
                elif ctrl == "Local-Greedy":
                    x = (q_ns >= q_ew).astype(int)
                else:
                    Q = construct_qubo_matrix(eff_ns, eff_ew, x_prev_c, edges_c,
                                              w_sync=0.55, w_switch=1.8)
                    x, _ = solve_qubo_simulated_quantum_annealing(Q, rng, num_reads=20, num_sweeps=18)

                x_hist.append(x.copy())
                switched = (x != x_prev_c).astype(float)
                npl_ns = np.zeros(N_val); npl_ew = np.zeros(N_val)
                stop_pl = 0.0
                for i in range(N_val):
                    if x[i]==1:
                        q_ns[i]+=0.35*platoon_ns[i]; q_ew[i]+=platoon_ew[i]
                        stop_pl+=platoon_ew[i]
                    else:
                        q_ew[i]+=0.35*platoon_ew[i]; q_ns[i]+=platoon_ns[i]
                        stop_pl+=platoon_ns[i]
                for i in range(N_val):
                    cap = 10.0*(1.0-0.25*switched[i])
                    if x[i]==1:
                        dep=min(q_ns[i],cap); q_ns[i]-=dep
                        for nb,ax2 in neighbors_c[i]:
                            if ax2=="NS": npl_ns[nb]+=0.32*dep
                    else:
                        dep=min(q_ew[i],cap); q_ew[i]-=dep
                        for nb,ax2 in neighbors_c[i]:
                            if ax2=="EW": npl_ew[nb]+=0.32*dep
                platoon_ns=npl_ns; platoon_ew=npl_ew
                x_prev_c = x.copy()

            runs.append(measure_coherence_length(x_hist, 4))

        coherence_results[ctrl]["mean"].append(np.mean(runs))
        coherence_results[ctrl]["std"].append(np.std(runs))

# ── FIGURE 7: Coherence Length ─────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8.5, 4.8))

for ctrl in CONTROLLERS:
    mn = np.array(coherence_results[ctrl]["mean"])
    sd = np.array(coherence_results[ctrl]["std"])
    sm = gaussian_filter1d(mn, sigma=1.0)
    ax.plot(DEMANDS_C, sm, marker=MARKERS[ctrl], color=COLORS[ctrl],
            lw=2.2, markersize=6, label=ctrl)
    ax.fill_between(DEMANDS_C, sm-sd, sm+sd, alpha=0.15, color=COLORS[ctrl])

ax.set_xlabel("Traffic Demand Multiplier (λ/λ₀)")
ax.set_ylabel("Mean Maximum Green-Wave Coherence Length\n(consecutive intersections with same phase)")
ax.set_title("Green-Wave Coherence: How Many Consecutive Intersections Stay Synchronized?")
ax.legend(fontsize=10)
ax.grid(True, ls='--', alpha=0.4)
ax.set_xlim(DEMANDS_C[0], DEMANDS_C[-1])
ax.set_ylim(1, 5)
ax.axhline(4, color='grey', lw=0.8, ls=':', alpha=0.6)
ax.text(DEMANDS_C[0]+0.05, 4.08, "Full corridor (4 intersections)", ha='left', fontsize=8, color='grey')

# annotate max coherence at peak demand
for ctrl in CONTROLLERS:
    mn = coherence_results[ctrl]["mean"]
    ax.annotate(f"{mn[-1]:.1f}",
                xy=(DEMANDS_C[-1], mn[-1]),
                xytext=(DEMANDS_C[-1]-0.15, mn[-1]+0.1),
                color=COLORS[ctrl], fontsize=9, fontweight='bold')

fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "fig07_greenwave_coherence.png"), bbox_inches="tight")
plt.close(fig)
print("  Saved fig07_greenwave_coherence.png")

print("\n" + "="*60)
print("ALL EXPERIMENTS COMPLETE.")
print(f"Figures saved to: {FIG_DIR}")
print("="*60)
print(f"\n  Critical lam* (phase transition thresholds):")
for c in CONTROLLERS:
    print(f"    {c:20s}: {critical[c]:.2f} x lam0")
print(f"\n  QUBO advantage vs Fixed-Time: lam* raised by {critical['QA-QUBO']-critical['Fixed-Time']:+.2f} x lam0")
print(f"  QUBO advantage vs Local-Greedy: lam* raised by {critical['QA-QUBO']-critical['Local-Greedy']:+.2f} x lam0")
