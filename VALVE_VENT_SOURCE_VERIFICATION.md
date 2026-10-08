# Valve / Vent Model — Source Verification Register

Purpose: before adding physically-driven pressure, PCV/PRV and vent state to the
twin, record which source supports each parameter and how deeply it was
verified. Nothing here has been put into code. Same discipline as the cp(T)
fix: a number is "verified" only if I read it at a document, not because a
search summary said so.

Verification levels
- **V1** — primary document text/figure read in this session.
- **V2** — reputable secondary (trade/journal/conference) quoting the primary; primary NOT seen.
- **V3** — existence/scope confirmed only; no values taken from it.
- **U**  — not verified / not found.

Two web-search summaries were wrong about their own sources (the KIT paper is
helium-only; the Camplese paper is fire/high-temperature MLI, not loss of
vacuum). Every entry below was therefore checked against the document itself.

**Revision 2.** Merged the confirmed parts of the second-reviewer addendum v2
(the first addendum is superseded and was not used). Provenance is marked
**(R)** where a number was confirmed by the reviewer's direct fetch and not
re-read by me. Several of that addendum's original claims were retracted and
are deliberately NOT carried here (a gravity-regime distinction between the
MHTB and K-site data, a blanket 5–10× stratification multiplier, point values
read off the Johnson-thesis vacuum figure, a single "~200–250×" vacuum
multiplier, and an industrial-scale regulator deadband). Items nobody has
confirmed are kept in Section 4 as unverified, not dropped.

**Revision 3.** Merged addendum B. KSC reference [9] is resolved and I re-read it
myself (S20, V1). Belonogov and the Johnson-thesis figure remain hard stops.
Two statements in that addendum were not adopted: that S20 "supersedes"
Belonogov (S20 is nitrogen-cooled MLI blankets; Belonogov is a bare hydrogen
surface, so the hydrogen-specific loss-of-vacuum value is still unknown) and
that nothing remaining needs engineering input for physics reasons (see
`ENGINEER_QUESTIONS_VALVE_VENT.md`).

**Revision 5.** Merged addendum D (reviewer-read sources, marked **(R)**). I tried
to verify the one set of numbers that would feed the vacuum ladder (S24) and
could not reproduce them; they are NOT used. Also corrected the 75% fill cap:
it is a first-fill-of-a-warm-tank limit, unverified, renamed
`first_fill_max_fraction`.

**Revision 4.** Merged addendum C: the first hydrogen-specific loss-of-vacuum
data (S21, S22). I read the key tables of both papers myself (V1). The
addendum conceded both of the earlier pushbacks; I did not adopt its
"9,000–20,000×" headline as the figure for a tank, because it comes from a
flowing-LH2 hose. See Finding 1 for the corrected framing.

## 1. Source register

