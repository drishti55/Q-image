# Q-ImageLab

### Can quantum image encodings classify real steel defects? FRQI, NEQR and quantum kernels against classical baselines

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![Qiskit](https://img.shields.io/badge/Qiskit-2.5-purple)](https://qiskit.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.142-teal)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.2-blue)](https://react.dev)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.9-orange)](https://scikit-learn.org)

Q-ImageLab tests whether the two best-known quantum image encodings, **FRQI** and **NEQR**, can classify the six defect classes of hot-rolled steel in the public **NEU-DET** dataset. Every quantum model is compared with a classical model that receives exactly the same input, under a protocol that keeps the test set locked until the end.

The repository contains the experiments (protocols V2 → V4), a new **patch-ensemble mixed-state kernel**, a FastAPI + React research and learning platform, the project report and the presentation.

> All quantum computations are exact (noiseless) classical simulations on a CPU. No quantum hardware was used.

---

## Key findings

All numbers are accuracy on the same **360 locked test images**, mean ± s.d. over three seeds.

| Model | Type | Test accuracy |
|---|---|---:|
| Whole-image FRQI kernel (V2) | quantum (simulated) | 60.6 ± 1.2 % |
| Whole-image NEQR kernel (V2) | quantum (simulated) | 60.2 ± 0.4 % |
| **Patch-ensemble FRQI, 8×8 patches (V4, proposed)** | quantum (simulated) | **87.8 ± 1.5 %** |
| **Patch-ensemble NEQR, 4×4 patches (V4, proposed)** | quantum (simulated) | **82.7 ± 10.1 %** |
| RBF-SVM on the same patches (V4, matched control) | classical | 83.6 ± 0.3 % |
| QKC on texture features (V3) | quantum (simulated) | 95.3 ± 3.2 % |
| Texture (LBP + GLCM) RBF-SVM (V3) | classical | 95.6 ± 2.2 % |
| Frozen MobileNetV3 + logistic regression (V2, best overall) | classical | 96.4 ± 1.1 % |

1. **Patching works.** Representing an image as the mixture of its FRQI/NEQR patch states and comparing images with Tr(ρ_A ρ_B) improves FRQI by +27.1 pp and NEQR by +22.5 pp (Holm-corrected p < 0.001).
2. **No quantum advantage.** A classical SVM on the same patches is statistically tied with patch FRQI (+4.2 pp, p = 0.060). On every matched input (CNN, texture, pixel features), quantum kernels and RBF-SVM score about the same.
3. **Features set the ceiling.** Quantum and classical models on raw pixels stay near 40–65 %. On CNN or texture features both reach 90–96 %.
4. **More quantum machinery did not help.**
   - A VQC with no trained layers (90.8 %) beat the trained VQC (72.4 %).
   - The feature map without entanglement (Product-RY, 95.3 %) beat ZZ-Linear (60.6 %).
   - 8-bit NEQR was worse than 4-bit.
5. **FRQI vs NEQR depends on the job.** NEQR reads images back exactly and is robust to few measurement shots. FRQI compares textures better (+5.1 pp in the patch kernel) but needs many shots.

---

## Dataset — NEU-DET

1,800 grayscale images of hot-rolled steel, 200×200 px. Six classes with 300 images each: **crazing, inclusion, patches, pitted surface, rolled-in scale, scratches**.

| Split (identical for seeds 0, 1, 2) | Per class | Total |
|---|---:|---:|
| Train | 180 | 1,080 |
| Validation | 60 | 360 |
| **Locked test** (official validation folder) | 60 | 360 |

- Every file is fingerprinted with SHA-256 in a dataset manifest.
- Train and validation are split by blocks of 20 consecutive files, so near-duplicate neighbouring images never land on both sides.
- The 1,800 images are included in `NEU-DET/` (`train/images/<class>/`, `validation/images/<class>/`); the XML annotations are not used. Set `QIL_DATASET_PATH` to use a copy elsewhere.

---

## What was implemented

| Component | Where |
|---|---|
| FRQI and NEQR encoders (real Qiskit circuits; NEQR with 2/4/8 bits) | `src/frqi`, `src/neqr`, `src/v2/frqi_neqr.py` |
| Whole-image FRQI/NEQR overlap kernels + SVM | `src/v2/frqi_neqr.py` |
| Quantum kernel classifier (QKC): Product-RY, ZZ-Linear, ZZ-Full; exact and shot-based | `src/v2/qkernel.py` |
| Projected quantum kernel (PQK) | `src/v3/models.py` |
| Variational quantum classifier (VQC): Adam / COBYLA / SPSA, parameter-shift, frozen and encoding-only controls | `src/v2/vqc.py` |
| Hybrid: frozen MobileNetV3 → PCA → QKC or VQC | `src/v2/cnn.py` |
| Classical baselines: RBF-SVM, logistic regression, small CNN, frozen MobileNetV3; texture features (LBP + GLCM) | `src/v2/models_classical.py`, `src/v3/features.py` |
| **Patch-ensemble mixed-state kernel** and the matched classical patch control | `src/v4/models.py` |
| Reconstruction study: all 1,800 images × 20 methods (MSE, PSNR, SSIM vs shots) | `scripts/v4/reconstruct_all.py` |

### Evaluation protocol

1. Every configuration is trained on 3 seeds and scored on **validation macro-F1 only**.
2. The best configuration of each group is **frozen with a SHA-256 hash**.
3. Each frozen model is evaluated **once** on the locked test set, and every access is logged.
4. Eight pre-declared V4 comparisons are tested with:
   - a paired permutation test (10,000 sign flips);
   - paired-bootstrap 95 % confidence intervals;
   - McNemar's test;
   - Holm correction.

| Protocol | Runs → selected models | What it added |
|---|---|---|
| V0 (historical) | — | Early prototype: SVM, Random Forest, KNN, Decision Tree on raw pixels with random splits and no locked test. Kept read-only; **not comparable** with V2–V4. |
| V2 | 2,583 → 88 | Locked test; classical, QKC, VQC, whole-image FRQI/NEQR, hybrid, shot study |
| V3 | 5,316 → 70 | Texture features, PQK, VQC controls, matched classical controls |
| V4 | 864 → 5 | Patch-ensemble FRQI/NEQR kernels + matched classical control |

---

## The Q-ImageLab platform

A FastAPI back end and a React 19 + TypeScript front end (Vite, Tailwind, Recharts). The platform reads only saved results; it never retrains or re-selects models.

| Area | Pages |
|---|---|
| Start here | Overview of all versions · Presentation mode (V4) |
| Results | V4 results · model comparison (V2–V4, 163 models) · quantum vs classical · classification analysis · V3 results · experiment log |
| Learn & explore | Concepts & pipeline · How it works (live replay of the frozen V4 model) · 3×3 algorithm playground · CNN feature studio · quantum image encoding · quantum circuits · knowledge-check quiz |
| Images | **Dataset gallery (all 1,800 images, click to view)** · upload your own image (FRQI/NEQR encoding, reconstruction and classification) · reconstruction study |
| Archive | Historical V0 results (read-only) |

---

## Setup and usage

Requirements: Python 3.11, Node 20+.

```bash
# Back end
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python api_main.py                      # API on http://localhost:8000

# Front end (second terminal)
cd frontend
npm install
npm run dev                             # app on http://localhost:5173 (proxies /api to :8000)
```

### Re-running the experiments

The saved results under `results/qml_v2`, `results/qml_v3` and `results/qml_v4` are what the platform shows. To regenerate them:

```bash
python scripts/v2/phase1_data_protocol.py    # manifest and splits
python scripts/v2/phase3_classical.py        # classical baselines
zsh scripts/v2/run_quantum_chain.sh          # V2 quantum phases 4–8
bash scripts/v3/chain_v3.sh                  # V3: candidates → select → freeze → test
bash scripts/v4/chain_v4.sh                  # V4: candidates → select → freeze → test
python scripts/v4/reconstruct_all.py         # reconstruction of all 1,800 images
```

### Tests

```bash
python -m pytest tests                  # back end: encoders, kernels, protocol integrity, API
cd frontend && npm test                 # front end (Vitest)
```

---

## Deployment (Render, free plan)

The repository deploys as **one Docker service**: the `Dockerfile` builds the React app, installs the pinned runtime
dependencies (`requirements-render.txt`), precomputes the frozen FRQI model's density matrices
(`scripts/v4/precompute_frozen.py`) and starts FastAPI, which serves both the site and `/api` on `$PORT`.

1. On [render.com](https://render.com): **New → Blueprint**, connect this GitHub repository. `render.yaml` creates the
   `q-imagelab` web service (Docker, free plan, branch `main`, health check `/api/v2/health`).
2. The first build takes about 10 minutes. The site is then at `https://<service-name>.onrender.com`.

The free instance has 512 MB of memory, so the hosted demo runs in **lite mode** (`QIL_LITE=1`):

| In the hosted demo | Status |
|---|---|
| All results pages, model comparison, learning pages, playground, quiz, dataset gallery, reconstruction study | available |
| How it works (live replay of the frozen V4 FRQI model) | available |
| Upload lab: FRQI and NEQR encoding up to 8×8, classification with the FRQI model | available |
| CNN feature studio, hybrid CNN pipeline, NEQR classification of uploads, uploads above 8×8 | off (need PyTorch / more memory); run locally |

Free instances sleep after 15 minutes without visitors; the first request after that takes about a minute.
Locally nothing changes: without `QIL_LITE` every feature is on.

---

## Report and presentation

| File | Contents |
|---|---|
| `research_paper_visuals/Project_Report/Q-ImageLab_Project_Report.pdf` (+ `.docx`) | B.Tech project report; generated by `research_paper_visuals/source/make_project_report.js` |
| `research_paper_visuals/Presentation/Q-ImageLab_Presentation.pptx` | 26-slide presentation with speaker notes; generated by `research_paper_visuals/source/make_presentation.js` |
| `research_paper_visuals/Presentation/Q-ImageLab_Slide_Wise_Content.md` (+ `.docx`) | Slide-by-slide content and speaker script |
| `research_paper_visuals/V4_paper_pack/` | Paper figures, tables and LaTeX sources |

---

## Project structure

```
QIP/
├── api_main.py               # FastAPI app (mounts /api/v2, /api/v3, /api/v4)
├── src/
│   ├── frqi/, neqr/          # FRQI and NEQR encoders (Qiskit)
│   ├── v2/                   # data protocol, features, QKC, VQC, CNN, FRQI/NEQR kernels, API
│   ├── v3/                   # texture features, PQK, API
│   └── v4/                   # patch-ensemble kernel, upload lab, CNN studio, dataset gallery, API
├── scripts/v2, v3, v4/       # experiment drivers
├── results/qml_v2, v3, v4/   # saved results the platform reads
├── frontend/                 # React + TypeScript app
├── tests/                    # pytest suite
└── research_paper_visuals/   # report, presentation, paper figures and their generators
```

---

## References

1. P. Q. Le, F. Dong and K. Hirota, "A flexible representation of quantum images for polynomial preparation, image compression, and processing operations," *Quantum Information Processing*, 10(1), 2011.
2. Y. Zhang, K. Lu, Y. Gao and M. Wang, "NEQR: a novel enhanced quantum representation of digital images," *Quantum Information Processing*, 12(8), 2013.
3. V. Havlíček et al., "Supervised learning with quantum-enhanced feature spaces," *Nature*, 567, 2019.
4. H.-Y. Huang et al., "Power of data in quantum machine learning," *Nature Communications*, 12, 2021.
5. K. Song and Y. Yan, "A noise robust method based on completed local binary patterns for hot-rolled steel strip surface defects," *Applied Surface Science*, 285, 2013.
