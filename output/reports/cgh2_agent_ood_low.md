# HYDRAI tool agent: ONE-SHOT low set (low pressure class, out of distribution); frozen configuration, trained on all dev

Reference configuration, not a verified Saudi system. Touched ONCE, after the configuration was frozen; nothing was tuned on these units. Intervals are 95 % bootstrap over episodes. Small n is shown as k/n with its interval. 'floor' = first observable deviation of the paired healthy twin (an ideal-observer bound, not a hard physical limit).

Detectors: **static A** = the reference DCS alarms (no low-pressure alarm); **static B** = A plus the PROPOSED low-pressure alarm at 70 % MOP (register open decision; would false-alarm in the healthy twin); ROC / EWMA / CUSUM / inventory = classical baselines (checkpoint 1, 1 healthy false alarm per week); **learned** = the single learned model of checkpoint 1 (66 features, one model); **fusion only** = the tool features' meta-model score alone (no investigation); **agent watch / alert** = the orchestrator tiers. Thresholds for all of them come from healthy dev data only.

## 1. False alarms on healthy exposure

| detector | events | healthy exposure (weeks) | false alarms per week (95 % CI) | per healthy hour |
|---|---|---|---|---|
| static_A | 0 | 35.2 | 0.00 (0.00-0.10) | 0.0000 |
| static_B | 304 | 35.2 | 8.63 (7.68-9.65) | 0.0514 |
| roc | 0 | 35.2 | 0.00 (0.00-0.10) | 0.0000 |
| ewma | 45 | 35.2 | 1.28 (0.93-1.71) | 0.0076 |
| cusum | 44 | 35.2 | 1.25 (0.91-1.68) | 0.0074 |
| inv | 6 | 35.2 | 0.17 (0.06-0.37) | 0.0010 |
| learned | 60 | 35.2 | 1.70 (1.30-2.19) | 0.0101 |
| fusion_alert | 94 | 35.2 | 2.67 (2.16-3.26) | 0.0159 |
| agent_watch | 135 | 35.2 | 3.83 (3.21-4.53) | 0.0228 |
| agent_alert | 96 | 35.2 | 2.72 (2.21-3.33) | 0.0162 |

Alarm-load reference: EEMUA 191 / ISA-18.2 manageable <= 6 per hour; agent target about 1 alert per hour. Healthy exposure includes the dark-vessel stress variants (not used for thresholds).

## 2. Detection per class (alert level; tier definitions fixed before the results were seen)

### 1 sensor_fault  (n = 3; floor: first observable 0.0 h after onset for 3/3)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 3/3 (1.00-1.00) | 0.1 (0.1-0.2) | 0.1 | 0.00 (n=3) |
| static_B | 3/3 (1.00-1.00) | 0.1 (0.1-0.2) | 0.1 | 0.00 (n=3) |
| roc | 0/3 (0.00-0.00) | 49.0 (37.4-60.7) | 49.0 | 0.00 (n=2) |
| ewma | 0/3 (0.00-0.00) | - | - | - |
| cusum | 0/3 (0.00-0.00) | - | - | - |
| inv | 0/3 (0.00-0.00) | 209.4 (209.4-209.4) | 209.3 | 0.00 (n=1) |
| learned | 3/3 (1.00-1.00) | 1.8 (1.6-2.1) | 1.8 | 0.00 (n=3) |
| fusion_alert | 3/3 (1.00-1.00) | 0.9 (0.8-1.1) | 0.8 | 0.00 (n=3) |
| agent_watch | 3/3 (1.00-1.00) | 0.1 (0.1-0.2) | 0.1 | 0.00 (n=3) |
| agent_alert | 3/3 (1.00-1.00) | 0.1 (0.1-0.2) | 0.1 | 0.00 (n=3) |

