"""
Isolated quantum simulation runner.
Runs in a subprocess so a Qiskit-Aer segfault never kills the Streamlit process.
Called by: app/pages/4__Quantum_Lab.py
"""

import sys
import json
import traceback
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

def run_simulation(params: dict) -> dict:
    """
    Execute a full FRQI/NEQR quantum experiment.
    Returns a JSON-serializable result dict (or an error dict).
    """
    try:
        from src.preprocessing.image_processor import ImageProcessor
        from src.frqi.encoder import FRQIEncoder
        from src.neqr.encoder import NEQREncoder
        from src.simulation.simulator import QuantumSimulator
        from src.reconstruction.reconstructor import FRQIReconstructor, NEQRReconstructor
        from src.metrics.evaluator import MetricsEvaluator
        import time

        representation = params["representation"]
        size_n         = params["size_n"]
        bits           = params["bits"]
        use_sv         = params["use_sv"]
        shots          = params.get("shots", 1000)
        raw_image      = np.array(params["raw_image"], dtype=np.float32)

        processor    = ImageProcessor(random_seed=42)
        simulator    = QuantumSimulator(seed=42)
        metrics_eval = MetricsEvaluator()

        size = (size_n, size_n)

        # Preprocess
        resized   = processor.resize_image(raw_image.astype(np.uint8), size)
        quantized = processor.quantize_intensity(resized, bits)
        if representation == "FRQI":
            proc_image = processor.normalize_for_frqi(quantized, bits)
        else:
            proc_image = processor.normalize_for_neqr(quantized, bits)

        # Encode
        t0 = time.perf_counter()
        if representation == "FRQI":
            encoder = FRQIEncoder(proc_image)
        else:
            encoder = NEQREncoder(proc_image, intensity_bits=bits)
        circuit = encoder.build_circuit()
        stats   = encoder.get_circuit_stats()
        enc_time = time.perf_counter() - t0

        # Simulate
        if use_sv:
            sim_result = simulator.run_statevector(circuit)
            sim_time   = sim_result["simulation_time"]
            meas_time  = 0.0
            counts_result = None
        else:
            sim_result    = simulator.run_shots(circuit, shots)
            sim_time      = sim_result["simulation_time"]
            meas_time     = sim_result["measurement_time"]
            counts_result = sim_result["counts"]

        # Reconstruct
        t_rec = time.perf_counter()
        if representation == "FRQI":
            reconstructor = FRQIReconstructor(encoder.n_position_qubits, proc_image.shape)
            if use_sv:
                recon_result = reconstructor.reconstruct_from_statevector(sim_result["statevector"])
            else:
                recon_result = reconstructor.reconstruct_from_counts(counts_result, shots)
        else:
            reconstructor = NEQRReconstructor(
                encoder.n_position_qubits, encoder.n_intensity_qubits, proc_image.shape
            )
            if use_sv:
                recon_result = reconstructor.reconstruct_from_statevector(sim_result["statevector"])
            else:
                recon_result = reconstructor.reconstruct_from_counts(counts_result, shots)
        rec_time    = time.perf_counter() - t_rec
        recon_image = recon_result["image"]

        # Quality
        if representation == "FRQI":
            quality = metrics_eval.compute_image_quality(proc_image, recon_image, max_val=1.0)
        else:
            quality = metrics_eval.compute_image_quality(
                proc_image.astype(np.float64),
                recon_image.astype(np.float64),
                max_val=float(2 ** bits - 1),
            )

        # Build display images (serializable)
        resized_list = resized.tolist()
        if representation == "FRQI":
            disp_recon = (recon_image * 255).clip(0, 255).astype(np.uint8).tolist()
            diff = np.abs(proc_image - recon_image)
        else:
            scale = 255.0 / max(2 ** bits - 1, 1)
            disp_recon = (recon_image.astype(np.float32) * scale).clip(0, 255).astype(np.uint8).tolist()
            diff = np.abs(proc_image.astype(np.float32) - recon_image.astype(np.float32))
        diff_disp = (diff * 255 / max(diff.max(), 1e-6)).clip(0, 255).astype(np.uint8).tolist()

        return {
            "ok": True,
            "stats": stats,
            "quality": {k: float(v) for k, v in quality.items()},
            "enc_time":  float(enc_time),
            "sim_time":  float(sim_time),
            "meas_time": float(meas_time),
            "rec_time":  float(rec_time),
            "resized":   resized_list,
            "disp_recon": disp_recon,
            "diff_disp":  diff_disp,
        }

    except Exception:
        return {"ok": False, "error": traceback.format_exc()}


if __name__ == "__main__":
    # Read JSON params from stdin, write JSON result to stdout
    raw = sys.stdin.read()
    params = json.loads(raw)
    result = run_simulation(params)
    sys.stdout.write(json.dumps(result))
    sys.stdout.flush()
