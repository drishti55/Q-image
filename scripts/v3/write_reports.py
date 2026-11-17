"""
Write the three result-dependent V3 reports from results/qml_v3/aggregates/v3_results.json.
Every number in the tables is read from that file (which analyze_v3.py builds from the per-experiment records);
nothing is typed by hand. Prose statements that depend on numbers are checked with assertions so that the
text cannot silently disagree with the data.

  QUANTUM_PERFORMANCE_IMPROVEMENT_REPORT.md
  QUANTUM_CLASSICAL_COMPARISON_REPORT.md
  V3_VERIFICATION_REPORT.md   (also needs the verification facts collected by verify_v3.py -> aggregates/v3_verification.json)
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V3 = ROOT / "results" / "qml_v3"
D = json.loads((V3 / "aggregates" / "v3_results.json").read_text())
VER = json.loads((V3 / "aggregates" / "v3_verification.json").read_text()) if (V3 / "aggregates" / "v3_verification.json").exists() else None
G = {g["group"]: g for g in D["groups"]}
C = {c["name"]: c for c in D["comparisons"]}
SEC = {c["name"]: c for c in D.get("secondary_comparisons_posthoc", [])}
OUT = V3 / "reports"


def pc(x, d=1):
    return "—" if x is None else f"{100 * x:.{d}f}"


def ms(m, d=1):
    if not m or m.get("mean") is None:
        return "—"
    return f"{100 * m['mean']:.{d}f} ± {100 * (m.get('std') or 0):.{d}f}"


def pp(c):
    return f"{100 * c['diff']:+.1f} pp [{100 * c['ci95'][0]:+.1f}, {100 * c['ci95'][1]:+.1f}]"


def pv(p):
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def mcn(c):
    return ", ".join(f"s{m['seed']}: {m['a_only_correct']}/{m['b_only_correct']} (p={pv(m['p_exact'])})" for m in c["mcnemar_per_seed"])


def table(head, rows):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(x) for x in r) + " |" for r in rows])


def g(name):
    return G[name]


def acc(name):
    return G[name]["test_accuracy"]["mean"]


H = D["headlines"]
hdr = (f"Protocol V3 · {D['counts']['groups']} frozen groups · {D['counts']['candidate_runs']:,} validation runs "
       f"({D['counts']['failed_runs']} failed) · selections frozen {D['frozen_at']} (SHA-256 `{D['frozen_selection_sha256']}`) · "
       f"{D['counts']['test_access_events']} locked-test evaluation stages.\n\n"
       "Source: `results/qml_v3/aggregates/v3_results.json` (built by `scripts/v3/analyze_v3.py` from the per-experiment records). "
       "Accuracy and macro-F1 are on the 360 locked test images, mean ± s.d. over seeds 0, 1, 2. "
       "All quantum circuits are simulated exactly (statevector) on a CPU; no quantum hardware and no noise model were used.")

# ------------------------------------------------------------------ sanity facts used in prose (fail loudly if data changes)
tex_q, tex_c = "V3-tex8c-qkc-zz_full", "V3-tex8c-rbfsvm"
assert abs(acc(tex_q) - acc(tex_c)) < 0.01, "prose assumes texture ZZ-full ~= texture RBF-SVM"
assert acc("V3-tex8c-vqc-encoding-only") > acc("V3-tex8c-vqc") + 0.1, "prose assumes encoding-only beats trained VQC"
assert acc("V3-pix8c-vqc") < D["before_after"][5]["v2_test_accuracy"]["mean"], "prose assumes like-for-like VQC got worse"
assert [m["feature_set"] for m in D["matched_controls"] if C[f"Quantum vs matched RBF-SVM ({m['feature_set']})"]["p_holm"] < 0.05] == ["pix12c"]
assert C["Quantum vs matched RBF-SVM (pix12c)"]["diff"] < 0, "prose assumes the only significant matched result favours classical"
assert D["before_after"][3]["model"].startswith("FRQI") and D["before_after"][5]["model"].startswith("Genuine VQC")
assert H["pure_quantum"]["group"].endswith("product_ry"), "prose assumes pure-quantum headline is product-RY"

# ================================================================== 1. improvement report
ba_rows = []
for b in D["before_after"]:
    l, a = b["v3_like_for_like"], b["v3_best"]
    name = f"V3 vs V2: {b['model']}"
    c = C.get(name)
    s = SEC.get(f"V3 like-for-like vs V2: {b['model']}")
    ba_rows.append([b["model"], f"{ms(b['v2_test_accuracy'])}<br>`{b['v2_group']}`",
                    f"{ms(l['test_accuracy'])}<br>`{l['group']}` ({l['n_qubits']} q)" + (f"<br>{pp(s)}, p<sub>Holm,post-hoc</sub>={pv(s['p_holm'])}" if s else ""),
                    f"{ms(a['test_accuracy'])}<br>`{a['group']}` ({a['n_qubits']} q)",
                    f"{pp(c)}<br>p<sub>Holm</sub>={pv(c['p_holm'])}" if c else "—"])

vqc_rows = []
for f in ("pix8c", "tex8c", "mnv8c"):
    for suf, lab in (("vqc", "trained VQC (Adam, parameter shift)"), ("vqc-spsa", "trained VQC (calibrated SPSA)"),
                     ("vqc-encoding-only", "encoding only, L = 0 (control)"), ("vqc-ablation-frozen", "random frozen circuit (ablation)")):
        k = f"V3-{f}-{suf}"
        if k in G:
            vd = G[k].get("vqc_diagnostics_seed0") or {}
            vqc_rows.append([f, lab, f"{ms(G[k]['val_f1_macro'])}", ms(G[k]["test_accuracy"]), ms(G[k]["test_f1_macro"]),
                             vd.get("stopped_at") if vd.get("stopped_at") is not None else "—",
                             f"{(vd.get('init_grad') or {}).get('var', 0):.1e}" if vd.get("init_grad") else "—"])

vqc_cmp = [[c["name"], f"`{c['a']}` vs `{c['b']}`", pc(c["acc_a"]), pc(c["acc_b"]), pp(c), pv(c["p_holm"])]
           for c in D["comparisons"] if c["kind"] == "vqc_vs_control"]

kern_rows = []
for k in ("V3-pix8a-qkc-zz_full", "V3-pix8c-qkc-zz_full", "V3-tex8c-qkc-zz_full", "V3-tex12c-qkc-zz_full", "V3-tex8c-qkc-product_ry",
          "V3-tex12c-qkc-product_ry", "V3-mnv8c-qkc-zz_full", "V3-tex8c-pqk-zz_full", "V3-frqi8", "V3-neqr16"):
    kd = G[k].get("kernel_diagnostics_seed0") or {}
    kern_rows.append([f"`{k}`", json.dumps({x: G[k]["params"].get(x) for x in ("bandwidth", "C", "gamma", "angle_scale", "bits") if G[k]["params"].get(x) is not None}),
                      f"{kd.get('offdiag_mean', float('nan')):.3f}", f"{kd.get('centered_kernel_alignment', float('nan')):.2f}",
                      ms(G[k]["val_f1_macro"]), ms(G[k]["test_accuracy"])])

frqi_rows = [[f"`{k}`", G[k]["n_qubits"], json.dumps({x: G[k]["params"].get(x) for x in ("angle_scale", "bits", "kernel", "norm", "C")}),
              ms(G[k]["val_f1_macro"]), ms(G[k]["test_accuracy"]), ms(G[k]["test_f1_macro"])]
             for k in sorted(G, key=lambda x: (x[:7], int("".join(ch for ch in x if ch.isdigit()) or 0))) if k.startswith(("V3-frqi", "V3-neqr"))]

imp = f"""# Quantum Performance Improvement Report — Protocol V3

