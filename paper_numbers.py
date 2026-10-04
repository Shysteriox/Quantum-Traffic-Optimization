"""Every number in the paper's results tables, computed from sim_10seeds/results.csv (900 runs).

Pure standard library. Run:  python paper_numbers.py
Convention: "% less delay than Fixed-Time", positive = better, mean of per-trial values.
The fifth network is stored in results.csv under the key "Singapore". It is the synthetic 5x5 fallback grid
(the OpenStreetMap download failed), so it is reported as "Grid-25 (synthetic)".
"""
import csv, itertools, math, statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
CITIES = ["Fremont", "Delhi", "Los Angeles", "Singapore", "Oslo"]
NAME = {"Singapore": "Grid-25 (synthetic)"}
CTRL = ["Fixed-Time", "Local-Greedy", "SA-QUBO"]
YEARS = list(range(2025, 2031))
T975 = 2.2621571627409915  # t, 9 degrees of freedom

rows = list(csv.DictReader(open(HERE / "sim_10seeds" / "results.csv")))
D, W, A = {}, {}, {}
for r in rows:
    k = (r["city"], int(r["year"]), r["controller"], int(r["trial"]))
    D[k] = float(r["delay_vehicle_seconds"])
    W[k] = float(r["wait_seconds_per_injected_vehicle"])
    A[k] = float(r["arrivals"])
N = len({k[3] for k in D})
assert len(rows) == 900 and N == 10


def delay_h(city, year, ctrl):
    return [D[(city, year, ctrl, t)] / 3600 for t in range(N)]


def less(city, year, ctrl, base="Fixed-Time"):
    """per-trial % less delay than base (positive = ctrl better)"""
    return [100 * (D[(city, year, base, t)] - D[(city, year, ctrl, t)]) / D[(city, year, base, t)] for t in range(N)]


def extra(city, year, ctrl="SA-QUBO", base="Local-Greedy"):
    """per-trial % more delay than base (positive = ctrl worse)"""
    return [100 * (D[(city, year, ctrl, t)] - D[(city, year, base, t)]) / D[(city, year, base, t)] for t in range(N)]


def mean_ci(v):
    m = st.mean(v)
    h = T975 * st.stdev(v) / math.sqrt(len(v))
    return m, m - h, m + h


def sign_p(v):
    """exact two-sided sign test"""
    pos, n = sum(x > 0 for x in v), sum(x != 0 for x in v)
    k = min(pos, n - pos)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def wilcoxon_p(v):
    """exact two-sided Wilcoxon signed-rank test (no zeros or ties expected with continuous delays)"""
    v = [x for x in v if x != 0]
    order = sorted(range(len(v)), key=lambda i: abs(v[i]))
    rank = {i: r + 1 for r, i in enumerate(order)}
    wplus = sum(rank[i] for i in range(len(v)) if v[i] > 0)
    total = len(v) * (len(v) + 1) / 2
    obs = abs(wplus - total / 2)
    hits = sum(abs(sum(r for r, s in zip(range(1, len(v) + 1), signs) if s) - total / 2) >= obs - 1e-12
               for signs in itertools.product([0, 1], repeat=len(v)))
    return hits / 2 ** len(v)


def table3():
    out = []
    for c in CITIES:
        ms = {k: (st.mean(delay_h(c, 2030, k)), st.stdev(delay_h(c, 2030, k)),
                  st.mean(W[(c, 2030, k, t)] for t in range(N))) for k in CTRL}
        out.append(dict(city=NAME.get(c, c), stats=ms, sa=mean_ci(less(c, 2030, "SA-QUBO")),
                        wins_greedy=sum(x > 0 for x in less(c, 2030, "Local-Greedy")),
                        wins_sa=sum(x > 0 for x in less(c, 2030, "SA-QUBO"))))
    return out


def table4():
    out = []
    for c in CITIES:
        sa = less(c, 2030, "SA-QUBO")
        out.append(dict(city=NAME.get(c, c), greedy=mean_ci(less(c, 2030, "Local-Greedy")), sa=mean_ci(sa),
                        extra=mean_ci(extra(c, 2030)), sign=sign_p(sa), wilcoxon=wilcoxon_p(sa),
                        greedy_beats_sa=sum(x > 0 for x in extra(c, 2030))))
    return out


def by_year(city, ctrl):
    return [st.mean(less(city, y, ctrl)) for y in YEARS]


def fixed_growth(city):
    """(Fixed-Time delay 2030 / 2025, vehicles injected 2030 / 2025), means over trials"""
    d = st.mean(delay_h(city, 2030, "Fixed-Time")) / st.mean(delay_h(city, 2025, "Fixed-Time"))
    a = st.mean(A[(city, 2030, "Fixed-Time", t)] for t in range(N)) / st.mean(A[(city, 2025, "Fixed-Time", t)] for t in range(N))
    return d, a


def unanimous_comparisons():
    """of the 15 paired 2030 comparisons (5 networks x 3 controller pairs), how many agree in all 10 trials"""
    n = 0
    for c in CITIES:
        for v in (less(c, 2030, "Local-Greedy"), less(c, 2030, "SA-QUBO"), extra(c, 2030)):
            n += sum(x > 0 for x in v) in (0, N)
    return n


if __name__ == "__main__":
    print(f"runs: {len(rows)}; vehicles injected over all runs: {sum(A.values()):,.0f}")
    print("\nTable 3 (2030, 100% adoption): delay veh-h mean +/- SD | delay per vehicle (s)")
    for r in table3():
        s = r["stats"]
        print(f"  {r['city']:20s}", " | ".join(f"{k}: {s[k][0]:,.0f} +/- {s[k][1]:.0f}, {s[k][2]:.1f} s" for k in CTRL),
              f"| less delay than Fixed-Time in {r['wins_greedy']}/10 (Local-Greedy), {r['wins_sa']}/10 (SA-QUBO)")
    print("\nTable 4 (2030): % less delay than Fixed-Time [95% CI]; SA-QUBO extra delay vs Local-Greedy; exact p (SA-QUBO vs Fixed-Time)")
    f = lambda t: f"{t[0]:+.1f} [{t[1]:+.1f}, {t[2]:+.1f}]"
    for r in table4():
        print(f"  {r['city']:20s} Local-Greedy {f(r['greedy'])} | SA-QUBO {f(r['sa'])} | extra {f(r['extra'])} | "
              f"sign p={r['sign']:.5f} Wilcoxon p={r['wilcoxon']:.5f} | Local-Greedy beats SA-QUBO in {r['greedy_beats_sa']}/10")
    print(f"\nLocal-Greedy beats SA-QUBO in {sum(r['greedy_beats_sa'] for r in table4())} of {5 * N} paired 2030 trials")
    print(f"comparisons unanimous across 10 trials: {unanimous_comparisons()} of 15")
    print("\n% less delay than Fixed-Time by year, 2025-2030 (SA-QUBO adoption 0, 0, 20, 50, 80, 100%)")
    for c in CITIES:
        print(f"  {NAME.get(c, c):20s} SA-QUBO", [round(x, 1) + 0.0 for x in by_year(c, "SA-QUBO")],
              " Local-Greedy", [round(x, 1) for x in by_year(c, "Local-Greedy")])
    print("\nFixed-Time delay growth 2025 -> 2030 vs demand growth")
    for c in CITIES:
        d, a = fixed_growth(c)
        print(f"  {NAME.get(c, c):20s} delay x{d:.2f}, vehicles x{a:.2f}")
