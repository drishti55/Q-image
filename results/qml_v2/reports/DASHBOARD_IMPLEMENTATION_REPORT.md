# Dashboard Implementation Report — Protocol V2 as the primary experience

Date: 2026-11-14. Root-cause analysis: `DASHBOARD_AUDIT.md`. Verification: `DASHBOARD_VERIFICATION_REPORT.md`.

## 1. Root cause (summary)
The V2 page itself rendered V2 data, but the application was V0-first and made V2 look like V0 or fail silently:
1. `/` was the V0 home; 11 of 14 navigation links were V0; old `/circuit` and `/reconstruction` redirected into V0.
2. The V2 page sat inside V0 chrome: header title "Dashboard", hardcoded V0 figures ("1,800 Images Ready", badges
   "3,632", "3.6k", "7 Models", "11 Models", "15"), "Backend Online" from the V0 `/api/status`.
3. The V2 page opened on a comparison sorted by internal id, whose first rows were FRQI kernels and relabelled
   legacy V0 methods, without human-readable names; it also contained a "Historical (V0)" tab.
4. A backend started before the V2 router existed returns 404 for every `/api/v2` call: the V2 page showed only error
   boxes while the V0 shell kept working (reproduced in a real browser).
No V0 record was ever rendered by the V2 page and no data source was mixed.

## 2. New navigation
```
Q-ImageLab                         (sidebar, every page; breadcrumb "Protocol V2 › <page>")
  PROTOCOL V2 · CURRENT
    Overview                 /
    Experiments V2           /experiments-v2        (+ /experiments/:id details)
    Model Comparison         /models                (?focus=<group> deep links)
    Quantum Image Encoding   /encoding
    Quantum Circuits         /circuits              (?id=<experiment_id>)
    Reconstruction Studio    /reconstruction
    Classification Analysis  /classification        (?model=<group>)
  HISTORICAL · V0 · READ-ONLY
    Historical Results (V0)  /historical-v0
    V0 Home, V0 Quantum ML Lab, V0 Classical Analytics, V0 Confusion Matrix, V0 Classical Comparison,
    V0 Quantum Image Lab, V0 Encoding Lab, V0 Batch Lab, Dataset Browser     /historical-v0/<page>
  Settings                   /settings
```
Every V0 page is wrapped in a "Historical Results — Protocol V0 (read-only)" banner; the header shows a
"Protocol V0 · read-only" pill and the breadcrumb root "Historical V0". Old URLs redirect (query string kept):
`/quantum-ml-lab`, `/ml`, `/confusion-matrix`, `/compare`, `/quantum`, `/quantum-compare-lab`, `/dataset` →
`/historical-v0/...`; `/circuit` → `/circuits`; `/experiments` → `/experiments-v2`; unknown paths → "Page not found".
V0 pages' internal links were repointed to `/historical-v0/...` (only paths changed), so V0 never links into V2.

