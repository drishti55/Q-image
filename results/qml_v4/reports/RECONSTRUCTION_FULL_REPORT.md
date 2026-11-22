# Full Reconstruction Study — all 1,800 images, every encoding

Created 2026-11-17T20:12:09 by `scripts/v4/reconstruct_all.py` (20 methods × 1,800 images; results in
`results/qml_v4/reconstruction_full/`). The V2 study used 30 training images; this one covers **every image of NEU-DET**
(1,440 train-folder + 360 locked-test-folder) for **every encoding**.

**How each quantum row was produced (no shortcuts):** the real Qiskit encoder circuit (`src/frqi/encoder.py`, `src/neqr/encoder.py`) →
Qiskit-Aer statevector → decoded with `src/reconstruction/reconstructor.py`; shot rows draw a multinomial sample of the exact
output distribution with that many shots and decode the counts. Patch rows (the Protocol V4 representation) encode and decode every
patch separately with the same circuits and stitch the patches back together; their shot counts are **per patch**.
Classical rows: PCA fitted on the seed-0 training split only, inverse-transformed. They show how much of the image the
PCA-input QKC / VQC classifiers actually receive. Reconstruction uses no labels, so including test-folder images cannot affect model selection.
Everything was simulated on a CPU (no quantum hardware, no noise model).

## 1. All methods (mean over 1,800 images; MSE / SSIM against the preprocessed image)

| Method | qubits | compiled gates | exact MSE | exact SSIM | images reproduced exactly | MSE 100 shots | MSE 1k | MSE 10k | MSE 100k | SSIM at most shots |
|---|---|---|---|---|---|---|---|---|---|---|
| `R-FRQI-2x2` | 3 | 143 | 0 (exact) | 1.000 | 1,800 / 1,800 | 4.68e-03 | 4.24e-04 | 3.90e-05 | 4.09e-06 | 0.999 |
| `R-FRQI-4x4` | 5 | 1,070 | 0 (exact) | 1.000 | 1,800 / 1,800 | 3.26e-02 | 1.73e-03 | 1.66e-04 | 1.64e-05 | 0.997 |
| `R-FRQI-8x8` | 7 | 8,339 | 0 (exact) | 1.000 | 1,800 / 1,800 | 1.57e-01 | 8.66e-03 | 6.76e-04 | 6.57e-05 | 0.988 |
| `R-FRQI-16x16` | 9 | 77,307 | 0 (exact) | 1.000 | 1,800 / 1,800 | 2.53e-01 | 6.40e-02 | 2.92e-03 | 2.64e-04 | 0.935 |
| `R-NEQR-2x2-b2` | 4 | 70 | 9.01e-03 | 0.554 | 0 / 1,800 | 9.01e-03 | 9.01e-03 | 9.01e-03 | 9.01e-03 | 0.554 |
| `R-NEQR-2x2-b4` | 6 | 132 | 3.68e-04 | 0.907 | 0 / 1,800 | 3.68e-04 | 3.68e-04 | 3.68e-04 | 3.68e-04 | 0.907 |
| `R-NEQR-2x2-b8` | 10 | 256 | 0 (exact) | 1.000 | 1,800 / 1,800 | 0 (exact) | 0 (exact) | 0 (exact) | 0 (exact) | 1.000 |
| `R-NEQR-4x4-b2` | 6 | 838 | 8.97e-03 | 0.542 | 0 / 1,800 | 9.41e-03 | 8.97e-03 | 8.97e-03 | 8.97e-03 | 0.542 |
| `R-NEQR-4x4-b4` | 8 | 1,031 | 3.68e-04 | 0.934 | 0 / 1,800 | 7.15e-04 | 3.68e-04 | 3.68e-04 | 3.68e-04 | 0.934 |
| `R-NEQR-4x4-b8` | 12 | 1,549 | 0 (exact) | 1.000 | 1,800 / 1,800 | 4.67e-04 | 0 (exact) | 0 (exact) | 0 (exact) | 1.000 |
| `R-NEQR-8x8-b2` | 8 | 8,928 | 8.94e-03 | 0.549 | 0 / 1,800 | 6.76e-02 | 8.94e-03 | 8.94e-03 | 8.94e-03 | 0.549 |
| `R-NEQR-8x8-b4` | 10 | 14,531 | 3.69e-04 | 0.941 | 0 / 1,800 | 6.09e-02 | 3.69e-04 | 3.69e-04 | 3.69e-04 | 0.941 |
| `R-NEQR-8x8-b8` | 14 | 19,749 | 0 (exact) | 1.000 | 1,800 / 1,800 | 6.07e-02 | 0 (exact) | 0 (exact) | 0 (exact) | 1.000 |
| `R-NEQR-16x16-b2` | 10 | 58,806 | 8.93e-03 | 0.540 | 0 / 1,800 | 2.02e-01 | 1.48e-02 | 8.93e-03 | 8.93e-03 | 0.540 |
| `R-NEQR-16x16-b4` | 12 | 131,375 | 3.68e-04 | 0.915 | 0 / 1,800 | 1.99e-01 | 6.12e-03 | 3.68e-04 | 3.68e-04 | 0.915 |
| `R-NEQR-16x16-b8` | 16 | 174,963 | 0 (exact) | 1.000 | 1,800 / 1,800 | 1.99e-01 | 5.75e-03 | 0 (exact) | 0 (exact) | 1.000 |
| `P-FRQI-64-p8` | 7 | 8,339 | 0 (exact) | 1.000 | 1,800 / 1,800 | 1.55e-01 | 8.67e-03 | 6.70e-04 | n/a | 0.791 |
| `P-NEQR-64-p4-b4` | 8 | 2,901 | 3.67e-04 | 0.888 | 0 / 1,800 | 8.38e-04 | 3.67e-04 | 3.67e-04 | n/a | 0.888 |
| `C-PCA8-64` (classical) | — | — | 4.66e-03 | 0.590 | — | — | — | — | — | — |
| `C-PCA12-64` (classical) | — | — | 3.85e-03 | 0.603 | — | — | — | — | — | — |

