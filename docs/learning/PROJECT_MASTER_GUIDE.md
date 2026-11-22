# Q-ImageLab — Project Master Guide

> Source of truth: the code and the saved result files in this repository (audited on 19 Nov 2026).
> Where the code and documentation disagree, the code wins and the disagreement is listed in §6.
> Companion files in this folder go deeper on each topic (see §8).

---

## 0. The project in one paragraph

Q-ImageLab asks a simple question: **can quantum image encodings (FRQI and NEQR) classify real steel-surface
defects, and if they help, is it because of the quantum part?** We use the NEU-DET data set (1,800 images, 6
defect classes). Everything quantum is *simulated exactly on a laptop CPU* — no quantum hardware is used.
Across four research protocols (V0 → V2 → V3 → V4) we found that FRQI/NEQR kernels that compare whole images
stay near 60 %, and that a new **patch-ensemble mixed-state kernel** (V4) lifts them to **87.8 ± 1.5 % (FRQI)**
and **82.7 ± 10.1 % (NEQR)**. A classical SVM on the *same patches* reaches 83.6 ± 0.3 % (not significantly
different from FRQI, p = 0.060) and classical texture features reach 95.6 ± 2.2 %. **So: big improvement,
no quantum advantage.** A React + FastAPI dashboard shows every result and replays the final model live.

---

## 1. Repository audit — what exists

### 1.1 Top-level layout

| Path | What it is |
|---|---|
| `api_main.py` | FastAPI application. Hosts the legacy V0 endpoints and mounts the V2/V3/V4 routers. |
| `src/frqi/encoder.py`, `src/neqr/encoder.py` | The real Qiskit circuit builders for FRQI and NEQR. |
| `src/reconstruction/reconstructor.py` | Decoders: turn statevectors or measurement counts back into images. |
| `src/simulation/simulator.py` | Qiskit-Aer wrapper (statevector + shot sampling) used by V0 and the reconstruction study. |
| `src/metrics/evaluator.py` | MSE / PSNR / SSIM (SSIM via scikit-image). |
| `src/preprocessing/image_processor.py` | V0 resize / quantise helpers. |
| `src/ml/trainer.py`, `src/qml/*` | **V0 (historical)** classical trainer (SVM/RF/KNN/DT) and V0 QML code. |
| `src/v2/*` | Protocol V2 engine: dataset & splits, feature pipelines, NumPy statevector simulator, QKC, VQC, CNN/MobileNetV3, runner, result store, API. |
| `src/v3/*` | Protocol V3: texture features (LBP+GLCM), CDF angle view, projected quantum kernel, improved VQC, API. |
| `src/v4/*` | Protocol V4: patch-ensemble mixed-state kernel, classical patch control, API incl. live walkthrough. |
| `scripts/v2/phase*.py` | V2 experiment phases (data protocol, classical, QKC, VQC, FRQI/NEQR, hybrid, analysis). |
| `scripts/v3/*`, `scripts/v4/*` | V3/V4 setup → run → select → freeze → test → analyse → verify; V4 reconstruction study. |
| `results/qml` , `results/models`, `results/experiments` | **V0 historical results** (read-only). |
| `results/qml_v2`, `results/qml_v3`, `results/qml_v4` | Protocol results: manifests, `experiments/<id>/`, `aggregates/`, `reports/`. |
| `frontend/src/v2/pages/*` | Current dashboard pages (V2–V4). |
| `frontend/src/pages/*` | Legacy V0 pages, reachable under `/historical-v0/*`. |
| `tests/` | 179 pytest test functions (encoders, kernels, runner, protection, APIs). |
| `frontend/src/**/*.test.ts(x)` | 27 Vitest tests. |
| `research_paper_visuals/` | Figure/table generators, paper pack, Overleaf project, project-report assets. |

### 1.2 The most important files, one by one

For each: **what · why · called by · input → output · technique · contribution.**

