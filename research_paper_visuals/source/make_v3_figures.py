"""Protocol V3 figures -> research_paper_visuals/figures_v3/ (PNG 300 dpi, PDF, SVG) + data CSVs.
Reads results/qml_v3/aggregates/v3_results.json only (read-only). No number is typed by hand."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research_paper_visuals" / "figures_v3"
(OUT / "data").mkdir(parents=True, exist_ok=True)
D = json.loads((ROOT / "results/qml_v3/aggregates/v3_results.json").read_text())
G = {g["group"]: g for g in D["groups"]}
C = {c["name"]: c for c in D["comparisons"]}

BLUE, ORANGE, AQUA, YELLOW, MAGENTA, VIOLET = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"
GREY, INK, MUTED, GRID = "#9aa3ad", "#1a1a1a", "#5b6470", "#e6e8eb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": "#b8bec6", "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "svg.fonttype": "none", "pdf.fonttype": 42, "legend.frameon": False})
NOTE = "Locked test set (360 images), mean ± s.d. over seeds 0–2. Quantum circuits: exact noiseless CPU simulation."


def save(fig, name, rows, head):
    for ext, kw in (("png", {"dpi": 300}), ("pdf", {}), ("svg", {})):
        fig.savefig(OUT / f"{name}.{ext}", bbox_inches="tight", pad_inches=0.05, facecolor="white", **kw)
    plt.close(fig)
    with open(OUT / "data" / f"{name}.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(head); w.writerows(rows)


def m(g, k="test_accuracy"):
    return 100 * G[g][k]["mean"], 100 * (G[g][k].get("std") or 0)


# ---------------------------------------------------------------- V3-1 before / after
ba = D["before_after"]
fig, ax = plt.subplots(figsize=(6.6, 4.2))
rows = []
for i, b in enumerate(ba):
    y = len(ba) - 1 - i
    v2, v3 = 100 * b["v2_test_accuracy"]["mean"], 100 * b["v3_best"]["test_accuracy"]["mean"]
    ax.plot([v2, v3], [y, y], color="#c9ced4", lw=2, zorder=1)
    ax.scatter([v2], [y], s=42, color=GREY, edgecolor="white", lw=1.5, zorder=3)
    ax.scatter([v3], [y], s=42, color=AQUA, edgecolor="white", lw=1.5, zorder=3)
    ax.text(max(v2, v3) + 1.5, y, f"{v3 - v2:+.1f} pp", va="center", fontsize=7.5, color=MUTED)
    rows.append([b["model"], b["v2_group"], f"{v2:.2f}", b["v3_best"]["group"], f"{v3:.2f}", f"{v3 - v2:.2f}"])
ax.set_yticks(range(len(ba)), [b["model"].replace(" (V2: pixel PCA-8)", "") for b in ba][::-1])
ax.set_xlim(30, 108); ax.set_xlabel("Test accuracy (%)")
ax.grid(axis="x", color=GRID, lw=0.7); ax.set_axisbelow(True)
ax.scatter([], [], color=GREY, label="Protocol V2"); ax.scatter([], [], color=AQUA, label="Protocol V3 (chosen on validation)")
ax.legend(loc="lower left", fontsize=8, bbox_to_anchor=(0, 1.0), ncol=2)
fig.text(0.0, -0.04, "V3 may use a different input representation (e.g. texture features) than V2. " + NOTE, fontsize=6.8, color=MUTED, wrap=True)
save(fig, "figV3_1_before_after", rows, ["model", "v2_group", "v2_acc", "v3_group", "v3_acc", "diff_pp"])

# ---------------------------------------------------------------- V3-2 matched quantum vs classical
order = ["pix8a", "pix8c", "pix12c", "pixn8c", "tex8c", "tex12c", "mnv8c", "mnv12c"]
lab = {"pix8a": "Pixels\nPCA-8\n(MinMax)", "pix8c": "Pixels\nPCA-8", "pix12c": "Pixels\nPCA-12", "pixn8c": "Pixels\nPCA-8\n(img-norm)",
       "tex8c": "Texture\nPCA-8", "tex12c": "Texture\nPCA-12", "mnv8c": "Mobile-\nNetV3\nPCA-8", "mnv12c": "Mobile-\nNetV3\nPCA-12"}
mc = {x["feature_set"]: x for x in D["matched_controls"]}
fs = [f for f in order if f in mc]
x = np.arange(len(fs)); w = 0.38
fig, ax = plt.subplots(figsize=(8.0, 3.6))
rows = []
for j, (key, col, name) in enumerate((("quantum", AQUA, "Best quantum model (by validation)"), ("rbfsvm", BLUE, "Classical RBF-SVM, same features"))):
    vals = [m(mc[f][key]) for f in fs]
    ax.bar(x + (j - 0.5) * w, [v[0] for v in vals], w * 0.92, yerr=[v[1] for v in vals], color=col, label=name,
           error_kw={"elinewidth": 0.8, "capsize": 2, "ecolor": "#555"})
for i, f in enumerate(fs):
    c = C[f"Quantum vs matched RBF-SVM ({f})"]
    star = "*" if c["p_holm"] < 0.05 else "n.s."
    ax.text(i, max(m(mc[f]["quantum"])[0], m(mc[f]["rbfsvm"])[0]) + 5.5, star, ha="center", fontsize=7.5, color=MUTED)
    rows.append([f, mc[f]["quantum"], f"{m(mc[f]['quantum'])[0]:.2f}", mc[f]["rbfsvm"], f"{m(mc[f]['rbfsvm'])[0]:.2f}",
                 f"{100 * c['diff']:.2f}", f"{c['p_holm']:.4f}"])
ax.set_xticks(x, [lab[f] for f in fs], fontsize=7.5); ax.set_ylim(0, 108); ax.set_ylabel("Test accuracy (%)")
ax.grid(axis="y", color=GRID, lw=0.7); ax.set_axisbelow(True)
ax.legend(loc="lower left", fontsize=8, bbox_to_anchor=(0, 1.0), ncol=2)
fig.text(0.0, -0.14, "Holm-corrected paired permutation test (24 comparisons): * p < 0.05, n.s. not significant. The only significant "
         "difference (Pixels PCA-12) favours the classical model. " + NOTE, fontsize=6.8, color=MUTED, wrap=True)
save(fig, "figV3_2_quantum_vs_classical_matched", rows, ["features", "quantum_group", "quantum_acc", "classical_group", "classical_acc", "diff_pp", "p_holm"])

# ---------------------------------------------------------------- V3-3 VQC vs controls
fsv = ["pix8c", "tex8c", "mnv8c"]
ser = [("vqc", ORANGE, "Trained VQC (L = 2)"), ("vqc-encoding-only", BLUE, "Encoding only, no trainable gates (control)"),
       ("vqc-ablation-frozen", GREY, "Random frozen circuit (ablation)")]
x = np.arange(len(fsv)); w = 0.26
fig, ax = plt.subplots(figsize=(6.2, 3.4))
rows = []
for j, (suf, col, name) in enumerate(ser):
    vals = [m(f"V3-{f}-{suf}") for f in fsv]
    ax.bar(x + (j - 1) * w, [v[0] for v in vals], w * 0.92, yerr=[v[1] for v in vals], color=col, label=name,
           error_kw={"elinewidth": 0.8, "capsize": 2, "ecolor": "#555"})
    rows += [[f, f"V3-{f}-{suf}", f"{v[0]:.2f}", f"{v[1]:.2f}"] for f, v in zip(fsv, vals)]
ax.set_xticks(x, [lab[f].replace("\n", " ").replace(" (MinMax)", "") for f in fsv]); ax.set_ylim(0, 105); ax.set_ylabel("Test accuracy (%)")
ax.axhline(100 / 6, color=MUTED, lw=0.8, ls=(0, (3, 3))); ax.text(2.45, 100 / 6 + 1.5, "chance", fontsize=7, color=MUTED, ha="right")
ax.grid(axis="y", color=GRID, lw=0.7); ax.set_axisbelow(True)
ax.legend(loc="lower left", fontsize=7.5, bbox_to_anchor=(0, 1.0), ncol=1)
fig.text(0.0, -0.06, "8 qubits; same readout (⟨Z⟩ on every qubit → linear head) in all three. " + NOTE, fontsize=6.8, color=MUTED, wrap=True)
save(fig, "figV3_3_vqc_controls", rows, ["features", "group", "acc_mean", "acc_sd"])

# ---------------------------------------------------------------- V3-4 representation effect
models = [("logreg", "Logistic regression", BLUE, "-"), ("rbfsvm", "RBF-SVM", VIOLET, "-"), ("qkc-zz_full", "QKC ZZ-full", AQUA, "-"),
          ("qkc-product_ry", "QKC product-RY", YELLOW, (0, (4, 2))), ("vqc", "VQC", ORANGE, "-")]
fig, ax = plt.subplots(figsize=(5.4, 3.8))
rows = []
for key, name, col, ls in models:
    a, b = m(f"V3-pix8c-{key}")[0], m(f"V3-tex8c-{key}")[0]
    ax.plot([0, 1], [a, b], color=col, lw=2, ls=ls, marker="o", ms=6, mec="white", mew=1.2, label=f"{name}: {a:.1f} → {b:.1f}%")
    rows.append([name, f"{a:.2f}", f"{b:.2f}"])
ax.legend(loc="upper left", fontsize=7.5, bbox_to_anchor=(1.0, 1.0), handlelength=2.6)
ax.set_xticks([0, 1], ["Pixels PCA-8", "Texture PCA-8"]); ax.set_xlim(-0.15, 1.15); ax.set_ylim(20, 105)
ax.set_ylabel("Test accuracy (%)"); ax.grid(axis="y", color=GRID, lw=0.7); ax.set_axisbelow(True)
fig.text(0.0, -0.06, "Same 8 inputs given to every model; texture = fixed LBP + GLCM + gradient statistics. " + NOTE, fontsize=6.8, color=MUTED, wrap=True)
save(fig, "figV3_4_representation_effect", rows, ["model", "pixels_pca8_acc", "texture_pca8_acc"])

# ---------------------------------------------------------------- V3-5 headline models
H = D["headlines"]
hs = [("pure_quantum", "Pure quantum", AQUA), ("vqc", "VQC", ORANGE), ("hybrid_quantum", "Hybrid quantum", MAGENTA),
      ("classical_control_best", "Classical (best)", BLUE), ("frqi", "FRQI", "#7fd4b2"), ("neqr", "NEQR", "#7fd4b2")]
fig, ax = plt.subplots(figsize=(6.4, 3.2))
rows = []
for i, (k, name, col) in enumerate(hs):
    a, s = m(H[k]["group"]); f1 = m(H[k]["group"], "test_f1_macro")[0]
    ax.barh(len(hs) - 1 - i, a, 0.62, xerr=s, color=col, error_kw={"elinewidth": 0.8, "capsize": 2, "ecolor": "#555"})
    ax.text(a + s + 1.2, len(hs) - 1 - i, f"{a:.1f}%  ({H[k]['display_name']})", va="center", fontsize=7)
    rows.append([name, H[k]["group"], H[k]["display_name"], f"{a:.2f}", f"{s:.2f}", f"{f1:.2f}", f"{100 * H[k]['val_f1_macro']['mean']:.2f}"])
ax.set_yticks(range(len(hs)), [h[1] for h in hs][::-1]); ax.set_xlim(0, 175); ax.set_xticks(range(0, 101, 20))
ax.set_xlabel("Test accuracy (%)"); ax.grid(axis="x", color=GRID, lw=0.7); ax.set_axisbelow(True)
ax.spines["bottom"].set_bounds(0, 100)
fig.text(0.0, -0.11, "Each model is the best in its category by validation macro-F1 (test set not used for selection). "
         "Product-RY kernels are classically computable. " + NOTE, fontsize=6.8, color=MUTED, wrap=True)
save(fig, "figV3_5_headline_models", rows, ["category", "group", "model", "acc_mean", "acc_sd", "f1_mean", "val_f1"])
print("V3 figures written to", OUT)
