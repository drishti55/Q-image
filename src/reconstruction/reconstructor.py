"""
Image Reconstruction Module.

Reconstructs classical images from quantum simulation results for both
FRQI and NEQR representations.

FRQI Reconstruction:
===================
From statevector:
  - Extract amplitudes for each position state
  - For position i: amplitude_|0,i⟩ = cos(θ_i)/√N, amplitude_|1,i⟩ = sin(θ_i)/√N
  - Compute θ_i = arctan(|amplitude_|1,i⟩| / |amplitude_|0,i⟩|)
  - Convert θ_i back to intensity: intensity = (θ_i / (π/2))

From measurement counts:
  - For each position i: count occurrences of color=0 and color=1
  - Estimate P(color=1|position=i) = count_1 / (count_0 + count_1)
  - sin²(θ_i) ≈ P(color=1|position=i)
  - θ_i = arcsin(√P), intensity = θ_i / (π/2)

NEQR Reconstruction:
===================
From statevector:
  - Each basis state encodes position and intensity as |intensity⟩|position⟩
  - Extract non-zero amplitude states, decode position and intensity bits
  - Read binary intensity directly

From measurement counts:
  - Parse each measured bitstring: separate position and intensity bits
  - For each position: take majority vote across measurements
  - Convert binary intensity back to integer
"""

import numpy as np
import math
import time
from typing import Dict, Any, Optional, Tuple, List
from collections import defaultdict


