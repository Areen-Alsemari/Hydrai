"""
First observable deviation: when does a fault first become visible in the
data, as distinct from when it truly starts?

TRUE ONSET is the physical cause beginning (`onset_s`). FIRST OBSERVABLE
DEVIATION is the earliest time a channel departs from what a healthy twin of
the SAME episode (same seed, module, fill, weather) would have shown, by more
than the sensor's own noise, for several consecutive samples. Both go in the
manifest so detection delay and lead time can be scored against either.

Definition (an evaluation convention, not a plant value):
  * compare NOISE-FREE ground truth of the fault run with the paired healthy
    counterfactual run, on the 60 s slow-layer grid;
  * a channel deviates at the first sample from which |difference| exceeds
    k * sigma_sensor for `N_CONSECUTIVE` consecutive samples, where
    sigma_sensor is the Sec. 9 accuracy treated as a 2-sigma bound (sensors.py);
  * two sensitivities: k = 3 ("sensitive") and k = 10 ("clear").
  * sensor faults live in the measurement layer: the deviation is the first
    single outlier above OUTLIER_K sigma on the affected tag.

Scale note (deliberately NOT changed when the sensor error model was split into bias + drift + noise): sigma stays
accuracy/2, i.e. the 2-sigma spec bound on TOTAL instrument error, so k=3 means "1.5x the whole stated accuracy". The
random-noise part alone is now 5x smaller (sensors.SensorErrorSplit), so these times are conservative; they were not
tightened to look better.

This is an IDEAL-OBSERVER time: a real detector has no healthy counterfactual
and must also absorb weather and module differences, so it will detect later.
Hence it is a bound for scoring lead time, not a target the agent must hit.
Channels are reported individually so the result can be recomputed under any
channel mask (channels.py) -- a fault visible only on an untagged channel is
not observable to a model restricted to the dashboard's tags.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np

from hydrai_twin import constants as C
from hydrai_twin.sensors import ACCURACY_SIGMA_DIVISOR, accuracy_abs

K_SENSITIVE = 3.0
K_CLEAR = 10.0
N_CONSECUTIVE = 5
OUTLIER_K = 10.0
SENSOR_FAULT_TAG = "liquid_temp_c"

# measurement tag -> NOISE-FREE ground-truth key recorded by the generator
NOISE_FREE_KEY = {
    "inner_wall_temp_c": "inner_wall_nf_c",
    "h2_concentration_pct": "h2_nf_pct",
    "strain_ue": "strain_nf_ue",
}


def sensor_sigma(tag: str) -> float:
    return accuracy_abs(tag) / ACCURACY_SIGMA_DIVISOR


def _t_s(rec: dict[str, Any]) -> float:
    return float(rec["system_context"]["t_s"])


def _first_run(mask: np.ndarray, n: int) -> int | None:
    """Index of the first position starting a run of `n` consecutive Trues."""
    if len(mask) < n:
        return None
    run = np.convolve(mask.astype(int), np.ones(n, dtype=int), mode="valid")
    hits = np.flatnonzero(run >= n)
    return int(hits[0]) if len(hits) else None


def first_deviation_times(
    fault_slow: list[dict[str, Any]],
    healthy_slow: list[dict[str, Any]],
    fault_id: int,
    sigma_fn=None,
    tags=None,
    noise_free_key=None,
    sensor_fault_tag: str | None = None,
) -> dict[str, dict[str, float | None]]:
    """Per measurement tag: {'k3': t_s|None, 'k10': t_s|None}. `sigma_fn(tag, healthy_reference_array)` gives the
    sigma scale (scalar or per-sample array, in ground-truth units); default = Sec. 9 accuracy / 2 for every tag.
    The instrument view (sensor_view.py) supplies the scale for the %LFL H2 detector and the log vacuum gauge.
    Optional (append-only, for the CGH2 twin; defaults are the LH2 behaviour): `tags` = channels to test (default: the LH2 Sec. 9 set),
    `noise_free_key` = {tag: ground-truth key} (default NOISE_FREE_KEY), `sensor_fault_tag` = tag of the single-outlier rule (default
    SENSOR_FAULT_TAG)."""
    n = min(len(fault_slow), len(healthy_slow))
    out: dict[str, dict[str, float | None]] = {}
    times = np.array([_t_s(r) for r in fault_slow[:n]])
    nfk = NOISE_FREE_KEY if noise_free_key is None else noise_free_key
    for tag in (C.SENSOR_SPECS if tags is None else tags):
        key = nfk.get(tag, tag)
        f = np.array([r["simulation_ground_truth"][key] for r in fault_slow[:n]], dtype=float)
        h = np.array([r["simulation_ground_truth"][key] for r in healthy_slow[:n]], dtype=float)
        sigma = sensor_sigma(tag) if sigma_fn is None else sigma_fn(tag, h)
        dev = np.abs(f - h)
        entry: dict[str, float | None] = {}
        for label, k in (("k3", K_SENSITIVE), ("k10", K_CLEAR)):
            i = _first_run(dev > k * sigma, N_CONSECUTIVE)
            entry[label] = float(times[i]) if i is not None else None
        out[tag] = entry
    if fault_id == 1:
        ftag = SENSOR_FAULT_TAG if sensor_fault_tag is None else sensor_fault_tag
        m = np.array([r["measurements"][ftag] for r in fault_slow[:n]], dtype=float)
        h = np.array([r["simulation_ground_truth"][nfk.get(ftag, ftag)] for r in healthy_slow[:n]], dtype=float)
        sig_t = sensor_sigma(ftag) if sigma_fn is None else sigma_fn(ftag, h)
        idx = np.flatnonzero(np.abs(m - h) > OUTLIER_K * sig_t)
        t = float(times[idx[0]]) if len(idx) else None
        out[ftag] = {"k3": t, "k10": t}     # a single outlier is the observable event
    return out


def observable_time(per_channel: dict[str, dict[str, float | None]], channels: set[str] | frozenset[str] | None, k: str = "k3") -> float | None:
    """Earliest deviation over `channels` (None = all channels)."""
    ts = [v[k] for tag, v in per_channel.items() if (channels is None or tag in channels) and v[k] is not None]
    return min(ts) if ts else None


def parse_t_s(ts_iso: str, t0_iso: str) -> float:
    return (datetime.fromisoformat(ts_iso) - datetime.fromisoformat(t0_iso)).total_seconds()
