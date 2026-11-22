# Quantum Performance Improvement Report — Protocol V3

Protocol V3 · 70 frozen groups · 5,316 validation runs (0 failed) · selections frozen 2026-11-16T08:19:14.500799 (SHA-256 `54c5c6e64cd95502ee8c95fd11d4b39b55455787535d614915e303ab238aedc5`) · 70 locked-test evaluation stages.

Source: `results/qml_v3/aggregates/v3_results.json` (built by `scripts/v3/analyze_v3.py` from the per-experiment records). Accuracy and macro-F1 are on the 360 locked test images, mean ± s.d. over seeds 0, 1, 2. All quantum circuits are simulated exactly (statevector) on a CPU; no quantum hardware and no noise model were used.

## 1. Summary (read this first)

* **Did the quantum models improve?** Their locked-test accuracy did, sometimes a lot. But **the gain comes from a better
  classical input representation**, not from anything quantum. On those same inputs, an ordinary classical RBF-SVM is as
  good or better.
* **Biggest effect: texture features.** Replacing raw-pixel PCA with fixed (not learned) LBP + GLCM texture
  features lifted the 8-qubit ZZ-full kernel from 64.0 % (V2) to
  93.0 % (+29.0 pp [+24.9, +33.2], p<sub>Holm</sub> = 0.002).
  The classical RBF-SVM on the identical 8 texture features scores 93.2 %. The best quantum model on those features by validation
  (`V3-tex8c-qkc-product_ry`) minus that RBF-SVM = -0.2 pp [-0.9, +0.5],
  p<sub>Holm</sub> = 1.000.
* **Like-for-like (still raw pixels), V3 did not help the ZZ kernels.** Validation chose exactly the V2 configuration again, and
  it reproduced V2 to the image (difference 0.0 pp). The product-RY kernel improved by
  +5.6 pp [+1.6, +9.7] (12 PCA components instead of 8; post-hoc test).
* **The best "pure quantum" model is a product-RY kernel**, 95.3 %. A product-RY
  kernel is a product of single-qubit cosines, so a classical computer can evaluate it in closed form. It is a control, not
  evidence of quantum benefit.
* **VQC: a genuine improvement in training, a negative result for the circuit.** The genuine trainable 8-qubit VQC
  on texture features reaches 73.4 % (V2 VQC 48.1 %).
  But the **encoding-only control (no trainable gates, L = 0) reaches 92.6 %**: the trainable
  entangling layers *reduce* accuracy by 19.2 pp. On raw pixels the V3 VQC is
  worse than V2 (35.3 % vs 48.1 %).
* **FRQI / NEQR did not improve.** NEQR 16×16 4-bit was re-selected unchanged (60.2 %). The best FRQI fell from
  60.6 % to 57.5 % (-3.1 pp [-5.6, -0.7], p<sub>Holm</sub> = 0.167, not significant after correction).
* **Hybrid (MobileNetV3 + quantum) got slightly worse.** All three V3 hybrid kernels score 91.3 %, vs 91.9–93.2 % in V2.
  V3 searched only the cdf angle map for MobileNetV3 features, not V2's MinMax map, and the V3 hybrids are already lower on
  validation (0.939–0.964
  vs 0.965–0.970 in V2). The cdf map was a poor
  choice for these features; this shows without the test set. V3 does not re-run them, because the locked test is now open.

## 2. What was tried (all chosen on validation, frozen before the locked test)

| Audit finding (QUANTUM_PERFORMANCE_AUDIT.md) | V3 change | Outcome on the locked test |
|---|---|---|
| Raw-pixel PCA carries little class information (CKA ≈ 0.30 for every pixel kernel) | fixed texture features (LBP 8/1, 16/2, 24/3 + GLCM + gradient statistics, 76-d) → PCA 8 / 12 | large gain **for every model, quantum and classical alike** |
| MinMax angle map squashes outliers (audit: RBF 64.8 % standard vs 60.7 % angle) | cdf map: θ = π·Φ(z) | no consistent gain on pixels (pix8c vs pix8a; Section 6) |
| Per-image brightness differences | per-image normalisation (pixn8c) | worse (48.0 % best quantum) |
| Truncated hyperparameter grids | wider bandwidth / C grids | ZZ kernels now pick the **smallest** bandwidth offered (0.25), so the grid edge remains (Section 6) |
| Kernel concentration | projected quantum kernel (Bloch vectors) | **worse** than fidelity kernels (e.g. tex8c PQK ZZ-full 40.7 %) |
| VQC under-trained (40-epoch cap), SPSA uncalibrated | 120 epochs + patience 15, Z-on-all-qubits readout + linear head, calibrated SPSA | Adam runs converge (stopped at 22–77 epochs). Calibrated SPSA still well below Adam |
| FRQI / NEQR | Hadamard-test overlap kernel, contrast stretching, angle scale | no gain |

