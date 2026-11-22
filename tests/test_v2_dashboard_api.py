"""Dashboard API tests. Real-data tests are READ-ONLY against results/qml_v2 (skipped if absent); empty-state tests
use a temporary results root."""
import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from src.v2 import api as v2api  # noqa: E402
from src.v2 import api_models  # noqa: E402

V2 = ROOT / "results" / "qml_v2"
ANALYSIS = V2 / "aggregates" / "analysis.json"
real = pytest.mark.skipif(not ANALYSIS.exists(), reason="no real v2 results")


def client():
    app = FastAPI()
    app.include_router(v2api.router)
    app.include_router(api_models.router)
    return TestClient(app)


@pytest.fixture()
def real_client(monkeypatch):
    monkeypatch.delenv("QIL_RESULTS_V2", raising=False)
    api_models._models_cached.cache_clear()
    api_models._per_class_cached.cache_clear()
    return client()


@real
def test_models_match_analysis_exactly(real_client):
    a = json.loads(ANALYSIS.read_text())
    m = real_client.get("/api/v2/models").json()
    assert m["count"] == len(a["selected"]) == 88
    rows = {r["group"]: r for r in m["models"]}
    assert set(rows) == set(a["selected"])
    for g, s in a["selected"].items():
        r = rows[g]
        for k in ("test_accuracy", "test_f1_macro", "test_precision_macro", "test_recall_macro", "val_f1_macro"):
            assert r[k] == s[k], (g, k)
        assert r["experiment_ids"] == s["experiment_ids"]
        assert len(r["per_seed"]) == 3 and {p["seed"] for p in r["per_seed"]} == {0, 1, 2}
        assert r["category"] in m["categories"]
        assert r["display_name"] and "unavailable" not in r["display_name"]


@real
def test_no_v0_records_in_v2(real_client):
    with open(ROOT / "results" / "qml" / "qml_experiments.csv", newline="") as f:
        v0_ids = {row["experiment_id"] for row in csv.DictReader(f)}
    m = real_client.get("/api/v2/models").json()
    ids = {e for r in m["models"] for e in r["experiment_ids"]}
    assert not ids & v0_ids
    assert all((V2 / "experiments" / e / "status.json").exists() for e in ids)
    exps = real_client.get("/api/v2/experiments").json()["experiments"]
    assert not {e["experiment_id"] for e in exps} & v0_ids


@real
def test_summary_best_models_computed_from_data(real_client):
    a = json.loads(ANALYSIS.read_text())
    s = real_client.get("/api/v2/summary").json()
    best_overall = max(v["test_accuracy"]["mean"] for v in a["selected"].values())
    assert abs(s["best"]["overall"]["test_accuracy"] - best_overall) < 1e-12
    pure_q = [v for g, v in a["selected"].items() if v["family"] in ("quantum_kernel", "variational_quantum")
              and not (v["params"] or {}).get("shots") and "ablation" not in g and v["category"].startswith(("2.", "3."))]
    assert abs(s["best"]["quantum"]["test_accuracy"] - max(v["test_accuracy"]["mean"] for v in pure_q)) < 1e-12
    assert s["counts"]["selected_configurations"] == 88
    assert s["counts"]["experiments"]["completed"] == a["n_completed"]
    assert s["dataset"]["locked_test_images"] == 360 and s["dataset"]["n_classes"] == 6
    assert s["counts"]["quantum_configurations"] + s["counts"]["classical_configurations"] == 88
    assert {f["id"] for f in s["findings"]} >= {"cnn_features", "qkc_competitive", "no_advantage", "vqc", "shots", "recon_vs_cls"}


@real
def test_circuit_artefacts_match_recorded_resources(real_client):
    cs = real_client.get("/api/v2/circuits").json()["circuits"]
    assert len(cs) >= 30
    for c in cs:
        r = real_client.get(f"/api/v2/circuits/{c['experiment_id']}")
        assert r.status_code == 200, c["circuit_key"]
        d = r.json()
        assert d["experiment_id"] == c["experiment_id"] and d["n_qubits"] == c["n_qubits"]
        if not c["circuit_key"].startswith("neqr"):  # NEQR recorded = mean over 5 images (data-dependent)
            assert d["logical_gates_displayed_circuit"] == d["recorded_resources"]["gates_logical"], c["circuit_key"]
    classical = next(r for r in real_client.get("/api/v2/models").json()["models"] if r["category"] == "Classical models")
    assert real_client.get(f"/api/v2/circuits/{classical['experiment_ids'][0]}").status_code == 404


@real
def test_reconstruction_render_from_saved_arrays(real_client):
    j = real_client.get("/api/v2/reconstructions/R-NEQR-8x8-b4/images").json()
    assert len(j["images"]) == 30 and j["images"][29]["class"] == "scratches"
    for kind in ("original", "reconstructed", "diff"):
        r = real_client.get(f"/api/v2/reconstructions/R-NEQR-8x8-b4/render/29/shots1000/{kind}.png")
        assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert real_client.get("/api/v2/reconstructions/R-NEQR-8x8-b4/render/30/shots1000/diff.png").status_code == 404
    assert real_client.get("/api/v2/reconstructions/R-NEQR-8x8-b4/render/0/shots7/diff.png").status_code == 404


@real
def test_v0_endpoints_still_serve_v0(real_client):
    import api_main
    c = TestClient(api_main.app)
    v0 = c.get("/api/models/comparison")
    assert v0.status_code == 200
    groups = {r["group"] for r in real_client.get("/api/v2/models").json()["models"]}
    assert not any(g in json.dumps(v0.json()) for g in groups)


def test_empty_results_root(tmp_path, monkeypatch):
    monkeypatch.setenv("QIL_RESULTS_V2", str(tmp_path / "v2"))
    api_models._models_cached.cache_clear()
    c = client()
    assert c.get("/api/v2/health").json()["analysis_present"] is False
    assert c.get("/api/v2/summary").json() == {"has_data": False}
    assert c.get("/api/v2/models").json()["count"] == 0
    assert c.get("/api/v2/circuits").json()["count"] == 0
    r = c.get("/api/v2/circuits/anything")
    assert r.status_code == 404 and "build_circuit_artifacts" in r.json()["detail"]
    assert c.get("/api/v2/models/x").status_code == 404
    api_models._models_cached.cache_clear()


def test_api_disables_pyarrow_string_inference():
    """Regression (2026-11-15): pyarrow-backed strings segfaulted (pyarrow.compute.take) when V0 endpoints filtered the
    V0 CSV from concurrent request threads; the API must use plain object strings."""
    import pandas as pd

    import api_main  # noqa: F401  (sets the option at import)
    assert pd.get_option("future.infer_string") is False
    df = pd.read_csv(ROOT / "results" / "qml" / "qml_experiments.csv")
    assert df["image_name"].dtype == object


@real
def test_dataset_sample_images_are_train_folder_only(real_client):
    for c in ("crazing", "scratches"):
        r = real_client.get(f"/api/v2/dataset/sample/{c}.png")
        assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert real_client.get("/api/v2/dataset/sample/unknown.png").status_code == 404
    assert real_client.get("/api/v2/dataset/sample/crazing.png?n=99").status_code == 404
