"""
Tests for Reconstruction Module.

Tests round-trip: Encode → Simulate (statevector) → Reconstruct
on known small images to verify exact reconstruction.
"""

import numpy as np
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.frqi.encoder import FRQIEncoder
from src.neqr.encoder import NEQREncoder
from src.simulation.simulator import QuantumSimulator
from src.reconstruction.reconstructor import FRQIReconstructor, NEQRReconstructor


class TestFRQIReconstruction:
    """Test FRQI encode → simulate → reconstruct round-trip."""

    def setup_method(self):
        self.simulator = QuantumSimulator(seed=42)

    def test_roundtrip_uniform_image(self):
        """Uniform 2×2 image should reconstruct exactly from statevector."""
        img = np.array([[0.5, 0.5], [0.5, 0.5]])
        encoder = FRQIEncoder(img)
        circuit = encoder.build_circuit()

        sv_result = self.simulator.run_statevector(circuit)
        reconstructor = FRQIReconstructor(
            encoder.n_position_qubits, img.shape
        )
        recon_result = reconstructor.reconstruct_from_statevector(
            sv_result["statevector"]
        )

        np.testing.assert_allclose(
            recon_result["image"], img, atol=1e-6,
            err_msg="FRQI uniform image round-trip failed"
        )

    def test_roundtrip_black_image(self):
        """All-black image should reconstruct as all zeros."""
        img = np.array([[0.0, 0.0], [0.0, 0.0]])
        encoder = FRQIEncoder(img)
        circuit = encoder.build_circuit()

        sv_result = self.simulator.run_statevector(circuit)
        reconstructor = FRQIReconstructor(
            encoder.n_position_qubits, img.shape
        )
        recon_result = reconstructor.reconstruct_from_statevector(
            sv_result["statevector"]
        )

        np.testing.assert_allclose(
            recon_result["image"], img, atol=1e-6,
            err_msg="FRQI black image round-trip failed"
        )

    def test_roundtrip_white_image(self):
        """All-white image should reconstruct as all ones."""
        img = np.array([[1.0, 1.0], [1.0, 1.0]])
        encoder = FRQIEncoder(img)
        circuit = encoder.build_circuit()

        sv_result = self.simulator.run_statevector(circuit)
        reconstructor = FRQIReconstructor(
            encoder.n_position_qubits, img.shape
        )
        recon_result = reconstructor.reconstruct_from_statevector(
            sv_result["statevector"]
        )

        np.testing.assert_allclose(
            recon_result["image"], img, atol=1e-6,
            err_msg="FRQI white image round-trip failed"
        )

    def test_roundtrip_mixed_image(self):
        """Mixed 2×2 image should reconstruct accurately from statevector."""
        img = np.array([[0.0, 0.25], [0.5, 1.0]])
        encoder = FRQIEncoder(img)
        circuit = encoder.build_circuit()

        sv_result = self.simulator.run_statevector(circuit)
        reconstructor = FRQIReconstructor(
            encoder.n_position_qubits, img.shape
        )
        recon_result = reconstructor.reconstruct_from_statevector(
            sv_result["statevector"]
        )

        np.testing.assert_allclose(
            recon_result["image"], img, atol=1e-6,
            err_msg="FRQI mixed image round-trip failed"
        )

    def test_roundtrip_4x4(self):
        """4×4 image should also round-trip correctly."""
        np.random.seed(42)
        img = np.random.rand(4, 4)
        encoder = FRQIEncoder(img)
        circuit = encoder.build_circuit()

        sv_result = self.simulator.run_statevector(circuit)
        reconstructor = FRQIReconstructor(
            encoder.n_position_qubits, img.shape
        )
        recon_result = reconstructor.reconstruct_from_statevector(
            sv_result["statevector"]
        )

        np.testing.assert_allclose(
            recon_result["image"], img, atol=1e-4,
            err_msg="FRQI 4×4 round-trip failed"
        )

    def test_shot_reconstruction_not_exact(self):
        """Shot-based reconstruction should produce reasonable results but not exact."""
        img = np.array([[0.0, 0.5], [0.25, 1.0]])
        encoder = FRQIEncoder(img)
        circuit = encoder.build_circuit()

        shots_result = self.simulator.run_shots(circuit, shots=5000)
        reconstructor = FRQIReconstructor(
            encoder.n_position_qubits, img.shape
        )
        recon_result = reconstructor.reconstruct_from_counts(
            shots_result["counts"], 5000
        )

        # Should be reasonably close but not exact
        recon = recon_result["image"]
        assert recon.shape == img.shape
        # Allow larger tolerance for shot-based
        np.testing.assert_allclose(recon, img, atol=0.15)


