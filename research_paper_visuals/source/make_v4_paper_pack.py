"""Protocol V4 paper pack -> research_paper_visuals/V4_paper_pack/
figures/  Fig01–Fig15 (.png 300 dpi, .pdf, .svg) + figures/data/*.csv (the plotted numbers)
tables/   Tab01–Tab10 (.csv, .md, .tex booktabs, .png image for pasting)
data/numbers.json  every number the paper text uses (read by write_v4_paper.py)

Every value is read from saved result files (read-only); nothing is typed by hand. Run from the project root:
    .venv/bin/python research_paper_visuals/source/make_v4_figures.py      # base figures V4-1..V4-4
    .venv/bin/python research_paper_visuals/source/make_v4_paper_pack.py
"""
import csv
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.v2.dataset import preprocess_image  # noqa: E402
from src.v2.paths import dataset_root  # noqa: E402
from src.v4.models import frqi_states, mixed_states, patches, stretch  # noqa: E402

PACK = ROOT / "research_paper_visuals" / "V4_paper_pack"
FIG, TAB, DAT = PACK / "figures", PACK / "tables", PACK / "data"
for d in (FIG / "data", TAB, DAT):
    d.mkdir(parents=True, exist_ok=True)
V4 = ROOT / "results/qml_v4"
D = json.loads((V4 / "aggregates/v4_results.json").read_text())
VER = json.loads((V4 / "aggregates/v4_verification.json").read_text())
A2 = json.loads((ROOT / "results/qml_v2/aggregates/analysis.json").read_text())["selected"]
R3 = {g["group"]: g for g in json.loads((ROOT / "results/qml_v3/aggregates/v3_results.json").read_text())["groups"]}
RS = json.loads((V4 / "reconstruction_full/summary.json").read_text())
REC = RS["records"]
PII = json.loads((V4 / "aggregates/per_image_predictions.json").read_text())
G, REF, H = D["groups"], D["references"], D["headlines"]
CL = ["crazing", "inclusion", "patches", "pitted_surface", "rolled-in_scale", "scratches"]
CLN = ["crazing", "inclusion", "patches", "pitted surface", "rolled-in scale", "scratches"]
QG = ["V4-frqi-p4", "V4-frqi-p8", "V4-neqr-p2", "V4-neqr-p4"]
CTRL = "V4-patchmom-rbfsvm"

BLUE, ORANGE, GREY, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#8a939d", "#1a1a1a", "#5b6470", "#e6e8eb"
LBLUE, LORANGE, GREEN = "#9ec5f4", "#f6b48f", "#2f9e6b"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": "#b8bec6", "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False, "svg.fonttype": "none", "pdf.fonttype": 42, "legend.frameon": False})
SIM = "Exact noiseless CPU simulation (no quantum hardware)."
LBL = {"V4-frqi-p4": "FRQI patches 4×4", "V4-frqi-p8": "FRQI patches 8×8", "V4-neqr-p2": "NEQR patches 2×2",
       "V4-neqr-p4": "NEQR patches 4×4", CTRL: "Classical RBF-SVM, same patches"}
COL = {"V4-frqi-p4": LBLUE, "V4-frqi-p8": BLUE, "V4-neqr-p2": LORANGE, "V4-neqr-p4": ORANGE, CTRL: GREY}
N = {}   # numbers for the paper text


def pct(v, d=1):
    return f"{100 * v:.{d}f}"


def ms(s, d=1):
    return f"{100 * s['mean']:.{d}f} ± {100 * s['std']:.{d}f}"


