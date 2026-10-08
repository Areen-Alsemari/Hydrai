# HYDRAI tool agent: claims, supported and not supported

Reference configuration, not a verified Saudi system. Dev = 6 modules, leave-one-module-out (188 episodes). Unseen = 3 modules never used (94 episodes, scored ONCE after the
configuration was frozen: `output/reports/cgh2_agent_freeze.json`). OOD = the low (50 bar) and high (350 bar) classes, scored once, thresholds and tool parameters fitted
on the medium class only. Numbers are k/n over episodes; n is small for most single-severity groups, so read the intervals in the per-class reports, not the medians alone.
Detail: `cgh2_agent_dev.md`, `cgh2_agent_unseen.md`, `cgh2_agent_ood_low.md`, `cgh2_agent_ood_high.md`, `cgh2_agent_lead_times_*.md`, `cgh2_agent_ablation.md`.

The rules for any "earlier" claim were: lead time with its false-alarm cost, split by class and severity, episode counts, bootstrap interval, against the static alarms AND the best
classical detector, the physical floor alongside, with and without the expected-miss leaks. The paired lead-time tables do exactly that.

## Supported

1. **A diagnosis, a size and an action, which the baselines do not give at all.** At the first alert the decided class is correct in 99/124 known-class episodes on dev (80 %) and
   47/62 on unseen (76 %). Static alarms and the classical/learned detectors give no class: for them "time to correct diagnosis" is never. Median time to the first correct
   alert-level diagnosis (dev): sensor fault 0.3 h, leaks 1.3 h, containment 0.0 h, abnormal pressure 4.1 h, thermal 15.8 h, structural 32 h.
2. **Containment, within minutes (the gas detector fires first, the agent ties it in time).** Containment leaks (2-5 mm): detected 18/20 dev, 9/10 unseen, with median delay 0.0 h (a tie
   with the static alarm, which fires within a minute). By +30 min after the first alert: correct class 20/20 dev and 10/10 unseen, isolation advice 20/20 and 10/10, leak-rate estimate
   within a factor 2 of the twin's true rate in 17/20 (dev) and 6/10 (unseen), median estimate/true 0.84 and 0.91. The size comes from the twin fit (T9), not from the inventory filter,
   which is too slow for a vessel emptying in minutes. The first decision (1-2 minutes after onset) is right in only 13/20 dev and 5/10 unseen containment cases.
3. **Small leaks, earlier than the single learned model and far earlier than the static alarms, on dev.** 0.1 mm: 4/6 within 24 h (median 7.0 h, about 2.9 x the 2.4 h floor) against 1/6
   for the learned model (35 h), 0/6 for the static alarms; all 0.1-1 mm leaks: 20/24 against 18/24 for the learned model, and the median kg released before detection is 2.3 against 6.3.
   Alert-level false alarms on dev 0.66/week against 0.46/week for the learned model: the gain is not bought at a lower false-alarm rate, see the operating-curve table in `cgh2_agent_dev.md` (2b).
4. **Thermal and abnormal pressure versus the static alarms.** Thermal: 14/24 within 24 h against 1/24 for the static alarms (dev); 8/12 against 1/12 (unseen). Abnormal pressure: 20/24 against
   14/24 (dev); 12/12 against 9/12 (unseen). Against the single learned model and the best classical detector the median lead is about zero (paired tables), i.e. not earlier, but with a diagnosis.
5. **Union coverage (static alarms OR agent), within 24 h (dev, classes 1-6 and composites): 115/128, against 58/128 for the static alarms alone.** The agent adds 57 episodes the static alarms never
   caught in time; the static alarms catch 4 the agent misses (2 sensor faults, 2 containment).
6. **The agent adds a closed loop that a detector does not have:** tool calls are logged with inputs, outputs and runtimes (mean 5 calls and 133 ms of tool time per investigated event), every number in
   the explanation text comes from a tool output, and the whole thing replays deterministically.

## Partly supported

