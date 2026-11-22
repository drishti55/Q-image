# Phase 0 — Repository Baseline and Preservation

Date: 2026-11-13. Status: **PASS**

## 1. Existing architecture (as found)

- Backend: FastAPI monolith `api_main.py` (~1,500 lines). Legacy reconstruction endpoints (`/api/quantum/*`),
  classical ML read endpoints (`/api/ml/*`, `/api/models/*`), QML endpoints (`/api/qml/*`) backed by
  `src/qml/experiment_manager.py::QMLExperimentManager`.
- Frontend: React 19 + Vite + Recharts (`frontend/src/pages/*.tsx`, routes in `frontend/src/App.tsx`).
- Quantum code: `src/frqi/encoder.py`, `src/neqr/encoder.py` (Qiskit circuit builders),
  `src/reconstruction/reconstructor.py`, `src/simulation/simulator.py` (Aer wrapper),
  `src/qml/{frqi_qml,neqr_qml,models,quantum_kernel,feature_extractor,classifier,reconstruction_eval}.py`.
- Classical ML: `src/ml/trainer.py` (64×64 raw pixels, StandardScaler, SVM/RF/KNN/DT; writes `results/models`).
- Legacy reconstruction study: `src/experiments/runner.py` (writes `results/experiments`, `results/images`).
- Environment: project venv `.venv`, Python 3.11.0, qiskit 2.5.2, qiskit-aer 0.17.2, scikit-learn 1.9.1,
  scikit-image 0.26.0, fastapi 0.142.2. torch/torchvision NOT installed. httpx NOT installed.

### Experiment entry points
`main.py`, `run_all_experiments.py` (legacy reconstruction), `src/ml/trainer.py::run_full_ml_pipeline`,
`src/qml/run_matrix_pipeline.py`, API: `POST /api/quantum/batch/run`, `POST /api/qml/run`,
`POST /api/qml/suite/run|resume`.

### Result-writing code paths into historical directories (all identified)
| Writer | Target |
|---|---|
| `QMLExperimentManager._init_csv/_persist_experiment/delete_experiment/run_full_dataset_pipeline` | `results/qml/*` |
| `QMLExperimentManager.discover_dataset` (called by GET `/api/qml/overview`) | rewrote `results/qml/dataset_manifest.json` on **every dashboard overview load** |
| `tests/test_qml.py::TestExperimentPersistence` | appended `test001`/`fail001` rows to `results/qml/qml_experiments.csv` |
| `src/ml/trainer.py` (10 write sites) | `results/models/*`, `results/dataset/*` |
| `ResultsManager.save_results_csv/json`, `ResultsPlotter.*` (via `ExperimentRunner`, `/api/quantum/batch/run`) | `results/experiments/*`, `results/images/*` |

## 2. Working / broken / partial (verified against code)
- Working: FRQI/NEQR circuit construction; statevector + shot reconstruction; classical trainer pipeline.
- Broken: shot-mode QKC kernel (returns 0 for identical inputs — reproduced); `run_full_dataset_pipeline`
  (`KeyError: 'class'` at the manifest lookup — manifest has `ground_truth`); test isolation.
- Mislabelled: "VQC" = 15-step classical softmax on fixed features; HQCC "observables" are classical pixel
  statistics (baseline test failure: NEQR "expectation values" reach 2.5, outside [-1, 1]).
- Partial/disconnected: PCA + ZZFeatureMap QKC (`classifier.py`) has no caller.

## 3. Baseline test status (before any change)
- Python: `pytest` executed on an isolated **copy** of the code (scratch directory) because
  `tests/test_qml.py` writes into the real results directory → **95 passed, 1 failed**
  (`test_qml.py::TestNEQRQMLPipeline::test_neqr_quantum_features`). The copy's results dir received
  `results/qml/*` files, confirming the unsafe writes.
- Frontend: `npx tsc -b --noEmit` → exit 0. `npx oxlint` → warnings only, no errors.
- No frontend test runner is configured (`package.json` has no test script).

## 4. Historical preservation
- Manifest: `results/qml_v2/manifests/historical_preservation_manifest.json`
  (SHA-256 of the manifest file itself: `1f0175481797f71cc712efbbecc126697eeafba5694f809b56d351be220572c7`).
- Scope: every file under `results/` except `results/qml_v2/` → **3,690 files**.
  - `results/qml`: 3,652 files (3,639 JSON; `qml_experiments.csv` 3,646 data rows).
  - `results/models`: 14 files (6 JSON; `model_comparison.csv` 4 rows, `per_class_metrics.csv` 24 rows,
    `hyperparameter_results.csv` 27 rows).
- Verifier: `python scripts/v2/verify_historical.py --label <phase>` (appends to
  `results/qml_v2/logs/historical_verification.jsonl`). Phase 0 result: changed=0, missing=0, added=0.

## 5. Phase 0 changes
| File | Change |
|---|---|
| `src/v2/__init__.py`, `src/v2/paths.py` (new) | `QIL_DATASET_PATH`, `QIL_RESULTS_V2`, `assert_writable()` guard (refuses writes under `results/` outside `results/qml_v2` unless `QIL_ALLOW_V0_WRITES=1`). |
| `src/qml/experiment_manager.py` | Injectable `results_root`; **read-only by default when pointing at `results/qml`**; `discover_dataset` no longer persists into the historical dir. |
| `src/ml/trainer.py`, `src/metrics/evaluator.py`, `src/visualization/plotter.py` | `assert_writable()` before every file write. |
| `tests/test_qml.py` | Persistence tests use `tmp_path`; new read-only test. |
| `tests/test_v2_protection.py` (new) | Guard tests. |
| `scripts/v2/verify_historical.py` (new) | Hash verifier. |

## 6. Dependency changes required (later phases)
torch + torchvision (CPU) for Phase 3/7 (approved). httpx (FastAPI TestClient) for API integration tests.

## 7. Risks to historical data
- Legacy POST endpoints that launch v0 experiments now fail with a read-only error instead of writing
  (intended; documented in Phase 9).
- The v0 classical trainer / legacy reconstruction runner cannot rewrite their outputs without
  `QIL_ALLOW_V0_WRITES=1`.
