# HYDRAI valve / vent model — questions for the engineering team

**Context.** We are rebuilding the digital twin so pressure follows from heat
leak, venting and valve action, instead of the current random pressure process
(which has no valve or vent state at all). Literature has settled the physics
we could settle (how fast pressure rises, how heat leak grows as insulation
vacuum degrades, relief-valve tolerance magnitudes). What remains is specific to
*your* tank, valves and instruments. Sources and verification levels are in
`VALVE_VENT_SOURCE_VERIFICATION.md`.

**How to answer.** For each item: confirm the placeholder, replace it, or say
"unknown". Anything unconfirmed stays flagged as a placeholder in the twin and
in any dataset built from it. "Unknown" is a fine answer; we would rather
know than guess.

Today's workbook values for reference: normal band 1.0–1.5 bar(a), warning
2.0, critical 3.0, MAWP 6.0, healthy boil-off 0.30 %/day (≈9 W, ≈0.35 W/m²
for the 10 m³ module).

---

## A. Control and relief

**Q1. When does the pressure control valve (PCV) open, close and reclose in normal operation?**
Workbook Sec. 17.2 says the PCV opens at the 2.0 bar(a) warning level, but the
normal band tops out at 1.5 bar(a), so the PCV would never hold the band.
- *Why:* sets the pressure cycle, the vent frequency, and what "2.0 bar(a)" means (normal action, or the PCV failing to hold).
- *Placeholder:* opens at the top of the normal band (≈1.5 bar(a)) and recloses ≈0.07 bar lower (≈1.43), with 2.0 bar(a) meaning venting failed. **No clean match exists in the literature.** There are three imperfect analogs: a NASA vent control band at the right scale but a different mechanism (6.9 kPa), an industrial-gas regulator pair at the right mechanism but far too wide a gap for this tank (the figure is not used), and a commercial LH2 vessel (pressure-build regulator 75 psi, economizer 90 psi, primary relief 250 psi) with the right fluid but a pressure band of about 6–19 bar, where only the proportion (economizer about 20% above pressure-build) could transfer. This stays an engineering judgment for you, not a research gap.
- *Also:* does the tank have a **pressure-building circuit** (a vaporizer that raises pressure when it drops, as on the commercial vessel)? Without one, discharging liquid pulls pressure down. The twin's placeholder adds one that engages below about 1.10 bar(a).

**Q2. What is the pressure relief valve (PRV) arrangement?**
Set pressure, number of devices (single or multiple, any rupture disc), valve model/datasheet with certified discharge coefficient or orifice area, pop tolerance, blowdown.
- *Why:* sets where the twin's worst-case pressure stops and how the relief flow is computed. **Relief capacity is the governing question for severe vacuum loss.** With the placeholder relief area (the 19 mm reference orifice, about 283 mm², which is not a design value), a loss-of-vacuum at the hydrogen-tank flux (about 33 kW) holds at 6.04 bar(a), but at the flowing-hose flux (about 190 kW) the tank goes liquid-full within about 5 minutes and pressure peaks near 7.8 bar(a), about 130% of MAWP and beyond the 110% accumulation limit. Please also say whether the PRV is rated to pass liquid, since a liquid-full tank forces it to.
- *Placeholder:* one PRV set at MAWP 6.0 bar(a); ±3% pop tolerance and blowdown not more than 5% of set (magnitudes from a marine relief-valve regulation, not ASME VIII); accumulation to 110% of MAWP (secondary source); 19 mm-orifice relief area and a 0.65 liquid discharge coefficient, both unverified stand-ins.

**Q3. Where does vented boil-off go, and how big is the vent path?**
Atmospheric vent stack, or recovery to a header (workbook Sec. 17.4 flags a possibly shared header across modules)? Line size, any back-pressure, vent capacity.
- *Why:* determines vent flow for a given valve position, and whether one module's venting can affect the others.
- *Placeholder:* each module vents independently through an effective orifice (discharge coefficient 0.62, area to be set).

## B. Faults

