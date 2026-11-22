"""
FRQI-based Quantum Machine Learning Pipeline.

Pipeline A:
Image → Preprocessing → FRQI Encoding → Quantum Kernel / Feature Extraction / VQC → Classification

Mathematical Representation:
  |I_FRQI⟩ = (1/√N) Σ_{i=0}^{N-1} (cos(θ_i)|0⟩ + sin(θ_i)|1⟩) ⊗ |i⟩
where:
  - n = log2(N) position qubits (|i⟩)
  - 1 color qubit (rotation θ_i = intensity_i * π/2)
  - Total qubits: n + 1

Quantum Operations:
  - Hadamard superposition on position qubits
  - Multi-controlled Ry(2θ_i) to color qubit
  - Quantum kernel overlap: |⟨ψ_A | ψ_B⟩|² = |⟨0| U_A† U_B |0⟩|²
  - Quantum expectation values: ⟨Z_k⟩ across color and position registers
  - Variational parameterized ansatz W(θ) acting directly on FRQI state

Classical Operations:
  - Image normalization and resizing to power-of-2 dimensions
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

from src.frqi.encoder import FRQIEncoder
from src.simulation.simulator import QuantumSimulator


class FRQIQMLPipeline:
    """
    Implements quantum machine learning operations directly on FRQI quantum states.
    """

    def __init__(self, resolution: Tuple[int, int] = (4, 4), shots: int = 0, seed: int = 42):
        """
        Args:
            resolution: (height, width) of images (must be power of 2 total pixels).
            shots: 0 for exact statevector, >0 for shot-based simulation.
            seed: Random seed for reproducibility.
        """
        self.resolution = resolution
        self.height, self.width = resolution
        self.num_pixels = self.height * self.width
        self.n_pos = int(np.log2(self.num_pixels))
        self.n_color = 1
        self.total_qubits = self.n_pos + self.n_color
        self.shots = shots
        self.seed = seed
        self.simulator = QuantumSimulator(seed=seed)

    def encode_image(self, image: np.ndarray) -> QuantumCircuit:
        """Construct FRQI quantum circuit for a normalized [0, 1] image."""
        if image.shape != self.resolution:
            raise ValueError(f"Expected shape {self.resolution}, got {image.shape}")
        encoder = FRQIEncoder(image)
        return encoder.build_circuit()

    def get_circuit_stats(self, image: np.ndarray) -> Dict[str, Any]:
        """Extract gate count, depth, qubit count from FRQI circuit."""
        encoder = FRQIEncoder(image)
        return encoder.get_circuit_stats()

    def compute_statevector(self, image: np.ndarray) -> np.ndarray:
        """Compute statevector of FRQI circuit."""
        circuit = self.encode_image(image)
        sv = Statevector.from_instruction(circuit)
        return np.asarray(sv.data)

    def compute_kernel_entry(self, img_a: np.ndarray, img_b: np.ndarray) -> float:
        """
        Compute quantum kernel K(A, B) = |⟨ψ_A | ψ_B⟩|² between two FRQI images.
        
        In FRQI:
          ⟨ψ_A | ψ_B⟩ = (1/N) Σ_{i=0}^{N-1} cos(θ_i^A - θ_i^B)
          K(A, B) = [ (1/N) Σ cos(θ_i^A - θ_i^B) ]²
          
        If shots > 0: runs U_A† U_B circuit and measures ground-state probability P(|00...0⟩).
        """
        if self.shots == 0:
            # Exact quantum overlap
            angles_a = img_a.flatten() * (np.pi / 2.0)
            angles_b = img_b.flatten() * (np.pi / 2.0)
            inner_prod = np.mean(np.cos(angles_a - angles_b))
            return float(np.clip(inner_prod ** 2, 0.0, 1.0))
        else:
            # Circuit inversion test with measurement shots
            qc_a = self.encode_image(img_a)
            qc_b = self.encode_image(img_b)
            
            # Combine: U_A† U_B
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
        Compute FRQI quantum kernel matrix between sets of images.
        Uses exact analytical overlap in O(M*N):
          K(A, B) = [ (1/P) Σ cos(θ_k^A - θ_k^B) ]² = [ (1/P) (cos(θ^A) @ cos(θ^B).T + sin(θ^A) @ sin(θ^B).T) ]²
        """
        if self.shots > 0:
            # Fallback to pairwise shot execution if shots requested
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
        angles_1 = X1.reshape(M1, -1) * (np.pi / 2.0)
        P = angles_1.shape[1]
        C1 = np.cos(angles_1)
        S1 = np.sin(angles_1)

        if X2 is None:
            overlap = (C1 @ C1.T + S1 @ S1.T) / float(P)
        else:
            M2 = len(X2)
            angles_2 = X2.reshape(M2, -1) * (np.pi / 2.0)
            C2 = np.cos(angles_2)
            S2 = np.sin(angles_2)
            overlap = (C1 @ C2.T + S1 @ S2.T) / float(P)

        K = np.clip(overlap ** 2, 0.0, 1.0)
        return K

    def extract_quantum_features(self, image: np.ndarray) -> np.ndarray:
        """
        Extract quantum measurement expectation values from the FRQI state.
        
        Observable signatures:
          - Color qubit expectation: ⟨Z_color⟩ = (1/N) Σ cos(2θ_i) = (1/N) Σ cos(π * I_i)
          - Color X-basis expectation: ⟨X_color⟩ = (1/N) Σ sin(2θ_i) = (1/N) Σ sin(π * I_i)
          - Position marginals: ⟨Z_{pos, j}⟩
          - Parity & correlation observables: ⟨Z_{pos, j} ⊗ Z_color⟩
          - Spatial contrast & texture quantum expectations
        
        Returns:
            Real feature vector of quantum expectation values.
        """
        angles = image.flatten() * (np.pi / 2.0)
        N = float(self.num_pixels)
        features = []

        # Color observables
        z_col = float(np.mean(np.cos(2.0 * angles)))
        x_col = float(np.mean(np.sin(2.0 * angles)))
        features.extend([z_col, x_col])

        # Position Z expectations (0 for uniform superposition, computed analytically)
        for _ in range(self.n_pos):
            features.append(0.0)

        # Cross correlation: Z_pos_j ⊗ Z_color
        # For each position bit j: difference of cos(2*theta) between bit=0 and bit=1
        idx = np.arange(self.num_pixels)
        for pos_q in range(self.n_pos):
            mask = ((idx >> pos_q) & 1) == 0
            val_0 = np.sum(np.cos(2.0 * angles[mask]))
            val_1 = np.sum(np.cos(2.0 * angles[~mask]))
            features.append(float((val_0 - val_1) / N))

        # Spatial texture quantum expectations: row/col variations
        img_2d = image.reshape(self.height, self.width)
        row_z = np.mean(np.cos(2.0 * img_2d * (np.pi / 2.0)), axis=1)
        col_z = np.mean(np.cos(2.0 * img_2d * (np.pi / 2.0)), axis=0)
        features.extend([float(v) for v in row_z])
        features.extend([float(v) for v in col_z])

        # Contrast observable
        features.append(float(np.std(np.cos(2.0 * angles))))

        return np.array(features, dtype=np.float64)

    def build_vqc_circuit(self, image: np.ndarray, weights: np.ndarray, reps: int = 1) -> QuantumCircuit:
        """
        Build Variational Quantum Circuit:
          FRQI Encoding (U_FRQI) + Parameterized Ansatz (RealAmplitudes)
        """
        base_qc = self.encode_image(image)
        ansatz = RealAmplitudes(num_qubits=self.total_qubits, reps=reps, entanglement="full")
        assigned = ansatz.assign_parameters(weights)
        
        full_qc = QuantumCircuit(self.total_qubits)
        full_qc.compose(base_qc, inplace=True)
        full_qc.compose(assigned, inplace=True)
        return full_qc
