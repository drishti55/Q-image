"""
Tests for Image Preprocessing Module.
"""

import numpy as np
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.preprocessing.image_processor import ImageProcessor


class TestImageProcessor:
    """Tests for ImageProcessor class."""

    def setup_method(self):
        self.processor = ImageProcessor(random_seed=42)

    # ---- Resize tests ----

    def test_resize_valid_sizes(self):
        """Test resizing to valid power-of-2 sizes."""
        img = np.random.randint(0, 256, (200, 200), dtype=np.uint8)
        for size in [(2, 2), (4, 4), (8, 8)]:
            resized = self.processor.resize_image(img, size)
            assert resized.shape == (size[1], size[0])

    def test_resize_invalid_size(self):
        """Test that non-power-of-2 sizes raise ValueError."""
        img = np.random.randint(0, 256, (10, 10), dtype=np.uint8)
        with pytest.raises(ValueError, match="powers of 2"):
            self.processor.resize_image(img, (3, 3))

    # ---- Quantization tests ----

    def test_quantize_8bit_identity(self):
        """8-bit quantization should return a copy of the original."""
        img = np.array([[0, 128, 255]], dtype=np.uint8)
        q = self.processor.quantize_intensity(img, 8)
        np.testing.assert_array_equal(q, img)

    def test_quantize_2bit(self):
        """2-bit quantization should produce values in [0, 3]."""
        img = np.array([[0, 85, 170, 255]], dtype=np.uint8)
        q = self.processor.quantize_intensity(img, 2)
        assert q.min() >= 0
        assert q.max() <= 3

    def test_quantize_4bit(self):
        """4-bit quantization should produce values in [0, 15]."""
        img = np.array([[0, 64, 128, 255]], dtype=np.uint8)
        q = self.processor.quantize_intensity(img, 4)
        assert q.min() >= 0
        assert q.max() <= 15

    def test_quantize_invalid_bits(self):
        """Invalid bit count should raise ValueError."""
        img = np.array([[0]], dtype=np.uint8)
        with pytest.raises(ValueError):
            self.processor.quantize_intensity(img, 0)
        with pytest.raises(ValueError):
            self.processor.quantize_intensity(img, 9)

    # ---- Normalization tests ----

    def test_normalize_frqi_range(self):
        """FRQI normalization should produce values in [0, 1]."""
        img = np.array([[0, 128, 255]], dtype=np.uint8)
        norm = self.processor.normalize_for_frqi(img, 8)
        assert norm.min() >= 0.0
        assert norm.max() <= 1.0
        assert abs(norm[0, 0] - 0.0) < 1e-10
        assert abs(norm[0, 2] - 1.0) < 1e-10

    def test_normalize_neqr_range(self):
        """NEQR normalization should keep integer values in range."""
        img = np.array([[0, 128, 255]], dtype=np.uint8)
        neqr = self.processor.normalize_for_neqr(img, 8)
        assert neqr.min() >= 0
        assert neqr.max() <= 255

    # ---- Synthetic image tests ----

    def test_synthetic_gradient(self):
        """Gradient image should have increasing values left to right."""
        result = self.processor.create_synthetic_image((4, 4), "gradient", 8)
        img = result["image"]
        assert img.shape == (4, 4)
        # First row should be non-decreasing
        for i in range(3):
            assert img[0, i] <= img[0, i + 1]

    def test_synthetic_checkerboard(self):
        """Checkerboard should alternate between 0 and max."""
        result = self.processor.create_synthetic_image((4, 4), "checkerboard", 8)
        img = result["image"]
        assert img[0, 0] == 255
        assert img[0, 1] == 0
        assert img[1, 0] == 0
        assert img[1, 1] == 255

    def test_synthetic_uniform(self):
        """Uniform image should have all same values."""
        result = self.processor.create_synthetic_image((2, 2), "uniform", 8)
        img = result["image"]
        assert np.all(img == img[0, 0])

    # ---- Flatten test ----

    def test_flatten_row_major(self):
        """Flatten should be in row-major order."""
        img = np.array([[1, 2], [3, 4]], dtype=np.uint8)
        flat = self.processor.flatten_image(img)
        np.testing.assert_array_equal(flat, [1, 2, 3, 4])

    # ---- Preprocess pipeline test ----

    def test_preprocess_returns_all_keys(self):
        """Preprocess pipeline should return all expected keys."""
        # Create a small temp image
        img = np.random.randint(0, 256, (20, 20), dtype=np.uint8)

        # Save and load
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            from PIL import Image
            Image.fromarray(img).save(f.name)
            result = self.processor.preprocess(f.name, (4, 4), 8)

        expected_keys = [
            "original", "resized", "quantized", "frqi_normalized",
            "neqr_values", "pixel_matrix", "metadata",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

        assert result["resized"].shape == (4, 4)
        assert result["metadata"]["target_size"] == (4, 4)

    def test_pixel_info_string(self):
        """get_pixel_info should return a non-empty string."""
        img = np.array([[0, 255], [128, 64]], dtype=np.uint8)
        info = self.processor.get_pixel_info(img, 8)
        assert "2x2" in info
        assert "4 pixels" in info


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
