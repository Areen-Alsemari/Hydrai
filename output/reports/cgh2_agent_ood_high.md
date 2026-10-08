# HYDRAI tool agent: ONE-SHOT high set (high pressure class, out of distribution); frozen configuration, trained on all dev

Reference configuration, not a verified Saudi system. Touched ONCE, after the configuration was frozen; nothing was tuned on these units. Intervals are 95 % bootstrap over episodes. Small n is shown as k/n with its interval. 'floor' = first observable deviation of the paired healthy twin (an ideal-observer bound, not a hard physical limit).

Detectors: **static A** = the reference DCS alarms (no low-pressure alarm); **static B** = A plus the PROPOSED low-pressure alarm at 70 % MOP (register open decision; would false-alarm in the healthy twin); ROC / EWMA / CUSUM / inventory = classical baselines (checkpoint 1, 1 healthy false alarm per week); **learned** = the single learned model of checkpoint 1 (66 features, one model); **fusion only** = the tool features' meta-model score alone (no investigation); **agent watch / alert** = the orchestrator tiers. Thresholds for all of them come from healthy dev data only.

## 1. False alarms on healthy exposure

| detector | events | healthy exposure (weeks) | false alarms per week (95 % CI) | per healthy hour |
|---|---|---|---|---|
| static_A | 0 | 40.6 | 0.00 (0.00-0.09) | 0.0000 |
| static_B | 34 | 40.6 | 0.84 (0.58-1.17) | 0.0050 |
| roc | 71 | 40.6 | 1.75 (1.36-2.20) | 0.0104 |
| ewma | 352 | 40.6 | 8.66 (7.78-9.62) | 0.0516 |
| cusum | 48 | 40.6 | 1.18 (0.87-1.57) | 0.0070 |
| inv | 6 | 40.6 | 0.15 (0.05-0.32) | 0.0009 |
| learned | 28 | 40.6 | 0.69 (0.46-1.00) | 0.0041 |
| fusion_alert | 79 | 40.6 | 1.94 (1.54-2.42) | 0.0116 |
| agent_watch | 100 | 40.6 | 2.46 (2.00-2.99) | 0.0147 |
| agent_alert | 77 | 40.6 | 1.90 (1.50-2.37) | 0.0113 |

Alarm-load reference: EEMUA 191 / ISA-18.2 manageable <= 6 per hour; agent target about 1 alert per hour. Healthy exposure includes the dark-vessel stress variants (not used for thresholds).

## 2. Detection per class (alert level; tier definitions fixed before the results were seen)

### 1 sensor_fault  (n = 3; floor: first observable 0.1 h after onset for 3/3)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 3/3 (1.00-1.00) | 0.4 (0.4-0.6) | 0.3 | 0.00 (n=3) |
| static_B | 3/3 (1.00-1.00) | 0.4 (0.4-0.6) | 0.3 | 0.00 (n=3) |
| roc | 2/3 (0.00-1.00) | 19.3 (13.5-30.6) | 19.1 | 0.00 (n=3) |
| ewma | 3/3 (1.00-1.00) | 5.6 (5.3-9.6) | 5.5 | 0.00 (n=3) |
| cusum | 0/3 (0.00-0.00) | - | - | - |
| inv | 3/3 (1.00-1.00) | 4.3 (2.9-10.1) | 4.2 | 0.00 (n=3) |
| learned | 3/3 (1.00-1.00) | 1.4 (1.1-1.6) | 1.3 | 0.00 (n=3) |
| fusion_alert | 3/3 (1.00-1.00) | 0.4 (0.3-0.6) | 0.2 | 0.00 (n=3) |
| agent_watch | 3/3 (1.00-1.00) | 0.3 (0.3-0.4) | 0.2 | 0.00 (n=3) |
| agent_alert | 3/3 (1.00-1.00) | 0.3 (0.3-0.4) | 0.2 | 0.00 (n=3) |

