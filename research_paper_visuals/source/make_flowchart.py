"""Methodology flowchart (Protocol V2) -> flowchart/methodology_flowchart.{svg,pdf,png}.
Every box states a step recorded in results/qml_v2 (manifest, split files, selection files, analysis.json,
reconstruction configs). Editable: this script, the SVG (text kept as text) and flowchart/methodology_flowchart_tikz.tex."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "flowchart"
OUT.mkdir(exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "none", "pdf.fonttype": 42})

BLUE, ORANGE, AQUA, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#6b6b6b"
FILL = {"data": "#eef3fb", "classical": "#e8f0fb", "quantum": "#e6f6ef", "hybrid": "#fdeee6", "eval": "#f3f3f3"}
EDGE = {"data": BLUE, "classical": BLUE, "quantum": AQUA, "hybrid": ORANGE, "eval": GREY}

fig = plt.figure(figsize=(6.3, 8.4))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 100)
ax.set_ylim(0, 133)
ax.axis("off")


def box(x, y, w, h, title, body, kind, fs=6.6):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=1.2", fc=FILL[kind], ec=EDGE[kind], lw=1.0))
    ax.text(x + w / 2, y + h - 1.6, title, ha="center", va="top", fontsize=fs + 0.6, fontweight="bold", color="#1a1a1a")
    ax.text(x + w / 2, y + h - 5.0, body, ha="center", va="top", fontsize=fs, color="#333333", linespacing=1.25)
    return (x, y, w, h)


def arrow(p, q, color=GREY):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=8, lw=0.9, color=color, shrinkA=1, shrinkB=1))


# 1. data
b1 = box(20, 121, 60, 10.5, "NEU-DET steel-surface defect dataset",
         "1,800 grayscale images, 200×200 px, 6 classes (300 per class)\nSHA-256 manifest of every file", "data")
b2 = box(5, 104, 42, 13, "Locked test set",
         "NEU validation folder: 360 images\n(60 per class); read once, only after\nmodel selection", "data")
b3 = box(53, 104, 42, 13, "Train-folder pool (1,440 images)",
         "group-blocked split (blocks of 20 files)\n1,080 train / 360 validation\nseeds 0, 1, 2", "data")
arrow((40, 121), (26, 117.4))
arrow((60, 121), (74, 117.4))
b4 = box(20, 91, 60, 9, "Preprocessing", "grayscale → bilinear resize to s×s → intensities / 255", "data")
arrow((74, 104), (60, 100.3))

# 2. four method lanes
lanes = [
    (6, "Quantum image encoding", "FRQI: θᵢ = (π/2)·b·Iᵢ\n(b = 1; angle-scaled b = 2, 4, 8)\nNEQR: 2 / 4 / 8-bit basis states\nresolutions 2×2 … 16×16\n↓\nexact state-overlap kernel\n|⟨Iₐ|I_b⟩|² (+10²–10⁴ shots)\n↓ SVM (C by validation)", "quantum"),
    (29.5, "Quantum feature models", "64×64 → PCA k = 4 / 6 / 8\n→ angles in [0, π]\n↓\nQKC: product-RY, ZZ-linear,\nZZ-full (+10²–5·10³ shots) → SVM\n↓\nVQC: RY encoding, RY/RZ layers,\nCNOT ring; parameter-shift +\nAdam / COBYLA / SPSA", "quantum"),
    (53, "Classical baselines", "PCA k = 4 / 6 / 8 →\nRBF-SVM / logistic regression\n(also on the identical\nangle features of the QKC)\n↓\nsmall CNN (128×128)\n↓\nfrozen MobileNetV3 (576-d)\n→ logistic regression / SVM", "classical"),
    (76.5, "Hybrid models", "frozen MobileNetV3 576-d\n→ PCA k = 4 / 6 / 8\n↓\nQKC (product-RY / ZZ) → SVM\nVQC\n↓\nmatched classical controls\non identical features:\nRBF-SVM, logistic regression", "hybrid"),
]
LY, LH = 63, 24
for x, t, body, kind in lanes:
    box(x, LY, 22.5, LH, t, body, kind, fs=5.7)
    arrow((50, 91), (x + 11.25, LY + LH + 0.4), color=EDGE[kind])

# 3. selection + single locked test
b5 = box(6, 41, 93, 11, "Model selection (validation only)",
         "every configuration × 3 seeds: fit on train, score on validation\nselect max mean validation macro-F1; configurations with a failed seed are ineligible", "eval")
for x, _, _, kind in lanes:
    arrow((x + 11.25, LY - 0.3), (x + 11.25, 52.4), color=GREY)
b6 = box(6, 25, 93, 11, "Single locked-test evaluation (360 images, seeds 0–2)",
         "accuracy, macro-F1, precision, recall, per-class F1, confusion matrices,\nbootstrap 95% CI, paired exact McNemar tests on identical features", "eval")
arrow((52.5, 41), (52.5, 36.4))
# locked test set -> final evaluation (dashed, along the left margin)
ax.plot([5, 2.2, 2.2], [110.5, 110.5, 30.5], ls=(0, (3, 2)), lw=0.9, color=GREY)
ax.add_patch(FancyArrowPatch((2.2, 30.5), (5.6, 30.5), arrowstyle="-|>", mutation_scale=8, lw=0.9, color=GREY, ls="--"))
ax.text(3.0, 70, "used only here", rotation=90, fontsize=5.4, color=GREY, ha="center", va="center",
        bbox=dict(fc="white", ec="none", pad=0.6))

# 4. additional analyses (separate tasks, not used for ranking)
ax.text(52.5, 21.3, "Additional analyses of the quantum circuits (separate tasks; not used for model ranking)",
        ha="center", va="center", fontsize=6.2, color=GREY, style="italic")
box(6, 6, 45.5, 13, "Reconstruction study",
    "FRQI / NEQR decoding of 30 training images\n(5 per class), statevector and 10²–10⁵ shots\n→ MSE, PSNR, SSIM", "quantum")
box(53.5, 6, 45.5, 13, "Quantum circuit resources",
    "Qiskit circuits transpiled to {cx, rz, sx, x}\n(optimisation level 1): qubits, gates,\ndepth (logical / compiled)", "quantum")
ax.text(52.5, 2.2, "All quantum circuits were simulated without noise on a CPU (no quantum hardware).",
        ha="center", va="center", fontsize=5.8, color=GREY, style="italic")

for ext, kw in (("svg", {}), ("pdf", {}), ("png", {"dpi": 600})):
    fig.savefig(OUT / f"methodology_flowchart.{ext}", bbox_inches="tight", pad_inches=0.04, **kw)
print("flowchart written")