| File | What & why | Called by | Input → Output | Technique |
|---|---|---|---|---|
| `src/v2/dataset.py` | Builds the hashed **manifest** of all 1,800 images and the **group-blocked splits**. Exists so every protocol uses identical, verifiable data. | every provider, V3/V4 setup | NEU-DET folders → manifest JSON (path, class, folder, block, SHA-256), split JSONs per seed | SHA-256 hashing; blocks of 20 consecutive file indices; 3 val blocks/class; seeds 0,1,2 |
| `src/v2/providers.py` | "Feature providers": hand a model the train/val/test arrays for a seed. | `src/v2/runner.py` | seed → `FeatureSet(X, y, paths)` | caching, train-only fitting |
| `src/v2/features.py` | Pixel PCA and vector featurisers with two views: *standard* (z-scored) and *angle* (MinMax to [0, π]). | providers | images/vectors → k-dim features | StandardScaler → PCA → MinMax, all **fitted on train only** |
| `src/v2/qsim.py` | Small batched **NumPy statevector simulator** (H, RY, RZ, P, CX) that mirrors gates into a Qiskit circuit for resource counting. | `qkernel.py`, `vqc.py`, V3 | angles → statevectors | exact matrix algebra; tested against Qiskit to 1e-10 |
| `src/v2/qkernel.py` | **Quantum kernel classifier**: feature maps `product_ry`, `zz_linear`, `zz_full`; fidelity kernel; optional shot noise; SVC. | `scripts/v2/phase4_qkc.py`, `phase7_hybrid.py` | angle features → kernel matrix → SVM predictions | K = \|⟨φ(x)\|φ(y)⟩\|², Binomial shot model |
| `src/v2/vqc.py` | **Variational quantum classifier**: RY encoding, L layers of trainable RY·RZ + CNOT ring, optional re-uploading, 6 expectation readouts, cross-entropy. | `phase5_vqc.py`, `phase7_hybrid.py` | angle features → class probabilities | parameter-shift gradients; Adam / COBYLA / SPSA |
| `src/v2/cnn.py` | `SmallCNN` (trained from scratch) and `FrozenMobileNetV3Source` (576-d features). | `phase3_classical.py`, `phase7_hybrid.py` | images → logits / 576-d vectors | PyTorch; torchvision `mobilenet_v3_small` IMAGENET1K_V1 |
| `src/v2/models_classical.py` | RBF-SVM and logistic regression + their grids. | many phases | features → predictions | scikit-learn |
| `src/v2/frqi_neqr.py` | Whole-image FRQI/NEQR **overlap kernels** in closed form (verified against the circuits), plus honestly relabelled V0 "HQCC"/"VQC". | `phase6_frqi_neqr.py` | images → kernel → SVM | FRQI: [mean cos(θA−θB)]²; NEQR: [fraction of equal codes]² |
| `src/v2/runner.py` | **Experiment runner**: trains every config × seed, selects on validation, freezes, runs the single locked-test evaluation. | all run scripts | ModelSpecs → experiment folders, selection files, test metrics | validation-only selection; `final_evaluation_stage` guard |
| `src/v2/store.py`, `paths.py` | Result store and **write-protection** of historical results. | runner, APIs | — | `assert_writable`, env `QIL_PROTECT_V2/V3` |
| `src/v3/features.py` | Texture descriptors (LBP 54 + GLCM 18 + 4 gradient stats = 76-d), CDF angle view, per-image normalisation. | `scripts/v3/run_v3.py` | 128×128 images → 76-d → PCA | scikit-image LBP/GLCM |
| `src/v3/models.py` | V3 QKC, **projected quantum kernel (PQK)**, VQCv3 (longer training, `zall` readout + controls), FRQI/NEQR *overlap* kernels with optional stretch. | `run_v3.py` | features → predictions | Huang et al. 2021 PQK |
| `src/v4/models.py` | **Patch-ensemble mixed-state kernel** and the **classical patch-moment control**. | `scripts/v4/run_v4.py`, V4 API | images → patches → ρ → Tr(ρAρB) → SVM | density matrices, Hilbert–Schmidt kernel |
| `scripts/v4/run_v4.py` | V4 stages `candidates / select / freeze / test`. | shell (`chain_v4.sh`) | grid → 864 runs → frozen selection → test metrics | SHA-256 freeze |
| `scripts/v4/analyze_v4.py` | 8 pre-declared comparisons. | after test | predictions → `v4_results.json` | sign-flip permutation (10,000), bootstrap CI, McNemar, Holm |
| `scripts/v4/verify_v4.py` | 17 integrity checks. | after analysis | all files → `v4_verification.json` | hash checks, access-log checks |
| `scripts/v4/reconstruct_all.py` | Reconstruction of **all 1,800 images × 20 methods**. | `chain_recon.sh` | images → reconstructions.npz + metrics | real Qiskit circuits + Aer + multinomial shots |
| `src/v4/api.py` | `/api/v4/*`: results, versions, images, per-image models, **live pipeline**, reconstruction. | frontend | HTTP → JSON | read-only; live recompute of the frozen FRQI model |
| `src/v2/api.py`, `api_models.py`, `src/v3/api.py` | `/api/v2/*`, `/api/v3/*` read-only result endpoints. | frontend | HTTP → JSON | — |
| `frontend/src/App.tsx` | Routes, sidebar, header health badge. | browser | — | React Router |
| `frontend/src/v2/api.ts` | `useV2/useV3/useV4` hooks with explicit loading/error/empty states. | all pages | path → `{data, error, loading}` | fetch + AbortController |