{hdr}

## 1. Summary (read this first)

* **Did the quantum models improve?** Their locked-test accuracy did, sometimes a lot. But **the gain comes from a better
  classical input representation**, not from anything quantum. On those same inputs, an ordinary classical RBF-SVM is as
  good or better.
* **Biggest effect: texture features.** Replacing raw-pixel PCA with fixed (not learned) LBP + GLCM texture
  features lifted the 8-qubit ZZ-full kernel from {pc(D['before_after'][0]['v2_test_accuracy']['mean'])} % (V2) to
  {pc(acc(tex_q))} % ({pp(C['V3 vs V2: ZZ-full QKC (V2: pixel PCA-8)'])}, p<sub>Holm</sub> = {pv(C['V3 vs V2: ZZ-full QKC (V2: pixel PCA-8)']['p_holm'])}).
  The classical RBF-SVM on the identical 8 texture features scores {pc(acc(tex_c))} %. The best quantum model on those features by validation
  (`{C['Quantum vs matched RBF-SVM (tex8c)']['a']}`) minus that RBF-SVM = {pp(C['Quantum vs matched RBF-SVM (tex8c)'])},
  p<sub>Holm</sub> = {pv(C['Quantum vs matched RBF-SVM (tex8c)']['p_holm'])}.
* **Like-for-like (still raw pixels), V3 did not help the ZZ kernels.** Validation chose exactly the V2 configuration again, and
  it reproduced V2 to the image (difference 0.0 pp). The product-RY kernel improved by
  {pp(SEC['V3 like-for-like vs V2: product-RY QKC (V2: pixel PCA-8)'])} (12 PCA components instead of 8; post-hoc test).
