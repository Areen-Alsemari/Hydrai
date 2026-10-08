# HYDRAI tool agent on the CGH2 data: report

Reference configuration, not a verified Saudi system. Nothing was committed; the LH2 system, its generators and its data were not touched; no dataset was regenerated.

## What was built

A tool-using orchestrator (`hydrai_twin/cgh2_agent/`), not one learned model. Tools in the registry (name, description, version, runtime cost class, input window, structured output with intervals, bilingual text; every call logged):

| tool | status |
|---|---|
| T1 data_integrity | built (despiking confirmed by the strain gauge; stale probe handling; flow gating by valve/compressor state) |
| T2 inventory_leak | built (E2 per-unit commissioning baseline, E3 bulk-temperature corrector, E4 Kalman [inventory, leak rate] + slope test + multi-window fast estimator, equivalent orifice, kg released) |
| T3 thermal_state | built |
| T4 pressure_behaviour | built (control-logic comparison, fast pressure-collapse trip, time to PAH/PAHH/relief) |
| T5 sensor_integrity | built (pressure/strain/temperature redundancy; drift estimator NOT evaluated, 0 drift episodes) |
| T6 structural | built (Group 2; strain-per-pressure stiffness against the unit's own baseline, excess fatigue) |
| T9 twin_verifier | built (hypothesis replay; leak-fit mode of rate and start time) |
| T10 forecast_consequence | built (refill-aware leak forecast, no-refill bound, time to limit) |
| T11 hold_test_planner | built (Group 2; E6) |
| T12 alarm_context | built |
| T13 procedures | built (rule table class x severity, Arabic and English, physical reason) |
| T7 gas_release, T8 novelty | NOT built (T8 tried: isolation forest on the tool features separates composites from single faults at AUC 0.58; T7 left out because the leak-to-hydrogen dispersion coupling is a placeholder) |
| E8 sensor-upgrade what-if | NOT done |

Orchestrator: MONITOR -> SUSPECT -> INVESTIGATE -> DECIDE -> AWAIT_APPROVAL -> FOLLOW_UP -> CLOSE, deterministic policy mode; tiers watch / alert / critical were defined before results (see the module docstring); fusion = a multiclass
meta-model on the tool outputs trained on dev only, healthy-calibrated thresholds, times a fixed likelihood table over tool verdicts; simulated operator approve/reject; every decision stores its trace. Fast triggers: a static alarm or a pressure collapse opens an investigation at once, with instantaneous (not 15-minute-smoothed) fusion probabilities, and follow-ups at +10, +30 min and then hourly. LLM mode (`llm.py`): demo only, temperature 0, number checker with template fallback; never used in a benchmark number.

Demo and interfaces: `scripts/cgh2_agent_replay.py` (JSON ticks with tags, raw pressure, compensated inventory, agent state, tiers, leak estimate with interval, kg released, forecast, bilingual text, trace; accelerated playback; HTML viewer with simulated operator approve/reject; sample outputs in `output/cgh2_agent_demo/` for `M01__leak-0.25mm`, `M01__leak-0.5mm`, `M01__rupture-50mm`), and `scripts/cgh2_agent_api.py` (function `AgentAPI` + small JSON API).

## Protocol and integrity

Dev = 6 modules, leave-one-module-out. Tool parameters are cross-fitted by module (a unit's tool parameters never use its own module; second-order note: the fusion model of a held-out module trains on other modules' rows whose tool parameters were fitted on data that includes the held-out module's HEALTHY episodes). Thresholds from healthy dev data only (out-of-fold for the fusion model). No labels, onset times or healthy-twin data are features; the first-observable time is a training label only; features use dashboard tags, quality flags, compressor/valve states, the clock and the fast layer; the existing static alarm state is an input only to the orchestrator (a fast trigger and hard evidence), not to the fusion model, and an ablation without it is reported. Causality of every tool is tested (`tests/test_cgh2_agent_causality.py`: the value at tick i on truncated data equals the value on the full episode), so the accelerated replay equals running tick by tick.

Dev decisions made on healthy dev data or on diagnosed bugs before freezing (each was a real defect, none was a search over detection scores): causal E2 offset; flow gating against a silent flat-line fault; noise inflation after large draws; removal of the fast-slope features and of the cumulative fatigue count from the fusion features (both drifted or spiked in healthy runs and pushed the healthy-calibrated thresholds up); strain-confirmed despiking after finding that the cleaned pressure froze during real fast falls. The configuration was frozen (`output/reports/cgh2_agent_freeze.json`, hashes of code, models and thresholds) before the unseen and OOD sets were touched; the final script refuses to run if the freeze is violated. Unseen and OOD were scored once.

## Results (details in the per-set reports)

- **Dev** (`cgh2_agent_dev.md`), **unseen** (`cgh2_agent_unseen.md`), **OOD low / high** (`cgh2_agent_ood_low.md`, `cgh2_agent_ood_high.md`), paired lead times (`cgh2_agent_lead_times_*.md`), ablations (`cgh2_agent_ablation.md`), claims (`cgh2_agent_claims.md`).
- Healthy false alarms per week at the alert tier: dev 0.66, unseen 1.03, OOD low 2.72, OOD high 1.90 (single learned model 0.46 / 2.23 / 1.70 / 0.69; static alarms 0). Healthy-calibrated thresholds do not transfer to other pressure classes.
- Headlines (see the claims file for the full supported / not supported list): the agent adds a diagnosis (80 % correct at the first alert on dev, 76 % on unseen), a leak-size estimate and isolation advice within the first half hour for large leaks and containment, and a lower kg released before detection for 0.1-1 mm leaks on dev; it is not earlier than the single learned model on most classes; open-set rejection, structural concern on unseen, forecast intervals and OOD false-alarm control are not supported.
- E-items: E1 (gap to the physical floor, checkpoint 1); E2 per-unit baseline (commissioning + first 2 days, causal); E3 corrector reduces the inventory-estimate error (robust spread 0.50 % -> 0.41 % of the class inventory when settled, 0.64 % -> 0.54 % when not); E4 Kalman + slope test; E5 tiers; E6 hold-test planner (built; its recommendation effect was not simulated); E7 stop: 0 subtle-drift episodes; E8 not done.

## Ablations (`cgh2_agent_ablation.md`, dev; contribution table inside)

The model-based tools T3-T6 carry most of the diagnostic value (without them: thermal 5/24 against 16/24 detected, structural 2/12 against 7/12, correct class 30 minutes after the first alert 64/117 against 110/124). T2 and T9 carry the small-leak gain
(0.1 mm: 2/6 without them against 4/6). T5 is what sees structural change; T6 adds nothing measurable beyond it. T10, T11, T12, T13 are content tools (forecast, hold test, alarm context, procedure): no detection or diagnosis effect. The static alarm state as a trigger halves the kg released
before detection for 0.1-1 mm leaks but makes the first decision less informed (class right at the first decision in 99/124 with it, 108/124 without; 109/124 either way 30 minutes later).

## Surprises and defects found

1. The T1 despiker froze the cleaned pressure during real fast falls (held against a stale median): fixed by letting the strain gauge confirm a real change. It was invisible in the aggregate dev numbers and showed only when the leak-size estimates of large leaks were inspected.
2. Historian back-interpolation: the dashboard series of a step after a long quiet period moves BEFORE the event (M04 rupture: 7 minutes of ramp). Same mechanism as the earlier out-of-range artifact. A regeneration with a causal archiver would fix it; decision with the owner.
3. Silent flat-line faults on flow meters corrupt the mass balance (up to ~50 kg/h) unless gated by valve/compressor state; a flat-lined gas-temperature probe breaks the compensated stop and the inventory unless detected.
4. Healthy refuelling episodes cause inventory-estimate errors of about the drawn mass for roughly an hour; every leak estimator must widen its noise after large operations.
5. A cumulative feature (fatigue count) works as an episode-age clock and raised the healthy-calibrated thresholds; cumulative quantities do not belong in the fusion features.
6. The shared LH2 `fit_threshold` degenerates for statistics that are always above threshold (it returns 0.0 for ROC-pressure and EWMA); not modified (LH2 untouched); CGH2 uses `fit_threshold_bounded`.
7. `tests/test_cgh2_gas_registry.py::test_usage_is_recorded_...` fails in full-suite order (it passes alone and with the agent tests); it pre-dates this work.

## Runtime

Features and tool monitors: about 1.7 s per 14-day unit (about 1 minute for a 33-unit module on 6 workers); fusion models: 17-23 minutes for the 6 folds with nested out-of-fold thresholds (2.4 minutes for the final model on all dev); orchestrator on dev: about 10 minutes for 188 units; mean 5 tool calls and 133 ms of tool time per investigated event (the twin leak fit about 1-2 s when called).

## Open decisions for the owner (nothing here blocks anything delivered)

Low-pressure alarm (70 % MOP would false-alarm 1.7/week in the healthy twin); strain range +/-1000 vs +/-5000 ue; gas-temperature range 100 vs 150 C; regenerate with a causal historian archiver (fixes the back-interpolation artifact); per-class recalibration of thresholds for non-medium classes; whether to add subtle-drift sensor episodes to the dataset (needed to evaluate the T5 drift estimator); LH2 regeneration at the new 0.30 %/day default (not done).
