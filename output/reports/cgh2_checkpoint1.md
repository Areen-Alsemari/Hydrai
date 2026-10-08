# CGH2 agent - checkpoint 1 (dev leave-one-module-out, medium class)

Reference configuration, not a verified Saudi system. PROVISIONAL: static-alarm limits are PAH 1.02 x MOP, PAHH 1.05 x MOP (Addendum 1), gas temperature 85/100 C (JUDGE) and hydrogen 25/50 %LFL (INL); no real Saudi alarm settings are public. The static baseline has NO low-pressure alarm (see cgh2_register_diff.md).

Thresholds of every detector are set on healthy dev units only (classical: normal episodes + commissioning of the training modules; learned: out-of-fold scores of the training modules' normal episodes). Unseen and OOD are untouched. 'delay' = first alarm event at/after onset; 'floor' = first observable deviation of the paired healthy twin (an ideal-observer bound, k = 3 sigma). Intervals are 95 % bootstrap over episodes.

## Table 1. Per-class results at a false-alarm budget of 1/wk

Realized false alarms per week on the scored healthy exposure (normal episodes + pre-onset time):

| detector | static | roc | ewma | cusum | inv | learned | learned_noH2 |
|---|---|---|---|---|---|---|---|
| false alarms / week | 0.00 | 0.87 | 1.00 | 0.83 | 0.23 | 0.46 | 0.56 |
| NULL: healthy episodes, a pseudo-onset on day 3-5: 'detected' by chance (any time) | 0 % | 67 % | 72 % | 53 % | 39 % | 25 % | 48 % |
| NULL: ... within 24 h | 0 % | 3 % | 9 % | 13 % | 1 % | 6 % | 4 % |
| NULL: ... within 48 h | 0 % | 13 % | 16 % | 16 % | 6 % | 9 % | 7 % |

**Read the detection columns against the NULL rows.** A detector with about 1 false alarm per week 'detects' a pseudo-fault on a healthy tank in the 'any time' row's share of cases within the ~10 days left in the episode, so a detection delayed by days is indistinguishable from chance. 'Detected within 24 h' is the column to trust.

Detection = k/n (95 % CI); 'after floor' = median delay after the first-observable time, hours (negative = alarm before the ideal-observer floor); lead = median over episodes where both fire (n), hours, positive = the learned layer / this detector alarmed EARLIER.

### 1 sensor_fault  (n = 12; floor: first observable 0.1 h after onset for 12/12)

| detector | detected (95 % CI) | detected within 24 h | median delay after onset h (IQR) | median delay after floor h | lead vs static h (n) | lead vs best classical (ewma) h (n) |
|---|---|---|---|---|---|---|
| static | 12/12 (1.00-1.00) | 12/12 | 0.3 (0.1-1.2) | 0.1 | - | - |
| roc | 12/12 (1.00-1.00) | 5/12 | 35.3 (6.6-56.7) | 35.1 | -28.1 (12) | -21.7 (12) |
| ewma | 12/12 (1.00-1.00) | 11/12 | 4.3 (2.7-7.5) | 4.2 | -3.5 (12) | - |
| cusum | 12/12 (1.00-1.00) | 12/12 | 4.5 (3.4-5.7) | 4.4 | -3.7 (12) | -0.0 (12) |
| inv | 12/12 (1.00-1.00) | 11/12 | 5.4 (3.3-9.4) | 5.2 | -5.0 (12) | -1.4 (12) |
| learned | 12/12 (1.00-1.00) | 12/12 | 1.8 (1.6-2.8) | 1.8 | -1.3 (12) | 2.0 (12) |
| learned_noH2 | 12/12 (1.00-1.00) | 12/12 | 1.9 (1.5-2.9) | 1.8 | -1.3 (12) | 1.7 (12) |

### 2 thermal_anomaly  (n = 24; floor: first observable 1.7 h after onset for 24/24)

| detector | detected (95 % CI) | detected within 24 h | median delay after onset h (IQR) | median delay after floor h | lead vs static h (n) | lead vs best classical (cusum) h (n) |
|---|---|---|---|---|---|---|
| static | 6/24 (0.08-0.42) | 1/24 | 47.4 (25.1-82.9) | 46.2 | - | - |
| roc | 21/24 (0.75-1.00) | 11/24 | 18.0 (14.5-45.8) | 10.6 | 0.1 (6) | 0.5 (19) |
| ewma | 22/24 (0.79-1.00) | 10/24 | 28.9 (13.8-75.3) | 20.1 | 14.6 (6) | 0.2 (20) |
| cusum | 22/24 (0.79-1.00) | 12/24 | 20.6 (14.1-34.4) | 14.9 | 11.3 (5) | - |
| inv | 5/24 (0.08-0.38) | 2/24 | 63.4 (20.2-63.7) | 49.6 | -50.9 (2) | -4.0 (4) |
| learned | 22/24 (0.79-1.00) | 15/24 | 12.2 (10.8-34.0) | 11.4 | 42.6 (6) | -0.6 (20) |
| learned_noH2 | 24/24 (1.00-1.00) | 18/24 | 11.9 (9.7-18.8) | 9.0 | 43.0 (6) | 1.1 (22) |

### 3 leak 0.1mm  (n = 6; floor: first observable 2.4 h after onset for 6/6)

| detector | detected (95 % CI) | detected within 24 h | median delay after onset h (IQR) | median delay after floor h | lead vs static h (n) | lead vs best classical (ewma) h (n) |
|---|---|---|---|---|---|---|
| static | 0/6 (0.00-0.00) | 0/6 | - (-) | - | - | - |
| roc | 4/6 (0.33-1.00) | 0/6 | 73.0 (44.2-102.7) | 70.2 | - | -1.2 (3) |
| ewma | 5/6 (0.50-1.00) | 2/6 | 43.8 (13.4-92.0) | 41.0 | - | - |
| cusum | 2/6 (0.00-0.67) | 1/6 | 52.3 (31.0-73.5) | 49.7 | - | 15.6 (2) |
| inv | 4/6 (0.33-1.00) | 1/6 | 68.8 (54.0-79.9) | 66.4 | - | -60.1 (3) |
| learned | 3/6 (0.17-0.83) | 1/6 | 35.4 (18.0-55.0) | 33.3 | - | 17.3 (3) |
| learned_noH2 | 5/6 (0.50-1.00) | 1/6 | 44.7 (28.2-46.4) | 41.9 | - | 7.7 (4) |

### 3 leak 0.25mm  (n = 6; floor: first observable 0.3 h after onset for 6/6)

| detector | detected (95 % CI) | detected within 24 h | median delay after onset h (IQR) | median delay after floor h | lead vs static h (n) | lead vs best classical (inv) h (n) |
|---|---|---|---|---|---|---|
| static | 0/6 (0.00-0.00) | 0/6 | - (-) | - | - | - |
| roc | 4/6 (0.33-1.00) | 0/6 | 108.5 (94.6-112.2) | 108.2 | - | -92.8 (3) |
| ewma | 4/6 (0.33-1.00) | 0/6 | 102.6 (85.6-112.4) | 102.3 | - | -91.6 (3) |
| cusum | 4/6 (0.33-1.00) | 0/6 | 103.0 (85.7-113.0) | 102.7 | - | -91.8 (3) |
| inv | 5/6 (0.50-1.00) | 5/6 | 5.0 (2.6-6.8) | 4.6 | - | - |
| learned | 6/6 (1.00-1.00) | 6/6 | 6.0 (1.5-7.4) | 5.6 | - | 2.2 (5) |
| learned_noH2 | 6/6 (1.00-1.00) | 6/6 | 6.9 (4.7-11.0) | 6.5 | - | 0.7 (5) |

### 3 leak 0.5mm  (n = 6; floor: first observable 0.0 h after onset for 6/6)

| detector | detected (95 % CI) | detected within 24 h | median delay after onset h (IQR) | median delay after floor h | lead vs static h (n) | lead vs best classical (inv) h (n) |
|---|---|---|---|---|---|---|
| static | 0/6 (0.00-0.00) | 0/6 | - (-) | - | - | - |
| roc | 3/6 (0.17-0.83) | 0/6 | 100.6 (63.3-159.2) | 100.5 | - | -86.4 (3) |
| ewma | 5/6 (0.50-1.00) | 0/6 | 100.4 (76.7-183.4) | 100.3 | - | -86.2 (5) |
| cusum | 5/6 (0.50-1.00) | 0/6 | 160.7 (100.9-171.5) | 160.7 | - | -164.8 (4) |
| inv | 5/6 (0.50-1.00) | 5/6 | 1.4 (1.4-11.1) | 1.4 | - | - |
| learned | 6/6 (1.00-1.00) | 6/6 | 0.4 (0.3-0.6) | 0.4 | - | 1.2 (5) |
| learned_noH2 | 5/6 (0.50-1.00) | 5/6 | 2.7 (1.5-2.8) | 2.6 | - | 3.2 (4) |

### 3 leak 1mm  (n = 6; floor: first observable 0.0 h after onset for 6/6)

| detector | detected (95 % CI) | detected within 24 h | median delay after onset h (IQR) | median delay after floor h | lead vs static h (n) | lead vs best classical (ewma) h (n) |
|---|---|---|---|---|---|---|
| static | 6/6 (1.00-1.00) | 5/6 | 0.0 (0.0-0.0) | 0.0 | - | - |
| roc | 1/6 (0.00-0.50) | 1/6 | 1.2 (1.2-1.2) | 1.1 | -1.1 (1) | -0.2 (1) |
| ewma | 5/6 (0.50-1.00) | 5/6 | 1.6 (1.3-2.0) | 1.6 | -1.6 (5) | - |
| cusum | 4/6 (0.33-1.00) | 4/6 | 3.0 (2.1-4.1) | 3.0 | -3.0 (4) | -1.4 (4) |
| inv | 2/6 (0.00-0.67) | 2/6 | 0.7 (0.7-0.7) | 0.6 | -0.6 (2) | 1.3 (2) |
| learned | 5/6 (0.50-1.00) | 5/6 | 0.3 (0.2-0.3) | 0.2 | -0.2 (5) | 1.4 (5) |
| learned_noH2 | 5/6 (0.50-1.00) | 5/6 | 0.4 (0.3-0.8) | 0.4 | -0.4 (5) | 1.0 (5) |

### 3 small_slow_leak  (n = 36; floor: first observable 1.2 h after onset for 36/36)

| detector | detected (95 % CI) | detected within 24 h | median delay after onset h (IQR) | median delay after floor h | lead vs static h (n) | lead vs best classical (ewma) h (n) |
|---|---|---|---|---|---|---|
| static | 6/36 (0.06-0.28) | 5/36 | 0.0 (0.0-0.0) | 0.0 | - | - |
| roc | 22/36 (0.44-0.75) | 2/36 | 106.7 (48.7-122.8) | 99.4 | -1.1 (1) | -0.7 (18) |
| ewma | 27/36 (0.61-0.89) | 9/36 | 76.7 (15.0-113.7) | 57.1 | -1.6 (5) | - |
| cusum | 20/36 (0.39-0.72) | 6/36 | 75.3 (8.6-113.0) | 58.1 | -3.0 (4) | -0.6 (18) |
| inv | 19/36 (0.36-0.67) | 14/36 | 11.1 (2.0-36.6) | 9.8 | -0.6 (2) | 50.3 (14) |
| learned | 21/36 (0.42-0.75) | 18/36 | 0.4 (0.3-7.0) | 0.4 | -0.2 (5) | 55.1 (17) |
| learned_noH2 | 25/36 (0.53-0.86) | 18/36 | 6.2 (1.1-28.2) | 4.6 | -0.4 (5) | 22.0 (19) |

### 3 small_slow_leak, WITHOUT expected-miss (0.1-1 mm)  (n = 24; floor: first observable 0.2 h after onset for 24/24)

| detector | detected (95 % CI) | detected within 24 h | median delay after onset h (IQR) | median delay after floor h | lead vs static h (n) | lead vs best classical (ewma) h (n) |
|---|---|---|---|---|---|---|
| static | 6/24 (0.08-0.42) | 5/24 | 0.0 (0.0-0.0) | 0.0 | - | - |
| roc | 12/24 (0.29-0.71) | 1/24 | 100.8 (44.2-108.2) | 99.4 | -1.1 (1) | -0.2 (11) |
| ewma | 19/24 (0.62-0.96) | 7/24 | 60.0 (7.4-105.5) | 59.6 | -1.6 (5) | - |
| cusum | 15/24 (0.42-0.79) | 5/24 | 94.3 (7.4-114.2) | 92.4 | -3.0 (4) | -0.7 (14) |
| inv | 16/24 (0.46-0.83) | 13/24 | 5.9 (1.4-21.4) | 5.5 | -0.6 (2) | 55.1 (13) |
| learned | 20/24 (0.67-0.96) | 18/24 | 0.4 (0.3-5.5) | 0.3 | -0.2 (5) | 55.1 (17) |
| learned_noH2 | 21/24 (0.75-1.00) | 17/24 | 4.3 (1.0-12.2) | 3.9 | -0.4 (5) | 22.0 (17) |

### 4 abnormal_pressure_behaviour  (n = 24; floor: first observable 2.1 h after onset for 24/24)

| detector | detected (95 % CI) | detected within 24 h | median delay after onset h (IQR) | median delay after floor h | lead vs static h (n) | lead vs best classical (ewma) h (n) |
|---|---|---|---|---|---|---|
| static | 18/24 (0.58-0.92) | 14/24 | 12.4 (0.6-21.0) | 0.6 | - | - |
| roc | 14/24 (0.38-0.79) | 8/24 | 19.7 (0.7-68.2) | 1.3 | -0.2 (10) | -0.4 (14) |
| ewma | 24/24 (1.00-1.00) | 14/24 | 19.5 (4.3-47.2) | 1.4 | -0.6 (18) | - |
| cusum | 22/24 (0.79-1.00) | 12/24 | 20.2 (0.5-42.3) | 3.7 | -0.8 (17) | -0.3 (22) |
| inv | 0/24 (0.00-0.00) | 0/24 | - (-) | - | - | - |
| learned | 24/24 (1.00-1.00) | 20/24 | 10.4 (0.5-19.6) | 0.8 | -0.1 (18) | 0.4 (24) |
| learned_noH2 | 23/24 (0.88-1.00) | 20/24 | 5.6 (0.8-17.4) | 0.7 | 0.1 (18) | 0.8 (23) |

### 5 containment_anomaly  (n = 20; floor: first observable 0.0 h after onset for 20/20)

| detector | detected (95 % CI) | detected within 24 h | median delay after onset h (IQR) | median delay after floor h | lead vs static h (n) | lead vs best classical (ewma) h (n) |
|---|---|---|---|---|---|---|
| static | 20/20 (1.00-1.00) | 20/20 | 0.0 (0.0-0.0) | 0.0 | - | - |
| roc | 17/20 (0.70-1.00) | 17/20 | 0.3 (0.3-0.5) | 0.3 | -0.3 (17) | -0.1 (17) |
| ewma | 17/20 (0.65-1.00) | 17/20 | 0.2 (0.2-0.3) | 0.2 | -0.2 (17) | - |
| cusum | 16/20 (0.60-0.95) | 16/20 | 0.4 (0.3-0.4) | 0.3 | -0.3 (16) | -0.1 (16) |
| inv | 0/20 (0.00-0.00) | 0/20 | - (-) | - | - | - |
| learned | 18/20 (0.75-1.00) | 18/20 | 0.2 (0.2-0.2) | 0.2 | -0.2 (18) | 0.1 (17) |
| learned_noH2 | 18/20 (0.75-1.00) | 18/20 | 0.2 (0.2-0.3) | 0.2 | -0.2 (18) | 0.0 (17) |

### 6 structural_concern  (n = 12; floor: first observable 91.1 h after onset for 12/12)

| detector | detected (95 % CI) | detected within 24 h | median delay after onset h (IQR) | median delay after floor h | lead vs static h (n) | lead vs best classical (ewma) h (n) |
|---|---|---|---|---|---|---|
| static | no alarm defined | | | | | |
| roc | 8/12 (0.41-0.92) | 2/12 | 71.2 (33.5-96.4) | -0.6 | - | -1.4 (7) |
| ewma | 9/12 (0.50-1.00) | 1/12 | 75.3 (60.4-150.6) | 16.6 | - | - |
| cusum | 8/12 (0.41-0.92) | 4/12 | 22.1 (11.3-60.4) | -43.2 | - | 21.1 (5) |
| inv | 5/12 (0.17-0.67) | 0/12 | 97.8 (89.4-161.5) | 5.0 | - | 29.0 (3) |
| learned | 12/12 (1.00-1.00) | 4/12 | 43.9 (16.4-71.9) | -29.5 | - | 39.0 (9) |
| learned_noH2 | 12/12 (1.00-1.00) | 3/12 | 49.4 (25.2-74.7) | -29.9 | - | 39.0 (9) |

### 3s leak 0.03mm  (n = 6; floor: first observable 44.1 h after onset for 6/6)

| detector | detected (95 % CI) | detected within 24 h | median delay after onset h (IQR) | median delay after floor h | lead vs static h (n) | lead vs best classical (roc) h (n) |
|---|---|---|---|---|---|---|
| static | 0/6 (0.00-0.00) | 0/6 | - (-) | - | - | - |
| roc | 5/6 (0.50-1.00) | 0/6 | 158.8 (120.3-209.4) | 113.6 | - | - |
| ewma | 4/6 (0.33-1.00) | 1/6 | 94.2 (56.3-128.5) | 28.7 | - | 1.6 (3) |
| cusum | 3/6 (0.17-0.83) | 1/6 | 82.6 (43.4-137.9) | -12.9 | - | 1.7 (2) |
| inv | 0/6 (0.00-0.00) | 0/6 | - (-) | - | - | - |
| learned | 1/6 (0.00-0.50) | 0/6 | 209.8 (209.8-209.8) | 189.2 | - | -0.4 (1) |
| learned_noH2 | 2/6 (0.00-0.67) | 0/6 | 139.8 (104.7-174.8) | 108.0 | - | -0.5 (1) |

### 3s leak 0.05mm  (n = 6; floor: first observable 13.4 h after onset for 6/6)

| detector | detected (95 % CI) | detected within 24 h | median delay after onset h (IQR) | median delay after floor h | lead vs static h (n) | lead vs best classical (roc) h (n) |
|---|---|---|---|---|---|---|
| static | 0/6 (0.00-0.00) | 0/6 | - (-) | - | - | - |
| roc | 5/6 (0.50-1.00) | 1/6 | 80.2 (25.0-123.6) | 68.6 | - | - |
| ewma | 4/6 (0.33-1.00) | 1/6 | 101.1 (64.9-133.9) | 86.1 | - | 0.8 (4) |
| cusum | 2/6 (0.00-0.67) | 0/6 | 63.1 (60.5-65.6) | 49.6 | - | 60.3 (2) |
| inv | 3/6 (0.17-0.83) | 1/6 | 49.7 (35.5-105.3) | 39.4 | - | 32.2 (2) |
| learned | 0/6 (0.00-0.00) | 0/6 | - (-) | - | - | - |
| learned_noH2 | 2/6 (0.00-0.67) | 1/6 | 70.4 (41.2-99.6) | 61.1 | - | 111.6 (1) |

### 5r rupture (50 mm)  (n = 2; floor: first observable 0.0 h after onset for 2/2)

| detector | detected (95 % CI) | detected within 24 h | median delay after onset h (IQR) | median delay after floor h | lead vs static h (n) | lead vs best classical (roc) h (n) |
|---|---|---|---|---|---|---|
| static | 2/2 (1.00-1.00) | 2/2 | 0.0 (0.0-0.0) | 0.0 | - | - |
| roc | 0/2 (0.00-0.00) | 0/2 | - (-) | - | - | - |
| ewma | 0/2 (0.00-0.00) | 0/2 | - (-) | - | - | - |
| cusum | 0/2 (0.00-0.00) | 0/2 | - (-) | - | - | - |
| inv | 0/2 (0.00-0.00) | 0/2 | - (-) | - | - | - |
| learned | 0/2 (0.00-0.00) | 0/2 | - (-) | - | - | - |
| learned_noH2 | 0/2 (0.00-0.00) | 0/2 | - (-) | - | - | - |

### -1 unknown_anomaly  (n = 24; floor: first observable 0.2 h after onset for 24/24)

| detector | detected (95 % CI) | detected within 24 h | median delay after onset h (IQR) | median delay after floor h | lead vs static h (n) | lead vs best classical (ewma) h (n) |
|---|---|---|---|---|---|---|
| static | 6/24 (0.08-0.42) | 6/24 | 0.0 (0.0-0.0) | 0.0 | - | - |
| roc | 19/24 (0.62-0.96) | 9/24 | 37.2 (1.9-106.0) | 37.0 | -0.9 (5) | -0.1 (18) |
| ewma | 21/24 (0.71-1.00) | 11/24 | 18.7 (1.0-118.6) | 3.6 | -0.6 (6) | - |
| cusum | 18/24 (0.54-0.92) | 10/24 | 12.6 (1.4-92.4) | 9.6 | -1.2 (6) | -0.7 (17) |
| inv | 16/24 (0.46-0.83) | 12/24 | 6.7 (3.7-20.0) | 6.5 | - | 17.1 (13) |
| learned | 24/24 (1.00-1.00) | 19/24 | 0.4 (0.4-6.6) | 0.4 | -0.3 (6) | 3.1 (21) |
| learned_noH2 | 23/24 (0.87-1.00) | 21/24 | 3.3 (1.4-8.2) | 2.2 | -0.5 (5) | 8.0 (20) |

## Table 2 (E1). Gap analysis: delay versus the physical floor, and operating curves

Ratio = detection delay after onset / (first-observable time after onset), median over episodes detected and observable; 1.0 = at the floor, >1 = later. Operating curve = detection rate and median delay after onset (h) as the false-alarm budget loosens.

### 1 sensor_fault  (floor median 0.1 h, IQR 0.0-0.1)

| detector | ratio delay/floor (median) | 1/day: detected, delay h | 1/wk: detected, delay h | 1/4wk: detected, delay h |
|---|---|---|---|---|
| static | 2.2 (n=12) | 12/12, 0.3 | 12/12, 0.3 | 12/12, 0.3 |
| roc | 300.7 (n=12) | 12/12, 10.3 | 12/12, 35.3 | 10/12, 67.5 |
| ewma | 55.0 (n=12) | 12/12, 3.1 | 12/12, 4.3 | 12/12, 6.2 |
| cusum | 55.7 (n=12) | 12/12, 4.0 | 12/12, 4.5 | 12/12, 5.6 |
| inv | 101.0 (n=12) | 12/12, 5.4 | 12/12, 5.4 | 12/12, 6.3 |
| learned | 22.4 (n=12) | 12/12, 1.8 | 12/12, 1.8 | 11/12, 2.3 |
| learned_noH2 | 22.3 (n=12) | 12/12, 1.5 | 12/12, 1.9 | 11/12, 2.2 |

### 2 thermal_anomaly  (floor median 1.7 h, IQR 0.7-13.9)

| detector | ratio delay/floor (median) | 1/day: detected, delay h | 1/wk: detected, delay h | 1/4wk: detected, delay h |
|---|---|---|---|---|
| static | 33.7 (n=6) | 6/24, 47.4 | 6/24, 47.4 | 6/24, 47.4 |
| roc | 3.2 (n=21) | 24/24, 14.4 | 21/24, 18.0 | 17/24, 67.6 |
| ewma | 6.8 (n=22) | 24/24, 14.7 | 22/24, 28.9 | 19/24, 76.8 |
| cusum | 5.9 (n=22) | 23/24, 16.7 | 22/24, 20.6 | 23/24, 27.0 |
| inv | 30.3 (n=5) | 5/24, 63.4 | 5/24, 63.4 | 4/24, 41.9 |
| learned | 6.9 (n=22) | 22/24, 12.2 | 22/24, 12.2 | 18/24, 19.1 |
| learned_noH2 | 3.8 (n=24) | 24/24, 11.9 | 24/24, 11.9 | 19/24, 17.7 |

### 3 leak 0.1mm  (floor median 2.4 h, IQR 2.1-2.7)

| detector | ratio delay/floor (median) | 1/day: detected, delay h | 1/wk: detected, delay h | 1/4wk: detected, delay h |
|---|---|---|---|---|
| static | - | 0/6, - | 0/6, - | 0/6, - |
| roc | 26.6 (n=4) | 6/6, 19.4 | 4/6, 73.0 | 1/6, 71.3 |
| ewma | 15.6 (n=5) | 6/6, 18.7 | 5/6, 43.8 | 1/6, 46.2 |
| cusum | 21.8 (n=2) | 3/6, 16.5 | 2/6, 52.3 | 2/6, 97.4 |
| inv | 28.9 (n=4) | 4/6, 68.8 | 4/6, 68.8 | 3/6, 73.1 |
| learned | 17.5 (n=3) | 5/6, 74.7 | 3/6, 35.4 | 2/6, 106.6 |
| learned_noH2 | 15.7 (n=5) | 6/6, 30.6 | 5/6, 44.7 | 1/6, 130.8 |

### 3 leak 0.25mm  (floor median 0.3 h, IQR 0.3-0.3)

| detector | ratio delay/floor (median) | 1/day: detected, delay h | 1/wk: detected, delay h | 1/4wk: detected, delay h |
|---|---|---|---|---|
| static | - | 0/6, - | 0/6, - | 0/6, - |
| roc | 296.0 (n=4) | 6/6, 11.6 | 4/6, 108.5 | 3/6, 110.8 |
| ewma | 314.0 (n=4) | 6/6, 15.7 | 4/6, 102.6 | 2/6, 113.9 |
| cusum | 315.2 (n=4) | 4/6, 60.4 | 4/6, 103.0 | 3/6, 94.9 |
| inv | 12.8 (n=5) | 5/6, 5.0 | 5/6, 5.0 | 5/6, 5.1 |
| learned | 16.5 (n=6) | 6/6, 6.0 | 6/6, 6.0 | 6/6, 10.4 |
| learned_noH2 | 21.7 (n=6) | 6/6, 4.5 | 6/6, 6.9 | 6/6, 11.6 |

### 3 leak 0.5mm  (floor median 0.0 h, IQR 0.0-0.0)

| detector | ratio delay/floor (median) | 1/day: detected, delay h | 1/wk: detected, delay h | 1/4wk: detected, delay h |
|---|---|---|---|---|
| static | - | 0/6, - | 0/6, - | 0/6, - |
| roc | 2466.2 (n=3) | 6/6, 22.7 | 3/6, 100.6 | 3/6, 100.7 |
| ewma | 2460.8 (n=5) | 6/6, 88.4 | 5/6, 100.4 | 3/6, 158.8 |
| cusum | 3857.4 (n=5) | 5/6, 160.7 | 5/6, 160.7 | 4/6, 168.4 |
| inv | 38.7 (n=5) | 5/6, 1.4 | 5/6, 1.4 | 5/6, 1.4 |
| learned | 9.9 (n=6) | 6/6, 0.4 | 6/6, 0.4 | 6/6, 1.3 |
| learned_noH2 | 60.6 (n=5) | 5/6, 2.5 | 5/6, 2.7 | 6/6, 5.5 |

### 3 leak 1mm  (floor median 0.0 h, IQR 0.0-0.0)

| detector | ratio delay/floor (median) | 1/day: detected, delay h | 1/wk: detected, delay h | 1/4wk: detected, delay h |
|---|---|---|---|---|
| static | 1.4 (n=6) | 6/6, 0.0 | 6/6, 0.0 | 6/6, 0.0 |
| roc | 34.1 (n=1) | 6/6, 10.5 | 1/6, 1.2 | 1/6, 1.4 |
| ewma | 79.5 (n=5) | 5/6, 1.0 | 5/6, 1.6 | 4/6, 2.6 |
| cusum | 108.9 (n=4) | 4/6, 2.2 | 4/6, 3.0 | 4/6, 4.4 |
| inv | 31.5 (n=2) | 2/6, 0.7 | 2/6, 0.7 | 0/6, - |
| learned | 7.7 (n=5) | 5/6, 0.2 | 5/6, 0.3 | 5/6, 0.4 |
| learned_noH2 | 13.1 (n=5) | 5/6, 0.4 | 5/6, 0.4 | 5/6, 1.3 |

### 3 small_slow_leak  (floor median 1.2 h, IQR 0.0-12.5)

| detector | ratio delay/floor (median) | 1/day: detected, delay h | 1/wk: detected, delay h | 1/4wk: detected, delay h |
|---|---|---|---|---|
| static | 1.4 (n=6) | 6/36, 0.0 | 6/36, 0.0 | 6/36, 0.0 |
| roc | 16.8 (n=22) | 36/36, 19.2 | 22/36, 106.7 | 14/36, 113.7 |
| ewma | 39.2 (n=27) | 35/36, 19.1 | 27/36, 76.7 | 13/36, 100.4 |
| cusum | 153.3 (n=20) | 24/36, 50.6 | 20/36, 75.3 | 17/36, 68.5 |
| inv | 28.3 (n=19) | 19/36, 11.1 | 19/36, 11.1 | 16/36, 12.7 |
| learned | 10.6 (n=21) | 24/36, 0.4 | 21/36, 0.4 | 19/36, 1.4 |
| learned_noH2 | 16.5 (n=25) | 27/36, 4.4 | 25/36, 6.2 | 18/36, 7.2 |

### 3 small_slow_leak, WITHOUT expected-miss (0.1-1 mm)  (floor median 0.2 h, IQR 0.0-0.8)

| detector | ratio delay/floor (median) | 1/day: detected, delay h | 1/wk: detected, delay h | 1/4wk: detected, delay h |
|---|---|---|---|---|
| static | 1.4 (n=6) | 6/24, 0.0 | 6/24, 0.0 | 6/24, 0.0 |
| roc | 236.1 (n=12) | 24/24, 17.3 | 12/24, 100.8 | 8/24, 96.2 |
| ewma | 100.9 (n=19) | 23/24, 13.2 | 19/24, 60.0 | 10/24, 73.3 |
| cusum | 310.8 (n=15) | 16/24, 36.9 | 15/24, 94.3 | 13/24, 68.5 |
| inv | 31.8 (n=16) | 16/24, 5.9 | 16/24, 5.9 | 13/24, 6.8 |
| learned | 11.0 (n=20) | 22/24, 0.4 | 20/24, 0.4 | 19/24, 1.4 |
| learned_noH2 | 21.9 (n=21) | 22/24, 3.0 | 21/24, 4.3 | 18/24, 7.2 |

### 4 abnormal_pressure_behaviour  (floor median 2.1 h, IQR 0.0-17.8)

| detector | ratio delay/floor (median) | 1/day: detected, delay h | 1/wk: detected, delay h | 1/4wk: detected, delay h |
|---|---|---|---|---|
| static | 1.1 (n=18) | 18/24, 12.4 | 18/24, 12.4 | 18/24, 12.4 |
| roc | 16.9 (n=14) | 24/24, 11.8 | 14/24, 19.7 | 8/24, 0.7 |
| ewma | 3.6 (n=24) | 23/24, 14.7 | 24/24, 19.5 | 22/24, 19.3 |
| cusum | 5.6 (n=22) | 21/24, 19.9 | 22/24, 20.2 | 22/24, 20.9 |
| inv | - | 0/24, - | 0/24, - | 0/24, - |
| learned | 5.0 (n=24) | 24/24, 9.8 | 24/24, 10.4 | 22/24, 14.4 |
| learned_noH2 | 1.2 (n=23) | 23/24, 5.4 | 23/24, 5.6 | 23/24, 9.2 |

### 5 containment_anomaly  (floor median 0.0 h, IQR 0.0-0.0)

| detector | ratio delay/floor (median) | 1/day: detected, delay h | 1/wk: detected, delay h | 1/4wk: detected, delay h |
|---|---|---|---|---|
| static | 1.0 (n=20) | 20/20, 0.0 | 20/20, 0.0 | 20/20, 0.0 |
| roc | 16.5 (n=17) | 18/20, 0.3 | 17/20, 0.3 | 17/20, 0.4 |
| ewma | 12.9 (n=17) | 18/20, 0.2 | 17/20, 0.2 | 17/20, 0.3 |
| cusum | 18.7 (n=16) | 15/20, 0.3 | 16/20, 0.4 | 17/20, 0.5 |
| inv | - | 0/20, - | 0/20, - | 0/20, - |
| learned | 9.8 (n=18) | 18/20, 0.2 | 18/20, 0.2 | 18/20, 0.3 |
| learned_noH2 | 11.0 (n=18) | 18/20, 0.2 | 18/20, 0.2 | 17/20, 0.3 |

### 6 structural_concern  (floor median 91.1 h, IQR 57.5-110.0)

| detector | ratio delay/floor (median) | 1/day: detected, delay h | 1/wk: detected, delay h | 1/4wk: detected, delay h |
|---|---|---|---|---|
| roc | 1.0 (n=8) | 12/12, 43.9 | 8/12, 71.2 | 2/12, 179.9 |
| ewma | 1.2 (n=9) | 12/12, 10.4 | 9/12, 75.3 | 0/12, - |
| cusum | 0.4 (n=8) | 8/12, 11.7 | 8/12, 22.1 | 5/12, 56.1 |
| inv | 1.1 (n=5) | 5/12, 97.8 | 5/12, 97.8 | 5/12, 97.9 |
| learned | 0.5 (n=12) | 12/12, 43.0 | 12/12, 43.9 | 12/12, 63.9 |
| learned_noH2 | 0.5 (n=12) | 12/12, 41.1 | 12/12, 49.4 | 12/12, 63.8 |

### 3s leak 0.03mm  (floor median 44.1 h, IQR 37.4-71.1)

| detector | ratio delay/floor (median) | 1/day: detected, delay h | 1/wk: detected, delay h | 1/4wk: detected, delay h |
|---|---|---|---|---|
| static | - | 0/6, - | 0/6, - | 0/6, - |
| roc | 3.0 (n=5) | 6/6, 20.1 | 5/6, 158.8 | 5/6, 203.1 |
| ewma | 1.6 (n=4) | 6/6, 24.2 | 4/6, 94.2 | 3/6, 153.2 |
| cusum | 0.9 (n=3) | 4/6, 27.0 | 3/6, 82.6 | 2/6, 100.5 |
| inv | - | 0/6, - | 0/6, - | 0/6, - |
| learned | 10.2 (n=1) | 1/6, 209.7 | 1/6, 209.8 | 0/6, - |
| learned_noH2 | 5.9 (n=2) | 3/6, 166.7 | 2/6, 139.8 | 0/6, - |

### 3s leak 0.05mm  (floor median 13.4 h, IQR 10.6-18.3)

| detector | ratio delay/floor (median) | 1/day: detected, delay h | 1/wk: detected, delay h | 1/4wk: detected, delay h |
|---|---|---|---|---|
| static | - | 0/6, - | 0/6, - | 0/6, - |
| roc | 6.9 (n=5) | 6/6, 21.8 | 5/6, 80.2 | 1/6, 58.7 |
| ewma | 7.2 (n=4) | 6/6, 20.7 | 4/6, 101.1 | 0/6, - |
| cusum | 4.8 (n=2) | 4/6, 79.2 | 2/6, 63.1 | 2/6, 66.1 |
| inv | 4.8 (n=3) | 3/6, 49.7 | 3/6, 49.7 | 3/6, 49.7 |
| learned | - | 1/6, 50.9 | 0/6, - | 0/6, - |
| learned_noH2 | 7.0 (n=2) | 2/6, 40.6 | 2/6, 70.4 | 0/6, - |

### 5r rupture (50 mm)  (floor median 0.0 h, IQR 0.0-0.0)

| detector | ratio delay/floor (median) | 1/day: detected, delay h | 1/wk: detected, delay h | 1/4wk: detected, delay h |
|---|---|---|---|---|
| static | 1.0 (n=2) | 2/2, 0.0 | 2/2, 0.0 | 2/2, 0.0 |
| roc | - | 1/2, 0.0 | 0/2, - | 0/2, - |
| ewma | - | 1/2, 0.0 | 0/2, - | 0/2, - |
| cusum | - | 0/2, - | 0/2, - | 0/2, - |
| inv | - | 0/2, - | 0/2, - | 0/2, - |
| learned | - | 0/2, - | 0/2, - | 0/2, - |
| learned_noH2 | - | 0/2, - | 0/2, - | 0/2, - |

### -1 unknown_anomaly  (floor median 0.2 h, IQR 0.0-0.5)

| detector | ratio delay/floor (median) | 1/day: detected, delay h | 1/wk: detected, delay h | 1/4wk: detected, delay h |
|---|---|---|---|---|
| static | 1.0 (n=6) | 6/24, 0.0 | 6/24, 0.0 | 6/24, 0.0 |
| roc | 48.4 (n=19) | 23/24, 7.4 | 19/24, 37.2 | 13/24, 18.4 |
| ewma | 30.9 (n=21) | 23/24, 8.4 | 21/24, 18.7 | 15/24, 70.0 |
| cusum | 45.8 (n=18) | 17/24, 8.7 | 18/24, 12.6 | 15/24, 9.9 |
| inv | 24.5 (n=16) | 16/24, 6.7 | 16/24, 6.7 | 16/24, 6.7 |
| learned | 8.3 (n=24) | 24/24, 0.4 | 24/24, 0.4 | 24/24, 2.6 |
| learned_noH2 | 12.7 (n=23) | 23/24, 2.7 | 23/24, 3.3 | 24/24, 6.4 |

