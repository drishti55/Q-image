"""
Protocol V2 dashboard endpoints (read-only; sources: results/qml_v2 only).

  GET /api/v2/health                     version + availability of the V2 results (lets the UI detect a stale backend)
  GET /api/v2/summary                    overview counts, best models, family comparison, data-derived findings
  GET /api/v2/models                     all selected configurations (88) with names, category, metrics, per-seed values
  GET /api/v2/models/{group}             one configuration: per-seed val/test metrics, per-class, confusion matrices, CI
  GET /api/v2/per-class                  per-class test F1 (seed mean) for every selected configuration
  GET /api/v2/circuits                   circuit configurations actually executed by selected quantum models
  GET /api/v2/circuits/{experiment_id}   that experiment's circuit rebuilt from its saved checkpoint + saved resources

Every number is read from saved records (aggregates/analysis.json, experiments/*/status.json, test_metrics.json,
circuit_stats.json, manifests). Nothing is estimated; missing values are null.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from fastapi import APIRouter, HTTPException

from .paths import v2_root

router = APIRouter(prefix="/api/v2", tags=["v2-dashboard"])
API_VERSION = "2.2"


def _root() -> Path:
    return v2_root(create=False)


def _read(p: Path):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


# ─── naming / categorisation (derived from saved config fields) ─────────────
CATEGORIES = [
    "Classical models",
    "Quantum kernel models",
    "FRQI / NEQR encoding kernels",
    "Variational quantum classifiers",
    "Hybrid CNN + quantum models",
]


def category_of(code: str, family: str) -> str:
    if family in ("classical", "quantum_inspired_classical"):
        return "Classical models"
    if code == "E3":
        return "Quantum kernel models"
    if code in ("E1", "E1b", "E2"):
        return "FRQI / NEQR encoding kernels"
    if code == "E4":
        return "Variational quantum classifiers"
    return "Hybrid CNN + quantum models"


def feature_source(code: str, group: str, fe: str) -> str:
    if code == "E7" and "smallcnn" in group:
        return "End-to-end CNN (128×128 pixels)"
    if "MobileNet" in (fe or "") or "mnv3" in group:
        m = re.search(r"PCA\((\d+)\)", fe or "")
        return f"MobileNetV3 features → PCA {m.group(1)}" if m else "MobileNetV3 features (576-d)"
    m = re.search(r"PCA\((\d+)\)", fe or "")
    if m:
        return f"Pixels 64×64 → PCA {m.group(1)}"
    m = re.search(r"(\d+)x(\d+)", fe or "")
    if m:
        return f"Raw pixels {m.group(1)}×{m.group(2)}"
    return fe or "unavailable"


def display_name(group: str, code: str, family: str, params: Dict, n_qubits, fe: str) -> str:
    p = params or {}
    src = feature_source(code, group, fe)
    shots = p.get("shots") or 0
    sh = f", {shots} shots" if shots else ""
    fmap = {"product_ry": "product-RY", "zz_linear": "ZZ-linear", "zz_full": "ZZ-full"}
    if code == "E7":
        if "smallcnn" in group:
            return "Small CNN (trained from scratch)"
        return f"Frozen MobileNetV3 + {'RBF-SVM' if 'rbfsvm' in group else 'Logistic Regression'}"
    if code == "E6":
        clf = "RBF-SVM" if "rbfsvm" in group else "Logistic Regression"
        extra = " (QKC-identical angle features)" if "angle" in group else ""
        return f"{src} + {clf}{extra}"
    if code == "E3":
        return f"QKC {fmap.get(p.get('feature_map'), p.get('feature_map'))} · {n_qubits} qubits{sh}"
    if code == "E4":
        lbl = f"VQC · {n_qubits} qubits · {p.get('optimizer', '?')} · {p.get('layers')} layer(s)"
        if p.get("reupload"):
            lbl += " · re-upload"
        if p.get("train_quantum") is False or "ablation" in group:
            lbl = f"VQC ablation (frozen random circuit) · {n_qubits} qubits"
        return lbl
    if code in ("E1", "E1b", "E2"):
        m = re.search(r"(\d+)x(\d+)", fe or "")
        res = f"{m.group(1)}×{m.group(2)}" if m else "?"
        if family == "quantum_inspired_classical":
            if "legacy-softmax" in group:
                return f"Legacy V0 'VQC' = fixed-feature softmax ({p.get('representation')}, {res}) — classical"
            return f"Legacy V0 'HQCC' = {p.get('representation')} statistics + LogReg ({res}) — classical"
        if p.get("representation") == "NEQR":
            return f"NEQR kernel · {res} · {p.get('bits')}-bit{sh}"
        scaled = f" · angle ×{p.get('angle_scale'):g}" if p.get("angle_scale", 1.0) != 1.0 else ""
        return f"FRQI kernel · {res}{scaled}{sh}"
    if code == "E5":
        if family == "classical":
            return f"{src} + {'RBF-SVM' if 'rbfsvm' in group else 'Logistic Regression'}"
        if "vqc" in group:
            return f"{src} + VQC ({p.get('layers')} layer(s))"
        return f"{src} + QKC {fmap.get(p.get('feature_map'), p.get('feature_map'))}"
    return group


def encoding_of(code: str, group: str, params: Dict) -> str:
    p = params or {}
    if code in ("E3",) or (code == "E5" and "qkc" in group):
        return {"product_ry": "Product-RY feature map", "zz_linear": "ZZ feature map (linear)",
                "zz_full": "ZZ feature map (full)"}.get(p.get("feature_map"), "unavailable")
    if code == "E4" or (code == "E5" and "vqc" in group):
        return "RY angle encoding + variational layers"
    if code in ("E1", "E1b", "E2") and "qkc" in group:
        return f"{p.get('representation')}" + (f" {p.get('bits')}-bit" if p.get("representation") == "NEQR" else "")
    return "none (classical)"


def execution_of(category: str, shots) -> str:
    if category == "Classical models":
        return "classical"
    return f"finite shots ({shots}), simulated" if shots else "exact statevector, simulated"


# ─── cached loaders ──────────────────────────────────────────────────────────
def _stamp(p: Path):
    try:
        return p.stat().st_mtime
    except FileNotFoundError:
        return None


@lru_cache(maxsize=4)
def _models_cached(stamp) -> List[Dict]:
    a = _read(_root() / "aggregates" / "analysis.json") or {}
    exp = _root() / "experiments"
    rows = []
    for g, s in sorted((a.get("selected") or {}).items()):
        st0 = (_read(exp / s["experiment_ids"][0] / "status.json") or {}).get("summary", {})
        code = st0.get("experiment_code") or g.split("-")[0]
        fam = s["family"]
        params = s.get("params") or {}
        cat = category_of(code, fam)
        shots = (params or {}).get("shots") or 0
        per_seed = []
        for eid in s["experiment_ids"]:
            ss = (_read(exp / eid / "status.json") or {}).get("summary", {})
            per_seed.append({"seed": ss.get("seed"), "experiment_id": eid, "val": ss.get("val"), "test": ss.get("test"),
                             "test_ci": ss.get("test_ci"), "train_time_s": ss.get("train_time_s"),
                             "test_inference_ms_per_image": ss.get("test_inference_ms_per_image")})
        cs = _read(exp / s["experiment_ids"][0] / "circuit_stats.json")
        circuit = None if not cs else {k: cs.get(k) for k in (
            "n_qubits", "gates_logical", "depth_logical", "gates_compiled", "depth_compiled", "cx_compiled",
            "two_qubit_gates_compiled", "single_qubit_gates_compiled")}
        if circuit and cs.get("n_sample_images"):
            circuit["note"] = cs.get("note")
        rows.append({
            "group": g, "display_name": display_name(g, code, fam, params, s.get("n_qubits"), s.get("feature_extraction")),
            "model_name": s.get("model_name"), "experiment_code": code, "category": cat, "family": fam,
            "is_quantum": cat != "Classical models", "is_legacy_relabelled": fam == "quantum_inspired_classical",
            "is_ablation": "ablation" in g,
            "feature_source": feature_source(code, g, s.get("feature_extraction")),
            "feature_extraction": s.get("feature_extraction"), "encoding": encoding_of(code, g, params),
            "n_qubits": s.get("n_qubits"), "n_layers": st0.get("n_layers"), "optimizer": st0.get("optimizer"),
            "shots": shots, "execution": execution_of(cat, shots), "params": params,
            "experiment_ids": s["experiment_ids"], "n_seeds": s.get("n_seeds"), "n_test": s.get("n_test"),
            "n_candidates": s.get("n_candidates"),
            "val_f1_macro": s.get("val_f1_macro"), "test_accuracy": s.get("test_accuracy"),
            "test_precision_macro": s.get("test_precision_macro"), "test_recall_macro": s.get("test_recall_macro"),
            "test_f1_macro": s.get("test_f1_macro"), "test_f1_weighted": s.get("test_f1_weighted"),
            "train_time_s": s.get("train_time_s"), "test_inference_ms_per_image": s.get("test_inference_ms_per_image"),
            "circuit": circuit, "per_seed": per_seed,
        })
    return rows


def models() -> List[Dict]:
    return _models_cached(_stamp(_root() / "aggregates" / "analysis.json"))


def _acc(r):
    return (r.get("test_accuracy") or {}).get("mean") or -1


def _best(rows, pred):
    c = [r for r in rows if pred(r)]
    if not c:
        return None
    top = max(_acc(r) for r in c)
    ties = [r for r in c if abs(_acc(r) - top) < 1e-9]
    pick = lambda r: {k: r[k] for k in ("group", "display_name", "category", "test_accuracy", "test_f1_macro",  # noqa: E731
                                         "experiment_ids", "execution", "n_qubits")}
    return {"models": [pick(r) for r in ties], "test_accuracy": top}


# ─── endpoints ───────────────────────────────────────────────────────────────
@router.get("/health")
def health():
    root = _root()
    a = root / "aggregates" / "analysis.json"
    return {"api": "qimagelab-v2", "api_version": API_VERSION, "results_root_exists": root.exists(),
            "analysis_present": a.exists(), "n_selected": len(models()) if a.exists() else 0}


@router.get("/models")
def models_endpoint():
    rows = models()
    return {"count": len(rows), "categories": CATEGORIES, "models": rows,
            "source": "results/qml_v2/aggregates/analysis.json + experiments/*/status.json"}


@router.get("/models/{group}")
def model_detail(group: str):
    row = next((r for r in models() if r["group"] == group), None)
    if row is None:
        raise HTTPException(404, "configuration not found")
    exp = _root() / "experiments"
    seeds = []
    for ps in row["per_seed"]:
        eid = ps["experiment_id"]
        seeds.append({**ps, "test_metrics": _read(exp / eid / "test_metrics.json"),
                      "validation_metrics": _read(exp / eid / "validation_metrics.json"),
                      "confusion_matrix": _read(exp / eid / "confusion_matrix.json"),
                      "has_training_log": (exp / eid / "training_log.json").exists()})
    sel = _read(_root() / "aggregates" / "selection" / f"{group}.json") or {}
    return {**row, "seeds": seeds, "selection": {k: sel.get(k) for k in ("criterion", "n_candidates", "n_eligible")},
            "candidates": sel.get("candidates")}


@lru_cache(maxsize=4)
def _per_class_cached(stamp) -> List[Dict]:
    exp = _root() / "experiments"
    out = []
    for r in models():
        acc: Dict[str, List[float]] = {}
        for eid in r["experiment_ids"]:
            tm = _read(exp / eid / "test_metrics.json") or {}
            for c, m in (tm.get("per_class") or {}).items():
                acc.setdefault(c, []).append(m.get("f1"))
        out.append({"group": r["group"], "display_name": r["display_name"], "category": r["category"],
                    "feature_source": r["feature_source"], "execution": r["execution"],
                    "per_class_f1": {c: float(np.mean(v)) for c, v in acc.items()}})
    return out


@router.get("/per-class")
def per_class():
    rows = _per_class_cached(_stamp(_root() / "aggregates" / "analysis.json"))
    return {"count": len(rows), "rows": rows, "metric": "test F1 per class, mean over seeds"}


def _paired(a: Dict, label_prefix: str):
    return [p for p in a.get("paired_tests", []) if p["comparison"].startswith(label_prefix)]


@router.get("/summary")
def summary():
    root = _root()
    a = _read(root / "aggregates" / "analysis.json")
    if not a:
        return {"has_data": False}
    rows = models()
    man_cur = _read(root / "manifests" / "dataset_manifest_current.json") or {}
    man = _read(root / "manifests" / man_cur.get("path", "-")) or {}
    recs = man.get("records", [])
    recon_dir = root / "reconstructions"
    recon = [_read(d / "status.json") for d in recon_dir.iterdir()] if recon_dir.exists() else []
    exp_status = {"completed": a.get("n_completed"), "failed": a.get("n_failed"), "total": a.get("n_experiments")}
    exact = lambda r: not r["shots"]  # noqa: E731
    pure_q = lambda r: r["category"] in ("Quantum kernel models", "FRQI / NEQR encoding kernels",  # noqa: E731
                                         "Variational quantum classifiers") and exact(r) and not r["is_ablation"]
    best = {
        "overall": _best(rows, lambda r: True),
        "quantum": _best(rows, pure_q),
        "hybrid": _best(rows, lambda r: r["category"] == "Hybrid CNN + quantum models" and exact(r)),
        "classical_pixel": _best(rows, lambda r: r["category"] == "Classical models" and r["feature_source"].startswith(("Pixels", "Raw"))
                                 and not r["is_legacy_relabelled"]),
    }
    families = [
        ("Classical ML on pixels", lambda r: r["category"] == "Classical models" and r["feature_source"].startswith("Pixels")),
        ("CNN models (classical)", lambda r: r["category"] == "Classical models" and ("CNN" in r["feature_source"] or "MobileNet" in r["feature_source"])),
        ("Quantum kernel classifiers", lambda r: r["category"] == "Quantum kernel models" and exact(r)),
        ("Variational quantum classifiers", lambda r: r["category"] == "Variational quantum classifiers" and not r["is_ablation"]),
        ("Hybrid quantum-classical", lambda r: r["category"] == "Hybrid CNN + quantum models"),
        ("FRQI / NEQR kernels", lambda r: r["category"] == "FRQI / NEQR encoding kernels" and exact(r)),
    ]
    fam_rows = []
    for name, pred in families:
        c = [r for r in rows if pred(r)]
        if not c:
            fam_rows.append({"family": name, "n_models": 0, "best": None})
            continue
        b = max(c, key=_acc)
        fam_rows.append({"family": name, "n_models": len(c), "best_group": b["group"], "best_name": b["display_name"],
                         "best_test_accuracy": b["test_accuracy"], "best_test_f1_macro": b["test_f1_macro"],
                         "median_test_accuracy": float(np.median([_acc(r) for r in c]))})

    # findings — every number computed from saved records
    S = {r["group"]: r for r in rows}
    f = []
    cnn, pix = best["overall"], best["classical_pixel"]
    if cnn and pix:
        f.append({"id": "cnn_features", "title": "CNN feature extraction significantly improves classification",
                  "text": f"Best model {cnn['models'][0]['display_name']} reaches {cnn['test_accuracy']:.1%} test accuracy vs "
                          f"{pix['test_accuracy']:.1%} for the best pixel-based classical model.",
                  "groups": [m["group"] for m in cnn["models"]] + [m["group"] for m in pix["models"]]})
    pt = {p["comparison"]: p for p in a.get("paired_tests", [])}
    qk = [pt.get(f"QKC {m} vs RBF-SVM, identical PCA({k}) angle features") for k in (4, 6, 8) for m in ("product_ry", "zz_linear", "zz_full")]
    qk = [p for p in qk if p]
    if qk:
        n = sum(len(p["per_seed"]) for p in qk)
        q_better = sum(1 for p in qk for s in p["per_seed"] if s["p_value_exact"] < 0.05 and s["acc_a"] > s["acc_b"])
        c_better = sum(1 for p in qk for s in p["per_seed"] if s["p_value_exact"] < 0.05 and s["acc_a"] < s["acc_b"])
        z8 = S.get("E3-pca8-qkc-zz_full"), S.get("E6-pca8-rbfsvm-angle")
        txt = (f"On identical PCA features, {n - q_better - c_better} of {n} seed-level comparisons show no significant "
               f"difference between quantum kernels and an RBF-SVM; {q_better} favour the quantum kernel, {c_better} the RBF-SVM.")
        if all(z8):
            txt += (f" Best case: 8-qubit ZZ-full {z8[0]['test_accuracy']['mean']:.1%} vs RBF-SVM "
                    f"{z8[1]['test_accuracy']['mean']:.1%}.")
        f.append({"id": "qkc_competitive", "title": "Quantum kernels are competitive on low-dimensional features", "text": txt,
                  "groups": ["E3-pca8-qkc-zz_full", "E6-pca8-rbfsvm-angle"]})
        hy = [p for c, p in pt.items() if c.startswith("CNN+QKC")]
        hq = sum(1 for p in hy for s in p["per_seed"] if s["p_value_exact"] < 0.05 and s["acc_a"] > s["acc_b"])
        hn = sum(len(p["per_seed"]) for p in hy)
        f.append({"id": "no_advantage", "title": "No consistent quantum advantage was established",
                  "text": f"Quantum kernels won {q_better} of {n} pixel-feature comparisons and {hq} of {hn} CNN-feature "
                          "comparisons (uncorrected, p<0.05). All quantum results are noiseless classical simulations.",
                  "groups": []})
    vq = [pt.get(f"VQC vs RBF-SVM, PCA({k})") for k in (4, 6, 8)]
    ab = [pt.get(f"Trained VQC vs frozen-circuit ablation (PCA {k})") for k in (4, 6, 8)]
    if all(vq) and all(ab):
        vbest = max((S[f"E4-pca{k}-vqc"] for k in (4, 6, 8) if f"E4-pca{k}-vqc" in S), key=_acc)
        f.append({"id": "vqc", "title": "Genuine VQCs learn but underperform kernel methods",
                  "text": f"Trained VQCs beat their frozen-circuit ablation in "
                          f"{sum(s['p_value_exact'] < 0.05 and s['acc_a'] > s['acc_b'] for p in ab for s in p['per_seed'])}/9 "
                          f"seed comparisons but lose to the RBF-SVM in "
                          f"{sum(s['p_value_exact'] < 0.05 and s['acc_a'] < s['acc_b'] for p in vq for s in p['per_seed'])}/9; "
                          f"best VQC {vbest['test_accuracy']['mean']:.1%}.",
                  "groups": [vbest["group"]]})
    sh = a.get("shot_sensitivity") or {}
    drops = []
    for base, d in sh.items():
        if "0" in d:
            for s_, v in d.items():
                if s_ != "0":
                    drops.append((d["0"]["test_accuracy"]["mean"] - v["test_accuracy"]["mean"],
                                  S[base]["display_name"] if base in S else base, int(s_), base))
    if drops:
        mx = max(drops)
        f.append({"id": "shots", "title": "Finite measurement shots affect kernel performance",
                  "text": f"Largest drop: {mx[1]} loses {mx[0]:.1%} test accuracy at {mx[2]} shots per kernel entry "
                          "relative to exact statevector simulation.", "groups": [mx[3]]})
    rc = [r for r in a.get("reconstruction", []) if r.get("summary")]
    if rc:
        fr8 = next((r for r in rc if r["record_id"] == "R-FRQI-8x8"), None)
        txt = "Statevector decoding reconstructs every encoded image exactly (encoder/decoder consistency)"
        if fr8:
            txt += (f"; with 1,000 shots FRQI 8×8 has MSE {fr8['summary']['shots1000']['vs_preprocessed']['mse']['mean']:.1e}"
                    f" and SSIM {fr8['summary']['shots1000']['vs_preprocessed']['ssim']['mean']:.2f}")
        txt += ". NEQR 8-bit — perfect reconstruction — is the weakest NEQR kernel for classification."
        f.append({"id": "recon_vs_cls", "title": "Reconstruction quality and classification performance are different objectives",
                  "text": txt, "groups": ["E2-neqr8-b8-qkc", "E2-neqr8-b4-qkc"]})

    return {
        "has_data": True, "api_version": API_VERSION,
        "dataset": {"name": "NEU-DET", "manifest_id": man.get("manifest_id"), "total_images": len(recs),
                    "classes": man.get("classes"), "n_classes": len(man.get("classes") or []),
                    "locked_test_images": sum(1 for r in recs if r.get("role") == "locked_test"),
                    "trainval_images": sum(1 for r in recs if r.get("role") == "trainval")},
        "protocol": {"locked_test": "NEU-DET validation folder, read only after model selection",
                     "selection": "mean internal-validation macro-F1 over seeds 0,1,2 (group-blocked splits)",
                     "seeds": [0, 1, 2],
                     "execution": "All quantum models are classical (CPU) simulations — no quantum hardware."},
        "counts": {"selected_configurations": len(rows), "experiments": exp_status,
                   "reconstruction_runs": sum(1 for r in recon if r and r.get("status") == "completed"),
                   "reconstruction_failed": sum(1 for r in recon if r and r.get("status") == "failed"),
                   "quantum_configurations": sum(1 for r in rows if r["is_quantum"]),
                   "classical_configurations": sum(1 for r in rows if not r["is_quantum"]),
                   "by_category": {c: sum(1 for r in rows if r["category"] == c) for c in CATEGORIES}},
        "best": best, "families": fam_rows, "findings": f,
    }


# ─── circuits ────────────────────────────────────────────────────────────────
def _circuit_kind(r: Dict) -> Optional[str]:
    if r["category"] == "Classical models":
        return None
    p = r["params"] or {}
    if "feature_map" in p:
        return f"qkc|{p['feature_map']}|reps{p['reps']}|q{r['n_qubits']}"
    if "layers" in p:
        return f"vqc|L{p['layers']}|reupload{bool(p.get('reupload'))}|q{r['n_qubits']}"
    if "representation" in p:
        m = re.search(r"(\d+)×(\d+)", r["display_name"])
        res = m.group(1) if m else "?"
        return f"{p['representation'].lower()}|{res}x{res}" + (f"|b{p['bits']}" if p["representation"] == "NEQR" else "")
    return None


@router.get("/circuits")
def circuits():
    seen: Dict[str, Dict] = {}
    for r in models():
        k = _circuit_kind(r)
        if not k or not r.get("circuit"):
            continue
        e = seen.setdefault(k, {"circuit_key": k, "experiment_id": r["experiment_ids"][0], "n_qubits": r["n_qubits"],
                                "encoding": r["encoding"], "resources": r["circuit"], "used_by": []})
        e["used_by"].append({"group": r["group"], "display_name": r["display_name"], "execution": r["execution"]})
    rows = sorted(seen.values(), key=lambda e: (e["circuit_key"].split("|")[0], e["n_qubits"] or 0, e["circuit_key"]))
    return {"count": len(rows), "circuits": rows}


def build_circuit_detail(experiment_id: str) -> Dict:
    import joblib
    from qiskit.circuit.library import zz_feature_map  # noqa: F401  (import check only)

    d = _root() / "experiments" / experiment_id
    cfg, st = _read(d / "config.json"), _read(d / "status.json")
    if not cfg or not (d / "model" / "estimator.joblib").exists():
        raise HTTPException(404, "experiment or checkpoint not found")
    est = joblib.load(d / "model" / "estimator.joblib")
    params = cfg.get("params") or {}
    seed = cfg.get("seed")
    split = _read(_root() / "manifests" / "splits" / f"{cfg.get('split_id')}.json") or {}
    first_train = (split.get("train") or [None])[0]
    meas, ent, kind = None, [], None
    if hasattr(est, "Xtr") and "feature_map" in params:  # QKC
        from .qkernel import _pairs, encode
        x = np.asarray(est.Xtr[0], float) * params["bandwidth"]
        qc = encode(x[None, :], params["feature_map"], params["reps"], record=True).qc
        ent = [list(p) for p in _pairs(qc.num_qubits, params["feature_map"])]
        kind = "Quantum kernel feature map U(x)"
        meas = ("Kernel circuit U(x) then U(y)†, all qubits measured once; K(x,y) = P(0…0). "
                + ("Exact statevector overlap used." if not params.get("shots") else
                   f"{params['shots']} shots per kernel entry (Binomial sampling, validated against Aer)."))
        inp = f"first training image of split {cfg.get('split_id')} ({first_train}), PCA angles × bandwidth {params['bandwidth']}"
    elif hasattr(est, "circ") and est.circ is not None:  # VQC
        from .providers import PixelPCAProvider, VectorProvider  # noqa: F401
        from .vqc import entangler_pairs
        a0 = None
        if "mnv3" not in cfg.get("group", ""):
            from .providers import _fitted_pca, neu
            k = est.circ.n
            a0 = _fitted_pca(seed, k, 64).transform(neu(seed).train(64).X[:1], "angle")
            inp = f"first training image of split {cfg.get('split_id')} ({first_train}) as PCA angles"
        else:
            from .cnn import FrozenMobileNetV3Source
            tr, _, _ = VectorProvider(FrozenMobileNetV3Source(), est.circ.n, "angle").train_val(seed)
            a0 = tr.X[:1]
            inp = (f"first training image of split {cfg.get('split_id')} ({first_train}) as MobileNetV3 → "
                   f"PCA {est.circ.n} angles (train-fitted, recomputed from cached features)")
        qc = est.circ.run(a0, est.theta, record=True).qc
        ent = [list(p) for p in entangler_pairs(est.circ.n, est.circ.ent)] * est.circ.L
        kind = "Variational quantum classifier (encoding + trained layers)"
        meas = f"Exact expectation values of {[f'{k_}{q}' for k_, q in est.circ.readout]} → 6 class logits"
    elif hasattr(est, "Xtr") and "representation" in params:  # FRQI / NEQR
        from src.frqi.encoder import FRQIEncoder
        from src.neqr.encoder import NEQREncoder

        from .frqi_neqr import neqr_quantize
        img = np.asarray(est.Xtr[0], float)
        if params["representation"] == "FRQI":
            qc = FRQIEncoder(img).build_circuit()
            kind = "FRQI encoding circuit"
        else:
            r = img.shape[0]
            qc = NEQREncoder(neqr_quantize(img[None], params["bits"]).reshape(r, r), intensity_bits=params["bits"]).build_circuit()
            kind = f"NEQR encoding circuit ({params['bits']}-bit)"
        meas = ("Kernel = |⟨I_A|I_B⟩|² of the encoded states; " +
                ("exact statevector overlap." if not params.get("shots") else f"{params['shots']} shots per entry (sampled)."))
        ent = [["all position qubits", "colour/intensity qubit(s)", "multi-controlled rotations / X"]]
        inp = f"first training image of split {cfg.get('split_id')} ({first_train})"
    else:
        raise HTTPException(404, "this experiment has no quantum circuit (classical model)")
    ops = list(qc.data)
    limit = 600
    instr = []
    for i, ins in enumerate(ops[:limit]):
        q = [qc.find_bit(b).index for b in ins.qubits]
        prm = []
        for v in ins.operation.params:
            try:
                prm.append(round(float(v), 4))
            except (TypeError, ValueError):
                pass
        instr.append({"i": i, "name": ins.operation.name, "qubits": q, "params": prm})
    try:
        text = str(qc.draw(output="text", fold=120)) if len(ops) <= 240 else None
    except Exception:
        text = None
    regs = [{"name": r.name, "size": r.size} for r in qc.qregs]
    return {
        "experiment_id": experiment_id, "group": cfg.get("group"), "kind": kind, "params": params,
        "n_qubits": qc.num_qubits, "registers": regs, "input": inp,
        "logical_counts_displayed_circuit": {k: int(v) for k, v in qc.count_ops().items()},
        "logical_gates_displayed_circuit": len(ops), "logical_depth_displayed_circuit": qc.depth(),
        "recorded_resources": _read(d / "circuit_stats.json"),
        "entanglement": ent, "measurement": meas,
        "instructions": instr, "instructions_truncated": len(ops) > limit, "text_diagram": text,
        "status": (st or {}).get("status"),
    }


def circuit_artifact_path(experiment_id: str) -> Path:
    return _root() / "circuits" / f"{experiment_id}.json"


@router.get("/circuits/{experiment_id}")
def circuit_detail(experiment_id: str):
    """Serves the circuit artefact built offline by scripts/v2/build_circuit_artifacts.py (rebuilt from the saved
    checkpoint in a clean process). Circuits are not built inside the web server: Qiskit's native code segfaulted
    when constructed inside the API process (observed 2026-11-14; reproduced only with the full api_main import set)."""
    if "/" in experiment_id or ".." in experiment_id:
        raise HTTPException(400, "bad id")
    d = _read(circuit_artifact_path(experiment_id))
    if d is None:
        raise HTTPException(404, "circuit artefact not built for this experiment — run "
                                 "`python scripts/v2/build_circuit_artifacts.py` (classical models have no circuit)")
    return d


# ─── reconstruction images rendered from the saved arrays ────────────────────
from fastapi.responses import Response  # noqa: E402

RECON_MODES = ("statevector", "shots100", "shots1000", "shots10000", "shots100000")


@lru_cache(maxsize=8)
def _recon_arrays(record_id: str, stamp):
    p = _root() / "reconstructions" / record_id / "reconstructions.npz"
    z = np.load(p, allow_pickle=False)
    return {k: z[k] for k in z.files}


def _recon_dir(record_id: str) -> Path:
    if "/" in record_id or ".." in record_id:
        raise HTTPException(400, "bad id")
    d = _root() / "reconstructions" / record_id
    if not (d / "metrics.json").exists():
        raise HTTPException(404, "reconstruction record not found")
    return d


@router.get("/reconstructions/{record_id}/images")
def recon_images(record_id: str):
    """All evaluated images of a record with their per-mode metrics (from metrics.json)."""
    d = _recon_dir(record_id)
    m = _read(d / "metrics.json") or {}
    cfg = _read(d / "config.json") or {}
    rows = []
    for k, im in enumerate(m.get("per_image", [])):
        rows.append({"index": k, "image": im["image"], "class": im["class"], "modes": im["modes"],
                     "quantization_only": im.get("quantization_only")})
    return {"record_id": record_id, "config": cfg, "modes": [x for x in RECON_MODES if any(x in r["modes"] for r in rows)],
            "images": rows}


def _png(arr: np.ndarray) -> bytes:
    import io

    from PIL import Image
    u8 = (np.clip(arr, 0, 1) * 255).round().astype(np.uint8)
    h, w = u8.shape
    s = max(1, 192 // max(h, w))
    buf = io.BytesIO()
    Image.fromarray(u8, "L").resize((w * s, h * s), Image.Resampling.NEAREST).save(buf, "PNG")
    return buf.getvalue()


@router.get("/reconstructions/{record_id}/render/{index}/{mode}/{kind}.png")
def recon_render(record_id: str, index: int, mode: str, kind: str):
    """original | reconstructed | diff for one evaluated image, from the saved reconstruction arrays and the
    dataset image passed through the study's documented preprocessing (convert L → bilinear r×r → /255)."""
    from .dataset import load_manifest, preprocess_image
    d = _recon_dir(record_id)
    cfg = _read(d / "config.json") or {}
    imgs = cfg.get("images") or []
    if not 0 <= index < len(imgs) or mode not in RECON_MODES or kind not in ("original", "reconstructed", "diff"):
        raise HTTPException(404, "image/mode/kind not available")
    arrs = _recon_arrays(record_id, _stamp(d / "reconstructions.npz"))
    key = f"{index}__{mode}"
    if key not in arrs:
        raise HTTPException(404, "no saved reconstruction for this image and mode")
    root = Path(load_manifest()["dataset_root"])
    orig = preprocess_image(root / imgs[index], int(cfg["resolution"]))
    arr = orig if kind == "original" else arrs[key] if kind == "reconstructed" else np.abs(orig - arrs[key])
    return Response(_png(arr), media_type="image/png", headers={"Cache-Control": "max-age=3600"})


