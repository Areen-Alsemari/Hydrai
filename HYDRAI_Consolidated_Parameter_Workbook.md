# HYDRAI — Consolidated Engineering Parameter Workbook

*Merged from: **HYDRAI** (system definition, envelopes, sensors, fault taxonomy) + **Predictive Hydrogen Storage** doc (temperature-dependent material correlations), per engineering's instruction to pull the T-dependent values from the earlier file's last table.*

**Resolves the open question from the prior handoff: canonical system is confirmed as liquid hydrogen (LH₂), not compressed gaseous H₂.**

---

## 0. Build Readiness — Do You Have Enough to Start?

**Short answer: yes — including the boil-off question, which now has a decided answer rather than an open flag.**

| Component the twin needs | Status |
|---|---|
| System topology, geometry | ✅ Given, arithmetic self-checked |
| LH₂ fluid properties + EOS | ✅ Given + verified against primary source; EOS choice proposed (CoolProp/Leachman) |
| Material properties (fixed + T-dependent: k, cp, CTE, E) | ✅ Verified against NIST, one coefficient error caught & corrected |
| Pressure/temperature envelope | ✅ Given + consistent with real-world LH₂ systems |
| Mass balance + boil-off staging | ✅ Two-tier decision made: 0.30%/day realistic baseline for the AI's ground truth, 0.05–0.10%/day kept as a named future-tech target — see Sec. 7 |
| Filling/discharge flow | ✅ Given |
| Sensor suite (for injecting realistic noise) | ✅ Given, domain-plausible |
| Fault taxonomy (qualitative signatures) | ✅ Given + causal logic checked |
| Leak-size categories (quantitative) | ✅ Proposed default (HyRAM+ ladder), Sec. 17.3 |
| **Leak mass-flow equation** (turns hole size → kg/s) | ✅ Proposed default (standard compressible orifice flow), Sec. 17.5 |
| Wall thickness | ✅ Proposed default with ASME calc, Sec. 17.1 |
| Valve/control logic | ✅ Proposed default, Sec. 17.2 |
| Multi-module coupling | ✅ Proposed default, flag if vent header is shared, Sec. 17.4 |

