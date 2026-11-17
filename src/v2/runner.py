"""
Central experiment runner for Protocol V2.

Flow for one *selection group* (e.g. "E6 PCA k=8 RBF-SVM"):
  1. Candidates: every hyperparameter configuration × every split seed is fitted on TRAIN and scored
     on the internal VAL split. Each (configuration, seed) is one experiment directory with
     validation metrics, training log, model checkpoint. Failures are recorded, never hidden.
  2. Selection: the configuration with the best MEAN validation macro-F1 across seeds is selected
     (a configuration with any failed seed is ineligible). Written to aggregates/selection/<group>.json.
  3. Final evaluation: only the selected configuration's checkpoints (one per seed) are evaluated on
     the LOCKED test set inside `final_evaluation_stage`. No refitting happens at this stage.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence

import joblib
import numpy as np

from .dataset import CLASSES, final_evaluation_stage
from .metrics import bootstrap_ci, classification_metrics, cross_entropy
from .paths import assert_writable
from .store import ExperimentStore, config_hash, dump_json

FAMILIES = {
    "classical": "Classical",
    "quantum_kernel": "Quantum kernel (simulated)",
    "variational_quantum": "Variational quantum (simulated)",
    "hybrid": "Hybrid classical-quantum (simulated)",
    "quantum_inspired_classical": "Classical computation of quantum-encoding statistics",
}


@dataclass
class FeatureSet:
    X: np.ndarray
    y: np.ndarray
    paths: List[str]


class FeatureProvider:
    """Subclasses produce model inputs for a seed. `test()` must only be called inside the
    final-evaluation stage (the underlying NEUData.test enforces this)."""
    name: str = "base"

    def train_val(self, seed: int):  # -> (FeatureSet, FeatureSet, info dict)
        raise NotImplementedError

    def test(self, seed: int) -> FeatureSet:
        raise NotImplementedError

    def describe(self) -> Dict:
        return {"name": self.name}


@dataclass
class ModelSpec:
    experiment_code: str              # E1..E7 / E1b ...
    group: str                        # selection group id
    model_name: str
    family: str                       # key of FAMILIES
    compute_type: str                 # classical | quantum | hybrid
    feature_extraction: str
    encoding: Optional[str]
    params: Dict[str, Any]
    make: Callable[[Dict[str, Any], int], Any]   # (params, seed) -> estimator
    provider: FeatureProvider
    notes: str = ""
    quantum: Dict[str, Any] = field(default_factory=dict)  # n_qubits, n_layers, optimizer, lr, shots ...

    def config(self, seed: int, split_id: str, manifest_id: str) -> Dict:
        return {
            "experiment_code": self.experiment_code, "group": self.group, "model_name": self.model_name,
            "family": self.family, "family_label": FAMILIES[self.family], "compute_type": self.compute_type,
            "feature_extraction": self.feature_extraction, "encoding": self.encoding,
            "params": self.params, "quantum": self.quantum, "provider": self.provider.describe(),
            "seed": seed, "split_id": split_id, "dataset_manifest_id": manifest_id,
            "protocol": "V2 locked-test (validation folder) + group-blocked train/val", "notes": self.notes,
        }

    def config_key(self) -> str:
        # Computed once and frozen: provider descriptions must not change the key mid-run.
        if getattr(self, "_key", None) is None:
            h = config_hash({"params": self.params, "provider": self.provider.describe(), "q": self.quantum})
            self._key = f"{self.group}__{h}"
        return self._key

    def experiment_id(self, seed: int) -> str:
        return f"{self.config_key()}__s{seed}"


def _summary(spec: ModelSpec, seed: int, n: Dict[str, int], val: Optional[Dict], test: Optional[Dict],
             circuit: Optional[Dict], timing: Dict, split_id: str, manifest_id: str) -> Dict:
    q = spec.quantum or {}

    def pick(m):
        return None if m is None else {k: m[k] for k in
                                       ("accuracy", "precision_macro", "recall_macro", "f1_macro", "f1_weighted")}
    return {
        "record_type": "classification",
        "experiment_code": spec.experiment_code, "group": spec.group, "model_name": spec.model_name,
        "family": spec.family, "compute_type": spec.compute_type,
        "feature_extraction": spec.feature_extraction, "encoding": spec.encoding,
        "n_qubits": q.get("n_qubits"), "circuit_depth": (circuit or {}).get("depth_logical"),
        "circuit_depth_compiled": (circuit or {}).get("depth_compiled"),
        "n_layers": q.get("n_layers"), "optimizer": q.get("optimizer"), "learning_rate": q.get("learning_rate"),
        "shots": q.get("shots"), "seed": seed, "n_train": n.get("train"), "n_val": n.get("val"),
        "n_test": n.get("test"), "dataset_manifest_id": manifest_id, "split_id": split_id,
        "params": spec.params, "val": pick(val), "test": pick(test), **timing,
    }


class Runner:
    def __init__(self, store: Optional[ExperimentStore] = None, seeds: Sequence[int] = (0, 1, 2),
                 split_ids: Optional[Dict[int, str]] = None, manifest_id: str = "", log=print,
                 select_metric: str = "f1_macro"):
        self.store = store or ExperimentStore()
        self.seeds = list(seeds)
        self.split_ids = split_ids or {s: f"seed{s}" for s in self.seeds}
        self.manifest_id = manifest_id
        self.log = log
        self.select_metric = select_metric
        self._models: Dict[str, Any] = {}

    # ── candidates ──
    def run_candidate(self, spec: ModelSpec, seed: int, force: bool = False) -> Dict:
        eid = spec.experiment_id(seed)
        st = self.store.status(eid)
        if st and st.get("status") == "completed" and not force:
            return st["summary"]
        split_id = self.split_ids[seed]
        self.store.start(eid, spec.config(seed, split_id, self.manifest_id), {
            "dataset_manifest_id": self.manifest_id, "split_id": split_id, "seed": seed,
            "stage": "candidate (train -> internal validation)",
        })
        try:
            tr, va, finfo = spec.provider.train_val(seed)
            est = spec.make(spec.params, seed)
            t0 = time.perf_counter()
            fit_out = est.fit(tr.X, tr.y, va.X, va.y) or {}
            t_fit = time.perf_counter() - t0
            t0 = time.perf_counter()
            yv = est.predict(va.X)
            t_pred = time.perf_counter() - t0
            proba = est.predict_proba(va.X) if hasattr(est, "predict_proba") else None
            val = classification_metrics(va.y, yv)
            if proba is not None:
                val["cross_entropy"] = cross_entropy(proba, va.y)
            self.store.write(eid, "validation_metrics.json", val)
            self.store.write_predictions(eid, "val", va.paths, va.y, yv, proba, CLASSES)
            self.store.write(eid, "confusion_matrix.json", {"labels": CLASSES, "val": val["confusion_matrix"]})
            if fit_out.get("training_log"):
                self.store.write(eid, "training_log.json", fit_out["training_log"])
            circuit = est.circuit_stats() if hasattr(est, "circuit_stats") else None
            if circuit:
                self.store.write(eid, "circuit_stats.json", circuit)
            diag = est.diagnostics() if hasattr(est, "diagnostics") else None
            diag = {**(diag or {}), "features": finfo}
            self.store.write(eid, "diagnostics.json", diag)
            mdir = self.store.dir(eid) / "model"
            mdir.mkdir(exist_ok=True)
            assert_writable(mdir / "estimator.joblib")
            joblib.dump(est, mdir / "estimator.joblib")
            self._models[eid] = est
            timing = {"train_time_s": t_fit, "val_inference_time_s": t_pred,
                      "inference_ms_per_image": 1000 * t_pred / max(len(va.y), 1)}
            summ = _summary(spec, seed, {"train": len(tr.y), "val": len(va.y)}, val, None, circuit, timing,
                            split_id, self.manifest_id)
            summ["selected"] = False
            self.store.finish(eid, summ)
            self.log(f"  [ok] {eid}  val acc={val['accuracy']:.3f} F1={val['f1_macro']:.3f}  fit {t_fit:.1f}s")
            return summ
        except Exception as e:  # recorded, never hidden
            summ = _summary(spec, seed, {}, None, None, None, {}, split_id, self.manifest_id)
            self.store.finish(eid, summ, status="failed", error=e)
            self.log(f"  [FAILED] {eid}: {type(e).__name__}: {e}")
            return {**summ, "failed": True}

    # ── selection ──
    def select(self, group: str, specs: List[ModelSpec], results: Dict[str, List[Dict]]) -> Dict:
        rows = []
        for spec in specs:
            res = results[spec.config_key()]
            ok = all(r.get("val") for r in res)
            vals = [r["val"][self.select_metric] for r in res if r.get("val")]
            rows.append({"config_key": spec.config_key(), "params": spec.params, "quantum": spec.quantum,
                         "eligible": ok, "val_mean": float(np.mean(vals)) if ok else None,
                         "val_std": float(np.std(vals, ddof=1)) if ok and len(vals) > 1 else None,
                         "experiment_ids": [spec.experiment_id(s) for s in self.seeds]})
        elig = [r for r in rows if r["eligible"]]
        best = max(elig, key=lambda r: r["val_mean"]) if elig else None
        sel = {"group": group, "selected_at": datetime.now().isoformat(),
               "criterion": f"max mean validation {self.select_metric} over seeds {self.seeds} "
                            "(ties: first in grid order); locked test NOT consulted",
               "n_candidates": len(rows), "n_eligible": len(elig), "selected": best, "candidates": rows}
        dump_json(self.store.root / "aggregates" / "selection" / f"{group}.json", sel)
        return sel

    # ── final evaluation ──
    def final_test(self, spec: ModelSpec) -> List[Dict]:
        out = []
        with final_evaluation_stage(f"final test evaluation of selected config for group {spec.group}"):
            for seed in self.seeds:
                eid = spec.experiment_id(seed)
                est = self._models.get(eid)
                if est is None:
                    est = joblib.load(self.store.dir(eid) / "model" / "estimator.joblib")
                te = spec.provider.test(seed)
                t0 = time.perf_counter()
                yt = est.predict(te.X)
                t_pred = time.perf_counter() - t0
                proba = est.predict_proba(te.X) if hasattr(est, "predict_proba") else None
                m = classification_metrics(te.y, yt)
                m["bootstrap_ci"] = bootstrap_ci(te.y, yt, seed=seed)
                if proba is not None:
                    m["cross_entropy"] = cross_entropy(proba, te.y)
                self.store.write(eid, "test_metrics.json", m)
                self.store.write_predictions(eid, "test", te.paths, te.y, yt, proba, CLASSES)
                cm = self.store.read(eid, "confusion_matrix.json") or {"labels": CLASSES}
                cm["test"] = m["confusion_matrix"]
                self.store.write(eid, "confusion_matrix.json", cm)
                pick = {k: m[k] for k in ("accuracy", "precision_macro", "recall_macro", "f1_macro", "f1_weighted")}
                self.store.update_summary(eid, test=pick, n_test=len(te.y), selected=True,
                                          test_ci=m["bootstrap_ci"],
                                          test_inference_ms_per_image=1000 * t_pred / max(len(te.y), 1))
                self.log(f"  [TEST] {eid}  acc={m['accuracy']:.3f} F1={m['f1_macro']:.3f}")
                out.append(m)
        return out

    def run_group(self, group: str, specs: List[ModelSpec], final: bool = True, force: bool = False) -> Dict:
        self.log(f"== group {group}: {len(specs)} configs x {len(self.seeds)} seeds")
        results: Dict[str, List[Dict]] = {}
        for spec in specs:
            key = spec.config_key()
            results[key] = [self.run_candidate(spec, s, force=force) for s in self.seeds]
        sel = self.select(group, specs, results)
        if final and sel["selected"]:
            best = next(s for s in specs if s.config_key() == sel["selected"]["config_key"])
            done = [(self.store.dir(best.experiment_id(s)) / "test_metrics.json").exists() for s in self.seeds]
            if all(done):
                # Resume safety: the locked test set is evaluated at most once per selected configuration.
                self.log(f"  locked test already evaluated for {best.config_key()} — not re-evaluated")
            else:
                self.final_test(best)
        elif not sel["selected"]:
            self.log(f"  no eligible configuration in group {group}; no test evaluation")
        return sel
