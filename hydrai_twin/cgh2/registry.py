"""
CGH2 parameter registry. Every number the CGH2 twin uses is here with a SOURCE TAG, so manifests can carry them.

Tags (from the decision register and Addendum 1):
  V1  read at the primary document or datasheet (via a fetch tool that summarises PDFs: spot-check before quoting)
  V2  reputable secondary source
  V3  existence only (no number taken)
  U   not found
  CALC  our calculation
  JUDGE decision without a source
  REG-UNREAD  value relayed in the build instruction as "from the register"; the register file itself was NOT available when this
              was built, so the tag could not be read. Treated as a placeholder.
Anything tagged U, JUDGE or REG-UNREAD is a flagged placeholder (`is_placeholder`). Own registry (not hydrai_twin.placeholders) so
that CGH2 entries can never leak into LH2 manifests.
"""

from __future__ import annotations

from dataclasses import dataclass

TAGS = ("V1", "V2", "V3", "U", "CALC", "JUDGE", "REG-UNREAD")
PLACEHOLDER_TAGS = ("U", "JUDGE", "REG-UNREAD")


@dataclass(frozen=True)
class Entry:
    name: str
    value: float | str | tuple
    unit: str
    tag: str
    source: str
    basis: str = ""
    conflict: str | None = None          # a register-vs-addendum (or instruction) conflict this entry resolves

    @property
    def is_placeholder(self) -> bool:
        return self.tag in PLACEHOLDER_TAGS


def E(name, value, unit, tag, source, basis="", conflict=None) -> Entry:
    assert tag in TAGS, tag
    return Entry(name, value, unit, tag, source, basis, conflict)


