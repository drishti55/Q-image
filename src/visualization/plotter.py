"""
Visualization Module.

Generates research-quality plots for quantum image processing experiments:
  - Reconstruction comparison (original vs FRQI vs NEQR)
  - Resource metrics vs resolution/precision
  - Quality metrics vs measurement shots
  - Category-wise analysis for NEU-DET dataset
  - Comparison tables
  - Circuit diagrams

All plots use clean labels, units, legends, and titles.
Figures are saved to the results/images/ directory.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for saving
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.settings import RESULTS_IMAGES_PATH, FIGURE_DPI, COLORMAP, ensure_directories
from src.metrics.evaluator import ExperimentResult


# Use a clean style for research plots
plt.style.use("seaborn-v0_8-whitegrid")


class ResultPlotter:
    """
    Generates research-quality visualizations from experiment results.
    """

    def __init__(self, output_dir: Path = None):
        """
        Initialize the plotter.
        
        Args:
            output_dir: Directory to save plots. Defaults to results/images/.
        """
        self.output_dir = output_dir or RESULTS_IMAGES_PATH
        ensure_directories()

    def plot_reconstruction_comparison(
        self,
        original: np.ndarray,
        frqi_recon: np.ndarray,
        neqr_recon: np.ndarray,
        title: str = "Reconstruction Comparison",
        filename: str = "reconstruction_comparison.png",
        frqi_metrics: Dict = None,
        neqr_metrics: Dict = None,
    ) -> str:
        """
        Plot side-by-side comparison of original, FRQI, and NEQR reconstructions.
        
        Returns:
            Path to saved figure.
        """
        fig, axes = plt.subplots(1, 3, figsize=(12, 4))

        # Original
        axes[0].imshow(original, cmap=COLORMAP, vmin=0,
                       vmax=np.max(original) if np.max(original) > 1 else 1)
        axes[0].set_title("Original", fontsize=12, fontweight="bold")
        axes[0].axis("off")

        # FRQI Reconstruction
        axes[1].imshow(frqi_recon, cmap=COLORMAP, vmin=0,
                       vmax=np.max(frqi_recon) if np.max(frqi_recon) > 1 else 1)
        frqi_title = "FRQI Reconstruction"
        if frqi_metrics:
            frqi_title += f"\nMSE={frqi_metrics.get('mse', 0):.4f}, PSNR={frqi_metrics.get('psnr', 0):.1f}dB"
        axes[1].set_title(frqi_title, fontsize=11)
        axes[1].axis("off")

        # NEQR Reconstruction
        axes[2].imshow(neqr_recon, cmap=COLORMAP, vmin=0,
                       vmax=np.max(neqr_recon) if np.max(neqr_recon) > 1 else 1)
        neqr_title = "NEQR Reconstruction"
        if neqr_metrics:
            neqr_title += f"\nMSE={neqr_metrics.get('mse', 0):.4f}, PSNR={neqr_metrics.get('psnr', 0):.1f}dB"
        axes[2].set_title(neqr_title, fontsize=11)
        axes[2].axis("off")

        fig.suptitle(title, fontsize=14, fontweight="bold", y=1.02)
        plt.tight_layout()

        save_path = self.output_dir / filename
        fig.savefig(save_path, dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close(fig)
        return str(save_path)

    def plot_resource_vs_resolution(
        self,
        results: List[ExperimentResult],
        filename: str = "resource_vs_resolution.png",
    ) -> str:
        """
        Plot quantum resource metrics vs image resolution.
        
        Generates 4 subplots: Qubits, Gates, Depth, Time vs Resolution.
        """
        # Group results by representation and resolution
        frqi_data = self._filter_results(results, "FRQI")
        neqr_data = self._filter_results(results, "NEQR")

        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        metrics = [
            ("qubits", "Total Qubits", axes[0, 0]),
            ("gate_count", "Total Gates", axes[0, 1]),
            ("circuit_depth", "Circuit Depth", axes[1, 0]),
            ("total_time", "Total Execution Time (s)", axes[1, 1]),
        ]

        for attr_name, ylabel, ax in metrics:
            frqi_resolutions, frqi_values = self._extract_by_resolution(frqi_data, attr_name)
            neqr_resolutions, neqr_values = self._extract_by_resolution(neqr_data, attr_name)

            ax.plot(frqi_resolutions, frqi_values, "o-", label="FRQI",
                    color="#2196F3", linewidth=2, markersize=8)
            ax.plot(neqr_resolutions, neqr_values, "s-", label="NEQR",
                    color="#FF5722", linewidth=2, markersize=8)

            ax.set_xlabel("Resolution", fontsize=11)
            ax.set_ylabel(ylabel, fontsize=11)
            ax.legend(fontsize=10)
            ax.grid(True, alpha=0.3)

        fig.suptitle("Quantum Resource Metrics vs Image Resolution",
                     fontsize=14, fontweight="bold")
        plt.tight_layout()

        save_path = self.output_dir / filename
        fig.savefig(save_path, dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close(fig)
        return str(save_path)

    def plot_quality_vs_shots(
        self,
        results: List[ExperimentResult],
        filename: str = "quality_vs_shots.png",
    ) -> str:
        """
        Plot reconstruction quality metrics vs measurement shots.
        
        Generates 3 subplots: MSE, PSNR, SSIM vs Shots.
        """
        frqi_data = self._filter_results(results, "FRQI")
        neqr_data = self._filter_results(results, "NEQR")

        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        metrics = [
            ("mse", "MSE (lower is better)", axes[0]),
            ("psnr", "PSNR (dB, higher is better)", axes[1]),
            ("ssim", "SSIM (higher is better)", axes[2]),
        ]

        for attr_name, ylabel, ax in metrics:
            frqi_shots, frqi_values = self._extract_by_shots(frqi_data, attr_name)
            neqr_shots, neqr_values = self._extract_by_shots(neqr_data, attr_name)

            ax.plot(frqi_shots, frqi_values, "o-", label="FRQI",
                    color="#2196F3", linewidth=2, markersize=8)
            ax.plot(neqr_shots, neqr_values, "s-", label="NEQR",
                    color="#FF5722", linewidth=2, markersize=8)

            ax.set_xlabel("Number of Shots", fontsize=11)
            ax.set_ylabel(ylabel, fontsize=11)
            ax.legend(fontsize=10)
            ax.grid(True, alpha=0.3)
            ax.set_xscale("log")

        fig.suptitle("Reconstruction Quality vs Measurement Shots",
                     fontsize=14, fontweight="bold")
        plt.tight_layout()

        save_path = self.output_dir / filename
        fig.savefig(save_path, dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close(fig)
        return str(save_path)

    def plot_category_analysis(
        self,
        results: List[ExperimentResult],
        filename: str = "category_analysis.png",
    ) -> str:
        """
        Plot average reconstruction quality by NEU-DET defect category.
        """
        frqi_data = self._filter_results(results, "FRQI")
        neqr_data = self._filter_results(results, "NEQR")

        categories = sorted(set(
            r.defect_category for r in results
            if r.defect_category and r.defect_category != "synthetic"
        ))

        if not categories:
            return ""

        fig, axes = plt.subplots(1, 3, figsize=(16, 6))
        x = np.arange(len(categories))
        width = 0.35

        for idx, (metric, ylabel, ax) in enumerate([
            ("mse", "MSE", axes[0]),
            ("psnr", "PSNR (dB)", axes[1]),
            ("ssim", "SSIM", axes[2]),
        ]):
            frqi_vals = []
            neqr_vals = []

            for cat in categories:
                frqi_cat = [r for r in frqi_data if r.defect_category == cat]
                neqr_cat = [r for r in neqr_data if r.defect_category == cat]

                frqi_vals.append(
                    np.mean([getattr(r, metric) for r in frqi_cat]) if frqi_cat else 0
                )
                neqr_vals.append(
                    np.mean([getattr(r, metric) for r in neqr_cat]) if neqr_cat else 0
                )

            bars1 = ax.bar(x - width / 2, frqi_vals, width, label="FRQI",
                           color="#2196F3", alpha=0.8)
            bars2 = ax.bar(x + width / 2, neqr_vals, width, label="NEQR",
                           color="#FF5722", alpha=0.8)

            ax.set_xlabel("Defect Category", fontsize=11)
            ax.set_ylabel(ylabel, fontsize=11)
            ax.set_xticks(x)
            ax.set_xticklabels([c.replace("_", "\n") for c in categories],
                               fontsize=9, rotation=0)
            ax.legend(fontsize=10)
            ax.grid(True, alpha=0.3, axis="y")

        fig.suptitle("Average Reconstruction Quality by Defect Category",
                     fontsize=14, fontweight="bold")
        plt.tight_layout()

        save_path = self.output_dir / filename
        fig.savefig(save_path, dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close(fig)
        return str(save_path)

    def plot_precision_comparison(
        self,
        results: List[ExperimentResult],
        filename: str = "precision_comparison.png",
    ) -> str:
        """
        Plot resource and quality metrics vs intensity precision.
        """
        frqi_data = self._filter_results(results, "FRQI")
        neqr_data = self._filter_results(results, "NEQR")

        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        metrics = [
            ("qubits", "Total Qubits", axes[0, 0]),
            ("gate_count", "Total Gates", axes[0, 1]),
            ("circuit_depth", "Circuit Depth", axes[1, 0]),
            ("mse", "MSE", axes[1, 1]),
        ]

        for attr_name, ylabel, ax in metrics:
            frqi_bits = sorted(set(r.intensity_precision for r in frqi_data))
            neqr_bits = sorted(set(r.intensity_precision for r in neqr_data))

            frqi_vals = [
                np.mean([getattr(r, attr_name) for r in frqi_data
                         if r.intensity_precision == b])
                for b in frqi_bits
            ]
            neqr_vals = [
                np.mean([getattr(r, attr_name) for r in neqr_data
                         if r.intensity_precision == b])
                for b in neqr_bits
            ]

            ax.plot(frqi_bits, frqi_vals, "o-", label="FRQI",
                    color="#2196F3", linewidth=2, markersize=8)
            ax.plot(neqr_bits, neqr_vals, "s-", label="NEQR",
                    color="#FF5722", linewidth=2, markersize=8)

            ax.set_xlabel("Intensity Precision (bits)", fontsize=11)
            ax.set_ylabel(ylabel, fontsize=11)
            ax.legend(fontsize=10)
            ax.grid(True, alpha=0.3)

        fig.suptitle("Metrics vs Intensity Precision",
                     fontsize=14, fontweight="bold")
        plt.tight_layout()

        save_path = self.output_dir / filename
        fig.savefig(save_path, dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close(fig)
        return str(save_path)

    def plot_comparison_table(
        self,
        frqi_result: ExperimentResult,
        neqr_result: ExperimentResult,
        filename: str = "comparison_table.png",
    ) -> str:
        """
        Generate a formatted comparison table as an image.
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.axis("off")

        rows = [
            ["Qubits", str(frqi_result.qubits), str(neqr_result.qubits)],
            ["Position Qubits", str(frqi_result.n_position_qubits),
             str(neqr_result.n_position_qubits)],
            ["Color/Intensity Qubits",
             str(frqi_result.n_color_or_intensity_qubits),
             str(neqr_result.n_color_or_intensity_qubits)],
            ["Gates", str(frqi_result.gate_count), str(neqr_result.gate_count)],
            ["Circuit Depth", str(frqi_result.circuit_depth),
             str(neqr_result.circuit_depth)],
            ["Controlled Gates", str(frqi_result.controlled_gates),
             str(neqr_result.controlled_gates)],
            ["Encoding Time (s)", f"{frqi_result.encoding_time:.4f}",
             f"{neqr_result.encoding_time:.4f}"],
            ["Simulation Time (s)", f"{frqi_result.simulation_time:.4f}",
             f"{neqr_result.simulation_time:.4f}"],
            ["Reconstruction Time (s)", f"{frqi_result.reconstruction_time:.4f}",
             f"{neqr_result.reconstruction_time:.4f}"],
            ["Total Time (s)", f"{frqi_result.total_time:.4f}",
             f"{neqr_result.total_time:.4f}"],
            ["MSE", f"{frqi_result.mse:.6f}", f"{neqr_result.mse:.6f}"],
            ["PSNR (dB)", f"{frqi_result.psnr:.2f}", f"{neqr_result.psnr:.2f}"],
            ["SSIM", f"{frqi_result.ssim:.4f}", f"{neqr_result.ssim:.4f}"],
        ]

        table = ax.table(
            cellText=rows,
            colLabels=["Metric", "FRQI", "NEQR"],
            cellLoc="center",
            loc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.5)

        # Style header
        for j in range(3):
            table[0, j].set_facecolor("#333333")
            table[0, j].set_text_props(color="white", fontweight="bold")

        # Alternate row colors
        for i in range(1, len(rows) + 1):
            color = "#f0f0f0" if i % 2 == 0 else "#ffffff"
            for j in range(3):
                table[i, j].set_facecolor(color)

        title = (f"FRQI vs NEQR Comparison\n"
                 f"{frqi_result.image_name} @ {frqi_result.resolution}, "
                 f"{frqi_result.intensity_precision}-bit")
        ax.set_title(title, fontsize=13, fontweight="bold", pad=20)

        save_path = self.output_dir / filename
        fig.savefig(save_path, dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close(fig)
        return str(save_path)

    def generate_all_plots(
        self,
        all_results: Dict[str, List[ExperimentResult]],
    ) -> Dict[str, str]:
        """
        Generate all research visualizations from experiment results.
        
        Returns:
            Dictionary mapping plot name to file path.
        """
        plots = {}

        if "resolution" in all_results and all_results["resolution"]:
            plots["resource_vs_resolution"] = self.plot_resource_vs_resolution(
                all_results["resolution"]
            )

        if "precision" in all_results and all_results["precision"]:
            plots["precision_comparison"] = self.plot_precision_comparison(
                all_results["precision"]
            )

        if "shots" in all_results and all_results["shots"]:
            plots["quality_vs_shots"] = self.plot_quality_vs_shots(
                all_results["shots"]
            )

        if "neu_det" in all_results and all_results["neu_det"]:
            plots["category_analysis"] = self.plot_category_analysis(
                all_results["neu_det"]
            )

        print(f"\nGenerated {len(plots)} plots:")
        for name, path in plots.items():
            print(f"  {name}: {path}")

        return plots

    # =========================================================================
    # Helper Methods
    # =========================================================================

    @staticmethod
    def _filter_results(
        results: List[ExperimentResult], representation: str
    ) -> List[ExperimentResult]:
        """Filter results by representation type."""
        return [r for r in results if r.representation == representation]

    @staticmethod
    def _extract_by_resolution(
        results: List[ExperimentResult], metric: str
    ) -> Tuple[List[str], List[float]]:
        """Extract metric values grouped by resolution."""
        res_map = defaultdict(list)
        for r in results:
            res_map[r.resolution].append(getattr(r, metric))

        resolutions = sorted(res_map.keys(), key=lambda x: int(x.split("x")[0]))
        values = [np.mean(res_map[r]) for r in resolutions]
        return resolutions, values

    @staticmethod
    def _extract_by_shots(
        results: List[ExperimentResult], metric: str
    ) -> Tuple[List[int], List[float]]:
        """Extract metric values grouped by shot count."""
        shots_map = defaultdict(list)
        for r in results:
            val = getattr(r, metric)
            if val != float("inf") and not np.isnan(val):
                shots_map[r.shots].append(val)

        shots = sorted(shots_map.keys())
        values = [np.mean(shots_map[s]) for s in shots]
        return shots, values
