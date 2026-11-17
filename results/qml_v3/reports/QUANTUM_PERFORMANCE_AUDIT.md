# Quantum Performance Audit (input to Protocol V3)

Date: 2026-11-16. Read-only audit of the Protocol V2 code (`src/v2/*`) and of the saved V2 records
(`results/qml_v2/experiments/*/diagnostics.json`, `training_log.json`, `aggregates/selection/*.json`). Nothing in
`results/qml/`, `results/models/` or `results/qml_v2/` was modified.

## 0. Baseline verification
Every baseline in the brief was checked against `results/qml_v2/aggregates/analysis.json` (mean test accuracy, 3 seeds, 360 locked images):

| Model | Group | Brief | Saved record |
|---|---|---|---|
| 8-qubit ZZ-full QKC | E3-pca8-qkc-zz_full | 64.0% | 0.6398 |
| 8-qubit ZZ-linear QKC | E3-pca8-qkc-zz_linear | 60.9% | 0.6093 |
| 8-qubit product-RY QKC | E3-pca8-qkc-product_ry | 58.1% | 0.5806 |
| FRQI angle-scaled 8×8 | E1b-frqi8-qkc-scaled | 60.6% | 0.6065 |
| NEQR 4-bit 16×16 | E2-neqr16-b4-qkc | 60.2% | 0.6019 |
| Genuine 8-qubit VQC | E4-pca8-vqc | 48.1% | 0.4806 |
| CNN + product-RY QKC | E5-mnv3pca8-qkc-product_ry | 93.2% | 0.9324 |
| CNN + ZZ-full QKC | E5-mnv3pca8-qkc-zz_full | 92.7% | 0.9269 |
| CNN + ZZ-linear QKC | E5-mnv3pca8-qkc-zz_linear | 91.9% | 0.9185 |
| CNN + VQC | E5-mnv3pca8-vqc | 81.3% | 0.8130 |

All match.

## 1. What was inspected
| Component | Where | Finding |
|---|---|---|
| FRQI state preparation | `src/frqi/encoder.py`, closed form in `src/v2/frqi_neqr.py` | Correct: θᵢ = (π/2)·Iᵢ, H on position qubits, MCRY(2θ) per non-zero pixel. Closed-form kernel verified against encoder statevectors (existing tests). |
| NEQR state preparation | `src/neqr/encoder.py`, `neqr_quantize` | Correct: q = round(I·(2ᵇ−1)), MCX onto set bits. |
| Product-RY / ZZ-linear / ZZ-full | `src/v2/qkernel.py::encode` | Correct Qiskit ZZFeatureMap convention; product-RY kernel = Π cos²((xᵢ−yᵢ)/2), which is classically computable. |
| Kernel construction | `fidelity_kernel` = abs(S S†)² | Exact statevector fidelities. Symmetric (max error 0), unit diagonal, PSD within 1e-13 for every saved kernel. |
| Kernel normalisation | none needed for fidelity (diag = 1) | — |
| VQC ansatz | `src/v2/vqc.py` | RY(aᵢ) encoding; L × [RY RZ per qubit, CNOT ring], optional re-upload; readout ⟨Z₀..Z₅⟩ (n ≥ 6). |
| Parameter-shift | `param_shift_jacobian` | Exact ±π/2 rule with prefix-state reuse (verified by existing finite-difference test). |
| Optimisers | Adam / COBYLA / SPSA | See §2.6. |
| Shots | `sample_shot_kernel` (Binomial per entry) | Correct ideal-measurement model, validated against Aer. |
| Search spaces | `scripts/v2/phase4_qkc.py`, `phase5_vqc.py`, `phase6_frqi_neqr.py`, `phase7_hybrid.py` | See §2.1. |

No implementation bug was found in the quantum code. The bottlenecks are protocol and design choices.

## 2. Bottlenecks found (with evidence)

### 2.1 Truncated hyperparameter grids
QKC grid: bandwidth ∈ {0.05, 0.1, 0.2, 0.5, 1.0}, C ∈ {0.1, 1, 10, 100}. **Every 8-qubit pixel QKC selected bandwidth = 1.0 and C = 100 or 10, so the optimum lies on or beyond the edge of the grid** (ZZ-full 8q: val F1 rises monotonically 0.705 → 0.767 as bandwidth goes 0.05 → 1.0). FRQI also selected C = 100, the grid maximum (val F1 0.644 at C = 100 vs 0.564 at C = 10). The 8-qubit VQC selected the deepest configuration in its grid (L = 3 with re-upload).

### 2.2 The angle feature view loses information
QKC inputs are MinMax-scaled to [0, π] on training data. PCA scores are heavy-tailed, so a few training outliers set the range and squeeze the bulk of the data. Evidence: the classical RBF-SVM on the same PCA-8 pixels scores **64.8%** with standardised features but **60.7%** with the angle view (E6-pca8-rbfsvm vs E6-pca8-rbfsvm-angle). The QKC only ever saw the angle view.

