"""
Tests for Metrics/Evaluation Module.
"""

import numpy as np
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.metrics.evaluator import MetricsEvaluator, ExperimentResult, ResultsManager


class TestMSE:
    """Tests for Mean Squared Error."""

    def test_identical_images(self):
        """MSE of identical images should be 0."""
        img = np.array([[100, 200], [50, 150]], dtype=np.float64)
        assert MetricsEvaluator.mse(img, img) == 0.0

    def test_completely_different(self):
        """MSE of completely different images should be calculable."""
        img1 = np.array([[0, 0], [0, 0]], dtype=np.float64)
        img2 = np.array([[255, 255], [255, 255]], dtype=np.float64)
        expected = 255.0 ** 2
        assert abs(MetricsEvaluator.mse(img1, img2) - expected) < 1e-6

    def test_known_mse(self):
        """Test with known MSE value."""
        img1 = np.array([[0.0, 0.0]])
        img2 = np.array([[1.0, 0.0]])
        # MSE = (1^2 + 0^2) / 2 = 0.5
        assert abs(MetricsEvaluator.mse(img1, img2) - 0.5) < 1e-10

    def test_shape_mismatch(self):
        """Different shapes should raise ValueError."""
        img1 = np.array([[0, 0]])
        img2 = np.array([[0, 0, 0]])
        with pytest.raises(ValueError, match="Shape mismatch"):
            MetricsEvaluator.mse(img1, img2)


class TestPSNR:
    """Tests for Peak Signal-to-Noise Ratio."""

    def test_identical_images_infinity(self):
        """PSNR of identical images should be infinity."""
        img = np.array([[100, 200]], dtype=np.float64)
        assert MetricsEvaluator.psnr(img, img) == float("inf")

    def test_known_psnr(self):
        """Test PSNR with known values."""
        img1 = np.array([[0.0]])
        img2 = np.array([[0.1]])
        # MSE = 0.01, PSNR = 10*log10(1/0.01) = 20 dB
        psnr = MetricsEvaluator.psnr(img1, img2, max_val=1.0)
        assert abs(psnr - 20.0) < 0.01

    def test_higher_psnr_is_better(self):
        """Lower error should produce higher PSNR."""
        img = np.array([[0.5, 0.5]], dtype=np.float64)
        small_error = np.array([[0.51, 0.49]], dtype=np.float64)
        large_error = np.array([[0.8, 0.2]], dtype=np.float64)

        psnr_small = MetricsEvaluator.psnr(img, small_error, max_val=1.0)
        psnr_large = MetricsEvaluator.psnr(img, large_error, max_val=1.0)
        assert psnr_small > psnr_large


class TestSSIM:
    """Tests for Structural Similarity Index."""

    def test_identical_images(self):
        """SSIM of identical images should be 1.0."""
        img = np.array([[0.0, 0.5], [0.25, 1.0]])
        ssim = MetricsEvaluator.ssim(img, img)
        assert abs(ssim - 1.0) < 1e-6

    def test_different_images_less_than_1(self):
        """SSIM of different images should be less than 1."""
        img1 = np.array([[0.0, 1.0], [0.5, 0.5]])
        img2 = np.array([[1.0, 0.0], [0.5, 0.5]])
        ssim = MetricsEvaluator.ssim(img1, img2)
        assert ssim < 1.0

    def test_shape_mismatch(self):
        """Different shapes should raise ValueError."""
        img1 = np.array([[0, 0]])
        img2 = np.array([[0, 0, 0]])
        with pytest.raises(ValueError, match="Shape mismatch"):
            MetricsEvaluator.ssim(img1, img2)


class TestComputeImageQuality:
    """Tests for combined quality metric computation."""

    def test_returns_all_metrics(self):
        """Should return dict with mse, psnr, ssim."""
        img = np.array([[0.0, 0.5], [0.25, 1.0]])
        quality = MetricsEvaluator.compute_image_quality(img, img)
        assert "mse" in quality
        assert "psnr" in quality
        assert "ssim" in quality
        assert quality["mse"] == 0.0
        assert quality["psnr"] == float("inf")
        assert abs(quality["ssim"] - 1.0) < 1e-6


class TestExperimentResult:
    """Tests for ExperimentResult dataclass."""

    def test_to_dict(self):
        """ExperimentResult should convert to dict."""
        r = ExperimentResult(experiment_id="test1", representation="FRQI")
        d = r.to_dict()
        assert d["experiment_id"] == "test1"
        assert d["representation"] == "FRQI"

    def test_to_json(self):
        """ExperimentResult should convert to JSON string."""
        r = ExperimentResult(experiment_id="test1")
        j = r.to_json()
        assert '"experiment_id": "test1"' in j


class TestResultsManager:
    """Tests for results save/load."""

    def test_save_load_csv(self, tmp_path):
        """CSV save and load should preserve data."""
        results = [
            ExperimentResult(experiment_id="1", mse=0.5, psnr=20.0),
            ExperimentResult(experiment_id="2", mse=0.1, psnr=30.0),
        ]
        path = tmp_path / "test_results.csv"
        ResultsManager.save_results_csv(results, path)
        loaded = ResultsManager.load_results_csv(path)
        assert len(loaded) == 2
        assert loaded[0]["experiment_id"] == "1"

    def test_save_load_json(self, tmp_path):
        """JSON save and load should preserve data."""
        results = [
            ExperimentResult(experiment_id="1", mse=0.5),
        ]
        path = tmp_path / "test_results.json"
        ResultsManager.save_results_json(results, path)
        loaded = ResultsManager.load_results_json(path)
        assert len(loaded) == 1
        assert loaded[0]["experiment_id"] == "1"

    def test_load_nonexistent(self, tmp_path):
        """Loading non-existent file should return empty list."""
        path = tmp_path / "nonexistent.csv"
        assert ResultsManager.load_results_csv(path) == []
        assert ResultsManager.load_results_json(path) == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
