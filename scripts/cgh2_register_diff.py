"""Diff of the CGH2 twin against HYDRAI_GAS_H2_Decision_Register.md (read after the build). Writes output/reports/cgh2_register_diff.md.

Every row: the register value, the value in the twin (registry / generated manifest), the verdict and why. Rows marked MATERIAL would change
the generated data if the register value were adopted; per the instruction the datasets are NOT regenerated and the decision is the owner's.
The healthy-operation numbers for the low-pressure alarm are measured from the generated medium set.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hydrai_twin.cgh2 import registry as R
from hydrai_twin.cgh2.config import make_class
from ml.headline_metrics import alarm_events

ROOT = Path(__file__).resolve().parent.parent


def pal_numbers(root: Path, mop: float):
    m = json.loads((root / "manifest.json").read_text())
    hours = events = bad = n = 0.0
    minp = []
    for e in m["episodes"]:
        if e["role"] == "commissioning":
            continue
        t = pq.read_table(root / e["slow_file"], columns=["ctx__t_s", "live__pressure_bar_a"]).to_pydict()
        ts, P = np.array(t["ctx__t_s"]), np.array(t["live__pressure_bar_a"], dtype=float)
        h = ts < (e["onset_s"] if e["onset_s"] is not None else np.inf)
        if not h.any():
            continue
        hours += h.sum() / 60.0
        ev = len(alarm_events(ts, (P < 0.7 * mop) & h, 300.0))
        events += ev; bad += ev > 0; n += 1
        minp.append(P[h].min() / mop)
    return hours, events, int(bad), int(n), float(np.median(minp)), float(min(minp))


def main():
    c = {k: make_class(k) for k in ("low", "medium", "high")}
    hours, events, bad, n, med_min, min_min = pal_numbers(ROOT / "output/cgh2/medium", 300.0)
    rows = [
        ("Class MOP 50 / 300 / 350; MAWP = PRV set 55 / 330 / 385; compressor start/stop 42.5/50, 255/300, 300/350; compressor flow 10 / 20 / 25 kg/h", "same", "MATCH", "-"),
        ("PAH / PAHH = 52.5/54, 315/324, 367.5/378 (1.05 / 1.08 x MOP)", f"{c['medium'].pah_bar:.0f} / {c['medium'].pahh_bar:.0f} bar (1.02 / 1.05 x MOP)", "KEPT MINE (addendum overrides the register)",
         "At 1.08 the trip sits inside the PRV tolerance band (1.10 +/- 3%). Instruction: the addendum overrides."),
        ("Low-pressure alarm 70 % of MOP (JUDGE)", "NOT implemented (no low-pressure alarm)", "**MATERIAL - decision needed**",
         f"Adopting it makes the healthy twin alarm: {events:.0f} events in {hours:,.0f} healthy hours ({events / (hours / 168):.1f} per week), in {bad} of {n} episodes; healthy minimum pressure median {med_min:.2f} x MOP, lowest {min_min:.2f}. "
         "Peak-hour draws (10 fills in 2 h against a 20 kg/h compressor) plus cool nights take the store below 70 %. Either the alarm is lower (about 50 %), or the compressor is bigger, or demand lower. It would also give leaks a static alarm (they have none today)."),
        ("Transmitter range low class 0-60 bar (medium 0-400, high 0-500)", f"low {c['low'].transmitter_range_bar:.0f} bar", "MINOR (low OOD set only)", "0.25 % FS of 100 vs 60 bar: pressure noise 1.7x larger in the low set than the register implies."),
        ("Strain range +/-1000 ue (JUDGE)", "+/-5000 ue (spec), 1 % FS = 100 ue", "**MATERIAL - decision needed**",
         "With +/-1000 ue the gauge error is 20 ue (5x smaller, better structural detectability) but 4.0 % of healthy samples (|strain| up to 1.2-1.5k ue at 300 bar x SCF) would saturate."),
        ("Gas temperature range -40..+100 C; alarm 85 C (no second alarm)", "-40..+150 C; TAH 85, TAHH 100 C (JUDGE)", "**MATERIAL for fire/thermal cases**",
         "A probe clipped at 100 C cannot read the fire or intercooler-failure cases above 100 C and TAHH 100 would be unreachable. Healthy gas never exceeds 61 C (light) / 71 C (dark), so healthy data is unaffected."),
        ("Outer wall -20..+80 C; ambient -10..55 C", "-50..+100 C; -20..+60 C", "MINOR", "Only clipping at the extremes (fire case wall > 150 C; Dammam record 51 C)."),
        ("Whole-shell thermal time constant: low ~1 h, medium ~5-10 h, high ~10 h (CALC)", f"{c['low'].tau_wall_ambient_s() / 3600:.1f} / {c['medium'].tau_wall_ambient_s() / 3600:.1f} / {c['high'].tau_wall_ambient_s() / 3600:.1f} h (from wall thickness, h = 20 / 12 W/m2K)", "MATCH (high 7.6 vs ~10 h: minor)", "Gas-wall time constant 8 / 42 / 48 min (register: tens of minutes)."),
        ("Heat transfer h = 20 inner / 10 outer W/m2K", "20 / 12", "MATCH (outer 12 vs 10: minor)", "-"),
        ("PRV pop tolerance +/-3 %, blowdown <= 5 % (carried over from the marine rule, placeholder)", "+/-3 %; blowdown 7 % nominal / 10 % conservative", "KEPT MINE (addendum overrides)", "Spring PRV 7-10 % (V2)."),
        ("TPRD optional in the fire scenario (110 C, U)", "none; fire handled by PRV at 121 % accumulation", "KEPT MINE (addendum overrides)", "Michigan rule: thermal devices belong to composite containers."),
        ("Weekend factor 0.6; peak 07-10; fills 3-6 kg", "0.9; bimodal 07-09 and 17-19; mean 2.9 kg (clip 1-6)", "KEPT MINE (addendum overrides)", "NREL 2023 (V1)."),
        ("Solar shell offset +10-15 K", "+10 K light vessel (base), +27 K dark (stress); solar flux peak 1050 W/m2", "KEPT MINE (addendum overrides)", "Measured Dhahran peak (V2)."),
        ("Flow meters 1 % FS; fill range 0-2 x compressor flow", "datasheet mode 0.5 % of reading + 0.009 kg/min (1 % FS as flow_mode='spec'); fill 0-0.8 kg/min", "KEPT MINE (addendum overrides)", "Micro Motion datasheet (V1)."),
        ("Gas-temperature gradient sigma ~1 K (placeholder)", "1 K at hold; 5-10 K after a fill, decaying over the gas-wall time constant", "KEPT MINE (addendum extends)", "Vehicle-tank data (V2); extrapolation JUDGE."),
        ("Detector alarm 25 / trip 50 %LFL, +/-5 %LFL, T90 < 15 s", "same", "MATCH", "-"),
        ("Compressor stops at MOP (fixed)", "stop pressure compensated to a design gas temperature (60 C)", "KEPT MINE (accepted by the owner)", "A fixed stop leaves ~6 bar below PAH against a 6-9 bar afternoon thermal rise."),
        ("Discrete: compressor run/stop/TRIP; valves open/closed/FAULT", "compressor run/stop; valves open/closed", "MINOR", "No trip/fault state: the twin has no trips. Not data-changing for the faults modelled."),
        ("Shell material 304L (team-stated)", "carbon/low-alloy steel properties (allowable 250 MPa, 490 J/kg/K)", "NOTE", "Material only sets the shell heat capacity; keep '304L (team-stated)' in the appendix as the register says."),
        ("Abel-Noble within ~1 % below 350 bar", "measured 0.6 % over -10..60 C, 1.09 % at -40 C", "MATCH", "CoolProp used throughout."),
        ("Headline findings (7 % pressure per 20 K; 0.1 mm loses 1 % in 3.4-5.7 h and 10 % in 36-60 h; 0.5 mm 1 % in 8-14 min; 0.5 vs 2.4 kg/h meter)", "7 % (20.8 bar / 300); 4.1 h and 42.9 h; 12 min; 0.51 vs 2.40 kg/h", "MATCH", "Reproduced by scripts/cgh2_verify.py."),
    ]
    out = ["# CGH2: diff of the twin against the Decision Register", "",
           "Read after the build (the register file was missing at build time). Rows marked MATERIAL would change the generated data if the register value were adopted. **The datasets were NOT regenerated; the decision is the owner's.**", "",
           "| register | twin | verdict | why / numbers |", "|---|---|---|---|"]
    out += [f"| {a} | {b} | {v} | {w} |" for a, b, v, w in rows]
    out += ["", "## Decisions needed (none blocks the agent work, which runs on the existing data)", "",
            "1. **Low-pressure alarm (PAL).** Adopt the register's 70 % of MOP, change the level, or leave it out? With 70 % the healthy twin alarms 1.7/week. The static baseline in all reports is WITHOUT a PAL and says so.",
            "2. **Strain range** +/-1000 ue (register) or +/-5000 ue (spec, current)? Changes the structural-class detectability by about 5x in noise.",
            "3. **Gas-temperature range** 100 C (register) or 150 C (current)? Only the fire / intercooler-failure cases are affected.",
            "4. Low-class transmitter range 60 vs 100 bar (minor)."]
    p = ROOT / "output" / "reports" / "cgh2_register_diff.md"
    p.write_text("\n".join(out) + "\n")
    print(f"wrote {p}")
    print(f"PAL @70% MOP on healthy data: {events:.0f} events / {hours:,.0f} h = {events / (hours / 168):.2f}/wk; {bad}/{n} episodes")


if __name__ == "__main__":
    main()