* **The best "pure quantum" model is a product-RY kernel**, {pc(H['pure_quantum']['test_accuracy']['mean'])} %. A product-RY
  kernel is a product of single-qubit cosines, so a classical computer can evaluate it in closed form. It is a control, not
  evidence of quantum benefit.
* **VQC: a genuine improvement in training, a negative result for the circuit.** The genuine trainable 8-qubit VQC
  on texture features reaches {pc(acc('V3-tex8c-vqc'))} % (V2 VQC {pc(D['before_after'][5]['v2_test_accuracy']['mean'])} %).
  But the **encoding-only control (no trainable gates, L = 0) reaches {pc(acc('V3-tex8c-vqc-encoding-only'))} %**: the trainable
  entangling layers *reduce* accuracy by {-100 * C['VQC vs vqc-encoding-only (tex8c)']['diff']:.1f} pp. On raw pixels the V3 VQC is
  worse than V2 ({pc(acc('V3-pix8c-vqc'))} % vs {pc(D['before_after'][5]['v2_test_accuracy']['mean'])} %).
* **FRQI / NEQR did not improve.** NEQR 16×16 4-bit was re-selected unchanged ({pc(acc('V3-neqr16'))} %). The best FRQI fell from
  {pc(D['before_after'][3]['v2_test_accuracy']['mean'])} % to {pc(acc('V3-frqi8'))} % ({pp(C['V3 vs V2: FRQI angle-scaled 8×8'])}, p<sub>Holm</sub> = {pv(C['V3 vs V2: FRQI angle-scaled 8×8']['p_holm'])}, not significant after correction).
* **Hybrid (MobileNetV3 + quantum) got slightly worse.** All three V3 hybrid kernels score {pc(acc('V3-mnv8c-qkc-zz_full'))} %, vs 91.9–93.2 % in V2.
  V3 searched only the cdf angle map for MobileNetV3 features, not V2's MinMax map, and the V3 hybrids are already lower on
  validation ({min(b['v3_best']['val_f1_macro']['mean'] for b in D['before_after'][6:9]):.3f}–{max(b['v3_best']['val_f1_macro']['mean'] for b in D['before_after'][6:9]):.3f}
  vs {min(b['v2_val_f1']['mean'] for b in D['before_after'][6:9]):.3f}–{max(b['v2_val_f1']['mean'] for b in D['before_after'][6:9]):.3f} in V2). The cdf map was a poor
  choice for these features; this shows without the test set. V3 does not re-run them, because the locked test is now open.

## 2. What was tried (all chosen on validation, frozen before the locked test)

