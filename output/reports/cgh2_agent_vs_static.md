# Agent versus the static alarms and a modelled operator

Reference configuration, not a verified Saudi system. The agent is the FROZEN configuration (dev: leave-one-module-out; unseen, OOD low / high and the slow-drift set: scored once, fitted on all dev). Detection counts alarms within 72 h of onset. 'Operator' is a MODELLED operator, not a human study; its thresholds were set once on healthy dev data at 1 false alarm per week per rule and never touched again: look every 15 min: pressure-low 0.152 of MOP below the compressor start level, temperature 25.5 K above ambient, compensated inventory 0.053 of the class inventory below its start level; look every 60 min: pressure-low 0.131 of MOP below the compressor start level, temperature 23.8 K above ambient, compensated inventory 0.031 of the class inventory below its start level. The low-pressure rule lands near 70 % of MOP, i.e. close to the proposed low-pressure alarm of static B. Static B = A plus the proposed 70 % MOP low-pressure alarm. Read the false-alarm line of every section next to its lead times: an earlier alarm that costs more false alarms is not a free win.

## dev

Healthy false alarms per week (cost): static A 0.00, static B 1.26, agent alert tier 0.66, agent watch tier 0.86, operator 15 min 1.71, operator 60 min 1.66, expert operator 15 min 1.64 (healthy exposure 159.4 weeks).

### Agent vs the static alarms

Detected = first alarm within 72 h of onset. Lead in hours, positive = the agent earlier, where both fired. kg = released before detection, agent vs static A where both fired (median).

| group | n | floor h | detected: A | B | agent | vs A: both / agent only / A only / neither | lead over A, h (95 % CI) | lead over B, h | kg before detection: agent vs A | union A or agent: 24 h | 72 h | union B or agent: 24 h | 72 h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 sensor fault: spikes on the gas-temperature probe | 12 | 0.1 | 12 | 12 | 10 | 10 / 0 / 2 / 0 | +0.0 (+0.0 to +0.4; n=10) | +0.0 (+0.0 to +0.4; n=10) | 0.00 vs 0.00 | 12/12 | 12/12 | 12/12 | 12/12 |
| 2 thermal anomaly (all) | 24 | 1.7 | 4 | 14 | 21 | 4 / 17 / 0 / 3 | +17.4 (+2.9 to +55.8; n=4) | +0.1 (-1.3 to +13.5; n=13) | 0.00 vs 0.00 | 14/24 | 21/24 | 14/24 | 22/24 |
| 2 thermal: external heat | 12 | 1.2 | 4 | 7 | 11 | 4 / 7 / 0 / 1 | +17.4 (+2.9 to +55.8; n=4) | +0.1 (-5.2 to +13.5; n=7) | 0.00 vs 0.00 | 9/12 | 11/12 | 9/12 | 11/12 |
| 2 thermal: intercooler failure | 12 | 14.0 | 0 | 7 | 10 | 0 / 10 / 0 / 2 | - | +1.9 (-1.5 to +19.2; n=6) | - | 5/12 | 10/12 | 5/12 | 11/12 |
| 3 leak 0.1 mm | 6 | 2.4 | 0 | 5 | 5 | 0 / 5 / 0 / 1 | - | +15.5 (-21.2 to +35.7; n=4) | - | 4/6 | 5/6 | 5/6 | 6/6 |
| 3 leak 0.25 mm | 6 | 0.3 | 0 | 2 | 5 | 0 / 5 / 0 / 1 | - | +50.3 (n=2) | - | 5/6 | 5/6 | 5/6 | 5/6 |
| 3 leak 0.5 mm | 6 | 0.0 | 0 | 3 | 6 | 0 / 6 / 0 / 0 | - | +19.6 (+6.7 to +24.8; n=3) | - | 6/6 | 6/6 | 6/6 | 6/6 |
| 3 leak 1 mm | 6 | 0.0 | 5 | 5 | 5 | 5 / 0 / 0 / 1 | +0.0 (+0.0 to +0.0; n=5) | +0.0 (+0.0 to +0.0; n=5) | 0.06 vs 0.06 | 5/6 | 5/6 | 5/6 | 5/6 |
| 3 leaks 0.1-1 mm (all) | 24 | 0.2 | 5 | 15 | 21 | 5 / 16 / 0 / 3 | +0.0 (+0.0 to +0.0; n=5) | +6.9 (+0.0 to +24.4; n=14) | 0.06 vs 0.06 | 20/24 | 21/24 | 21/24 | 22/24 |
| 4 abnormal pressure (all) | 24 | 2.1 | 18 | 19 | 23 | 18 / 5 / 0 / 1 | +0.1 (+0.0 to +0.2; n=18) | +0.0 (+0.0 to +0.2; n=19) | 0.00 vs 0.00 | 20/24 | 23/24 | 20/24 | 23/24 |
| 4 pressure: blocked_relief | 6 | 27.9 | 6 | 6 | 6 | 6 / 0 / 0 / 0 | +0.3 (+0.0 to +16.2; n=6) | +0.3 (+0.0 to +16.1; n=6) | 0.00 vs 0.00 | 4/6 | 6/6 | 4/6 | 6/6 |
| 4 pressure: compressor_overrun | 6 | 14.5 | 6 | 6 | 6 | 6 / 0 / 0 / 0 | +0.2 (+0.0 to +0.3; n=6) | +0.0 (-3.3 to +0.2; n=6) | 0.00 vs 0.00 | 5/6 | 6/6 | 5/6 | 6/6 |
| 4 pressure: fire | 6 | 0.0 | 6 | 6 | 6 | 6 / 0 / 0 / 0 | +0.0 (+0.0 to +0.1; n=6) | +0.0 (+0.0 to +0.1; n=6) | 0.00 vs 0.00 | 6/6 | 6/6 | 6/6 | 6/6 |
| 4 pressure: stuck_open | 6 | 0.0 | 0 | 1 | 5 | 0 / 5 / 0 / 1 | - | +22.2 (n=1) | - | 5/6 | 5/6 | 5/6 | 5/6 |
| 5 containment (all) | 18 | 0.0 | 18 | 18 | 18 | 18 / 0 / 0 / 0 | +0.0 (+0.0 to +0.0; n=18) | +0.0 (+0.0 to +0.0; n=18) | 0.00 vs 0.00 | 18/18 | 18/18 | 18/18 | 18/18 |
| 5 containment 2 mm | 6 | 0.0 | 6 | 6 | 6 | 6 / 0 / 0 / 0 | +0.0 (+0.0 to +0.0; n=6) | +0.0 (+0.0 to +0.0; n=6) | 0.00 vs 0.00 | 6/6 | 6/6 | 6/6 | 6/6 |
| 5 containment 3.5 mm | 6 | 0.0 | 6 | 6 | 6 | 6 / 0 / 0 / 0 | +0.0 (+0.0 to +0.0; n=6) | +0.0 (+0.0 to +0.0; n=6) | 0.00 vs 0.00 | 6/6 | 6/6 | 6/6 | 6/6 |
| 5 containment 5 mm | 6 | 0.0 | 6 | 6 | 6 | 6 / 0 / 0 / 0 | +0.0 (+0.0 to +0.0; n=6) | +0.0 (+0.0 to +0.0; n=6) | 0.00 vs 0.00 | 6/6 | 6/6 | 6/6 | 6/6 |
| 6 structural (all) | 12 | 91.1 | 0 | 5 | 9 | 0 / 9 / 0 / 3 | - | +7.3 (-6.3 to +30.6; n=3) | - | 6/12 | 9/12 | 7/12 | 11/12 |
| 6 structural severity 0.5 | 6 | 118.2 | 0 | 3 | 4 | 0 / 4 / 0 / 2 | - | +0.5 (n=2) | - | 2/6 | 4/6 | 2/6 | 5/6 |
| 6 structural severity 1 | 6 | 48.8 | 0 | 2 | 5 | 0 / 5 / 0 / 1 | - | +30.6 (n=1) | - | 4/6 | 5/6 | 5/6 | 6/6 |
| 3s stress leak 0.03 mm (expected miss) | 6 | 44.1 | 0 | 2 | 2 | 0 / 2 / 0 / 4 | - | -3.9 (n=1) | - | 2/6 | 2/6 | 3/6 | 3/6 |
| 3s stress leak 0.05 mm (expected miss) | 6 | 13.4 | 0 | 2 | 1 | 0 / 1 / 0 / 5 | - | - | - | 1/6 | 1/6 | 3/6 | 3/6 |
| 5r rupture 50 mm | 2 | 0.0 | 2 | 0 | 0 | 0 / 0 / 2 / 0 | - | - | - | 2/2 | 2/2 | 0/2 | 0/2 |
| -1 composite (two faults) | 24 | 0.2 | 6 | 16 | 23 | 6 / 17 / 0 / 1 | +0.0 (+0.0 to +0.0; n=6) | +0.9 (+0.0 to +25.1; n=15) | 0.00 vs 0.00 | 20/24 | 23/24 | 20/24 | 24/24 |

### Agent vs the modelled operator (not a human study)

Operator: looks every 15 min (op15) or 60 min (op60), raw pressure below the working band by more than X or gas temperature more than Y above ambient (thresholds set once on healthy dev data at 1 false alarm per week per rule); 'expert' reads the temperature-compensated inventory instead of the raw pressure. Lead = operator's first alarm - agent's first alarm.

