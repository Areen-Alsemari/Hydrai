# CGH2 agent - checkpoint 1: detected within 24 h of onset (dev leave-one-module-out, medium class)

Budget 1 false alarm per week. Cells: k/n and the median delay in hours among those detected within 24 h. NULL (chance on healthy episodes, within 24 h): roc 3 %, ewma 9 %, cusum 13 %, inv 1 %, learned 6 %, learned_noH2 4 %. learned_noH2 = the learned layer with the hydrogen-detector features removed (the leak-to-detector coupling is a placeholder). Static has no low-pressure alarm and no strain alarm. PROVISIONAL limits; reference configuration, not a verified Saudi system.

| group | n | floor h | static | roc | ewma | cusum | inv | learned | learned_noH2 |
|---|---|---|---|---|---|---|---|---|---|
| 1 sensor_fault | 12 | 0.1 | 12/12 (0.3 h) | 5/12 (4.7 h) | 11/12 (4.0 h) | 12/12 (4.5 h) | 11/12 (4.6 h) | 12/12 (1.8 h) | 12/12 (1.9 h) |
| 2 thermal_anomaly | 24 | 1.7 | 1/24 (15.8 h) | 11/24 (14.5 h) | 10/24 (13.1 h) | 12/24 (14.2 h) | 2/24 (17.9 h) | 15/24 (11.3 h) | 18/24 (11.2 h) |
| 3 leak 0.03mm (stress) | 6 | 44.1 | 0/6 | 0/6 | 1/6 (16.6 h) | 1/6 (4.3 h) | 0/6 | 0/6 | 0/6 |
| 3 leak 0.05mm (stress) | 6 | 13.4 | 0/6 | 1/6 (9.3 h) | 1/6 (23.6 h) | 0/6 | 1/6 (21.4 h) | 0/6 | 1/6 (12.0 h) |
| 3 leak 0.1mm | 6 | 2.4 | 0/6 | 0/6 | 2/6 (13.0 h) | 1/6 (9.8 h) | 1/6 (20.7 h) | 1/6 (0.6 h) | 1/6 (10.0 h) |
| 3 leak 0.25mm | 6 | 0.3 | 0/6 | 0/6 | 0/6 | 0/6 | 5/6 (5.0 h) | 6/6 (6.0 h) | 6/6 (6.9 h) |
| 3 leak 0.5mm | 6 | 0.0 | 0/6 | 0/6 | 0/6 | 0/6 | 5/6 (1.4 h) | 6/6 (0.4 h) | 5/6 (2.7 h) |
| 3 leak 1mm | 6 | 0.0 | 5/6 (0.0 h) | 1/6 (1.2 h) | 5/6 (1.6 h) | 4/6 (3.0 h) | 2/6 (0.7 h) | 5/6 (0.3 h) | 5/6 (0.4 h) |
| 3 leaks 0.1-1 mm only | 24 | 0.2 | 5/24 (0.0 h) | 1/24 (1.2 h) | 7/24 (2.0 h) | 5/24 (3.8 h) | 13/24 (2.6 h) | 18/24 (0.4 h) | 17/24 (2.7 h) |
| 3 small_slow_leak | 36 | 1.2 | 5/36 (0.0 h) | 2/36 (5.3 h) | 9/36 (2.3 h) | 6/36 (4.0 h) | 14/36 (3.8 h) | 18/36 (0.4 h) | 18/36 (2.7 h) |
| 4 abnormal_pressure | 24 | 2.1 | 14/24 (6.8 h) | 8/24 (0.7 h) | 14/24 (5.7 h) | 12/24 (0.5 h) | 0/24 | 20/24 (5.4 h) | 20/24 (4.6 h) |
| 5 containment | 20 | 0.0 | 20/20 (0.0 h) | 17/20 (0.3 h) | 17/20 (0.2 h) | 16/20 (0.4 h) | 0/20 | 18/20 (0.2 h) | 18/20 (0.2 h) |
| 6 structural | 12 | 91.1 | no alarm defined | 2/12 (17.7 h) | 1/12 (10.5 h) | 4/12 (11.2 h) | 0/12 | 4/12 (12.4 h) | 3/12 (9.6 h) |
| -1 unknown | 24 | 0.2 | 6/24 (0.0 h) | 9/24 (1.3 h) | 11/24 (1.0 h) | 10/24 (1.5 h) | 12/24 (5.4 h) | 19/24 (0.4 h) | 21/24 (3.0 h) |
