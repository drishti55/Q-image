"""
Generate every figure and table in research_paper_visuals/ from the saved Protocol V2 records (read-only):
  results/qml_v2/aggregates/analysis.json, results/qml_v2/aggregates/selection/*.json,
  results/qml_v2/manifests/dataset_manifest_*.json, results/qml_v2/manifests/splits/*.json,
  results/qml_v2/experiments/<id>/{test_metrics.json, circuit_stats.json},
  results/qml_v2/reconstructions/<id>/{metrics.json, circuit_stats.json, config.json, reconstructions.npz, images/}.
No value is typed by hand. Representative models are chosen by VALIDATION macro-F1 inside each family (never by test).
Usage:  python research_paper_visuals/source/make_visuals.py
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
PROJ = OUT.parent
R = PROJ / "results" / "qml_v2"
FIG, TAB, DATA = OUT / "figures", OUT / "tables", OUT / "figures" / "data"
for d in (FIG, TAB, DATA):
    d.mkdir(parents=True, exist_ok=True)

A = json.loads((R / "aggregates" / "analysis.json").read_text())
SEL = A["selected"]
CLASSES = ["crazing", "inclusion", "patches", "pitted_surface", "rolled-in_scale", "scratches"]
CLS_LABEL = ["Crazing", "Inclusion", "Patches", "Pitted surface", "Rolled-in scale", "Scratches"]

# ── style: validated colour-blind-safe palette (light / print) ──
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, VIOLET = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"
PARADIGM_COLOR = {"Classical": BLUE, "Quantum (simulated)": AQUA, "Hybrid": ORANGE}
INK, MUTED, GRID = "#1a1a1a", "#555555", "#dddddd"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8.5, "axes.titlesize": 9, "axes.labelsize": 8.5, "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5, "legend.fontsize": 7.5, "axes.edgecolor": "#888888", "axes.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5,
    "axes.axisbelow": True, "savefig.bbox": "tight", "savefig.pad_inches": 0.03, "pdf.fonttype": 42, "svg.fonttype": "none",
    "legend.frameon": False, "lines.linewidth": 1.6, "lines.markersize": 4.5,
})
W = 6.3  # single-column text width (inches)


def save(fig, name):
    for ext, kw in (("pdf", {}), ("svg", {}), ("png", {"dpi": 300})):
        fig.savefig(FIG / f"{name}.{ext}", **kw)
    plt.close(fig)


def write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


# ── naming / families (derived from group identifiers) ──
MAP = {"product_ry": "product-RY", "zz_linear": "ZZ-linear", "zz_full": "ZZ-full"}


def nice(g: str) -> str:
    s = SEL[g]
    shots = re.search(r"-shots(\d+)$", g)
    sh = f", {int(shots.group(1)):,} shots" if shots else ""
    base = re.sub(r"-shots\d+$", "", g)
    if m := re.fullmatch(r"E1-frqi(\d+)-qkc", base):
        return f"FRQI {m[1]}×{m[1]}{sh}"
    if m := re.fullmatch(r"E1b-frqi(\d+)-qkc-scaled", base):
        return f"FRQI {m[1]}×{m[1]} (angle ×{s['params']['angle_scale']:g}){sh}"
    if m := re.fullmatch(r"E2-neqr(\d+)-b(\d+)-qkc", base):
        return f"NEQR {m[1]}×{m[1]}, {m[2]}-bit{sh}"
    if m := re.fullmatch(r"E3-pca(\d+)-qkc-(\w+)", base):
        return f"QKC {MAP[m[2]]}, {m[1]} qubits{sh}"
    if m := re.fullmatch(r"E4-pca(\d+)-vqc", base):
        return f"VQC, {m[1]} qubits"
    if m := re.fullmatch(r"E4-pca(\d+)-vqc-ablation-frozen", base):
        return f"VQC frozen circuit (ablation), {m[1]} qubits"
    if m := re.fullmatch(r"E5-mnv3pca(\d+)-qkc-(\w+)", base):
        return f"MobileNetV3-PCA{m[1]} + QKC {MAP[m[2]]}"
    if m := re.fullmatch(r"E5-mnv3pca(\d+)-vqc", base):
        return f"MobileNetV3-PCA{m[1]} + VQC"
    if m := re.fullmatch(r"E5-mnv3pca(\d+)-(logreg|rbfsvm)", base):
        return f"MobileNetV3-PCA{m[1]} + {'LogReg' if m[2] == 'logreg' else 'RBF-SVM'}"
    if m := re.fullmatch(r"E6-pca(\d+)-(logreg|rbfsvm)(-angle)?", base):
        return f"Pixel PCA-{m[1]} + {'LogReg' if m[2] == 'logreg' else 'RBF-SVM'}{' (angle features)' if m[3] else ''}"
    return {"E7-smallcnn": "Small CNN (from scratch)", "E7-mnv3-logreg": "MobileNetV3 + LogReg",
            "E7-mnv3-rbfsvm": "MobileNetV3 + RBF-SVM"}.get(g, s["model_name"] + " [legacy, classical]")


def paradigm(g):
    if g.startswith(("E1", "E2", "E3", "E4")):
        return "Quantum (simulated)"
    if g.startswith("E5") and ("-qkc-" in g or g.endswith("-vqc")):
        return "Hybrid"
    return "Classical"


def is_variant(g):
    return "-shots" in g or "ablation" in g or SEL[g]["category"].startswith("6.")


def mean(g, k):
    return SEL[g][k]["mean"]


def sd(g, k):
    return SEL[g][k]["std"] or 0.0


FAMILIES = [
    ("Classical: pixel PCA", lambda g: g.startswith("E6")),
    ("Classical: CNN features", lambda g: g.startswith("E7") or re.fullmatch(r"E5-mnv3pca\d+-(logreg|rbfsvm)", g) is not None),
    ("Quantum: FRQI kernel", lambda g: g.startswith(("E1-", "E1b-"))),
    ("Quantum: NEQR kernel", lambda g: g.startswith("E2-")),
    ("Quantum: QKC (PCA)", lambda g: g.startswith("E3-")),
    ("Quantum: VQC", lambda g: g.startswith("E4-")),
    ("Hybrid: CNN + QKC", lambda g: g.startswith("E5") and "-qkc-" in g),
    ("Hybrid: CNN + VQC", lambda g: re.fullmatch(r"E5-mnv3pca\d+-vqc", g) is not None),
]


def best_by_val(pred):
    cands = [g for g in SEL if pred(g) and not is_variant(g)]
    return max(cands, key=lambda g: mean(g, "val_f1_macro"))


REP = [(fam, best_by_val(p)) for fam, p in FAMILIES]


def test_metrics(eid):
    return json.loads((R / "experiments" / eid / "test_metrics.json").read_text())


def circuit(g):
    p = R / "experiments" / SEL[g]["experiment_ids"][0] / "circuit_stats.json"
    return json.loads(p.read_text()) if p.exists() else None


def pct(v, d=1):
    return f"{100 * v:.{d}f}"


def pm(g, k, d=1):
    return f"{pct(mean(g, k), d)} ± {pct(sd(g, k), d)}"


# ═════════════════════════════ FIGURES ═════════════════════════════
def fig_dataset():
    man = json.loads((R / "manifests" / "dataset_manifest_neu-5625b937479b.json").read_text())
    split = json.loads((R / "manifests" / "splits" / "split-s0-2a1d15648e.json").read_text())
    by = {p: r for r in man["records"] for p in [r["rel_path"]]}
    cnt = {k: Counter(by[p]["class"] for p in split[k]) for k in ("train", "val", "test")}
    rows = [[c, cnt["train"][c], cnt["val"][c], cnt["test"][c]] for c in CLASSES]
    write_csv(DATA / "fig01_dataset_distribution.csv", ["class", "train", "validation", "locked_test"], rows)
    fig, ax = plt.subplots(figsize=(W, 2.4))
    x = np.arange(6)
    bottom = np.zeros(6)
    for i, (k, lab, col) in enumerate((("train", "Train (internal)", BLUE), ("val", "Validation (internal)", ORANGE), ("test", "Locked test", AQUA))):
        v = np.array([cnt[k][c] for c in CLASSES])
        ax.bar(x, v, 0.6, bottom=bottom, color=col, label=lab, edgecolor="white", linewidth=1)
        for xi, (b, vi) in enumerate(zip(bottom, v)):
            ax.text(xi, b + vi / 2, str(vi), ha="center", va="center", fontsize=7, color="white" if col != AQUA else INK)
        bottom += v
    ax.set_xticks(x, CLS_LABEL)
    ax.set_ylabel("Images")
    ax.set_ylim(0, 330)
    ax.grid(axis="x", visible=False)
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.13))
    save(fig, "fig01_dataset_distribution")
    return rows


def hbar_metric(key, name, fname, xlabel):
    rows = [(fam, g, mean(g, key), sd(g, key)) for fam, g in REP]
    rows.sort(key=lambda r: r[2])
    write_csv(DATA / f"{fname}.csv", ["family", "group", "model", f"{key}_mean", f"{key}_std", "val_f1_macro_mean"],
              [[f, g, nice(g), m, s, mean(g, "val_f1_macro")] for f, g, m, s in rows])
    fig, ax = plt.subplots(figsize=(W, 3.2))
    y = np.arange(len(rows))
    cols = [PARADIGM_COLOR[paradigm(g)] for _, g, _, _ in rows]
    ax.barh(y, [100 * r[2] for r in rows], xerr=[100 * r[3] for r in rows], color=cols, height=0.62,
            error_kw={"elinewidth": 0.8, "capsize": 2, "ecolor": INK})
    for yi, r in zip(y, rows):
        ax.text(100 * (r[2] + r[3]) + 1.2, yi, f"{100 * r[2]:.1f}%", va="center", fontsize=7.5, color=INK)
    ax.set_yticks(y, [f"{nice(g)}\n{f}" for f, g, _, _ in rows], fontsize=7)
    ax.set_xlim(0, 108)
    ax.set_xlabel(xlabel)
    ax.grid(axis="y", visible=False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in PARADIGM_COLOR.values()]
    ax.legend(handles, list(PARADIGM_COLOR), ncol=3, loc="lower right", bbox_to_anchor=(1.0, 1.0))
    save(fig, fname)


def fig_precision_recall():
    rows = [(fam, g) for fam, g in REP]
    write_csv(DATA / "fig04_precision_recall.csv", ["family", "group", "model", "precision_macro_mean", "precision_macro_std",
                                                     "recall_macro_mean", "recall_macro_std"],
              [[f, g, nice(g), mean(g, "test_precision_macro"), sd(g, "test_precision_macro"), mean(g, "test_recall_macro"),
                sd(g, "test_recall_macro")] for f, g in rows])
    fig, ax = plt.subplots(figsize=(W, 2.9))
    x = np.arange(len(rows))
    for off, k, lab, col, hatch in ((-0.19, "test_precision_macro", "Macro precision", BLUE, ""),
                                    (0.19, "test_recall_macro", "Macro recall", ORANGE, "///")):
        ax.bar(x + off, [100 * mean(g, k) for _, g in rows], 0.36, yerr=[100 * sd(g, k) for _, g in rows], color=col, label=lab,
               hatch=hatch, edgecolor="white", linewidth=0.6, error_kw={"elinewidth": 0.8, "capsize": 2})
    short = {"Classical: pixel PCA": "Classical\npixel PCA", "Classical: CNN features": "Classical\nCNN feat.",
             "Quantum: FRQI kernel": "Quantum\nFRQI", "Quantum: NEQR kernel": "Quantum\nNEQR", "Quantum: QKC (PCA)": "Quantum\nQKC (PCA)",
             "Quantum: VQC": "Quantum\nVQC", "Hybrid: CNN + QKC": "Hybrid\nCNN+QKC", "Hybrid: CNN + VQC": "Hybrid\nCNN+VQC"}
    ax.set_xticks(x, [short[f] for f, _ in rows], fontsize=6.8)
    ax.set_ylabel("Locked-test score (%)")
    ax.set_ylim(0, 105)
    ax.grid(axis="x", visible=False)
    ax.legend(ncol=2, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    save(fig, "fig04_precision_recall")


def fig_paradigms():
    """Matched-feature comparison for k = 4, 6, 8: representation × classifier paradigm."""
    groups = [("Pixel PCA + RBF-SVM\n(classical)", lambda k: f"E6-pca{k}-rbfsvm-angle", BLUE, ""),
              ("Pixel PCA + best QKC\n(quantum, by validation)", lambda k: max([f"E3-pca{k}-qkc-{m}" for m in MAP], key=lambda g: mean(g, "val_f1_macro")), AQUA, "//"),
              ("CNN-PCA + best classical\n(by validation)", lambda k: max([f"E5-mnv3pca{k}-logreg", f"E5-mnv3pca{k}-rbfsvm"], key=lambda g: mean(g, "val_f1_macro")), BLUE, "xx"),
              ("CNN-PCA + best quantum\n(hybrid, by validation)", lambda k: max([f"E5-mnv3pca{k}-qkc-{m}" for m in MAP] + [f"E5-mnv3pca{k}-vqc"], key=lambda g: mean(g, "val_f1_macro")), ORANGE, "")]
    ks = [4, 6, 8]
    data = [[(lab, k, fn(k)) for k in ks] for lab, fn, _, _ in groups]
    write_csv(DATA / "fig05_paradigm_comparison.csv", ["setting", "k", "group", "model", "test_acc_mean", "test_acc_std"],
              [[lab.replace("\n", " "), k, g, nice(g), mean(g, "test_accuracy"), sd(g, "test_accuracy")] for row in data for lab, k, g in row])
    fig, ax = plt.subplots(figsize=(W, 2.9))
    x = np.arange(len(ks))
    wdt = 0.2
    for i, ((lab, _, col, hatch), row) in enumerate(zip(groups, data)):
        v = [100 * mean(g, "test_accuracy") for _, _, g in row]
        e = [100 * sd(g, "test_accuracy") for _, _, g in row]
        ax.bar(x + (i - 1.5) * wdt, v, wdt * 0.92, yerr=e, color=col, hatch=hatch, edgecolor="white", linewidth=0.6, label=lab,
               error_kw={"elinewidth": 0.8, "capsize": 1.5})
        for xi, vi, ei in zip(x + (i - 1.5) * wdt, v, e):
            ax.text(xi, vi + ei + 1.5, f"{vi:.0f}", ha="center", fontsize=6.5)
    ax.set_xticks(x, [f"k = {k} features / qubits" for k in ks])
    ax.set_ylabel("Locked-test accuracy (%)")
    ax.set_ylim(0, 108)
    ax.grid(axis="x", visible=False)
    ax.legend(ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.28), fontsize=7)
    save(fig, "fig05_paradigm_comparison")


RES = [2, 4, 8, 16]


def fig_frqi_neqr_resolution():
    series = [("FRQI (original, θ = πI/2)", lambda r: f"E1-frqi{r}-qkc", BLUE, "o", "-"),
              ("FRQI (angle-scaled, by validation)", lambda r: f"E1b-frqi{r}-qkc-scaled" if f"E1b-frqi{r}-qkc-scaled" in SEL else None, BLUE, "s", "--"),
              ("NEQR 2-bit", lambda r: f"E2-neqr{r}-b2-qkc", ORANGE, "v", ":"),
              ("NEQR 4-bit", lambda r: f"E2-neqr{r}-b4-qkc", ORANGE, "o", "-"),
              ("NEQR 8-bit", lambda r: f"E2-neqr{r}-b8-qkc", ORANGE, "^", "--")]
    rows = []
    fig, axs = plt.subplots(1, 2, figsize=(W, 2.6), sharey=True)
    for ax, key, title in ((axs[0], "test_accuracy", "(a) Accuracy"), (axs[1], "test_f1_macro", "(b) Macro-F1")):
        for lab, fn, col, mk, ls in series:
            pts = [(r, fn(r)) for r in RES if fn(r)]
            ax.errorbar([np.log2(r) for r, _ in pts], [100 * mean(g, key) for _, g in pts], yerr=[100 * sd(g, key) for _, g in pts],
                        color=col, marker=mk, ls=ls, capsize=2, label=lab, elinewidth=0.8)
            if key == "test_accuracy":
                rows += [[lab, r, g, mean(g, "test_accuracy"), sd(g, "test_accuracy"), mean(g, "test_f1_macro"), sd(g, "test_f1_macro"), SEL[g]["n_qubits"]] for r, g in pts]
        ax.set_xticks([1, 2, 3, 4], ["2×2", "4×4", "8×8", "16×16"])
        ax.set_xlabel("Image resolution")
        ax.set_title(title, loc="left")
    axs[0].set_ylabel("Locked-test score (%)")
    axs[0].set_ylim(20, 70)
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, fontsize=6.8, bbox_to_anchor=(0.5, -0.13))
    write_csv(DATA / "fig06_frqi_vs_neqr_resolution.csv", ["series", "resolution", "group", "acc_mean", "acc_std", "f1_mean", "f1_std", "n_qubits"], rows)
    save(fig, "fig06_frqi_vs_neqr_resolution")


def fig_neqr_precision():
    rows = []
    fig, ax = plt.subplots(figsize=(W * 0.62, 2.5))
    cols = {2: YELLOW, 4: BLUE, 8: ORANGE, 16: AQUA}
    mks = {2: "v", 4: "o", 8: "s", 16: "^"}
    for r in RES:
        gs = [(b, f"E2-neqr{r}-b{b}-qkc") for b in (2, 4, 8)]
        ax.errorbar([b for b, _ in gs], [100 * mean(g, "test_accuracy") for _, g in gs], yerr=[100 * sd(g, "test_accuracy") for _, g in gs],
                    color=cols[r], marker=mks[r], capsize=2, label=f"{r}×{r}", elinewidth=0.8)
        ax.annotate(f"{r}×{r}", (8, 100 * mean(gs[-1][1], "test_accuracy")), xytext=(5, 0), textcoords="offset points", va="center", fontsize=7)
        rows += [[r, b, g, mean(g, "test_accuracy"), sd(g, "test_accuracy"), mean(g, "test_f1_macro"), SEL[g]["n_qubits"]] for b, g in gs]
    ax.set_xscale("log", base=2)
    ax.set_xticks([2, 4, 8], ["2-bit", "4-bit", "8-bit"])
    ax.set_xlim(1.7, 11)
    ax.set_xlabel("NEQR intensity precision")
    ax.set_ylabel("Locked-test accuracy (%)")
    ax.legend(title="Resolution", fontsize=6.8, title_fontsize=7, loc="upper left", bbox_to_anchor=(1.12, 1.0))
    write_csv(DATA / "fig07_neqr_precision.csv", ["resolution", "bits", "group", "acc_mean", "acc_std", "f1_mean", "n_qubits"], rows)
    save(fig, "fig07_neqr_precision")


def fig_shots():
    ss = A["shot_sensitivity"]
    rows = []
    fig, axs = plt.subplots(1, 2, figsize=(W, 2.6), sharey=True)
    panels = [(axs[0], "(a) FRQI vs NEQR kernels, 8×8", [("E1-frqi8-qkc", "FRQI 8×8", BLUE, "o"), ("E2-neqr8-b4-qkc", "NEQR 8×8, 4-bit", ORANGE, "s")]),
              (axs[1], "(b) Quantum kernels on PCA features (ZZ-full)", [("E3-pca4-qkc-zz_full", "4 qubits", AQUA, "o"), ("E3-pca6-qkc-zz_full", "6 qubits", BLUE, "s"), ("E3-pca8-qkc-zz_full", "8 qubits", ORANGE, "^")])]
    xmax = 2e5
    for ax, title, ser in panels:
        for g, lab, col, mk in ser:
            d = ss[g]
            pts = sorted((int(k), v) for k, v in d.items() if k.isdigit() and int(k) > 0)  # "0" = exact kernel, plotted as "exact"
            xs = [p[0] for p in pts] + [xmax]
            ys = [100 * p[1]["test_accuracy"]["mean"] for p in pts] + [100 * mean(g, "test_accuracy")]
            es = [100 * (p[1]["test_accuracy"]["std"] or 0) for p in pts] + [100 * sd(g, "test_accuracy")]
            ax.errorbar(xs, ys, yerr=es, color=col, marker=mk, capsize=2, label=lab, elinewidth=0.8)
            rows += [[g, lab, s, v["test_accuracy"]["mean"], v["test_accuracy"]["std"], v["test_f1_macro"]["mean"]] for s, v in pts]
            rows.append([g, lab, "exact", mean(g, "test_accuracy"), sd(g, "test_accuracy"), mean(g, "test_f1_macro")])
        ax.set_xscale("log")
        ax.set_xticks([100, 1000, 10000, xmax], ["10²", "10³", "10⁴", "exact"])
        ax.set_xlabel("Measurement shots per kernel entry")
        ax.set_title(title, loc="left")
        ax.legend(fontsize=6.8, loc="lower right")
    axs[0].set_ylabel("Locked-test accuracy (%)")
    write_csv(DATA / "fig08_shot_analysis.csv", ["group", "label", "shots", "acc_mean", "acc_std", "f1_mean"], rows)
    save(fig, "fig08_shot_analysis")


def recon_records():
    return {r["record_id"]: r for r in A["reconstruction"]}


SHOT_KEYS = ["shots100", "shots1000", "shots10000", "shots100000"]


def fig_reconstruction_metrics():
    rec = recon_records()
    series = [("R-FRQI-8x8", "FRQI 8×8", BLUE, "o", "-"), ("R-FRQI-16x16", "FRQI 16×16", BLUE, "s", "--"),
              ("R-NEQR-8x8-b4", "NEQR 8×8, 4-bit", ORANGE, "o", "-"), ("R-NEQR-16x16-b4", "NEQR 16×16, 4-bit", ORANGE, "s", "--")]
    rows = []
    fig, axs = plt.subplots(1, 3, figsize=(W, 2.3))
    xs = [1e2, 1e3, 1e4, 1e5]
    for rid, lab, col, mk, ls in series:
        s = rec[rid]["summary"]
        for ax, met in zip(axs, ("mse", "psnr", "ssim")):
            ys = [s[k]["vs_preprocessed"][met]["mean"] for k in SHOT_KEYS]
            ax.plot(xs, ys, color=col, marker=mk, ls=ls, label=lab)
        for k in SHOT_KEYS + ["statevector"]:
            v = s[k]["vs_preprocessed"]
            rows.append([rid, k, v["mse"]["mean"], v["psnr"]["mean"], v["psnr"].get("n_exact"), v["ssim"]["mean"]])
    for ax, t in zip(axs, ("(a) MSE ↓", "(b) PSNR (dB) ↑", "(c) SSIM ↑")):
        ax.set_xscale("log")
        ax.set_xticks(xs, ["10²", "10³", "10⁴", "10⁵"])
        ax.set_xlabel("Shots")
        ax.set_title(t, loc="left")
    axs[0].set_yscale("log")
    axs[2].set_ylim(0, 1.02)
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, fontsize=6.8, bbox_to_anchor=(0.5, -0.1))
    fig.tight_layout()
    write_csv(DATA / "fig09_reconstruction_metrics.csv", ["record", "mode", "mse_mean", "psnr_mean_db", "psnr_n_exact", "ssim_mean"], rows)
    save(fig, "fig09_reconstruction_metrics")


def recon_resources():
    out = []
    for rid in sorted(recon_records(), key=lambda s: (s.split("-")[1], int(s.split("-")[2].split("x")[0]), s)):
        c = json.loads((R / "reconstructions" / rid / "circuit_stats.json").read_text())
        rep, res = rid.split("-")[1], int(rid.split("-")[2].split("x")[0])
        bits = int(rid.split("-b")[-1]) if rep == "NEQR" else None
        out.append({"record": rid, "rep": rep, "res": res, "bits": bits, **{k: c.get(k) for k in (
            "n_qubits", "gates_logical", "depth_logical", "gates_compiled", "depth_compiled", "cx_compiled")},
            "gates_compiled_range": c.get("gates_compiled_range"), "n_sample_images": c.get("n_sample_images")})
    return out


def fig_circuits():
    rows = recon_resources()
    write_csv(DATA / "fig10_circuit_resources.csv", ["record", "representation", "resolution", "bits", "qubits", "gates_logical", "depth_logical",
                                                     "gates_compiled", "depth_compiled", "cx_compiled", "gates_compiled_range", "n_sample_images"],
              [[r["record"], r["rep"], r["res"], r["bits"], r["n_qubits"], r["gates_logical"], r["depth_logical"], r["gates_compiled"],
                r["depth_compiled"], r["cx_compiled"], r["gates_compiled_range"], r["n_sample_images"]] for r in rows])
    fig, axs = plt.subplots(1, 3, figsize=(W, 2.3))
    ser = [("FRQI", None, BLUE, "o", "-"), ("NEQR", 2, ORANGE, "v", ":"), ("NEQR", 4, ORANGE, "o", "-"), ("NEQR", 8, ORANGE, "^", "--")]
    for rep, b, col, mk, ls in ser:
        pts = sorted((r for r in rows if r["rep"] == rep and r["bits"] == b), key=lambda r: r["res"])
        x = [np.log2(r["res"]) for r in pts]
        lab = "FRQI" if rep == "FRQI" else f"NEQR {b}-bit"
        axs[0].plot(x, [r["n_qubits"] for r in pts], color=col, marker=mk, ls=ls, label=lab)
        axs[1].plot(x, [r["gates_compiled"] for r in pts], color=col, marker=mk, ls=ls, label=lab)
        axs[2].plot(x, [r["depth_compiled"] for r in pts], color=col, marker=mk, ls=ls, label=lab)
    for ax, t in zip(axs, ("(a) Qubits", "(b) Compiled gates", "(c) Compiled depth")):
        ax.set_xticks([1, 2, 3, 4], ["2×2", "4×4", "8×8", "16×16"])
        ax.set_xlabel("Image resolution")
        ax.set_title(t, loc="left")
    axs[1].set_yscale("log")
    axs[2].set_yscale("log")
    axs[0].legend(fontsize=6.5)
    fig.tight_layout()
    save(fig, "fig10_circuit_resources")
    return rows


CM_MODELS = [REP[0], REP[1], REP[2], REP[3], REP[4], REP[6]]


def fig_confusion():
    fig, axs = plt.subplots(2, 3, figsize=(W, 4.6))
    rows = []
    for ax, (fam, g) in zip(axs.flat, CM_MODELS):
        cm = np.zeros((6, 6))
        for eid in SEL[g]["experiment_ids"]:
            cm += np.array(test_metrics(eid)["confusion_matrix"])
        norm = cm / cm.sum(1, keepdims=True)
        ax.imshow(norm, cmap="Blues", vmin=0, vmax=1)
        for i in range(6):
            for j in range(6):
                ax.text(j, i, f"{100 * norm[i, j]:.0f}", ha="center", va="center", fontsize=6, color="white" if norm[i, j] > 0.55 else INK)
        ax.set_xticks(range(6), ["Cr", "In", "Pa", "PS", "RS", "Sc"], fontsize=6.5)
        ax.set_yticks(range(6), ["Cr", "In", "Pa", "PS", "RS", "Sc"], fontsize=6.5)
        ax.grid(False)
        ax.set_title(f"{fam}\n{nice(g)}", fontsize=6.8)
        rows += [[fam, g, CLASSES[i], CLASSES[j], int(cm[i, j]), norm[i, j]] for i in range(6) for j in range(6)]
    for ax in axs[1]:
        ax.set_xlabel("Predicted")
    for ax in axs[:, 0]:
        ax.set_ylabel("True")
    fig.text(0.5, -0.02, "Cr crazing · In inclusion · Pa patches · PS pitted surface · RS rolled-in scale · Sc scratches. "
             "Row-normalised (%), counts summed over seeds 0–2 (3 × 360 test predictions).", ha="center", fontsize=6.5, color=MUTED)
    fig.tight_layout()
    write_csv(DATA / "fig11_confusion_matrices.csv", ["family", "group", "true", "predicted", "count_sum_3_seeds", "row_fraction"], rows)
    save(fig, "fig11_confusion_matrices")


def fig_per_class():
    rows = []
    fig, ax = plt.subplots(figsize=(W, 2.7))
    x = np.arange(6)
    sel = CM_MODELS
    cols = [BLUE, ORANGE, AQUA, YELLOW, MAGENTA, VIOLET]  # validated adjacent order
    w = 0.13
    for i, ((fam, g), col) in enumerate(zip(sel, cols)):
        f1 = np.array([[test_metrics(e)["per_class"][c]["f1"] for c in CLASSES] for e in SEL[g]["experiment_ids"]])
        ax.bar(x + (i - 2.5) * w, 100 * f1.mean(0), w * 0.9, color=col, label=f"{fam}", edgecolor="white", linewidth=0.4)
        for xi, v in zip(x + (i - 2.5) * w, 100 * f1.mean(0)):
            if v < 0.5:
                ax.text(xi, 1.5, "0", ha="center", fontsize=6, color=INK)
        rows += [[fam, g, c, f1[:, j].mean(), f1[:, j].std(ddof=1)] for j, c in enumerate(CLASSES)]
    ax.set_xticks(x, CLS_LABEL)
    ax.set_ylabel("Per-class F1 (%)")
    ax.set_ylim(0, 105)
    ax.grid(axis="x", visible=False)
    ax.legend(ncol=3, fontsize=6.5, loc="upper center", bbox_to_anchor=(0.5, 1.22))
    write_csv(DATA / "fig12_per_class_f1.csv", ["family", "group", "class", "f1_mean", "f1_std"], rows)
    save(fig, "fig12_per_class_f1")


def load_original(rid, idx, cls, res):
    p = R / "reconstructions" / rid / "images" / f"{idx:02d}_{cls}_original.png"
    im = np.asarray(Image.open(p), dtype=float) / 255.0
    f = im.shape[0] // res
    return im[::f, ::f]


def fig_recon_examples():
    """Original (preprocessed) vs reconstructed images from the saved arrays."""
    cfg = json.loads((R / "reconstructions" / "R-FRQI-16x16" / "config.json").read_text())
    picks = [0, 12, 24]  # first image of crazing, patches, rolled-in scale (saved order: 5 per class)
    cols = [("Original\n16×16", None, None), ("FRQI\nstatevector", "R-FRQI-16x16", "statevector"),
            ("FRQI\n10⁴ shots", "R-FRQI-16x16", "shots10000"), ("FRQI\n10⁵ shots", "R-FRQI-16x16", "shots100000"),
            ("NEQR 4-bit\nstatevector", "R-NEQR-16x16-b4", "statevector"), ("NEQR 2-bit\nstatevector", "R-NEQR-16x16-b2", "statevector")]
    npz = {rid: np.load(R / "reconstructions" / rid / "reconstructions.npz") for rid in ("R-FRQI-16x16", "R-NEQR-16x16-b4", "R-NEQR-16x16-b2")}
    fig, axs = plt.subplots(len(picks), len(cols), figsize=(W, W * len(picks) / len(cols) * 1.08))
    checks = []
    for i, idx in enumerate(picks):
        img_path = cfg["images"][idx]
        cls = img_path.split("/")[-2]
        orig = load_original("R-FRQI-16x16", idx, cls, 16)
        for j, (title, rid, mode) in enumerate(cols):
            a = orig if rid is None else npz[rid][f"{idx}__{mode}"]
            ax = axs[i, j]
            ax.imshow(a, cmap="gray", vmin=0, vmax=1, interpolation="nearest")
            ax.set_xticks([])
            ax.set_yticks([])
            ax.grid(False)
            for s in ax.spines.values():
                s.set_visible(False)
            if i == 0:
                ax.set_title(title, fontsize=7)
            if j == 0:
                ax.set_ylabel(CLS_LABEL[CLASSES.index(cls)], fontsize=7)
            if rid:
                checks.append([img_path, rid, mode, float(np.mean((a - orig) ** 2))])
    fig.subplots_adjust(wspace=0.05, hspace=0.08)
    write_csv(DATA / "fig13_reconstruction_examples.csv", ["image", "record", "mode", "mse_vs_original_png"], checks)
    save(fig, "fig13_reconstruction_examples")


def fig_kernel_concentration():
    kc = A["kernel_concentration"]
    rows = []
    fig, axs = plt.subplots(1, 2, figsize=(W, 2.4))
    for k, col, mk in ((4, AQUA, "o"), (6, BLUE, "s"), (8, ORANGE, "^")):
        keys = sorted([key for key in kc if key.startswith(f"k={k}|zz_full|reps=1|")], key=lambda s: float(s.split("bw=")[1]))
        bw = [float(s.split("bw=")[1]) for s in keys]
        axs[0].plot(bw, [kc[s]["offdiag_mean"]["mean"] for s in keys], color=col, marker=mk, label=f"{k} qubits")
        axs[1].plot(bw, [100 * kc[s]["val_f1"]["mean"] for s in keys], color=col, marker=mk, label=f"{k} qubits")
        rows += [[k, b, kc[s]["offdiag_mean"]["mean"], kc[s]["cka"]["mean"], kc[s]["val_f1"]["mean"]] for b, s in zip(bw, keys)]
    for ax in axs:
        ax.set_xscale("log")
        ax.set_xlabel("Feature-map bandwidth")
    axs[0].set_title("(a) Mean off-diagonal kernel value", loc="left")
    axs[1].set_title("(b) Validation macro-F1 (%)", loc="left")
    axs[1].text(0.02, 0.02, "mean over C ∈ {0.1, 1, 10, 100} and seeds 0–2", transform=axs[1].transAxes, fontsize=6.3, color=MUTED)
    axs[0].legend(fontsize=6.8)
    write_csv(DATA / "fig14_kernel_concentration.csv", ["qubits", "bandwidth", "offdiag_mean", "cka", "val_f1_macro"], rows)
    save(fig, "fig14_kernel_concentration")


# ═════════════════════════════ TABLES ═════════════════════════════
UNI = {"×": r"$\times$", "±": r"$\pm$", "θ": r"$\theta$", "π": r"$\pi$", "→": r"$\rightarrow$", "γ": r"$\gamma$",
       "≥": r"$\geq$", "—": "---", "–": "--", "−": r"$-$", "∈": r"$\in$", "∞": r"$\infty$", "·": r"$\cdot$", "Δ": r"$\Delta$",
       "†": r"$^\dagger$", "²": r"$^2$", "³": r"$^3$", "⁴": r"$^4$", "⁵": r"$^5$", "↓": r"$\downarrow$", "≈": r"$\approx$",
       "⟨": r"$\langle$", "⟩": r"$\rangle$", "‖": r"$\|$", "é": r"\'e"}
SPECIAL = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "_": r"\_", "#": r"\#", "{": r"\{", "}": r"\}", "$": r"\$",
           "~": r"\textasciitilde{}", "^": r"\textasciicircum{}", "<": r"$<$", ">": r"$>$"}


def uni(s):
    return "".join(UNI.get(ch, ch) for ch in str(s))


def tex_escape(s):
    return "".join(SPECIAL.get(ch, UNI.get(ch, ch)) for ch in str(s))


def table(name, caption, label, header, rows, colspec=None, note=None, small=True, resize=True):
    write_csv(TAB / f"{name}.csv", header, rows)
    colspec = colspec or ("l" + "r" * (len(header) - 1))
    body = [r"\begin{table}[htbp]", r"\centering", r"\caption{" + uni(caption) + "}", r"\label{" + label + "}"]
    if small:
        body.append(r"\small")
    body += ([r"\resizebox{\linewidth}{!}{%"] if resize else []) + [r"\begin{tabular}{" + colspec + "}", r"\toprule",
             " & ".join(r"\textbf{" + tex_escape(h) + "}" for h in header) + r" \\", r"\midrule"]
    body += [" & ".join(tex_escape(c) for c in r) + r" \\" for r in rows]
    body += [r"\bottomrule", r"\end{tabular}" + ("}" if resize else "")]
    if note:
        body.append(r"\par\smallskip\footnotesize " + tex_escape(note))
    body.append(r"\end{table}")
    (TAB / f"{name}.tex").write_text("\n".join(body) + "\n")


def tables(dataset_rows, circ_rows):
    tot = [sum(r[i] for r in dataset_rows) for i in (1, 2, 3)]
    table("tab01_dataset", "Characteristics of the NEU-DET steel-surface defect dataset and the evaluation protocol.", "tab:dataset",
          ["Property", "Value"], [
              ["Classes", "6 (crazing, inclusion, patches, pitted surface, rolled-in scale, scratches)"],
              ["Images", f"{tot[0] + tot[1] + tot[2]} grayscale, 200×200 px"],
              ["Train-folder pool", f"{tot[0] + tot[1]} (240 per class)"],
              ["Locked test set", f"{tot[2]} (NEU validation folder, 60 per class)"],
              ["Internal split (per seed)", f"{tot[0]} train / {tot[1]} validation (group-blocked, 3 blocks of 20 per class)"],
              ["Seeds", "0, 1, 2"],
              ["Preprocessing", "grayscale → bilinear resize to s×s → /255"],
              ["Model selection", "mean validation macro-F1 over 3 seeds; test evaluated once per selected configuration"],
          ], colspec="lp{0.66\\linewidth}", small=False, resize=False)

    def grid(group, keys):
        p = R / "aggregates" / "selection" / f"{group}.json"
        c = json.loads(p.read_text())["candidates"]
        out = []
        for k in keys:
            vals = sorted({x["params"].get(k) for x in c if x["params"].get(k) is not None})
            if vals:
                fmt = lambda v: ("yes" if v else "no") if isinstance(v, bool) else (f"{v:g}" if isinstance(v, (int, float)) else str(v))
                out.append(f"{k}∈{{{', '.join(fmt(v) for v in vals)}}}")
        return "; ".join(out), len(c)
    cfg = []
    for code, desc, g, keys, reps in (
            ("E1", "FRQI state-overlap kernel + SVM", "E1-frqi8-qkc", ["C"], "2×2–16×16; θ=πI/2"),
            ("E1b", "FRQI kernel, angle-scaled", "E1b-frqi8-qkc-scaled", ["angle_scale", "C"], "4×4–16×16"),
            ("E2", "NEQR state-overlap kernel + SVM", "E2-neqr8-b4-qkc", ["C"], "2×2–16×16; 2/4/8-bit"),
            ("E3", "PCA + quantum kernel (product-RY / ZZ)", "E3-pca8-qkc-zz_full", ["reps", "bandwidth", "C"], "64×64 → PCA k=4/6/8"),
            ("E4", "PCA + variational quantum classifier", "E4-pca8-vqc", ["layers", "optimizer", "reupload"], "64×64 → PCA k=4/6/8"),
            ("E5", "MobileNetV3 + PCA + QKC / VQC / classical", "E5-mnv3pca8-qkc-zz_full", ["bandwidth", "C"], "576-d → PCA k=4/6/8"),
            ("E6", "PCA + RBF-SVM / LogReg (classical)", "E6-pca8-rbfsvm", ["C", "gamma"], "64×64 → PCA k=4/6/8"),
            ("E7", "Small CNN (trained from scratch)", "E7-smallcnn", ["lr"], "128×128"),
            ("E7", "Frozen MobileNetV3 + LogReg", "E7-mnv3-logreg", ["C"], "224×224 → 576-d"),
            ("E7", "Frozen MobileNetV3 + RBF-SVM", "E7-mnv3-rbfsvm", ["C", "gamma"], "224×224 → 576-d")):
        gtxt, n = grid(g, keys)
        cfg.append([code, desc, reps, gtxt or "see records", n])
    cfg.append(["Shots", "Finite-shot kernel estimates (selected E1/E2 at 8×8, E3 ZZ-full)", "", "FRQI/NEQR {100, 1,000, 10,000}; QKC {100, 500, 1,000, 5,000}", ""])
    table("tab02_experimental_configuration", "Experimental configurations (Protocol V2). Grids are listed for one representative group of each experiment; "
          "the number of candidate configurations refers to that group.", "tab:config",
          ["Exp.", "Model", "Input", "Hyper-parameter grid", "Configs"], cfg, colspec="llllr",
          note="All quantum circuits are simulated exactly (statevector) on a CPU unless a shot count is stated; no quantum hardware was used.")

    rec = recon_records()
    fn = []
    for r in RES:
        for rep, g, rid in [("FRQI", f"E1-frqi{r}-qkc", f"R-FRQI-{r}x{r}")] + [("NEQR", f"E2-neqr{r}-b{b}-qkc", f"R-NEQR-{r}x{r}-b{b}") for b in (2, 4, 8)]:
            cr = next(x for x in circ_rows if x["record"] == rid)
            sv = rec[rid]["summary"]["statevector"]["vs_preprocessed"]
            psnr = "∞ (exact)" if sv["psnr"].get("n_exact") else f"{sv['psnr']['mean']:.1f}"
            fn.append([f"{r}×{r}", rep + ("" if rep == "FRQI" else f" {SEL[g]['params']['bits']}-bit"), cr["n_qubits"], f"{cr['gates_compiled']:,.0f}",
                       f"{cr['depth_compiled']:,.0f}", pm(g, "test_accuracy"), pm(g, "test_f1_macro"), psnr, f"{sv['ssim']['mean']:.3f}"])
    table("tab03_frqi_vs_neqr", "FRQI (original angle map, $b=1$) versus NEQR: circuit resources, classification (state-overlap kernel + SVM, locked test, mean $\\pm$ s.d. over 3 seeds) "
          "and exact (statevector) reconstruction quality against the preprocessed image.", "tab:frqi-neqr",
          ["Res.", "Encoding", "Qubits", "Gates (compiled)", "Depth (compiled)", "Accuracy (%)", "Macro-F1 (%)", "PSNR (dB)", "SSIM"], fn,
          colspec="llrrrrrrr", note="Gate counts and depth: one encoding circuit, transpiled to {cx, rz, sx, x} (optimisation level 1); NEQR values are means "
                                    "over 5 sample images because they depend on pixel values. Reconstruction: 30 training images per configuration.")

    perf = [[fam, nice(g), SEL[g]["n_qubits"] or "–", f"{100 * mean(g, 'val_f1_macro'):.1f}", pm(g, "test_accuracy"), pm(g, "test_f1_macro"),
             pm(g, "test_precision_macro"), pm(g, "test_recall_macro")] for fam, g in REP]
    table("tab04_classification_performance", "Classification performance on the 360-image locked test set (mean $\\pm$ s.d. over seeds 0--2). "
          "One representative per family, chosen by validation macro-F1.", "tab:performance",
          ["Family", "Model", "Qubits", "Val. F1", "Accuracy", "Macro-F1", "Precision", "Recall"], perf, colspec="llrrrrrr")

    res_rows = []
    for x in circ_rows:
        res_rows.append([x["rep"] + ("" if x["bits"] is None else f" {x['bits']}-bit"), f"{x['res']}×{x['res']}", x["n_qubits"],
                         f"{x['gates_logical']:,.0f}", f"{x['depth_logical']:,.0f}", f"{x['gates_compiled']:,.0f}", f"{x['depth_compiled']:,.0f}",
                         f"{x['cx_compiled']:,.0f}"])
    for g in ("E3-pca8-qkc-product_ry", "E3-pca8-qkc-zz_linear", "E3-pca8-qkc-zz_full", "E4-pca8-vqc"):
        c = circuit(g)
        res_rows.append([nice(g).split(",")[0], "PCA-8", c["n_qubits"], f"{c['gates_logical']:,}", f"{c['depth_logical']:,}",
                         f"{c['gates_compiled']:,}", f"{c['depth_compiled']:,}", f"{c['cx_compiled']:,}"])
    table("tab05_circuit_resources", "Quantum circuit resources of one encoding / feature-map circuit.", "tab:resources",
          ["Circuit", "Input", "Qubits", "Gates (logical)", "Depth (logical)", "Gates (compiled)", "Depth (compiled)", "CX (compiled)"], res_rows,
          colspec="llrrrrrr", note="Compiled: basis {cx, rz, sx, x}, optimisation level 1, all-to-all connectivity. A kernel entry uses U(x) followed by U(y)† (twice the gates).")

    rr = []
    for rid, r in sorted(rec.items(), key=lambda kv: (kv[0].split("-")[1], int(kv[0].split("-")[2].split("x")[0]), kv[0])):
        s = r["summary"]
        row = [rid.replace("R-", "").replace("-b", " ").replace("x", "×") + ("-bit" if "NEQR" in rid else "")]
        for k in ("statevector", "shots1000", "shots10000"):
            v = s[k]["vs_preprocessed"]
            row += [f"{v['mse']['mean']:.2e}", "∞" if v["psnr"].get("n_exact") else f"{v['psnr']['mean']:.1f}", f"{v['ssim']['mean']:.3f}"]
        rr.append(row)
    table("tab06_reconstruction_metrics", "Reconstruction quality against the preprocessed image (mean over 30 training images): MSE, PSNR (dB) and SSIM "
          "for exact statevector decoding and for 10$^3$ / 10$^4$ measurement shots.", "tab:reconstruction",
          ["Encoding", "SV MSE", "SV PSNR", "SV SSIM", "1k MSE", "1k PSNR", "1k SSIM", "10k MSE", "10k PSNR", "10k SSIM"], rr, colspec="lrrrrrrrrr",
          note="∞: reconstruction identical to the reference (MSE below 1e-20). NEQR errors at statevector level are pure quantisation error. "
               "Reconstruction quality is a separate task from classification and is not used to rank classifiers.")

    best = {}
    for name, pred in (("Classical", lambda g: paradigm(g) == "Classical"), ("Quantum (simulated)", lambda g: paradigm(g) == "Quantum (simulated)"),
                       ("Hybrid", lambda g: paradigm(g) == "Hybrid"), ("FRQI", lambda g: g.startswith(("E1-", "E1b-"))), ("NEQR", lambda g: g.startswith("E2-"))):
        best[name] = best_by_val(pred)
    bm = [[k, nice(g), f"{100 * mean(g, 'val_f1_macro'):.1f}", pm(g, "test_accuracy"), pm(g, "test_f1_macro"), SEL[g]["n_qubits"] or "–"]
          for k, g in best.items()]
    table("tab07_best_model_comparison", "Best model per paradigm and per encoding, selected by validation macro-F1 (locked test reported).", "tab:best",
          ["Category", "Model", "Val. F1 (%)", "Test accuracy (%)", "Test macro-F1 (%)", "Qubits"], bm, colspec="llrrrr")

    pt = []
    for p in A["paired_tests"]:
        if "PCA 8" in p["comparison"] or "PCA(8)" in p["comparison"] or "Frozen" in p["comparison"]:
            ps = [x["p_value_exact"] for x in p["per_seed"]]
            da = np.mean([x["acc_a"] - x["acc_b"] for x in p["per_seed"]])
            pt.append([p["comparison"], f"{100 * da:+.1f}", ", ".join("<0.001" if v < 0.001 else f"{v:.3f}" for v in ps), sum(v < 0.05 for v in ps)])
    table("tab08_paired_tests", "Paired comparisons on identical features (k = 8): mean accuracy difference A − B over seeds and exact McNemar p-values per seed "
          "(uncorrected).", "tab:paired", ["Comparison (A vs B)", "Δ acc. (pp)", "McNemar p (seeds 0, 1, 2)", "Seeds p<0.05"], pt, colspec="lrlr")

    lim = [["Simulation only", "All quantum circuits were simulated exactly on a CPU; no noise model and no quantum hardware."],
           ["Shot noise only for subsets", "Finite-shot kernels were evaluated only for the validation-selected 8×8 FRQI/NEQR and ZZ-full QKC configurations."],
           ["Small image sizes", "FRQI/NEQR were limited to 16×16 because simulated circuit depth grows to ~10⁵ compiled gates."],
           ["Distribution shift", "Locked test = NEU validation folder; validation (train-folder) scores exceed test scores for all models."],
           ["Gate counts depend on data", "NEQR gate counts vary with pixel values; means over 5 sample images are reported."],
           ["Reconstruction subset", "Reconstruction metrics use 30 training images (5 per class)."],
           ["Multiple comparisons", "Per-seed McNemar p-values are not corrected for multiple comparisons."],
           ["Classical features in hybrids", "Hybrid gains come from classical MobileNetV3 features; quantum and classical classifiers on the same features perform similarly."],
           ["Product-RY control", "The product-RY kernel is classically computable in closed form."]]
    table("tab09_limitations", "Experimental limitations.", "tab:limitations", ["Limitation", "Description"], lim, colspec="lp{0.62\\linewidth}", small=False, resize=False)

    full = [[g, nice(g), paradigm(g), SEL[g]["category"], SEL[g]["n_qubits"], mean(g, "val_f1_macro"), mean(g, "test_accuracy"), sd(g, "test_accuracy"),
             mean(g, "test_f1_macro"), sd(g, "test_f1_macro"), mean(g, "test_precision_macro"), mean(g, "test_recall_macro"), ";".join(SEL[g]["experiment_ids"])]
            for g in sorted(SEL)]
    write_csv(TAB / "tabS1_all_selected_models.csv", ["group", "model", "paradigm", "category", "n_qubits", "val_f1_macro", "test_acc_mean", "test_acc_std",
                                                      "test_f1_mean", "test_f1_std", "test_precision_mean", "test_recall_mean", "experiment_ids"], full)
    return best


if __name__ == "__main__":
    ds = fig_dataset()
    hbar_metric("test_accuracy", "Accuracy", "fig02_accuracy_comparison", "Locked-test accuracy (%)")
    hbar_metric("test_f1_macro", "Macro-F1", "fig03_macro_f1_comparison", "Locked-test macro-F1 (%)")
    fig_precision_recall()
    fig_paradigms()
    fig_frqi_neqr_resolution()
    fig_neqr_precision()
    fig_shots()
    fig_reconstruction_metrics()
    circ = fig_circuits()
    fig_confusion()
    fig_per_class()
    fig_recon_examples()
    fig_kernel_concentration()
    best = tables(ds, circ)
    (DATA / "representative_models.json").write_text(json.dumps({"by_validation": REP, "best_per_category": best}, indent=1))
    print("representatives:", [(f, g) for f, g in REP])
    print("best:", best)
