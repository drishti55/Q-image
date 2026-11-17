#!/bin/bash
# Full Protocol V3 chain: candidates (9 parallel workers) -> select -> VQC controls -> freeze -> locked test (once).
# Resumable: completed candidates are skipped. Writes only to results/qml_v3.
set -e
cd "$(dirname "$0")"
PY=../../.venv/bin/python
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 PYTHONUNBUFFERED=1
N=${N:-9}
LOG=../../results/qml_v3/logs
mkdir -p $LOG
echo "$(date) chain start N=$N"
pids=()
for i in $(seq 0 $((N-1))); do
  $PY run_v3.py candidates --worker $i --of $N > $LOG/worker_$i.stdout 2>&1 &
  pids+=($!)
done
fail=0
for p in "${pids[@]}"; do wait $p || fail=1; done
[ $fail = 0 ] || { echo "a worker failed"; exit 1; }
echo "$(date) candidates done"
$PY run_v3.py select > $LOG/select.stdout 2>&1
echo "$(date) select done"
pids=()
for i in 0 1 2 3 4 5; do
  $PY run_v3.py controls --worker $i --of 6 > $LOG/controls_$i.stdout 2>&1 &
  pids+=($!)
done
for p in "${pids[@]}"; do wait $p; done
$PY run_v3.py controls --worker 0 --of 1 > $LOG/controls_select.stdout 2>&1
echo "$(date) controls done"
$PY run_v3.py freeze > $LOG/freeze.stdout 2>&1
echo "$(date) frozen: $(cat $LOG/freeze.stdout)"
$PY run_v3.py test > $LOG/test.stdout 2>&1
echo "$(date) locked test done"