## 3. Backend API (new: `src/v2/api_models.py`, mounted in `api_main.py`)
| Endpoint | Source | Purpose |
|---|---|---|
| `GET /api/v2/health` | results/qml_v2 | version + presence of analysis → shell detects a stale/old backend |
| `GET /api/v2/summary` | analysis.json, manifests, reconstructions | overview counts, best models (computed), family comparison, findings generated from paired tests |
| `GET /api/v2/models` | analysis.json + experiments/*/status.json + circuit_stats.json | all 88 selected configurations: readable name, category, feature source, encoding, execution (classical / exact statevector / finite shots), metrics mean±std, per-seed val/test + CI, circuit resources |
| `GET /api/v2/models/{group}` | + test/validation metrics, confusion matrices, selection file | details for one configuration |
| `GET /api/v2/per-class` | test_metrics.json | per-class F1 (seed mean) for every configuration |
| `GET /api/v2/circuits`, `/circuits/{id}` | circuits/*.json | circuit configurations executed by selected quantum models; per-experiment artefact |
| `GET /api/v2/reconstructions/{id}/images` | metrics.json | all 30 evaluated images with per-mode metrics |
| `GET /api/v2/reconstructions/{id}/render/{k}/{mode}/{kind}.png` | reconstructions.npz + dataset | original / reconstructed / difference image rendered from the saved arrays |
Existing `/api/v2/*` endpoints (`overview`, `dataset`, `experiments`, `experiments/{id}`, `reconstructions`, `historical`)
are unchanged.

Backend corrections made during implementation:
- **Circuit artefacts are built offline.** Building Qiskit circuits inside the API process segfaulted
  (`QuantumCircuit.__init__`, only with the full `api_main` import set; not with a larger thread stack). The new script
  `scripts/v2/build_circuit_artifacts.py` rebuilds each executed circuit in a clean process from the experiment's saved
  checkpoint (first training image of its split; trained θ for VQCs; CNN-feature VQCs use the real cached MobileNet
  features) and writes `results/qml_v2/circuits/<experiment_id>.json` (33 files). The API only reads them.
  Logical gate counts equal the counts recorded during the experiments for every deterministic circuit; NEQR counts
  differ by a few gates because they depend on pixel bits (recorded value = mean over 5 images; labelled in the UI).
- **Reconstruction images for all 30 images.** The study saved PNGs for only 5 of 30 images (no Scratches image).
  Instead of re-running, the API renders images from the saved `reconstructions.npz` arrays.

## 4. How V2 data reaches the screen
`results/qml_v2/{aggregates/analysis.json, experiments/*, reconstructions/*, circuits/*, manifests/*}` →
`src/v2/api_models.py` / `src/v2/api.py` (read-only, cached by file mtime) → `/api/v2/*` →
`frontend/src/v2/api.ts::useV2()` (fetch with explicit loading / error / data states; no fallbacks; 404 errors explain
how to restart an old backend) → page components in `frontend/src/v2/pages/*`. No V0 endpoint is called by any V2
page (the shell's health check is `/api/v2/health`).

## 5. How all 88 configurations are displayed
`/models` renders one row per configuration returned by `/api/v2/models` (88 rows; verified equal to
`analysis.json → selected`), with search (name/id), filters (family/category, qubits, feature representation,
encoding, execution: exact statevector / finite shots / classical), sorting (accuracy, macro-F1, name, qubits),
expandable rows (per-seed validation/test metrics, bootstrap CIs, links to each experiment, selected parameters,
circuit resources, timing) and side-by-side comparison of up to 4 models (table + chart). Finite-shot rows carry an
amber badge; relabelled legacy V0 methods carry a "legacy · classical" badge; ablations a red badge.
Categories: Classical (24, incl. relabelled legacy methods), Quantum kernel (21), FRQI/NEQR encoding kernels (25),
Variational quantum (6, incl. ablations), Hybrid CNN + quantum (12).

## 6. Pages
- Overview (`/`): headline, protocol, simulation disclaimer; 8 count cards; best overall / purely quantum / hybrid /
  classical-pixel models (computed — ties shown); family comparison chart + table; 6 generated findings.
- Experiments V2: dataset manifest, split integrity per seed (overlaps, near-duplicate rates), class distribution;
  all 2,583 runs with filters; run detail page (training curves, val/test confusion matrices, per-class, provenance,
  error trace, link to its circuit).
- Quantum Image Encoding: FRQI and NEQR methodology; per-resolution/precision tables (qubits, logical→compiled
  gates, depth, CX, MSE exact / 10³ / 10⁵ shots, SSIM, classification accuracy); compiled-gate, accuracy and
  MSE-vs-shots charts; data-generated FRQI-vs-NEQR statements.
- Quantum Circuits: 33 executed circuit configurations; SVG wire diagram drawn from the actual gate sequence;
  logical and compiled counts; entanglement pairs; feature-map parameters; measurement configuration; Qiskit text
  drawing for small circuits; models using each circuit.
- Reconstruction Studio: record × image (all 30) × measurement mode, optional second record side by side; original /
  reconstructed / difference; MSE, PSNR (∞ for exact), SSIM (+ method), NEQR vs its quantised image and
  quantisation-only error; explanation of exact vs finite-shot reconstruction.
- Classification Analysis: any configuration; metrics, per-class P/R/F1, confusion matrix per seed, seed-wise table
  with CIs; weak-class panel (rolled-in scale / inclusion F1 for every model, pixel vs CNN inputs).
- Historical Results (V0): warnings, V0 counts, links to all V0 pages, V0 paired-run table as saved.

## 7. Files
Created: `src/v2/api_models.py`, `scripts/v2/build_circuit_artifacts.py`, `scripts/v2/dashboard_e2e.py`,
`tests/test_v2_dashboard_api.py`, `frontend/src/v2/{api.ts, ui.tsx, v2.test.tsx}`,
`frontend/src/v2/pages/{Overview, Experiments, ExperimentDetail, Models, Encoding, Circuits, Reconstruction,
Classification, HistoricalHome}.tsx`, `results/qml_v2/circuits/*.json` (33, derived), reports + screenshots.
Modified: `api_main.py` (mount router), `frontend/src/App.tsx` (rewritten shell + routes),
`frontend/src/pages/{Dashboard, Comparison, DatasetExplorer}.tsx` (internal link paths only).
Removed: `frontend/src/pages/ExperimentsV2.tsx` and its test (the earlier single-page V2 view, superseded by the
pages above; not V0 code). No V0 page implementation or V0/V2 result file was deleted or modified.

## 8. Limitations
- The development server (Vite) and backend must both run; an old backend is detected and explained, not fixed.
- Circuit artefacts must be rebuilt (`python scripts/v2/build_circuit_artifacts.py`) if new quantum experiments are added.
- Large circuits (FRQI/NEQR ≥ 8×8, up to 72,713 logical gates) are drawn for their first 160 gates; counts always
  refer to the full circuit.
- Lint: 0 errors; warnings remain (React fast-refresh hints for helper exports, one set-state-in-effect in the fetch hook,
  pre-existing V0 warnings).

## 9. UX redesign for viva / demo use (2026-11-15)
User feedback: too much information at once, hard to navigate, plain look; main audience = viva / project demo.
- **Navigation shortened**: sidebar = 7 result pages + "Experiment log" + one "Historical results (V0)" entry (the
  ten V0 pages are reached from the V0 landing page, not the sidebar).
- **Presentation mode** (`/present`, new `frontend/src/v2/pages/Present.tsx`): six full-screen slides — problem (real
  sample image per class via new `GET /api/v2/dataset/sample/{class}.png`, train-folder images only), fair evaluation,
  FRQI vs NEQR with real reconstructions, model families, results, conclusions. Arrow/Space/PageUp/PageDown, dots,
  Esc to exit; slide in the URL (`?slide=n`) so refresh keeps position. Every number from `/api/v2/*`.
- **Overview rewritten story-first**: question + two headline numbers (best overall, best purely quantum) + a
  data-derived summary sentence, slim KPI strip, family bar chart, "three things to remember", explore cards;
  methodology/statistics and remaining findings collapsed.
- **Model Comparison**: default = ranked leaderboard (top 12, family filter chips, accuracy bars; shot-noise,
  ablation and legacy variants hidden unless switched on); the full 88-row table, filters and side-by-side compare
  moved to "Advanced".
- **Encoding**: FRQI-vs-NEQR "at a glance" (qubits, compiled gates, MSE at 1,000 shots, accuracy) first; detailed
  per-resolution tables collapsible. **Classification**: weak-class table collapsible.
- **Visual system** (`frontend/src/v2/theme.tsx`): one colour + icon per family used on every page, accuracy bars,
  collapsibles, fade-in (disabled under `prefers-reduced-motion`).

## 10. Stability fix found by the repeated browser runs
The backend process died during an end-to-end run. Re-running with `-X faulthandler` captured the cause:
**segfault in `pyarrow.compute.take`** (pandas 3 stores strings in pyarrow by default) while the V0 endpoint
`experiment_manager.get_reconstruction_details` filtered the V0 CSV from concurrent request threads.
Fix: `pd.set_option("future.infer_string", False)` at the top of `api_main.py` (identical values, plain object
strings; verified on the 3,646-row V0 CSV). Regression test `test_api_disables_pyarrow_string_inference`.
After the fix the backend survived 5 consecutive full browser runs (it died on the 2nd run before).
Also fixed: rapid key presses in Presentation mode advanced only one slide (router state is stale until re-render;
steps now read the live URL).
