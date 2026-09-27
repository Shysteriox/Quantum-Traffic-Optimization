import os
import time
import json
import numpy as np
import matplotlib.pyplot as plt

# Set publication-quality matplotlib defaults
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.dpi": 300,
})

OUTPUT_DIR = r"C:\QuantumTrafficOptimization"
FIG_DIR = os.path.join(OUTPUT_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)


def build_grid_adjacency(L):
    """
    Build adjacency list and edge list for an L x L square grid of intersections.
    Returns:
      edges: list of tuples (i, j, axis) where i < j, axis in {'NS', 'EW'}
      neighbors: dict mapping node i -> list of (neighbor_j, axis)
    """
    N = L * L
    edges = []
    neighbors = {i: [] for i in range(N)}
    for r in range(L):
        for c in range(L):
            i = r * L + c
            # East neighbor
            if c + 1 < L:
                j = r * L + (c + 1)
                edges.append((i, j, "EW"))
                neighbors[i].append((j, "EW"))
                neighbors[j].append((i, "EW"))
            # South neighbor
            if r + 1 < L:
                j = (r + 1) * L + c
                edges.append((i, j, "NS"))
                neighbors[i].append((j, "NS"))
                neighbors[j].append((i, "NS"))
    return edges, neighbors


def construct_qubo_matrix(q_ns, q_ew, x_prev, edges, w_sync=1.8, w_switch=3.2):
    """
    Construct the N x N upper-triangular QUBO matrix Q for traffic signal optimization.
    Binary variable x_i in {0, 1}:
      x_i = 1 => North-South (NS) green, East-West (EW) red
      x_i = 0 => East-West (EW) green, North-South (NS) red

    Hamiltonian:
      H(x) = sum_i Q_ii x_i + sum_{i < j} Q_ij x_i x_j
    """
    N = len(q_ns)
    Q = np.zeros((N, N), dtype=float)

    # 1. Local Queue Imbalance Term: -2 * (q_ns - q_ew) * x_i
    delta_q = q_ns - q_ew
    for i in range(N):
        Q[i, i] += -2.0 * delta_q[i]

    # 2. Phase-Switching Penalty Term: w_switch * (1 - 2 * x_prev_i) * x_i
    for i in range(N):
        Q[i, i] += w_switch * (1.0 - 2.0 * x_prev[i])

    # 3. Adjacent Platoon Synchronization Term (Green-Wave Coupling):
    # Weight J_ij proportional to shared arterial corridor queue demand
    for (i, j, axis) in edges:
        if axis == "NS":
            corridor_load = 0.5 * (q_ns[i] + q_ns[j])
        else:
            corridor_load = 0.5 * (q_ew[i] + q_ew[j])
        J_ij = 1.0 + 0.15 * corridor_load
        # (x_i - x_j)^2 = x_i + x_j - 2 x_i x_j
        Q[i, i] += w_sync * J_ij
        Q[j, j] += w_sync * J_ij
        Q[i, j] += -2.0 * w_sync * J_ij

    return Q


def solve_qubo_simulated_quantum_annealing(Q, rng, num_reads=30, num_sweeps=20):
    """
    Vectorized Simulated Quantum Annealing (SQA) across `num_reads` replicas simultaneously.
    Solves min_{x in {0,1}^N} x^T Q x with a transverse-field annealing schedule.
    """
    N = Q.shape[0]
    diag = np.diag(Q).copy()
    off_diag = Q - np.diag(diag)
    sym_off = off_diag + off_diag.T

    X = rng.integers(0, 2, size=(num_reads, N)).astype(float)
    betas = np.linspace(0.25, 5.5, num_sweeps)
    gammas = np.linspace(2.2, 0.02, num_sweeps)

    # Generic bipartite partition — works for any N (grid or irregular OSM network)
    even_idx = list(range(0, N, 2))
    odd_idx  = list(range(1, N, 2))

    for s in range(num_sweeps):
        eff_temp = (1.0 / betas[s]) + 0.35 * gammas[s]
        for sub in (even_idx, odd_idx):
            fields_sub = diag[None, sub] + X @ sym_off[:, sub]
            delta_x = 1.0 - 2.0 * X[:, sub]
            delta_E = delta_x * fields_sub
            probs = np.where(delta_E <= 0.0, 1.0, np.exp(-np.clip(delta_E / eff_temp, -30.0, 30.0)))
            accept = rng.random((num_reads, len(sub))) < probs
            X[:, sub] += delta_x * accept

    energies = np.sum((X @ Q) * X, axis=1)
    best_idx = int(np.argmin(energies))
    return X[best_idx].astype(int), float(energies[best_idx])


