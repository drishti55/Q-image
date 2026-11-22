"""
Quantum Kernel Computation Module.

Implements a ZZFeatureMap-based quantum kernel using statevector simulation.
The kernel value between two data points x, y is:

    K(x, y) = |⟨Φ(x)|Φ(y)⟩|²

where Φ(x) is the quantum state produced by the ZZFeatureMap encoding of x.

This is computed using the Qiskit statevector simulator for exact results
(no shot noise). This is explicitly a simulation — it does not prove
quantum speedup or advantage.
"""

import numpy as np
import time
from typing import Dict, Any, Optional, Tuple
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector


class ZZFeatureMap:
    """
    Builds a ZZFeatureMap circuit for quantum feature encoding.

    The ZZFeatureMap applies:
      1. Hadamard on all qubits
      2. Single-qubit Z rotations: RZ(2·xᵢ)
      3. Entangling ZZ interactions: CNOT + RZ(2·(π - xᵢ)·(π - xⱼ)) + CNOT

    Repeated for `reps` layers.

    This is a standard quantum feature map used in quantum kernel methods.
    Reference: Havlíček et al., "Supervised learning with quantum-enhanced
    feature spaces", Nature 567, 209–212 (2019).
    """

    def __init__(self, n_qubits: int, reps: int = 2):
        """
        Args:
            n_qubits: Number of qubits (= feature dimension)
            reps: Number of repetitions of the feature map layer
        """
        self.n_qubits = n_qubits
        self.reps = reps

    def build_circuit(self, x: np.ndarray) -> QuantumCircuit:
        """
        Build the ZZFeatureMap circuit for a single data point.

        Args:
            x: Feature vector of length n_qubits, values in [0, π]

        Returns:
            QuantumCircuit encoding the feature vector
        """
        if len(x) != self.n_qubits:
            raise ValueError(
                f"Feature vector length {len(x)} != n_qubits {self.n_qubits}"
            )

        qc = QuantumCircuit(self.n_qubits)

        for _ in range(self.reps):
            # Layer 1: Hadamard + single-qubit Z rotations
            for i in range(self.n_qubits):
                qc.h(i)
                qc.rz(2.0 * float(x[i]), i)

            # Layer 2: Entangling ZZ interactions (linear connectivity)
            for i in range(self.n_qubits - 1):
                j = i + 1
                qc.cx(i, j)
                qc.rz(2.0 * (np.pi - float(x[i])) * (np.pi - float(x[j])), j)
                qc.cx(i, j)

        return qc

    def get_circuit_stats(self, x: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        Get circuit resource statistics.

        Args:
            x: Feature vector (if None, uses zeros for structure analysis)

        Returns:
            Dictionary with qubit count, gate count, depth, gate types
        """
        if x is None:
            x = np.zeros(self.n_qubits)

        qc = self.build_circuit(x)

        gate_counts = {}
        for instr in qc.data:
            name = instr.operation.name
            gate_counts[name] = gate_counts.get(name, 0) + 1

        return {
            "qubits": qc.num_qubits,
            "gates": sum(gate_counts.values()),
            "depth": qc.depth(),
            "gate_types": gate_counts,
            "reps": self.reps,
            "feature_map": "ZZFeatureMap",
        }


class QuantumKernelComputer:
    """
    Computes quantum kernel matrices using statevector overlap.

    The quantum kernel K(x, y) = |⟨Φ(x)|Φ(y)⟩|² is computed by:
      1. Evaluating the statevectors |Φ(x)⟩ = U(x)|0⟩ and |Φ(y)⟩ = U(y)|0⟩
      2. Computing the transition amplitude ⟨Φ(x)|Φ(y)⟩
      3. Calculating fidelity |⟨Φ(x)|Φ(y)⟩|²

    This uses exact statevector evaluation (no shot noise).
    """

    def __init__(self, n_qubits: int, reps: int = 2, seed: int = 42):
        """
        Args:
            n_qubits: Number of qubits
            reps: Feature map repetitions
            seed: Random seed for simulator
        """
        self.n_qubits = n_qubits
        self.reps = reps
        self.feature_map = ZZFeatureMap(n_qubits, reps)
        self.seed = seed

        # Tracking
        self._kernel_evaluations = 0
        self._total_compute_time = 0.0

    def _compute_statevector(self, x: np.ndarray) -> np.ndarray:
        """Compute the normalized statevector for a feature vector x."""
        qc = self.feature_map.build_circuit(x)
        return np.asarray(Statevector(qc))

    def _compute_kernel_entry(self, x: np.ndarray, y: np.ndarray) -> float:
        """
        Compute a single kernel entry K(x, y) = |⟨Φ(x)|Φ(y)⟩|².

        Args:
            x, y: Feature vectors of length n_qubits

        Returns:
            Kernel value in [0, 1]
        """
        sv_x = self._compute_statevector(x)
        sv_y = self._compute_statevector(y)

        # K(x, y) = |⟨Φ(x)|Φ(y)⟩|² = |vdot(sv_x, sv_y)|²
        inner = np.vdot(sv_x, sv_y)
        kernel_value = float(np.abs(inner) ** 2)

        self._kernel_evaluations += 1
        return kernel_value

    def compute_kernel_matrix(
        self,
        X: np.ndarray,
        Y: Optional[np.ndarray] = None,
        progress_callback=None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Compute the kernel matrix between two sets of data points.

        If Y is None, computes the symmetric kernel matrix K(X, X).
        If Y is provided, computes the rectangular matrix K(X, Y).

        Args:
            X: Feature matrix (n_samples_x, n_features)
            Y: Feature matrix (n_samples_y, n_features) or None
            progress_callback: Optional callable(current, total) for progress

        Returns:
            Tuple of (kernel_matrix, stats_dict)
        """
        symmetric = Y is None
        if symmetric:
            Y = X

        n_x = X.shape[0]
        n_y = Y.shape[0]

        if symmetric:
            total_evals = n_x * (n_x + 1) // 2
        else:
            total_evals = n_x * n_y

        start_time = time.perf_counter()

        # Step 1: Precompute statevectors for all samples in X
        sv_x_list = []
        for i in range(n_x):
            sv_x_list.append(self._compute_statevector(X[i]))
            if progress_callback and (i % 10 == 0 or i == n_x - 1):
                progress_callback(i + 1, n_x + (0 if symmetric else n_y))

        sv_x = np.array(sv_x_list)  # (n_x, 2^n_qubits)

        # Step 2: Compute kernel matrix via matrix multiplication
        if symmetric:
            # Overlap matrix: sv_x @ sv_x.conj().T
            overlaps = sv_x @ sv_x.conj().T
            kernel_matrix = np.clip(np.abs(overlaps) ** 2, 0.0, 1.0)
            np.fill_diagonal(kernel_matrix, 1.0)
        else:
            # Precompute statevectors for Y
            sv_y_list = []
            for j in range(n_y):
                sv_y_list.append(self._compute_statevector(Y[j]))
                if progress_callback and (j % 10 == 0 or j == n_y - 1):
                    progress_callback(n_x + j + 1, n_x + n_y)

            sv_y = np.array(sv_y_list)  # (n_y, 2^n_qubits)
            overlaps = sv_x @ sv_y.conj().T
            kernel_matrix = np.clip(np.abs(overlaps) ** 2, 0.0, 1.0)

        compute_time = time.perf_counter() - start_time
        self._kernel_evaluations += total_evals
        self._total_compute_time += compute_time

        stats = {
            "n_x": n_x,
            "n_y": n_y,
            "symmetric": symmetric,
            "kernel_evaluations": total_evals,
            "compute_time_s": compute_time,
            "avg_time_per_entry_ms": (compute_time / max(total_evals, 1)) * 1000,
            "n_qubits": self.n_qubits,
            "feature_map_reps": self.reps,
            "simulator": "statevector (exact, no shot noise)",
        }

        return kernel_matrix, stats

    def get_feature_map_stats(self) -> Dict[str, Any]:
        """Get statistics about the feature map circuit."""
        return self.feature_map.get_circuit_stats()

    def get_feature_map_circuit(self, x: Optional[np.ndarray] = None) -> QuantumCircuit:
        """Get the feature map circuit for visualization."""
        if x is None:
            x = np.linspace(0, np.pi, self.n_qubits)
        return self.feature_map.build_circuit(x)

    def get_kernel_circuit(
        self, x: np.ndarray, y: np.ndarray
    ) -> QuantumCircuit:
        """
        Build the full kernel evaluation circuit U†(x)·U(y) for visualization.

        Args:
            x, y: Feature vectors

        Returns:
            The combined quantum circuit
        """
        circuit_y = self.feature_map.build_circuit(y)
        circuit_x = self.feature_map.build_circuit(x)
        circuit_x_dag = circuit_x.inverse()

        qc = QuantumCircuit(self.n_qubits)
        qc.compose(circuit_y, inplace=True)
        qc.compose(circuit_x_dag, inplace=True)
        return qc
