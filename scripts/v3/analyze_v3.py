"""
Protocol V3 analysis -> results/qml_v3/aggregates/v3_results.json. Built ONLY from saved records:
results/qml_v3 (V3 experiments, selections, frozen manifest) and, read-only, results/qml_v2 (V2 baselines).

Headline rule (declared in frozen_selection.json before testing): within each category the headline is the group with
the highest mean VALIDATION macro-F1; the test set is never used to choose.
Statistics for every pre-declared comparison (A vs B, both evaluated on the same 360 locked images, seeds 0/1/2):
  * accuracy difference of the seed-mean, 95% bootstrap CI over images (10,000 resamples);
  * paired sign-flip permutation test on per-image correctness averaged over seeds (10,000 permutations, two-sided);
  * per-seed exact McNemar p-values (information);
  * Holm correction over the whole family of comparisons.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy.stats import binomtest

from common import V2, V3
from run_v3 import FEATS

EXP3, EXP2 = V3 / "experiments", V2 / "experiments"
CLASSES = ["crazing", "inclusion", "patches", "pitted_surface", "rolled-in_scale", "scratches"]
RNG = np.random.default_rng(0)


def rd(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def ms(v):
    v = [x for x in v if x is not None]
    return {"mean": float(np.mean(v)) if v else None, "std": float(np.std(v, ddof=1)) if len(v) > 1 else None, "n": len(v)}


def correctness(exp_dir: Path):
    """image -> correct (bool) for the test split."""
    out = {}
    with open(exp_dir / "predictions.csv", newline="") as f:
        for r in csv.DictReader(f):
            if r["split"] == "test":
                out[r["image"]] = int(r["y_true"]) == int(r["y_pred"])
    return out


def seed_matrix(dirs):
    cs = [correctness(d) for d in dirs]
    keys = sorted(set.intersection(*[set(c) for c in cs]))
    return keys, np.array([[c[k] for k in keys] for c in cs], dtype=float)  # (seeds, images)


def compare(name, dirs_a, dirs_b, label_a, label_b, kind):
    ka, A = seed_matrix(dirs_a)
    kb, B = seed_matrix(dirs_b)
    assert ka == kb, "comparisons must use the same test images"
    d = A.mean(0) - B.mean(0)
    obs = float(d.mean())
    n = len(d)
    # per-comparison RNG seeded from its name: results do not depend on how many / which other comparisons run
    rng = np.random.default_rng(int(__import__("hashlib").sha256(name.encode()).hexdigest()[:8], 16))
    boots = np.array([d[rng.integers(0, n, n)].mean() for _ in range(10000)])
    signs = rng.choice([-1.0, 1.0], size=(10000, n))
    perm = np.abs((signs * d).mean(1))
    p_perm = float((np.sum(perm >= abs(obs) - 1e-12) + 1) / (len(perm) + 1))
    mcn = []
    for s in range(A.shape[0]):
        a_only, b_only = int(np.sum((A[s] == 1) & (B[s] == 0))), int(np.sum((A[s] == 0) & (B[s] == 1)))
        p = binomtest(a_only, a_only + b_only, 0.5).pvalue if a_only + b_only else 1.0
        mcn.append({"seed": s, "a_only_correct": a_only, "b_only_correct": b_only, "p_exact": float(p)})
    return {"name": name, "kind": kind, "a": label_a, "b": label_b, "n_images": n,
            "acc_a": float(A.mean()), "acc_b": float(B.mean()), "diff": obs,
            "ci95": [float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))],
            "p_permutation": p_perm, "mcnemar_per_seed": mcn}


def holm(rows):
    order = sorted(range(len(rows)), key=lambda i: rows[i]["p_permutation"])
    m, running = len(rows), 0.0
    for rank, i in enumerate(order):
        adj = min(1.0, (m - rank) * rows[i]["p_permutation"])
        running = max(running, adj)
        rows[i]["p_holm"] = running
        rows[i]["significant_0.05"] = running < 0.05
    return rows


# ─────────────────────────── group metadata ───────────────────────────
def parse(group: str):
    parts = group.split("-")  # V3-<feat>-<model...>
    feat, model = parts[1], "-".join(parts[2:])
    return feat, model


def category(feat, model, family):
    if feat.startswith(("frqi", "neqr")):
        return "quantum_encoding"
    if model in ("rbfsvm", "logreg"):
        return "classical_control"
    if "ablation" in model or "encoding-only" in model:
        return "vqc_control"
    if model.startswith("vqc"):
        return "hybrid_vqc" if feat.startswith("mnv") else "vqc"
    return "hybrid" if feat.startswith("mnv") else "quantum_kernel"


def display(feat, model, params):
    fd = {"pix8a": "Pixels PCA-8 (angle)", "pix8c": "Pixels PCA-8", "pix12c": "Pixels PCA-12", "pixn8c": "Pixels PCA-8 (per-image norm)",
          "tex8c": "Texture PCA-8", "tex12c": "Texture PCA-12", "mnv8c": "MobileNetV3 PCA-8", "mnv12c": "MobileNetV3 PCA-12"}.get(feat)
    if feat.startswith(("frqi", "neqr")):
        r = feat[4:]
        rep = feat[:4].upper()
        extra = f" · {params.get('bits')}-bit" if rep == "NEQR" else f" · angle ×{params.get('angle_scale')}"
        return f"{rep} {r}×{r}{extra} · {params.get('kernel')} kernel{' · stretch' if params.get('norm') == 'stretch' else ''}"
    mm = {"rbfsvm": "RBF-SVM", "logreg": "Logistic Regression", "vqc": "VQC", "vqc-spsa": "VQC (calibrated SPSA)",
          "vqc-ablation-frozen": "VQC ablation (frozen circuit)", "vqc-encoding-only": "VQC control (encoding only)"}
    if model in mm:
        name = mm[model]
        if model == "vqc" or model == "vqc-spsa":
            name += f" · L={params.get('layers')} · {params.get('readout')}"
        return f"{fd} + {name}"
    kind, fmap = model.split("-", 1)
    fm = {"product_ry": "product-RY", "zz_linear": "ZZ-linear", "zz_full": "ZZ-full"}[fmap]
    return f"{fd} + {'QKC' if kind == 'qkc' else 'Projected QK'} {fm}"


def load_group(group: str, sel: dict):
    best = sel.get("selected")
    if not best:
        return None
    dirs = [EXP3 / e for e in best["experiment_ids"]]
    st = [rd(d / "status.json") or {} for d in dirs]
    summ = [s.get("summary") or {} for s in st]
    tm = [rd(d / "test_metrics.json") for d in dirs]
    if not all(tm):
        return None
    feat, model = parse(group)
    fam = summ[0].get("family")
    pcls = {}
    for i, c in enumerate(CLASSES):
        vals = [t["per_class"][c]["f1"] if isinstance(t.get("per_class"), dict) and c in t["per_class"] else None for t in tm]
        pcls[c] = ms(vals)
    circ = rd(dirs[0] / "circuit_stats.json")
    diag = rd(dirs[0] / "diagnostics.json") or {}
    tk = diag.get("train_kernel") or {}
    return {
        "group": group, "feature_set": feat, "model": model, "category": category(feat, model, fam), "family": fam,
        "display_name": display(feat, model, best["params"]), "feature_description": FEATS.get(feat, (None, None, f"{feat} image"))[2],
        "params": best["params"], "quantum": best.get("quantum"), "n_candidates": sel["n_candidates"],
        "experiment_ids": best["experiment_ids"], "val_f1_macro": {"mean": best["val_mean"], "std": best.get("val_std")},
        "test_accuracy": ms([t["accuracy"] for t in tm]), "test_f1_macro": ms([t["f1_macro"] for t in tm]),
        "test_precision_macro": ms([t["precision_macro"] for t in tm]), "test_recall_macro": ms([t["recall_macro"] for t in tm]),
        "per_seed_test_accuracy": [t["accuracy"] for t in tm],
        "per_seed_ci95": [t.get("bootstrap_ci", {}).get("accuracy") for t in tm],
        "per_class_f1": pcls,
        "train_time_s": ms([s.get("train_time_s") for s in summ]),
        "inference_ms_per_image": ms([s.get("test_inference_ms_per_image") for s in summ]),
        "n_qubits": (best.get("quantum") or {}).get("n_qubits"),
        "circuit": {k: circ.get(k) for k in ("n_qubits", "gates_logical", "depth_logical", "gates_compiled", "depth_compiled",
                                              "cx_compiled", "readout_kind", "n_trainable_quantum_params", "n_classical_head_params",
                                              "measurement", "execution_mode")} if circ else None,
        "kernel_diagnostics_seed0": {k: tk.get(k) for k in ("offdiag_mean", "offdiag_var", "min_eigenvalue", "psd_within_tol",
                                                           "centered_kernel_alignment", "kernel_target_alignment",
                                                           "mean_same_class", "mean_diff_class")} if tk else None,
        "kernel_spectrum_seed0": diag.get("train_kernel_spectrum"),
        "vqc_diagnostics_seed0": {k: diag.get(k) for k in ("init_grad", "stopped_at", "converged", "theta_change_l2",
                                                           "n_quantum_params", "n_classical_params", "spsa_calibrated_a")}
        if model.startswith("vqc") else None,
        "dirs": [str(d) for d in dirs],
    }


def v2_dirs(group):
    sel = rd(V2 / "aggregates" / "selection" / f"{group}.json")["selected"]
    return [EXP2 / e for e in sel["experiment_ids"]]


def v2_row(group):
    a = rd(V2 / "aggregates" / "analysis.json")
    for row in a["selected"] if isinstance(a.get("selected"), list) else []:
        if row.get("group") == group:
            return row
    dirs = v2_dirs(group)
    tm = [rd(d / "test_metrics.json") for d in dirs]
    sel = rd(V2 / "aggregates" / "selection" / f"{group}.json")["selected"]
    return {"group": group, "val_f1_macro": {"mean": sel["val_mean"]}, "test_accuracy": ms([t["accuracy"] for t in tm]),
            "test_f1_macro": ms([t["f1_macro"] for t in tm]), "experiment_ids": sel["experiment_ids"]}


def best_by_val(rows):
    rows = [r for r in rows if r and r["val_f1_macro"]["mean"] is not None]
    return max(rows, key=lambda r: r["val_f1_macro"]["mean"]) if rows else None


def main():
    fz = rd(V3 / "aggregates" / "frozen_selection.json")
    assert fz, "run the freeze stage first"
    G = {}
    for g in fz["groups"]:
        sel = rd(V3 / "aggregates" / "selection" / f"{g}.json")
        row = load_group(g, sel)
        if row:
            G[g] = row
    rows = list(G.values())
    by_cat = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)

    # headlines by validation
    pure = [r for r in rows if r["category"] in ("quantum_kernel", "quantum_encoding")]
    head = {"pure_quantum": best_by_val(pure), "vqc": best_by_val(by_cat["vqc"]),
            "hybrid_quantum": best_by_val(by_cat["hybrid"] + by_cat["hybrid_vqc"]),
            "classical_control_best": best_by_val(by_cat["classical_control"]),
            "frqi": best_by_val([r for r in rows if r["feature_set"].startswith("frqi")]),
            "neqr": best_by_val([r for r in rows if r["feature_set"].startswith("neqr")])}

    # before / after (V2 baseline -> V3, V3 pick by validation)
    def pick(pred):
        return best_by_val([r for r in rows if pred(r)])
    pixel = ("pix8a", "pix8c", "pix12c", "pixn8c")
    before_after = []
    spec = [
        ("ZZ-full QKC (V2: pixel PCA-8)", "E3-pca8-qkc-zz_full", lambda r: r["model"] == "qkc-zz_full" and r["feature_set"] in pixel,
         lambda r: r["model"] in ("qkc-zz_full", "pqk-zz_full") and r["category"] == "quantum_kernel"),
        ("ZZ-linear QKC (V2: pixel PCA-8)", "E3-pca8-qkc-zz_linear", lambda r: r["model"] == "qkc-zz_linear" and r["feature_set"] in pixel,
         lambda r: r["model"] in ("qkc-zz_linear", "pqk-zz_linear") and r["category"] == "quantum_kernel"),
        ("product-RY QKC (V2: pixel PCA-8)", "E3-pca8-qkc-product_ry", lambda r: r["model"] == "qkc-product_ry" and r["feature_set"] in pixel,
         lambda r: r["model"] == "qkc-product_ry" and r["category"] == "quantum_kernel"),
        ("FRQI angle-scaled 8×8", "E1b-frqi8-qkc-scaled", lambda r: r["feature_set"].startswith("frqi"), lambda r: r["feature_set"].startswith("frqi")),
        ("NEQR 4-bit 16×16", "E2-neqr16-b4-qkc", lambda r: r["feature_set"].startswith("neqr"), lambda r: r["feature_set"].startswith("neqr")),
        ("Genuine VQC (V2: pixel PCA-8)", "E4-pca8-vqc", lambda r: r["category"] == "vqc" and r["feature_set"].startswith("pix"),
         lambda r: r["category"] == "vqc"),
        ("CNN + product-RY QKC", "E5-mnv3pca8-qkc-product_ry", lambda r: r["model"] == "qkc-product_ry" and r["feature_set"] == "mnv8c",
         lambda r: r["category"] == "hybrid" and r["model"] == "qkc-product_ry"),
        ("CNN + ZZ-full QKC", "E5-mnv3pca8-qkc-zz_full", lambda r: r["model"] == "qkc-zz_full" and r["feature_set"] == "mnv8c",
         lambda r: r["category"] == "hybrid" and r["model"] in ("qkc-zz_full", "pqk-zz_full")),
        ("CNN + ZZ-linear QKC", "E5-mnv3pca8-qkc-zz_linear", lambda r: r["model"] == "qkc-zz_linear" and r["feature_set"] == "mnv8c",
         lambda r: r["category"] == "hybrid" and r["model"] in ("qkc-zz_linear", "pqk-zz_linear")),
        ("CNN + VQC", "E5-mnv3pca8-vqc", lambda r: r["category"] == "hybrid_vqc", lambda r: r["category"] == "hybrid_vqc"),
    ]
    comps, secondary = [], []
    for label, v2g, like, any_ in spec:
        b = v2_row(v2g)
        l, a = pick(like), pick(any_)
        before_after.append({"model": label, "v2_group": v2g, "v2_test_accuracy": b["test_accuracy"], "v2_val_f1": b["val_f1_macro"],
                             "v3_like_for_like": l and {k: l[k] for k in ("group", "display_name", "n_qubits", "test_accuracy", "val_f1_macro", "test_f1_macro")},
                             "v3_best": a and {k: a[k] for k in ("group", "display_name", "n_qubits", "test_accuracy", "val_f1_macro", "test_f1_macro")}})
        if a:
            comps.append(compare(f"V3 vs V2: {label}", [Path(x) for x in a["dirs"]], v2_dirs(v2g), a["group"], v2g, "v3_vs_v2"))
        # secondary, added after unblinding: like-for-like (same input family as V2); own Holm family
        if l and a and l["group"] != a["group"]:
            secondary.append(compare(f"V3 like-for-like vs V2: {label}", [Path(x) for x in l["dirs"]], v2_dirs(v2g), l["group"], v2g,
                                     "v3_like_vs_v2_posthoc"))

    # quantum vs matched classical control (same feature set; quantum group chosen by validation)
    matched = []
    for f in sorted({r["feature_set"] for r in rows if not r["feature_set"].startswith(("frqi", "neqr"))}):
        q = best_by_val([r for r in rows if r["feature_set"] == f and r["category"] in ("quantum_kernel", "hybrid", "vqc", "hybrid_vqc")])
        c = G.get(f"V3-{f}-rbfsvm")
        lr = G.get(f"V3-{f}-logreg")
        if q and c:
            row = compare(f"Quantum vs matched RBF-SVM ({f})", [Path(x) for x in q["dirs"]], [Path(x) for x in c["dirs"]], q["group"], c["group"], "quantum_vs_classical")
            comps.append(row)
            matched.append({"feature_set": f, "quantum": q["group"], "rbfsvm": c["group"], "logreg": lr and lr["group"]})
        vq = G.get(f"V3-{f}-vqc")
        if vq:
            for ctl in ("vqc-ablation-frozen", "vqc-encoding-only"):
                cg = G.get(f"V3-{f}-{ctl}")
                if cg:
                    comps.append(compare(f"VQC vs {ctl} ({f})", [Path(x) for x in vq["dirs"]], [Path(x) for x in cg["dirs"]], vq["group"], cg["group"], "vqc_vs_control"))
    holm(comps)
    holm(secondary)

    tal = [json.loads(l) for l in (V3 / "logs" / "test_access.jsonl").read_text().splitlines() if l.strip()] \
        if (V3 / "logs" / "test_access.jsonl").exists() else []
    n_runs = sum(1 for _ in EXP3.iterdir())
    failed = [d.name for d in EXP3.iterdir() if (rd(d / "status.json") or {}).get("status") == "failed"]
    for r in rows:
        r.pop("dirs", None)
    out = {"protocol": "V3", "created_at": datetime.now().isoformat(),
           "frozen_selection_sha256": __import__("hashlib").sha256((V3 / "aggregates" / "frozen_selection.json").read_bytes()).hexdigest(),
           "frozen_at": fz["frozen_at"], "headline_rule": fz["plan"]["headline_rule"],
           "counts": {"groups": len(fz["groups"]), "groups_tested": len(rows), "candidate_runs": n_runs, "failed_runs": len(failed),
                      "test_access_events": len(tal)},
           "failed_runs": failed[:50], "test_access_log": tal,
           "headlines": {k: v and {kk: v[kk] for kk in ("group", "display_name", "category", "test_accuracy", "test_f1_macro", "val_f1_macro")} for k, v in head.items()},
           "before_after": before_after, "matched_controls": matched, "comparisons": comps,
           "secondary_comparisons_posthoc": secondary, "groups": rows,
           "notes": ["All quantum circuits were simulated exactly on a CPU (no quantum hardware, no noise).",
                     "Texture (LBP/GLCM) features are classical and non-learned; any gain they bring is a representation effect, "
                     "measured against RBF-SVM / logistic regression on the identical features.",
                     "Product-RY kernels are classically computable in closed form (control)."]}
    p = V3 / "aggregates" / "v3_results.json"
    p.write_text(json.dumps(out, indent=1, default=float))
    print(f"wrote {p}: {len(rows)} groups, {len(comps)} comparisons")
    for k, v in out["headlines"].items():
        if v:
            print(f"  {k:24s} {v['display_name']:60s} val {v['val_f1_macro']['mean']:.3f}  test acc {v['test_accuracy']['mean']:.3f}")
    for b in before_after:
        a = b["v3_best"]
        print(f"  {b['model']:24s} V2 {b['v2_test_accuracy']['mean']:.3f} -> V3 {a and a['test_accuracy']['mean']:.3f}  ({a and a['display_name']})")
    for c in comps + secondary:
        print(f"  {c['name']:55s} diff {c['diff']*100:+.1f}pp CI [{c['ci95'][0]*100:+.1f},{c['ci95'][1]*100:+.1f}] p={c['p_permutation']:.4f} holm={c['p_holm']:.4f}")


if __name__ == "__main__":
    main()
