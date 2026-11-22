**Table 5. The 8 pre-declared paired comparisons (Holm-corrected)**

| Comparison (a vs b) | Acc. a % | Acc. b % | Δ pp | 95% CI pp | p (Holm) | Significant | McNemar a-only:b-only (seeds 0/1/2) |
|---|---|---|---|---|---|---|---|
| V4 FRQI vs V2 FRQI (E1b-frqi8-qkc-scaled) | 87.8 | 60.6 | +27.1 | [+21.7, +32.7] | <0.001 | yes | 114:25 / 118:21 / 123:16 |
| V4 FRQI vs V3 FRQI (V3-frqi8) | 87.8 | 57.5 | +30.3 | [+25.1, +35.4] | <0.001 | yes | 120:22 / 134:19 / 131:17 |
| V4 NEQR vs V2 NEQR (E2-neqr16-b4-qkc) | 82.7 | 60.2 | +22.5 | [+18.5, +26.7] | <0.001 | yes | 108:11 / 48:7 / 119:14 |
| V4 FRQI vs V4 NEQR | 87.8 | 82.7 | +5.1 | [+1.1, +9.0] | 0.045 | yes | 30:33 / 87:29 / 32:32 |
| V4 FRQI vs classical patch-moment RBF-SVM | 87.8 | 83.6 | +4.2 | [+0.5, +7.7] | 0.060 | no | 36:24 / 34:22 / 42:21 |
| V4 NEQR vs classical patch-moment RBF-SVM | 82.7 | 83.6 | -0.9 | [-4.9, +3.1] | 0.678 | no | 40:25 / 34:80 / 44:23 |
| V4 FRQI vs classical texture RBF-SVM (V3-tex12c-rbfsvm) | 87.8 | 95.6 | -7.8 | [-10.9, -4.7] | <0.001 | yes | 12:40 / 11:36 / 6:37 |
| V4 NEQR vs classical texture RBF-SVM (V3-tex12c-rbfsvm) | 82.7 | 95.6 | -12.9 | [-15.8, -10.0] | <0.001 | yes | 7:32 / 3:86 / 5:36 |

*Paired sign-flip permutation test (10,000) on per-image correctness averaged over seeds; bootstrap 95% CI; Holm correction over 8 tests.*
