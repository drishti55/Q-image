"""
NEQR-based Quantum Machine Learning Pipeline.

Pipeline B:
Image → Preprocessing → NEQR Encoding → Quantum Kernel / Feature Extraction / VQC → Classification

Mathematical Representation:
  |I_NEQR⟩ = (1/√N) Σ_{i=0}^{N-1} |C_i⟩ ⊗ |i⟩
where:
  - n = log2(N) position qubits (|i⟩)
  - q intensity qubits (|C_i⟩ = |c^{q-1} ... c^0⟩)
  - Total qubits: n + q

Quantum Operations:
  - Hadamard superposition on position qubits
  - Multi-controlled X (basis state) mapping to intensity register
  - Quantum kernel overlap: |⟨ψ_A | ψ_B⟩|² = |⟨0| U_A† U_B |0⟩|²
  - Quantum expectation values: ⟨Z_k⟩ on intensity and position qubits
  - Variational parameterized ansatz W(θ) acting directly on NEQR state

Classical Operations:
  - Intensity quantization to q-bit precision (e.g., 2, 4, 8 bits)
  - SVM decision boundary or classical optimizer updates
"""

import numpy as np
import time
from typing import Dict, Any, List, Optional, Tuple
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit.library import RealAmplitudes
from qiskit.quantum_info import Statevector

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.neqr.encoder import NEQREncoder
from src.simulation.simulator import QuantumSimulator


