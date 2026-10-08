# HYDRAI tool agent: ablations (dev, leave-one-module-out)

Each row removes a tool (or a group) from the agent. 'Investigation-only' removals change what the orchestrator may call and the evidence it uses; removals that also remove the tool's monitor features retrain the fusion model without them (tag shows which).

| variant | healthy false alarms / week (alert) | detected within 24 h (all classes 1-6 standard) | by class (k/n) 1 / 2 / 3 / 4 / 5 / 6 | correct class at first alert | calls per event |
|---|---|---|---|---|---|
| full | 0.66 | 91/128 | 10/12 / 14/24 / 23/36 / 20/24 / 18/20 / 6/12 | 99/124 | 5.0 |
| noT9 | 0.58 | 89/128 | 10/12 / 13/24 / 20/36 / 21/24 / 19/20 / 6/12 | 94/124 | 4.0 |
| noT10 | 0.66 | 91/128 | 10/12 / 14/24 / 23/36 / 20/24 / 18/20 / 6/12 | 99/124 | 4.6 |
| noT11 | 0.66 | 91/128 | 10/12 / 14/24 / 23/36 / 20/24 / 18/20 / 6/12 | 99/124 | 4.7 |
| noT12 | 0.66 | 91/128 | 10/12 / 14/24 / 23/36 / 20/24 / 18/20 / 6/12 | 103/124 | 4.0 |
| noT13 | 0.66 | 91/128 | 10/12 / 14/24 / 23/36 / 20/24 / 18/20 / 6/12 | 99/124 | 5.0 |
| nostatic | 0.66 | 92/128 | 11/12 / 14/24 / 23/36 / 20/24 / 18/20 / 6/12 | 108/124 | 5.0 |
| noInvestigation | 0.58 | 90/128 | 11/12 / 13/24 / 20/36 / 21/24 / 19/20 / 6/12 | 105/124 | 2.3 |
| s10 | 0.70 | 94/128 | 10/12 / 16/24 / 23/36 / 19/24 / 19/20 / 7/12 | 101/124 | 5.0 |
| noT2 | 0.44 | 89/128 | 10/12 / 15/24 / 19/36 / 21/24 / 19/20 / 5/12 | 93/117 | 2.8 |
| noT3 | 0.70 | 94/128 | 10/12 / 11/24 / 25/36 / 21/24 / 19/20 / 8/12 | 85/122 | 4.6 |
| noT4 | 0.77 | 90/128 | 10/12 / 15/24 / 20/36 / 20/24 / 20/20 / 5/12 | 90/124 | 4.9 |
| noT5 | 0.64 | 92/128 | 10/12 / 16/24 / 24/36 / 20/24 / 19/20 / 3/12 | 99/123 | 4.5 |
| noT6 | 0.65 | 92/128 | 10/12 / 14/24 / 22/36 / 21/24 / 19/20 / 6/12 | 97/124 | 4.9 |
| noModelTools | 0.98 | 81/128 | 10/12 / 5/24 / 26/36 / 19/24 / 19/20 / 2/12 | 50/117 | 4.7 |


## How to read this

Rows `full` and `no T9/T10/T11/T12/T13`, `nostatic`, `noInvestigation` use the main fusion model: only the orchestrator's investigation or inputs change. `nostatic` removes the static alarm state as a trigger and as hard evidence.
Rows `noT2 ... noModelTools` also retrain the fusion model WITHOUT that tool's features (stride-10 training for speed), so their reference is `s10` (all features, the same stride-10 training), not `full`. The fast pressure-collapse trip is a
separate fast-layer rule and stays in every variant. Removing T2 also removes T9/T10/T11 (they need its leak-rate estimate); `noModelTools` removes T3, T4, T5 and T6 together. T1 cannot be removed without losing the cleaned series every tool reads.
The single-run noise of these tables is of the order of a few episodes (n = 128 fault episodes, 6-24 per class): differences of 1-2 episodes are not evidence.

## Extra metrics (class 30 minutes after the first alert, time to correct diagnosis, kg released before detection)

