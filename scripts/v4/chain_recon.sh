#!/bin/bash
set -e
cd "$(dirname "$0")"
PY=../../.venv/bin/python; L=../../results/qml_v4/logs; N=${N:-9}
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
echo "$(date) recon start N=$N" >> $L/recon_chain.stdout
pids=(); for i in $(seq 0 $((N-1))); do $PY reconstruct_all.py run --worker $i --of $N > $L/recon_worker_$i.stdout 2>&1 & pids+=($!); done
for p in "${pids[@]}"; do wait $p || { echo "$(date) recon worker failed" >> $L/recon_chain.stdout; exit 1; }; done
$PY reconstruct_all.py merge > $L/recon_merge.stdout 2>&1
echo "$(date) recon done" >> $L/recon_chain.stdout
