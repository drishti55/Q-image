"""Shared setup for Protocol V3 drivers. Importing this module points every V2 library function at
results/qml_v3 (QIL_RESULTS_V2) and makes results/qml_v2 immutable for this process (QIL_PROTECT_V2=1)."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V3 = ROOT / "results" / "qml_v3"
V2 = ROOT / "results" / "qml_v2"
os.environ["QIL_RESULTS_V2"] = str(V3)
os.environ["QIL_PROTECT_V2"] = "1"
sys.path.insert(0, str(ROOT))

from src.v2.dataset import DEFAULT_SEEDS, load_manifest, load_split  # noqa: E402
from src.v2.paths import v2_root  # noqa: E402
from src.v2.runner import Runner  # noqa: E402
from src.v2.store import ExperimentStore  # noqa: E402

assert v2_root(create=False) == V3.resolve(), "V3 drivers must write to results/qml_v3"


def make_runner(log_name: str) -> Runner:
    root = v2_root()
    log_path = root / "logs" / f"{log_name}.log"

    def log(*a):
        line = " ".join(str(x) for x in a)
        print(line, flush=True)
        with open(log_path, "a") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')} {line}\n")

    m = load_manifest()
    split_ids = {s: load_split(s)["split_id"] for s in DEFAULT_SEEDS}
    log(f"# start {log_name}: manifest={m['manifest_id']} splits={json.dumps(split_ids)}")
    return Runner(store=ExperimentStore(root), seeds=DEFAULT_SEEDS, split_ids=split_ids,
                  manifest_id=m["manifest_id"], log=log)
