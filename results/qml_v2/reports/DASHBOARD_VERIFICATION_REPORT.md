# Dashboard Verification Report

Date: 2026-11-15 (updated after the UX redesign). Overall: **PASS** — real-browser checks 49/49 passed
(5 consecutive full runs, backend alive throughout), backend tests 164/164, frontend tests 12/12, type check clean, lint 0 errors,
production build OK, historical hashes identical.

## 1. Real browser testing (not mocked)
- Stack exactly as in `RUN.txt`: FastAPI backend `python api_main.py` (:8000, restarted on the new code) + Vite dev server (:5173,
  `/api` proxy). Browser: installed Google Chrome driven headless by Playwright (installed in an isolated scratch virtualenv, not a
  project dependency). Repeatable: `python scripts/v2/dashboard_e2e.py`.
- All pages loaded against the real `results/qml_v2` data; console errors and failed `/api` responses recorded on every page (none).

| Check | Result | Detail |
|---|---|---|
| / opens the Protocol V2 overview | PASS |  |
| overview counts come from /api/v2/summary | PASS |  |
| sidebar is short (≤ 12 links incl. logo) | PASS | 11 links |
| best overall accuracy displayed | PASS | 96.4% |
| best purely quantum accuracy displayed | PASS | 64.0% |
| no V0 KPI text on V2 overview | PASS |  |
| simulation disclaimer shown | PASS |  |
| /experiments-v2 shows V2 runs + split integrity | PASS |  |
| status filter offers only statuses present in the data | PASS | options=['All', 'completed'] |
| experiments seed filter works | PASS | seeds shown=['1'] |
| experiment detail page opens from history | PASS | E1-frqi16-qkc__08c086c77b__s0 |
| browser refresh on deep link /experiments/:id works | PASS |  |
| leaderboard (default) ranks the best model first | PASS | Frozen MobileNetV3 + Logistic Regression |
| leaderboard shows top 12 by default | PASS | 12 rows |
| leaderboard family filter | PASS | expected 9 |
| model comparison lists all 88 configurations | PASS |  |
| table row count equals API count | PASS | rows=88 |
| every configuration name rendered | PASS | missing=[] |
| default sort = test accuracy descending | PASS | 96.4 ± 1.1% |
| search filters configurations | PASS | expected 18 |
| family filter works | PASS | expected 6 |
| exact vs finite-shot filter works | PASS | expected 18 |
| qubit filter works | PASS | expected 15 |
| side-by-side comparison opens | PASS |  |
| row expands to seed-wise results | PASS |  |
| encoding page shows FRQI and NEQR sections + comparison | PASS |  |
| encoding page uses recorded compiled gate counts | PASS |  |
| circuit diagram renders | PASS |  |
| selected circuit matches executed experiment | PASS |  |
| logical gate count of executed circuit displayed | PASS |  |
| reconstruction images load (original/reconstructed/diff × 2 records) | PASS | 6/6 |
| scratches image (index 29) available | PASS |  |
| classification shows confusion matrix, per-class and seed-wise | PASS |  |
| weak-class panel shown | PASS |  |
| /historical-v0 opens labelled read-only V0 | PASS |  |
| V0 pages carry the historical banner | PASS |  |
| breadcrumb marks V0 pages | PASS |  |
| old V0 URL redirects into /historical-v0 (query kept) | PASS | http://127.0.0.1:5173/historical-v0/qml-lab?tab=models |
| presentation slide 1 shows a real sample image for every class | PASS | 6 images |
| presentation renders full-screen (no sidebar) | PASS |  |
| arrow key advances to slide 2 | PASS |  |
| results slide shows best accuracies from the API | PASS |  |
| encoding slide shows real reconstructions | PASS | 4 images |
| Escape exits the presentation | PASS |  |
| sidebar navigation works | PASS |  |
| mobile viewport: no horizontal page overflow | PASS |  |
| mobile navigation drawer opens | PASS |  |
| no console errors on any page | PASS |  |
| no failed /api requests | PASS |  |

## 2. Screenshots (`results/qml_v2/reports/dashboard_screenshots/`)
| File | Content |
|---|---|
| `before_experiments-v2.png`, `before_experiments-v2_stale_backend.png` | before: V2 inside V0 chrome; with a pre-V2 backend only 404 errors |
| `01_v2_overview.png` | story-first V2 overview (full page) |
| `02_experiment_detail.png` | run detail after a browser refresh on the deep link |
| `03a_model_leaderboard.png` | Model Comparison default leaderboard |
| `03_model_comparison.png` | Advanced view: 2 models side by side, expanded seed-wise row |
| `04_quantum_encoding.png` | FRQI vs NEQR at a glance + charts |
| `05_circuit_explorer.png` | 8-qubit ZZ-full feature-map circuit of the selected experiment |
| `06_reconstruction_studio.png` | NEQR 8×8 4-bit vs FRQI 8×8, Scratches image, 1,000 shots |
| `07_classification.png` | classification analysis |
| `08_historical_v0.png` | historical V0 landing page |
| `09_mobile_overview.png` | 390-px mobile viewport, navigation drawer |
| `10_presentation_slide1.png`, `12_presentation_encoding.png`, `11_presentation_results.png` | presentation slides 1, 3, 5 |
Visual review of the screenshots led to fixes: clipped chart label, circuit-page overflow, sub-10 ms train times shown as 0.00 s,
and (presentation) screenshot timing during fade-in. Charts animate when drawn; full-page captures can catch lines mid-animation.

## 3. Backend and data
`tests/test_v2_dashboard_api.py` (9 tests; real-data tests read-only): `/api/v2/models` = exactly the 88 groups of
`aggregates/analysis.json` with identical metrics and experiment ids; no V0 experiment id anywhere in V2 responses; best-model values
equal the maxima recomputed from the analysis file; all circuit artefacts load and match recorded gate counts (deterministic circuits);
reconstruction images render for all 30 images; V0 endpoint still serves V0 data with no V2 group; empty results → explicit no-data
responses; API uses object (not pyarrow) strings; dataset sample images are train-folder only with 404 for invalid requests.

## 4. Stability incident and fix
During repeated browser runs the backend process died. With `-X faulthandler` the cause was captured: segfault in
`pyarrow/compute.py:take` reached from `pandas` filtering in the V0 endpoint `get_reconstruction_details` under concurrent requests.
Fixed by disabling pyarrow string inference in the API process (values verified identical). Before the fix: crash on the 2nd full run;
after: 5 consecutive full runs, backend alive. An earlier crash of Qiskit circuit construction inside the API process is avoided by
building circuit artefacts offline (`scripts/v2/build_circuit_artifacts.py`).

## 5. Frontend tests (`npm test`, mocked API)
12 passed: `/` renders the V2 story overview with numbers only from the API (no V0 figures); stale-backend banner on `/api/v2` 404;
empty state; `/historical-v0` labelled read-only; old V0 URL redirect keeps the query; not-found page; model filters and sorting;
formatting never invents numbers.

## 6. Historical and V2 data preservation
`verify_historical.py`: before (`dashboard-redesign-before`) and after (`dashboard-redesign-after`, `ux-redesign-after`) — 3,690 files,
0 changed / missing / added. No file in `results/qml_v2/{experiments, aggregates, reconstructions, manifests}` is newer than
`aggregates/analysis.json` (2026-11-14 20:28): no V2 experiment output modified; no experiments re-run.

## 7. Not verified / limitations
Only Chrome (headless) tested. Chart hover tooltips exercised indirectly. Lint warnings remain (fast-refresh hints, pre-existing V0).
