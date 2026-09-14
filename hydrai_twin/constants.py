"""
Every constant here is transcribed from HYDRAI_Consolidated_Parameter_Workbook.md.
Each value/block cites the workbook section it came from so the mapping from
spec -> code is auditable. Nothing here is a fresh assumption; where the
workbook itself flags something as a "proposed default", that is repeated
in the comment.
"""

# ---------------------------------------------------------------------------
# Section 1 - System Definition / Section 2 - Geometry (per module)
# ---------------------------------------------------------------------------
N_MODULES = 6                       # Sec. 1: modules M01-M06
MODULE_IDS = [f"M{n:02d}" for n in range(1, N_MODULES + 1)]

TANK_INTERNAL_VOLUME_M3 = 10.0      # Sec. 2
TANK_INTERNAL_RADIUS_M = 1.00       # Sec. 2
TANK_INTERNAL_DIAMETER_M = 2.00     # Sec. 2
TANK_LENGTH_M = 3.18                # Sec. 2
WALL_THICKNESS_M = 10e-3            # Sec. 2 (flagged assumption) / confirmed as
                                     # working value by the UG-27 check in Sec. 17.1
INNER_SURFACE_AREA_M2 = 26.1        # Sec. 2
NOMINAL_FILL_PCT = 85.0             # Sec. 2 / Sec. 8 "target fill"
MAX_MODELED_FILL_PCT = 90.0         # Sec. 2 / Sec. 8
LH2_MASS_AT_NOMINAL_FILL_KG = 603.2 # Sec. 2 arithmetic self-check (8.5 m3 * 70.97 kg/m3)

# ---------------------------------------------------------------------------
# Section 3 - LH2 physical properties (fixed constants)
# Real thermophysical state (density, T_sat, latent heat, etc.) is NOT
# hardcoded here -- it comes from CoolProp's HEOS::Hydrogen backend
# (Leachman et al. 2009 EOS), per Sec. 4.5 and hydrai_twin/eos.py.
# These are kept only as reference/labeling constants, matched against
# CoolProp at startup in eos.py to confirm the backend agrees with Sec. 3.
# ---------------------------------------------------------------------------
H2_MOLECULAR_WEIGHT_G_MOL = 2.016     # Sec. 3
H2_NBP_C = -252.76                    # Sec. 3
H2_TCRIT_C = -239.96                  # Sec. 3 (Tc = 33.19 K, matches Leachman 2009 exactly)
H2_PCRIT_BAR = 13.15                  # Sec. 3
H2_LATENT_HEAT_MJ_KG = 0.446          # Sec. 3 (reference value; CoolProp used for sim)
H2_FLAMMABILITY_RANGE_VOL_PCT = (4.0, 75.0)  # Sec. 3

# ---------------------------------------------------------------------------
# Section 4.1 - 304L point values near 20 K (used as sanity bounds, not
# a T-dependent function -- see materials.py for the E(T)/yield discussion)
# ---------------------------------------------------------------------------
YIELD_STRENGTH_20K_MPA = (682.0, 1059.0)   # Sec. 4.1 / Sec. 4.4 (MDPI 2023 exact match at upper bound)
TENSILE_STRENGTH_20K_MPA = (1943.0, 2433.0)  # Sec. 4.1

# ---------------------------------------------------------------------------
# Section 5 - Operating envelope, pressure (bar absolute)
# ---------------------------------------------------------------------------
PRESSURE_NORMAL_BAR = 1.2                 # Sec. 5 "Normal pressure"
PRESSURE_NORMAL_RANGE_BAR = (1.0, 1.5)    # Sec. 5 "Normal operating range"
PRESSURE_LOW_WARNING_BAR = 0.8            # Sec. 5
PRESSURE_HIGH_WARNING_BAR = 2.0           # Sec. 5
PRESSURE_CRITICAL_BAR = 3.0               # Sec. 5
PRESSURE_MAWP_BAR = 6.0                   # Sec. 5
PRESSURE_MIN_MODELED_BAR = 0.5            # Sec. 5

# ---------------------------------------------------------------------------
# Section 6 - Operating envelope, temperature (deg C)
# ---------------------------------------------------------------------------
TEMP_LH2_NORMAL_C = (-253.0, -250.0)
TEMP_LH2_WARNING_C = -248.0     # "warning if >"
TEMP_LH2_CRITICAL_C = -245.0    # "critical if >"

