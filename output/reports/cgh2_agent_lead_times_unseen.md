# Paired lead times of the tool agent (unseen): when is it EARLIER, at what false-alarm cost

Lead = other detector's first alarm - the agent's first alarm (hours); positive = the agent warned earlier. Only episodes where both fired count in the median; the counts of agent-only / other-only / neither show what a median would hide. Intervals: 95 % bootstrap over episodes. The cost is each detector's realized healthy false alarms per week on the same exposure: static_A 0.00, roc 0.48, ewma 0.85, cusum 0.61, inv 0.25, learned 2.23, agent_alert 1.03. 'Floor' = median first-observable time after onset (ideal-observer bound).

### 1 sensor_fault (n = 6, floor 0.1 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 6 | 0 | 0 | 0 | +0.0 (-31.4 to +0.5) |
| best classical (inv) | 6 | 0 | 0 | 0 | +3.2 (-29.4 to +11.4) |
| single learned model | 4 | 2 | 0 | 0 | +1.3 (-62.2 to +1.9) |

### 2 thermal_anomaly (n = 12, floor 1.7 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 3 | 9 | 0 | 0 | +3.0 (+0.0 to +44.7) |
| best classical (cusum) | 11 | 1 | 0 | 0 | -1.2 (-9.4 to +0.4) |
| single learned model | 12 | 0 | 0 | 0 | -4.9 (-14.3 to +12.6) |

### 3 leak 0.1mm (n = 3, floor 1.8 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 0 | 3 | 0 | 0 | - |
| best classical (inv) | 3 | 0 | 0 | 0 | +0.3 (-111.1 to +16.5) |
| single learned model | 3 | 0 | 0 | 0 | -18.6 (-99.5 to +0.4) |

### 3 leak 0.25mm (n = 3, floor 0.3 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 0 | 2 | 0 | 1 | - |
| best classical (inv) | 2 | 0 | 1 | 0 | +10.4 (+4.9 to +15.8) |
| single learned model | 2 | 0 | 1 | 0 | +2.8 (-0.2 to +5.9) |

### 3 leak 0.5mm (n = 3, floor 0.0 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 0 | 3 | 0 | 0 | - |
| best classical (inv) | 3 | 0 | 0 | 0 | +5.7 (+0.5 to +22.7) |
| single learned model | 3 | 0 | 0 | 0 | -0.3 (-0.5 to -0.3) |

### 3 leak 1mm (n = 3, floor 0.0 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 2 | 0 | 1 | 0 | +0.0 (+0.0 to +0.0) |
| best classical (ewma) | 2 | 0 | 1 | 0 | +1.7 (+1.5 to +1.9) |
| single learned model | 2 | 0 | 1 | 0 | +0.2 (+0.2 to +0.2) |

### 3 small_slow_leak (n = 18, floor 1.0 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 2 | 12 | 1 | 3 | +0.0 (+0.0 to +0.0) |
| best classical (inv) | 8 | 6 | 2 | 2 | +5.3 (+0.3 to +16.5) |
| single learned model | 14 | 0 | 3 | 1 | -0.1 (-0.4 to +0.9) |

### 3 small_slow_leak WITHOUT expected-miss (0.1-1 mm) (n = 12, floor 0.1 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 2 | 8 | 1 | 1 | +0.0 (+0.0 to +0.0) |
| best classical (inv) | 8 | 2 | 1 | 1 | +5.3 (+0.3 to +16.5) |
| single learned model | 10 | 0 | 2 | 0 | -0.2 (-9.4 to +0.3) |

### 4 abnormal_pressure_behaviour (n = 12, floor 0.4 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 9 | 3 | 0 | 0 | +0.2 (+0.0 to +0.5) |
| best classical (ewma) | 12 | 0 | 0 | 0 | +0.9 (+0.4 to +4.0) |
| single learned model | 12 | 0 | 0 | 0 | +0.0 (-0.3 to +0.5) |

### 5 containment_anomaly (n = 10, floor 0.0 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 9 | 0 | 1 | 0 | +0.0 (+0.0 to +0.0) |
| best classical (ewma) | 8 | 1 | 1 | 0 | +0.3 (+0.2 to +0.5) |
| single learned model | 8 | 1 | 1 | 0 | +0.1 (+0.1 to +0.2) |

### 6 structural_concern (n = 6, floor 104.1 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| best classical (ewma) | 4 | 2 | 0 | 0 | +14.9 (-102.4 to +162.2) |
| single learned model | 6 | 0 | 0 | 0 | -25.9 (-79.5 to +4.6) |

### 3s leak 0.03mm (n = 3, floor 27.6 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 0 | 1 | 0 | 2 | - |
| best classical (ewma) | 1 | 0 | 0 | 2 | -3.0 (-3.0 to -3.0) |
| single learned model | 1 | 0 | 1 | 1 | +0.0 (+0.0 to +0.0) |

### 3s leak 0.05mm (n = 3, floor 8.8 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 0 | 3 | 0 | 0 | - |
| best classical (ewma) | 1 | 2 | 0 | 0 | -26.5 (-26.5 to -26.5) |
| single learned model | 3 | 0 | 0 | 0 | +1.6 (-9.1 to +17.6) |

### 5r rupture (50 mm) (n = 1, floor 0.0 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 1 | 0 | 0 | 0 | +0.0 (+0.0 to +0.0) |
| best classical (roc) | 0 | 1 | 0 | 0 | - |
| single learned model | 0 | 1 | 0 | 0 | - |

### -1 unknown_anomaly (composite) (n = 12, floor 0.2 h)

| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |
|---|---|---|---|---|---|
| static A | 3 | 8 | 0 | 1 | +0.0 (+0.0 to +0.0) |
| best classical (roc) | 10 | 1 | 1 | 0 | +8.5 (+0.8 to +88.9) |
| single learned model | 11 | 0 | 1 | 0 | +0.2 (-0.5 to +0.3) |

