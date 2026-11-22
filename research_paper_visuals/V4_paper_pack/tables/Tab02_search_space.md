**Table 2. Hyper-parameter grid searched on the validation split (test never used)**

| Group | Image size, patch p, stride s | Encoding option | Normalisation | SVM C | Configs | Runs (×3 seeds) |
|---|---|---|---|---|---|---|
| FRQI patches 4×4 | 32² p4 s2; 64² p4 s4 | angle ×1, 2, 4 | none, stretch | 1, 10, 100, 1000 | 48 | 144 |
| FRQI patches 8×8 | 32² p8 s4; 64² p8 s4; 128² p8 s8 | angle ×1, 2, 4 | none, stretch | 1, 10, 100, 1000 | 72 | 216 |
| NEQR patches 2×2 | 32² p2 s1; 64² p2 s2 | 4, 5, 6 bits | none, stretch | 1, 10, 100, 1000 | 48 | 144 |
| NEQR patches 4×4 | 32² p4 s2; 64² p4 s4; 128² p4 s4 | 3, 4 bits | none, stretch | 1, 10, 100, 1000 | 48 | 144 |
| Classical RBF-SVM, same patches | 64² p4 s4; 64² p8 s4; 128² p4 s4 | γ 0.3, 1, 3 | none, stretch | 1, 10, 100, 1000 | 72 | 216 |
| Total |  |  |  |  | 288 | 864 |

*Selection rule: maximum mean validation macro-F1 over seeds 0–2. Selections were SHA-256 frozen before the locked test was read.*
