"""Model figures for the project report -> research_paper_visuals/Project_Report/figures/ (PNG, 300 dpi).
  C1–C7  circuit drawings: the project's own FRQI / NEQR encoders (src/frqi, src/neqr), the three QKC feature maps
         (same gate sequence as src/v2/qkernel.py), the VQC ansatz (src/v2/vqc.py structure) and the swap test.
  M1     architecture diagram of every model family (schematic).
  M2–M4  model-family metrics, timings and all 163 selected models — read from the running API (/api/v4/families,
         /api/v4/all-models), i.e. from the saved result files. No number is typed by hand.
Run (needs pylatexenc for Qiskit's matplotlib drawer, so use an isolated env):
  uvx --with qiskit==2.5.2 --with pylatexenc --with matplotlib --with numpy python research_paper_visuals/source/make_report_model_figures.py
"""
import json
import sys
import urllib.request
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from qiskit import QuantumCircuit, QuantumRegister

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.frqi.encoder import FRQIEncoder  # noqa: E402
from src.neqr.encoder import NEQREncoder  # noqa: E402

OUT = ROOT / "research_paper_visuals/Project_Report/figures"
OUT.mkdir(parents=True, exist_ok=True)
API = "http://127.0.0.1:8000"
BLUE, ORANGE, AQUA, GREY, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#1baf7a", "#8a939d", "#1a1a1a", "#5b6470", "#e6e8eb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": "#b8bec6", "axes.spines.top": False,
                     "axes.spines.right": False, "xtick.color": MUTED, "ytick.color": MUTED, "legend.frameon": False})
STYLE = {"name": "iqp", "fontsize": 11}


def save_circuit(qc, name, scale=0.9):
    fig = qc.draw("mpl", style=STYLE, scale=scale, fold=40)
    fig.savefig(OUT / f"{name}.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def get(p):
    with urllib.request.urlopen(API + p, timeout=120) as r:
        return json.loads(r.read())


# ── C1 / C2: the project's real encoders on a 2×2 image ──
img = np.array([[0.20, 0.60], [0.90, 0.40]])
save_circuit(FRQIEncoder(img).build_circuit(), "C1_frqi_circuit_2x2")
save_circuit(NEQREncoder(np.round(img * 3).astype(int), intensity_bits=2).build_circuit(), "C2_neqr_circuit_2x2")

# ── C3–C5: QKC feature maps (gate sequence of src/v2/qkernel.py) on 4 example angles ──
x = [0.6, 1.4, 2.2, 0.9]


def feature_map(fmap):
    q = QuantumRegister(4, "q"); qc = QuantumCircuit(q, name=fmap)
    if fmap == "product_ry":
        for i, v in enumerate(x):
            qc.ry(v, i)
        return qc
    qc.h(range(4))
    for i, v in enumerate(x):
        qc.p(2 * v, i)
    pairs = [(i, j) for i in range(4) for j in range(i + 1, 4) if fmap == "zz_full" or j == i + 1]
    for i, j in pairs:
        qc.cx(i, j); qc.p(2 * (np.pi - x[i]) * (np.pi - x[j]), j); qc.cx(i, j)
    return qc


save_circuit(feature_map("product_ry"), "C3_product_ry")
save_circuit(feature_map("zz_linear"), "C4_zz_linear")
save_circuit(feature_map("zz_full"), "C5_zz_full", scale=0.75)

# ── C6: VQC ansatz (RY encoding, L = 2 layers of trainable RY·RZ + CNOT ring; src/v2/vqc.py) ──
vqc = QuantumCircuit(4)
for i, v in enumerate(x):
    vqc.ry(v, i)
vqc.barrier()
rng = np.random.default_rng(0)
for layer in range(2):
    for i in range(4):
        vqc.ry(round(float(rng.normal(0, 0.5)), 2), i); vqc.rz(round(float(rng.normal(0, 0.5)), 2), i)
    for i in range(4):
        vqc.cx(i, (i + 1) % 4)
    vqc.barrier()
vqc.measure_all(add_bits=True)
save_circuit(vqc, "C6_vqc_ansatz", scale=0.75)

# ── C7: swap test between two patch registers (estimates Tr(ρσ)) ──
anc, a, b = QuantumRegister(1, "anc"), QuantumRegister(3, "patch A"), QuantumRegister(3, "patch B")
sw = QuantumCircuit(anc, a, b)
sw.h(anc[0])
for k in range(3):
    sw.cswap(anc[0], a[k], b[k])
sw.h(anc[0])
sw.measure_all(add_bits=True)
save_circuit(sw, "C7_swap_test")


# ── M1: architecture of every model family ──
def box(ax, x, y, w, h, text, quantum=False, accent=False):
    fc = "#fde8dc" if quantum else ("#e3f5ec" if accent else "#eef4fc")
    ec = ORANGE if quantum else (AQUA if accent else BLUE)
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=7.4, color=INK)


