"""
Script to execute the complete Quantum Machine Learning experiment suite across the full NEU-DET dataset.

Executes:
1. Full dataset run across all 1,800 images (both FRQI and NEQR) with paired inference & reconstruction.
2. Model matrix sweeps (QKC, VQC, HQCC).
3. Resolution sweeps (2x2, 4x4, 8x8).
4. Shot sensitivity sweeps (100, 500, 1000).
5. NEQR intensity precision sweeps (2, 4, 8 bits).
"""

import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.qml.experiment_manager import QMLExperimentManager

def progress_printer(status):
    pct = status.get("percent", 0)
    msg = status.get("message", "")
    phase = status.get("phase", "")
    comp = status.get("completed", "")
    print(f"[{pct}%] ({phase}) {msg}", flush=True)

def main():
    print("=" * 70)
    print("Q-IMAGELAB: FULL-DATASET QUANTUM ML EXPERIMENT PIPELINE")
    print("=" * 70)

    manager = QMLExperimentManager()

    # Step 1: Manifest verification
    manifest = manager.discover_dataset()
    print(f"Total Eligible Images: {manifest['total_images']}")
    print(f"Classes Verified (6): {manifest['classes']}")
    print(f"Train Counts: {manifest['train_counts']}")
    print(f"Validation Counts: {manifest['val_counts']}")
    print("-" * 70)

    # Step 2: Run Full Dataset Pipeline across all 1,800 images (Hybrid Quantum-Classical)
    print("\n--- PHASE 1: FULL DATASET EXECUTION (1,800 IMAGES - FRQI + NEQR) ---")
    t0 = time.perf_counter()
    res_full = manager.run_full_dataset_pipeline(
        {
            "resolution": "4x4",
            "intensity_bits": 4,
            "shots": 0,
            "model_type": "Hybrid Quantum-Classical Classifier",
            "batch_limit": None,  # Process all 1,800 images
        },
        progress_callback=progress_printer,
    )
    t_full = time.perf_counter() - t0
    print(f"Full Dataset Run Completed in {t_full:.2f}s:")
    print(res_full)

    # Step 3: Run Experiment Matrix Benchmarks for QKC & VQC
    print("\n--- PHASE 2: MODEL ARCHITECTURE MATRIX (QKC & VQC) ---")
    for model in ["Quantum Kernel Classifier", "Variational Quantum Classifier"]:
        print(f"\nExecuting paired benchmark for {model}...")
        res_m = manager.run_paired_experiment(
            {
                "resolution": "4x4",
                "intensity_bits": 4,
                "shots": 0,
                "model_type": model,
                "max_per_class": 10,
            },
            progress_callback=progress_printer,
        )
        print(f"Completed {model}: Comparison ID {res_m.get('comparison_id')}")

    # Step 4: Run Resolution Scaling Matrix (2x2 and 8x8)
    print("\n--- PHASE 3: RESOLUTION SCALING MATRIX (2x2 & 8x8) ---")
    for res in ["2x2", "8x8"]:
        print(f"\nExecuting paired benchmark at {res}...")
        res_r = manager.run_paired_experiment(
            {
                "resolution": res,
                "intensity_bits": 4,
                "shots": 0,
                "model_type": "Hybrid Quantum-Classical Classifier",
                "max_per_class": 8,
            },
            progress_callback=progress_printer,
        )
        print(f"Completed {res}: Comparison ID {res_r.get('comparison_id')}")

    # Step 5: Run Shot Sensitivity Matrix (100, 500, 1000 shots)
    print("\n--- PHASE 4: SHOT SENSITIVITY MATRIX (100, 500, 1000 shots) ---")
    for shots in [100, 500, 1000]:
        print(f"\nExecuting paired benchmark at {shots} shots...")
        res_s = manager.run_paired_experiment(
            {
                "resolution": "4x4",
                "intensity_bits": 4,
                "shots": shots,
                "model_type": "Hybrid Quantum-Classical Classifier",
                "max_per_class": 8,
            },
            progress_callback=progress_printer,
        )
        print(f"Completed {shots} shots: Comparison ID {res_s.get('comparison_id')}")

    # Step 6: Final Overview KPIs
    print("\n" + "=" * 70)
    print("ALL EXPERIMENTS COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    kpis = manager.get_overview_kpis()
    print("Overview KPIs:")
    for k, v in kpis.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