**Everything has a value and a confidence level attached (Section 15) — nothing is silently assumed.** The distinction that matters: some things are *verified* (checked against a primary source or independent literature), some are *proposed defaults* (grounded in a real code/methodology, but standing in for your team's decision), and boil-off staging is now a *made decision* (Section 7) rather than an open flag — realistic baseline for the AI, honest roadmap target for the pitch. That's not the same as "incomplete." A system with clearly labeled assumptions and reasoned decisions is more defensible than one that looks finished but hides them.

---



## 1. System Definition

| Parameter | Value |
|---|---|
| Storage type | Liquid hydrogen (LH₂), cryogenic |
| Configuration | 6 modules (M01–M06) |
| Tank type | Vacuum-jacketed cylindrical |
| Inner vessel material | 304L stainless steel |
| Insulation | Vacuum + Multi-Layer Insulation (MLI) |
| Outer jacket | Stainless steel |

---

## 2. Geometry (per module)

| Parameter | Value | Unit |
|---|---|---|
| Internal volume | 10 | m³ |
| Internal diameter | 2.00 | m |
| Internal radius | 1.00 | m |
| Cylindrical length | 3.18 | m |
| Wall thickness | 10 (assumption — flagged, not final) | mm |
| Inner surface area | ~26.1 | m² |
| Nominal fill level | 85 | % |
| Maximum modeled fill | 90 | % |
| LH₂ volume at nominal fill | 8.5 | m³ |
| LH₂ mass at nominal fill | ~603–604 | kg |

**Arithmetic self-check (not a literature check, just verifying the numbers agree with each other):** π × (1.00 m)² × 3.18 m = 9.99 m³ ✓ matches the stated 10 m³. 8.5 m³ × 70.97 kg/m³ = 603.2 kg ✓ matches the stated ~603–604 kg. Inner surface area for a flat-ended cylinder of this size (2πrL + 2πr²) = 26.26 m² — close enough to the stated ~26.1 m² that the small difference is plausibly just the head geometry (e.g. slightly domed rather than flat ends), not an error. All internally consistent.

---

## 3. LH₂ Physical Properties (fixed constants)

**Cross-checked against the primary reference:** the current NIST-standard equation of state for hydrogen (Leachman et al., 2009, *J. Phys. Chem. Ref. Data*) gives the critical temperature of normal hydrogen as **33.19 K** — this matches HYDRAI's −239.96 °C (= 33.19 K) *exactly*. That's a strong signal HYDRAI's constants trace back to the correct reference EOS rather than an approximate/rounded source. Molecular weight, NBP, density at NBP, latent heat, and LHV/HHV are all standard, well-established values consistent across every source checked — no discrepancies found.

| Property | Value | Unit |
|---|---|---|
| Molecular weight | 2.016 | g/mol |
| Normal boiling point | −252.76 | °C |
| Critical temperature | −239.96 | °C |
| Critical pressure | ~13.15 | bar |
| Density at NBP | ~70.97 | kg/m³ |
| Latent heat of vaporization | ~0.446 | MJ/kg |
| LHV | ~120 | MJ/kg |
| HHV | ~142 | MJ/kg |
| Flammability range in air | ~4–75 | vol% H₂ |

---

## 4. 304L Material Properties

### 4.1 Point values near 20 K (experimental)

| Property | Value | Note |
|---|---|---|
| Yield strength | 682–1059 MPa | Monitor after 682 MPa; above 1059 MPa, leakage risk increases (material can't return to original state) |
| Tensile strength | 1943–2433 MPa | Destructive |
| Elongation | 32.6–39% | Ductility indicator |

### 4.2 Temperature-dependent correlations (from the earlier engineering doc)

These are the functions to use wherever HYDRAI lists a property as "temperature-dependent" (thermal conductivity, specific heat, thermal expansion), across the tank's operating range (293 K → 20 K):

**Thermal conductivity k(T):**
```
log10(k) = -1.4087 + 1.3982*log10(T) + 0.2543*log10(T)^2 - 0.6260*log10(T)^3
           + 0.2334*log10(T)^4 + 0.4256*log10(T)^5 - 0.4658*log10(T)^6
           + 0.1650*log10(T)^7 - 0.0199*log10(T)^8
k = 10^(log10(k))
```
Reference/sanity-check point from HYDRAI: k ≈ 1–3 W/m·K near −253 °C (with 2.71 W/m·K cited as a reference value).

**Specific heat cp(T):**
```
log10(cp) = 22.0061 - 127.5528*log10(T) + 303.6175*log10(T)^2 - 383.8407*log10(T)^3
            + 277.8344*log10(T)^4 - 119.2458*log10(T)^5 + 30.0031*log10(T)^6
            - 4.1312*log10(T)^7 + 0.2382*log10(T)^8
cp = 10^(log10(cp))
```

**Linear thermal expansion dL/L(T):**
```
dL/L = -2.955e-3 - (3.980e-7)*T + (9.256e-9)*T^2 - (2.022e-11)*T^3 + (1.465e-14)*T^4
```

✅ **Resolved by checking the NIST source directly (trc.nist.gov/cryogenics/materials):** `T` is Kelvin, confirmed by NIST's own equation documentation. Valid ranges per NIST:
- Thermal conductivity: data 4–300 K, equation valid 1–300 K → covers the full tank span.
- Specific heat: **the coefficients above match NIST's UNS S30400 (304, not 304L) fit**, which is valid across the full 4–300 K range. NIST's own **304L**-specific fit (UNS S30403) uses entirely different coefficients and is only valid **4–23 K** — far too narrow to cover ambient/outer-wall temperatures. In practice, 304 vs. 304L have effectively identical thermal behavior (the "L" only affects carbon content, for corrosion resistance, not thermal properties), so using the 304 fit as given is a reasonable engineering substitution — but it should be logged as a substitution, not silently treated as native 304L data.

⚠️ **Found a likely transcription error:** cross-checking the thermal-expansion coefficients against the NIST source, the `a` term matches exactly, but `b` through `e` are each off by roughly a factor of 10 from what NIST's page (scaled by ×10⁻⁵, per its stated units) implies. Recommend using the corrected form below instead of the version in the earlier doc:

```
dL/L = -2.9554e-3 - (3.9811e-6)*T + (9.2683e-8)*T^2 - (2.0261e-10)*T^3 + (1.7127e-13)*T^4      for T ≥ 23 K
dL/L = -3.0004e-3                                                                              for T < 23 K (constant, per NIST)
```
Worth a quick sanity-check against engineering before locking this in, since this affects any strain/structural-stress calculation derived from thermal contraction.

**Validation of this correction (not just asserted — checked two ways):**

1. *Self-consistency check.* By definition, `dL/L` is measured relative to the length at 293 K, so plugging T = 293 K into the formula should give ≈0. The corrected formula gives **+0.0000014** (essentially zero, as required). The original (uncorrected) coefficients give **−0.00268** — i.e., they imply the material is already 0.27% contracted at its own reference temperature, which is physically impossible. That alone confirms the original coefficients were mis-scaled.
2. *Independent literature cross-check.* A Fermilab cryogenics conference paper (unrelated to either engineering doc or NIST) independently reports the integrated thermal contraction of 304 stainless steel from 293 K to 77 K as **−0.281%**. The corrected formula evaluated at 77 K gives **−0.280%** — a match to within 0.001 percentage points. The original coefficients give −0.294% at the same point — noticeably further off.

Both checks agree: the corrected formula is the one to use.

⚠️ **A second, independent transcription error found in the same source (during digital-twin implementation, 2026-09):** the `cp(T)` coefficients above (the `c` through `i` terms) are also mis-transcribed. Evaluated as given, `cp(T)` *decreases* toward ~0 J/(kg·K) as T rises toward 293 K — physically backwards (304 stainless's specific heat should rise toward ~470 J/(kg·K) near room temperature) — and the error isn't confined to the high-T extrapolation: it also produces physically meaningless values (~10⁻²⁰ J/(kg·K), not just "off") at 20–21 K, i.e. inside the actual LH₂ operating range this workbook is meant to cover. Re-fetching trc.nist.gov/cryogenics/materials' 304 Stainless Steel page directly gives different coefficients from the `c` term onward (confirmed independently by two separate checks against the live NIST page). Corrected coefficients:

```
log10(cp) = 22.0061 - 127.5528*log10(T) + 303.647*log10(T)^2 - 381.0098*log10(T)^3
            + 274.0328*log10(T)^4 - 112.9212*log10(T)^5 + 24.7593*log10(T)^6
            - 2.239153*log10(T)^7 + 0*log10(T)^8
cp = 10^(log10(cp))
```
(`a`, `b` match the earlier doc exactly — only `c` through `h` drift, and `i` is dropped to 0.) This corrected form gives cp(20 K) ≈ 13.5 J/(kg·K) and cp(293 K) ≈ 470.5 J/(kg·K), both physically sane. **Recommend replacing the `c`–`i` coefficients above with these before this formula is used for anything** — it was silently producing near-zero specific heat across the entire operating envelope. Same recommendation as the dL/L fix: confirm with engineering before locking in, since anything using cp(T) (thermal transient/lumped-capacitance calculations) inherits this.

### 4.3 Young's Modulus E(T) — filling the gap

Not published on NIST's 304L page (appears to be a gap in NIST's own site, since it's listed as "available" but no table is shown). Substituting NIST's standard 304 (UNS S30400) fit, valid across the full 5–293 K range as two pieces:

```
E(T) = 209.8145 + 0.1217019*T - 0.01146999*T^2 + 0.0003605430*T^3 - 0.000003017900*T^4   GPa, for 5-57 K
E(T) = 210.0593 + 0.1534883*T - 0.001617390*T^2 + 0.000005117060*T^3 - 0.000000006154600*T^4   GPa, for 57-293 K
```
Same 304/304L substitution logic as above applies — flag it, don't present it as native 304L data.

### 4.4 Yield/tensile values — cross-checked against literature

The MDPI *Metals* (2023) paper tested 304L specimens (8.05% Ni) at 20 K and 300 K directly. Their 20 K result — yield 1059 MPa, tensile 2433.4 MPa — matches the **exact upper bound** of the range given in the earlier engineering doc, confirming that range is grounded in real cryogenic test data, not an estimate. The same paper gives a useful room-temperature anchor not in either engineering doc: **yield ≈ 258 MPa, tensile ≈ 725 MPa at 300 K** for the same 304L lot.

⚠️ Caveat: this is only **discrete point data** (4 K, 20 K, 77 K, 300 K across various studies) — there is no published continuous yield(T)/tensile(T) function. If Scenario 5 (material integrity) needs a continuous stress margin at arbitrary intermediate temperatures, you'd need to either interpolate between these points or ask engineering whether a simpler piecewise/linear model between the known points is acceptable for V1.

### 4.5 Real-gas property model for H₂ (open item from the original handoff)

NIST's own hydrogen data (webbook.nist.gov) is exposed through an interactive fluid-properties tool rather than a simple downloadable formula, so it's not something I can hand you as a closed-form equation. The standard, well-documented equation of state behind it is the **Leachman et al. (2009)** reference EOS for normal hydrogen — this is the same one NIST/REFPROP use, and it's implemented in the open-source **CoolProp** library (`HEOS::Hydrogen` backend), which can be called directly from Python. Given your operating envelope is low pressure (0.5–6 bar(a)), a simpler correction to ideal-gas behavior might even be adequate for the vapor/ullage region — but the liquid phase (LH₂ itself, and the saturation curve that governs ullage pressure vs. boil-off) is not ideal-gas at all, so you do need a real-fluid source there. Proposing CoolProp/Leachman as the default for the digital twin is a defensible, literature-grounded choice — flag it to engineering as the adopted EOS rather than presenting it as pre-approved, since the original handoff is explicit that engineers sign off on this.

---

## 5. Operating Envelope — Pressure

**Cross-checked against industry practice:** multiple independent sources (patent filings for LH₂ transfer systems, DOE truck-storage documentation) describe real LH₂ holding tanks operating in the 1.2–2.5 bar(a) range, with fuel-cell-side systems around 6 bar — this lines up well with HYDRAI's 1.0–1.5 bar(a) normal range and 6.0 bar(a) MAWP. I can't verify the *exact* warning/critical/MAWP digits without your engineering team's own design calculations (those depend on your specific vessel's stress analysis), but the overall envelope is realistic, not out of step with how LH₂ vessels are actually operated.

| Parameter | Value | Classification |
|---|---|---|
| Normal pressure | 1.2 bar(a) | Normal |
| Normal operating range | 1.0–1.5 bar(a) | Normal |
| Low-pressure warning | 0.8 bar(a) | Warning |
| High-pressure warning | 2.0 bar(a) | Warning |
| Critical pressure | 3.0 bar(a) | Critical |
| MAWP | 6.0 bar(a) | Design assumption |
| Minimum modeled pressure | 0.5 bar(a) | Simulation boundary |

---

## 6. Operating Envelope — Temperature

| Measurement | Normal | Warning | Critical | Unit |
|---|---|---|---|---|
| LH₂ temperature | −253 to −250 | >−248 | >−245 | °C |
| Inner wall | −253 to −245 | >−240 | >−235 | °C |
| Outer wall | −20 to +40 | >50 | >60 | °C |
| Ambient | −20 to +60 | >60 | >70 | °C |

---

## 7. Boil-Off Model

⚠️ **Worth real attention: the boil-off staging may be optimistic for a tank this size.**

I checked HYDRAI's staging (0.05%/day excellent → 0.10%/day normal → 0.20%/day mild → 0.40%/day severe → >0.50%/day major anomaly) against published real-world boil-off rates, and there's a pattern worth flagging:

| Source | Tank size | Boil-off rate |
|---|---|---|
| Ewe & Selbach 1987 (cited in ScienceDirect review) | 50 m³ | 0.3–0.5%/day |
| Same source | 103 m³ | 0.2%/day |
| Same source | 19,000 m³ | 0.06%/day |
| Liquid-hydrogen tank car (Wikipedia, DOE-sourced) | rail-car scale | 0.3–0.6%/day |
| DOE H₂ emissions workshop | field-deployed storage | ~1%/day (general rule of thumb) |
| MDPI 2024 review | MLI, best-case/lab-optimized | 0.01–0.05%/day |
| NASA/CB&I (glass bubbles + active refrigeration) | 4,732 m³, cutting-edge | <0.05%/day |

The physical trend across all of these is consistent: **smaller tanks have worse (higher) percentage boil-off**, because surface area scales with the square of size while volume scales with the cube — a smaller vessel has proportionally more surface to leak heat through per kg of hydrogen stored. Your module is **10 m³ — smaller than every real-world tank above that hits 0.2–0.6%/day**, yet HYDRAI's "normal" baseline (0.10%/day) sits closer to the *best-case, laboratory-optimized* MLI figure (0.01–0.05%/day) than to what similarly-sized or even larger real vessels achieve in the field. The only configurations in the literature that beat 0.1%/day are either much larger tanks or ones using active refrigeration (IRAS-style), which HYDRAI doesn't mention.

This doesn't mean the number is wrong — it's possible your vacuum+MLI design is genuinely best-in-class, or that "normal" is meant as a target design spec rather than an expected field value. But given the size mismatch with the literature, **this is worth an explicit confirmation with engineering**: is 0.10%/day an aspirational design target, or the expected as-built performance? If the latter, the whole staging ladder (and any anomaly threshold built on top of it) may need to shift upward — everything downstream (the "elevated boil-off = anomaly" logic in Section 10) inherits this assumption.

**Decision made (see rationale below): use a two-tier framing rather than picking one number.**

- **Ground-truth baseline for the digital twin / AI training data:** 0.30%/day "normal" (not 0.10%) — anchored to the realistic low end of what comparably-or-larger sized real vacuum+MLI vessels achieve (tank-car and 50 m³ literature). Scaled proportionally: excellent ≈0.15%, normal ≈0.30%, mild ≈0.60%, severe ≈1.2%, major >1.5%. This is what the anomaly-detection logic should actually be calibrated against — a safety-monitoring AI's core credibility depends on "normal" being real, not aspirational, or it will systematically over- or under-alarm once built on real hardware.
- **Roadmap/target tier:** HYDRAI's original 0.05–0.10%/day numbers are kept, explicitly labeled as a **future target enabled by a named upgrade path** (vapor-cooled shield and/or catalytic para-to-ortho hydrogen conversion — both real, citable 2020s techniques in the literature, not currently part of HYDRAI's stated vacuum+MLI-only design). Framed this way, the gap becomes a technical differentiator and roadmap story rather than an unexplained optimistic assumption — a stronger position for a technical judging panel than either silently keeping the optimistic number or discarding it without explanation.

Mass balance: **dM/dt = ṁ_in − ṁ_out − ṁ_BOG**

AI approach: compare measured inventory change against physically expected inventory change — mismatch indicates anomaly.

| Boil-off rate | Condition | Mass loss (for ~603 kg) |
|---|---|---|
| ~0.05%/day | Excellent insulation | 0.30 kg/day |
| ~0.10%/day | Normal | 0.60 kg/day |
| ~0.20%/day | Mild degradation | 1.21 kg/day |
| ~0.40%/day | Severe degradation | 2.42 kg/day |
| >0.50%/day | Major anomaly | 3.02 kg/day |

---

## 8. Filling / Flow Parameters

| Parameter | Value |
|---|---|
| Initial fill | 10% |
| Target fill | 85% |
| Maximum modeled fill | 90% |
| Normal fill flow | 1 kg/s |
| Fill flow range | 0.5–2 kg/s |
| Flow measurement frequency | 10 Hz |

| Discharge demand | Flow |
|---|---|
| Low | 0.2 kg/s |
| Normal | 0.5 kg/s |
| High | 1.0 kg/s |
| Peak | 1.5 kg/s |

---

## 9. Sensor Specification

**Plausibility check:** the accuracy/range figures (±0.25% FS pressure, ±0.5°C cryogenic RTD, ±2% FS H₂ concentration) are consistent with commercially available cryogenic instrumentation — this is domain-standard performance, not unusually optimistic. I don't have a specific vendor datasheet to cite for an exact match, so treat this as "plausible and normal-range," not "verified against a named product."

| Sensor | Location | Range | Accuracy | Sampling |
|---|---|---|---|---|
| Pressure | Tank ullage | 0–6 bar(a) | ±0.25% | 1 Hz |
| Liquid temperature | Inside tank | −270 to −200 °C | ±0.5 °C | 1 Hz |
| Inner wall temperature | Tank wall | −270 to +50 °C | ±0.5 °C | 1 Hz |
| Outer wall temperature | Outer shell | −50 to +100 °C | ±0.5 °C | 0.2 Hz |
| H₂ concentration | Vent/exterior | 0–100% vol | ±2% FS | 5 Hz |
| Liquid level | Tank | 0–100% | ±0.5% FS | 1 Hz |
| Mass flow (fill) | Fill line | 0–2 kg/s | ±1% FS | 10 Hz |
| Mass flow (discharge) | Discharge line | 0–2 kg/s | ±1% FS | 10 Hz |
| Strain | Critical wall areas | ±5,000 µε | ±1% FS | 10 Hz |
| Vacuum pressure | Jacket | 0–1,000 Pa | ±1% FS | 0.1 Hz |
| Ambient temperature | Exterior | −20 to +60 °C | ±0.3 °C | 0.1 Hz |

**Sensor placement map:**

| Location | Sensors |
|---|---|
| Tank top | Pressure, vapor temperature |
| Upper liquid region | Temperature, level |
| Middle tank | Temperature |
| Bottom tank | Temperature |
| Inner wall | Temperature, strain |
| Outer wall | Temperature |
| Vacuum jacket | Vacuum pressure |
| Fill line | Pressure, temperature, mass flow |
| Discharge line | Pressure, temperature, mass flow |
| Vent area | H₂ concentration |
| Exterior | Ambient temperature |

---

## 10. Fault / Anomaly Taxonomy (quantified)

**Physics-consistency check (logic, not literature — verified by tracing the mass/energy balance):** the causal chains hold together. Insulation/vacuum degradation → higher heat leak → higher boil-off → (in a sealed, periodically-vented ullage) higher pressure → higher wall temperature is the correct direction of causation. The containment-anomaly signature (unexplained mass loss beyond expected boil-off + rising external H₂ + abnormal P/T) is exactly what the mass balance (dM/dt = ṁ_in − ṁ_out − ṁ_BOG) predicts when an unaccounted leak term appears. No inconsistencies found in the taxonomy's internal logic.

| Scenario | Pressure | Temperature | Boil-off | H₂ | Strain | AI label |
|---|---|---|---|---|---|---|
| Normal | Normal | Normal | Normal | Normal | Normal | 0 |
| Sensor fault | Normal | Erratic | Normal | Normal | Normal | 1 |
| Insulation degradation | High | High | High | Normal | Normal | 2 |
| Vacuum degradation | High | High | High | Normal | Normal | 3 |
| Abnormal pressure rise | High | High | High | Normal | Normal | 4 |
| Containment anomaly | High/abnormal | Abnormal | High | High | High | 5 |
| Structural concern | Variable | Variable | Variable | Normal | High | 6 |
| Unknown anomaly | Variable | Variable | Variable | Variable | Variable | — |

**Containment-anomaly signature:**

| Variable | Normal | Anomaly |
|---|---|---|
| H₂ concentration | ~0% | Increasing |
| H₂ concentration rate | ~0 | Positive |
| Tank mass | Expected | Faster-than-expected decrease |
| Pressure | Expected | Abnormal |
| Boil-off | ~0.1%/day | Elevated |
| Temperature | Stable | Abnormal |
| Strain | Stable | Potential increase |
| AI conclusion | Healthy | Possible containment anomaly |

**Insulation-degradation staging:**

| Parameter | Healthy | Degraded | Severe |
|---|---|---|---|
| Insulation health | 100% | 70% | 40% |
| Heat leak | 100% baseline | 150% | 250% |
| Boil-off | 0.10%/day | 0.15%/day | 0.25%/day |
| Wall temperature | Normal | High | High |
| Pressure rise | Normal | High | High |

---

## 11. What this resolves from the original open-decisions list

- ✅ System type confirmed: LH₂
- ✅ Geometry (per module)
- ✅ Pressure and temperature envelopes with warning/critical thresholds
- ✅ Boil-off model with staged severity
- ✅ Sensor specification and placement
- ✅ Fault taxonomy, quantified with AI labels and two detailed sub-scenarios

## 12. Resolved via the references (no engineering wait needed)

- ✅ Units/range for k(T), cp(T), thermal-expansion(T) — confirmed via direct NIST source check.
- ✅ Young's modulus(T) — filled in via NIST's 304 fit (flagged as a 304→304L substitution).
- ✅ Yield/tensile values — cross-validated against the MDPI paper's own 20 K test data (exact match).
- ✅ Source citation for the thermal/material correlations — identified as NIST's cryogenic materials database (trc.nist.gov), for the validation evidence pack.
- ✅ H₂ real-gas property approach — proposed default (CoolProp / Leachman EOS), pending engineering sign-off rather than pending discovery.

## 13. Previously open — now given proposed defaults (Section 17)

These still have no external fact to discover, but Section 17 now proposes grounded, code-based defaults for each so the build isn't blocked. Treat these as prototype assumptions, not confirmed specs:

- **Control/valve logic** — proposed in 17.2 (PCV/PRV/fill/discharge architecture).
- **Wall thickness** — proposed in 17.1 (10 mm supported by an ASME UG-27 calculation + buckling reasoning).
- **Leak/orifice-size variation** — proposed in 17.3 (HyRAM+'s own standard release-size ladder).
- **Multi-module coupling** — proposed in 17.4 (independent containment, flag if vent header is shared).
- **304 vs. 304L substitution** (specific heat, Young's modulus) — still worth a one-line confirmation; this one has no literature-based default to propose beyond what's already in Section 4.

## 15. Confidence & Validation Status

For a hackathon submission with real incubation stakes, it matters which of these numbers are verified versus assumed. Use this table if judges/mentors probe assumptions:

| Item | Status | Basis |
|---|---|---|
| System = LH₂, 6 modules, geometry | **Confirmed by engineering + arithmetic self-checks pass** | Given directly; volume/mass/surface-area figures are internally consistent |
| LH₂/H₂ physical constants (Tc, NBP, density, latent heat, LHV/HHV) | **Verified against primary reference EOS** | Tc matches Leachman et al. (2009) exactly; others are standard, uncontested values |
| Pressure envelope (1.0–1.5 bar normal, 6.0 bar MAWP) | **Consistent with industry practice** | Matches multiple independent real LH₂ system examples (1.2–2.5 bar holding tanks, 6 bar fuel-cell side); exact thresholds not independently derivable without your vessel's stress calcs |
| Temperature envelope | **Confirmed by engineering** | Consistent with LH₂ saturation behavior; not independently re-derived |
| **Boil-off staging (0.05–0.5%/day)** | **⚠️ Flagged — may be optimistic for a 10 m³ tank** | Real-world tanks of comparable-or-larger size (50–103 m³) see 0.2–0.6%/day in the literature; your "normal" (0.10%/day) sits closer to best-case lab-optimized MLI performance. Confirm with engineering whether this is a target or an expected value. |
| Sensor specs | **Plausible, domain-consistent** | Matches general cryogenic-instrumentation norms; not matched to a specific datasheet |
| Fault taxonomy causal logic | **Internally consistent** | Verified via mass/energy balance tracing, not literature |
| k(T) formula, units (K), range (1–300K) | **Verified against primary source** | Matches NIST cryogenics database exactly |
| cp(T) formula | **⚠️ Corrected — original coefficients were transcribed wrong** | `c`–`i` coefficients replaced with NIST's actual 304 fit (re-fetched directly); original gave physically meaningless (~0) values across the whole operating range, including at 20–21 K. Substitution note (304 not 304L) still applies; range 4–300K |
| Thermal expansion dL/L(T) | **Corrected and independently validated** | Two independent checks (self-consistency at 293K + Fermilab literature match at 77K), both pass |
| Young's modulus E(T) | **Filled gap, flagged substitution** | NIST's 304 fit, used because 304L's own isn't published |
| Yield/tensile strength (682–1059 / 1943–2433 MPa) | **Verified against independent literature** | MDPI 2023 paper's own 20K test matches upper bound almost exactly |
| H₂ real-gas EOS choice (CoolProp/Leachman) | **Proposed default, not yet engineering-approved** | Standard, well-documented choice; flag as adopted assumption in any writeup |
| 304 vs. 304L substitution (cp, E) | **Reasonable approximation, not verified equivalence** | L-grade differs mainly in carbon content (corrosion resistance), not thermal/elastic behavior — standard engineering assumption, but say so explicitly if asked |
| **Wall thickness, valve/control logic, leak-size matrix, module coupling** | **Proposed defaults given (Section 17), pending engineering confirmation** | Grounded in ASME VIII-1 (the code SASO/Saudi Aramco-grade projects actually use), HyRAM+'s own methodology, and standard multi-tank-farm practice — not discovered facts, but defensible, code-based placeholders. Still need your team's sign-off before treating as final. |

The honest framing for a pitch: *the physics foundation is verified against primary sources (NIST) and cross-checked against independent literature where possible; the remaining open items are explicitly-flagged engineering decisions, not gaps in the team's diligence.* That distinction is usually exactly what a technical judge wants to see — not a claim that everything is finished.

## 17. Proposed Defaults for the Remaining Open Items (prototype-grade, not engineering-confirmed)

These four items have no external fact to discover — they're specific to your vessel. But "no discoverable fact" isn't the same as "no defensible default." Below are grounded proposals, each clearly a **proposed assumption for the prototype**, not a verified spec. Use them to keep building; say so plainly if a judge asks.

**Why ASME here specifically:** Saudi Arabia's national standards body (SASO) recognizes ASME Section VIII as the base pressure-vessel design code, and Saudi Aramco/SABIC-grade energy projects build to it (layered with internal SAES specs). This isn't an imported convention — it's the applicable framework for a hydrogen-storage system built in Saudi Arabia.

### 17.1 Wall thickness — proposed default: keep 10 mm

ASME BPVC VIII-1, UG-27 (thin cylindrical shell, internal pressure): `t = PR / (SE − 0.6P)`
- P = 6 bar(a) MAWP ≈ 0.5 MPa, R = 1000 mm, S ≈ 115 MPa (304L allowable stress near ambient — the limiting case across your range, since 304L is *stronger*, not weaker, at cryogenic temperature), E = 0.85 (typical spot-radiographed weld)
- **t ≈ 5.1 mm** minimum for internal pressure alone (4.4 mm if E = 1.0, fully radiographed)

Your inner vessel also sits inside a vacuum jacket, so it must resist *external* pressure — a buckling problem (UG-28), not simple hoop stress, and buckling resistance typically demands meaningfully more thickness than the internal-pressure case. HYDRAI's 10 mm sits comfortably above the 4.4–5.1 mm internal-pressure floor, consistent with a buckling-governed (not internal-pressure-governed) design plus standard fabrication minimums for a 2 m-diameter vessel. **Proposed: adopt 10 mm as the working value**, with a note that the actual UG-28 buckling calculation (which needs unsupported length and any stiffening-ring spacing) is the real governing check your team should eventually run.

### 17.2 Control/valve logic — proposed default

Standard architecture for a vented cryogenic storage system:
- **Pressure Control Valve (PCV):** opens at the high-pressure warning (2.0 bar(a)) to vent boil-off and hold the tank in the normal band (1.0–1.5 bar(a)); recloses once pressure drops back near setpoint.
- **Safety Pressure Relief Valve (PRV):** independent, spring-loaded, set at/near MAWP (6.0 bar(a)) — last-resort mechanical overpressure protection per ASME UG-125/126, separate from the PCV.
- **Fill valve:** opens per the existing fill-flow table (0.5–2 kg/s), closes automatically at 85–90% level via the liquid-level sensor.
- **Discharge valve:** modulates per the existing demand table (0.2–1.5 kg/s).
- **Vacuum jacket:** sealed, no active valve — monitored passively by the vacuum-pressure sensor only.

### 17.3 Leak-size severity gradient — proposed default (from your own reference tool)

You already have the right source for this: **HyRAM+** (one of engineering's cited references) uses a standard release-size ladder expressed as a fraction of reference flow area, not arbitrary diameters — typically **0.01% (pinhole) → 0.1% (small) → 1% (small-medium) → 10% (medium-large) → 100% (full-bore rupture)**. Proposing this directly as your Scenario 5 severity gradient isn't importing an unrelated convention — it's using the tool your team already named for its intended purpose.

### 17.4 Multi-module coupling — proposed default

Standard practice in multi-tank cryogenic storage farms (LNG/LH₂ yards): each module has fully **independent primary containment** — its own inner vessel, vacuum jacket, and full sensor suite (consistent with HYDRAI's per-module data) — but often shares a **common downstream boil-off/vent header** feeding shared handling equipment. **Proposed: model M01–M06 independently for the state/mass-energy-balance model** (matches how the data is already structured), but explicitly confirm with engineering whether boil-off venting is metered per-module or at a shared header — if it's shared, a spike from one module's degrading insulation could misleadingly look like "all six modules degrading together" in your anomaly detector.

**Regional grounding, honestly stated:** NEOM's green hydrogen project (Vision 2030's flagship, ~90% complete as of early 2026) explicitly includes "hydrogen storage vessels" in its installed equipment — confirming this kind of system is real, current, and relevant in Saudi Arabia right now. I don't have access to NEOM's internal vessel specs, so this is context for why the work matters, not a claim that HYDRAI mirrors NEOM's design.

### 17.5 Leak discharge (mass-flow) model — the one physics piece that was still missing

Everything above gives you leak *categories* (Section 17.3) and a *signature* (Section 10), but not yet the equation that turns "a 1% orifice at pressure P" into an actual kg/s mass-flow number your twin needs. This is standard compressible-flow theory (the same math HyRAM+ itself uses), not vessel-specific, so it's safe to adopt directly rather than flag as unresolved:

Check choke condition first — critical pressure ratio for H₂ (γ ≈ 1.41): `r_crit = (2/(γ+1))^(γ/(γ-1)) ≈ 0.528`

- **If P_ambient / P_tank ≤ 0.528 (choked/sonic flow)** — happens whenever tank pressure is above ~1.9× ambient, i.e. above roughly 1.9 bar(a) in your envelope:
`ṁ = Cd·A·P_tank·√[ (γ/(R·T)) · (2/(γ+1))^((γ+1)/(γ-1)) ]`
- **If P_ambient / P_tank > 0.528 (unchoked/subsonic flow)** — the normal case near your 1.0–1.5 bar(a) operating band:
`ṁ = Cd·A·√[ 2·ρ_tank·P_tank·(γ/(γ-1))·((P_amb/P_tank)^(2/γ) − (P_amb/P_tank)^((γ+1)/γ)) ]`

**Discharge coefficient Cd:** propose **0.62** (standard sharp-edged-orifice default used across hydrogen QRA tools including HyRAM+) unless engineering specifies a different hole geometry.

Note both regimes are actually relevant for you: near normal operating pressure (1.0–1.5 bar(a)) a leak is unchoked/subsonic; near MAWP (6.0 bar(a)) it would be choked. Your twin needs both branches, not just one.

## 18. References

- Leachman, Jacobsen, Penoncello, Lemmon, "Fundamental Equations of State for Parahydrogen, Normal Hydrogen, and Orthohydrogen," *J. Phys. Chem. Ref. Data* 38(3), 2009 — source of the critical-point value (Tc = 33.19 K) confirmed against HYDRAI.
- NIST Cryogenic Materials Database — 304/304L Stainless: k(T), cp(T), thermal-expansion(T), Young's modulus(T). trc.nist.gov/cryogenics/materials
- NIST Chemistry WebBook — Hydrogen (fluid properties tool). webbook.nist.gov
- Kim et al., "Tensile and Fracture Characteristics of 304L Stainless Steel at Cryogenic Temperatures for Liquid Hydrogen Service," *Metals* 13(10), 1774 (2023), open access CC BY. mdpi.com/2075-4701/13/10/1774
- Fesmire et al., "Energy Efficient Large-Scale Storage of Liquid Hydrogen," NASA/KSC, Cryogenic Engineering Conference (2021) — context on insulation/boil-off relationship at much larger tank scale; not directly scalable to the 10 m³ module. ntrs.nasa.gov/citations/20210018293
- ASME Clean Hydrogen resource page — identifies governing codes (BPVC.VIII.1 for pressure vessel design, B31.12 for hydrogen piping) as the likely basis for HYDRAI's P/T thresholds; standards themselves are paywalled, so this confirms *which* codes apply rather than giving free numeric criteria. asme.org/resources/clean-hydrogen
- Ewe & Selbach (1987), boil-off rate vs. tank size data, as cited in a ScienceDirect "Liquid Hydrogen" topic overview — basis for the tank-size boil-off comparison in Section 7.
- "Brief Review and Technical Insight of Liquefied Hydrogen Carriers Development," Springer — additional boil-off-vs-size data points (300 m³, 1100–2300 m³).
- "A Review on Liquid Hydrogen Storage," MDPI *Sustainability* 16(18), 8270 (2024) — MLI best-case boil-off figures and perlite-insulation baseline.
- *Liquid-hydrogen tank car*, Wikipedia (DOE-sourced) — rail-car boil-off rate (0.3–0.6%/day) for a comparably-insulated vacuum/MLI vessel.
- U.S. DOE, "H2 Emissions Workshop" presentation materials — field/industry rule-of-thumb boil-off figure (~1%/day) and LH₂ transfer-loss context.
- U.S. patent filings on LH₂ transfer/holding-tank systems and DOE long-haul-truck LH₂ storage documentation — used to cross-check the plausibility of HYDRAI's pressure envelope (1.0–1.5 bar normal, 6.0 bar MAWP) against real system examples.
- ASME Boiler and Pressure Vessel Code, Section VIII, Division 1 (UG-27, UG-28, UG-125/126) — basis for the wall-thickness and relief-valve proposals in Section 17; confirmed as the design code SASO recognizes and Saudi Aramco/SABIC-grade projects build to.
- HyRAM+ (Hydrogen Risk Assessment Models, Sandia National Labs) — standard release-size categorization used as the basis for the leak-size gradient proposal in Section 17.3; already one of engineering's own cited references.
- NEOM Green Hydrogen Company project reporting (2025–2026 construction updates) — confirms hydrogen storage vessels as real, current infrastructure in Saudi Arabia's Vision 2030 hydrogen strategy; used as regional context only, not as a technical source for HYDRAI's specs.