7. **1 mm leaks: tie in time, correct class and size in the same minutes.** Tie in time with the static alarm (median delay 0.0 h, 5/6 dev, 2/3 unseen). Correct class at +30 min 6/6 on dev but 1/3 on unseen; size within
   a factor 2 at +30 min 5/6 on dev, 0/3 on unseen. Three unseen cases are too few to say more.
8. **Stress leaks 0.03 / 0.05 mm (labelled expected misses).** Within 3 x the first-observable floor: 5/6 and 1/6 on dev (the learned model 0/6, 0/6); 1/3 and 2/3 on unseen (the learned model 1/3, 2/3).
   Within 24 h: 2/6 and 1/6 (dev). Kg released before detection are small in absolute terms (about 3-10 kg) but these leaks are at the edge of what any detector sees.
9. **Sensor faults (spikes on the gas-temperature probe).** The static alarms are faster (12/12 within 24 h, 0.3 h) than the agent (10/12, 0.2 h median where it fires); the agent identifies the probe as the
   culprit (11/12 at the first alert) and the union is 12/12. Subtle slow drift (0.5-2 % FS over days) is NOT evaluated: **0 such episodes in the dataset**; per the instruction, no regeneration was done.

## Not supported

10. **Open-set rejection of unknown patterns.** Composites (two simultaneous faults) are answered "unknown pattern" in only 2/24 (dev) and 2/12 (unseen) cases; the decided class is one of the real components in
    17/24 and 8/12. An isolation forest on the tool features separates composites from single faults at AUC 0.58 (about chance), so no novelty tool (T8) was built.
11. **Structural concern.** 6/12 on dev against 4/12 for the learned model (the static alarms define none); 1/6 on unseen against 3/6 for the learned model. The strain-per-pressure tool (T6) helps on dev but is not robust on unseen.
12. **Rupture.** Scored strictly, 0/2 on dev (M04's dashboard series ramps down 7 minutes BEFORE the onset time, a historian back-interpolation artifact, so the agent alerts before onset; M01's critical alert at onset merges with a false alert exactly
    one hour earlier under the one-hour event-merge rule) and 1/1 on unseen. n = 3 in total.
13. **False-alarm control outside the medium class.** Alert-level healthy false alarms per week: dev 0.66, unseen 1.03, OOD low 2.72, OOD high 1.90 (the single learned model: 0.46, 2.23, 1.70, 0.69). The healthy-calibrated thresholds
    do not transfer to other pressure classes; per-class recalibration on healthy data of that class would be needed.
14. **The forecasts.** Leak forecast of kg released in the next 6 h: median forecast/actual 0.60, the actual inside the stated interval in 29 % of cases (n = 28). Time to PAH: the actual inside the interval in 1 of 10 cases. The
    intervals are too narrow and the numbers are not to be trusted yet.
15. **Earlier than the learned model on thermal, abnormal pressure, containment and 0.25-1 mm leaks.** The medians are equal within noise (paired lead about 0 h with intervals spanning zero); only the diagnosis is new there.
16. **Anything about subtle sensor drift, the gas detector as an independent leak sensor (T7: not built, the dispersion coupling is a placeholder), or the value of the language model.** The LLM mode is a demo; no benchmark number uses it,
    and no claim is made that it improves detection or diagnosis.

## What the agent adds even where it is not earlier

A named class with a probability, a leak-rate or heat-input estimate with an interval, the kg released so far, a forecast (see 14), a hold-test recommendation when a small leak is ambiguous, a bilingual explanation with the physical reason, and a
trace that shows which tool said what. The static alarms and the classical detectors give a bit.

## Known defects, found and reported, not hidden

- Historian back-interpolation: a step after a long quiet period (a rupture, or an injected out-of-range sample) is archived by interpolation from the NEXT archived point, so the dashboard series moves before the event. Needs a regeneration to fix; waiting for the owner's decision.
- 44 of 7,416 forecast outputs (late follow-ups after a vessel has emptied, negative inventory estimate) are non-finite; none is a first-alert decision, so no reported metric is affected.
- The shared LH2 `fit_threshold` degenerates for always-on statistics (threshold 0.0); not modified (LH2 untouched by instruction), the CGH2 code uses `fit_threshold_bounded`.
- `tests/test_cgh2_gas_registry.py::test_usage_is_recorded_...` passes alone but fails in the full-suite order (registry usage recorded by an earlier test); it pre-dates the agent work.


