"""Independent check of the V4 paper pack: recompute key numbers from the raw per-run files and compare with the pack tables/text.
Writes V4_paper_pack/VALIDATION.md; exit code 1 on any mismatch."""
import csv
import json
import statistics as st
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "research_paper_visuals/V4_paper_pack"
V4 = ROOT / "results/qml_v4"
D = json.loads((V4 / "aggregates/v4_results.json").read_text())
LBL = {"V4-frqi-p4": "FRQI patches 4×4", "V4-frqi-p8": "FRQI patches 8×8", "V4-neqr-p2": "NEQR patches 2×2",
       "V4-neqr-p4": "NEQR patches 4×4", "V4-patchmom-rbfsvm": "Classical RBF-SVM, same patches"}
res = []


def check(name, got, exp):
    res.append((name, got == exp, got, exp))


t4 = {r[0]: r for r in csv.reader(open(PACK / "tables/Tab04_main_results.csv"))}
t6 = {r[0]: r for r in csv.reader(open(PACK / "tables/Tab06_per_class_f1.csv"))}
for g, lab in LBL.items():
    accs = []
    for e in D["groups"][g]["experiment_ids"]:
        df = pd.read_csv(V4 / "experiments" / e / "predictions.csv")
        df = df[df["split"] == "test"] if "test" in set(df["split"]) else df
        assert len(df) == 360, (e, len(df))
        accs.append(float((df["y_true"] == df["y_pred"]).mean()))
    check(f"Tab04 {lab}: test accuracy recomputed from predictions.csv", t4[lab][3], f"{100 * st.mean(accs):.1f} ± {100 * st.stdev(accs):.1f}")
    check(f"Tab04 {lab}: per-seed accuracies", t4[lab][5], ", ".join(f"{100 * a:.1f}" for a in accs))
    sel = json.loads((V4 / "aggregates/selection" / f"{g}.json").read_text())["selected"]
    check(f"Tab04 {lab}: validation F1 equals frozen selection file", t4[lab][2], f"{100 * sel['val_mean']:.1f}")
    check(f"Tab06 {lab}: crazing F1", t6[lab][1], f"{100 * D['groups'][g]['per_class_f1']['crazing']['mean']:.1f}")
t5 = list(csv.reader(open(PACK / "tables/Tab05_statistical_comparisons.csv")))[1:]
check("Tab05 has the 8 pre-declared comparisons in order", [r[0] for r in t5], [c["name"] for c in D["comparisons"]])
md = (PACK / "content/PAPER_V4.md").read_text()
for g in ("V4-frqi-p8", "V4-neqr-p4"):
    check(f"paper text quotes the {g} test accuracy", t4[LBL[g]][3] in md, True)
import re
check("no unfilled template fields in paper text", re.findall(r"\{[A-Za-z_]+[\[}]", md), [])
figs = sorted(p.stem for p in (PACK / "figures").glob("*.png"))
check("15 figures (png) present, each with pdf + svg + data csv", all((PACK / "figures" / f"{f}.{x}").exists() for f in figs for x in ("pdf", "svg")) and
      all((PACK / "figures/data" / f"{f}.csv").exists() for f in figs) and len(figs) == 15, True)
check("10 tables, each as csv/md/tex/png", all((PACK / "tables" / f"{t}.{x}").exists() for t in [p.stem for p in (PACK / "tables").glob("*.csv")] for x in ("md", "tex", "png"))
      and len(list((PACK / "tables").glob("*.csv"))) == 10, True)
ver = json.loads((V4 / "aggregates/v4_verification.json").read_text())
check("V4 integrity checks all pass", all(c["ok"] for c in ver["checks"]), True)

n_ok = sum(r[1] for r in res)
lines = [f"# V4 paper pack — validation ({n_ok}/{len(res)} pass)", "",
         "Numbers recomputed independently from `results/qml_v4/experiments/*/predictions.csv` and the frozen selection files.", "",
         "| Check | Result |", "|---|---|"] + [f"| {n} | {'PASS' if o else f'FAIL (got {g!r}, expected {e!r})'} |" for n, o, g, e in res]
(PACK / "VALIDATION.md").write_text("\n".join(lines) + "\n")
print(f"{n_ok}/{len(res)} pass")
for n, o, g, e in res:
    if not o:
        print("FAIL", n, g, e)
sys.exit(0 if n_ok == len(res) else 1)
