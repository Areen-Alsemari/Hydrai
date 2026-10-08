# HYDRAI tool agent: dev evaluation (leave-one-module-out, medium class)

Reference configuration, not a verified Saudi system. All numbers are dev only (6 modules x leave-one-module-out). Unseen and OOD are NOT used. Intervals are 95 % bootstrap over episodes. Small n is shown as k/n with its interval. 'floor' = first observable deviation of the paired healthy twin (an ideal-observer bound, not a hard physical limit).

Detectors: **static A** = the reference DCS alarms (no low-pressure alarm); **static B** = A plus the PROPOSED low-pressure alarm at 70 % MOP (register open decision; would false-alarm in the healthy twin); ROC / EWMA / CUSUM / inventory = classical baselines (checkpoint 1, 1 healthy false alarm per week); **learned** = the single learned model of checkpoint 1 (66 features, one model); **fusion only** = the tool features' meta-model score alone (no investigation); **agent watch / alert** = the orchestrator tiers. Thresholds for all of them come from healthy dev data only.

## 1. False alarms on healthy exposure

| detector | events | healthy exposure (weeks) | false alarms per week (95 % CI) | per healthy hour |
|---|---|---|---|---|
| static_A | 0 | 159.4 | 0.00 (0.00-0.02) | 0.0000 |
| static_B | 201 | 159.4 | 1.26 (1.09-1.45) | 0.0075 |
| roc | 139 | 159.4 | 0.87 (0.73-1.03) | 0.0052 |
| ewma | 160 | 159.4 | 1.00 (0.85-1.17) | 0.0060 |
| cusum | 132 | 159.4 | 0.83 (0.69-0.98) | 0.0049 |
| inv | 37 | 159.4 | 0.23 (0.16-0.32) | 0.0014 |
| learned | 73 | 159.4 | 0.46 (0.36-0.58) | 0.0027 |
| fusion_alert | 108 | 159.4 | 0.68 (0.56-0.82) | 0.0040 |
| agent_watch | 137 | 159.4 | 0.86 (0.72-1.02) | 0.0051 |
| agent_alert | 105 | 159.4 | 0.66 (0.54-0.80) | 0.0039 |

Alarm-load reference: EEMUA 191 / ISA-18.2 manageable <= 6 per hour; agent target about 1 alert per hour. Healthy exposure includes the dark-vessel stress variants (not used for thresholds).

## 2. Detection per class (alert level; tier definitions fixed before the results were seen)

### 1 sensor_fault  (n = 12; floor: first observable 0.1 h after onset for 12/12)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 12/12 (1.00-1.00) | 0.3 (0.1-1.2) | 0.1 | 0.00 (n=12) |
| static_B | 12/12 (1.00-1.00) | 0.3 (0.1-1.2) | 0.1 | 0.00 (n=12) |
| roc | 5/12 (0.17-0.75) | 35.3 (6.6-56.7) | 35.1 | 0.00 (n=12) |
| ewma | 11/12 (0.75-1.00) | 4.3 (2.7-7.5) | 4.2 | 0.00 (n=12) |
| cusum | 12/12 (1.00-1.00) | 4.5 (3.4-5.7) | 4.4 | 0.00 (n=12) |
| inv | 11/12 (0.75-1.00) | 5.4 (3.3-9.4) | 5.2 | 0.00 (n=12) |
| learned | 12/12 (1.00-1.00) | 1.8 (1.6-2.8) | 1.8 | 0.00 (n=12) |
| fusion_alert | 11/12 (0.75-1.00) | 0.3 (0.3-0.5) | 0.2 | 0.00 (n=11) |
| agent_watch | 10/12 (0.58-1.00) | 0.2 (0.1-0.3) | 0.1 | 0.00 (n=10) |
| agent_alert | 10/12 (0.58-1.00) | 0.2 (0.1-0.3) | 0.1 | 0.00 (n=10) |

