# Q-ImageLab Protocol V2 — Reproducibility Guide

## 1. Environment
- macOS (Apple silicon), Python 3.11.0 in the project venv `.venv`; CPU only.
- `python -m pip install -r requirements.txt` (V2 adds `torch==2.15.0`, `torchvision==0.29.2`, `httpx==0.28.1`).
  The exact environment used is frozen in `results/qml_v2/manifests/pip_freeze_v2.txt`; package versions are
  also recorded in every experiment's `metadata.json`.
- Frontend: `cd frontend && npm install` (Vitest, Testing Library and jsdom are dev-only dependencies).
- MobileNetV3 weights (`MobileNet_V3_Small_Weights.IMAGENET1K_V1`, file `mobilenet_v3_small-047dcff4.pth`,
  SHA-256 `047dcff4addef86ea5bc2eff13c9614dc11f47ab1160d0a71a25e7db994f4e1f`) are downloaded by torchvision on first
  use into `~/.cache/torch/hub/checkpoints`. With python.org builds of Python on macOS the download can fail with
  `CERTIFICATE_VERIFY_FAILED`; set `SSL_CERT_FILE=.venv/lib/python3.11/site-packages/certifi/cacert.pem`
  (verification stays on; torchvision also checks the hash prefix).

## 2. Paths
| Variable | Default | Meaning |
|---|---|---|
| `QIL_DATASET_PATH` | `./NEU-DET` | dataset root (`train/images`, `validation/images`) |
| `QIL_RESULTS_V2` | `./results/qml_v2` | all V2 outputs |
| `QIL_ALLOW_V0_WRITES` | unset | must stay unset; legacy code cannot write into `results/` |

## 3. Run order (each step is resumable: completed experiments are skipped)
```bash
source .venv/bin/activate
python scripts/v2/verify_historical.py --label before        # historical hash check
python scripts/v2/phase1_data_protocol.py                    # manifest, splits (seeds 0,1,2), integrity
python scripts/v2/phase3_classical.py pca                    # E6 PCA + RBF-SVM / LogReg
SSL_CERT_FILE=... python scripts/v2/phase3_classical.py mnv3 cnn   # E7 frozen MobileNetV3, small CNN
python scripts/v2/phase4_qkc.py control sv shots             # E6 angle-feature control, E3 QKC, E3 shots
python scripts/v2/phase5_vqc.py grid ablation                # E4 VQC + frozen-circuit ablation
python scripts/v2/phase6_frqi_neqr.py classify shots recon   # E1/E1b/E2 + reconstruction study
python scripts/v2/phase7_hybrid.py                           # E5 CNN features + QKC/VQC + controls
python scripts/v2/phase8_analysis.py                         # aggregates/analysis.json
python scripts/v2/verify_historical.py --label after
```
Re-running a script with the same code and data reproduces the same experiment IDs (IDs hash the configuration),
so finished experiments are skipped. To reproduce one saved experiment from scratch, move its directory out
of `results/qml_v2/experiments/` and re-run the script that produced it (its `config.json` names the group).
Nondeterminism: sklearn/NumPy paths are seeded; PyTorch uses `torch.use_deterministic_algorithms(True)` with
4 threads; timing fields naturally vary between runs.

## 4. Tests (safe: they never write into `results/`)
```bash
python -m pytest -q tests            # backend, data protocol, simulator/kernel/VQC validation, API
cd frontend && npm test && npx tsc -b --noEmit && npx oxlint
```

## 5. Dashboard
```bash
python scripts/v2/build_circuit_artifacts.py   # once after experiments: circuits/*.json for the Circuit Explorer
python api_main.py                   # FastAPI on :8000 (restart it after updating the code!)
cd frontend && npm run dev           # http://localhost:5173/  → Protocol V2 overview; V0 under /historical-v0
python scripts/v2/dashboard_e2e.py   # optional real-browser check (needs `pip install playwright` + Google Chrome)
```
If the dashboard shows "Protocol V2 data cannot be loaded", the running backend predates the V2 API — stop it and
start `python api_main.py` again.

## 6. Output layout
```
results/qml_v2/
  manifests/     dataset manifest, splits/, split_integrity.json, historical_preservation_manifest.json, pip freeze
  experiments/   <group>__<confighash>__s<seed>/ config, metadata, status, metrics, predictions, model/
  aggregates/    selection/<group>.json, analysis.json
  reconstructions/ R-<FRQI|NEQR>-<r>x<r>[-b<bits>]/ metrics, circuit_stats, images/
  logs/          run logs, test_access.jsonl (every locked-test access), historical_verification.jsonl
  superseded/    artefacts from a buggy run, kept for traceability and excluded from analysis
  reports/       phase reports and final reports
```

## Algorithm Playground data (illustrative 3×3 demo)
```bash
.venv/bin/python scripts/v2/build_playground.py      # writes results/qml_v2/playground/playground_3x3.json (offline; uses seed-0 checkpoints)
python scripts/v2/playground_e2e.py                  # browser check of /playground and /quantum-vs-classical (needs Playwright, running servers)
```
The demo is labelled illustrative and is never part of any evaluation result.
