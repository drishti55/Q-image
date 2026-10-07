"""
Isolated circuit analyzer worker to prevent Qiskit/Rust segfaults in the main Streamlit process.
"""
import sys
import json
import traceback
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

def run_analysis(params: dict) -> dict:
    try:
        from src.preprocessing.image_processor import ImageProcessor
        from src.frqi.encoder import FRQIEncoder
        from src.neqr.encoder import NEQREncoder

        rep = params["representation"]
        size_n = params["size_n"]
        bits = params["bits"]
        raw_image = np.array(params["raw_image"], dtype=np.uint8)

        processor = ImageProcessor(random_seed=42)
        size = (size_n, size_n)
        
        resized = processor.resize_image(raw_image, size)
        quantized = processor.quantize_intensity(resized, bits)
        frqi_img  = processor.normalize_for_frqi(quantized, bits)
        neqr_img  = processor.normalize_for_neqr(quantized, bits)

        reps_to_show = ["FRQI", "NEQR"] if rep == "Both" else [rep]
        circuits_info = {}
        for r in reps_to_show:
            if r == "FRQI":
                encoder = FRQIEncoder(frqi_img)
            else:
                encoder = NEQREncoder(neqr_img, intensity_bits=bits)
            circuit = encoder.build_circuit()
            stats = encoder.get_circuit_stats()
            
            ops = []
            qubit_depths = {i: 0 for i in range(circuit.num_qubits)}
            for instruction in circuit.data:
                op_name = instruction.operation.name
                params = instruction.operation.params
                
                qubit_indices = [circuit.find_bit(q).index for q in instruction.qubits]
                cbit_indices = [circuit.find_bit(c).index for c in instruction.clbits]
                
                gate_depth = max([qubit_depths[q] for q in qubit_indices] + [0]) + 1
                for q in qubit_indices:
                    qubit_depths[q] = gate_depth
                
                # convert parameters safely (some might be ParameterExpressions, though usually float here)
                try:
                    parsed_params = [float(p) for p in params] if params else []
                except:
                    parsed_params = [str(p) for p in params] if params else []

                ops.append({
                    "name": op_name,
                    "params": parsed_params,
                    "qubits": qubit_indices,
                    "cbits": cbit_indices,
                    "depth": gate_depth
                })

            diagram = ""
            if size_n <= 4:
                diagram = circuit.draw(output="text").__str__()
                
            circuits_info[r] = {
                "stats": stats, 
                "diagram": diagram,
                "ops": ops,
                "num_qubits": circuit.num_qubits,
                "num_clbits": circuit.num_clbits
            }
            
        # Compute scaling metrics using synthetic image
        scaling = {"FRQI": {"sizes":[], "qubits":[], "gates":[], "depth":[]},
                   "NEQR": {"sizes":[], "qubits":[], "gates":[], "depth":[]}}
        test_img = processor.create_synthetic_image((8, 8), "gradient", bits)["image"]
        
        for s_n in [2, 4, 8]:
            sz = (s_n, s_n)
            res = processor.resize_image(test_img, sz)
            q_   = processor.quantize_intensity(res, bits)
            fi   = processor.normalize_for_frqi(q_, bits)
            ni   = processor.normalize_for_neqr(q_, bits)
            for r, img in [("FRQI", fi), ("NEQR", ni)]:
                try:
                    enc = FRQIEncoder(img) if r=="FRQI" else NEQREncoder(img, bits)
                    enc.build_circuit()
                    st = enc.get_circuit_stats()
                    scaling[r]["sizes"].append(s_n)
                    scaling[r]["qubits"].append(st["qubits"])
                    scaling[r]["gates"].append(st["gates"])
                    scaling[r]["depth"].append(st["depth"])
                except:
                    pass

        return {
            "ok": True,
            "circuits_info": circuits_info,
            "scaling": scaling
        }
    except Exception:
        return {"ok": False, "error": traceback.format_exc()}

if __name__ == "__main__":
    raw = sys.stdin.read()
    params = json.loads(raw)
    result = run_analysis(params)
    sys.stdout.write(json.dumps(result))
    sys.stdout.flush()