class FRQIReconstructor:
    """
    Reconstructs images from FRQI quantum simulation results.
    """

    def __init__(self, n_position_qubits: int, image_shape: Tuple[int, int]):
        """
        Initialize the FRQI reconstructor.
        
        Args:
            n_position_qubits: Number of position qubits used in encoding.
            image_shape: Original image shape (height, width).
        """
        self.n_position_qubits = n_position_qubits
        self.n_color_qubits = 1
        self.total_qubits = n_position_qubits + self.n_color_qubits
        self.num_pixels = 2**n_position_qubits
        self.image_shape = image_shape

    def reconstruct_from_statevector(
        self, statevector: np.ndarray
    ) -> Dict[str, Any]:
        """
        Reconstruct image from exact statevector simulation.
        
        The statevector encodes the FRQI state:
        |I⟩ = (1/√N) Σ_i (cos(θ_i)|0⟩ + sin(θ_i)|1⟩) ⊗ |i⟩
        
        Qubit ordering in Qiskit: |q_{n} q_{n-1} ... q_1 q_0⟩
        where q_0 to q_{n-1} are position qubits, q_n is the color qubit.
        
        For position i with color qubit c:
          state index = c * 2^n + i
          where i is the position index (using the n position qubits)
        
        Args:
            statevector: Complex numpy array from statevector simulation.
            
        Returns:
            Dictionary with:
                - 'image': Reconstructed 2D numpy array [0, 1]
                - 'reconstruction_time': Time taken (seconds)
                - 'pixel_values': 1D array of reconstructed intensities
        """
        start_time = time.perf_counter()

        n = self.n_position_qubits
        N = self.num_pixels
        reconstructed = np.zeros(N, dtype=np.float64)

        for pos_idx in range(N):
            # State index for color=0: pos_idx (color qubit is MSB = 0)
            # State index for color=1: pos_idx + N (color qubit is MSB = 1)
            idx_0 = pos_idx       # |0⟩|pos⟩
            idx_1 = pos_idx + N   # |1⟩|pos⟩

            amp_0 = abs(statevector[idx_0])
            amp_1 = abs(statevector[idx_1])

            # Recover θ from amplitudes
            # amp_0 = cos(θ)/√N, amp_1 = sin(θ)/√N
            if amp_0 < 1e-10 and amp_1 < 1e-10:
                theta = 0.0
            elif amp_0 < 1e-10:
                theta = np.pi / 2
            else:
                theta = np.arctan2(amp_1, amp_0)

            # Convert θ back to normalized intensity [0, 1]
            intensity = theta / (np.pi / 2)
            reconstructed[pos_idx] = np.clip(intensity, 0.0, 1.0)

        reconstruction_time = time.perf_counter() - start_time

        return {
            "image": reconstructed.reshape(self.image_shape),
            "reconstruction_time": reconstruction_time,
            "pixel_values": reconstructed,
        }

    def reconstruct_from_counts(
        self, counts: Dict[str, int], shots: int
    ) -> Dict[str, Any]:
        """
        Reconstruct image from shot-based measurement counts.
        
        For each position, estimates intensity from the ratio of 
        color=1 measurements to total measurements at that position.
        
        Bitstring format (Qiskit): "c p_{n-1} ... p_1 p_0"
        where c is the color bit and p_i are position bits.
        
        Args:
            counts: Measurement counts dict {bitstring: count}.
            shots: Total number of shots.
            
        Returns:
            Dictionary with:
                - 'image': Reconstructed 2D numpy array [0, 1]
                - 'reconstruction_time': Time taken (seconds)
                - 'pixel_values': 1D array of reconstructed intensities
                - 'position_counts': Number of measurements per position
        """
        start_time = time.perf_counter()

        n = self.n_position_qubits
        N = self.num_pixels

        # Count color=0 and color=1 for each position
        count_0 = np.zeros(N, dtype=np.float64)
        count_1 = np.zeros(N, dtype=np.float64)

        for bitstring, count in counts.items():
            # Remove spaces if any
            bits = bitstring.replace(" ", "")

            # Qiskit bitstring: MSB on left
            # bits[0] = color qubit (MSB), bits[1:] = position qubits
            color_bit = int(bits[0])
            pos_bits = bits[1:]  # remaining bits are position
            pos_idx = int(pos_bits, 2)

            if pos_idx < N:
                if color_bit == 0:
                    count_0[pos_idx] += count
                else:
                    count_1[pos_idx] += count

        # Reconstruct intensities
        reconstructed = np.zeros(N, dtype=np.float64)
        position_total = count_0 + count_1

        for pos_idx in range(N):
            total = position_total[pos_idx]
            if total == 0:
                # No measurements at this position — cannot reconstruct
                reconstructed[pos_idx] = 0.0
            else:
                # P(color=1|position) ≈ sin²(θ)
                p1 = count_1[pos_idx] / total
                # θ = arcsin(√P)
                theta = np.arcsin(np.sqrt(np.clip(p1, 0.0, 1.0)))
                reconstructed[pos_idx] = np.clip(theta / (np.pi / 2), 0.0, 1.0)

        reconstruction_time = time.perf_counter() - start_time

        return {
            "image": reconstructed.reshape(self.image_shape),
            "reconstruction_time": reconstruction_time,
            "pixel_values": reconstructed,
            "position_counts": position_total,
        }


