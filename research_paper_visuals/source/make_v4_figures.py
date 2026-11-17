"""Protocol V4 figures -> research_paper_visuals/figures_v4/ (PNG 300 dpi, PDF, SVG + data CSVs).
Reads results/qml_v4/aggregates/v4_results.json and the per-seed records it lists (read-only)."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research_paper_visuals" / "figures_v4"
(OUT / "data").mkdir(parents=True, exist_ok=True)
D = json.loads((ROOT / "results/qml_v4/aggregates/v4_results.json").read_text())
A2 = json.loads((ROOT / "results/qml_v2/aggregates/analysis.json").read_text())["selected"]
R3 = {g["group"]: g for g in json.loads((ROOT / "results/qml_v3/aggregates/v3_results.json").read_text())["groups"]}
G, REF, H = D["groups"], D["references"], D["headlines"]
BLUE, ORANGE, GREY, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#8a939d", "#1a1a1a", "#5b6470", "#e6e8eb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": "#b8bec6", "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False, "svg.fonttype": "none", "pdf.fonttype": 42, "legend.frameon": False})
NOTE = "Locked test set (360 images); bars = mean of seeds 0–2, error bars = s.d., dots = individual seeds. Exact noiseless CPU simulation."


def seeds_v2(g):
    return [json.loads((ROOT / "results/qml_v2/experiments" / e / "test_metrics.json").read_text())["accuracy"] for e in A2[g]["experiment_ids"]]


def seeds_v3(g):
    return [json.loads((ROOT / "results/qml_v3/experiments" / e / "test_metrics.json").read_text())["accuracy"] for e in R3[g]["experiment_ids"]]


def save(fig, name, head, rows):
    for ext, kw in (("png", {"dpi": 300}), ("pdf", {}), ("svg", {})):
        fig.savefig(OUT / f"{name}.{ext}", bbox_inches="tight", pad_inches=0.05, facecolor="white", **kw)
    plt.close(fig)
    with open(OUT / "data" / f"{name}.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(head); w.writerows(rows)


# ---------------------------------------------------------------- V4-1 FRQI / NEQR across protocols
proto = [("V2\npixel-level kernel", {"FRQI": seeds_v2("E1b-frqi8-qkc-scaled"), "NEQR": seeds_v2("E2-neqr16-b4-qkc")}),
         ("V3\npixel-level kernel,\nwider search", {"FRQI": seeds_v3("V3-frqi8"), "NEQR": seeds_v3("V3-neqr16")}),
         ("V4\npatch-ensemble\nmixed-state kernel", {"FRQI": G[H["frqi"]]["per_seed_test_accuracy"], "NEQR": G[H["neqr"]]["per_seed_test_accuracy"]})]
fig, ax = plt.subplots(figsize=(6.4, 3.8))
x, w, rows = np.arange(3), 0.34, []
for j, (rep, col) in enumerate((("FRQI", BLUE), ("NEQR", ORANGE))):
    for i, (lab, d) in enumerate(proto):
        v = 100 * np.array(d[rep])
        xi = x[i] + (j - 0.5) * w
        ax.bar(xi, v.mean(), w * 0.9, yerr=v.std(ddof=1), color=col, label=rep if i == 0 else None,
               error_kw={"elinewidth": 0.8, "capsize": 2, "ecolor": "#555"})
        ax.scatter([xi - 0.06, xi, xi + 0.06], v, s=10, color="white", edgecolor=INK, lw=0.6, zorder=4)
        ax.text(xi, 4, f"{v.mean():.1f}", ha="center", fontsize=8, color="white", fontweight="bold")
        rows.append([lab.replace("\n", " "), rep] + [f"{t:.2f}" for t in v] + [f"{v.mean():.2f}"])
for val, lab, ls in ((100 * G["V4-patchmom-rbfsvm"]["test_accuracy"]["mean"], "classical RBF-SVM, same patches", (0, (4, 3))),
                     (100 * REF["V3-tex12c-rbfsvm"]["test_accuracy"]["mean"], "classical RBF-SVM, texture features", (0, (1, 2)))):
    ax.axhline(val, color=GREY, lw=1, ls=ls, zorder=0)
    ax.text(-0.5, val + 0.8, f"{lab} ({val:.1f}%)", fontsize=7, color=MUTED, va="bottom")
    rows.append(["reference", lab, f"{val:.2f}"])
ax.set_xticks(x, [p[0] for p in proto], fontsize=8); ax.set_xlim(-0.55, 2.55); ax.set_ylim(0, 105)
ax.set_ylabel("Test accuracy (%)"); ax.grid(axis="y", color=GRID, lw=0.7); ax.set_axisbelow(True)
ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=8)
fig.text(0.0, -0.1, NOTE + " The low NEQR V4 seed is seed 1 (rolled-in scale misclassified; see report).", fontsize=6.8, color=MUTED, wrap=True)
save(fig, "figV4_1_frqi_neqr_protocols", ["protocol", "encoding", "seed0", "seed1", "seed2", "mean"], rows)

# ---------------------------------------------------------------- V4-2 per-class F1
CL = ["crazing", "inclusion", "patches", "pitted_surface", "rolled-in_scale", "scratches"]
ser = [(H["frqi"], "FRQI patch-ensemble", BLUE), (H["neqr"], "NEQR patch-ensemble", ORANGE), ("V4-patchmom-rbfsvm", "Classical RBF-SVM, same patches", GREY)]
fig, ax = plt.subplots(figsize=(7.0, 3.3))
x, w, rows = np.arange(len(CL)), 0.27, []
for j, (g, lab, col) in enumerate(ser):
    pcf = G[g]["per_class_f1"]
    v = [100 * pcf[c]["mean"] for c in CL]
    ax.bar(x + (j - 1) * w, v, w * 0.92, color=col, label=lab)
    rows += [[lab, c, f"{t:.2f}"] for c, t in zip(CL, v)]
ax.set_xticks(x, [c.replace("_", " ").replace("rolled-in", "rolled-in\n").replace("pitted ", "pitted\n") for c in CL], fontsize=8)
ax.set_ylim(0, 105); ax.set_ylabel("F1 (%)"); ax.grid(axis="y", color=GRID, lw=0.7); ax.set_axisbelow(True)
ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, fontsize=7.5)
fig.text(0.0, -0.1, "Per-class F1 on the locked test set, mean over seeds 0–2. Exact noiseless CPU simulation.", fontsize=6.8, color=MUTED)
save(fig, "figV4_2_per_class_f1", ["model", "class", "f1_mean"], rows)
print("V4 figures written to", OUT)

# ---------------------------------------------------------------- V4-3 / V4-4 full reconstruction study (all 1,800 images)
import sys  # noqa: E402
sys.path.insert(0, str(ROOT))
RF = ROOT / "results/qml_v4/reconstruction_full"
if (RF / "summary.json").exists():
    S = json.loads((RF / "summary.json").read_text())["records"]
    SH = [100, 1000, 10000, 100000]
    RAMP = {2: "#9ec5f4", 4: "#5a9fe8", 8: "#2a78d6", 16: "#174a8a"}
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
    rows = []
    for ax, fam, title in ((axs[0], "FRQI", "(a) FRQI"), (axs[1], "NEQR", "(b) NEQR, 4-bit")):
        for r in (2, 4, 8, 16):
            rid = f"R-{fam}-{r}x{r}" + ("-b4" if fam == "NEQR" else "")
            y = [S[rid]["summary"]["all"][f"shots{s}"]["vs_preprocessed"]["mse"]["mean"] for s in SH]
            ax.plot(SH, y, marker="o", ms=4, lw=1.8, color=RAMP[r], label=f"{r}×{r}")
            rows += [[rid, s, f"{v:.6g}"] for s, v in zip(SH, y)]
        ax.set_xscale("log"); ax.set_yscale("log"); ax.set_title(title, fontsize=9, loc="left")
        ax.set_xlabel("measurement shots per image"); ax.grid(color=GRID, lw=0.7)
    axs[0].set_ylabel("MSE vs preprocessed image")
    axs[1].legend(fontsize=7.5, title="resolution", title_fontsize=7.5, loc="upper right")
    fig.text(0.0, -0.16, "Mean over all 1,800 NEU-DET images (train + locked-test folders). Real Qiskit FRQI/NEQR circuits, Qiskit-Aer "
             "statevector, multinomial shot sampling, project decoder. NEQR saturates at its 4-bit quantisation error.", fontsize=6.8, color=MUTED, wrap=True)
    save(fig, "figV4_3_reconstruction_all_images", ["record", "shots", "mse_mean"], rows)

    # example grid: one locked-test image per class
    met = json.loads((RF / "R-FRQI-16x16" / "metrics.json").read_text())["per_image"]
    picks = [next(r["i"] for r in met if r["role"] == "locked_test" and r["class"] == c) for c in CL]
    cols = [("R-FRQI-16x16", "statevector", "FRQI 16×16\nexact"), ("R-FRQI-16x16", "shots1000", "FRQI 16×16\n1k shots"),
            ("R-NEQR-16x16-b4", "statevector", "NEQR 16×16\n4-bit, exact"), ("P-FRQI-64-p8", "shots1000", "FRQI 8×8 patches\n1k shots/patch"),
            ("C-PCA8-64", "reconstruction", "PCA-8\n(classical)")]
    Z = {rid: np.load(RF / rid / "reconstructions.npz") for rid, _, _ in cols}
    from PIL import Image
    from src.v2.dataset import preprocess_image  # noqa: E402
    from src.v2.paths import dataset_root  # noqa: E402
    fig, axs = plt.subplots(len(CL), len(cols) + 1, figsize=(7.6, 7.4))
    for r_, (c, i) in enumerate(zip(CL, picks)):
        axs[r_, 0].imshow(preprocess_image(dataset_root() / met[i]["image"], 64), cmap="gray", vmin=0, vmax=1)
        axs[r_, 0].set_ylabel(c.replace("_", " "), fontsize=7.5)
        for k, (rid, mode, lab) in enumerate(cols):
            axs[r_, k + 1].imshow(Z[rid][mode][i].astype(float), cmap="gray", vmin=0, vmax=1, interpolation="nearest")
            if r_ == 0:
                axs[r_, k + 1].set_title(lab, fontsize=6.8)
        if r_ == 0:
            axs[r_, 0].set_title("original\n(64×64)", fontsize=6.8)
    for ax in axs.ravel():
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)
    fig.text(0.0, 0.06, "One locked-test-folder image per class; arrays are the saved decoder outputs of the full study (V4 = patch representation).", fontsize=6.8, color=MUTED)
    save(fig, "figV4_4_reconstruction_examples", ["class", "image_index", "image"], [[c, i, met[i]["image"]] for c, i in zip(CL, picks)])
    print("reconstruction figures written")
