"""
FRQI (Flexible Representation of Quantum Images) Encoder.

Mathematical Basis:
==================

FRQI encodes a 2^n image (with N = 2^n total pixels) using:
  - n position qubits to index pixel locations
  - 1 color/intensity qubit to store intensity via rotation angle

The FRQI quantum state for an image is:

    |I⟩ = (1/√N) Σ_{i=0}^{N-1} (cos(θ_i)|0⟩ + sin(θ_i)|1⟩) ⊗ |i⟩

where:
  - |i⟩ is the n-qubit binary representation of pixel position i
  - θ_i ∈ [0, π/2] encodes the intensity of pixel i
  - θ_i = normalized_intensity × π/2
  - normalized_intensity ∈ [0, 1] maps from quantized pixel value

Circuit Construction:
====================

1. Apply Hadamard gates to all n position qubits → uniform superposition
2. For each pixel position i (0 to N-1):
   a. Apply X gates to position qubits where bit of i is 0 (position selection)
   b. Apply multi-controlled Ry(2θ_i) gate: all position qubits control, 
      color qubit is target
   c. Apply X gates again to undo position selection (restore)

This produces the correct FRQI state because:
- Step 2a-c selects exactly position |i⟩ and rotates the color qubit by θ_i
- The controlled rotation only acts when all position qubits match |i⟩

Resource Requirements:
=====================
- Qubits: n + 1  (where N = 2^n total pixels; for a w×h image, n = log2(w×h))
- Controlled rotations: N (one per pixel)
- Each controlled rotation uses n control qubits → decomposes into O(n) basic gates

References:
==========
Le, P.Q., Dong, F., Hirota, K. (2011). A Flexible Representation of Quantum Images
for Polynomial Preparation, Image Compression, and Processing Operations.
Quantum Information Processing, 10(1), 63-84.
"""

import numpy as np
import math
import time
from typing import Dict, Any, Optional, Tuple

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister


class FRQIEncoder:
    """
    Encodes a grayscale image into a quantum circuit using FRQI representation.
    
    The encoder takes a 2D image array with normalized intensity values [0, 1]
    and constructs a quantum circuit that prepares the FRQI quantum state.
    """

    def __init__(self, image: np.ndarray):
        """
        Initialize the FRQI encoder.
        
        Args:
            image: 2D numpy array with normalized float values in [0, 1].
                   Shape must be (H, W) where H×W is a power of 2.
                   
        Raises:
            ValueError: If image dimensions are invalid.
        """
        self._validate_image(image)
        self.image = image
        self.height, self.width = image.shape
        self.num_pixels = self.height * self.width
        self.n_position_qubits = int(math.log2(self.num_pixels))
        self.n_color_qubits = 1
        self.total_qubits = self.n_position_qubits + self.n_color_qubits

        # Flatten image to 1D in row-major order
        self.pixel_values = image.flatten()

        # Convert intensities to rotation angles
        # θ_i = intensity × π/2, so Ry rotation angle = 2θ_i = intensity × π
        self.angles = self._compute_angles()

        # Circuit will be built on demand
        self._circuit = None
        self._encoding_time = None

    def _validate_image(self, image: np.ndarray):
        """Validate image for FRQI encoding."""
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
        if np.any(image < 0) or np.any(image > 1):
            raise ValueError(
                f"Pixel values must be in [0, 1], got range [{image.min()}, {image.max()}]"
            )

    def _compute_angles(self) -> np.ndarray:
        """
        Compute rotation angles from normalized intensities.
        
        Mapping: intensity ∈ [0, 1] → θ ∈ [0, π/2]
        The Ry gate rotation angle is 2θ = intensity × π
        
        Returns:
            Array of Ry rotation angles (2θ values).
        """
        # θ_i = intensity_i × π/2
        # Ry rotation angle = 2 × θ_i = intensity_i × π
        return self.pixel_values * np.pi

    def build_circuit(self) -> QuantumCircuit:
        """
        Build the FRQI quantum circuit.
        
        Circuit structure:
        1. Position qubits: |q_0⟩ ... |q_{n-1}⟩  (index register)
        2. Color qubit: |q_n⟩  (intensity register)
        
        Returns:
            Qiskit QuantumCircuit implementing FRQI encoding.
        """
        start_time = time.perf_counter()

        # Create registers
        # Position qubits: indices 0 to n-1
        # Color qubit: index n
        pos_reg = QuantumRegister(self.n_position_qubits, name="pos")
        color_reg = QuantumRegister(self.n_color_qubits, name="color")
        circuit = QuantumCircuit(pos_reg, color_reg, name="FRQI")

        # Step 1: Apply Hadamard to all position qubits (uniform superposition)
        for i in range(self.n_position_qubits):
            circuit.h(pos_reg[i])

        circuit.barrier()

        # Step 2: For each pixel, apply controlled rotation
        for pixel_idx in range(self.num_pixels):
            angle = self.angles[pixel_idx]

            # Skip if angle is effectively zero (black pixel)
            if abs(angle) < 1e-10:
                continue

            # Get binary representation of pixel position
            pos_bits = self._index_to_bits(pixel_idx)

            # Step 2a: Apply X gates where bit is 0 (to select this position)
            for bit_idx, bit_val in enumerate(pos_bits):
                if bit_val == 0:
                    circuit.x(pos_reg[bit_idx])

            # Step 2b: Apply multi-controlled Ry rotation
            # Control: all position qubits, Target: color qubit
            if self.n_position_qubits == 1:
                circuit.cry(angle, pos_reg[0], color_reg[0])
            else:
                circuit.mcry(
                    angle,
                    q_controls=[pos_reg[i] for i in range(self.n_position_qubits)],
                    q_target=color_reg[0],
                )

            # Step 2c: Undo X gates (restore position qubits)
            for bit_idx, bit_val in enumerate(pos_bits):
                if bit_val == 0:
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
                - n_color_qubits: Number of color/intensity qubits
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
            "representation": "FRQI",
            "qubits": self.total_qubits,
            "n_position_qubits": self.n_position_qubits,
            "n_color_qubits": self.n_color_qubits,
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
        """Get a human-readable summary of the FRQI encoding."""
        stats = self.get_circuit_stats()
        lines = [
            "=" * 60,
            "FRQI Encoding Summary",
            "=" * 60,
            f"Image size: {self.width}×{self.height} ({self.num_pixels} pixels)",
            f"Position qubits: {self.n_position_qubits}",
            f"Color qubit: {self.n_color_qubits}",
            f"Total qubits: {self.total_qubits}",
            f"Total gates: {stats['gates']}",
            f"Circuit depth: {stats['depth']}",
            f"Controlled gates: {stats['controlled_gates']}",
            f"Gate types: {stats['gate_types']}",
            f"Encoding time: {stats['encoding_time']:.4f}s",
            "",
            "Angle mapping (per pixel):",
        ]

        for i, (val, angle) in enumerate(zip(self.pixel_values, self.angles)):
            r, c = divmod(i, self.width)
            theta = angle / 2  # θ = Ry_angle / 2
            lines.append(
                f"  Pixel ({r},{c}): intensity={val:.4f}, "
                f"θ={theta:.4f} rad, Ry_angle={angle:.4f} rad"
            )

        lines.append("=" * 60)
        return "\n".join(lines)
