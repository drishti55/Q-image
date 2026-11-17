# Q-ImageLab — Protocol V4 paper pack

Everything for the research paper on the **new method (Protocol V4: patch-ensemble mixed-state FRQI / NEQR kernels)** and the
**full reconstruction study (all 1,800 images × 20 methods)**: figures, tables, methodology diagram and the paper text.
Every number is read from the saved result files, nothing is typed by hand. `VALIDATION.md` recomputes the key numbers from the
raw per-run predictions: **all checks pass**.

## Quick start
| You want to… | Use |
|---|---|
| Paste into Word / Google Docs | `content/PAPER_V4.docx` (full paper text with every figure and table already inside) or the PNGs |
| Read / copy the text | `content/PAPER_V4.md` |
| Paste a graph | `figures/FigXX_*.png` (300 dpi) |
| Paste a table as an image | `tables/TabXX_*.png` |
| Edit a table | `tables/TabXX_*.csv` (Excel) or `.md` |
| LaTeX / Overleaf | `figures/*.pdf` + `tables/*.tex` (booktabs); `latex/v4_figures_tables.tex` inserts all of them |

## Headline numbers (locked test, 360 images, mean ± s.d. over 3 seeds)
| Model | Test accuracy % |
|---|---|
| FRQI patch-ensemble kernel (8×8 patches, 7 qubits) | **87.8 ± 1.5** |
| NEQR patch-ensemble kernel (4×4 patches, 4-bit, 8 qubits) | **82.7 ± 10.1** |
| Classical RBF-SVM on the same patches | 83.6 ± 0.3 |
| Old whole-image FRQI / NEQR (V2) | 60.6 ± 1.2 / 60.2 ± 0.4 |
| Best classical (texture RBF-SVM, V3) | 95.6 ± 2.2 |

## Figures (`figures/`, each as .png 300 dpi + .pdf + .svg; plotted numbers in `figures/data/*.csv`)
| File | Shows | Paper |
|---|---|---|
| `Fig01_methodology_flowchart` | Methodology | Figure 1 |
| `Fig02_patch_encoding_illustration` | The method on a real NEU-DET training image (frozen FRQI settings: 64×64, 8×8 patches, stride 4) | Figure 2 |
| `Fig09_validation_sweep` | Validation-only hyper-parameter sweep: best validation macro-F1 for each image size / stride and normalisation | Figure 3 |
| `Fig03_main_results` | Locked-test accuracy of all V4 groups and reference models (mean ± s.d | Figure 4 |
| `Fig04_frqi_neqr_across_protocols` | FRQI and NEQR test accuracy across protocols V2, V3 and V4, with classical references. | Figure 5 |
| `Fig05_comparisons_forest` | The eight pre-declared paired comparisons: accuracy difference with 95 % bootstrap CI and Holm-corrected p-values. | Figure 6 |
| `Fig07_per_class_f1` | Per-class F1 on the locked test set (mean over seeds). | Figure 7 |
| `Fig06_confusion_matrices` | Row-normalised confusion matrices summed over seeds 0–2. | Figure 8 |
| `Fig08_seed_stability` | Test accuracy of each split seed. NEQR's seed-1 drop is caused by the rolled-in-scale class. | Figure 9 |
| `Fig10_circuit_resources` | Qubits, compiled gates and compiled depth of the encoder circuit for one patch. | Figure 10 |
| `Fig11_reconstruction_mse_vs_shots` | Reconstruction MSE versus measurement shots, mean over all 1,800 images. | Figure 11 |
| `Fig13_reconstruction_ssim_by_method` | Mean SSIM of every reconstruction method (exact and 1,000 shots). | Figure 12 |
| `Fig12_reconstruction_examples` | One locked-test-folder image per class reconstructed by representative methods (saved decoder outputs). | Figure 13 |
| `Fig14_per_image_difficulty` | (a) Fraction of all model-seed pairs that classify each test image correctly; (b) mean per class, all models vs V4 FRQI. | Figure 14 |
| `Fig15_cross_protocol_overview` | Key quantum (simulated) and classical models across protocols V2, V3 and V4. | Figure 15 |

## Tables (`tables/`, each as .csv + .md + .tex + .png)
| File | Title |
|---|---|
| `Tab01_dataset_splits` | NEU-DET dataset and splits (per class; identical counts for seeds 0, 1, 2) |
| `Tab02_search_space` | Hyper-parameter grid searched on the validation split (test never used) |
| `Tab03_selected_configs` | Configurations selected by validation macro-F1 |
| `Tab04_main_results` | Main results on the locked test set (360 images; mean ± s.d. over seeds 0–2) |
| `Tab05_statistical_comparisons` | The 8 pre-declared paired comparisons (Holm-corrected) |
| `Tab06_per_class_f1` | Per-class F1 % on the locked test set (mean over seeds 0–2) |
| `Tab07_circuit_resources` | Encoder circuit resources for ONE patch state (Qiskit, transpiled) |
| `Tab08_reconstruction` | Reconstruction of all 1,800 NEU-DET images by every method (mean MSE / SSIM) |
| `Tab09_cross_protocol` | Key models across protocols V2 → V3 → V4 (locked test accuracy %) |
| `Tab10_integrity_checks` | Automated integrity checks (17/17 pass) |

## Methodology in one paragraph
Grayscale NEU-DET images are resized (32–128 px) and cut into p×p patches. Every patch is encoded as an FRQI or NEQR state with the real
Qiskit encoder circuits; the image becomes the mixed state ρ = (1/P) Σ |ψk⟩⟨ψk|; two images are compared by K(A,B) = Tr(ρA ρB)
(measurable with a swap test) and an SVM is trained on K. 288 configurations × 3 seeds were searched on the validation split
only, selections were SHA-256 frozen, and each frozen model was tested once on the 360-image locked test set; 8 pre-declared paired
comparisons with Holm correction. A classical RBF-SVM on the identical patches is the matched control.

## Honest limits (keep these in the paper)
- Exact CPU simulation only: no quantum hardware, no noise model. **No quantum advantage is claimed**; a classical model on the same patches is statistically tied.
- The locked test set was used before by protocols V2 and V3 (disclosed in the paper's limitations).
- NEQR is unstable across seeds (one seed misses every rolled-in-scale image).
- References in the paper text are real publications; check them against your journal's style before submission.

## Regenerate (from the project root)
```bash
.venv/bin/python research_paper_visuals/source/make_v4_figures.py
.venv/bin/python research_paper_visuals/source/make_v4_paper_pack.py
.venv/bin/python research_paper_visuals/source/write_v4_paper.py
.venv/bin/python research_paper_visuals/source/validate_v4_pack.py
```
Sources (read-only): `results/qml_v4/aggregates/{v4_results,v4_verification,per_image_predictions}.json`, `results/qml_v4/aggregates/selection/`,
`results/qml_v4/experiments/*/predictions.csv`, `results/qml_v4/reconstruction_full/summary.json`, `results/qml_v2/aggregates/analysis.json`,
`results/qml_v3/aggregates/v3_results.json`.
