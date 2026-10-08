"""Every tool's monitor() must be causal: the value at tick i computed on the data up to i equals the value computed on the whole episode.
This is what makes the accelerated replay equivalent to running the agent tick by tick on a live stream."""

import pytest

np = pytest.importorskip("numpy")
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if not (ROOT / "output" / "cgh2" / "medium" / "manifest.json").exists() or not (ROOT / "output" / "cgh2_cache" / "agent" / "fit_M01.pkl").exists():
    pytest.skip("CGH2 dataset or agent fits not built", allow_module_level=True)

import pickle

from hydrai_twin.cgh2_agent import fusion as F
from hydrai_twin.cgh2_agent.features import FEATURES, feature_matrix
from hydrai_twin.cgh2_agent.session import get_units
from hydrai_twin.cgh2_agent.stream import slice_unit
from hydrai_twin.cgh2_agent.tools import Ctx, load_all_tools

TOOLS = ("T1_data_integrity", "T2_inventory_leak", "T3_thermal_state", "T4_pressure_behaviour", "T5_sensor_integrity", "T6_structural")


@pytest.mark.parametrize("name,cut", [("M01__leak-0.25mm", 6000), ("M01__normal-refuelling0", 9000)])
def test_monitors_are_causal(name, cut):
    load_all_tools()
    _, units = get_units()
    u = units[name]
    fb = pickle.load(open(F.CACHE / "fit_M01.pkl", "rb"))
    full = Ctx(u, fb["fit"], fb["baseline"])
    part = Ctx(slice_unit(u, cut), fb["fit"], fb["baseline"])
    for tool in TOOLS:
        a, b = full.monitor(tool), part.monitor(tool)
        for k in b:
            x, y = np.asarray(a[k])[cut - 30:cut], np.asarray(b[k])[cut - 30:cut]
            assert np.allclose(x, y, rtol=1e-6, atol=1e-6, equal_nan=True), f"{tool}.{k} is not causal"
    Xf, Xp = feature_matrix(full)[cut - 30:cut], feature_matrix(part)[cut - 30:cut]
    bad = [FEATURES[j] for j in range(len(FEATURES)) if not np.allclose(Xf[:, j], Xp[:, j], rtol=1e-5, atol=1e-5)]
    assert not bad, f"non-causal features: {bad}"