class NEQRReconstructor:
    """
    Reconstructs images from NEQR quantum simulation results.
    """

    def __init__(
        self,
        n_position_qubits: int,
        n_intensity_qubits: int,
        image_shape: Tuple[int, int],
    ):
        """
        Initialize the NEQR reconstructor.
        
        Args:
            n_position_qubits: Number of position qubits.
            n_intensity_qubits: Number of intensity qubits.
            image_shape: Original image shape (height, width).
        """
        self.n_position_qubits = n_position_qubits
        self.n_intensity_qubits = n_intensity_qubits
        self.total_qubits = n_position_qubits + n_intensity_qubits
        self.num_pixels = 2**n_position_qubits
        self.max_intensity = 2**n_intensity_qubits - 1
        self.image_shape = image_shape

    def reconstruct_from_statevector(
        self, statevector: np.ndarray
    ) -> Dict[str, Any]:
        """
        Reconstruct image from exact statevector simulation.
        
        The statevector encodes the NEQR state:
        |I⟩ = (1/√N) Σ_i |C_i⟩|i⟩
        
        Qubit ordering in Qiskit: |int_{q-1} ... int_0 pos_{n-1} ... pos_0⟩
        State index = intensity_value * 2^n + position_index
        
        Args:
            statevector: Complex numpy array from statevector simulation.
            
        Returns:
            Dictionary with:
                - 'image': Reconstructed 2D numpy array (integer values)
                - 'reconstruction_time': Time taken (seconds)
                - 'pixel_values': 1D array of reconstructed integer intensities
        """
        start_time = time.perf_counter()

        n = self.n_position_qubits
        q = self.n_intensity_qubits
        N = self.num_pixels

        reconstructed = np.zeros(N, dtype=np.int32)

        # For each position, find the intensity with highest amplitude
        for pos_idx in range(N):
            max_amp = 0
            best_intensity = 0

            for int_val in range(2**q):
                # State index: |intensity⟩|position⟩
                state_idx = int_val * N + pos_idx
                amp = abs(statevector[state_idx])

                if amp > max_amp:
                    max_amp = amp
                    best_intensity = int_val

            reconstructed[pos_idx] = best_intensity

        reconstruction_time = time.perf_counter() - start_time

        return {
            "image": reconstructed.reshape(self.image_shape),
            "reconstruction_time": reconstruction_time,
            "pixel_values": reconstructed,
        }

    def reconstruct_from_counts(
        self, counts: Dict[str, int], shots: int
    ) -> Dict[str, Any]:
        """
        Reconstruct image from shot-based measurement counts.
        
        For each position, takes the most frequently measured intensity value
        (majority vote across shots).
        
        Bitstring format (Qiskit): "int_{q-1}...int_0 pos_{n-1}...pos_0"
        
        Args:
            counts: Measurement counts dict {bitstring: count}.
            shots: Total number of shots.
            
        Returns:
            Dictionary with:
                - 'image': Reconstructed 2D numpy array (integer values)
                - 'reconstruction_time': Time taken (seconds)
                - 'pixel_values': 1D array of reconstructed integer intensities
                - 'position_counts': Number of measurements per position
                - 'confidence': Confidence of majority vote per position
        """
        start_time = time.perf_counter()

        n = self.n_position_qubits
        q = self.n_intensity_qubits
        N = self.num_pixels

        # Collect intensity votes for each position
        position_votes: Dict[int, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        position_total = np.zeros(N, dtype=np.float64)

        for bitstring, count in counts.items():
            bits = bitstring.replace(" ", "")

            # Qiskit bitstring: MSB on left
            # bits[:q] = intensity qubits (MSB first)
            # bits[q:] = position qubits (MSB first)
            int_bits = bits[:q]
            pos_bits = bits[q:]

            pos_idx = int(pos_bits, 2)
            int_val = int(int_bits, 2)

            if pos_idx < N:
                position_votes[pos_idx][int_val] += count
                position_total[pos_idx] += count

        # Reconstruct using majority vote
        reconstructed = np.zeros(N, dtype=np.int32)
        confidence = np.zeros(N, dtype=np.float64)

        for pos_idx in range(N):
            if pos_idx in position_votes and position_votes[pos_idx]:
                votes = position_votes[pos_idx]
                best_intensity = max(votes, key=votes.get)
                reconstructed[pos_idx] = best_intensity
                total = sum(votes.values())
                confidence[pos_idx] = votes[best_intensity] / total if total > 0 else 0.0
            else:
                reconstructed[pos_idx] = 0
                confidence[pos_idx] = 0.0

        reconstruction_time = time.perf_counter() - start_time

        return {
            "image": reconstructed.reshape(self.image_shape),
            "reconstruction_time": reconstruction_time,
            "pixel_values": reconstructed,
            "position_counts": position_total,
            "confidence": confidence.reshape(self.image_shape),
        }