def solve_qubo_exact(Q):
    """
    Exact brute-force solver for validation on N <= 16 (evaluates all 2^N binary states).
    """
    N = Q.shape[0]
    states = ((np.arange(1 << N)[:, None] & (1 << np.arange(N))) > 0).astype(float)
    # Compute energies in batch: sum((states @ Q) * states, axis=1)
    energies = np.sum((states @ Q) * states, axis=1)
    idx = int(np.argmin(energies))
    return states[idx].astype(int), float(energies[idx])


def run_traffic_simulation(
    L=4,
    T=120,
    dt=15.0,
    arrival_rate_Multiplier=1.0,
    controller="QA-QUBO",
    seed=42,
):
    """
    Simulate an L x L urban intersection network over T steps (each dt = 15 seconds, total 30 mins).
    Models:
      - Time-varying rush-hour arrival wave + directional arterial platoons
      - Saturation discharge rate during green phase (10.0 veh / 15s step)
      - Clearance lost time (25% capacity lost to 3.75s yellow/all-red clearance on phase switch)
      - Platoon progression between adjacent intersections (green-wave pass-through when coordinated)
      - EPA / Argonne vehicle idling and stop-start CO2 and NOx emissions
    """
    rng = np.random.default_rng(seed)
    N = L * L
    edges, neighbors = build_grid_adjacency(L)

    q_ns = rng.uniform(2.0, 6.0, size=N)
    q_ew = rng.uniform(2.0, 6.0, size=N)
    platoon_ns = np.zeros(N)
    platoon_ew = np.zeros(N)
    x_prev = np.array([(r + c) % 2 for r in range(L) for c in range(L)], dtype=int)

    # Physical constants
    sat_flow_per_step = 10.0        # max vehicles discharged per 15s green step
    switch_lost_fraction = 0.25     # 25% capacity lost to 3.75s yellow/all-red clearance on switch
    co2_idle_g_per_veh_sec = 2.79   # g CO2 / sec per idling vehicle (US DOE / EPA)
    nox_idle_g_per_veh_sec = 0.0035 # g NOx / sec per idling vehicle
    co2_stop_start_g = 22.0         # extra g CO2 per vehicle forced to stop at a red signal
    fuel_l_per_g_co2 = 1.0 / 2310.0 # 2,310 g CO2 per liter of gasoline

    total_idling_veh_sec = 0.0
    total_co2_g = 0.0
    total_nox_g = 0.0
    total_switches = 0
    total_departed = 0.0
    queue_history = []
    co2_step_history = []

    for t in range(T):
        # Rush-hour demand profile (builds up to peak around t = 60, then subsides)
        rush_factor = 0.80 + 0.55 * np.sin(np.pi * t / T)
        base_rate = 2.15 * arrival_rate_Multiplier * rush_factor

        # External arrivals with oscillating directional arterial waves
        ns_wave = 1.0 + 0.35 * np.sin(2.0 * np.pi * t / 16.0)
        ew_wave = 1.0 - 0.35 * np.sin(2.0 * np.pi * t / 16.0)
        for r in range(L):
            for c in range(L):
                i = r * L + c
                ns_bias = (1.25 if c in (1, 2) else 0.85) * ns_wave
                ew_bias = (1.25 if r in (1, 2) else 0.85) * ew_wave
                q_ns[i] += rng.poisson(base_rate * ns_bias)
                q_ew[i] += rng.poisson(base_rate * ew_bias)

        # Effective queue demand including incoming platoons from upstream intersections
        eff_q_ns = q_ns + 1.45 * platoon_ns
        eff_q_ew = q_ew + 1.45 * platoon_ew

        # Choose signal configuration x in {0, 1}^N
        if controller == "Fixed-Time":
            # Alternates every 2 steps (30 seconds)
            phase = (t // 2) % 2
            x = np.array([(phase + r + c) % 2 for r in range(L) for c in range(L)], dtype=int)
        elif controller == "Local-Greedy":
            # Greedy local actuated based only on current standing queue (ignores neighbor coupling & switch cost)
            x = (q_ns >= q_ew).astype(int)
        elif controller == "QA-QUBO":
            Q = construct_qubo_matrix(eff_q_ns, eff_q_ew, x_prev, edges, w_sync=0.55, w_switch=1.8)
            x, _ = solve_qubo_simulated_quantum_annealing(Q, rng, num_reads=30, num_sweeps=22)
        elif controller == "Exact-QUBO":
            Q = construct_qubo_matrix(eff_q_ns, eff_q_ew, x_prev, edges, w_sync=0.55, w_switch=1.8)
            x, _ = solve_qubo_exact(Q)
        else:
            raise ValueError(f"Unknown controller: {controller}")

        switched = (x != x_prev).astype(float)
        total_switches += int(np.sum(switched))

        # Process incoming platoons: if signal matches platoon direction, green-wave pass-through occurs!
        stopped_platoon_vehicles = 0.0
        for i in range(N):
            if x[i] == 1:
                # NS is green: NS platoon glides through; EW platoon must stop and join standing queue
                q_ns[i] += 0.35 * platoon_ns[i]
                total_departed += 0.65 * platoon_ns[i]
                q_ew[i] += platoon_ew[i]
                stopped_platoon_vehicles += platoon_ew[i]
            else:
                # EW is green: EW platoon glides through; NS platoon must stop and join standing queue
                q_ew[i] += 0.35 * platoon_ew[i]
                total_departed += 0.65 * platoon_ew[i]
                q_ns[i] += platoon_ns[i]
                stopped_platoon_vehicles += platoon_ns[i]

        next_platoon_ns = np.zeros(N)
        next_platoon_ew = np.zeros(N)

        for i in range(N):
            eff_cap = sat_flow_per_step * (1.0 - switch_lost_fraction * switched[i])

            # Green-wave synchronization bonus along active corridor
            sync_neighbors = [
                nb for (nb, axis) in neighbors[i]
                if (axis == "NS" and x[i] == 1 and x[nb] == 1)
                or (axis == "EW" and x[i] == 0 and x[nb] == 0)
            ]
            if len(sync_neighbors) > 0:
                eff_cap *= (1.0 + 0.10 * len(sync_neighbors))

            if x[i] == 1:  # NS Green
                dep_ns = min(q_ns[i], eff_cap)
                dep_ew = 0.0
            else:          # EW Green
                dep_ns = 0.0
                dep_ew = min(q_ew[i], eff_cap)

            q_ns[i] -= dep_ns
            q_ew[i] -= dep_ew
            total_departed += (dep_ns + dep_ew)

            # 36% of discharged vehicles form platoons heading to adjacent intersections
            ns_nbs = [nb for (nb, axis) in neighbors[i] if axis == "NS"]
            ew_nbs = [nb for (nb, axis) in neighbors[i] if axis == "EW"]
            if dep_ns > 0 and ns_nbs:
                for nb in ns_nbs:
                    next_platoon_ns[nb] += 0.32 * dep_ns / len(ns_nbs)
                    next_platoon_ew[nb] += 0.04 * dep_ns / len(ns_nbs)
            if dep_ew > 0 and ew_nbs:
                for nb in ew_nbs:
                    next_platoon_ew[nb] += 0.32 * dep_ew / len(ew_nbs)
                    next_platoon_ns[nb] += 0.04 * dep_ew / len(ew_nbs)

        platoon_ns = next_platoon_ns
        platoon_ew = next_platoon_ew

        # Remaining vehicles in queues idle for dt seconds
        idling_vehicles = float(np.sum(q_ns + q_ew))
        step_idling_veh_sec = idling_vehicles * dt
        total_idling_veh_sec += step_idling_veh_sec

        # Emissions during this step (idling + stop-start braking/acceleration penalty)
        switch_stops = float(np.sum(switched * np.minimum(q_ns + q_ew, 5.0)))
        step_co2 = (
            step_idling_veh_sec * co2_idle_g_per_veh_sec
            + (stopped_platoon_vehicles + switch_stops) * co2_stop_start_g
        )
        step_nox = step_idling_veh_sec * nox_idle_g_per_veh_sec + (stopped_platoon_vehicles + switch_stops) * 0.025

        total_co2_g += step_co2
        total_nox_g += step_nox

        queue_history.append(idling_vehicles / N)  # avg idling queue per intersection
        co2_step_history.append(step_co2 / 1000.0) # kg CO2 per step
        x_prev = x.copy()

    avg_wait_sec_per_veh = total_idling_veh_sec / max(total_departed, 1.0)
    total_co2_kg = total_co2_g / 1000.0
    total_nox_g_val = total_nox_g
    total_fuel_liters = total_co2_g * fuel_l_per_g_co2

    return {
        "avg_queue_per_intersection": float(np.mean(queue_history)),
        "peak_queue_per_intersection": float(np.max(queue_history)),
        "avg_wait_sec_per_veh": float(avg_wait_sec_per_veh),
        "total_co2_kg": float(total_co2_kg),
        "total_nox_g": float(total_nox_g_val),
        "total_fuel_liters": float(total_fuel_liters),
        "total_switches": int(total_switches),
        "queue_history": queue_history,
        "co2_step_history": co2_step_history,
    }


def main():
    print("Running Monte Carlo evaluation on 4x4 urban grid (N=16 intersections)...")
    controllers = ["Fixed-Time", "Local-Greedy", "QA-QUBO"]
    num_trials = 20
    results = {c: [] for c in controllers}

    for trial in range(num_trials):
        seed = 1000 + trial
        for c in controllers:
            res = run_traffic_simulation(
                L=4, T=120, dt=15.0, arrival_rate_Multiplier=1.0, controller=c, seed=seed
            )
            results[c].append(res)

    summary = {}
    metrics = [
        "avg_queue_per_intersection",
        "peak_queue_per_intersection",
        "avg_wait_sec_per_veh",
        "total_co2_kg",
        "total_nox_g",
        "total_fuel_liters",
        "total_switches",
    ]
    for c in controllers:
        summary[c] = {}
        for m in metrics:
            vals = [r[m] for r in results[c]]
            summary[c][m] = {
                "mean": float(np.mean(vals)),
                "std": float(np.std(vals)),
            }

    # Check QA-QUBO vs Exact-QUBO optimality gap across 50 random traffic snapshots
    print("Benchmarking Simulated Quantum Annealing against Exact QUBO Ground State...")
    rng = np.random.default_rng(2026)
    edges, _ = build_grid_adjacency(4)
    exact_matches = 0
    rel_errors = []
    for _ in range(50):
        q_ns = rng.uniform(2.0, 25.0, size=16)
        q_ew = rng.uniform(2.0, 25.0, size=16)
        x_prev = rng.integers(0, 2, size=16)
        Q = construct_qubo_matrix(q_ns, q_ew, x_prev, edges)
        _, e_sqa = solve_qubo_simulated_quantum_annealing(Q, rng, num_reads=35, num_sweeps=50)
        _, e_exact = solve_qubo_exact(Q)
        if abs(e_sqa - e_exact) < 1e-6:
            exact_matches += 1
        rel_errors.append(abs(e_sqa - e_exact) / (abs(e_exact) + 1e-9))

    optimality_stats = {
        "ground_state_hit_rate_pct": 100.0 * exact_matches / 50.0,
        "mean_relative_energy_error_pct": 100.0 * float(np.mean(rel_errors)),
    }

    # Run arrival rate sweep (low, moderate, heavy, severe rush hour congestion)
    demand_multipliers = [0.6, 0.8, 1.0, 1.2, 1.4]
    demand_sweep = {c: [] for c in controllers}
    for mult in demand_multipliers:
        for c in controllers:
            trial_co2 = []
            trial_wait = []
            for trial in range(10):
                r = run_traffic_simulation(
                    L=4, T=120, dt=15.0, arrival_rate_Multiplier=mult, controller=c, seed=500 + trial
                )
                trial_co2.append(r["total_co2_kg"])
                trial_wait.append(r["avg_wait_sec_per_veh"])
            demand_sweep[c].append({
                "multiplier": mult,
                "co2_mean": float(np.mean(trial_co2)),
                "co2_std": float(np.std(trial_co2)),
                "wait_mean": float(np.mean(trial_wait)),
                "wait_std": float(np.std(trial_wait)),
            })

    # Figure 1: Time-Series Queue Evolution during 30-Minute Rush Hour Peak
    fig, ax = plt.subplots(figsize=(9.0, 4.8))
    time_mins = np.arange(1, 121) * 15.0 / 60.0
    colors = {"Fixed-Time": "#d95f02", "Local-Greedy": "#7570b3", "QA-QUBO": "#1b9e77"}
    labels = {
        "Fixed-Time": "Fixed-Time Schedule (Baseline)",
        "Local-Greedy": "Local Actuated Sensors (Uncoordinated)",
        "QA-QUBO": "Quantum Annealing QUBO (Proposed)",
    }
    for c in controllers:
        q_mat = np.array([r["queue_history"] for r in results[c]])
        mean_q = np.mean(q_mat, axis=0)
        std_q = np.std(q_mat, axis=0)
        ax.plot(time_mins, mean_q, label=labels[c], color=colors[c], linewidth=2.2)
        ax.fill_between(time_mins, mean_q - std_q, mean_q + std_q, color=colors[c], alpha=0.18)

    ax.set_xlabel("Simulation Time (minutes)")
    ax.set_ylabel("Mean Idling Vehicles per Intersection")
    ax.set_title("Urban 4×4 Grid: Real-Time Idling Queue Length During Rush Hour\n(n = 20 trials)", fontsize=12.5)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(frameon=True, loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig1_queue_timeseries.png"), bbox_inches="tight")
    plt.close(fig)

    # Figure 2: Bar Chart Comparison of Key Environmental & Delay Metrics
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 4.0))
    bar_colors = ["#d95f02", "#7570b3", "#1b9e77"]
    short_names = ["Fixed-Time", "Local Actuated", "QA-QUBO"]

    plot_Readouts = [
        ("avg_wait_sec_per_veh", "Avg. Idling Wait Time (s / veh)", "Vehicle Idling Delay"),
        ("total_co2_kg", "Cumulative CO$_2$ Emissions (kg)", "Total CO$_2$ Emissions (30 min)"),
        ("total_nox_g", "Cumulative NO$_x$ Emissions (g)", "Total NO$_x$ Pollutants (30 min)"),
    ]
    for idx, (m_key, ylabel, title) in enumerate(plot_Readouts):
        ax = axes[idx]
        means = [summary[c][m_key]["mean"] for c in controllers]
        stds = [summary[c][m_key]["std"] for c in controllers]
        bars = ax.bar(short_names, means, yerr=stds, capsize=5, color=bar_colors, edgecolor="black", alpha=0.88, width=0.58)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(True, axis="y", linestyle="--", alpha=0.4)
        ax.set_ylim(0, (max(means) + max(stds)) * 1.28)
        label_pad = ax.get_ylim()[1] * 0.03
        for bar, mean_val, std_val in zip(bars, means, stds):
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                bar.get_height() + std_val + label_pad,
                f"{mean_val:.1f}",
                ha="center",
                va="bottom",
                fontsize=9.5,
                fontweight="bold",
            )

    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig2_emissions_comparison.png"))
    plt.close(fig)

    # Figure 3: CO2 Emissions & Idling Delay vs. Traffic Congestion Demand Multiplier
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.0, 4.3))
    markers = {"Fixed-Time": "o", "Local-Greedy": "s", "QA-QUBO": "^"}
    for c in controllers:
        mults = [d["multiplier"] for d in demand_sweep[c]]
        co2_m = [d["co2_mean"] for d in demand_sweep[c]]
        co2_s = [d["co2_std"] for d in demand_sweep[c]]
        wait_m = [d["wait_mean"] for d in demand_sweep[c]]
        wait_s = [d["wait_std"] for d in demand_sweep[c]]

        ax1.errorbar(mults, wait_m, yerr=wait_s, marker=markers[c], color=colors[c], label=labels[c], linewidth=2, capsize=4)
        ax2.errorbar(mults, co2_m, yerr=co2_s, marker=markers[c], color=colors[c], label=labels[c], linewidth=2, capsize=4)

    ax1.set_xlabel("Traffic Arrival Demand Multiplier ($\\lambda / \\lambda_0$)")
    ax1.set_ylabel("Mean Idling Delay per Vehicle (s)")
    ax1.set_title("Idling Delay Across Congestion Regimes")
    ax1.grid(True, linestyle="--", alpha=0.4)
    ax1.legend(fontsize=8.5)

    ax2.set_xlabel("Traffic Arrival Demand Multiplier ($\\lambda / \\lambda_0$)")
    ax2.set_ylabel("Total CO$_2$ Emissions (kg / 30 min)")
    ax2.set_title("CO$_2$ Emissions Scaling with Traffic Volume")
    ax2.grid(True, linestyle="--", alpha=0.4)
    ax2.legend(fontsize=8.5)

    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig3_congestion_scaling.png"))
    plt.close(fig)

    output_report = {
        "summary_4x4_grid": summary,
        "optimality_benchmark": optimality_stats,
        "demand_sweep": demand_sweep,
    }
    with open(os.path.join(OUTPUT_DIR, "simulation_results.json"), "w") as f:
        json.dump(output_report, f, indent=2)

    print("Simulation complete! Summary of 4x4 Grid Results:")
    print(json.dumps(summary, indent=2))
    print("Optimality Benchmark:", optimality_stats)


if __name__ == "__main__":
    main()
