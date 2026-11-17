"""Phase 2 tests: result schema, unique IDs, selection on validation only, locked final stage,
failure records, resume and reload. Everything is written to tmp_path."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.v2 import dataset as ds  # noqa: E402
from src.v2.paths import DEFAULT_V2_ROOT  # noqa: E402
from src.v2.runner import FeatureProvider, FeatureSet, ModelSpec, Runner  # noqa: E402
from src.v2.store import ExperimentStore  # noqa: E402


class SynthProvider(FeatureProvider):
    name = "synthetic"

    def __init__(self):
        rng = np.random.default_rng(0)
        self.c = rng.normal(size=(6, 5)) * 3
        self.test_calls = 0

    def _make(self, n, seed):
        rng = np.random.default_rng(seed)
        y = np.arange(n) % 6
        return FeatureSet(self.c[y] + rng.normal(size=(n, 5)), y, [f"img{i}.jpg" for i in range(n)])

    def train_val(self, seed):
        return self._make(120, seed), self._make(60, seed + 100), {"synthetic": True}

    def test(self, seed):
        if not ds._final_eval_active():
            raise ds.TestSetLockedError("locked")
        self.test_calls += 1
        return self._make(60, 999)


class LR:
    def __init__(self, params, seed):
        self.m = LogisticRegression(C=params["C"], max_iter=500)

    def fit(self, X, y, Xv, yv):
        self.m.fit(X, y)
        return {"training_log": {"note": "single fit"}}

    def predict(self, X):
        return self.m.predict(X)

    def predict_proba(self, X):
        return self.m.predict_proba(X)


class Broken:
    def __init__(self, params, seed):
        pass

    def fit(self, *a):
        raise RuntimeError("deliberate failure")


def _spec(prov, C, make=LR):
    return ModelSpec("E0", "unit-group", "LR", "classical", "classical", "synthetic", None, {"C": C}, make, prov)


@pytest.fixture()
def runner(tmp_path, monkeypatch):
    monkeypatch.setenv("QIL_RESULTS_V2", str(tmp_path / "v2"))
    store = ExperimentStore(tmp_path / "v2")
    return Runner(store=store, seeds=(0, 1, 2), manifest_id="neu-test", log=lambda *a: None)


def test_group_end_to_end(runner, tmp_path):
    prov = SynthProvider()
    specs = [_spec(prov, C) for C in (0.001, 1.0)] + [_spec(prov, 5.0, make=Broken)]
    sel = runner.run_group("unit-group", specs)
    # unique ids
    ids = runner.store.list_ids()
    assert len(ids) == 9 and len(set(ids)) == 9
    # failure preserved with traceback, not silently dropped
    failed = [i for i in ids if runner.store.status(i)["status"] == "failed"]
    assert len(failed) == 3
    assert "deliberate failure" in runner.store.status(failed[0])["error"]["traceback"]
    assert not (runner.store.dir(failed[0]) / "validation_metrics.json").exists()
    # selection ignores failed config and never touched the test set beforehand
    assert sel["n_eligible"] == 2 and sel["selected"]["params"]["C"] == 1.0
    assert prov.test_calls == 3
    # test metrics only for the selected config
    with_test = [i for i in ids if (runner.store.dir(i) / "test_metrics.json").exists()]
    assert sorted(with_test) == sorted(sel["selected"]["experiment_ids"])
    e = with_test[0]
    for f in ("config.json", "metadata.json", "status.json", "validation_metrics.json", "predictions.csv",
              "confusion_matrix.json", "model/estimator.joblib"):
        assert (runner.store.dir(e) / f).exists(), f
    st = runner.store.status(e)
    s = st["summary"]
    assert s["selected"] and s["val"] and s["test"] and s["seed"] in (0, 1, 2) and s["n_test"] == 60
    meta = runner.store.read(e, "metadata.json")
    assert meta["dataset_manifest_id"] == "neu-test" and "environment" in meta and meta["duration_s"] >= 0
    preds = (runner.store.dir(e) / "predictions.csv").read_text().splitlines()
    assert sum(1 for r in preds if r.startswith("val,")) == 60 and sum(1 for r in preds if r.startswith("test,")) == 60
    assert (tmp_path / "v2" / "aggregates" / "selection" / "unit-group.json").exists()
    assert not any(DEFAULT_V2_ROOT.joinpath("experiments", i).exists() for i in ids)


def test_resume_skips_completed(runner):
    prov = SynthProvider()
    spec = _spec(prov, 1.0)
    runner.run_candidate(spec, 0)
    t1 = runner.store.status(spec.experiment_id(0))["updated_at"]
    runner.run_candidate(spec, 0)
    assert runner.store.status(spec.experiment_id(0))["updated_at"] == t1


def test_reload_from_checkpoint(runner, tmp_path):
    prov = SynthProvider()
    spec = _spec(prov, 1.0)
    runner.run_group("unit-group", [spec], final=False)
    fresh = Runner(store=ExperimentStore(tmp_path / "v2"), seeds=(0, 1, 2), manifest_id="neu-test",
                   log=lambda *a: None)
    out = fresh.final_test(spec)  # loads joblib checkpoints, no refit
    assert len(out) == 3 and all(0 <= m["accuracy"] <= 1 for m in out)


def test_test_set_locked_outside_final_stage():
    with pytest.raises(ds.TestSetLockedError):
        SynthProvider().test(0)


def test_json_has_no_nan(tmp_path):
    store = ExperimentStore(tmp_path / "v2")
    store.write("x", "a.json", {"v": float("nan"), "w": [1.0, float("inf")]})
    assert json.loads((store.dir("x") / "a.json").read_text()) == {"v": None, "w": [1.0, None]}


def test_resumed_group_does_not_reevaluate_test(runner):
    """Regression (2026-11-14): resuming a finished group must not read the locked test set again."""
    prov = SynthProvider()
    specs = [_spec(prov, 1.0)]
    runner.run_group("unit-group", specs)
    assert prov.test_calls == 3
    runner.run_group("unit-group", specs)  # resume: everything already done
    assert prov.test_calls == 3