### 2 thermal_anomaly  (n = 24; floor: first observable 1.7 h after onset for 24/24)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 1/24 (0.00-0.12) | 47.4 (25.1-82.9) | 46.2 | 0.00 (n=6) |
| static_B | 7/24 (0.12-0.46) | 34.1 (13.2-78.4) | 24.1 | 0.00 (n=20) |
| roc | 11/24 (0.25-0.67) | 18.0 (14.5-45.8) | 10.6 | 0.00 (n=21) |
| ewma | 10/24 (0.25-0.58) | 28.9 (13.8-75.3) | 20.1 | 0.00 (n=22) |
| cusum | 12/24 (0.29-0.71) | 20.6 (14.1-34.4) | 14.9 | 0.00 (n=22) |
| inv | 2/24 (0.00-0.21) | 63.4 (20.2-63.7) | 49.6 | 0.00 (n=5) |
| learned | 15/24 (0.42-0.83) | 12.2 (10.8-34.0) | 11.4 | 0.00 (n=22) |
| fusion_alert | 14/24 (0.42-0.79) | 16.4 (12.2-37.3) | 11.4 | 0.00 (n=24) |
| agent_watch | 16/24 (0.50-0.83) | 15.8 (10.9-31.1) | 9.8 | 0.00 (n=24) |
| agent_alert | 14/24 (0.38-0.79) | 16.4 (11.6-42.5) | 11.5 | 0.00 (n=24) |

### 3 leak 0.1mm  (n = 6; floor: first observable 2.4 h after onset for 6/6)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 0/6 (0.00-0.00) | - | - | - |
| static_B | 2/6 (0.00-0.67) | 30.4 (17.2-38.0) | 28.0 | 10.39 (n=6) |
| roc | 0/6 (0.00-0.00) | 73.0 (44.2-102.7) | 70.2 | 22.60 (n=4) |
| ewma | 2/6 (0.00-0.67) | 43.8 (13.4-92.0) | 41.0 | 13.19 (n=5) |
| cusum | 1/6 (0.00-0.50) | 52.3 (31.0-73.5) | 49.7 | 19.28 (n=2) |
| inv | 1/6 (0.00-0.50) | 68.8 (54.0-79.9) | 66.4 | 23.47 (n=4) |
| learned | 1/6 (0.00-0.50) | 35.4 (18.0-55.0) | 33.3 | 13.84 (n=3) |
| fusion_alert | 2/6 (0.00-0.67) | 55.5 (15.0-96.4) | 53.0 | 19.96 (n=6) |
| agent_watch | 4/6 (0.33-1.00) | 6.7 (5.1-26.9) | 4.3 | 2.15 (n=6) |
| agent_alert | 4/6 (0.33-1.00) | 7.0 (5.4-26.9) | 4.6 | 2.25 (n=6) |

### 3 leak 0.25mm  (n = 6; floor: first observable 0.3 h after onset for 6/6)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 0/6 (0.00-0.00) | - | - | - |
| static_B | 0/6 (0.00-0.00) | 101.0 (66.4-114.7) | 100.7 | 214.46 (n=6) |
| roc | 0/6 (0.00-0.00) | 108.5 (94.6-112.2) | 108.2 | 229.94 (n=4) |
| ewma | 0/6 (0.00-0.00) | 102.6 (85.6-112.4) | 102.3 | 217.57 (n=4) |
| cusum | 0/6 (0.00-0.00) | 103.0 (85.7-113.0) | 102.7 | 218.30 (n=4) |
| inv | 5/6 (0.50-1.00) | 5.0 (2.6-6.8) | 4.6 | 10.71 (n=5) |
| learned | 6/6 (1.00-1.00) | 6.0 (1.5-7.4) | 5.6 | 12.92 (n=6) |
| fusion_alert | 5/6 (0.50-1.00) | 1.9 (0.9-2.7) | 1.6 | 4.09 (n=6) |
| agent_watch | 5/6 (0.50-1.00) | 1.1 (0.7-2.4) | 0.8 | 2.13 (n=6) |
| agent_alert | 5/6 (0.50-1.00) | 1.9 (0.9-2.6) | 1.6 | 3.99 (n=6) |

