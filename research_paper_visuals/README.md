# Q-ImageLab — research paper visuals

Publication figures, tables and a methodology flowchart for *Q-ImageLab: Comparative Analysis of FRQI and NEQR
Quantum Image Processing for Steel Surface Defect Classification*.

Every value is read from the saved **Protocol V2** experiment records. Nothing is typed by hand.
`VALIDATION_REPORT.md` recomputes every number from the raw per-experiment files: **67 / 67 checks pass**.

## Contents
```
research_paper_visuals/
├── figures/            fig01–fig14 as .pdf (vector), .svg (vector, editable text), .png (300 dpi)
│   └── data/           the exact numbers plotted in every figure (.csv) + representative_models.json
├── tables/             tab01–tab09 as .csv and booktabs .tex;  tabS1_all_selected_models.csv (all 88 groups)
├── flowchart/          methodology_flowchart.{pdf,svg,png (600 dpi)} + methodology_flowchart_tikz.tex (editable)
├── latex/              visuals_insertion.tex, preamble_packages.tex, example_main.tex
├── source/             make_visuals.py, make_flowchart.py, validate.py (regenerate + re-validate everything)
├── VALIDATION_REPORT.md
└── README.md
```

## Source data (read-only)
| File | Used for |
|---|---|
| `results/qml_v2/aggregates/analysis.json` | selected models (mean ± s.d.), paired tests, shot sensitivity, kernel concentration, reconstruction summaries |
| `results/qml_v2/aggregates/selection/*.json` | hyperparameter grids (Table 2) |
| `results/qml_v2/manifests/dataset_manifest_neu-5625b937479b.json`, `manifests/splits/*.json` | dataset and split counts |
| `results/qml_v2/experiments/<id>/test_metrics.json`, `predictions.csv` | confusion matrices, per-class F1, validation recomputation, McNemar recomputation |
| `results/qml_v2/experiments/<id>/circuit_stats.json` | QKC / VQC circuit resources |
| `results/qml_v2/reconstructions/<id>/{metrics.json, circuit_stats.json, config.json, reconstructions.npz, images/}` | reconstruction metrics, encoder resources, example images |

Not used:
- **Historical Protocol V0** (`results/qml/`): its "HQCC" and "VQC" models were classical computations labelled as quantum, and its shot-based kernel had a bug.
- **Protocol V3** (`results/qml_v3/`): still running when these visuals were made.

## Figures
| File | Content |
|---|---|
| fig01_dataset_distribution | class × split counts |
| fig02_accuracy_comparison | accuracy of one representative per family |
| fig03_macro_f1_comparison | macro-F1, same models |
| fig04_precision_recall | macro precision vs recall |
| fig05_paradigm_comparison | classical vs quantum vs hybrid on matched features (k = 4/6/8) |
| fig06_frqi_vs_neqr_resolution | FRQI vs NEQR (2/4/8-bit) vs resolution; accuracy and macro-F1 |
| fig07_neqr_precision | NEQR bit depth vs accuracy per resolution |
| fig08_shot_analysis | accuracy vs measurement shots (FRQI, NEQR, ZZ-full QKC) |
| fig09_reconstruction_metrics | MSE / PSNR / SSIM vs shots |
| fig10_circuit_resources | qubits, compiled gates, compiled depth (FRQI vs NEQR) |
| fig11_confusion_matrices | 6 representative models |
| fig12_per_class_f1 | per-class F1 |
| fig13_reconstruction_examples | original vs FRQI / NEQR reconstructions (real arrays) |
| fig14_kernel_concentration | off-diagonal kernel mean and validation F1 vs bandwidth (supplementary) |

**Representative models** are chosen by **validation** macro-F1 inside each family, never by test accuracy:
| Family | Representative |
|---|---|
| Classical pixel PCA | Pixel PCA-8 + RBF-SVM |
| Classical CNN features | MobileNetV3 + RBF-SVM |
| FRQI | FRQI 8×8, angle ×2 |
| NEQR | NEQR 16×16, 4-bit |
| QKC | ZZ-full, 8 qubits |
| VQC | 8 qubits |
| Hybrid QKC | MobileNetV3-PCA8 + product-RY |
| Hybrid VQC | MobileNetV3-PCA6 + VQC |

## Tables
| Table | Content |
|---|---|
| tab01_dataset | dataset characteristics and protocol |
| tab02_experimental_configuration | experiments E1–E7, inputs, hyperparameter grids, shots |
| tab03_frqi_vs_neqr | per resolution × encoding: qubits, gates, depth, accuracy, macro-F1, exact-reconstruction PSNR/SSIM |
| tab04_classification_performance | validation F1, accuracy, macro-F1, precision, recall (mean ± s.d.) |
| tab05_circuit_resources | logical / compiled gates and depth, CX count |
| tab06_reconstruction_metrics | MSE / PSNR / SSIM at statevector, 10³ and 10⁴ shots |
| tab07_best_model_comparison | best per paradigm and per encoding (by validation) |
| tab08_paired_tests | matched comparisons at k = 8 with per-seed exact McNemar p-values |
| tab09_limitations | experimental limitations |
| tabS1_all_selected_models.csv | all 88 selected configurations (supplementary) |