_ENTRIES: list[Entry] = [
    # --- pressure classes (instruction: register Sec. 3) ---
    E("mop_bar_low", 50.0, "bar", "REG-UNREAD", "register Sec. 3 as relayed", "low class"),
    E("mop_bar_medium", 300.0, "bar", "REG-UNREAD", "register Sec. 3 as relayed", "PRIMARY class"),
    E("mop_bar_high", 350.0, "bar", "REG-UNREAD", "register Sec. 3 as relayed", "high class"),
    E("mop_bar_700_illustrative", 700.0, "bar", "REG-UNREAD", "register Sec. 3 as relayed", "NOT in the main dataset; optional illustrative flag only"),
    E("mawp_over_mop", 1.10, "x MOP", "JUDGE", "Addendum A", "no source for the ratio; consistent with a ~10% spring-valve margin"),
    E("prv_set_over_mawp", 1.0, "x MAWP", "V2", "ASME VIII-1 UG-134 (set at or below MAWP)"),
    E("pah_over_mop", 1.02, "x MOP", "CALC", "Addendum A", "at 1.08 the trip sat inside the PRV tolerance band (1.10 +/- 3% = 1.067-1.133 x MOP)",
      conflict="register 1.05 -> 1.02 (Addendum 1)"),
    E("pahh_over_mop", 1.05, "x MOP", "CALC", "Addendum A; INL station storage alarm/trip 6200/6500 psig (ratio 1.05), V1 (one old station)",
      conflict="register 1.08 -> 1.05 (Addendum 1)"),
    E("compressor_start_frac_mop", 0.85, "x MOP", "REG-UNREAD", "instruction"),
    E("compressor_stop_frac_mop", 1.00, "x MOP", "REG-UNREAD", "instruction"),
    E("compressor_flow_kg_h_low", 10.0, "kg/h", "JUDGE", "Addendum A design points 10 / 20 / 25 kg/h; mapping to classes is ours",
      "real references: Burckhardt 44 kg/h, Haskel 45, NEOM station 14 kg/h (V1/V2)"),
    E("compressor_flow_kg_h_medium", 20.0, "kg/h", "JUDGE", "as above"),
    E("compressor_flow_kg_h_high", 25.0, "kg/h", "JUDGE", "as above"),
    E("compressor_discharge_dT_ambient_k", 15.0, "K", "REG-UNREAD", "instruction: intercooled discharge at ambient + 15 K"),
    E("compressor_ramp_s", 30.0, "s", "JUDGE", "start/stop ramp of the compressor flow"),
    E("transmitter_range_bar_low", 100.0, "bar", "JUDGE", "ranged above PRV full-lift pressure (1.10 x 1.10 x MOP)"),
    E("transmitter_range_bar_medium", 400.0, "bar", "JUDGE", "as above"),
    E("transmitter_range_bar_high", 500.0, "bar", "JUDGE", "as above"),
    # --- relief ---
    E("prv_set_tolerance", 0.03, "fraction", "V2", "ASME VIII-1 UG-126(d)", conflict="register marine rule +/-3% confirmed; +/-2 psi only up to 70 psi (Addendum 1)"),
    E("prv_blowdown_nominal", 0.07, "fraction", "V2", "conventional spring PRV 7-10%; hydrogen PRV sheet '7% or 0.2 bar'", conflict="register 5% -> 7% nominal (Addendum 1)"),
    E("prv_blowdown_conservative", 0.10, "fraction", "V2", "as above", conflict="register 5% -> 10% conservative (Addendum 1)"),
    E("prv_accumulation_single", 1.10, "x set", "V2", "ASME VIII-1 UG-125"),
    E("prv_accumulation_multi", 1.16, "x set", "V2", "ASME VIII-1 UG-125 (multiple valves)"),
    E("prv_accumulation_fire", 1.21, "x set", "V2", "ASME VIII-1 UG-125 (fire)"),
    E("prv_effective_diameter_mm", 6.0, "mm", "JUDGE", "no relief-sizing data; sized to relieve the fire case at 121% accumulation"),
    E("prv_cd", 0.8, "-", "JUDGE", "generic"),
    E("tprd_fitted", 0.0, "bool", "V2", "Michigan hydrogen rule R 29.7021: thermal devices belong to composite containers; steel stationary vessels use PRVs",
      conflict="register optional TPRD 110 C in the fire scenario -> REMOVED (Addendum 1)"),
    E("prv_fail_to_open_per_demand_hyram", 8.0e-6, "per demand", "V1", "HyRAM+ v5.1 Table 2-4: lognormal mu=-11.74 sigma=0.67 (median ~8e-6), via summary"),
    E("prv_fail_to_open_per_demand_stress", 0.027, "per demand", "V2", "hydrogen-PRV Bayesian study; stress variant only"),
    # --- vessel and thermal model (register: hours-scale shell time constants) ---
    E("vessel_volume_m3", 10.0, "m3", "REG-UNREAD", "register inventory table uses 10 m3 (Step 5a)"),
    E("vessel_inner_diameter_m", 1.2, "m", "JUDGE", "geometry; length follows from the volume"),
    E("vessel_allowable_stress_mpa", 250.0, "MPa", "JUDGE", "wall thickness from Barlow with this allowable (low-alloy steel vessel; DOE: industry standard for stationary storage, V2)"),
    E("steel_density", 7850.0, "kg/m3", "V2", "carbon / low-alloy steel"),
    E("steel_cp", 490.0, "J/kg/K", "V2", "carbon / low-alloy steel"),
    E("steel_E_gpa", 210.0, "GPa", "V2", "carbon / low-alloy steel"),
    E("h_gas_wall", 20.0, "W/m2/K", "JUDGE", "natural convection of dense hydrogen against the wall"),
    E("h_outer", 12.0, "W/m2/K", "JUDGE", "outer natural convection + radiation"),
    E("gas_temp_gradient_hold_sigma_k", 1.0, "K", "JUDGE", "Addendum A: sigma ~1 K at hold; no stationary-vessel data (U); vehicle tanks 1-2 K axial (V2)"),
    E("gas_temp_gradient_postfill_k", (5.0, 10.0), "K", "JUDGE", "Addendum A: 5-10 K right after a fill, decaying over the gas-wall time constant; vehicle-tank data (V2), extrapolation is JUDGE",
      conflict="register hold-only 1 K -> add post-fill 5-10 K decaying (Addendum 1)"),
    E("gas_temp_gradient_rise_tau_s", 600.0, "s", "JUDGE", "how fast the inlet-side gradient builds while the compressor runs"),
    # --- environment (Dammam/Dhahran reference climate) ---
    E("ambient_july_max_c", 45.2, "C", "V2", "Dammam/Dhahran July mean max (NCM via Wikipedia)"),
    E("ambient_july_min_c", 29.6, "C", "V2", "Dammam/Dhahran July mean min"),
    E("ambient_record_c", 51.0, "C", "V2", "Dammam/Dhahran record", "hot-case bound 50 C"),
    E("ambient_diurnal_amplitude_k", 7.8, "K", "CALC", "half of the 15.6 K July diurnal range"),
    E("ambient_episode_mean_range_c", (14.0, 38.0), "C", "JUDGE", "per-episode mean drawn uniformly; with the amplitude this spans minima/maxima inside the register 25-50 C summer and -10..55 extremes"),
    E("solar_peak_flux_w_m2", 1050.0, "W/m2", "V2", "measured Dhahran peak", conflict="register: no solar-flux input -> solar-flux input, peak 1050 W/m2 hourly (Addendum 1)"),
    E("solar_offset_light_k", 10.0, "K", "V2", "Riyadh roof regressions (derived; roof-not-vessel caveat): light-coloured vessel +10 K at midday peak",
      conflict="register +10-15 K -> base +10 K light / +27 K dark stress (Addendum 1)"),
    E("solar_offset_dark_k", 27.0, "K", "V2", "dark-steel stress case (black +36 K bounding)"),
    E("solar_day_length_h", (5.5, 18.5), "h", "JUDGE", "sunrise/sunset used for the half-sine solar flux"),
    # --- demand ---
    E("fill_mean_kg", 2.9, "kg", "V1", "NREL FY18/2023: mean 2.78-2.9 kg over 1.85 M fills", "spread is JUDGE", conflict="register 3-6 kg -> mean ~2.9 kg (Addendum 1)"),
    E("fill_rate_kg_min", 0.85, "kg/min", "V1", "NREL: mean 0.83-0.90 kg/min, mean 3.2-3.8 min"),
    E("fill_size_clip_kg", (1.0, 6.0), "kg", "JUDGE", "light-duty fill size clip"),
    E("bus_fill_kg", (20.0, 40.0), "kg", "JUDGE", "rare large fills; bus 30 kg in <=10 min (NREL, V1)"),
    E("bus_fill_rate_kg_min", 3.5, "kg/min", "V1", "30 kg in <= 10 min"),
    E("bus_fill_probability", 0.03, "fraction of fills", "JUDGE", "rare"),
    E("demand_kg_per_day", (20.0, 50.0), "kg/day", "REG-UNREAD", "instruction: 20-50 kg/day per module", "station assumption 120-300 kg/day over ~6 modules"),
    E("demand_peak_hours", ((7.0, 9.0), (17.0, 19.0)), "h", "V1", "NREL 2023 (latest report); earlier reports conflict: 07-10 (2015), noon (FY18)", conflict="register 07-10 -> bimodal 07-09 and 17-19 (Addendum 1)"),
    E("demand_weekend_factor", 0.9, "x", "V1", "NREL 2023: weekday 14-15% of weekly fills each, weekend slightly lower", conflict="register 0.6 -> 0.9 (Addendum 1)"),
    # --- sensors (Addendum A) ---
    E("pressure_accuracy_pct_fs", 0.25, "% FS", "V1", "Keller 23SY-H2, Barksdale BHyT datasheets; 0.1% option; stability 0.1-0.3 %FS/yr"),
    E("gas_temp_accuracy_c", 0.5, "C", "V2", "conservative vs Pt100 Class A +/-0.25 C at 50 C (IEC 60751 via tcdirect)"),
    E("gas_temp_range_c", (-40.0, 150.0), "C", "JUDGE", "transmitter range"),
    E("outer_wall_temp_range_c", (-50.0, 100.0), "C", "REG-UNREAD", "kept from the LH2 spec"),
    E("outer_wall_accuracy_c", 0.5, "C", "REG-UNREAD", "kept from the LH2 spec"),
    E("ambient_accuracy_c", 0.3, "C", "REG-UNREAD", "spec (instruction)"),
    E("strain_accuracy_pct_fs", 1.0, "% FS", "REG-UNREAD", "spec (instruction)"),
    E("flow_datasheet_pct_reading", 0.5, "% of reading", "V1", "Micro Motion CNG050 datasheet (E+H +/-0.35%, KOBOLD +/-0.5%)", conflict="register 1% FS -> datasheet mode default, 1% FS as flow_mode='spec' (Addendum 1)"),
    E("flow_datasheet_zero_kg_min", 0.009, "kg/min", "V1", "Micro Motion CNG050 zero stability (~0.54 kg/h)"),
    E("flow_spec_pct_fs", 1.0, "% FS", "REG-UNREAD", "spec mode"),
    E("fill_meter_range_kg_min", (0.0, 0.8), "kg/min", "JUDGE", "Addendum A: 0-0.8 kg/min (0-50 kg/h); vendor ranges V1"),
    E("discharge_meter_range_kg_min", (0.0, 4.0), "kg/min", "JUDGE", "Addendum A: 0-4 kg/min (HPC015 0-3.6, KOBOLD 4)"),
    E("flow_meter_delay_s", (2.0, 9.0), "s", "REG-UNREAD", "instruction: Coriolis delay 2-9 s as a healthy property"),
    E("sensor_bias_frac", 0.5, "x accuracy", "JUDGE", "same split as the LH2 twin (Q12-style placeholder)"),
    E("sensor_drift_frac", 0.3, "x accuracy", "JUDGE", "same split as the LH2 twin"),
    E("sensor_noise_sigma_frac", 0.1, "x accuracy", "JUDGE", "same split as the LH2 twin"),
    E("sensor_drift_tau_days", 3.0, "d", "JUDGE", "same split as the LH2 twin"),
    # --- hydrogen detector ---
    E("h2_lfl_vol_pct", 4.0, "%vol", "V1", "100 %LFL = 4 %vol hydrogen in air"),
    E("h2_detector_accuracy_lfl", 5.0, "%LFL", "V1", "DODTEC lists +/-5% as repeatability, <15 s with 3 m tubing; Draeger catalytic <=+/-1 %LEL at 50 %LEL (conservative default)"),
    E("h2_detector_t90_s", 15.0, "s", "V1", "datasheets: 15-20 s"),
    E("h2_alarm_lfl", 25.0, "%LFL", "V1", "INL (V1); ISO 26142 requires >=1 alarm at <=1 %vol = 25 %LFL (V2)", conflict="old LH2 20/40 (unverified) -> 25 / 50 (INL)"),
    E("h2_trip_lfl", 50.0, "%LFL", "V1", "INL"),
    E("h2_dispersion_pct_per_g_s", 0.2, "%vol per g/s", "JUDGE", "leak mass rate to detector concentration; no dispersion model. 0.2 puts the detector alarm at ~5 g/s (a ~1 mm leak at 300 bar) so 2-5 mm leaks are picked up and 0.1-0.5 mm are not"),
    E("h2_calibration_months", (3.0, 6.0), "months", "V1", "Draeger"),
    # --- leaks and failures ---
    E("leak_cd_range", (0.6, 1.0), "-", "JUDGE", "discharge coefficient of the equivalent orifice"),
    E("leak_main_diameter_mm", (0.1, 1.0), "mm", "REG-UNREAD", "instruction: small slow leak main set"),
    E("leak_stress_diameter_mm", (0.03, 0.1), "mm", "REG-UNREAD", "instruction: stress set labelled expected_miss"),
    E("leak_containment_diameter_mm", (2.0, 5.0), "mm", "REG-UNREAD", "instruction: containment anomaly with detector pickup"),
    E("rupture_diameter_mm", (25.0, 100.0), "mm", "REG-UNREAD", "instruction: rare rupture, <2% of fault episodes"),
    E("hyram_component_weights", "Table 2-3 ratios (compressor, vessel, filter, flange, hose, joint, pipe, valve, instrument)", "-", "V1", "HyRAM+ v5.1 Technical Reference Table 2-3, via summary; absolute rates not used"),
    E("failure_priors", "HyRAM+ Table 2-4: manual valve fail-to-close 1e-3, solenoid 2e-3, nozzle 2e-3, detection+isolation 0.9", "-", "V1", "via summary; scenario priors are 'assumed' (U)"),
    E("fire_heat_flux_kw_m2", 50.0, "kW/m2", "JUDGE", "engulfing-fire flux on the exposed wall fraction"),
    E("fire_exposed_fraction", 0.5, "fraction", "JUDGE", "wall area exposed to the fire"),
    E("fire_duration_s", 3600.0, "s", "JUDGE", "fire exposure lasts 1 h (a sustained 1 MW fire would take the steel past 500 C, where the vessel fails structurally)"),
    E("wall_failure_temp_k", 800.0, "K", "JUDGE", "episode ends on wall over-temperature (steel strength loss)"),
    E("stuck_open_discharge_kg_min", (0.1, 0.3), "kg/min", "JUDGE", "dispenser discharge valve stuck open: continuous draw"),
    E("intercooler_failure_dT_k", 60.0, "K", "JUDGE", "extra compressor discharge temperature when the intercooler fails"),
    E("external_heat_flux_w_m2", 300.0, "W/m2", "JUDGE", "abnormal external heat input (hot spot) at full severity"),
    E("strain_scf_max", 4.0, "-", "JUDGE", "stress-concentration growth at full severity (as the LH2 twin)"),
    E("structural_cycles_to_full_scf", 40.0, "pressure cycles", "JUDGE", "compressor cycles after onset for the SCF to reach its maximum"),
    # --- alarms (static) ---
    E("gas_temp_alarm_c", (85.0, 100.0), "C", "JUDGE", "TAH / TAHH on gas temperature; 85 C is the older SAE J2601 vehicle-tank limit (V2, older edition) used only as an analog"),
    # --- compressor stop policy (found by the healthy-run check, step 5b) ---
    E("compensated_ref_temp_c_default", 60.0, "C", "JUDGE", "medium/high classes, light vessel: the fixed stop at MOP leaves almost no thermal margin (peak 1.018 x MOP against PAH at 1.02 over 120 random units; the generated unseen unit U01 alarmed in 3 healthy segments once sensor error was added: cool start, afternoon sun +9 K = +9 bar). Compensated at 60 C: 0/120 alarming, peak 1.003 x MOP",
      conflict="instruction: compressor stops at MOP -> MOP is the rating at the 60 C reference gas temperature; the compressor stops at the temperature-compensated MOP (fixed stop kept as stop_mode='fixed')"),
    E("compensated_ref_temp_c_low", 65.0, "C", "JUDGE", "temperature-compensated compressor stop for the low class: 2% of 50 bar (PAH) is 1 bar = 6 K of margin at 0.168 bar/K, so a fixed stop at MOP alarms in 12/12 healthy runs",
      conflict="instruction: compressor stops at MOP -> stops at temperature-compensated MOP where a fixed stop alarms in healthy runs (found by check 5b)"),
    E("compensated_ref_temp_c_dark", 70.0, "C", "JUDGE", "dark-vessel stress case (+27 K sun-air offset; gas peaks near 70 C): a fixed stop alarms in 10/12 medium runs; compensated at 70 C: 0/48 (60 C: 3/24)",
      conflict="as above"),
    E("compensated_ref_temp_c_dark_low", 80.0, "C", "JUDGE", "low class and dark vessel: still 1/48 healthy runs alarm at 80 C (gas reaches 79 C against 6 K of margin); the combination is NOT in the dataset"),
    # --- historian (same filters as the LH2 reference configuration) ---
    E("historian_exception_forced_s", 600.0, "s", "JUDGE", "instruction: historian realism exactly as for LH2"),
    E("historian_compression_forced_s", 28800.0, "s", "JUDGE", "as above"),
    E("historian_compdev_mult", 2.0, "x exception deadband", "JUDGE", "as above"),
    E("historian_fault_dropout_per_day", 0.2, "events/day/tag", "JUDGE", "as above (injected dropout, mean 300 s)"),
    E("historian_fault_stale_per_day", 0.1, "events/day/tag", "JUDGE", "as above (mean 900 s)"),
    E("historian_fault_flatline_per_day", 0.05, "events/day/tag", "JUDGE", "as above (mean 7200 s)"),
    E("historian_fault_outofrange_per_day", 0.05, "events/day/tag", "JUDGE", "as above (mean 120 s)"),
    E("demand_scaling_by_class", "inventory at MOP / inventory of the medium class, fills capped at 25% of the inventory", "-", "JUDGE", "a 50 bar store holds ~39 kg in 10 m3 and cannot serve 20-50 kg/day"),
    E("verification_tolerance", 0.02, "fraction", "REG-UNREAD", "instruction step 5a"),
]

REGISTRY: dict[str, Entry] = {e.name: e for e in _ENTRIES}
_USED: set[str] = set()


def value(name: str):
    """Look up an entry and record that it was used (for manifests)."""
    _USED.add(name)
    return REGISTRY[name].value


def used() -> list[dict]:
    return [{"name": e.name, "value": e.value, "unit": e.unit, "tag": e.tag, "source": e.source, "basis": e.basis,
             "placeholder": e.is_placeholder, "conflict": e.conflict} for n, e in REGISTRY.items() if n in _USED]


def reset_usage() -> None:
    _USED.clear()


def conflicts() -> list[dict]:
    return [{"name": e.name, "resolved_as": e.conflict, "tag": e.tag, "source": e.source} for e in REGISTRY.values() if e.conflict]
