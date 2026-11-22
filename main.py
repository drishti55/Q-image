#!/usr/bin/env python3
"""
Main Entry Point for the Quantum Image Processing Research Project.

Provides a CLI for running experiments and generating visualizations.
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from src.experiments.runner import ExperimentRunner
from src.visualization.plotter import ResultPlotter
from config.settings import DEFAULT_IMAGE_SIZE, DEFAULT_INTENSITY_BITS, DEFAULT_SHOTS


def parse_args():
    parser = argparse.ArgumentParser(
        description="FRQI vs NEQR Quantum Image Processing Experiments"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Command: demo
    parser_demo = subparsers.add_parser(
        "demo", help="Run a single FRQI vs NEQR comparison on a synthetic image"
    )
    parser_demo.add_argument(
        "--size", type=int, default=4, help="Image dimension (e.g., 4 for 4x4)"
    )
    parser_demo.add_argument(
        "--bits", type=int, default=8, help="Intensity precision in bits"
    )
    parser_demo.add_argument(
        "--shots", type=int, default=1000, help="Number of measurement shots"
    )
    parser_demo.add_argument(
        "--sv", action="store_true", help="Use statevector simulator (exact)"
    )

    # Command: experiment
    parser_exp = subparsers.add_parser(
        "experiment", help="Run a specific experiment suite"
    )
    parser_exp.add_argument(
        "--type", 
        type=str, 
        choices=["resolution", "precision", "shots", "complexity", "neu"],
        required=True,
        help="Type of experiment to run"
    )

    # Command: all
    parser_all = subparsers.add_parser(
        "all", help="Run all experiments and generate all plots"
    )

    # Command: dashboard
    parser_dash = subparsers.add_parser(
        "dashboard", help="Start the interactive Streamlit dashboard"
    )

    return parser.parse_args()


def run_demo(args):
    """Run a single demonstration experiment."""
    runner = ExperimentRunner()
    plotter = ResultPlotter()
    
    size = (args.size, args.size)
    print(f"\nRunning FRQI vs NEQR Demo")
    print(f"Resolution: {size[0]}x{size[1]}, Precision: {args.bits}-bit, "
          f"Shots: {args.shots}")
    
    # Create test image
    img_data = runner.processor.create_synthetic_image(size, "gradient", args.bits)
    image = img_data["image"]
    
    # Run comparison
    frqi_result, neqr_result = runner.run_comparison(
        image, "demo_gradient", size, args.bits, args.shots, 
        use_statevector=args.sv
    )
    
    # Print table
    runner.print_comparison_table(frqi_result, neqr_result)
    
    # Generate visualization
    # Recreate reconstructions since they aren't stored in ExperimentResult to save memory
    frqi_image = runner.processor.normalize_for_frqi(img_data["quantized"], args.bits)
    from src.frqi.encoder import FRQIEncoder
    from src.simulation.simulator import QuantumSimulator
    from src.reconstruction.reconstructor import FRQIReconstructor
    
    encoder_f = FRQIEncoder(frqi_image)
    circ_f = encoder_f.build_circuit()
    sim = QuantumSimulator()
    recon_f = FRQIReconstructor(encoder_f.n_position_qubits, size)
    
    if args.sv:
        res_f = sim.run_statevector(circ_f)
        recon_img_f = recon_f.reconstruct_from_statevector(res_f["statevector"])["image"]
    else:
        res_f = sim.run_shots(circ_f, args.shots)
        recon_img_f = recon_f.reconstruct_from_counts(res_f["counts"], args.shots)["image"]
        
    from src.neqr.encoder import NEQREncoder
    from src.reconstruction.reconstructor import NEQRReconstructor
    neqr_image = runner.processor.normalize_for_neqr(img_data["quantized"], args.bits)
    encoder_n = NEQREncoder(neqr_image, args.bits)
    circ_n = encoder_n.build_circuit()
    recon_n = NEQRReconstructor(encoder_n.n_position_qubits, encoder_n.n_intensity_qubits, size)
    
    if args.sv:
        res_n = sim.run_statevector(circ_n)
        recon_img_n = recon_n.reconstruct_from_statevector(res_n["statevector"])["image"]
    else:
        res_n = sim.run_shots(circ_n, args.shots)
        recon_img_n = recon_n.reconstruct_from_counts(res_n["counts"], args.shots)["image"]
        
    plot_path = plotter.plot_reconstruction_comparison(
        image, recon_img_f, recon_img_n,
        title=f"Demo Reconstruction: {size[0]}x{size[1]}, {args.bits}-bit, {args.shots} shots",
        frqi_metrics={"mse": frqi_result.mse, "psnr": frqi_result.psnr},
        neqr_metrics={"mse": neqr_result.mse, "psnr": neqr_result.psnr}
    )
    print(f"\nSaved reconstruction comparison to: {plot_path}")
    print("Demo complete!")


def run_experiment(args):
    """Run a specific experiment suite."""
    runner = ExperimentRunner()
    plotter = ResultPlotter()
    
    # Create test image for parametric experiments
    test_img_data = runner.processor.create_synthetic_image(
        DEFAULT_IMAGE_SIZE, "gradient", DEFAULT_INTENSITY_BITS
    )
    test_image = test_img_data["image"]
    
    results_dict = {}
    
    if args.type == "resolution":
        results = runner.run_resolution_experiment(test_image, use_statevector=False)
        results_dict["resolution"] = results
    elif args.type == "precision":
        results = runner.run_precision_experiment(test_image, use_statevector=False)
        results_dict["precision"] = results
    elif args.type == "shots":
        results = runner.run_shots_experiment(test_image)
        results_dict["shots"] = results
    elif args.type == "complexity":
        results = runner.run_complexity_experiment(use_statevector=False)
        results_dict["complexity"] = results
    elif args.type == "neu":
        results = runner.run_neu_experiment(use_statevector=False)
        results_dict["neu_det"] = results
        
    runner._save_all_results(results_dict)
    plotter.generate_all_plots(results_dict)


def run_all(args):
    """Run all experiments."""
    runner = ExperimentRunner()
    plotter = ResultPlotter()
    
    all_results = runner.run_all_experiments()
    plotter.generate_all_plots(all_results)
    
    print("\nAll experiments completed successfully!")


def start_dashboard():
    """Start the Streamlit dashboard."""
    import subprocess
    dash_path = PROJECT_ROOT / "app" / "dashboard.py"
    print(f"Starting Streamlit dashboard from {dash_path}")
    subprocess.run(["streamlit", "run", str(dash_path)])


def main():
    args = parse_args()
    
    if args.command == "demo":
        run_demo(args)
    elif args.command == "experiment":
        run_experiment(args)
    elif args.command == "all":
        run_all(args)
    elif args.command == "dashboard":
        start_dashboard()
    else:
        print("Please specify a command: demo, experiment, all, or dashboard.")
        print("Run 'python main.py -h' for help.")


if __name__ == "__main__":
    main()
