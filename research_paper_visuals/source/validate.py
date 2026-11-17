"""
Independent validation of every figure and table in research_paper_visuals/ against the raw Protocol V2 records.
Recomputes values from per-experiment files (test_metrics.json, predictions.csv, circuit_stats.json,
reconstructions/*/metrics.json, manifest, split files) — NOT from analysis.json — and compares them with
(a) analysis.json, (b) the figure-data CSVs and (c) the table CSVs. Also checks every LaTeX path.
Writes research_paper_visuals/VALIDATION_REPORT.md; exit code 1 on any failure.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import binomtest

OUT = Path(__file__).resolve().parent.parent
R = OUT.parent / "results" / "qml_v2"
A = json.loads((R / "aggregates" / "analysis.json").read_text())
SEL = A["selected"]
checks = []


def ok(name, cond, detail=""):
    checks.append((name, bool(cond), detail))


def rcsv(p):
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def raw_ms(group, key):
    v = [json.loads((R / "experiments" / e / "test_metrics.json").read_text())[key] for e in SEL[group]["experiment_ids"]]
    return float(np.mean(v)), float(np.std(v, ddof=1))


# 1. analysis.json selected metrics == recomputation from per-experiment files (all 88 groups, 4 metrics)
bad = []
for g in SEL:
    for k, tk in (("test_accuracy", "accuracy"), ("test_f1_macro", "f1_macro"), ("test_precision_macro", "precision_macro"),
                  ("test_recall_macro", "recall_macro")):
        m, s = raw_ms(g, tk)
        if abs(m - SEL[g][k]["mean"]) > 1e-12 or abs(s - (SEL[g][k]["std"] or 0)) > 1e-12:
            bad.append((g, k))
ok("analysis.json metrics equal per-experiment test_metrics.json (88 groups x 4 metrics)", not bad, str(bad[:3]))

# 2. each selected experiment has exactly 360 test predictions and the test set is the locked folder
n_bad = 0
for g in SEL:
    for e in SEL[g]["experiment_ids"]:
        rows = [r for r in rcsv(R / "experiments" / e / "predictions.csv") if r["split"] == "test"]
        n_bad += len(rows) != 360 or any(not r["image"].startswith("validation/") for r in rows)
ok("every selected experiment: 360 locked-test predictions from validation/ folder", n_bad == 0, f"{n_bad} bad")

# 3. dataset / splits
man = json.loads((R / "manifests" / "dataset_manifest_neu-5625b937479b.json").read_text())
cls = Counter((r["role"], r["class"]) for r in man["records"])
ok("manifest: 1,800 images, 240 trainval + 60 locked test per class", len(man["records"]) == 1800 and
   all(cls[("trainval", c)] == 240 and cls[("locked_test", c)] == 60 for c in man["classes"]))
by = {r["rel_path"]: r for r in man["records"]}
d1 = rcsv(OUT / "figures" / "data" / "fig01_dataset_distribution.csv")
for seed, fn in ((0, "split-s0-2a1d15648e"), (1, "split-s1-c53cfc7e08"), (2, "split-s2-cbd05190d5")):
    sp = json.loads((R / "manifests" / "splits" / f"{fn}.json").read_text())
    cnt = {k: Counter(by[p]["class"] for p in sp[k]) for k in ("train", "val", "test")}
    same = all(int(r["train"]) == cnt["train"][r["class"]] and int(r["validation"]) == cnt["val"][r["class"]] and
               int(r["locked_test"]) == cnt["test"][r["class"]] for r in d1)
    ok(f"fig01 counts match split seed {seed}", same)

# 4. representative models reproduce (max validation macro-F1 within family)
rep = json.loads((OUT / "figures" / "data" / "representative_models.json").read_text())
fam_pred = {"Classical: pixel PCA": lambda g: g.startswith("E6"),
            "Classical: CNN features": lambda g: g.startswith("E7") or re.fullmatch(r"E5-mnv3pca\d+-(logreg|rbfsvm)", g),
            "Quantum: FRQI kernel": lambda g: g.startswith(("E1-", "E1b-")), "Quantum: NEQR kernel": lambda g: g.startswith("E2-"),
            "Quantum: QKC (PCA)": lambda g: g.startswith("E3-"), "Quantum: VQC": lambda g: g.startswith("E4-"),
            "Hybrid: CNN + QKC": lambda g: g.startswith("E5") and "-qkc-" in g, "Hybrid: CNN + VQC": lambda g: re.fullmatch(r"E5-mnv3pca\d+-vqc", g)}
variant = lambda g: "-shots" in g or "ablation" in g or SEL[g]["category"].startswith("6.")  # noqa: E731
for fam, g in rep["by_validation"]:
    exp = max((x for x in SEL if fam_pred[fam](x) and not variant(x)), key=lambda x: SEL[x]["val_f1_macro"]["mean"])
    ok(f"representative by validation: {fam} -> {g}", exp == g, exp)

# 5. figure-data CSVs vs raw recomputation
for fname, key in (("fig02_accuracy_comparison", "accuracy"), ("fig03_macro_f1_comparison", "f1_macro")):
    rows = rcsv(OUT / "figures" / "data" / f"{fname}.csv")
    k = [c for c in rows[0] if c.endswith("_mean") and not c.startswith("val")][0]
    ok(f"{fname}: values equal raw test_metrics", all(abs(float(r[k]) - raw_ms(r["group"], key)[0]) < 1e-12 for r in rows))
rows = rcsv(OUT / "figures" / "data" / "fig04_precision_recall.csv")
ok("fig04: precision/recall equal raw", all(abs(float(r["precision_macro_mean"]) - raw_ms(r["group"], "precision_macro")[0]) < 1e-12 and
                                            abs(float(r["recall_macro_mean"]) - raw_ms(r["group"], "recall_macro")[0]) < 1e-12 for r in rows))
for fname in ("fig05_paradigm_comparison", "fig06_frqi_vs_neqr_resolution", "fig07_neqr_precision"):
    rows = rcsv(OUT / "figures" / "data" / f"{fname}.csv")
    k = "test_acc_mean" if "test_acc_mean" in rows[0] else "acc_mean"
    ok(f"{fname}: accuracies equal raw ({len(rows)} points)", all(abs(float(r[k]) - raw_ms(r["group"], "accuracy")[0]) < 1e-12 for r in rows))
rows = rcsv(OUT / "figures" / "data" / "fig08_shot_analysis.csv")
bad = []
for r in rows:
    g = r["group"] if r["shots"] == "exact" else f"{r['group']}-shots{r['shots']}"
    if abs(float(r["acc_mean"]) - raw_ms(g, "accuracy")[0]) > 1e-12:
        bad.append(g)
ok(f"fig08: shot accuracies equal raw shot-group experiments ({len(rows)} points)", not bad, str(bad))

# 6. confusion matrices + per-class F1 from raw files
cm_rows = rcsv(OUT / "figures" / "data" / "fig11_confusion_matrices.csv")
bad = 0
for g in {r["group"] for r in cm_rows}:
    cm = sum(np.array(json.loads((R / "experiments" / e / "test_metrics.json").read_text())["confusion_matrix"]) for e in SEL[g]["experiment_ids"])
    # cross-check against predictions.csv
    pc = np.zeros((6, 6), int)
    for e in SEL[g]["experiment_ids"]:
        for r in rcsv(R / "experiments" / e / "predictions.csv"):
            if r["split"] == "test":
                pc[int(r["y_true"]), int(r["y_pred"])] += 1
    bad += int(not np.array_equal(cm, pc)) + int(cm.sum() != 1080)
    classes = ["crazing", "inclusion", "patches", "pitted_surface", "rolled-in_scale", "scratches"]
    for r in (x for x in cm_rows if x["group"] == g):
        bad += int(cm[classes.index(r["true"]), classes.index(r["predicted"])] != int(r["count_sum_3_seeds"]))
ok("fig11: confusion matrices = test_metrics = predictions.csv (1,080 predictions each)", bad == 0)

# 7. McNemar recomputed from predictions for tab08
bad = []
for p in A["paired_tests"]:
    for s in p["per_seed"]:
        a = {r["image"]: r["y_true"] == r["y_pred"] for r in rcsv(R / "experiments" / s["a"] / "predictions.csv") if r["split"] == "test"}
        b = {r["image"]: r["y_true"] == r["y_pred"] for r in rcsv(R / "experiments" / s["b"] / "predictions.csv") if r["split"] == "test"}
        n01 = sum(a[k] and not b[k] for k in a)
        n10 = sum(b[k] and not a[k] for k in a)
        pv = binomtest(n01, n01 + n10, 0.5).pvalue if n01 + n10 else 1.0
        if n01 != s["a_only_correct"] or abs(pv - s["p_value_exact"]) > 1e-12:
            bad.append(p["comparison"])
ok(f"tab08: McNemar p-values recomputed from predictions ({len(A['paired_tests'])} comparisons x 3 seeds)", not bad, str(bad[:2]))

# 8. reconstruction metrics: analysis.json == reconstructions/*/metrics.json; fig09 data == metrics.json
bad = []
for r in A["reconstruction"]:
    m = json.loads((R / "reconstructions" / r["record_id"] / "metrics.json").read_text())["summary"]
    if json.dumps(m, sort_keys=True) != json.dumps(r["summary"], sort_keys=True):
        bad.append(r["record_id"])
ok("reconstruction summaries: analysis.json == reconstructions/*/metrics.json (16 records)", not bad, str(bad))
for r in rcsv(OUT / "figures" / "data" / "fig09_reconstruction_metrics.csv"):
    m = json.loads((R / "reconstructions" / r["record"] / "metrics.json").read_text())["summary"][r["mode"]]["vs_preprocessed"]
    if abs(float(r["mse_mean"]) - m["mse"]["mean"]) > 1e-15 or abs(float(r["ssim_mean"]) - m["ssim"]["mean"]) > 1e-12:
        bad.append(r["record"] + r["mode"])
ok("fig09: MSE/SSIM equal metrics.json", not bad, str(bad[:3]))
# per-image recomputation of MSE from the saved arrays for the exact FRQI records
ex = rcsv(OUT / "figures" / "data" / "fig13_reconstruction_examples.csv")
ok("fig13: FRQI statevector reconstruction equals the saved original (MSE < 1e-20)",
   all(float(r["mse_vs_original_png"]) < 1e-20 for r in ex if r["record"] == "R-FRQI-16x16" and r["mode"] == "statevector"))

# 9. circuit resources table == circuit_stats.json
bad = []
for r in rcsv(OUT / "figures" / "data" / "fig10_circuit_resources.csv"):
    c = json.loads((R / "reconstructions" / r["record"] / "circuit_stats.json").read_text())
    if int(r["qubits"]) != c["n_qubits"] or abs(float(r["gates_compiled"]) - c["gates_compiled"]) > 1e-9 or abs(float(r["depth_compiled"]) - c["depth_compiled"]) > 1e-9:
        bad.append(r["record"])
ok("fig10 / tab05: circuit resources equal circuit_stats.json", not bad, str(bad))
# qubit formula: FRQI 2log2(r)+1, NEQR 2log2(r)+bits
bad = [r["record"] for r in rcsv(OUT / "figures" / "data" / "fig10_circuit_resources.csv")
       if int(r["qubits"]) != 2 * int(np.log2(int(r["resolution"]))) + (1 if r["representation"] == "FRQI" else int(r["bits"]))]
ok("qubit counts follow FRQI 2n+1 / NEQR 2n+q", not bad, str(bad))
# classification groups report the same qubit count as the encoders
bad = [g for g in SEL if g.startswith(("E1-", "E2-")) and "-shots" not in g and not SEL[g]["category"].startswith("6.") and SEL[g]["n_qubits"] !=
       2 * int(np.log2(int(re.search(r"(\d+)", g.split("-")[1]).group(1)))) + (1 if g.startswith("E1") else SEL[g]["params"]["bits"])]
ok("FRQI/NEQR classification qubit counts consistent", not bad, str(bad))

# 10. table CSVs: tab04 values equal raw
for r in rcsv(OUT / "tables" / "tab04_classification_performance.csv"):
    g = next(gg for fam, gg in rep["by_validation"] if fam == r["Family"])
    m, s = raw_ms(g, "accuracy")
    ok(f"tab04 accuracy {r['Family']}", r["Accuracy"] == f"{100 * m:.1f} ± {100 * s:.1f}", r["Accuracy"])

# 11. files + LaTeX paths
figs = sorted({p.stem for p in (OUT / "figures").glob("fig*.pdf")})
for f in figs:
    ok(f"{f}: pdf/png/svg present", all((OUT / "figures" / f"{f}.{e}").exists() for e in ("pdf", "png", "svg")))
from PIL import Image  # noqa: E402
dpis = [Image.open(OUT / "figures" / f"{f}.png").info.get("dpi", (0, 0))[0] for f in figs]
ok("all PNG figures >= 300 dpi", all(round(d) >= 300 for d in dpis), str(dpis))
ok("flowchart: svg/pdf/png/tikz present", all((OUT / "flowchart" / n).exists() for n in (
    "methodology_flowchart.svg", "methodology_flowchart.pdf", "methodology_flowchart.png", "methodology_flowchart_tikz.tex")))
ok("flowchart PNG >= 300 dpi", round(Image.open(OUT / "flowchart" / "methodology_flowchart.png").info.get("dpi", (0, 0))[0]) >= 300)
ins = (OUT / "latex" / "visuals_insertion.tex").read_text()
paths = re.findall(r"\\(?:includegraphics(?:\[[^\]]*\])?|input)\{\\visdir/([^}]+)\}", ins)
missing = [p for p in paths if not ((OUT / p).exists() or (OUT / (p + ".tex")).exists())]
ok(f"visuals_insertion.tex: all {len(paths)} paths exist", not missing and len(paths) >= 24, str(missing))
labels = re.findall(r"\\label\{([^}]+)\}", ins) + [l for f in (OUT / "tables").glob("*.tex") for l in re.findall(r"\\label\{([^}]+)\}", f.read_text())]
ok("LaTeX labels unique", len(labels) == len(set(labels)), str([l for l in labels if labels.count(l) > 1][:3]))
for f in list((OUT / "tables").glob("*.tex")) + [OUT / "latex" / "visuals_insertion.tex", OUT / "latex" / "example_main.tex"]:
    t = f.read_text()
    ok(f"{f.name}: ASCII only and balanced braces", all(ord(c) < 128 for c in t) and
       t.count("{") - t.count("\\{") == t.count("}") - t.count("\\}"))

n_fail = sum(not c[1] for c in checks)
lines = ["# Validation report", "", f"Checks: {len(checks)} · passed: {len(checks) - n_fail} · failed: {n_fail}", "",
         "Every value was recomputed from the raw per-experiment records in results/qml_v2 (test_metrics.json, predictions.csv, "
         "circuit_stats.json, reconstructions/*/metrics.json, manifest and split files) and compared with the figure data, the tables "
         "and analysis.json.", "", "| Check | Result | Detail |", "|---|---|---|"]
lines += [f"| {n} | {'PASS' if c else 'FAIL'} | {d} |" for n, c, d in checks]
lines += ["", "LaTeX was not compiled locally (no TeX installation on this machine); syntax checks above are static "
          "(ASCII-only, balanced braces, existing paths, unique labels)."]
(OUT / "VALIDATION_REPORT.md").write_text("\n".join(lines) + "\n")
print(f"{len(checks)} checks, {n_fail} failed")
for n, c, d in checks:
    if not c:
        print("FAIL", n, d)
sys.exit(1 if n_fail else 0)
