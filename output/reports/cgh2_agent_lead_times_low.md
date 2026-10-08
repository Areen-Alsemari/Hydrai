# Paired lead times of the tool agent (low): when is it EARLIER, at what false-alarm cost

Lead = other detector's first alarm - the agent's first alarm (hours); positive = the agent warned earlier. Only episodes where both fired count in the median; the counts of agent-only / other-only / neither show what a median would hide. Intervals: 95 % bootstrap over episodes. The cost is each detector's realized healthy false alarms per week on the same exposure: static_A 0.00, roc 0.00, ewma 1.28, cusum 1.25, inv 0.17, learned 1.70, agent_alert 2.72. 'Floor' = median first-observable time after onset (ideal-observer bound).

### 1 sensor_fault (n = 3, floor 0.0 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 3 | 0 | 0 | 0 | +0.0 (+0.0 to +0.0) |
| best classical (roc) | 2 | 1 | 0 | 0 | +48.9 (+25.6 to +72.2) |
| single learned model | 3 | 0 | 0 | 0 | +1.8 (+1.2 to +2.1) |

### 2 thermal_anomaly (n = 6, floor 2.9 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 2 | 4 | 0 | 0 | +35.4 (+18.4 to +52.5) |
| best classical (inv) | 1 | 5 | 0 | 0 | +57.6 (+57.6 to +57.6) |
| single learned model | 6 | 0 | 0 | 0 | -3.8 (-121.5 to +58.7) |

### 3 leak 0.25mm (n = 3, floor 0.7 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 0 | 3 | 0 | 0 | - |
| best classical (inv) | 3 | 0 | 0 | 0 | +0.9 (-8.0 to +38.8) |
| single learned model | 3 | 0 | 0 | 0 | -0.8 (-2.8 to +4.7) |

### 3 leak 1mm (n = 3, floor 0.0 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 0 | 3 | 0 | 0 | - |
| best classical (roc) | 0 | 3 | 0 | 0 | - |
| single learned model | 3 | 0 | 0 | 0 | -0.9 (-94.1 to -0.7) |

### 3 small_slow_leak (n = 9, floor 0.7 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 0 | 7 | 0 | 2 | - |
| best classical (inv) | 3 | 4 | 0 | 2 | +0.9 (-8.0 to +38.8) |
| single learned model | 7 | 0 | 2 | 0 | -0.9 (-10.9 to -0.7) |

### 3 small_slow_leak WITHOUT expected-miss (0.1-1 mm) (n = 6, floor 0.3 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 0 | 6 | 0 | 0 | - |
| best classical (inv) | 3 | 3 | 0 | 0 | +0.9 (-8.0 to +38.8) |
| single learned model | 6 | 0 | 0 | 0 | -0.8 (-48.5 to +2.0) |

### 4 abnormal_pressure_behaviour (n = 12, floor 0.2 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 9 | 2 | 0 | 1 | +0.0 (+0.0 to +0.0) |
| best classical (roc) | 3 | 8 | 0 | 1 | +0.1 (+0.1 to +0.1) |
| single learned model | 10 | 1 | 1 | 0 | +0.2 (+0.1 to +0.4) |

### 5 containment_anomaly (n = 3, floor 0.0 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 3 | 0 | 0 | 0 | +0.0 (+0.0 to +0.0) |
| best classical (roc) | 0 | 3 | 0 | 0 | - |
| single learned model | 3 | 0 | 0 | 0 | +0.1 (+0.1 to +0.2) |

### 6 structural_concern (n = 3, floor 101.7 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| best classical (roc) | 0 | 3 | 0 | 0 | - |
| single learned model | 3 | 0 | 0 | 0 | -0.4 (-88.0 to +18.8) |

### 3s leak 0.05mm (n = 3, floor 31.9 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 0 | 1 | 0 | 2 | - |
| best classical (roc) | 0 | 1 | 0 | 2 | - |
| single learned model | 1 | 0 | 2 | 0 | -10.9 (-10.9 to -10.9) |

### -1 unknown_anomaly (composite) (n = 3, floor 0.3 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 0 | 3 | 0 | 0 | - |
| best classical (inv) | 3 | 0 | 0 | 0 | +1.1 (-0.8 to +1.9) |
| single learned model | 3 | 0 | 0 | 0 | -3.5 (-3.6 to +205.8) |

