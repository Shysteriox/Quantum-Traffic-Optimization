import os
import numpy as np
import matplotlib.pyplot as plt
from simulate_qubo_traffic import build_grid_adjacency, construct_qubo_matrix, solve_qubo_exact

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 10.5,
    "axes.labelsize": 11.5,
    "axes.titlesize": 12.5,
    "figure.dpi": 300,
})

OUTPUT_DIR = r"C:\QuantumTrafficOptimization"
FIG_DIR = os.path.join(OUTPUT_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)


def main():
    L = 4
    N = L * L
    edges, _ = build_grid_adjacency(L)
    rng = np.random.default_rng(1042)

    # Generate a representative rush-hour traffic snapshot
    q_ns = rng.uniform(4.0, 22.0, size=N)
    q_ew = rng.uniform(4.0, 22.0, size=N)
    # Emphasize North-South arterial on columns 1,2 and East-West arterial on rows 1,2
    for r in range(L):
        for c in range(L):
            i = r * L + c
            if c in (1, 2):
                q_ns[i] += 6.5
            if r in (1, 2):
                q_ew[i] += 5.0

    x_prev = np.array([(r + c) % 2 for r in range(L) for c in range(L)], dtype=int)
    Q = construct_qubo_matrix(q_ns, q_ew, x_prev, edges, w_sync=0.55, w_switch=1.8)
    x_opt, e_opt = solve_qubo_exact(Q)

    fig, (ax_grid, ax_mat) = plt.subplots(1, 2, figsize=(11.0, 4.8))

    # Left Panel: 4x4 Urban Intersection Topology & Optimal Signal Assignment
    ax_grid.set_xlim(-0.5, L - 0.5)
    ax_grid.set_ylim(-0.5, L - 0.5)
    ax_grid.invert_yaxis()
    ax_grid.set_aspect("equal")

    # Draw road links with thickness proportional to coupling J_ij
    for (i, j, axis) in edges:
        r_i, c_i = divmod(i, L)
        r_j, c_j = divmod(j, L)
        coup = abs(Q[i, j])
        ax_grid.plot(
            [c_i, c_j],
            [r_i, r_j],
            color="#555555",
            linewidth=1.0 + 0.12 * coup,
            zorder=1,
        )

    # Draw intersections colored by optimal QUBO phase decision
    for i in range(N):
        r, c = divmod(i, L)
        is_ns = x_opt[i] == 1
        node_color = "#1b9e77" if is_ns else "#d95f02"
        phase_str = "NS" if is_ns else "EW"
        ax_grid.scatter(c, r, s=620, color=node_color, edgecolors="black", linewidth=1.5, zorder=3)
        ax_grid.text(
            c,
            r,
            f"$v_{{{i+1}}}$\n({phase_str})",
            ha="center",
            va="center",
            color="white",
            fontweight="bold",
            fontsize=8.5,
            zorder=4,
        )
        # Annotate queue differential Delta q_i
        dq = q_ns[i] - q_ew[i]
        ax_grid.text(
            c,
            r + 0.34,
            f"$\\Delta q={dq:+.1f}$",
            ha="center",
            va="top",
            fontsize=8.0,
            color="#222222",
            bbox=dict(boxstyle="round,pad=0.15", facecolor="#f8f8f8", edgecolor="none", alpha=0.85),
        )

    # Legend proxies
    ax_grid.scatter([], [], s=150, color="#1b9e77", edgecolors="black", label="$x_i = 1$ (N–S Green Phase)")
    ax_grid.scatter([], [], s=150, color="#d95f02", edgecolors="black", label="$x_i = 0$ (E–W Green Phase)")
    ax_grid.plot([], [], color="#555555", linewidth=3.0, label="Arterial Coupling ($Q_{ij} < 0$)")
    ax_grid.set_xticks(range(L))
    ax_grid.set_yticks(range(L))
    ax_grid.set_xticklabels([f"Ave {c+1}" for c in range(L)])
    ax_grid.set_yticklabels([f"St {r+1}" for r in range(L)])
    ax_grid.set_title("(a) 4×4 Urban Grid & QUBO Ground-State Phases")
    ax_grid.legend(loc="lower center", bbox_to_anchor=(0.5, -0.23), ncol=2, fontsize=8.5, frameon=True)
    ax_grid.grid(False)

    # Right Panel: 16x16 QUBO Matrix Q Heatmap
    im = ax_mat.imshow(Q, cmap="coolwarm", aspect="equal")
    cbar = fig.colorbar(im, ax=ax_mat, fraction=0.046, pad=0.04)
    cbar.set_label("QUBO Matrix Entry $Q_{ij}$")
    ticks = np.arange(0, N, 2)
    ax_mat.set_xticks(ticks)
    ax_mat.set_yticks(ticks)
    ax_mat.set_xticklabels([f"$x_{{{k+1}}}$" for k in ticks])
    ax_mat.set_yticklabels([f"$x_{{{k+1}}}$" for k in ticks])
    ax_mat.set_xlabel("Intersection Binary Variable $x_j$")
    ax_mat.set_ylabel("Intersection Binary Variable $x_i$")
    ax_mat.set_title("(b) Upper-Triangular 16×16 QUBO Matrix $Q$")

    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig4_qubo_architecture.png"), bbox_inches="tight")
    plt.close(fig)
    print("Saved fig4_qubo_architecture.png successfully.")


if __name__ == "__main__":
    main()
