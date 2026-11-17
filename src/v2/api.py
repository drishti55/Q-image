"""
Read-only FastAPI router for Protocol V2 results (results/qml_v2) and a separately labelled,
read-only view of historical Protocol V0 results. Every value returned is read from a saved file;
missing values are returned as null — never substituted.
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from .paths import HISTORICAL_RESULTS_ROOT, v2_root

router = APIRouter(prefix="/api/v2", tags=["v2"])


def _root() -> Path:
    return v2_root(create=False)


def _read(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


_index_cache: Dict = {"mtime": None, "rows": []}


def _index() -> List[Dict]:
    exp = _root() / "experiments"
    if not exp.exists():
        return []
    mt = max((d.stat().st_mtime for d in exp.iterdir()), default=0)
    stamp = (mt, len(os.listdir(exp)))
    if _index_cache["mtime"] == stamp:
        return _index_cache["rows"]
    rows = []
    for d in sorted(exp.iterdir()):
        st = _read(d / "status.json")
        if not st:
            continue
        s = st.get("summary") or {}
        cfg = _read(d / "config.json") or {}
        rows.append({
            "experiment_id": d.name, "status": st.get("status"), "updated_at": st.get("updated_at"),
            "error": (st.get("error") or {}).get("message"),
            "experiment_code": s.get("experiment_code", cfg.get("experiment_code")),
            "group": s.get("group", cfg.get("group")), "model_name": s.get("model_name", cfg.get("model_name")),
            "family": s.get("family", cfg.get("family")), "compute_type": s.get("compute_type", cfg.get("compute_type")),
            "feature_extraction": s.get("feature_extraction"), "encoding": s.get("encoding"),
            "n_qubits": s.get("n_qubits"), "n_layers": s.get("n_layers"), "optimizer": s.get("optimizer"),
            "shots": s.get("shots"), "seed": s.get("seed", cfg.get("seed")), "params": s.get("params", cfg.get("params")),
            "circuit_depth": s.get("circuit_depth"), "circuit_depth_compiled": s.get("circuit_depth_compiled"),
            "n_train": s.get("n_train"), "n_val": s.get("n_val"), "n_test": s.get("n_test"),
            "val": s.get("val"), "test": s.get("test"), "test_ci": s.get("test_ci"), "selected": bool(s.get("selected")),
            "train_time_s": s.get("train_time_s"), "inference_ms_per_image": s.get("inference_ms_per_image"),
            "test_inference_ms_per_image": s.get("test_inference_ms_per_image"),
            "has_training_log": (d / "training_log.json").exists(), "has_circuit": (d / "circuit_stats.json").exists(),
        })
    _index_cache.update(mtime=stamp, rows=rows)
    return rows


@router.get("/overview")
def overview():
    rows = _index()
    recon = _root() / "reconstructions"
    rec = [_read(d / "status.json") for d in recon.iterdir()] if recon.exists() else []
    by = lambda key: sorted({r[key] for r in rows if r.get(key) is not None}, key=str)  # noqa: E731
    return {
        "has_data": bool(rows),
        "experiments": {"total": len(rows), "completed": sum(r["status"] == "completed" for r in rows),
                        "failed": sum(r["status"] == "failed" for r in rows),
                        "running": sum(r["status"] == "running" for r in rows),
                        "selected_with_test": sum(bool(r["test"]) for r in rows)},
        "families": by("family"), "experiment_codes": by("experiment_code"), "seeds": by("seed"),
        "reconstruction_records": {"total": len([r for r in rec if r]),
                                   "completed": sum(1 for r in rec if r and r.get("status") == "completed"),
                                   "failed": sum(1 for r in rec if r and r.get("status") == "failed")},
        "execution": "All quantum results are classical simulations (no quantum hardware).",
    }


@router.get("/dataset")
def dataset():
    m = _root() / "manifests"
    cur = _read(m / "dataset_manifest_current.json")
    if not cur:
        return {"has_data": False}
    man = _read(m / cur["path"]) or {}
    integ = _read(m / "split_integrity.json") or {}
    recs = man.get("records", [])
    dims: Dict[str, int] = {}
    for r in recs:
        k = f"{r.get('width')}x{r.get('height')} {r.get('mode')}"
        dims[k] = dims.get(k, 0) + 1
    splits = {}
    for seed, s in (integ.get("splits") or {}).items():
        splits[seed] = {"split_id": s["split_id"], "counts": s["counts"], "overlap_checks": s["overlap_checks"],
                        "adjacency_blocked": s["adjacency_blocked"],
                        "adjacency_random_split_for_comparison": s["adjacency_random_split_for_comparison"]}
    chk = integ.get("dataset_checks", {})
    return {"has_data": True, "manifest_id": man.get("manifest_id"), "created_at": man.get("created_at"),
            "protocol": man.get("protocol"), "classes": man.get("classes"), "total_images": len(recs),
            "counts": chk.get("counts"), "dimensions": dims, "warnings": chk.get("warnings"),
            "exact_duplicates": chk.get("exact_duplicates"), "integrity_ok": integ.get("ok"), "splits": splits}


@router.get("/experiments")
def experiments(family: Optional[str] = None, code: Optional[str] = None, group: Optional[str] = None,
                n_qubits: Optional[int] = None, n_layers: Optional[int] = None, optimizer: Optional[str] = None,
                shots: Optional[int] = None, seed: Optional[int] = None, status: Optional[str] = None,
                selected: Optional[bool] = None, feature: Optional[str] = Query(None, description="substring"),
                limit: int = 5000):
    rows = _index()
    def keep(r):  # noqa: E306
        return ((family is None or r["family"] == family) and (code is None or r["experiment_code"] == code)
                and (group is None or r["group"] == group) and (n_qubits is None or r["n_qubits"] == n_qubits)
                and (n_layers is None or r["n_layers"] == n_layers) and (optimizer is None or r["optimizer"] == optimizer)
                and (shots is None or (r["shots"] or 0) == shots) and (seed is None or r["seed"] == seed)
                and (status is None or r["status"] == status) and (selected is None or r["selected"] == selected)
                and (feature is None or feature.lower() in (r["feature_extraction"] or "").lower()))
    out = [r for r in rows if keep(r)]
    return {"count": len(out), "experiments": out[:limit]}


@router.get("/experiments/{experiment_id}")
def experiment(experiment_id: str):
    d = _root() / "experiments" / experiment_id
    if not (d / "status.json").exists():
        raise HTTPException(404, "experiment not found")
    files = {n: _read(d / f"{n}.json") for n in ("config", "metadata", "status", "validation_metrics", "test_metrics",
                                                  "training_log", "circuit_stats", "diagnostics", "confusion_matrix")}
    return {"experiment_id": experiment_id, **files}


@router.get("/experiments/{experiment_id}/predictions")
def predictions(experiment_id: str, split: Optional[str] = None):
    p = _root() / "experiments" / experiment_id / "predictions.csv"
    if not p.exists():
        raise HTTPException(404, "no predictions saved")
    with open(p, newline="") as f:
        rows = [r for r in csv.DictReader(f) if split is None or r["split"] == split]
    return {"count": len(rows), "rows": rows}


@router.get("/selections")
def selections():
    d = _root() / "aggregates" / "selection"
    out = []
    for p in sorted(d.glob("*.json")) if d.exists() else []:
        s = _read(p) or {}
        out.append({"group": s.get("group"), "criterion": s.get("criterion"), "n_candidates": s.get("n_candidates"),
                    "n_eligible": s.get("n_eligible"), "selected": s.get("selected")})
    return {"count": len(out), "selections": out}


@router.get("/selections/{group}")
def selection(group: str):
    s = _read(_root() / "aggregates" / "selection" / f"{group}.json")
    if not s:
        raise HTTPException(404, "selection not found")
    return s


def _ms(v):
    v = [x for x in v if x is not None]
    if not v:
        return {"mean": None, "std": None, "n": 0}
    return {"mean": float(np.mean(v)), "std": float(np.std(v, ddof=1)) if len(v) > 1 else 0.0, "n": len(v)}


@router.get("/comparison")
def comparison():
    """Selected configuration of every group: mean ± std over seeds of validation and locked-test metrics."""
    groups: Dict[str, List[Dict]] = {}
    for r in _index():
        if r["selected"] and r["test"]:
            groups.setdefault(r["group"], []).append(r)
    out = []
    for g, rs in sorted(groups.items()):
        r0 = rs[0]
        row = {k: r0[k] for k in ("group", "experiment_code", "model_name", "family", "compute_type",
                                  "feature_extraction", "encoding", "n_qubits", "n_layers", "optimizer", "shots",
                                  "params", "circuit_depth", "circuit_depth_compiled")}
        row["experiment_ids"] = [r["experiment_id"] for r in rs]
        row["seeds"] = sorted(r["seed"] for r in rs)
        row["n_test"] = r0["n_test"]
        for split in ("val", "test"):
            for m in ("accuracy", "precision_macro", "recall_macro", "f1_macro", "f1_weighted"):
                row[f"{split}_{m}"] = _ms([(r[split] or {}).get(m) for r in rs])
        row["train_time_s"] = _ms([r["train_time_s"] for r in rs])
        row["test_inference_ms_per_image"] = _ms([r["test_inference_ms_per_image"] for r in rs])
        out.append(row)
    return {"count": len(out), "rows": out,
            "note": "Classification only. Reconstruction metrics are in /api/v2/reconstructions."}


@router.get("/analysis")
def analysis():
    p = _root() / "aggregates" / "analysis.json"
    a = _read(p)
    if not a:
        return {"has_data": False}
    return {"has_data": True, **a}


@router.get("/reconstructions")
def reconstructions():
    d = _root() / "reconstructions"
    out = []
    for r in sorted(d.iterdir()) if d.exists() else []:
        st = _read(r / "status.json")
        if not st:
            continue
        m = _read(r / "metrics.json") or {}
        out.append({"record_id": r.name, "status": st.get("status"), "error": (st.get("error") or {}).get("message"),
                    "config": _read(r / "config.json"), "summary": m.get("summary"), "timing": m.get("timing"),
                    "circuit_stats": _read(r / "circuit_stats.json")})
    return {"count": len(out), "records": out}


@router.get("/reconstructions/{record_id}")
def reconstruction(record_id: str):
    r = _root() / "reconstructions" / record_id
    if not (r / "status.json").exists():
        raise HTTPException(404, "record not found")
    imgs = sorted(p.name for p in (r / "images").glob("*.png")) if (r / "images").exists() else []
    return {"record_id": record_id, "status": _read(r / "status.json"), "config": _read(r / "config.json"),
            "metrics": _read(r / "metrics.json"), "circuit_stats": _read(r / "circuit_stats.json"), "images": imgs}


@router.get("/reconstructions/{record_id}/image/{name}")
def reconstruction_image(record_id: str, name: str):
    if "/" in name or ".." in name or not name.endswith(".png"):
        raise HTTPException(400, "bad image name")
    p = _root() / "reconstructions" / record_id / "images" / name
    if not p.exists():
        raise HTTPException(404, "image not found")
    return FileResponse(p, media_type="image/png")


@router.get("/historical")
def historical():
    """Protocol V0 records, read-only, with provenance flags. Never merged with v2 comparisons."""
    p = HISTORICAL_RESULTS_ROOT / "qml" / "qml_experiments.csv"
    rows = []
    if p.exists():
        with open(p, newline="") as f:
            for r in csv.DictReader(f):
                eid = r.get("experiment_id", "")
                kind = ("unit_test_fixture" if eid in ("test001", "fail001")
                        else "per_image_record" if eid.startswith(("frqi_", "neqr_")) else "paired_run")
                rows.append({**r, "record_kind": kind})
    paired = [r for r in rows if r["record_kind"] == "paired_run"]
    cls = HISTORICAL_RESULTS_ROOT / "models" / "model_comparison.csv"
    classical = []
    if cls.exists():
        with open(cls, newline="") as f:
            classical = list(csv.DictReader(f))
    return {
        "label": "Historical Results — Protocol V0",
        "warnings": [
            "Protocol V0 paired runs used max_per_class=10 (about 42 train / 12-18 test images), alphabetical file order.",
            "Per-image records hold 0/1 correctness, include training images, and are not aggregate metrics.",
            "Rows test001/fail001 are unit-test fixtures written by an old test, not experiments.",
            "The V0 'Variational Quantum Classifier' had no parameterised quantum circuit; 'HQCC' features were "
            "classical pixel statistics.",
            "V0 classical 'test' = random 30% of the train folder (index-adjacent images can leak); "
            "not comparable with the V2 locked test.",
        ],
        "counts": {k: sum(r["record_kind"] == k for r in rows)
                   for k in ("paired_run", "per_image_record", "unit_test_fixture")},
        "paired_runs": paired,
        "classical_v0": classical,
        "source_files": [str(p.relative_to(HISTORICAL_RESULTS_ROOT.parent)), str(cls.relative_to(HISTORICAL_RESULTS_ROOT.parent))],
    }
