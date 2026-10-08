# HYDRAI Digital Twin

Simulation code and dataset generator for the HYDRAI liquid-hydrogen storage
digital twin. See `HYDRAI_Consolidated_Parameter_Workbook.md` and
`Predictive_Hydrogen_Storage_Safety_Project_Handoff.md` for the source
specs this implements against (every hardcoded constant in `hydrai_twin/`
cites which section it came from).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Regenerating the dataset

`output/dataset/*.jsonl` is generated, not checked in (300-800MB per file,
and fully reproducible from a fixed seed -- see `.gitignore`). To rebuild:

```bash
# Full dataset: 6 modules x ~35 scenario/severity/onset variants each,
# ~432K records, train/test split by held-out module (M06). Takes ~4 min.
python scripts/generate_dataset.py

# Quick smoke-test version (shorter episodes, fewer modules): ~6s.
python scripts/generate_dataset.py --modules M01 M02 --fast

# Also write the separate Sec.7 "target"-tier (0.05-0.10%/day) file,
# never merged into the baseline train/test set:
python scripts/generate_dataset.py --include-target-tier
```

Each module gets its own as-built profile (insulation quality, tank volume,
wall thickness, PCV setpoint, sensor calibration bias, site ambient, flows,
vacuum baseline -- see `hydrai_twin/module_profile.py`; ranges are
simulation assumptions, not workbook values). The profiles are recorded in
`manifest.json`. Output is byte-reproducible for a given seed.

Output: `dataset.jsonl` (everything), `train.jsonl` / `test.jsonl` (split
by held-out module, see `hydrai_twin/dataset.py:split_train_test`), and
`manifest.json` (per-episode metadata + label/variant counts -- this one
IS checked in, since it's small and lets you inspect what a run produced
without regenerating).

## Physical pressure model (in progress; the legacy generators remain the default)

`hydrai_twin/physical_episode.py` builds episodes on a physically-driven tank
(real hydrogen EOS; pressure follows heat leak, venting and valve action).
Scenarios are causes (insulation heat leak, vacuum ladder, stuck/blocked PCV,
leak, strain), not painted-on signatures. Every valve, regulator, vent and
vacuum value is a **placeholder** pending `ENGINEER_QUESTIONS_VALVE_VENT.md`
(see `hydrai_twin/placeholders.py`; sources and verification levels are in
`VALVE_VENT_SOURCE_VERIFICATION.md`; the cutover plan is in
`PHYSICAL_MODEL_CUTOVER_PROPOSAL.md`).

Two layers per episode: a **slow** 60 s Parquet snapshot of the whole timeline
(14-day storage episodes, fault onset drawn around days 3-5) and a **fast** 1 s
JSONL layer for operations and event bursts. Healthy and most fault episodes
run at the spec fill (85% nominal, 90% maximum); only fills above 90% appear, as an explicit, labeled
`overfill_hydraulic_lock` scenario. Stratification is off in the main data.

```bash
python scripts/generate_physical_sample.py             # 6 scenarios x 14 d -> output/physical/ (not in git)
python scripts/generate_physical_sample.py --stratified # robustness variant -> output/physical_stratified/
python scripts/generate_physical_sample.py --sample     # the small committed sample -> samples/physical/
python scripts/demo_physical_pressure.py                # model validation and fault timescales
```

`samples/physical/` (about 8 MB: normal, stuck-closed PCV, and an overfill
hydraulic lock; fast layer gzipped) is the only generated physical data in git.
Slow files are read with `pyarrow.parquet.read_table`.

### Multi-episode physical dataset (modules x variants, unseen units, reference dashboard)

The agent will sit on EXISTING dashboards; no real Saudi LH2 dashboard is publicly documented, so the dataset is seen
through the **reference configuration, not a verified Saudi system** (`dashboard_tags.json`; the minimal
`dashboard_tags.example.json` still loads).

