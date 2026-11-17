"""results/qml_v4/reports/V4_FRQI_NEQR_IMPROVEMENT_REPORT.md from aggregates/v4_results.json + v4_verification.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V4 = ROOT / "results" / "qml_v4"
D = json.loads((V4 / "aggregates" / "v4_results.json").read_text())
VER = json.loads((V4 / "aggregates" / "v4_verification.json").read_text())
G, REF, H = D["groups"], D["references"], D["headlines"]
C = {c["name"]: c for c in D["comparisons"]}
CL = ["crazing", "inclusion", "patches", "pitted_surface", "rolled-in_scale", "scratches"]


def ms(m):
    return f"{100 * m['mean']:.1f} ± {100 * (m.get('std') or 0):.1f}"


def pv(p):
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def tab(head, rows):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(map(str, r)) + " |" for r in rows])


fr, ne = G[H["frqi"]], G[H["neqr"]]
c = lambda n: C[n]  # noqa: E731
ne_seeds = [round(100 * x, 1) for x in ne["per_seed_test_accuracy"]]
cm_ne = ne["confusion_matrix_sum"]
rolled_ne = cm_ne[4][4]
rolled_fr = fr["confusion_matrix_sum"][4][4]

grp_rows = []
for g, r in G.items():
    p = r["params"]
    q = (r.get("quantum") or {}).get("n_qubits")
    desc = (f"{p['image_size']}×{p['image_size']}, {p['patch']}×{p['patch']} patches, stride {p['stride']}, "
            + (f"angle ×{p['angle_scale']}" if p.get("representation") == "FRQI" else f"{p['bits']}-bit" if p.get("representation") == "NEQR" else f"γ={p['gamma']}")
            + f", {'contrast stretch' if p['norm'] == 'stretch' else 'no stretch'}, C={p['C']:g}")
    grp_rows.append([f"`{g}`", q or "— (classical)", desc, f"{100 * r['val_f1_macro']['mean']:.1f}", ms(r["test_accuracy"]), ms(r["test_f1_macro"]),
                     ", ".join(f"{100 * x:.1f}" for x in r["per_seed_test_accuracy"])])

cmp_rows = [[x["name"], f"{100 * x['acc_a']:.1f}", f"{100 * x['acc_b']:.1f}", f"{100 * x['diff']:+.1f} [{100 * x['ci95'][0]:+.1f}, {100 * x['ci95'][1]:+.1f}]",
             pv(x["p_holm"]), "yes" if x["p_holm"] < 0.05 else "no"] for x in D["comparisons"]]

pc_rows = []
for g in (H["frqi"], H["neqr"], "V4-patchmom-rbfsvm"):
    pcf = G[g]["per_class_f1"]
    pc_rows.append([f"`{g}`"] + [f"{100 * pcf[k]['mean']:.1f}" for k in CL])

story = [
    ["V2 (pixel-level kernel)", ms(REF["E1b-frqi8-qkc-scaled"]["test_accuracy"]), ms(REF["E2-neqr16-b4-qkc"]["test_accuracy"])],
    ["V3 (pixel-level kernel, wider search)", ms(REF["V3-frqi8"]["test_accuracy"]), ms(REF["V3-neqr16"]["test_accuracy"])],
    ["**V4 (patch-ensemble mixed-state kernel)**", f"**{ms(fr['test_accuracy'])}**", f"**{ms(ne['test_accuracy'])}**"],
]

rep = f"""# FRQI / NEQR Improvement Report — Protocol V4

Protocol V4 · {D['counts']['groups']} frozen groups · {D['counts']['candidate_runs']} validation runs ({D['counts']['failed_runs']} failed) ·
selections frozen {D['frozen_at']} (SHA-256 `{D['frozen_selection_sha256']}`) · {D['counts']['test_access_events']} locked-test stages.
Source: `results/qml_v4/aggregates/v4_results.json` (`scripts/v4/analyze_v4.py`). Test = 360 locked images, mean ± s.d. over seeds 0–2.
All circuits simulated exactly on a CPU (no hardware, no noise).

## 1. Result

{tab(['Protocol', 'FRQI test accuracy %', 'NEQR test accuracy %'], story)}

* **FRQI: {ms(REF['E1b-frqi8-qkc-scaled']['test_accuracy'])} → {ms(fr['test_accuracy'])} %**
  ({100 * c('V4 FRQI vs V2 FRQI (E1b-frqi8-qkc-scaled)')['diff']:+.1f} pp, p<sub>Holm</sub> {pv(c('V4 FRQI vs V2 FRQI (E1b-frqi8-qkc-scaled)')['p_holm'])}).
* **NEQR: {ms(REF['E2-neqr16-b4-qkc']['test_accuracy'])} → {ms(ne['test_accuracy'])} %**
  ({100 * c('V4 NEQR vs V2 NEQR (E2-neqr16-b4-qkc)')['diff']:+.1f} pp, p<sub>Holm</sub> {pv(c('V4 NEQR vs V2 NEQR (E2-neqr16-b4-qkc)')['p_holm'])}).
  Seeds: {ne_seeds} %. Seed 1 is weak because NEQR misclassifies every *rolled-in scale* image on that split (Section 4).
