#!/bin/bash
# candidates (N workers) -> select -> freeze -> locked test, logs in results/qml_v4/logs
set -e
cd "$(dirname "$0")"
PY=../../.venv/bin/python; L=../../results/qml_v4/logs; N=${N:-5}
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
echo "$(date) chain start N=$N" >> $L/chain.stdout
pids=(); for i in $(seq 0 $((N-1))); do $PY run_v4.py candidates --worker $i --of $N > $L/worker_$i.stdout 2>&1 & pids+=($!); done
for p in "${pids[@]}"; do wait $p || { echo "$(date) worker failed" >> $L/chain.stdout; exit 1; }; done
echo "$(date) candidates done" >> $L/chain.stdout
$PY run_v4.py select > $L/select.stdout 2>&1; echo "$(date) select done" >> $L/chain.stdout
$PY run_v4.py freeze > $L/freeze.stdout 2>&1; echo "$(date) frozen: $(cat $L/freeze.stdout)" >> $L/chain.stdout
$PY run_v4.py test > $L/test.stdout 2>&1; echo "$(date) locked test done" >> $L/chain.stdout
