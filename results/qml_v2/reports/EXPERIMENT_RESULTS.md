# Q-ImageLab Protocol V2 — Experiment Results

All numbers are measured outputs saved under `results/qml_v2/` (aggregated in `aggregates/analysis.json`, each with its
experiment ids). All quantum models are **noiseless classical simulations** (≤ 16 qubits); no quantum hardware was used.
Details per phase: `PHASE3_CLASSICAL.md` … `PHASE9_DASHBOARD.md` in this folder.

## 1. Dataset and protocol
- NEU-DET (manifest `neu-5625b937479b`): 1,800 images, 6 classes, 200×200, 240 train-folder + 60 validation-folder
  images per class. One exact duplicate pair (kept, same group); 123 images carry secondary defect annotations.
- **Locked test** = the whole validation folder (360 images), read only inside a logged final-evaluation stage after
  selection (90 logged accesses for 88 groups; the 2 repeats were exact reproductions — see PHASE5_VQC.md).
- Train folder → internal train/val (1,080 / 360) by **contiguous 20-index blocks**, 3 blocks per class to validation,
  seeds 0, 1, 2. Nearest-neighbour adjacency val→train within ±3 indices: 0.8–2.2% (vs 8–10% for a random split).
- Selection: best mean validation macro-F1 over the 3 seeds; then the selected checkpoints (no refit) are scored on the
  locked test. Reported: mean ± sample std over seeds; per-seed bootstrap CIs; paired exact McNemar tests.

## 2. Classification — locked test accuracy (mean ± std, 3 seeds)
### 2.1 Pixel features (64×64 → train-fitted PCA)
| k | LogReg | RBF-SVM (std. features) | RBF-SVM (identical angle features) | QKC product-RY (control) | QKC ZZ-linear | QKC ZZ-full | VQC (best) |
|---|---|---|---|---|---|---|---|
| 4 | 0.269 ± 0.030 | 0.554 ± 0.015 | 0.520 ± 0.006 | 0.513 ± 0.018 | 0.526 ± 0.025 | 0.524 ± 0.014 | 0.341 ± 0.011 |
| 6 | 0.326 ± 0.021 | 0.570 ± 0.011 | 0.569 ± 0.022 | 0.557 ± 0.016 | 0.557 ± 0.016 | 0.555 ± 0.014 | 0.445 ± 0.027 |
| 8 | 0.381 ± 0.014 | 0.648 ± 0.033 | 0.607 ± 0.011 | 0.581 ± 0.023 | 0.609 ± 0.022 | 0.640 ± 0.035 | 0.481 ± 0.019 |

### 2.2 Quantum image encodings as kernels (raw r×r pixels, original FRQI/NEQR)
| r | FRQI | FRQI angle-scaled (variant) | NEQR 2-bit | NEQR 4-bit | NEQR 8-bit |
|---|---|---|---|---|---|
| 2 | 0.430 ± 0.016 | — | 0.358 ± 0.007 | 0.406 ± 0.018 | 0.307 ± 0.004 |
| 4 | 0.527 ± 0.014 | 0.559 ± 0.009 | 0.450 ± 0.008 | 0.513 ± 0.014 | 0.398 ± 0.017 |
| 8 | 0.578 ± 0.011 | 0.606 ± 0.012 | 0.510 ± 0.008 | 0.599 ± 0.011 | 0.455 ± 0.011 |
| 16 | 0.576 ± 0.023 | 0.599 ± 0.006 | 0.531 ± 0.003 | 0.602 ± 0.004 | 0.503 ± 0.013 |

### 2.3 CNN features
| Model | Test accuracy |
|---|---|
| Small CNN (from scratch, 128×128) | 0.930 ± 0.059 (seeds: 0.886 / 0.906 / 0.997) |
| Frozen MobileNetV3 (576-d) + LogReg | 0.964 ± 0.011 |
| Frozen MobileNetV3 (576-d) + RBF-SVM | 0.964 ± 0.017 |
| CNN → PCA8 + LogReg / RBF-SVM (classical controls) | 0.920 ± 0.013 / 0.930 ± 0.007 |
| CNN → PCA8 + QKC product-RY / ZZ-linear / ZZ-full (hybrid) | 0.932 ± 0.011 / 0.919 ± 0.022 / 0.927 ± 0.014 |
| CNN → PCA8 + VQC (hybrid) | 0.813 ± 0.072 |

### 2.4 Relabelled legacy methods (classical)
V0 "HQCC" (closed-form encoding statistics + LogReg): 0.400–0.556. V0 "VQC" (fixed-feature softmax): 0.244–0.261.

## 3. Statistical comparisons (paired McNemar, per seed, α = 0.05, uncorrected)
- QKC vs classical RBF-SVM on identical PCA features: no difference at k = 4 (0/9 seed tests); k = 6: 2/9 significant,
  both favouring RBF-SVM; k = 8: ZZ-full better on 2/3 seeds (+6.1 and +5.6 points, p = 0.008 and 0.02; seed 1 −1.9,
  n.s.), product-RY worse on 2/3.
- With CNN features, QKC never beats the RBF-SVM (2/27 significant, both favouring RBF-SVM).
- VQC < RBF-SVM (9/9), VQC > its frozen-circuit ablation (9/9), VQC > LogReg on pixel PCA (8/9), VQC < LogReg on CNN
  PCA features at k = 6–8 (6/6).