```bash
python scripts/generate_physical_dataset.py                 # 279 episodes, a few minutes on 8 workers -> output/physical_dataset/ (not in git)
python scripts/generate_physical_dataset.py --fast          # smoke test: 5-day episodes, one variant per family
python scripts/generate_physical_dataset.py --stratified    # robustness variant only -> output/physical_dataset_stratified/
python scripts/generate_physical_dataset.py --dashboard my_tags.json     # the plant's real tag list / periods / alarm limits
python scripts/generate_physical_dataset.py --no-historian               # ideal instrument data (no filters, quality codes, faults)
python scripts/generate_physical_dataset.py --h2-mode spec --vacuum-mode spec --level-mode ideal   # workbook Sec. 9 instruments
python scripts/generate_physical_dataset.py --boiloff target             # 0.10 %/day (the handoff / Sec. 10 spec value) instead of the 0.30 %/day default
python scripts/generate_physical_dataset.py --valve-states               # expose pcv_state / prv_state as discrete inputs (default OFF)
python scripts/static_alarm_baseline.py                     # static alarms scored with the headline metrics (PROVISIONAL limits)
python scripts/alarm_load_report.py                         # alarms per hour in healthy runs vs EEMUA 191; agent target ~1/h
python scripts/h2_false_alarm_check.py                      # H2 detector false alarms over many units, both modes
python scripts/vacuum_visibility.py                         # soft-vacuum step visibility, both gauge modes
python scripts/timescale_tables.py                          # healthy drift and fault timescales, both boil-off tiers
python scripts/classical_baselines.py                       # ROC / EWMA / CUSUM next to the static alarms, fixed false-alarm budgets (PROVISIONAL)
python scripts/data_fault_rates.py                          # injected data-fault rates per channel-day, 60 s vs 1 s layer
python scripts/healthy_drift_visibility.py                  # slope-noise table behind PHYSICAL_MODEL_CUTOVER_PROPOSAL.md
python scripts/generate_physical_sample.py --sample         # the small committed sample -> samples/physical/
```

What a model sees. Per tag, a historian view at the tag's period: 1 s tags are read every second, 5 s and 10 s tags are held,
and channels faster than the 1 s grid (flows, strain, H2) are aggregated. Storage is recorded as 60 s snapshots of that 1 s-grid
view (14 d at 1 s would be about 340 M rows); operations and event bursts are 1 s. With the historian ON (default), values go through
an exception filter (0.1-0.5% of span, forced point 600 s), swinging-door compression (forced point 8 h), OPC quality codes
Good/Uncertain/Bad, and low-rate injected data faults (stale, flat-line, out-of-range, dropout), each **labelled** (`dfault__<tag>`,
`label__has_data_fault`) and never counted as a physical anomaly. `live__<tag>` holds the pre-historian value that static alarms act on.

Instruments (defaults are UNVERIFIED placeholders; Sec. 9 variants are switches): H2 as a 0-100 %LFL detector (+/-5 %LFL, T90
10-15 s; `--h2-mode spec` = Sec. 9 %vol), vacuum as a log-scale Pirani-class gauge (`--vacuum-mode spec` = 1% FS linear), level
as a DP gauge (biased by density; `--level-mode ideal`), valve states off.

Spec fill: healthy episodes fill to 85% nominal (never above the 90% maximum); only fills above 90% are the labeled
`overfill_hydraulic_lock` scenario. Healthy boil-off defaults to 0.30 %/day (`PHYSICAL_DEFAULT_BOILOFF_MODE = "baseline"`, workbook Sec. 7: real
10 m^3 tanks run 0.3-0.6 %/day); the handoff's 0.10 %/day is the `"target"` switch. Every manifest records the mode.