# ─── dataset sample images (raw NEU-DET training images, for presentation) ───
@router.get("/dataset/sample/{cls}.png")
def dataset_sample(cls: str, n: int = 0):
    """The n-th (by file index) TRAIN-folder image of a class, served as PNG. Never a locked-test image."""
    from .dataset import CLASSES, load_manifest
    if cls not in CLASSES or not 0 <= n < 20:
        raise HTTPException(404, "unknown class or index")
    man = load_manifest()
    recs = sorted((r for r in man["records"] if r["class"] == cls and r["role"] == "trainval"), key=lambda r: r["index"])
    import io

    from PIL import Image
    with Image.open(Path(man["dataset_root"]) / recs[n]["rel_path"]) as im:
        buf = io.BytesIO()
        im.convert("L").save(buf, "PNG")
    return Response(buf.getvalue(), media_type="image/png", headers={"Cache-Control": "max-age=86400"})


# ─── algorithm playground (illustrative 3×3 demo, built offline) ─────────────
@router.get("/playground")
def playground():
    """Illustrative 3×3 demonstration computed offline with the real implementations
    (scripts/v2/build_playground.py). Flagged `illustrative`; never an evaluation result."""
    d = _read(_root() / "playground" / "playground_3x3.json")
    if d is None:
        raise HTTPException(404, "playground data not built — run `python scripts/v2/build_playground.py`")
    return d
