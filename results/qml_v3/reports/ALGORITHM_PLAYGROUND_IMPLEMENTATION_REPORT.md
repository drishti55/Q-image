# 3×3 Algorithm Playground — Implementation Report (V3)

Date: 2026-11-16. Route `/playground` (sidebar: **3×3 Algorithm Playground**, second item after Overview).
Presentation mode: `/playground?present=1` (button on the page).

## 1. Data: real values, no classifier outputs
| Item | Where |
|---|---|
| Builder | `scripts/v3/build_playground_v3.py` |
| Output | `results/qml_v3/playground/playground_3x3.json` (`"illustrative": true`) |
| API | `GET /api/v3/playground` (`src/v3/api.py`, read-only; 404 with a build hint if missing) |

The builder starts from the V2 playground file (read-only). Every intermediate value in that file was produced by the real implementations: `preprocess_image` resize, the train-fitted PCA, the trained seed-0 checkpoints, `FRQIEncoder` / `NEQREncoder` / reconstructors, the QKC feature maps and the VQC circuit.

V3 changes:
- **Removed:** all 25 classifier-output fields for the artificial grid (predicted classes, probabilities, logits, decision values), as the brief requires.
- **Added:** per-pixel traces. For each of 70, 180, 19 and 20, the builder records the real PCA-8 (standard) and PCA-4 (angle) features of the grid with that pixel set to 0, and the change this causes. It asserts that the reproduction matches the stored features before writing.
- **Added:** the raw flattened vector `[70, 180, 0, 19, 20, 0, 0, 0, 0]` and the CNN input value `(p/255 − 0.5)/0.25` per pixel.

## 2. Layout
| Area | Content |
|---|---|
| Top bar | Algorithm picker. Classical: Preprocessing, PCA, Logistic regression, RBF-SVM, CNN features, MobileNetV3 features. Quantum (simulated): FRQI, NEQR, QKC, VQC. Options: FRQI shots 100 / 1,000 / 10,000; NEQR precision 2 / 4 / 8-bit; QKC feature map product-RY / ZZ-linear / ZZ-full. Presentation-mode button. |
| Left — input image | Clickable 3×3 grayscale grid; the 4×4 zero-padded embedding is shown for FRQI/NEQR steps, with position indices. Padding is hatched, labelled and not selectable. The selected cell is ringed and shows its current value at the current stage (e.g. `θ0.43`, `0100`, `RY`). The selected-pixel card shows intensity, row/column, normalised value, 8-bit binary, NEQR 4-bit code, FRQI angle (rad and °) and the current processing state. |
| Centre — processing | Family badge, Previous / Play / Pause / Next / Reset, "Step k of N", clickable progress bar and stage list. Below it, the **journey of the selected pixel**: one chip per stage, the active chip highlighted and earlier chips marked done. Then the step's visual. |
| Right — explanation | What is happening? · Why is it needed? · Formula · Actual calculated output (real numbers for the selected pixel) · Interpretation (classical or quantum). |

URL state (`algo`, `step`, `px`, `bits`, `fmap`, `shots`, `present`) makes every view linkable. Layout: three columns at ≥1280 px, two below that (explanation underneath), one column on phones.

## 3. Walkthroughs (all values from the data file)
| Algorithm | Steps | Pixel journey |
|---|---|---|
| Preprocessing | original image → extraction → `pixel/255` → flatten (raw and normalised vectors, selected entry highlighted) → pixel vector vs reduced feature vector → 64×64 resize → standardisation | 70 → 0.2745 → x[0] → 64² block → z |
| PCA | input → real components (fitted on 1,080 training images) → projection → the selected pixel's real contribution Δ → reduced feature vector | ‖Δ‖ per pixel: 1.318 (70), 4.040 (180), 0.415 (19), 0.518 (20) |
| Logistic regression | features → real weights (heat map) → Δ class score from this pixel (real W·Δx) → softmax worked on clearly labelled example numbers | Δx → W → Δz → σ |
| RBF-SVM | features → distance → K = exp(−γd²) with the recorded numbers → decision-boundary intuition (training scatter) | Δx → d² → K → support vectors |
| CNN features | 128×128 input with (x−0.5)/0.25 → real trained 3×3 filters → feature maps (demo and a real training image) → pooling/architecture → 128-d vector | 70 → −0.902 → filters → maps → 128-d |
| MobileNetV3 | ImageNet preprocessing → frozen network (checksum) → real first-layer maps → 576-d vector | RGB copy → network → maps → 576-d |
| FRQI (10) | pixel selection → normalisation → angles for all 9 cells (padding θ = 0) → position bits → H⊗4 → registers → this pixel's X + MCRY(2θ) block → amplitudes from the statevector → measurement (shots) → reconstruction | 70 → 0.2745 → θ 0.4312 rad = 24.71° → \|0000⟩ → MCRY(0.8624) → 0.2271\|0⟩ + 0.1045\|1⟩ → P = 0.1747 → 70 |
| NEQR (9) | value → quantisation → binary (bit tiles) → amplitude vs basis-state encoding → position → intensity register → this pixel's X + MCX block → basis states → reconstruction | 70 → q = 4 → 0100 (4-bit) / 01 (2-bit) / 01000110 (8-bit) → \|0000⟩ → MCX onto q6 → 68.0 (4-bit) |
| QKC (8) | input features (this pixel's real Δ angles) → bandwidth → feature-map circuit (switchable) → statevector → overlap → **clickable kernel matrix** (each entry explained) → classical SVM → output (no class for the grid) | Δa → x = b·a → U(x) → ψ → K → SVM |
| VQC (10) | input → RY encoding → trained θ → CNOT ring → measurement (untrained vs trained) → loss (illustrative label) → parameter-shift table → Adam step (illustrative, real code) → updated circuit → recorded loss curve | Δa → RY → θ → CX → ⟨Z⟩ → ∇ |

All classifier stages end with: *"No class is shown for this grid …"*. The only traces that are not recorded data are the illustrative Adam step and the softmax example numbers, and both are labelled as such. Per-step VQC parameter trajectories were never recorded, so none are shown; the loss curve is the recorded one.

## 4. Presentation mode
- Full-screen overlay without the dashboard navigation.
- Larger algorithm buttons, pixel cells (100 px), headings and explanation text.
- Auto-play advances every 4.2 s. ← → step through, Esc or Exit leaves.
- Reset and every control remain available.

## 5. Quantum vs Classical side by side
`/quantum-vs-classical?view=side` now uses the V3 data, has a pixel picker and shows, for one classical and one quantum algorithm:
- the selected pixel's value at every stage;
- representation, maths, similarity, cost and output representation;
- the matching model's real NEU-DET test accuracy;
- a 7-row dimension table, including complexity and hardware.

No demo predictions are shown.

## 6. Files
| File | Purpose |
|---|---|
| `frontend/src/v2/playground/types.ts` | Step / Trace / Algo types |
| `frontend/src/v2/playground/classical.tsx` | 6 classical walkthroughs |
| `frontend/src/v2/playground/quantum.tsx` | 4 quantum walkthroughs |
| `frontend/src/v2/playground/widgets.tsx` | clickable `PixelGrid` and other widgets |
| `frontend/src/v2/pages/Playground.tsx` | the page and presentation mode |
| `frontend/src/v2/api.ts` | `useV3` |
| `frontend/src/App.tsx` | navigation and routes |
| `src/v3/api.py`, `api_main.py` | the `/api/v3` router |
