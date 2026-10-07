"""
Metrics and Evaluation Module.

Provides quantitative evaluation of quantum image encoding/reconstruction:

1. Image Quality Metrics:
   - MSE (Mean Squared Error)
   - PSNR (Peak Signal-to-Noise Ratio)
   - SSIM (Structural Similarity Index)

2. Quantum Resource Metrics:
   - Qubit count, gate count, circuit depth, gate types

3. Computational Metrics:
   - Encoding, simulation, measurement, reconstruction, total times

All metrics are computed consistently to enable fair FRQI vs NEQR comparison.
"""

import numpy as np
import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
import csv
from pathlib import Path

try:
    from skimage.metrics import structural_similarity as ssim_fn
except ImportError:
    ssim_fn = None


@dataclass
class ExperimentResult:
    """
    Structured result of a single experiment run.
    
    Contains all fields needed for experiment tracking and reproducibility.
    """
    # Experiment identification
    experiment_id: str = ""
    timestamp: str = ""
    
    # Dataset information
    dataset: str = ""
    defect_category: str = ""
    image_name: str = ""
    
    # Experimental configuration
    resolution: str = ""          # e.g., "4x4"
    image_width: int = 0
    image_height: int = 0
    intensity_precision: int = 0  # bits
    representation: str = ""      # "FRQI" or "NEQR"
    shots: int = 0
    simulator: str = ""
    
    # Quantum resource metrics
    qubits: int = 0
    n_position_qubits: int = 0
    n_color_or_intensity_qubits: int = 0
    gate_count: int = 0
    circuit_depth: int = 0
    controlled_gates: int = 0
    gate_types: str = ""  # JSON string of gate type counts
    
    # Computational metrics (seconds)
    encoding_time: float = 0.0
    simulation_time: float = 0.0
    measurement_time: float = 0.0
    reconstruction_time: float = 0.0
    total_time: float = 0.0
    
    # Image quality metrics
    mse: float = 0.0
    psnr: float = 0.0
    ssim: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class MetricsEvaluator:
    """
    Computes image quality, quantum resource, and computational metrics.
    """

    @staticmethod
    def mse(original: np.ndarray, reconstructed: np.ndarray) -> float:
        """
        Compute Mean Squared Error between original and reconstructed images.
        
        MSE = (1/N) Σ (original_i - reconstructed_i)²
        
        Args:
            original: Original image array (any dtype, will be cast to float64).
            reconstructed: Reconstructed image array (same shape).
            
        Returns:
            MSE value (0.0 for identical images).
            
        Raises:
            ValueError: If shapes don't match.
        """
        if original.shape != reconstructed.shape:
            raise ValueError(
                f"Shape mismatch: original {original.shape} vs "
                f"reconstructed {reconstructed.shape}"
            )
        orig = original.astype(np.float64)
        recon = reconstructed.astype(np.float64)
        return float(np.mean((orig - recon) ** 2))

    @staticmethod
    def psnr(
        original: np.ndarray, reconstructed: np.ndarray, max_val: float = None
    ) -> float:
        """
        Compute Peak Signal-to-Noise Ratio.
        
        PSNR = 10 × log10(MAX² / MSE)
        
        Args:
            original: Original image array.
            reconstructed: Reconstructed image array.
            max_val: Maximum possible pixel value. If None, inferred from dtype
                     or from data range.
            
        Returns:
            PSNR value in dB. Returns float('inf') if MSE is 0.
        """
        mse_val = MetricsEvaluator.mse(original, reconstructed)

        if mse_val < 1e-10:
            return 100.0  # Cap PSNR at 100 dB for plotting

        if max_val is None:
            # Infer max value from data
            if original.dtype in (np.uint8,):
                max_val = 255.0
            elif np.max(original) <= 1.0:
                max_val = 1.0
            else:
                max_val = float(np.max(original))

        return float(10 * np.log10(max_val**2 / mse_val))

    @staticmethod
    def ssim(
        original: np.ndarray,
        reconstructed: np.ndarray,
        data_range: float = None,
    ) -> float:
        """
        Compute Structural Similarity Index (SSIM).
        
        Uses scikit-image implementation when available.
        Falls back to a simplified implementation if scikit-image is not installed.
        
        Args:
            original: Original image array.
            reconstructed: Reconstructed image array.
            data_range: Dynamic range of the images. If None, auto-detected.
            
        Returns:
            SSIM value in [-1, 1] (1.0 for identical images).
        """
        if original.shape != reconstructed.shape:
            raise ValueError(
                f"Shape mismatch: original {original.shape} vs "
                f"reconstructed {reconstructed.shape}"
            )

        orig = original.astype(np.float64)
        recon = reconstructed.astype(np.float64)

        if data_range is None:
            if orig.max() <= 1.0 and orig.min() >= 0.0:
                data_range = 1.0
            else:
                data_range = float(max(orig.max(), recon.max()) - min(orig.min(), recon.min()))
                if data_range == 0:
                    data_range = 1.0

        if ssim_fn is not None and min(orig.shape) >= 3:
            # Use scikit-image SSIM
            # For very small images (< 7 pixels on a side), reduce window size
            min_dim = min(orig.shape)
            win_size = min(7, min_dim)
            if win_size % 2 == 0:
                win_size = max(win_size - 1, 3)
            
            return float(ssim_fn(
                orig, recon, data_range=data_range, win_size=win_size
            ))
        else:
            # Simplified SSIM fallback
            return MetricsEvaluator._simple_ssim(orig, recon, data_range)

    @staticmethod
    def _simple_ssim(
        img1: np.ndarray, img2: np.ndarray, data_range: float
    ) -> float:
        """
        Simplified SSIM computation (fallback when scikit-image unavailable).
        
        Uses the global SSIM formula (without windowing):
        SSIM = (2*μ₁μ₂ + C₁)(2*σ₁₂ + C₂) / ((μ₁² + μ₂² + C₁)(σ₁² + σ₂² + C₂))
        """
        C1 = (0.01 * data_range) ** 2
        C2 = (0.03 * data_range) ** 2

        mu1 = np.mean(img1)
        mu2 = np.mean(img2)
        sigma1_sq = np.var(img1)
        sigma2_sq = np.var(img2)
        sigma12 = np.mean((img1 - mu1) * (img2 - mu2))

        numerator = (2 * mu1 * mu2 + C1) * (2 * sigma12 + C2)
        denominator = (mu1**2 + mu2**2 + C1) * (sigma1_sq + sigma2_sq + C2)

        return float(numerator / denominator)

    @staticmethod
    def compute_image_quality(
        original: np.ndarray,
        reconstructed: np.ndarray,
        max_val: float = None,
    ) -> Dict[str, float]:
        """
        Compute all image quality metrics at once.
        
        Args:
            original: Original image array.
            reconstructed: Reconstructed image array.
            max_val: Maximum pixel value for PSNR.
            
        Returns:
            Dictionary with 'mse', 'psnr', 'ssim' values.
        """
        return {
            "mse": MetricsEvaluator.mse(original, reconstructed),
            "psnr": MetricsEvaluator.psnr(original, reconstructed, max_val),
            "ssim": MetricsEvaluator.ssim(original, reconstructed),
        }

    @staticmethod
    def extract_resource_metrics(circuit_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract quantum resource metrics from circuit statistics.
        
        Args:
            circuit_stats: Dictionary from encoder.get_circuit_stats().
            
        Returns:
            Standardized resource metrics dictionary.
        """
        return {
            "qubits": circuit_stats.get("qubits", 0),
            "n_position_qubits": circuit_stats.get("n_position_qubits", 0),
            "n_color_or_intensity_qubits": circuit_stats.get(
                "n_color_qubits", circuit_stats.get("n_intensity_qubits", 0)
            ),
            "gate_count": circuit_stats.get("gates", 0),
            "circuit_depth": circuit_stats.get("depth", 0),
            "controlled_gates": circuit_stats.get("controlled_gates", 0),
            "gate_types": json.dumps(circuit_stats.get("gate_types", {})),
        }


class ResultsManager:
    """
    Manages saving and loading of experiment results.
    """

    @staticmethod
    def save_results_csv(
        results: list, filepath: str | Path
    ):
        """
        Save experiment results to CSV file.
        
        Args:
            results: List of ExperimentResult objects or dicts.
            filepath: Path to save CSV file.
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        if not results:
            return

        # Convert to dicts if needed
        rows = []
        for r in results:
            if isinstance(r, ExperimentResult):
                rows.append(r.to_dict())
            else:
                rows.append(r)

        fieldnames = list(rows[0].keys())

        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def save_results_json(
        results: list, filepath: str | Path
    ):
        """
        Save experiment results to JSON file.
        
        Args:
            results: List of ExperimentResult objects or dicts.
            filepath: Path to save JSON file.
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        rows = []
        for r in results:
            if isinstance(r, ExperimentResult):
                rows.append(r.to_dict())
            else:
                rows.append(r)

        with open(filepath, "w") as f:
            json.dump(rows, f, indent=2, default=str)

    @staticmethod
    def load_results_csv(filepath: str | Path) -> list:
        """
        Load experiment results from CSV file.
        
        Args:
            filepath: Path to CSV file.
            
        Returns:
            List of dictionaries.
        """
        filepath = Path(filepath)
        if not filepath.exists():
            return []

        with open(filepath, "r") as f:
            reader = csv.DictReader(f)
            return list(reader)

    @staticmethod
    def load_results_json(filepath: str | Path) -> list:
        """
        Load experiment results from JSON file.
        
        Args:
            filepath: Path to JSON file.
            
        Returns:
            List of dictionaries.
        """
        filepath = Path(filepath)
        if not filepath.exists():
            return []

        with open(filepath, "r") as f:
            return json.load(f)
