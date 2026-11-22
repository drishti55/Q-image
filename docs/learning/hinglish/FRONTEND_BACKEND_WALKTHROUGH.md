# Frontend aur Backend Walkthrough

> Code: `api_main.py`, `src/v2/api.py`, `src/v2/api_models.py`, `src/v3/api.py`, `src/v4/api.py`,
> `frontend/src/App.tsx`, `frontend/src/v2/api.ts`, `frontend/src/v2/ui.tsx`, `frontend/src/v2/pages/*`,
> legacy `frontend/src/pages/*`.

---

## 1. Stack aur kyun

| Layer | Technology (version) | Role | Alternatives & kyun nahi |
|---|---|---|---|
| Back end | Python 3.11, **FastAPI** 0.142, Uvicorn 0.54 | result files par REST API; live walkthrough | Flask/Django: FastAPI kam code mein typed params, validation aur docs deta hai; Qiskit ke liye Python chahiye |
| Quantum | **Qiskit** 2.5.2, **Qiskit Aer** 0.17.2 | encoder circuits, transpilation, statevector/shots | PennyLane/Cirq: Qiskit mein MCRY/MCX aur transpiler resource counts native hain |
| Apna simulator | NumPy batched statevector (`qsim.py`) | poore dataset par fast kernels/VQC | har circuit Aer par 1,080² kernels ke liye bahut slow; Qiskit se verify |
| ML | scikit-learn 1.9.1, PyTorch 2.15, torchvision 0.29 | SVM, LogReg, PCA, CNN, MobileNetV3 | — |
| Data/plots | NumPy 2.4.6, pandas 3.0.6, SciPy 1.17, Pillow 12.3, scikit-image, Matplotlib 3.11 | arrays, files, texture features, figures | Plotly use nahi hua |
| Front end | **TypeScript 6**, **React 19.2**, React Router 7.18, **Vite 8.3**, **Tailwind 3.4**, Recharts 3.10, lucide-react | single-page dashboard | plain JS: TypeScript API shape ki galtiyan pakadta hai; Vite: fast dev server |
| Tests | pytest (179), Vitest + Testing Library (27), Playwright (browser e2e) | correctness | — |

---

## 2. Backend architecture

`api_main.py` FastAPI app banata hai, **legacy V0 endpoints** rakhta hai aur routers mount karta hai: `/api/v2`, `/api/v3`,
`/api/v4`. V2–V4 routers **read-only** hain: `results/qml_v*` se JSON/CSV/NPZ load karte hain, kabhi train ya select nahi
karte. File missing → HTTP 404 message ke saath ("V4 results not built — run scripts/v4/analyze_v4.py"); frontend ise
dikhata hai. Validation: FastAPI query parameters, explicit checks (jaise `/pipeline` locked-test image na ho toh 404).
V2–V4 mein Pydantic request models nahi (sirf GET). Caching: `functools.lru_cache` (per-image index, frozen model).
Write protection: `assert_writable` + `QIL_PROTECT_V2=1 QIL_PROTECT_V3=1`.

### Main endpoints
| Endpoint | Kya deta hai | Kaunsa page |
|---|---|---|
| `GET /api/v2/health` | API version, selected models | header badge |
| `GET /api/v2/summary` | V2 overview: counts, best models, families, findings | V2 overview, Present |
| `GET /api/v2/models`, `/models/{group}`, `/per-class` | saare 88 models + metrics | Model comparison, Classification, Q-vs-C |
| `GET /api/v2/experiments…` | run log aur details | Experiment log / detail |
| `GET /api/v2/circuits…` | rebuilt circuits + resources | Circuits |
| `GET /api/v2/reconstructions…` | V2 reconstruction records, PNGs | Reconstruction studio, Encoding |
| `GET /api/v2/historical` | V0 summary (read-only) | Historical V0 |
| `GET /api/v3/results`, `/playground` | V3 groups, comparisons; 3×3 demo data | V3 results, Playground |
| `GET /api/v4/results` | V4 groups, frozen hash, 8 comparisons | V4 results |
| `GET /api/v4/versions` | V0–V4 headline numbers (saved aggregates se) | home (All versions) |
| `GET /api/v4/images` | 360 test images + 163 models mein se kitne % sahi | How it works |
| `GET /api/v4/image-models?image=` | ek image par 163 models ki saved predictions | How it works step 9 |
| `GET /api/v4/pipeline?image=` | us image par frozen FRQI model ka **live** recomputation | How it works steps 1–7 |
| `GET /api/v4/reconstruction/summary`, `/image` | saari images ke reconstruction metrics aur arrays | Reconstruction (all 1,800), step 8 |
| Legacy `POST /api/quantum/compare-custom` | **uploaded** image ko FRQI aur NEQR se encode, simulate, reconstruct, MSE/PSNR/SSIM | V0 Encoding Lab |
| Legacy `GET /api/quantum/reconstruct`, `/circuit` | single-image encode/reconstruct; circuit | V0 pages |
| Legacy `POST /api/quantum/batch/run`, `/api/qml/run`, `/api/qml/suite/run` | **HTTP 409 — disabled** (V0 results immutable) | V0 buttons (disabled) |

