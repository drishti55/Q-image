# Algorithm Visualization — Verification Report

Date: 2026-11-16. Everything below was run against the real backend (`api_main.py`, :8000) and Vite dev server (:5173)
in installed Google Chrome (Playwright, headless), plus unit and integration suites.

## 1. Summary
| Suite | Result |
|---|---|
| Backend pytest (`tests/`, incl. new `tests/test_v2_playground.py`: 8 tests) | **172 passed** |
| Frontend Vitest (`src/lib/v2.test.ts`, `src/v2/v2.test.tsx`, new `src/v2/playground.test.tsx`: 10 tests) | **22 passed** |
| TypeScript `tsc -b` | clean |
| Production build `npm run build` | success (existing >500 kB chunk-size warning only) |
| Browser e2e, new `scripts/v2/playground_e2e.py` | **35 passed, 0 failed** |
| Browser e2e, existing `scripts/v2/dashboard_e2e.py` (regression) | **49 passed, 0 failed** — see note |
| Historical hashes `verify_historical.py --label algorithm_visualization` | 3,690 / 3,690 unchanged, `all_ok=true` |
| V2 experiment files newer than `analysis.json` | 0 (nothing rerun or modified) |
| Locked test set | not accessed (the playground uses one demo grid, plus one *training* image for the CNN comparison) |

Linting: the frontend has no ESLint configuration file (`eslint` v10 requires `eslint.config.*`), so no lint step exists to run. Type checking (`tsc -b`) is the static check.

Note on the regression e2e: its check "sidebar is short (≤ 12 links)" was raised to ≤ 14 because the two requested navigation entries were added (13 links now).

## 2. Value checks (independent of the UI)
`tests/test_v2_playground.py` recomputes from first principles:
- the grid is [[70,180,0],[19,20,0],[0,0,0]]; the 4×4 embedding is zero-padded; flattened values are /255;
- FRQI: θ = (π/2)·p/255 for 70/180/19/20 (0.4312, 1.1088, 0.1170, 0.1232 rad), amplitudes cos θ/4 and sin θ/4; statevector vs formula error < 1e-10; 4 gate blocks (zero pixels add none); exact reconstruction;
- NEQR binaries: 2-bit 01/10/00/00, 4-bit 0100/1011/0001/0001, 8-bit 01000110/10110100/00010011/00010100; quantisation = round(p/255·(2ᵇ−1)); decode matches; 8-bit MSE = 0;
- QKC: self-overlap = 1, statevector normalised, scaled features = bandwidth × angles; VQC: parameter count = 2·n·L, probabilities sum to 1, parameter-shift = (E₊ − E₋)/2; LogReg probabilities = softmax(scores); SVM example K = exp(−γ·d²);
- endpoint serves the file; it returns 404 with a build hint when the file is missing (temporary results root).

## 3. Frontend unit checks (Vitest)
PixelGrid values, highlight, five "pad" labels, hover tooltip text (given and padding cells); every algorithm × option builds and renders all steps from the real JSON; step controls (next / previous / go-to / reset, disabled Previous at step 1); FRQI angles on screen; NEQR 2/4/8-bit toggle; explicit error state when `/api/v2/playground` 404s; comparison helpers (input dims, legacy/ablation exclusion, best model, feature-vs-classifier effect); Quantum vs Classical tabs bound to API data.

## 4. Browser checks (`results/qml_v2/reports/algorithm_screenshots/e2e_results.json`)
Expected values are read from the API at run time, never hardcoded.

| Check | Result |
|---|---|
| sidebar link opens the Algorithm Playground | PASS |
| illustrative disclaimer visible | PASS |
| 3×3 grid shows 70,180,0,19,20,0,0,0,0 | PASS |
| hover tooltip shows row/column/intensity | PASS |
| hover on padding cell says zero padding | PASS |
| normalisation step shows 70/255 = 0.2745 | PASS |
| Next advances the counter | PASS |
| Previous goes back | PASS |
| Play auto-advances | PASS |
| Pause stops the animation | PASS |
| Reset returns to step 1 | PASS |
| RBF numeric example uses the recorded kernel value | PASS |
| CNN feature maps rendered (canvas) | PASS |
| FRQI angles for 70/180/19/20 are correct | PASS |
| FRQI gate count from data | PASS |
| FRQI shots toggle changes the reconstruction label | PASS |
| NEQR 2-bit binaries ['01', '10', '00', '00'] | PASS |
| NEQR 4-bit binaries ['0100', '1011', '0001', '0001'] | PASS |
| NEQR 8-bit binaries ['01000110', '10110100', '00010011', '00010100'] | PASS |
| QKC product_ry circuit has 4 gates | PASS |
| QKC zz_linear circuit has 17 gates | PASS |
| QKC zz_full circuit has 26 gates | PASS |
| VQC parameter-shift derivative from data | PASS |
| VQC loss curve rendered | PASS |
| classical best highlighted matches API | PASS |
| classical row shows API accuracy | PASS |
| quantum row: accuracy + gate counts from API | PASS |
| quantum view excludes legacy V0 rows | PASS |
| hybrid table shows product-RY hybrid accuracy | PASS |
| hybrid explains no quantum advantage | PASS |
| side-by-side shows real VQC accuracy | PASS |
| mobile /playground?algo=frqi&step=3: no horizontal page overflow | PASS |
| mobile /quantum-vs-classical?view=side: no horizontal page overflow | PASS |
| no console errors | PASS |
| no failed /api requests | PASS |

## 5. Screenshots (`results/qml_v2/reports/algorithm_screenshots/`)
| Requested | File |
|---|---|
| 3×3 playground | `01_playground_3x3.png` |
| Classical walkthrough | `02_classical_walkthrough_cnn.png` |
| FRQI | `03_frqi_angles.png`, `03b_frqi_reconstruction.png` |
| NEQR | `04_neqr_binary.png` |
| QKC | `05a_qkc_circuit.png`, `05_qkc_kernel.png` |
| VQC | `06_vqc.png` |
| Quantum vs classical | `07_classical_view.png`, `08_quantum_vs_classical.png`, `10_side_by_side.png` |
| Hybrid | `09_hybrid.png` |
| Mobile (390 px) | `11_mobile_playground.png` |

## 6. Fix made during verification
- The QKC kernel heatmaps (7 columns each) were clipped side by side at 1440 px. They now stack below 2xl widths.
- The first e2e run raced React re-renders (assertions ran before the step updated). The script now waits 300 ms after each click. The UI itself was correct, confirmed by a slow manual run.

## 7. Addendum — results-comparison charts (2026-11-16)
New `frontend/src/v2/charts.tsx` (Recharts; every value from `/api/v2/models`, each chart has a Chart/Table toggle and hover tooltips):
best model per family (± sd whiskers), every model by family (strip plot), hybrid feature-vs-classifier effect, accuracy vs qubits
(QKC maps vs the classical RBF-SVM on identical features vs VQC), NEQR bit depth × resolution, shot noise (QKC; FRQI vs NEQR),
accuracy vs prediction time (log scale). Shown as the default **Charts** tab of Quantum vs Classical; the first two also on Model Comparison.
Family colours were re-stepped to a palette validated with the dataviz validator on the #0f172a surface (the previous amber/orange pair failed
the normal-vision floor); within-family series use validated single-hue ordinal ramps plus dash patterns and direct end labels.
Checks: playground/comparison e2e **48/48** (adds chart-render, tooltip, table-view and Model Comparison chart checks; screenshots `12_*`, `13_*`, `14_*`),
dashboard e2e 49/49, Vitest 22/22, pytest 172 passed, build OK, historical hashes 3,690/3,690 unchanged.