| ID | Source | Access | What I verified | Level |
|---|---|---|---|---|
| S1 | Hastings et al., *Spray Bar Zero-Gravity Vent System for On-Orbit LH2 Storage*, NASA/TM-2003-212926 (Oct 2003) | NTRS PDF, full text read | MHTB tank: 18.09 m³, 35.74 m², foam+MLI. Measured heat leak (Table 2), liquid saturation pressure rise rates after lockup (Table 5), 6.9 kPa (1 psi) vent control band. Tests ran at normal gravity in the MSFC Test Stand 300 thermal-vacuum chamber (the title refers to the vent hardware's intended use) | V1 |
| S2 | Petitpas (LLNL), *Boil-off losses along LH2 pathway*, LLNL-TR-750685 (OSTI 1466121, Apr 2018) + DOE FCTO webinar slides (26 Jun 2018) | OSTI record; slides read (1–22) | Report: abstract only (V2). Slides: Dewar boil-off flow-meter data (s.18), heat-entry estimate (s.9), LH2 trailer relief hierarchy plate (s.14), vent behavior in transfers (s.10–11) | V1 slides / V2 report |
| S3 | Fesmire, Augustynowicz, Scholtens (NASA KSC), layered composite insulation paper, NTRS 20130012851 | NTRS PDF read | States degraded vacuum to 100 millitorr raises MLI heat flux from ~1 to ~100 W/m², citing its own ref [9]. Ref [9] is now read (S20): the primary figure is ≈60× (≈52 W/m²), so this "~100 W/m²" was an approximation | V2, superseded by S20 |
| S4 | Johnson & Fesmire (NASA KSC), *Thermal performance of low layer density MLI using liquid nitrogen*, NTRS 20110014015 | NTRS PDF read | MLI coupons, LN2 boil-off calorimeter, 78 K cold boundary: high vacuum (~1e-6 torr) k = 0.07–0.09 mW/m·K (read cleanly); heat flux ~0.25–0.5 W/m² (**OCR-garbled, inferred**, consistent with k); **no vacuum: 122–147 W/m², k 34–37 mW/m·K** | V1 (flux range: OCR-inferred) |
| S5 | Poncet, Duri, Raba (CEA), abstract, European Cryogenics Days 2025 (indico) | Abstract page | Reports ISO 21013-3 loss-of-vacuum flux 3.8 W/cm² (derived from helium), a measured ~9.4 W/cm² for H2 without MLI (Belonogov), and says quantitative H2 data are poor. Belonogov's own numbers and the trace of the ISO value to a 1978 helium test (Lehman & Zahn) are unconfirmed (see S19, Section 4) | V2 |
| S6 | ISO 21013-3:2016 (sizing/capacity) and ISO 21013-1:2021 (reclosing valves) | Listings only; ANSI preview 403 | Scope: capacity cases incl. loss of vacuum / fire; valves ≤ DN150 for cryogenic service. Text paywalled | V3 |
| S7 | ASME BPVC VIII-1 (UG-125/126/134) as summarized by Crowl & Tipler, *Sizing Pressure-Relief Devices*, AIChE CEP (2013) | PDF read | Single device set ≤ MAWP; extra devices ≤ 105% MAWP; accumulation 110% (single, non-fire), 116% (multiple), 121% (fire); spring valves start leaking at 92–95% of set | V2 |
| S8 | API 520/526, effective discharge coefficient Kd = 0.975 (gas) | Blog/web summaries only | Said to be an effective (not certified) value; certified Kd is lower | V3 / U |
| S9 | ISA-75.01.01 / IEC 60534-2-1 control-valve gas flow | Listings + web summaries | Standard exists; Cv/Y/xT form seen only in secondary summaries | V3 |
| S10 | NASA Glenn, *Mass Flow Choking* | Open web page | Choked mass flow equation. **Algebraically identical to workbook Sec. 17.5 choked branch** (both factors = 0.578066 at γ=1.41) | V1 |
| S11 | Barsi & Kassemi, *Self-pressurization behaviour of an LH2 tank in normal gravity*, Cryogenics 48(3–4), 2008 | Abstract via IIF/IIR | Exists; CFD vs experiment. No values extracted | V3 |
| S12 | NASA NSS 1740.16, Safety Standard for Hydrogen | Listings | **Cancelled 25 Jul 2005**, superseded by ANSI/AIAA G-095-2004 — do not cite as current | V3 |
| S13 | Emerson/Cash Valve PBE-2 pressure-builder/economizer manual and data sheet | Reviewer read both documents directly; my own fetch could not extract the text | I did not read them. The reviewer relayed an economizer-vs-pressure-builder setpoint offset at industrial-cylinder scale, which is far wider than this tank's whole normal band, so it is not used. Do not re-attempt these documents expecting new tank-scale numbers | V1 **(R)** for "read", not usable for this tank |
| S14 | Weber et al., *Heat flux in MLI helium cryostats after loss of insulating vacuum*, IOP CS MSE 755 (2020) | Abstract page | **Helium only; no hydrogen values** | V1 (not usable for H2) |
| S15 | Camplese et al., *High-temperature degradation of MLI for LH2 tanks* | docx text read | Fire exposure of a 0.31 m³ vehicle tank; **no loss-of-vacuum heat flux** | V1 (not usable) |
| S16 | Van Dresar, Lin, Hasan, *Self-pressurization of a flightweight LH2 tank: effects of fill level at low wall heat flux*, NASA TM-105411 / AIAA 92-0818 (1992), NTRS 19920009200 | NTRS PDF; text extracted locally and read | 4.89 m³ tank, 14.0 m² internal area, 17-layer MLI, normal gravity. Table 1 quasi-steady pressure rise rates vs heat flux and fill level, with homogeneous-model ratios (table in Section 2a). The 83%-fill rows are from its ref [2] (Hasan et al.) | V1 |
| S17 | 46 CFR §162.018-5 (US Coast Guard relief-valve regulation) | Confirmed by a second reviewer's direct fetch of the regulation text; my own fetch was redirected, so I did not re-read it | Pop tolerance ±3% of set pressure (±2 psi at or below 70 psig); valves close after blowing down not more than 5% of set pressure. A marine regulation, not ASME VIII | V1 **(R)** |
| S18 | Johnson, *Thermal Performance of Cryogenic MLI at Various Layer Spacings*, UCF thesis 2010, NTRS 20100034929 | My fetch failed (PDF over the tool's size limit). The reviewer's two independent figure reads disagreed by ~60× | Heat-flux-vs-vacuum curve shape unverified; no values taken from it | U |
| S19 | Belonogov et al., *Heat transfer with a breakdown of the insulating vacuum in vessels with cryogenic liquids*, Chem. & Petroleum Eng. 14(3), 1978, DOI 10.1007/BF01143860 | Bibliographic ID only (via reviewer); paywalled; a second search route found nothing beyond the DOI | The ~9.4 W/cm² H2 figure (bare surface, no MLI) is known only secondhand via S5. A hard stop without institutional access | U (V2 for the secondhand number) |
| S20 | Fesmire, Augustynowicz, Darve, *Performance characterization of perforated multilayer insulation blankets*, ICEC19 (2003); openly hosted PDF (cdarve.web.cern.ch) | Text extracted locally and read by me | 30-layer perforated MLI (two 15-layer blankets, 4.3 layers/mm), **liquid-nitrogen boil-off cryostat, cold boundary ≈78 K, warm boundary ≈293 K**, 10 vacuum levels from 0.1 to 5000 millitorr. **0.87 W/m² at 0.0015 Pa; heat transfer "about 60 times greater" at 13.33 Pa (100 mtorr)**, i.e. ≈52 W/m². Heat-flux values at the other vacuum levels are in a figure I did not read. Nitrogen-cooled, not hydrogen | V1 |
| S21 | Goff, Wray, Coldrick, *Vacuum Failure Experiments on a Liquid Hydrogen Tank*, Hydrogen Safety 3(1), 97–114 (2026), DOI 10.58895/hysafe.46 (open access, CC BY 4.0) | Open PDF; text extracted locally; key sections and tables read by me | **Hydrogen.** 1.5 m³ inner tank, inner area 6.69 m², vacuum deliberately failed with nitrogen as the air surrogate at a *flow-controlled* 871–1,346 L/min. Heat delivered by the nitrogen: **9.501–14.682 kW**, stated as an upper bound (assumes all N2 condenses/freezes at the tank bottom), implying boil-off 0.021–0.033 kg/s. Boil-off estimated from the vent and level data: **0.013–0.019 kg/s** (level-slope extremes 0.008–0.024). ISO 21013-3 predicts 30 kW / 0.068 kg/s, which is 2.6–3.6× above the measured flow (the standard is conservative here). MLI was damaged during the experiments | V1 |
| S23 | Yu, Xie, Zhu, Yu, Li, *Design and Optimization of the Insulation Performance of a 4000 m³ Liquid Hydrogen Spherical Tank*, Processes 11(6), 1778 (2023), DOI 10.3390/pr11061778 | Reviewer-read; not read by me | **Simulation (CFD/analytical), not measured.** LH2 boil-off vs vacuum: 1e-3 Pa → 1.24e-4 %/day; 1e-1 Pa → 3.31e-4; 1.34 Pa → 2.05e-3 (MLI); 13.3 Pa → 7.45e-3 (microspheres). "Heat leakage increased rapidly when the vacuum was >1 Pa." Reported as %/day on a 4000 m³ sphere, so not convertible to W/m² without geometry | V1 **(R)** |
| S24 | Sumner & Maloy, NASA TN, Lewis (July 1971), *Transient Thermal Performance of MLI Systems During Simulated Ascent Pressure Decay*, NTRS 19710021246 | PDF text extracted locally by me; Table I garbled | LH2 calorimeter, 30-layer MLI **purged with nitrogen or helium**, three insulation systems. Space-hold heat flux 0.44–1.6 W/m²; ground-hold up to 325 W/m². The addendum's rungs (1.33 Pa → 11.5, 13.3 Pa → 64.3, 133 Pa → 128, 244 Pa → 140 W/m²) **could not be reproduced**: my reading of Table I gives roughly 30–95 W/m² near 0.01 torr (1.33 Pa) depending on system, ~120–200 W/m² near 1 torr, ~110–165 near 750 torr. Heat flux at one pressure varies several-fold between systems | Existence V1; ladder values unverified, not used |
| S25 | Chart Industries Perma-Cyl 5500 LH2 vessel manual/datasheet | Reviewer-read; not read by me | Top fill via spray header, operated as a no-vent fill once pre-chilled. Pressure-build regulator opens at 75 psi, economizer vents at 90 psi, primary relief 250 psi, thermal relief 275 psi (≈6–19 bar, a much higher band than the twin's) | V1 **(R)** |
| S26 | EU HIAD incident records (8 cryogenic/hydrogen cases) and an LH2 road-tanker over-pressurization record | Reviewer-read; not read by me | Icing/freezing-induced valve sticking (open or closed) in 4 of 8 cases; vent-line/backpressure design flaws recur as what makes a valve fault serious. Tanker: post-fill 8 psig, rising ~2–6 psig/h under quiescent boil-off to 30 psig before a controlled vent. Non-statistical sample; the tanker is not a fixed module | V1 **(R)** |
| S27 | OREDA-derived PSV fail-to-open ≈2.1e-6 /h (via a citing paper); German chemical-plant safety-valve audit (6% of assessments show vent-line pressure-loss defects, trending up) | OREDA paywalled; others reviewer-read | Generic valve reliability, not cryogenic- or hydrogen-specific. No public mode-specific (stuck-open / stuck-closed / leak) rates exist for cryogenic hydrogen valves (reviewer, citing HyCReD) | V2 / V1 **(R)** |
| S22 | Goff, Newton, Wray, Rattigan, Vizma, Lyons, *Failure of the vacuum in a vacuum insulated hose while flowing liquid hydrogen*, IChemE Hazards 34 (SS No. 171, 2024), paper 111 | Open PDF; text extracted locally; Table 1 and discussion read by me | **Hydrogen, an accidental failure** during ZEST transfer experiments (not a controlled test): 20 m flexible hose, 25 mm bore, 30-layer MLI, LH2 flowing at 5.5–6 barg and 25–27 K. Heat flux derived from the change in flowing-fluid density, with a concurrent leak confounding it. Table 1: **averaged 3.18 kW/m² (with leak, 80 g/s) to 7.23 kW/m² (without leak, 55 g/s)**; "complete evaporation" 11.1 and 161 kW/m², which the authors say likely overestimates. Heat-transfer coefficient 11.7–26.7 W/m²K averaged; they suggest modeling with values towards 50 W/m²K | V1 |

## 2. Parameter register

| # | Model parameter | Evidence | Level | Notes / who decides |
|---|---|---|---|---|
| P1 | Healthy heat flux, MLI/foam LH2 vessel | MHTB: 20.2 W / 35.74 m² = **0.57 W/m²** (≈0.35 %/day at 90% fill, lab); high-leak config 54.1 W = 1.51 W/m². KSC MLI coupon ~0.25–0.5 W/m² (S4). Twin baseline: 9.2 W / 26.1 m² = **0.35 W/m²** | S1 V1, S4 V1* | Twin's Sec. 7 baseline sits inside the lab range. LLNL field Dewar (S2 s.18) measured ≈3.5 kg/day quiescent, 6–8 kg/day after a delivery (≈18–36 W equivalent) — higher, but not normalized for size/fill (not extracted) |
| P2 | Closed-tank self-pressurization, **flux-dependent** | K-site (S16): **0.223 kPa/hr at 0.35 W/m²** (83% fill) rising to 2.7–3.8 kPa/hr at 2.0 W/m² and 6.1–8.2 kPa/hr at 3.5 W/m² (Section 2a). MHTB (S1), liquid saturation pressure after lockup: 0.31 / 0.29 / 0.50 kPa/hr at 20.2 / 18.7 / 18.8 W (≈0.5 W/m²; 90/50/25% fill); 0.89 / 0.96 kPa/hr at 54.1 / 51.0 W | S16 V1, S1 V1 | Healthy operation is a **days-scale** process (≈135 h for 1.2→1.5 bar at the twin's healthy flux); a fault that raises flux 6–10× gives **hours** (≈4–11 h). The two datasets agree in magnitude at low flux but measure different quantities (MHTB: bulk liquid saturation pressure with mixing; K-site: ullage pressure), so they corroborate each other rather than being interchangeable. The twin needs a flux-dependent pressurization rate, not a fixed ramp time |
| P3 | Pressure control band / hysteresis | MHTB vent control band **6.9 kPa (1 psi)** (131–138 kPa) | S1 V1 | The deadband analog at this tank's scale (the twin's whole normal band is 0.5 bar). MHTB's vent system is a thermodynamic vent system, not a ground PCV, so this is an analog for hysteresis width. Ground PCV deadband: U — engineers |
| P4 | PRV set pressure, accumulation, tolerance, blowdown | Set ≤ MAWP; max relieving pressure 110% (non-fire) / 116% / 121% (fire) (S7). Pop tolerance ±3% of set (±2 psi at or below 70 psig); blowdown not more than 5% of set (S17) | S7 V2, S17 V1 (R) | Twin MAWP 6.0 bar(a) ⇒ ≤ 6.6 bar(a) non-fire, ≤ 7.26 fire. S17 is a marine regulation, so it is a defensible magnitude for tolerance/blowdown, not the ASME VIII text. ASME primary not read |
| P5 | Operating margin below relief set | Leak onset 92–95% of set (S7). LH2 trailer plate: max offloading 135 psig, main safety 150 psig (=90%), rupture disc 190 psig (=127%) | S7 V2, S2 s.14 V1 (photo) | Plate is a trailer, not a stationary tank — relative ratios only |
| P6 | Relief-valve flow coefficient | Kd 0.975 effective (API); certified values lower | S8 V3/U | Needs the actual valve datasheet |
| P7 | Vent/leak flow equation | Choked equation verified (S10) and identical to Sec. 17.5. Unchoked (subsonic) branch not separately verified here | S10 V1 (choked) | |
| P8 | PCV flow vs position | ISA/IEC Cv form exists; simpler to model as effective orifice area × position using P7 | S9 V3 | Engineers: valve Cv/curve |
| P9 | Degraded / lost insulating vacuum heat flux | 1 → ~100 W/m² between 0.1 and 100 millitorr (S3, N2 gas, ref [9] unseen). MLI no-vacuum 122–147 W/m² (S4, LN2 78 K boundary). ISO 21013-3 3.8 W/cm² = 38,000 W/m² (helium-derived, via S5). H2 without MLI ~9.4 W/cm² (S5, Belonogov unseen). CEA authors: "H2 data are poor" | S3 V2, S4 V1, S5 V2; hydrogen: S21 V1, S22 V1 | **Hydrogen data now exists for the severe end only** (full loss with air ingress): tank, ≈0.9–2.2 kW/m² (S21, converted from kW over the 6.69 m² inner area; ≈×2,500–6,200 the twin's healthy 0.35 W/m²); flowing hose, 3.2–7.2 kW/m² averaged (S22; ≈×9,000–20,500). That is roughly 6–60× above the nitrogen no-vacuum rung. **No hydrogen data for soft vacuum.** **Spread of ~3 orders of magnitude; no single study-backed value, point multiplier or fitted curve exists.** Use a coarse severity ladder with engineering-chosen rungs, bounded by **S20 (soft vacuum: ≈52 W/m² at 13.33 Pa, ≈60× that blanket's high-vacuum 0.87 W/m²; V1)** and **S4 (no vacuum: 122–147 W/m²; V1)**. Against the twin's healthy 0.35 W/m² that is ≈×149 and ≈×350–420. Both are nitrogen-cooled MLI test articles, not hydrogen; the hydrogen-specific value is still unknown (S19). A third source (S18) could not be read reliably and is not used |
| P10 | Vacuum gauge location/range | Not specified. KSC "cold vacuum pressure" is measured at the cold boundary inside the blanket | U | Engineers — jacket gauge location matters for mapping gauge reading → heat flux |
| P11 | Vent/boil-off flow and valve-position instrumentation | LLNL measured Dewar boil-off with a mass flow meter and found it more accurate than inferring from level (S2 s.18). Handoff Sec. 10 lists "valve/regulator state" as a context signal | S2 V1; handoff | Meter accuracy, whether positions are instrumented: U — engineers |

\* flux range for S4 recovered from garbled OCR; k-values read cleanly.

### 2a. Self-pressurization vs heat flux — K-site, S16 (Table 1)

4.89 m³ tank, 14.0 m² internal area, 17-layer MLI, normal gravity, quasi-steady
rates, steady-boil-off starting condition. Column values were read from
extracted text of a scanned page; they agree with the paper's own prose
(ratios 1.4–1.5 and 1.6–1.7 at 29/49% fill; 2.4 and 3.1 at 83%).

| Heat flux (W/m²) | Fill (%) | Tank pressure (kPa) | Measured dP/dt (kPa/hr) | Homogeneous (kPa/hr) | Measured ÷ homogeneous | Time for 30 kPa (1.2→1.5 bar) |
|---|---|---|---|---|---|---|
| 0.35 (≈4.9 W) | 83 † | 121–128 | **0.223** | 0.198 | 1.13 | ≈135 h (5.6 d) |
| 2.0 (≈28 W) | 29 | 159–172 | 3.82 | 2.73 | 1.40 | ≈7.9 h |
| 2.0 | 49 | 145–159 | 2.72 | 1.86 | 1.46 | ≈11.0 h |
| 2.0 | 83 † | 159–172 | 3.47 | 1.46 | 2.38 | ≈8.6 h |
| 3.5 (≈49 W) | 29 | 186–200 | 8.21 | 4.83 | 1.70 | ≈3.7 h |
| 3.5 | 49 | 186–200 | 6.07 | 3.71 | 1.64 | ≈4.9 h |
| 3.5 | 83 † | 186–200 | 8.14 | 2.63 | 3.10 | ≈3.7 h |

† from the paper's ref [2]. At fixed 83% fill, a 5.7× flux increase gives a 15.6×
rate and a 10× increase gives 36.5× — super-linear. Caveats: (a) the high-flux
tests ran at 145–200 kPa, above the twin's 120–150 kPa band, so the 30 kPa times
are approximate; (b) early transients after lockup run faster than these
quasi-steady rates (the paper says so; magnitude not extracted); (c) the K-site
surface-to-volume ratio (14.0/4.89 = 2.86 m⁻¹) is close to the twin's
(26.1/10 = 2.61 m⁻¹), so flux-based transfer needs only a modest geometry
adjustment. The stratification ratio is 1.13 at the twin's healthy flux and
1.4–3.1 at 2–3.5 W/m², not a large fixed multiplier.

## 3. Findings that affect the existing twin (flagged, not fixed)

1. **Vacuum-degradation scenario is inconsistent with the literature — direction
   confirmed, magnitude not.** The twin applies ×2.5 heat leak while the jacket
   reading rises to 500 Pa (3.75 torr). Against the twin's healthy 0.35 W/m²,
   MLI with no vacuum at 122–147 W/m² (S4, V1) is ≈×350–420 (3.2–3.8 kW vs ~9 W),
   and a soft-vacuum rung of ≈52 W/m² at 13.33 Pa (S20, V1; "60×" that
   blanket's own baseline) is ≈×149. The two V1 rungs are now mutually
   consistent in order, and both are orders of magnitude above ×2.5, but they
   come from different test articles, so no single multiplier or curve is
   defensible. The twin's 500 Pa endpoint (3.75 torr) lies between the soft
   and no-vacuum rungs. Replace the point multiplier with a coarse
   healthy / soft-vacuum / no-vacuum severity ladder, rungs chosen by
   engineers. (Caveat in P10: gauge location.)

   **Hydrogen data (S21, S22) says the nitrogen-based upper rung is probably
   an underestimate, not merely unconfirmed.** A hydrogen tank with its vacuum
   failed delivered about 0.9–2.2 kW/m² (≈×2,500–6,200 the twin's healthy
   flux), and a flowing LH2 hose about 3.2–7.2 kW/m² (≈×9,000–20,500), versus
   ≈×350–420 from the nitrogen coupons. On the twin's 26.1 m² tank that is
   roughly 23–190 kW, i.e. 3–25 kg/min of boil-off (about 3 h down to under
   half an hour for ~600 kg), not the ≈3.5 kW of the nitrogen rung. Caveats,
   all of which stay open:
   - S21's heat flow is an upper bound tied to the *imposed* nitrogen inflow;
     the heat actually implied by the measured boil-off is lower (the 0.9 end).
     The flux therefore depends on the air-ingress rate, which a real breach sets.
   - S22 is an accidental failure in a flowing hose with a concurrent leak. Its
     "complete evaporation" figures (11.1 and 161 kW/m²) are described by the
     authors as likely overestimates; the averaged 3.2–7.2 kW/m² are the
     defensible range, and a 25 mm hose is not a tank jacket.
   - Neither paper gives a jacket-pressure progression, so **there is still no
     hydrogen data for the soft-vacuum rung.**
   - ISO 21013-3 predicts 2.6–3.6× more than S21 measured, so a relief design
     built on it is conservative against this tank.
2. **Pressure time scale is flux-dependent.** Healthy: ≈135 h from 1.2→1.5 bar
   (K-site, 0.223 kPa/hr at 0.35 W/m²; MHTB agrees in magnitude at ≈0.5 W/m²).
   Heat flux 6–10× above healthy: ≈4–11 h (Section 2a). The twin's pressure
   wanders ±0.2 bar over minutes and its thermal fault ramps last 2–15 minutes,
   which is too fast under either condition; minute-scale events come from
   operations (fills, valve actions), not thermal faults.
3. **Workbook Sec. 17.2 has the PCV open at the 2.0 bar(a) warning level** while
   the normal band tops out at 1.5. Real practice (S1 control band, S7
   operating margin) puts venting at the top of the normal band, making 2.0 the
   sign of a venting failure. The MHTB 6.9 kPa band (P3) is the deadband analog
   at this tank's scale. Engineering decision.
4. **Sec. 7 baseline (0.30 %/day) is corroborated** at the lab end: MHTB 0.35 %/day,
   0.57 W/m² vs twin 0.35 W/m². Field Dewar data (S2) are higher but not normalized;
   no change recommended until normalized.
5. **Sec. 17.5 choked-flow equation is verified** against NASA Glenn (S10).
6. **NSS 1740.16 is cancelled** — do not cite it as current.
7. **The twin's vacuum channel cannot see the regime that matters.** S20's healthy
   vacuum is 0.0015 Pa and a 13.33 Pa jacket already means ≈60× the heat flux.
   The twin's healthy jacket reading is 0.3–2.0 Pa (hundreds of times higher than
   S20's healthy value), and its Sec. 9 vacuum sensor is specified as 0–1000 Pa
   with ±1% of full scale (±10 Pa), so a 13 Pa degraded condition is barely
   distinguishable from healthy within the sensor's own error. Either the
   gauge type/range assumed in Sec. 9 is wrong for this purpose, or the gauge
   location (P10) hides the real insulation pressure. Ask engineers (Q6).

8. **Fill level decides what a blocked tank does (new, from the rebuilt pressure
   model, `hydrai_twin/ullage.py`).** A closed, unvented tank heated at constant
   volume goes liquid-full at a pressure set by its fill: from a 1.2 bar(a) start,
   75% → 8.7, 85% → 5.5, 90% → 3.8, 95% → 2.4 bar(a) (CoolProp; the
   starting pressure moves these by roughly ±0.2–0.4 bar). The workbook's 85%
   nominal fill therefore reaches liquid-full *below* MAWP 6.0, so the PRV would
   pass liquid; 75% reaches MAWP first and passes vapor. The cap on first fill
   (75%, Chart LH2 manual) is reported to me by the user and not read by me, so it
   is carried as a flagged, UNVERIFIED placeholder (`first_fill_max_fraction`, Q9b).
   Correction supplied by the user: it applies to the first fill of a warm tank
   only; later fills go to the rated maximum, which is an unanswered question.
9. **Validated against sourced data.** The homogeneous real-EOS tank reproduces
   K-site's homogeneous column within about ±6% on all seven rows (S16); the
   model's two-phase and liquid-full pressure-vs-energy slopes match independent
   CoolProp finite differences (0.0117 and 0.1643 Pa/J, a 14× jump at the
   boundary); steady boil-off emerges within ~2% of the Sec. 7 calibration.
10. **Placeholder relief area is too small for hydrogen loss-of-vacuum flux.**
    With the 19 mm reference orifice standing in for the PRV, S21-scale flux
    (≈33 kW) holds near MAWP (6.04 bar(a)), while S22-scale flux (≈190 kW) drives
    the tank liquid-full in ~5 minutes and peaks near 7.8 bar(a) (~130% of MAWP).
    Neither area nor liquid discharge coefficient is sourced (Q2).

## 4. Still unverified (do not hard-code)

Nobody has independently confirmed or refuted these; they stay open, not resolved
either way:

- Belonogov's actual hydrogen loss-of-vacuum numbers (S19 — a hard stop without
  institutional Springer access; only the secondhand ~9.4 W/cm² exists). It is
  **not** superseded by S20 (nitrogen-cooled MLI). S21 and S22 now give
  hydrogen MLI-in-service data for the severe end, but Belonogov is a bare
  hydrogen surface and stays unread, so it is still not replaced.
- The Johnson-thesis heat-flux-vs-vacuum curve shape (S18) — two figure reads
  disagreed by ~60×; a hard stop until a person reads the chart by eye. No values used.
- The trace of ISO 21013-3's 3.8 W/cm² to a 1978 helium test (Lehman & Zahn).
- Heat-flux values at the other nine vacuum levels in S20 (they are in a figure
  I did not read).
- The 75% first-fill cap attributed to Chart's LH2 manual (reported to me, not read;
  applies to the first fill of a warm tank only; the rated maximum fill is unknown, Q9b).
- S23 (Yu et al.), S25 (Chart datasheet), S26 (HIAD records), S27 audit: reviewer-read only;
  I did not independently read them.
- S24 numbers: not reproduced (see source row); not used for the ladder.
- Liquid discharge coefficient (0.65) and any flashing correction for liquid relief.
- Any hydrogen data for the soft-vacuum / degraded rung, and any hydrogen
  jacket-pressure → heat-flux progression (S21 and S22 cover sudden full loss only).
- Resolved this revision: KSC ref [9] (now S20, V1).

Not read at the primary text: ASME BPVC VIII-1 and ISO 21013 (S6, S7 are
secondary); API 520/526 Kd and its blowdown conventions (S8; the marine
regulation S17 covers tolerance and blowdown magnitudes only); ISA/IEC
control-valve equations (S9); Barsi & Kassemi numbers (S11); the unchoked
(subsonic) orifice branch.

## 5. Questions only engineers can answer

Shrunk to the items literature cannot settle; see
`ENGINEER_QUESTIONS_VALVE_VENT.md` (nine questions, each with a placeholder to
confirm or replace). Resolved by sources and removed from the list: pressure
time scale (flux-dependent, Section 2a), stratification factor at this scale,
the PRV tolerance/blowdown magnitudes (S17), the deadband analog (P3), and the
soft-vacuum heat-flux rung (S20).
