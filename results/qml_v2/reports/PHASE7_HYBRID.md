# Phase 7 — CNN + Quantum Hybrid Models (E5)

Status: **PASS**

## Design
Frozen MobileNetV3-small (IMAGENET1K_V1, weights loaded from cache, SHA-256 047dcff4…) → 576-d features →
train-fitted StandardScaler → PCA(k ∈ {4,6,8}) → train-fitted MinMax to [0, π]. Every model below receives exactly
these k numbers per image (same splits, seeds 0/1/2):
- Classical controls: RBF-SVM (16-point grid), logistic regression (6-point grid).
- CNN + QKC (hybrid): product-RY / ZZ-linear / ZZ-full (reps 1) × bandwidth {0.05,…,1.0} × C {0.1,1,10,100}.
- CNN + VQC (hybrid): Adam, L ∈ {1,2,3}, ring entangler.
Classical CNN feature extraction is labelled as such in every record; the quantum part is the simulated kernel or
circuit only. The small CNN was not used as a feature source (its features would have to be re-trained per seed;
documented limitation).

## Locked-test results (mean ± std, 3 seeds)
| k | CNN + LogReg | CNN + RBF-SVM | CNN + QKC product-RY | CNN + QKC ZZ-linear | CNN + QKC ZZ-full | CNN + VQC |
|---|---|---|---|---|---|---|
| 4 | 0.859 ± 0.011 | 0.884 ± 0.003 | 0.884 ± 0.003 | 0.890 ± 0.004 | 0.878 ± 0.007 | 0.866 ± 0.011 |
| 6 | 0.906 ± 0.007 | 0.911 ± 0.008 | 0.906 ± 0.013 | 0.910 ± 0.014 | 0.900 ± 0.017 | 0.856 ± 0.013 |
| 8 | 0.920 ± 0.013 | 0.930 ± 0.007 | 0.932 ± 0.011 | 0.919 ± 0.022 | 0.927 ± 0.014 | 0.813 ± 0.072 |
Reference: frozen MobileNetV3 on all 576 features + RBF-SVM / LogReg: 0.964 (Phase 3).

Paired McNemar tests (per seed): CNN+QKC vs CNN+RBF-SVM — 2 of 27 seed comparisons significant at 0.05, both in
favour of the classical SVM (k=6 ZZ-full seed 0; k=8 ZZ-linear seed 1); all others p ≥ 0.1. CNN+VQC vs CNN+LogReg —
k=4: 0/3 significant; k=6 and k=8: 3/3 significant in favour of logistic regression.

## Interpretation
- Hybrid performance comes from the CNN features: reducing 576 → 8 dimensions costs ~3 points (0.964 → 0.93), and
  replacing the classical classifier by a quantum kernel changes nothing measurable.
- The VQC head is worse than a linear model on the same 6–8 features; it does not improve the hybrid.
- No quantum contribution to performance is supported by these results.

## Historical preservation
`after-phase7`: 3,690 files, changed 0, missing 0, added 0.
