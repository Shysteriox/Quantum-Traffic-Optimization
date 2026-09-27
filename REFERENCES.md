# Verified real references for the paper rewrite

Every entry below was independently confirmed against the actual source
(CrossRef metadata, Semantic Scholar, arXiv, or TRID — not just a citation
string that "looks right"). This is the exact failure mode that got the
original draft's bibliography flagged: two of its five references had
correct-looking DOI/arXiv links that resolved to a completely different
paper than what was claimed. Do not add anything to this list without
opening the link yourself and checking title/authors/venue/year/subject all
actually match.

## Core quantum-annealing-for-traffic papers

1. F. Neukart, G. Compostella, C. Seidel, D. von Dollen, S. Yarkoni, B. Parney,
   "Traffic Flow Optimization Using a Quantum Annealer," *Frontiers in ICT*,
   vol. 4, p. 29, 2017. https://doi.org/10.3389/fict.2017.00029
2. H. Hussain, M. B. Javaid, F. S. Khan, A. Dalal, A. Khalique,
   "Optimal control of traffic signals using quantum annealing," *Quantum
   Information Processing*, vol. 19, no. 312, 2020.
   https://doi.org/10.1007/s11128-020-02815-1
3. D. Inoue, A. Okada, T. Matsumori, K. Aihara, H. Yoshida, "Traffic signal
   optimization on a square lattice with quantum annealing," *Scientific
   Reports*, vol. 11, 2021. https://doi.org/10.1038/s41598-021-82740-0
4. F. Glover, G. Kochenberger, Y. Du, "Quantum Bridge Analytics I: A Tutorial
   on Formulating and Using QUBO Models," *Annals of Operations Research*,
   2019. https://doi.org/10.1007/s10479-019-03171-9

## A. Max-pressure / adaptive signal control (grounds the Local-Greedy baseline)

5. P. Varaiya, "Max Pressure Control of a Network of Signalized
   Intersections," *Transportation Research Part C*, vol. 36, pp. 177-195,
   2013. https://doi.org/10.1016/j.trc.2013.08.014 — the classic max-pressure
   reference; Local-Greedy in this project is a simplified relative of this
   family, not a strawman.
6. X. Sun, Y. Yin, "A Simulation Study on Max Pressure Control of Signalized
   Intersections," *Transportation Research Record*, vol. 2672, no. 18,
   pp. 117-127, 2018. https://doi.org/10.1177/0361198118786840 — supports that
   a simple queue-based controller can be simulation-competitive with more
   complex schemes (relevant to our Greedy-sometimes-beats-QUBO finding).
7. M. Papageorgiou, C. Diakaki, V. Dinopoulou, A. Kotsialos, Y. Wang, "Review
   of Road Traffic Control Strategies," *Proceedings of the IEEE*, vol. 91,
   no. 12, pp. 2043-2067, 2003. https://doi.org/10.1109/JPROC.2003.819610 —
   standard survey of adaptive signal control (SCOOT/SCATS/OPAC-type systems).

## B. Why "simulated annealing standing in for quantum annealing" is a legitimate, literature-recognized caveat, not just an excuse

8. T. F. Ronnow, Z. Wang, J. Job, S. Boixo, S. V. Isakov, D. Wecker, J. M.
   Martinis, D. A. Lidar, M. Troyer, "Defining and Detecting Quantum
   Speedup," *Science*, vol. 345, no. 6195, pp. 420-424, 2014.
   https://doi.org/10.1126/science.1252319 (arXiv: https://arxiv.org/abs/1401.2910) —
   benchmarked a 503-qubit D-Wave Two against classical simulated annealing;
   found no evidence of quantum speedup over the full instance set.
9. B. Heim, T. F. Ronnow, S. V. Isakov, M. Troyer, "Quantum versus Classical
   Annealing of Ising Spin Glasses," *Science*, vol. 348, no. 6231,
   pp. 215-217, 2015. https://doi.org/10.1126/science.aaa4170 (arXiv:
   https://arxiv.org/abs/1411.5693) — an apparent quantum-annealing advantage
   turned out to be a discretization artifact, not present in the continuous
   physical limit.
10. H. G. Katzgraber, F. Hamze, R. S. Andrist, "Glassy Chimeras Could Be Blind
    to Quantum Speedup: Designing Better Benchmarks for Quantum Annealing
    Machines," *Physical Review X*, vol. 4, art. 021008, 2014.
    https://doi.org/10.1103/PhysRevX.4.021008 (arXiv:
    https://arxiv.org/abs/1401.1546) — standard D-Wave benchmark problem
    classes can mask or fake evidence of quantum speedup.

## C. Traffic phase transitions / gridlock as a recognized physical phenomenon

11. K. Nagel, M. Schreckenberg, "A Cellular Automaton Model for Freeway
    Traffic," *Journal de Physique I*, vol. 2, pp. 2221-2229, 1992.
    https://doi.org/10.1051/jp1:1992277 — the foundational free-flow-to-jam
    cellular automaton model.
12. K. Nagel, M. Paczuski, "Emergent Traffic Jams," *Physical Review E*,
    vol. 51, no. 4, pp. 2909-2918, 1995. https://doi.org/10.1103/PhysRevE.51.2909
    (arXiv: adap-org/9502004) — explicit self-organized-criticality treatment
    of the free-flow/gridlock transition, with power-law jam lifetimes.
13. B. S. Kerner, P. Konhauser, "Structure and Parameters of Clusters in
    Traffic Flow," *Physical Review E*, vol. 50, pp. 54-83, 1994.
    https://doi.org/10.1103/PhysRevE.50.54 — nonlinear theory of spontaneous
    jam-cluster formation in initially homogeneous traffic.

## D. Green-wave / signal coordination

14. J. D. C. Little, "The Synchronization of Traffic Signals by Mixed-Integer
    Linear Programming," *Operations Research*, vol. 14, no. 4, pp. 568-594,
    1966. https://doi.org/10.1287/opre.14.4.568 — the foundational
    MAXBAND-lineage arterial green-wave optimization paper.
15. K. K. Talluri, C. Stang, G. Weidl, "Green Wave as an Integral Part for the
    Optimization of Traffic Efficiency and Safety: A Survey," arXiv:2507.22511,
    2025. https://arxiv.org/abs/2507.22511 — modern survey; cite only as
    general background, its abstract doesn't analyze corridor-size dependence
    specifically.

## E. Idling emissions methodology

16. L. Gaines, E. Rask, G. Keller, "Which Is Greener: Idle, or Stop and
    Restart? Comparing Fuel Use and Emissions for Short Passenger-Car Stops,"
    TRB 92nd Annual Meeting, Paper 13-4606, 2013.
    https://afdc.energy.gov/files/u/publication/which_is_greener.pdf
    (record: https://trid.trb.org/view/1242705) — Argonne National Laboratory
    experimental measurement of fuel/CO2/HC/CO/NOx for idling vs. restart;
    idling beyond ~10s is worse for fuel and CO2. More quantitative than the
    EPA Fast Facts one-pager already in use for the emission-factor claims.
