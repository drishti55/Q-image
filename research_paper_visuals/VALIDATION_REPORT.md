# Validation report

Checks: 67 · passed: 67 · failed: 0

Every value was recomputed from the raw per-experiment records in results/qml_v2 (test_metrics.json, predictions.csv, circuit_stats.json, reconstructions/*/metrics.json, manifest and split files) and compared with the figure data, the tables and analysis.json.

| Check | Result | Detail |
|---|---|---|
| analysis.json metrics equal per-experiment test_metrics.json (88 groups x 4 metrics) | PASS | [] |
| every selected experiment: 360 locked-test predictions from validation/ folder | PASS | 0 bad |
| manifest: 1,800 images, 240 trainval + 60 locked test per class | PASS |  |
| fig01 counts match split seed 0 | PASS |  |
| fig01 counts match split seed 1 | PASS |  |
| fig01 counts match split seed 2 | PASS |  |
| representative by validation: Classical: pixel PCA -> E6-pca8-rbfsvm | PASS | E6-pca8-rbfsvm |
| representative by validation: Classical: CNN features -> E7-mnv3-rbfsvm | PASS | E7-mnv3-rbfsvm |
| representative by validation: Quantum: FRQI kernel -> E1b-frqi8-qkc-scaled | PASS | E1b-frqi8-qkc-scaled |
| representative by validation: Quantum: NEQR kernel -> E2-neqr16-b4-qkc | PASS | E2-neqr16-b4-qkc |
| representative by validation: Quantum: QKC (PCA) -> E3-pca8-qkc-zz_full | PASS | E3-pca8-qkc-zz_full |
| representative by validation: Quantum: VQC -> E4-pca8-vqc | PASS | E4-pca8-vqc |
| representative by validation: Hybrid: CNN + QKC -> E5-mnv3pca8-qkc-product_ry | PASS | E5-mnv3pca8-qkc-product_ry |
| representative by validation: Hybrid: CNN + VQC -> E5-mnv3pca6-vqc | PASS | E5-mnv3pca6-vqc |
| fig02_accuracy_comparison: values equal raw test_metrics | PASS |  |
| fig03_macro_f1_comparison: values equal raw test_metrics | PASS |  |
| fig04: precision/recall equal raw | PASS |  |
| fig05_paradigm_comparison: accuracies equal raw (12 points) | PASS |  |
| fig06_frqi_vs_neqr_resolution: accuracies equal raw (19 points) | PASS |  |
| fig07_neqr_precision: accuracies equal raw (12 points) | PASS |  |
| fig08: shot accuracies equal raw shot-group experiments (23 points) | PASS | [] |
| fig11: confusion matrices = test_metrics = predictions.csv (1,080 predictions each) | PASS |  |
| tab08: McNemar p-values recomputed from predictions (34 comparisons x 3 seeds) | PASS | [] |
| reconstruction summaries: analysis.json == reconstructions/*/metrics.json (16 records) | PASS | [] |
| fig09: MSE/SSIM equal metrics.json | PASS | [] |
| fig13: FRQI statevector reconstruction equals the saved original (MSE < 1e-20) | PASS |  |
| fig10 / tab05: circuit resources equal circuit_stats.json | PASS | [] |
| qubit counts follow FRQI 2n+1 / NEQR 2n+q | PASS | [] |
| FRQI/NEQR classification qubit counts consistent | PASS | [] |
| tab04 accuracy Classical: pixel PCA | PASS | 64.8 ± 3.3 |
| tab04 accuracy Classical: CNN features | PASS | 96.4 ± 1.7 |
| tab04 accuracy Quantum: FRQI kernel | PASS | 60.6 ± 1.2 |
| tab04 accuracy Quantum: NEQR kernel | PASS | 60.2 ± 0.4 |
| tab04 accuracy Quantum: QKC (PCA) | PASS | 64.0 ± 3.5 |
| tab04 accuracy Quantum: VQC | PASS | 48.1 ± 1.9 |
| tab04 accuracy Hybrid: CNN + QKC | PASS | 93.2 ± 1.1 |
| tab04 accuracy Hybrid: CNN + VQC | PASS | 85.6 ± 1.3 |
| fig01_dataset_distribution: pdf/png/svg present | PASS |  |
| fig02_accuracy_comparison: pdf/png/svg present | PASS |  |
| fig03_macro_f1_comparison: pdf/png/svg present | PASS |  |
| fig04_precision_recall: pdf/png/svg present | PASS |  |
| fig05_paradigm_comparison: pdf/png/svg present | PASS |  |
| fig06_frqi_vs_neqr_resolution: pdf/png/svg present | PASS |  |
| fig07_neqr_precision: pdf/png/svg present | PASS |  |
| fig08_shot_analysis: pdf/png/svg present | PASS |  |
| fig09_reconstruction_metrics: pdf/png/svg present | PASS |  |
| fig10_circuit_resources: pdf/png/svg present | PASS |  |
| fig11_confusion_matrices: pdf/png/svg present | PASS |  |
| fig12_per_class_f1: pdf/png/svg present | PASS |  |
| fig13_reconstruction_examples: pdf/png/svg present | PASS |  |
| fig14_kernel_concentration: pdf/png/svg present | PASS |  |
| all PNG figures >= 300 dpi | PASS | [299.9994, 299.9994, 299.9994, 299.9994, 299.9994, 299.9994, 299.9994, 299.9994, 299.9994, 299.9994, 299.9994, 299.9994, 299.9994, 299.9994] |
| flowchart: svg/pdf/png/tikz present | PASS |  |
| flowchart PNG >= 300 dpi | PASS |  |
| visuals_insertion.tex: all 24 paths exist | PASS | [] |
| LaTeX labels unique | PASS | [] |
| tab06_reconstruction_metrics.tex: ASCII only and balanced braces | PASS |  |
| tab01_dataset.tex: ASCII only and balanced braces | PASS |  |
| tab08_paired_tests.tex: ASCII only and balanced braces | PASS |  |
| tab05_circuit_resources.tex: ASCII only and balanced braces | PASS |  |
| tab03_frqi_vs_neqr.tex: ASCII only and balanced braces | PASS |  |
| tab07_best_model_comparison.tex: ASCII only and balanced braces | PASS |  |
| tab02_experimental_configuration.tex: ASCII only and balanced braces | PASS |  |
| tab09_limitations.tex: ASCII only and balanced braces | PASS |  |
| tab04_classification_performance.tex: ASCII only and balanced braces | PASS |  |
| visuals_insertion.tex: ASCII only and balanced braces | PASS |  |
| example_main.tex: ASCII only and balanced braces | PASS |  |

LaTeX was not compiled locally (no TeX installation on this machine); syntax checks above are static (ASCII-only, balanced braces, existing paths, unique labels).
