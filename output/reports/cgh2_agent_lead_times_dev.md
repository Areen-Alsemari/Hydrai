# Paired lead times of the tool agent (dev): when is it EARLIER, at what false-alarm cost

Lead = other detector's first alarm - the agent's first alarm (hours); positive = the agent warned earlier. Only episodes where both fired count in the median; the counts of agent-only / other-only / neither show what a median would hide. Intervals: 95 % bootstrap over episodes. The cost is each detector's realized healthy false alarms per week on the same exposure: static_A 0.00, roc 0.87, ewma 1.00, cusum 0.83, inv 0.23, learned 0.46, agent_alert 0.66. 'Floor' = median first-observable time after onset (ideal-observer bound).

### 1 sensor_fault (n = 12, floor 0.1 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 10 | 0 | 2 | 0 | +0.0 (+0.0 to +0.4) |
| best classical (cusum) | 10 | 0 | 2 | 0 | +4.0 (+2.5 to +6.3) |
| single learned model | 10 | 0 | 2 | 0 | +1.6 (+1.3 to +2.6) |

### 2 thermal_anomaly (n = 24, floor 1.7 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 6 | 18 | 0 | 0 | +38.6 (+8.2 to +84.5) |
| best classical (cusum) | 22 | 2 | 0 | 0 | +0.9 (-1.0 to +1.6) |
| single learned model | 22 | 2 | 0 | 0 | +0.7 (-1.3 to +8.3) |

### 3 leak 0.1mm (n = 6, floor 2.4 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 0 | 6 | 0 | 0 | - |
| best classical (ewma) | 5 | 1 | 0 | 0 | +7.3 (-20.7 to +87.6) |
| single learned model | 3 | 3 | 0 | 0 | -5.5 (-71.7 to +70.3) |

### 3 leak 0.25mm (n = 6, floor 0.3 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 0 | 6 | 0 | 0 | - |
| best classical (inv) | 5 | 1 | 0 | 0 | +1.9 (-184.5 to +6.1) |
| single learned model | 6 | 0 | 0 | 0 | +1.0 (-101.2 to +10.2) |

### 3 leak 0.5mm (n = 6, floor 0.0 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 0 | 6 | 0 | 0 | - |
| best classical (inv) | 5 | 1 | 0 | 0 | +1.1 (+1.0 to +13.3) |
| single learned model | 6 | 0 | 0 | 0 | -0.1 (-0.2 to +0.1) |

### 3 leak 1mm (n = 6, floor 0.0 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 5 | 0 | 1 | 0 | +0.0 (+0.0 to +0.0) |
| best classical (ewma) | 5 | 0 | 0 | 1 | +1.6 (+0.9 to +2.3) |
| single learned model | 5 | 0 | 0 | 1 | +0.2 (+0.1 to +0.3) |

### 3 small_slow_leak (n = 36, floor 1.2 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 5 | 26 | 1 | 4 | +0.0 (+0.0 to +0.0) |
| best classical (inv) | 17 | 14 | 2 | 3 | +1.9 (+0.6 to +13.3) |
| single learned model | 21 | 10 | 0 | 5 | +0.1 (-0.3 to +0.2) |

### 3 small_slow_leak WITHOUT expected-miss (0.1-1 mm) (n = 24, floor 0.2 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 5 | 18 | 1 | 0 | +0.0 (+0.0 to +0.0) |
| best classical (inv) | 16 | 7 | 0 | 1 | +1.5 (+0.6 to +10.2) |
| single learned model | 20 | 3 | 0 | 1 | +0.1 (-0.2 to +0.2) |

### 4 abnormal_pressure_behaviour (n = 24, floor 2.1 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 18 | 5 | 0 | 1 | +0.1 (+0.0 to +0.2) |
| best classical (ewma) | 23 | 0 | 1 | 0 | +0.9 (+0.1 to +1.5) |
| single learned model | 23 | 0 | 1 | 0 | +0.5 (+0.0 to +0.9) |

### 5 containment_anomaly (n = 20, floor 0.0 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 18 | 0 | 2 | 0 | +0.0 (+0.0 to +0.0) |
| best classical (ewma) | 17 | 1 | 0 | 2 | +0.2 (+0.2 to +0.3) |
| single learned model | 18 | 0 | 0 | 2 | +0.2 (+0.2 to +0.2) |

### 6 structural_concern (n = 12, floor 91.1 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| best classical (cusum) | 7 | 4 | 1 | 0 | +0.8 (-34.0 to +75.6) |
| single learned model | 11 | 0 | 1 | 0 | +10.4 (-3.9 to +48.5) |

### 3s leak 0.03mm (n = 6, floor 44.1 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 0 | 5 | 0 | 1 | - |
| best classical (cusum) | 3 | 2 | 0 | 1 | -15.9 (-87.6 to +104.7) |
| single learned model | 1 | 4 | 0 | 1 | +201.1 (+201.1 to +201.1) |

### 3s leak 0.05mm (n = 6, floor 13.4 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 0 | 3 | 0 | 3 | - |
| best classical (inv) | 1 | 2 | 2 | 1 | +16.8 (+16.8 to +16.8) |
| single learned model | 0 | 3 | 0 | 3 | - |

### 5r rupture (50 mm) (n = 2, floor 0.0 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 0 | 0 | 2 | 0 | - |
| best classical (roc) | 0 | 0 | 0 | 2 | - |
| single learned model | 0 | 0 | 0 | 2 | - |

### -1 unknown_anomaly (composite) (n = 24, floor 0.2 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 6 | 18 | 0 | 0 | +0.0 (+0.0 to +0.0) |
| best classical (inv) | 16 | 8 | 0 | 0 | +5.8 (+3.3 to +11.5) |
| single learned model | 24 | 0 | 0 | 0 | +0.2 (-0.3 to +0.3) |