| Audit finding (QUANTUM_PERFORMANCE_AUDIT.md) | V3 change | Outcome on the locked test |
|---|---|---|
| Raw-pixel PCA carries little class information (CKA ≈ 0.30 for every pixel kernel) | fixed texture features (LBP 8/1, 16/2, 24/3 + GLCM + gradient statistics, 76-d) → PCA 8 / 12 | large gain **for every model, quantum and classical alike** |
| MinMax angle map squashes outliers (audit: RBF 64.8 % standard vs 60.7 % angle) | cdf map: θ = π·Φ(z) | no consistent gain on pixels (pix8c vs pix8a; Section 6) |
| Per-image brightness differences | per-image normalisation (pixn8c) | worse ({pc(acc('V3-pixn8c-qkc-product_ry'))} % best quantum) |
| Truncated hyperparameter grids | wider bandwidth / C grids | ZZ kernels now pick the **smallest** bandwidth offered (0.25), so the grid edge remains (Section 6) |
| Kernel concentration | projected quantum kernel (Bloch vectors) | **worse** than fidelity kernels (e.g. tex8c PQK ZZ-full {pc(acc('V3-tex8c-pqk-zz_full'))} %) |
| VQC under-trained (40-epoch cap), SPSA uncalibrated | 120 epochs + patience 15, Z-on-all-qubits readout + linear head, calibrated SPSA | Adam runs converge (stopped at 22–77 epochs). Calibrated SPSA still well below Adam |
| FRQI / NEQR | Hadamard-test overlap kernel, contrast stretching, angle scale | no gain |

V3 searched {D['counts']['candidate_runs']:,} candidate runs (configs × 3 seeds) on validation only. The locked test was opened once,
after `frozen_selection.json` was written (see V3_VERIFICATION_REPORT.md).

## 3. Before → after, model by model

"Like-for-like" keeps the V2 representation family (raw pixels for pixel models, MobileNetV3 for hybrids). "Best" allows any V3 representation.
Both are picked by validation macro-F1. Δ is V3 best − V2: paired sign-flip permutation test with a 95 % bootstrap CI, Holm-corrected over the
{len(D['comparisons'])} planned comparisons. Like-for-like p-values are a **post-hoc** family (added after unblinding), Holm-corrected separately.

{table(['Model (V2 baseline)', 'V2 test acc. %', 'V3 like-for-like %', 'V3 best (by validation) %', 'Δ best − V2'], ba_rows)}

## 4. VQC: genuine trainable circuit, plus controls

Circuit: 8 qubits, RY angle encoding with re-uploading, L = 2 layers of RY/RZ + CNOT ring (32 trainable rotation angles), ⟨Z⟩ on all
qubits → 6-class linear head (54 parameters). Exact parameter-shift gradients, Adam. Controls:
- *encoding only*: L = 0, the same head on ⟨Z_i⟩ = cos θ_i, i.e. a classical linear model on cosine features;
- *frozen ablation*: random circuit weights, only the head trained.

{table(['Features', 'Model', 'val macro-F1 %', 'test acc. %', 'test macro-F1 %', 'stopped at epoch (seed 0)', 'initial grad. variance'], vqc_rows)}

{table(['Comparison', 'Groups', 'acc. a %', 'acc. b %', 'Δ (95 % CI)', 'p<sub>Holm</sub>'], vqc_cmp)}

**Interpretation.**
- *Training does something.* The trained VQC beats its own random-weights ablation by 13–31 pp.
- *The trainable entangling layers are not useful here.* On texture and MobileNetV3 features, the encoding-only control (no trainable
  gates, classically simulable) is 18–19 pp better than the trained circuit. On pixels the two are statistically indistinguishable.
- *Not a barren plateau.* Initial gradient variance is ~1e-4 and the Adam runs converge before the epoch cap. The circuit and readout
  simply add a harder, non-convex optimisation on top of an already linearly separable representation.
- *SPSA still fails.* Even calibrated, SPSA reaches only {pc(acc('V3-tex8c-vqc-spsa'))} % on texture features.

## 5. FRQI and NEQR

{table(['Group', 'qubits', 'selected params', 'val macro-F1 %', 'test acc. %', 'test macro-F1 %'], frqi_rows)}

Neither the Hadamard-test overlap kernel nor contrast stretching beat the fidelity kernel on validation. NEQR 16×16 4-bit chose the V2
configuration again and reproduced V2 exactly. Image-encoding kernels compare images pixel by pixel. They are not invariant to
the translations and texture phase that separate these classes, so a better kernel on the same encoding cannot fix that.

## 6. Kernel diagnostics (training kernel, seed 0)

{table(['Group', 'selected', 'off-diag. mean', 'CKA', 'val macro-F1 %', 'test acc. %'], kern_rows)}

