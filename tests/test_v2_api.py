"""Phase 9: API integration tests against a temporary v2 results tree (never the real one)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from src.v2 import api as v2api  # noqa: E402
from src.v2.runner import Runner  # noqa: E402
from src.v2.store import ExperimentStore  # noqa: E402
from test_v2_runner import LR, Broken, SynthProvider, _spec  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("QIL_RESULTS_V2", str(tmp_path / "v2"))
    v2api._index_cache.update(mtime=None, rows=[])
    app = FastAPI()
    app.include_router(v2api.router)
    return TestClient(app), tmp_path / "v2"


def test_empty_results_return_no_data(client):
    c, _ = client
    assert c.get("/api/v2/overview").json()["has_data"] is False
    assert c.get("/api/v2/comparison").json()["rows"] == []
    assert c.get("/api/v2/dataset").json() == {"has_data": False}
    assert c.get("/api/v2/reconstructions").json()["records"] == []
    assert c.get("/api/v2/experiments/nope").status_code == 404


def test_endpoints_read_saved_records(client):
    c, root = client
    r = Runner(store=ExperimentStore(root), seeds=(0, 1, 2), manifest_id="neu-test", log=lambda *a: None)
    prov = SynthProvider()
    r.run_group("unit-group", [_spec(prov, 1.0), _spec(prov, 5.0, make=Broken)])
    ov = c.get("/api/v2/overview").json()
    assert ov["experiments"] == {"total": 6, "completed": 3, "failed": 3, "running": 0, "selected_with_test": 3}
    failed = c.get("/api/v2/experiments", params={"status": "failed"}).json()
    assert failed["count"] == 3
    det = c.get(f"/api/v2/experiments/{failed['experiments'][0]['experiment_id']}").json()
    assert det["status"]["error"]["message"] == "deliberate failure" and det["test_metrics"] is None
    comp = c.get("/api/v2/comparison").json()["rows"]
    assert len(comp) == 1 and comp[0]["seeds"] == [0, 1, 2] and comp[0]["test_accuracy"]["n"] == 3
    saved = [ExperimentStore(root).read(i, "test_metrics.json")["accuracy"] for i in comp[0]["experiment_ids"]]
    assert abs(comp[0]["test_accuracy"]["mean"] - sum(saved) / 3) < 1e-12
    preds = c.get(f"/api/v2/experiments/{comp[0]['experiment_ids'][0]}/predictions", params={"split": "test"}).json()
    assert preds["count"] == 60
    assert c.get("/api/v2/experiments", params={"seed": 1, "selected": True}).json()["count"] == 1
    assert c.get("/api/v2/selections/unit-group").json()["n_eligible"] == 1


def test_reconstruction_image_path_traversal_blocked(client):
    c, root = client
    (root / "reconstructions" / "R-X" / "images").mkdir(parents=True)
    (root / "reconstructions" / "R-X" / "status.json").write_text('{"status": "completed"}')
    assert c.get("/api/v2/reconstructions/R-X/image/..%2F..%2Fstatus.json").status_code in (400, 404)
    assert c.get("/api/v2/reconstructions/R-X/image/missing.png").status_code == 404


def test_historical_is_separate_and_flags_fixtures(client):
    c, _ = client
    h = c.get("/api/v2/historical").json()
    assert h["label"] == "Historical Results — Protocol V0"
    assert h["counts"]["unit_test_fixture"] == 16  # 8 x test001 + 8 x fail001 (verified by grep)
    assert all(r["record_kind"] == "paired_run" for r in h["paired_runs"])


def test_legacy_v0_launch_endpoints_refuse():
    import api_main
    c = TestClient(api_main.app)
    for method, url in (("post", "/api/qml/run"), ("post", "/api/qml/suite/run"),
                        ("post", "/api/quantum/batch/run"), ("delete", "/api/qml/experiment/test001")):
        r = getattr(c, method)(url, json={}) if method == "post" else c.delete(url)
        assert r.status_code == 409, url