**Q4. Which valve and vent faults are credible, and worth simulating?**
Candidates: PCV stuck closed; PCV stuck open or leaking; blocked or iced vent line; PRV simmering or leaking. Add or strike any, and rank by how likely or serious you consider them.
- *Why:* this decides what scenario 4 ("abnormal pressure rise") physically is. Today it is only a shifted pressure target with no mechanism, which is why it cannot be told apart from insulation degradation.
- *Placeholder:* ranked from real incident records, not methodology alone: **icing- or freezing-induced valve sticking (open or closed) was the most recurrent mechanism (4 of 8 incident records read), and vent-line or back-pressure design flaws recur as what turns a valve fault into a serious event.** So the twin simulates PCV stuck closed (icing) and a severely blocked vent line as the pressure-rise causes. Stuck open is not simulated as a labeled scenario yet (the taxonomy has no "pressure low" class). The sample is small and non-statistical, and no public mode-specific failure rates exist for cryogenic hydrogen valves; a generic safety-valve fail-to-open rate of about 2e-6 per hour exists but is not hydrogen-specific.

## C. Instrumentation

**Q5. Which of these are measured, and with what range, accuracy and rate?**
PCV position or command; vent mass flow (a boil-off flow meter); vent-line pressure/temperature; PRV lift or discharge indication. Also: where are the pressure and temperature sensors relative to the liquid and vapor (this affects how much stratification the readings show)?
- *Why:* anything the detector can see must exist in the plant. The handoff expects "valve/regulator state"; a field LH2 study found a flow meter more accurate than inferring boil-off from level.
- *Placeholder:* none. We would rather not invent instrument specs.

**Q6. What does the vacuum gauge look like?** *(stays OPEN)*
Type, range, accuracy, sampling, location (jacket pump-out port or inside the insulation), and the normal reading in healthy service.
- *Why:* the workbook specifies 0–1000 Pa, ±10 Pa. Literature healthy vacuum is about 0.0015 Pa, and 13 Pa already means roughly 60× the heat flux, so a ±10 Pa linear gauge cannot tell healthy from degraded. The twin's current healthy value (0.3–2 Pa) is also hundreds of times higher than that reference.
- *Placeholder (default, UNVERIFIED):* a log-scale Pirani/thermocouple-class gauge, error ±20% of reading plus a 0.05 Pa floor, range 0.1 Pa–1e5 Pa, 10 s sample. The Sec. 9 linear 1% FS gauge is kept as `vacuum_mode="spec"`. Visibility of a soft-vacuum step (`scripts/vacuum_visibility.py`): +13 Pa on a 1.15 Pa jacket is 35 sigma on the log gauge and 7 sigma on the Sec. 9 gauge against the unit's own baseline; against the fleet, with no per-unit baseline, the log gauge separates it (14 Pa vs at most 2.4 Pa healthy) and the Sec. 9 gauge does not (6.5–22.5 Pa vs up to 10 Pa healthy).

## D. Insulation and heat leak

**Q7. What insulation do the tanks have, and what is the measured heat leak?**
Insulation type (perlite, MLI, foam+MLI), acceptance or measured boil-off (%/day or W) at what fill level.
- *Why:* confirms or corrects the 0.30 %/day baseline (about 0.35 W/m²). A NASA lab tank with foam and MLI measured about 0.57 W/m²; a field Dewar measured higher.
- *Placeholder (changed twice; now):* default **0.30 %/day** (`PHYSICAL_DEFAULT_BOILOFF_MODE = "baseline"`), the workbook Sec. 7 ground truth. Reason: Sec. 7 cites real tanks of this size at 0.3–0.6 %/day, and at the handoff's 0.10 %/day a healthy tank first vents 19 d after a fill and pressure faults are weakly visible in 14-day episodes. **0.10 %/day (the handoff and workbook Sec. 10 spec value) is kept as the spec switch** (`"target"`); each manifest records the mode. Still please confirm which is the as-built expectation (the 0.05–0.10 %/day figures were flagged in Sec. 7 as optimistic for a 10 m³ tank). Timescales for both tiers are in `output/reports/timescale_tables.txt`.