TEMP_INNER_WALL_NORMAL_C = (-253.0, -245.0)
TEMP_INNER_WALL_WARNING_C = -240.0
TEMP_INNER_WALL_CRITICAL_C = -235.0

TEMP_OUTER_WALL_NORMAL_C = (-20.0, 40.0)
TEMP_OUTER_WALL_WARNING_C = 50.0
TEMP_OUTER_WALL_CRITICAL_C = 60.0

TEMP_AMBIENT_NORMAL_C = (-20.0, 60.0)
TEMP_AMBIENT_WARNING_C = 60.0
TEMP_AMBIENT_CRITICAL_C = 70.0

# ---------------------------------------------------------------------------
# Section 7 - Boil-off model, two-tier (kept separate, NOT blended)
#
# "baseline" = the decided ground-truth tier for the digital twin
#   (0.30%/day normal, scaled ladder anchored to real comparable/larger
#   vacuum+MLI vessels -- tank-car + 50 m3 literature).
# "target"   = HYDRAI's original roadmap numbers (0.05-0.10%/day),
#   labeled as a future-tech target enabled by a named upgrade path
#   (vapor-cooled shield / para-ortho catalytic conversion), not current
#   as-built performance.
# ---------------------------------------------------------------------------
BOILOFF_LADDER_PCT_PER_DAY = {
    "baseline": {
        "excellent": 0.15,
        "normal": 0.30,
        "mild": 0.60,
        "severe": 1.20,
        "major": 1.50,   # ">" this value in the workbook framing
    },
    "target": {
        "excellent": 0.05,
        "normal": 0.10,
        "mild": 0.20,
        "severe": 0.40,
        "major": 0.50,   # ">" this value in the workbook framing
    },
}
DEFAULT_BOILOFF_MODE = "baseline"   # Sec. 7: "use as the ground truth ... a
                                     # safety-monitoring AI's core credibility
                                     # depends on 'normal' being real"

# ---------------------------------------------------------------------------
# Section 8 - Filling / discharge flow parameters (kg/s unless noted)
# ---------------------------------------------------------------------------
INITIAL_FILL_PCT = 10.0
TARGET_FILL_PCT = 85.0
MAX_MODELED_FILL_PCT_FLOW = 90.0
FILL_FLOW_NORMAL_KG_S = 1.0
FILL_FLOW_RANGE_KG_S = (0.5, 2.0)
FLOW_MEASUREMENT_HZ = 10.0

DISCHARGE_DEMAND_KG_S = {
    "low": 0.2,
    "normal": 0.5,
    "high": 1.0,
    "peak": 1.5,
}

# ---------------------------------------------------------------------------
# Section 9 - Sensor specification
# Each entry: (range_min, range_max, unit, accuracy_kind, accuracy_value, sampling_hz)
# accuracy_kind: "pct_fs" -> accuracy_value is a % of (range_max - range_min)
#                "abs"    -> accuracy_value is an absolute +/- in `unit`
# The mapping from this stated accuracy to a Gaussian sigma for noise
# injection is a simulation modeling choice (see sensors.py); Sec. 9 gives
# only the instrument specs, not a noise model.
# ---------------------------------------------------------------------------
SENSOR_SPECS = {
    "pressure_bar_a":        (0.0, 6.0,    "bar(a)", "pct_fs", 0.25, 1.0),
    "liquid_temp_c":         (-270.0, -200.0, "C",    "abs",    0.5,  1.0),
    "inner_wall_temp_c":     (-270.0, 50.0, "C",      "abs",    0.5,  1.0),
    "outer_wall_temp_c":     (-50.0, 100.0, "C",      "abs",    0.5,  0.2),
    "h2_concentration_pct":  (0.0, 100.0,  "%vol",    "pct_fs", 2.0,  5.0),
    "liquid_level_pct":      (0.0, 100.0,  "%",       "pct_fs", 0.5,  1.0),
    "mass_flow_fill_kg_s":   (0.0, 2.0,    "kg/s",    "pct_fs", 1.0,  10.0),
    "mass_flow_discharge_kg_s": (0.0, 2.0, "kg/s",    "pct_fs", 1.0,  10.0),
    "strain_ue":             (-5000.0, 5000.0, "ue",  "pct_fs", 1.0,  10.0),
    "vacuum_pressure_pa":    (0.0, 1000.0, "Pa",      "pct_fs", 1.0,  0.1),
    "ambient_temp_c":        (-20.0, 60.0, "C",       "abs",    0.3,  0.1),
}

