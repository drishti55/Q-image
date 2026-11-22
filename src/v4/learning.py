"""Model-family learning centre (/api/v4/families). Read-only summary of Protocol V3 (which ran every model family on the
same feature sets, splits, seeds and locked test set). For each family the representative is the configuration with the
best VALIDATION macro-F1 (never chosen on test). Confusion matrices are summed over seeds from the saved locked-test
predictions in results/qml_v4/aggregates/per_image_predictions.json. Nothing is re-run."""
from __future__ import annotations

import json
from pathlib import Path

FEATURES = {"pix": "Pixels", "pixn": "Pixels (normalised)", "tex": "Texture (LBP + GLCM)", "mnv": "MobileNetV3 CNN"}
def _quantum(model: str) -> bool:
    return model.startswith(("qkc", "pqk")) or model in ("vqc", "vqc-spsa")


FAMILIES = [  # key, label, rule(group) -> bool
    ("qkc", "QKC · quantum kernel", lambda g: g["model"].startswith("qkc") and not g["feature_set"].startswith("mnv")),
    ("pqk", "PQK · projected quantum kernel", lambda g: g["model"].startswith("pqk")),
    ("vqc", "VQC · variational circuit", lambda g: g["model"] in ("vqc", "vqc-spsa")),
    ("hybrid", "Hybrid · CNN + quantum", lambda g: g["feature_set"].startswith("mnv") and _quantum(g["model"])),
    ("rbfsvm", "Classical RBF-SVM", lambda g: g["model"] == "rbfsvm"),
]
CLASSES = ["crazing", "inclusion", "patches", "pitted_surface", "rolled-in_scale", "scratches"]


def _ms(m):
    return {"mean": m.get("mean"), "std": m.get("std")} if isinstance(m, dict) else None


def _arch(g: dict) -> list:
    fs = g["feature_set"]
    base = next((v for k, v in sorted(FEATURES.items(), key=lambda kv: -len(kv[0])) if fs.startswith(k)), fs)
    k = "".join(ch for ch in fs if ch.isdigit())
    q = g.get("quantum") or {}
    m = g["model"]
    steps = [base, f"PCA → {k}" if k else None]
    if m.startswith("qkc"):
        steps += [f"{q.get('n_qubits', k)} qubits · {m.split('-', 1)[1].replace('_', '-')}", "|⟨φ(x)|φ(y)⟩|²", "SVM"]
    elif m.startswith("pqk"):
        steps += [f"{q.get('n_qubits', k)} qubits · {m.split('-', 1)[1].replace('_', '-')}", "Bloch vectors → RBF", "SVM"]
    elif m.startswith("vqc"):
        steps += [f"{q.get('n_qubits', k)} qubits · {q.get('n_layers')} trained layers", "⟨Z⟩ readout", "softmax"]
    else:
        steps += ["RBF kernel", "SVM"]
    return [s for s in steps if s]


def families(v3_root: Path, v4_root: Path) -> dict:
    r = json.loads((v3_root / "aggregates" / "v3_results.json").read_text())
    ix = json.loads((v4_root / "aggregates" / "per_image_predictions.json").read_text())
    G = {g["group"]: g for g in r["groups"]}
    rbf = {g["feature_set"]: g for g in r["groups"] if g["model"] == "rbfsvm"}

    def cm(gid):
        M = [[0] * 6 for _ in range(6)]
        for im in ix["images"].values():
            for p in im["preds"].get(gid, []):
                M[im["y_true"]][p] += 1
        return M if any(map(any, M)) else None

    def row(g):
        mate = rbf.get(g["feature_set"]) if g["model"] != "rbfsvm" else None
        return {"group": g["group"], "name": g.get("display_name") or g["group"], "feature_set": g["feature_set"],
                "n_qubits": (g.get("quantum") or {}).get("n_qubits"), "val_f1_macro": _ms(g.get("val_f1_macro")),
                "test_accuracy": _ms(g["test_accuracy"]), "test_precision_macro": _ms(g.get("test_precision_macro")),
                "test_recall_macro": _ms(g.get("test_recall_macro")), "test_f1_macro": _ms(g.get("test_f1_macro")),
                "train_time_s": _ms(g.get("train_time_s")), "inference_ms_per_image": _ms(g.get("inference_ms_per_image")),
                "architecture": _arch(g), "confusion_matrix": cm(g["group"]),
                "matched_rbfsvm": {"group": mate["group"], "test_accuracy": _ms(mate["test_accuracy"]),
                                   "train_time_s": _ms(mate.get("train_time_s"))} if mate else None}

    out = []
    for key, label, rule in FAMILIES:
        cands = [g for g in r["groups"] if rule(g) and g.get("val_f1_macro")]
        if not cands:
            continue
        best = max(cands, key=lambda g: g["val_f1_macro"]["mean"])
        out.append({"key": key, "label": label, "n_configs": len(cands), **row(best)})

    pairs = []
    for mc in r.get("matched_controls", []):
        q, c = G.get(mc.get("quantum")), G.get(mc.get("rbfsvm"))
        if q and c:
            pairs.append({"feature_set": mc["feature_set"], "features": _arch(c)[0], "quantum": q["group"], "quantum_acc": q["test_accuracy"]["mean"],
                          "rbfsvm": c["group"], "rbfsvm_acc": c["test_accuracy"]["mean"]})
    by_source = {}
    for g in r["groups"]:
        if g["model"].split("-")[0] in ("qkc", "pqk", "vqc") and "ablation" not in g["model"] and "encoding-only" not in g["model"]:
            src = _arch(g)[0]
            if src not in by_source or g["val_f1_macro"]["mean"] > by_source[src]["val_f1"]:
                by_source[src] = {"features": src, "group": g["group"], "val_f1": g["val_f1_macro"]["mean"], "test_accuracy": g["test_accuracy"]["mean"]}
    return {"protocol": "V3", "selection": "family representative = best validation macro-F1; test numbers reported once",
            "n_test": len(ix["images"]), "classes": CLASSES, "families": out, "matched_pairs": pairs,
            "quantum_by_feature_source": sorted(by_source.values(), key=lambda x: x["test_accuracy"])}
