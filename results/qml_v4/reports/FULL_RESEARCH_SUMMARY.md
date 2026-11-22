# Q-ImageLab — Full Research Summary (Protocols V2 → V3 → V4 + full reconstruction study)

Dataset: NEU-DET, 1,800 grayscale images, 6 defect classes (300 each). Locked test set = NEU validation folder (360 images,
60 per class), evaluated **once per frozen model**. Train-folder pool (1,440) split 1,080 train / 360 validation, seeds 0, 1, 2.
All quantum circuits were simulated exactly on a CPU (Qiskit / NumPy). **No quantum hardware was used and no noise model was applied.**
Every number below is read from saved result files (sources in brackets).

## 1. Classification — key models across protocols
| Model | Protocol | Test accuracy % (mean ± s.d., 3 seeds) |
|---|---|---|
| FRQI (whole image, pixel-level kernel) | V2 | 60.6 ± 1.2 |
| NEQR (whole image, pixel-level kernel) | V2 | 60.2 ± 0.4 |
| ZZ-full QKC on pixel PCA-8 | V2 | 64.0 ± 3.5 |
| Genuine VQC on pixel PCA-8 | V2 | 48.1 ± 1.9 |
| Hybrid: MobileNetV3 PCA-8 + product-RY QKC | V2 | 93.2 ± 1.1 |
| ZZ-full QKC on texture PCA-8 | V3 | 93.0 ± 3.0 |
| Product-RY QKC on texture PCA-12 (classically computable) | V3 | 95.3 ± 3.2 |
| Genuine VQC on texture PCA-8 | V3 | 73.4 ± 3.8 |
| Classical RBF-SVM on texture PCA-12 | V3 | 95.6 ± 2.2 |
| **FRQI patch-ensemble (mixed-state) kernel** | V4 | **87.8 ± 1.5** |
| **NEQR patch-ensemble (mixed-state) kernel** | V4 | **82.7 ± 10.1** |
| Classical RBF-SVM on the same patches | V4 | 83.6 ± 0.3 |

Sources: `results/qml_v2/aggregates/analysis.json`, `results/qml_v3/aggregates/v3_results.json`, `results/qml_v4/aggregates/v4_results.json`.

**Main findings**
1. **FRQI/NEQR were stuck near 60 % because the old kernel compared pixels at fixed positions.** Encoding *patches* and comparing
   images by the mixed-state overlap Tr(ρσ) (a swap test) gives FRQI 87.8 ± 1.5 % and NEQR 82.7 ± 10.1 %
   (both p<sub>Holm</sub> < 0.001 vs V2). FRQI beats NEQR (+5.1 pp, p<sub>Holm</sub> = 0.045).
2. **There is no quantum advantage.** On identical inputs, quantum and classical models are statistically tied (V3: 8 matched comparisons,
   none significantly in favour of quantum; V4: FRQI vs classical-on-the-same-patches +4.2 pp,
   p<sub>Holm</sub> = 0.060). The best overall model is classical (texture RBF-SVM, 95.6 ± 2.2 %).
3. **Representation matters more than the classifier.** Texture features lifted quantum and classical models by about 30 pp alike (V3).
4. **The VQC's trainable layers hurt.** An encoding-only control with no trainable gates beat the trained VQC by about 19 pp (V3).
5. **NEQR is unstable across splits.** One seed misclassified every rolled-in-scale image (V4). FRQI with per-image contrast stretch did not.

## 2. Every model on every test image
`results/qml_v4/aggregates/per_image_predictions.json`: the saved prediction of all **163 selected models × 3 seeds** on each of the
**360** locked-test images. 0 images are classified correctly by at least one seed of *every one* of the 163 models, and **0** images are never classified correctly by any model or seed.
The dashboard's *How it works* page shows this grid for any image.

## 3. Reconstruction — all 1,800 images × 20 methods
`results/qml_v4/reports/RECONSTRUCTION_FULL_REPORT.md`. Real Qiskit FRQI/NEQR circuits, statevector plus 100–100,000 shots, the project decoder.
- FRQI statevector decoding is exact for every image. With 1,000 shots, MSE is 8.66e-03 at 8×8 and 6.40e-02 at 16×16.
- NEQR is exact up to its quantisation: 4-bit floor 3.68e-04; 8-bit is lossless.
- V4 patches: 8×8 FRQI patches (7 qubits) with 1,000 shots per patch give a 64×64 MSE of 8.67e-03.
- Classical PCA-8 keeps little of the image (SSIM 0.590). This explains the weak pixel-PCA quantum classifiers.

## 4. Integrity
- Every protocol froze its selections on validation, then evaluated the test set once (V3: 29/29 checks; V4: 17/17 checks).
- V0 and V2 results are unchanged (SHA-256 verified). V3 records are unchanged.
- The test set has been used by V2, V3 and V4. V4 was proposed after V2/V3 showed weak FRQI/NEQR results; this is disclosed in its report.
- Live check: the dashboard recomputes the frozen V4 FRQI decision for all 360 test images and matches the saved predictions exactly (`tests/test_v4_api.py`).

## 5. Where to look
| What | Where |
|---|---|
| Animated walkthrough on a real image | dashboard → **How it works (live)** (`/how-it-works`) |
| V4 results and statistics | dashboard → **FRQI / NEQR Improvement (V4)**; `results/qml_v4/reports/V4_FRQI_NEQR_IMPROVEMENT_REPORT.md` |
| Reconstruction explorer (any image × any method) | dashboard → **Reconstruction (all 1,800)** |
| V3 study | `results/qml_v3/reports/` |
| Paper figures and tables | `research_paper_visuals/` (PNG for pasting in `PNG_for_report/`) |
