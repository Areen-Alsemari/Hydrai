# Physical pressure model — time-compression and cutover proposal

**Status: proposal only. Nothing here is implemented.** The physical model
(`hydrai_twin/ullage.py`, `valves.py`, `physical_tank.py`) exists and is tested,
but the legacy random-process generators, the dataset and the ML pipeline are
untouched and remain the default.

## 1. The problem, with numbers

The physical model puts events on three very different timescales. Valve parameters are placeholders (PCV opens at 1.5 bar(a), 0.069 bar
deadband; Q1 open). The healthy boil-off default is now **0.10 %/day** (handoff / workbook Sec. 10); workbook Sec. 7 recommends 0.30 %/day and it is
a one-line switch. Both tiers, computed by `scripts/timescale_tables.py` at the spec nominal fill (85%):

| Regime | What happens | 0.10 %/day (DEFAULT) | 0.30 %/day (Sec. 7) |
|---|---|---|---|
| Healthy wall flux | calibrated to the tier | 0.118 W/m² | 0.354 W/m² |
| Healthy storage | first PCV opening after a fill from 1.2 bar | 19.0 d | 6.3 d |
| | steady PCV cycle (1.429 to 1.500 bar) | **4.1 d** | 1.2 d |
| | healthy pressure drift between openings | **0.073 kPa/h** | 0.241 kPa/h |
| | vented in 60 d | 24.5 kg | 96.0 kg |
| PCV stuck closed (from 1.2 bar, healthy heat leak) | time to 1.5 / 2.0 / 3.0 bar | 19.0 / 46.7 / 93.0 d | 6.3 / 15.6 / 31.0 d |
| Insulation x1.5 / x2.5 / x6 / x10 | first PCV opening | 12.7 / 7.6 / 3.2 / 1.9 d | 4.2 / 2.5 / 1.1 / 0.6 d |
| Severe events | vacuum loss at about 33 kW: PRV lifts in 49 min, tank dry in 2.2 h; at about 190 kW: liquid-full and PRV lift in about 5 min, dry in about 25 min | (absolute fluxes: same in both tiers) | |

Consequence for the 14-day episodes with onset on days 3 to 5: at the default tier a stuck-closed PCV barely moves the pressure within the
episode (it needs 19 d to reach the top of the normal band), so pressure-only valve faults are weakly observable there; the 0.30 %/day tier
shows them within days. Longer episodes or the other tier are a decision for the data owner.

The current ML windows are 2 min (short) and 10 min (long) at 1 s sampling. Slope noise of the pressure channel
against the healthy drift, measured by Monte Carlo (`scripts/healthy_drift_visibility.py`). The first table is the ORIGINAL one, kept for
comparison: it assumed the whole accuracy was white noise and the 0.30 %/day drift of 0.22 kPa/h.

**Original table (whole Sec. 9 accuracy as white noise, sigma = 7.5 mbar per sample):**

| Window | Slope noise | Healthy drift in sigma |
|---|---|---|
| 2 min @ 1 s | 7.1 kPa/h | 0.03 |
| 10 min @ 1 s | 0.64 kPa/h | 0.35 |
| 2 h @ 60 s | 0.12 kPa/h | 1.9 |
| 6 h @ 60 s | 0.023 kPa/h | 9.6 |
| 24 h @ 60 s | 0.003 kPa/h | 77 |

**Corrected table (accuracy split into per-unit bias + slow drift + small noise; split values are placeholders, Q12)** — 4,000-trial Monte
Carlo, `scripts/healthy_drift_visibility.py` (output in `output/reports/healthy_drift_visibility.txt`). White noise sigma 1.5 mbar (0.1 x accuracy),
drift 2-sigma 4.5 mbar (0.3 x accuracy, tau 3 d), bias up to 7.5 mbar (does not affect a slope). Healthy drift is re-stated for BOTH boil-off
tiers (default 0.073 kPa/h; the table above used 0.22 kPa/h, which belonged to a 0.30 %/day tank):

| Window | Slope noise | Drift in sigma, 0.10 %/day (default) | Drift in sigma, 0.30 %/day | of which white-only noise |
|---|---|---|---|---|
| 2 min @ 1 s | 1.43 kPa/h | 0.05 | 0.17 | 1.42 |
| 10 min @ 1 s | 0.16 kPa/h | 0.45 | 1.5 | 0.13 |
| 30 min @ 60 s | 0.20 kPa/h | 0.37 | 1.2 | 0.19 |
| 1 h @ 60 s | 0.079 kPa/h | 0.92 | 3.0 | 0.067 |
| 2 h @ 60 s | 0.036 kPa/h | 2.0 | 6.6 | 0.024 |
| 6 h @ 60 s | 0.016 kPa/h | 4.4 | 14.6 | 0.0046 |
| 24 h @ 60 s | 0.0073 kPa/h | 9.9 | 32.8 | 0.00057 |

