# Frontend and Backend Walkthrough

> Code: `api_main.py`, `src/v2/api.py`, `src/v2/api_models.py`, `src/v3/api.py`, `src/v4/api.py`,
> `frontend/src/App.tsx`, `frontend/src/v2/api.ts`, `frontend/src/v2/ui.tsx`, `frontend/src/v2/pages/*`,
> legacy `frontend/src/pages/*`.

---

## 1. Stack and why

| Layer | Technology (version) | Role | Alternatives & why not |
|---|---|---|---|
| Back end | Python 3.11, **FastAPI** 0.142, Uvicorn 0.54 | REST API over result files; live walkthrough | Flask/Django: FastAPI gives typed params, automatic validation and docs with less code; Python is required for Qiskit |
| Quantum | **Qiskit** 2.5.2, **Qiskit Aer** 0.17.2 | encoder circuits, transpilation, statevector/shots | PennyLane/Cirq: Qiskit has native FRQI-style MCRY/MCX and transpiler resource counts |
| Own simulator | NumPy batched statevector (`src/v2/qsim.py`) | fast kernels/VQC over whole data sets | Aer per circuit would be far slower for 1,080² kernels; verified vs Qiskit |
| ML | scikit-learn 1.9.1, PyTorch 2.15, torchvision 0.29 | SVM, LogReg, PCA, CNN, MobileNetV3 | — |
| Data/plots | NumPy 2.4.6, pandas 3.0.6, SciPy 1.17, Pillow 12.3, scikit-image, Matplotlib 3.11 | arrays, files, texture features, figures | Plotly not used |
| Front end | **TypeScript 6**, **React 19.2**, React Router 7.18, **Vite 8.3**, **Tailwind 3.4**, Recharts 3.10, lucide-react | single-page dashboard | plain JS: TypeScript catches API shape errors; Vite: fast dev server |
| Tests | pytest (179 functions), Vitest + Testing Library (27), Playwright (browser e2e) | correctness | — |

---

## 2. Backend architecture

`api_main.py` creates the FastAPI app, keeps the **legacy V0 endpoints** and mounts routers:
`/api/v2` (`src/v2/api.py`, `src/v2/api_models.py`), `/api/v3` (`src/v3/api.py`), `/api/v4` (`src/v4/api.py`).
V2–V4 routers are **read-only**: they load JSON/CSV/NPZ from `results/qml_v*`, never train or select. Missing files →
HTTP 404 with a message ("V4 results not built — run scripts/v4/analyze_v4.py"); the frontend shows it.
Validation: FastAPI query parameters (`Query(...)`), explicit checks (e.g. `/pipeline` rejects any image that is not a
locked-test image with 404). Pydantic request models are not used for V2–V4 (GET only). Results caching:
`functools.lru_cache` for the per-image index and the frozen model. Write protection: `src/v2/paths.assert_writable`
with `QIL_PROTECT_V2=1 QIL_PROTECT_V3=1`.

### Main endpoints
| Endpoint | Returns | Used by page |
|---|---|---|
| `GET /api/v2/health` | API version, number of selected models | header badge |
| `GET /api/v2/summary` | V2 overview: counts, best models, families, findings | V2 overview, Present |
| `GET /api/v2/models`, `/models/{group}`, `/per-class` | all 88 selected models + metrics | Model comparison, Classification, Q-vs-C |
| `GET /api/v2/experiments`, `/experiments/{id}`, `/…/predictions` | run log and details | Experiment log / detail |
| `GET /api/v2/circuits`, `/circuits/{id}` | rebuilt circuits + resources | Circuits |
| `GET /api/v2/reconstructions…` | V2 reconstruction records, rendered PNGs | Reconstruction studio, Encoding |
| `GET /api/v2/historical` | V0 summary (read-only) | Historical V0 |
| `GET /api/v3/results`, `/playground` | V3 groups, comparisons; 3×3 demo data | V3 results, Playground |
| `GET /api/v4/results` | V4 groups, frozen hash, 8 comparisons | V4 results |
| `GET /api/v4/versions` | headline numbers of V0–V4 (built from saved aggregates) | home (All versions) |
| `GET /api/v4/images` | 360 test images + % of 163 models correct | How it works |
| `GET /api/v4/image-models?image=` | saved predictions of all 163 models for one image | How it works step 9 |
| `GET /api/v4/pipeline?image=` | **live** recomputation of the frozen FRQI model on that image | How it works steps 1–7 |
| `GET /api/v4/reconstruction/summary`, `/reconstruction/image` | all-image reconstruction metrics and arrays | Reconstruction (all 1,800), How it works step 8 |
| Legacy `POST /api/quantum/compare-custom` | encodes an **uploaded** image with FRQI and NEQR, simulates, reconstructs, MSE/PSNR/SSIM | V0 Encoding Lab |
| Legacy `GET /api/quantum/reconstruct`, `/api/quantum/circuit` | single-image encode/reconstruct; circuit | V0 pages |
| Legacy `POST /api/quantum/batch/run`, `/api/qml/run`, `/api/qml/suite/run` | **HTTP 409 — disabled** (V0 results immutable) | V0 buttons (disabled) |

