# Results from this run

10 paired trials per city/year/controller; 900 runs. Annual totals cover only each sampled network, using 250 twelve-hour days.

| City | Fixed CO2, 2030 (kg/run) | Greedy | SA-QUBO | SA reduction vs fixed |
|---|---:|---:|---:|---:|
| Fremont | 663.11 | 412.73 | 468.54 | 29.3% |
| Delhi | 252.42 | 202.43 | 239.99 | 4.9% |
| Los Angeles | 233.70 | 210.56 | 242.48 | -3.8% |
| Singapore (key; synthetic 5x5 grid, "Grid-25" in the paper) | 108.93 | 107.12 | 118.43 | -8.7% |
| Oslo | 784.68 | 548.98 | 634.17 | 19.2% |

These results measure controller behavior under assumed demand, not observed city traffic. The greedy controller is an essential comparator; a benefit over fixed timing alone is not a quantum benefit.

Exploratory reference scatter R²: nan. This is not a validation statistic for comparable measurements.