### 2 thermal_anomaly  (n = 6; floor: first observable 2.9 h after onset for 6/6)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 0/6 (0.00-0.00) | 40.9 (32.9-48.9) | 40.1 | 0.00 (n=2) |
| static_B | 1/6 (0.00-0.50) | 24.9 (24.4-56.9) | 24.1 | 0.00 (n=5) |
| roc | 0/6 (0.00-0.00) | - | - | - |
| ewma | 0/6 (0.00-0.00) | - | - | - |
| cusum | 0/6 (0.00-0.00) | - | - | - |
| inv | 0/6 (0.00-0.00) | 82.6 (82.6-82.6) | 58.0 | 0.00 (n=1) |
| learned | 3/6 (0.17-0.83) | 23.4 (4.1-66.6) | 18.9 | 0.00 (n=6) |
| fusion_alert | 3/6 (0.17-0.83) | 17.8 (7.5-136.6) | 7.8 | 0.00 (n=6) |
| agent_watch | 5/6 (0.50-1.00) | 13.7 (7.5-18.1) | 7.6 | 0.00 (n=6) |
| agent_alert | 3/6 (0.17-0.83) | 17.6 (7.5-116.8) | 7.7 | 0.00 (n=6) |

### 3 leak 0.25mm  (n = 3; floor: first observable 0.7 h after onset for 3/3)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 0/3 (0.00-0.00) | - | - | - |
| static_B | 1/3 (0.00-1.00) | 28.8 (20.5-66.7) | 28.1 | 9.64 (n=3) |
| roc | 0/3 (0.00-0.00) | - | - | - |
| ewma | 0/3 (0.00-0.00) | - | - | - |
| cusum | 0/3 (0.00-0.00) | - | - | - |
| inv | 2/3 (0.00-1.00) | 21.3 (17.3-31.6) | 20.6 | 7.64 (n=3) |
| learned | 2/3 (0.00-1.00) | 11.7 (9.7-19.1) | 11.0 | 3.96 (n=3) |
| fusion_alert | 2/3 (0.00-1.00) | 14.0 (8.4-22.3) | 13.3 | 4.67 (n=3) |
| agent_watch | 2/3 (0.00-1.00) | 12.4 (7.7-20.9) | 11.7 | 4.19 (n=3) |
| agent_alert | 2/3 (0.00-1.00) | 12.4 (7.7-20.9) | 11.7 | 4.19 (n=3) |

### 3 leak 1mm  (n = 3; floor: first observable 0.0 h after onset for 3/3)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 0/3 (0.00-0.00) | - | - | - |
| static_B | 1/3 (0.00-1.00) | 115.2 (58.3-161.0) | 115.2 | 677.63 (n=3) |
| roc | 0/3 (0.00-0.00) | - | - | - |
| ewma | 0/3 (0.00-0.00) | - | - | - |
| cusum | 0/3 (0.00-0.00) | - | - | - |
| inv | 0/3 (0.00-0.00) | - | - | - |
| learned | 3/3 (1.00-1.00) | 0.3 (0.3-0.3) | 0.3 | 1.89 (n=3) |
| fusion_alert | 2/3 (0.00-1.00) | 1.0 (1.0-47.7) | 1.0 | 6.88 (n=3) |
| agent_watch | 2/3 (0.00-1.00) | 1.1 (1.1-47.8) | 1.1 | 7.62 (n=3) |
| agent_alert | 2/3 (0.00-1.00) | 1.1 (1.1-47.8) | 1.1 | 7.62 (n=3) |

### 3 small_slow_leak  (n = 9; floor: first observable 0.7 h after onset for 9/9)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 0/9 (0.00-0.00) | - | - | - |
| static_B | 4/9 (0.11-0.78) | 28.8 (18.5-104.7) | 28.1 | 8.03 (n=9) |
| roc | 0/9 (0.00-0.00) | - | - | - |
| ewma | 0/9 (0.00-0.00) | - | - | - |
| cusum | 0/9 (0.00-0.00) | - | - | - |
| inv | 2/9 (0.00-0.56) | 21.3 (17.3-31.6) | 20.6 | 7.64 (n=3) |
| learned | 7/9 (0.44-1.00) | 7.7 (0.3-23.6) | 6.5 | 1.89 (n=9) |
| fusion_alert | 5/9 (0.22-0.89) | 14.0 (2.0-23.3) | 2.4 | 5.96 (n=7) |
| agent_watch | 5/9 (0.22-0.89) | 14.2 (2.5-45.6) | 7.1 | 5.38 (n=8) |
| agent_alert | 5/9 (0.22-0.89) | 12.4 (2.1-22.7) | 2.5 | 6.57 (n=7) |