---

## 2. Architecture map

```
                         ┌──────────────────────────── DATA ────────────────────────────┐
 NEU-DET/train (1,440)   │ src/v2/dataset.py → manifest (SHA-256 per file)              │
 NEU-DET/validation (360)│   → splits seed 0/1/2: train 1,080 | val 360 (blocked)       │
                         │   → locked test = validation folder (360), read once/model   │
                         └──────────────┬───────────────────────────────────────────────┘
                                        │ providers (train-fitted transforms only)
        ┌───────────────────────────────┼─────────────────────────────────────────────────┐
        ▼                               ▼                                                 ▼
 PIXELS (V2)                    CLASSICAL FEATURES                                 PATCHES (V4)
 resize 2…128 px                 PCA (V2), MobileNetV3 576-d (V2/V3),              64/128 px → p×p patches
 FRQI / NEQR whole image         LBP+GLCM texture 76-d (V3) → PCA k=4..12          stride s, optional stretch
        │                               │                                                 │
        ▼                               ▼                                                 ▼
 QUANTUM ENCODING (simulated)    ANGLE ENCODING (simulated)                         FRQI / NEQR PATCH STATES
 src/frqi, src/neqr  (Qiskit)    qsim.py: product-RY, ZZ maps, VQC circuits         → mixed state ρ (D×D)
        │                               │                                                 │
        ▼                               ▼                                                 ▼
 overlap kernel |⟨IA|IB⟩|²       fidelity / projected kernel, or VQC expectations    Tr(ρA ρB)  (swap-test quantity)
        └──────────────┬────────────────┴──────────────────────────┬──────────────────────┘
                       ▼                                           ▼
             SVC(kernel=precomputed)                     classical controls on IDENTICAL inputs
                       │                                 (RBF-SVM, LogReg, patch-moment SVM)
                       ▼
 src/v2/runner.py: validation selection → SHA-256 freeze → ONE locked-test evaluation → predictions.csv
                       ▼
 analyse (permutation / bootstrap / McNemar / Holm) → aggregates/*.json → verify (17 checks)
                       ▼
 FastAPI (api_main.py + /api/v2 /api/v3 /api/v4, read-only)  ──HTTP JSON──►  React dashboard (frontend/)
                       ▲
 reconstruction study: scripts/v4/reconstruct_all.py (Qiskit circuits + Aer, 1,800 images × 20 methods)
```

---

## 3. Implementation status (verified in code, not inferred from the UI)

