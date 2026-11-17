# Phase 6 — FRQI and NEQR under Protocol V2

Status: **PASS**

Original encoders (`src/frqi/encoder.py`, `src/neqr/encoder.py`) and decoders (`src/reconstruction/reconstructor.py`)
are used unchanged. Classification (E1/E1b/E2, `results/qml_v2/experiments`) and reconstruction
(`results/qml_v2/reconstructions`, record_type = reconstruction) are separate records and are never ranked together.

## A. Classification with encoding-state overlap kernels (`src/v2/frqi_neqr.py`)
K(A,B) = |⟨I_A|I_B⟩|² of the encoded images; closed forms verified equal to overlaps of the original circuits'
statevectors (1e-10) and to the V0 kernels (tests/test_v2_frqi_neqr.py, 9 tests). E1b = FRQI angle-scaled variant
(θ = b·I·π/2, b ∈ {2,4,8}; a kernel variant only — not an invertible encoding). SVC C ∈ {0.1,1,10,100} selected on
validation. Locked test, mean ± std over seeds:

| Resolution | FRQI (original) | FRQI angle-scaled (E1b) | NEQR 2-bit | NEQR 4-bit | NEQR 8-bit |
|---|---|---|---|---|---|
| 2×2 | 0.430 ± 0.016 (3 q) | — | 0.358 ± 0.007 (4 q) | 0.406 ± 0.018 (6 q) | 0.307 ± 0.004 (10 q) |
| 4×4 | 0.527 ± 0.014 (5 q) | 0.559 ± 0.009 (b=2) | 0.450 ± 0.008 (6 q) | 0.513 ± 0.014 (8 q) | 0.398 ± 0.017 (12 q) |
| 8×8 | 0.578 ± 0.011 (7 q) | 0.606 ± 0.012 (b=2) | 0.510 ± 0.008 (8 q) | 0.599 ± 0.011 (10 q) | 0.455 ± 0.011 (14 q) |
| 16×16 | 0.576 ± 0.023 (9 q) | 0.599 ± 0.006 (b=2) | 0.531 ± 0.003 (10 q) | 0.602 ± 0.004 (12 q) | 0.503 ± 0.013 (16 q) |

- NEQR overlap is an exact-match kernel: 4-bit quantisation is best; 8-bit makes almost every pixel pair mismatch
  (kernel near-diagonal) and accuracy drops.
- Gains saturate at 8×8 (16×16 ≈ 8×8). The best encoding kernels (~0.60) match PCA-8 + RBF-SVM (0.607 ± 0.011).
- Shots (8×8): FRQI is very shot-sensitive (statevector 0.578 → 0.463 @10⁴, 0.393 @10³, 0.335 @10² shots per entry);
  NEQR 4-bit is robust (0.599 → 0.601 @10⁴, 0.594 @10³, 0.562 @10²) because its overlaps are large, not tiny.

### Relabelled legacy methods (classical; no circuit executed)
| Model | Test acc |
|---|---|
| FRQI encoding statistics + LogReg (V0 "HQCC"), 4×4 / 8×8 | 0.473 ± 0.011 / 0.556 ± 0.014 |
| NEQR encoding statistics + LogReg (V0 "HQCC"), 4×4 / 8×8 | 0.400 ± 0.022 / 0.473 ± 0.027 |
| Fixed-feature softmax (V0 "VQC"), FRQI / NEQR 4×4 | 0.261 ± 0.026 / 0.244 ± 0.008 |
The V0 "VQC", run unchanged on the full protocol, is close to chance (0.167).

## B. Encoding / reconstruction study (`src/v2/encoding_study.py`)
30 fixed train-folder images (indices 12, 60, 108, 156, 204 of each class). Aer statevector simulation; shot modes =
Multinomial(shots, |ψ|²) on the simulated state (equivalent to ideal measure_all; equivalence vs Aer sampling tested).
Mean MSE vs the preprocessed image (NEQR quantisation error shown separately):

| Record | Qubits | Gates logical → compiled | Compiled depth / CX | Statevector MSE | 10² shots | 10³ | 10⁴ | 10⁵ | SSIM @10³ |
|---|---|---|---|---|---|---|---|---|---|
| FRQI 2×2 | 3 | 27 → 143 | 93 / 48 | 0 (exact) | 4.6e-3 | 4.9e-4 | 3.4e-5 | 4.3e-6 | 0.885* |
| FRQI 4×4 | 5 | 1,093 → 1,070 | 710 / 384 | 0 | 3.0e-2 | 1.8e-3 | 1.7e-4 | 1.5e-5 | 0.761* |
| FRQI 8×8 | 7 | 8,583 → 8,339 | 4,878 / 3,584 | 0 | 0.165 | 8.3e-3 | 7.0e-4 | 6.4e-5 | 0.501 |
| FRQI 16×16 | 9 | 72,713 → 77,307 | 57,352 / 26,624 | 0 | 0.265 | 6.5e-2 | 2.9e-3 | 2.7e-4 | 0.151 |
| NEQR 4×4, 4-bit | 8 | 99 → 1,679 | 1,385 / 577 | 3.9e-4 (= quantisation) | 6.9e-4 | 3.9e-4 | 3.9e-4 | 3.9e-4 | 0.925* |
| NEQR 8×8, 4-bit | 10 | 510 → 16,690 | 12,431 / 5,342 | 3.7e-4 (= quantisation) | 6.0e-2 | 3.7e-4 | 3.7e-4 | 3.7e-4 | 0.935 |
| NEQR 8×8, 8-bit | 14 | 639 → 25,005 | 21,925 / 8,533 | 0 | 6.0e-2 | 0 | 0 | 0 | 1.000 |
| NEQR 16×16, 8-bit | 16 | 3,059 → 145,804 | 130,741 / 49,012 | 0 | 0.210 | 6.3e-3 | 0 | 0 | 0.629 |
All 16 records (FRQI ×4 resolutions, NEQR ×4 resolutions ×3 bit depths) are in `aggregates/analysis.json` and the
dashboard. *SSIM for images < 7 px is a single global window (limited meaning; labelled in the records).

- Statevector reconstruction is exact for both encodings (FRQI MSE ≤ 3e-27; NEQR = its own quantisation error) — a
  consistency check of encoder + decoder, not evidence of practical quality.
- FRQI needs many shots per pixel (MSE ∝ 1/shots); NEQR is exact at every position that is observed at least once
  (majority vote over a deterministic intensity), so its shot error comes only from never-sampled positions: 100 shots
  for 256 pixels leave most positions unobserved (MSE 0.21); 1,000 shots still miss ≈ 2% of them ((1−1/256)^1000)
  (MSE 6.3e-3); 10⁴ shots → exact.
- Compiled cost: NEQR's logical counts are small because one multi-controlled X counts as one gate; compiled to the
  common basis {cx, rz, sx, x}, NEQR 8×8 4-bit needs 2.0× FRQI 8×8's gates (16,690 vs 8,339) and 16×16 8-bit NEQR needs
  1.9× FRQI 16×16. The V0 dashboard's "NEQR ≈ 10× cheaper" comparison mixed logical and decomposed counts.
- Transpilation: basis {cx, rz, sx, x}, optimization_level 1, all-to-all connectivity, seed 0 — identical for every circuit.

## Historical preservation
`after-phase6`: 3,690 files, changed 0, missing 0, added 0.
