"""
NEQR (Novel Enhanced Quantum Representation) Encoder.

Mathematical Basis:
==================

NEQR encodes a 2^n image (with N = 2^n total pixels) using:
  - n position qubits to index pixel locations
  - q intensity qubits to store pixel values as binary strings

The NEQR quantum state for an image is:

    |I⟩ = (1/√N) Σ_{i=0}^{N-1} |C_i⟩ ⊗ |i⟩

where:
  - |i⟩ is the n-qubit binary representation of pixel position i
  - |C_i⟩ = |c_i^{q-1} c_i^{q-2} ... c_i^0⟩ is the q-bit binary
    representation of pixel intensity value C_i
  - q is the number of intensity bits (e.g., 8 for 256 gray levels)

Circuit Construction:
====================

1. Apply Hadamard gates to all n position qubits → uniform superposition
2. For each pixel position i (0 to N-1):
   Convert intensity C_i to binary: c^{q-1} c^{q-2} ... c^0
   For each intensity bit j (0 to q-1):
     If c^j == 1:
       a. Apply X gates to position qubits where bit of i is 0 (selection)
       b. Apply multi-controlled X (CNOT) gate: position qubits control,
          intensity qubit j is target
       c. Apply X gates again to undo selection (restore)

Key Difference from FRQI:
========================
- NEQR uses basis-state encoding (|0⟩ or |1⟩) instead of angle encoding
- NEQR uses multiple intensity qubits instead of a single color qubit
- NEQR provides exact binary representation of intensity values
- NEQR requires more qubits but allows direct intensity readout

Resource Requirements:
=====================
- Qubits: n + q  (where n = log2(N), q = intensity bits)
- Multi-controlled X gates: up to N × q (one per set bit per pixel)
- Each MCX uses n control qubits → decomposes into O(n) basic gates

References:
==========
Zhang, Y., Lu, K., Gao, Y., Wang, M. (2013). NEQR: A Novel Enhanced Quantum
Representation of Digital Images. Quantum Information Processing, 12(8), 2833-2860.
"""

import numpy as np
import math
import time
from typing import Dict, Any, Optional, Tuple, List

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister


class NEQREncoder:
    """
    Encodes a grayscale image into a quantum circuit using NEQR representation.
    
    The encoder takes a 2D image array with integer intensity values
    and constructs a quantum circuit that prepares the NEQR quantum state.
    
    This implementation is completely independent from FRQI —
    it uses basis-state encoding (X gates) rather than rotation gates.
    """

    def __init__(self, image: np.ndarray, intensity_bits: int = 8):
        """
        Initialize the NEQR encoder.
        
        Args:
            image: 2D numpy array with integer values in [0, 2^intensity_bits - 1].
                   Shape must be (H, W) where H×W is a power of 2.
            intensity_bits: Number of bits for intensity encoding (e.g., 2, 4, 8).
                   
        Raises:
            ValueError: If image dimensions or values are invalid.
        """
        self.intensity_bits = intensity_bits
        self._validate_image(image)
        self.image = image
        self.height, self.width = image.shape
        self.num_pixels = self.height * self.width
        self.n_position_qubits = int(math.log2(self.num_pixels))
        self.n_intensity_qubits = intensity_bits
        self.total_qubits = self.n_position_qubits + self.n_intensity_qubits

        # Flatten image to 1D in row-major order
        self.pixel_values = image.flatten().astype(int)

        # Pre-compute binary representations
        self.binary_values = self._compute_binary_values()

        # Circuit will be built on demand
        self._circuit = None
        self._encoding_time = None

    def _validate_image(self, image: np.ndarray):
        """Validate image for NEQR encoding."""
        if image.ndim != 2:
            raise ValueError(f"Image must be 2D, got shape {image.shape}")

        h, w = image.shape
        total = h * w
        if total == 0:
            raise ValueError("Image cannot be empty")
        if total & (total - 1) != 0:
            raise ValueError(
                f"Total pixel count must be a power of 2, got {total} ({h}×{w})"
            )

        max_val = 2**self.intensity_bits - 1
        if np.any(image < 0) or np.any(image > max_val):
            raise ValueError(
                f"Pixel values must be in [0, {max_val}] for {self.intensity_bits}-bit "
                f"encoding, got range [{image.min()}, {image.max()}]"
            )

    def _compute_binary_values(self) -> List[List[int]]:
        """
        Convert all pixel intensity values to binary representation.
        
        Returns:
            List of binary lists, each of length intensity_bits.
            Bit ordering: [bit_0 (LSB), bit_1, ..., bit_{q-1} (MSB)]
        """
        binary_values = []
        for val in self.pixel_values:
            bits = self._intensity_to_binary(int(val))
            binary_values.append(bits)
        return binary_values

    def _intensity_to_binary(self, intensity: int) -> List[int]:
        """
        Convert integer intensity to binary bit list.
        
        Args:
            intensity: Integer pixel value.
            
        Returns:
            List of bits [bit_0 (LSB), ..., bit_{q-1} (MSB)].
        """
        bits = []
        for i in range(self.intensity_bits):
            bits.append((intensity >> i) & 1)
        return bits

    def build_circuit(self) -> QuantumCircuit:
        """
        Build the NEQR quantum circuit.
        
        Circuit structure:
        1. Position qubits: |q_0⟩ ... |q_{n-1}⟩  (coordinate register)
        2. Intensity qubits: |q_n⟩ ... |q_{n+q-1}⟩  (grayscale register)
        
        Returns:
            Qiskit QuantumCircuit implementing NEQR encoding.
        """
        start_time = time.perf_counter()

        # Create registers
        pos_reg = QuantumRegister(self.n_position_qubits, name="pos")
        int_reg = QuantumRegister(self.n_intensity_qubits, name="intensity")
        circuit = QuantumCircuit(pos_reg, int_reg, name="NEQR")

        # Step 1: Apply Hadamard to all position qubits (uniform superposition)
        for i in range(self.n_position_qubits):
            circuit.h(pos_reg[i])

        circuit.barrier()

        # Step 2: For each pixel, encode its binary intensity value
        for pixel_idx in range(self.num_pixels):
            binary_val = self.binary_values[pixel_idx]

            # Check if any bit is set (skip all-zero intensity = black)
            if not any(b == 1 for b in binary_val):
                continue

            # Get binary representation of pixel position
            pos_bits = self._index_to_bits(pixel_idx)

            # Apply X gates to select this position
            x_gates_applied = []
            for bit_idx, bit_val in enumerate(pos_bits):
                if bit_val == 0:
                    circuit.x(pos_reg[bit_idx])
                    x_gates_applied.append(bit_idx)

            # For each intensity bit that is 1, apply MCX
            for int_bit_idx, int_bit_val in enumerate(binary_val):
                if int_bit_val == 1:
                    # Multi-controlled X: position qubits control, intensity qubit target
                    if self.n_position_qubits == 1:
                        circuit.cx(pos_reg[0], int_reg[int_bit_idx])
                    else:
                        circuit.mcx(
                            control_qubits=[pos_reg[i] for i in range(self.n_position_qubits)],
                            target_qubit=int_reg[int_bit_idx],
                        )

            # Undo X gates (restore position qubits)
            for bit_idx in x_gates_applied:
                circuit.x(pos_reg[bit_idx])

        self._circuit = circuit
        self._encoding_time = time.perf_counter() - start_time

        return circuit

    def _index_to_bits(self, index: int) -> list:
        """
        Convert pixel index to binary bit list.
        
        Returns bits in order [q_0, q_1, ..., q_{n-1}] where q_0 is LSB.
        
        Args:
            index: Pixel position index.
            
        Returns:
            List of bit values (0 or 1).
        """
        bits = []
        for i in range(self.n_position_qubits):
            bits.append((index >> i) & 1)
        return bits

    def get_circuit(self) -> QuantumCircuit:
        """Get the built circuit, building it if necessary."""
        if self._circuit is None:
            self.build_circuit()
        return self._circuit

    def get_circuit_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive circuit statistics.
        
        Returns:
            Dictionary with:
                - qubits: Total qubit count
                - n_position_qubits: Number of position qubits
                - n_intensity_qubits: Number of intensity qubits
                - gates: Total gate count
                - depth: Circuit depth
                - gate_types: Dict of gate name → count
                - controlled_gates: Count of multi-controlled gates
                - encoding_time: Time to build circuit (seconds)
        """
        circuit = self.get_circuit()

        # Count gates by type
        gate_counts = {}
        controlled_count = 0
        total_gates = 0

        for instruction in circuit.data:
            gate_name = instruction.operation.name
            if gate_name == "barrier":
                continue
            gate_counts[gate_name] = gate_counts.get(gate_name, 0) + 1
            total_gates += 1
            if len(instruction.qubits) > 1:
                controlled_count += 1

        return {
            "representation": "NEQR",
            "qubits": self.total_qubits,
            "n_position_qubits": self.n_position_qubits,
            "n_intensity_qubits": self.n_intensity_qubits,
            "intensity_bits": self.intensity_bits,
            "gates": total_gates,
            "depth": circuit.depth(),
            "gate_types": gate_counts,
            "controlled_gates": controlled_count,
            "num_pixels": self.num_pixels,
            "image_size": (self.width, self.height),
            "encoding_time": self._encoding_time,
        }

    def get_circuit_diagram(self, output: str = "text") -> str:
        """
        Get a visual representation of the circuit.
        
        Args:
            output: Output format - 'text' for ASCII, 'mpl' for matplotlib.
            
        Returns:
            Circuit diagram as string (text) or matplotlib figure (mpl).
        """
        circuit = self.get_circuit()
        if output == "text":
            return circuit.draw(output="text").__str__()
        elif output == "mpl":
            return circuit.draw(output="mpl")
        else:
            raise ValueError(f"Unknown output format: {output}")

    def get_encoding_info(self) -> str:
        """Get a human-readable summary of the NEQR encoding."""
        stats = self.get_circuit_stats()
        lines = [
            "=" * 60,
            "NEQR Encoding Summary",
            "=" * 60,
            f"Image size: {self.width}×{self.height} ({self.num_pixels} pixels)",
            f"Intensity precision: {self.intensity_bits} bits "
            f"({2**self.intensity_bits} levels)",
            f"Position qubits: {self.n_position_qubits}",
            f"Intensity qubits: {self.n_intensity_qubits}",
            f"Total qubits: {self.total_qubits}",
            f"Total gates: {stats['gates']}",
            f"Circuit depth: {stats['depth']}",
            f"Controlled gates: {stats['controlled_gates']}",
            f"Gate types: {stats['gate_types']}",
            f"Encoding time: {stats['encoding_time']:.4f}s",
            "",
            "Binary encoding (per pixel):",
        ]

        for i, (val, binary) in enumerate(
            zip(self.pixel_values, self.binary_values)
        ):
            r, c = divmod(i, self.width)
            bin_str = "".join(str(b) for b in reversed(binary))  # MSB first
            lines.append(
                f"  Pixel ({r},{c}): intensity={val:3d}, "
                f"binary={bin_str}"
            )

        lines.append("=" * 60)
        return "\n".join(lines)