### 2 thermal_anomaly  (n = 6; floor: first observable 7.6 h after onset for 6/6)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 0/6 (0.00-0.00) | 29.4 (27.1-32.4) | 27.6 | 0.00 (n=3) |
| static_B | 0/6 (0.00-0.00) | 35.4 (29.4-76.6) | 33.5 | 0.00 (n=5) |
| roc | 2/6 (0.00-0.67) | 26.7 (19.2-33.4) | 19.1 | 0.00 (n=6) |
| ewma | 5/6 (0.50-1.00) | 15.3 (8.6-17.0) | 0.9 | 0.00 (n=6) |
| cusum | 0/6 (0.00-0.00) | - | - | - |
| inv | 0/6 (0.00-0.00) | 168.7 (157.1-180.4) | 138.0 | 0.00 (n=2) |
| learned | 4/6 (0.33-1.00) | 13.0 (11.7-48.9) | 7.9 | 0.00 (n=6) |
| fusion_alert | 5/6 (0.50-1.00) | 15.8 (12.8-18.2) | 7.7 | 0.00 (n=6) |
| agent_watch | 5/6 (0.50-1.00) | 15.3 (12.3-18.1) | 6.2 | 0.00 (n=6) |
| agent_alert | 5/6 (0.50-1.00) | 15.8 (12.8-18.2) | 7.7 | 0.00 (n=6) |

### 3 leak 0.25mm  (n = 3; floor: first observable 0.3 h after onset for 3/3)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 0/3 (0.00-0.00) | - | - | - |
| static_B | 0/3 (0.00-0.00) | 76.2 (73.5-78.9) | 75.8 | 188.48 (n=2) |
| roc | 0/3 (0.00-0.00) | 83.4 (77.9-149.2) | 83.0 | 221.47 (n=3) |
| ewma | 3/3 (1.00-1.00) | 3.7 (2.1-4.0) | 3.3 | 9.53 (n=3) |
| cusum | 0/3 (0.00-0.00) | - | - | - |
| inv | 3/3 (1.00-1.00) | 7.9 (7.1-8.4) | 7.6 | 21.01 (n=3) |
| learned | 3/3 (1.00-1.00) | 1.5 (0.9-3.5) | 1.2 | 3.89 (n=3) |
| fusion_alert | 3/3 (1.00-1.00) | 3.1 (2.9-6.1) | 2.7 | 7.30 (n=3) |
| agent_watch | 2/3 (0.00-1.00) | 9.2 (5.9-65.2) | 8.9 | 25.15 (n=3) |
| agent_alert | 2/3 (0.00-1.00) | 9.2 (5.9-65.2) | 8.9 | 25.15 (n=3) |

### 3 leak 1mm  (n = 3; floor: first observable 0.0 h after onset for 3/3)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 3/3 (1.00-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=3) |
| static_B | 3/3 (1.00-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=3) |
| roc | 1/3 (0.00-1.00) | 1.2 (1.2-1.2) | 1.2 | 50.31 (n=1) |
| ewma | 3/3 (1.00-1.00) | 3.6 (3.3-4.0) | 3.6 | 136.68 (n=3) |
| cusum | 0/3 (0.00-0.00) | - | - | - |
| inv | 0/3 (0.00-0.00) | - | - | - |
| learned | 3/3 (1.00-1.00) | 0.2 (0.2-0.2) | 0.2 | 9.04 (n=3) |
| fusion_alert | 3/3 (1.00-1.00) | 0.6 (0.5-0.6) | 0.5 | 23.84 (n=3) |
| agent_watch | 3/3 (1.00-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=3) |
| agent_alert | 3/3 (1.00-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=3) |

### 3 small_slow_leak  (n = 9; floor: first observable 0.3 h after onset for 9/9)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 3/9 (0.11-0.67) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=3) |
| static_B | 4/9 (0.11-0.78) | 13.7 (0.0-49.6) | 3.0 | 1.29 (n=7) |
| roc | 1/9 (0.00-0.33) | 72.4 (41.2-149.2) | 72.1 | 50.31 (n=7) |
| ewma | 8/9 (0.67-1.00) | 3.7 (2.9-4.4) | 3.3 | 9.53 (n=9) |
| cusum | 0/9 (0.00-0.00) | - | - | - |
| inv | 3/9 (0.11-0.67) | 7.9 (7.1-8.4) | 7.6 | 21.01 (n=3) |
| learned | 6/9 (0.33-1.00) | 0.9 (0.3-11.9) | 0.7 | 8.40 (n=8) |
| fusion_alert | 7/9 (0.44-1.00) | 3.1 (0.7-9.1) | 2.3 | 11.62 (n=9) |
| agent_watch | 7/9 (0.44-1.00) | 6.1 (0.0-9.2) | 0.0 | 0.65 (n=9) |
| agent_alert | 6/9 (0.33-0.89) | 7.9 (0.0-33.6) | 2.3 | 3.21 (n=9) |

