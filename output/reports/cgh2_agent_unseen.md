# HYDRAI tool agent: ONE-SHOT unseen set (medium class, modules never seen in dev); frozen configuration, trained on all dev

Reference configuration, not a verified Saudi system. Touched ONCE, after the configuration was frozen; nothing was tuned on these units. Intervals are 95 % bootstrap over episodes. Small n is shown as k/n with its interval. 'floor' = first observable deviation of the paired healthy twin (an ideal-observer bound, not a hard physical limit).

Detectors: **static A** = the reference DCS alarms (no low-pressure alarm); **static B** = A plus the PROPOSED low-pressure alarm at 70 % MOP (register open decision; would false-alarm in the healthy twin); ROC / EWMA / CUSUM / inventory = classical baselines (checkpoint 1, 1 healthy false alarm per week); **learned** = the single learned model of checkpoint 1 (66 features, one model); **fusion only** = the tool features' meta-model score alone (no investigation); **agent watch / alert** = the orchestrator tiers. Thresholds for all of them come from healthy dev data only.

## 1. False alarms on healthy exposure

| detector | events | healthy exposure (weeks) | false alarms per week (95 % CI) | per healthy hour |
|---|---|---|---|---|
| static_A | 0 | 78.9 | 0.00 (0.00-0.05) | 0.0000 |
| static_B | 92 | 78.9 | 1.17 (0.94-1.43) | 0.0069 |
| roc | 38 | 78.9 | 0.48 (0.34-0.66) | 0.0029 |
| ewma | 67 | 78.9 | 0.85 (0.66-1.08) | 0.0051 |
| cusum | 48 | 78.9 | 0.61 (0.45-0.81) | 0.0036 |
| inv | 20 | 78.9 | 0.25 (0.15-0.39) | 0.0015 |
| learned | 176 | 78.9 | 2.23 (1.91-2.58) | 0.0133 |
| fusion_alert | 64 | 78.9 | 0.81 (0.62-1.04) | 0.0048 |
| agent_watch | 102 | 78.9 | 1.29 (1.05-1.57) | 0.0077 |
| agent_alert | 81 | 78.9 | 1.03 (0.81-1.28) | 0.0061 |

Alarm-load reference: EEMUA 191 / ISA-18.2 manageable <= 6 per hour; agent target about 1 alert per hour. Healthy exposure includes the dark-vessel stress variants (not used for thresholds).

## 2. Detection per class (alert level; tier definitions fixed before the results were seen)

### 1 sensor_fault  (n = 6; floor: first observable 0.1 h after onset for 6/6)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 6/6 (1.00-1.00) | 0.5 (0.2-0.7) | 0.3 | 0.00 (n=6) |
| static_B | 6/6 (1.00-1.00) | 0.5 (0.2-0.7) | 0.3 | 0.00 (n=6) |
| roc | 0/6 (0.00-0.00) | 69.4 (62.6-130.4) | 69.4 | 0.00 (n=6) |
| ewma | 6/6 (1.00-1.00) | 3.7 (1.6-8.1) | 3.6 | 0.00 (n=6) |
| cusum | 6/6 (1.00-1.00) | 4.6 (2.4-6.6) | 4.5 | 0.00 (n=6) |
| inv | 6/6 (1.00-1.00) | 3.5 (3.3-8.3) | 3.4 | 0.00 (n=6) |
| learned | 4/6 (0.33-1.00) | 1.8 (1.5-2.0) | 1.7 | 0.00 (n=4) |
| fusion_alert | 5/6 (0.50-1.00) | 0.5 (0.3-0.6) | 0.3 | 0.00 (n=6) |
| agent_watch | 5/6 (0.50-1.00) | 0.4 (0.2-0.5) | 0.3 | 0.00 (n=6) |
| agent_alert | 5/6 (0.50-1.00) | 0.4 (0.2-0.5) | 0.3 | 0.00 (n=6) |