### 2.3 Kernel concentration
Off-diagonal fidelity mean of the training kernel (seed 0):
- ZZ-full 8q, bandwidth 1.0: 0.040 (variance 0.003). reps = 2 is worse (0.01; val F1 0.656).
- NEQR 16×16, 4-bit: 0.021. NEQR 16×16, 8-bit: **0.0001**, i.e. close to the identity kernel. This explains why 8-bit NEQR is worse than 4-bit: the NEQR fidelity = (fraction of positions with identical quantised intensity)², and exact matches become rare at 256 levels.
- Squaring the overlap (fidelity) compresses small overlaps further. The un-squared overlap Re⟨ψ_A|ψ_B⟩ is also quantum-measurable (Hadamard test) and is a PSD kernel for FRQI (real states) and NEQR (basis states).

Centred kernel alignment (CKA) with the labels is ~0.30 for every pixel-feature quantum kernel and 0.75 for the CNN-feature ZZ-full kernel. **The representation, not the feature map, limits pixel-based QKC.** Note: uncentred kernel-target alignment is negative for all kernels because 5/6 of pairs are cross-class; it is reported but CKA is the informative measure.

### 2.4 Feature representation
Pixel PCA from 64×64 keeps global brightness and illumination patterns, while NEU-DET classes differ by texture. Every model on these features (classical or quantum) sits at 54–65% test accuracy. Non-learned texture descriptors (local binary patterns, grey-level co-occurrence statistics) are the standard representation for this dataset and were never tried.

### 2.5 Validation-to-test shift
Validation macro-F1 ≈ 0.77 but test accuracy ≈ 0.64 for both the best QKC and its classical control. The locked test set comes from a different folder than the train/val splits, so a large part of the error is distribution shift. Illumination-robust representations (per-image intensity normalisation, texture statistics) are the principled response. Test-set statistics were **not** inspected to decide this.

### 2.6 VQC training budget and readout
- Every selected VQC hit the **40-epoch cap while still improving** (8q pixels: epoch 39, train acc 0.65, val loss still falling; CNN-feature VQC: stopped at 40). Under-trained.
- Readout: one ⟨Zᵢ⟩ per class with a diagonal head (6 scales + 6 biases). With 8 qubits, qubits 6–7 are never measured.
- Initial gradient variance is about 1e-4 per layer at 8 qubits (small-angle initialisation), so there is **no barren plateau** at this size.
- SPSA failed (val F1 0.10–0.18, chance level). With the fixed gain a = 0.2 the parameters barely move in 600 iterations; SPSA was not calibrated.
- COBYLA was competitive at L = 2 (0.477).

### 2.7 Not bottlenecks
- Kernel numerical stability: no indefiniteness, symmetry error 0.
- Qubit count alone: more qubits concentrate the fidelity kernel (§2.3). Increasing qubits is only useful together with a matching bandwidth.
- Circuit depth: reps = 2 hurt every ZZ map at 8 qubits.

## 3. V3 experiment plan derived from the audit
All in `results/qml_v3/`, using the V2 manifests and splits copied unchanged (hash-verified), seeds 0/1/2, selection on mean validation macro-F1. **All selections are frozen in one manifest before any locked-test evaluation**, then every frozen configuration is tested exactly once.

| Bottleneck | V3 change | Matched classical control |
|---|---|---|
| 2.1 truncated grids | bandwidth up to 3.0, C up to 1000 | RBF-SVM with an extended γ/C grid |
| 2.2 angle view | new "cdf" view: angle = π·Φ(z), z = train-standardised feature (smooth, outlier-robust, no clipping) | same features |
| 2.3 concentration | projected quantum kernel (PQK, Huang et al. 2021) on single-qubit reduced states; overlap (Hadamard-test) kernel for FRQI/NEQR | — |
| 2.4 representation | texture features (LBP + GLCM, non-learned) → PCA → quantum models | RBF-SVM / LogReg on identical features |
| 2.5 shift | per-image intensity normalisation before FRQI/NEQR and pixel PCA | same |
| 2.6 VQC | up to 120 epochs with patience, deeper re-uploading circuits, all-qubit readout option, calibrated SPSA; frozen-circuit ablation kept | LogReg on the same features; frozen circuit |
| Hybrid | MobileNetV3 → PCA 8/12 with the cdf view; QKC, PQK and VQC vs RBF/LogReg on the identical features | yes |

Statistics: mean ± sd over seeds; bootstrap CIs; paired sign-flip permutation test on per-image correctness (averaged over seeds) and per-seed exact McNemar tests; Holm correction over the pre-declared family of quantum-vs-matched-control and V3-vs-V2 comparisons.
