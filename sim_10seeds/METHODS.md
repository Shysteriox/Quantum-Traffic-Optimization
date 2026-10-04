# Methods and interpretation

## Experimental unit

One run models 12 hours on a road network retrieved within approximately 500 m of the supplied coordinate. Five coordinates and six scenario years follow the original request. Coordinates are used as supplied: they are not verified downtown centers. Current OSM geometry is reused across scenario years; it is not historical 2025 geometry.

There are 900 runs: five networks, six years, three controllers, ten random seeds. Synthetic demand grows 2% per year. The same representative season is held fixed across years so annual differences are not confounded by seasonal demand. The original request for seasonal variation in the animation is omitted: these are representative days, not a simulated full calendar. Demand has a Gaussian morning peak at reporting interval 10. Every controller receives the same arrivals in each city/year/trial. A fixed seed order selects nested adoption subsets: 0%, 0%, 20%, 50%, 80%, 100%, rounded to an integer node count. Fixed and greedy controllers run in every year as counterfactuals. QUBO is exactly fixed-time before deployment.

## Traffic model

The simulation advances at 30-second intervals and records 48 fifteen-minute snapshots. This replaces the original instruction's unrealistic fifteen-minute signal phases. Signals are reconsidered every 60 seconds; fixed-time alternates NS/EW each minute. Every graph node is treated as a hypothetical two-phase controller, including nodes that may not be actual signalized intersections. Traffic signal inventory, lane counts, turning movements, pedestrian phases and signal safety requirements are not modeled.

Independent Poisson arrivals enter every node/axis at an assumed base rate of 0.025 vehicles/second, multiplied by a seeded spatial factor, demand envelope, year growth. These rates are not observed traffic counts. Each green approach serves up to 0.45 vehicles/second; a signal change removes three seconds of service. Departing flow exits with probability mass 0.4; the remaining fractional flow splits evenly over directed outgoing links. It joins a downstream NS or EW queue based on that link's bearing, after travel time at an assumed 30 km/h, rounded up to a simulation step. Nodes without outgoing links discharge all served flow. Fractional flow is intentional: this is a fluid queue model, not an individual-vehicle microsimulation. Random splits, route choice, turn restrictions, storage limits, spillback and upstream blocking are absent. Departing phase does not restrict outgoing turns.

The instantaneous residual queue is integrated using end-step rectangles. Delay per injected vehicle includes delay accumulated by vehicles still in the network when the run ends; it is not completed-trip mean waiting time. Remaining vehicles and transit mass are recorded. Conservation is asserted in every run. No warm-up or terminal draining is performed, so finite-horizon and discretization effects remain.

## Corrected QUBO

Use x_i=1 for NS green, x_i=0 for EW green. Minimize:

E(x) = sum_i [eff_EW,i - eff_NS,i] x_i
     + 1.8 sum_i (x_i - previous_i)^2
     - 0.45 sum_NSlinks x_i x_j
     - 0.45 sum_EWlinks (1-x_i)(1-x_j).

Here eff is queue capped at 27 vehicles (one minute of nominal service). Store each pair once in an upper-triangular coefficient dictionary, merging duplicate physical direction pairs. Ignore self-loops. Constants may be omitted.

The switch diagonal is 1.8*(1-2*previous_i), correcting the prompt's coefficient. The EW-link expansion in the prompt was already correct. Partial deployment fixes non-adopted variables to the fixed-time phases and substitutes their contributions into adopted variables' linear coefficients. This retains interactions across the deployment boundary.

D-Wave's `neal` package uses classical simulated annealing: four reads, 40 sweeps, reproducible seeds. It is not simulated quantum annealing and uses no quantum hardware. There is no optimality guarantee. The synchronization reward is a heuristic for aligned greens; it does not explicitly optimize travel-time-offset green waves. A small exhaustive state check verifies the polynomial represents the stated objective, not that the solver always finds its minimum.

## Emissions and annualization

Idle vehicle-seconds / 900 is multiplied by the prompt's assumed factors: 0.038 kg CO2, 0.047 g NOx and 0.016 L fuel. These factors were not independently validated; fuel and CO2 factors were not reconciled through fuel carbon content. They are separate illustrative inputs, not a calibrated emissions inventory. Running exhaust, acceleration, electric fleet share and cold starts are excluded. CO2 and NOx reductions are necessarily identical percentages because both are linear functions of the same delay measure; they are not independent findings.

Annualization uses 250 twelve-hour workdays. The prompt requested 250 x 2, but each run already spans twelve hours; that would extrapolate to 24 hours/day. No scaling to a city's population or total road network is performed.

## Figures

A: all three controllers in 2030 under matched demand, with three-trial sample standard deviations. This replaces the confounded 2025-versus-2030 headline comparison. Original cross-year comparisons can be calculated from the raw data but combine controller and demand effects.

B: year-by-year idle emissions, normalized to each network's fixed 2025 baseline. Scenario year is not a forecast. No uncertainty band is supplied; the individual trials are in CSV/JSON.

C: prompt-supplied, unverified city-level TomTom percentages versus an assumed free-flow-normalized model delay proxy. The free-flow proxy is mean link travel time / exit fraction. The five-point regression R-squared is purely descriptive: source years, spatial coverage and metric definitions differ. No fitting to TomTom was performed, and this is not real-world validation. The source city values require verification before external use.

D: paired 2030 CO2 differences with sample SD, alongside an explicit statement that PM2.5 and health effects cannot be estimated here. The requested PM2.5 reduction bars are omitted because no emissions-to-concentration or exposure model was supplied. No fabricated health estimate substitutes for missing data.

Animation: 288 frames, 28.8 seconds, six representative days. Counters reset each scenario year. Road color represents the downstream queue, not measured road density. Pulse size reflects queued flow. The day/night background is decorative. This is an explanatory animation of the same saved model outputs, not a separate performance demonstration.

## Next research step

Obtain intersection-level arrival counts, turning ratios, real signal plans and measured delays for one corridor. Calibrate on one period and evaluate on a held-out period. Compare a tuned fixed controller, greedy controller and a standard adaptive baseline under matched demand. Increase seeds and examine demand, service-rate, time-step and QUBO-weight sensitivity. Benchmark solver quality/runtime under equal computational budgets before claiming any solver advantage. Actual quantum claims require a quantum method and direct classical comparators.

## Sources and provenance

- OSM contributors, road geometry: https://www.openstreetmap.org/copyright
- OSMnx API: https://osmnx.readthedocs.io/en/stable/user-reference.html
- Classical SA implementation: https://github.com/dwavesystems/dwave-neal
- Prompt-supplied comparison source (city values not verified): https://www.tomtom.com/traffic-index/

Original Downloads files were not changed. This implementation replaces the earlier prototype instead of reusing its existing figures as new evidence.

## Development correction

An initial diagnostic run used 0.065 vehicles/second per node/axis. Its nominal two-axis inflow divided by the 0.4 exit fraction exceeded effective per-node service capacity near peak demand, producing extreme queues. The final base input was reduced to 0.025 for an illustrative lower-load experiment (peak nominal aggregate load approximately 0.18 vehicles/second before growth versus roughly 0.43 total service/second). This was a model-load correction, not calibration to measured traffic. The final saved results all use the corrected input. Local topology can still create bottlenecks. An arbitrary annual season multiplier was also removed before the final run.
