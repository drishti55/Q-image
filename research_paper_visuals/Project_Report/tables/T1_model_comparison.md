| Model | Ver. | Type | Qubits | Input | Test acc. (%) | Test F1 (%) | Val F1 (%) | Seed spread (pp) | CX | Depth |
|---|---|---|---|---|---|---|---|---|---|---|
| FRQI patch ensemble (8x8) | V4 | Quantum | 7 | 64x64, 8x8 stride 4, stretch | 87.8 ± 1.5 | 87.5 ± 1.6 | 88.0 | 2.8 | 3584 | 4878 |
| FRQI patch ensemble (4x4) | V4 | Quantum | 5 | 64x64, 4x4 stride 4, stretch | 85.3 ± 1.7 | 85.0 ± 1.6 | 85.7 | 3.3 | 384 | 710 |
| RBF-SVM, patch moments (control) | V4 | Classical | - | 64x64, 8x8 stride 4, stretch | 83.6 ± 0.3 | 83.3 ± 0.3 | 83.8 | 0.6 | - | - |
| NEQR patch ensemble (4x4) | V4 | Quantum | 8 | 128x128, 4x4 stride 4, 4-bit | 82.7 ± 10.1 | 80.4 ± 13.5 | 89.2 | 18.3 | 694 | 1634 |
| NEQR patch ensemble (2x2) | V4 | Quantum | 6 | 64x64, 2x2 stride 2, 4-bit | 81.5 ± 10.6 | 79.2 ± 14.1 | 88.2 | 20.0 | 55 | 99 |
| RBF-SVM, texture features | V3 | Classical | - | LBP + GLCM, PCA-12 | 95.6 ± 2.2 | 95.5 ± 2.2 | 95.3 | - | - | - |
| NEQR, whole image (re-tuned) | V3 | Quantum | 12 | 16x16 image, one state | 60.2 ± 0.4 | 56.5 ± 0.4 | 72.7 | - | - | - |
| FRQI, whole image (re-tuned) | V3 | Quantum | 7 | 8x8 image, one state | 57.5 ± 2.1 | 55.3 ± 2.4 | 69.4 | - | - | - |
| FRQI, whole image | V2 | Quantum | 7 | 8x8 image, one state | 60.6 ± 1.2 | 58.3 ± 1.3 | 69.3 | - | - | - |
| NEQR, whole image (4-bit) | V2 | Quantum | 12 | 16x16 image, one state | 60.2 ± 0.4 | 56.5 ± 0.4 | 72.7 | - | - | - |