### 3 small_slow_leak WITHOUT expected-miss (0.1-1 mm)  (n = 6; floor: first observable 0.3 h after onset for 6/6)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 0/6 (0.00-0.00) | - | - | - |
| static_B | 2/6 (0.00-0.67) | 66.7 (16.3-112.6) | 66.0 | 23.31 (n=6) |
| roc | 0/6 (0.00-0.00) | - | - | - |
| ewma | 0/6 (0.00-0.00) | - | - | - |
| cusum | 0/6 (0.00-0.00) | - | - | - |
| inv | 2/6 (0.00-0.83) | 21.3 (17.3-31.6) | 20.6 | 7.64 (n=3) |
| learned | 5/6 (0.50-1.00) | 4.0 (0.3-10.7) | 3.8 | 2.18 (n=6) |
| fusion_alert | 4/6 (0.33-1.00) | 8.4 (1.5-26.4) | 7.8 | 6.42 (n=6) |
| agent_watch | 4/6 (0.33-1.00) | 7.7 (1.6-25.1) | 7.1 | 7.10 (n=6) |
| agent_alert | 4/6 (0.33-1.00) | 7.7 (1.6-25.1) | 7.1 | 7.10 (n=6) |

### 4 abnormal_pressure_behaviour  (n = 12; floor: first observable 0.2 h after onset for 12/12)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 7/12 (0.33-0.83) | 2.7 (0.1-13.6) | 0.4 | 0.00 (n=9) |
| static_B | 9/12 (0.50-0.92) | 2.3 (0.4-19.2) | 0.4 | 0.00 (n=12) |
| roc | 3/12 (0.00-0.50) | 0.2 (0.2-0.3) | 0.2 | 2.86 (n=3) |
| ewma | 0/12 (0.00-0.00) | - | - | - |
| cusum | 0/12 (0.00-0.00) | - | - | - |
| inv | 0/12 (0.00-0.00) | - | - | - |
| learned | 9/12 (0.50-1.00) | 3.0 (0.4-12.1) | 0.7 | 0.00 (n=11) |
| fusion_alert | 6/12 (0.25-0.83) | 5.7 (1.4-19.2) | 0.5 | 0.00 (n=8) |
| agent_watch | 9/12 (0.50-1.00) | 1.2 (0.4-11.1) | 0.3 | 0.00 (n=11) |
| agent_alert | 9/12 (0.50-1.00) | 1.2 (0.4-11.1) | 0.3 | 0.00 (n=11) |

### 5 containment_anomaly  (n = 3; floor: first observable 0.0 h after onset for 3/3)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 3/3 (1.00-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=3) |
| static_B | 3/3 (1.00-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=3) |
| roc | 0/3 (0.00-0.00) | - | - | - |
| ewma | 0/3 (0.00-0.00) | - | - | - |
| cusum | 0/3 (0.00-0.00) | - | - | - |
| inv | 0/3 (0.00-0.00) | - | - | - |
| learned | 3/3 (1.00-1.00) | 0.2 (0.1-0.2) | 0.1 | 10.22 (n=3) |
| fusion_alert | 3/3 (1.00-1.00) | 0.2 (0.2-0.2) | 0.2 | 10.94 (n=3) |
| agent_watch | 3/3 (1.00-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=3) |
| agent_alert | 3/3 (1.00-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=3) |

### 6 structural_concern  (n = 3; floor: first observable 101.7 h after onset for 3/3)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | no alarm defined | | | |
| static_B | no alarm defined | | | |
| roc | 0/3 (0.00-0.00) | - | - | - |
| ewma | 0/3 (0.00-0.00) | - | - | - |
| cusum | 0/3 (0.00-0.00) | - | - | - |
| inv | 0/3 (0.00-0.00) | - | - | - |
| learned | 2/3 (0.00-1.00) | 23.2 (14.0-29.7) | -84.5 | 0.00 (n=3) |
| fusion_alert | 1/3 (0.00-1.00) | 36.5 (20.5-64.7) | -33.1 | 0.00 (n=3) |
| agent_watch | 1/3 (0.00-1.00) | 36.7 (19.7-52.2) | -34.8 | 0.00 (n=3) |
| agent_alert | 1/3 (0.00-1.00) | 36.7 (20.5-64.8) | -33.1 | 0.00 (n=3) |

