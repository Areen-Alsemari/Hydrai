#!/bin/bash
# Tool ablations on dev (leave-one-module-out). Investigation-only removals reuse the main fusion model; removals of a tool that feeds the fusion retrain the
# fusion without its features (stride 10 for speed, with its own all-features reference "s10" so the comparison is like for like).
# Usage: bash scripts/cgh2_agent_ablate.sh   (about 1.5 h; writes output/cgh2_cache/agent/runs_<tag>.pkl)
set -e
cd "$(dirname "$0")/.."
source .venv/bin/activate
run() { python scripts/cgh2_agent_run_dev.py --tag "$1" "${@:2}" | tail -1; }
meta() { python scripts/cgh2_agent_meta.py --tag "$1" --stride 10 --drop "$2" | tail -1; }

# --- investigation-only removals (main fusion model)
run noT9  --off T9_twin_verifier
run noT10 --off T10_forecast_consequence
run noT11 --off T11_hold_test_planner
run noT12 --off T12_alarm_context
run noT13 --off T13_procedures
run nostatic --no-static
run noInvestigation --off T9_twin_verifier,T10_forecast_consequence,T11_hold_test_planner,T12_alarm_context,T13_procedures --no-static

# --- removals that retrain the fusion without the tool's features
meta s10 "NONE_"
run s10 --meta-tag s10
for T in T2 T3 T4 T5 T6; do
  case $T in
    T2) OFF=T2_inventory_leak,T9_twin_verifier,T10_forecast_consequence,T11_hold_test_planner ;;
    T3) OFF=T3_thermal_state ;;
    T4) OFF=T4_pressure_behaviour ;;
    T5) OFF=T5_sensor_integrity ;;
    T6) OFF=T6_structural ;;
  esac
  meta no$T "${T}_"
  run no$T --meta-tag no$T --off $OFF
done
meta noModelTools "T3_,T4_,T5_,T6_"
run noModelTools --meta-tag noModelTools --off T3_thermal_state,T4_pressure_behaviour,T5_sensor_integrity,T6_structural
echo ablations done
