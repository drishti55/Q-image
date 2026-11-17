"""Historical (Protocol V0) results must be protected from any write."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.v2.paths import (  # noqa: E402
    HISTORICAL_RESULTS_ROOT, DEFAULT_V2_ROOT, HistoricalWriteError, assert_writable, is_historical_path,
)


def test_historical_paths_detected():
    assert is_historical_path(HISTORICAL_RESULTS_ROOT / "qml" / "qml_experiments.csv")
    assert is_historical_path(HISTORICAL_RESULTS_ROOT / "models" / "model_comparison.csv")
    assert is_historical_path(HISTORICAL_RESULTS_ROOT / "experiments" / "all_results.csv")
    assert not is_historical_path(DEFAULT_V2_ROOT / "experiments" / "x.json")


def test_assert_writable_blocks_historical(tmp_path, monkeypatch):
    monkeypatch.delenv("QIL_ALLOW_V0_WRITES", raising=False)
    with pytest.raises(HistoricalWriteError):
        assert_writable(HISTORICAL_RESULTS_ROOT / "models" / "split_info.json")
    assert_writable(tmp_path / "ok.json")  # non-historical paths are fine


def test_legacy_results_manager_refuses_historical(monkeypatch):
    monkeypatch.delenv("QIL_ALLOW_V0_WRITES", raising=False)
    from src.metrics.evaluator import ResultsManager
    with pytest.raises(HistoricalWriteError):
        ResultsManager.save_results_json([{"a": 1}], HISTORICAL_RESULTS_ROOT / "experiments" / "all_results.json")
