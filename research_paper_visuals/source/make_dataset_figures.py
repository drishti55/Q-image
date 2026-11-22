"""Before/after image figures for the report, built only from real NEU-DET images, the saved reconstructions of
results/qml_v4/reconstruction_full (real Qiskit circuits, Aer statevector + multinomial shots) and the saved
locked-test predictions of the frozen V4 FRQI model. Nothing is re-trained or re-selected.

Writes Fig16-Fig22 (pdf + png @300 dpi) to research_paper_visuals/V4_paper_pack/figures and copies the PDFs to
research_paper_visuals/Overleaf_Group02/figures.
Run: .venv/bin/python research_paper_visuals/source/make_dataset_figures.py
"""
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts/v4")]
from src.v2.dataset import preprocess_image  # noqa: E402
import src.v2.paths as P  # noqa: E402
from src.v4.models import mixed_states, stretch  # noqa: E402

spec = importlib.util.spec_from_file_location("ra", ROOT / "scripts/v4/reconstruct_all.py")
ra = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ra)

OUT = ROOT / "research_paper_visuals/V4_paper_pack/figures"
OVL = ROOT / "research_paper_visuals/Overleaf_Group02/figures"
REC = ROOT / "results/qml_v4/reconstruction_full"
V4 = ROOT / "results/qml_v4"
DS = P.dataset_root()
IMGS = ra.images()                       # same order as every reconstructions.npz
CL = ["crazing", "inclusion", "patches", "pitted_surface", "rolled-in_scale", "scratches"]
CLN = ["crazing", "inclusion", "patches", "pitted surface", "rolled-in scale", "scratches"]
PER = 240                                # train-folder images per class in IMGS (trainval first)
PICK = [PER * c + 5 for c in range(6)]   # one fixed training image per class for the method figures
INK, MUTED = "#1a1a1a", "#5b6470"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "pdf.fonttype": 42, "svg.fonttype": "none"})

_npz = {}


def rec(method, mode):
    if method not in _npz:
        _npz[method] = np.load(REC / method / "reconstructions.npz")
    return _npz[method][mode].astype(np.float64)


def raw(i):
    with Image.open(DS / IMGS[i]["rel_path"]) as im:
        return np.asarray(im.convert("L"), dtype=np.float64) / 255.0


def mse(a, b):
    return float(np.mean((a - b) ** 2))


def show(ax, img, title=None, vmin=0, vmax=1, cmap="gray"):
    ax.imshow(img, cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color("#c8cdd3"); s.set_linewidth(0.5)
    if title:
        ax.set_title(title, fontsize=7, color=INK, pad=2)


def grid(rows, cols, w=1.05, h=1.08, left=0.9, top=0.42):
    fig, axs = plt.subplots(rows, cols, figsize=(left + w * cols, top + 0.03 + h * rows), squeeze=False)
    fig.subplots_adjust(left=left / (left + w * cols), right=0.995, top=1 - top / (top + 0.03 + h * rows), bottom=0.02, wspace=0.08, hspace=0.32)
    return fig, axs


def row_labels(fig, axs, labels):
    for r, lab in enumerate(labels):
        axs[r, 0].set_ylabel(lab, fontsize=8, color=INK, rotation=0, ha="right", va="center", labelpad=6)


def save(fig, name, note):
    fig.text(0.995, 0.003, note, ha="right", va="bottom", fontsize=5.5, color=MUTED)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=300)
    plt.close(fig)
    shutil.copy(OUT / f"{name}.pdf", OVL / f"{name}.pdf")
    print("wrote", name)


# ── Fig16: dataset samples ──────────────────────────────────────────────────────────────────────
fig, axs = grid(6, 6, w=1.0, h=1.02)
for c in range(6):
    for k in range(6):
        i = PER * c + 7 + 38 * k
        show(axs[c, k], raw(i), IMGS[i]["rel_path"].split("/")[-1].replace(".jpg", "") if c == 0 or True else None)
row_labels(fig, axs, CLN)
fig.suptitle("NEU-DET: six training images per defect class (original 200×200 grayscale)", fontsize=9, y=0.995)
save(fig, "Fig16_dataset_samples", "Source: NEU-DET train folder, unmodified.")