**Q8. What counts as degraded and lost insulating vacuum, and how does it fail?**
Jacket pressure thresholds or alarm levels; credible failure modes (slow leak-up or outgassing versus sudden loss); and the heat flux your relief sizing assumes for loss of vacuum, with its basis (ISO 21013-3 or CGA).
- *Why:* replaces the twin's ×2.5 heat-leak jump with a severity ladder. Nitrogen-cooled MLI blankets give about 52 W/m² at 13 Pa and 122–147 W/m² at no vacuum, versus 0.35 W/m² healthy. **Hydrogen measurements of full vacuum loss are far higher**: roughly 0.9–2.2 kW/m² on a 1.5 m³ hydrogen tank and 3–7 kW/m² on a flowing LH2 hose (Goff et al., 2026 and 2024). **So the nitrogen-based upper rung is probably an underestimate, not just unconfirmed.** On our 26 m² tank the hydrogen figures mean roughly 23–190 kW and 3–25 kg/min of boil-off, which makes relief capacity the governing question. Both hydrogen results have limits: the tank heat flow depends on how fast air enters (a real breach sets that), the hose failure was accidental and in a small-bore flowing line, and **there is no hydrogen data for the soft-vacuum middle of the ladder.**
- *Also please tell us:* the credible air-ingress rate or breach size for a jacket failure (this sets the flux), and the heat flux your relief sizing assumes with its basis (ISO 21013-3 predicted 2.6–3.6× more than the tank measurement, so it may be conservative).
- *More hydrogen context (reviewer-read, not verified by me):* a 4000 m³ LH2 tank simulation shows boil-off rising rapidly once the vacuum worsens beyond about 1 Pa. A 1971 NASA liquid-hydrogen calorimeter study of purged MLI spans the transition regime, but **I could not reproduce the numbers quoted from it**, and in my reading heat flux at one pressure varies several-fold between insulation systems, so it is not used. No single published source bridges healthy to failed for hydrogen; that gap is real.
- *Placeholder:* a ladder of added jacket pressure to heat flux. Linear in pressure below 13.3 Pa (gas conduction in the free-molecular regime), 52 W/m² at 13.3 Pa (nitrogen-cooled MLI), then log-log interpolation to about 1,270 W/m² at atmospheric pressure (hydrogen tank, **flagged as likely still low**). Rung boundaries and the credible jacket-pressure range are for you to choose.

## E. Operation

**Q9. What does normal operation look like?**
How often does the PCV vent in healthy idle? How are fills done (top or bottom, no-vent fill)? What pressure swings do fills and discharges cause?
- *Why:* healthy idle pressure rises over days, so any rapid pressure behavior in normal data comes from operations, and the twin should model them explicitly.
- *Placeholder:* fills and discharges as in workbook Sec. 8. **Fill method (reviewer-read from a commercial LH2 vessel manual): top fill through a spray header, run as a no-vent fill once the tank is pre-chilled**, so the twin models fills as well-mixed (equilibrium) with the vent closed. How often the PCV vents in healthy service is **not published anywhere I or the reviewer could find** (it lives in plant logs); the twin's value (about every 1.3 days at the workbook's 0.30 %/day) is an emergent result of the heat leak, not a measurement. A tanker incident record shows post-fill pressure rising 2–6 psig per hour under quiescent boil-off, but that is a mobile tank with a different heat load, so it is only an order-of-magnitude analog.