## Not generated, and why
- **Real-hardware results:** none exist. All circuits were simulated without noise on a CPU.
- **PSNR for exact reconstructions:** undefined, because MSE = 0 (below 1e-20). Reported as ∞ ("exact") instead of a number.
- **Reconstructions of test images:** the reconstruction study used 30 training images (5 per class), so only those are shown.
- **Training-loss curves:** not requested. They exist only per epoch for the VQC and small CNN.

## Metrics that need care
- **Validation–test gap:** validation (train folder) scores exceed locked-test scores for all models, because of a folder distribution shift (Table 9).
- **Rolled-in scale:** the FRQI and NEQR kernel models score **0 % F1** on this class; it is predicted as inclusion (Figs. 11 and 12). This is a real result.
- **McNemar p-values** are per seed and uncorrected for multiple comparisons.
- **NEQR gate counts** depend on pixel values; they are means over 5 sample images (ranges in `figures/data/fig10_circuit_resources.csv`).
- **Fig. 14(b)** averages validation F1 over the C grid and seeds, so it is lower than the selected configuration's value.
- **Product-RY kernels** are classically computable (a control).

## Overleaf
1. Upload the whole `research_paper_visuals/` folder to the **root** of your Overleaf project (next to `main.tex`). Drag the ZIP onto the file panel; Overleaf unpacks it.
2. In your preamble add `\input{research_paper_visuals/latex/preamble_packages}`, or the packages it lists: `fontenc[T1]`, `graphicx`, `booktabs`, `array`, `amsmath`, `caption`.
3. Copy the figure / table blocks you need from `latex/visuals_insertion.tex` into your paper, or `\input{research_paper_visuals/latex/visuals_insertion}` to insert everything.
4. Reference with `\ref{fig:frqi-neqr}`, `\ref{tab:frqi-neqr}` and so on (labels are listed in `visuals_insertion.tex` and the table files).
5. Compile with **pdfLaTeX**. To test the bundle alone, copy `latex/example_main.tex` to the project root and compile it.

If the folder lives elsewhere, change `\visdir` (defined in `preamble_packages.tex` / `visuals_insertion.tex`).

**Note:** LaTeX is not installed on the machine that produced these files, so the `.tex` files were checked statically (ASCII-only, balanced braces, all paths exist, unique labels) but **not compiled**. The same applies to `flowchart/methodology_flowchart_tikz.tex`; the PDF / SVG / PNG flowchart was rendered and inspected.

## Regenerate
```bash
.venv/bin/python research_paper_visuals/source/make_visuals.py
.venv/bin/python research_paper_visuals/source/make_flowchart.py
.venv/bin/python research_paper_visuals/source/validate.py      # writes VALIDATION_REPORT.md
```

## Protocol V3 figures (added after V3 finished)
`figures_v3/` (PNG 300 dpi, PDF, SVG, data CSVs), made by `source/make_v3_figures.py` from `results/qml_v3/aggregates/v3_results.json`:
| File | Content |
|---|---|
| figV3_1_before_after | V2 → V3 test accuracy per model (V3 may use a different input representation) |
| figV3_2_quantum_vs_classical_matched | best quantum model vs classical RBF-SVM on identical features, Holm-corrected significance |
| figV3_3_vqc_controls | trained VQC vs encoding-only control vs random frozen circuit |
| figV3_4_representation_effect | pixels → texture features for classical and quantum models alike |
| figV3_5_headline_models | best model per category (chosen by validation) |

`PNG_for_report/` holds every PNG (V2 figures, V3 figures, flowchart) in one place for pasting into Word / Google Docs.

## Protocol V4 figures (FRQI / NEQR improvement)
`figures_v4/` (PNG 300 dpi, PDF, SVG, data CSVs), made by `source/make_v4_figures.py` from `results/qml_v4/aggregates/v4_results.json`:
| File | Content |
|---|---|
| figV4_1_frqi_neqr_protocols | FRQI and NEQR test accuracy in V2 → V3 → V4 (patch-ensemble mixed-state kernel), per-seed dots, classical reference lines |
| figV4_2_per_class_f1 | per-class F1: V4 FRQI, V4 NEQR, classical RBF-SVM on the same patches |
| figV4_3_reconstruction_all_images | FRQI / NEQR reconstruction error vs shots, mean over ALL 1,800 images |
| figV4_4_reconstruction_examples | one locked-test image per class: original, FRQI exact / 1k shots, NEQR 4-bit, V4 patches, PCA-8 |