Roles: `dev` (M01-M06, scored by leave-one-module-out; folds in the manifest), `commissioning` (one healthy run per unit),
`unseen` (U01-U03: own profile and episode seeds; **one-shot**). The manifest carries, per episode, `onset_s` (true onset)
and `first_observable_s` / `first_observable_clear_s` (first deviation from a paired healthy twin, k=3 and k=10; `..._dashboard_s`
under the dashboard's channel mask), per-channel deviation times, first static-alarm times (marked PROVISIONAL), and historian
statistics (compression ratio, injected-fault counts). Labels: `ai_label` (flips at onset), `ai_label_observable`.

Sensor error: each Sec. 9 accuracy is split into a per-unit calibration bias (bounded by the spec), a slow drift and a smaller
random noise (`hydrai_twin/sensors.py`, `SensorErrorSplit`; the split is a placeholder, Q12). The legacy generators keep the old
all-white-noise model. `scripts/healthy_drift_visibility.py` regenerates the slope-noise table in `PHYSICAL_MODEL_CUTOVER_PROPOSAL.md`.

Models go through `hydrai_twin/channels.py` (`ChannelMask`, `load_slow_for_model`): dashboard tags and their OPC quality codes
only, never ground truth, labels, live values or fault labels. Headline metrics (`ml/headline_metrics.py`): lead time against the
first static alarm (with the outcome mix) and false alarms per week over healthy exposure; alarms starting inside a data fault are
counted separately. The static-alarm baseline is **PROVISIONAL**: its limits are the workbook's "simulation threshold" values.

## ML baselines (Model A anomaly detection, Model B fault diagnosis)

Features come from sensor measurements only (never ground truth, labels or
module profiles); see `ml/features.py`. Module-relative features normalize
each unit against its own healthy *commissioning run*
(`output/dataset/commissioning.jsonl`, separate from train/test) -- see
`ml/relative.py` for the no-leakage rules. Results are conditional on a
healthy commissioning run existing for each unit.

```bash
# Headline generalization number: leave-one-module-out over M01-M06,
# comparing absolute / relative / relative+multi-horizon features (~6 min)
python scripts/lomo_baselines.py

# Confusions, ambiguity-aware grouped metric, persistence, detection delay (~2.5 min)
python scripts/analyze_lomo.py

# ONE-SHOT evaluation on 3 never-seen units (needs output/dataset_final; refuses to re-run)
python scripts/final_eval.py
```

Generate the unseen units first with `DatasetConfig(modules=("X01","X02","X03"), base_seed=20270101)`
via `write_dataset(..., held_out_modules=(), write_split=False)` into `output/dataset_final`.
`scripts/train_baselines.py` is the original single-split (M06) run, kept for reference.

## Tests

```bash
python -m pytest tests/ -q
```

## Compressed gaseous hydrogen (CGH2) system (new; the LH2 twin above is the BACKUP system and is unchanged)

`hydrai_twin/cgh2/` is a second twin: steel vessels of compressed hydrogen refuelled by a compressor and drawn down by a dispenser.
Select it with the system switch (`hydrai_twin/systems.py`, `system="lh2"` default or `"cgh2"`); nothing in the LH2 path changes.
The dashboard is a **reference configuration, not a verified Saudi system** (`dashboard_tags_cgh2.json`). Every number carries a source
tag (V1 / V2 / V3 / U / CALC / JUDGE / REG-UNREAD) in `CGH2_REGISTRY.md`; anything U, JUDGE or REG-UNREAD is a placeholder. The decision
register file was not available when this was built: only the instruction and Addendum 1 were, so values from the register that neither
gives are JUDGE defaults, listed there.

Physics (1 s recording grid, 60 s snapshots): real-gas hydrogen (CoolProp "Hydrogen", normal hydrogen), a two-node gas/shell model with
the exact real-gas energy balance, ambient diurnal cycle (Dammam/Dhahran) and a solar offset (+10 K light vessel, +27 K dark-vessel stress),
compressor start 85 % / stop 100 % of MOP (temperature-compensated stop where a fixed stop provably alarms), refuelling or industrial
demand, PRV at MAWP (+/-3 %, 7 % blowdown), choked real-gas leaks and ruptures. Classes: low MOP 50, **medium MOP 300 (primary)**, high MOP 350 bar.

```bash
python scripts/cgh2_verify.py                          # steps 5a-d: reference numbers, healthy runs, leak detectability, timescales
python scripts/cgh2_generate.py                        # medium (main) + low and high (out-of-distribution) -> output/cgh2/{medium,low,high}/ (not in git)
python scripts/cgh2_generate.py --sample               # the small committed sample -> samples/cgh2/
python scripts/generate_physical_dataset.py --system cgh2    # same, through the LH2 script's system switch (default stays lh2)
python scripts/cgh2_baselines.py                       # static + ROC + EWMA + CUSUM + inventory residual, healthy-only thresholds, 1/wk and 1/4wk (PROVISIONAL)
python scripts/cgh2_alarm_load.py                      # static alarms per hour vs ISA-18.2 / EEMUA 191
python scripts/cgh2_h2_false_alarm.py                  # hydrogen-detector false alarms over 2,000 healthy units x 14 d, both detector modes
python scripts/cgh2_fault_rates.py                     # injected data-fault rates per channel-day, 60 s layer vs 1 s layer
python scripts/cgh2_registry_doc.py                    # regenerate CGH2_REGISTRY.md
```

Switches: `--h2-mode spec` (workbook Sec. 9 hydrogen model instead of the realistic %LFL detector), `--flow-mode spec` (1 % FS instead of the
datasheet 0.5 % of reading + 0.009 kg/min), `--no-valve-states` (ablation: compressor status and valve states hidden), `--no-historian`
(ideal instrument data), `--prv-blowdown conservative` (10 %). Faults (class ids as LH2, register names): 1 sensor_fault, 2 thermal_anomaly,
3 small_slow_leak (0.1-1 mm; 0.03-0.05 mm stress set labelled `expected_miss`), 4 abnormal_pressure_behaviour, 5 containment_anomaly (2-5 mm
leaks; rare ruptures, under 2 % of fault episodes), 6 structural_concern, -1 unknown_anomaly. Labels, paired healthy twin, historian and data-fault
labelling work exactly as for LH2 (`onset_s` vs `first_observable_s`).


## HYDRAI agent on the CGH2 data (tool-using orchestrator, not one learned model)

`hydrai_twin/cgh2_agent/` is an orchestrator that investigates suspicious behaviour by calling specialist tools (name, description, version, runtime cost, structured
output with intervals and bilingual text; every call is logged in a reasoning trace). Tools read only dashboard-visible tags, OPC quality flags, compressor/valve
states, the existing alarm state and the clock; the digital twin is used by the verifier tool only. **Reference configuration, not a verified Saudi system.**

| tool | what it does |
|---|---|
| T1 data_integrity | quality flags, causal despiking (a real step is confirmed by the strain gauge), stale probe handling, flow gating by valve/compressor state |
| T2 inventory_leak | temperature-compensated real-gas inventory, per-unit commissioning baseline, bulk-temperature correction, Kalman estimator [inventory, leak rate], slope test, fast multi-window estimator for large leaks |
| T3 thermal_state | expected gas/shell temperature from ambient, diurnal phase, fills and draws; overheating / cooling failure / external heating |
| T4 pressure_behaviour | pressure against the control logic: stop overrun, stuck valve, blocked relief, relief lift, pressure collapse; time to PAH / PAHH / relief set point |
| T5 sensor_integrity | pressure vs strain vs temperature redundancy; which gauge is lying |
| T6 structural | strain-per-pressure stiffness drift against the unit's own baseline; excess fatigue |
| T9 twin_verifier | replays the recent window through the twin under a hypothesis (leak, extra heat); also fits leak rate and start time |
| T10 forecast_consequence | kg released and time to limit if unchecked, with intervals |
| T11 hold_test_planner | recommends a hold test and its duration |
| T12 alarm_context | what the existing static alarms say |
| T13 procedures | rule table of actions per class and severity, Arabic and English, with the physical reason |

State machine MONITOR -> SUSPECT -> INVESTIGATE -> DECIDE -> AWAIT_APPROVAL -> FOLLOW_UP -> CLOSE; tiers watch / alert / critical; the benchmarked orchestrator is the
deterministic policy mode (`hydrai_twin/cgh2_agent/agent.py`). The LLM mode (`llm.py`, demo only, never in a benchmark) answers operator questions through the same
tools at temperature 0 and a checker rejects any number that is not in a tool output (fallback: the template text).

```bash
python scripts/cgh2_agent_features.py            # cross-fitted tool parameters + feature matrices (dev, leave-one-module-out)
python scripts/cgh2_agent_meta.py                # fusion models and healthy-calibrated thresholds
python scripts/cgh2_agent_run_dev.py --tag full  # orchestrator over every dev unit
python scripts/cgh2_agent_eval.py --runs full --out cgh2_agent_dev     # -> output/reports/cgh2_agent_dev.md
bash scripts/cgh2_agent_ablate.sh                # tool ablations
python scripts/cgh2_agent_replay.py --episode M01__leak-0.25mm         # JSON ticks + HTML viewer -> output/cgh2_agent_demo/
python scripts/cgh2_agent_replay.py --episode M01__leak-0.25mm --stream --speed 3600   # accelerated JSON stream on stdout
python scripts/cgh2_agent_api.py --port 8800     # small JSON API: /tools /episodes /assess /decisions, POST /approve
python scripts/cgh2_agent_freeze.py              # freeze the dev configuration (hashes), then the ONE-SHOT: scripts/cgh2_agent_final.py models|agent|baselines
```


### Agent vs the static alarms and a modelled operator; slow-drift episodes (added after the frozen evaluation)

```bash
python scripts/cgh2_drift_generate.py            # 12 slow sensor-drift episodes (+6 commissioning runs) -> output/cgh2_drift/medium/ (separate folder, never used for tuning)
python scripts/cgh2_drift_run.py                 # scores the FROZEN agent, static A/B, learned model ONCE (refuses to run twice) ; python scripts/cgh2_drift_report.py -> cgh2_agent_drift.md
python scripts/cgh2_agent_vs_static.py           # -> output/reports/cgh2_agent_vs_static.md (dev, unseen, OOD, recalibrated OOD, drift; per class and severity)
python scripts/cgh2_ood_recalibrate.py           # per-class recalibration of the OOD thresholds on healthy data of that class (cross-fitted), separate rows
python scripts/cgh2_agent_lead_times.py --set dev|unseen|low|high
```
The operator proxy (`hydrai_twin/cgh2_agent/operator_proxy.py`) is a modelled operator who looks at the raw dashboard every 15 / 60 minutes; it is not a human study.