| Feature | Status | Evidence |
|---|---|---|
| FRQI / NEQR Qiskit encoders | **Fully implemented** | `src/frqi/encoder.py` (H + X-sandwiched MCRY per pixel), `src/neqr/encoder.py` (H + X-sandwiched MCX per set bit); tests `test_frqi.py`, `test_neqr.py` |
| Reconstruction from statevector / shots | **Fully implemented** | `reconstructor.py`; FRQI arcsin√P, NEQR majority vote; 1,800 × 20 study saved |
| V2 QKC (product-RY, ZZ-linear, ZZ-full) | **Fully implemented** | `qkernel.py`, results in `results/qml_v2` |
| V2 shot-noise kernels | **Implemented (statistical model)** | Binomial(shots, K)/shots per entry; one Aer cross-check in `aer_validation.py` |
| V2/V3 VQC | **Fully implemented** | `vqc.py` (parameter shift, Adam/COBYLA/SPSA) |
| MobileNetV3 features | **Fully implemented, frozen** (no fine-tuning) | `cnn.py` |
| Small CNN | **Fully implemented** | `cnn.py`, E7-smallcnn 93.0 ± 5.9 % |
| Hybrid CNN → PCA → QKC / VQC | **Fully implemented** | `phase7_hybrid.py` |
| V3 texture features, PQK, CDF view | **Fully implemented** | `src/v3/*` |
| V4 patch-ensemble kernel + control | **Fully implemented** | `src/v4/models.py`, 864 runs, 0 failed |
| Swap test on hardware / in simulation | **Not implemented** (described only) | kernel computed exactly as Tr(ρAρB); no swap-test circuit is executed |
| Quantum hardware / noise models | **Not implemented** | none in code |
| Live "How it works" walkthrough | **Fully implemented, read-only** | `/api/v4/pipeline` recomputes and checks against the saved prediction |
| Dashboard V2–V4 pages | **Fully implemented, read-only** | numbers come from API; Vitest asserts this |
| Image upload (V0 Encoding Lab) | **Implemented (legacy V0)** | `POST /api/quantum/compare-custom` encodes an uploaded image with FRQI+NEQR, simulates, reconstructs, returns metrics; not part of V2–V4 claims |
| V0 "run experiment / batch / QML suite" buttons | **Present in UI but disabled** | endpoints return HTTP 409 ("V0 results are immutable") |
| 3×3 Playground | **Illustrative demo** | precomputed JSON (`build_playground*.py`), flagged `illustrative: true` |
| V0 "VQC" and "HQCC" | **Mislabelled in V0** — not quantum | V2 re-ran them as `legacy-softmax` / `encstats-logreg`, labelled classical |
| Random Forest / KNN / Decision Tree | **V0 only (historical)** | `src/ml/trainer.py`, random 70/30 split; not comparable with V2–V4 |

---

## 4. The complete pipeline in plain words

1. **Dataset** — 1,800 grey 200×200 pictures of steel, 300 per defect class. The *validation folder* (360) is
   our **locked test set**: no model sees it until it is frozen.
2. **Preprocessing** — convert to grey, resize (2×2 … 128×128 depending on the model), scale pixels to 0–1,
   optionally *contrast-stretch* each image on its own.
3. **Representation / encoding** — one of: whole-image FRQI/NEQR state; PCA or CNN or texture features turned
   into rotation angles; or (V4) many small patch states mixed into a density matrix ρ.
4. **Model** — almost always an SVM. Quantum models give the SVM a *kernel* (a similarity table); the VQC is the
   exception (it is trained by gradient descent).
5. **Prediction** — the class with the highest SVM vote / VQC probability.
6. **Evaluation** — accuracy and macro-F1 on validation (for choosing) and once on the locked test (for
   reporting), 3 seeds, then paired statistics.
7. **Results** — JSON/CSV files per run and per protocol.
8. **Dashboard** — FastAPI serves those files; React draws them.

---

## 5. Protocol history (why there are versions)

| Version | Question | Key outcome |
|---|---|---|
| **V0** | First prototype: does the pipeline work? | Small runs (~42 train / 12–16 test images), random splits; some models mislabelled. **Kept read-only, not comparable.** |
| **V2** | Fair benchmark with a locked test set: 88 models, 2,583 runs. | Whole-image FRQI 60.6 %, NEQR 60.2 %; pixel QKC 64.0 %; CNN+QKC 93.2 %; MobileNetV3+LogReg 96.4 % (best). |
| **V3** | Better features (texture, CDF angles, PQK, better VQC): 70 groups, 5,316 runs. | Texture-PCA12 + QKC 95.3 % ≈ classical texture SVM 95.6 %; FRQI/NEQR still ≈ 60 %. |
| **V4** | Fix FRQI/NEQR themselves: patch-ensemble mixed-state kernel, 288 configs, 864 runs. | FRQI 87.8 ± 1.5 %, NEQR 82.7 ± 10.1 %; same-patch classical 83.6 ± 0.3 %. |

