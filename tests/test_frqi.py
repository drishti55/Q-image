"""
Tests for FRQI Encoder Module.
"""

import numpy as np
import pytest
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.frqi.encoder import FRQIEncoder


class TestFRQIEncoder:
    """Tests for FRQIEncoder class."""

    # ---- Initialization tests ----

    def test_init_2x2(self):
        """Test initialization with a 2×2 image."""
        img = np.array([[0.0, 0.5], [0.25, 1.0]])
        encoder = FRQIEncoder(img)
        assert encoder.n_position_qubits == 2
        assert encoder.n_color_qubits == 1
        assert encoder.total_qubits == 3
        assert encoder.num_pixels == 4

    def test_init_4x4(self):
        """Test initialization with a 4×4 image."""
        img = np.random.rand(4, 4)
        encoder = FRQIEncoder(img)
        assert encoder.n_position_qubits == 4
        assert encoder.total_qubits == 5

    def test_init_invalid_shape(self):
        """1D image should raise ValueError."""
        with pytest.raises(ValueError, match="2D"):
            FRQIEncoder(np.array([0.0, 0.5]))

    def test_init_non_power_of_two(self):
        """Non-power-of-2 total pixels should raise ValueError."""
        with pytest.raises(ValueError, match="power of 2"):
            FRQIEncoder(np.array([[0.0, 0.5, 0.3]]))

    def test_init_out_of_range(self):
        """Values outside [0, 1] should raise ValueError."""
        with pytest.raises(ValueError, match="[0, 1]"):
            FRQIEncoder(np.array([[0.0, 1.5], [0.0, 0.0]]))

    # ---- Angle computation tests ----

    def test_angle_black_pixel(self):
        """Black pixel (0.0) should produce angle 0."""
        img = np.array([[0.0, 0.0], [0.0, 0.0]])
        encoder = FRQIEncoder(img)
        np.testing.assert_allclose(encoder.angles, [0, 0, 0, 0])

    def test_angle_white_pixel(self):
        """White pixel (1.0) should produce angle π."""
        img = np.array([[1.0, 1.0], [1.0, 1.0]])
        encoder = FRQIEncoder(img)
        np.testing.assert_allclose(encoder.angles, [np.pi] * 4)

    def test_angle_half_intensity(self):
        """Half intensity (0.5) should produce angle π/2."""
        img = np.array([[0.5, 0.5], [0.5, 0.5]])
        encoder = FRQIEncoder(img)
        np.testing.assert_allclose(encoder.angles, [np.pi / 2] * 4)

    # ---- Circuit building tests ----

    def test_build_circuit_2x2(self):
        """Circuit should be built without errors for 2×2."""
        img = np.array([[0.0, 0.5], [0.25, 1.0]])
        encoder = FRQIEncoder(img)
        circuit = encoder.build_circuit()
        assert circuit.num_qubits == 3

    def test_circuit_has_hadamards(self):
        """Circuit should have Hadamard gates on position qubits."""
        img = np.array([[0.5, 0.5], [0.5, 0.5]])
        encoder = FRQIEncoder(img)
        circuit = encoder.build_circuit()
        stats = encoder.get_circuit_stats()
        assert "h" in stats["gate_types"]
        assert stats["gate_types"]["h"] == 2  # 2 position qubits

    def test_all_black_circuit_minimal(self):
        """All-black image should have minimal gates (only Hadamards)."""
        img = np.array([[0.0, 0.0], [0.0, 0.0]])
        encoder = FRQIEncoder(img)
        circuit = encoder.build_circuit()
        stats = encoder.get_circuit_stats()
        # Should only have Hadamard gates (no rotations needed)
        assert stats["controlled_gates"] == 0

    # ---- Circuit stats tests ----

    def test_circuit_stats_structure(self):
        """Circuit stats should contain all expected keys."""
        img = np.array([[0.0, 0.5], [0.25, 1.0]])
        encoder = FRQIEncoder(img)
        stats = encoder.get_circuit_stats()
        expected_keys = [
            "representation", "qubits", "n_position_qubits",
            "n_color_qubits", "gates", "depth", "gate_types",
            "controlled_gates", "num_pixels", "image_size",
            "encoding_time",
        ]
        for key in expected_keys:
            assert key in stats, f"Missing key: {key}"

        assert stats["representation"] == "FRQI"

    # ---- Encoding info test ----

    def test_encoding_info_string(self):
        """Encoding info should return a non-empty string."""
        img = np.array([[0.0, 1.0], [0.5, 0.25]])
        encoder = FRQIEncoder(img)
        info = encoder.get_encoding_info()
        assert "FRQI" in info
        assert "2×2" in info

    # ---- Index to bits test ----

    def test_index_to_bits(self):
        """Test binary index conversion."""
        img = np.array([[0.0, 0.0], [0.0, 0.0]])
        encoder = FRQIEncoder(img)
        assert encoder._index_to_bits(0) == [0, 0]
        assert encoder._index_to_bits(1) == [1, 0]
        assert encoder._index_to_bits(2) == [0, 1]
        assert encoder._index_to_bits(3) == [1, 1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
