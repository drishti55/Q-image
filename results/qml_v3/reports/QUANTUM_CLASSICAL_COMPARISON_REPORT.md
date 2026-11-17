# Quantum vs Classical Comparison — Protocol V3

Protocol V3 · 70 frozen groups · 5,316 validation runs (0 failed) · selections frozen 2026-11-16T08:19:14.500799 (SHA-256 `54c5c6e64cd95502ee8c95fd11d4b39b55455787535d614915e303ab238aedc5`) · 70 locked-test evaluation stages.

Source: `results/qml_v3/aggregates/v3_results.json` (built by `scripts/v3/analyze_v3.py` from the per-experiment records). Accuracy and macro-F1 are on the 360 locked test images, mean ± s.d. over seeds 0, 1, 2. All quantum circuits are simulated exactly (statevector) on a CPU; no quantum hardware and no noise model were used.

## Bottom line

**Measured this way, no quantum model shows an advantage over a classical model on identical inputs.** Of
8 matched comparisons (best quantum model on a feature set, chosen by validation, vs a classical RBF-SVM on *exactly* the
same features), 1
is significant after Holm correction, and it favours the **classical** model. The quantum models that look strongest (product-RY
kernels) are classically computable in closed form.

This does **not** show that quantum kernels are useless in general. It is one dataset, 3–12 simulated qubits, and the feature maps and grids
listed below.

## Headline models (picked by validation macro-F1 inside each category)

| Category | Model | val macro-F1 % | test acc. % | test macro-F1 % |
|---|---|---|---|---|
| Pure quantum (non-CNN inputs, incl. FRQI/NEQR) | Texture PCA-12 + QKC product-RY | 95.1 | 95.3 ± 3.2 | 95.1 ± 3.4 |
| Genuine VQC | Texture PCA-8 + VQC · L=2 · zall | 75.4 | 73.4 ± 3.8 | 73.3 ± 3.7 |
| Hybrid quantum (MobileNetV3 → quantum) | MobileNetV3 PCA-8 + QKC product-RY | 96.4 | 91.3 ± 0.8 | 90.8 ± 1.2 |
| Classical control (best) | MobileNetV3 PCA-8 + RBF-SVM | 96.4 | 90.6 ± 0.6 | 90.2 ± 0.4 |
| FRQI | FRQI 8×8 · angle ×2.0 · fidelity kernel | 69.4 | 57.5 ± 2.1 | 55.3 ± 2.4 |
| NEQR | NEQR 16×16 · 4-bit · fidelity kernel | 72.7 | 60.2 ± 0.4 | 56.5 ± 0.4 |

## Matched comparisons: same features, quantum vs classical

Quantum = best quantum model on that feature set by validation (QKC, projected QKC or VQC). RBF-SVM and logistic regression were tuned on
the same validation folds. Δ = quantum − RBF-SVM, paired over the 360 locked images × 3 seeds. McNemar column: seed: quantum-only correct /
classical-only correct (exact p).

| Features | Quantum model | Quantum acc. % | RBF-SVM acc. % | LogReg acc. % | Δ (95 % CI) | p<sub>Holm</sub> | per-seed McNemar |
|---|---|---|---|---|---|---|---|
| `mnv12c` | MobileNetV3 PCA-12 + QKC product-RY | 91.2 ± 0.7 | 92.2 ± 1.7 | 92.0 ± 1.3 | -1.0 pp [-2.3, +0.2] | 1.000 | s0: 5/5 (p=1.000), s1: 4/8 (p=0.388), s2: 1/8 (p=0.039) |
| `mnv8c` | MobileNetV3 PCA-8 + QKC product-RY | 91.3 ± 0.8 | 90.6 ± 0.6 | 91.6 ± 1.4 | +0.6 pp [-0.2, +1.6] | 1.000 | s0: 1/4 (p=0.375), s1: 4/1 (p=0.375), s2: 8/1 (p=0.039) |
| `pix12c` | Pixels PCA-12 + QKC product-RY | 63.7 ± 2.8 | 66.1 ± 2.1 | 37.6 ± 2.2 | -2.4 pp [-3.8, -1.0] | 0.020 | s0: 5/14 (p=0.064), s1: 4/15 (p=0.019), s2: 7/13 (p=0.263) |
| `pix8a` | Pixels PCA-8 (angle) + QKC ZZ-full | 64.0 ± 3.5 | 60.9 ± 1.3 | 38.1 ± 1.4 | +3.1 pp [+0.6, +5.7] | 0.254 | s0: 34/17 (p=0.024), s1: 22/20 (p=0.878), s2: 32/18 (p=0.065) |
| `pix8c` | Pixels PCA-8 + QKC product-RY | 56.4 ± 0.7 | 60.7 ± 3.1 | 35.6 ± 1.1 | -4.4 pp [-7.4, -1.3] | 0.095 | s0: 18/38 (p=0.010), s1: 17/20 (p=0.743), s2: 24/48 (p=0.006) |
| `pixn8c` | Pixels PCA-8 (per-image norm) + QKC product-RY | 48.0 ± 1.1 | 49.1 ± 2.9 | 30.1 ± 0.4 | -1.1 pp [-4.4, +2.1] | 1.000 | s0: 35/42 (p=0.494), s1: 32/27 (p=0.603), s2: 31/41 (p=0.289) |
| `tex12c` | Texture PCA-12 + QKC product-RY | 95.3 ± 3.2 | 95.6 ± 2.2 | 93.7 ± 2.8 | -0.3 pp [-1.4, +0.8] | 1.000 | s0: 2/11 (p=0.022), s1: 8/3 (p=0.227), s2: 3/2 (p=1.000) |
| `tex8c` | Texture PCA-8 + QKC product-RY | 93.1 ± 1.9 | 93.2 ± 2.0 | 91.9 ± 2.2 | -0.2 pp [-0.9, +0.5] | 1.000 | s0: 1/2 (p=1.000), s1: 2/2 (p=1.000), s2: 2/3 (p=1.000) |

