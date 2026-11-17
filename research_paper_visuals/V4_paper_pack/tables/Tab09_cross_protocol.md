**Table 9. Key models across protocols V2 → V3 → V4 (locked test accuracy %)**

| Protocol | Model | Type | Test accuracy % |
|---|---|---|---|
| V2 | FRQI, whole image (pixel kernel) | quantum | 60.6 ± 1.2 |
| V2 | NEQR, whole image (pixel kernel) | quantum | 60.2 ± 0.4 |
| V2 | ZZ-feature-map kernel on pixel PCA-8 | quantum | 64.0 ± 3.5 |
| V2 | Variational classifier (VQC) on pixel PCA-8 | quantum | 48.1 ± 1.9 |
| V2 | Classical RBF-SVM on pixel PCA-8 | classical | 64.8 ± 3.3 |
| V3 | ZZ-feature-map kernel on texture PCA-8 | quantum | 93.0 ± 3.0 |
| V3 | VQC on texture PCA-8 | quantum | 73.4 ± 3.8 |
| V3 | Classical RBF-SVM on texture PCA-12 | classical | 95.6 ± 2.2 |
| V4 | FRQI patch-ensemble kernel (8×8) | quantum | 87.8 ± 1.5 |
| V4 | NEQR patch-ensemble kernel (4×4) | quantum | 82.7 ± 10.1 |
| V4 | Classical RBF-SVM on the same patches | classical | 83.6 ± 0.3 |

*Same dataset, splits, seeds and locked test set in every protocol. Quantum = exact CPU simulation.*
