"""Phase 1 tests: manifest, validation, blocked splits, locked test, train-only preprocessing.
All tests use a synthetic fixture dataset in tmp_path; nothing is written to the project."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.v2 import dataset as ds  # noqa: E402
from src.v2.features import PCAFeaturizer  # noqa: E402
from src.v2.metrics import bootstrap_ci, classification_metrics  # noqa: E402

N_TRAIN, N_TEST = 60, 10  # per class; 3 blocks of 20 per class in the train folder


@pytest.fixture()
def fake_neu(tmp_path, monkeypatch):
    root = tmp_path / "NEU"
    rng = np.random.default_rng(0)
    for folder, start, n in (("train", 1, N_TRAIN), ("validation", N_TRAIN + 1, N_TEST)):
        for ci, c in enumerate(ds.CLASSES):
            d = root / folder / "images" / c
            d.mkdir(parents=True)
            a = root / folder / "annotations"
            a.mkdir(parents=True, exist_ok=True)
            for i in range(start, start + n):
                arr = (rng.random((16, 16)) * 60 + ci * 30).astype(np.uint8)
                Image.fromarray(arr).convert("RGB").save(d / f"{c}_{i}.jpg", quality=95)
                (a / f"{c}_{i}.xml").write_text(
                    f"<annotation><object><name>{c}</name></object></annotation>")
    monkeypatch.setenv("QIL_RESULTS_V2", str(tmp_path / "v2"))
    monkeypatch.setenv("QIL_DATASET_PATH", str(root))
    return root


def test_manifest_and_validation(fake_neu):
    m = ds.build_manifest(fake_neu)
    assert len(m["records"]) == 6 * (N_TRAIN + N_TEST)
    chk = ds.validate_manifest(m)
    assert chk["ok"], chk
    assert chk["counts"]["train"]["scratches"] == N_TRAIN
    assert all(len(r["sha256"]) == 64 for r in m["records"])
    assert {r["group_id"] for r in m["records"] if r["class"] == "crazing" and r["folder"] == "train"} == {
        "train:crazing:b00", "train:crazing:b01", "train:crazing:b02"}


def test_validation_flags_cross_group_duplicates(fake_neu):
    src = fake_neu / "train/images/crazing/crazing_1.jpg"
    dst = fake_neu / "train/images/crazing/crazing_55.jpg"  # different block
    dst.write_bytes(src.read_bytes())
    chk = ds.validate_manifest(ds.build_manifest(fake_neu))
    assert chk["duplicates_crossing_groups"] and not chk["ok"]


def test_blocked_split_has_no_overlap(fake_neu):
    m = ds.build_manifest(fake_neu)
    for seed in (0, 1, 2):
        sp = ds.make_split(m, seed, val_blocks_per_class=1)
        v = ds.verify_split(sp, m)
        assert v["ok"], v
        assert sp["counts"] == {"train": 6 * 40, "val": 6 * 20, "test": 6 * N_TEST}
    # deterministic per seed, different across seeds
    assert ds.make_split(m, 0, 1)["split_id"] == ds.make_split(m, 0, 1)["split_id"]
    assert len({ds.make_split(m, s, 1)["split_id"] for s in range(6)}) > 1


def test_locked_test_requires_final_stage(fake_neu, tmp_path):
    m = ds.build_manifest(fake_neu)
    sp = ds.make_split(m, 0, val_blocks_per_class=1)
    data = ds.NEUData(0, manifest=m, split=sp, cache_dir=tmp_path / "cache")
    assert data.train(4).X.shape == (240, 4, 4)
    with pytest.raises(ds.TestSetLockedError):
        data.test(4)
    with ds.final_evaluation_stage("unit test", log_dir=tmp_path / "logs"):
        t = data.test(4)
    assert t.X.shape == (6 * N_TEST, 4, 4)
    log = (tmp_path / "logs" / "test_access.jsonl").read_text().strip().splitlines()
    assert json.loads(log[-1])["reason"] == "unit test"
    with pytest.raises(ds.TestSetLockedError):  # lock re-engages after the stage
        data.test(4)


def test_preprocessing_range(fake_neu):
    p = next((fake_neu / "train/images/crazing").glob("*.jpg"))
    x = ds.preprocess_image(p, 8)
    assert x.shape == (8, 8) and 0.0 <= x.min() <= x.max() <= 1.0


def test_pca_fit_uses_train_only():
    rng = np.random.default_rng(0)
    Xtr = rng.random((50, 8, 8))
    Xother = rng.random((30, 8, 8)) + 5.0  # very different distribution
    f = PCAFeaturizer(k=4).fit(Xtr)
    mean_before = f._pix.mean_.copy()
    _ = f.transform(Xother, "standard"), f.transform(Xother, "angle")
    np.testing.assert_allclose(f._pix.mean_, mean_before)
    np.testing.assert_allclose(f._pix.mean_, Xtr.reshape(50, -1).mean(0))
    A = f.transform(Xtr, "angle")
    assert A.min() >= -1e-12 and A.max() <= np.pi + 1e-12
    assert f.info()["fitted_on_n_train"] == 50


def test_metrics_use_all_six_labels():
    y_true = [0, 0, 1, 1]          # classes 2..5 absent
    y_pred = [0, 1, 1, 1]
    m = classification_metrics(y_true, y_pred)
    assert len(m["per_class"]) == 6 and np.array(m["confusion_matrix"]).shape == (6, 6)
    assert m["per_class"]["inclusion"]["recall"] == 1.0
    assert m["per_class"]["patches"]["support"] == 0
    ci = bootstrap_ci([0, 1, 2, 3, 4, 5] * 10, [0, 1, 2, 3, 4, 0] * 10, n_boot=200)
    assert ci["accuracy"][0] <= 50 / 60 <= ci["accuracy"][1]
