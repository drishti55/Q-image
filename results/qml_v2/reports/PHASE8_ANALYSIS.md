# Phase 8 — Consolidated Experiment Analysis

Status: **PASS**

Source: `scripts/v2/phase8_analysis.py` → `results/qml_v2/aggregates/analysis.json`, built only from saved v2 records.
Totals: 2,583 experiments (2,583 completed, 0 failed), 88 selection groups each with locked-test metrics for 3 seeds,
34 paired comparisons, 16 reconstruction records. Every number in the analysis file lists its experiment ids.

## Statistical method
- Test metrics: mean ± sample std over seeds 0, 1, 2 (each seed = different blocked train/val split + model
  initialisation; the 360 test images are the same for all seeds). Per-seed 95% percentile-bootstrap CIs are stored
  in every `test_metrics.json` (half-width ≈ ±5 points at 60% accuracy, ±2–3 points at 95%).
- Paired comparisons: exact McNemar (binomial) test per seed on the 360 identical test images, reported per seed
  (not pooled); p-values are uncorrected for the 34×3 comparisons, so isolated p ≈ 0.01–0.05 should be read as weak.

## Categories (never ranked together)
1. Classical classification — pixels: PCA8+RBF-SVM 0.648 ± 0.033; frozen MobileNetV3 + SVM/LogReg 0.964;
   small CNN 0.930 ± 0.059.
2. Quantum-kernel classification (simulated) — best: PCA8 ZZ-full 0.640 ± 0.035; FRQI-overlap 8×8 angle-scaled
   0.606 ± 0.012; NEQR-overlap 8×8 4-bit 0.599 ± 0.011.
3. Variational quantum classification (simulated) — best: PCA8, Adam, L3, re-upload 0.481 ± 0.019.
4. Hybrid (frozen CNN + quantum head) — best: CNN-PCA8 + QKC product-RY 0.932 ± 0.011 (classical control 0.930).
5. Encoding/reconstruction — reported only as MSE/PSNR/SSIM/resources (Phase 6 B).
6. Relabelled legacy (classical) — V0 "HQCC" statistics + LogReg ≤ 0.556; V0 "VQC" softmax ≤ 0.261.

## Key paired results (seeds significant at 0.05 / 3)
| Comparison (identical features & test images) | Result |
|---|---|
| QKC vs RBF-SVM, PCA 4 (3 feature maps) | 0/3 for every map — indistinguishable |
| QKC vs RBF-SVM, PCA 6 | product-RY 1/3 and ZZ-linear 1/3, both favouring RBF-SVM; ZZ-full 0/3 |
| QKC ZZ-full vs RBF-SVM, PCA 8 | 2/3 favour QKC (0.664 vs 0.603, p=0.008; 0.656 vs 0.600, p=0.02); seed 1: 0.600 vs 0.619, p=0.31 |
| QKC product-RY vs RBF-SVM, PCA 8 | 2/3 favour RBF-SVM |
| ZZ-linear vs product-RY control | 0/3 (k=4,6), 1/3 (k=8) |
| VQC vs RBF-SVM (k=4,6,8) | 9/9 favour RBF-SVM (p ≤ 1.3e-4) |
| VQC vs frozen-circuit ablation | 9/9 favour trained VQC (p ≤ 8e-4) |
| VQC vs LogReg on same PCA | 8/9 favour VQC |
| CNN+QKC vs CNN+RBF-SVM (27 seed tests) | 2/27 significant, both favour RBF-SVM |
| CNN+VQC vs CNN+LogReg | k=4 0/3; k=6, k=8 3/3 favour LogReg |
| Frozen MobileNetV3+SVM vs small CNN | 2/3 favour MobileNetV3; seed 2 not significant (0.983 vs 0.997) |

Reading: the one positive quantum result (8-qubit ZZ-full kernel on pixel PCA, +3.3 points mean) is significant on
2 of 3 seeds before multiple-comparison correction and is not reproduced with CNN features. It is a candidate for
confirmation on a fresh protocol, not evidence of quantum advantage (noiseless simulation, 8 qubits, classical
alternatives such as better-tuned RBF kernels — several selected at grid edges — were not exhausted).

## Per-class findings (test F1, seed mean)
| Model | Crazing | Inclusion | Patches | Pitted | Rolled-in scale | Scratches |
|---|---|---|---|---|---|---|
| PCA8 RBF-SVM (angle) | 0.84 | 0.28 | 0.96 | 0.77 | **0.00** | 0.65 |
| PCA8 QKC ZZ-full | 0.86 | 0.31 | 0.97 | 0.76 | 0.24 | 0.59 |
| PCA8 VQC | 0.76 | 0.19 | 0.80 | 0.59 | 0.02 | 0.35 |
| NEQR-overlap 8×8 4-bit | 0.77 | 0.31 | 0.92 | 0.70 | 0.08 | 0.63 |
| Frozen MobileNetV3 + SVM | 1.00 | 0.88 | 1.00 | 0.98 | 1.00 | 0.92 |
| CNN-PCA8 + QKC ZZ-full | 0.99 | 0.75 | 1.00 | 0.98 | 0.98 | 0.84 |
Global pixel statistics cannot recognise rolled-in scale on the locked test folder (and barely inclusion), while CNN
features can — the main reason pixel-based quantum and classical models stay near 0.6.

## Other analyses in `analysis.json`
Kernel concentration vs bandwidth for every E3 configuration (off-diagonal mean/std, CKA, min eigenvalue, validation
F1); shot sensitivity (E1, E2, E3); VQC validation grid and initial-gradient variance; reconstruction summaries and
compiled resources; meta-selection of PCA dimension by validation (k = 8 selected for SVM, LogReg and VQC).

## Historical preservation
`after-phase8`: 3,690 files, changed 0, missing 0, added 0.
