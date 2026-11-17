"""Protocol V3 API + playground data tests. READ-ONLY against results/qml_v3 (real-data tests skip if absent);
missing-data tests use a temporary root."""
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from src.v3 import api as v3api  # noqa: E402

V3 = ROOT / "results" / "qml_v3"
PG = V3 / "playground" / "playground_3x3.json"
built = pytest.mark.skipif(not PG.exists(), reason="V3 playground not built")


def client():
    app = FastAPI()
    app.include_router(v3api.router)
    return TestClient(app)


def test_missing_data_gives_404(tmp_path, monkeypatch):
    monkeypatch.setenv("QIL_RESULTS_V3", str(tmp_path / "v3"))
    c = client()
    assert c.get("/api/v3/playground").status_code == 404
    r = c.get("/api/v3/results")
    assert r.status_code == 404 and "analyze_v3" in r.json()["detail"]
    h = c.get("/api/v3/health").json()
    assert h["results_root_exists"] is False and h["playground_present"] is False


@built
def test_v3_playground_has_no_classifier_outputs_and_real_traces(monkeypatch):
    monkeypatch.delenv("QIL_RESULTS_V3", raising=False)
    d = client().get("/api/v3/playground").json()
    txt = json.dumps(d)
    for k in ('"prediction"', '"probabilities"', '"decision_ovr"', '"logits"', '"probabilities_after"'):
        assert k not in txt
    assert d["illustrative"] is True and d["grid"] == [[70, 180, 0], [19, 20, 0], [0, 0, 0]]
    assert d["flattened_raw_9"] == [70, 180, 0, 19, 20, 0, 0, 0, 0]
    tr = d["pixel_traces"]
    assert [t["value"] for t in tr] == [70, 180, 19, 20]
    for t in tr:
        assert t["normalized"] == pytest.approx(t["value"] / 255, abs=1e-6)
        assert t["cnn_input"] == pytest.approx((t["value"] / 255 - 0.5) / 0.25, abs=1e-6)
        base = d["preprocessing"]["pca"]["8"]["standard"]
        assert [b - w for b, w in zip(base, t["pca8_standard_without"])] == pytest.approx(t["pca8_standard_delta"], abs=1e-5)
    # brighter pixels move the PCA features more
    l2 = [math.sqrt(sum(v * v for v in t["pca8_standard_delta"])) for t in tr]
    assert l2[1] == max(l2)
    # FRQI angles for all nine cells (padding = 0)
    pos = {p["position"]: p for p in d["frqi"]["positions"]}
    for r in range(3):
        for c in range(3):
            v = d["grid"][r][c]
            assert pos[4 * r + c]["theta"] == pytest.approx(math.pi / 2 * v / 255, abs=1e-5)


@built
def test_v3_results_served_if_present(monkeypatch):
    monkeypatch.delenv("QIL_RESULTS_V3", raising=False)
    r = client().get("/api/v3/results")
    if not (V3 / "aggregates" / "v3_results.json").exists():
        assert r.status_code == 404
        return
    d = r.json()
    assert d["protocol"] == "V3" and d["counts"]["groups_tested"] > 0
    for c in d["comparisons"]:
        assert 0 <= c["p_holm"] <= 1 and c["p_holm"] >= c["p_permutation"] - 1e-12
        assert c["ci95"][0] <= c["diff"] <= c["ci95"][1]
