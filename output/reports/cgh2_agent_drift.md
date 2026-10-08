# Slow sensor-drift episodes: frozen agent against the static alarms, the learned model and the modelled operator

Reference configuration, not a verified Saudi system. 12 NEW episodes (6 slow pressure-transmitter drifts, 6 slow gas-temperature-probe drifts, 0.5-2 % of full scale reached after 5 days, medium class, modules M01-M06, new seeds) in `output/cgh2_drift/medium/`, never used for tuning; scored ONCE with the frozen configuration (tool fit and fusion model fitted on all dev, nothing fitted here). The vessel is healthy: only the dashboard reading is wrong. 'First alarm after onset' is the first alarm event at or after the drift onset (a pre-onset alarm is a false alarm and is shown separately; it is never credited). The ideal-observer floor is the time the noise-free drift first exceeds 3 sigma of the channel (sigma = accuracy / 2; for the gas-temperature probe this includes the 1 K bulk gradient); '-' = it never does, so no per-channel observer could see that drift at all. The operator proxy is a MODELLED operator (see `operator_proxy.py`), not a human study.

## Per episode

| episode | sensor, drift | floor (ideal observer) | static_A: first alarm after onset | static_B: first alarm after onset | learned: first alarm after onset | agent: first alarm after onset | op15: first alarm after onset | op60: first alarm after onset | op15x: first alarm after onset | agent: class at first alert / any decision in the event | agent: which sensor (T5 verdict) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M01__drift-gastemp-p1 | gas_temp +1.0 % FS | - | - | - | 86.1 h† | 88.4 h† | 14.0 h† (+1 pre-onset) | 13.7 h† (+1 pre-onset) | 14.0 h† (+1 pre-onset) | class 2 / sensor not named | - |
| M01__drift-pressure-p0.5 | pressure +0.5 % FS | 90 h | - | 72.7 h† (+1 pre-onset) | - | 73.1 h† | 100.8 h (+1 pre-onset) | 35.1 h† (+1 pre-onset) | 100.8 h (+1 pre-onset) | class 1 / sensor named | flow_meters_suspect/temperature_probe_suspect (wrong) |
| M02__drift-gastemp-m2 | gas_temp -2.0 % FS | 98 h | - | 24.5 h† | - | - | 24.5 h† | 24.8 h† | 24.5 h† | no alert / sensor not named | - |
| M02__drift-pressure-m1 | pressure -1.0 % FS | 45 h | - | 4.3 h† | - | 5.1 h† (+1 pre-onset) | 4.3 h† (+1 pre-onset) | 23.1 h† | 4.3 h† (+1 pre-onset) | class 6 / sensor not named | pressure_transmitter_suspect/strain_gauge_suspect (right) |
| M03__drift-gastemp-p0.5 | gas_temp +0.5 % FS | - | - | 105.7 h† | - | 165.7 h† | 25.2 h† | 25.7 h† | 25.2 h† | class 3 / sensor not named | - |
| M03__drift-pressure-p2 | pressure +2.0 % FS | 22 h | - | 108.1 h (+1 pre-onset) | - | - | 108.2 h (+2 pre-onset) | 108.7 h (+2 pre-onset) | 108.2 h (+1 pre-onset) | class 3 / sensor not named | - |
| M04__drift-gastemp-m1 | gas_temp -1.0 % FS | - | - | 70.8 h† (+2 pre-onset) | - | 82.0 h† | 70.9 h† (+2 pre-onset) | 72.6 h† (+2 pre-onset) | 70.9 h† (+2 pre-onset) | class 3 / sensor not named | - |
| M04__drift-pressure-m0.5 | pressure -0.5 % FS | 90 h | - | 73.1 h† | 93.5 h | - | 73.3 h† | 74.0 h† | 73.3 h† | no alert / sensor not named | - |
| M05__drift-gastemp-p2 | gas_temp +2.0 % FS | 98 h | - | 12.9 h† | 15.0 h† | 57.5 h† | 12.9 h† | 14.4 h† | 12.9 h† | class 2 / sensor not named | flow_meters_suspect (wrong) |
| M05__drift-pressure-p1 | pressure +1.0 % FS | 45 h | - | 70.9 h | 41.3 h† | 128.6 h | 71.1 h | 71.3 h | 71.1 h | class 6 / sensor not named | flow_meters_suspect (wrong) |
| M06__drift-gastemp-m0.5 | gas_temp -0.5 % FS | - | - | 1.0 h† | - | 193.1 h† | 1.2 h† (+1 pre-onset) | 1.7 h† | 1.2 h† (+1 pre-onset) | class 1 / sensor named | flow_meters_suspect/temperature_probe_suspect (right) |
| M06__drift-pressure-m2 | pressure -2.0 % FS | 22 h | - | 211.9 h | 44.1 h | 171.3 h | 82.4 h | 82.1 h | 82.4 h | class 3 / sensor not named | - |

## Summary

| detector | alarm after onset, any time (of 12) | CHANCE: the same detector on healthy dev episodes with the same pseudo-onsets | alarm after onset AND after the ideal-observer floor (the drift could have caused it) | CHANCE within 72 h of onset |
|---|---|---|---|---|
| static_A | 0 | 0 % (expect 0.0 of 12) | 0 | 0 % |
| static_B | 11 | 77 % (expect 9.2 of 12) | 3 | 41 % |
| learned | 5 | 25 % (expect 3.0 of 12) | 2 | 12 % |
| agent | 9 | 58 % (expect 7.0 of 12) | 2 | 28 % |
| op15 | 12 | 96 % (expect 11.6 of 12) | 4 | 66 % |
| op60 | 12 | 89 % (expect 10.7 of 12) | 3 | 62 % |
| op15x | 12 | 96 % (expect 11.6 of 12) | 4 | 66 % |

† = the alarm came before the drift was observable at all (before the ideal-observer floor, or the floor does not exist): it cannot have been caused by the drift. A detector that fires at its false-alarm rate, whatever happens, looks like a detector in this table; the chance column says how much of that is expected from false alarms alone.

Agent named a sensor fault at the first alert in 2/12 episodes and the RIGHT sensor in 2/12. 
Static A never fired on a drift episode after onset in a case where the agent also fired (no paired lead).

Reading guide: the static alarms (PAH / PAHH / TAH / TAHH / H2) watch limits, and a drift of 0.5-2 % of full scale leaves the reading far inside them; they can only fire if something else happens in the same episode. The agent's chance on a pressure drift comes from the pressure-strain redundancy (T5) and from the inventory balance (T2), which a biased pressure reading breaks; a gas-temperature drift shifts the compensated inventory and the thermal residual (T3, T5) but at 0.5-2 % of a 190 K span (1-4 K) it is at or below the probe's own error plus the 1 K bulk gradient, which is why most of those have no ideal-observer floor.
