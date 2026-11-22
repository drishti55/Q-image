# Phase 9 — Dashboard Integration

Status: **PASS** (one verification limitation, stated below)

## Backend
- `src/v2/api.py` — read-only FastAPI router mounted at `/api/v2` in `api_main.py`:
  `/overview`, `/dataset`, `/experiments` (filters: family, code, group, n_qubits, n_layers, optimizer, shots, seed,
  status, selected, feature substring), `/experiments/{id}`, `/experiments/{id}/predictions`, `/selections`,
  `/selections/{group}`, `/comparison` (selected configs, mean ± std val/test), `/analysis`, `/reconstructions`,
  `/reconstructions/{id}`, `/reconstructions/{id}/image/{name}` (path-traversal guarded), `/historical`.
  Every value is read from files; missing values are `null`.
- Legacy endpoints that would launch or delete Protocol V0 runs (`POST /api/qml/run`, `/api/qml/suite/run`,
  `/api/qml/suite/resume`, `/api/quantum/batch/run`, `DELETE /api/qml/experiment/{id}`) now return **409** with an
  explanation instead of writing into `results/`. Read endpoints are unchanged.
- Hardcoded/fabricated fallbacks removed from `src/qml/experiment_manager.py`: classical metric fallbacks (two
  places), gate/depth chart fallbacks, hardcoded reconstruction-panel gate counts (now measured on the actual circuits,
  logical + compiled), static qubit table (now computed from the encoding formulas for resolutions present).

## Frontend
- New page `frontend/src/pages/ExperimentsV2.tsx` (route `/experiments-v2`, sidebar "Experiments V2 (locked test)")
  with the 10 required sections: Dataset, Experiments (history + filters), Model comparison (selected configs,
  error bars, category filter, links to experiment ids), Training studio (saved loss/accuracy curves, quantum gradient
  norms), Confusion matrix (val + locked test, side-by-side comparison), Per-class (P/R/F1/support, misclassification
  targets, bootstrap CI), Circuit explorer (logical vs compiled gates, depth, 2-qubit/CX counts, shots, mode),
  Reconstruction studio (saved PNGs, metrics per shot mode), Experiment details (config, provenance, error trace),
  Historical (V0, labelled "Historical Results — Protocol V0", with provenance warnings, never merged).
  Empty states ("No experiment results available.") and failed-run states throughout.
- `frontend/src/lib/v2.ts` — formatting helpers that render missing values as "unavailable", filters, categories.
- `QuantumMLLab.tsx` (V0 page): removed the hardcoded "benchmark verdict" section (fixed 76.6% / 51.1% numbers and the
  unsupported "quantum kernel advantage" claim), the hardcoded model cards, all numeric fallbacks (gate counts 1092/705/
  384/136/96/68, image count 1800, support 60, model tables, all-zero confusion matrix); V0 sections now carry a
  Protocol V0 banner and link to Experiments V2. `App.tsx`: the hardcoded "3,632 Runs" sidebar badge (which counted
  per-image records and test fixtures as runs) replaced by "Protocol V0".

## Tests
- `tests/test_v2_api.py` (5): empty results → no-data responses; endpoints return saved records (counts, failure
  traces, comparison means equal the saved test metrics, predictions, filters); image path traversal blocked;
  historical endpoint separate and flags 16 fixture rows; V0 launch/delete endpoints refuse with 409.
- `frontend/src/lib/v2.test.ts` + `frontend/src/pages/ExperimentsV2.test.tsx` (Vitest + Testing Library, 10 tests):
  missing → "unavailable" (a real 0 still shows 0), every filter, empty state shows no numbers, comparison rows from
  API, failed experiments listed and filterable, failure reason in details, historical section separate, reconstruction
  images load from the saved-artefact URL.
- Live check against the real results (FastAPI TestClient): overview 1,433 → (final) 2,583 experiments, dataset manifest
  + split integrity, comparison rows, CNN training curve (27 epochs), 6×6 confusion matrices, circuit stats, historical
  counts (30 paired / 3,600 per-image / 16 fixtures); historical hashes unchanged afterwards.
- `npx tsc -b --noEmit` clean; `npx oxlint` 0 errors (warnings pre-existing); `npx vite build` succeeds.

## Limitation
The page was verified by component tests (mocked API) and by live API calls on real data, but I did not open it in a
browser in this session (no browser tool available). Launch: `python api_main.py` and `cd frontend && npm run dev`,
then open http://localhost:5173/experiments-v2.

## Dev dependencies added (frontend)
vitest ^5.1.0, @testing-library/react ^16.3.3, @testing-library/dom ^10.4.2, jsdom ^31.0.1; `npm test` script.