rows = [
    ("Classical RBF-SVM\n(baseline)", [("Image", 0), ("Pixels / texture /\nCNN features", 0), ("PCA → k", 0), ("RBF kernel\nexp(−γ‖x−y‖²)", 0), ("SVM", 0), ("Class", 0)]),
    ("QKC\n(quantum kernel)", [("Image", 0), ("Features", 0), ("PCA → k angles", 0), ("Feature map U(x)\nk qubits", 1), ("|⟨φ(x)|φ(y)⟩|²", 1), ("SVM → class", 0)]),
    ("PQK\n(projected kernel)", [("Image", 0), ("Features", 0), ("PCA → k angles", 0), ("Feature map U(x)\nk qubits", 1), ("Bloch vector\nper qubit", 1), ("RBF + SVM", 0)]),
    ("VQC\n(variational)", [("Image", 0), ("Features", 0), ("PCA → k angles", 0), ("RY encoding +\nL trained layers", 1), ("⟨Z⟩ readout", 1), ("Softmax → class", 0)]),
    ("Hybrid\n(CNN + quantum)", [("Image", 0), ("Frozen\nMobileNetV3", 2), ("576 → PCA k", 0), ("Feature map U(x)\nk qubits", 1), ("Kernel", 1), ("SVM → class", 0)]),
    ("Patch-ensemble\n(proposed, V4)", [("Image", 0), ("Stretch +\np×p patches", 0), ("FRQI / NEQR\nper patch |ψₖ⟩", 1), ("mixed state\nρ = avg |ψₖ⟩⟨ψₖ|", 1), ("Tr(ρ_A ρ_B)\n(swap test)", 1), ("SVM → class", 0)]),
]
fig, ax = plt.subplots(figsize=(11.5, 7.6))
ax.set_xlim(0, 23.2); ax.set_ylim(0, len(rows) * 2.1 + 0.6); ax.axis("off")
for r, (label, steps) in enumerate(rows):
    y = (len(rows) - 1 - r) * 2.1 + 0.55
    ax.text(0.1, y + 0.65, label, ha="left", va="center", fontsize=9, fontweight="bold", color=INK)
    for k, (t, kind) in enumerate(steps):
        x0 = 4.6 + k * 3.05
        box(ax, x0, y, 2.6, 1.3, t, quantum=kind == 1, accent=kind == 2)
        if k < len(steps) - 1:
            ax.add_patch(FancyArrowPatch((x0 + 2.62, y + 0.65), (x0 + 3.03, y + 0.65), arrowstyle="-|>", mutation_scale=9, color=MUTED, lw=1))
for lab, fc, ec, xx in [("classical step", "#eef4fc", BLUE, 4.6), ("quantum step (exact CPU simulation)", "#fde8dc", ORANGE, 8.6), ("frozen pretrained CNN", "#e3f5ec", AQUA, 15.6)]:
    ax.add_patch(FancyBboxPatch((xx, 0.02), 0.45, 0.3, boxstyle="round,pad=0.01", fc=fc, ec=ec)); ax.text(xx + 0.6, 0.17, lab, va="center", fontsize=8.5, color=MUTED)
fig.savefig(OUT / "M1_model_architectures.png", dpi=300, bbox_inches="tight", facecolor="white"); plt.close(fig)

