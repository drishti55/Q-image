# Phase 4 — PCA + Quantum Kernel Classifier (E3)

Status: **PASS**

## Implementation
- `src/v2/qsim.py`: batched NumPy statevector simulator in Qiskit conventions; every gate can be mirrored into
  a `QuantumCircuit`, so the simulated circuit is the one whose resources are reported (logical and
  transpiled to basis {cx, rz, sx, x}, optimization level 1, all-to-all, seed 0).
- `src/v2/qkernel.py`: feature maps `product_ry` (closed-form-computable control), `zz_linear`, `zz_full`
  (ZZFeatureMap convention, reps 1–2); fidelity kernel K = |⟨φ(x)|φ(y)⟩|²; bandwidth b scales the train-fitted
  [0, π] PCA angles (b = 1 = original map); `QuantumKernelSVC` = precomputed-kernel SVC; diagnostics: symmetry,
  diagonal, range, eigenvalues (PSD), off-diagonal mean/std/quantiles/histogram, same/different-class means,
  kernel-target alignment and centred kernel alignment (CKA); shot mode = Binomial(shots, K) per entry; Qiskit
  compute–uncompute circuit measured once + Aer execution for validation.
- Driver `scripts/v2/phase4_qkc.py` (runner-integrated, resumable). Grid per k ∈ {4,6,8}: product-RY (reps 1),
  ZZ-linear and ZZ-full (reps 1, 2) × bandwidth {0.05, 0.1, 0.2, 0.5, 1.0} × C {0.1, 1, 10, 100};
  each (k, feature map) is its own selection group. Control: RBF-SVM on the **identical** angle features
  (`E6-pca{k}-rbfsvm-angle`, 16-point grid).
- Legacy V0 shot-kernel bug fixed in `src/qml/frqi_qml.py` / `neqr_qml.py` (double measurement + reading the
  result dict instead of `["counts"]`; K(a,a) was 0, now 1).

## Validation (tests/test_v2_qsim.py, 16 tests, all pass)
Simulator vs `qiskit.quantum_info.Statevector` ≤ 1e-10; ZZ maps equal Qiskit's `zz_feature_map` (linear/full,
reps 1/2) up to global phase; product-RY equals Π cos²((x−y)/2); kernels symmetric, diagonal = 1, in [0,1], PSD;
Aer compute–uncompute: identical inputs → exactly 1.0 with one measurement layer; shot estimates within 5σ of
statevector; binomial sampler unbiased; legacy FRQI/NEQR shot kernels return 1.0 for identical images.
On real NEU features (train split, seed 0; `aggregates/aer_kernel_validation.json`, 4,000 shots, 25 pairs per
config): identical pairs = 1.0; max |z| 2.66 (k=4 ZZ-full), 1.68 (k=8 ZZ-full); MAE 0.0042 / 0.0013 → pass.

