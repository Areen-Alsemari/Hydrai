"""
Registry of every value in the physical pressure/valve model that is NOT
settled by a verified source. Each entry carries its basis and the engineer
question (ENGINEER_QUESTIONS_VALVE_VENT.md) that would replace it, so
"flagged as a placeholder" is machine-readable: `used_placeholders()` is what
a dataset manifest should record.

Levels
  placeholder : stand-in pending engineering confirmation (question id given)
  literature  : taken from a verified source (id from VALVE_VENT_SOURCE_VERIFICATION.md)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hydrai_twin import constants as C


@dataclass(frozen=True)
class Placeholder:
    name: str
    value: float
    unit: str
    basis: str
    question: str | None   # engineer question id, e.g. "Q1"
    level: str             # "placeholder" | "literature"


_REF_ORIFICE_AREA_M2 = math.pi / 4.0 * C.REFERENCE_LEAK_ORIFICE_DIAMETER_M**2

_ENTRIES = [
    # --- PCV (Q1, Q3) ---
    Placeholder("pcv_open_bar_a", 1.5, "bar(a)",
                "Top of the workbook Sec. 5 normal band. Workbook Sec. 17.2 instead says the PCV opens at the 2.0 bar(a) warning level; unresolved.",
                "Q1", "placeholder"),
    Placeholder("pcv_deadband_bar", 0.069, "bar",
                "NASA MHTB vent control band, 6.9 kPa (S1). An analog for hysteresis width at this tank's scale, not this valve.",
                "Q1", "placeholder"),
    Placeholder("pcv_effective_diameter_m", 0.010, "m",
                "Arbitrary effective vent orifice; no vent-line design basis exists.",
                "Q3", "placeholder"),
    Placeholder("pcv_cd", C.DISCHARGE_COEFFICIENT_CD, "-",
                "Workbook Sec. 17.5 sharp-edged orifice default (0.62).",
                "Q3", "placeholder"),
    # --- pressure-building circuit (Q1) ---
    Placeholder("pbr_open_bar_a", 1.10, "bar(a)",
                "Pressure-build regulator engages below this. A commercial LH2 vessel has one (reviewer-read datasheet, S25); whether this tank does is unknown. Without it, liquid discharge pulls pressure down.",
                "Q1", "placeholder"),
    Placeholder("pbr_close_bar_a", 1.15, "bar(a)",
                "Pressure-build regulator disengages above this (0.05 bar hysteresis, arbitrary).",
                "Q1", "placeholder"),
    Placeholder("pbr_heat_w", 10000.0, "W",
                "Vaporizer heat added to the ullage while the regulator is engaged. Arbitrary capacity, roughly what a 0.5 kg/s discharge needs.",
                "Q1", "placeholder"),
    # --- PRV (Q2) ---
    Placeholder("prv_set_bar_a", C.PRESSURE_MAWP_BAR, "bar(a)",
                "Set at MAWP (workbook Sec. 5); ASME VIII-1 rule via a secondary source (S7).",
                "Q2", "placeholder"),
    Placeholder("prv_pop_tolerance_frac", 0.03, "-",
                "Magnitude from a marine relief-valve regulation, 46 CFR 162.018-5 (S17), not ASME VIII.",
                "Q2", "placeholder"),
    Placeholder("prv_blowdown_frac", 0.05, "-",
                "Magnitude from 46 CFR 162.018-5 (S17): closes after blowing down not more than 5% of set.",
                "Q2", "placeholder"),
    Placeholder("prv_full_lift_overpressure_frac", 0.10, "-",
                "Linear lift from set to set+10%: ASME-certified valves reach rated capacity at 10% or less overpressure (S7, secondary).",
                "Q2", "placeholder"),
    Placeholder("prv_effective_area_m2", _REF_ORIFICE_AREA_M2, "m^2",
                "Reuses the 19 mm reference orifice of workbook Sec. 17.3. There is no relief design basis for this tank.",
                "Q2", "placeholder"),
    Placeholder("prv_cd", 0.975, "-",
                "API effective discharge coefficient for gas (S8, secondary); certified valves are lower.",
                "Q2", "placeholder"),
    Placeholder("prv_cd_liquid", 0.65, "-",
                "Effective liquid discharge coefficient used when the PRV must pass liquid (tank liquid-full). Not verified by me; flashing downstream is ignored.",
                "Q2", "placeholder"),
    # --- fill limit (Q9b) ---
    Placeholder("first_fill_max_fraction", 0.75, "-",
                "UNVERIFIED. Reported to me as the cap on FIRST fill of a WARM tank in Chart's LH2 manual; I have not read it. It does not apply to later fills, which go to the rated maximum (a separate unanswered question, Q9b). The workbook uses 85% nominal / 90% max modeled (Secs. 2, 8). At 85% a blocked tank goes liquid-full near 5.5-5.9 bar(a), below MAWP 6.0 (my CoolProp check).",
                "Q9b", "placeholder"),
    # --- environment and instrumentation assumptions ---
    Placeholder("ambient_diurnal_amplitude_c", 5.0, "C",
                "Day/night ambient swing; heat leak is scaled by a radiation law (T^4) against the cold surface. Amplitude is an assumption.",
                "Q7", "placeholder"),
    Placeholder("h2_dispersion_pct_per_kg_s", 50000.0, "%vol per kg/s",
                "Crude leak-rate to vent-sensor concentration scaling carried over from the legacy generator. Handoff Sec. 11.6 says not to invent ppm readings; no dispersion model exists.",
                "Q3", "placeholder"),
    Placeholder("sensor_fault_spike_prob", 0.15, "-",
                "Per-sample chance of an erratic liquid-temperature reading once a sensor fault is active (carried over from the legacy generator).",
                "Q5", "placeholder"),
    Placeholder("strain_scf_max", 4.0, "-",
                "Stress-concentration factor at full structural-concern severity (carried over from the legacy generator; not a structural model).",
                "Q5", "placeholder"),
    Placeholder("ambient_bar_a", C.STANDARD_ATMOSPHERIC_PRESSURE_BAR, "bar(a)",
                "Standard atmosphere; vent discharges to atmosphere (assumed; Q3 asks whether a recovery header exists).",
                "Q3", "placeholder"),
    # --- sensor error split (Q12): how the Sec. 9 accuracy figure divides into bias / drift / noise ---
    Placeholder("sensor_bias_frac", 0.5, "x accuracy",
                "Per-unit calibration bias is bounded by this fraction of the Sec. 9 accuracy (uniform +/-). 0.5 was the module-profile value already in use; no datasheet split exists.",
                "Q12", "placeholder"),
    Placeholder("sensor_drift_frac", 0.3, "x accuracy",
                "Slow drift: Ornstein-Uhlenbeck with 2-sigma = this fraction of the accuracy, hard-clipped at it. Assumed split; real long-term stability is a datasheet/calibration-interval number.",
                "Q12", "placeholder"),
    Placeholder("sensor_noise_sigma_frac", 0.1, "x accuracy",
                "Random per-sample noise sigma as a fraction of the accuracy (2-sigma = 0.2 x accuracy). Chosen so bias + drift + 2-sigma noise = 0.5 + 0.3 + 0.2 = 1.0 x accuracy, i.e. total error stays inside the stated spec.",
                "Q12", "placeholder"),
    Placeholder("sensor_h2_zero_bias_frac", 0.1, "x accuracy",
                "Hydrogen channel only: the detector reads ~0 in healthy service and is assumed zero-referenced (clean-air zero check at commissioning), so most of the +/-2% FS is span error that is near zero at zero reading. Zero-offset bias bound = 0.1 x 2 %vol = 0.2 %vol. With the generic 0.5 the bound is 1.0 %vol and ~22% of simulated units would sit in a persistent 25%-LFL alarm.",
                "Q12", "placeholder"),
    Placeholder("sensor_h2_zero_drift_frac", 0.1, "x accuracy",
                "Hydrogen channel only: zero drift bound 0.1 x accuracy (0.2 %vol); the generic 0.3 (0.6 %vol) alone would exceed a 10%-LFL alarm.",
                "Q12", "placeholder"),
    Placeholder("sensor_drift_tau_days", 3.0, "d",
                "Drift correlation time. Arbitrary: slow against a 14-day episode, fast enough to wander within it.",
                "Q12", "placeholder"),
    # --- reference dashboard: H2 detector, vacuum gauge, level DP, historian (Q6, Q10, Q11, Q12) ---
    Placeholder("h2_lfl_vol_pct", 4.0, "%vol",
                "100 %LFL = 4 %vol hydrogen in air (workbook Sec. 3 flammability range 4-75 %vol).", "Q11", "literature"),
    Placeholder("h2_detector_accuracy_lfl", 5.0, "%LFL",
                "Realistic point/open-path %LFL hydrogen detector, +/-5 %LFL over 0-100 %LFL. Reference-configuration value, UNVERIFIED; replaces the Sec. 9 0-100 %vol +/-2% FS spec in the default mode.",
                "Q11", "placeholder"),
    Placeholder("h2_detector_t90_s", 12.5, "s",
                "Detector response, T90 of 10-15 s (reference configuration, UNVERIFIED). Modelled as a first-order lag with tau = T90/2.3.", "Q11", "placeholder"),
    Placeholder("h2_alarm_h_lfl", 20.0, "%LFL",
                "H (low) alarm. Alternates seen in practice: 10/25 and 25/50 %LFL; Aramco SAES setpoints are not public. UNVERIFIED.", "Q11", "placeholder"),
    Placeholder("h2_alarm_hh_lfl", 40.0, "%LFL", "HH (high) alarm, see h2_alarm_h_lfl. UNVERIFIED.", "Q11", "placeholder"),
    Placeholder("vacuum_gauge_rel_accuracy", 0.20, "x reading",
                "Log-scale Pirani/thermocouple-class gauge: +/-20% of reading in the mid range. UNVERIFIED; no gauge datasheet.", "Q6", "placeholder"),
    Placeholder("vacuum_gauge_floor_pa", 0.05, "Pa",
                "Absolute accuracy floor added to the relative term. UNVERIFIED.", "Q6", "placeholder"),
    Placeholder("vacuum_gauge_min_pa", 0.1, "Pa", "Lower end of the gauge range (below it the reading saturates). UNVERIFIED.", "Q6", "placeholder"),
    Placeholder("vacuum_gauge_max_pa", 1.0e5, "Pa", "Upper end of the gauge range. UNVERIFIED.", "Q6", "placeholder"),
    Placeholder("level_dp_reference_pressure_bar_a", 1.2, "bar(a)",
                "The differential-pressure level gauge is scaled at the saturated-liquid and vapor densities of this pressure (workbook Sec. 5 normal pressure); density change with pressure then biases the reading.",
                "Q5", "placeholder"),
    Placeholder("historian_exception_forced_s", 600.0, "s", "Exception filter forced point (reference configuration, STD).", "Q10", "placeholder"),
    Placeholder("historian_compression_forced_s", 28800.0, "s", "Swinging-door forced archive point, 8 h (reference configuration, STD).", "Q10", "placeholder"),
    Placeholder("historian_compdev_mult", 2.0, "x exception deadband",
                "Compression deviation = 2 x exception deviation, a common PI-style rule of thumb. Assumption.", "Q10", "placeholder"),
    Placeholder("historian_fault_dropout_per_day", 0.2, "events/day/tag", "Injected dropout rate (Bad, no value); mean 300 s. Low-rate assumption.", "Q10", "placeholder"),
    Placeholder("historian_fault_stale_per_day", 0.1, "events/day/tag", "Injected stale-value rate (last value repeated, Uncertain); mean 900 s. Assumption.", "Q10", "placeholder"),
    Placeholder("historian_fault_flatline_per_day", 0.05, "events/day/tag", "Injected flat-line rate (sensor output stuck, quality still Good); mean 7200 s. Assumption.", "Q10", "placeholder"),
    Placeholder("historian_fault_outofrange_per_day", 0.05, "events/day/tag", "Injected out-of-range rate (Uncertain); mean 120 s. Assumption.", "Q10", "placeholder"),
    Placeholder("boiloff_normal_pct_per_day_default", 0.30, "%/day",
                "Default healthy boil-off of the physical generator: 0.30 %/day (workbook Sec. 7: real 10 m^3 vacuum+MLI tanks run 0.3-0.6 %/day; at the handoff's 0.10 %/day a healthy tank first vents after 19 d and pressure faults are weak in 14 d episodes). PHYSICAL_DEFAULT_BOILOFF_MODE = 'target' switches to the 0.10 %/day spec value (handoff / workbook Sec. 10).",
                "Q7", "placeholder"),
    Placeholder("overfill_fill_fraction", 0.93, "fraction",
                "Fill used for the labeled overfill scenarios: above the 90% spec maximum (Sec. 2/8). Arbitrary value.", "Q9b", "placeholder"),
    # --- heat leak / vacuum ladder (Q7, Q8) ---
    Placeholder("vacuum_ladder_soft_dp_pa", 13.33, "Pa",
                "Added jacket pressure at the soft-vacuum rung (100 mtorr), where S20 measured 52 W/m^2. Below it the ladder is linear in pressure (free-molecular gas conduction is proportional to pressure). The interpolation is mine, not a source.",
                "Q8", "placeholder"),
    Placeholder("vacuum_lost_jacket_pa", 101325.0, "Pa",
                "Jacket at atmospheric pressure for the 'lost' rung.",
                "Q8", "placeholder"),
    Placeholder("vacuum_flux_soft_w_m2", 52.2, "W/m^2",
                "ICEC19 (S20): 0.87 W/m^2 at 0.0015 Pa rising ~60x at 13.33 Pa. Nitrogen-cooled MLI blanket, not hydrogen.",
                "Q8", "literature"),
    Placeholder("vacuum_flux_lost_high_w_m2", 7230.0, "W/m^2",
                "Upper averaged heat flux from a flowing-LH2 hose after vacuum failure (S22, accidental event, small-bore line). Used only to probe relief capacity.",
                "Q8", "literature"),
    Placeholder("vacuum_flux_lost_w_m2", 1274.0, "W/m^2",
                "Hydrogen tank, vacuum failed with N2 ingress (S21): boil-off 0.013 kg/s over 6.69 m^2. Flow-limited and likely still LOW (flowing hose, S22, gave 3,180-7,230).",
                "Q8", "literature"),
]

REGISTRY: dict[str, Placeholder] = {p.name: p for p in _ENTRIES}
_USED: set[str] = set()


def value(name: str) -> float:
    """Look up a registry value and record that it was used."""
    _USED.add(name)
    return REGISTRY[name].value


def used_placeholders() -> list[dict]:
    """The registry entries that were read since import (or last reset), for
    inclusion in a dataset manifest."""
    return [
        {"name": p.name, "value": p.value, "unit": p.unit, "level": p.level, "question": p.question, "basis": p.basis}
        for n, p in REGISTRY.items() if n in _USED
    ]


def reset_usage() -> None:
    _USED.clear()
