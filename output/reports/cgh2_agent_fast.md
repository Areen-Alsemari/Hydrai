# CGH2 agent - fast layer (1 s), dev leave-one-module-out

Reference configuration, not a verified Saudi system. Limits (largest healthy 30 s pressure drop as a fraction of MOP, largest healthy 10 s hydrogen rise) come from the other dev modules' healthy 1 s data; margin 1.5x. The 1 s layer covers fills, compressor transitions and events only.

| class | episodes with 1 s rows after onset | detected by a fast event | median delay s | event types |
|---|---|---|---|---|
| -1 unknown_anomaly | 24/24 | 6/24 | 107 | {'detector': 6} |
| 1 sensor_fault | 12/12 | 0/12 | - | - |
| 2 thermal_anomaly | 24/24 | 2/24 | 397092 | {'overpressure': 2} |
| 3 small_slow_leak [0.1-0.5 mm] | 18/18 | 3/18 | 185942 | {'detector': 2, 'collapse': 1} |
| 3 small_slow_leak [1 mm] | 6/6 | 6/6 | 81 | {'detector': 6} |
| 3 small_slow_leak [stress 0.03-0.05 mm] | 12/12 | 0/12 | - | - |
| 4 abnormal_pressure_behaviour [blocked_relief] | 6/6 | 5/6 | 69631 | {'overpressure': 5} |
| 4 abnormal_pressure_behaviour [compressor_overrun] | 6/6 | 6/6 | 62132 | {'overpressure': 6} |
| 4 abnormal_pressure_behaviour [fire] | 6/6 | 6/6 | 2287 | {'overpressure': 6} |
| 4 abnormal_pressure_behaviour [stuck_open] | 6/6 | 0/6 | - | - |
| 5 containment_anomaly | 18/18 | 18/18 | 81 | {'detector': 18} |
| 5r rupture (50 mm) | 2/2 | 2/2 | 27 | {'detector': 2} |
| 6 structural_concern | 12/12 | 0/12 | - | - |

Healthy 1 s data scored: 399.2 h recorded; fast events raised there (leave-one-module-out limits): {'detector': 0, 'relief': 0, 'collapse': 0, 'rupture': 0, 'overpressure': 2} -> 0.0050 per recorded healthy hour.

Healthy limits by held-out module (largest healthy 30 s drop / MOP, largest healthy 10 s hydrogen rise in %LFL):

- M01: drop 0.0140, rise 0.4
- M02: drop 0.0140, rise 0.4
- M03: drop 0.0140, rise 0.4
- M04: drop 0.0140, rise 0.4
- M05: drop 0.0140, rise 0.4
- M06: drop 0.0140, rise 0.2
