"""
Path configuration and historical-result protection for Q-ImageLab v2.

Environment variables
---------------------
QIL_DATASET_PATH     Root of the NEU-DET dataset (must contain train/images and
                     validation/images). Default: <project>/NEU-DET.
                     There is NO silent fallback to any other location.
QIL_RESULTS_V2       Root for all v2 outputs. Default: <project>/results/qml_v2.
QIL_ALLOW_V0_WRITES  Set to "1" to deliberately allow legacy (Protocol V0) code to write
                     under <project>/results. Unset by default: historical results are
                     immutable evidence.
QIL_PROTECT_V2       Set to "1" (done by every Protocol V3 driver) to make results/qml_v2 immutable too:
                     V3 runs write only to results/qml_v3 (QIL_RESULTS_V2 is pointed there).
QIL_PROTECT_V3       Set to "1" (done by every Protocol V4 driver) to make results/qml_v3 immutable as well:
                     V4 runs write only to results/qml_v4.
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HISTORICAL_RESULTS_ROOT = PROJECT_ROOT / "results"
DEFAULT_V2_ROOT = HISTORICAL_RESULTS_ROOT / "qml_v2"
DEFAULT_V3_ROOT = HISTORICAL_RESULTS_ROOT / "qml_v3"
DEFAULT_V4_ROOT = HISTORICAL_RESULTS_ROOT / "qml_v4"

V2_SUBDIRS = (
    "manifests", "experiments", "aggregates", "predictions", "reconstructions",
    "circuits", "logs", "reports", "cache",
)


class HistoricalWriteError(PermissionError):
    """Raised when code attempts to write into an immutable historical results path."""


def dataset_root() -> Path:
    env = os.environ.get("QIL_DATASET_PATH")
    return Path(env).expanduser().resolve() if env else (PROJECT_ROOT / "NEU-DET").resolve()


def v2_root(create: bool = True) -> Path:
    env = os.environ.get("QIL_RESULTS_V2")
    root = Path(env).expanduser().resolve() if env else DEFAULT_V2_ROOT
    if create:
        for sub in V2_SUBDIRS:
            (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def _under(p: Path, root: Path) -> bool:
    try:
        p.relative_to(root.resolve())
        return True
    except ValueError:
        return False


def is_historical_path(path: Path | str) -> bool:
    """True if `path` lies under <project>/results but outside the writable roots (results/qml_v2,
    results/qml_v3). With QIL_PROTECT_V2=1, results/qml_v2 is treated as historical as well."""
    p = Path(path).expanduser().resolve()
    if not _under(p, HISTORICAL_RESULTS_ROOT):
        return False
    if _under(p, DEFAULT_V4_ROOT):
        return False
    if _under(p, DEFAULT_V3_ROOT):
        return os.environ.get("QIL_PROTECT_V3") == "1"
    if _under(p, DEFAULT_V2_ROOT):
        return os.environ.get("QIL_PROTECT_V2") == "1"
    return True


def assert_writable(path: Path | str) -> None:
    """Refuse writes into historical result directories unless explicitly allowed."""
    if os.environ.get("QIL_ALLOW_V0_WRITES") == "1":
        return
    if is_historical_path(path):
        raise HistoricalWriteError(
            f"Refusing to write {path}: historical (Protocol V0) results under "
            f"{HISTORICAL_RESULTS_ROOT} are immutable. Write v2 outputs to {DEFAULT_V2_ROOT} "
            "or set QIL_ALLOW_V0_WRITES=1 deliberately."
        )
