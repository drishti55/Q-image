"""Protocol V4 API: read-only endpoints and the live walkthrough of the frozen FRQI model."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api_main import app
from src.v2.paths import DEFAULT_V4_ROOT

pytestmark = pytest.mark.skipif(not (DEFAULT_V4_ROOT / "aggregates" / "v4_results.json").exists(), reason="V4 results not built")
c = TestClient(app)


def test_results_and_index():
    r = c.get("/api/v4/results").json()
    assert r["counts"]["failed_runs"] == 0 and len(r["comparisons"]) == 8
    imgs = c.get("/api/v4/images").json()
    assert len(imgs["images"]) == 360 and imgs["n_models"] == 163


def test_live_prediction_equals_saved_for_every_test_image():
    """The animated page recomputes the frozen model's decision; it must reproduce all 360 saved predictions."""
    imgs = [x["image"] for x in c.get("/api/v4/images").json()["images"]]
    bad = [im for im in imgs if not c.get("/api/v4/pipeline", params={"image": im}).json()["matches_saved_prediction"]]
    assert not bad, bad[:3]


def test_pipeline_rejects_non_test_images():
    assert c.get("/api/v4/pipeline", params={"image": "train/images/crazing/crazing_1.jpg"}).status_code == 404


def test_image_models_are_copied_from_saved_predictions():
    ix = json.loads((DEFAULT_V4_ROOT / "aggregates" / "per_image_predictions.json").read_text())
    img = next(iter(ix["images"]))
    m = c.get("/api/v4/image-models", params={"image": img}).json()
    assert len(m["models"]) == 163
    assert all(row["preds"] == ix["images"][img]["preds"][row["id"]] for row in m["models"])


def test_reconstruction_endpoint_validates_record():
    assert c.get("/api/v4/reconstruction/image", params={"record": "../x", "i": 0}).status_code == 404


def test_versions_numbers_match_saved_aggregates():
    d = c.get("/api/v4/versions").json()
    v = {x["id"]: x for x in d["versions"]}
    assert list(v) == ["V0", "V2", "V3", "V4"] and not v["V0"]["comparable"] and v["V4"]["latest"]
    r4 = json.loads((DEFAULT_V4_ROOT / "aggregates" / "v4_results.json").read_text())
    assert v["V4"]["frqi"] == r4["groups"][r4["headlines"]["frqi"]]["test_accuracy"]
    assert v["V4"]["neqr"] == r4["groups"][r4["headlines"]["neqr"]]["test_accuracy"]
    assert v["V2"]["frqi"] == r4["references"]["E1b-frqi8-qkc-scaled"]["test_accuracy"]
    assert v["V3"]["frqi"] == r4["references"]["V3-frqi8"]["test_accuracy"]
    assert len(v["V4"]["comparisons"]) == len(r4["comparisons"])