class NEQRQMLPipeline:
    """
    Implements quantum machine learning operations directly on NEQR quantum states.
    """

    def __init__(
        self,
        resolution: Tuple[int, int] = (4, 4),
        intensity_bits: int = 4,
        shots: int = 0,
        seed: int = 42,
    ):
        """
        Args:
            resolution: (height, width) of images (must be power of 2 total pixels).
            intensity_bits: Number of intensity qubits (e.g. 2, 4, 8).
            shots: 0 for exact statevector, >0 for shot-based simulation.
            seed: Random seed for reproducibility.
        """
        self.resolution = resolution
        self.height, self.width = resolution
        self.num_pixels = self.height * self.width
        self.intensity_bits = intensity_bits
        self.n_pos = int(np.log2(self.num_pixels))
        self.n_intensity = intensity_bits
        self.total_qubits = self.n_pos + self.n_intensity
        self.shots = shots
        self.seed = seed
        self.simulator = QuantumSimulator(seed=seed)

    def _quantize_image(self, image: np.ndarray) -> np.ndarray:
        """Ensure image has integer values in [0, 2^intensity_bits - 1]."""
        max_val = (1 << self.intensity_bits) - 1
        if image.max() <= 1.0 and image.dtype in (np.float32, np.float64):
            # Scale from normalized [0, 1] to integer levels
            quantized = np.clip(np.round(image * max_val), 0, max_val).astype(int)
        else:
            quantized = np.clip(np.round(image), 0, max_val).astype(int)
        return quantized

    def encode_image(self, image: np.ndarray) -> QuantumCircuit:
        """Construct NEQR quantum circuit for a quantized image."""
        quantized = self._quantize_image(image)
        encoder = NEQREncoder(quantized, intensity_bits=self.intensity_bits)
        return encoder.build_circuit()

    def get_circuit_stats(self, image: np.ndarray) -> Dict[str, Any]:
        """Extract gate count, depth, qubit count from NEQR circuit."""
        quantized = self._quantize_image(image)
        encoder = NEQREncoder(quantized, intensity_bits=self.intensity_bits)
        return encoder.get_circuit_stats()

    def compute_statevector(self, image: np.ndarray) -> np.ndarray:
        """Compute statevector of NEQR circuit."""
        circuit = self.encode_image(image)
        sv = Statevector.from_instruction(circuit)
        return np.asarray(sv.data)

    def compute_kernel_entry(self, img_a: np.ndarray, img_b: np.ndarray) -> float:
        """
        Compute quantum kernel K(A, B) = |⟨ψ_A | ψ_B⟩|² between two NEQR images.
        
        In NEQR:
          |I_A⟩ = (1/√N) Σ_i |C_i^A⟩ ⊗ |i⟩
          ⟨ψ_A | ψ_B⟩ = (1/N) Σ_{i=0}^{N-1} ⟨C_i^A | C_i^B⟩ = (1/N) Σ_{i=0}^{N-1} δ(C_i^A, C_i^B)
          
        If shots > 0: runs U_A† U_B circuit and measures ground-state probability P(|00...0⟩).
        """
        quant_a = self._quantize_image(img_a).flatten()
        quant_b = self._quantize_image(img_b).flatten()

        if self.shots == 0:
            # Exact quantum overlap
            matches = np.sum(quant_a == quant_b)
            inner_prod = matches / float(self.num_pixels)
            return float(np.clip(inner_prod ** 2, 0.0, 1.0))
        else:
            # Circuit inversion test with measurement shots
            qc_a = self.encode_image(img_a)
            qc_b = self.encode_image(img_b)

            # Fixed (v2): previously the circuit was measured twice (explicit measure + run_shots'
            # measure_all) and the code read .get() on the result dict instead of its "counts",
            # so every kernel entry — even K(a, a) — came out 0. Measure exactly once here.
            circuit = QuantumCircuit(self.total_qubits)
            circuit.compose(qc_b, inplace=True)
            circuit.compose(qc_a.inverse(), inplace=True)

            result = self.simulator.run_shots(circuit, shots=self.shots)  # adds one measure_all
            counts = result["counts"]
            zero_str = "0" * self.total_qubits
            prob_0 = counts.get(zero_str, 0) / float(self.shots)
            return float(np.clip(prob_0, 0.0, 1.0))

    def compute_kernel_matrix(self, X1: np.ndarray, X2: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Compute NEQR quantum kernel matrix between sets of images.
        Uses exact analytical overlap in O(M*N):
          K(A, B) = [ (1/P) Σ δ(C_k^A, C_k^B) ]²
        """
        if self.shots > 0:
            n1 = len(X1)
            n2 = len(X2) if X2 is not None else n1
            K = np.zeros((n1, n2), dtype=np.float64)
            for i in range(n1):
                j_start = i if X2 is None else 0
                for j in range(j_start, n2):
                    img_b = X1[j] if X2 is None else X2[j]
                    val = self.compute_kernel_entry(X1[i], img_b)
                    K[i, j] = val
                    if X2 is None:
                        K[j, i] = val
            return K

        M1 = len(X1)
        q1 = np.array([self._quantize_image(x).flatten() for x in X1])
        P = q1.shape[1]
        n_levels = 2 ** self.intensity_bits
        oh1 = (q1[..., None] == np.arange(n_levels)).reshape(M1, -1).astype(np.float64)

        if X2 is None:
            matches = (oh1 @ oh1.T) / float(P)
        else:
            M2 = len(X2)
            q2 = np.array([self._quantize_image(x).flatten() for x in X2])
            oh2 = (q2[..., None] == np.arange(n_levels)).reshape(M2, -1).astype(np.float64)
            matches = (oh1 @ oh2.T) / float(P)

        K = np.clip(matches ** 2, 0.0, 1.0)
        return K

    def extract_quantum_features(self, image: np.ndarray) -> np.ndarray:
        """
        Extract quantum measurement expectation values from the NEQR state.
        
        Observable signatures:
          - Expectation of Z on position qubits: ⟨Z_{pos, j}⟩ = 0
          - Expectation of Z on intensity bit qubits: ⟨Z_{int, k}⟩ = 1 - 2*P(bit_k == 1)
          - Inter-register correlation: ⟨Z_{pos, j} ⊗ Z_{int, k}⟩
          - Spatial texture quantum expectations: row/col bit marginals
        
        Returns:
            Real feature vector of quantum expectation values.
        """
        quant = self._quantize_image(image).flatten()
        P = float(self.num_pixels)
        features = []

        # Position Z expectations (0 for uniform superposition)
        for _ in range(self.n_pos):
            features.append(0.0)

        # Intensity bit expectations: <Z_k> = (1/P) sum (1 - 2 * bit_k(C_i))
        bits = []
        for k in range(self.intensity_bits):
            bit_k = (quant >> k) & 1
            z_k = float(np.mean(1.0 - 2.0 * bit_k))
            features.append(z_k)
            bits.append(bit_k)

        # Cross correlation: Z_{pos, j} ⊗ Z_{int, k}
        idx = np.arange(self.num_pixels)
        for pos_q in range(self.n_pos):
            pos_bit = (idx >> pos_q) & 1
            for int_q in range(self.intensity_bits):
                int_bit = bits[int_q]
                parity = 1.0 - 2.0 * (pos_bit ^ int_bit)
                features.append(float(np.mean(parity)))

        # Spatial texture: row/col intensity averages
        img_2d = image.reshape(self.height, self.width)
        row_m = np.mean(img_2d, axis=1)
        col_m = np.mean(img_2d, axis=0)
        features.extend([float(v) for v in row_m])
        features.extend([float(v) for v in col_m])

        return np.array(features, dtype=np.float64)

    def build_vqc_circuit(self, image: np.ndarray, weights: np.ndarray, reps: int = 1) -> QuantumCircuit:
        """
        Build Variational Quantum Circuit:
          NEQR Encoding (U_NEQR) + Parameterized Ansatz (RealAmplitudes)
        """
        base_qc = self.encode_image(image)
        ansatz = RealAmplitudes(num_qubits=self.total_qubits, reps=reps, entanglement="linear")
        assigned = ansatz.assign_parameters(weights)

        full_qc = QuantumCircuit(self.total_qubits)
        full_qc.compose(base_qc, inplace=True)
        full_qc.compose(assigned, inplace=True)
        return full_qc
