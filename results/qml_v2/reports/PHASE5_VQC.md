# Phase 5 — Genuine Variational Quantum Classifier (E4)

Status: **PASS**

## Implementation (`src/v2/vqc.py`)
- Circuit on k qubits (k = PCA features 4/6/8): RY(a_i) angle encoding (a ∈ [0, π], train-fitted) → L ∈ {1,2,3}
  layers of trainable RY·RZ per qubit + CNOT ring; optional data re-uploading before every layer.
- Readout: exact expectation values of 6 observables (k ≥ 6: Z₀…Z₅; k = 4: Z₀…Z₃, Z₀Z₁, Z₂Z₃).
- Classical output layer: logit_c = w_c·⟨O_c⟩ + b_c (12 parameters, diagonal — cannot mix observables).
- Loss: mean cross-entropy. Optimisers: Adam with parameter-shift gradients (exact; shifted circuits share a cached
  prefix — same values, fewer gate applications), COBYLA (scipy, gradient-free), SPSA (own implementation, Spall gains).
- Early stopping / best-parameter selection on internal-validation loss only. Saved per run: per-epoch/iteration train
  and validation loss and accuracy, quantum-gradient norm per epoch, gradient variance at initialisation, parameter
  change ‖Δθ‖, circuit resources (logical + compiled), optimiser settings, training time, checkpoint.
- The V0 "VQC" (`src/qml/models.py::VariationalQuantumClassifier`) is unchanged and re-run in Phase 6 under the
  label "Fixed-feature softmax regression (formerly labelled 'VQC' in V0)", family = classical.

## Validation (tests/test_v2_vqc.py — 9 tests pass)
Statevector and all six readout expectations equal Qiskit `Statevector.expectation_value` to 1e-10 (k = 4, 6, 8;
ring/linear; with/without re-uploading); parameter-shift gradients equal central finite differences to 1e-7 for every
quantum and classical parameter; RZ gates of the final layer have exactly zero gradient (they cannot affect Z-basis
readout — reported, not hidden); all three optimisers move θ and reduce validation loss; changing θ changes predictions.

## Grid and selection
Per k: Adam / COBYLA / SPSA × L ∈ {1,2,3} (no re-upload) + Adam with re-upload L ∈ {2,3} = 11 configurations × 3 seeds.
Mean validation macro-F1:
| k | Adam L1/L2/L3 | Adam re-upload L2/L3 | COBYLA L1/L2/L3 | SPSA L1/L2/L3 |
|---|---|---|---|---|
| 4 | 0.324 / **0.509** / 0.430 | 0.362 / 0.432 | 0.319 / 0.449 / 0.398 | 0.149 / 0.269 / 0.339 |
| 6 | 0.447 / 0.451 / 0.499 | 0.450 / **0.540** | 0.440 / 0.391 / 0.425 | 0.172 / 0.167 / 0.219 |
| 8 | 0.442 / 0.469 / 0.498 | 0.467 / **0.558** | 0.429 / 0.477 / 0.445 | 0.171 / 0.102 / 0.184 |
Adam with parameter-shift gradients is best at every k; SPSA (600 iterations, mini-batch) did not converge to useful
models; deeper circuits and data re-uploading help at k = 6–8. Gradient variance at initialisation falls with width and
depth (k=4 L3: 5.2e-3 → k=8 L3: 9e-5), consistent with the onset of barren-plateau behaviour.

## Locked-test results (mean ± std, seeds 0,1,2; 360 images)
| k | Selected | Test acc | Test macro-F1 | Frozen-circuit ablation test acc | RBF-SVM same features | LogReg same PCA |
|---|---|---|---|---|---|---|
| 4 | Adam, L2 | 0.341 ± 0.011 | 0.328 | 0.164 ± 0.053 | 0.520 | 0.269 |
| 6 | Adam, L3, re-upload | 0.445 ± 0.027 | 0.419 | 0.283 ± 0.027 | 0.569 | 0.326 |
| 8 | Adam, L3, re-upload | 0.481 ± 0.019 | 0.450 | 0.286 ± 0.091 | 0.607 | 0.381 |
Paired McNemar tests (each seed, 360 images): trained VQC > frozen-circuit ablation in 9/9 seed comparisons
(p ≤ 8e-4) — the trained quantum parameters carry the model, not the 12-parameter head; VQC > logistic regression
on the same PCA features in 8/9 (p < 0.04); VQC < RBF-SVM in 9/9 (p ≤ 1.3e-4).
Per-class (k = 8): rolled-in scale F1 0.02 and inclusion 0.19 — the same classes pixel-PCA models miss (Phase 8).
Selected-model training time (Adam, k = 8): ~196 s (CPU, simulated); inference ~0.09 ms/image.

## Interpretation
The VQC is a genuine, trainable quantum model that learns (it beats its own frozen circuit and a linear model on
identical inputs), but on these features it is clearly worse than kernel methods. No quantum advantage.

## Incident and correction (traceable)
- The launching session ended at ~02:06 on 2026-11-14 while `E4-pca8-vqc__907f62311f__s2` was running. That directory
  was preserved unchanged in `superseded/2026-11-14_session_interrupt/` and the run repeated from scratch.
- On resume, the runner re-ran the final stage for the already-finished groups E4-pca4-vqc and E4-pca6-vqc (2 extra
  entries in `logs/test_access.jsonl`). Selection was recomputed from the same saved validation results, chose the same
  configurations, and the re-evaluation of the same checkpoints reproduced the first evaluation exactly (all six
  per-seed accuracies/F1 identical, see `logs/phase5_grid_ablation.log`). Runner fixed: a group whose selected
  configuration already has test metrics is never re-evaluated (regression test
  `test_resumed_group_does_not_reevaluate_test`).
- Wall-clock `duration_s` in metadata includes periods when the Mac was asleep (Nov 13 evening, verified in
  `pmset -g log`); `train_time_s` uses `perf_counter`, which excludes sleep.

## Historical preservation
`after-phase5`: 3,690 files, changed 0, missing 0, added 0.