def save(fig, name, head, rows):
    for ext, kw in (("png", {"dpi": 300}), ("pdf", {}), ("svg", {})):
        fig.savefig(FIG / f"{name}.{ext}", bbox_inches="tight", pad_inches=0.06, facecolor="white", **kw)
    plt.close(fig)
    with open(FIG / "data" / f"{name}.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(head); w.writerows(rows)
    print("figure", name)


def note(fig, text, y=-0.06):
    fig.text(0.0, y, text, fontsize=6.8, color=MUTED, wrap=True)


def n_patches(p):
    return ((p["image_size"] - p["patch"]) // p["stride"] + 1) ** 2


# ════════════════════════════════════════════════════════════ TABLES
TEX_ESC = str.maketrans({"_": r"\_", "%": r"\%", "&": r"\&", "#": r"\#", "±": r"$\pm$", "×": r"$\times$", "≥": r"$\geq$",
                         "ρ": r"$\rho$", "γ": r"$\gamma$", "Δ": r"$\Delta$", "−": "--", "<": r"$<$", "→": r"$\rightarrow$", "θ": r"$\theta$"})
TABLES = []


def table(name, title, head, rows, notes=""):
    rows = [[str(c) for c in r] for r in rows]
    with open(TAB / f"{name}.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(head); w.writerows(rows)
    md = f"**{title}**\n\n| " + " | ".join(head) + " |\n|" + "---|" * len(head) + "\n" + "\n".join("| " + " | ".join(r) + " |" for r in rows)
    if notes:
        md += f"\n\n*{notes}*"
    (TAB / f"{name}.md").write_text(md + "\n")
    tex = ["\\begin{table}[t]", "\\centering", "\\small", f"\\caption{{{title.translate(TEX_ESC)}}}", f"\\label{{tab:{name.split('_')[0].lower()}}}",
           "\\resizebox{\\linewidth}{!}{%", "\\begin{tabular}{" + "l" * len(head) + "}", "\\toprule",
           " & ".join(h.translate(TEX_ESC) for h in head) + r" \\", "\\midrule"]
    tex += [" & ".join(c.translate(TEX_ESC) for c in r) + r" \\" for r in rows]
    tex += ["\\bottomrule", "\\end{tabular}}"]
    if notes:
        tex.append(f"\\par\\smallskip\\footnotesize {notes.translate(TEX_ESC)}")
    tex.append("\\end{table}")
    (TAB / f"{name}.tex").write_text("\n".join(tex) + "\n")
    # PNG image of the table (paste-ready)
    import textwrap
    cells = [["\n".join(textwrap.wrap(c, 38)) or c for c in r] for r in rows]
    cw = [max([1] + [max(len(x) for x in c.split("\n")) for c in col]) for col in zip(*cells)]
    hd = ["\n".join(textwrap.wrap(h, max(cw[i], 9), break_long_words=False)) for i, h in enumerate(head)]
    width = [max(cw[i], max(len(x) for x in hd[i].split("\n"))) + 2 for i in range(len(head))]
    nl = [max(c.count("\n") + 1 for c in r) for r in cells]
    hl = max(h.count("\n") + 1 for h in hd)
    unit = 0.2
    th = unit * (hl + sum(nl) + 0.35 * (len(rows) + 1))
    fw = max(4.5, 0.066 * sum(width))
    fig = plt.figure(figsize=(fw, th + 0.55 + (0.6 if notes else 0)))
    ax = fig.add_axes([0, (0.6 if notes else 0) / fig.get_figheight(), 1, th / fig.get_figheight()]); ax.axis("off")
    t = ax.table(cellText=cells, colLabels=hd, bbox=[0, 0, 1, 1], cellLoc="left", colLoc="left", colWidths=[w / sum(width) for w in width])
    t.auto_set_font_size(False); t.set_fontsize(8)
    tot = hl + sum(nl) + 0.35 * (len(rows) + 1)
    for (r, c), cell in t.get_celld().items():
        cell.set_edgecolor("#d0d5db"); cell.set_linewidth(0.6); cell.PAD = 0.04
        cell.set_height(((hl if r == 0 else nl[r - 1]) + 0.35) / tot)
        if r == 0:
            cell.set_facecolor("#eef2f7"); cell.get_text().set_fontweight("bold")
    fig.text(0.0, 1 - 0.12 / fig.get_figheight(), title, fontsize=9.5, fontweight="bold", color=INK, va="top")
    if notes:
        fig.text(0.0, 0.02, "\n".join(textwrap.wrap(notes, int(sum(width) * 1.1))), fontsize=7, color=MUTED, va="bottom")
    fig.savefig(TAB / f"{name}.png", dpi=250, bbox_inches="tight", pad_inches=0.08, facecolor="white")
    plt.close(fig)
    TABLES.append((name, title, head, rows, notes))
    print("table", name)


# Tab01 dataset and splits
splits = {s: json.loads(next((V4 / "manifests/splits").glob(f"split-s{s}-*.json")).read_text()) for s in (0, 1, 2)}
cnt = {role: Counter(p.split("/")[2] for p in splits[0][role]) for role in ("train", "val", "test")}
same = all({r: Counter(p.split("/")[2] for p in splits[s][r]) for r in ("train", "val", "test")} == cnt for s in (1, 2))
assert same, "class counts differ between seeds"
t1 = [[n, cnt["train"][c], cnt["val"][c], cnt["test"][c], cnt["train"][c] + cnt["val"][c] + cnt["test"][c]] for c, n in zip(CL, CLN)]
t1.append(["Total"] + [sum(r[i] for r in t1) for i in (1, 2, 3, 4)])
table("Tab01_dataset_splits", "Table 1. NEU-DET dataset and splits (per class; identical counts for seeds 0, 1, 2)",
      ["Class", "Train", "Validation", "Locked test", "Total"], t1,
      f"Train/validation = group-blocked split of the 1,440 NEU-DET train-folder images ({splits[0]['strategy']}); locked test = the 360 NEU-DET validation-folder images, read once per frozen model.")
N["dataset"] = {"n": t1[-1][4], "train": t1[-1][1], "val": t1[-1][2], "test": t1[-1][3], "classes": len(CL), "strategy": splits[0]["strategy"]}

# Tab02 search space
SEL = {g: json.loads((V4 / f"aggregates/selection/{g}.json").read_text()) for g in QG + [CTRL]}
t2 = []
for g in QG + [CTRL]:
    cs = SEL[g]["candidates"]
    geo = sorted({(c["params"]["image_size"], c["params"]["patch"], c["params"]["stride"]) for c in cs})
    vals = lambda k: sorted({c["params"][k] for c in cs if k in c["params"]})  # noqa: E731
    extra = (f"angle ×{', '.join(f'{v:g}' for v in vals('angle_scale'))}" if "frqi" in g else
             f"{', '.join(map(str, vals('bits')))} bits" if "neqr" in g else f"γ {', '.join(f'{v:g}' for v in vals('gamma'))}")
    t2.append([LBL[g], "; ".join(f"{s}² p{p} s{st}" for s, p, st in geo), extra, ", ".join(vals("norm")),
               ", ".join(f"{v:g}" for v in vals("C")), len(cs), 3 * len(cs)])
t2.append(["Total", "", "", "", "", sum(r[5] for r in t2), sum(r[6] for r in t2)])
table("Tab02_search_space", "Table 2. Hyper-parameter grid searched on the validation split (test never used)",
      ["Group", "Image size, patch p, stride s", "Encoding option", "Normalisation", "SVM C", "Configs", "Runs (×3 seeds)"], t2,
      "Selection rule: maximum mean validation macro-F1 over seeds 0–2. Selections were SHA-256 frozen before the locked test was read.")
N["search"] = {"configs": t2[-1][5], "runs": t2[-1][6], "failed": D["counts"]["failed_runs"]}

# Tab03 selected configurations
t3 = []
for g in QG + [CTRL]:
    p, c = G[g]["params"], G[g]["circuit"]
    enc = (f"FRQI, angle ×{p['angle_scale']:g}" if p.get("representation") == "FRQI" else
           f"NEQR, {p['bits']}-bit" if p.get("representation") == "NEQR" else f"patch moments, γ={p['gamma']:g}")
    dim = (2 * p["patch"] ** 2 if p.get("representation") == "FRQI" else p["patch"] ** 2 * 2 ** p["bits"] if p.get("representation") == "NEQR" else "—")
    t3.append([LBL[g], f"{p['image_size']}×{p['image_size']}", f"{p['patch']}×{p['patch']} / {p['stride']}", n_patches(p), enc,
               "per-image stretch" if p["norm"] == "stretch" else "none", f"{p['C']:g}", c["n_qubits"] if c else "— (classical)", dim])
table("Tab03_selected_configs", "Table 3. Configurations selected by validation macro-F1",
      ["Group", "Image", "Patch / stride", "Patches per image", "Encoding", "Normalisation", "C", "Qubits per patch state", "State dimension D"], t3,
      "ρ is a D×D density matrix (average of the patch states). FRQI: 2·log2(p)+1 qubits; NEQR: 2·log2(p)+q qubits.")

# Tab04 main results
t4 = [[LBL[g], "quantum (simulated)" if g != CTRL else "classical", pct(G[g]["val_f1_macro"]["mean"]), ms(G[g]["test_accuracy"]),
       ms(G[g]["test_f1_macro"]), ", ".join(pct(x) for x in G[g]["per_seed_test_accuracy"])] for g in QG + [CTRL]]
for rid, lab in (("E1b-frqi8-qkc-scaled", "V2 FRQI, whole image (baseline)"), ("E2-neqr16-b4-qkc", "V2 NEQR, whole image (baseline)"),
                 ("V3-tex12c-rbfsvm", "V3 classical texture RBF-SVM (best classical)")):
    t4.append([lab, "reference", pct(REF[rid]["val_f1_macro"]["mean"]), ms(REF[rid]["test_accuracy"]), ms(REF[rid]["test_f1_macro"]), "—"])
table("Tab04_main_results", "Table 4. Main results on the locked test set (360 images; mean ± s.d. over seeds 0–2)",
      ["Model", "Type", "Validation macro-F1 %", "Test accuracy %", "Test macro-F1 %", "Per-seed test accuracy %"], t4,
      f"Headline models (pre-declared rule, by validation): FRQI = {LBL[H['frqi']]}, NEQR = {LBL[H['neqr']]}. {SIM}")

# Tab05 comparisons
t5 = []
for c in D["comparisons"]:
    t5.append([c["name"], pct(c["acc_a"]), pct(c["acc_b"]), f"{100 * c['diff']:+.1f}", f"[{100 * c['ci95'][0]:+.1f}, {100 * c['ci95'][1]:+.1f}]",
               "<0.001" if c["p_holm"] < 0.001 else f"{c['p_holm']:.3f}", "yes" if c["significant_0_05"] else "no",
               " / ".join(f"{m['a_only_correct']}:{m['b_only_correct']}" for m in c["mcnemar_per_seed"])])
table("Tab05_statistical_comparisons", "Table 5. The 8 pre-declared paired comparisons (Holm-corrected)",
      ["Comparison (a vs b)", "Acc. a %", "Acc. b %", "Δ pp", "95% CI pp", "p (Holm)", "Significant", "McNemar a-only:b-only (seeds 0/1/2)"], t5,
      "Paired sign-flip permutation test (10,000) on per-image correctness averaged over seeds; bootstrap 95% CI; Holm correction over 8 tests.")

# Tab06 per-class F1
t6 = [[LBL[g]] + [pct(G[g]["per_class_f1"][c]["mean"]) for c in CL] for g in QG + [CTRL]]
table("Tab06_per_class_f1", "Table 6. Per-class F1 % on the locked test set (mean over seeds 0–2)", ["Model"] + CLN, t6)

# Tab07 circuit resources
t7 = []
for g in QG:
    c, p = G[g]["circuit"], G[g]["params"]
    t7.append([LBL[g], c["n_qubits"], c["gates_logical"], c["depth_logical"], c["gates_compiled"], c["depth_compiled"], c["cx_compiled"], n_patches(p)])
table("Tab07_circuit_resources", "Table 7. Encoder circuit resources for ONE patch state (Qiskit, transpiled)",
      ["Group", "Qubits", "Logical gates", "Logical depth", "Compiled gates", "Compiled depth", "CX (compiled)", "Patches per image"], t7,
      "Basis {cx, rz, sx, x}, optimisation level 1, all-to-all coupling. A swap test between two patch states uses 2·qubits + 1 qubits.")

# Tab08 reconstruction
t8 = []
sci = lambda v: "0 (exact)" if v < 1e-15 else f"{v:.2e}"  # noqa: E731
for rid, r in REC.items():
    s = r["summary"]["all"]
    if rid.startswith("C-"):
        t8.append([rid, "classical PCA", "—", sci(s["reconstruction"]["vs_preprocessed"]["mse"]["mean"]), "—", "—",
                   f"{s['reconstruction']['vs_preprocessed']['ssim']['mean']:.3f}", "—"])
        continue
    sh = r["config"]["shots"]
    t8.append([rid, r["config"]["representation"], (r["circuit"] or {}).get("n_qubits", "—"), sci(s["statevector"]["vs_preprocessed"]["mse"]["mean"]),
               sci(s["shots1000"]["vs_preprocessed"]["mse"]["mean"]), sci(s[f"shots{sh[-1]}"]["vs_preprocessed"]["mse"]["mean"]) + f" ({sh[-1]:,})",
               f"{s['shots1000']['vs_preprocessed']['ssim']['mean']:.3f}", f"{s['statevector']['n_exact']:,}"])
table("Tab08_reconstruction", f"Table 8. Reconstruction of all {RS['n_images']:,} NEU-DET images by every method (mean MSE / SSIM)",
      ["Method", "Encoding", "Qubits", "MSE exact (statevector)", "MSE 1,000 shots", "MSE most shots", "SSIM 1,000 shots", f"Images exact (of {RS['n_images']:,})"], t8,
      "R- = whole image r×r; NEQR -bN = N-bit intensity; P- = V4 patch representation (shots per patch); C- = classical PCA (fit on seed-0 train). Real Qiskit circuits + Aer statevector + multinomial shots.")

# Tab09 cross-protocol overview
def g2(k):
    return A2[k]["test_accuracy"]


def g3(k):
    return R3[k]["test_accuracy"]


XP = [("V2", "FRQI, whole image (pixel kernel)", "quantum", g2("E1b-frqi8-qkc-scaled")),
      ("V2", "NEQR, whole image (pixel kernel)", "quantum", g2("E2-neqr16-b4-qkc")),
      ("V2", "ZZ-feature-map kernel on pixel PCA-8", "quantum", g2("E3-pca8-qkc-zz_full")),
      ("V2", "Variational classifier (VQC) on pixel PCA-8", "quantum", g2("E4-pca8-vqc")),
      ("V2", "Classical RBF-SVM on pixel PCA-8", "classical", g2("E6-pca8-rbfsvm")),
      ("V3", "ZZ-feature-map kernel on texture PCA-8", "quantum", g3("V3-tex8c-qkc-zz_full")),
      ("V3", "VQC on texture PCA-8", "quantum", g3("V3-tex8c-vqc")),
      ("V3", "Classical RBF-SVM on texture PCA-12", "classical", g3("V3-tex12c-rbfsvm")),
      ("V4", "FRQI patch-ensemble kernel (8×8)", "quantum", G["V4-frqi-p8"]["test_accuracy"]),
      ("V4", "NEQR patch-ensemble kernel (4×4)", "quantum", G["V4-neqr-p4"]["test_accuracy"]),
      ("V4", "Classical RBF-SVM on the same patches", "classical", G[CTRL]["test_accuracy"])]
table("Tab09_cross_protocol", "Table 9. Key models across protocols V2 → V3 → V4 (locked test accuracy %)",
      ["Protocol", "Model", "Type", "Test accuracy %"], [[a, b, c, ms(d)] for a, b, c, d in XP],
      "Same dataset, splits, seeds and locked test set in every protocol. Quantum = exact CPU simulation.")

# Tab10 integrity checks
table("Tab10_integrity_checks", f"Table 10. Automated integrity checks ({sum(c['ok'] for c in VER['checks'])}/{len(VER['checks'])} pass)",
      ["Check", "Result"], [[c["check"], "PASS" if c["ok"] else "FAIL"] for c in VER["checks"]])

# ════════════════════════════════════════════════════════════ FIGURES
# Fig01 methodology flowchart
fig, ax = plt.subplots(figsize=(9.0, 5.6)); ax.set_xlim(-1, 102); ax.set_ylim(0, 72); ax.axis("off")


def box(x, y, w, h, txt, fc="#f3f6fa", ec="#b8c3d0", fs=7.4, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=fc, ec=ec, lw=0.9))
    ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=fs, color=INK, fontweight="bold" if bold else "normal", linespacing=1.25)


def arrow(x1, y1, x2, y2, col="#7d8794"):
    ax.annotate("", (x2, y2), (x1, y1), arrowprops=dict(arrowstyle="-|>", color=col, lw=1.0, shrinkA=0, shrinkB=0))


ax.text(0, 70, "(a) Data protocol", fontsize=8.5, fontweight="bold", color=INK)
box(0, 58, 21, 9, f"NEU-DET\n{N['dataset']['n']:,} images\n6 classes", bold=True)
box(27, 61.5, 22, 7, f"Train folder (1,440)\n→ train {N['dataset']['train']:,} / val {N['dataset']['val']}\nseeds 0, 1, 2 (blocked)")
box(27, 52.5, 22, 7, f"Validation folder ({N['dataset']['test']})\n= LOCKED TEST\nnot read until freeze", fc="#fdeee6", ec=ORANGE)
arrow(21.5, 63.5, 26.5, 65); arrow(21.5, 61, 26.5, 56)
box(55, 58, 21, 9, f"Grid search on\nvalidation only\n{N['search']['configs']} configs × 3 seeds")
box(81, 58, 19, 9, "Select by val\nmacro-F1, then\nSHA-256 freeze")
arrow(49.5, 65, 54.5, 63.5); arrow(76.5, 62.5, 80.5, 62.5)
box(55, 47, 21, 7.5, "Locked test,\nonce per frozen model", fc="#fdeee6", ec=ORANGE)
box(81, 47, 19, 7.5, "Paired permutation\n+ bootstrap CI + McNemar\nHolm over 8 tests", fs=6.8)
arrow(90.5, 57.5, 70, 54.8); arrow(49.5, 55.5, 54.5, 51.5, ORANGE); arrow(76.5, 50.7, 80.5, 50.7)

ax.text(0, 41, "(b) Patch-ensemble mixed-state kernel (one image)", fontsize=8.5, fontweight="bold", color=INK)
steps = [("Grayscale,\nresize to S×S\n(+ optional\ncontrast stretch)", "#f3f6fa"),
         ("Cut into p×p\npatches,\nstride s\n(P patches)", "#f3f6fa"),
         ("Encode each patch\nas FRQI or NEQR\nstate |ψk⟩\n(Qiskit circuit)", "#e8f1fc"),
         ("Mixed state\nρ = (1/P) Σk\n|ψk⟩⟨ψk|", "#e8f1fc"),
         ("Kernel\nK(A,B) = Tr(ρA ρB)\n(swap test)", "#e8f1fc"),
         ("SVM on K\n→ defect class", "#f3f6fa")]
for i, (t, fc) in enumerate(steps):
    x = i * 17
    box(x, 22, 14.5, 14, t, fc=fc, ec=BLUE if fc == "#e8f1fc" else "#b8c3d0", fs=6.8)
    if i:
        arrow(x - 2.3, 29, x - 0.4, 29)
ax.text(51, 19, "quantum part (simulated exactly)", ha="center", fontsize=7, color=BLUE)
ax.plot([34, 82.5], [20.5, 20.5], color=BLUE, lw=0.8)
ax.text(0, 13, "FRQI patch state:   |ψ⟩ = N^(−1/2) Σi (cos θi |0⟩ + sin θi |1⟩) |i⟩,   θi = (π/2)·b·xi          (2·log2 p + 1 qubits)", fontsize=7.2, color=INK)
ax.text(0, 8.5, "NEQR patch state:  |ψ⟩ = N^(−1/2) Σi |ci⟩ |i⟩,   ci = round(xi (2^q − 1))                                    (2·log2 p + q qubits)", fontsize=7.2, color=INK)
ax.text(0, 4, "Kernel:  K(A,B) = Tr(ρA ρB) = mean over patch pairs k,l of |⟨ψk^A | ψl^B⟩|²   — translation-robust because ρ averages over positions.", fontsize=7.2, color=INK)
ax.text(0, 0, "Classical control: identical patches, per-patch moments + RBF-SVM.", fontsize=7.2, color=MUTED)
save(fig, "Fig01_methodology_flowchart", ["step", "text"], [[i + 1, t.replace("\n", " ")] for i, (t, _) in enumerate(steps)])

# Fig02 encoding illustration on a real training image
p8 = {"bits": None, **G[H["frqi"]]["params"]}
train = splits[0]["train"]
pick = {c: [x for x in train if f"/{c}/" in x][:10] for c in CL}
X = {c: np.stack([preprocess_image(dataset_root() / x, p8["image_size"]) for x in pick[c]]) for c in CL}
img = X["scratches"][0]
rho = {c: mixed_states(X[c], p8) for c in CL}
D2 = 2 * p8["patch"] ** 2
nrm = {c: np.sqrt(np.einsum("ij,ij->i", rho[c], rho[c])) for c in CL}
K = np.array([[float(((rho[a] @ rho[b].T) / np.outer(nrm[a], nrm[b])).mean()) for b in CL] for a in CL])
fig = plt.figure(figsize=(7.6, 5.0))
gs = fig.add_gridspec(2, 4, height_ratios=[1, 1], hspace=0.55, wspace=0.45)
a0 = fig.add_subplot(gs[0, 0]); a0.imshow(stretch(img[None])[0], cmap="gray", vmin=0, vmax=1)
pp, st = p8["patch"], p8["stride"]
for (i, j), col in zip(((8, 8), (8, 12), (32, 40)), (ORANGE, GREEN, BLUE)):
    a0.add_patch(Rectangle((j - .5, i - .5), pp, pp, fill=False, ec=col, lw=1.4))
a0.set_title(f"(a) image {p8['image_size']}×{p8['image_size']}, stretched;\n{n_patches(p8)} patches {pp}×{pp}, stride {st}", fontsize=7, loc="left")
a0.set_xticks([]); a0.set_yticks([])
P = patches(stretch(img[None]), pp, st)[0]
k = (32 // st) * ((p8["image_size"] - pp) // st + 1) + 40 // st
a1 = fig.add_subplot(gs[0, 1]); a1.imshow(P[k].reshape(pp, pp), cmap="gray", vmin=0, vmax=1, interpolation="nearest")
a1.set_title(f"(b) one {pp}×{pp} patch\n(blue box)", fontsize=7, loc="left"); a1.set_xticks([]); a1.set_yticks([])
psi = frqi_states(P[None, k:k + 1], p8["angle_scale"])[0, 0]
a2 = fig.add_subplot(gs[0, 2:])
a2.bar(np.arange(pp * pp), psi[:pp * pp], color=BLUE, width=0.8, label="cos θi (colour qubit |0⟩)")
a2.bar(np.arange(pp * pp), psi[pp * pp:], color=ORANGE, width=0.8, alpha=0.75, label="sin θi (colour qubit |1⟩)")
a2.set_title(f"(c) FRQI state of the patch: {D2} amplitudes, {G[H['frqi']]['circuit']['n_qubits']} qubits (angle ×{p8['angle_scale']:g})", fontsize=7, loc="left")
a2.set_xlabel("pixel index i", fontsize=7); a2.legend(fontsize=6.5, loc="upper left", ncol=2, bbox_to_anchor=(0, -0.22)); a2.tick_params(labelsize=6.5)
a3 = fig.add_subplot(gs[1, 0:2])
R1 = rho["scratches"][0].reshape(D2, D2)
im = a3.imshow(R1, cmap="RdBu_r", vmin=-np.abs(R1).max(), vmax=np.abs(R1).max())
a3.set_title(f"(d) mixed state ρ of the image ({D2}×{D2}),\nmean of {n_patches(p8)} patch states; Tr ρ = {np.trace(R1):.3f}", fontsize=7, loc="left")
a3.set_xticks([]); a3.set_yticks([]); plt.colorbar(im, ax=a3, fraction=0.046, pad=0.03).ax.tick_params(labelsize=6)
a4 = fig.add_subplot(gs[1, 2:])
im = a4.imshow(K, cmap="Blues")
a4.set_xticks(range(6), ["craz.", "incl.", "patch.", "pitted", "rolled", "scratch."], fontsize=6, rotation=35, ha="right"); a4.set_yticks(range(6), CLN, fontsize=6)
for i in range(6):
    for j in range(6):
        a4.text(j, i, f"{K[i, j]:.2f}", ha="center", va="center", fontsize=5.6, color="white" if K[i, j] > K.mean() + K.std() else INK)
a4.set_title("(e) normalised kernel Tr(ρAρB)/(‖ρA‖‖ρB‖),\nmean per class pair (10 train images/class)", fontsize=7, loc="left")
note(fig, f"Real computation with the frozen V4 FRQI settings on seed-0 training images (no test images). Rows/cols of (e): class of A / class of B; normalised for display only (the SVM uses the raw Tr(ρAρB)). {SIM}", 0.02)
save(fig, "Fig02_patch_encoding_illustration", ["class_A"] + CL, [[a] + [f"{v:.5f}" for v in r] for a, r in zip(CL, K)])
N["illustration"] = {"diag_mean": float(np.diag(K).mean()), "offdiag_mean": float(K[~np.eye(6, dtype=bool)].mean()),
                     "diag_is_row_max": int(sum(K[i].argmax() == i for i in range(6)))}

# Fig03 main results (horizontal bars)
items = [(LBL[g] + (" ★" if g in H.values() else ""), G[g]["test_accuracy"], G[g]["per_seed_test_accuracy"], COL[g]) for g in QG + [CTRL]]
items += [("V2 FRQI whole image (baseline)", REF["E1b-frqi8-qkc-scaled"]["test_accuracy"], None, "#c9d6e6"),
          ("V2 NEQR whole image (baseline)", REF["E2-neqr16-b4-qkc"]["test_accuracy"], None, "#f3d3c2"),
          ("V3 classical texture RBF-SVM", REF["V3-tex12c-rbfsvm"]["test_accuracy"], None, "#5f6b78")]
fig, ax = plt.subplots(figsize=(6.6, 3.7))
rows = []
for i, (lab, s, seeds, col) in enumerate(items[::-1]):
    ax.barh(i, 100 * s["mean"], 0.66, xerr=100 * s["std"], color=col, error_kw={"elinewidth": 0.8, "capsize": 2, "ecolor": "#555"})
    if seeds:
        ax.scatter(100 * np.array(seeds), [i] * 3, s=9, color="white", edgecolor=INK, lw=0.6, zorder=4)
    ax.text(2, i, f"{100 * s['mean']:.1f}%", va="center", fontsize=7.5, color="white" if col not in ("#c9d6e6", "#f3d3c2", LBLUE, LORANGE) else INK, fontweight="bold")
    rows.append([lab, f"{100 * s['mean']:.2f}", f"{100 * s['std']:.2f}"])
ax.set_yticks(range(len(items)), [x[0] for x in items[::-1]], fontsize=7.5); ax.set_xlim(0, 100)
ax.set_xlabel("Locked test accuracy (%)"); ax.grid(axis="x", color=GRID, lw=0.7); ax.set_axisbelow(True)
note(fig, "★ = headline model chosen by validation. Bars: mean of seeds 0–2; whiskers: s.d.; dots: individual seeds. " + SIM, -0.08)
save(fig, "Fig03_main_results", ["model", "test_acc_mean", "test_acc_sd"], rows)

# Fig05 forest plot of comparisons
fig, ax = plt.subplots(figsize=(6.8, 3.4))
rows = []
for i, c in enumerate(D["comparisons"][::-1]):
    d, lo, hi = 100 * c["diff"], 100 * c["ci95"][0], 100 * c["ci95"][1]
    col = BLUE if c["significant_0_05"] and d > 0 else ORANGE if c["significant_0_05"] else GREY
    ax.plot([lo, hi], [i, i], color=col, lw=2, solid_capstyle="round"); ax.scatter([d], [i], s=30, color=col, zorder=3)
    pstr = "<0.001" if c["p_holm"] < 0.001 else f"{c['p_holm']:.3f}"
    ax.text(hi + 1, i, f"{d:+.1f} pp, p{pstr if pstr.startswith('<') else '=' + pstr}", va="center", fontsize=6.8, color=INK)
    rows.append([c["name"], f"{d:.2f}", f"{lo:.2f}", f"{hi:.2f}", f"{c['p_holm']:.4g}"])
ax.axvline(0, color=INK, lw=0.8)
ax.set_yticks(range(8), [c["name"].replace(" (E1b-frqi8-qkc-scaled)", "").replace(" (V3-frqi8)", "").replace(" (E2-neqr16-b4-qkc)", "")
                         .replace(" (V3-tex12c-rbfsvm)", "") for c in D["comparisons"][::-1]], fontsize=7)
ax.set_xlim(-20, 50); ax.set_xlabel("Accuracy difference a − b (percentage points), 95% bootstrap CI"); ax.grid(axis="x", color=GRID, lw=0.7)
note(fig, "Blue: a significantly better; orange: a significantly worse; grey: not significant (Holm-corrected p < 0.05, paired permutation test).", -0.1)
save(fig, "Fig05_comparisons_forest", ["comparison", "diff_pp", "ci_lo", "ci_hi", "p_holm"], rows)

# Fig06 confusion matrices
fig, axs = plt.subplots(1, 3, figsize=(7.6, 2.9))
rows = []
for ax, g in zip(axs, (H["frqi"], H["neqr"], CTRL)):
    M = np.array(G[g]["confusion_matrix_sum"], float); Mn = M / M.sum(1, keepdims=True)
    ax.imshow(Mn, cmap="Blues", vmin=0, vmax=1)
    for i in range(6):
        for j in range(6):
            ax.text(j, i, f"{100 * Mn[i, j]:.0f}", ha="center", va="center", fontsize=6.3, color="white" if Mn[i, j] > 0.55 else INK)
    SH6 = ["crazing", "inclusion", "patches", "pitted", "rolled-in", "scratches"]
    ax.set_xticks(range(6), SH6, fontsize=6, rotation=45, ha="right"); ax.set_yticks(range(6), SH6 if ax is axs[0] else [], fontsize=6)
    ax.set_title(LBL[g], fontsize=7.5); ax.set_xlabel("predicted", fontsize=7)
    rows += [[g, CL[i], CL[j], int(M[i, j])] for i in range(6) for j in range(6)]
axs[0].set_ylabel("true class", fontsize=7)
note(fig, "Row-normalised confusion matrices (%), summed over seeds 0–2 (3 × 360 locked-test predictions).", -0.02)
save(fig, "Fig06_confusion_matrices", ["model", "true", "pred", "count"], rows)

# Fig08 per-seed stability
fig, ax = plt.subplots(figsize=(6.0, 3.0))
rows = []
for i, g in enumerate(QG + [CTRL]):
    v = 100 * np.array(G[g]["per_seed_test_accuracy"])
    ax.plot([i, i], [v.min(), v.max()], color=COL[g], lw=6, alpha=0.35, solid_capstyle="round")
    for s, (val, mk) in enumerate(zip(v, "os^")):
        ax.scatter(i, val, marker=mk, s=34, color=COL[g], edgecolor=INK, lw=0.5, zorder=3, label=f"seed {s}" if i == 0 else None)
        rows.append([g, s, f"{val:.2f}"])
    ax.text(i + 0.12, v.mean(), f"s.d. {v.std(ddof=1):.1f}", fontsize=6.8, color=MUTED, va="center")
ax.set_xticks(range(5), [LBL[g].replace(" patches", "\npatches").replace("Classical RBF-SVM, same patches", "Classical RBF-SVM\n(same patches)") for g in QG + [CTRL]], fontsize=7)
ax.set_ylabel("Locked test accuracy (%)"); ax.set_ylim(60, 95); ax.grid(axis="y", color=GRID, lw=0.7); ax.legend(fontsize=7, ncol=3, loc="lower left")
note(fig, "Each split seed changes the train/validation partition (test fixed). NEQR's low seed 1 = every rolled-in-scale test image misclassified.", -0.14)
save(fig, "Fig08_seed_stability", ["model", "seed", "test_acc"], rows)

# Fig09 validation sweep (validation only)
fig, axs = plt.subplots(1, 4, figsize=(7.8, 2.6), sharey=True)
rows = []
for ax, g in zip(axs, QG):
    cs = SEL[g]["candidates"]
    geos = sorted({(c["params"]["image_size"], c["params"]["patch"], c["params"]["stride"]) for c in cs})
    for k_, (norm, col) in enumerate((("none", GREY), ("stretch", COL[g] if "frqi" in g else ORANGE))):
        best = [max((c["val_mean"] for c in cs if (c["params"]["image_size"], c["params"]["patch"], c["params"]["stride"]) == geo and c["params"]["norm"] == norm), default=np.nan) for geo in geos]
        ax.bar(np.arange(len(geos)) + (k_ - 0.5) * 0.38, 100 * np.array(best), 0.36, color=col, label=norm if ax is axs[0] else None)
        rows += [[g, f"{geo[0]}/p{geo[1]}/s{geo[2]}", norm, f"{b:.4f}"] for geo, b in zip(geos, best)]
    ax.set_xticks(range(len(geos)), [f"{s}²\ns{st}" for s, _, st in geos], fontsize=6.5)
    ax.set_title(LBL[g], fontsize=7.5); ax.grid(axis="y", color=GRID, lw=0.7); ax.set_axisbelow(True)
axs[0].set_ylabel("best validation macro-F1 (%)"); axs[0].set_ylim(0, 100)
from matplotlib.patches import Patch
axs[0].legend(handles=[Patch(color=GREY, label="none"), Patch(color=LBLUE, label="contrast stretch")], title="normalisation", fontsize=6.5, title_fontsize=6.5, loc="lower left", frameon=True, facecolor="white", edgecolor="none")
note(fig, "Validation split only (mean over seeds 0–2), best over the remaining options (angle/bits, C) for each image size and stride. The locked test set was not used.", -0.1)
save(fig, "Fig09_validation_sweep", ["group", "geometry", "norm", "best_val_f1"], rows)

# Fig10 circuit resources
fig, axs = plt.subplots(1, 3, figsize=(7.4, 2.5))
rows = []
for ax, (key, lab) in zip(axs, (("n_qubits", "qubits per patch"), ("gates_compiled", "compiled gates"), ("depth_compiled", "compiled depth"))):
    v = [G[g]["circuit"][key] for g in QG]
    ax.bar(range(4), v, 0.65, color=[COL[g] for g in QG])
    for i, x in enumerate(v):
        ax.text(i, x, f"{x:,}", ha="center", va="bottom", fontsize=6.8)
    ax.set_xticks(range(4), [LBL[g].replace(" patches ", "\n") for g in QG], fontsize=6.5); ax.set_title(lab, fontsize=8)
    ax.grid(axis="y", color=GRID, lw=0.7); ax.set_axisbelow(True)
    rows += [[g, key, x] for g, x in zip(QG, v)]
note(fig, "Encoder circuit for ONE patch, Qiskit transpiled to {cx, rz, sx, x}, optimisation level 1, all-to-all coupling.", -0.1)
save(fig, "Fig10_circuit_resources", ["group", "metric", "value"], rows)

# Fig13 reconstruction SSIM by method
ids = [r for r in REC]
fig, ax = plt.subplots(figsize=(7.6, 3.3))
rows = []
for i, rid in enumerate(ids):
    s = REC[rid]["summary"]["all"]
    if rid.startswith("C-"):
        a, b = s["reconstruction"]["vs_preprocessed"]["ssim"]["mean"], None
    else:
        a, b = s["statevector"]["vs_preprocessed"]["ssim"]["mean"], s["shots1000"]["vs_preprocessed"]["ssim"]["mean"]
    col = BLUE if "FRQI" in rid else ORANGE if "NEQR" in rid else GREY
    ax.bar(i - 0.2, a, 0.38, color=col, label=None)
    if b is not None:
        ax.bar(i + 0.2, b, 0.38, color=col, alpha=0.45)
    rows.append([rid, f"{a:.4f}", "" if b is None else f"{b:.4f}"])
from matplotlib.patches import Patch
lh = [Patch(color="#555", label="left bar: exact (statevector) or PCA"), Patch(color="#555", alpha=0.4, label="right bar: 1,000 shots")]
ax.set_xticks(range(len(ids)), [r[2:] if r[:2] in ("R-", "C-") else "patch " + r[2:] for r in ids], rotation=60, ha="right", fontsize=6.3)
ax.set_ylabel(f"mean SSIM over {RS['n_images']:,} images"); ax.set_ylim(0, 1.05); ax.grid(axis="y", color=GRID, lw=0.7); ax.set_axisbelow(True)
ax.legend(handles=lh, fontsize=7, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.12))
note(fig, "Blue = FRQI, orange = NEQR, grey = classical PCA. SSIM against the preprocessed image. Patch rows: 1,000 shots per patch.", -0.18)
save(fig, "Fig13_reconstruction_ssim_by_method", ["method", "ssim_exact_or_pca", "ssim_1000_shots"], rows)

# Fig14 per-image difficulty
models = PII["models"]
frac, ycls, v4ok = [], [], []
for im, r in PII["images"].items():
    allp = [p == r["y_true"] for m in models for p in r["preds"][m["id"]]]
    frac.append(np.mean(allp)); ycls.append(r["y_true"])
    v4ok.append(np.mean([p == r["y_true"] for p in r["preds"][H["frqi"]]]))
frac, ycls, v4ok = map(np.array, (frac, ycls, v4ok))
fig, axs = plt.subplots(1, 2, figsize=(7.4, 2.8), gridspec_kw={"width_ratios": [1.2, 1]})
axs[0].hist(100 * frac, bins=20, range=(0, 100), color=BLUE, edgecolor="white")
axs[0].set_xlabel(f"% of the {len(models)} models × 3 seeds that classify the image correctly", fontsize=7); axs[0].set_ylabel("test images")
axs[0].grid(axis="y", color=GRID, lw=0.7); axs[0].set_axisbelow(True); axs[0].set_title("(a) difficulty of each of the 360 test images", fontsize=8, loc="left")
m1 = [100 * frac[ycls == i].mean() for i in range(6)]; m2 = [100 * v4ok[ycls == i].mean() for i in range(6)]
x = np.arange(6)
axs[1].bar(x - 0.2, m1, 0.38, color=GREY, label=f"all {len(models)} models"); axs[1].bar(x + 0.2, m2, 0.38, color=BLUE, label=LBL[H["frqi"]])
axs[1].set_xticks(x, ["craz.", "incl.", "patch.", "pitted", "rolled", "scratch."], fontsize=6.5); axs[1].set_ylim(0, 125); axs[1].set_yticks(range(0, 101, 20)); axs[1].legend(fontsize=6.5, loc="upper left", ncol=2)
axs[1].set_title("(b) mean % correct per class", fontsize=8, loc="left"); axs[1].grid(axis="y", color=GRID, lw=0.7); axs[1].set_axisbelow(True)
note(fig, f"Saved locked-test predictions of all {len(models)} selected models of protocols V2, V3, V4 (3 seeds each).", -0.06)
save(fig, "Fig14_per_image_difficulty", ["class", "mean_pct_all_models", "mean_pct_v4_frqi"], [[c, f"{a:.2f}", f"{b:.2f}"] for c, a, b in zip(CL, m1, m2)])
N["per_image"] = {"n_models": len(models), "never_correct": int((frac == 0).sum()), "always_correct": int((frac == 1).sum()),
                  "median_pct": float(100 * np.median(frac)), "hardest_class": CL[int(np.argmin(m1))], "easiest_class": CL[int(np.argmax(m1))]}

# Fig15 cross-protocol overview
fig, ax = plt.subplots(figsize=(6.8, 3.8))
rows = []
for i, (pr, lab, kind, s) in enumerate(XP[::-1]):
    col = {"V2": "#c9d6e6", "V3": "#7fa9dd", "V4": BLUE}[pr] if kind == "quantum" else {"V2": "#d5d8dc", "V3": "#a3aab3", "V4": "#5f6b78"}[pr]
    ax.barh(i, 100 * s["mean"], 0.66, xerr=100 * s["std"], color=col, hatch="" if kind == "quantum" else "///", edgecolor="white",
            error_kw={"elinewidth": 0.8, "capsize": 2, "ecolor": "#555"})
    ax.text(100 * s["mean"] + 100 * s["std"] + 1, i, f"{100 * s['mean']:.1f}", va="center", fontsize=7)
    rows.append([pr, lab, kind, f"{100 * s['mean']:.2f}", f"{100 * s['std']:.2f}"])
ax.set_yticks(range(len(XP)), [f"{pr} · {lab}" for pr, lab, _, _ in XP[::-1]], fontsize=7)
ax.set_xlim(0, 105); ax.set_xlabel("Locked test accuracy (%)"); ax.grid(axis="x", color=GRID, lw=0.7); ax.set_axisbelow(True)
ax.barh([], [], color=BLUE, label="quantum (simulated)"); ax.barh([], [], color="#5f6b78", hatch="///", edgecolor="white", label="classical")
ax.legend(fontsize=7, loc="lower center", ncol=2, bbox_to_anchor=(0.5, 1.0))
note(fig, "Same data, splits, seeds and locked test set in all protocols; mean ± s.d. over seeds 0–2. " + SIM, -0.08)
save(fig, "Fig15_cross_protocol_overview", ["protocol", "model", "type", "mean", "sd"], rows)

# copy base figures (made by make_v4_figures.py) under pack numbering
BASE = ROOT / "research_paper_visuals/figures_v4"
for src, dst in (("figV4_1_frqi_neqr_protocols", "Fig04_frqi_neqr_across_protocols"), ("figV4_2_per_class_f1", "Fig07_per_class_f1"),
                 ("figV4_3_reconstruction_all_images", "Fig11_reconstruction_mse_vs_shots"), ("figV4_4_reconstruction_examples", "Fig12_reconstruction_examples")):
    for ext in ("png", "pdf", "svg"):
        shutil.copy2(BASE / f"{src}.{ext}", FIG / f"{dst}.{ext}")
    shutil.copy2(BASE / "data" / f"{src}.csv", FIG / "data" / f"{dst}.csv")
    print("figure", dst, "(copied)")

# ════════════════════════════════════════════════════════════ numbers for the text
fr, ne = G[H["frqi"]], G[H["neqr"]]
cmp = {c["name"]: c for c in D["comparisons"]}
N.update({
    "frqi": {"group": H["frqi"], "acc": ms(fr["test_accuracy"]), "f1": ms(fr["test_f1_macro"]), "val": pct(fr["val_f1_macro"]["mean"]),
             "seeds": [pct(x) for x in fr["per_seed_test_accuracy"]], "qubits": fr["circuit"]["n_qubits"], "params": fr["params"], "patches": n_patches(fr["params"])},
    "neqr": {"group": H["neqr"], "acc": ms(ne["test_accuracy"]), "f1": ms(ne["test_f1_macro"]), "val": pct(ne["val_f1_macro"]["mean"]),
             "seeds": [pct(x) for x in ne["per_seed_test_accuracy"]], "qubits": ne["circuit"]["n_qubits"], "params": ne["params"], "patches": n_patches(ne["params"]),
             "rolled_correct": int(np.array(ne["confusion_matrix_sum"])[4, 4]), "rolled_correct_frqi": int(np.array(fr["confusion_matrix_sum"])[4, 4])},
    "others": {g: ms(G[g]["test_accuracy"]) for g in QG + [CTRL]},
    "refs": {k: ms(v["test_accuracy"]) for k, v in REF.items()},
    "xp": {f"{a}|{b}": ms(d) for a, b, _, d in XP},
    "cmp": [{"name": c["name"], "diff": f"{100 * c['diff']:+.1f}", "ci": f"[{100 * c['ci95'][0]:+.1f}, {100 * c['ci95'][1]:+.1f}]",
             "p": "< 0.001" if c["p_holm"] < 0.001 else f"= {c['p_holm']:.3f}", "sig": c["significant_0_05"]} for c in D["comparisons"]],
    "recon": {"n": RS["n_images"], "methods": len(REC),
              "frqi_exact_all": all(REC[k]["summary"]["all"]["statevector"]["n_exact"] == RS["n_images"] for k in REC if k.startswith("R-FRQI")),
              **{f"{k}|{m}": REC[k]["summary"]["all"][m]["vs_preprocessed"]["mse"]["mean"] for k in REC for m in REC[k]["summary"]["all"]
                 if m not in ("quantization_only",) and isinstance(REC[k]["summary"]["all"][m], dict) and "vs_preprocessed" in REC[k]["summary"]["all"][m]},
              "pca8_ssim": REC["C-PCA8-64"]["summary"]["all"]["reconstruction"]["vs_preprocessed"]["ssim"]["mean"],
              "pca12_ssim": REC["C-PCA12-64"]["summary"]["all"]["reconstruction"]["vs_preprocessed"]["ssim"]["mean"],
              "neqr_q4": REC["R-NEQR-16x16-b4"]["summary"]["all"]["quantization_only"]["mse"]["mean"]},
    "verify": {"pass": sum(c["ok"] for c in VER["checks"]), "total": len(VER["checks"])},
    "frozen": {"at": D["frozen_at"], "sha": D["frozen_selection_sha256"], "test_events": D["counts"]["test_access_events"]},
    "circuit_frqi": {k: fr["circuit"][k] for k in ("gates_compiled", "depth_compiled", "cx_compiled")},
    "tables": [[n, t] for n, t, *_ in TABLES],
})
(DAT / "numbers.json").write_text(json.dumps(N, indent=1, default=str))
(DAT / "tables.json").write_text(json.dumps([{"name": n, "title": t, "head": h, "rows": r, "notes": no} for n, t, h, r, no in TABLES], indent=1))
print("numbers written; illustration:", N["illustration"], N["per_image"])
