# V3 Verification Report

Protocol V3 · 70 frozen groups · 5,316 validation runs (0 failed) · selections frozen 2026-11-16T08:19:14.500799 (SHA-256 `54c5c6e64cd95502ee8c95fd11d4b39b55455787535d614915e303ab238aedc5`) · 70 locked-test evaluation stages.

Source: `results/qml_v3/aggregates/v3_results.json` (built by `scripts/v3/analyze_v3.py` from the per-experiment records). Accuracy and macro-F1 are on the 360 locked test images, mean ± s.d. over seeds 0, 1, 2. All quantum circuits are simulated exactly (statevector) on a CPU; no quantum hardware and no noise model were used.

Generated 2026-11-16T08:49:49 by `scripts/v3/verify_v3.py`; checks: 29, passed: 29.

| Check | Result | Detail |
|---|---|---|
| historical V0 results (results/qml, results/models): 0 changed, 0 missing | PASS | original files 3690; changed 0; missing 0 |
| no new files under historical folders (added files are all in qml_v2/qml_v3) | PASS | [] |
| 53 copied V2 manifests / splits / caches identical in qml_v2 and qml_v3 (SHA-256) | PASS | [] |
| split verification at copy time: no path / hash / group overlap; test = whole NEU validation folder | PASS |  |
| no Protocol V2 experiment, aggregate, manifest or cache file modified since V3 setup | PASS | [] |
| V2 files touched since V3 setup are only report screenshots / verification log (disclosed in notes) | PASS | 18 files |
| 70 selection files unchanged since freeze (SHA-256) | PASS | [] |
| frozen_selection.json hash matches v3_results.json | PASS |  |
| every locked-test access happened after the freeze | PASS | first 2026-11-16T08:19:15.471484 > frozen 2026-11-16T08:19:14.500799 |
| exactly one locked-test stage per frozen group | PASS | 70 groups |
| test predictions exist only for the 3 seeds of each frozen configuration | PASS | 210 dirs with test predictions; 210 frozen; extra [] |
| no selection file contains a test metric | PASS | [] |
| no failed or missing candidate runs | PASS | {'completed': 5316} |
| test accuracy recomputed from predictions.csv for all 70 groups (210 runs, 360 locked images each) | PASS | [] |
| headline 'vqc' is the max-validation group in its category | PASS | V3-tex8c-vqc |
| headline 'hybrid_quantum' is the max-validation group in its category | PASS | V3-mnv8c-qkc-product_ry |
| headline 'classical_control_best' is the max-validation group in its category | PASS | V3-mnv8c-rbfsvm |
| headline 'pure_quantum' is the max-validation group in its category | PASS | V3-tex12c-qkc-product_ry |
| every VQC group has trainable quantum parameters (> 0) and an entangling circuit | PASS | 5 groups |
| encoding-only controls have 0 trainable quantum parameters (labelled as controls) | PASS | 3 groups |
| every quantum-labelled group records a simulated circuit (statevector, no hardware) | PASS | 43 groups |
| no classical model is categorised as quantum | PASS |  |
| Holm-adjusted p-values are >= raw and monotone | PASS | 24 comparisons |
| pytest: tests/ (incl. test_v3_models, test_v3_api) | PASS | 184 passed |
| vitest: frontend unit tests (playground walkthroughs vs V3 JSON) | PASS | 26 passed |
| TypeScript (tsc -b) and production build (vite build) | PASS | no errors |
| browser e2e: 3x3 playground (scripts/v2/playground_e2e.py) | PASS | 65 passed, 0 failed |
| browser e2e: dashboard (scripts/v2/dashboard_e2e.py) | PASS | 49 passed, 0 failed |
| browser e2e: V3 results page (scripts/v3/v3_results_e2e.py) | PASS | 10 passed, 0 failed |

## Notes
- The V2 report screenshots in results/qml_v2/reports/algorithm_screenshots/ were re-captured by scripts/v2/playground_e2e.py while the V3 UI was being tested, before its default output was moved to results/qml_v3/reports/screenshots/. They are report images, not results; no V2 experiment, aggregate, manifest or cache file changed.
- results/qml_v2/logs/historical_verification.jsonl is an append-only log written by the verification script itself.
- verify_historical.py reports all_ok=False only because new files exist (results/qml_v3); mandatory checks (changed = missing = 0) pass.
- The like-for-like V3-vs-V2 comparisons were added to analyze_v3.py after the locked test was opened; they are reported as a separate post-hoc family and change no selection.