### 3 small_slow_leak WITHOUT expected-miss (0.1-1 mm)  (n = 6; floor: first observable 0.2 h after onset for 6/6)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 3/6 (0.17-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=3) |
| static_B | 3/6 (0.17-0.83) | 0.0 (0.0-70.8) | 0.0 | 0.15 (n=5) |
| roc | 1/6 (0.00-0.50) | 77.9 (54.6-116.3) | 77.5 | 192.24 (n=4) |
| ewma | 6/6 (1.00-1.00) | 3.6 (3.1-4.1) | 3.5 | 58.14 (n=6) |
| cusum | 0/6 (0.00-0.00) | - | - | - |
| inv | 3/6 (0.17-0.83) | 7.9 (7.1-8.4) | 7.6 | 21.01 (n=3) |
| learned | 6/6 (1.00-1.00) | 0.3 (0.2-1.2) | 0.2 | 8.40 (n=6) |
| fusion_alert | 6/6 (1.00-1.00) | 1.7 (0.6-3.0) | 1.5 | 21.10 (n=6) |
| agent_watch | 5/6 (0.50-1.00) | 1.3 (0.0-7.6) | 1.2 | 3.39 (n=6) |
| agent_alert | 5/6 (0.50-1.00) | 1.3 (0.0-7.6) | 1.2 | 3.39 (n=6) |

### 4 abnormal_pressure_behaviour  (n = 12; floor: first observable 5.1 h after onset for 12/12)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 6/12 (0.25-0.75) | 12.1 (0.7-17.7) | 0.7 | 0.00 (n=8) |
| static_B | 6/12 (0.25-0.75) | 12.9 (5.6-38.8) | 0.7 | 0.00 (n=11) |
| roc | 7/12 (0.33-0.83) | 14.3 (8.7-39.9) | 0.7 | 0.00 (n=12) |
| ewma | 8/12 (0.42-0.92) | 13.3 (7.0-21.0) | 1.9 | 0.00 (n=11) |
| cusum | 0/12 (0.00-0.00) | - | - | - |
| inv | 0/12 (0.00-0.00) | - | - | - |
| learned | 9/12 (0.50-1.00) | 2.2 (0.9-13.8) | 0.5 | 0.00 (n=11) |
| fusion_alert | 9/12 (0.50-1.00) | 2.0 (0.8-12.6) | 0.4 | 0.00 (n=11) |
| agent_watch | 8/12 (0.42-0.92) | 5.7 (0.6-13.2) | 0.4 | 0.00 (n=10) |
| agent_alert | 9/12 (0.50-1.00) | 1.4 (0.7-12.5) | 0.4 | 0.00 (n=11) |

### 5 containment_anomaly  (n = 3; floor: first observable 0.0 h after onset for 3/3)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 3/3 (1.00-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=3) |
| static_B | 3/3 (1.00-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=3) |
| roc | 3/3 (1.00-1.00) | 0.3 (0.3-0.3) | 0.3 | 91.08 (n=3) |
| ewma | 1/3 (0.00-1.00) | 0.3 (0.3-0.3) | 0.2 | 81.86 (n=1) |
| cusum | 0/3 (0.00-0.00) | - | - | - |
| inv | 0/3 (0.00-0.00) | - | - | - |
| learned | 3/3 (1.00-1.00) | 0.2 (0.1-0.2) | 0.1 | 42.69 (n=3) |
| fusion_alert | 3/3 (1.00-1.00) | 0.2 (0.2-0.3) | 0.2 | 60.25 (n=3) |
| agent_watch | 3/3 (1.00-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=3) |
| agent_alert | 3/3 (1.00-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=3) |

### 6 structural_concern  (n = 3; floor: first observable 42.4 h after onset for 3/3)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | no alarm defined | | | |
| static_B | no alarm defined | | | |
| roc | 1/3 (0.00-1.00) | 41.7 (29.6-68.2) | -0.8 | 0.00 (n=3) |
| ewma | 3/3 (1.00-1.00) | 15.0 (11.6-16.4) | -34.1 | 0.00 (n=3) |
| cusum | 0/3 (0.00-0.00) | - | - | - |
| inv | 0/3 (0.00-0.00) | 121.7 (121.7-121.7) | 79.3 | 0.00 (n=1) |
| learned | 1/3 (0.00-1.00) | 40.5 (28.9-41.4) | -1.9 | 0.00 (n=3) |
| fusion_alert | 1/3 (0.00-1.00) | 25.7 (23.1-33.6) | -16.7 | 0.00 (n=3) |
| agent_watch | 2/3 (0.00-1.00) | 16.6 (13.0-24.7) | -25.8 | 0.00 (n=3) |
| agent_alert | 2/3 (0.00-1.00) | 16.6 (13.0-24.7) | -25.8 | 0.00 (n=3) |

