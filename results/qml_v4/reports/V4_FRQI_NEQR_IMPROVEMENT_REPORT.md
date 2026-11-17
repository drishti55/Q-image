# FRQI / NEQR Improvement Report — Protocol V4

Protocol V4 · 5 frozen groups · 864 validation runs (0 failed) ·
selections frozen 2026-11-17T05:06:51.858617 (SHA-256 `b1735fdcfb035a696b84deb8d54438fce0dbc0583b074e00b034a206f21ef8c5`) · 5 locked-test stages.
Source: `results/qml_v4/aggregates/v4_results.json` (`scripts/v4/analyze_v4.py`). Test = 360 locked images, mean ± s.d. over seeds 0–2.
All circuits simulated exactly on a CPU (no hardware, no noise).

## 1. Result

| Protocol | FRQI test accuracy % | NEQR test accuracy % |
|---|---|---|
| V2 (pixel-level kernel) | 60.6 ± 1.2 | 60.2 ± 0.4 |
| V3 (pixel-level kernel, wider search) | 57.5 ± 2.1 | 60.2 ± 0.4 |
| **V4 (patch-ensemble mixed-state kernel)** | **87.8 ± 1.5** | **82.7 ± 10.1** |

* **FRQI: 60.6 ± 1.2 → 87.8 ± 1.5 %**
  (+27.1 pp, p<sub>Holm</sub> <0.001).
* **NEQR: 60.2 ± 0.4 → 82.7 ± 10.1 %**
  (+22.5 pp, p<sub>Holm</sub> <0.001).
  Seeds: [87.5, 71.1, 89.4] %. Seed 1 is weak because NEQR misclassifies every *rolled-in scale* image on that split (Section 4).
* **FRQI now beats NEQR** (+5.1 pp, p<sub>Holm</sub> 0.045).
* **Against classical baselines:** FRQI vs a classical RBF-SVM on the *same patches* is
  +4.2 pp (p<sub>Holm</sub> 0.060,
  not significant). Both FRQI and NEQR remain clearly **below** the best classical texture model (RBF-SVM on LBP/GLCM texture features,
  95.6 ± 2.2 %).

## 2. What changed, and why it works

The V2/V3 FRQI and NEQR kernels compared two images **pixel by pixel at the same positions**: the overlap
⟨I_a|I_b⟩ sums cos(θ_i^a − θ_i^b) over the same pixel index i. NEU defects are textures. The same scratch shifted by a few pixels
gives an unrelated state, so the kernel measured position rather than texture.

V4 keeps FRQI and NEQR as the encodings but changes **what is encoded and how two images are compared**:

1. Cut the (resized) image into p×p patches with stride s. Encode each patch as an FRQI state (2·log₂p + 1 qubits) or an NEQR state
   (2·log₂p + q qubits) with the original encoder circuits.
2. Represent the image by the **mixed state** of a uniformly random patch: ρ_I = (1/P) Σ_k |ψ_k⟩⟨ψ_k|.
3. Kernel: **K(A, B) = Tr(ρ_A ρ_B) = mean over patch pairs of |⟨ψ_k^A|ψ_l^B⟩|²**. A swap test between one random patch state of
   each image estimates it directly (the swap test measures Tr(ρσ) for mixed inputs). An SVM is trained on K.

Because ρ is an average over positions, the kernel is translation-robust (`tests/test_v4_models.py` checks this). The unit tests also check
that it equals the mean of squared overlaps of the Qiskit encoder statevectors. Per-image contrast stretch (min–max within the image only)
was a searched option.

**Selected configurations (validation macro-F1, test not consulted):**

| Group | qubits per patch state | selected configuration | val F1 % | test acc. % | test macro-F1 % | per-seed test acc. % |
|---|---|---|---|---|---|---|
| `V4-frqi-p4` | 5 | 64×64, 4×4 patches, stride 4, angle ×4.0, contrast stretch, C=1000 | 85.7 | 85.3 ± 1.7 | 85.0 ± 1.6 | 86.9, 85.3, 83.6 |
| `V4-frqi-p8` | 7 | 64×64, 8×8 patches, stride 4, angle ×4.0, contrast stretch, C=1000 | 88.0 | 87.8 ± 1.5 | 87.5 ± 1.6 | 86.7, 87.2, 89.4 |
| `V4-neqr-p2` | 6 | 64×64, 2×2 patches, stride 2, 4-bit, no stretch, C=1000 | 88.2 | 81.5 ± 10.6 | 79.2 ± 14.1 | 85.6, 69.4, 89.4 |
| `V4-neqr-p4` | 8 | 128×128, 4×4 patches, stride 4, 4-bit, no stretch, C=1000 | 89.2 | 82.7 ± 10.1 | 80.4 ± 13.5 | 87.5, 71.1, 89.4 |
| `V4-patchmom-rbfsvm` | — (classical) | 64×64, 8×8 patches, stride 4, γ=1.0, contrast stretch, C=1000 | 83.8 | 83.6 ± 0.3 | 83.3 ± 0.3 | 83.3, 83.9, 83.6 |

The FRQI headline (`V4-frqi-p8`) and NEQR headline (`V4-neqr-p4`) are the groups with the higher validation score, as pre-declared.

## 3. Pre-declared comparisons (8, Holm-corrected)

