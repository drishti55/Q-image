# Phase 2 — Experiment Runner and Result Schema V2

Status: **PASS**

## Implemented
- `src/v2/store.py` — `ExperimentStore`: one directory per experiment
  (`config.json`, `metadata.json`, `status.json`, `training_log.json`, `validation_metrics.json`,
  `test_metrics.json`, `predictions.csv`, `confusion_matrix.json`, `circuit_stats.json`, `diagnostics.json`,
  `model/estimator.joblib`). Atomic JSON writes; NaN/inf saved as `null`; every write passes the
  historical-path guard. Provenance in `metadata.json`: git commit + dirty flag, Python/package versions,
  platform, CPU count, memory, dataset manifest id, split id, seed, start/end/duration,
  "classical CPU simulation (no quantum hardware)".
- `src/v2/runner.py` — `ModelSpec` (experiment code, selection group, model name, family, compute type,
  feature extraction, encoding, params, quantum descriptors) and `Runner`:
  1. candidates: every configuration × seed (0, 1, 2) fitted on train, scored on internal validation;
  2. selection: best mean validation macro-F1 (any failed seed → ineligible) → `aggregates/selection/<group>.json`;
  3. final stage: selected checkpoints loaded (no refit) and scored once per seed on the locked test set
     inside `final_evaluation_stage`, with a percentile-bootstrap 95% CI.
  Experiment ID = `<group>__<sha256(config)[:10]>__s<seed>`; completed experiments are skipped (resume).
  Failures are stored with type, message and traceback; no metrics are written for them.
- `src/v2/providers.py` — feature providers (pixel PCA, raw images, precomputed vectors); fitted
  transforms cached per seed; test features only via the locked loader.
- Record types: `classification` (experiments/) and `reconstruction` (reconstructions/), kept separate.

## Tests
`tests/test_v2_runner.py` (5 tests, all in `tmp_path`): unique IDs, failure preserved with traceback,
selection ignores failed configs and the test set is read only in the final stage (3 calls = 3 seeds),
test metrics only for the selected config, required files present, provenance, resume skips completed
work, checkpoint reload without refit, JSON NaN → null.

## Correction recorded during Phase 3 (traceable)
The first MobileNetV3 run exposed a runner integration defect: the provider description (part of the
config hash) changed after weights loaded, so a group's IDs changed mid-run → `KeyError` in selection.
Fixes: volatile load information moved to diagnostics; `ModelSpec.config_key()` is computed once and frozen.
The affected directories were moved, unchanged, to
`results/qml_v2/superseded/2026-11-13_mnv3_config_hash_bug/` (README inside); no test evaluation had run.

## Historical preservation
`verify_historical.py --label phase2`: 3,690 files, changed 0, missing 0, added 0.