### 3s leak 0.05mm  (n = 3; floor: first observable 12.2 h after onset for 3/3)

| detector | detected within 24 h (95 % CI) | within 72 h | within 3x floor | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|---|---|
| static_A | 0/3 (0.00-0.00) | 0/3 | 0/3 (floor exists) | - | - | - |
| static_B | 1/3 (0.00-1.00) | 2/3 | 2/3 (floor exists) | 21.0 (17.3-24.7) | 7.6 | 2.00 (n=2) |
| roc | 0/3 (0.00-0.00) | 2/3 | 1/3 (floor exists) | 52.3 (41.2-133.7) | 41.7 | 4.85 (n=3) |
| ewma | 2/3 (0.00-1.00) | 3/3 | 2/3 (floor exists) | 4.4 (2.8-25.9) | -9.6 | 0.40 (n=3) |
| cusum | 0/3 (0.00-0.00) | 0/3 | 0/3 (floor exists) | - | - | - |
| inv | 0/3 (0.00-0.00) | 0/3 | 0/3 (floor exists) | - | - | - |
| learned | 0/3 (0.00-0.00) | 1/3 | 1/3 (floor exists) | 95.4 (63.2-127.7) | 82.1 | 8.82 (n=2) |
| fusion_alert | 1/3 (0.00-1.00) | 2/3 | 2/3 (floor exists) | 33.5 (20.7-79.5) | 17.4 | 3.21 (n=3) |
| agent_watch | 2/3 (0.00-1.00) | 2/3 | 2/3 (floor exists) | 7.7 (6.9-58.5) | -4.5 | 0.65 (n=3) |
| agent_alert | 1/3 (0.00-1.00) | 2/3 | 2/3 (floor exists) | 33.6 (20.7-71.8) | 17.5 | 3.21 (n=3) |

### -1 unknown_anomaly (composite)  (n = 3; floor: first observable 0.2 h after onset for 3/3)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 0/3 (0.00-0.00) | - | - | - |
| static_B | 3/3 (1.00-1.00) | 13.7 (8.8-17.0) | 13.5 | 53.77 (n=3) |
| roc | 3/3 (1.00-1.00) | 12.3 (7.4-13.8) | 12.1 | 56.15 (n=3) |
| ewma | 3/3 (1.00-1.00) | 4.2 (3.4-5.0) | 4.0 | 15.84 (n=3) |
| cusum | 0/3 (0.00-0.00) | - | - | - |
| inv | 2/3 (0.00-1.00) | 3.5 (2.6-4.5) | 3.4 | 19.22 (n=2) |
| learned | 3/3 (1.00-1.00) | 0.3 (0.2-0.3) | 0.1 | 1.18 (n=3) |
| fusion_alert | 3/3 (1.00-1.00) | 0.8 (0.6-1.5) | 0.6 | 4.21 (n=3) |
| agent_watch | 3/3 (1.00-1.00) | 0.9 (0.6-1.6) | 0.7 | 4.75 (n=3) |
| agent_alert | 3/3 (1.00-1.00) | 0.9 (0.6-1.6) | 0.7 | 4.75 (n=3) |

## 3. Union coverage within 24 h (static A OR agent alert)

| class | n | static A | agent alert | static OR agent | agent only | static only | neither |
|---|---|---|---|---|---|---|---|
| 1 sensor_fault | 3 | 3 | 3 | 3 | 0 | 0 | 0 |
| 2 thermal_anomaly | 6 | 0 | 5 | 5 | 5 | 0 | 1 |
| 3 small_slow_leak | 9 | 3 | 6 | 6 | 3 | 0 | 3 |
| 4 abnormal_pressure_behaviour | 12 | 6 | 9 | 9 | 3 | 0 | 3 |
| 5 containment_anomaly | 3 | 3 | 3 | 3 | 0 | 0 | 0 |
| 6 structural_concern | 3 | 0 | 2 | 2 | 2 | 0 | 1 |
| -1 unknown_anomaly (composite) | 3 | 0 | 3 | 3 | 3 | 0 | 0 |
| **all classes (rows above)** | 36 | 15 | 31 | 31 | 16 | 0 | 8 |

