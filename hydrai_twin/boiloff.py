"""
Two-tier boil-off model, Sec. 7. The two tiers are kept as separate,
explicitly-selected modes -- never averaged or blended into one number,
per Sec. 7's own framing ("use a two-tier framing rather than picking one
number") and the user's explicit instruction.

Mass balance (Sec. 7): dM/dt = mdot_in - mdot_out - mdot_BOG
"""

from __future__ import annotations

from hydrai_twin.constants import BOILOFF_LADDER_PCT_PER_DAY, DEFAULT_BOILOFF_MODE

SECONDS_PER_DAY = 86400.0


def boiloff_rate_kg_s(mass_kg: float, mode: str = DEFAULT_BOILOFF_MODE, stage: str = "normal") -> float:
    """mdot_BOG for the current tank mass, mode ('baseline'|'target'), and
    severity stage ('excellent'|'normal'|'mild'|'severe'|'major'). Sec. 7
    ground-truth episodes should stay on stage='normal' for the selected
    mode; other stages exist for the fault-injection generator that follows
    this one (insulation-degradation scenario)."""
    if mode not in BOILOFF_LADDER_PCT_PER_DAY:
        raise ValueError(f"unknown boil-off mode '{mode}', expected one of {list(BOILOFF_LADDER_PCT_PER_DAY)}")
    ladder = BOILOFF_LADDER_PCT_PER_DAY[mode]
    if stage not in ladder:
        raise ValueError(f"unknown boil-off stage '{stage}', expected one of {list(ladder)}")
    pct_per_day = ladder[stage]
    return mass_kg * (pct_per_day / 100.0) / SECONDS_PER_DAY


def boiloff_rate_pct_per_day(mode: str = DEFAULT_BOILOFF_MODE, stage: str = "normal") -> float:
    return BOILOFF_LADDER_PCT_PER_DAY[mode][stage]
