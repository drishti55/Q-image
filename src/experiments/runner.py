"""
Experiment Runner Module.

Provides a framework for running controlled quantum image processing experiments:
  - Experiment A: Image resolution comparison
  - Experiment B: Intensity precision comparison
  - Experiment C: Image complexity comparison
  - Experiment D: Measurement shots comparison
  - NEU-DET dataset experiments

Each experiment follows the standardized pipeline:
  Load → Preprocess → Encode (timed) → Simulate (timed) → 
  Measure (timed) → Reconstruct (timed) → Evaluate → Store
"""

import numpy as np
import time
import json
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
import uuid

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.settings import (
    IMAGE_SIZES, DEFAULT_IMAGE_SIZE, INTENSITY_BITS_OPTIONS,
    DEFAULT_INTENSITY_BITS, SHOTS_LIST, DEFAULT_SHOTS,
    DEFECT_CATEGORIES, IMAGES_PER_CATEGORY, RANDOM_SEED,
    RESULTS_EXPERIMENTS_PATH, RESULTS_IMAGES_PATH,
    ensure_directories, get_image_paths,
)
from src.preprocessing.image_processor import ImageProcessor
from src.frqi.encoder import FRQIEncoder
from src.neqr.encoder import NEQREncoder
from src.simulation.simulator import QuantumSimulator
from src.reconstruction.reconstructor import FRQIReconstructor, NEQRReconstructor
from src.metrics.evaluator import (
    MetricsEvaluator, ExperimentResult, ResultsManager,
)