# ── M2 / M3: model-family metrics and timings (V3, validation-selected representatives) ──
fam = get("/api/v4/families")["families"]
NAMES = {"qkc": "QKC", "pqk": "PQK", "vqc": "VQC", "hybrid": "Hybrid", "rbfsvm": "RBF-SVM"}
labels = [NAMES.get(f["key"], f["key"]) for f in fam]
metrics = [("Accuracy", "test_accuracy"), ("Precision", "test_precision_macro"), ("Recall", "test_recall_macro"), ("F1", "test_f1_macro")]
cols = [BLUE, AQUA, ORANGE, "#6250d6"]
fig, ax = plt.subplots(figsize=(9.5, 4.2))
w = 0.2; xs = np.arange(len(fam))
for m, ((name, key), col) in enumerate(zip(metrics, cols)):
    vals = [100 * (f[key]["mean"] or 0) for f in fam]
    bars = ax.bar(xs + (m - 1.5) * w, vals, w * 0.92, color=col, label=name, edgecolor="white", lw=0.5)
    for b_, v in zip(bars, vals):
        ax.text(b_.get_x() + b_.get_width() / 2, v + 0.8, f"{v:.0f}", ha="center", fontsize=7, color=MUTED)
ax.set_xticks(xs, [f"{l}\n{f['n_qubits'] or '—'} qubits" for l, f in zip(labels, fam)])
ax.set_ylabel("Locked-test score (%)"); ax.set_ylim(0, 108); ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.13))
fig.savefig(OUT / "M2_family_metrics.png", dpi=300, bbox_inches="tight", facecolor="white"); plt.close(fig)

fig, axs = plt.subplots(1, 2, figsize=(9.5, 3.4))
for ax, (title, key, unit, scale) in zip(axs, [("Training time per run", "train_time_s", "s", 1), ("Inference time per image", "inference_ms_per_image", "ms", 1)]):
    vals = [f[key]["mean"] * scale for f in fam]
    bars = ax.barh(labels, vals, color=[ORANGE if l != "RBF-SVM" else AQUA for l in labels], edgecolor="white")
    ax.set_xscale("log"); ax.set_title(title + " (log scale)", fontsize=9.5, loc="left"); ax.invert_yaxis(); ax.grid(axis="x", color=GRID)
    for b_, v in zip(bars, vals):
        ax.text(v * 1.15, b_.get_y() + b_.get_height() / 2, f"{v:.3g} {unit}", va="center", fontsize=7.5, color=MUTED)
    ax.set_xlim(min(vals) / 3, max(vals) * 12)
fig.tight_layout(); fig.savefig(OUT / "M3_family_timing.png", dpi=300, bbox_inches="tight", facecolor="white"); plt.close(fig)

# ── M4: every selected model of V2–V4 (163) ──
models = get("/api/v4/all-models")["models"]
kind = lambda k: k if k in ("quantum", "hybrid", "classical") else ("control" if k == "control" else "classical")
COL = {"quantum": BLUE, "hybrid": ORANGE, "classical": AQUA, "control": GREY}
fig, ax = plt.subplots(figsize=(9.5, 3.6))
for r, proto in enumerate(["V2", "V3", "V4"]):
    ms_ = sorted([m for m in models if m["protocol"] == proto], key=lambda m: m["test_accuracy"])
    rng = np.random.default_rng(r)
    for m in ms_:
        k = kind(m["kind"])
        ax.scatter(100 * m["test_accuracy"], r + rng.uniform(-0.28, 0.28), s=22, color=COL[k], edgecolor="white", lw=0.4,
                   marker="o" if k != "control" else "D", zorder=3)
ax.axvline(100 / 6, ls="--", color=GREY, lw=0.8); ax.text(100 / 6 + 0.6, -0.42, "chance (16.7 %)", fontsize=7.5, color=MUTED)
ax.set_yticks([0, 1, 2], ["V2 (88)", "V3 (70)", "V4 (5)"]); ax.set_xlabel("Locked-test accuracy (%) — one dot per selected model, mean over 3 seeds")
ax.set_xlim(0, 100); ax.grid(axis="x", color=GRID); ax.set_axisbelow(True)
for k, lab in [("quantum", "quantum"), ("hybrid", "hybrid (CNN + quantum)"), ("classical", "classical"), ("control", "quantum controls / ablations")]:
    ax.scatter([], [], color=COL[k], marker="o" if k != "control" else "D", label=lab)
ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.16), fontsize=8)
fig.savefig(OUT / "M4_all_models.png", dpi=300, bbox_inches="tight", facecolor="white"); plt.close(fig)
print("wrote", sorted(p.name for p in OUT.glob("[CM][0-9]_*.png")))
