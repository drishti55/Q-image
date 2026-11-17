# Protocol V3 — Reproducibility Report

## 1. What V3 shares with V2 (unchanged)
- **Dataset and splits:** NEU-DET manifest `neu-5625b937479b`. The split files `split-s0-2a1d15648e`, `split-s1-c53cfc7e08` and `split-s2-cbd05190d5` (seeds 0, 1, 2) were copied byte-for-byte from `results/qml_v2/manifests`. Every copy is SHA-256 verified and listed in `results/qml_v3/manifests/v3_provenance.json`, and all three splits pass `verify_split`: the test set is exactly the NEU validation folder and the union covers the dataset.
- **Locked test:** the 360 NEU validation-folder images, readable only inside `final_evaluation_stage`. Every access is logged in `results/qml_v3/logs/test_access.jsonl`.
- **Preprocessing:** `preprocess_image` (convert L → bilinear resize → /255). Derived image arrays and MobileNetV3 features are copied from the V2 cache (keys are content hashes) and are otherwise recomputed identically.
- **Selection:** best mean validation macro-F1 over seeds 0, 1, 2 (`Runner.select`); configurations with a failed seed are ineligible.

## 2. Isolation from historical results
- **Write destination:** every V3 driver imports `scripts/v3/common.py`, which sets `QIL_RESULTS_V2=results/qml_v3` (all library writes go there) and `QIL_PROTECT_V2=1`.
- **Write protection:** with that flag, `src/v2/paths.assert_writable` refuses writes into `results/qml_v2` as well as `results/qml` and `results/models`. This is covered by the test `tests/test_v3_models.py::test_v2_root_protected_when_requested`.
- **Hash checks:** historical SHA-256 hashes (3,690 files) are re-verified with `scripts/v2/verify_historical.py`. Any V2 experiment file newer than `results/qml_v2/aggregates/analysis.json` would indicate a modification, and is checked as well.

## 3. Commands (in order)
```bash
.venv/bin/python scripts/v3/setup_v3.py                 # copy + verify manifest / splits / caches
cd scripts/v3 && N=9 ./chain_v3.sh                       # candidates (9 workers) → select → VQC controls → freeze → locked test
.venv/bin/python scripts/v3/analyze_v3.py                # → results/qml_v3/aggregates/v3_results.json (statistics, before/after)
.venv/bin/python scripts/v3/build_playground_v3.py       # → results/qml_v3/playground/playground_3x3.json
.venv/bin/python scripts/v2/verify_historical.py --label v3_final
# after the test-suite runs (results recorded in aggregates/test_suites_final.json):
.venv/bin/python scripts/v3/verify_v3.py --suites results/qml_v3/aggregates/test_suites_final.json   # → aggregates/v3_verification.json
.venv/bin/python scripts/v3/write_reports.py             # → reports/QUANTUM_PERFORMANCE_IMPROVEMENT_REPORT.md, QUANTUM_CLASSICAL_COMPARISON_REPORT.md, V3_VERIFICATION_REPORT.md
<playwright python> scripts/v3/v3_results_e2e.py          # browser check of /quantum-v3 (backend :8000 + Vite :5173 running)
```
Statistics are deterministic: each comparison's bootstrap / permutation RNG is seeded from the comparison name.

**Run record (this V3 run):** chain started 2026-11-16 04:57, candidates done 08:17, frozen 08:19:14, locked test done 08:25 (9 workers,
5,316 candidate runs, 0 failed).
Single-threaded BLAS is used per worker (`OMP_NUM_THREADS=1` etc.) to make parallel runs deterministic and fair. The chain is resumable: completed candidates are skipped, and the locked test is evaluated at most once per frozen configuration.

## 4. Freeze-then-test protocol
1. **Candidates:** every (configuration, seed) is fitted on train and scored on the internal validation split.
2. **Selection:** one configuration per group, chosen by mean validation macro-F1.
3. **VQC controls:** the frozen-random-circuit ablation and the encoding-only control, both with the selected configuration.
4. **Freeze:** `aggregates/frozen_selection.json` records every selected configuration key, its validation score and the SHA-256 of every selection file, together with the pre-declared comparison family and the headline rule. The file refuses to be overwritten.
5. **Test:** before evaluating, the test stage re-hashes every selection file and aborts if any changed since the freeze. Each frozen configuration is then evaluated once on the locked test set.
6. **Analysis:** reads saved records only. Headlines are chosen by validation, never by test.

## 5. Randomness
| Source | Seeding |
|---|---|
| Split seeds | 0, 1, 2 |
| SVC | `random_state = seed` |
| VQC | initial θ from `default_rng(seed)`; linear-head init from `default_rng(1000 + seed)`; mini-batch order from the same generator |
| SPSA | perturbations from the estimator's seeded generator |
| Bootstrap / permutation tests | `default_rng(0)` |
| Simulations | exact statevector (no shot noise) unless a shot count is stated |

## 6. Environment
Python 3.11 (`.venv`), qiskit 2.5.2, qiskit-aer 0.17.2, scikit-learn 1.9.1, numpy 2.4.6, scipy 1.17.1, scikit-image 0.26.0, torch 2.15.0 / torchvision 0.29.2 (MobileNetV3-small IMAGENET1K_V1, SHA-256 047dcff4…). Frontend: React 19, Vite 8, Recharts 3, Vitest. CPU only; no quantum hardware.
