"""Phase 8: consolidated analysis built ONLY from saved v2 records -> aggregates/analysis.json.
Every number carries the experiment ids it came from."""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.v2.paths import v2_root  # noqa: E402
from src.v2.store import dump_json  # noqa: E402

R = v2_root()
EXP = R / "experiments"


def rd(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


def ms(v):
    v = [x for x in v if x is not None]
    return {"mean": float(np.mean(v)) if v else None, "std": float(np.std(v, ddof=1)) if len(v) > 1 else None, "n": len(v)}


def load_all():
    rows = []
    for d in sorted(EXP.iterdir()):
        st = rd(d / "status.json")
        if st:
            rows.append({"id": d.name, "status": st["status"], **(st.get("summary") or {}),
                         "error": (st.get("error") or {}).get("message")})
    return rows


def test_preds(eid):
    p = EXP / eid / "predictions.csv"
    out = {}
    with open(p, newline="") as f:
        for r in csv.DictReader(f):
            if r["split"] == "test":
                out[r["image"]] = (int(r["y_true"]), int(r["y_pred"]))
    return out


def mcnemar(eid_a, eid_b):
    a, b = test_preds(eid_a), test_preds(eid_b)
    keys = sorted(set(a) & set(b))
    ca = np.array([a[k][0] == a[k][1] for k in keys])
    cb = np.array([b[k][0] == b[k][1] for k in keys])
    n01, n10 = int(np.sum(ca & ~cb)), int(np.sum(~ca & cb))
    p = binomtest(n01, n01 + n10, 0.5).pvalue if n01 + n10 else 1.0
    return {"n_images": len(keys), "a_only_correct": n01, "b_only_correct": n10, "p_value_exact": float(p),
            "acc_a": float(ca.mean()), "acc_b": float(cb.mean())}


def category(fam):
    return {"classical": "1. Classical classification", "quantum_kernel": "2. Quantum kernel classification",
            "variational_quantum": "3. Variational quantum classification", "hybrid": "4. Hybrid classification",
            "quantum_inspired_classical": "6. Relabelled legacy (classical) methods"}.get(fam, "other")


def main():
    rows = load_all()
    by_group = defaultdict(list)
    for r in rows:
        by_group[r.get("group")].append(r)

    # 1. selected configuration per group
    selected = {}
    for g, rs in by_group.items():
        sel = [r for r in rs if r.get("selected") and r.get("test")]
        if not sel:
            continue
        r0 = sel[0]
        selected[g] = {
            "group": g, "category": category(r0["family"]), "model_name": r0["model_name"], "family": r0["family"],
            "n_qubits": r0.get("n_qubits"), "params": r0.get("params"), "feature_extraction": r0.get("feature_extraction"),
            "experiment_ids": sorted(r["id"] for r in sel), "n_seeds": len(sel), "n_test": r0.get("n_test"),
            "val_f1_macro": ms([r["val"]["f1_macro"] for r in sel]),
            **{f"test_{m}": ms([r["test"][m] for r in sel]) for m in
               ("accuracy", "precision_macro", "recall_macro", "f1_macro", "f1_weighted")},
            "test_ci_per_seed": {str(r["seed"]): r.get("test_ci") for r in sel},
            "train_time_s": ms([r.get("train_time_s") for r in sel]),
            "test_inference_ms_per_image": ms([r.get("test_inference_ms_per_image") for r in sel]),
            "circuit_depth_logical": r0.get("circuit_depth"), "circuit_depth_compiled": r0.get("circuit_depth_compiled"),
        }
        sel_file = rd(R / "aggregates" / "selection" / f"{g}.json") or {}
        selected[g]["n_candidates"] = sel_file.get("n_candidates")

    # 2. meta-selection of PCA dimension per family (validation only)
    meta = {}
    for fam_prefix in ("E6-pca{k}-rbfsvm", "E6-pca{k}-logreg", "E6-pca{k}-rbfsvm-angle", "E5-mnv3pca{k}-rbfsvm",
                       "E5-mnv3pca{k}-logreg", "E5-mnv3pca{k}-vqc", "E4-pca{k}-vqc"):
        cands = {k: selected.get(fam_prefix.format(k=k)) for k in (4, 6, 8)}
        cands = {k: v for k, v in cands.items() if v}
        if cands:
            kb = max(cands, key=lambda k: cands[k]["val_f1_macro"]["mean"])
            meta[fam_prefix.format(k="K")] = {"selected_k_by_validation": kb, "group": cands[kb]["group"],
                                              "val_by_k": {k: v["val_f1_macro"]["mean"] for k, v in cands.items()}}
    for k in (4, 6, 8):
        q = {g: v for g, v in selected.items() if g.startswith(f"E3-pca{k}-qkc-") and "shots" not in g}
        if q:
            gb = max(q, key=lambda g: q[g]["val_f1_macro"]["mean"])
            meta[f"E3-pca{k}-qkc (best feature map by validation)"] = {"group": gb, "val_by_map": {g: v["val_f1_macro"]["mean"] for g, v in q.items()}}

    # 3. paired significance tests on identical test images (per seed)
    pairs = []

    def pair(ga, gb, label):
        if ga in selected and gb in selected:
            res = []
            for ea in selected[ga]["experiment_ids"]:
                seed = ea.rsplit("__s", 1)[1]
                eb = next((e for e in selected[gb]["experiment_ids"] if e.endswith(f"__s{seed}")), None)
                if eb:
                    res.append({"seed": int(seed), "a": ea, "b": eb, **mcnemar(ea, eb)})
            pairs.append({"comparison": label, "a": ga, "b": gb, "per_seed": res,
                          "seeds_significant_at_0.05": sum(r["p_value_exact"] < 0.05 for r in res)})
    for k in (4, 6, 8):
        for fmap in ("product_ry", "zz_linear", "zz_full"):
            pair(f"E3-pca{k}-qkc-{fmap}", f"E6-pca{k}-rbfsvm-angle", f"QKC {fmap} vs RBF-SVM, identical PCA({k}) angle features")
        pair(f"E3-pca{k}-qkc-zz_linear", f"E3-pca{k}-qkc-product_ry", f"ZZ-linear vs product-RY control (PCA {k})")
        pair(f"E4-pca{k}-vqc", f"E6-pca{k}-rbfsvm-angle", f"VQC vs RBF-SVM, PCA({k})")
        pair(f"E4-pca{k}-vqc", f"E4-pca{k}-vqc-ablation-frozen", f"Trained VQC vs frozen-circuit ablation (PCA {k})")
        pair(f"E4-pca{k}-vqc", f"E6-pca{k}-logreg", f"VQC vs logistic regression, PCA({k})")
        for fmap in ("product_ry", "zz_linear", "zz_full"):
            pair(f"E5-mnv3pca{k}-qkc-{fmap}", f"E5-mnv3pca{k}-rbfsvm", f"CNN+QKC {fmap} vs CNN+RBF-SVM (MobileNet PCA {k})")
        pair(f"E5-mnv3pca{k}-vqc", f"E5-mnv3pca{k}-logreg", f"CNN+VQC vs CNN+LogReg (MobileNet PCA {k})")
    pair("E7-mnv3-rbfsvm", "E7-smallcnn", "Frozen MobileNetV3+SVM vs small CNN")

    # 4. kernel concentration vs bandwidth (train kernels of all E3 candidates)
    conc = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r.get("experiment_code") == "E3" and r["status"] == "completed" and not (r.get("params") or {}).get("shots"):
            d = rd(EXP / r["id"] / "diagnostics.json") or {}
            tk = d.get("train_kernel") or {}
            p = r["params"]
            key = f"k={r['n_qubits']}|{p['feature_map']}|reps={p['reps']}|bw={p['bandwidth']}"
            if p["C"] == 1.0:  # kernel does not depend on C: one entry per seed
                conc[key]["offdiag_mean"].append(tk.get("offdiag_mean"))
                conc[key]["offdiag_std"].append(tk.get("offdiag_std"))
                conc[key]["cka"].append(tk.get("centered_kernel_alignment"))
                conc[key]["min_eig"].append(tk.get("min_eigenvalue"))
            conc[key]["val_f1"].append((r.get("val") or {}).get("f1_macro"))
    concentration = {k: {m: ms(v) for m, v in d.items()} for k, d in sorted(conc.items())}

    # 5. shot sensitivity
    shots = defaultdict(dict)
    for g, s in selected.items():
        if "shots" in g:
            base = g.split("-shots")[0]
            shots[base][int(g.split("-shots")[1])] = {"test_accuracy": s["test_accuracy"], "test_f1_macro": s["test_f1_macro"],
                                                     "experiment_ids": s["experiment_ids"]}
    for base in list(shots):
        sv = selected.get(base) or next((v for g, v in selected.items() if g.startswith(base.rsplit("-", 1)[0] + "-") and
                                         v["params"] and not v["params"].get("shots") and
                                         v["params"].get("feature_map") == base.rsplit("-", 1)[1]), None)
        if sv:
            shots[base][0] = {"test_accuracy": sv["test_accuracy"], "test_f1_macro": sv["test_f1_macro"],
                              "experiment_ids": sv["experiment_ids"], "note": "statevector (exact)"}

    # 6. VQC grid summary (validation only for non-selected)
    vqc = defaultdict(list)
    for r in rows:
        if r.get("experiment_code") in ("E4",) and r["status"] == "completed" and "ablation" not in r["group"]:
            p = r["params"]
            vqc[f"k={r['n_qubits']}|L={p['layers']}|{p['optimizer']}|reupload={p['reupload']}"].append(r["val"]["f1_macro"])
    vqc_summary = {k: ms(v) for k, v in sorted(vqc.items())}
    vqc_diag = defaultdict(list)
    for r in rows:
        if r.get("experiment_code") == "E4" and r["status"] == "completed":
            d = rd(EXP / r["id"] / "diagnostics.json") or {}
            if d.get("init_grad"):
                vqc_diag[f"k={r['n_qubits']}|L={r['params']['layers']}"].append(d["init_grad"]["var"])
    vqc_grad = {k: ms(v) for k, v in sorted(vqc_diag.items())}

    # 7. reconstruction
    recon = []
    for d in sorted((R / "reconstructions").iterdir()) if (R / "reconstructions").exists() else []:
        st, m, cs = rd(d / "status.json"), rd(d / "metrics.json"), rd(d / "circuit_stats.json")
        if not st:
            continue
        row = {"record_id": d.name, "status": st["status"], "error": (st.get("error") or {}).get("message")}
        if m:
            row["summary"] = m["summary"]
            row["timing"] = m["timing"]
        if cs:
            row["circuit"] = {k: cs.get(k) for k in ("n_qubits", "gates_logical", "depth_logical", "gates_compiled",
                                                     "depth_compiled", "cx_compiled", "two_qubit_gates_compiled")}
        recon.append(row)

    failed = [{"id": r["id"], "group": r.get("group"), "error": r["error"]} for r in rows if r["status"] == "failed"]
    out = {"n_experiments": len(rows), "n_completed": sum(r["status"] == "completed" for r in rows),
           "n_failed": len(failed), "failed": failed, "selected": selected, "meta_selection": meta,
           "paired_tests": pairs, "kernel_concentration": concentration, "shot_sensitivity": shots,
           "vqc_validation_grid": vqc_summary, "vqc_init_gradient_variance": vqc_grad, "reconstruction": recon,
           "notes": ["Classification and reconstruction are separate tasks and are never ranked together.",
                     "Test metrics exist only for validation-selected configurations; mean ± sample std over seeds 0,1,2.",
                     "McNemar exact test per seed on the 360 locked-test images; p-values are not corrected for "
                     "multiple comparisons.", "All quantum results are noiseless classical simulations."]}
    dump_json(R / "aggregates" / "analysis.json", out)
    print(f"analysis: {len(selected)} selected groups, {len(pairs)} paired comparisons, {len(recon)} reconstruction records, "
          f"{len(failed)} failed experiments")


if __name__ == "__main__":
    main()