What changes: (1) short windows get **more** visible than the old table said, because the random noise is 5x smaller, but at the default tier the drift is a
third as large, so the 3-sigma crossing is about 2 to 3 h (about 1 h at 0.30 %/day). (2) Long windows are drift-limited: from about 2 h the sensor-drift
term is comparable to the white term, and it dominates from 6 h. (3) The 2 min and 10 min 1 s windows of the current ML pipeline still cannot see healthy
thermal drift at either tier (0.05 and 0.45 sigma at the default), so the two-layer conclusion stands and is stronger at 0.10 %/day: the slow layer needs windows
of several hours. (4) Historian effects are not in this table: a 0.1% FS exception deadband (6 mbar) already exceeds the 1.5 mbar white noise and
quantises slow slopes, so slope features on the historian copy are coarser than shown. The drift share and time constant are assumptions.

## 2. Options

| | Option | Data volume (210 episodes, as now) | What it means for ML features | Main risk |
|---|---|---|---|---|
| A | Keep 1 s sampling, run multi-day episodes | 7 d @ 1 s → 127 M rows, ≈226 GB JSONL | Existing features still blind to drift (table above) | Infeasible; solves nothing |
| B | **Multi-rate sampling**: 60 s for storage episodes; 1 s only for operations and event bursts | 7 d @ 60 s → 2.1 M rows, ≈3.8 GB JSONL (14 d: 7.5 GB) | Windows of 2–24 h; slope/trend features in kPa/h; "time since last PCV opening", cycle period, vent-mass per day; pressure noise is no longer the limit at ≥6 h | Two feature regimes to maintain; label/onset timing becomes hours |
| C | Event-triggered / adaptive rows (record on Δp or Δt cap) | Smallest | Irregular timestamps; must resample to a grid before windowing | Easy to leak event timing into features; harder tests |
| D | **Time compression**: scale heat flux or valve dynamics up so a fault plays out in minutes | Same as today | Existing pipeline unchanged | Distorts the physics: a "fast" insulation fault is indistinguishable from a real vacuum failure by flux, sensor noise stays fixed, and the model learns dynamics that do not exist in service. Fine for a smoke test, not for results |
| E | **Two-layer detector** (builds on B) | As B | Fast layer: existing short-window pipeline for severe events and sensor faults. Slow layer: trend/vent-cycle features over hours–days for drifts and valve faults | Needs per-layer evaluation; handoff Sec. 19 early-warning metrics (lead time) become the primary ones |

## 3. Recommendation

**E on top of B**, in this order, each step reviewable on its own:

1. **Freeze and review the physical core.** Placeholders are in the registry
   (`hydrai_twin/placeholders.py`), and the manifest records the ones used.
   Engineer answers (Q1–Q9) replace them as they arrive; no re-architecture is
   needed to swap a value.
2. **Add a `PhysicalEpisodeGenerator`** that reuses the existing sensor, schema,
   module-profile and strain code, with three modes: operations (minutes, 1 s),
   storage (days, 60 s) and event burst (1 s around PRV lifts and vacuum events).
3. **Re-express scenarios as causes** (this is what fixes the scenario-4 problem):
   - 2 insulation degradation → heat-flux multiplier ramp over hours–days (K-site-based rates)
   - 3 vacuum degradation → the severity ladder (Q8), not a ×2.5 jump
   - 4 abnormal pressure rise → PCV stuck closed / blocked vent
   - 5 containment anomaly → leak removes vapor from the ullage, so pressure falls (the legacy generator pushed pressure the wrong way)
   - 1 sensor fault, 6 structural concern, −1 composite: unchanged in kind
4. **Add valve/vent signals** only to the extent Q5 says they are instrumented
   (position, vent flow). Until then they are ground truth only.
5. **Rebuild features for two layers**, add the time-to-detect metrics, and
   keep leave-one-module-out plus a fresh set of unseen units. Because the twin
   changes, the current unseen units are no longer unseen.
6. **Run legacy and physical side by side** for one evaluation cycle, then
   retire the legacy generator once results and the placeholder list are signed off.

## 4. Decisions needed from you

- Storage-episode length (7 or 14 days) and sampling interval (60 s, or 600 s with a lower volume).
- Whether the dataset stays JSONL at the multi-GB scale or moves to a compact
  format for the slow layer (the fast layer can stay as is).
- Which fill level healthy scenarios use (85% never reaches liquid-full while the
  PCV works; fault scenarios should run at several fills, Q9b).
- Whether to model stratification (`stratification="empirical"`) in fault
  scenarios. It changes time-to-1.5-bar by 2–3× at 2–3.5 W/m² (off: 26.9 h and
  15.4 h; on: 11.3 h and 5.0 h) and is energy-inconsistent, so it is off by default.
