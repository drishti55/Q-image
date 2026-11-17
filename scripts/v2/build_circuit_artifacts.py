"""Build circuit artefacts for every circuit configuration used by a selected V2 quantum model.
Each artefact = the circuit rebuilt from that experiment's saved checkpoint (first training image of its split;
trained parameters for VQCs) + its recorded resources. Output: results/qml_v2/circuits/<experiment_id>.json.
Runs in a clean process (see src/v2/api_models.py::circuit_detail for why not inside the API)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.v2.api_models import build_circuit_detail, circuit_artifact_path, circuits  # noqa: E402
from src.v2.store import dump_json  # noqa: E402


def main():
    rows = circuits()["circuits"]
    ok = 0
    for c in rows:
        eid = c["experiment_id"]
        t = time.perf_counter()
        d = build_circuit_detail(eid)
        d["circuit_key"] = c["circuit_key"]
        d["used_by"] = c["used_by"]
        d["built_by"] = "scripts/v2/build_circuit_artifacts.py"
        dump_json(circuit_artifact_path(eid), d)
        ok += 1
        rec = (d.get("recorded_resources") or {}).get("gates_logical")
        print(f"{c['circuit_key']:32s} {eid:45s} q={d['n_qubits']:2d} gates={d['logical_gates_displayed_circuit']:6d} "
              f"recorded={rec} ({time.perf_counter() - t:.1f}s)", flush=True)
    print(f"built {ok}/{len(rows)} circuit artefacts")


if __name__ == "__main__":
    main()
