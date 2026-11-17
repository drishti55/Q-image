"""
Image Reconstruction Evaluator for FRQI and NEQR Quantum States.

Executes actual quantum reconstruction from statevector or measurement shots:
  Image -> Preprocess -> Quantum Circuit -> Simulator -> Reconstructor -> Metrics & Difference Maps
"""

import numpy as np
import time
import io
import base64
from typing import Dict, Any, Optional, Tuple
from PIL import Image

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.frqi.encoder import FRQIEncoder
from src.neqr.encoder import NEQREncoder
from src.simulation.simulator import QuantumSimulator
from src.reconstruction.reconstructor import FRQIReconstructor, NEQRReconstructor
from src.metrics.evaluator import MetricsEvaluator


def array_to_base64_png(arr: np.ndarray) -> str:
    """Convert a 2D numpy array [0, 1] or [0, 255] to base64 PNG string."""
    if arr.max() <= 1.0 and arr.min() >= 0.0:
        uint_img = (np.clip(arr, 0.0, 1.0) * 255.0).astype(np.uint8)
    else:
        uint_img = np.clip(arr, 0, 255).astype(np.uint8)

    # Scale up small resolutions (e.g. 2x2, 4x4, 8x8) using nearest-neighbor for clear visualization
    h, w = uint_img.shape
    if max(h, w) < 128:
        scale = max(1, 128 // max(h, w))
        pil_img = Image.fromarray(uint_img, mode="L").resize(
            (w * scale, h * scale), Image.Resampling.NEAREST
        )
    else:
        pil_img = Image.fromarray(uint_img, mode="L")

    buffer = io.BytesIO()
    pil_img.save(buffer, format="PNG")
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"


class QuantumReconstructionEvaluator:
    """Evaluates image reconstruction fidelity for FRQI and NEQR representations."""

    def __init__(self, seed: int = 42):
        self.simulator = QuantumSimulator(seed=seed)

    def evaluate_frqi(
        self,
        image: np.ndarray,
        resolution: Tuple[int, int] = (4, 4),
        shots: int = 0,
    ) -> Dict[str, Any]:
        """
        Run genuine FRQI quantum reconstruction.
        """
        t0 = time.perf_counter()
        encoder = FRQIEncoder(image)
        circuit = encoder.build_circuit()
        build_time = encoder.get_circuit_stats()["encoding_time"]

        sim_t0 = time.perf_counter()
        if shots == 0:
            sv_res = self.simulator.run_statevector(circuit)
            sim_time = time.perf_counter() - sim_t0
            reconstructor = FRQIReconstructor(encoder.n_position_qubits, resolution)
            rec_res = reconstructor.reconstruct_from_statevector(sv_res["statevector"])
        else:
            shots_res = self.simulator.run_shots(circuit, shots=shots)
            sim_time = shots_res["simulation_time"]
            reconstructor = FRQIReconstructor(encoder.n_position_qubits, resolution)
            rec_res = reconstructor.reconstruct_from_counts(shots_res["counts"], shots=shots)

        recon_img = rec_res["image"]
        diff_img = np.abs(image - recon_img)

        # Metrics
        mse = MetricsEvaluator.mse(image, recon_img)
        psnr = MetricsEvaluator.psnr(image, recon_img, max_val=1.0)
        ssim = MetricsEvaluator.ssim(image, recon_img, data_range=1.0)
        total_time = time.perf_counter() - t0

        return {
            "representation": "FRQI",
            "resolution": f"{resolution[0]}x{resolution[1]}",
            "shots": shots,
            "success": True,
            "mse": float(mse),
            "psnr": 100.0 if np.isinf(psnr) else float(psnr),
            "ssim": float(ssim),
            "encoding_time": float(build_time),
            "simulation_time": float(sim_time),
            "reconstruction_time": float(rec_res["reconstruction_time"]),
            "total_time": float(total_time),
            "original_b64": array_to_base64_png(image),
            "reconstructed_b64": array_to_base64_png(recon_img),
            "diff_b64": array_to_base64_png(diff_img),
        }

    def evaluate_neqr(
        self,
        image: np.ndarray,
        resolution: Tuple[int, int] = (4, 4),
        intensity_bits: int = 4,
        shots: int = 0,
    ) -> Dict[str, Any]:
        """
        Run genuine NEQR quantum reconstruction.
        """
        t0 = time.perf_counter()
        max_val = (1 << intensity_bits) - 1
        quantized = np.clip(np.round(image * max_val), 0, max_val).astype(int)

        encoder = NEQREncoder(quantized, intensity_bits=intensity_bits)
        circuit = encoder.build_circuit()
        build_time = encoder.get_circuit_stats()["encoding_time"]

        sim_t0 = time.perf_counter()
        if shots == 0:
            sv_res = self.simulator.run_statevector(circuit)
            sim_time = time.perf_counter() - sim_t0
            reconstructor = NEQRReconstructor(
                encoder.n_position_qubits, intensity_bits, resolution
            )
            rec_res = reconstructor.reconstruct_from_statevector(sv_res["statevector"])
        else:
            shots_res = self.simulator.run_shots(circuit, shots=shots)
            sim_time = shots_res["simulation_time"]
            reconstructor = NEQRReconstructor(
                encoder.n_position_qubits, intensity_bits, resolution
            )
            rec_res = reconstructor.reconstruct_from_counts(shots_res["counts"], shots=shots)

        # Normalize reconstructed image back to [0, 1] for fair comparison with original
        recon_norm = rec_res["image"].astype(np.float64) / float(max_val)
        diff_img = np.abs(image - recon_norm)

        mse = MetricsEvaluator.mse(image, recon_norm)
        psnr = MetricsEvaluator.psnr(image, recon_norm, max_val=1.0)
        ssim = MetricsEvaluator.ssim(image, recon_norm, data_range=1.0)
        total_time = time.perf_counter() - t0

        return {
            "representation": "NEQR",
            "resolution": f"{resolution[0]}x{resolution[1]}",
            "intensity_bits": intensity_bits,
            "shots": shots,
            "success": True,
            "mse": float(mse),
            "psnr": 100.0 if np.isinf(psnr) else float(psnr),
            "ssim": float(ssim),
            "encoding_time": float(build_time),
            "simulation_time": float(sim_time),
            "reconstruction_time": float(rec_res["reconstruction_time"]),
            "total_time": float(total_time),
            "original_b64": array_to_base64_png(image),
            "reconstructed_b64": array_to_base64_png(recon_norm),
            "diff_b64": array_to_base64_png(diff_img),
        }

    def evaluate_paired_reconstruction(
        self,
        image: np.ndarray,
        resolution: Tuple[int, int] = (4, 4),
        intensity_bits: int = 4,
        shots: int = 0,
    ) -> Dict[str, Any]:
        """Run paired FRQI and NEQR reconstruction on the exact same preprocessed image."""
        frqi_res = self.evaluate_frqi(image, resolution=resolution, shots=shots)
        neqr_res = self.evaluate_neqr(
            image, resolution=resolution, intensity_bits=intensity_bits, shots=shots
        )
        return {
            "resolution": f"{resolution[0]}x{resolution[1]}",
            "original_b64": frqi_res["original_b64"],
            "frqi": frqi_res,
            "neqr": neqr_res,
        }