Feature sets: `pix8a` = pixel PCA-8 with MinMax angles (V2 representation), `pix8c` / `pix12c` = pixel PCA-8 / 12 with cdf angles, `pixn8c`
= per-image normalised pixels, `tex8c` / `tex12c` = texture PCA-8 / 12, `mnv8c` / `mnv12c` = MobileNetV3 PCA-8 / 12.

## Top 12 groups overall, ranked by validation

| # | Model | category | qubits | val macro-F1 % | test acc. % |
|---|---|---|---|---|---|
| 1 | MobileNetV3 PCA-8 + RBF-SVM | classical_control | — | 96.4 | 90.6 ± 0.6 |
| 2 | MobileNetV3 PCA-8 + QKC product-RY | hybrid | 8 | 96.4 | 91.3 ± 0.8 |
| 3 | MobileNetV3 PCA-12 + QKC product-RY | hybrid | 12 | 96.4 | 91.2 ± 0.7 |
| 4 | MobileNetV3 PCA-12 + RBF-SVM | classical_control | — | 96.2 | 92.2 ± 1.7 |
| 5 | MobileNetV3 PCA-12 + Logistic Regression | classical_control | — | 95.8 | 92.0 ± 1.3 |
| 6 | Texture PCA-12 + RBF-SVM | classical_control | — | 95.3 | 95.6 ± 2.2 |
| 7 | MobileNetV3 PCA-8 + Logistic Regression | classical_control | — | 95.2 | 91.6 ± 1.4 |
| 8 | Texture PCA-12 + QKC product-RY | quantum_kernel | 12 | 95.1 | 95.3 ± 3.2 |
| 9 | Texture PCA-8 + RBF-SVM | classical_control | — | 95.1 | 93.2 ± 2.0 |
| 10 | MobileNetV3 PCA-8 + QKC ZZ-linear | hybrid | 8 | 95.0 | 91.3 ± 1.8 |
| 11 | Texture PCA-8 + QKC product-RY | quantum_kernel | 8 | 94.7 | 93.1 ± 1.9 |
| 12 | MobileNetV3 PCA-8 + VQC control (encoding only) | vqc_control | 8 | 94.0 | 90.8 ± 1.3 |

## How to read the V2 → V3 jump

The V3 quantum headlines (≈ 93–95 %) are much higher than V2 (≈ 58–64 %). This is **not a quantum improvement**. On texture features the
classical RBF-SVM moves the same way (V3 `tex12c` RBF-SVM 95.6 %, `tex8c` 93.2 %). Any claim built
on these results should compare quantum with classical on the same features, as in the matched table, and not V3 quantum with V2 quantum.

## Integrity

- Same dataset manifest, splits, seeds and 360-image locked test as V2 (hash-verified copies).
- Selections frozen (SHA-256 above) before the single locked-test stage. No selection uses test data.
- Product-RY kernels and the encoding-only VQC are labelled as classically computable controls.
- All circuits: exact statevector simulation on a CPU. No hardware, no noise model.
