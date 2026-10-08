# Where every number on the dashboard screens comes from

Everything is read from replays of the digital twin (reference configuration, not a verified Saudi system). Nothing was changed in the agent, datasets, thresholds or reports; this folder only reads them.
`python build_data.py && python build_html.py && python screenshot.py` rebuilds `data.json`, the two HTML files and all PNGs (`make_replays.py` generates the replays that did not exist yet).

## Replay JSON used (one JSON line per 5-minute tick + `meta` line; `decision` objects carry the tool-call trace)

| key | episode | file |
|---|---|---|
| leak05 | M01__leak-0.5mm | `output/cgh2_agent_demo/M01__leak-0.5mm.ticks.jsonl` (existing, read-only) |
| leak025 | M01__leak-0.25mm | `output/cgh2_agent_demo/M01__leak-0.25mm.ticks.jsonl` (existing) |
| interc | M01__thermal-intercooler-r6h | `output/cgh2_agent_demo/M01__thermal-intercooler-r6h.ticks.jsonl` (existing) |
| leak01 | M01__leak-0.1mm | existing replay; loaded into `data.json`, not shown on the 7 screens |
| cont | M01__containment-leak-3.5mm | `output/cgh2_agent_dashboard/replays/` (NEW: no containment replay existed); loaded, not shown (see "left out") |
| M02..M06 | M0x__normal-refuelling0 | `output/cgh2_agent_dashboard/replays/` (NEW; same frozen agent, leave-one-module-out parameters, healthy episodes) |

