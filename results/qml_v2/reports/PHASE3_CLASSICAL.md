# Phase 3 — Classical Baselines and CNN Models

Status: **PASS** (with documented limitations below)

## Dependencies
| Package | Version | Note |
|---|---|---|
| torch | 2.15.0 | CPU execution verified (`torch.ones(2).sum()`; 4 threads used for training) |
| torchvision | 0.29.2 | |
| (pulled in) sympy 1.14.0, mpmath 1.3.0, filelock 4.2.10, fsspec 2026.9.0; setuptools changed to 84.2.1 | | numpy 2.4.6 / scipy / qiskit unchanged |

MobileNetV3: `MobileNet_V3_Small_Weights.IMAGENET1K_V1`, file `mobilenet_v3_small-047dcff4.pth`,
SHA-256 `047dcff4addef86ea5bc2eff13c9614dc11f47ab1160d0a71a25e7db994f4e1f`, 2,542,856 parameters.
First download failed: `SSL: CERTIFICATE_VERIFY_FAILED` (python.org macOS Python has no CA store linked).
Resolved with `SSL_CERT_FILE=<certifi bundle>` (verification kept on; torchvision hash check passed).
The download happened during setup; the experiments then loaded the weights **from cache**
(`pretrained_loaded: true, loaded_from_cache: true` recorded in each experiment's diagnostics).

## Results (locked test = 360 images; mean ± sample std over seeds 0,1,2)
| Group | Candidates | Selected (by validation) | Val macro-F1 | Test accuracy | Test macro-F1 |
|---|---|---|---|---|---|
| E6 PCA4 + RBF-SVM | 16 | C=10, γ=1.0 | 0.660 ± 0.039 | 0.554 ± 0.015 | 0.523 ± 0.026 |
| E6 PCA6 + RBF-SVM | 16 | C=1, γ=0.3 | 0.730 ± 0.060 | 0.570 ± 0.011 | 0.547 ± 0.010 |
| E6 PCA8 + RBF-SVM | 16 | C=100, γ=0.3 | 0.764 ± 0.039 | 0.648 ± 0.033 | 0.633 ± 0.055 |
| E6 PCA4 + LogReg | 6 | C=1 | 0.331 ± 0.031 | 0.269 ± 0.030 | 0.226 ± 0.010 |
| E6 PCA6 + LogReg | 6 | C=1 | 0.430 ± 0.043 | 0.326 ± 0.021 | 0.302 ± 0.011 |
| E6 PCA8 + LogReg | 6 | C=10 | 0.461 ± 0.047 | 0.381 ± 0.014 | 0.361 ± 0.011 |
| E7 frozen MobileNetV3 + LogReg | 6 | C=10 | 0.974 ± 0.016 | 0.964 ± 0.011 | 0.963 ± 0.012 |
| E7 frozen MobileNetV3 + RBF-SVM | 12 | C=10, γ=0.0005 | 0.977 ± 0.017 | 0.964 ± 0.017 | 0.963 ± 0.018 |
| E7 small CNN (from scratch) | 2 | lr=1e-3 | 0.943 ± 0.047 | 0.930 ± 0.059 | 0.927 ± 0.062 |

PCA explained variance (train-fitted, 64×64 pixels): k=4 0.836, k=6 0.870, k=8 0.888.
Small CNN per seed: test accuracy 0.886 / 0.906 / 0.997 (95% bootstrap CIs [0.853, 0.917], [0.875, 0.933],
[0.992, 1.000]); best epochs 17 / 8 / 46 (early stopping on internal-validation loss, patience 10).
Every selected experiment's per-class metrics, confusion matrices (val + test), predictions, checkpoint
(`model/estimator.joblib`, reloadable — tested) and, for the CNN, loss/accuracy curves are saved.

## Interpretation (Phase 3 only)
- Pixel-PCA features carry limited class information under the locked protocol: PCA8+RBF-SVM reaches
  0.648 test accuracy, far below the 0.82 measured in the audit on the V0-style random in-folder split —
  consistent with the leakage/distribution-shift finding.
- Linear models on 4–8 PCA components are weak (0.27–0.38): the classes are not linearly separable in
  these few components. Any quantum classifier on PCA features must be judged against PCA+RBF-SVM.
- Frozen ImageNet features are very strong (0.964). This sets the ceiling for the hybrid phase and means
  a hybrid model's performance will mostly reflect the CNN features.
- The small CNN's seed-to-seed spread (0.886–0.997) is larger than the difference between it and
  MobileNetV3; with 3 seeds no ranking between them is claimed.

## Limitations
- Validation > test for every pixel model (e.g. 0.764 vs 0.633 F1): the train folder (indices 1–240) and the
  locked test folder (241–300) differ in difficulty; blocked validation reduces but does not remove this gap.
- Selected values at grid edges (PCA4 SVM γ=1.0; PCA8 SVM C=100; MobileNet SVM γ=0.0005). Grids were NOT
  widened afterwards because test results for these groups had been computed; widening now could be
  influenced by test results.
- CNN training times are inflated by CPU contention (other jobs ran concurrently; e.g. 1,218 s vs 240 s for
  comparable runs); timings are reported but should not be over-interpreted.

## Locked-test integrity
`logs/test_access.jsonl` contains exactly 9 entries — one per selection group — all in the final stage.

## Historical preservation
`verify_historical.py --label phase3`: changed 0, missing 0, added 0.
