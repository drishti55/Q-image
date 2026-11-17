# Dashboard Audit — why users "see V0 when opening V2"

Date: 2026-11-14. Method: code inspection + **real browser runs** (Playwright driving the installed Google Chrome,
headless) against the running FastAPI backend and Vite dev server, plus a reproduction with a pre-V2 backend.
Historical hashes before any change: 3,690 files, 0 changed (`dashboard-redesign-before`).

## 1. Architecture as found
- Frontend: Vite + React 19 + react-router-dom 7, single shell in `frontend/src/App.tsx` (sidebar, header,
  `<Routes>`). 13 page components in `frontend/src/pages/`. No global state library, no query cache; each page
  fetches with `fetch` in `useEffect`. Dev server proxies `/api` → `http://127.0.0.1:8000`.
- Backend: `api_main.py` (FastAPI). V0 endpoints (`/api/status`, `/api/dataset/*`, `/api/models/*`, `/api/quantum/*`,
  `/api/qml/*`) read `results/`, `results/qml`, `results/models`. V2 router `src/v2/api.py` (`/api/v2/*`) reads only
  `results/qml_v2`. FastAPI does not serve the frontend.

## 2. Data flow traced
`results/qml_v2/experiments/*/status.json, aggregates/*.json, reconstructions/*` → `src/v2/api.py::_index()` and
handlers → `/api/v2/...` → `ExperimentsV2.tsx::useApi()` → tabs. Verified live: `/api/v2/overview` via the Vite
proxy returns the 2,583 V2 experiments; the V2 page requests only `/api/v2/comparison` and `/api/v2/experiments`;
no V0 page requests `/api/v2`, and the V2 page requests no V0 endpoint (the shell requests `/api/status`).
**No V0 record is ever rendered by the V2 page.**

## 3. Root cause (verified; several causes combine)
1. **The application is V0-first.** `/` renders the V0 `Dashboard` (V0 KPIs: "Total images 1440, Images evaluated…").
   11 of 14 sidebar links open V0 pages; the "Quantum ML Suite" section (Overview & Telemetry, QML Model Comparisons,
   FRQI vs NEQR, Quantum vs Classical, Circuit Visualizer, Reconstruction Studio, 15 Charts, Experiment Explorer) is
   entirely V0 (`/quantum-ml-lab?tab=…`). Old routes `/circuit` and `/reconstruction` redirect into V0.
2. **The V2 page is embedded in V0 chrome with V0 numbers.** On `/experiments-v2` the header title falls back to
   `'Dashboard'` (`titleMap` has no entry), the breadcrumb reads "Q-ImageLab / Dashboard", and the shell shows
   hardcoded V0 figures: header chip "1,800 Images Ready", sidebar badges "3,632", "3.6k", "7 Models", "11 Models",
   "15", "6-Panel", "Paired". "Backend Online" comes from the V0 `/api/status`.
3. **The V2 page itself opens on something that looks old.** Default tab = "Model comparison", rows sorted by
   group id, so the first rows are `E1-frqi16-qkc`, `E1-frqi2-qkc`, `E1-frqi4-encstats-logreg`,
   `E1-frqi4-legacy-softmax` — FRQI/NEQR and *relabelled legacy V0 methods*, shown by internal ids without
   human-readable names. A "Historical (V0)" tab sits inside the V2 page.
4. **A backend started before the V2 router existed makes the V2 page empty while the V0 shell keeps working.**
   Reproduced: running the committed (HEAD) `api_main.py` → `/api/v2/overview` = 404; the browser shows only
   "Could not load data: Error: 404 Not Found" boxes inside a shell that still says "Backend Online"
   (screenshot `dashboard_screenshots/before_experiments-v2_stale_backend.png`). Anyone with a long-running backend
   from before 2026-11-13 sees no V2 data and only V0 content elsewhere. No version/health check exposes this.
5. Minor: `/api/v2/overview.selected_with_test` counts experiment *runs* (264 = 88 × 3) not configurations; the
   comparison endpoint lacks human-readable names, execution mode (exact vs shots), circuit resources, per-seed values.

Not a cause (checked): no redirect from `/experiments-v2`; no stale-cache layer (no service worker, no query cache);
no shared state mixing V0/V2; the Vite build in `frontend/dist` includes the V2 route.

## 4. Fix plan (implemented — see DASHBOARD_IMPLEMENTATION_REPORT.md)
- New V2-first shell and routes: `/` V2 overview; `/experiments-v2`; `/models`; `/encoding`; `/circuits`;
  `/reconstruction`; `/classification`; `/experiments/:id`; `/historical-v0/*` for every V0 page (old URLs redirect).
- Remove hardcoded numbers from the shell; header shows V2 API health + dataset/manifest from `/api/v2/summary`;
  explicit "API out of date / V2 endpoints missing" banner when `/api/v2/health` is not reachable.
- Backend: `/api/v2/health`, `/api/v2/summary`, `/api/v2/models` (all 88 selected configurations with names,
  category, metrics, per-seed values, exec mode, circuit resources), `/api/v2/models/{group}`, `/api/v2/circuits`,
  `/api/v2/circuits/{experiment_id}` (actual executed circuit rebuilt from the saved checkpoint), encoding endpoint.
