"""Algorithm Playground data tests. READ-ONLY against results/qml_v2/playground (skipped if not built);
the missing-data test uses a temporary results root. Values are checked against independent formulas."""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from src.v2 import api_models  # noqa: E402

PG = ROOT / "results" / "qml_v2" / "playground" / "playground_3x3.json"
built = pytest.mark.skipif(not PG.exists(), reason="playground not built")
GIVEN = [(0, 0, 70), (0, 1, 180), (1, 0, 19), (1, 1, 20)]


def client():
    app = FastAPI()
    app.include_router(api_models.router)
    return TestClient(app)


@pytest.fixture(scope="module")
def d():
    return json.loads(PG.read_text())


@built
def test_grid_and_illustrative_flag(d):
    assert d["illustrative"] is True and "not" in d["disclaimer"].lower()
    assert d["grid"] == [[70, 180, 0], [19, 20, 0], [0, 0, 0]]
    assert d["frqi"]["padded_4x4"] == [[70, 180, 0, 0], [19, 20, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    assert d["preprocessing"]["flattened_9"] == pytest.approx([v / 255 for row in d["grid"] for v in row], abs=1e-5)


@built
def test_frqi_angles_and_amplitudes(d):
    pos = {p["position"]: p for p in d["frqi"]["positions"]}
    for r, c, v in GIVEN:
        p = pos[4 * r + c]
        theta = (math.pi / 2) * v / 255
        assert p["pixel"] == v
        assert p["theta"] == pytest.approx(theta, abs=1e-5)
        assert p["theta_deg"] == pytest.approx(math.degrees(theta), abs=1e-3)
        assert p["amp_colour0"] == pytest.approx(math.cos(theta) / 4, abs=1e-5)
        assert p["amp_colour1"] == pytest.approx(math.sin(theta) / 4, abs=1e-5)
    assert d["frqi"]["statevector_formula_max_abs_error"] < 1e-10
    assert len(d["frqi"]["blocks"]) == 4  # zero pixels add no gates
    assert np.allclose(d["frqi"]["reconstructed_exact_255"], d["frqi"]["padded_4x4"], atol=1e-6)


@built
@pytest.mark.parametrize("bits,expected", [
    (2, ["01", "10", "00", "00"]),
    (4, ["0100", "1011", "0001", "0001"]),
    (8, ["01000110", "10110100", "00010011", "00010100"]),
])
def test_neqr_binary_per_precision(d, bits, expected):
    p = d["neqr"]["precisions"][str(bits)]
    assert p["levels"] == 2 ** bits and p["n_qubits"] == 4 + bits
    got = [x["binary_msb_first"] for x in p["pixels"]]
    assert got == expected
    for x in p["pixels"]:
        q = int(round(x["pixel"] / 255 * (2 ** bits - 1)))
        assert x["quantized"] == q and int(x["binary_msb_first"], 2) == q
    assert p["decode_matches_quantized"] is True
    if bits == 8:
        assert p["mse_given_pixels_255sq"] == pytest.approx(0, abs=1e-9)


@built
def test_qkc_and_vqc_consistency(d):
    for fm, m in d["qkc"]["maps"].items():
        assert m["kernel_heatmap"][0][0] == pytest.approx(1.0, abs=1e-6)  # self-overlap
        assert sum(a * a for a in m["statevector_abs"]) == pytest.approx(1.0, abs=1e-6)
        assert m["x_scaled"] == pytest.approx([m["params"]["bandwidth"] * a for a in d["qkc"]["features"]], abs=1e-5)
    v = d["vqc"]
    assert len(v["theta_trained"]) == len(v["theta_initial"]) == v["n_qubits"] * v["layers"] * 2
    assert sum(v["trained"]["probabilities"]) == pytest.approx(1.0, abs=1e-5)
    ps = v["parameter_shift"]
    assert ps["dE_dtheta"] == pytest.approx([(a - b) / 2 for a, b in zip(ps["E_plus"], ps["E_minus"])], abs=1e-5)
    lr = d["logreg"]
    assert lr["probabilities"] == pytest.approx(lr["softmax_of_scores"], abs=1e-6)
    s = d["svm"]
    assert s["example"]["K"] == pytest.approx(math.exp(-s["gamma"] * s["example"]["dist2"]), abs=1e-5)


@built
def test_endpoint_serves_file(monkeypatch):
    monkeypatch.delenv("QIL_RESULTS_V2", raising=False)
    r = client().get("/api/v2/playground")
    assert r.status_code == 200 and r.json()["illustrative"] is True


def test_endpoint_404_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("QIL_RESULTS_V2", str(tmp_path / "v2"))
    r = client().get("/api/v2/playground")
    assert r.status_code == 404 and "build_playground" in r.json()["detail"]
