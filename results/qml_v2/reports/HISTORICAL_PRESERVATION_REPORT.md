# Historical Preservation Report

**Result: PASS — 0 changed, 0 missing, 0 added across all 3,690 historical files.**

## Scope
Every file under `results/` except `results/qml_v2/` (mandatory-immutable: `results/qml`, `results/models`; also
covered: `results/experiments`, `results/images`, `results/dataset`, `results/charts`).

| | Original (2026-11-13, before any change) | Final |
|---|---|---|
| All historical files | 3,690 | 3,690 |
| results/qml | 3,652 files (3,639 JSON; qml_experiments.csv 3,646 data rows) | 3,652 files |
| results/models | 14 files | 14 files |
| Changed / missing / added files | — | 0 / 0 / 0 |

## Original SHA-256 manifest
`results/qml_v2/manifests/historical_preservation_manifest.json` — relative path, size and SHA-256 of all
3,690 files, captured before any code change (manifest file SHA-256 `1f0175481797f71cc712efbbecc126697eeafba5694f809b56d351be220572c7`).
Final per-file comparison: `results/qml_v2/reports/historical_final_comparison.json`.

## Verification log (`results/qml_v2/logs/historical_verification.jsonl`)
| Label | Time | Files | Changed | Missing | Added | All OK |
|---|---|---|---|---|---|---|
| phase0 | 2026-11-13T15:38:27 | 3690 | 0 | 0 | 0 | True |
| phase1 | 2026-11-13T15:42:16 | 3690 | 0 | 0 | 0 | True |
| phase2 | 2026-11-13T15:47:56 | 3690 | 0 | 0 | 0 | True |
| phase9-api-tests | 2026-11-13T16:41:56 | 3690 | 0 | 0 | 0 | True |
| phase3 | 2026-11-13T17:27:41 | 3690 | 0 | 0 | 0 | True |
| before-chain | 2026-11-13T17:27:41 | 3690 | 0 | 0 | 0 | True |
| after-phase4 | 2026-11-13T18:44:23 | 3690 | 0 | 0 | 0 | True |
| session2-resume | 2026-11-14T19:50:25 | 3690 | 0 | 0 | 0 | True |
| resume-before-phase5 | 2026-11-14T19:50:56 | 3690 | 0 | 0 | 0 | True |
| after-api-smoke | 2026-11-14T19:51:16 | 3690 | 0 | 0 | 0 | True |
| after-phase5 | 2026-11-14T20:03:52 | 3690 | 0 | 0 | 0 | True |
| after-phase6 | 2026-11-14T20:10:08 | 3690 | 0 | 0 | 0 | True |
| after-phase7 | 2026-11-14T20:28:31 | 3690 | 0 | 0 | 0 | True |
| after-phase8 | 2026-11-14T20:28:32 | 3690 | 0 | 0 | 0 | True |
| final-validation | 2026-11-14T20:29:24 | 3690 | 0 | 0 | 0 | True |
| final | 2026-11-14T20:32:24 | 3690 | 0 | 0 | 0 | True |

## How preservation was enforced
- `src/v2/paths.py::assert_writable` refuses writes under `results/` outside `results/qml_v2/` (unless
  `QIL_ALLOW_V0_WRITES=1`, never set) — called by the legacy trainer, results manager and plotter.
- `QMLExperimentManager` is read-only when pointed at `results/qml` (the default); its dataset-manifest rewrite on
  every dashboard overview load was removed; V0 launch/delete API endpoints return 409.
- Tests write only to `tmp_path`; the old test that appended 16 fixture rows (`test001`/`fail001`) to
  `results/qml/qml_experiments.csv` now uses a temporary directory. Those 16 historical rows were left in place and are
  flagged as fixtures in the historical view (not deleted).
- No `git reset/checkout/clean` or restore commands were used.

Old results were not overwritten, rewritten, renamed, reformatted or appended to.