### 2 thermal_anomaly  (n = 12; floor: first observable 1.7 h after onset for 12/12)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 1/12 (0.00-0.25) | 29.8 (20.8-43.1) | 29.1 | 0.00 (n=3) |
| static_B | 3/12 (0.00-0.50) | 43.1 (15.4-128.4) | 42.4 | 0.00 (n=10) |
| roc | 3/12 (0.00-0.50) | 37.5 (14.5-98.5) | 25.0 | 0.00 (n=10) |
| ewma | 5/12 (0.17-0.67) | 32.2 (16.7-61.3) | 14.0 | 0.00 (n=12) |
| cusum | 8/12 (0.42-0.92) | 19.7 (10.6-25.5) | 8.5 | 0.00 (n=11) |
| inv | 1/12 (0.00-0.25) | 83.5 (44.8-122.2) | 81.9 | 0.00 (n=2) |
| learned | 9/12 (0.50-1.00) | 10.9 (6.9-22.1) | 7.6 | 0.00 (n=12) |
| fusion_alert | 7/12 (0.33-0.83) | 18.0 (11.7-30.2) | 10.9 | 0.00 (n=11) |
| agent_watch | 9/12 (0.50-1.00) | 16.9 (11.5-22.7) | 10.8 | 0.00 (n=12) |
| agent_alert | 8/12 (0.42-0.92) | 17.8 (11.6-28.4) | 10.9 | 0.00 (n=12) |

### 3 leak 0.1mm  (n = 3; floor: first observable 1.8 h after onset for 3/3)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 0/3 (0.00-0.00) | - | - | - |
| static_B | 1/3 (0.00-1.00) | 93.1 (57.8-128.3) | 89.3 | 35.95 (n=2) |
| roc | 0/3 (0.00-0.00) | 180.6 (180.6-180.6) | 175.0 | 48.29 (n=1) |
| ewma | 0/3 (0.00-0.00) | 159.8 (157.8-161.8) | 156.1 | 53.71 (n=2) |
| cusum | 0/3 (0.00-0.00) | - | - | - |
| inv | 2/3 (0.00-1.00) | 19.4 (18.9-27.9) | 16.8 | 8.05 (n=3) |
| learned | 2/3 (0.00-1.00) | 18.6 (10.0-24.8) | 16.8 | 8.06 (n=3) |
| fusion_alert | 1/3 (0.00-1.00) | 30.5 (25.2-35.8) | 28.8 | 12.79 (n=2) |
| agent_watch | 2/3 (0.00-1.00) | 19.9 (19.1-75.2) | 18.1 | 8.05 (n=3) |
| agent_alert | 2/3 (0.00-1.00) | 20.0 (19.1-75.2) | 18.2 | 8.09 (n=3) |

### 3 leak 0.25mm  (n = 3; floor: first observable 0.3 h after onset for 3/3)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 0/3 (0.00-0.00) | - | - | - |
| static_B | 1/3 (0.00-1.00) | 77.3 (41.0-86.1) | 77.0 | 196.59 (n=3) |
| roc | 1/3 (0.00-1.00) | 41.0 (22.5-59.4) | 40.7 | 103.95 (n=2) |
| ewma | 0/3 (0.00-0.00) | 69.3 (65.1-73.6) | 69.1 | 176.72 (n=2) |
| cusum | 0/3 (0.00-0.00) | 135.8 (130.2-141.4) | 135.5 | 345.85 (n=2) |
| inv | 3/3 (1.00-1.00) | 16.2 (10.9-16.2) | 15.8 | 40.91 (n=3) |
| learned | 3/3 (1.00-1.00) | 0.3 (0.3-3.4) | 0.0 | 0.69 (n=3) |
| fusion_alert | 1/3 (0.00-1.00) | 34.5 (17.4-51.7) | 34.2 | 86.57 (n=2) |
| agent_watch | 2/3 (0.00-1.00) | 0.4 (0.3-0.6) | 0.1 | 0.94 (n=2) |
| agent_alert | 2/3 (0.00-1.00) | 0.6 (0.5-0.6) | 0.3 | 1.38 (n=2) |