V3 searched 5,316 candidate runs (configs × 3 seeds) on validation only. The locked test was opened once,
after `frozen_selection.json` was written (see V3_VERIFICATION_REPORT.md).

## 3. Before → after, model by model

"Like-for-like" keeps the V2 representation family (raw pixels for pixel models, MobileNetV3 for hybrids). "Best" allows any V3 representation.
Both are picked by validation macro-F1. Δ is V3 best − V2: paired sign-flip permutation test with a 95 % bootstrap CI, Holm-corrected over the
24 planned comparisons. Like-for-like p-values are a **post-hoc** family (added after unblinding), Holm-corrected separately.

| Model (V2 baseline) | V2 test acc. % | V3 like-for-like % | V3 best (by validation) % | Δ best − V2 |
|---|---|---|---|---|
| ZZ-full QKC (V2: pixel PCA-8) | 64.0 ± 3.5<br>`E3-pca8-qkc-zz_full` | 64.0 ± 3.5<br>`V3-pix8a-qkc-zz_full` (8 q)<br>+0.0 pp [+0.0, +0.0], p<sub>Holm,post-hoc</sub>=1.000 | 93.0 ± 3.0<br>`V3-tex8c-qkc-zz_full` (8 q) | +29.0 pp [+24.9, +33.2]<br>p<sub>Holm</sub>=0.002 |
| ZZ-linear QKC (V2: pixel PCA-8) | 60.9 ± 2.2<br>`E3-pca8-qkc-zz_linear` | 60.9 ± 2.2<br>`V3-pix8a-qkc-zz_linear` (8 q)<br>+0.0 pp [+0.0, +0.0], p<sub>Holm,post-hoc</sub>=1.000 | 91.4 ± 3.8<br>`V3-tex8c-qkc-zz_linear` (8 q) | +30.5 pp [+26.1, +34.6]<br>p<sub>Holm</sub>=0.002 |
| product-RY QKC (V2: pixel PCA-8) | 58.1 ± 2.3<br>`E3-pca8-qkc-product_ry` | 63.7 ± 2.8<br>`V3-pix12c-qkc-product_ry` (12 q)<br>+5.6 pp [+1.6, +9.7], p<sub>Holm,post-hoc</sub>=0.027 | 95.3 ± 3.2<br>`V3-tex12c-qkc-product_ry` (12 q) | +37.2 pp [+32.4, +42.0]<br>p<sub>Holm</sub>=0.002 |
| FRQI angle-scaled 8×8 | 60.6 ± 1.2<br>`E1b-frqi8-qkc-scaled` | 57.5 ± 2.1<br>`V3-frqi8` (7 q) | 57.5 ± 2.1<br>`V3-frqi8` (7 q) | -3.1 pp [-5.6, -0.7]<br>p<sub>Holm</sub>=0.167 |
| NEQR 4-bit 16×16 | 60.2 ± 0.4<br>`E2-neqr16-b4-qkc` | 60.2 ± 0.4<br>`V3-neqr16` (12 q) | 60.2 ± 0.4<br>`V3-neqr16` (12 q) | +0.0 pp [+0.0, +0.0]<br>p<sub>Holm</sub>=1.000 |
| Genuine VQC (V2: pixel PCA-8) | 48.1 ± 1.9<br>`E4-pca8-vqc` | 35.3 ± 1.7<br>`V3-pix8c-vqc` (8 q)<br>-12.8 pp [-17.2, -8.3], p<sub>Holm,post-hoc</sub>=<0.001 | 73.4 ± 3.8<br>`V3-tex8c-vqc` (8 q) | +25.4 pp [+20.2, +30.6]<br>p<sub>Holm</sub>=0.002 |
| CNN + product-RY QKC | 93.2 ± 1.1<br>`E5-mnv3pca8-qkc-product_ry` | 91.3 ± 0.8<br>`V3-mnv8c-qkc-product_ry` (8 q) | 91.3 ± 0.8<br>`V3-mnv8c-qkc-product_ry` (8 q) | -1.9 pp [-3.5, -0.4]<br>p<sub>Holm</sub>=0.200 |
| CNN + ZZ-full QKC | 92.7 ± 1.4<br>`E5-mnv3pca8-qkc-zz_full` | 91.3 ± 2.6<br>`V3-mnv8c-qkc-zz_full` (8 q) | 91.3 ± 2.6<br>`V3-mnv8c-qkc-zz_full` (8 q) | -1.4 pp [-2.9, +0.1]<br>p<sub>Holm</sub>=0.773 |
| CNN + ZZ-linear QKC | 91.9 ± 2.2<br>`E5-mnv3pca8-qkc-zz_linear` | 91.3 ± 1.8<br>`V3-mnv8c-qkc-zz_linear` (8 q) | 91.3 ± 1.8<br>`V3-mnv8c-qkc-zz_linear` (8 q) | -0.6 pp [-1.8, +0.6]<br>p<sub>Holm</sub>=1.000 |
| CNN + VQC | 81.3 ± 7.2<br>`E5-mnv3pca8-vqc` | 72.4 ± 2.4<br>`V3-mnv8c-vqc` (8 q) | 72.4 ± 2.4<br>`V3-mnv8c-vqc` (8 q) | -8.9 pp [-12.0, -5.7]<br>p<sub>Holm</sub>=0.002 |