### 3s leak 0.05mm  (n = 3; floor: first observable 31.9 h after onset for 3/3)

| detector | detected within 24 h (95 % CI) | within 72 h | within 3x floor | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|---|---|
| static_A | 0/3 (0.00-0.00) | 0/3 | 0/3 (floor exists) | - | - | - |
| static_B | 2/3 (0.00-1.00) | 3/3 | 2/3 (floor exists) | 19.5 (19.0-41.5) | -13.4 | 0.28 (n=3) |
| roc | 0/3 (0.00-0.00) | 0/3 | 0/3 (floor exists) | - | - | - |
| ewma | 0/3 (0.00-0.00) | 0/3 | 0/3 (floor exists) | - | - | - |
| cusum | 0/3 (0.00-0.00) | 0/3 | 0/3 (floor exists) | - | - | - |
| inv | 0/3 (0.00-0.00) | 0/3 | 0/3 (floor exists) | - | - | - |
| learned | 2/3 (0.00-1.00) | 3/3 | 3/3 (floor exists) | 23.6 (14.4-39.8) | 6.5 | 0.39 (n=3) |
| fusion_alert | 1/3 (0.00-1.00) | 1/3 | 1/3 (floor exists) | 16.0 (16.0-16.0) | -45.6 | 0.20 (n=1) |
| agent_watch | 1/3 (0.00-1.00) | 1/3 | 1/3 (floor exists) | 74.2 (45.1-103.4) | 34.8 | 1.27 (n=2) |
| agent_alert | 1/3 (0.00-1.00) | 1/3 | 1/3 (floor exists) | 16.1 (16.1-16.1) | -45.6 | 0.20 (n=1) |

### -1 unknown_anomaly (composite)  (n = 3; floor: first observable 0.3 h after onset for 3/3)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 0/3 (0.00-0.00) | - | - | - |
| static_B | 0/3 (0.00-0.00) | 26.4 (26.0-94.5) | 26.2 | 27.94 (n=3) |
| roc | 0/3 (0.00-0.00) | - | - | - |
| ewma | 0/3 (0.00-0.00) | - | - | - |
| cusum | 0/3 (0.00-0.00) | - | - | - |
| inv | 3/3 (1.00-1.00) | 5.1 (4.4-6.5) | 4.8 | 3.93 (n=3) |
| learned | 2/3 (0.00-1.00) | 2.3 (1.4-106.3) | 2.0 | 1.66 (n=3) |
| fusion_alert | 3/3 (1.00-1.00) | 4.4 (4.2-5.1) | 4.1 | 4.30 (n=3) |
| agent_watch | 3/3 (1.00-1.00) | 4.5 (3.4-5.2) | 4.2 | 4.38 (n=3) |
| agent_alert | 3/3 (1.00-1.00) | 4.5 (4.3-5.2) | 4.2 | 4.38 (n=3) |

## 3. Union coverage within 24 h (static A OR agent alert)

| class | n | static A | agent alert | static OR agent | agent only | static only | neither |
|---|---|---|---|---|---|---|---|
| 1 sensor_fault | 3 | 3 | 3 | 3 | 0 | 0 | 0 |
| 2 thermal_anomaly | 6 | 0 | 3 | 3 | 3 | 0 | 3 |
| 3 small_slow_leak | 9 | 0 | 5 | 5 | 5 | 0 | 4 |
| 4 abnormal_pressure_behaviour | 12 | 7 | 9 | 9 | 2 | 0 | 3 |
| 5 containment_anomaly | 3 | 3 | 3 | 3 | 0 | 0 | 0 |
| 6 structural_concern | 3 | 0 | 1 | 1 | 1 | 0 | 2 |
| -1 unknown_anomaly (composite) | 3 | 0 | 3 | 3 | 3 | 0 | 0 |
| **all classes (rows above)** | 36 | 13 | 27 | 27 | 14 | 0 | 12 |

## 4. Diagnosis (decision at the first alert; time to the first CORRECT alert-level diagnosis)

Static alarms and the classical baselines give no diagnosis: for them 'time to correct diagnosis' is never. A composite (two simultaneous faults) is not a trained class: the correct answer is the open-set 'unknown pattern'.

