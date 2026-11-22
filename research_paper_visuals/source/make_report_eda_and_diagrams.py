"""EDA figures (from all 1,800 real NEU-DET images) and system diagrams (use case, DFD, flowchart, ER) for the
project report. Writes PNGs (300 dpi) to research_paper_visuals/Project_Report/figures.
Run: .venv/bin/python research_paper_visuals/source/make_report_eda_and_diagrams.py
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import src.v2.paths as P  # noqa: E402
from src.v2.dataset import load_manifest  # noqa: E402

OUT = ROOT / "research_paper_visuals/Project_Report/figures"
OUT.mkdir(parents=True, exist_ok=True)
DS = P.dataset_root()
CL = ["crazing", "inclusion", "patches", "pitted_surface", "rolled-in_scale", "scratches"]
CLN = ["crazing", "inclusion", "patches", "pitted\nsurface", "rolled-in\nscale", "scratches"]
BLUE, ORANGE, GREY, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#8a939d", "#1a1a1a", "#5b6470", "#e6e8eb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": "#b8bec6", "axes.spines.top": False,
                     "axes.spines.right": False, "xtick.color": MUTED, "ytick.color": MUTED, "legend.frameon": False})
STATS = {}


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


# ── load all images once ──
recs = load_manifest()["records"]
data = {"train": {c: [] for c in CL}, "validation": {c: [] for c in CL}}
sizes, modes = set(), set()
for r in recs:
    with Image.open(DS / r["rel_path"]) as im:
        sizes.add(im.size); modes.add(im.mode)
        a = np.asarray(im.convert("L"), dtype=np.float64) / 255.0
    data[r["folder"]][r["class"]].append(a)
STATS["sizes"] = sorted(map(list, sizes)); STATS["modes"] = sorted(modes); STATS["n"] = len(recs)

# ── E1 class distribution per folder ──
fig, ax = plt.subplots(figsize=(7, 3.2))
x = np.arange(6)
tr = [len(data["train"][c]) for c in CL]; va = [len(data["validation"][c]) for c in CL]
ax.bar(x - 0.2, tr, 0.38, color=BLUE, label="train folder (train + validation splits)")
ax.bar(x + 0.2, va, 0.38, color=ORANGE, label="validation folder (locked test set)")
for i in range(6):
    ax.text(i - 0.2, tr[i] + 4, tr[i], ha="center", fontsize=8); ax.text(i + 0.2, va[i] + 4, va[i], ha="center", fontsize=8)
ax.set_xticks(x, CLN); ax.set_ylabel("number of images"); ax.set_ylim(0, 290); ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.16), ncol=2, fontsize=8)
save(fig, "E1_class_distribution")
STATS["counts"] = {"train": dict(zip(CL, tr)), "validation": dict(zip(CL, va))}

# ── E2 brightness and contrast per class, train vs test folder ──
fig, axs = plt.subplots(1, 2, figsize=(9, 3.4))
for ax, fn, lab in ((axs[0], np.mean, "mean intensity per image"), (axs[1], np.std, "contrast (std. of intensity) per image")):
    for k, (folder, col) in enumerate((("train", BLUE), ("validation", ORANGE))):
        vals = [[fn(a) for a in data[folder][c]] for c in CL]
        bp = ax.boxplot(vals, positions=x + (k - 0.5) * 0.36, widths=0.3, patch_artist=True, showfliers=False,
                        medianprops=dict(color=INK), boxprops=dict(facecolor=col, edgecolor=col, alpha=0.75), whiskerprops=dict(color=col), capprops=dict(color=col))
        if fn is np.mean:
            STATS.setdefault("brightness", {})[folder] = {c: [float(np.mean(v)), float(np.std(v))] for c, v in zip(CL, vals)}
        else:
            STATS.setdefault("contrast", {})[folder] = {c: [float(np.mean(v)), float(np.std(v))] for c, v in zip(CL, vals)}
    ax.set_xticks(x, CLN, fontsize=8); ax.set_ylabel(lab); ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
h = [plt.Rectangle((0, 0), 1, 1, color=BLUE, alpha=0.75), plt.Rectangle((0, 0), 1, 1, color=ORANGE, alpha=0.75)]
fig.legend(h, ["train folder", "validation folder (locked test)"], loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.06), fontsize=8)
fig.tight_layout()
save(fig, "E2_brightness_contrast")

# ── E3 intensity histograms per class ──
fig, axs = plt.subplots(2, 3, figsize=(9, 4.6), sharex=True)
bins = np.linspace(0, 1, 52)
for ax, c, n in zip(axs.ravel(), CL, CLN):
    for folder, col in (("train", BLUE), ("validation", ORANGE)):
        v = np.concatenate([a.ravel() for a in data[folder][c]])
        ax.hist(v, bins=bins, density=True, histtype="step", lw=1.6, color=col)
    ax.set_title(n.replace("\n", " "), fontsize=9); ax.grid(color=GRID); ax.set_axisbelow(True)
for ax in axs[1]:
    ax.set_xlabel("pixel intensity (0 = black, 1 = white)")
for ax in axs[:, 0]:
    ax.set_ylabel("density")
fig.legend([plt.Line2D([], [], color=BLUE, lw=2), plt.Line2D([], [], color=ORANGE, lw=2)], ["train folder", "validation folder (locked test)"],
           loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.04), fontsize=8)
fig.tight_layout()
save(fig, "E3_intensity_histograms")

# ── E4 class-average images ──
fig, axs = plt.subplots(1, 6, figsize=(10, 2.1))
for ax, c, n in zip(axs, CL, CLN):
    ax.imshow(np.mean(data["train"][c] + data["validation"][c], 0), cmap="gray", vmin=0, vmax=1)
    ax.set_title(n.replace("\n", " "), fontsize=9); ax.set_xticks([]); ax.set_yticks([])
save(fig, "E4_class_average_images")

(OUT / "eda_stats.json").write_text(json.dumps(STATS, indent=1))


# ───────────────────────────── diagrams ─────────────────────────────
def box(ax, x, y, w, h, text, fc="#eef4fc", ec=BLUE, fs=8.5, bold=False):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", fc=fc, ec=ec, lw=1.1))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, color=INK, weight="bold" if bold else "normal", wrap=True)


def arrow(ax, a, b, text=None, color="#6b7280", style="-|>", ls="-", rad=0.0, fs=7.5):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=11, color=color, lw=1.1, linestyle=ls, connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 0.18, text, ha="center", va="bottom", fontsize=fs, color=MUTED)


def canvas(w, h, xl, yl):
    fig, ax = plt.subplots(figsize=(w, h)); ax.set_xlim(0, xl); ax.set_ylim(0, yl); ax.axis("off")
    return fig, ax


# D1 use case diagram
fig, ax = canvas(9, 5.6, 18, 11)
ax.add_patch(FancyBboxPatch((4.2, 0.4), 9.6, 10.2, boxstyle="round,pad=0.02,rounding_size=0.2", fc="#fafbfc", ec="#9aa3ad", lw=1))
ax.text(9, 10.25, "Q-ImageLab system", ha="center", fontsize=10, weight="bold")


def actor(x, y, name):
    ax.add_patch(plt.Circle((x, y + 1.1), 0.28, fc="white", ec=INK, lw=1.2))
    ax.plot([x, x], [y + 0.82, y + 0.0], color=INK, lw=1.2); ax.plot([x - 0.45, x + 0.45], [y + 0.55, y + 0.55], color=INK, lw=1.2)
    ax.plot([x, x - 0.35], [y, y - 0.6], color=INK, lw=1.2); ax.plot([x, x + 0.35], [y, y - 0.6], color=INK, lw=1.2)
    ax.text(x, y - 0.85, name, ha="center", va="top", fontsize=8.5)


actor(1.6, 7.0, "Researcher /\nstudent"); actor(1.6, 2.2, "Reviewer /\nsupervisor"); actor(16.4, 4.8, "Experiment\nrunner (scripts)")
uc = [(9, 9.2, "Browse NEU-DET dataset"), (9, 8.0, "Run experiments (V2/V3/V4)"), (9, 6.8, "Select on validation & freeze"),
      (9, 5.6, "Evaluate frozen model on locked test"), (9, 4.4, "Compare models & statistics"), (9, 3.2, "Watch live 'How it works' replay"),
      (9, 2.0, "Reconstruct images (FRQI / NEQR)"), (9, 0.95, "Export figures, tables, reports")]
for x, y, t in uc:
    ax.add_patch(Ellipse((x, y), 7.6, 0.95, fc="#eef4fc", ec=BLUE, lw=1)); ax.text(x, y, t, ha="center", va="center", fontsize=8.2)
for y in (9.2, 8.0, 4.4, 3.2, 2.0, 0.95):
    ax.plot([2.2, 5.2], [7.6, y], color="#9aa3ad", lw=0.8)
for y in (4.4, 3.2, 0.95):
    ax.plot([2.2, 5.2], [2.8, y], color="#9aa3ad", lw=0.8)
for y in (8.0, 6.8, 5.6, 2.0):
    ax.plot([15.8, 12.8], [5.4, y], color="#9aa3ad", lw=0.8)
save(fig, "D1_use_case_diagram")

# D2 DFD level 0 and level 1
fig, axs = plt.subplots(2, 1, figsize=(9.5, 7.6), gridspec_kw={"height_ratios": [1, 1.5]})
ax = axs[0]; ax.set_xlim(0, 20); ax.set_ylim(0, 6); ax.axis("off"); ax.set_title("(a) Level-0 DFD (context diagram)", fontsize=10, loc="left")
box(ax, 3, 3, 4.2, 1.5, "NEU-DET image\nfolders", fc="#f3f4f6", ec=GREY)
ax.add_patch(plt.Circle((10, 3), 1.9, fc="#fdeee6", ec=ORANGE, lw=1.3)); ax.text(10, 3, "0\nQ-ImageLab\nsystem", ha="center", va="center", fontsize=9, weight="bold")
box(ax, 17, 4.4, 4.2, 1.3, "Researcher /\nreviewer", fc="#f3f4f6", ec=GREY)
box(ax, 17, 1.6, 4.2, 1.3, "Result store\n(results/qml_v*)", fc="#f3f4f6", ec=GREY)
arrow(ax, (5.1, 3), (8.1, 3), "images + labels")
arrow(ax, (11.8, 3.9), (14.9, 4.5), "dashboards, figures")
arrow(ax, (14.9, 4.0), (11.9, 3.4))
ax.text(13.6, 3.15, "requests", fontsize=7.5, color=MUTED, ha="center")
arrow(ax, (11.8, 2.3), (14.9, 1.7), "metrics, predictions")
ax = axs[1]; ax.set_xlim(0, 20); ax.set_ylim(0, 9); ax.axis("off"); ax.set_title("(b) Level-1 DFD", fontsize=10, loc="left")
procs = [(2.5, 7, "1.0\nLoad & hash\nmanifest"), (7, 7, "2.0\nPreprocess\n(resize, stretch,\npatches)"), (11.5, 7, "3.0\nEncode\n(FRQI / NEQR\nstates, ρ)"),
         (16.5, 7, "4.0\nKernel + SVM\ntraining"), (16.5, 2.5, "5.0\nValidation\nselection +\nSHA-256 freeze"), (11.5, 2.5, "6.0\nLocked-test\nevaluation"),
         (7, 2.5, "7.0\nStatistics &\nreports"), (2.5, 2.5, "8.0\nFastAPI +\nReact dashboard")]
for x, y, t in procs:
    ax.add_patch(plt.Circle((x, y), 1.45, fc="#fdeee6", ec=ORANGE, lw=1.1)); ax.text(x, y, t, ha="center", va="center", fontsize=7.6)
for a, b, t in (((3.95, 7), (5.55, 7), "records"), ((8.45, 7), (10.05, 7), "patches"), ((12.95, 7), (15.05, 7), "ρ / kernel"),
                ((16.5, 5.55), (16.5, 3.95), "val. scores"), ((15.05, 2.5), (12.95, 2.5), "frozen config"), ((10.05, 2.5), (8.45, 2.5), "predictions"),
                ((5.55, 2.5), (3.95, 2.5), "JSON / CSV")):
    arrow(ax, a, b, t)
ax.plot([5.2, 13.8], [4.75, 4.75], color=INK, lw=1); ax.plot([5.2, 13.8], [4.05, 4.05], color=INK, lw=1)
ax.text(9.5, 4.4, "D1  result store: manifests, experiments/*, aggregates/*, reconstruction_full/*", ha="center", va="center", fontsize=7.6)
for x in (11.5, 7):
    arrow(ax, (x, 3.95), (x, 4.05), ls="--")
arrow(ax, (16.5 - 1.0, 6.0), (13.4, 4.8), "candidate runs", ls="--")
fig.tight_layout()
save(fig, "D2_data_flow_diagrams")

# D3 flowchart of the experiment pipeline
fig, ax = canvas(6.4, 9.2, 10, 20)
steps = [(18.8, "Start", "#f3f4f6"), (16.9, "Load NEU-DET, verify SHA-256\nmanifest, build splits (seeds 0,1,2)", "#eef4fc"),
         (14.9, "For each group, configuration, seed:\ntrain on train split, score validation", "#eef4fc"),
         (12.9, "Select best mean validation\nmacro-F1 per group", "#eef4fc"), (10.9, "Write selection files and\nSHA-256 hashes (freeze)", "#eef4fc"),
         (8.6, "Selection hash\nunchanged?", "#fff6d6"), (6.3, "Evaluate frozen model on the\nlocked test set once; log access", "#eef4fc"),
         (4.3, "Pre-declared comparisons:\npermutation, bootstrap, McNemar, Holm", "#eef4fc"), (2.3, "Write aggregates, figures,\nreports; serve dashboard", "#eef4fc"), (0.6, "End", "#f3f4f6")]
for y, t, fc in steps:
    if "?" in t:
        ax.add_patch(plt.Polygon([[5, y + 1.2], [8.2, y], [5, y - 1.2], [1.8, y]], fc=fc, ec="#b38b00", lw=1.1)); ax.text(5, y, t, ha="center", va="center", fontsize=8)
    else:
        box(ax, 5, y, 7.4 if t not in ("Start", "End") else 3, 1.3 if t not in ("Start", "End") else 0.9, t, fc=fc, fs=8)
ys = [s[0] for s in steps]
for a, b in zip(ys[:-1], ys[1:]):
    top = a - (0.45 if a in (18.8,) else 0.65 if a != 8.6 else 1.2); bot = b + (0.65 if b not in (8.6, 0.6) else 1.2 if b == 8.6 else 0.45)
    arrow(ax, (5, top), (5, bot))
ax.text(5.25, 7.15, "yes", fontsize=8, color=MUTED)
ax.add_patch(FancyArrowPatch((8.2, 8.6), (9.4, 8.6), arrowstyle="-", color="#b3321f", lw=1.1)); ax.text(9.0, 8.85, "no", fontsize=8, color="#b3321f")
ax.text(9.5, 8.6, "abort", fontsize=8, color="#b3321f", va="center")
save(fig, "D3_pipeline_flowchart")

# D4 ER diagram
fig, ax = canvas(10, 6.4, 20, 12.5)
ents = {"IMAGE": (3, 9.5, ["rel_path (PK)", "class", "folder / role", "block, group_id", "sha256"]),
        "SPLIT": (3, 3.2, ["seed (PK)", "train images", "validation images", "locked-test images"]),
        "CONFIGURATION": (10, 9.5, ["config_key (PK)", "group", "params (S, p, s, b/q, norm, C)", "representation"]),
        "EXPERIMENT_RUN": (10, 3.2, ["experiment_id (PK)", "config_key (FK)", "seed (FK)", "validation_metrics", "status, circuit_stats"]),
        "PREDICTION": (17, 3.2, ["experiment_id (FK)", "image (FK)", "split", "y_true, y_pred"]),
        "SELECTION": (17, 9.5, ["group (PK)", "selected config_key (FK)", "val_mean, val_std", "SHA-256 hash"])}
for name, (x, y, fields) in ents.items():
    h = 0.62 * (len(fields) + 1)
    ax.add_patch(FancyBboxPatch((x - 2.7, y - h / 2), 5.4, h, boxstyle="round,pad=0.02,rounding_size=0.1", fc="white", ec=BLUE, lw=1.2))
    ax.add_patch(FancyBboxPatch((x - 2.7, y + h / 2 - 0.62), 5.4, 0.62, boxstyle="round,pad=0.02,rounding_size=0.1", fc=BLUE, ec=BLUE))
    ax.text(x, y + h / 2 - 0.31, name, ha="center", va="center", color="white", fontsize=8.5, weight="bold")
    for k, f in enumerate(fields):
        ax.text(x - 2.5, y + h / 2 - 0.95 - 0.62 * k, f, fontsize=7.6, va="center")
rels = [((5.7, 9.3), (7.3, 9.3), "M : N"), ((3, 7.6), (3, 5.0), "M : N"), ((10, 7.4), (10, 5.3), "1 : 3"),
        ((5.7, 3.2), (7.3, 3.2), "1 : N"), ((12.7, 3.2), (14.3, 3.2), "1 : N"), ((14.3, 9.3), (12.7, 9.3), "1 : 1")]
for a, b, t in rels:
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-", color="#6b7280", lw=1.0))
    if a[0] == b[0]:
        ax.text(a[0] + 0.25, (a[1] + b[1]) / 2, t, ha="left", va="center", fontsize=7.2, color=MUTED)
    else:
        ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 0.2, t, ha="center", fontsize=7.2, color=MUTED)
ax.text(10, 0.3, "Each PREDICTION also references one IMAGE (1 image : N predictions). Stored as JSON/CSV files, not a relational database.", ha="center", fontsize=7.6, color=MUTED)
save(fig, "D4_er_diagram")

# ── equation images ──
EQ = {"Q1_frqi": r"$|\psi_{FRQI}\rangle=\frac{1}{\sqrt{N}}\sum_{i=0}^{N-1}(\cos\theta_i|0\rangle+\sin\theta_i|1\rangle)\otimes|i\rangle,\quad \theta_i=\frac{\pi}{2}\,b\,x_i$",
      "Q2_neqr": r"$|\psi_{NEQR}\rangle=\frac{1}{\sqrt{N}}\sum_{i=0}^{N-1}|c_i\rangle\otimes|i\rangle,\quad c_i=\mathrm{round}(x_i(2^q-1))$",
      "Q3_rho": r"$\rho_I=\frac{1}{P}\sum_{k=1}^{P}|\psi_k\rangle\langle\psi_k|,\qquad P=\left(\frac{S-p}{s}+1\right)^2$",
      "Q4_kernel": r"$K(A,B)=\mathrm{Tr}(\rho_A\rho_B)=\frac{1}{P_A P_B}\sum_{k=1}^{P_A}\sum_{l=1}^{P_B}|\langle\psi_k^A|\psi_l^B\rangle|^2$",
      "Q5_swap": r"$\Pr[\mathrm{ancilla}=0]=\frac{1}{2}\left(1+\mathrm{Tr}(\rho\sigma)\right)$",
      "Q6_stretch": r"$x_i'=\frac{x_i-\min_j x_j}{\max_j x_j-\min_j x_j}$",
      "Q7_fidelity": r"$K_{fid}(A,B)=|\langle\psi_A|\psi_B\rangle|^2,\qquad \langle\psi^A_{FRQI}|\psi^B_{FRQI}\rangle=\frac{1}{N}\sum_i\cos(\theta^A_i-\theta^B_i)$",
      "Q8_f1": r"$F1_c=\frac{2\,P_c R_c}{P_c+R_c},\qquad \mathrm{macro}\text{-}F1=\frac{1}{6}\sum_{c=1}^{6}F1_c$"}
for k, t in EQ.items():
    fig = plt.figure(figsize=(0.1, 0.1)); fig.text(0, 0, t, fontsize=15, color=INK)
    fig.savefig(OUT / f"{k}.png", dpi=300, bbox_inches="tight", pad_inches=0.06, transparent=False, facecolor="white"); plt.close(fig)
print("equations written")