## Results — locked test (360 images), mean ± std over seeds 0,1,2
| k (qubits) | Model | Selected (validation) | Val F1 | Test acc | Test F1 | Kernel off-diag mean ± std | CKA | Compiled gates / depth / CX |
|---|---|---|---|---|---|---|---|---|
| 4 | QKC product-RY | b=1.0, C=100 | 0.624 | 0.513 ± 0.018 | 0.494 | 0.692 ± 0.221 | 0.239 | 16 / 4 / 0 |
| 4 | QKC ZZ-linear | reps 1, b=0.5, C=100 | 0.634 | 0.526 ± 0.025 | 0.498 | 0.213 ± 0.254 | 0.271 | 21 / 12 / 6 |
| 4 | QKC ZZ-full | reps 1, b=0.2, C=100 | 0.654 | 0.524 ± 0.014 | 0.501 | 0.408 ± 0.257 | 0.293 | 30 / 18 / 12 |
| 4 | RBF-SVM (same features) | C=100, γ=1 | 0.653 | 0.520 ± 0.006 | 0.497 | — | — | — |
| 6 | QKC product-RY | b=1.0, C=100 | 0.692 | 0.557 ± 0.016 | 0.538 | 0.638 ± 0.234 | 0.277 | 24 / 4 / 0 |
| 6 | QKC ZZ-linear | reps 2, b=0.5, C=1 | 0.706 | 0.557 ± 0.016 | 0.529 | 0.094 ± 0.151 | 0.250 | 66 / 27 / 20 |
| 6 | QKC ZZ-full | reps 2, b=0.2, C=10 | 0.722 | 0.555 ± 0.014 | 0.525 | 0.132 ± 0.160 | 0.259 | 126 / 51 / 60 |
| 6 | RBF-SVM (same features) | C=10, γ=1 | 0.717 | 0.569 ± 0.022 | 0.546 | — | — | — |
| 8 | QKC product-RY | b=1.0, C=100 | 0.720 | 0.581 ± 0.023 | 0.561 | 0.602 ± 0.246 | 0.305 | 32 / 4 / 0 |
| 8 | QKC ZZ-linear | reps 1, b=1.0, C=10 | 0.752 | 0.609 ± 0.022 | 0.593 | 0.054 ± 0.116 | 0.284 | 45 / 24 / 14 |
| 8 | QKC ZZ-full | reps 1, b=1.0, C=100 | 0.767 | 0.640 ± 0.035 | 0.622 | 0.040 ± 0.057 | 0.302 | 108 / 42 / 56 |
| 8 | RBF-SVM (same features) | C=10, γ=1 | 0.752 | 0.607 ± 0.011 | 0.584 | — | — | — |
Kernel statistics are of the training kernel (seed 0); gate counts are for one feature-map encoding U(x)
(the kernel circuit U(y)†U(x) doubles them). Significance of differences: see Phase 8 (paired McNemar tests).

### Finite shots (validation-selected ZZ configuration, re-evaluated with sampled kernels)
| k | statevector | 100 shots | 500 | 1,000 | 5,000 |
|---|---|---|---|---|---|
| 4 (ZZ-full) | 0.524 ± 0.014 | 0.446 ± 0.019 | 0.483 ± 0.017 | 0.484 ± 0.047 | 0.480 ± 0.025 |
| 6 (ZZ-full) | 0.555 ± 0.014 | 0.491 ± 0.018 | 0.548 ± 0.006 | 0.550 ± 0.021 | 0.548 ± 0.009 |
| 8 (ZZ-full) | 0.640 ± 0.035 | 0.571 ± 0.014 | 0.635 ± 0.038 | 0.634 ± 0.038 | 0.634 ± 0.032 |
Shot noise makes the kernel indefinite (training-kernel minimum eigenvalue −2.7 at 100 shots, −0.05 at 5,000 for
k=8). Shot counts are per kernel entry; a full 1,080×1,080 training kernel at 1,000 shots corresponds to ~5.8×10⁸
circuit executions on hardware (not run; simulated by validated binomial sampling).

## Interpretation
- Exponential concentration is visible: for ZZ maps the off-diagonal kernel mass falls to 0.04–0.13 at 6–8 qubits
  (near-diagonal Gram matrices), and validation selected small bandwidths (0.2–0.5) for k = 4–6, which counteract it.
- At k = 4 and 6, QKC and the classical RBF-SVM on identical features are indistinguishable within seed variance.
  At k = 8 ZZ-full is ~3 points above the control (0.640 vs 0.607), with seed std 0.035 — not established without
  the paired test. The product-RY control kernel (classically simulable) performs like the RBF-SVM.
- No quantum advantage is claimed: all results are noiseless classical simulations of ≤ 8 qubits, and the classical
  pixel ceiling under this protocol is itself low (≈0.65); frozen CNN features reach 0.96 (Phase 3).

## Limitations
- Several selections are at grid edges (product-RY b = 1.0 and C = 100; k = 8 ZZ b = 1.0; RBF γ = 1.0). Not
  extended after test evaluation, to keep the locked test uninformative for model choice.
- Shot study re-uses the statevector-selected hyperparameters (no re-selection under noise).

## Historical preservation
`after-phase4`: 3,690 files, changed 0, missing 0, added 0.