### 3 leak 0.5mm  (n = 6; floor: first observable 0.0 h after onset for 6/6)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 0/6 (0.00-0.00) | - | - | - |
| static_B | 2/6 (0.00-0.67) | 51.1 (21.4-94.2) | 51.1 | 379.58 (n=6) |
| roc | 0/6 (0.00-0.00) | 100.6 (63.3-159.2) | 100.5 | 894.37 (n=3) |
| ewma | 0/6 (0.00-0.00) | 100.4 (76.7-183.4) | 100.3 | 893.00 (n=5) |
| cusum | 0/6 (0.00-0.00) | 160.7 (100.9-171.5) | 160.7 | 1197.41 (n=5) |
| inv | 5/6 (0.50-1.00) | 1.4 (1.4-11.1) | 1.4 | 11.14 (n=5) |
| learned | 6/6 (1.00-1.00) | 0.4 (0.3-0.6) | 0.4 | 3.12 (n=6) |
| fusion_alert | 6/6 (1.00-1.00) | 0.3 (0.2-0.6) | 0.3 | 2.43 (n=6) |
| agent_watch | 6/6 (1.00-1.00) | 0.3 (0.3-0.7) | 0.3 | 2.94 (n=6) |
| agent_alert | 6/6 (1.00-1.00) | 0.3 (0.3-0.7) | 0.3 | 2.94 (n=6) |