| class | episodes alerted | correct class at first alert | median time to correct diagnosis h (n) | median kg released before correct diagnosis |
|---|---|---|---|---|
| -1 unknown_anomaly (composite) | 3 | 0/3 | 30.0 (1) | 22.21 |
| 1 sensor_fault | 3 | 2/3 | 0.2 (3) | 0.00 |
| 2 thermal_anomaly | 6 | 6/6 | 17.6 (6) | 0.00 |
| 3 small_slow_leak | 8 | 7/8 | 3.0 (7) | 4.19 |
| 4 abnormal_pressure_behaviour | 12 | 7/12 | 2.7 (9) | 0.00 |
| 5 containment_anomaly | 3 | 0/3 | 0.3 (3) | 12.63 |
| 6 structural_concern | 3 | 2/3 | 36.7 (3) | 0.00 |

Confusion matrix at the first alert decision (rows true, columns decided):

| true \ decided | healthy | sensor | thermal | leak | pressure | contain. | struct. | unknown |
|---|---|---|---|---|---|---|---|---|
| 1 sensor | 0 | 2 | 0 | 0 | 1 | 0 | 0 | 0 |
| 2 thermal | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 |
| 3 leak | 0 | 0 | 0 | 7 | 1 | 0 | 0 | 0 |
| 4 pressure | 0 | 1 | 2 | 1 | 7 | 0 | 0 | 1 |
| 5 contain. | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 |
| 6 struct. | 0 | 0 | 0 | 1 | 0 | 0 | 2 | 0 |
| composite | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 |

Overall accuracy over known-class episodes alerted: 24/35. Open-set: composites answered 'unknown pattern': 0/3. Composites whose decided class is one of their two real components: 3/3 (partial credit; the agent has no novelty detector: an isolation forest on the tool features separated composites from single faults at AUC 0.58, i.e. almost chance, so T8 was not built).

## 4b. Leaks and containment: class, size and advice in the first half hour after the first alert

The static alarms (gas detector) fire within about a minute of a large leak, so the agent cannot be earlier; the target is a correct class, a leak-size estimate and isolation advice in the same minutes. Decisions are made at the trigger tick and re-made at +10 and +30 min. True rate = the twin's leak mass flow at that moment (evaluation only).

| group | n alerted | correct class at first alert | correct class at +30 min | median est/true rate at +30 min (n) | est within a factor 2 at +30 min | median time to a factor-2 estimate, min (n) | isolation advice by +30 min |
|---|---|---|---|---|---|---|---|
| 3 leak 0.5mm | 0 | 0/0 | 0/0 | - (0) | 0/0 | never (0) | 0/0 |
| 3 leak 1mm | 3 | 3/3 | 3/3 | 0.72 (3) | 2/3 | 0 (3) | 3/3 |
| 5 containment_anomaly | 3 | 0/3 | 3/3 | 1.03 (3) | 3/3 | 14 (3) | 3/3 |

## 5. Investigation effort

Per investigated event (first decision): mean 5.2 tool calls (max 8), mean tool runtime 86 ms (95th percentile 402 ms, max 489 ms), over 417 events.
Tool runtime is the compute time of the tools; the always-on monitor series are vectorised and cost ~2 s per 14-day unit in total.

## 6. Forecast error

Leak cases: kg released in the 6 h after the first alert, forecast (unchecked, no refill, isothermal pressure decay) vs the twin's actual leaked mass. The forecast ignores compressor refills that keep the pressure (and the leak rate) higher, so it is a lower bound when the vessel is topped up.

n = 10; median forecast/actual = 1.52 (IQR 0.75-2.97); median absolute error 5.82 kg; actual inside the forecast interval in 30 % of cases.

Pressure-rise cases: time to PAH forecast at the first alert-time forecast vs the time the true pressure actually crossed PAH:

n = 2; median absolute error 0.01 h; median forecast 0.24 h vs actual 0.26 h; actual inside interval 0 %.

## 7. Sensor faults by subtype

The dataset's sensor-fault episodes are all spike faults on the gas-temperature probe (3 dev episodes). **Episodes of subtle slow drift (0.5-2 % FS over days): 0.** The T5 drift estimator is therefore not evaluated; stopping here as instructed (no regeneration without approval).