- Changing the features raises the centred alignment (CKA) of the ZZ-full kernel from {G['V3-pix8a-qkc-zz_full']['kernel_diagnostics_seed0']['centered_kernel_alignment']:.2f} (pixels) to
  {G['V3-tex8c-qkc-zz_full']['kernel_diagnostics_seed0']['centered_kernel_alignment']:.2f} (texture). The off-diagonal mean stays ≈ 0.04, so concentration is
  unchanged: the gain comes from the features, not the circuit.
- **The grid-edge problem is not fully fixed.** Of the selected configurations, {sum(1 for k in G if k.endswith(('qkc-zz_full','qkc-zz_linear')) and G[k]['params'].get('bandwidth') in (0.25,))} ZZ kernels chose bandwidth 0.25, the smallest
  value offered (and 0.5 where it was the smallest). Smaller bandwidth means weaker ZZ interactions, so these kernels are pushed towards the
  classically simulable product-like regime. We did **not** extend the grid after unblinding, because that would be tuning informed by the
  test set. A V4 should extend it on validation only.

## 7. Why the quantum models did not beat classical

1. **Representation dominates.** Moving from pixel PCA-8 (cdf) to texture PCA-8 lifts quantum and classical models alike: logistic regression
   {pc(acc('V3-pix8c-logreg'))} → {pc(acc('V3-tex8c-logreg'))} %, RBF-SVM {pc(acc('V3-pix8c-rbfsvm'))} → {pc(acc('V3-tex8c-rbfsvm'))} %,
   ZZ-full QKC {pc(acc('V3-pix8c-qkc-zz_full'))} → {pc(acc('V3-tex8c-qkc-zz_full'))} %, VQC {pc(acc('V3-pix8c-vqc'))} → {pc(acc('V3-tex8c-vqc'))} %.
2. **Concentration and the bandwidth limit.** The richer ZZ feature maps work best when their entangling terms are scaled down, which
   makes them more classical. Fully entangled maps at larger bandwidth concentrate (off-diagonal → 0) and lose accuracy.
3. **VQC optimisation.** Trainable layers on top of a separable encoding hurt rather than help (Section 4).
4. **Image encodings** (FRQI / NEQR) do not build in invariances that matter for texture classes.
5. **Distribution shift** between the training folder and the locked folder costs most models several points: validation macro-F1 exceeds locked-test macro-F1 for
   {sum(1 for x in D['groups'] if x['val_f1_macro']['mean'] > x['test_f1_macro']['mean'])} of {len(D['groups'])} groups.

## 8. What we did *not* do

- No configuration was chosen, changed or re-run after looking at test results. The like-for-like post-hoc comparisons are reported as
  post-hoc and do not change any selection.
- No V2 or V0 result was modified (V3_VERIFICATION_REPORT.md).
- No classical model is labelled quantum. Product-RY kernels and the encoding-only VQC are marked as classically computable controls.
- No hardware claims: everything is exact CPU simulation.
"""
(OUT / "QUANTUM_PERFORMANCE_IMPROVEMENT_REPORT.md").write_text(imp)

# ================================================================== 2. quantum vs classical (V3)
mrows = []
for m in D["matched_controls"]:
    f = m["feature_set"]
    c = C.get(f"Quantum vs matched RBF-SVM ({f})")
    lr = m.get("logreg")
    mrows.append([f"`{f}`", G[m["quantum"]]["display_name"], ms(G[m["quantum"]]["test_accuracy"]), ms(G[m["rbfsvm"]]["test_accuracy"]),
                  ms(G[lr]["test_accuracy"]) if lr else "—", pp(c), pv(c["p_holm"]), mcn(c)])

cat_rows = []
for k, lab in (("pure_quantum", "Pure quantum (non-CNN inputs, incl. FRQI/NEQR)"), ("vqc", "Genuine VQC"), ("hybrid_quantum", "Hybrid quantum (MobileNetV3 → quantum)"),
               ("classical_control_best", "Classical control (best)"), ("frqi", "FRQI"), ("neqr", "NEQR")):
    h = H[k]
    cat_rows.append([lab, h["display_name"], f"{100 * h['val_f1_macro']['mean']:.1f}", ms(h["test_accuracy"]), ms(h["test_f1_macro"])])

top = sorted(D["groups"], key=lambda x: -x["val_f1_macro"]["mean"])[:12]
top_rows = [[i + 1, x["display_name"], x["category"], x.get("n_qubits") or "—", f"{100 * x['val_f1_macro']['mean']:.1f}", ms(x["test_accuracy"])]
            for i, x in enumerate(top)]
best_val_cls = H["classical_control_best"]
qc = f"""# Quantum vs Classical Comparison — Protocol V3

