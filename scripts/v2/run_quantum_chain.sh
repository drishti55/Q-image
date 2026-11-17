#!/bin/zsh
# Sequential Protocol V2 quantum experiment chain (stops at the first failing phase).
set -e
cd "$(dirname "$0")/../.."
export SSL_CERT_FILE=.venv/lib/python3.11/site-packages/certifi/cacert.pem
L=results/qml_v2/logs
python3 scripts/v2/verify_historical.py --label before-chain
python3 scripts/v2/phase4_qkc.py control sv     > $L/phase4_sv.stdout 2>&1
python3 scripts/v2/phase4_qkc.py shots          > $L/phase4_shots.stdout 2>&1
python3 scripts/v2/verify_historical.py --label after-phase4
python3 scripts/v2/phase5_vqc.py grid ablation  > $L/phase5.stdout 2>&1
python3 scripts/v2/verify_historical.py --label after-phase5
python3 scripts/v2/phase6_frqi_neqr.py classify shots recon > $L/phase6.stdout 2>&1
python3 scripts/v2/verify_historical.py --label after-phase6
python3 scripts/v2/phase7_hybrid.py             > $L/phase7.stdout 2>&1
python3 scripts/v2/verify_historical.py --label after-phase7
python3 scripts/v2/phase8_analysis.py           > $L/phase8.stdout 2>&1
python3 scripts/v2/verify_historical.py --label after-phase8
echo CHAIN_DONE