# ── Fig17: preprocessing and the V4 representation, per class ─────────────────────────────────
H = json.loads((V4 / "aggregates/v4_results.json").read_text())
fr = H["groups"][H["headlines"]["frqi"]]["params"]          # frozen FRQI settings (64, p8, s4, stretch, b=4)
fig, axs = grid(6, 5, w=1.25, h=1.22)
for r, i in enumerate(PICK):
    x64 = preprocess_image(DS / IMGS[i]["rel_path"], fr["image_size"])
    xs = stretch(x64[None])[0] if fr["norm"] == "stretch" else x64
    show(axs[r, 0], raw(i), "(a) original 200×200" if r == 0 else None)
    show(axs[r, 1], x64, "(b) resized 64×64" if r == 0 else None)
    show(axs[r, 2], xs, "(c) contrast stretch" if r == 0 else None)
    show(axs[r, 3], xs, "(d) 8×8 patches" if r == 0 else None)
    for a in range(0, 64, 8):
        axs[r, 3].axhline(a - 0.5, color="#2a78d6", lw=0.35); axs[r, 3].axvline(a - 0.5, color="#2a78d6", lw=0.35)
    axs[r, 3].add_patch(Rectangle((19.5, 27.5), 8, 8, fill=False, ec="#eb6834", lw=1.0))
    rho = mixed_states(x64[None], {"bits": None, **fr}).reshape(128, 128)
    m = np.abs(rho).max()
    show(axs[r, 4], rho, "(e) mixed state ρ" if r == 0 else None, vmin=-m, vmax=m, cmap="RdBu_r")
row_labels(fig, axs, CLN)
fig.suptitle("Before and after preprocessing and patch-ensemble encoding (frozen V4 FRQI settings)", fontsize=9, y=0.995)
save(fig, "Fig17_preprocessing_and_mixed_state",
     "(d) grid shows non-overlapping 8×8 blocks for clarity; the model uses stride 4 (225 overlapping patches). (e) real ρ from the 7-qubit FRQI patch states.")

# ── Fig18: FRQI whole-image reconstruction before/after, shots ────────────────────────────────
modes = [("statevector", "exact statevector"), ("shots100", "100 shots"), ("shots1000", "1,000 shots"),
         ("shots10000", "10,000 shots"), ("shots100000", "100,000 shots")]
fig, axs = grid(6, 6)
for r, i in enumerate(PICK):
    ref = preprocess_image(DS / IMGS[i]["rel_path"], 16)
    show(axs[r, 0], ref, "before: 16×16 input" if r == 0 else None)
    for k, (m, lab) in enumerate(modes, 1):
        y = rec("R-FRQI-16x16", m)[i]
        show(axs[r, k], np.clip(y, 0, 1), None)
        axs[r, k].set_title((lab + "\n" if r == 0 else "") + f"MSE {mse(y, ref):.1e}", fontsize=6.5, pad=2)
row_labels(fig, axs, CLN)
fig.suptitle("FRQI (9 qubits): image before encoding and after measurement + decoding", fontsize=9, y=0.995)
save(fig, "Fig18_frqi_before_after", "Real Qiskit FRQI circuits; Qiskit-Aer statevector and multinomial shot sampling; project decoder.")

# ── Fig19: NEQR before/after, bit depth and shots ─────────────────────────────────────────────
cols = [("R-NEQR-16x16-b2", "statevector", "2-bit, exact"), ("R-NEQR-16x16-b4", "statevector", "4-bit, exact"),
        ("R-NEQR-16x16-b8", "statevector", "8-bit, exact"), ("R-NEQR-16x16-b4", "shots100", "4-bit, 100 shots"),
        ("R-NEQR-16x16-b4", "shots1000", "4-bit, 1,000 shots")]
fig, axs = grid(6, 6)
for r, i in enumerate(PICK):
    ref = preprocess_image(DS / IMGS[i]["rel_path"], 16)
    show(axs[r, 0], ref, "before: 16×16 input" if r == 0 else None)
    for k, (meth, m, lab) in enumerate(cols, 1):
        y = rec(meth, m)[i]
        show(axs[r, k], np.clip(y, 0, 1))
        axs[r, k].set_title((lab + "\n" if r == 0 else "") + f"MSE {mse(y, ref):.1e}", fontsize=6.5, pad=2)
row_labels(fig, axs, CLN)
fig.suptitle("NEQR (10–16 qubits): image before encoding and after measurement + decoding", fontsize=9, y=0.995)
save(fig, "Fig19_neqr_before_after", "Real Qiskit NEQR circuits; Qiskit-Aer statevector and multinomial shot sampling; unobserved pixels decode as 0.")