class TestNEQRReconstruction:
    """Test NEQR encode → simulate → reconstruct round-trip."""

    def setup_method(self):
        self.simulator = QuantumSimulator(seed=42)

    def test_roundtrip_2bit_image(self):
        """2-bit 2×2 image should reconstruct exactly from statevector."""
        img = np.array([[0, 3], [1, 2]], dtype=np.uint8)
        encoder = NEQREncoder(img, intensity_bits=2)
        circuit = encoder.build_circuit()

        sv_result = self.simulator.run_statevector(circuit)
        reconstructor = NEQRReconstructor(
            encoder.n_position_qubits,
            encoder.n_intensity_qubits,
            img.shape,
        )
        recon_result = reconstructor.reconstruct_from_statevector(
            sv_result["statevector"]
        )

        np.testing.assert_array_equal(
            recon_result["image"], img,
            err_msg="NEQR 2-bit round-trip failed"
        )

    def test_roundtrip_all_black(self):
        """All-black image should reconstruct as all zeros."""
        img = np.array([[0, 0], [0, 0]], dtype=np.uint8)
        encoder = NEQREncoder(img, intensity_bits=2)
        circuit = encoder.build_circuit()

        sv_result = self.simulator.run_statevector(circuit)
        reconstructor = NEQRReconstructor(
            encoder.n_position_qubits,
            encoder.n_intensity_qubits,
            img.shape,
        )
        recon_result = reconstructor.reconstruct_from_statevector(
            sv_result["statevector"]
        )

        np.testing.assert_array_equal(recon_result["image"], img)

    def test_roundtrip_all_white(self):
        """All-white image should reconstruct as all max values."""
        img = np.array([[3, 3], [3, 3]], dtype=np.uint8)
        encoder = NEQREncoder(img, intensity_bits=2)
        circuit = encoder.build_circuit()

        sv_result = self.simulator.run_statevector(circuit)
        reconstructor = NEQRReconstructor(
            encoder.n_position_qubits,
            encoder.n_intensity_qubits,
            img.shape,
        )
        recon_result = reconstructor.reconstruct_from_statevector(
            sv_result["statevector"]
        )

        np.testing.assert_array_equal(recon_result["image"], img)

    def test_roundtrip_4bit(self):
        """4-bit image should also round-trip correctly."""
        img = np.array([[0, 7], [15, 10]], dtype=np.uint8)
        encoder = NEQREncoder(img, intensity_bits=4)
        circuit = encoder.build_circuit()

        sv_result = self.simulator.run_statevector(circuit)
        reconstructor = NEQRReconstructor(
            encoder.n_position_qubits,
            encoder.n_intensity_qubits,
            img.shape,
        )
        recon_result = reconstructor.reconstruct_from_statevector(
            sv_result["statevector"]
        )

        np.testing.assert_array_equal(
            recon_result["image"], img,
            err_msg="NEQR 4-bit round-trip failed"
        )

    def test_shot_reconstruction_high_shots(self):
        """Shot-based NEQR reconstruction with high shots should be exact."""
        img = np.array([[0, 3], [1, 2]], dtype=np.uint8)
        encoder = NEQREncoder(img, intensity_bits=2)
        circuit = encoder.build_circuit()

        shots_result = self.simulator.run_shots(circuit, shots=5000)
        reconstructor = NEQRReconstructor(
            encoder.n_position_qubits,
            encoder.n_intensity_qubits,
            img.shape,
        )
        recon_result = reconstructor.reconstruct_from_counts(
            shots_result["counts"], 5000
        )

        # NEQR with high shots should reconstruct exactly
        np.testing.assert_array_equal(
            recon_result["image"], img,
            err_msg="NEQR shot-based round-trip failed with 5000 shots"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