### 3 leak 0.5mm  (n = 3; floor: first observable 0.0 h after onset for 3/3)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 0/3 (0.00-0.00) | - | - | - |
| static_B | 2/3 (0.00-1.00) | 7.3 (7.2-55.7) | 7.3 | 72.54 (n=3) |
| roc | 0/3 (0.00-0.00) | 77.5 (64.2-90.9) | 77.5 | 624.75 (n=2) |
| ewma | 1/3 (0.00-1.00) | 55.9 (31.7-80.1) | 55.9 | 404.78 (n=2) |
| cusum | 1/3 (0.00-1.00) | 56.2 (32.0-80.5) | 56.2 | 406.61 (n=2) |
| inv | 3/3 (1.00-1.00) | 6.6 (3.8-14.9) | 6.5 | 45.86 (n=3) |
| learned | 3/3 (1.00-1.00) | 0.3 (0.3-0.3) | 0.3 | 2.84 (n=3) |
| fusion_alert | 3/3 (1.00-1.00) | 0.7 (0.6-0.7) | 0.6 | 5.42 (n=3) |
| agent_watch | 3/3 (1.00-1.00) | 0.6 (0.6-0.7) | 0.6 | 5.93 (n=3) |
| agent_alert | 3/3 (1.00-1.00) | 0.6 (0.6-0.7) | 0.6 | 5.93 (n=3) |