| group | n | detected: op15 | op60 | expert | agent | vs op15: both / agent only / op only / neither | lead over op15, h (95 % CI) | lead over op60, h | lead over expert, h | kg before detection: agent vs op15 | union op15 or agent: 24 h | 72 h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 sensor fault: spikes on the gas-temperature probe | 12 | 12 | 12 | 12 | 10 | 10 / 0 / 2 / 0 | +2.1 (+1.0 to +3.5; n=10) | +4.5 (+1.2 to +10.0; n=10) | +2.1 (+1.0 to +3.4; n=10) | 0.00 vs 0.00 | 12/12 | 12/12 |
| 2 thermal anomaly (all) | 24 | 23 | 23 | 23 | 21 | 20 / 1 / 3 / 0 | -0.5 (-1.4 to +0.6; n=20) | +0.9 (-0.2 to +4.3; n=20) | -0.5 (-1.4 to +0.4; n=20) | 0.00 vs 0.00 | 17/24 | 24/24 |
| 2 thermal: external heat | 12 | 12 | 12 | 12 | 11 | 11 / 0 / 1 / 0 | +0.2 (-5.8 to +1.5; n=11) | +1.1 (-5.1 to +2.1; n=11) | +0.2 (-5.8 to +1.5; n=11) | 0.00 vs 0.00 | 12/12 | 12/12 |
| 2 thermal: intercooler failure | 12 | 11 | 11 | 11 | 10 | 9 / 1 / 2 / 0 | -0.6 (-1.6 to +4.8; n=9) | +0.1 (-1.2 to +28.2; n=9) | -0.6 (-1.6 to +4.8; n=9) | 0.00 vs 0.00 | 5/12 | 12/12 |
| 3 leak 0.1 mm | 6 | 6 | 5 | 6 | 5 | 5 / 0 / 1 / 0 | +7.2 (-21.1 to +42.2; n=5) | +6.5 (+0.6 to +36.0; n=4) | +7.2 (-21.1 to +42.2; n=5) | 2.25 vs 4.78 | 5/6 | 6/6 |
| 3 leak 0.25 mm | 6 | 4 | 4 | 4 | 5 | 4 / 1 / 0 / 1 | +28.4 (+3.0 to +55.5; n=4) | +38.9 (+17.6 to +57.2; n=4) | +28.4 (+3.0 to +55.5; n=4) | 3.99 vs 63.97 | 5/6 | 5/6 |
| 3 leak 0.5 mm | 6 | 5 | 5 | 4 | 6 | 5 / 1 / 0 / 0 | +26.5 (+19.7 to +46.7; n=5) | +20.8 (+7.0 to +46.7; n=5) | +35.4 (+19.7 to +46.7; n=4) | 2.52 vs 224.71 | 6/6 | 6/6 |
| 3 leak 1 mm | 6 | 5 | 6 | 5 | 5 | 5 / 0 / 0 / 1 | +1.8 (+0.6 to +2.0; n=5) | +1.5 (+1.1 to +2.0; n=5) | +1.6 (+0.9 to +2.0; n=5) | 0.06 vs 58.55 | 5/6 | 5/6 |
| 3 leaks 0.1-1 mm (all) | 24 | 20 | 20 | 19 | 21 | 19 / 2 / 1 / 2 | +19.7 (+2.0 to +29.5; n=19) | +12.4 (+1.9 to +26.5; n=18) | +13.5 (+1.7 to +32.6; n=18) | 2.00 vs 59.15 | 21/24 | 22/24 |
| 4 abnormal pressure (all) | 24 | 18 | 19 | 18 | 23 | 18 / 5 / 0 / 1 | +0.2 (-0.0 to +0.8; n=18) | +0.7 (+0.2 to +1.3; n=19) | +0.2 (-0.1 to +0.8; n=18) | 0.00 vs 0.00 | 20/24 | 23/24 |
| 4 pressure: blocked_relief | 6 | 5 | 5 | 5 | 6 | 5 / 1 / 0 / 0 | +1.1 (+0.7 to +34.8; n=5) | +2.9 (+0.8 to +35.2; n=5) | +1.1 (+0.7 to +34.8; n=5) | 0.00 vs 0.00 | 4/6 | 6/6 |
| 4 pressure: compressor_overrun | 6 | 5 | 5 | 5 | 6 | 5 / 1 / 0 / 0 | -0.3 (-3.3 to +0.6; n=5) | -0.8 (-3.3 to +1.0; n=5) | -0.3 (-3.3 to +0.6; n=5) | 0.00 vs 0.00 | 5/6 | 6/6 |
| 4 pressure: fire | 6 | 6 | 6 | 6 | 6 | 6 / 0 / 0 / 0 | -0.0 (-0.1 to +0.1; n=6) | +0.4 (+0.2 to +0.6; n=6) | -0.0 (-0.1 to +0.1; n=6) | 0.00 vs 0.00 | 6/6 | 6/6 |
| 4 pressure: stuck_open | 6 | 2 | 3 | 2 | 5 | 2 / 3 / 0 / 1 | +21.8 (n=2) | +6.1 (-1.3 to +20.6; n=3) | +21.8 (n=2) | 0.00 vs 0.00 | 5/6 | 5/6 |
| 5 containment (all) | 18 | 18 | 18 | 18 | 18 | 18 / 0 / 0 / 0 | +0.2 (+0.2 to +0.3; n=18) | +0.6 (+0.5 to +0.8; n=18) | +0.2 (+0.1 to +0.3; n=18) | 0.00 vs 53.29 | 18/18 | 18/18 |
| 5 containment 2 mm | 6 | 6 | 6 | 6 | 6 | 6 / 0 / 0 / 0 | +0.3 (+0.2 to +0.4; n=6) | +0.9 (+0.5 to +20.4; n=6) | +0.3 (+0.2 to +0.4; n=6) | 0.00 vs 38.38 | 6/6 | 6/6 |
| 5 containment 3.5 mm | 6 | 6 | 6 | 6 | 6 | 6 / 0 / 0 / 0 | +0.1 (+0.1 to +0.2; n=6) | +0.6 (+0.2 to +0.8; n=6) | +0.1 (+0.1 to +0.2; n=6) | 0.00 vs 43.50 | 6/6 | 6/6 |
| 5 containment 5 mm | 6 | 6 | 6 | 6 | 6 | 6 / 0 / 0 / 0 | +0.2 (+0.1 to +0.3; n=6) | +0.6 (+0.3 to +0.8; n=6) | +0.2 (+0.1 to +0.3; n=6) | 0.00 vs 95.29 | 6/6 | 6/6 |
| 6 structural (all) | 12 | 7 | 4 | 8 | 9 | 5 / 4 / 2 / 1 | +7.3 (-6.2 to +50.2; n=5) | +21.2 (-5.8 to +30.6; n=3) | +27.2 (-6.0 to +49.7; n=6) | 0.00 vs 0.00 | 7/12 | 11/12 |
| 6 structural severity 0.5 | 6 | 4 | 0 | 4 | 4 | 3 / 1 / 1 / 1 | +7.3 (-6.2 to +23.8; n=3) | - | +23.8 (-6.2 to +49.1; n=3) | 0.00 vs 0.00 | 2/6 | 5/6 |
| 6 structural severity 1 | 6 | 3 | 4 | 4 | 5 | 2 / 3 / 1 / 0 | +22.2 (n=2) | +21.2 (-5.8 to +30.6; n=3) | +30.6 (-5.8 to +50.2; n=3) | 0.00 vs 0.00 | 5/6 | 6/6 |
| 3s stress leak 0.03 mm (expected miss) | 6 | 3 | 2 | 3 | 2 | 1 / 1 / 2 / 2 | -3.9 (n=1) | -3.9 (n=1) | -3.7 (n=1) | 0.70 vs 0.57 | 2/6 | 4/6 |
| 3s stress leak 0.05 mm (expected miss) | 6 | 2 | 3 | 2 | 1 | 0 / 1 / 2 / 3 | - | - | - | - | 3/6 | 3/6 |
| 5r rupture 50 mm | 2 | 1 | 2 | 1 | 0 | 0 / 0 / 1 / 1 | - | - | - | - | 1/2 | 1/2 |
| -1 composite (two faults) | 24 | 21 | 22 | 21 | 23 | 21 / 2 / 0 / 1 | +4.4 (+0.5 to +17.4; n=21) | +8.7 (+2.0 to +16.3; n=22) | +2.8 (+0.5 to +17.4; n=21) | 0.79 vs 27.91 | 20/24 | 23/24 |

## unseen

Healthy false alarms per week (cost): static A 0.00, static B 1.17, agent alert tier 1.03, agent watch tier 1.29, operator 15 min 1.71, operator 60 min 1.71, expert operator 15 min 1.46 (healthy exposure 78.9 weeks).

### Agent vs the static alarms

Detected = first alarm within 72 h of onset. Lead in hours, positive = the agent earlier, where both fired. kg = released before detection, agent vs static A where both fired (median).