---

# Update: agent versus the static alarms and a modelled operator (new episodes, new table)

Full tables: `cgh2_agent_vs_static.md` (dev, unseen, OOD low / high, recalibrated OOD rows, slow drift; per class and severity), `cgh2_agent_drift.md` (the 12 drift episodes one by one). Detection in these tables = an alarm within 72 h of onset;
lead in hours where both detectors fired, positive = the agent earlier, 95 % bootstrap intervals. The operator is a MODELLED operator (`operator_proxy.py`: looks at the raw dashboard every 15 or 60 minutes, acts when the raw pressure is below the compressor's
working band by more than X or the gas temperature is more than Y above ambient; X, Y set once on healthy dev data at 1 false alarm per week per rule; an 'expert' variant reads the temperature-compensated inventory). It is not a human study.
Healthy false alarms per week, dev / unseen: static A 0.00 / 0.00, static B 1.26 / 1.17, agent alert tier 0.66 / 1.03, operator proxy (15 min) 1.71 / 1.71.

## Supported (new)

17. **0.1-0.5 mm leaks: the agent is earlier than the operator proxy and far earlier than the static alarms, and releases much less gas first (dev).** Static A fires on none of the 0.1 / 0.25 / 0.5 mm leaks (0/18 within 72 h); the agent detects 5/6, 5/6, 6/6.
    Against the 15-minute operator proxy, median lead: 0.1 mm +7.2 h (-21 to +42; n = 5), 0.25 mm +28.4 h (+3 to +56; n = 4), 0.5 mm +26.5 h (+20 to +47; n = 5); kg released before detection, agent vs operator: 2.3 vs 4.8, 4.0 vs 64, 2.5 vs 225.
    Unseen (n = 3 per size, so intervals are mostly undefined): 0.25 mm +4.3 h (n = 1), 0.5 mm +25.6 h (n = 2), kg 6.0 vs 254 at 0.5 mm; the agent detects 2/3, 2/3, 3/3, the static alarms 0/9. The 0.1 mm lead is not established (wide interval on dev, n = 3 unseen).
    Cost: the agent's alert tier costs 0.66 (dev) / 1.03 (unseen) healthy false alarms per week against 1.71 for the operator proxy.
18. **Thermal anomaly versus the static alarms.** External heat: static A detects 4/12, the agent 11/12; where both fired the agent was earlier by a median of 17.4 h (+2.9 to +55.8; n = 4). Intercooler failure: static A 0/12, the agent 10/12. Unseen: external heat 3/6 vs 6/6.
19. **Faults the static alarms never see within 72 h (dev):** stuck-open discharge valve 0/6 (agent 5/6), structural 0/12 (agent 9/12), 0.1-0.5 mm leaks 0/18 (agent 16/18), intercooler failure 0/12 (agent 10/12). Union with static A within 72 h: 0.1 mm 5/6, 0.25 mm 5/6, 0.5 mm 6/6.
20. **1 mm leaks, containment, fire and compressor overrun: a tie with the static alarms (median lead 0.0 h) and a small lead over the operator proxy that comes from its look interval.** 1 mm +1.8 h (+0.6 to +2.0), containment +0.2 h (about 12 minutes), but the kg released before detection is
    0.06 vs 58.6 kg (1 mm) and 0.0 vs 53.3 kg (containment) for the agent vs the operator (dev), because the static-alarm trigger fires in the first minute and the operator only looks every 15.
21. **Per-class recalibration repairs the OOD false-alarm problem (claim 13) without losing detection.** Thresholds re-fitted on healthy data of the class only, cross-fitted by module: agent alert false alarms low 2.72 -> 1.67 per week, high 1.90 -> 0.39; detection within 72 h essentially unchanged (e.g. 0.1-1 mm leaks low 5/6 -> 5/6, high 5/6 -> 6/6). The frozen OOD numbers are untouched; the recalibrated ones are separate rows.