## 4. VQC: genuine trainable circuit, plus controls

Circuit: 8 qubits, RY angle encoding with re-uploading, L = 2 layers of RY/RZ + CNOT ring (32 trainable rotation angles), ⟨Z⟩ on all
qubits → 6-class linear head (54 parameters). Exact parameter-shift gradients, Adam. Controls:
- *encoding only*: L = 0, the same head on ⟨Z_i⟩ = cos θ_i, i.e. a classical linear model on cosine features;
- *frozen ablation*: random circuit weights, only the head trained.

| Features | Model | val macro-F1 % | test acc. % | test macro-F1 % | stopped at epoch (seed 0) | initial grad. variance |
|---|---|---|---|---|---|---|
| pix8c | trained VQC (Adam, parameter shift) | 49.0 ± 6.3 | 35.3 ± 1.7 | 32.6 ± 2.0 | 22 | 2.3e-04 |
| pix8c | trained VQC (calibrated SPSA) | 30.3 ± 11.2 | 21.0 ± 6.7 | 18.8 ± 5.9 | — | 2.3e-04 |
| pix8c | encoding only, L = 0 (control) | 38.5 ± 3.1 | 34.0 ± 2.8 | 33.5 ± 2.6 | 18 | 0.0e+00 |
| pix8c | random frozen circuit (ablation) | 37.1 ± 3.7 | 22.0 ± 2.4 | 18.7 ± 1.9 | 31 | 0.0e+00 |
| tex8c | trained VQC (Adam, parameter shift) | 75.4 ± 2.2 | 73.4 ± 3.8 | 73.3 ± 3.7 | 53 | 1.2e-04 |
| tex8c | trained VQC (calibrated SPSA) | 45.4 ± 20.5 | 51.1 ± 15.1 | 46.9 ± 20.5 | — | 1.2e-04 |
| tex8c | encoding only, L = 0 (control) | 93.6 ± 3.1 | 92.6 ± 2.5 | 92.4 ± 2.7 | 24 | 0.0e+00 |
| tex8c | random frozen circuit (ablation) | 47.4 ± 3.3 | 42.9 ± 3.0 | 42.7 ± 2.3 | 57 | 0.0e+00 |
| mnv8c | trained VQC (Adam, parameter shift) | 87.7 ± 5.1 | 72.4 ± 2.4 | 71.8 ± 2.0 | 77 | 2.8e-04 |
| mnv8c | encoding only, L = 0 (control) | 94.0 ± 3.7 | 90.8 ± 1.3 | 90.5 ± 1.5 | 25 | 0.0e+00 |
| mnv8c | random frozen circuit (ablation) | 49.3 ± 5.2 | 42.9 ± 8.8 | 42.4 ± 8.9 | 41 | 0.0e+00 |