| Comparison | acc. a % | acc. b % | Δ (95 % CI) pp | p<sub>Holm</sub> | significant |
|---|---|---|---|---|---|
| V4 FRQI vs V2 FRQI (E1b-frqi8-qkc-scaled) | 87.8 | 60.6 | +27.1 [+21.7, +32.7] | <0.001 | yes |
| V4 FRQI vs V3 FRQI (V3-frqi8) | 87.8 | 57.5 | +30.3 [+25.1, +35.4] | <0.001 | yes |
| V4 NEQR vs V2 NEQR (E2-neqr16-b4-qkc) | 82.7 | 60.2 | +22.5 [+18.5, +26.7] | <0.001 | yes |
| V4 FRQI vs V4 NEQR | 87.8 | 82.7 | +5.1 [+1.1, +9.0] | 0.045 | yes |
| V4 FRQI vs classical patch-moment RBF-SVM | 87.8 | 83.6 | +4.2 [+0.5, +7.7] | 0.060 | no |
| V4 NEQR vs classical patch-moment RBF-SVM | 82.7 | 83.6 | -0.9 [-4.9, +3.1] | 0.678 | no |
| V4 FRQI vs classical texture RBF-SVM (V3-tex12c-rbfsvm) | 87.8 | 95.6 | -7.8 [-10.9, -4.7] | <0.001 | yes |
| V4 NEQR vs classical texture RBF-SVM (V3-tex12c-rbfsvm) | 82.7 | 95.6 | -12.9 [-15.8, -10.0] | <0.001 | yes |

## 4. Per-class F1 (%, mean over seeds) and the NEQR seed-1 failure

| Model | crazing | inclusion | patches | pitted_surface | rolled-in_scale | scratches |
|---|---|---|---|---|---|---|
| `V4-frqi-p8` | 93.1 | 84.0 | 95.8 | 81.5 | 89.5 | 81.3 |
| `V4-neqr-p4` | 89.5 | 72.7 | 91.4 | 80.0 | 65.0 | 84.0 |
| `V4-patchmom-rbfsvm` | 83.5 | 67.8 | 92.9 | 66.7 | 93.0 | 95.9 |

Rolled-in scale correctly classified, summed over 3 seeds (180 images): FRQI 178, NEQR 118.
NEQR, selected **without** contrast stretch, loses this class on seed 1. The V2 pixel-level FRQI and NEQR kernels already scored 0 % F1 on it,
which suggests a brightness difference between the training and locked-test folders for this class. FRQI, selected **with** per-image
contrast stretch, is not affected. We did not re-tune NEQR after seeing this, because that would use the test set for model choice.

## 5. Honest limits

- **No quantum advantage.** Every kernel here has a closed form and was computed classically. On the same patches, a classical
  RBF-SVM is statistically indistinguishable from FRQI (and from NEQR). A classical texture model is still better (Section 3).
- **A real implementation would need many shots.** On hardware each kernel entry would be estimated by swap tests over random patch pairs.
  Shot noise was not simulated in V4.
- **Validation-only exploration before the grid.** Before the grid was fixed, a few patch geometries were tried on the *validation* split
  (seeds 0–2). Every geometry tried is in the grid except one too-slow NEQR setting (documented in `scripts/v4/run_v4.py`).
- **The locked test set is not fresh.** It was used by V2 and V3. V4 is a new method, frozen on validation and evaluated once, but
  it was proposed after seeing that earlier FRQI/NEQR results were weak.
- **NEQR is seed-sensitive** (s.d. 10.1 pp) because of the class failure above.

## 6. Verification (17/17 checks pass, `scripts/v4/verify_v4.py`)

| Check | Result |
|---|---|
| historical V0 results: 0 changed, 0 missing | PASS |
| V2 manifest/splits/caches unchanged (SHA-256, in qml_v2 and qml_v3) | PASS |
| V4 copies of manifest/splits/image caches identical to the V3/V2 originals | PASS |
| no Protocol V2 result file modified or added since V3 was finalised | PASS |
| no Protocol V3 result file modified or added since V3 was finalised | PASS |
| all 70 V3 selection files unchanged since the V3 freeze | PASS |
| V4 selection files unchanged since the V4 freeze | PASS |
| every V4 locked-test access after the freeze, one per frozen group | PASS |
| test predictions exist only for the frozen configurations | PASS |
| no selection file contains a test metric | PASS |
| 864 candidate runs, 0 failed | PASS |
| test accuracy recomputed from predictions.csv (360 locked images per run) | PASS |
| FRQI headline chosen by validation | PASS |
| NEQR headline chosen by validation | PASS |
| comparisons are exactly the 8 pre-declared ones | PASS |
| every V4 quantum group records a real FRQI/NEQR encoder circuit (Qiskit, transpiled) | PASS |
| classical control has no circuit and is labelled classical | PASS |

- Before the V4 grid was written, patch geometries were explored on the internal VALIDATION split only (no test data). That exploration used the V3 data loader and wrote six 32x32 train/val image-cache files into results/qml_v3/cache; they were deleted minutes later (they were additions, not modifications; all V3 records and hashes are unchanged).
- A first V4 launch failed after 1 minute (disk full: checkpoints stored training density matrices). Its partial candidate outputs (validation only, no test access) were deleted and the grid was re-run from scratch with small checkpoints; a reloaded checkpoint was verified to reproduce its validation predictions exactly.
- The locked test set has been used by Protocols V2 and V3 before; V4 is a new method frozen on validation and evaluated once, but readers should know the test set is not 'fresh' for the project as a whole.

## 7. Reproduce

```bash
cd scripts/v4 && ../../.venv/bin/python setup_v4.py && N=4 ./chain_v4.sh   # candidates → select → freeze → locked test (~5 min)
cd ../.. && .venv/bin/python scripts/v4/analyze_v4.py && .venv/bin/python scripts/v4/verify_v4.py && .venv/bin/python scripts/v4/write_report_v4.py
.venv/bin/python -m pytest -q tests/test_v4_models.py
```
