"""Protocol V4 analysis -> results/qml_v4/aggregates/v4_results.json. Reads saved records only (V2/V3 read-only).
Runs exactly the 8 comparisons pre-declared in frozen_selection.json["plan"], Holm-corrected."""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parents[2]
V2, V3, V4 = (ROOT / "results" / x for x in ("qml_v2", "qml_v3", "qml_v4"))
FZ = json.loads((V4 / "aggregates" / "frozen_selection.json").read_text())
A2 = json.loads((V2 / "aggregates" / "analysis.json").read_text())["selected"]
R3 = {g["group"]: g for g in json.loads((V3 / "aggregates" / "v3_results.json").read_text())["groups"]}
CLASSES = ["crazing", "inclusion", "patches", "pitted_surface", "rolled-in_scale", "scratches"]


def dirs(g):
    if g.startswith("V4-"):
        k = FZ["groups"][g]["selected_config_key"]
        return [V4 / "experiments" / f"{k}__s{s}" for s in (0, 1, 2)]
    if g.startswith("V3-"):
        return [V3 / "experiments" / e for e in R3[g]["experiment_ids"]]
    return [V2 / "experiments" / e for e in A2[g]["experiment_ids"]]


def correct(d):
    with open(d / "predictions.csv", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["split"] == "test"]
    assert len(rows) == 360
    return {r["image"]: r["y_true"] == r["y_pred"] for r in rows}


def mat(g):
    cs = [correct(d) for d in dirs(g)]
    keys = sorted(cs[0])
    return keys, np.array([[c[k] for k in keys] for c in cs], float)


def compare(name, ga, gb):
    ka, A = mat(ga)
    kb, B = mat(gb)
    assert ka == kb
    d = A.mean(0) - B.mean(0)
    obs, n = float(d.mean()), len(d)
    rng = np.random.default_rng(int(hashlib.sha256(name.encode()).hexdigest()[:8], 16))
    boots = np.array([d[rng.integers(0, n, n)].mean() for _ in range(10000)])
    perm = np.abs((rng.choice([-1.0, 1.0], size=(10000, n)) * d).mean(1))
    p = float((np.sum(perm >= abs(obs) - 1e-12) + 1) / 10001)
    mc = []
    for s in range(3):
        a_only, b_only = int(((A[s] == 1) & (B[s] == 0)).sum()), int(((A[s] == 0) & (B[s] == 1)).sum())
        mc.append({"seed": s, "a_only_correct": a_only, "b_only_correct": b_only,
                   "p_exact": float(binomtest(a_only, a_only + b_only, 0.5).pvalue) if a_only + b_only else 1.0})
    return {"name": name, "a": ga, "b": gb, "acc_a": float(A.mean()), "acc_b": float(B.mean()), "diff": obs,
            "ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))], "p_permutation": p, "mcnemar_per_seed": mc}


def holm(rows):
    order = sorted(range(len(rows)), key=lambda i: rows[i]["p_permutation"])
    m, run = len(rows), 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (m - r) * rows[i]["p_permutation"]))
        rows[i]["p_holm"] = run
        rows[i]["significant_0_05"] = run < 0.05


def ms(v):
    return {"mean": float(np.mean(v)), "std": float(np.std(v, ddof=1)), "n": len(v)}


def group_row(g):
    tm = [json.loads((d / "test_metrics.json").read_text()) for d in dirs(g)]
    vm = [json.loads((d / "validation_metrics.json").read_text()) for d in dirs(g)]
    cfg = json.loads((dirs(g)[0] / "config.json").read_text())
    circ = dirs(g)[0] / "circuit_stats.json"
    pcf = {c: ms([t["per_class"][c]["f1"] if "per_class" in t else t["f1_per_class"][i] for t in tm]) for i, c in enumerate(CLASSES)} \
        if ("per_class" in tm[0] or "f1_per_class" in tm[0]) else None
    return {"group": g, "params": cfg["params"], "model_name": cfg["model_name"], "feature_extraction": cfg["feature_extraction"],
            "quantum": cfg.get("quantum"), "experiment_ids": [d.name for d in dirs(g)],
            "val_f1_macro": ms([v["f1_macro"] for v in vm]), "test_accuracy": ms([t["accuracy"] for t in tm]),
            "test_f1_macro": ms([t["f1_macro"] for t in tm]), "per_seed_test_accuracy": [t["accuracy"] for t in tm],
            "confusion_matrix_sum": np.sum([t["confusion_matrix"] for t in tm], 0).tolist(), "per_class_f1": pcf,
            "circuit": json.loads(circ.read_text()) if circ.exists() else None}