Time on every screen is **replay (episode) time in hours** from the start of the episode, `t_h` / `t_s`/3600. "After onset" = replay time minus `meta.timelines.onset_h` (the twin's fault-onset ground truth).
Fields used: tick `t_h`, `tags` (GH2-PT-101 pressure bar(a), GH2-TT-101 gas temperature °C, GH2-TT-102 outer wall °C, GH2-AT-101 gas detector %LFL, GH2-FT-101 fill and GH2-FT-102 discharge flow kg/s, GH2-SE-101 strain µε, GH2-TT-901 ambient °C),
`raw_pressure_bar`, `compensated_inventory_kg`, `agent.{state,tier,score,watch_threshold,alert_threshold,class_name_*}`, `leak.{rate_kgh,lo,hi,orifice_mm}`, `static_alarm`; meta `timelines.{agent_alert_h,static_alarm_h,operator_15min_h,onset_h}`, `events[0].{t_suspect_s,t_watch_s,t_alert_s,approval_s,closed_s}`;
decision `{t_s,tier,class,class_name_*,posterior,leak_estimate,released_kg,procedure.{action_*,reason_*},approved,trace[].{order,tool,runtime_ms,result.{verdict,estimate,fields,series,text_en,text_ar}}}`.

Not in the replay JSON, taken from the same episode's dataset files or the run manifest (read-only):
* compressor, inlet valve, discharge valve and relief valve states (screens 1, 2, fleet compressor state): the dashboard's discrete tags of the same episode (`Unit.raw.disc_state` at the tick index);
* kg released before an alarm (screens 5): cumulative of the twin's own leak mass flow (`gt__mdot_leak_kg_s` + PRV vent) from onset to the alarm time. This is twin ground truth, labelled as such on screen;
* PAH 306 and PAHH 315 bar(a): `output/cgh2/medium/manifest.json` `class_parameters`; TAH 85 / TAHH 100 °C and H2 alarm 25 / trip 50 %LFL: the alarm limits in the reference dashboard configuration (also in tool T12);
* modelled-operator rule (screen 5 note): `output/cgh2_cache/agent/operator_thresholds.json`, 15-minute looks: pressure rule 0.1518 x MOP = 45.5 bar below the compressor working band, temperature rule 25.5 K above ambient (set once on healthy dev data).

## Screens

| screen | episode | instant / window | what feeds what |
|---|---|---|---|
| s1 plant view | leak05 (M01); M02..M06 normal replays | now = 81.0 h (onset 73.01 h + 8 h), trends 51–81 h | module table: tag P/T, compressor state, `static_alarm` of each episode at 81.0 h; M01 tag table: all 8 `tags` at 81.0 h; trends: `raw_pressure_bar`, GH2-TT-101, GH2-AT-101, valve/compressor states, `static_alarm`; no HYDRAI data and no onset marker |
| s2 with HYDRAI | leak05 | same window | left panel as s1; inventory line `compensated_inventory_kg`; leak-rate line and band `leak.rate_kgh/lo/hi` (drawn only where the replay has an estimate); markers: onset 73.01 h (`timelines.onset_h`), HYDRAI alert 73.333 h (`timelines.agent_alert_h[0]`); table: HYDRAI +0.32 h, static alarms none (`timelines.static_alarm_h` empty over the whole 14-day episode), operator proxy 95.75 h = +22.74 h (`timelines.operator_15min_h`, first value at/after onset); gap = 95.75 − 73.333 = 22.4 h |
| s3 alert detail | leak05, `decisions[0]` (first alert, 73.333 h, tier critical) | | class `class_name_*` and `posterior[3]` = 0.999; leak rate 7.44 kg/h (3.82–11.05) and orifice 0.46 mm (0.29–0.65) = `leak_estimate`; released 0.6 kg = `released_kg` (inventory tool estimate); action and reason = `procedure.action_*` / `reason_*`; "approved after 5 min" = `events[0].approval_s − t_watch_s`; decision-history table = `decisions[0..5]` (minutes after onset, rate, interval, released); chart = tick `leak`; evidence rows = trace results of T2, T9 (twin replay, twin fit), T12 as text or as RMS errors from `estimate.rms_error_*` |
| s4 reasoning trace | leak05, `decisions[0]` | | stepper times: SUSPECT/INVESTIGATE = `t_suspect_s`/`t_watch_s` (73.33 h), DECIDE = decision `t_s`, AWAIT_APPROVAL = `approval_s` (73.42 h), CLOSE = `closed_s` (193.7 h); FOLLOW_UP text states the follow-up schedule coded in the orchestrator; table = `trace[]` (tool, verdict, runtime_ms) with one-line results: text of T1, T2, T12 as returned; T9 as "pressure error a bar against b bar for a healthy vessel" from `estimate.rms_error_hypothesis/healthy` and `fields.window_min` (the verifier's own quoted leak rate is not repeated because it differs from the inventory tool's); T11 from `estimate.hold_duration`; T10 only "forecast computed, not shown" |
| s5 who warned when | leak05 | 0–24 h after onset | HYDRAI +0.32 h and 2.5 kg; operator proxy +22.7 h and 191.4 kg; static alarms: none; gap 22.4 h; kg = twin ground truth (see above) |
| s6 fleet | leak025 for M01; M02..M06 normal replays | 100.0 h | per tile: tick values at 100.0 h (`raw_pressure_bar`, GH2-TT-101, compressor state, `compensated_inventory_kg`, `static_alarm`, `agent.score` with its thresholds, `agent.state`, class); M01 is in tier `alert`, FOLLOW_UP; the other five are tier none, MONITOR. M01 here is the 0.25 mm episode, not the 0.5 mm one of the other screens |
| s7 intercooler | interc, first alert-tier decision (154.667 h) | gas temperature 131–159 h | class thermal anomaly, `posterior` 0.995; 4.6 K (2.5–6.7) = T3 `estimate.excess_temperature`; diagnosis sentence = T3 `text_*`; static alarm sentence = T12 `text_*`; T3 residual chart = T3 `series.gas_residual_K_last6h_every15min` (15-minute spacing, last 6 h before the alert); gas-temperature chart = tick GH2-TT-101 |

## Left out because the data does not exist or would mislead

* A containment replay did not exist in `output/cgh2_agent_demo/`; one was generated into this folder (M01__containment-leak-3.5mm). Its first decision is "unknown pattern" (open-set), which is not a good picture, so no screen shows it.
* The 0.1 mm leak replay exists and its data is embedded, but none of the 7 requested screens uses it.
* Forecasts (kg lost if unchecked, time to limit) are not shown anywhere: the claims file marks forecast accuracy as not supported.
* Screen 7 shows no timeline and no "after onset" figure: the modelled operator proxy fires first on that episode (replay h 102.0 against HYDRAI at 154.7 h); the T9 verifier's `reject` for the heating hypothesis is not shown either (the T3 diagnosis is).
* No rupture episode is used. Static-alarm detail per limit (PAH, PAHH, TAH, TAHH, H2 alarm, H2 trip separately) is not in the replay (only one combined `static_alarm` flag), so only the combined indicator is drawn.
* IBM Plex fonts are not installed, system fonts are used (Helvetica Neue, Menlo, SF Arabic / Geeza Pro). The smallest text is about 19 px on the 1920 px canvas (about 14 pt at 96 dpi).
