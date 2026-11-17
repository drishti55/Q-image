"""
Result store for Protocol V2 (results/qml_v2/experiments/<experiment_id>/).

Per-experiment files (only those relevant are written):
  config.json              full configuration (model, features, preprocessing, seeds, split ids)
  metadata.json            provenance: git commit, versions, hardware, dataset/split manifests, timing
  status.json              status (running|completed|failed), error + traceback, summary record
  training_log.json        per-epoch / per-iteration history (only if the model trains iteratively)
  validation_metrics.json  metrics on the internal validation split
  test_metrics.json        metrics on the LOCKED test set (only for selected configurations)
  predictions.csv          per-image predictions (split column = val | test)
  confusion_matrix.json    val (+ test) confusion matrices
  circuit_stats.json       quantum circuit resources (quantum models only)
  diagnostics.json         model-specific diagnostics (kernel checks, gradient stats, ...)
  model/                   saved model artefacts (checkpoint) used for the final test evaluation
Reconstruction studies use a separate record type (record_type = "reconstruction").
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .paths import PROJECT_ROOT, assert_writable, v2_root

SCHEMA_VERSION = "qml_v2.1"


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    return str(o)


def _sanitize(o):
    """Replace NaN/inf with None so JSON stays standard-compliant (missing != 0)."""
    if isinstance(o, dict):
        return {k: _sanitize(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_sanitize(v) for v in o]
    if isinstance(o, float) and not np.isfinite(o):
        return None
    return o


def dump_json(path: Path, obj: Any) -> None:
    assert_writable(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(_sanitize(json.loads(json.dumps(obj, default=_json_default))), indent=1))
    os.replace(tmp, path)


def config_hash(cfg: Dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, default=_json_default).encode()).hexdigest()[:10]


_ENV_CACHE: Optional[Dict] = None


def environment_info() -> Dict:
    global _ENV_CACHE
    if _ENV_CACHE is not None:
        return _ENV_CACHE
    vers = {}
    for mod in ("numpy", "scipy", "sklearn", "qiskit", "qiskit_aer", "torch", "torchvision", "PIL", "skimage"):
        try:
            vers[mod] = __import__(mod).__version__
        except Exception:
            vers[mod] = None
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True,
                             text=True, timeout=10).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "src", "scripts", "config"],
                                    cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=20).stdout.strip())
    except Exception:
        sha, dirty = None, None
    try:
        mem = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True).stdout.strip())
    except Exception:
        mem = None
    _ENV_CACHE = {
        "git_commit": sha, "git_worktree_dirty": dirty,
        "python": sys.version.split()[0], "platform": platform.platform(),
        "machine": platform.machine(), "cpu_count": os.cpu_count(), "memory_bytes": mem,
        "packages": vers,
        "execution": "classical CPU simulation (no quantum hardware)",
    }
    return _ENV_CACHE


class ExperimentStore:
    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root) if root else v2_root()
        self.exp_root = self.root / "experiments"
        self.exp_root.mkdir(parents=True, exist_ok=True)

    def dir(self, experiment_id: str) -> Path:
        return self.exp_root / experiment_id

    def exists(self, experiment_id: str) -> bool:
        return (self.dir(experiment_id) / "status.json").exists()

    def status(self, experiment_id: str) -> Optional[Dict]:
        p = self.dir(experiment_id) / "status.json"
        return json.loads(p.read_text()) if p.exists() else None

    def write(self, experiment_id: str, name: str, obj: Any) -> None:
        dump_json(self.dir(experiment_id) / name, obj)

    def read(self, experiment_id: str, name: str) -> Optional[Any]:
        p = self.dir(experiment_id) / name
        return json.loads(p.read_text()) if p.exists() else None

    def start(self, experiment_id: str, config: Dict, provenance: Dict) -> None:
        d = self.dir(experiment_id)
        d.mkdir(parents=True, exist_ok=True)
        self.write(experiment_id, "config.json", config)
        self.write(experiment_id, "metadata.json", {
            "schema_version": SCHEMA_VERSION, "experiment_id": experiment_id,
            "started_at": datetime.now().isoformat(), "environment": environment_info(), **provenance,
        })
        self.write(experiment_id, "status.json", {"experiment_id": experiment_id, "status": "running",
                                                   "updated_at": datetime.now().isoformat()})

    def finish(self, experiment_id: str, summary: Dict, status: str = "completed",
               error: Optional[BaseException] = None) -> None:
        meta = self.read(experiment_id, "metadata.json") or {}
        ended = datetime.now()
        meta["ended_at"] = ended.isoformat()
        if meta.get("started_at"):
            meta["duration_s"] = (ended - datetime.fromisoformat(meta["started_at"])).total_seconds()
        self.write(experiment_id, "metadata.json", meta)
        st = {"experiment_id": experiment_id, "status": status, "updated_at": ended.isoformat(),
              "summary": summary}
        if error is not None:
            st["error"] = {"type": type(error).__name__, "message": str(error),
                           "traceback": "".join(traceback.format_exception(type(error), error, error.__traceback__))}
        self.write(experiment_id, "status.json", st)

    def update_summary(self, experiment_id: str, **fields) -> None:
        st = self.status(experiment_id) or {"experiment_id": experiment_id}
        st.setdefault("summary", {}).update(fields)
        st["updated_at"] = datetime.now().isoformat()
        self.write(experiment_id, "status.json", st)

    def write_predictions(self, experiment_id: str, split: str, paths: List[str], y_true, y_pred,
                          proba: Optional[np.ndarray] = None, class_names: Optional[List[str]] = None) -> None:
        p = self.dir(experiment_id) / "predictions.csv"
        assert_writable(p)
        rows = []
        if p.exists():
            with open(p, newline="") as f:
                rows = [r for r in csv.DictReader(f) if r["split"] != split]
        for i, path in enumerate(paths):
            r = {"split": split, "image": path, "y_true": int(y_true[i]), "y_pred": int(y_pred[i])}
            if class_names:
                r["true_class"], r["pred_class"] = class_names[int(y_true[i])], class_names[int(y_pred[i])]
            if proba is not None:
                r["confidence"] = float(np.max(proba[i]))
            rows.append(r)
        fields = ["split", "image", "y_true", "y_pred", "true_class", "pred_class", "confidence"]
        with open(p, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)

    def list_ids(self) -> List[str]:
        return sorted(d.name for d in self.exp_root.iterdir() if (d / "status.json").exists())