### Request lifecycle (real example: "How it works", step "The SVM decides")
1. User opens `/how-it-works`; React calls `useV4('/images')` → list of 360 test images with difficulty.
2. User clicks an image (or *Random* / *Hardest*); `useV4('/pipeline?image=validation/images/scratches/…jpg')`.
3. Backend `pipeline()`: loads the frozen V4-frqi-p8 model and its 1,080 training density matrices (cached) →
   preprocesses the image (64×64, stretch) → cuts 225 patches → computes θ = (π/2)·4·x → builds ρ → computes
   Tr(ρ ρ_train) for all 1,080 training images → `svm.decision_function` and `predict` → compares with the
   prediction saved during the single locked-test evaluation → JSON.
4. Frontend stores it in hook state; the stepper animates through preprocess → patches → encode → mix → kernel →
   SVM; the verdict text says whether the live prediction is "identical to the saved locked-test prediction".

### Request lifecycle (legacy upload)
V0 Encoding Lab → form-data (file, resolution, precision, shots) → `compare-custom` → resize + quantise → FRQIEncoder
and NEQREncoder → Aer simulation → reconstructors → MetricsEvaluator → base64 images + metrics → page shows
original vs reconstructions. (Historical tool; nothing is saved.)

---

## 3. Frontend structure
`App.tsx`: routes + sidebar (sections "Latest · Protocol V4", "Earlier · Protocols V3/V2", "Data & history"),
header with breadcrumb and V2 API health badge. `v2/api.ts`: hooks returning `{data, error, loading}`.
`ui.tsx` `Gate` component renders **loading / error / empty** states explicitly (no silent fallbacks, no hard-coded
numbers — Vitest checks that numbers come from mocked API responses).

### Pages (current)
| Route | What it shows & interactions | Data |
|---|---|---|
| `/` All versions | V4 hero (FRQI/NEQR big numbers, deltas vs V2 with p-values), chart of FRQI/NEQR per version (hover tooltips), version cards (links), key-model table | `/api/v4/versions` |
| `/quantum-v4` | protocol strip (groups, runs, freeze hash), 4 tiles, 8 comparisons table (significant / n.s. badges), all V4 groups | `/api/v4/results` |
| `/how-it-works` | class filter + image grid (% correct), *Random* / *Hardest*, **Play / Pause / Next / Previous / Reset**, step dots 1–9: real image → preprocess → patches → encode one patch (angles, amplitudes, circuit sketch) → ρ heat-map → kernel (top similar training images) → SVM scores + verdict → measurement (real shot reconstructions) → grid of 163 models' saved predictions | `/images`, `/pipeline`, `/reconstruction/image`, `/image-models` |
| `/reconstruction-full` | table of 20 methods (MSE/SSIM per shot count), error-vs-shots charts, per-class table selector, image browser (record dropdown, index slider, *random*, *animate shots*) | `/api/v4/reconstruction/*` |
| `/quantum-v3` | V3 headline tiles, before/after chart, comparisons, groups | `/api/v3/results` |
| `/overview-v2` | V2 headline, family bars, findings | `/api/v2/summary` |
| `/quantum-vs-classical` | matched quantum vs classical comparisons | `/api/v2/models`, `/api/v3/playground` |
| `/playground` | **illustrative** 3×3 image: step through FRQI, NEQR, QKC, VQC, classical pipelines | `/api/v3/playground` (precomputed) |
| `/present` | slide mode (previous/next/slide dots/exit) | V2 summary, dataset, reconstructions |
| `/models` | leaderboard/advanced views, search, family filters, compare chips | `/api/v2/models` |
| `/encoding` | FRQI vs NEQR explanation and measured costs | models + reconstructions |
| `/circuits` | list of 33 circuit configurations, real SVG + text diagram, resources | `/api/v2/circuits` |
| `/reconstruction` | V2 reconstruction studio | `/api/v2/reconstructions` |
| `/classification` | model selector, per-class precision/recall/F1, confusion matrices per seed | `/api/v2/models`, `/per-class` |
| `/experiments-v2`, `/experiments/:id` | run log, configs, metrics | `/api/v2/experiments` |
| `/historical-v0/*` | V0 pages (dashboard, QML lab, classical analytics, encoding lab with upload, batch lab with launching disabled, dataset browser) | legacy `/api/*` |

### Verifying "not hard-coded"
`frontend/src/v2/v2.test.tsx` mocks API responses with unusual numbers (e.g. 88.9 %) and asserts the page shows
them; Playwright `scripts/v4/v4_pages_e2e.py` checks the FRQI tile equals the frozen accuracy in `v4_results.json`.

### Self-check
1. Which endpoint recomputes a prediction live? 2. What happens when you click V0 "Run batch"? 3. How does the
Gate component handle a missing results file? 4. Where do Circuits-page diagrams come from? 5. Trace the upload flow.