| group | n | floor h | detected: A | B | agent | vs A: both / agent only / A only / neither | lead over A, h (95 % CI) | lead over B, h | kg before detection: agent vs A | union A or agent: 24 h | 72 h | union B or agent: 24 h | 72 h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 sensor fault: spikes on the gas-temperature probe | 6 | 0.1 | 6 | 6 | 6 | 6 / 0 / 0 / 0 | +0.0 (-31.4 to +0.5; n=6) | +0.0 (-31.4 to +0.5; n=6) | 0.00 vs 0.00 | 6/6 | 6/6 | 6/6 | 6/6 |
| 2 thermal anomaly (all) | 12 | 1.7 | 3 | 6 | 10 | 3 / 7 / 0 / 2 | +3.0 (+0.0 to +44.7; n=3) | +1.5 (-10.3 to +33.5; n=6) | 0.00 vs 0.00 | 8/12 | 10/12 | 8/12 | 10/12 |
| 2 thermal: external heat | 6 | 1.2 | 3 | 4 | 6 | 3 / 3 / 0 / 0 | +3.0 (+0.0 to +44.7; n=3) | +1.5 (-16.5 to +44.7; n=4) | 0.00 vs 0.00 | 5/6 | 6/6 | 5/6 | 6/6 |
| 2 thermal: intercooler failure | 6 | 14.7 | 0 | 2 | 4 | 0 / 4 / 0 / 2 | - | +9.1 (n=2) | - | 3/6 | 4/6 | 3/6 | 4/6 |
| 3 leak 0.1 mm | 3 | 1.8 | 0 | 1 | 2 | 0 / 2 / 0 / 1 | - | - | - | 2/3 | 2/3 | 3/3 | 3/3 |
| 3 leak 0.25 mm | 3 | 0.3 | 0 | 1 | 2 | 0 / 2 / 0 / 1 | - | +4.3 (n=1) | - | 2/3 | 2/3 | 2/3 | 2/3 |
| 3 leak 0.5 mm | 3 | 0.0 | 0 | 2 | 3 | 0 / 3 / 0 / 0 | - | +6.6 (n=2) | - | 3/3 | 3/3 | 3/3 | 3/3 |
| 3 leak 1 mm | 3 | 0.0 | 3 | 3 | 2 | 2 / 0 / 1 / 0 | +0.0 (n=2) | +0.0 (n=2) | 0.12 vs 0.12 | 3/3 | 3/3 | 3/3 | 3/3 |
| 3 leaks 0.1-1 mm (all) | 12 | 0.1 | 3 | 7 | 9 | 2 / 7 / 1 / 2 | +0.0 (n=2) | +4.3 (+0.0 to +6.7; n=5) | 0.12 vs 0.12 | 10/12 | 10/12 | 11/12 | 11/12 |
| 4 abnormal pressure (all) | 12 | 0.4 | 9 | 12 | 12 | 9 / 3 / 0 / 0 | +0.2 (+0.0 to +0.5; n=9) | +0.3 (+0.1 to +3.5; n=12) | 0.00 vs 0.00 | 12/12 | 12/12 | 12/12 | 12/12 |
| 4 pressure: blocked_relief | 3 | 1.3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.2 (+0.1 to +0.5; n=3) | +0.2 (+0.1 to +0.5; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 4 pressure: compressor_overrun | 3 | 11.4 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.3 (+0.0 to +0.7; n=3) | +0.3 (+0.0 to +0.7; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 4 pressure: fire | 3 | 0.0 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.4; n=3) | +0.0 (+0.0 to +0.4; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 4 pressure: stuck_open | 3 | 0.0 | 0 | 3 | 3 | 0 / 3 / 0 / 0 | - | +9.9 (+6.3 to +30.4; n=3) | - | 3/3 | 3/3 | 3/3 | 3/3 |
| 5 containment (all) | 9 | 0.0 | 9 | 9 | 8 | 8 / 0 / 1 / 0 | +0.0 (+0.0 to +0.0; n=8) | +0.0 (+0.0 to +0.0; n=8) | 0.00 vs 0.00 | 9/9 | 9/9 | 9/9 | 9/9 |
| 5 containment 2 mm | 3 | 0.0 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.0; n=3) | +0.0 (+0.0 to +0.0; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 5 containment 3.5 mm | 3 | 0.0 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.0; n=3) | +0.0 (+0.0 to +0.0; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 5 containment 5 mm | 3 | 0.0 | 3 | 3 | 2 | 2 / 0 / 1 / 0 | +0.0 (n=2) | +0.0 (n=2) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 6 structural (all) | 6 | 104.1 | 0 | 4 | 4 | 0 / 4 / 0 / 2 | - | +7.0 (-58.6 to +8.8; n=3) | - | 1/6 | 4/6 | 3/6 | 5/6 |
| 6 structural severity 0.5 | 3 | 176.4 | 0 | 2 | 1 | 0 / 1 / 0 / 2 | - | -58.6 (n=1) | - | 0/3 | 1/3 | 2/3 | 2/3 |
| 6 structural severity 1 | 3 | 71.5 | 0 | 2 | 3 | 0 / 3 / 0 / 0 | - | +7.9 (n=2) | - | 1/3 | 3/3 | 1/3 | 3/3 |
| 3s stress leak 0.03 mm (expected miss) | 3 | 27.6 | 0 | 2 | 1 | 0 / 1 / 0 / 2 | - | -3.3 (n=1) | - | 0/3 | 1/3 | 0/3 | 2/3 |
| 3s stress leak 0.05 mm (expected miss) | 3 | 8.8 | 0 | 0 | 2 | 0 / 2 / 0 / 1 | - | - | - | 1/3 | 2/3 | 1/3 | 2/3 |
| 5r rupture 50 mm | 1 | 0.0 | 1 | 0 | 1 | 1 / 0 / 0 / 0 | +0.0 (n=1) | - | 0.00 vs 0.00 | 1/1 | 1/1 | 1/1 | 1/1 |
| -1 composite (two faults) | 12 | 0.2 | 3 | 7 | 11 | 3 / 8 / 0 / 1 | +0.0 (+0.0 to +0.0; n=3) | +0.0 (-23.7 to +4.4; n=6) | 0.00 vs 0.00 | 9/12 | 11/12 | 10/12 | 12/12 |

### Agent vs the modelled operator (not a human study)

Operator: looks every 15 min (op15) or 60 min (op60), raw pressure below the working band by more than X or gas temperature more than Y above ambient (thresholds set once on healthy dev data at 1 false alarm per week per rule); 'expert' reads the temperature-compensated inventory instead of the raw pressure. Lead = operator's first alarm - agent's first alarm.

| group | n | detected: op15 | op60 | expert | agent | vs op15: both / agent only / op only / neither | lead over op15, h (95 % CI) | lead over op60, h | lead over expert, h | kg before detection: agent vs op15 | union op15 or agent: 24 h | 72 h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 sensor fault: spikes on the gas-temperature probe | 6 | 6 | 6 | 6 | 6 | 6 / 0 / 0 / 0 | +2.0 (-27.5 to +5.5; n=6) | +7.8 (-25.6 to +35.6; n=6) | +2.0 (-27.5 to +5.5; n=6) | 0.00 vs 0.00 | 6/6 | 6/6 |
| 2 thermal anomaly (all) | 12 | 10 | 9 | 10 | 10 | 8 / 2 / 2 / 0 | -2.5 (-16.2 to +5.1; n=8) | -2.2 (-11.3 to +4.1; n=8) | -2.9 (-16.2 to +5.1; n=8) | 0.00 vs 0.00 | 11/12 | 12/12 |
| 2 thermal: external heat | 6 | 6 | 6 | 6 | 6 | 6 / 0 / 0 / 0 | -2.9 (-16.7 to +4.1; n=6) | -2.4 (-16.8 to +4.1; n=6) | -3.3 (-16.7 to +4.1; n=6) | 0.00 vs 0.00 | 6/6 | 6/6 |
| 2 thermal: intercooler failure | 6 | 4 | 3 | 4 | 4 | 2 / 2 / 2 / 0 | +9.3 (n=2) | +10.4 (n=2) | +9.3 (n=2) | 0.00 vs 0.00 | 5/6 | 6/6 |
| 3 leak 0.1 mm | 3 | 1 | 1 | 1 | 2 | 0 / 2 / 1 / 0 | - | - | - | - | 3/3 | 3/3 |
| 3 leak 0.25 mm | 3 | 1 | 3 | 1 | 2 | 1 / 1 / 0 / 1 | +4.3 (n=1) | +17.0 (n=2) | +4.3 (n=1) | 1.22 vs 12.15 | 2/3 | 2/3 |
| 3 leak 0.5 mm | 3 | 2 | 3 | 2 | 3 | 2 / 1 / 0 / 0 | +25.6 (n=2) | +23.3 (+7.3 to +32.1; n=3) | +25.6 (n=2) | 5.95 vs 253.86 | 3/3 | 3/3 |
| 3 leak 1 mm | 3 | 3 | 3 | 3 | 2 | 2 / 0 / 1 / 0 | +1.4 (n=2) | +1.6 (n=2) | +1.3 (n=2) | 0.12 vs 45.98 | 3/3 | 3/3 |
| 3 leaks 0.1-1 mm (all) | 12 | 7 | 10 | 7 | 9 | 5 / 4 / 2 / 1 | +4.3 (+1.1 to +44.3; n=5) | +7.3 (+2.0 to +29.7; n=7) | +4.3 (+1.2 to +44.3; n=5) | 1.22 vs 60.00 | 11/12 | 11/12 |
| 4 abnormal pressure (all) | 12 | 10 | 11 | 10 | 12 | 10 / 2 / 0 / 0 | +3.5 (+0.2 to +7.5; n=10) | +1.5 (+0.2 to +6.4; n=11) | +3.5 (+0.2 to +7.5; n=10) | 0.00 vs 0.00 | 12/12 | 12/12 |
| 4 pressure: blocked_relief | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +2.5 (+1.2 to +4.4; n=3) | +2.2 (+1.5 to +3.7; n=3) | +2.5 (+1.2 to +4.4; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 |
| 4 pressure: compressor_overrun | 3 | 1 | 2 | 1 | 3 | 1 / 2 / 0 / 0 | +4.9 (n=1) | +0.4 (n=2) | +4.9 (n=1) | 0.00 vs 75.47 | 3/3 | 3/3 |
| 4 pressure: fire | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | -0.2 (-0.4 to +0.2; n=3) | +0.1 (-0.4 to +0.8; n=3) | -0.2 (-0.4 to +0.2; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 |
| 4 pressure: stuck_open | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +10.0 (+6.4 to +30.5; n=3) | +10.5 (+6.4 to +14.2; n=3) | +10.0 (+6.4 to +30.5; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 |
| 5 containment (all) | 9 | 9 | 9 | 8 | 8 | 8 / 0 / 1 / 0 | +0.2 (+0.1 to +0.3; n=8) | +0.7 (+0.3 to +0.8; n=8) | +0.3 (+0.2 to +0.3; n=8) | 0.00 vs 40.93 | 9/9 | 9/9 |
| 5 containment 2 mm | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.3 (+0.2 to +0.4; n=3) | +0.6 (+0.3 to +0.7; n=3) | +0.3 (+0.2 to +0.4; n=3) | 0.00 vs 28.65 | 3/3 | 3/3 |
| 5 containment 3.5 mm | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.2 (+0.1 to +0.3; n=3) | +0.8 (+0.3 to +1.0; n=3) | +0.3 (+0.2 to +0.3; n=3) | 0.00 vs 75.60 | 3/3 | 3/3 |
| 5 containment 5 mm | 3 | 3 | 3 | 2 | 2 | 2 / 0 / 1 / 0 | +0.1 (n=2) | +0.6 (n=2) | +0.1 (n=2) | 0.00 vs 56.19 | 3/3 | 3/3 |
| 6 structural (all) | 6 | 3 | 4 | 3 | 4 | 3 / 1 / 0 / 2 | +7.1 (-58.6 to +10.6; n=3) | +10.3 (-58.3 to +31.6; n=3) | +8.8 (n=2) | 0.00 vs 0.00 | 2/6 | 4/6 |
| 6 structural severity 0.5 | 3 | 1 | 2 | 1 | 1 | 1 / 0 / 0 / 2 | -58.6 (n=1) | -58.3 (n=1) | - | 0.00 vs 0.00 | 1/3 | 1/3 |
| 6 structural severity 1 | 3 | 2 | 2 | 2 | 3 | 2 / 1 / 0 / 0 | +8.8 (n=2) | +21.0 (n=2) | +8.8 (n=2) | 0.00 vs 0.00 | 1/3 | 3/3 |
| 3s stress leak 0.03 mm (expected miss) | 3 | 2 | 2 | 2 | 1 | 1 / 0 / 1 / 1 | -3.3 (n=1) | -4.8 (n=1) | -3.3 (n=1) | 1.04 vs 0.95 | 0/3 | 2/3 |
| 3s stress leak 0.05 mm (expected miss) | 3 | 0 | 1 | 0 | 2 | 0 / 2 / 0 / 1 | - | -21.7 (n=1) | - | - | 1/3 | 2/3 |
| 5r rupture 50 mm | 1 | 0 | 0 | 0 | 1 | 0 / 1 / 0 / 0 | - | - | - | - | 1/1 | 1/1 |
| -1 composite (two faults) | 12 | 8 | 10 | 8 | 11 | 7 / 4 / 1 / 0 | +0.9 (+0.2 to +14.4; n=7) | +0.6 (-0.7 to +14.2; n=9) | +0.6 (+0.4 to +14.4; n=7) | 0.00 vs 36.79 | 10/12 | 12/12 |

## OOD low

Healthy false alarms per week (cost): static A 0.00, static B 8.63, agent alert tier 2.72, agent watch tier 3.83, operator 15 min 4.68, operator 60 min 2.01, expert operator 15 min 6.27 (healthy exposure 35.2 weeks).

### Agent vs the static alarms

Detected = first alarm within 72 h of onset. Lead in hours, positive = the agent earlier, where both fired. kg = released before detection, agent vs static A where both fired (median).

| group | n | floor h | detected: A | B | agent | vs A: both / agent only / A only / neither | lead over A, h (95 % CI) | lead over B, h | kg before detection: agent vs A | union A or agent: 24 h | 72 h | union B or agent: 24 h | 72 h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 sensor fault: spikes on the gas-temperature probe | 3 | 0.0 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.0; n=3) | +0.0 (+0.0 to +0.0; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 2 thermal anomaly (all) | 6 | 2.9 | 2 | 4 | 4 | 2 / 2 / 0 / 2 | +35.4 (n=2) | +18.4 (-0.5 to +52.5; n=3) | 0.00 vs 0.00 | 3/6 | 4/6 | 4/6 | 5/6 |
| 2 thermal: external heat | 3 | 0.8 | 2 | 2 | 3 | 2 / 1 / 0 / 0 | +35.4 (n=2) | +35.4 (n=2) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 2 thermal: intercooler failure | 3 | 8.1 | 0 | 2 | 1 | 0 / 1 / 0 / 2 | - | -0.5 (n=1) | - | 0/3 | 1/3 | 1/3 | 2/3 |
| 3 leak 0.25 mm | 3 | 0.7 | 0 | 2 | 3 | 0 / 3 / 0 / 0 | - | +12.7 (n=2) | - | 2/3 | 3/3 | 2/3 | 3/3 |
| 3 leak 1 mm | 3 | 0.0 | 0 | 1 | 2 | 0 / 2 / 0 / 1 | - | +0.2 (n=1) | - | 2/3 | 2/3 | 2/3 | 2/3 |
| 3 leaks 0.1-1 mm (all) | 6 | 0.3 | 0 | 3 | 5 | 0 / 5 / 0 / 1 | - | +9.1 (+0.2 to +16.4; n=3) | - | 4/6 | 5/6 | 4/6 | 5/6 |
| 4 abnormal pressure (all) | 12 | 0.2 | 9 | 11 | 11 | 9 / 2 / 0 / 1 | +0.0 (+0.0 to +0.1; n=9) | +0.0 (-0.5 to +0.0; n=11) | 0.00 vs 0.00 | 9/12 | 11/12 | 9/12 | 11/12 |
| 4 pressure: blocked_relief | 3 | 8.3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.1; n=3) | +0.0 (+0.0 to +0.1; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 4 pressure: compressor_overrun | 3 | 35.7 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.7; n=3) | -0.6 (-1.2 to +0.0; n=3) | 0.00 vs 0.00 | 1/3 | 3/3 | 1/3 | 3/3 |
| 4 pressure: fire | 3 | 0.0 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.0; n=3) | +0.0 (+0.0 to +0.0; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 4 pressure: stuck_open | 3 | 0.0 | 0 | 2 | 2 | 0 / 2 / 0 / 1 | - | +1.0 (n=2) | - | 2/3 | 2/3 | 2/3 | 2/3 |
| 5 containment (all) | 3 | 0.0 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.0; n=3) | +0.0 (+0.0 to +0.0; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 5 containment 3.5 mm | 3 | 0.0 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.0; n=3) | +0.0 (+0.0 to +0.0; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 6 structural (all) | 3 | 101.7 | 0 | 2 | 2 | 0 / 2 / 0 / 1 | - | +15.5 (n=2) | - | 1/3 | 2/3 | 1/3 | 2/3 |
| 6 structural severity 1 | 3 | 101.7 | 0 | 2 | 2 | 0 / 2 / 0 / 1 | - | +15.5 (n=2) | - | 1/3 | 2/3 | 1/3 | 2/3 |
| 3s stress leak 0.05 mm (expected miss) | 3 | 31.9 | 0 | 3 | 1 | 0 / 1 / 0 / 2 | - | +3.4 (n=1) | - | 1/3 | 1/3 | 2/3 | 3/3 |
| -1 composite (two faults) | 3 | 0.3 | 0 | 2 | 3 | 0 / 3 / 0 / 0 | - | +21.7 (n=2) | - | 3/3 | 3/3 | 3/3 | 3/3 |

### Agent vs the modelled operator (not a human study)

Operator: looks every 15 min (op15) or 60 min (op60), raw pressure below the working band by more than X or gas temperature more than Y above ambient (thresholds set once on healthy dev data at 1 false alarm per week per rule); 'expert' reads the temperature-compensated inventory instead of the raw pressure. Lead = operator's first alarm - agent's first alarm.

| group | n | detected: op15 | op60 | expert | agent | vs op15: both / agent only / op only / neither | lead over op15, h (95 % CI) | lead over op60, h | lead over expert, h | kg before detection: agent vs op15 | union op15 or agent: 24 h | 72 h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 sensor fault: spikes on the gas-temperature probe | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.2 (+0.0 to +2.2; n=3) | +5.8 (+0.2 to +49.7; n=3) | +0.2 (+0.0 to +2.2; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 |
| 2 thermal anomaly (all) | 6 | 4 | 4 | 4 | 4 | 3 / 1 / 1 / 1 | +0.2 (-0.8 to +1.4; n=3) | +0.4 (-1.3 to +1.4; n=3) | +0.2 (-0.8 to +1.4; n=3) | 0.00 vs 0.00 | 3/6 | 5/6 |
| 2 thermal: external heat | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.2 (-0.8 to +1.4; n=3) | +0.4 (-1.3 to +1.4; n=3) | +0.2 (-0.8 to +1.4; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 |
| 2 thermal: intercooler failure | 3 | 1 | 1 | 1 | 1 | 0 / 1 / 1 / 1 | - | - | - | - | 0/3 | 2/3 |
| 3 leak 0.25 mm | 3 | 1 | 3 | 0 | 3 | 1 / 2 / 0 / 0 | +9.1 (n=1) | +2.8 (-0.9 to +33.3; n=3) | - | 0.88 vs 3.50 | 2/3 | 3/3 |
| 3 leak 1 mm | 3 | 1 | 1 | 1 | 2 | 1 / 1 / 0 / 1 | +28.9 (n=1) | +26.7 (n=1) | +68.2 (n=1) | 6.57 vs 196.25 | 2/3 | 2/3 |
| 3 leaks 0.1-1 mm (all) | 6 | 2 | 4 | 1 | 5 | 2 / 3 / 0 / 1 | +19.0 (n=2) | +14.8 (-0.9 to +33.3; n=4) | +68.2 (n=1) | 3.73 vs 99.88 | 4/6 | 5/6 |
| 4 abnormal pressure (all) | 12 | 6 | 5 | 5 | 11 | 6 / 5 / 0 / 1 | -0.0 (-0.7 to +1.5; n=6) | +0.3 (-0.2 to +2.8; n=5) | +0.0 (-0.7 to +1.0; n=5) | 0.00 vs 0.00 | 9/12 | 11/12 |
| 4 pressure: blocked_relief | 3 | 0 | 1 | 0 | 3 | 0 / 3 / 0 / 0 | - | +2.1 (n=1) | - | - | 3/3 | 3/3 |
| 4 pressure: compressor_overrun | 3 | 1 | 0 | 0 | 3 | 1 / 2 / 0 / 0 | -1.1 (n=1) | - | - | 0.00 vs 0.00 | 1/3 | 3/3 |
| 4 pressure: fire | 3 | 3 | 2 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (-0.0 to +0.2; n=3) | +0.1 (n=2) | +0.0 (-0.0 to +0.2; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 |
| 4 pressure: stuck_open | 3 | 2 | 2 | 2 | 2 | 2 / 0 / 0 / 1 | +1.2 (n=2) | +1.3 (n=2) | +0.2 (n=2) | 0.00 vs 0.00 | 2/3 | 2/3 |
| 5 containment (all) | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.1 (+0.1 to +0.1; n=3) | +0.4 (+0.1 to +0.4; n=3) | +0.1 (+0.1 to +0.1; n=3) | 0.00 vs 8.26 | 3/3 | 3/3 |
| 5 containment 3.5 mm | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.1 (+0.1 to +0.1; n=3) | +0.4 (+0.1 to +0.4; n=3) | +0.1 (+0.1 to +0.1; n=3) | 0.00 vs 8.26 | 3/3 | 3/3 |
| 6 structural (all) | 3 | 1 | 0 | 0 | 2 | 1 / 1 / 0 / 1 | -1.4 (n=1) | - | - | 0.00 vs 0.00 | 1/3 | 2/3 |
| 6 structural severity 1 | 3 | 1 | 0 | 0 | 2 | 1 / 1 / 0 / 1 | -1.4 (n=1) | - | - | 0.00 vs 0.00 | 1/3 | 2/3 |
| 3s stress leak 0.05 mm (expected miss) | 3 | 3 | 1 | 1 | 1 | 1 / 0 / 2 / 0 | +17.6 (n=1) | - | - | 0.20 vs 0.40 | 2/3 | 3/3 |
| -1 composite (two faults) | 3 | 3 | 2 | 3 | 3 | 3 / 0 / 0 / 0 | +21.6 (+1.4 to +22.0; n=3) | +16.0 (n=2) | +21.6 (+1.4 to +22.0; n=3) | 4.38 vs 19.16 | 3/3 | 3/3 |

## OOD high

Healthy false alarms per week (cost): static A 0.00, static B 0.84, agent alert tier 1.90, agent watch tier 2.46, operator 15 min 2.07, operator 60 min 1.70, expert operator 15 min 1.87 (healthy exposure 40.6 weeks).

### Agent vs the static alarms

Detected = first alarm within 72 h of onset. Lead in hours, positive = the agent earlier, where both fired. kg = released before detection, agent vs static A where both fired (median).

| group | n | floor h | detected: A | B | agent | vs A: both / agent only / A only / neither | lead over A, h (95 % CI) | lead over B, h | kg before detection: agent vs A | union A or agent: 24 h | 72 h | union B or agent: 24 h | 72 h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 sensor fault: spikes on the gas-temperature probe | 3 | 0.1 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.1 (+0.0 to +0.3; n=3) | +0.1 (+0.0 to +0.3; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 2 thermal anomaly (all) | 6 | 7.6 | 3 | 3 | 6 | 3 / 3 / 0 / 0 | +12.7 (+10.6 to +20.2; n=3) | +12.7 (+10.6 to +20.2; n=3) | 0.00 vs 0.00 | 5/6 | 6/6 | 5/6 | 6/6 |
| 2 thermal: external heat | 3 | 1.8 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +12.7 (+10.6 to +20.2; n=3) | +12.7 (+10.6 to +20.2; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 2 thermal: intercooler failure | 3 | 16.5 | 0 | 0 | 3 | 0 / 3 / 0 / 0 | - | - | - | 2/3 | 3/3 | 2/3 | 3/3 |
| 3 leak 0.25 mm | 3 | 0.3 | 0 | 1 | 2 | 0 / 2 / 0 / 1 | - | - | - | 2/3 | 2/3 | 2/3 | 3/3 |
| 3 leak 1 mm | 3 | 0.0 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.0; n=3) | +0.0 (+0.0 to +0.0; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 3 leaks 0.1-1 mm (all) | 6 | 0.2 | 3 | 4 | 5 | 3 / 2 / 0 / 1 | +0.0 (+0.0 to +0.0; n=3) | +0.0 (+0.0 to +0.0; n=3) | 0.00 vs 0.00 | 5/6 | 5/6 | 5/6 | 6/6 |
| 4 abnormal pressure (all) | 12 | 5.1 | 8 | 9 | 11 | 8 / 3 / 0 / 1 | +0.1 (+0.0 to +0.4; n=8) | +0.0 (-2.7 to +2.2; n=9) | 0.00 vs 0.00 | 9/12 | 11/12 | 9/12 | 11/12 |
| 4 pressure: blocked_relief | 3 | 11.1 | 2 | 2 | 2 | 2 / 0 / 0 / 1 | +0.1 (n=2) | +0.1 (n=2) | 0.00 vs 0.00 | 1/3 | 2/3 | 1/3 | 2/3 |
| 4 pressure: compressor_overrun | 3 | 13.5 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.4 (+0.3 to +2.2; n=3) | -2.7 (-3.5 to +2.2; n=3) | 0.00 vs 0.00 | 2/3 | 3/3 | 2/3 | 3/3 |
| 4 pressure: fire | 3 | 0.0 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.1; n=3) | +0.0 (+0.0 to +0.1; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 4 pressure: stuck_open | 3 | 0.0 | 0 | 1 | 3 | 0 / 3 / 0 / 0 | - | +37.7 (n=1) | - | 3/3 | 3/3 | 3/3 | 3/3 |
| 5 containment (all) | 3 | 0.0 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.0; n=3) | +0.0 (+0.0 to +0.0; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 5 containment 3.5 mm | 3 | 0.0 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.0; n=3) | +0.0 (+0.0 to +0.0; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 6 structural (all) | 3 | 42.4 | 0 | 2 | 3 | 0 / 3 / 0 / 0 | - | +14.8 (n=2) | - | 2/3 | 3/3 | 2/3 | 3/3 |
| 6 structural severity 1 | 3 | 42.4 | 0 | 2 | 3 | 0 / 3 / 0 / 0 | - | +14.8 (n=2) | - | 2/3 | 3/3 | 2/3 | 3/3 |
| 3s stress leak 0.05 mm (expected miss) | 3 | 12.2 | 0 | 2 | 2 | 0 / 2 / 0 / 1 | - | -5.2 (n=1) | - | 1/3 | 2/3 | 2/3 | 3/3 |
| -1 composite (two faults) | 3 | 0.2 | 0 | 3 | 3 | 0 / 3 / 0 / 0 | - | +13.4 (+1.5 to +19.5; n=3) | - | 3/3 | 3/3 | 3/3 | 3/3 |

### Agent vs the modelled operator (not a human study)

Operator: looks every 15 min (op15) or 60 min (op60), raw pressure below the working band by more than X or gas temperature more than Y above ambient (thresholds set once on healthy dev data at 1 false alarm per week per rule); 'expert' reads the temperature-compensated inventory instead of the raw pressure. Lead = operator's first alarm - agent's first alarm.

| group | n | detected: op15 | op60 | expert | agent | vs op15: both / agent only / op only / neither | lead over op15, h (95 % CI) | lead over op60, h | lead over expert, h | kg before detection: agent vs op15 | union op15 or agent: 24 h | 72 h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 sensor fault: spikes on the gas-temperature probe | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +1.2 (+0.9 to +6.2; n=3) | +6.2 (+5.8 to +26.7; n=3) | +1.2 (+0.9 to +6.2; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 |
| 2 thermal anomaly (all) | 6 | 6 | 4 | 6 | 6 | 6 / 0 / 0 / 0 | -1.7 (-8.4 to +19.1; n=6) | -1.6 (-12.2 to +3.6; n=4) | -1.7 (-8.4 to +19.1; n=6) | 0.00 vs 0.00 | 5/6 | 6/6 |
| 2 thermal: external heat | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | -1.1 (-12.2 to +3.6; n=3) | -0.8 (-12.2 to +3.6; n=3) | -1.1 (-12.2 to +3.6; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 |
| 2 thermal: intercooler failure | 3 | 3 | 1 | 3 | 3 | 3 / 0 / 0 / 0 | -2.3 (-4.7 to +34.6; n=3) | -2.3 (n=1) | -2.3 (-4.7 to +34.6; n=3) | 0.00 vs 0.00 | 2/3 | 3/3 |
| 3 leak 0.25 mm | 3 | 3 | 2 | 3 | 2 | 2 / 0 / 1 / 0 | +30.3 (n=2) | +22.7 (n=1) | +30.3 (n=2) | 15.90 vs 96.81 | 2/3 | 3/3 |
| 3 leak 1 mm | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +1.1 (+0.5 to +2.2; n=3) | +1.1 (+1.0 to +1.9; n=3) | +1.1 (+0.8 to +2.2; n=3) | 0.00 vs 48.99 | 3/3 | 3/3 |
| 3 leaks 0.1-1 mm (all) | 6 | 6 | 5 | 6 | 5 | 5 / 0 / 1 / 0 | +2.2 (+0.5 to +38.0; n=5) | +1.5 (+1.0 to +22.7; n=4) | +2.2 (+0.8 to +38.0; n=5) | 0.15 vs 85.93 | 5/6 | 6/6 |
| 4 abnormal pressure (all) | 12 | 11 | 11 | 11 | 11 | 11 / 0 / 0 / 1 | +1.2 (-0.2 to +2.2; n=11) | +0.8 (-0.2 to +2.5; n=11) | +1.2 (-0.2 to +2.2; n=11) | 0.00 vs 0.00 | 9/12 | 11/12 |
| 4 pressure: blocked_relief | 3 | 2 | 2 | 2 | 2 | 2 / 0 / 0 / 1 | +1.9 (n=2) | +1.7 (n=2) | +1.9 (n=2) | 0.00 vs 0.00 | 1/3 | 2/3 |
| 4 pressure: compressor_overrun | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | -2.7 (-3.3 to +2.0; n=3) | -1.9 (-2.8 to +2.5; n=3) | -2.4 (-3.3 to +2.0; n=3) | 0.00 vs 0.00 | 2/3 | 3/3 |
| 4 pressure: fire | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | -0.0 (-0.2 to +0.0; n=3) | -0.0 (-0.2 to +0.6; n=3) | -0.0 (-0.2 to +0.0; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 |
| 4 pressure: stuck_open | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +15.1 (+1.2 to +37.8; n=3) | +14.6 (+0.9 to +38.2; n=3) | +15.1 (+1.2 to +37.8; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 |
| 5 containment (all) | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.3 (+0.1 to +0.3; n=3) | +0.3 (+0.1 to +0.8; n=3) | +0.3 (+0.1 to +0.3; n=3) | 0.00 vs 83.03 | 3/3 | 3/3 |
| 5 containment 3.5 mm | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.3 (+0.1 to +0.3; n=3) | +0.3 (+0.1 to +0.8; n=3) | +0.3 (+0.1 to +0.3; n=3) | 0.00 vs 83.03 | 3/3 | 3/3 |
| 6 structural (all) | 3 | 2 | 2 | 2 | 3 | 2 / 1 / 0 / 0 | +14.9 (n=2) | +15.3 (n=2) | +14.9 (n=2) | 0.00 vs 0.00 | 2/3 | 3/3 |
| 6 structural severity 1 | 3 | 2 | 2 | 2 | 3 | 2 / 1 / 0 / 0 | +14.9 (n=2) | +15.3 (n=2) | +14.9 (n=2) | 0.00 vs 0.00 | 2/3 | 3/3 |
| 3s stress leak 0.05 mm (expected miss) | 3 | 1 | 1 | 1 | 2 | 1 / 1 / 0 / 1 | -5.1 (n=1) | -4.8 (n=1) | -5.1 (n=1) | 3.21 vs 2.73 | 1/3 | 2/3 |
| -1 composite (two faults) | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +3.5 (+1.6 to +7.2; n=3) | +3.8 (+1.3 to +12.7; n=3) | +7.2 (+3.5 to +15.1; n=3) | 4.75 vs 17.51 | 3/3 | 3/3 |

## OOD low, per-class recalibrated on healthy low-class data (cross-fitted by module; the agent column only, extra rows beside the frozen OOD low numbers)

Healthy false alarms per week (cost): static A 0.00, static B 8.63, agent alert tier 1.67, agent watch tier 2.61, operator 15 min 4.68, operator 60 min 2.01, expert operator 15 min 6.27 (healthy exposure 35.2 weeks).

### Agent vs the static alarms

Detected = first alarm within 72 h of onset. Lead in hours, positive = the agent earlier, where both fired. kg = released before detection, agent vs static A where both fired (median).

| group | n | floor h | detected: A | B | agent | vs A: both / agent only / A only / neither | lead over A, h (95 % CI) | lead over B, h | kg before detection: agent vs A | union A or agent: 24 h | 72 h | union B or agent: 24 h | 72 h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 sensor fault: spikes on the gas-temperature probe | 3 | 0.0 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.0; n=3) | +0.0 (+0.0 to +0.0; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 2 thermal anomaly (all) | 6 | 2.9 | 2 | 4 | 4 | 2 / 2 / 0 / 2 | +35.3 (n=2) | +18.3 (-0.5 to +52.4; n=3) | 0.00 vs 0.00 | 3/6 | 4/6 | 4/6 | 5/6 |
| 2 thermal: external heat | 3 | 0.8 | 2 | 2 | 3 | 2 / 1 / 0 / 0 | +35.3 (n=2) | +35.3 (n=2) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 2 thermal: intercooler failure | 3 | 8.1 | 0 | 2 | 1 | 0 / 1 / 0 / 2 | - | -0.5 (n=1) | - | 0/3 | 1/3 | 1/3 | 2/3 |
| 3 leak 0.25 mm | 3 | 0.7 | 0 | 2 | 3 | 0 / 3 / 0 / 0 | - | +12.5 (n=2) | - | 2/3 | 3/3 | 2/3 | 3/3 |
| 3 leak 1 mm | 3 | 0.0 | 0 | 1 | 2 | 0 / 2 / 0 / 1 | - | +0.2 (n=1) | - | 2/3 | 2/3 | 2/3 | 2/3 |
| 3 leaks 0.1-1 mm (all) | 6 | 0.3 | 0 | 3 | 5 | 0 / 5 / 0 / 1 | - | +9.1 (+0.2 to +16.0; n=3) | - | 4/6 | 5/6 | 4/6 | 5/6 |
| 4 abnormal pressure (all) | 12 | 0.2 | 9 | 11 | 11 | 9 / 2 / 0 / 1 | +0.0 (+0.0 to +0.0; n=9) | +0.0 (-0.9 to +0.0; n=11) | 0.00 vs 0.00 | 9/12 | 11/12 | 9/12 | 11/12 |
| 4 pressure: blocked_relief | 3 | 8.3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.1; n=3) | +0.0 (+0.0 to +0.1; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 4 pressure: compressor_overrun | 3 | 35.7 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.1; n=3) | -1.1 (-1.2 to +0.0; n=3) | 0.00 vs 0.00 | 1/3 | 3/3 | 1/3 | 3/3 |
| 4 pressure: fire | 3 | 0.0 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.0; n=3) | +0.0 (+0.0 to +0.0; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 4 pressure: stuck_open | 3 | 0.0 | 0 | 2 | 2 | 0 / 2 / 0 / 1 | - | +0.7 (n=2) | - | 2/3 | 2/3 | 2/3 | 2/3 |
| 5 containment (all) | 3 | 0.0 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.0; n=3) | +0.0 (+0.0 to +0.0; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 5 containment 3.5 mm | 3 | 0.0 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.0; n=3) | +0.0 (+0.0 to +0.0; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 6 structural (all) | 3 | 101.7 | 0 | 2 | 2 | 0 / 2 / 0 / 1 | - | +15.2 (n=2) | - | 1/3 | 2/3 | 1/3 | 2/3 |
| 6 structural severity 1 | 3 | 101.7 | 0 | 2 | 2 | 0 / 2 / 0 / 1 | - | +15.2 (n=2) | - | 1/3 | 2/3 | 1/3 | 2/3 |
| 3s stress leak 0.05 mm (expected miss) | 3 | 31.9 | 0 | 3 | 1 | 0 / 1 / 0 / 2 | - | -0.7 (n=1) | - | 1/3 | 1/3 | 2/3 | 3/3 |
| -1 composite (two faults) | 3 | 0.3 | 0 | 2 | 3 | 0 / 3 / 0 / 0 | - | +21.7 (n=2) | - | 3/3 | 3/3 | 3/3 | 3/3 |

### Agent vs the modelled operator (not a human study)

Operator: looks every 15 min (op15) or 60 min (op60), raw pressure below the working band by more than X or gas temperature more than Y above ambient (thresholds set once on healthy dev data at 1 false alarm per week per rule); 'expert' reads the temperature-compensated inventory instead of the raw pressure. Lead = operator's first alarm - agent's first alarm.

| group | n | detected: op15 | op60 | expert | agent | vs op15: both / agent only / op only / neither | lead over op15, h (95 % CI) | lead over op60, h | lead over expert, h | kg before detection: agent vs op15 | union op15 or agent: 24 h | 72 h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 sensor fault: spikes on the gas-temperature probe | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.2 (+0.0 to +2.2; n=3) | +5.8 (+0.2 to +49.7; n=3) | +0.2 (+0.0 to +2.2; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 |
| 2 thermal anomaly (all) | 6 | 4 | 4 | 4 | 4 | 3 / 1 / 1 / 1 | -0.2 (-0.9 to +1.2; n=3) | +0.1 (-1.4 to +1.2; n=3) | -0.2 (-0.9 to +1.2; n=3) | 0.00 vs 0.00 | 3/6 | 5/6 |
| 2 thermal: external heat | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | -0.2 (-0.9 to +1.2; n=3) | +0.1 (-1.4 to +1.2; n=3) | -0.2 (-0.9 to +1.2; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 |
| 2 thermal: intercooler failure | 3 | 1 | 1 | 1 | 1 | 0 / 1 / 1 / 1 | - | - | - | - | 0/3 | 2/3 |
| 3 leak 0.25 mm | 3 | 1 | 3 | 0 | 3 | 1 / 2 / 0 / 0 | +9.1 (n=1) | +2.4 (-2.7 to +33.3; n=3) | - | 0.88 vs 3.50 | 2/3 | 3/3 |
| 3 leak 1 mm | 3 | 1 | 1 | 1 | 2 | 1 / 1 / 0 / 1 | +28.9 (n=1) | +26.7 (n=1) | +68.2 (n=1) | 6.57 vs 196.25 | 2/3 | 2/3 |
| 3 leaks 0.1-1 mm (all) | 6 | 2 | 4 | 1 | 5 | 2 / 3 / 0 / 1 | +19.0 (n=2) | +14.5 (-2.7 to +33.3; n=4) | +68.2 (n=1) | 3.73 vs 99.88 | 4/6 | 5/6 |
| 4 abnormal pressure (all) | 12 | 6 | 5 | 5 | 11 | 6 / 5 / 0 / 1 | -0.0 (-0.9 to +1.3; n=6) | +0.3 (-0.6 to +2.5; n=5) | +0.0 (-1.1 to +0.8; n=5) | 0.00 vs 0.00 | 9/12 | 11/12 |
| 4 pressure: blocked_relief | 3 | 0 | 1 | 0 | 3 | 0 / 3 / 0 / 0 | - | +2.1 (n=1) | - | - | 3/3 | 3/3 |
| 4 pressure: compressor_overrun | 3 | 1 | 0 | 0 | 3 | 1 / 2 / 0 / 0 | -1.1 (n=1) | - | - | 0.00 vs 0.00 | 1/3 | 3/3 |
| 4 pressure: fire | 3 | 3 | 2 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (-0.0 to +0.2; n=3) | +0.1 (n=2) | +0.0 (-0.0 to +0.2; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 |
| 4 pressure: stuck_open | 3 | 2 | 2 | 2 | 2 | 2 / 0 / 0 / 1 | +0.8 (n=2) | +1.0 (n=2) | -0.2 (n=2) | 0.00 vs 0.00 | 2/3 | 2/3 |
| 5 containment (all) | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.1 (+0.1 to +0.1; n=3) | +0.4 (+0.1 to +0.4; n=3) | +0.1 (+0.1 to +0.1; n=3) | 0.00 vs 8.26 | 3/3 | 3/3 |
| 5 containment 3.5 mm | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.1 (+0.1 to +0.1; n=3) | +0.4 (+0.1 to +0.4; n=3) | +0.1 (+0.1 to +0.1; n=3) | 0.00 vs 8.26 | 3/3 | 3/3 |
| 6 structural (all) | 3 | 1 | 0 | 0 | 2 | 1 / 1 / 0 / 1 | -1.4 (n=1) | - | - | 0.00 vs 0.00 | 1/3 | 2/3 |
| 6 structural severity 1 | 3 | 1 | 0 | 0 | 2 | 1 / 1 / 0 / 1 | -1.4 (n=1) | - | - | 0.00 vs 0.00 | 1/3 | 2/3 |
| 3s stress leak 0.05 mm (expected miss) | 3 | 3 | 1 | 1 | 1 | 1 / 0 / 2 / 0 | +13.5 (n=1) | - | - | 0.25 vs 0.40 | 2/3 | 3/3 |
| -1 composite (two faults) | 3 | 3 | 2 | 3 | 3 | 3 / 0 / 0 / 0 | +21.6 (+0.8 to +21.9; n=3) | +16.0 (n=2) | +21.6 (+0.8 to +21.9; n=3) | 4.78 vs 19.16 | 3/3 | 3/3 |

## OOD high, per-class recalibrated on healthy high-class data (cross-fitted by module; the agent column only, extra rows beside the frozen OOD high numbers)

Healthy false alarms per week (cost): static A 0.00, static B 0.84, agent alert tier 0.39, agent watch tier 0.47, operator 15 min 2.07, operator 60 min 1.70, expert operator 15 min 1.87 (healthy exposure 40.6 weeks).

### Agent vs the static alarms

Detected = first alarm within 72 h of onset. Lead in hours, positive = the agent earlier, where both fired. kg = released before detection, agent vs static A where both fired (median).

| group | n | floor h | detected: A | B | agent | vs A: both / agent only / A only / neither | lead over A, h (95 % CI) | lead over B, h | kg before detection: agent vs A | union A or agent: 24 h | 72 h | union B or agent: 24 h | 72 h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 sensor fault: spikes on the gas-temperature probe | 3 | 0.1 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.0; n=3) | +0.0 (+0.0 to +0.0; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 2 thermal anomaly (all) | 6 | 7.6 | 3 | 3 | 5 | 3 / 2 / 0 / 1 | +10.3 (+0.0 to +17.9; n=3) | +10.3 (+0.0 to +17.9; n=3) | 0.00 vs 0.00 | 4/6 | 5/6 | 4/6 | 5/6 |
| 2 thermal: external heat | 3 | 1.8 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +10.3 (+0.0 to +17.9; n=3) | +10.3 (+0.0 to +17.9; n=3) | 0.00 vs 0.00 | 2/3 | 3/3 | 2/3 | 3/3 |
| 2 thermal: intercooler failure | 3 | 16.5 | 0 | 0 | 2 | 0 / 2 / 0 / 1 | - | - | - | 2/3 | 2/3 | 2/3 | 2/3 |
| 3 leak 0.25 mm | 3 | 0.3 | 0 | 1 | 3 | 0 / 3 / 0 / 0 | - | +67.4 (n=1) | - | 3/3 | 3/3 | 3/3 | 3/3 |
| 3 leak 1 mm | 3 | 0.0 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.0; n=3) | +0.0 (+0.0 to +0.0; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 3 leaks 0.1-1 mm (all) | 6 | 0.2 | 3 | 4 | 6 | 3 / 3 / 0 / 0 | +0.0 (+0.0 to +0.0; n=3) | +0.0 (+0.0 to +67.4; n=4) | 0.00 vs 0.00 | 6/6 | 6/6 | 6/6 | 6/6 |
| 4 abnormal pressure (all) | 12 | 5.1 | 8 | 9 | 11 | 8 / 3 / 0 / 1 | +0.0 (+0.0 to +0.2; n=8) | +0.0 (-2.9 to +0.0; n=9) | 0.00 vs 0.00 | 9/12 | 11/12 | 9/12 | 11/12 |
| 4 pressure: blocked_relief | 3 | 11.1 | 2 | 2 | 2 | 2 / 0 / 0 / 1 | +0.0 (n=2) | +0.0 (n=2) | 0.00 vs 0.00 | 1/3 | 2/3 | 1/3 | 2/3 |
| 4 pressure: compressor_overrun | 3 | 13.5 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.2 (+0.0 to +0.2; n=3) | -2.9 (-3.7 to +0.0; n=3) | 0.00 vs 0.00 | 2/3 | 3/3 | 2/3 | 3/3 |
| 4 pressure: fire | 3 | 0.0 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.0; n=3) | +0.0 (+0.0 to +0.0; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 4 pressure: stuck_open | 3 | 0.0 | 0 | 1 | 3 | 0 / 3 / 0 / 0 | - | +30.8 (n=1) | - | 3/3 | 3/3 | 3/3 | 3/3 |
| 5 containment (all) | 3 | 0.0 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.0; n=3) | +0.0 (+0.0 to +0.0; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 5 containment 3.5 mm | 3 | 0.0 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.0 (+0.0 to +0.0; n=3) | +0.0 (+0.0 to +0.0; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 | 3/3 | 3/3 |
| 6 structural (all) | 3 | 42.4 | 0 | 2 | 3 | 0 / 3 / 0 / 0 | - | -10.8 (n=2) | - | 0/3 | 3/3 | 1/3 | 3/3 |
| 6 structural severity 1 | 3 | 42.4 | 0 | 2 | 3 | 0 / 3 / 0 / 0 | - | -10.8 (n=2) | - | 0/3 | 3/3 | 1/3 | 3/3 |
| 3s stress leak 0.05 mm (expected miss) | 3 | 12.2 | 0 | 2 | 1 | 0 / 1 / 0 / 2 | - | -5.3 (n=1) | - | 0/3 | 1/3 | 1/3 | 2/3 |
| -1 composite (two faults) | 3 | 0.2 | 0 | 3 | 3 | 0 / 3 / 0 / 0 | - | +12.9 (+1.4 to +19.3; n=3) | - | 3/3 | 3/3 | 3/3 | 3/3 |

### Agent vs the modelled operator (not a human study)

Operator: looks every 15 min (op15) or 60 min (op60), raw pressure below the working band by more than X or gas temperature more than Y above ambient (thresholds set once on healthy dev data at 1 false alarm per week per rule); 'expert' reads the temperature-compensated inventory instead of the raw pressure. Lead = operator's first alarm - agent's first alarm.

| group | n | detected: op15 | op60 | expert | agent | vs op15: both / agent only / op only / neither | lead over op15, h (95 % CI) | lead over op60, h | lead over expert, h | kg before detection: agent vs op15 | union op15 or agent: 24 h | 72 h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 sensor fault: spikes on the gas-temperature probe | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.9 (+0.9 to +6.1; n=3) | +6.1 (+5.4 to +26.7; n=3) | +0.9 (+0.9 to +6.1; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 |
| 2 thermal anomaly (all) | 6 | 6 | 4 | 6 | 5 | 5 / 0 / 1 / 0 | -4.3 (-12.5 to +26.5; n=5) | -6.7 (-12.5 to -3.2; n=4) | -4.3 (-12.5 to +26.5; n=5) | 0.00 vs 0.00 | 5/6 | 6/6 |
| 2 thermal: external heat | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | -9.1 (-12.5 to -3.4; n=3) | -9.1 (-12.5 to -3.2; n=3) | -9.1 (-12.5 to -3.4; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 |
| 2 thermal: intercooler failure | 3 | 3 | 1 | 3 | 2 | 2 / 0 / 1 / 0 | +11.1 (n=2) | -4.3 (n=1) | +11.1 (n=2) | 0.00 vs 0.00 | 2/3 | 3/3 |
| 3 leak 0.25 mm | 3 | 3 | 2 | 3 | 3 | 3 / 0 / 0 / 0 | +28.8 (+22.0 to +37.8; n=3) | +34.3 (n=2) | +28.8 (+22.0 to +37.8; n=3) | 8.20 vs 85.93 | 3/3 | 3/3 |
| 3 leak 1 mm | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +1.1 (+0.5 to +2.2; n=3) | +1.1 (+1.0 to +1.9; n=3) | +1.1 (+0.8 to +2.2; n=3) | 0.00 vs 48.99 | 3/3 | 3/3 |
| 3 leaks 0.1-1 mm (all) | 6 | 6 | 5 | 6 | 6 | 6 / 0 / 0 / 0 | +12.1 (+0.8 to +29.9; n=6) | +1.9 (+1.0 to +46.6; n=5) | +12.1 (+0.9 to +33.3; n=6) | 3.60 vs 79.25 | 6/6 | 6/6 |
| 4 abnormal pressure (all) | 12 | 11 | 11 | 11 | 11 | 11 / 0 / 0 / 1 | -0.1 (-2.9 to +2.0; n=11) | +0.3 (-2.2 to +2.3; n=11) | -0.1 (-2.7 to +2.0; n=11) | 0.00 vs 0.00 | 9/12 | 11/12 |
| 4 pressure: blocked_relief | 3 | 2 | 2 | 2 | 2 | 2 / 0 / 0 / 1 | +1.8 (n=2) | +1.6 (n=2) | +1.8 (n=2) | 0.00 vs 0.00 | 1/3 | 2/3 |
| 4 pressure: compressor_overrun | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | -2.9 (-3.5 to -0.2; n=3) | -2.2 (-3.0 to +0.3; n=3) | -2.7 (-3.5 to -0.2; n=3) | 0.00 vs 0.00 | 2/3 | 3/3 |
| 4 pressure: fire | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | -0.1 (-0.2 to -0.0; n=3) | -0.0 (-0.3 to +0.6; n=3) | -0.1 (-0.2 to -0.0; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 |
| 4 pressure: stuck_open | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +14.5 (-3.5 to +30.9; n=3) | +14.0 (-3.8 to +31.4; n=3) | +14.5 (-3.5 to +30.9; n=3) | 0.00 vs 0.00 | 3/3 | 3/3 |
| 5 containment (all) | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.3 (+0.1 to +0.3; n=3) | +0.3 (+0.1 to +0.8; n=3) | +0.3 (+0.1 to +0.3; n=3) | 0.00 vs 83.03 | 3/3 | 3/3 |
| 5 containment 3.5 mm | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +0.3 (+0.1 to +0.3; n=3) | +0.3 (+0.1 to +0.8; n=3) | +0.3 (+0.1 to +0.3; n=3) | 0.00 vs 83.03 | 3/3 | 3/3 |
| 6 structural (all) | 3 | 2 | 2 | 2 | 3 | 2 / 1 / 0 / 0 | -10.7 (n=2) | -10.4 (n=2) | -10.7 (n=2) | 0.00 vs 0.00 | 1/3 | 3/3 |
| 6 structural severity 1 | 3 | 2 | 2 | 2 | 3 | 2 / 1 / 0 / 0 | -10.7 (n=2) | -10.4 (n=2) | -10.7 (n=2) | 0.00 vs 0.00 | 1/3 | 3/3 |
| 3s stress leak 0.05 mm (expected miss) | 3 | 1 | 1 | 1 | 1 | 1 / 0 / 0 / 2 | -5.2 (n=1) | -4.9 (n=1) | -5.2 (n=1) | 3.22 vs 2.73 | 0/3 | 1/3 |
| -1 composite (two faults) | 3 | 3 | 3 | 3 | 3 | 3 / 0 / 0 / 0 | +3.1 (+1.5 to +7.0; n=3) | +3.3 (+1.2 to +12.5; n=3) | +7.0 (+3.1 to +15.0; n=3) | 5.64 vs 17.51 | 3/3 | 3/3 |

## slow drift (new)

**Read with the chance column of `cgh2_agent_drift.md`:** an unrelated alarm falls in a 72 h window after a pseudo-onset on a HEALTHY episode about 41 % of the time for static B, 28 % for the agent, 66 % for the 15-minute operator and 0 % for static A. So the operator's and static B's 72 h detections below are about what their false-alarm rates alone would produce; only static A's zero and the agent's naming of the sensor (2 of 12, `cgh2_agent_drift.md`) are not chance. Many of those alarms come before the drift is observable at all (before the ideal-observer floor).

Healthy false alarms per week (cost): static A 0.00, static B 0.60, agent alert tier 0.30, agent watch tier 0.30, operator 15 min 1.20, operator 60 min 0.90, expert operator 15 min 1.05 (healthy exposure 6.7 weeks).

### Agent vs the static alarms

Detected = first alarm within 72 h of onset. Lead in hours, positive = the agent earlier, where both fired. kg = released before detection, agent vs static A where both fired (median).

| group | n | floor h | detected: A | B | agent | vs A: both / agent only / A only / neither | lead over A, h (95 % CI) | lead over B, h | kg before detection: agent vs A | union A or agent: 24 h | 72 h | union B or agent: 24 h | 72 h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1d drift 0.5 % FS | 4 | 90.0 | 0 | 1 | 0 | 0 / 0 / 0 / 4 | - | - | - | 0/4 | 0/4 | 1/4 | 1/4 |
| 1d drift 1 % FS | 4 | 45.0 | 0 | 3 | 1 | 0 / 1 / 0 / 3 | - | -0.8 (n=1) | - | 1/4 | 1/4 | 1/4 | 3/4 |
| 1d drift 2 % FS | 4 | 60.1 | 0 | 2 | 1 | 0 / 1 / 0 / 3 | - | -44.7 (n=1) | - | 0/4 | 1/4 | 1/4 | 2/4 |
| 1d drift: gas-temperature probe | 6 | 97.7 | 0 | 4 | 1 | 0 / 1 / 0 / 5 | - | -44.7 (n=1) | - | 0/6 | 1/6 | 2/6 | 4/6 |
| 1d drift: pressure transmitter | 6 | 45.0 | 0 | 2 | 1 | 0 / 1 / 0 / 5 | - | -0.8 (n=1) | - | 1/6 | 1/6 | 1/6 | 2/6 |
| 1d slow drift (all) | 12 | 67.5 | 0 | 6 | 2 | 0 / 2 / 0 / 10 | - | -22.7 (n=2) | - | 1/12 | 2/12 | 3/12 | 6/12 |

### Agent vs the modelled operator (not a human study)

Operator: looks every 15 min (op15) or 60 min (op60), raw pressure below the working band by more than X or gas temperature more than Y above ambient (thresholds set once on healthy dev data at 1 false alarm per week per rule); 'expert' reads the temperature-compensated inventory instead of the raw pressure. Lead = operator's first alarm - agent's first alarm.

| group | n | detected: op15 | op60 | expert | agent | vs op15: both / agent only / op only / neither | lead over op15, h (95 % CI) | lead over op60, h | lead over expert, h | kg before detection: agent vs op15 | union op15 or agent: 24 h | 72 h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1d drift 0.5 % FS | 4 | 2 | 3 | 2 | 0 | 0 / 0 / 2 / 2 | - | - | - | - | 1/4 | 2/4 |
| 1d drift 1 % FS | 4 | 4 | 3 | 4 | 1 | 1 / 0 / 3 / 0 | -0.8 (n=1) | +18.0 (n=1) | -0.8 (n=1) | 0.00 vs 0.00 | 2/4 | 4/4 |
| 1d drift 2 % FS | 4 | 2 | 2 | 2 | 1 | 1 / 0 / 1 / 2 | -44.7 (n=1) | -43.2 (n=1) | -44.7 (n=1) | 0.00 vs 0.00 | 1/4 | 2/4 |
| 1d drift: gas-temperature probe | 6 | 6 | 5 | 6 | 1 | 1 / 0 / 5 / 0 | -44.7 (n=1) | -43.2 (n=1) | -44.7 (n=1) | 0.00 vs 0.00 | 3/6 | 6/6 |
| 1d drift: pressure transmitter | 6 | 2 | 3 | 2 | 1 | 1 / 0 / 1 / 4 | -0.8 (n=1) | +18.0 (n=1) | -0.8 (n=1) | 0.00 vs 0.00 | 1/6 | 2/6 |
| 1d slow drift (all) | 12 | 8 | 8 | 8 | 2 | 2 / 0 / 6 / 4 | -22.7 (n=2) | -12.6 (n=2) | -22.7 (n=2) | 0.00 vs 0.00 | 4/12 | 8/12 |