# ── Fig20: what whole-image encodings see (resolution) ─────────────────────────────────────────
fig, axs = grid(6, 6)
for r, i in enumerate(PICK):
    show(axs[r, 0], raw(i), "original\n200×200" if r == 0 else None)
    show(axs[r, 1], preprocess_image(DS / IMGS[i]["rel_path"], 64), "resized\n64×64" if r == 0 else None)
    for k, s in enumerate((16, 8, 4, 2), 2):
        show(axs[r, k], np.clip(rec(f"R-FRQI-{s}x{s}", "statevector")[i], 0, 1),
             f"FRQI {s}×{s}\n{2 * int(np.log2(s)) + 1} qubits" if r == 0 else None)
row_labels(fig, axs, CLN)
fig.suptitle("Image detail available to whole-image FRQI encodings at each resolution", fontsize=9, y=0.995)
save(fig, "Fig20_resolution_whole_image", "FRQI columns: exact statevector reconstruction of the downsampled image.")

# ── Fig21: V4 patch representation and classical PCA, before/after ────────────────────────────
cols = [("P-FRQI-64-p8", "shots100", "FRQI patches\n100 shots/patch"), ("P-FRQI-64-p8", "shots1000", "FRQI patches\n1,000 shots/patch"),
        ("P-FRQI-64-p8", "shots10000", "FRQI patches\n10,000 shots/patch"), ("P-NEQR-64-p4-b4", "shots1000", "NEQR 4-bit patches\n1,000 shots/patch"),
        ("C-PCA8-64", "reconstruction", "classical PCA\n8 components"), ("C-PCA12-64", "reconstruction", "classical PCA\n12 components")]
fig, axs = grid(6, 7, h=1.1, top=0.62)
for r, i in enumerate(PICK):
    ref = preprocess_image(DS / IMGS[i]["rel_path"], 64)
    show(axs[r, 0], ref, "before: 64×64 input" if r == 0 else None)
    for k, (meth, m, lab) in enumerate(cols, 1):
        y = rec(meth, m)[i]
        show(axs[r, k], np.clip(y, 0, 1))
        axs[r, k].set_title((lab + "\n" if r == 0 else "") + f"MSE {mse(y, ref):.1e}", fontsize=6.2, pad=2)
row_labels(fig, axs, CLN)
fig.suptitle("64×64 images rebuilt from the V4 patch representations and from classical PCA", fontsize=9, y=0.997)
save(fig, "Fig21_patch_and_pca_before_after", "Patch rows: every patch encoded and measured separately, then re-assembled. PCA fit on the seed-0 training split.")

# ── Fig22: locked-test classification examples of the frozen V4 FRQI model ─────────────────────
eid = H["groups"][H["headlines"]["frqi"]]["experiment_ids"][0]
pr = pd.read_csv(V4 / "experiments" / eid / "predictions.csv")
pr = pr[pr["split"] == "test"]
fig, axs = grid(6, 5, w=1.3, h=1.3, top=0.5)
for c, cname in enumerate(CL):
    sub = pr[pr["true_class"] == cname]
    ok, bad = sub[sub.y_true == sub.y_pred].head(3), sub[sub.y_true != sub.y_pred].head(2)
    picks = list(ok.itertuples()) + list(bad.itertuples())
    picks += list(sub[sub.y_true == sub.y_pred].iloc[3:3 + 5 - len(picks)].itertuples())
    for k, row in enumerate(picks[:5]):
        with Image.open(DS / row.image) as im:
            img = np.asarray(im.convert("L"), dtype=np.float64) / 255.0
        good = row.y_true == row.y_pred
        show(axs[c, k], img)
        for s in axs[c, k].spines.values():
            s.set_color("#2f9e6b" if good else "#d1432f"); s.set_linewidth(2.0)
        axs[c, k].set_title("✓ correct" if good else "✗ wrong, predicted\n" + row.pred_class.replace("_", " "),
                            fontsize=6.5, color="#1f7a52" if good else "#b3321f", pad=2)
row_labels(fig, axs, CLN)
fig.suptitle("Frozen V4 FRQI model on locked-test images (seed 0)\ngreen = correct, red = misclassified", fontsize=9, y=0.995)
save(fig, "Fig22_classification_examples", f"Saved predictions of {eid}; images from the NEU-DET validation folder (locked test).")