## 4. Diagnosis (decision at the first alert; time to the first CORRECT alert-level diagnosis)

Static alarms and the classical baselines give no diagnosis: for them 'time to correct diagnosis' is never. A composite (two simultaneous faults) is not a trained class: the correct answer is the open-set 'unknown pattern'.

| class | episodes alerted | correct class at first alert | median time to correct diagnosis h (n) | median kg released before correct diagnosis |
|---|---|---|---|---|
| -1 unknown_anomaly (composite) | 3 | 0/3 | never (0) | - |
| 1 sensor_fault | 3 | 3/3 | 0.3 (3) | 0.00 |
| 2 thermal_anomaly | 6 | 5/6 | 17.4 (6) | 0.00 |
| 3 small_slow_leak | 9 | 6/9 | 7.9 (9) | 7.09 |
| 4 abnormal_pressure_behaviour | 12 | 7/12 | 6.2 (12) | 0.00 |
| 5 containment_anomaly | 3 | 0/3 | 0.2 (3) | 64.31 |
| 6 structural_concern | 3 | 1/3 | 41.8 (3) | 0.00 |

Confusion matrix at the first alert decision (rows true, columns decided):

| true \ decided | healthy | sensor | thermal | leak | pressure | contain. | struct. | unknown |
|---|---|---|---|---|---|---|---|---|
| 1 sensor | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2 thermal | 0 | 0 | 5 | 1 | 0 | 0 | 0 | 0 |
| 3 leak | 0 | 0 | 1 | 6 | 0 | 0 | 0 | 2 |
| 4 pressure | 0 | 0 | 4 | 1 | 7 | 0 | 0 | 0 |
| 5 contain. | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 2 |
| 6 struct. | 0 | 0 | 0 | 2 | 0 | 0 | 1 | 0 |
| composite | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 |

Overall accuracy over known-class episodes alerted: 22/36. Open-set: composites answered 'unknown pattern': 0/3. Composites whose decided class is one of their two real components: 3/3 (partial credit; the agent has no novelty detector: an isolation forest on the tool features separated composites from single faults at AUC 0.58, i.e. almost chance, so T8 was not built).

## 4b. Leaks and containment: class, size and advice in the first half hour after the first alert

The static alarms (gas detector) fire within about a minute of a large leak, so the agent cannot be earlier; the target is a correct class, a leak-size estimate and isolation advice in the same minutes. Decisions are made at the trigger tick and re-made at +10 and +30 min. True rate = the twin's leak mass flow at that moment (evaluation only).

| group | n alerted | correct class at first alert | correct class at +30 min | median est/true rate at +30 min (n) | est within a factor 2 at +30 min | median time to a factor-2 estimate, min (n) | isolation advice by +30 min |
|---|---|---|---|---|---|---|---|
| 3 leak 0.5mm | 0 | 0/0 | 0/0 | - (0) | 0/0 | never (0) | 0/0 |
| 3 leak 1mm | 3 | 1/3 | 3/3 | 0.96 (3) | 3/3 | 10 (3) | 3/3 |
| 5 containment_anomaly | 3 | 0/3 | 3/3 | 1.26 (3) | 3/3 | 13 (3) | 3/3 |

## 5. Investigation effort

Per investigated event (first decision): mean 5.6 tool calls (max 8), mean tool runtime 185 ms (95th percentile 384 ms, max 516 ms), over 207 events.
Tool runtime is the compute time of the tools; the always-on monitor series are vectorised and cost ~2 s per 14-day unit in total.

## 6. Forecast error

Leak cases: kg released in the 6 h after the first alert, forecast (unchecked, no refill, isothermal pressure decay) vs the twin's actual leaked mass. The forecast ignores compressor refills that keep the pressure (and the leak rate) higher, so it is a lower bound when the vessel is topped up.

n = 5; median forecast/actual = 0.69 (IQR 0.67-0.81); median absolute error 5.24 kg; actual inside the forecast interval in 20 % of cases.

Pressure-rise cases: time to PAH forecast at the first alert-time forecast vs the time the true pressure actually crossed PAH:

n = 4; median absolute error 0.02 h; median forecast 0.35 h vs actual 0.37 h; actual inside interval 50 %.

## 7. Sensor faults by subtype

The dataset's sensor-fault episodes are all spike faults on the gas-temperature probe (3 dev episodes). **Episodes of subtle slow drift (0.5-2 % FS over days): 0.** The T5 drift estimator is therefore not evaluated; stopping here as instructed (no regeneration without approval).

