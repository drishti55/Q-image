"""Protocol V4 API: read-only endpoints and the live walkthrough of the frozen FRQI model."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api_main import app
from src.v2.paths import DEFAULT_V4_ROOT
from src.v4.api import CLASSES

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


def test_upload_lab_encodes_reconstructs_and_classifies():
    img = (Path(__file__).resolve().parents[1] / "NEU-DET/validation/images/scratches/scratches_241.jpg")
    if not img.exists():
        pytest.skip("NEU-DET not present")
    r = c.post("/api/v4/upload", files={"file": ("s.jpg", img.read_bytes(), "image/jpeg")}, data={"resolution": "4", "bits": "4"})
    assert r.status_code == 200
    d = r.json()
    frqi, neqr = d["encodings"]
    assert frqi["circuit"]["n_qubits"] == 5 and neqr["circuit"]["n_qubits"] == 8
    sv = {m["mode"]: m for m in frqi["modes"]}
    assert sv["statevector"]["exact"] and sv["statevector"]["mse"] < 1e-12          # FRQI statevector is exact
    assert {m["mode"] for m in neqr["modes"]} == {"statevector", "shots100", "shots1000", "shots10000"}
    assert [k["representation"] for k in d["classifications"]] == ["FRQI", "NEQR"]
    assert all(k["prediction"] in CLASSES for k in d["classifications"])
    assert c.post("/api/v4/upload", files={"file": ("x.txt", b"hello", "text/plain")}).status_code == 422
    assert c.post("/api/v4/upload", files={"file": ("s.jpg", img.read_bytes(), "image/jpeg")}, data={"resolution": "5"}).status_code == 422
    one = c.post("/api/v4/upload", files={"file": ("s.jpg", img.read_bytes(), "image/jpeg")},
                 data={"resolution": "4", "bits": "4", "representations": "NEQR"}).json()
    assert [e["representation"] for e in one["encodings"]] == ["NEQR"] and [k["representation"] for k in one["classifications"]] == ["NEQR"]
    assert c.post("/api/v4/upload", files={"file": ("s.jpg", img.read_bytes(), "image/jpeg")}, data={"representations": "QPIE"}).status_code == 422


def test_cnn_feature_studio_reproduces_training_vectors():
    """Live MobileNetV3 features must equal the cached vectors the V2 hybrids were trained on; test images are refused."""
    L = c.get("/api/v4/cnn/images").json()
    assert set(L["images"]) == set(CLASSES) and L["n_available"] == 1440
    im = L["images"]["inclusion"][0]["image"]
    d = c.get("/api/v4/cnn/features", params={"image": im}).json()
    assert d["class"] == "inclusion" and d["vector_stats"]["dim"] == 576 and len(d["vector"]) == 576
    assert d["cache_check"]["max_abs_diff"] < 1e-4
    assert [s["shape"][0] for s in d["stages"]] == [16, 24, 48, 576]
    assert [p["k"] for p in d["pca"]] == [4, 6, 8]
    assert all(0 <= a <= 3.1416 for p in d["pca"] for a in p["angles_rad"]) or d["split"] == "val"
    assert len(d["scatter"]["pc1"]) == d["pca_fit"]["n_images"] == 1080
    assert {m["type"] for m in d["models"]} == {"hybrid", "classical"}
    test_img = c.get("/api/v4/images").json()["images"][0]["image"]
    assert c.get("/api/v4/cnn/features", params={"image": test_img}).status_code == 404


def test_all_models_match_saved_aggregates():
    d = c.get("/api/v4/all-models").json()
    assert len(d["models"]) == 163 and d["n_test"] == 360
    r4 = c.get("/api/v4/results").json()
    by = {m["id"]: m for m in d["models"]}
    for g, v in r4["groups"].items():
        assert abs(by[g]["test_accuracy"] - v["test_accuracy"]["mean"]) < 1e-9


def test_cnn_studio_returns_every_channel():
    im = c.get("/api/v4/cnn/images").json()["images"]["patches"][0]["image"]
    d = c.get("/api/v4/cnn/features", params={"image": im}).json()
    assert [len(s["channels"]) for s in d["stages"]] == [16, 24, 48, 576]
    acts = [ch["mean_activation"] for ch in d["stages"][3]["channels"]]
    assert acts == sorted(acts, reverse=True)


def test_hybrid_pipeline_uses_saved_predictions_and_real_kernel():
    imgs = c.get("/api/v4/images").json()["images"]
    im = imgs[0]["image"]
    d = c.get("/api/v4/hybrid-pipeline", params={"image": im}).json()
    ix = json.loads((DEFAULT_V4_ROOT / "aggregates" / "per_image_predictions.json").read_text())
    saved = ix["images"][im]["preds"]["E5-mnv3pca8-qkc-product_ry"]
    assert d["saved_predictions"] == [CLASSES[p] for p in saved]
    assert d["y_true"] == CLASSES[ix["images"][im]["y_true"]]
    assert len(d["pca"]["angles_rad"]) == 8 and d["kernel"]["n_train"] == 1080
    sims = [n["similarity"] for n in d["kernel"]["nearest"]]
    assert sims == sorted(sims, reverse=True) and all(0 <= s <= 1 for s in sims)
    train_im = c.get("/api/v4/cnn/images").json()["images"]["crazing"][0]["image"]
    assert c.get("/api/v4/hybrid-pipeline", params={"image": train_im}).status_code == 404


def test_model_families_are_validation_selected_with_confusion_matrices():
    d = c.get("/api/v4/families").json()
    assert [f["key"] for f in d["families"]] == ["qkc", "pqk", "vqc", "hybrid", "rbfsvm"]
    r3 = json.loads((Path(__file__).resolve().parents[1] / "results/qml_v3/aggregates/v3_results.json").read_text())
    G = {g["group"]: g for g in r3["groups"]}
    for f in d["families"]:
        assert f["test_accuracy"]["mean"] == G[f["group"]]["test_accuracy"]["mean"]
        assert sum(map(sum, f["confusion_matrix"])) == 3 * d["n_test"]
    assert d["matched_pairs"] and all(0 < p["rbfsvm_acc"] <= 1 for p in d["matched_pairs"])


def test_dataset_gallery_lists_all_1800_images():
    d = c.get("/api/v4/dataset").json()
    assert d["n"] == 1800 and len(d["images"]) == 1800
    by_class = {k: sum(1 for x in d["images"] if x["class"] == k) for k in CLASSES}
    assert set(by_class.values()) == {300}
    assert sum(1 for x in d["images"] if x["folder"] == "validation") == 360
    roles = {r: sum(1 for x in d["images"] if x["split_seed0"] == r) for r in ("train", "val", "test")}
    assert roles == {"train": 1080, "val": 360, "test": 360}


def test_dataset_image_serves_only_manifest_paths():
    first = c.get("/api/v4/dataset").json()["images"][0]["path"]
    r = c.get("/api/v4/dataset/image", params={"path": first})
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg" and len(r.content) > 1000
    assert c.get("/api/v4/dataset/image", params={"path": "../api_main.py"}).status_code == 404