**Q9b. What are the first-fill cap and the rated maximum fill?**
The workbook uses 85% nominal and 90% maximum modeled fill (Secs. 2 and 8). I was told Chart's LH2 manual caps the **first fill of a warm tank** at 75%, and that later fills go to the **rated maximum** (stated as 100%). I have not read the manual, so the 75% figure is unverified. **Please tell us the rated maximum fill, and whether the first-fill cap is a procedure for you.**
- *Why:* in a closed tank with no venting, heating makes the liquid expand until the tank is full of liquid, and that happens at a pressure that depends strongly on fill. By my CoolProp calculation, starting from 1.0–1.5 bar(a): **75% fill goes liquid-full near 8.5–9.0 bar(a) (above MAWP 6.0, so relief passes vapor); 85% near 5.2–5.9 bar(a) (below MAWP, so relief passes liquid); 90% near 3.6–4.2; 95% near 2.1–2.7.** So at the workbook's 85% nominal fill, a blocked-vent fault reaches liquid-full before relief lifts. In a healthy tank (PCV working) this never happens.
- *Placeholder (changed):* the workbook spec now governs. Healthy and fault episodes fill to 85% nominal (drawn 85% + 5% × Beta(1, 2.5), never above the 90% maximum); only fills **above 90%** are the labeled `overfill_hydraulic_lock` scenario (placeholder 93%). The unverified 75% first-fill cap is **no longer used as a gate** (it conflicts with the spec's 85% target fill) and stays in the registry as `first_fill_max_fraction`, flagged UNVERIFIED. The liquid-full hydraulic-lock *state* is kept: a closed tank at 85–90% can still go liquid-full (below MAWP at 85%) under a blocked vent plus lost vacuum, but a healthy tank with a working PCV does not. Please confirm which limits apply.

## F. Dashboards, alarms and data quality

**Q10. Which tags exist on the dashboard, at what rate, with what alarm limits, and how is data stored?**
Tag list (which of the Sec. 9 measurements actually exist; are valve position and PRV indication on it, see Q5), the rate each is logged at, the existing static alarm limits (value, direction, on-delay, level), the historian's exception deadbands, compression (deviation, maximum interval), quality-code behavior, and how often instruments go stale, flat-line, read out of range or drop out.
- *Why:* the agent goes onto the existing dashboards, so it may use only those tags, and its headline claims are lead time against **those** alarms and alerts per hour. A fault that shows only on an untagged channel is invisible to it.
- *Placeholder:* the **reference configuration, not a verified Saudi system** (`dashboard_tags.json`; no real Saudi LH2 dashboard is publicly documented): the ten Sec. 9 tags with their stated sample periods (pressure 1 s, outer wall 5 s, H2 0.2 s, flows and strain 0.1 s, vacuum and ambient 10 s), no inner-wall tag, PI-style historian (exception filter 0.1–0.5% of span with a forced point every 600 s, swinging-door compression with a forced point every 8 h, OPC Good/Uncertain/Bad, injected stale/flat-line/out-of-range/dropout faults at low rates). Filters and layout are the reference values; the per-channel deadbands, compression deviation (2× deadband) and fault rates are placeholders. The static alarm limits are the workbook's Sec. 5/6 "simulation threshold" values and are marked **PROVISIONAL** in every report. The reference file lists liquid temperature in K; the spec is in °C, so the twin carries °C.

**Q11. What is the hydrogen alarm, and what detector produces it?**
The workbook gives a 0–100 %vol, ±2% FS hydrogen sensor but no alarm level.
- *Why:* taken as white noise, ±2% FS is about 1 %vol per sample, so a 1 %vol alarm fired in every healthy episode of an early dataset. I did not raise the alarm; the error model was corrected (Q12).
- *Placeholder (default, UNVERIFIED):* a realistic %LFL detector, 0–100 %LFL, ±5 %LFL, 100 %LFL = 4 %vol, T90 10–15 s (first-order lag), H = 20 and HH = 40 %LFL (alternates seen in practice: 10/25 and 25/50; Aramco SAES setpoints are not public). The Sec. 9 spec model (0–100 %vol, ±2 %vol FS) is kept as `h2_mode="spec"`. False-alarm check over 2,000 healthy units × 14 d (`scripts/h2_false_alarm_check.py`, 1-sample, no persistence): realistic mode, worst reading 6.4 %LFL against H = 20, **0 alarms**; spec mode with the zero-referenced workaround, worst reading 0.87 %vol against 0.8, **1 of 2,000 units** alarms (0.0003 events per unit-week), so the workaround has almost no margin; spec mode with the generic 0.5/0.3 split, **989 of 2,000 units** alarm (210 H events per unit-week). The realistic mode supersedes the zero-bias workaround, which now applies to spec mode only. The leak-to-reading dispersion (`h2_dispersion_pct_per_kg_s`) is itself a placeholder, so leak scenarios' alarm timing is not a result.

**Q12. How does each sensor's stated accuracy divide into calibration bias, drift and random noise?**
For each Sec. 9 channel: calibration interval and tolerance, long-term stability (drift per month or year), repeatability/noise, and, for the hydrogen detector, whether it is zero-referenced and its zero-offset and span specifications separately.
- *Why:* Sec. 9 gives only a total accuracy. Spending all of it as per-sample noise (the first model) makes the random error 5× too large and has no slow error at all. The split decides what a trend or slope feature can see: white noise sets short-window visibility, drift sets long-window visibility (table in `PHYSICAL_MODEL_CUTOVER_PROPOSAL.md`).
- *Placeholder:* bias uniform within ±0.5 × accuracy per unit (hard-bounded by the spec), drift Ornstein-Uhlenbeck with 2-sigma 0.3 × accuracy and a 3-day correlation time (clipped at 0.3 ×), random noise sigma 0.1 × accuracy; total bias + drift + 2-sigma noise = 1.0 × accuracy. Hydrogen in spec mode only: bias and drift 0.1 × accuracy each (zero-referenced assumption). Channels faster than the 1 s grid are aggregated (noise / sqrt(n)). All flagged `level="placeholder"`, question Q12, recorded per episode in `meta["sensor_error_split"]`. Level is a DP gauge scaled at the 1.2 bar saturated densities, so its reading is biased by density change with pressure (about −1% at 1.5 bar).
