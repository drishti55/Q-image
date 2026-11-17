# Algorithm Visualization — Implementation Report

Date: 2026-11-16. See `ALGORITHM_VISUALIZATION_AUDIT.md` for what can and cannot be shown from the real implementations.

## 1. Data pipeline (no values computed in the browser)
| Piece | File | Role |
|---|---|---|
| Builder | `scripts/v2/build_playground.py` | Runs the illustrative grid [[70,180,0],[19,20,0],[0,0,0]] through the **real** code and seed-0 checkpoints: `preprocess_image` resize, train-fitted PCA, `E6-pca8-rbfsvm`, `E6-pca8-logreg`, `E7-smallcnn` (forward hooks), frozen MobileNetV3 + `E7-mnv3-logreg`, `FRQIEncoder`/`FRQIReconstructor`, `NEQREncoder`/`NEQRReconstructor` (2/4/8 bit), `qkernel` (product-RY / ZZ-linear / ZZ-full, `E3-pca4-qkc-*`), `vqc` (`E4-pca4-vqc`). Runs offline in a clean process (Qiskit/torch are never loaded inside the web server). |
| Output | `results/qml_v2/playground/playground_3x3.json` | ~650 KB, `"illustrative": true` + disclaimer. Self-checks at build time: the FRQI statevector matches the closed formula, NEQR decode equals the quantised grid, and the QKC checkpoint training features equal the re-derived PCA-4 angles. |
| API | `src/v2/api_models.py` → `GET /api/v2/playground` | Serves the file read-only. Returns 404 with a build hint if it is missing. |

Rebuild: `.venv/bin/python scripts/v2/build_playground.py` (MobileNetV3 weights come from the local torch cache).

## 2. Frontend
| File | Content |
|---|---|
| `frontend/src/v2/playground/widgets.tsx` | `PixelGrid` (grayscale cells, values, hover tooltip row/col/intensity, hatched + "pad" labels, highlight ring, position index), `ArrayImage` (canvas for feature maps / PCA components / resized input), `ValueBars`, `ProbBars`, `Heatmap`, `MiniCircuit` (draws recorded gate lists), `useStepper` + `StepControls` (Previous / Play / Pause / Next / Reset, "Step k of N", clickable progress), `Formula`, `Note`, `IO`, `Vec`. |
| `frontend/src/v2/playground/classical.tsx` | Image processing & PCA (8 steps), RBF-SVM (6), Logistic regression (4), CNN / MobileNetV3 (8; demo vs real NEU-DET crazing image side by side). |
| `frontend/src/v2/playground/quantum.tsx` | FRQI (10 steps; shots toggle 100/1,000/10,000), NEQR (8; 2/4/8-bit toggle), QKC (8; feature-map toggle, quantum vs RBF kernel heatmaps), VQC (9; trained θ, ring entanglement, measurement, loss, parameter-shift table, illustrative Adam step, untrained vs trained, recorded loss curve). |
| `frontend/src/v2/pages/Playground.tsx` | `/playground`. Algorithm picker grouped Classical / Quantum, persistent 3×3 grid (switches to the 4×4 zero-padded embedding for FRQI/NEQR steps), explanation, input/output, formulas, values. URL state `?algo=&step=&bits=&fmap=&shots=` makes steps linkable for the viva. |
| `frontend/src/v2/pages/QuantumVsClassical.tsx` | `/quantum-vs-classical`. Headline bests, tabs: A Classical, B Quantum (grouped kernels / FRQI-NEQR / VQC, ablations separate), C Hybrid (per k: classical controls vs quantum on identical features, feature effect vs classifier effect, seed-noise statement), D Side by side (pick one classical and one quantum algorithm; pipeline, representation, similarity, cost, demo output, matching real accuracy; dimension table). |
| `frontend/src/App.tsx` | Sidebar: **Algorithm Playground** and **Quantum vs Classical** placed right after Overview. Titles and routes added. |

## 3. Honesty rules applied
- An amber "Illustrative demonstration" banner appears on every playground view. Every demo prediction carries "not an evaluation result". The demo is never written into any V2 result or aggregate.
- Quantum steps say "noiseless statevector simulation on a classical CPU — not quantum hardware".
- PCA is *applied* (fitted on 1,080 training images), never fitted on the demo. FRQI/NEQR need 2ⁿ pixels, so the 4×4 zero-padded embedding is shown explicitly.
- CNN feature maps and kernels are captured from the trained networks with forward hooks. Nothing is synthesised.
- The VQC Adam step is labelled illustrative (one example, computed with the real code). Per-step θ trajectories were not recorded, so only the recorded per-epoch loss curve is shown.
- FRQI/NEQR are encodings, so the side-by-side shows "no classifier was run on the 3×3 demo" rather than inventing a prediction.
- The QKC demo angle −0.039 lies just outside [0, π] (the scaler was fitted on training data). The page says so instead of clipping it.
- Every metric on the comparison page comes from `/api/v2/models`. Nothing is hardcoded, and missing values render "unavailable".

## 4. Not changed
No experiment was rerun. No V0/V2 result file, split, seed or evaluation protocol was modified. Historical hashes were verified after the work (see the verification report).