def main():
    groups = {g: group_row(g) for g in FZ["groups"]}
    fr = max(("V4-frqi-p4", "V4-frqi-p8"), key=lambda g: groups[g]["val_f1_macro"]["mean"])
    ne = max(("V4-neqr-p2", "V4-neqr-p4"), key=lambda g: groups[g]["val_f1_macro"]["mean"])
    plan = [("V4 FRQI vs V2 FRQI (E1b-frqi8-qkc-scaled)", fr, "E1b-frqi8-qkc-scaled"),
            ("V4 FRQI vs V3 FRQI (V3-frqi8)", fr, "V3-frqi8"),
            ("V4 NEQR vs V2 NEQR (E2-neqr16-b4-qkc)", ne, "E2-neqr16-b4-qkc"),
            ("V4 FRQI vs V4 NEQR", fr, ne),
            ("V4 FRQI vs classical patch-moment RBF-SVM", fr, "V4-patchmom-rbfsvm"),
            ("V4 NEQR vs classical patch-moment RBF-SVM", ne, "V4-patchmom-rbfsvm"),
            ("V4 FRQI vs classical texture RBF-SVM (V3-tex12c-rbfsvm)", fr, "V3-tex12c-rbfsvm"),
            ("V4 NEQR vs classical texture RBF-SVM (V3-tex12c-rbfsvm)", ne, "V3-tex12c-rbfsvm")]
    assert len(plan) == len(FZ["plan"]["comparisons"])
    comps = [compare(*p) for p in plan]
    holm(comps)
    ref = {"E1b-frqi8-qkc-scaled": A2["E1b-frqi8-qkc-scaled"], "E2-neqr16-b4-qkc": A2["E2-neqr16-b4-qkc"]}
    refs = {g: {"test_accuracy": ref[g]["test_accuracy"], "test_f1_macro": ref[g]["test_f1_macro"], "val_f1_macro": ref[g]["val_f1_macro"]} for g in ref}
    for g in ("V3-frqi8", "V3-neqr16", "V3-tex12c-rbfsvm"):
        refs[g] = {k: R3[g][k] for k in ("test_accuracy", "test_f1_macro", "val_f1_macro")}
    tal = [json.loads(l) for l in (V4 / "logs" / "test_access.jsonl").read_text().splitlines() if l.strip()]
    n_runs = sum(1 for _ in (V4 / "experiments").iterdir())
    failed = [d.name for d in (V4 / "experiments").iterdir() if json.loads((d / "status.json").read_text()).get("status") != "completed"]
    out = {"protocol": "V4", "created_at": datetime.now().isoformat(timespec="seconds"),
           "frozen_selection_sha256": hashlib.sha256((V4 / "aggregates" / "frozen_selection.json").read_bytes()).hexdigest(),
           "frozen_at": FZ["frozen_at"], "plan": FZ["plan"], "headlines": {"frqi": fr, "neqr": ne},
           "counts": {"groups": len(groups), "candidate_runs": n_runs, "failed_runs": len(failed), "test_access_events": len(tal)},
           "test_access_log": tal, "groups": groups, "references": refs, "comparisons": comps}
    p = V4 / "aggregates" / "v4_results.json"
    p.write_text(json.dumps(out, indent=1, default=float))
    print(f"wrote {p}; runs {n_runs}, failed {len(failed)}")
    for g, r in groups.items():
        print(f"  {g:22s} val {r['val_f1_macro']['mean']:.3f}  test acc {100*r['test_accuracy']['mean']:.1f} ± {100*r['test_accuracy']['std']:.1f}  "
              f"F1 {100*r['test_f1_macro']['mean']:.1f}  seeds {[round(100*x,1) for x in r['per_seed_test_accuracy']]}")
    for c in comps:
        print(f"  {c['name']:58s} {100*c['acc_a']:.1f} vs {100*c['acc_b']:.1f}  diff {100*c['diff']:+.1f} "
              f"[{100*c['ci95'][0]:+.1f},{100*c['ci95'][1]:+.1f}]  p_holm={c['p_holm']:.4f}")


if __name__ == "__main__":
    main()