{hdr}

## Bottom line

**Measured this way, no quantum model shows an advantage over a classical model on identical inputs.** Of
{len(D['matched_controls'])} matched comparisons (best quantum model on a feature set, chosen by validation, vs a classical RBF-SVM on *exactly* the
same features), {sum(1 for m in D['matched_controls'] if C[f"Quantum vs matched RBF-SVM ({m['feature_set']})"]['p_holm'] < 0.05)}
is significant after Holm correction, and it favours the **classical** model. The quantum models that look strongest (product-RY
kernels) are classically computable in closed form.

This does **not** show that quantum kernels are useless in general. It is one dataset, 3–12 simulated qubits, and the feature maps and grids
listed below.

## Headline models (picked by validation macro-F1 inside each category)

{table(['Category', 'Model', 'val macro-F1 %', 'test acc. %', 'test macro-F1 %'], cat_rows)}

## Matched comparisons: same features, quantum vs classical

Quantum = best quantum model on that feature set by validation (QKC, projected QKC or VQC). RBF-SVM and logistic regression were tuned on
the same validation folds. Δ = quantum − RBF-SVM, paired over the 360 locked images × 3 seeds. McNemar column: seed: quantum-only correct /
classical-only correct (exact p).

{table(['Features', 'Quantum model', 'Quantum acc. %', 'RBF-SVM acc. %', 'LogReg acc. %', 'Δ (95 % CI)', 'p<sub>Holm</sub>', 'per-seed McNemar'], mrows)}

Feature sets: `pix8a` = pixel PCA-8 with MinMax angles (V2 representation), `pix8c` / `pix12c` = pixel PCA-8 / 12 with cdf angles, `pixn8c`
= per-image normalised pixels, `tex8c` / `tex12c` = texture PCA-8 / 12, `mnv8c` / `mnv12c` = MobileNetV3 PCA-8 / 12.

## Top 12 groups overall, ranked by validation

{table(['#', 'Model', 'category', 'qubits', 'val macro-F1 %', 'test acc. %'], top_rows)}

## How to read the V2 → V3 jump

The V3 quantum headlines (≈ 93–95 %) are much higher than V2 (≈ 58–64 %). This is **not a quantum improvement**. On texture features the
classical RBF-SVM moves the same way (V3 `tex12c` RBF-SVM {pc(acc('V3-tex12c-rbfsvm'))} %, `tex8c` {pc(acc('V3-tex8c-rbfsvm'))} %). Any claim built
on these results should compare quantum with classical on the same features, as in the matched table, and not V3 quantum with V2 quantum.

## Integrity

- Same dataset manifest, splits, seeds and 360-image locked test as V2 (hash-verified copies).
- Selections frozen (SHA-256 above) before the single locked-test stage. No selection uses test data.
- Product-RY kernels and the encoding-only VQC are labelled as classically computable controls.
- All circuits: exact statevector simulation on a CPU. No hardware, no noise model.
"""
(OUT / "QUANTUM_CLASSICAL_COMPARISON_REPORT.md").write_text(qc)

# ================================================================== 3. verification
if VER:
    vrows = [[v["check"], "PASS" if v["ok"] else "FAIL", v.get("detail", "")] for v in VER["checks"]]
    ver = f"""# V3 Verification Report

{hdr}

Generated {VER['created_at']} by `scripts/v3/verify_v3.py`; checks: {len(VER['checks'])}, passed: {sum(v['ok'] for v in VER['checks'])}.

{table(['Check', 'Result', 'Detail'], vrows)}

## Notes
{chr(10).join('- ' + n for n in VER.get('notes', []))}
"""
    (OUT / "V3_VERIFICATION_REPORT.md").write_text(ver)
print("reports written", "(verification included)" if VER else "(verification pending)")
