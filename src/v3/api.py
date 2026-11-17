"""Read-only Protocol V3 API (/api/v3). Serves results/qml_v3 files only; never computes or edits results.
Env QIL_RESULTS_V3 overrides the root (tests)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from src.v2.paths import DEFAULT_V3_ROOT

router = APIRouter(prefix="/api/v3", tags=["protocol-v3"])


def _root() -> Path:
    env = os.environ.get("QIL_RESULTS_V3")
    return Path(env).expanduser().resolve() if env else DEFAULT_V3_ROOT


def _read(p: Path):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


@router.get("/health")
def health():
    r = _root()
    return {"api": "qimagelab-v3", "results_root_exists": r.exists(),
            "playground_present": (r / "playground" / "playground_3x3.json").exists(),
            "results_present": (r / "aggregates" / "v3_results.json").exists(),
            "frozen": (r / "aggregates" / "frozen_selection.json").exists()}


@router.get("/playground")
def playground():
    d = _read(_root() / "playground" / "playground_3x3.json")
    if d is None:
        raise HTTPException(404, "V3 playground data not built — run `python scripts/v3/build_playground_v3.py`")
    return d


@router.get("/results")
def results():
    d = _read(_root() / "aggregates" / "v3_results.json")
    if d is None:
        raise HTTPException(404, "V3 results not available yet — run the V3 chain and `python scripts/v3/analyze_v3.py`")
    return d
