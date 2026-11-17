# Algorithm Visualization Audit

Date: 2026-11-16. Scope: which algorithmic steps of Q-ImageLab can be demonstrated **from the actual implementations**
on the illustrative 3×3 grid [[70, 180, 0], [19, 20, 0], [0, 0, 0]] (four given pixels + five zero padding cells).

## 1. Frontend / navigation (as found)
React + Vite + Recharts, V2 shell `frontend/src/App.tsx`; V2 pages in `frontend/src/v2/pages/` (Overview, Present,
Models, Encoding, Circuits, Reconstruction, Classification, Experiments, ExperimentDetail, HistoricalHome); data via
`/api/v2/*` (`src/v2/api.py`, `src/v2/api_models.py`). Existing visualisations show final metrics, saved circuits
(rebuilt from checkpoints) and reconstructions — no step-by-step algorithm walkthroughs.

## 2. Implementations and what can be demonstrated exactly
| Algorithm | Source | Operations (verified in code) | Can the 3×3 grid go through the real implementation? |
|---|---|---|---|
| Preprocessing | `src/v2/dataset.py::preprocess_image` | `convert("L")` → BILINEAR resize to s×s → `/255` | Yes: the 3×3 uint8 image is resized with the same PIL call (64×64 for pixel models, 128×128 small CNN). |
| Pixel PCA | `src/v2/features.py::PCAFeaturizer` | flatten → per-pixel StandardScaler → PCA(k) → StandardScaler ("standard") or MinMax[0,π] ("angle"), fitted on train only | Yes: the fitted transform is deterministic (`providers._fitted_pca(seed, k, 64)` from the cached train arrays) and is applied to the resized demo image. It cannot be *fitted* on the demo image (4 informative pixels); only applied. |
| RBF-SVM | `models_classical.RBFSVM` (sklearn SVC, rbf, C, γ) | K(x,y)=exp(−γ‖x−y‖²); one-vs-one decision | Yes: checkpoint `E6-pca8-rbfsvm` seed 0 (C=100, γ=0.3) — support vectors, decision values, prediction. |
| Logistic regression | `models_classical.LogReg` | z = Wx + b; softmax | Yes: checkpoint `E6-pca8-logreg` seed 0 (W 6×8, b) — scores, probabilities. |
| Small CNN | `src/v2/cnn.py::SmallCNNNet` | 4×[Conv3×3 → BN → ReLU → MaxPool2], GAP, Dropout, Linear(128→6); input (x−0.5)/0.25 | Yes: checkpoint `E7-smallcnn` seed 0; real feature maps captured with forward hooks. |
| Frozen MobileNetV3 | `cnn.FrozenMobileNetV3Source` | RGB copy → resize 256 → centre-crop 224 → ImageNet norm → `features` → GAP (576-d) → StandardScaler → LogReg | Yes: cached IMAGENET1K_V1 weights + checkpoint `E7-mnv3-logreg` seed 0; real first-layer maps and the 576-d vector. |
| FRQI | `src/frqi/encoder.py::FRQIEncoder` | H on position qubits; per non-zero pixel: X on position bits = 0, MCRY(π·I) on the colour qubit, undo X. θᵢ = (π/2)·Iᵢ, Iᵢ = pixel/255. Requires **2ⁿ pixels**. | Only after embedding the 3×3 grid in a **4×4 grid with zero padding** (16 positions → 4 position qubits + 1 colour qubit). Zero pixels are skipped (no gates). Statevector, Aer-equivalent sampling and the original `FRQIReconstructor` are run. |
| NEQR | `src/neqr/encoder.py::NEQREncoder` + `frqi_neqr.neqr_quantize` | q = round(I/255·(2ᵇ−1)); H on position qubits; per pixel: X on position bits = 0, MCX onto every intensity qubit whose bit is 1, undo X; LSB on the first intensity qubit. Requires 2ⁿ pixels. | Same 4×4 embedding; b ∈ {2, 4, 8}; statevector + original `NEQRReconstructor`. |
| QKC | `src/v2/qkernel.py` | angle features a∈[0,π]ᵏ × bandwidth → product-RY / ZZ-linear / ZZ-full (Qiskit ZZFeatureMap convention) → K=\|⟨φ(x)\|φ(y)⟩\|² → SVC(precomputed) | Yes: PCA-4 angle features of the demo; checkpoints `E3-pca4-qkc-{product_ry, zz_linear, zz_full}` seed 0 (training points stored) → kernel row, prediction. 4 qubits keep circuits readable. |
| VQC | `src/v2/vqc.py` | RY(aᵢ) encoding; L × [RY(θ) RZ(θ) per qubit, CNOT ring]; ⟨Z₀..Z₃, Z₀Z₁, Z₂Z₃⟩ → wᶜ⟨Oᶜ⟩+bᶜ → softmax; parameter-shift (±π/2); Adam | Yes: checkpoint `E4-pca4-vqc` seed 0 (L=2) gives trained θ; the **initial** θ is reproducible exactly (first draw of `default_rng(seed)`, U(−0.1, 0.1)). |

## 3. What is NOT available (and how it is handled)
- **Per-step VQC parameter trajectories** were not recorded (only per-epoch loss/accuracy, 31 epochs). The playground shows
  the real loss curve, the real initial vs trained θ, and one *illustrative* parameter-shift + Adam step computed with the
  real code on the demo input (labelled illustrative).
- **PCA cannot be fitted on the demo image**; the real fitted transform (from 1,080 training images) is applied to it.
- **FRQI/NEQR cannot encode 9 pixels**; the 4×4 zero-padded embedding is shown explicitly, padding labelled.
- **Predictions on the demo image are genuine outputs of the trained pipelines on an artificial, out-of-distribution
  input**. They are not evaluation results and are never mixed into Protocol V2 metrics.
- Circuit views use the real encoder logic. FRQI/NEQR multi-controlled gates are shown as logical blocks (Qiskit decomposes
  them into many basic gates at construction); the block list is verified against the real circuit's statevector.

## 4. Plan
An offline script (`scripts/v2/build_playground.py`, clean process — Qiskit/torch are not run inside the web server)
computes every intermediate value with the real implementations and writes `results/qml_v2/playground/playground_3x3.json`
(marked `illustrative`), served read-only by `GET /api/v2/playground`. New pages: **Algorithm Playground** (8 step-by-step
walkthroughs on the shared 3×3 grid) and **Quantum vs Classical** (separate classical / quantum / hybrid views from
`/api/v2/models`, plus a side-by-side processing comparison of the demo grid).