# ---------------------------------------------------------------------------
# Section 17.2 - Control/valve logic (proposed default)
# ---------------------------------------------------------------------------
PCV_SETPOINT_BAR = PRESSURE_NORMAL_BAR          # regulate toward 1.2 bar(a)
PCV_BAND_BAR = PRESSURE_NORMAL_RANGE_BAR        # hold within (1.0, 1.5)
PRV_SETPOINT_BAR = PRESSURE_MAWP_BAR            # last-resort mechanical relief, not
                                                 # modeled in normal-operation episodes
FILL_VALVE_CLOSE_PCT = (NOMINAL_FILL_PCT, MAX_MODELED_FILL_PCT_FLOW)  # closes 85-90%

# ---------------------------------------------------------------------------
# Section 17.5 - Leak discharge model constants
# ---------------------------------------------------------------------------
H2_GAMMA = 1.41                       # Sec. 17.5
CHOKE_PRESSURE_RATIO = 0.528          # Sec. 17.5: (2/(gamma+1))^(gamma/(gamma-1))
DISCHARGE_COEFFICIENT_CD = 0.62       # Sec. 17.5 proposed default (HyRAM+)

# ---------------------------------------------------------------------------
# Section 17.3 - Leak-size severity ladder, HyRAM+ standard release-size
# categories, as FRACTIONS of a reference flow area (Sec. 17.3 gives the
# fractions but not an absolute reference area for this specific vessel).
# ---------------------------------------------------------------------------
LEAK_SEVERITY_AREA_FRACTION = {
    "pinhole": 0.0001,       # 0.01%
    "small": 0.001,          # 0.1%
    "small_medium": 0.01,    # 1%
    "medium_large": 0.1,     # 10%
    "full_bore": 1.0,        # 100%
}

# NOT a workbook value -- Sec. 17.3 gives the ladder as fractions of a
# "reference flow area" without specifying that area for this vessel. A 3/4"
# (DN20, ~19 mm ID) connection is assumed as a representative instrument/vent
# penetration size, purely to convert the ladder's fractions into an
# absolute leak area. Cross-checked for plausibility (not confirmed by
# engineering) against this workbook's own Sec. 8 fill-flow data: at typical
# cryogenic transfer velocities, the main fill/discharge piping needed to
# carry the stated 2 kg/s max flow works out to roughly 85-110 mm -- so 19mm
# sits well below the main process lines, consistent with representing a
# small instrument/vent connection (a common real leak source) rather than a
# main-line breach. This is also how HyRAM+ itself typically frames
# reference leak scenarios. Still a placeholder pending final engineering
# confirmation, same status as the other Sec. 17 proposed defaults.
REFERENCE_LEAK_ORIFICE_DIAMETER_M = 0.019

# Not workbook-given -- standard sea-level atmospheric pressure, used as the
# ambient-side pressure in Sec. 17.5's choke-ratio check for leak scenarios.
STANDARD_ATMOSPHERIC_PRESSURE_BAR = 1.01325

# ---------------------------------------------------------------------------
# Section 10 - Insulation-degradation staging sub-table (health% -> heat-leak
# multiplier relative to a healthy baseline). Reused, per module docstring in
# fault_episode.py, as a general heat-leak multiplier applied on top of
# whichever Sec. 7 two-tier boil-off mode is active -- NOT a third boil-off
# tier, just the ratio Sec. 10 itself specifies (100/150/250% of baseline).
# ---------------------------------------------------------------------------
INSULATION_HEALTH_HEATLEAK_TABLE = [
    (100.0, 1.0),
    (70.0, 1.5),
    (40.0, 2.5),
]

# ---------------------------------------------------------------------------
# Section 10 - Fault / anomaly taxonomy (AI labels). Only "Normal" is used by
# the phase-1 normal-operation generator; the rest are wired up for the
# fault-injection generator that follows this one.
# ---------------------------------------------------------------------------
FAULT_LABELS = {
    0: "normal",
    1: "sensor_fault",
    2: "insulation_degradation",
    3: "vacuum_degradation",
    4: "abnormal_pressure_rise",
    5: "containment_anomaly",
    6: "structural_concern",
    -1: "unknown_anomaly",
}
