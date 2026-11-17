# Q-ImageLab Protocol V2 — Implementation Report

Overall status: **PASS** — all ten phases passed their acceptance gates; limitations are listed in §6.
Dates: 2026-11-13 → 2026-11-14. Results: `results/qml_v2/`. Findings: `EXPERIMENT_RESULTS.md`.

## 1. Architecture changes
- New package `src/v2/` (Protocol V2), independent of V0 code paths:
  `paths` (env-configurable dataset/results roots + historical write guard) · `dataset` (manifest, validation,
  blocked group splits, locked-test loader with logged `final_evaluation_stage`) · `features` / `providers`
  (train-only PCA/scaler pipelines, cached per seed) · `metrics` (six-label metrics, bootstrap CIs) · `store` / `runner`
  (experiment schema, candidate → validation selection → single locked-test evaluation, resume, failure records) ·
  `models_classical`, `cnn` (small CNN, frozen MobileNetV3) · `qsim` (batched statevector simulator, Qiskit-verified,
  circuit recording + common transpilation) · `qkernel` (product-RY / ZZ fidelity kernels, diagnostics, shot sampling,
  Aer validation) · `vqc` (genuine VQC, parameter-shift / COBYLA / SPSA) · `frqi_neqr` (original-encoding overlap
  kernels, relabelled legacy models) · `encoding_study` (reconstruction study) · `api` (read-only `/api/v2`).
- V0 code kept and protected: read-only by default, legacy writers guarded, V0 launch endpoints return 409.
- Frontend: new Experiments V2 page; V0 pages stripped of fabricated values and labelled Protocol V0.

## 2. Files
### Created
`src/v2/{__init__,paths,dataset,features,metrics,store,runner,providers,models_classical,cnn,qsim,qkernel,vqc,frqi_neqr,encoding_study,api}.py`
`scripts/v2/{verify_historical,phase1_data_protocol,common,phase3_classical,phase4_qkc,phase5_vqc,phase6_frqi_neqr,phase7_hybrid,phase8_analysis,aer_validation}.py`, `scripts/v2/run_quantum_chain.sh`, `scripts/v2/run_quantum_chain_resume.sh`
`tests/test_v2_{protection,data,runner,qsim,vqc,frqi_neqr,encoding,api}.py`
`frontend/src/pages/ExperimentsV2.tsx`, `frontend/src/pages/ExperimentsV2.test.tsx`, `frontend/src/lib/v2.ts`, `frontend/src/lib/v2.test.ts`, `frontend/vitest.config.ts`
`results/qml_v2/**` (all v2 outputs, manifests, logs, reports)

### Modified by this work
| File | Change |
|---|---|
| `src/qml/experiment_manager.py` | injectable results root, read-only by default for `results/qml`; no manifest rewrite on read; hardcoded classical/gate/depth/reconstruction fallbacks removed (resources now measured on real circuits) |
| `src/qml/frqi_qml.py`, `src/qml/neqr_qml.py` | shot-kernel bug fixed (double measurement; read `["counts"]`) |
| `src/ml/trainer.py`, `src/metrics/evaluator.py`, `src/visualization/plotter.py` | historical write guard before every file write |
| `config/settings.py` | removed silent `~/Downloads/NEU-DET-2` switch; `QIL_DATASET_PATH` override |
| `api_main.py` | `/api/v2` router mounted; V0 launch/delete endpoints → 409 |
| `tests/test_qml.py` | persistence tests on `tmp_path`; read-only test; NEQR-feature test corrected to what the features actually are |
| `frontend/src/App.tsx` | `/experiments-v2` route + sidebar entry; "3,632 Runs" badge → "Protocol V0" |
| `frontend/src/pages/QuantumMLLab.tsx` | fabricated benchmark section, model cards, numeric fallbacks and "quantum kernel advantage" claim removed; V0 banners |
| `frontend/package.json`, `package-lock.json` | Vitest/Testing Library/jsdom dev deps; `test` script |
| `requirements.txt` | torch 2.15.0, torchvision 0.29.2, httpx 0.28.1 pinned |

Several of these files (`api_main.py`, `config/settings.py`, `src/metrics/evaluator.py`, `frontend/src/App.tsx`,
`frontend/package.json`, and the untracked `src/qml/*`, `tests/test_qml.py`, `QuantumMLLab.tsx`) already had
uncommitted changes before this work. Uncommitted changes present before this work and **not** touched:
`frontend/index.html`, `frontend/src/pages/Dashboard.tsx`, `frontend/tsconfig.app.json`, `frontend/vite.config.ts`,
`results/experiments/all_results.csv` (that file is part of the hashed historical set and is unchanged since hashing).
Nothing was committed.