---

## 6. Discrepancies and caveats found during the audit

These are **not silently fixed**; know them before a viva.

1. **Swap test is described, not run.** The paper/report describe the kernel as "swap-test measurable". The code
   computes Tr(ρAρB) exactly from statevectors. Correct wording: *could be estimated with a swap test*.
2. **V4 FRQI circuit resources use the standard encoder.** `MixedStateEncodingKernelSVC._circuit_stats` builds the
   patch circuit with `src/frqi/encoder.py`, whose angle is `intensity × π` (b = 1). The model uses b = 4. The
   gate *structure* (one multi-controlled RY per non-zero pixel) is identical; only angle values differ, so qubit
   and gate counts are valid, but say so if asked.
3. **NEQR gate counts depend on the image.** One MCX per "1" bit of every pixel code. The paper's Table (NEQR 4×4
   patch: 1,998 compiled gates) and the reconstruction study (2,901) used different sample patches. FRQI counts are
   nearly image-independent (only black pixels are skipped).
4. **Shot-noise classification (V2) is a statistical model.** Each kernel entry is drawn as Binomial(shots, K)/shots;
   this is exactly what an ideal compute–uncompute circuit produces, and one entry type is cross-checked with Aer,
   but full kernels were not run shot-by-shot on Aer.
5. **The locked test set is not fresh for V4.** V2 and V3 used the same test set; V4 was designed after seeing
   their weak FRQI/NEQR results. Within V4, selection was validation-only and testing happened once.
6. **NEQR selected without contrast stretch** had the best validation mean but 3× larger variance; on seed 1 it
   misclassifies every rolled-in-scale image. Explained by a real brightness shift: rolled-in scale mean intensity
   0.496 (train folder) vs 0.329 (test folder).
7. **SVM decision shape.** sklearn `SVC` trains one-vs-one; `decision_function` reports one-vs-rest-shaped scores
   by default. The live walkthrough labels them "ovr scores" — that is the display shape, training is OvO.
8. **V0 labels.** V0 called a fixed softmax regression a "VQC" and a logistic regression on closed-form statistics
   "HQCC". V2 re-ran both and labelled them classical. Never present V0 numbers as quantum results.
9. **"Re-tuned FRQI (V3)" is lower than V2 (57.5 vs 60.6 %).** V3 re-selected FRQI on validation from a wider
   grid; validation was equal (69.4 vs 69.3) but test was lower — normal selection noise, not an error.

---

## 7. Learning path (modules)

1. Repository audit (this file) · 2. Project overview · 3. Fundamentals · 4. Dataset & preprocessing ·
5. Classical ML · 6. MobileNetV3 · 7. Quantum computing fundamentals · 8. FRQI · 9. NEQR · 10. Quantum ML ·
11. Hybrid architectures · 12. Experiments · 13. Circuits · 14. Metrics · 15. Backend · 16. Frontend ·
17. Results · 18. Research paper · 19. Viva.

## 8. Companion documents

| File | Use it for |
|---|---|
| `QUANTUM_COMPUTING_FROM_ZERO.md` | qubits, gates (only those in our code), circuits, kernels |
| `FRQI_NEQR_DEEP_DIVE.md` | encodings with worked 2×2 examples, circuits, decoding, patch-ensemble |
| `MOBILENET_AND_CLASSICAL_ML.md` | CNNs, MobileNetV3-Small in our code, SVM, LogReg, texture features |
| `EXPERIMENTS_EXPLAINED.md` | every experiment family, configs and real results |
| `CIRCUIT_ARCHITECTURE_GUIDE.md` | how to read each circuit, real resource counts |
| `FRONTEND_BACKEND_WALKTHROUGH.md` | every page, button, endpoint and request lifecycle |
| `RESULTS_AND_RESEARCH_DEFENCE.md` | interpretation, limitations, paper cross-check |
| `TECHNICAL_VIVA_QUESTIONS.md` | 150 questions with answers |
| `QUICK_REVISION_CHEATSHEET.md` | formulas, numbers, configs on one page |