* **FRQI now beats NEQR** ({100 * c('V4 FRQI vs V4 NEQR')['diff']:+.1f} pp, p<sub>Holm</sub> {pv(c('V4 FRQI vs V4 NEQR')['p_holm'])}).
* **Against classical baselines:** FRQI vs a classical RBF-SVM on the *same patches* is
  {100 * c('V4 FRQI vs classical patch-moment RBF-SVM')['diff']:+.1f} pp (p<sub>Holm</sub> {pv(c('V4 FRQI vs classical patch-moment RBF-SVM')['p_holm'])},
  not significant). Both FRQI and NEQR remain clearly **below** the best classical texture model (RBF-SVM on LBP/GLCM texture features,
  {ms(REF['V3-tex12c-rbfsvm']['test_accuracy'])} %).

## 2. What changed, and why it works

The V2/V3 FRQI and NEQR kernels compared two images **pixel by pixel at the same positions**: the overlap
⟨I_a|I_b⟩ sums cos(θ_i^a − θ_i^b) over the same pixel index i. NEU defects are textures. The same scratch shifted by a few pixels
gives an unrelated state, so the kernel measured position rather than texture.

V4 keeps FRQI and NEQR as the encodings but changes **what is encoded and how two images are compared**:

1. Cut the (resized) image into p×p patches with stride s. Encode each patch as an FRQI state (2·log₂p + 1 qubits) or an NEQR state
   (2·log₂p + q qubits) with the original encoder circuits.
2. Represent the image by the **mixed state** of a uniformly random patch: ρ_I = (1/P) Σ_k |ψ_k⟩⟨ψ_k|.
3. Kernel: **K(A, B) = Tr(ρ_A ρ_B) = mean over patch pairs of |⟨ψ_k^A|ψ_l^B⟩|²**. A swap test between one random patch state of
   each image estimates it directly (the swap test measures Tr(ρσ) for mixed inputs). An SVM is trained on K.

Because ρ is an average over positions, the kernel is translation-robust (`tests/test_v4_models.py` checks this). The unit tests also check
that it equals the mean of squared overlaps of the Qiskit encoder statevectors. Per-image contrast stretch (min–max within the image only)
was a searched option.

**Selected configurations (validation macro-F1, test not consulted):**

{tab(['Group', 'qubits per patch state', 'selected configuration', 'val F1 %', 'test acc. %', 'test macro-F1 %', 'per-seed test acc. %'], grp_rows)}

The FRQI headline (`{H['frqi']}`) and NEQR headline (`{H['neqr']}`) are the groups with the higher validation score, as pre-declared.

## 3. Pre-declared comparisons (8, Holm-corrected)

{tab(['Comparison', 'acc. a %', 'acc. b %', 'Δ (95 % CI) pp', 'p<sub>Holm</sub>', 'significant'], cmp_rows)}

## 4. Per-class F1 (%, mean over seeds) and the NEQR seed-1 failure

{tab(['Model'] + CL, pc_rows)}

Rolled-in scale correctly classified, summed over 3 seeds (180 images): FRQI {rolled_fr}, NEQR {rolled_ne}.
NEQR, selected **without** contrast stretch, loses this class on seed 1. The V2 pixel-level FRQI and NEQR kernels already scored 0 % F1 on it,
which suggests a brightness difference between the training and locked-test folders for this class. FRQI, selected **with** per-image
contrast stretch, is not affected. We did not re-tune NEQR after seeing this, because that would use the test set for model choice.

## 5. Honest limits

- **No quantum advantage.** Every kernel here has a closed form and was computed classically. On the same patches, a classical
  RBF-SVM is statistically indistinguishable from FRQI (and from NEQR). A classical texture model is still better (Section 3).
- **A real implementation would need many shots.** On hardware each kernel entry would be estimated by swap tests over random patch pairs.
  Shot noise was not simulated in V4.
- **Validation-only exploration before the grid.** Before the grid was fixed, a few patch geometries were tried on the *validation* split
  (seeds 0–2). Every geometry tried is in the grid except one too-slow NEQR setting (documented in `scripts/v4/run_v4.py`).
- **The locked test set is not fresh.** It was used by V2 and V3. V4 is a new method, frozen on validation and evaluated once, but
  it was proposed after seeing that earlier FRQI/NEQR results were weak.
- **NEQR is seed-sensitive** (s.d. {100 * ne['test_accuracy']['std']:.1f} pp) because of the class failure above.

## 6. Verification ({sum(x['ok'] for x in VER['checks'])}/{len(VER['checks'])} checks pass, `scripts/v4/verify_v4.py`)

{tab(['Check', 'Result'], [[x['check'], 'PASS' if x['ok'] else 'FAIL'] for x in VER['checks']])}

{chr(10).join('- ' + n for n in VER['notes'])}

## 7. Reproduce

```bash
cd scripts/v4 && ../../.venv/bin/python setup_v4.py && N=4 ./chain_v4.sh   # candidates → select → freeze → locked test (~5 min)
cd ../.. && .venv/bin/python scripts/v4/analyze_v4.py && .venv/bin/python scripts/v4/verify_v4.py && .venv/bin/python scripts/v4/write_report_v4.py
.venv/bin/python -m pytest -q tests/test_v4_models.py
```
"""
(V4 / "reports").mkdir(exist_ok=True)
(V4 / "reports" / "V4_FRQI_NEQR_IMPROVEMENT_REPORT.md").write_text(rep)
print("written")