| Comparison | Groups | acc. a % | acc. b % | Δ (95 % CI) | p<sub>Holm</sub> |
|---|---|---|---|---|---|
| VQC vs vqc-ablation-frozen (mnv8c) | `V3-mnv8c-vqc` vs `V3-mnv8c-vqc-ablation-frozen` | 72.4 | 42.9 | +29.5 pp [+25.3, +33.8] | 0.002 |
| VQC vs vqc-encoding-only (mnv8c) | `V3-mnv8c-vqc` vs `V3-mnv8c-vqc-encoding-only` | 72.4 | 90.8 | -18.4 pp [-21.9, -15.0] | 0.002 |
| VQC vs vqc-ablation-frozen (pix8c) | `V3-pix8c-vqc` vs `V3-pix8c-vqc-ablation-frozen` | 35.3 | 22.0 | +13.2 pp [+9.4, +17.1] | 0.002 |
| VQC vs vqc-encoding-only (pix8c) | `V3-pix8c-vqc` vs `V3-pix8c-vqc-encoding-only` | 35.3 | 34.0 | +1.3 pp [-3.1, +5.7] | 1.000 |
| VQC vs vqc-ablation-frozen (tex8c) | `V3-tex8c-vqc` vs `V3-tex8c-vqc-ablation-frozen` | 73.4 | 42.9 | +30.6 pp [+26.3, +34.8] | 0.002 |
| VQC vs vqc-encoding-only (tex8c) | `V3-tex8c-vqc` vs `V3-tex8c-vqc-encoding-only` | 73.4 | 92.6 | -19.2 pp [-22.5, -15.7] | 0.002 |

**Interpretation.**
- *Training does something.* The trained VQC beats its own random-weights ablation by 13–31 pp.
- *The trainable entangling layers are not useful here.* On texture and MobileNetV3 features, the encoding-only control (no trainable
  gates, classically simulable) is 18–19 pp better than the trained circuit. On pixels the two are statistically indistinguishable.
- *Not a barren plateau.* Initial gradient variance is ~1e-4 and the Adam runs converge before the epoch cap. The circuit and readout
  simply add a harder, non-convex optimisation on top of an already linearly separable representation.
- *SPSA still fails.* Even calibrated, SPSA reaches only 51.1 % on texture features.

## 5. FRQI and NEQR

| Group | qubits | selected params | val macro-F1 % | test acc. % | test macro-F1 % |
|---|---|---|---|---|---|
| `V3-frqi2` | 3 | {"angle_scale": 2.0, "bits": 8, "kernel": "fidelity", "norm": "none", "C": 1000.0} | 57.1 ± 2.7 | 47.8 ± 2.4 | 45.9 ± 2.3 |
| `V3-frqi4` | 5 | {"angle_scale": 2.0, "bits": 8, "kernel": "fidelity", "norm": "none", "C": 1000.0} | 67.5 ± 2.8 | 53.2 ± 1.3 | 51.4 ± 0.8 |
| `V3-frqi8` | 7 | {"angle_scale": 2.0, "bits": 8, "kernel": "fidelity", "norm": "none", "C": 1000.0} | 69.4 ± 4.3 | 57.5 ± 2.1 | 55.3 ± 2.4 |
| `V3-frqi16` | 9 | {"angle_scale": 2.0, "bits": 8, "kernel": "fidelity", "norm": "none", "C": 100.0} | 69.2 ± 5.4 | 59.9 ± 0.6 | 57.7 ± 0.6 |
| `V3-neqr2` | 6 | {"angle_scale": 1.0, "bits": 4, "kernel": "fidelity", "norm": "none", "C": 1.0} | 48.1 ± 2.4 | 40.6 ± 1.8 | 38.5 ± 1.7 |
| `V3-neqr4` | 8 | {"angle_scale": 1.0, "bits": 4, "kernel": "fidelity", "norm": "none", "C": 1.0} | 62.5 ± 4.7 | 51.3 ± 1.4 | 48.6 ± 1.2 |
| `V3-neqr8` | 10 | {"angle_scale": 1.0, "bits": 4, "kernel": "fidelity", "norm": "none", "C": 10.0} | 69.6 ± 3.9 | 59.9 ± 1.1 | 56.7 ± 1.9 |
| `V3-neqr16` | 12 | {"angle_scale": 1.0, "bits": 4, "kernel": "fidelity", "norm": "none", "C": 10.0} | 72.7 ± 5.6 | 60.2 ± 0.4 | 56.5 ± 0.4 |

Neither the Hadamard-test overlap kernel nor contrast stretching beat the fidelity kernel on validation. NEQR 16×16 4-bit chose the V2
configuration again and reproduced V2 exactly. Image-encoding kernels compare images pixel by pixel. They are not invariant to
the translations and texture phase that separate these classes, so a better kernel on the same encoding cannot fix that.

