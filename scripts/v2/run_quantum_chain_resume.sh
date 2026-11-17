#!/bin/zsh
# Resume the Protocol V2 chain from Phase 5 (completed experiments are skipped by the runner).
set -e
cd "$(dirname "$0")/../.."
export SSL_CERT_FILE=.venv/lib/python3.11/site-packages/certifi/cacert.pem
L=results/qml_v2/logs
PY=.venv/bin/python3
$PY scripts/v2/verify_historical.py --label resume-before-phase5
$PY scripts/v2/phase5_vqc.py grid ablation  >> $L/phase5.stdout 2>&1
$PY scripts/v2/verify_historical.py --label after-phase5
$PY scripts/v2/phase6_frqi_neqr.py classify shots recon >> $L/phase6.stdout 2>&1
$PY scripts/v2/verify_historical.py --label after-phase6
$PY scripts/v2/phase7_hybrid.py             >> $L/phase7.stdout 2>&1
$PY scripts/v2/verify_historical.py --label after-phase7
$PY scripts/v2/phase8_analysis.py           >> $L/phase8.stdout 2>&1
$PY scripts/v2/verify_historical.py --label after-phase8
echo CHAIN_DONE