## 3. Dependencies
Python (venv, Python 3.11.0): + torch 2.15.0, torchvision 0.29.2 (pulled sympy 1.14.0, mpmath 1.3.0, filelock 4.2.10,
fsspec 2026.9.0; setuptools → 84.2.1), + httpx 0.28.1. numpy 2.4.6, scipy 1.17.1, qiskit 2.5.2, qiskit-aer 0.17.2,
scikit-learn 1.9.1 unchanged. Full freeze: `results/qml_v2/manifests/pip_freeze_v2.txt`.
Frontend dev: vitest ^5.1.0, @testing-library/react ^16.3.3, @testing-library/dom ^10.4.2, jsdom ^31.0.1.
MobileNetV3-small IMAGENET1K_V1 weights (SHA-256 047dcff4…; first download needed `SSL_CERT_FILE` = certifi bundle).

## 4. Phase status
| Phase | Status | Report |
|---|---|---|
| 0 Baseline & preservation | PASS | PHASE0_BASELINE.md |
| 1 Data protocol | PASS | PHASE1_DATA_PROTOCOL.md |
| 2 Runner & schema | PASS | PHASE2_RUNNER.md |
| 3 Classical & CNN | PASS | PHASE3_CLASSICAL.md |
| 4 PCA + QKC | PASS | PHASE4_QKC.md |
| 5 Genuine VQC | PASS | PHASE5_VQC.md |
| 6 FRQI / NEQR | PASS | PHASE6_FRQI_NEQR.md |
| 7 Hybrid | PASS | PHASE7_HYBRID.md |
| 8 Analysis | PASS | PHASE8_ANALYSIS.md |
| 9 Dashboard | PASS (not visually inspected in a browser) | PHASE9_DASHBOARD.md |

## 5. Tests (final run, 2026-11-14)
- `python -m pytest -q tests` → **155 passed** (baseline before this work: 95 passed, 1 failed; the failing test was
  corrected to assert the true behaviour of the legacy features, see PHASE5/6).
- `cd frontend && npx vitest run` → 10 passed; `npx tsc -b --noEmit` → clean; `npx oxlint` → 0 errors; `npx vite build` → ok.
- End-to-end: 2,583 experiments + 16 reconstruction records produced by the runner, aggregated, served by `/api/v2`
  and checked against saved files.
- Historical verification: 16 checks, all 0 changed / 0 missing / 0 added (HISTORICAL_PRESERVATION_REPORT.md).

### Final acceptance checklist
Historical safety ✔ (hashes identical; no v2 output in v0 dirs; checkpoints unchanged) · Data integrity ✔ (6 classes,
locked test, no train/val/test overlap by path/hash/group, train-only preprocessing) · Model integrity ✔ (classical
baselines, small CNN, MobileNetV3 with pretrained weights loaded, genuine QKC and VQC, FRQI/NEQR, hybrids labelled,
V0 labels corrected) · Metric integrity ✔ (predictions-based, six labels, real image pairs, one gate-count method, no
hardcoded metrics or advantage claims in production views) · Experiment integrity ✔ (configs, seeds, manifests saved;
0 failed runs, superseded artefacts preserved; test used only in the final stage — 2 exact-reproduction repeats
disclosed) · Dashboard integrity ✔ (reads v2 files, empty/failed states, filters, genuine curves/matrices/circuits/
images, V0 separate) · Engineering ✔ (backend, frontend, integration tests and type checks pass).

## 6. Known limitations and unresolved issues
1. Dashboard verified by component tests and live API calls on real data, not by a manual browser session.
2. Grouping uses file-index blocks (no acquisition metadata exists); residual val→train adjacency 0.8–2.2%; a
   train-folder → test-folder difficulty gap remains (validation scores exceed test scores for pixel models).
3. Some selected hyperparameters lie at grid edges; grids were not widened after test results existed.
4. Shot-based kernels use validated Binomial sampling (Aer-checked on real features), not full Aer execution of every
   entry; no noise models; no hardware. VQC uses exact expectation values (no shot-based training).
5. Wall-clock `duration_s` includes periods when the Mac slept; training/inference times use `perf_counter` (sleep
   excluded). CNN timings were inflated by concurrent jobs.
6. Two locked-test re-evaluations occurred on resume (identical results); runner fixed + regression test.
7. 16 unit-test fixture rows remain in historical `results/qml/qml_experiments.csv` (immutable); flagged in the V0 view.
8. Legacy V0 pages still exist for historical browsing; their remaining charts show V0 data as saved (with banners).
9. Long runs need the Mac awake: `run_quantum_chain_resume.sh` runs under `caffeinate -i` (lid-close sleep on battery
   still pauses it).