## 6. Kernel diagnostics (training kernel, seed 0)

| Group | selected | off-diag. mean | CKA | val macro-F1 % | test acc. % |
|---|---|---|---|---|---|
| `V3-pix8a-qkc-zz_full` | {"bandwidth": 1.0, "C": 100.0} | 0.040 | 0.30 | 76.7 ± 6.3 | 64.0 ± 3.5 |
| `V3-pix8c-qkc-zz_full` | {"bandwidth": 0.25, "C": 10.0} | 0.050 | 0.18 | 67.3 ± 2.0 | 55.6 ± 1.9 |
| `V3-tex8c-qkc-zz_full` | {"bandwidth": 0.25, "C": 1.0} | 0.042 | 0.39 | 93.8 ± 3.1 | 93.0 ± 3.0 |
| `V3-tex12c-qkc-zz_full` | {"bandwidth": 0.5, "C": 10.0} | 0.005 | 0.13 | 91.8 ± 3.6 | 89.1 ± 1.4 |
| `V3-tex8c-qkc-product_ry` | {"bandwidth": 1.0, "C": 10.0} | 0.091 | 0.68 | 94.7 ± 3.6 | 93.1 ± 1.9 |
| `V3-tex12c-qkc-product_ry` | {"bandwidth": 0.5, "C": 10.0} | 0.335 | 0.63 | 95.1 ± 3.1 | 95.3 ± 3.2 |
| `V3-mnv8c-qkc-zz_full` | {"bandwidth": 0.25, "C": 10.0} | 0.043 | 0.45 | 93.9 ± 3.3 | 91.3 ± 2.6 |
| `V3-tex8c-pqk-zz_full` | {"bandwidth": 0.5, "C": 1000.0, "gamma": 3.0} | 0.808 | 0.03 | 41.3 ± 2.6 | 40.7 ± 1.8 |
| `V3-frqi8` | {"C": 1000.0, "angle_scale": 2.0, "bits": 8} | 0.561 | 0.26 | 69.4 ± 4.3 | 57.5 ± 2.1 |
| `V3-neqr16` | {"C": 10.0, "angle_scale": 1.0, "bits": 4} | 0.021 | 0.24 | 72.7 ± 5.6 | 60.2 ± 0.4 |

- Changing the features raises the centred alignment (CKA) of the ZZ-full kernel from 0.30 (pixels) to
  0.39 (texture). The off-diagonal mean stays ≈ 0.04, so concentration is
  unchanged: the gain comes from the features, not the circuit.
- **The grid-edge problem is not fully fixed.** Of the selected configurations, 7 ZZ kernels chose bandwidth 0.25, the smallest
  value offered (and 0.5 where it was the smallest). Smaller bandwidth means weaker ZZ interactions, so these kernels are pushed towards the
  classically simulable product-like regime. We did **not** extend the grid after unblinding, because that would be tuning informed by the
  test set. A V4 should extend it on validation only.

## 7. Why the quantum models did not beat classical

1. **Representation dominates.** Moving from pixel PCA-8 (cdf) to texture PCA-8 lifts quantum and classical models alike: logistic regression
   35.6 → 91.9 %, RBF-SVM 60.7 → 93.2 %,
   ZZ-full QKC 55.6 → 93.0 %, VQC 35.3 → 73.4 %.
2. **Concentration and the bandwidth limit.** The richer ZZ feature maps work best when their entangling terms are scaled down, which
   makes them more classical. Fully entangled maps at larger bandwidth concentrate (off-diagonal → 0) and lose accuracy.
3. **VQC optimisation.** Trainable layers on top of a separable encoding hurt rather than help (Section 4).
4. **Image encodings** (FRQI / NEQR) do not build in invariances that matter for texture classes.
5. **Distribution shift** between the training folder and the locked folder costs most models several points: validation macro-F1 exceeds locked-test macro-F1 for
   65 of 70 groups.

## 8. What we did *not* do

- No configuration was chosen, changed or re-run after looking at test results. The like-for-like post-hoc comparisons are reported as
  post-hoc and do not change any selection.
- No V2 or V0 result was modified (V3_VERIFICATION_REPORT.md).
- No classical model is labelled quantum. Product-RY kernels and the encoding-only VQC are marked as classically computable controls.
- No hardware claims: everything is exact CPU simulation.