### Request lifecycle (real example: "How it works", step "The SVM decides")
1. User `/how-it-works` kholta hai; React `useV4('/images')` call karta hai → 360 test images difficulty ke saath.
2. User image click karta hai (ya *Random* / *Hardest*); `useV4('/pipeline?image=validation/images/scratches/…jpg')`.
3. Backend `pipeline()`: frozen V4-frqi-p8 model aur uske 1,080 training density matrices load (cached) → image preprocess
   (64×64, stretch) → 225 patches → θ = (π/2)·4·x → ρ banao → saari 1,080 training images ke saath Tr(ρ ρ_train) →
   `svm.decision_function` aur `predict` → single locked-test evaluation mein saved prediction se compare → JSON.
4. Frontend hook state mein rakhta hai; stepper preprocess → patches → encode → mix → kernel → SVM animate karta hai;
   verdict batata hai ki live prediction "saved locked-test prediction ke identical" hai ya nahi.

### Request lifecycle (legacy upload)
V0 Encoding Lab → form-data (file, resolution, precision, shots) → `compare-custom` → resize + quantise → FRQIEncoder aur
NEQREncoder → Aer simulation → reconstructors → MetricsEvaluator → base64 images + metrics → page original vs reconstructions
dikhata hai. (Historical tool; kuch save nahi hota.)

---

## 3. Frontend structure
`App.tsx`: routes + sidebar (sections "Latest · Protocol V4", "Earlier · Protocols V3/V2", "Data & history"), breadcrumb aur V2
API health badge wala header. `v2/api.ts`: `{data, error, loading}` dene wale hooks. `ui.tsx` ka `Gate` component **loading /
error / empty** states saaf dikhata hai (koi silent fallback nahi, koi hard-coded number nahi — Vitest check karta hai ki numbers
mocked API se aate hain).

### Pages (current)
| Route | Kya dikhata hai & interactions | Data |
|---|---|---|
| `/` All versions | V4 hero (FRQI/NEQR bade numbers, V2 se delta + p-values), har version ka FRQI/NEQR chart (hover tooltips), version cards, key-model table | `/api/v4/versions` |
| `/quantum-v4` | protocol strip (groups, runs, freeze hash), 4 tiles, 8 comparisons table (significant / n.s.), saare V4 groups | `/api/v4/results` |
| `/how-it-works` | class filter + image grid (% correct), *Random* / *Hardest*, **Play / Pause / Next / Previous / Reset**, step dots 1–9: real image → preprocess → patches → ek patch encode (angles, amplitudes, circuit sketch) → ρ heat-map → kernel (sabse similar training images) → SVM scores + verdict → measurement (real shot reconstructions) → 163 models ki saved predictions ka grid | `/images`, `/pipeline`, `/reconstruction/image`, `/image-models` |
| `/reconstruction-full` | 20 methods ki table (har shot count par MSE/SSIM), error-vs-shots charts, per-class table, image browser (record dropdown, index slider, *random*, *animate shots*) | `/api/v4/reconstruction/*` |
| `/quantum-v3` | V3 tiles, before/after chart, comparisons, groups | `/api/v3/results` |
| `/overview-v2` | V2 headline, family bars, findings | `/api/v2/summary` |
| `/quantum-vs-classical` | matched quantum vs classical comparisons | `/api/v2/models`, `/api/v3/playground` |
| `/playground` | **illustrative** 3×3 image: FRQI, NEQR, QKC, VQC, classical pipelines step by step | `/api/v3/playground` (precomputed) |
| `/present` | slide mode (previous/next/slide dots/exit) | V2 summary, dataset, reconstructions |
| `/models` | leaderboard/advanced views, search, family filters, compare chips | `/api/v2/models` |
| `/encoding` | FRQI vs NEQR explanation aur measured costs | models + reconstructions |
| `/circuits` | 33 circuit configurations, real SVG + text diagram, resources | `/api/v2/circuits` |
| `/reconstruction` | V2 reconstruction studio | `/api/v2/reconstructions` |
| `/classification` | model selector, per-class precision/recall/F1, har seed ke confusion matrices | `/api/v2/models`, `/per-class` |
| `/experiments-v2`, `/experiments/:id` | run log, configs, metrics | `/api/v2/experiments` |
| `/historical-v0/*` | V0 pages (dashboard, QML lab, classical analytics, upload wala encoding lab, launching disabled batch lab, dataset browser) | legacy `/api/*` |

### "Hard-coded nahi hai" ka saboot
`frontend/src/v2/v2.test.tsx` unusual numbers (jaise 88.9 %) wale mocked API responses deta hai aur check karta hai ki page wahi
dikhaye; Playwright `scripts/v4/v4_pages_e2e.py` check karta hai ki FRQI tile `v4_results.json` ki frozen accuracy ke barabar hai.

### Self-check
1. Kaunsa endpoint prediction live recompute karta hai? 2. V0 "Run batch" click karne par kya hota hai? 3. Results file missing
ho toh Gate component kya karta hai? 4. Circuits page ke diagrams kahan se aate hain? 5. Upload flow trace karo.