## Not earlier / not supported (new)

22. **Slow sensor drift (new set, 12 episodes: 6 pressure transmitter, 6 gas-temperature probe, 0.5-2 % FS over 5 days): the agent does NOT reliably detect it.** Static A: 0/12 (as expected). Agent: 9/12 with an alarm after onset, but a healthy episode with a pseudo-onset gives the agent an alarm in 58 % of cases (7.0 of 12 expected by chance),
    and only 2/12 agent alerts came after the drift was observable at all. The agent named a sensor fault in 2/12 and the right sensor in 2/12 (one pressure transmitter, one temperature probe). Learned model 5/12 (chance 3.0), static B 11/12 (chance 9.2), operator proxy 12/12 (chance 11.6).
    For 6 of the 12 episodes the ideal-observer floor does not exist (the drift never exceeds 3 sigma of the channel): no per-channel observer could see them; the pressure-strain redundancy (T5) is limited by a strain gauge whose own noise (about 14 bar-equivalent after smoothing) is above a 1-2 % FS pressure drift.
    There is no lead-time claim for drift: the agent was not earlier than anything it was paired with in a way that can be separated from chance.
23. **Thermal anomalies versus the operator proxy: not earlier.** Median lead -0.5 h (-1.4 to +0.6; n = 20) on dev, -2.5 h (-16 to +5; n = 8) on unseen: a modelled operator who looks at gas temperature against ambient is as early as the agent (and more often detects: 23/24 vs 21/24, at 1.7 false alarms per week). The agent's advantage here is the diagnosis and the cost, not the time.
24. **Abnormal pressure versus the operator proxy: a tie** (dev +0.2 h, interval spans zero; unseen +3.5 h (+0.2 to +7.5), n = 10). Compressor overrun -0.3 h, fire 0.0 h, stuck-open valve +21.8 h (n = 2).
25. **Structural concern versus the operator proxy: not established** (dev +7.3 h (-6 to +50; n = 5), unseen +7.1 h (-59 to +11; n = 3)); the agent detects more (9/12 vs 7/12 dev) but the lead interval spans zero.
26. **Stress leaks 0.03 / 0.05 mm, rupture:** no lead over the operator proxy (0.03 mm -3.9 h, n = 1; 0.05 mm no paired cases; rupture 0/2 for the agent on dev, see claim 12).
27. **Sensor spikes:** the agent ties the static alarms (median lead 0.0 h) and is 2.1 h earlier than the operator proxy (+1.0 to +3.5; n = 10, dev); it detects 10/12 within 72 h against 12/12 for both of them.

## Corrections and changes since the freeze (all listed, none changes an agent decision)

- Found: the first one-shot OOD run cached the per-episode fusion probabilities under the episode name, and the low and high sets share names, so the OOD-low report's 'fusion only' row read the high set's probabilities. The agent rows and runs were never affected; the probabilities were rewritten and `cgh2_agent_ood_low.md` / `cgh2_agent_ood_high.md` regenerated (fusion-only false alarms low 2.67 per week, high 1.94).
- Files changed after the freeze: `hydrai_twin/cgh2/episode.py` (slow-drift option, off by default; existing episodes hash-identical), `hydrai_twin/cgh2_agent/replay.py` (viewer: language toggle, who-warned-when timeline), new `operator_proxy.py`, `t10_forecast_consequence.py` (numerical guard: forecasts stay finite when the inventory estimate is not positive; 44 of 7,416 late follow-up forecasts were non-finite, none a first-alert decision),
  and the order-dependent test `test_usage_is_recorded_...` (it now resets the LH2 placeholder usage record; the full-suite order failure was in the test, not in the code). `scripts/cgh2_agent_freeze.py --verify` reports exactly these, plus one file I did not edit: `ml/cgh2_agent.py` (the single learned model of checkpoint 1) was modified on disk at 16:57 by something outside my work (112 lines instead of 110; on reading, the logic is identical to the version I had printed earlier). Every learned-model number in these reports was computed before that time from caches and runs that predate it; nothing reported depends on the change.
- LH2 `fit_threshold` untouched. Nothing committed.
