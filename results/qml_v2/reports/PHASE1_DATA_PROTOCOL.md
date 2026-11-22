# Phase 1 — Data Protocol and Evaluation Integrity

Status: **PASS**

## Dataset validation (actual dataset, `./NEU-DET`, manifest `neu-5625b937479b`)
| Check | Result |
|---|---|
| Images | 1,800 (train folder 1,440 = 240/class; validation folder 360 = 60/class) |
| Classes | crazing, inclusion, patches, pitted_surface, rolled-in_scale, scratches (no unknown folders) |
| Dimensions / mode | all 200×200, stored as 3-channel RGB (grayscale content) → converted with `convert("L")` |
| Unreadable / corrupt | 0 |
| Index ranges | train 1–240, validation 241–300 per class, no repeated indices |
| Exact duplicates (SHA-256) | 1 pair: `train/patches/patches_101.jpg` ≡ `patches_105.jpg` — same index block, so never split across train/val/test. Kept (dataset not altered); documented. |
| Folder label vs XML annotation | Folder label present in every annotation. 123 images contain additional defect boxes (e.g. 49 scratches images also annotate `inclusion`). Single-label task uses the folder label. |
| Annotation files | `crazing_240.xml` is misplaced in `validation/annotations` (its image is in the train folder). Annotations are not used for labels. |

## Grouping evidence and design
Measured on the train folder (64×64, per-image standardized pixels): same-class pairs at index distance
1–2 are markedly more similar than distant pairs (e.g. inclusion: 0.44 at d=1 vs 0.04 for d>50;
pitted_surface: 0.46 vs 0.05), with elevated similarity up to d≈10–20 in several classes.
**Groups = contiguous blocks of 20 file indices per class** (12 blocks per class). Per seed, 3 blocks
per class are drawn for internal validation → 1,080 train / 360 val. The filenames carry no
acquisition metadata (coil/strip id), so index blocks are the strongest available grouping; blocks
reduce but cannot provably eliminate correlation at block boundaries.

## Splits (seeds 0, 1, 2) — `results/qml_v2/manifests/splits/`
| Seed | split_id | train / val / test | path, hash, group overlap (all pairs) | val NN within ±3 idx: blocked vs random split | test NN within ±3 idx |
|---|---|---|---|---|---|
| 0 | split-s0-2a1d15648e | 1080 / 360 / 360 | 0 / 0 / 0 | 0.008 vs 0.103 | 0.000 |
| 1 | split-s1-c53cfc7e08 | 1080 / 360 / 360 | 0 / 0 / 0 | 0.011 vs 0.089 | 0.000 |
| 2 | split-s2-cbd05190d5 | 1080 / 360 / 360 | 0 / 0 / 0 | 0.022 vs 0.081 | 0.003 |

"NN within ±3" = fraction of val (test) images whose most similar same-class training image is within
3 file indices. The blocked design lowers it 5–12× relative to the random split used by Protocol V0.

## Locked test enforcement
`NEUData.test()` raises `TestSetLockedError` unless called inside
`final_evaluation_stage(reason)`; every entry is logged to `results/qml_v2/logs/test_access.jsonl`.
Tuning code receives only `train()` / `val()`.

## Preprocessing (documented, identical for all pixel-based models)
`convert("L")` → `resize((s,s), BILINEAR)` → `/255`. PCA pipeline: per-pixel StandardScaler → PCA(k) →
StandardScaler (classical view) or MinMax to [0, π] (quantum angle view); all fitted on train only;
val/test angles are not clipped.

## Files
New: `src/v2/dataset.py`, `src/v2/features.py`, `src/v2/metrics.py`, `scripts/v2/phase1_data_protocol.py`,
`tests/test_v2_data.py`. Modified: `config/settings.py` (removed silent `~/Downloads/NEU-DET-2`
switch; `QIL_DATASET_PATH` override).

## Tests
`pytest tests` → 106 passed, 1 failed (pre-existing `test_neqr_quantum_features`, addressed in Phase 6).
`tests/test_v2_data.py` 7/7 pass (manifest, cross-group duplicate detection, split overlap, determinism,
test lock + logging, preprocessing range, train-only PCA, six-label metrics, bootstrap CI).

## Historical preservation
`verify_historical.py --label phase1`: changed=0, missing=0, added=0.
