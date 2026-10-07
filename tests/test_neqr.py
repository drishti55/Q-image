"""
Tests for NEQR Encoder Module.
"""

import numpy as np
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.neqr.encoder import NEQREncoder


class TestNEQREncoder:
    """Tests for NEQREncoder class."""

    # ---- Initialization tests ----

    def test_init_2x2_8bit(self):
        """Test initialization with a 2×2 image, 8-bit precision."""
        img = np.array([[0, 128], [64, 255]], dtype=np.uint8)
        encoder = NEQREncoder(img, intensity_bits=8)
        assert encoder.n_position_qubits == 2
        assert encoder.n_intensity_qubits == 8
        assert encoder.total_qubits == 10
        assert encoder.num_pixels == 4

    def test_init_2x2_2bit(self):
        """Test initialization with 2-bit precision."""
        img = np.array([[0, 1], [2, 3]], dtype=np.uint8)
        encoder = NEQREncoder(img, intensity_bits=2)
        assert encoder.n_intensity_qubits == 2
        assert encoder.total_qubits == 4  # 2 pos + 2 int

    def test_init_4x4(self):
        """Test initialization with a 4×4 image."""
        img = np.random.randint(0, 16, (4, 4), dtype=np.uint8)
        encoder = NEQREncoder(img, intensity_bits=4)
        assert encoder.n_position_qubits == 4
        assert encoder.n_intensity_qubits == 4
        assert encoder.total_qubits == 8

    def test_init_invalid_shape(self):
        """1D image should raise ValueError."""
        with pytest.raises(ValueError, match="2D"):
            NEQREncoder(np.array([0, 128], dtype=np.uint8))

    def test_init_non_power_of_two(self):
        """Non-power-of-2 total pixels should raise ValueError."""
        with pytest.raises(ValueError, match="power of 2"):
            NEQREncoder(np.array([[0, 1, 2]], dtype=np.uint8))

    def test_init_value_out_of_range(self):
        """Values exceeding max for given bits should raise ValueError."""
        # 2-bit max is 3, but we have 4
        with pytest.raises(ValueError, match="[0, 3]"):
            NEQREncoder(np.array([[0, 4], [0, 0]], dtype=np.uint8), intensity_bits=2)

    # ---- Binary conversion tests ----

    def test_intensity_to_binary_zero(self):
        """Zero intensity should give all zeros."""
        img = np.array([[0, 0], [0, 0]], dtype=np.uint8)
        encoder = NEQREncoder(img, intensity_bits=4)
        assert encoder._intensity_to_binary(0) == [0, 0, 0, 0]

    def test_intensity_to_binary_max(self):
        """Max intensity should give all ones."""
        img = np.array([[0, 0], [0, 0]], dtype=np.uint8)
        encoder = NEQREncoder(img, intensity_bits=4)
        assert encoder._intensity_to_binary(15) == [1, 1, 1, 1]

    def test_intensity_to_binary_specific(self):
        """Test specific binary values."""
        img = np.array([[0, 0], [0, 0]], dtype=np.uint8)
        encoder = NEQREncoder(img, intensity_bits=4)
        # 5 = 0101 binary, LSB first: [1, 0, 1, 0]
        assert encoder._intensity_to_binary(5) == [1, 0, 1, 0]
        # 10 = 1010 binary, LSB first: [0, 1, 0, 1]
        assert encoder._intensity_to_binary(10) == [0, 1, 0, 1]

    # ---- Circuit building tests ----

    def test_build_circuit_2x2(self):
        """Circuit should be built without errors for 2×2."""
        img = np.array([[0, 3], [1, 2]], dtype=np.uint8)
        encoder = NEQREncoder(img, intensity_bits=2)
        circuit = encoder.build_circuit()
        assert circuit.num_qubits == 4  # 2 pos + 2 int

    def test_circuit_has_hadamards(self):
        """Circuit should have Hadamard gates on position qubits."""
        img = np.array([[1, 1], [1, 1]], dtype=np.uint8)
        encoder = NEQREncoder(img, intensity_bits=2)
        circuit = encoder.build_circuit()
        stats = encoder.get_circuit_stats()
        assert "h" in stats["gate_types"]
        assert stats["gate_types"]["h"] == 2  # 2 position qubits

    def test_all_black_minimal(self):
        """All-black (zero) image should have minimal gates."""
        img = np.array([[0, 0], [0, 0]], dtype=np.uint8)
        encoder = NEQREncoder(img, intensity_bits=2)
        circuit = encoder.build_circuit()
        stats = encoder.get_circuit_stats()
        assert stats["controlled_gates"] == 0

    # ---- Circuit stats tests ----

    def test_circuit_stats_structure(self):
        """Circuit stats should contain all expected keys."""
        img = np.array([[0, 3], [1, 2]], dtype=np.uint8)
        encoder = NEQREncoder(img, intensity_bits=2)
        stats = encoder.get_circuit_stats()
        expected_keys = [
            "representation", "qubits", "n_position_qubits",
            "n_intensity_qubits", "intensity_bits", "gates",
            "depth", "gate_types", "controlled_gates",
            "num_pixels", "image_size", "encoding_time",
        ]
        for key in expected_keys:
            assert key in stats, f"Missing key: {key}"

        assert stats["representation"] == "NEQR"

    # ---- NEQR uses more qubits than FRQI ----

    def test_neqr_more_qubits_than_frqi(self):
        """
        NEQR should use more qubits than FRQI for the same image.
        FRQI: n_position + 1 color
        NEQR: n_position + q intensity
        """
        img_neqr = np.array([[0, 3], [1, 2]], dtype=np.uint8)
        encoder_neqr = NEQREncoder(img_neqr, intensity_bits=2)
        # FRQI would use 2+1=3 qubits; NEQR uses 2+2=4 qubits
        assert encoder_neqr.total_qubits > 3

    # ---- Encoding info test ----

    def test_encoding_info_string(self):
        """Encoding info should return a non-empty string."""
        img = np.array([[0, 3], [1, 2]], dtype=np.uint8)
        encoder = NEQREncoder(img, intensity_bits=2)
        info = encoder.get_encoding_info()
        assert "NEQR" in info
        assert "2 bits" in info

    # ---- Index to bits test ----

    def test_index_to_bits(self):
        """Test binary index conversion."""
        img = np.array([[0, 0], [0, 0]], dtype=np.uint8)
        encoder = NEQREncoder(img, intensity_bits=2)
        assert encoder._index_to_bits(0) == [0, 0]
        assert encoder._index_to_bits(1) == [1, 0]
        assert encoder._index_to_bits(2) == [0, 1]
        assert encoder._index_to_bits(3) == [1, 1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