## 2. Findings

1. **FRQI statevector decoding is exact for every image** — all 1,800 images at every resolution
   (R-FRQI-2x2: 1,800, R-FRQI-4x4: 1,800, R-FRQI-8x8: 1,800, R-FRQI-16x16: 1,800). Any FRQI error comes from finite measurement shots.
2. **FRQI needs many shots, and more pixels need more.** At 1,000 shots, MSE is 4.24e-04 for 2×2 but
   6.40e-02 for 16×16, because the shots are spread over r² pixels.
3. **NEQR is exact up to quantisation.** Its statevector reconstruction equals the quantised image (table below). The only error is the
   intensity rounding to 2/4/8 bits. Once every pixel has been observed at least once, more shots do not help.
4. **The V4 patch representation is cheap to reconstruct.** Each 8×8 FRQI patch is a 7-qubit state. With 1,000 shots per patch,
   the 64×64 image has MSE 8.67e-03. The whole-image 16×16 FRQI needs 9 qubits and gets 6.40e-02 with
   1,000 shots for the whole image. *Note: the total shot budget differs (64 patches × 1,000).*
5. **PCA inputs throw away most of the image.** The PCA-8 reconstruction SSIM is 0.590, and PCA-12 is
   0.603. This is why the PCA-input QKC / VQC classifiers in V2 had so little texture to work with.

### NEQR: statevector vs quantisation (mean MSE)

| Record | statevector vs quantised image | quantisation alone vs original | statevector vs original |
|---|---|---|---|
| `R-NEQR-2x2-b2` | 0 (exact) | 9.01e-03 | 9.01e-03 |
| `R-NEQR-2x2-b4` | 0 (exact) | 3.68e-04 | 3.68e-04 |
| `R-NEQR-2x2-b8` | 0 (exact) | 0 (exact) | 0 (exact) |
| `R-NEQR-4x4-b2` | 0 (exact) | 8.97e-03 | 8.97e-03 |
| `R-NEQR-4x4-b4` | 0 (exact) | 3.68e-04 | 3.68e-04 |
| `R-NEQR-4x4-b8` | 0 (exact) | 0 (exact) | 0 (exact) |
| `R-NEQR-8x8-b2` | 0 (exact) | 8.94e-03 | 8.94e-03 |
| `R-NEQR-8x8-b4` | 0 (exact) | 3.69e-04 | 3.69e-04 |
| `R-NEQR-8x8-b8` | 0 (exact) | 0 (exact) | 0 (exact) |
| `R-NEQR-16x16-b2` | 0 (exact) | 8.93e-03 | 8.93e-03 |
| `R-NEQR-16x16-b4` | 0 (exact) | 3.68e-04 | 3.68e-04 |
| `R-NEQR-16x16-b8` | 0 (exact) | 0 (exact) | 0 (exact) |

## 3. Per class (SSIM)

| Method | crazing | inclusion | patches | pitted_surface | rolled-in_scale | scratches |
|---|---|---|---|---|---|---|
| `R-FRQI-16x16` (1,000 shots) | 0.109 | 0.045 | 0.475 | 0.130 | 0.058 | 0.117 |
| `R-NEQR-16x16-b4` (1,000 shots) | 0.608 | 0.529 | 0.877 | 0.550 | 0.551 | 0.662 |
| `P-FRQI-64-p8` (1,000 shots) | 0.438 | 0.155 | 0.545 | 0.288 | 0.267 | 0.246 |
| `C-PCA8-64` (PCA) | 0.364 | 0.843 | 0.412 | 0.660 | 0.576 | 0.685 |

## 4. Train folder vs locked-test folder (MSE at 1,000 shots)

| Record | train folder (1,440) | locked-test folder (360) |
|---|---|---|
| `R-FRQI-16x16` | 6.45e-02 | 6.19e-02 |
| `R-NEQR-16x16-b4` | 6.05e-03 | 6.42e-03 |
| `R-NEQR-16x16-b8` | 5.79e-03 | 5.60e-03 |

## 5. Reproduce

```bash
cd scripts/v4 && N=9 ./chain_recon.sh          # ~30–60 min on 10 cores; resumable
cd ../.. && .venv/bin/python scripts/v4/write_recon_report.py
```
Interactive: dashboard → **Reconstruction (all 1,800)**. Browse any image with any method and animate the shots.
