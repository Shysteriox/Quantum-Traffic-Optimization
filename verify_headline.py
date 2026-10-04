"""Independent spot-check of the paper's headline numbers from sim_10seeds/results.csv.
Run from the repo root: python verify_headline.py
"""
import csv, collections, statistics as st

rows = list(csv.DictReader(open("sim_10seeds/results.csv")))
print("rows:", len(rows))
d = {}
for r in rows:
    d[(r["city"], int(r["year"]), r["controller"], int(r["trial"]))] = float(r["delay_vehicle_seconds"])
cities = sorted({k[0] for k in d})
T = 2.262  # t, df=9


def pct_less(city, year, ctrl, base):
    v = []
    for t in range(10):
        b = d[(city, year, base, t)]
        v.append(100 * (b - d[(city, year, ctrl, t)]) / b)
    m = st.mean(v)
    h = T * st.stdev(v) / 10 ** 0.5
    return m, m - h, m + h, sum(x > 0 for x in v)


print("\n2030 % less delay (mean, 95% lo, hi, wins/10)")
for c in cities:
    for ctrl in ("Local-Greedy", "SA-QUBO"):
        m, lo, hi, w = pct_less(c, 2030, ctrl, "Fixed-Time")
        print(f"{c:12s} {ctrl:12s} vs Fixed  {m:6.1f} ({lo:6.1f},{hi:6.1f}) {w}/10")
    g = sum(d[(c, 2030, "SA-QUBO", t)] > d[(c, 2030, "Local-Greedy", t)] for t in range(10))
    print(f"{c:12s} Greedy beats QUBO in {g}/10 trials")

print("\n2030 mean delay, vehicle-hours")
for c in cities:
    print(c, [round(st.mean(d[(c, 2030, k, t)] for t in range(10)) / 3600) for k in ("Fixed-Time", "Local-Greedy", "SA-QUBO")])

print("\nFremont SA-QUBO % less delay by year")
for y in range(2025, 2031):
    print(y, round(pct_less("Fremont", y, "SA-QUBO", "Fixed-Time")[0], 1))

print("\ntotal vehicles injected:", f"{sum(float(r['arrivals']) for r in rows):,.0f}")