- Frozen MobileNetV3 vs small CNN: 2/3 favour MobileNetV3.

## 4. Shot sensitivity (test accuracy; shots per kernel entry, Binomial sampling validated against Aer)
| Model | exact | 100 | 500 | 1,000 | 5,000 | 10,000 |
|---|---|---|---|---|---|---|
| PCA4 QKC ZZ-full | 0.524 | 0.446 | 0.483 | 0.484 | 0.480 | — |
| PCA6 QKC ZZ-full | 0.555 | 0.491 | 0.548 | 0.550 | 0.548 | — |
| PCA8 QKC ZZ-full | 0.640 | 0.571 | 0.635 | 0.634 | 0.634 | — |
| FRQI-overlap 8×8 | 0.578 | 0.335 | — | 0.393 | — | 0.463 |
| NEQR-overlap 8×8 4-bit | 0.599 | 0.562 | — | 0.594 | — | 0.601 |
Shot noise makes kernels indefinite (min eigenvalue down to −2.7). FRQI overlaps are close to 1 for all pairs, so
differences drown in sampling noise; NEQR overlaps are robust.

## 5. Kernel concentration
Training-kernel off-diagonal mean (seed 0, selected configs): product-RY 0.60–0.69 (k = 4–8); ZZ-linear 0.21 → 0.05;
ZZ-full 0.41 → 0.04 as k goes 4 → 8. Validation preferred small bandwidths (0.2–0.5) for k = 4–6, which counteract
concentration. Full bandwidth × feature-map × k table with CKA and eigenvalues: `analysis.json → kernel_concentration`.

## 6. VQC training behaviour
Adam with parameter-shift gradients was best at every k; COBYLA intermediate; SPSA (600 iterations) failed to learn.
Deeper circuits and data re-uploading helped at k = 6–8. Initial gradient variance fell from 5.2e-3 (k=4, L=3) to
9e-5 (k=8, L=3) — onset of barren-plateau behaviour. Training cost (CPU simulation): ~196 s per k = 8 model vs < 1 s
for kernel SVMs. RZ gates in the last layer provably have zero gradient for Z-basis readout (reported).

## 7. Reconstruction (separate task; 30 fixed train-folder images)
Statevector decoding is exact for FRQI and reproduces NEQR's quantisation error exactly (encoder/decoder consistency).
FRQI needs ~10⁴–10⁵ shots for MSE ≤ 10⁻³ at 8×8–16×16 (SSIM at 10³ shots falls from 0.89 at 2×2 to 0.15 at 16×16).
NEQR is exact once every pixel position is sampled (≥ 10³ shots up to 8×8, ≥ 10⁴ at 16×16) — its error is quantisation
(MSE 8e-3 at 2 bits, 4e-4 at 4 bits, 0 at 8 bits for these 8-bit source images).
Compiled resources (basis {cx, rz, sx, x}, opt. level 1): FRQI 8×8 8,339 gates / depth 4,878; NEQR 8×8 4-bit
16,690 / 12,431; FRQI 16×16 77,307 / 57,352; NEQR 16×16 8-bit 145,804 / 130,741. Logical counts understate NEQR cost
(multi-controlled X counted as one gate).

## 8. Honest interpretation
1. **Why V0 quantum results looked poor:** tiny samples (≈42 train / 18 test), a "VQC" with no quantum circuit,
   classical "observable" features, a broken shot kernel, and 4×4 inputs. Under a sound protocol the original FRQI/NEQR
   overlap kernels reach ~0.58–0.60 — about the same as a classical RBF-SVM on 8 PCA features.
2. **The bottleneck is the input representation, not the classifier.** Every pixel-based model (quantum or classical)
   stays at 0.5–0.65 and fails on rolled-in scale (F1 ≤ 0.24) and inclusion (≤ 0.31); CNN features reach 0.93–0.96.
3. **Quantum kernels match, but do not convincingly beat, classical kernels.** The single positive signal (8-qubit
   ZZ-full on pixel PCA, +3 points, significant on 2/3 seeds uncorrected) is not reproduced with CNN features and
   needs independent confirmation; it is not evidence of quantum advantage.
4. **The VQC learns but underperforms** kernel methods on the same inputs, and trains ~1,000× slower in simulation.
5. **Shot noise matters:** finite-shot kernels cost up to 7 points (ZZ-full, 100 shots) and up to 24 points (FRQI);
   a full 1,080×1,080 kernel at 1,000 shots would need ~5.8×10⁸ circuit executions on hardware.
6. **Encoding vs classification are different questions:** perfect statevector reconstruction says nothing about
   classification usefulness; NEQR's 8-bit exactness makes it the *worst* kernel.

## 9. Failed and skipped experiments
- Failed: 0 of 2,583 experiments; 0 of 16 reconstruction records.
- Superseded (kept, excluded from analysis): 18 directories from a runner-hash bug in the first MobileNetV3 run
  (no test evaluation happened), 1 run interrupted by session end (re-run).
- Not run (scope/resource decisions, documented): hardware execution; shot-based VQC training; small-CNN features as a
  hybrid source; extended hyperparameter grids for configurations selected at grid edges (not widened after test
  results existed); other datasets (out of approved scope).
