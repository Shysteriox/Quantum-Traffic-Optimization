"""Makes the two paper figures from sim_10seeds/results.csv.

Figure 1: 2030 delay by network and controller (a) and % less delay than Fixed-Time (b).
Figure 2: % less delay than Fixed-Time in the same year, 2025-2030 (adoption ramp), one panel per network.

Run from the repo root:  python make_figures.py   (needs matplotlib and numpy)
Output: figures_paper/Figure1_main_comparison_2030.png, Figure2_adoption_by_year.png (300 dpi PNG)

Percent method: for each trial, 100 * (Fixed - X) / Fixed using delay in
vehicle-seconds; then the mean over trials with a 95% t-interval. Positive = less delay than Fixed-Time.
"""
import csv, math, statistics as st
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
SIM = HERE / "sim_10seeds"
OUT = HERE / "figures_paper"
OUT.mkdir(exist_ok=True)

CITIES = ["Fremont", "Delhi", "Los Angeles", "Singapore", "Oslo"]
# The fifth network is the synthetic 5x5 fallback grid (the OpenStreetMap download for Singapore failed), so it is
# labelled Grid-25, never Singapore. "Singapore" is only the key used in results.csv.
LABELS = ["Fremont", "Delhi", "Los Angeles", "Grid-25\n(synthetic)", "Oslo"]
SHORT = ["Fremont", "Delhi", "Los Angeles", "Grid-25 (synthetic)", "Oslo"]
CTRL = ["Fixed-Time", "Local-Greedy", "SA-QUBO"]
# first three slots of the validated categorical palette (all-pairs CVD and normal-vision checks pass)
COLOR = {"Fixed-Time": "#2a78d6", "Local-Greedy": "#eb6834", "SA-QUBO": "#1baf7a"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#dcdcd8"
ADOPT = {2025: "0%", 2026: "0%", 2027: "20%", 2028: "50%", 2029: "80%", 2030: "100%"}

rows = list(csv.DictReader(open(SIM / "results.csv")))
NT = len({r["trial"] for r in rows})
T975 = {2: 4.302652729911275, 9: 2.2621571627409915}[NT - 1]
g = defaultdict(list)
for r in rows:
    g[(r["city"], int(r["year"]), r["controller"])].append(r)


def delay(city, year, ctrl):
    """delay in vehicle-hours per run, one value per trial (sorted by trial)."""
    return np.array([float(r["delay_vehicle_seconds"]) / 3600 for r in sorted(g[(city, year, ctrl)], key=lambda r: int(r["trial"]))])


def less_than_fixed(city, year, ctrl):
    f, x = delay(city, year, "Fixed-Time"), delay(city, year, ctrl)
    return 100 * (f - x) / f


def mean_ci(a):
    a = np.asarray(a, dtype=float)
    return a.mean(), T975 * a.std(ddof=1) / math.sqrt(len(a))


plt.rcParams.update({
    "font.family": ["Arial", "Liberation Sans", "DejaVu Sans"], "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8.5,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6, "savefig.dpi": 300, "figure.dpi": 100,
    "axes.facecolor": "white", "figure.facecolor": "white", "legend.frameon": False,
})


def style(ax):
    ax.grid(axis="y", color=GRID, lw=0.5)
    ax.set_axisbelow(True)


# ------------------------------------------------------------------ Figure 1
fig, axs = plt.subplots(1, 2, figsize=(7.0, 3.1), gridspec_kw={"width_ratios": [1.05, 1]}, layout="constrained")

ax = axs[0]
w = 0.26
for k, c in enumerate(CTRL):
    stats = [mean_ci(delay(city, 2030, c)) for city in CITIES]
    ax.bar(np.arange(5) + (k - 1) * w, [s[0] for s in stats], w * 0.92, yerr=[s[1] for s in stats],
           color=COLOR[c], label=c, error_kw=dict(lw=0.7, capsize=1.5, capthick=0.7, ecolor=INK2), zorder=3)
ax.set_xticks(range(5), LABELS, fontsize=7)
ax.set_ylabel("Delay per 12-hour run (vehicle-hours)")
ax.set_title("(a) Delay, 2030", loc="left", fontweight="bold")
ax.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.47, 1.0), handlelength=1.2)
style(ax)

ax = axs[1]
w = 0.34
for k, c in enumerate(["Local-Greedy", "SA-QUBO"]):
    stats = [mean_ci(less_than_fixed(city, 2030, c)) for city in CITIES]
    ax.bar(np.arange(5) + (k - 0.5) * w, [s[0] for s in stats], w * 0.92, yerr=[s[1] for s in stats],
           color=COLOR[c], label=c, error_kw=dict(lw=0.7, capsize=1.5, capthick=0.7, ecolor=INK2), zorder=3)
ax.axhline(0, color=INK2, lw=0.7, zorder=4)
ax.set_xticks(range(5), LABELS, fontsize=7)
ax.set_ylabel("Delay vs. Fixed-Time (% less delay)")
ax.set_title("(b) Change vs. Fixed-Time, 2030", loc="left", fontweight="bold")
ax.legend(fontsize=7.5, loc="upper right", handlelength=1.2)
style(ax)
fig.savefig(OUT / "Figure1_main_comparison_2030.png")
plt.close(fig)

# ------------------------------------------------------------------ Figure 2
years = list(range(2025, 2031))
fig, axs = plt.subplots(2, 3, figsize=(7.0, 4.6), sharey=True, layout="constrained")
flat = axs.ravel()
for i, city in enumerate(CITIES):
    ax = flat[i]
    for c in ["Local-Greedy", "SA-QUBO"]:
        st_ = [mean_ci(less_than_fixed(city, y, c)) for y in years]
        m = np.array([s[0] for s in st_])
        h = np.array([s[1] for s in st_])
        ax.fill_between(years, m - h, m + h, color=COLOR[c], alpha=0.18, lw=0, zorder=2)
        ax.plot(years, m, color=COLOR[c], lw=1.6, marker="o", ms=3.2, mec="white", mew=0.6, zorder=3, label=c)
    ax.axhline(0, color=COLOR["Fixed-Time"], lw=1.4, zorder=3, label="Fixed-Time (reference)")
    ax.set_xticks(years, [f"{y}\n{ADOPT[y]}" for y in years], fontsize=6.5)
    ax.set_title(SHORT[i], loc="left", fontweight="bold")
    style(ax)
    if i % 3 == 0:
        ax.set_ylabel("Delay vs. Fixed-Time\n(% less delay)")
ax = flat[5]
ax.axis("off")
handles, labels = flat[0].get_legend_handles_labels()
ax.legend(handles, labels, loc="upper left", fontsize=7.5, handlelength=1.8)
ax.text(0.0, 0.40, f"Second line under each year =\nshare of intersections under\nSA-QUBO. Local-Greedy and\nFixed-Time run at 100% in\nevery year.\n\nBands: 95% interval of the\nmean over {NT} trials.",
        transform=ax.transAxes, fontsize=7, color=INK2, va="top")
fig.savefig(OUT / "Figure2_adoption_by_year.png")
plt.close(fig)

print("wrote", sorted(p.name for p in OUT.glob("*.png")), f"(n = {NT} trials, t = {T975:.3f})")