| variant | class correct 30 min after the first alert | median time to correct diagnosis h (n) | median kg released before detection, 0.1-1 mm leaks (n) | detected within 24 h, 0.1 mm leaks | alert false alarms / week |
|---|---|---|---|---|---|
| full | 109/124 | 3.1 (121) | 2.25 (23) | 4/6 | 0.66 |
| noT9 | 108/124 | 2.9 (117) | 2.52 (23) | 2/6 | 0.58 |
| noT10 | 109/124 | 3.1 (121) | 2.25 (23) | 4/6 | 0.66 |
| noT11 | 109/124 | 3.1 (121) | 2.25 (23) | 4/6 | 0.66 |
| noT12 | 109/124 | 3.1 (121) | 2.77 (23) | 4/6 | 0.66 |
| noT13 | 109/124 | 3.1 (121) | 2.25 (23) | 4/6 | 0.66 |
| nostatic | 109/124 | 3.1 (121) | 5.20 (23) | 4/6 | 0.66 |
| noInvestigation | 108/124 | 2.9 (117) | 6.64 (23) | 2/6 | 0.58 |
| s10 | 110/124 | 2.5 (122) | 1.87 (23) | 4/6 | 0.70 |
| noT2 | 105/117 | 1.2 (112) | 2.73 (20) | 2/6 | 0.44 |
| noT3 | 96/122 | 1.3 (116) | 2.05 (22) | 6/6 | 0.70 |
| noT4 | 97/124 | 3.4 (120) | 2.52 (23) | 2/6 | 0.77 |
| noT5 | 110/123 | 2.1 (120) | 2.30 (22) | 4/6 | 0.64 |
| noT6 | 111/124 | 2.0 (122) | 2.25 (23) | 3/6 | 0.65 |
| noModelTools | 64/117 | 1.4 (96) | 1.80 (23) | 6/6 | 0.98 |


## Tool-contribution table (reference for the retrained variants: `s10`, 94/128 detected within 24 h, 110/124 correct class 30 min after the first alert)

| tool removed | what changes (dev) | verdict |
|---|---|---|
| T3 thermal_state | thermal detection 11/24 against 16/24; class correct 30 min after the first alert 96/122 against 110/124 | needed for thermal anomalies and for the class |
| T4 pressure_behaviour | class correct at +30 min 97/124 against 110/124; leaks 20/36 against 23/36; structural 5/12 against 7/12 | needed for the class; also helps leaks |
| T5 sensor_integrity | structural 3/12 against 7/12 (the pressure-strain redundancy is what sees stiffness change); nothing else moves | needed for structural |
| T6 structural | 6-7/12 structural either way; class at +30 min 111 against 110 | no measurable contribution beyond T5 |
| T2 inventory_leak (with T9, T10, T11) | leaks 19/36 against 23/36; 0.1 mm 2/6 against 4/6; fewer alerts overall (0.44 against 0.70 false alarms/week) | needed for small leaks |
| T3-T6 together | 81/128 against 94/128; thermal 5/24 against 16/24; structural 2/12 against 7/12; class at +30 min 64/117 against 110/124; false alarms 0.98 against 0.70 per week | the model-based tools are most of the diagnostic value |
| T9 twin_verifier (main model) | 0.1 mm 2/6 against 4/6; leaks 20/36 against 23/36; class at first alert 94/124 against 99/124 | helps small leaks; also sizes large ones (4b of the dev report) |
| investigation as a whole (T9-T13 off) | 0.1 mm 2/6 against 4/6; kg released before detection 6.6 against 2.3 | the evidence-based escalations matter for small leaks |
| static alarm state as input | kg released before detection (0.1-1 mm leaks) 5.2 against 2.3; class at the FIRST decision is better without it (108/124 against 99/124) because the first decision is taken at the instant the static alarm fires; 30 minutes later no difference (109/124) | trade-off: earlier alert, less informed first decision |
| T10, T11, T13, T12 | no measurable effect on detection or on class (T12 only changes the first-decision class: 103/124 against 99/124). They supply the forecast, the hold-test recommendation, the procedure text and the alarm context, which these metrics do not score | content tools: no detection claim |

Averages: 5.0 tool calls per investigated event for the full agent, 2.3 with no investigation tools. Tool runtimes are in the dev report (section 5).