### 3 leak 1mm  (n = 6; floor: first observable 0.0 h after onset for 6/6)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 5/6 (0.50-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.08 (n=6) |
| static_B | 5/6 (0.50-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.06 (n=5) |
| roc | 1/6 (0.00-0.50) | 1.2 (1.2-1.2) | 1.1 | 43.64 (n=1) |
| ewma | 5/6 (0.50-1.00) | 1.6 (1.3-2.0) | 1.6 | 48.46 (n=5) |
| cusum | 4/6 (0.33-1.00) | 3.0 (2.1-4.1) | 3.0 | 92.05 (n=4) |
| inv | 2/6 (0.00-0.67) | 0.7 (0.7-0.7) | 0.6 | 18.57 (n=2) |
| learned | 5/6 (0.50-1.00) | 0.3 (0.2-0.3) | 0.2 | 7.91 (n=5) |
| fusion_alert | 5/6 (0.50-1.00) | 0.6 (0.5-0.6) | 0.5 | 17.15 (n=5) |
| agent_watch | 5/6 (0.50-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.06 (n=5) |
| agent_alert | 5/6 (0.50-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.06 (n=5) |

### 3 small_slow_leak  (n = 36; floor: first observable 1.2 h after onset for 36/36)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 5/36 (0.03-0.28) | 0.0 (0.0-0.0) | 0.0 | 0.08 (n=6) |
| static_B | 13/36 (0.22-0.53) | 45.9 (12.6-113.4) | 37.7 | 11.25 (n=35) |
| roc | 2/36 (0.00-0.14) | 106.7 (48.7-122.8) | 99.4 | 14.53 (n=22) |
| ewma | 9/36 (0.11-0.39) | 76.7 (15.0-113.7) | 57.1 | 43.32 (n=27) |
| cusum | 6/36 (0.06-0.28) | 75.3 (8.6-113.0) | 58.1 | 113.62 (n=20) |
| inv | 14/36 (0.25-0.56) | 11.1 (2.0-36.6) | 9.8 | 13.00 (n=19) |
| learned | 18/36 (0.33-0.67) | 0.4 (0.3-7.0) | 0.4 | 6.43 (n=21) |
| fusion_alert | 20/36 (0.39-0.69) | 2.9 (0.7-94.5) | 1.2 | 5.78 (n=31) |
| agent_watch | 23/36 (0.47-0.78) | 2.7 (0.3-26.7) | 0.8 | 2.05 (n=31) |
| agent_alert | 23/36 (0.47-0.78) | 2.7 (0.3-26.7) | 0.9 | 2.26 (n=31) |

### 3 small_slow_leak WITHOUT expected-miss (0.1-1 mm)  (n = 24; floor: first observable 0.2 h after onset for 24/24)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 5/24 (0.04-0.38) | 0.0 (0.0-0.0) | 0.0 | 0.08 (n=6) |
| static_B | 9/24 (0.21-0.58) | 31.8 (9.5-95.7) | 29.0 | 52.54 (n=23) |
| roc | 1/24 (0.00-0.12) | 100.8 (44.2-108.2) | 99.4 | 175.63 (n=12) |
| ewma | 7/24 (0.12-0.46) | 60.0 (7.4-105.5) | 59.6 | 63.55 (n=19) |
| cusum | 5/24 (0.08-0.38) | 94.3 (7.4-114.2) | 92.4 | 199.79 (n=15) |
| inv | 13/24 (0.38-0.71) | 5.9 (1.4-21.4) | 5.5 | 16.02 (n=16) |
| learned | 18/24 (0.58-0.92) | 0.4 (0.3-5.5) | 0.3 | 6.25 (n=20) |
| fusion_alert | 18/24 (0.58-0.92) | 0.8 (0.5-6.9) | 0.8 | 6.05 (n=23) |
| agent_watch | 20/24 (0.67-0.96) | 0.7 (0.3-4.7) | 0.4 | 2.00 (n=23) |
| agent_alert | 20/24 (0.67-0.96) | 0.8 (0.3-4.8) | 0.8 | 2.25 (n=23) |

### 4 abnormal_pressure_behaviour  (n = 24; floor: first observable 2.1 h after onset for 24/24)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 14/24 (0.38-0.79) | 12.4 (0.6-21.0) | 0.6 | 0.00 (n=18) |
| static_B | 14/24 (0.38-0.79) | 18.7 (3.8-46.3) | 0.6 | 0.00 (n=24) |
| roc | 8/24 (0.17-0.54) | 19.7 (0.7-68.2) | 1.3 | 0.00 (n=14) |
| ewma | 14/24 (0.38-0.75) | 19.5 (4.3-47.2) | 1.4 | 0.00 (n=24) |
| cusum | 12/24 (0.29-0.71) | 20.2 (0.5-42.3) | 3.7 | 0.00 (n=22) |
| inv | 0/24 (0.00-0.00) | - | - | - |
| learned | 20/24 (0.67-0.96) | 10.4 (0.5-19.6) | 0.8 | 0.00 (n=24) |
| fusion_alert | 21/24 (0.75-1.00) | 4.1 (0.8-17.4) | 0.6 | 0.00 (n=24) |
| agent_watch | 20/24 (0.67-0.96) | 5.0 (0.6-17.5) | 0.5 | 0.00 (n=23) |
| agent_alert | 20/24 (0.67-0.96) | 5.0 (0.6-17.5) | 0.5 | 0.00 (n=23) |

### 5 containment_anomaly  (n = 20; floor: first observable 0.0 h after onset for 20/20)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 20/20 (1.00-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=20) |
| static_B | 18/20 (0.75-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=18) |
| roc | 17/20 (0.70-1.00) | 0.3 (0.3-0.5) | 0.3 | 89.94 (n=17) |
| ewma | 17/20 (0.70-1.00) | 0.2 (0.2-0.3) | 0.2 | 75.36 (n=17) |
| cusum | 16/20 (0.60-0.95) | 0.4 (0.3-0.4) | 0.3 | 101.96 (n=16) |
| inv | 0/20 (0.00-0.00) | - | - | - |
| learned | 18/20 (0.75-1.00) | 0.2 (0.2-0.2) | 0.2 | 56.33 (n=18) |
| fusion_alert | 17/20 (0.70-1.00) | 0.3 (0.3-0.3) | 0.2 | 71.44 (n=17) |
| agent_watch | 19/20 (0.85-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=19) |
| agent_alert | 18/20 (0.75-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=18) |

### 6 structural_concern  (n = 12; floor: first observable 91.1 h after onset for 12/12)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | no alarm defined | | | |
| static_B | no alarm defined | | | |
| roc | 2/12 (0.00-0.42) | 71.2 (33.5-96.4) | -0.6 | 0.00 (n=8) |
| ewma | 1/12 (0.00-0.25) | 75.3 (60.4-150.6) | 16.6 | 0.00 (n=9) |
| cusum | 4/12 (0.08-0.59) | 22.1 (11.3-60.4) | -43.2 | 0.00 (n=8) |
| inv | 0/12 (0.00-0.00) | 97.8 (89.4-161.5) | 5.0 | 0.00 (n=5) |
| learned | 4/12 (0.08-0.58) | 43.9 (16.4-71.9) | -29.5 | 0.00 (n=12) |
| fusion_alert | 7/12 (0.33-0.83) | 20.1 (10.1-34.9) | -65.4 | 0.00 (n=12) |
| agent_watch | 6/12 (0.25-0.75) | 21.1 (9.6-37.1) | -72.7 | 0.00 (n=11) |
| agent_alert | 6/12 (0.25-0.75) | 21.1 (10.9-37.1) | -72.7 | 0.00 (n=11) |

### 3s leak 0.03mm  (n = 6; floor: first observable 44.1 h after onset for 6/6)

| detector | detected within 24 h (95 % CI) | within 72 h | within 3x floor | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|---|---|
| static_A | 0/6 (0.00-0.00) | 0/6 | 0/6 (floor exists) | - | - | - |
| static_B | 2/6 (0.00-0.67) | 2/6 | 4/6 (floor exists) | 118.0 (32.0-195.0) | 47.6 | 3.51 (n=6) |
| roc | 0/6 (0.00-0.00) | 0/6 | 2/6 (floor exists) | 158.8 (120.3-209.4) | 113.6 | 5.15 (n=5) |
| ewma | 1/6 (0.00-0.50) | 2/6 | 3/6 (floor exists) | 94.2 (56.3-128.5) | 28.7 | 2.44 (n=4) |
| cusum | 1/6 (0.00-0.50) | 1/6 | 2/6 (floor exists) | 82.6 (43.4-137.9) | -12.9 | 2.02 (n=3) |
| inv | 0/6 (0.00-0.00) | 0/6 | 0/6 (floor exists) | - | - | - |
| learned | 0/6 (0.00-0.00) | 0/6 | 0/6 (floor exists) | 209.8 (209.8-209.8) | 189.2 | 7.26 (n=1) |
| fusion_alert | 1/6 (0.00-0.50) | 1/6 | 4/6 (floor exists) | 100.6 (88.3-170.1) | 65.1 | 2.85 (n=5) |
| agent_watch | 2/6 (0.00-0.67) | 2/6 | 5/6 (floor exists) | 88.4 (20.2-94.7) | 43.2 | 2.67 (n=5) |
| agent_alert | 2/6 (0.00-0.67) | 2/6 | 5/6 (floor exists) | 88.4 (20.2-94.7) | 43.2 | 2.67 (n=5) |

### 3s leak 0.05mm  (n = 6; floor: first observable 13.4 h after onset for 6/6)

| detector | detected within 24 h (95 % CI) | within 72 h | within 3x floor | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|---|---|
| static_A | 0/6 (0.00-0.00) | 0/6 | 0/6 (floor exists) | - | - | - |
| static_B | 2/6 (0.00-0.67) | 2/6 | 2/6 (floor exists) | 100.7 (36.9-154.2) | 90.8 | 8.83 (n=6) |
| roc | 1/6 (0.00-0.50) | 2/6 | 2/6 (floor exists) | 80.2 (25.0-123.6) | 68.6 | 6.15 (n=5) |
| ewma | 1/6 (0.00-0.50) | 1/6 | 1/6 (floor exists) | 101.1 (64.9-133.9) | 86.1 | 8.86 (n=4) |
| cusum | 0/6 (0.00-0.00) | 2/6 | 0/6 (floor exists) | 63.1 (60.5-65.6) | 49.6 | 4.94 (n=2) |
| inv | 1/6 (0.00-0.50) | 2/6 | 1/6 (floor exists) | 49.7 (35.5-105.3) | 39.4 | 4.46 (n=3) |
| learned | 0/6 (0.00-0.00) | 0/6 | 0/6 (floor exists) | - | - | - |
| fusion_alert | 1/6 (0.00-0.50) | 1/6 | 1/6 (floor exists) | 190.6 (97.6-197.5) | 182.2 | 15.79 (n=3) |
| agent_watch | 1/6 (0.00-0.50) | 2/6 | 1/6 (floor exists) | 65.9 (35.2-83.9) | 57.5 | 6.24 (n=3) |
| agent_alert | 1/6 (0.00-0.50) | 1/6 | 1/6 (floor exists) | 190.4 (97.5-197.4) | 182.0 | 15.80 (n=3) |

### 5r rupture (50 mm)  (n = 2; floor: first observable 0.0 h after onset for 2/2)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 2/2 (1.00-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=2) |
| static_B | 0/2 (0.00-0.00) | - | - | - |
| roc | 0/2 (0.00-0.00) | - | - | - |
| ewma | 0/2 (0.00-0.00) | - | - | - |
| cusum | 0/2 (0.00-0.00) | - | - | - |
| inv | 0/2 (0.00-0.00) | - | - | - |
| learned | 0/2 (0.00-0.00) | - | - | - |
| fusion_alert | 0/2 (0.00-0.00) | - | - | - |
| agent_watch | 1/2 (0.00-1.00) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=1) |
| agent_alert | 0/2 (0.00-0.00) | - | - | - |

### -1 unknown_anomaly (composite)  (n = 24; floor: first observable 0.2 h after onset for 24/24)

| detector | detected within 24 h (95 % CI) | median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |
|---|---|---|---|---|
| static_A | 6/24 (0.08-0.42) | 0.0 (0.0-0.0) | 0.0 | 0.00 (n=6) |
| static_B | 9/24 (0.21-0.54) | 26.7 (0.0-66.5) | 20.9 | 10.50 (n=20) |
| roc | 9/24 (0.17-0.58) | 37.2 (1.9-106.0) | 37.0 | 59.02 (n=19) |
| ewma | 11/24 (0.25-0.67) | 18.7 (1.0-118.6) | 3.6 | 36.82 (n=21) |
| cusum | 10/24 (0.21-0.58) | 12.6 (1.4-92.4) | 9.6 | 67.22 (n=18) |
| inv | 12/24 (0.29-0.71) | 6.7 (3.7-20.0) | 6.5 | 14.64 (n=16) |
| learned | 19/24 (0.62-0.96) | 0.4 (0.4-6.6) | 0.4 | 2.06 (n=24) |
| fusion_alert | 20/24 (0.67-0.96) | 0.9 (0.3-3.4) | 0.6 | 3.55 (n=24) |
| agent_watch | 20/24 (0.67-0.96) | 0.7 (0.1-3.4) | 0.5 | 0.43 (n=24) |
| agent_alert | 20/24 (0.67-0.96) | 0.8 (0.2-3.4) | 0.6 | 0.49 (n=24) |

## 2b. Operating curves: detected within 24 h and healthy false alarms per week at three budgets

Equal-cost reading of any 'earlier' claim: compare detectors at the same realized false-alarm rate (last row). The orchestrated agent's alert tier adds evidence-based escalations on top of the fusion score.

| group | learned @1/day | learned @1/wk | learned @1/4wk | fusion @watch | fusion @alert | fusion @4wk | agent alert |
|---|---|---|---|---|---|---|---|
| 1 sensor_fault | 12/12 | 12/12 | 11/12 | 11/12 | 11/12 | 11/12 | 10/12 |
| 2 thermal_anomaly | 15/24 | 15/24 | 11/24 | 17/24 | 14/24 | 10/24 | 14/24 |
| 3 leak 0.1mm | 1/6 | 1/6 | 0/6 | 4/6 | 2/6 | 0/6 | 4/6 |
| 3 leak 0.25mm | 6/6 | 6/6 | 6/6 | 5/6 | 5/6 | 6/6 | 5/6 |
| 3 leak 0.5mm | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 |
| 3 leak 1mm | 5/6 | 5/6 | 5/6 | 5/6 | 5/6 | 5/6 | 5/6 |
| 3 small_slow_leak | 18/36 | 18/36 | 17/36 | 24/36 | 20/36 | 17/36 | 23/36 |
| 3 small_slow_leak WITHOUT expected-miss (0.1-1 mm) | 18/24 | 18/24 | 17/24 | 20/24 | 18/24 | 17/24 | 20/24 |
| 4 abnormal_pressure_behaviour | 20/24 | 20/24 | 15/24 | 19/24 | 21/24 | 20/24 | 20/24 |
| 5 containment_anomaly | 18/20 | 18/20 | 18/20 | 17/20 | 17/20 | 18/20 | 18/20 |
| 6 structural_concern | 4/12 | 4/12 | 3/12 | 7/12 | 7/12 | 4/12 | 6/12 |
| 3s leak 0.03mm | 0/6 | 0/6 | 0/6 | 3/6 | 1/6 | 0/6 | 2/6 |
| 3s leak 0.05mm | 0/6 | 0/6 | 0/6 | 1/6 | 1/6 | 0/6 | 1/6 |
| 5r rupture (50 mm) | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 |
| -1 unknown_anomaly (composite) | 19/24 | 19/24 | 18/24 | 20/24 | 20/24 | 19/24 | 20/24 |
| **healthy false alarms / week** | 0.55 | 0.46 | 0.03 | 1.05 | 0.68 | 0.13 | 0.66 |

## 3. Union coverage within 24 h (static A OR agent alert)

| class | n | static A | agent alert | static OR agent | agent only | static only | neither |
|---|---|---|---|---|---|---|---|
| 1 sensor_fault | 12 | 12 | 10 | 12 | 0 | 2 | 0 |
| 2 thermal_anomaly | 24 | 1 | 14 | 14 | 13 | 0 | 10 |
| 3 small_slow_leak | 36 | 5 | 23 | 23 | 18 | 0 | 13 |
| 4 abnormal_pressure_behaviour | 24 | 14 | 20 | 20 | 6 | 0 | 4 |
| 5 containment_anomaly | 20 | 20 | 18 | 20 | 0 | 2 | 0 |
| 6 structural_concern | 12 | 0 | 6 | 6 | 6 | 0 | 6 |
| -1 unknown_anomaly (composite) | 24 | 6 | 20 | 20 | 14 | 0 | 4 |
| **all classes (rows above)** | 128 | 58 | 111 | 115 | 57 | 4 | 37 |

## 4. Diagnosis (decision at the first alert; time to the first CORRECT alert-level diagnosis)

Static alarms and the classical baselines give no diagnosis: for them 'time to correct diagnosis' is never. A composite (two simultaneous faults) is not a trained class: the correct answer is the open-set 'unknown pattern'.

| class | episodes alerted | correct class at first alert | median time to correct diagnosis h (n) | median kg released before correct diagnosis |
|---|---|---|---|---|
| -1 unknown_anomaly (composite) | 24 | 2/24 | 72.8 (7) | 0.00 |
| 1 sensor_fault | 12 | 11/12 | 0.3 (12) | 0.00 |
| 2 thermal_anomaly | 24 | 20/24 | 15.8 (24) | 0.00 |
| 3 small_slow_leak | 32 | 27/32 | 1.3 (30) | 2.39 |
| 4 abnormal_pressure_behaviour | 24 | 19/24 | 4.1 (24) | 0.00 |
| 5 containment_anomaly | 20 | 13/20 | 0.0 (20) | 0.00 |
| 6 structural_concern | 12 | 9/12 | 32.3 (11) | 0.00 |

Confusion matrix at the first alert decision (rows true, columns decided):

| true \ decided | healthy | sensor | thermal | leak | pressure | contain. | struct. | unknown |
|---|---|---|---|---|---|---|---|---|
| 1 sensor | 0 | 11 | 0 | 0 | 1 | 0 | 0 | 0 |
| 2 thermal | 0 | 1 | 20 | 2 | 1 | 0 | 0 | 0 |
| 3 leak | 0 | 2 | 0 | 27 | 1 | 0 | 1 | 1 |
| 4 pressure | 0 | 1 | 3 | 0 | 19 | 0 | 1 | 0 |
| 5 contain. | 0 | 0 | 0 | 4 | 1 | 13 | 0 | 2 |
| 6 struct. | 0 | 0 | 3 | 0 | 0 | 0 | 9 | 0 |
| composite | 0 | 1 | 3 | 16 | 0 | 0 | 2 | 2 |

Overall accuracy over known-class episodes alerted: 99/124. Open-set: composites answered 'unknown pattern': 2/24. Composites whose decided class is one of their two real components: 17/24 (partial credit; the agent has no novelty detector: an isolation forest on the tool features separated composites from single faults at AUC 0.58, i.e. almost chance, so T8 was not built).

## 4b. Leaks and containment: class, size and advice in the first half hour after the first alert

The static alarms (gas detector) fire within about a minute of a large leak, so the agent cannot be earlier; the target is a correct class, a leak-size estimate and isolation advice in the same minutes. Decisions are made at the trigger tick and re-made at +10 and +30 min. True rate = the twin's leak mass flow at that moment (evaluation only).

| group | n alerted | correct class at first alert | correct class at +30 min | median est/true rate at +30 min (n) | est within a factor 2 at +30 min | median time to a factor-2 estimate, min (n) | isolation advice by +30 min |
|---|---|---|---|---|---|---|---|
| 3 leak 0.5mm | 6 | 6/6 | 6/6 | 0.96 (6) | 4/6 | 0 (6) | 4/6 |
| 3 leak 1mm | 6 | 5/6 | 6/6 | 0.85 (5) | 5/6 | 13 (6) | 5/6 |
| 5 containment_anomaly | 20 | 13/20 | 20/20 | 0.84 (19) | 17/20 | 11 (18) | 20/20 |

## 5. Investigation effort

Per investigated event (first decision): mean 5.0 tool calls (max 8), mean tool runtime 133 ms (95th percentile 391 ms, max 467 ms), over 575 events.
Tool runtime is the compute time of the tools; the always-on monitor series are vectorised and cost ~2 s per 14-day unit in total.

## 6. Forecast error

Leak cases: kg released in the 6 h after the first alert, forecast (unchecked, no refill, isothermal pressure decay) vs the twin's actual leaked mass. The forecast ignores compressor refills that keep the pressure (and the leak rate) higher, so it is a lower bound when the vessel is topped up.

n = 28; median forecast/actual = 0.60 (IQR 0.32-1.28); median absolute error 62.01 kg; actual inside the forecast interval in 29 % of cases.

Pressure-rise cases: time to PAH forecast at the first alert-time forecast vs the time the true pressure actually crossed PAH:

n = 10; median absolute error 0.02 h; median forecast 0.21 h vs actual 0.26 h; actual inside interval 10 %.

## 7. Sensor faults by subtype

The dataset's sensor-fault episodes are all spike faults on the gas-temperature probe (12 dev episodes). **Episodes of subtle slow drift (0.5-2 % FS over days): 0.** The T5 drift estimator is therefore not evaluated; stopping here as instructed (no regeneration without approval).

