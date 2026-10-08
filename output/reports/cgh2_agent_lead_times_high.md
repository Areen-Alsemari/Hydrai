# Paired lead times of the tool agent (high): when is it EARLIER, at what false-alarm cost

Lead = other detector's first alarm - the agent's first alarm (hours); positive = the agent warned earlier. Only episodes where both fired count in the median; the counts of agent-only / other-only / neither show what a median would hide. Intervals: 95 % bootstrap over episodes. The cost is each detector's realized healthy false alarms per week on the same exposure: static_A 0.00, roc 1.75, ewma 8.66, cusum 1.18, inv 0.15, learned 0.69, agent_alert 1.90. 'Floor' = median first-observable time after onset (ideal-observer bound).

### 1 sensor_fault (n = 3, floor 0.1 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 3 | 0 | 0 | 0 | +0.1 (+0.0 to +0.3) |
| best classical (inv) | 3 | 0 | 0 | 0 | +3.7 (+1.2 to +15.6) |
| single learned model | 3 | 0 | 0 | 0 | +0.8 (+0.5 to +1.4) |

### 2 thermal_anomaly (n = 6, floor 7.6 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 3 | 3 | 0 | 0 | +12.7 (+10.6 to +20.2) |
| best classical (ewma) | 6 | 0 | 0 | 0 | -3.2 (-13.0 to +5.8) |
| single learned model | 6 | 0 | 0 | 0 | -3.9 (-5.7 to +63.2) |

### 3 leak 0.25mm (n = 3, floor 0.3 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 0 | 3 | 0 | 0 | - |
| best classical (ewma) | 3 | 0 | 0 | 0 | -5.5 (-120.8 to +1.7) |
| single learned model | 3 | 0 | 0 | 0 | -7.7 (-115.7 to -2.3) |

### 3 leak 1mm (n = 3, floor 0.0 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 3 | 0 | 0 | 0 | +0.0 (+0.0 to +0.0) |
| best classical (ewma) | 3 | 0 | 0 | 0 | +3.6 (+2.9 to +4.3) |
| single learned model | 3 | 0 | 0 | 0 | +0.2 (+0.2 to +0.2) |

### 3 small_slow_leak (n = 9, floor 0.3 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 3 | 6 | 0 | 0 | +0.0 (+0.0 to +0.0) |
| best classical (ewma) | 9 | 0 | 0 | 0 | +1.7 (-109.0 to +4.3) |
| single learned model | 8 | 1 | 0 | 0 | -1.1 (-7.7 to +0.2) |

### 3 small_slow_leak WITHOUT expected-miss (0.1-1 mm) (n = 6, floor 0.2 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 3 | 3 | 0 | 0 | +0.0 (+0.0 to +0.0) |
| best classical (ewma) | 6 | 0 | 0 | 0 | +2.3 (-63.2 to +4.0) |
| single learned model | 6 | 0 | 0 | 0 | -1.1 (-61.7 to +0.2) |

### 4 abnormal_pressure_behaviour (n = 12, floor 5.1 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 8 | 3 | 0 | 1 | +0.1 (+0.0 to +0.4) |
| best classical (ewma) | 11 | 0 | 0 | 1 | +1.4 (-0.2 to +12.6) |
| single learned model | 11 | 0 | 0 | 1 | +0.2 (-0.2 to +0.9) |

### 5 containment_anomaly (n = 3, floor 0.0 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 3 | 0 | 0 | 0 | +0.0 (+0.0 to +0.0) |
| best classical (roc) | 3 | 0 | 0 | 0 | +0.3 (+0.3 to +0.3) |
| single learned model | 3 | 0 | 0 | 0 | +0.1 (+0.1 to +0.2) |

### 6 structural_concern (n = 3, floor 42.4 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| best classical (ewma) | 3 | 0 | 0 | 0 | -1.6 (-24.6 to +8.4) |
| single learned model | 3 | 0 | 0 | 0 | +9.6 (+8.0 to +23.9) |

### 3s leak 0.05mm (n = 3, floor 12.2 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 0 | 3 | 0 | 0 | - |
| best classical (ewma) | 3 | 0 | 0 | 0 | -29.1 (-109.0 to +39.4) |
| single learned model | 2 | 1 | 0 | 0 | +23.6 (-2.6 to +49.9) |

### -1 unknown_anomaly (composite) (n = 3, floor 0.2 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 0 | 3 | 0 | 0 | - |
| best classical (ewma) | 3 | 0 | 0 | 0 | +3.5 (+1.8 to +3.8) |
| single learned model | 3 | 0 | 0 | 0 | -0.8 (-2.0 to -0.0) |

