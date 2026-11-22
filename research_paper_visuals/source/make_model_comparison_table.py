"""Model comparison table for the project report (same content as the frontend /compare page), built from
results/qml_v4/aggregates/v4_results.json. Writes to research_paper_visuals/Project_Report/tables:
  T1_model_comparison.png / .tex / .csv / .md   and   T2_per_class_f1.png / .tex / .csv / .md
Run: .venv/bin/python research_paper_visuals/source/make_model_comparison_table.py
"""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research_paper_visuals/Project_Report/tables"
OUT.mkdir(parents=True, exist_ok=True)
D = json.loads((ROOT / "results/qml_v4/aggregates/v4_results.json").read_text())
CL = ["crazing", "inclusion", "patches", "pitted_surface", "rolled-in_scale", "scratches"]
CLN = ["Crazing", "Inclusion", "Patches", "Pitted surf.", "Rolled-in sc.", "Scratches"]
REF = {  # earlier-protocol models stored as references in v4_results.json (same locked test set)
    "E1b-frqi8-qkc-scaled": ("FRQI, whole image", "V2", "Quantum", "7", "8x8 image, one state"),
    "E2-neqr16-b4-qkc": ("NEQR, whole image (4-bit)", "V2", "Quantum", "12", "16x16 image, one state"),
    "V3-frqi8": ("FRQI, whole image (re-tuned)", "V3", "Quantum", "7", "8x8 image, one state"),
    "V3-neqr16": ("NEQR, whole image (re-tuned)", "V3", "Quantum", "12", "16x16 image, one state"),
    "V3-tex12c-rbfsvm": ("RBF-SVM, texture features", "V3", "Classical", "-", "LBP + GLCM, PCA-12"),
}
p = lambda v: "-" if v is None else f"{100 * v:.1f}"
pm = lambda m: "-" if not m else f"{100 * m['mean']:.1f} ± {100 * m.get('std', 0):.1f}"

rows = []
for g, r in D["groups"].items():
    q, pr, c = r.get("quantum") or {}, r["params"], r.get("circuit") or {}
    s = r.get("per_seed_test_accuracy") or []
    name = (f"{q['representation']} patch ensemble ({pr['patch']}x{pr['patch']})" if q.get("n_qubits")
            else "RBF-SVM, patch moments (control)")
    inp = f"{pr['image_size']}x{pr['image_size']}, {pr['patch']}x{pr['patch']} stride {pr['stride']}" + (", stretch" if pr.get("norm") == "stretch" else "") + (f", {pr['bits']}-bit" if pr.get("bits") else "")
    rows.append(dict(model=name, version="V4", type="Quantum" if q.get("n_qubits") else "Classical",
                     qubits=str(q.get("n_qubits") or "-"), input=inp, acc=r["test_accuracy"], f1=r["test_f1_macro"],
                     val=r["val_f1_macro"], spread=(max(s) - min(s)) if s else None,
                     cx=c.get("cx_compiled"), depth=c.get("depth_compiled"), per_class=r.get("per_class_f1")))
for k, (name, v, t, qb, inp) in REF.items():
    r = D["references"][k]
    rows.append(dict(model=name, version=v, type=t, qubits=qb, input=inp, acc=r["test_accuracy"], f1=r["test_f1_macro"],
                     val=r["val_f1_macro"], spread=None, cx=None, depth=None, per_class=None))
rows.sort(key=lambda r: (-int(r["version"][1]), -r["acc"]["mean"]))

H1 = ["Model", "Ver.", "Type", "Qubits", "Input", "Test acc. (%)", "Test F1 (%)", "Val F1 (%)", "Seed spread (pp)", "CX", "Depth"]
T1 = [[r["model"], r["version"], r["type"], r["qubits"], r["input"], pm(r["acc"]), pm(r["f1"]), p(r["val"]["mean"]),
       p(r["spread"]), "-" if r["cx"] is None else str(r["cx"]), "-" if r["depth"] is None else str(r["depth"])] for r in rows]
v4 = [r for r in rows if r["per_class"]]
H2 = ["Model"] + CLN
T2 = [[r["model"]] + [p(r["per_class"][c]["mean"]) for c in CL] for r in v4]


def write_all(stem, head, body, caption, label, colspec):
    with open(OUT / f"{stem}.csv", "w", newline="") as f:
        csv.writer(f).writerows([head] + body)
    md = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(b) + " |" for b in body]
    (OUT / f"{stem}.md").write_text("\n".join(md) + "\n")
    esc = lambda s: s.replace("±", r"$\pm$").replace("x", r"$\times$") if any(ch.isdigit() for ch in s) else s.replace("_", r"\_")
    tex = [r"\begin{table*}[!t]", r"\centering", rf"\caption{{{caption}}}", rf"\label{{{label}}}", r"\footnotesize",
           rf"\begin{{tabular}}{{{colspec}}}", r"\toprule", " & ".join(r"\textbf{" + h.replace("%", r"\%") + "}" for h in head) + r" \\", r"\midrule"]
    prev = None
    for b in body:
        if stem.startswith("T1") and prev and b[1] != prev:
            tex.append(r"\midrule")
        prev = b[1]
        tex.append(" & ".join(esc(x) for x in b) + r" \\")
    tex += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    (OUT / f"{stem}.tex").write_text("\n".join(tex) + "\n")


write_all("T1_model_comparison", H1, T1,
          "Comparison of all models on the 360-image locked test set (mean $\\pm$ std over 3 seeds). Qubits are per encoded "
          "state (per patch for V4); CX and depth are for one compiled patch-state circuit. Exact noiseless simulation.",
          "tab:model_comparison", "llllllllrrr")
write_all("T2_per_class_f1", H2, T2, "Per-class F1 (\\%) of the V4 models on the locked test set, mean over 3 seeds.",
          "tab:per_class_f1", "lrrrrrr")


def png(stem, head, body, widths, hl_rows=(), bold_col_max=False):
    fig_w = sum(widths) * 1.0
    fig, ax = plt.subplots(figsize=(fig_w, 0.32 * (len(body) + 1) + 0.2))
    ax.axis("off")
    t = ax.table(cellText=body, colLabels=head, colWidths=[w / sum(widths) for w in widths], loc="center", cellLoc="left")
    t.auto_set_font_size(False); t.set_fontsize(8); t.scale(1, 1.45)
    t.auto_set_column_width(col=list(range(len(head))))
    for (i, j), cell in t.get_celld().items():
        cell.set_edgecolor("#d0d4da"); cell.set_linewidth(0.5)
        if i == 0:
            cell.set_facecolor("#1f3b5c"); cell.get_text().set_color("white"); cell.get_text().set_fontweight("bold")
        elif (i - 1) in hl_rows:
            cell.set_facecolor("#eaf3fc")
        elif i % 2 == 0:
            cell.set_facecolor("#f7f8fa")
    if bold_col_max:
        for j in range(1, len(head)):
            vals = [float(b[j]) for b in body]
            t[(vals.index(max(vals)) + 1, j)].get_text().set_fontweight("bold")
    fig.savefig(OUT / f"{stem}.png", dpi=300, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


png("T1_model_comparison", H1, T1, [2.3, 0.45, 0.75, 0.55, 2.1, 1.0, 1.0, 0.75, 1.0, 0.5, 0.55],
    hl_rows=[i for i, r in enumerate(rows) if r["version"] == "V4"])
png("T2_per_class_f1", H2, T2, [2.4] + [0.95] * 6, bold_col_max=True)
print("wrote", *sorted(x.name for x in OUT.iterdir()))