class ExperimentRunner:
    """
    Manages and executes controlled quantum image processing experiments.
    
    Ensures consistent experimental conditions between FRQI and NEQR
    for fair comparison.
    """

    def __init__(self, seed: int = RANDOM_SEED):
        """
        Initialize the experiment runner.
        
        Args:
            seed: Random seed for reproducibility.
        """
        self.seed = seed
        self.processor = ImageProcessor(random_seed=seed)
        self.simulator = QuantumSimulator(seed=seed)
        self.metrics = MetricsEvaluator()
        self.results_manager = ResultsManager()
        ensure_directories()

    def run_single_experiment(
        self,
        image: np.ndarray,
        image_name: str,
        size: Tuple[int, int],
        bits: int,
        shots: int,
        representation: str,
        category: str = "synthetic",
        dataset: str = "synthetic",
        use_statevector: bool = False,
    ) -> ExperimentResult:
        """
        Run a single experiment: encode → simulate → reconstruct → evaluate.
        
        Args:
            image: Original grayscale image (any size, uint8).
            image_name: Name identifier for the image.
            size: Target quantum-compatible resolution (width, height).
            bits: Intensity precision in bits.
            shots: Number of measurement shots.
            representation: "FRQI" or "NEQR".
            category: Defect category or "synthetic".
            dataset: Dataset name.
            use_statevector: If True, use statevector simulation for reconstruction.
            
        Returns:
            ExperimentResult with all metrics filled.
        """
        result = ExperimentResult()
        result.experiment_id = str(uuid.uuid4())[:8]
        result.timestamp = datetime.now().isoformat()
        result.dataset = dataset
        result.defect_category = category
        result.image_name = image_name
        result.resolution = f"{size[0]}x{size[1]}"
        result.image_width = size[0]
        result.image_height = size[1]
        result.intensity_precision = bits
        result.representation = representation
        result.shots = shots
        result.simulator = "statevector" if use_statevector else "aer"

        total_start = time.perf_counter()

        try:
            # Step 1: Preprocess
            resized = self.processor.resize_image(image, size)
            quantized = self.processor.quantize_intensity(resized, bits)

            if representation == "FRQI":
                result = self._run_frqi(
                    quantized, bits, shots, result, use_statevector
                )
            elif representation == "NEQR":
                result = self._run_neqr(
                    quantized, bits, shots, result, use_statevector
                )
            else:
                raise ValueError(f"Unknown representation: {representation}")

        except Exception as e:
            print(f"  ERROR in {representation} experiment: {e}")
            # Leave metrics at 0 to indicate failure

        result.total_time = time.perf_counter() - total_start
        return result

    def _run_frqi(
        self,
        quantized: np.ndarray,
        bits: int,
        shots: int,
        result: ExperimentResult,
        use_statevector: bool,
    ) -> ExperimentResult:
        """Run FRQI encoding, simulation, reconstruction, and evaluation."""
        # Normalize for FRQI [0, 1]
        frqi_image = self.processor.normalize_for_frqi(quantized, bits)

        # Encode
        encoder = FRQIEncoder(frqi_image)
        circuit = encoder.build_circuit()
        stats = encoder.get_circuit_stats()

        result.encoding_time = stats["encoding_time"]
        result.qubits = stats["qubits"]
        result.n_position_qubits = stats["n_position_qubits"]
        result.n_color_or_intensity_qubits = stats["n_color_qubits"]
        result.gate_count = stats["gates"]
        result.circuit_depth = stats["depth"]
        result.controlled_gates = stats["controlled_gates"]
        result.gate_types = json.dumps(stats["gate_types"])

        # Simulate and reconstruct
        reconstructor = FRQIReconstructor(
            encoder.n_position_qubits, frqi_image.shape
        )

        if use_statevector:
            sim_result = self.simulator.run_statevector(circuit)
            result.simulation_time = sim_result["simulation_time"]
            result.measurement_time = 0.0
            recon_result = reconstructor.reconstruct_from_statevector(
                sim_result["statevector"]
            )
        else:
            sim_result = self.simulator.run_shots(circuit, shots)
            result.simulation_time = sim_result["simulation_time"]
            result.measurement_time = sim_result["measurement_time"]
            recon_result = reconstructor.reconstruct_from_counts(
                sim_result["counts"], shots
            )

        result.reconstruction_time = recon_result["reconstruction_time"]

        # Evaluate quality (both in [0, 1] range for FRQI)
        quality = self.metrics.compute_image_quality(
            frqi_image, recon_result["image"], max_val=1.0
        )
        result.mse = quality["mse"]
        result.psnr = quality["psnr"]
        result.ssim = quality["ssim"]

        return result

    def _run_neqr(
        self,
        quantized: np.ndarray,
        bits: int,
        shots: int,
        result: ExperimentResult,
        use_statevector: bool,
    ) -> ExperimentResult:
        """Run NEQR encoding, simulation, reconstruction, and evaluation."""
        # Prepare for NEQR (integer values)
        neqr_image = self.processor.normalize_for_neqr(quantized, bits)

        # Encode
        encoder = NEQREncoder(neqr_image, intensity_bits=bits)
        circuit = encoder.build_circuit()
        stats = encoder.get_circuit_stats()

        result.encoding_time = stats["encoding_time"]
        result.qubits = stats["qubits"]
        result.n_position_qubits = stats["n_position_qubits"]
        result.n_color_or_intensity_qubits = stats["n_intensity_qubits"]
        result.gate_count = stats["gates"]
        result.circuit_depth = stats["depth"]
        result.controlled_gates = stats["controlled_gates"]
        result.gate_types = json.dumps(stats["gate_types"])

        # Simulate and reconstruct
        reconstructor = NEQRReconstructor(
            encoder.n_position_qubits,
            encoder.n_intensity_qubits,
            neqr_image.shape,
        )

        if use_statevector:
            sim_result = self.simulator.run_statevector(circuit)
            result.simulation_time = sim_result["simulation_time"]
            result.measurement_time = 0.0
            recon_result = reconstructor.reconstruct_from_statevector(
                sim_result["statevector"]
            )
        else:
            sim_result = self.simulator.run_shots(circuit, shots)
            result.simulation_time = sim_result["simulation_time"]
            result.measurement_time = sim_result["measurement_time"]
            recon_result = reconstructor.reconstruct_from_counts(
                sim_result["counts"], shots
            )

        result.reconstruction_time = recon_result["reconstruction_time"]

        # Evaluate quality (integer range for NEQR)
        max_val = float(2**bits - 1)
        quality = self.metrics.compute_image_quality(
            neqr_image.astype(np.float64),
            recon_result["image"].astype(np.float64),
            max_val=max_val,
        )
        result.mse = quality["mse"]
        result.psnr = quality["psnr"]
        result.ssim = quality["ssim"]

        return result

    def run_comparison(
        self,
        image: np.ndarray,
        image_name: str,
        size: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
        bits: int = DEFAULT_INTENSITY_BITS,
        shots: int = DEFAULT_SHOTS,
        category: str = "synthetic",
        dataset: str = "synthetic",
        use_statevector: bool = False,
    ) -> Tuple[ExperimentResult, ExperimentResult]:
        """
        Run FRQI and NEQR side-by-side under identical conditions.
        
        Returns:
            Tuple of (FRQI result, NEQR result).
        """
        frqi_result = self.run_single_experiment(
            image, image_name, size, bits, shots, "FRQI",
            category, dataset, use_statevector,
        )
        neqr_result = self.run_single_experiment(
            image, image_name, size, bits, shots, "NEQR",
            category, dataset, use_statevector,
        )
        return frqi_result, neqr_result

    # =========================================================================
    # Experiment A: Resolution Comparison
    # =========================================================================

    def run_resolution_experiment(
        self,
        image: np.ndarray,
        image_name: str = "test_image",
        bits: int = DEFAULT_INTENSITY_BITS,
        shots: int = DEFAULT_SHOTS,
        sizes: List[Tuple[int, int]] = None,
        use_statevector: bool = False,
    ) -> List[ExperimentResult]:
        """
        Experiment A: Compare FRQI and NEQR across different image resolutions.
        
        Studies how resolution affects qubit count, gate count, circuit depth,
        execution time, and reconstruction quality.
        """
        if sizes is None:
            sizes = IMAGE_SIZES

        results = []
        print("\n" + "=" * 60)
        print("EXPERIMENT A: Resolution Comparison")
        print("=" * 60)

        for size in sizes:
            print(f"\n--- Resolution: {size[0]}x{size[1]} ---")
            for rep in ["FRQI", "NEQR"]:
                print(f"  Running {rep}...", end=" ", flush=True)
                r = self.run_single_experiment(
                    image, image_name, size, bits, shots, rep,
                    use_statevector=use_statevector,
                )
                results.append(r)
                print(f"Done (MSE={r.mse:.6f}, PSNR={r.psnr:.2f}dB)")

        return results

    # =========================================================================
    # Experiment B: Intensity Precision Comparison
    # =========================================================================

    def run_precision_experiment(
        self,
        image: np.ndarray,
        image_name: str = "test_image",
        size: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
        shots: int = DEFAULT_SHOTS,
        bits_list: List[int] = None,
        use_statevector: bool = False,
    ) -> List[ExperimentResult]:
        """
        Experiment B: Compare FRQI and NEQR across different intensity precisions.
        
        Studies how intensity precision affects qubit requirements,
        circuit complexity, and reconstruction quality.
        """
        if bits_list is None:
            bits_list = INTENSITY_BITS_OPTIONS

        results = []
        print("\n" + "=" * 60)
        print("EXPERIMENT B: Intensity Precision Comparison")
        print("=" * 60)

        for bits in bits_list:
            print(f"\n--- Precision: {bits}-bit ({2**bits} levels) ---")
            for rep in ["FRQI", "NEQR"]:
                print(f"  Running {rep}...", end=" ", flush=True)
                r = self.run_single_experiment(
                    image, image_name, size, bits, shots, rep,
                    use_statevector=use_statevector,
                )
                results.append(r)
                print(f"Done (Qubits={r.qubits}, Gates={r.gate_count})")

        return results

    # =========================================================================
    # Experiment C: Image Complexity Comparison
    # =========================================================================

    def run_complexity_experiment(
        self,
        size: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
        bits: int = DEFAULT_INTENSITY_BITS,
        shots: int = DEFAULT_SHOTS,
        use_statevector: bool = False,
    ) -> List[ExperimentResult]:
        """
        Experiment C: Compare reconstruction quality across image types.
        
        Tests simple patterns, gradients, textured images, and NEU defect images.
        """
        results = []
        print("\n" + "=" * 60)
        print("EXPERIMENT C: Image Complexity Comparison")
        print("=" * 60)

        patterns = ["uniform", "gradient", "checkerboard", "diagonal", "random"]

        for pattern in patterns:
            print(f"\n--- Pattern: {pattern} ---")
            synth = self.processor.create_synthetic_image(size, pattern, bits)
            image = synth["image"]

            for rep in ["FRQI", "NEQR"]:
                print(f"  Running {rep}...", end=" ", flush=True)
                r = self.run_single_experiment(
                    image, f"synthetic_{pattern}", size, bits, shots, rep,
                    category=pattern, dataset="synthetic",
                    use_statevector=use_statevector,
                )
                results.append(r)
                print(f"Done (MSE={r.mse:.6f})")

        return results

    # =========================================================================
    # Experiment D: Measurement Shots Comparison
    # =========================================================================

    def run_shots_experiment(
        self,
        image: np.ndarray,
        image_name: str = "test_image",
        size: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
        bits: int = DEFAULT_INTENSITY_BITS,
        shots_list: List[int] = None,
    ) -> List[ExperimentResult]:
        """
        Experiment D: Compare reconstruction quality across different shot counts.
        
        Studies how measurement shots affect reconstruction quality (MSE, PSNR, SSIM).
        Always uses shot-based simulation (not statevector).
        """
        if shots_list is None:
            shots_list = SHOTS_LIST

        results = []
        print("\n" + "=" * 60)
        print("EXPERIMENT D: Measurement Shots Comparison")
        print("=" * 60)

        for shots in shots_list:
            print(f"\n--- Shots: {shots} ---")
            for rep in ["FRQI", "NEQR"]:
                print(f"  Running {rep}...", end=" ", flush=True)
                r = self.run_single_experiment(
                    image, image_name, size, bits, shots, rep,
                    use_statevector=False,
                )
                results.append(r)
                print(f"Done (MSE={r.mse:.6f}, PSNR={r.psnr:.2f}dB)")

        return results

    # =========================================================================
    # NEU-DET Dataset Experiments
    # =========================================================================

    def run_neu_experiment(
        self,
        size: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
        bits: int = DEFAULT_INTENSITY_BITS,
        shots: int = DEFAULT_SHOTS,
        categories: List[str] = None,
        images_per_category: int = IMAGES_PER_CATEGORY,
        use_statevector: bool = False,
    ) -> List[ExperimentResult]:
        """
        Run experiments on NEU Surface Defect Database images.
        
        Selects representative images from each defect category
        and runs the full FRQI vs NEQR comparison pipeline.
        """
        if categories is None:
            categories = DEFECT_CATEGORIES

        results = []
        print("\n" + "=" * 60)
        print("NEU-DET DATASET EXPERIMENT")
        print(f"Resolution: {size[0]}x{size[1]}, Precision: {bits}-bit, "
              f"Shots: {shots}")
        print("=" * 60)

        for category in categories:
            print(f"\n--- Category: {category} ---")
            try:
                image_paths = get_image_paths(
                    category, "train", images_per_category
                )
            except FileNotFoundError as e:
                print(f"  WARNING: {e}")
                continue

            for img_path in image_paths:
                img_name = img_path.name
                print(f"\n  Image: {img_name}")

                # Load the image
                image = self.processor.load_image(img_path)

                for rep in ["FRQI", "NEQR"]:
                    print(f"    Running {rep}...", end=" ", flush=True)
                    r = self.run_single_experiment(
                        image, img_name, size, bits, shots, rep,
                        category=category, dataset="NEU-DET",
                        use_statevector=use_statevector,
                    )
                    results.append(r)
                    print(f"Done (MSE={r.mse:.6f})")

        return results

    # =========================================================================
    # Full Experiment Suite
    # =========================================================================

    def run_all_experiments(
        self,
        save_results: bool = True,
    ) -> Dict[str, List[ExperimentResult]]:
        """
        Run the complete experimental suite.
        
        Returns:
            Dictionary mapping experiment name to list of results.
        """
        print("\n" + "=" * 70)
        print("RUNNING COMPLETE EXPERIMENT SUITE")
        print("=" * 70)

        # Create a test image for parametric experiments
        test_img_data = self.processor.create_synthetic_image(
            (8, 8), "gradient", DEFAULT_INTENSITY_BITS
        )
        test_image = test_img_data["image"]

        all_results = {}

        # Experiment A: Resolution
        print("\n[1/5] Running Resolution Experiment...")
        all_results["resolution"] = self.run_resolution_experiment(
            test_image, "gradient_8x8",
            use_statevector=False,
        )

        # Experiment B: Precision
        print("\n[2/5] Running Precision Experiment...")
        all_results["precision"] = self.run_precision_experiment(
            test_image, "gradient_8x8",
            use_statevector=False,
        )

        # Experiment C: Complexity
        print("\n[3/5] Running Complexity Experiment...")
        all_results["complexity"] = self.run_complexity_experiment(
            use_statevector=False,
        )

        # Experiment D: Shots
        print("\n[4/5] Running Shots Experiment...")
        all_results["shots"] = self.run_shots_experiment(
            test_image, "gradient_8x8",
        )

        # NEU-DET Experiment
        print("\n[5/5] Running NEU-DET Experiment...")
        all_results["neu_det"] = self.run_neu_experiment(
            use_statevector=False,
        )

        if save_results:
            self._save_all_results(all_results)

        return all_results

    def _save_all_results(self, all_results: Dict[str, List[ExperimentResult]]):
        """Save all experiment results to CSV and JSON files."""
        ensure_directories()

        # Save individual experiment files
        for exp_name, results in all_results.items():
            csv_path = RESULTS_EXPERIMENTS_PATH / f"{exp_name}_results.csv"
            json_path = RESULTS_EXPERIMENTS_PATH / f"{exp_name}_results.json"
            self.results_manager.save_results_csv(results, csv_path)
            self.results_manager.save_results_json(results, json_path)
            print(f"  Saved {exp_name}: {csv_path}")

        # Save combined results
        all_flat = []
        for results in all_results.values():
            all_flat.extend(results)

        combined_csv = RESULTS_EXPERIMENTS_PATH / "all_results.csv"
        combined_json = RESULTS_EXPERIMENTS_PATH / "all_results.json"
        self.results_manager.save_results_csv(all_flat, combined_csv)
        self.results_manager.save_results_json(all_flat, combined_json)
        print(f"\n  Combined results: {combined_csv}")

    def print_comparison_table(
        self,
        frqi_result: ExperimentResult,
        neqr_result: ExperimentResult,
    ):
        """Print a formatted comparison table for FRQI vs NEQR."""
        try:
            from tabulate import tabulate
        except ImportError:
            tabulate = None

        rows = [
            ["Qubits", frqi_result.qubits, neqr_result.qubits],
            ["Position Qubits", frqi_result.n_position_qubits, neqr_result.n_position_qubits],
            ["Color/Intensity Qubits", frqi_result.n_color_or_intensity_qubits,
             neqr_result.n_color_or_intensity_qubits],
            ["Gates", frqi_result.gate_count, neqr_result.gate_count],
            ["Circuit Depth", frqi_result.circuit_depth, neqr_result.circuit_depth],
            ["Controlled Gates", frqi_result.controlled_gates, neqr_result.controlled_gates],
            ["Encoding Time (s)", f"{frqi_result.encoding_time:.6f}",
             f"{neqr_result.encoding_time:.6f}"],
            ["Simulation Time (s)", f"{frqi_result.simulation_time:.6f}",
             f"{neqr_result.simulation_time:.6f}"],
            ["Reconstruction Time (s)", f"{frqi_result.reconstruction_time:.6f}",
             f"{neqr_result.reconstruction_time:.6f}"],
            ["Total Time (s)", f"{frqi_result.total_time:.6f}",
             f"{neqr_result.total_time:.6f}"],
            ["MSE", f"{frqi_result.mse:.6f}", f"{neqr_result.mse:.6f}"],
            ["PSNR (dB)", f"{frqi_result.psnr:.2f}", f"{neqr_result.psnr:.2f}"],
            ["SSIM", f"{frqi_result.ssim:.6f}", f"{neqr_result.ssim:.6f}"],
        ]

        print("\n" + "=" * 60)
        print(f"COMPARISON: {frqi_result.image_name} @ "
              f"{frqi_result.resolution}, {frqi_result.intensity_precision}-bit, "
              f"{frqi_result.shots} shots")
        print("=" * 60)

        if tabulate is not None:
            print(tabulate(rows, headers=["Metric", "FRQI", "NEQR"],
                           tablefmt="grid"))
        else:
            print(f"{'Metric':<25} {'FRQI':>12} {'NEQR':>12}")
            print("-" * 50)
            for row in rows:
                print(f"{row[0]:<25} {str(row[1]):>12} {str(row[2]):>12}")