### 3 leak 1mm  (n = 3; floor: first observable 0.0 h after onset for 3/3)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 3/3 (1.00-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.16 (n=3) |
| static_B | 3/3 (1.00-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.16 (n=3) |
| roc | 0/3 (0.00-0.00) | - | - | - |
| ewma | 3/3 (1.00-1.00) | 1.6 (1.4-1.7) | 1.5 | 41.58 (n=3) |
| cusum | 3/3 (1.00-1.00) | 2.5 (2.4-2.8) | 2.4 | 78.92 (n=3) |
| inv | 0/3 (0.00-0.00) | - | - | - |
| learned | 3/3 (1.00-1.00) | 0.2 (0.2-0.3) | 0.2 | 6.61 (n=3) |
| fusion_alert | 3/3 (1.00-1.00) | 0.6 (0.4-0.6) | 0.6 | 20.52 (n=3) |
| agent_watch | 2/3 (0.00-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=2) |
| agent_alert | 2/3 (0.00-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.12 (n=2) |

### 3 small_slow_leak  (n = 18; floor: first observable 1.0 h after onset for 18/18)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 3/18 (0.00-0.33) | 0.0 (0.0-0.0) | 0.0 | 0.16 (n=3) |
| static_B | 7/18 (0.17-0.61) | 35.1 (5.9-86.2) | 16.9 | 11.54 (n=15) |
| roc | 1/18 (0.00-0.17) | 104.3 (64.3-137.8) | 77.5 | 48.29 (n=7) |
| ewma | 4/18 (0.06-0.39) | 60.8 (4.7-110.7) | 60.5 | 64.68 (n=11) |
| cusum | 4/18 (0.06-0.39) | 38.4 (3.1-104.7) | 7.7 | 78.92 (n=9) |
| inv | 8/18 (0.22-0.67) | 17.4 (9.0-22.3) | 14.8 | 14.57 (n=10) |
| learned | 12/18 (0.44-0.89) | 1.4 (0.3-31.0) | 0.3 | 2.84 (n=17) |
| fusion_alert | 9/18 (0.28-0.72) | 0.7 (0.6-24.6) | 0.7 | 5.86 (n=12) |
| agent_watch | 10/18 (0.33-0.78) | 6.8 (0.6-33.3) | 0.7 | 4.15 (n=14) |
| agent_alert | 10/18 (0.33-0.78) | 6.8 (0.6-33.3) | 0.7 | 4.15 (n=14) |

### 3 small_slow_leak WITHOUT expected-miss (0.1-1 mm)  (n = 12; floor: first observable 0.1 h after onset for 12/12)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 3/12 (0.00-0.50) | 0.0 (0.0-0.0) | 0.0 | 0.16 (n=3) |
| static_B | 7/12 (0.33-0.83) | 7.3 (2.4-86.1) | 7.3 | 65.73 (n=11) |
| roc | 1/12 (0.00-0.25) | 77.8 (50.8-104.3) | 77.5 | 197.58 (n=5) |
| ewma | 4/12 (0.08-0.58) | 60.8 (1.9-104.3) | 60.5 | 65.79 (n=9) |
| cusum | 4/12 (0.08-0.58) | 7.7 (2.8-114.7) | 7.7 | 80.19 (n=7) |
| inv | 8/12 (0.42-0.92) | 16.3 (6.6-19.4) | 15.8 | 14.77 (n=9) |
| learned | 11/12 (0.75-1.00) | 0.3 (0.3-2.7) | 0.3 | 4.55 (n=12) |
| fusion_alert | 8/12 (0.42-0.92) | 0.7 (0.6-15.2) | 0.7 | 7.18 (n=10) |
| agent_watch | 9/12 (0.50-1.00) | 0.7 (0.3-13.8) | 0.6 | 5.89 (n=10) |
| agent_alert | 9/12 (0.50-1.00) | 0.7 (0.5-13.8) | 0.6 | 5.89 (n=10) |

### 4 abnormal_pressure_behaviour  (n = 12; floor: first observable 0.4 h after onset for 12/12)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 9/12 (0.50-0.92) | 2.0 (0.7-3.8) | 0.7 | 0.00 (n=9) |
| static_B | 11/12 (0.75-1.00) | 3.6 (1.5-11.4) | 0.8 | 0.00 (n=12) |
| roc | 5/12 (0.17-0.67) | 4.1 (0.6-21.7) | 2.8 | 0.00 (n=7) |
| ewma | 11/12 (0.75-1.00) | 4.6 (1.6-12.2) | 1.5 | 0.00 (n=12) |
| cusum | 10/12 (0.58-1.00) | 6.6 (1.5-18.8) | 4.0 | 0.00 (n=11) |
| inv | 0/12 (0.00-0.00) | 60.6 (46.8-151.1) | 60.6 | 60.78 (n=3) |
| learned | 12/12 (1.00-1.00) | 1.2 (0.5-3.6) | 0.7 | 0.00 (n=12) |
| fusion_alert | 12/12 (1.00-1.00) | 1.5 (0.9-3.5) | 0.6 | 0.00 (n=12) |
| agent_watch | 12/12 (1.00-1.00) | 1.0 (0.5-3.4) | 0.5 | 0.00 (n=12) |
| agent_alert | 12/12 (1.00-1.00) | 1.3 (0.7-3.4) | 0.6 | 0.00 (n=12) |

### 5 containment_anomaly  (n = 10; floor: first observable 0.0 h after onset for 10/10)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 10/10 (1.00-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=10) |
| static_B | 9/10 (0.70-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=9) |
| roc | 8/10 (0.50-1.00) | 0.4 (0.3-0.5) | 0.3 | 88.57 (n=8) |
| ewma | 9/10 (0.70-1.00) | 0.3 (0.2-0.4) | 0.2 | 66.23 (n=9) |
| cusum | 8/10 (0.50-1.00) | 0.4 (0.4-0.7) | 0.4 | 99.12 (n=8) |
| inv | 0/10 (0.00-0.00) | - | - | - |
| learned | 9/10 (0.70-1.00) | 0.2 (0.1-0.2) | 0.1 | 45.44 (n=9) |
| fusion_alert | 7/10 (0.40-0.90) | 0.3 (0.2-0.3) | 0.2 | 54.98 (n=7) |
| agent_watch | 9/10 (0.70-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=9) |
| agent_alert | 9/10 (0.70-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=9) |

### 6 structural_concern  (n = 6; floor: first observable 104.1 h after onset for 6/6)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | no alarm defined | | | |
| static_B | no alarm defined | | | |
| roc | 1/6 (0.00-0.50) | 47.4 (39.2-93.6) | -6.7 | 0.00 (n=4) |
| ewma | 1/6 (0.00-0.50) | 46.7 (38.3-93.5) | -7.4 | 0.00 (n=4) |
| cusum | 1/6 (0.00-0.50) | 61.9 (43.5-102.5) | 7.9 | 0.00 (n=4) |
| inv | 0/6 (0.00-0.00) | 59.1 (41.5-76.6) | -25.9 | 0.00 (n=2) |
| learned | 3/6 (0.17-0.83) | 22.7 (18.9-40.9) | -76.2 | 0.00 (n=6) |
| fusion_alert | 1/6 (0.00-0.50) | 56.5 (31.1-107.7) | -34.2 | 0.00 (n=6) |
| agent_watch | 1/6 (0.00-0.50) | 51.8 (28.8-107.7) | -38.8 | 0.00 (n=6) |
| agent_alert | 1/6 (0.00-0.50) | 51.8 (28.8-107.7) | -38.8 | 0.00 (n=6) |

### 3s leak 0.03mm  (n = 3; floor: first observable 27.6 h after onset for 3/3)

| detector | detected within 24 h (95 % CI) | within 72 h | within 3x floor | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|---|---|
| static_A | 0/3 (0.00-0.00) | 0/3 | 0/3 (floor exists) | - | - | - |
| static_B | 0/3 (0.00-0.00) | 2/3 | 2/3 (floor exists) | 49.5 (42.3-56.8) | -34.9 | 1.50 (n=2) |
| roc | 0/3 (0.00-0.00) | 0/3 | 1/3 (floor exists) | 158.1 (158.1-158.1) | 16.9 | 4.28 (n=1) |
| ewma | 0/3 (0.00-0.00) | 1/3 | 1/3 (floor exists) | 35.4 (35.4-35.4) | -105.8 | 0.96 (n=1) |
| cusum | 0/3 (0.00-0.00) | 2/3 | 2/3 (floor exists) | 53.1 (45.7-60.4) | -31.3 | 1.60 (n=2) |
| inv | 0/3 (0.00-0.00) | 1/3 | 1/3 (floor exists) | 40.1 (40.1-40.1) | 12.5 | 1.29 (n=1) |
| learned | 0/3 (0.00-0.00) | 1/3 | 1/3 (floor exists) | 61.6 (50.0-73.1) | -22.9 | 1.87 (n=2) |
| fusion_alert | 0/3 (0.00-0.00) | 1/3 | 1/3 (floor exists) | 38.5 (38.5-38.5) | -102.8 | 1.04 (n=1) |
| agent_watch | 0/3 (0.00-0.00) | 1/3 | 1/3 (floor exists) | 38.3 (38.3-38.3) | -102.9 | 1.03 (n=1) |
| agent_alert | 0/3 (0.00-0.00) | 1/3 | 1/3 (floor exists) | 38.5 (38.5-38.5) | -102.8 | 1.04 (n=1) |

### 3s leak 0.05mm  (n = 3; floor: first observable 8.8 h after onset for 3/3)

| detector | detected within 24 h (95 % CI) | within 72 h | within 3x floor | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|---|---|
| static_A | 0/3 (0.00-0.00) | 0/3 | 0/3 (floor exists) | - | - | - |
| static_B | 0/3 (0.00-0.00) | 0/3 | 0/3 (floor exists) | 97.2 (87.4-107.0) | 86.1 | 8.28 (n=2) |
| roc | 0/3 (0.00-0.00) | 0/3 | 0/3 (floor exists) | 117.4 (117.4-117.4) | 109.6 | 11.58 (n=1) |
| ewma | 0/3 (0.00-0.00) | 0/3 | 0/3 (floor exists) | 117.1 (117.1-117.1) | 109.3 | 11.55 (n=1) |
| cusum | 0/3 (0.00-0.00) | 0/3 | 0/3 (floor exists) | - | - | - |
| inv | 0/3 (0.00-0.00) | 0/3 | 0/3 (floor exists) | - | - | - |
| learned | 1/3 (0.00-1.00) | 2/3 | 2/3 (floor exists) | 39.3 (21.4-100.2) | 24.8 | 2.57 (n=3) |
| fusion_alert | 1/3 (0.00-1.00) | 1/3 | 1/3 (floor exists) | 12.7 (12.7-12.7) | 3.9 | 1.27 (n=1) |
| agent_watch | 1/3 (0.00-1.00) | 2/3 | 2/3 (floor exists) | 37.7 (25.2-59.1) | 23.2 | 2.46 (n=3) |
| agent_alert | 1/3 (0.00-1.00) | 2/3 | 2/3 (floor exists) | 37.7 (25.2-90.6) | 23.2 | 2.46 (n=3) |

### 5r rupture (50 mm)  (n = 1; floor: first observable 0.0 h after onset for 1/1)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 1/1 (1.00-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=1) |
| static_B | 0/1 (0.00-0.00) | - | - | - |
| roc | 0/1 (0.00-0.00) | - | - | - |
| ewma | 0/1 (0.00-0.00) | - | - | - |
| cusum | 0/1 (0.00-0.00) | - | - | - |
| inv | 0/1 (0.00-0.00) | - | - | - |
| learned | 0/1 (0.00-0.00) | - | - | - |
| fusion_alert | 0/1 (0.00-0.00) | - | - | - |
| agent_watch | 1/1 (1.00-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=1) |
| agent_alert | 1/1 (1.00-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=1) |

### -1 unknown_anomaly (composite)  (n = 12; floor: first observable 0.2 h after onset for 12/12)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 3/12 (0.00-0.50) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=3) |
| static_B | 6/12 (0.25-0.75) | 19.3 (4.6-80.3) | 9.1 | 0.00 (n=11) |
| roc | 6/12 (0.25-0.75) | 9.5 (4.6-79.4) | 8.9 | 38.33 (n=11) |
| ewma | 6/12 (0.25-0.75) | 21.3 (5.4-81.0) | 9.6 | 41.76 (n=11) |
| cusum | 5/12 (0.17-0.67) | 21.5 (1.4-77.3) | 2.4 | 68.50 (n=9) |
| inv | 5/12 (0.17-0.67) | 4.2 (4.1-6.8) | 4.0 | 23.90 (n=5) |
| learned | 10/12 (0.58-1.00) | 0.3 (0.2-5.9) | 0.2 | 1.41 (n=12) |
| fusion_alert | 8/12 (0.42-0.92) | 0.7 (0.4-28.0) | 0.7 | 4.97 (n=11) |
| agent_watch | 9/12 (0.50-1.00) | 0.7 (0.1-11.2) | 0.7 | 0.00 (n=11) |
| agent_alert | 9/12 (0.50-0.92) | 0.7 (0.1-11.2) | 0.7 | 0.00 (n=11) |

## 3. Union coverage within 24 h (static A OR agent alert)

| class | n | static A | agent alert | static OR agent | agent only | static only | neither |
|---|---|---|---|---|---|---|---|
| 1 sensor_fault | 6 | 6 | 5 | 6 | 0 | 1 | 0 |
| 2 thermal_anomaly | 12 | 1 | 8 | 8 | 7 | 0 | 4 |
| 3 small_slow_leak | 18 | 3 | 10 | 11 | 8 | 1 | 7 |
| 4 abnormal_pressure_behaviour | 12 | 9 | 12 | 12 | 3 | 0 | 0 |
| 5 containment_anomaly | 10 | 10 | 9 | 10 | 0 | 1 | 0 |
| 6 structural_concern | 6 | 0 | 1 | 1 | 1 | 0 | 5 |
| -1 unknown_anomaly (composite) | 12 | 3 | 9 | 9 | 6 | 0 | 3 |
| **all classes (rows above)** | 64 | 32 | 54 | 57 | 25 | 3 | 19 |

## 4. Diagnosis (decision at the first alert; time to the first CORRECT alert-level diagnosis)

Static alarms and the classical baselines give no diagnosis: for them 'time to correct diagnosis' is never. A composite (two simultaneous faults) is not a trained class: the correct answer is the open-set 'unknown pattern'.

| class | episodes alerted | correct class at first alert | median time to correct diagnosis h (n) | median kg released before correct diagnosis |
|---|---|---|---|---|
| -1 unknown_anomaly (composite) | 12 | 2/12 | 75.4 (5) | 0.00 |
| 1 sensor_fault | 6 | 6/6 | 0.4 (6) | 0.00 |
| 2 thermal_anomaly | 12 | 10/12 | 18.1 (11) | 0.00 |
| 3 small_slow_leak | 16 | 12/16 | 1.2 (16) | 4.85 |
| 4 abnormal_pressure_behaviour | 12 | 10/12 | 1.5 (12) | 0.00 |
| 5 containment_anomaly | 10 | 5/10 | 0.0 (10) | 0.70 |
| 6 structural_concern | 6 | 4/6 | 51.8 (6) | 0.00 |

Confusion matrix at the first alert decision (rows true, columns decided):

| true \ decided | healthy | sensor | thermal | leak | pressure | contain. | struct. | unknown |
|---|---|---|---|---|---|---|---|---|
| 1 sensor | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2 thermal | 0 | 0 | 10 | 0 | 1 | 0 | 1 | 0 |
| 3 leak | 0 | 1 | 1 | 12 | 2 | 0 | 0 | 0 |
| 4 pressure | 0 | 1 | 1 | 0 | 10 | 0 | 0 | 0 |
| 5 contain. | 0 | 1 | 0 | 2 | 1 | 5 | 0 | 1 |
| 6 struct. | 0 | 0 | 0 | 1 | 0 | 0 | 4 | 1 |
| composite | 0 | 1 | 1 | 6 | 0 | 0 | 2 | 2 |

Overall accuracy over known-class episodes alerted: 47/62. Open-set: composites answered 'unknown pattern': 2/12. Composites whose decided class is one of their two real components: 8/12 (partial credit; the agent has no novelty detector: an isolation forest on the tool features separated composites from single faults at AUC 0.58, i.e. almost chance, so T8 was not built).

## 4b. Leaks and containment: class, size and advice in the first half hour after the first alert

The static alarms (gas detector) fire within about a minute of a large leak, so the agent cannot be earlier; the target is a correct class, a leak-size estimate and isolation advice in the same minutes. Decisions are made at the trigger tick and re-made at +10 and +30 min. True rate = the twin's leak mass flow at that moment (evaluation only).

| group | n alerted | correct class at first alert | correct class at +30 min | median est/true rate at +30 min (n) | est within a factor 2 at +30 min | median time to a factor-2 estimate, min (n) | isolation advice by +30 min |
|---|---|---|---|---|---|---|---|
| 3 leak 0.5mm | 3 | 3/3 | 3/3 | 0.92 (3) | 3/3 | 0 (3) | 3/3 |
| 3 leak 1mm | 3 | 1/3 | 1/3 | - (0) | 0/3 | 40 (3) | 3/3 |
| 5 containment_anomaly | 10 | 5/10 | 10/10 | 0.91 (10) | 6/10 | 13 (9) | 10/10 |

## 5. Investigation effort

Per investigated event (first decision): mean 5.3 tool calls (max 8), mean tool runtime 159 ms (95th percentile 391 ms, max 451 ms), over 317 events.
Tool runtime is the compute time of the tools; the always-on monitor series are vectorised and cost ~2 s per 14-day unit in total.

## 6. Forecast error

Leak cases: kg released in the 6 h after the first alert, forecast (unchecked, no refill, isothermal pressure decay) vs the twin's actual leaked mass. The forecast ignores compressor refills that keep the pressure (and the leak rate) higher, so it is a lower bound when the vessel is topped up.

n = 11; median forecast/actual = 0.93 (IQR 0.44-1.28); median absolute error 19.43 kg; actual inside the forecast interval in 45 % of cases.

Pressure-rise cases: time to PAH forecast at the first alert-time forecast vs the time the true pressure actually crossed PAH:

n = 5; median absolute error 0.03 h; median forecast 0.31 h vs actual 0.27 h; actual inside interval 40 %.

## 7. Sensor faults by subtype

The dataset's sensor-fault episodes are all spike faults on the gas-temperature probe (6 dev episodes). **Episodes of subtle slow drift (0.5-2 % FS over days): 0.** The T5 drift estimator is therefore not evaluated; stopping here as instructed (no regeneration without approval).

