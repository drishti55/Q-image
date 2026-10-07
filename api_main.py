from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import json
from pathlib import Path
from fastapi.responses import FileResponse

app = FastAPI(title="Q-ImageLab API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).parent.resolve()
import sys
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ─── SYSTEM STATUS ───────────────────────────────────────────────

import threading

batch_job_state = {
    "is_running": False,
    "total": 0,
    "completed": 0,
    "failed": 0,
    "current_image": "",
    "current_representation": ""
}

def run_batch_job(config: dict):
    from src.experiments.runner import ExperimentRunner
    from src.preprocessing.image_processor import ImageProcessor
    from config.settings import DATASET_PATH
    import traceback

    global batch_job_state
    batch_job_state["is_running"] = True
    batch_job_state["completed"] = 0
    batch_job_state["failed"] = 0

    mode = config.get("mode", "all") # 'all' or 'category'
    target_category = config.get("category", "all")
    representation = config.get("representation", "FRQI") # 'FRQI', 'NEQR', 'Both'
    
    res_str = str(config.get("resolution", "4"))
    size_int = int(res_str.split("x")[0]) if "x" in res_str else int(res_str)
    size = (size_int, size_int)
    bits = int(config.get("precision", 8))
    shots = int(config.get("shots", 1024))

    images_to_process = []
    base = DATASET_PATH / "train" / "images"
    
    classes = [target_category] if target_category != "all" else [
        d.name for d in base.iterdir() if d.is_dir()
    ]
    
    for cls in classes:
        cls_dir = base / cls
        if not cls_dir.exists(): continue
        for f in cls_dir.iterdir():
            if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp"]:
                images_to_process.append((cls, f.name, f))
    
    reps_to_run = ["FRQI", "NEQR"] if representation == "Both" else [representation]
    batch_job_state["total"] = len(images_to_process) * len(reps_to_run)
    
    processor = ImageProcessor()
    runner = ExperimentRunner()
    
    for cls, img_name, img_path in images_to_process:
        if not batch_job_state["is_running"]: 
            break # allows cancellation
            
        try:
            original_image = processor.load_image(img_path)
            for rep in reps_to_run:
                batch_job_state["current_image"] = img_name
                batch_job_state["current_representation"] = rep
                
                try:
                    result = runner.run_single_experiment(
                        image=original_image,
                        image_name=img_name,
                        size=size,
                        bits=bits,
                        shots=shots,
                        representation=rep,
                        category=cls,
                        dataset="NEU-DET",
                        use_statevector=False
                    )
                    
                    from config.settings import RESULTS_EXPERIMENTS_PATH
                    save_path = RESULTS_EXPERIMENTS_PATH / "all_results.csv"
                    existing = runner.results_manager.load_results_csv(save_path)
                    all_res = existing + [result.to_dict()]
                    runner.results_manager.save_results_csv(all_res, save_path)
                    
                    batch_job_state["completed"] += 1
                except Exception as e:
                    traceback.print_exc()
                    batch_job_state["failed"] += 1
                    
        except Exception as e:
            traceback.print_exc()
            batch_job_state["failed"] += len(reps_to_run)
            
    batch_job_state["is_running"] = False
    batch_job_state["current_image"] = ""
    batch_job_state["current_representation"] = ""

@app.get("/api/quantum/batch/status")
def get_batch_status():
    global batch_job_state
    return batch_job_state

@app.post("/api/quantum/batch/run")
def start_batch_job(config: dict):
    global batch_job_state
    if batch_job_state["is_running"]:
        return {"status": "error", "message": "A batch job is already running."}
    
    thread = threading.Thread(target=run_batch_job, args=(config,))
    thread.daemon = True
    thread.start()
    return {"status": "started", "message": "Batch job started in background."}

@app.post("/api/quantum/batch/stop")
def stop_batch_job():
    global batch_job_state
    batch_job_state["is_running"] = False
    return {"status": "stopped", "message": "Batch job cancelled."}

@app.get("/api/ml/models")
def get_ml_models():
    """Get list of evaluated ML models."""
    cm_dir = PROJECT_ROOT / "results" / "models" / "confusion_matrices"
    models = []
    if cm_dir.exists():
        for f in cm_dir.iterdir():
            if f.name.endswith("_cm.json"):
                models.append(f.name.replace("_cm.json", "").replace("_", " "))
    return {"models": models}

@app.get("/api/ml/confusion-matrix/{model_name}")
def get_confusion_matrix(model_name: str):
    """Get confusion matrix data for a specific model."""
    cm_dir = PROJECT_ROOT / "results" / "models" / "confusion_matrices"
    filename = model_name.replace(" ", "_") + "_cm.json"
    file_path = cm_dir / filename
    if file_path.exists():
        with open(file_path, "r") as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Model confusion matrix not found")

@app.get("/api/ml/results")
def get_ml_results():
    """Get ML evaluation results from CSV."""
    p = PROJECT_ROOT / "results" / "models" / "model_comparison.csv"
    if p.exists():
        df = pd.read_csv(p)
        return df.to_dict(orient="records")
    return []

@app.get("/api/ml/per-class")
def get_ml_per_class():
    """Get ML per-class results from CSV."""
    p = PROJECT_ROOT / "results" / "models" / "per_class_metrics.csv"
    if p.exists():
        df = pd.read_csv(p)
        return df.to_dict(orient="records")
    return []

@app.get("/api/status")
def get_status():
    """Check backend health and data availability."""
    has_dataset = (PROJECT_ROOT / "NEU-DET" / "train" / "images").exists()
    has_models = (PROJECT_ROOT / "results" / "models" / "model_comparison.csv").exists()
    has_experiments = (PROJECT_ROOT / "results" / "experiments" / "all_results.csv").exists()
    return {
        "backend": "online",
        "dataset_available": has_dataset,
        "models_available": has_models,
        "experiments_available": has_experiments,
    }


# ─── DATASET ─────────────────────────────────────────────────────

@app.get("/api/dataset/summary")
def get_dataset_summary():
    p = PROJECT_ROOT / "results" / "dataset" / "dataset_summary.json"
    if p.exists():
        with open(p) as f:
            d = json.load(f)
        sp = PROJECT_ROOT / "results" / "models" / "split_info.json"
        if sp.exists():
            with open(sp) as f2:
                s = json.load(f2)
            d["test_total"] = s.get("test_samples", 0)
            d["split_info"] = s
        return d
    return {"total_images": 0, "n_classes": 0}


@app.get("/api/dataset/class-distribution")
def get_class_distribution():
    p = PROJECT_ROOT / "results" / "dataset" / "class_distribution.csv"
    if p.exists():
        df = pd.read_csv(p)
        return df.to_dict(orient="records")
    return []


@app.get("/api/dataset/images")
def list_dataset_images(split: str = "train", defect_class: str = "all", limit: int = 30, offset: int = 0):
    """List images from the NEU-DET dataset."""
    base = PROJECT_ROOT / "NEU-DET" / split / "images"
    if not base.exists():
        return {"images": [], "total": 0}

    classes = [defect_class] if defect_class != "all" else [
        d.name for d in base.iterdir() if d.is_dir()
    ]

    images = []
    for cls in sorted(classes):
        cls_dir = base / cls
        if not cls_dir.exists():
            continue
        for f in sorted(cls_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp"]:
                images.append({
                    "name": f.name,
                    "defect_class": cls,
                    "split": split,
                    "url": f"/api/dataset/image/{split}/{cls}/{f.name}",
                })

    total = len(images)
    return {"images": images[offset:offset + limit], "total": total}


@app.get("/api/dataset/image/{split}/{defect_class}/{filename}")
def serve_dataset_image(split: str, defect_class: str, filename: str):
    """Serve a specific image file."""
    p = PROJECT_ROOT / "NEU-DET" / split / "images" / defect_class / filename
    if p.exists():
        return FileResponse(str(p))
    raise HTTPException(status_code=404, detail=f"Image not found: {p}")


@app.get("/api/dataset/coverage")
def get_dataset_coverage():
    import pandas as pd
    from config.settings import DATASET_PATH
    
    coverage = {
        "total_images": 0,
        "images_evaluated": 0,
        "images_remaining": 0,
        "failed": batch_job_state["failed"] if batch_job_state else 0,
        "by_class": {}
    }
    
    base = DATASET_PATH / "train" / "images"
    if not base.exists():
        return coverage
        
    p = PROJECT_ROOT / "results" / "experiments" / "all_results.csv"
    evaluated = set()
    eval_by_class = {}
    if p.exists():
        df = pd.read_csv(p)
        for _, row in df.iterrows():
            img = str(row["image_name"])
            cls = str(row["defect_category"])
            evaluated.add(img)
            if cls not in eval_by_class: eval_by_class[cls] = set()
            eval_by_class[cls].add(img)
            
    classes = [d.name for d in base.iterdir() if d.is_dir()]
    for cls in classes:
        cls_dir = base / cls
        if not cls_dir.exists(): continue
        total_cls = len([f for f in cls_dir.iterdir() if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp"]])
        eval_cls = len(eval_by_class.get(cls, set()))
        coverage["total_images"] += total_cls
        coverage["by_class"][cls] = {
            "total": total_cls,
            "evaluated": eval_cls
        }
        
    coverage["images_evaluated"] = len(evaluated)
    coverage["images_remaining"] = coverage["total_images"] - coverage["images_evaluated"]
    return coverage

# ─── ML MODELS ───────────────────────────────────────────────────

@app.get("/api/models/comparison")
def get_model_comparison():
    p = PROJECT_ROOT / "results" / "models" / "model_comparison.csv"
    if p.exists():
        df = pd.read_csv(p)
        return df.to_dict(orient="records")
    return []


@app.get("/api/models/per-class-metrics")
def get_per_class_metrics():
    p = PROJECT_ROOT / "results" / "models" / "per_class_metrics.csv"
    if p.exists():
        df = pd.read_csv(p)
        return df.to_dict(orient="records")
    return []


@app.get("/api/models/confusion-matrices")
def list_confusion_matrices():
    d = PROJECT_ROOT / "results" / "models" / "confusion_matrices"
    if not d.exists():
        return []
    files = []
    for f in d.iterdir():
        if f.suffix in [".csv", ".json", ".png"]:
            files.append({"name": f.stem, "type": f.suffix, "url": f"/api/models/confusion-matrix/{f.name}"})
    return files


@app.get("/api/models/confusion-matrix/{filename}")
def get_confusion_matrix(filename: str):
    p = PROJECT_ROOT / "results" / "models" / "confusion_matrices" / filename
    if not p.exists():
        raise HTTPException(status_code=404)
    if p.suffix == ".csv":
        df = pd.read_csv(p, index_col=0)
        return {"labels": list(df.columns), "matrix": df.values.tolist()}
    return FileResponse(str(p))


@app.get("/api/models/all-results")
def get_all_model_results():
    p = PROJECT_ROOT / "results" / "models" / "all_model_results.json"
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return {}


# ─── QUANTUM EXPERIMENTS ─────────────────────────────────────────

@app.get("/api/quantum/experiments")
def get_quantum_experiments(limit: int = 100, offset: int = 0, representation: str = "all"):
    p = PROJECT_ROOT / "results" / "experiments" / "all_results.csv"
    if not p.exists():
        return {"experiments": [], "total": 0}
    df = pd.read_csv(p)
    if representation != "all":
        df = df[df["representation"].str.upper() == representation.upper()]
    total = len(df)
    df = df.iloc[offset:offset + limit]
    df = df.where(pd.notnull(df), None)
    # Replace inf values
    df = df.replace([float('inf'), float('-inf')], None)
    records = df.to_dict(orient="records")
    return {"experiments": records, "total": total}


@app.get("/api/quantum/kpis")
def get_quantum_kpis():
    p = PROJECT_ROOT / "results" / "experiments" / "all_results.csv"
    if not p.exists():
        return {"n_experiments": 0, "avg_psnr": None, "avg_ssim": None}
    df = pd.read_csv(p)
    # Filter out inf PSNR values for meaningful averages
    psnr_clean = df["psnr"].replace([float("inf"), float("-inf")], pd.NA).dropna()
    ssim_clean = df["ssim"].dropna()
    return {
        "n_experiments": len(df),
        "avg_psnr": round(float(psnr_clean.mean()), 2) if len(psnr_clean) > 0 else None,
        "avg_ssim": round(float(ssim_clean.mean()), 4) if len(ssim_clean) > 0 else None,
        "representations": list(df["representation"].unique()),
        "resolutions": list(df["resolution"].str.strip().unique()),
    }


@app.get("/api/quantum/resolution-results")
def get_resolution_results():
    p = PROJECT_ROOT / "results" / "experiments" / "resolution_results.csv"
    if p.exists():
        df = pd.read_csv(p)
        df = df.where(pd.notnull(df), None).replace([float('inf'), float('-inf')], None)
        return df.to_dict(orient="records")
    return []


@app.get("/api/quantum/shots-results")
def get_shots_results():
    p = PROJECT_ROOT / "results" / "experiments" / "shots_results.csv"
    if p.exists():
        df = pd.read_csv(p)
        df = df.where(pd.notnull(df), None).replace([float('inf'), float('-inf')], None)
        return df.to_dict(orient="records")
    return []


@app.get("/api/quantum/complexity-results")
def get_complexity_results():
    p = PROJECT_ROOT / "results" / "experiments" / "complexity_results.csv"
    if p.exists():
        df = pd.read_csv(p)
        df = df.where(pd.notnull(df), None).replace([float('inf'), float('-inf')], None)
        return df.to_dict(orient="records")
    return []


@app.get("/api/quantum/precision-results")
def get_precision_results():
    p = PROJECT_ROOT / "results" / "experiments" / "precision_results.csv"
    if p.exists():
        df = pd.read_csv(p)
        df = df.where(pd.notnull(df), None).replace([float('inf'), float('-inf')], None)
        return df.to_dict(orient="records")
    return []


# ─── QUANTUM EXPERIMENT EXECUTION ────────────────────────────────

@app.post("/api/quantum/run")
def run_quantum_experiment(config: dict):
    """Executes a single quantum image experiment and saves the result."""
    from src.experiments.runner import ExperimentRunner
    from src.preprocessing.image_processor import ImageProcessor
    from config.settings import DATASET_PATH
    import numpy as np

    try:
        image_name = config.get("image")
        category = config.get("defect_class")
        representation = config.get("representation", "FRQI")
        
        res_str = str(config.get("resolution", "4"))
        size_int = int(res_str.split("x")[0]) if "x" in res_str else int(res_str)
        size = (size_int, size_int)
        
        bits = int(config.get("precision", 8))
        shots = int(config.get("shots", 1024))

        img_path = DATASET_PATH / "train" / "images" / category / image_name
        if not img_path.exists():
            return {"error": f"Image {image_name} not found in {category}"}

        processor = ImageProcessor()
        original_image = processor.load_image(img_path)

        runner = ExperimentRunner()
        result = runner.run_single_experiment(
            image=original_image,
            image_name=image_name,
            size=size,
            bits=bits,
            shots=shots,
            representation=representation,
            category=category,
            dataset="NEU-DET",
            use_statevector=False
        )

        # Ensure the result is saved to all_results.csv
        from config.settings import RESULTS_EXPERIMENTS_PATH
        save_path = RESULTS_EXPERIMENTS_PATH / "all_results.csv"
        existing = runner.results_manager.load_results_csv(save_path)
        all_res = existing + [result.to_dict()]
        runner.results_manager.save_results_csv(all_res, save_path)

        # After saving, we can just return the experiment ID!
        return {
            "status": "completed",
            "message": "Experiment executed successfully.",
            "experiment_id": result.experiment_id,
            "metrics": {
                "mse": result.mse,
                "psnr": result.psnr,
                "ssim": result.ssim,
                "gate_count": result.gate_count,
                "depth": result.circuit_depth
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

@app.post("/api/quantum/compare-custom")
async def run_quantum_compare_custom(
    file: UploadFile = File(...),
    resolution: str = Form("4x4"),
    precision: int = Form(8),
    shots: int = Form(1024)
):
    """Executes a quantum experiment for both FRQI and NEQR on a custom uploaded image."""
    from src.preprocessing.image_processor import ImageProcessor
    from src.frqi.encoder import FRQIEncoder
    from src.neqr.encoder import NEQREncoder
    from src.simulation.simulator import QuantumSimulator
    from src.reconstruction.reconstructor import FRQIReconstructor, NEQRReconstructor
    from src.metrics.evaluator import MetricsEvaluator
    import numpy as np
    from PIL import Image
    import io
    import time
    import base64

    try:
        # Read the image from upload
        contents = await file.read()
        img = Image.open(io.BytesIO(contents)).convert("L")
        original_image = np.array(img, dtype=np.uint8)

        size_int = int(resolution.split("x")[0]) if "x" in resolution else int(resolution)
        size = size_int
        processor = ImageProcessor()
        processed_image = processor.resize_image(original_image, (size, size))
        processed_image = processor.quantize_intensity(processed_image, precision)
        
        simulator = QuantumSimulator()
        evaluator = MetricsEvaluator()
        
        def np_to_b64(arr, max_val_expected=255):
            if arr.dtype == np.float64 or arr.dtype == np.float32:
                arr = (arr * 255).astype(np.uint8) if arr.max() <= 1.0 else arr.astype(np.uint8)
            else:
                arr = arr.astype(np.float64)
                if max_val_expected > 0:
                    arr = (arr / max_val_expected) * 255.0
                arr = arr.astype(np.uint8)
                
            img = Image.fromarray(arr).resize((200, 200), Image.Resampling.NEAREST)
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
            
        max_pixel_val = 2**precision - 1
        original_b64 = np_to_b64(processed_image, max_pixel_val)
        
        # --- Run FRQI ---
        start_frqi = time.time()
        frqi_img = processor.normalize_for_frqi(processed_image, precision)
        frqi_encoder = FRQIEncoder(frqi_img)
        frqi_circuit = frqi_encoder.build_circuit()
        frqi_stats = frqi_encoder.get_circuit_stats()
        
        frqi_sim_result = simulator.run_shots(frqi_circuit, shots)
        frqi_reconstructor = FRQIReconstructor(frqi_encoder.n_position_qubits, frqi_img.shape)
        frqi_recon_result = frqi_reconstructor.reconstruct_from_counts(frqi_sim_result["counts"], shots)
        
        frqi_recon_pixels = (frqi_recon_result["image"] * max_pixel_val).astype(np.uint8)
        frqi_quality = evaluator.compute_image_quality(
            (frqi_img * max_pixel_val).astype(np.float64), 
            frqi_recon_pixels.astype(np.float64), 
            max_val=float(max_pixel_val)
        )
        
        frqi_diff = np.abs(processed_image.astype(np.int32) - frqi_recon_pixels.astype(np.int32))
        if frqi_diff.max() > 0:
            frqi_diff = (frqi_diff / frqi_diff.max() * 255)
        frqi_diff_b64 = np_to_b64(frqi_diff.astype(np.uint8), 255)
        end_frqi = time.time()
        
        # --- Run NEQR ---
        start_neqr = time.time()
        neqr_img = processor.normalize_for_neqr(processed_image, precision)
        neqr_encoder = NEQREncoder(neqr_img, precision)
        neqr_circuit = neqr_encoder.build_circuit()
        neqr_stats = neqr_encoder.get_circuit_stats()
        
        neqr_sim_result = simulator.run_shots(neqr_circuit, shots)
        neqr_reconstructor = NEQRReconstructor(neqr_encoder.n_position_qubits, neqr_encoder.n_intensity_qubits, neqr_img.shape)
        neqr_recon_result = neqr_reconstructor.reconstruct_from_counts(neqr_sim_result["counts"], shots)
        
        neqr_quality = evaluator.compute_image_quality(neqr_img.astype(np.float64), neqr_recon_result["image"].astype(np.float64), max_val=float(max_pixel_val))
        neqr_recon_pixels = neqr_recon_result["image"].astype(np.uint8)
        
        neqr_diff = np.abs(processed_image.astype(np.int32) - neqr_recon_pixels.astype(np.int32))
        if neqr_diff.max() > 0:
            neqr_diff = (neqr_diff / neqr_diff.max() * 255)
        neqr_diff_b64 = np_to_b64(neqr_diff.astype(np.uint8), 255)
        end_neqr = time.time()

        def extract_circuit(circuit):
            instructions = []
            for i, instr in enumerate(circuit.data):
                gate_name = instr.operation.name
                qubits = [circuit.find_bit(q).index for q in instr.qubits]
                controls = []
                targets = qubits
                if gate_name.startswith('c') and hasattr(instr.operation, 'num_ctrl_qubits'):
                    num_ctrl = instr.operation.num_ctrl_qubits
                    controls = qubits[:num_ctrl]
                    targets = qubits[num_ctrl:]
                elif gate_name.startswith('mc'):
                    num_ctrl = len(qubits) - 1
                    controls = qubits[:num_ctrl]
                    targets = [qubits[-1]]
                params = []
                if hasattr(instr.operation, 'params'):
                    for p in instr.operation.params:
                        try:
                            params.append(float(p))
                        except:
                            pass
                instructions.append({
                    "index": i,
                    "name": gate_name,
                    "controls": controls,
                    "targets": targets,
                    "qubits": qubits,
                    "params": params
                })
            return instructions

        return {
            "status": "completed",
            "original_image": f"data:image/png;base64,{original_b64}",
            "original_size": original_image.shape,
            "frqi": {
                "stats": frqi_stats,
                "metrics": {
                    "mse": frqi_quality["mse"],
                    "psnr": frqi_quality["psnr"],
                    "ssim": frqi_quality["ssim"],
                    "runtime": end_frqi - start_frqi
                },
                "reconstructed_image": f"data:image/png;base64,{np_to_b64(frqi_recon_pixels, max_pixel_val)}",
                "difference_image": f"data:image/png;base64,{frqi_diff_b64}",
                "circuit_instructions": extract_circuit(frqi_circuit),
                "num_qubits": frqi_circuit.num_qubits
            },
            "neqr": {
                "stats": neqr_stats,
                "metrics": {
                    "mse": neqr_quality["mse"],
                    "psnr": neqr_quality["psnr"],
                    "ssim": neqr_quality["ssim"],
                    "runtime": end_neqr - start_neqr
                },
                "reconstructed_image": f"data:image/png;base64,{np_to_b64(neqr_recon_pixels, max_pixel_val)}",
                "difference_image": f"data:image/png;base64,{neqr_diff_b64}",
                "circuit_instructions": extract_circuit(neqr_circuit),
                "num_qubits": neqr_circuit.num_qubits
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


@app.get("/api/quantum/reconstruct")
def reconstruct_experiment(
    image_name: str,
    category: str,
    representation: str = "FRQI",
    size: int = 4,
    bits: int = 8,
    shots: int = 1024
):
    import base64
    import io
    from PIL import Image
    import numpy as np
    from src.preprocessing.image_processor import ImageProcessor
    from src.frqi.encoder import FRQIEncoder
    from src.neqr.encoder import NEQREncoder
    from src.simulation.simulator import QuantumSimulator
    from src.reconstruction.reconstructor import FRQIReconstructor, NEQRReconstructor
    from src.metrics.evaluator import MetricsEvaluator
    from config.settings import DATASET_PATH
    
    img_path = DATASET_PATH / "train" / "images" / category / image_name
    if not img_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
        
    processor = ImageProcessor()
    original_image = processor.load_image(img_path)
    processed_image = processor.resize_image(original_image, (size, size))
    processed_image = processor.quantize_intensity(processed_image, bits)
    
    simulator = QuantumSimulator()
    evaluator = MetricsEvaluator()
    
    if representation.upper() == "FRQI":
        quantum_img = processor.normalize_for_frqi(processed_image, bits)
        encoder = FRQIEncoder(quantum_img)
        circuit = encoder.build_circuit()
        sim_result = simulator.run_shots(circuit, shots)
        reconstructor = FRQIReconstructor(encoder.n_position_qubits, quantum_img.shape)
        recon_result = reconstructor.reconstruct_from_counts(sim_result["counts"], shots)
        
        quality = evaluator.compute_image_quality(quantum_img, recon_result["image"], max_val=1.0)
        recon_pixels = (recon_result["image"] * (2**bits - 1)).astype(np.uint8)
        
    elif representation.upper() == "NEQR":
        quantum_img = processor.normalize_for_neqr(processed_image, bits)
        encoder = NEQREncoder(quantum_img, bits)
        circuit = encoder.build_circuit()
        sim_result = simulator.run_shots(circuit, shots)
        reconstructor = NEQRReconstructor(encoder.n_position_qubits, encoder.n_intensity_qubits, quantum_img.shape)
        recon_result = reconstructor.reconstruct_from_counts(sim_result["counts"], shots)
        
        quality = evaluator.compute_image_quality(quantum_img.astype(np.float64), recon_result["image"].astype(np.float64), max_val=float(2**bits - 1))
        recon_pixels = recon_result["image"].astype(np.uint8)
    else:
        raise HTTPException(status_code=400, detail="Unknown representation")
        
    # Helper to convert numpy array to base64 PNG
    def np_to_b64(arr):
        if arr.dtype == np.float64 or arr.dtype == np.float32:
            arr = (arr * 255).astype(np.uint8) if arr.max() <= 1.0 else arr.astype(np.uint8)
        # Resize it up with nearest neighbor so it's visible (e.g. 200x200)
        img = Image.fromarray(arr).resize((200, 200), Image.Resampling.NEAREST)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
        
    original_b64 = np_to_b64(processed_image)
    recon_b64 = np_to_b64(recon_pixels)
    
    # Difference image
    diff_arr = np.abs(processed_image.astype(np.int32) - recon_pixels.astype(np.int32))
    # Normalize difference for visibility
    if diff_arr.max() > 0:
        diff_arr = (diff_arr / diff_arr.max() * 255)
    diff_b64 = np_to_b64(diff_arr.astype(np.uint8))
    
    return {
        "mse": quality["mse"],
        "psnr": quality["psnr"],
        "ssim": quality["ssim"],
        "original_image": f"data:image/png;base64,{original_b64}",
        "reconstructed_image": f"data:image/png;base64,{recon_b64}",
        "difference_image": f"data:image/png;base64,{diff_b64}"
    }


@app.get("/api/quantum/circuit")
def get_quantum_circuit(representation: str = "FRQI", size: int = 4, bits: int = 8):
    """Dynamically generates the circuit for a given representation and returns the actual gates."""
    import numpy as np
    from src.preprocessing.image_processor import ImageProcessor
    
    processor = ImageProcessor()
    dummy_image = np.zeros((size, size), dtype=np.uint8)
    # Add a simple pattern so the circuit isn't totally empty
    dummy_image[0, 0] = 255
    dummy_image[size-1, size-1] = 128
    
    if representation.upper() == "FRQI":
        from src.frqi.encoder import FRQIEncoder
        frqi_img = processor.normalize_for_frqi(dummy_image, bits)
        encoder = FRQIEncoder(frqi_img)
    elif representation.upper() == "NEQR":
        from src.neqr.encoder import NEQREncoder
        neqr_img = processor.normalize_for_neqr(dummy_image, bits)
        encoder = NEQREncoder(neqr_img, bits)
    else:
        raise HTTPException(status_code=400, detail="Unknown representation")
        
    circuit = encoder.build_circuit()
    stats = encoder.get_circuit_stats()
    
    instructions = []
    # Qiskit circuit.data iteration
    for i, instr in enumerate(circuit.data):
        gate_name = instr.operation.name
        qubits = [circuit.find_bit(q).index for q in instr.qubits]
        
        controls = []
        targets = qubits
        
        if gate_name.startswith('c') and hasattr(instr.operation, 'num_ctrl_qubits'):
            num_ctrl = instr.operation.num_ctrl_qubits
            controls = qubits[:num_ctrl]
            targets = qubits[num_ctrl:]
        elif gate_name.startswith('mc'):
            num_ctrl = len(qubits) - 1
            controls = qubits[:num_ctrl]
            targets = [qubits[-1]]
            
        params = []
        if hasattr(instr.operation, 'params'):
            for p in instr.operation.params:
                try:
                    params.append(float(p))
                except:
                    pass
                    
        instructions.append({
            "index": i,
            "name": gate_name,
            "controls": controls,
            "targets": targets,
            "parameters": params
        })
        
    return {
        "qubits": stats["qubits"],
        "gates": stats["gates"],
        "depth": stats["depth"],
        "gate_types": stats["gate_types"],
        "instructions": instructions
    }


# ─── RESULT IMAGES ───────────────────────────────────────────────

@app.get("/api/results/images")
def list_result_images():
    d = PROJECT_ROOT / "results" / "images"
    if not d.exists():
        return []
    images = []
    for f in d.iterdir():
        if f.suffix.lower() in [".png", ".jpg", ".jpeg", ".bmp"]:
            images.append({"name": f.name, "url": f"/api/results/image/{f.name}"})
    return images


@app.get("/api/results/image/{filename}")
def serve_result_image(filename: str):
    p = PROJECT_ROOT / "results" / "images" / filename
    if p.exists():
        return FileResponse(str(p))
    raise HTTPException(status_code=404)


@app.get("/api/quantum/compare")
def get_quantum_comparison(defect_class: str = "all", resolution: str = "all", shots: str = "all"):
    """
    Returns paired comparison data between FRQI and NEQR based on actual experiment results.
    """
    from config.settings import RESULTS_EXPERIMENTS_PATH
    import pandas as pd
    import numpy as np
    import json
    
    save_path = RESULTS_EXPERIMENTS_PATH / "all_results.csv"
    if not save_path.exists():
        return {"error": "No experimental data found."}
        
    df = pd.read_csv(save_path)
    
    # Filter by user selections if not 'all'
    if defect_class != "all":
        df = df[df["defect_category"] == defect_class]
    if resolution != "all":
        df = df[df["resolution"] == resolution]
    if shots != "all":
        df = df[df["shots"] == int(shots)]
        
    # Standardize columns that might have empty/NaN
    df = df.fillna(0)
    
    # Separate FRQI and NEQR
    frqi_df = df[df["representation"] == "FRQI"]
    neqr_df = df[df["representation"] == "NEQR"]
    
    # Create an identifier for pairing: image_name + resolution + shots + precision
    def make_id(row):
        return f"{row['image_name']}_{row['resolution']}_{row['shots']}_{row['intensity_precision']}"
        
    if len(frqi_df) > 0:
        frqi_df = frqi_df.copy()
        frqi_df["pair_id"] = frqi_df.apply(make_id, axis=1)
        frqi_df = frqi_df.drop_duplicates(subset=["pair_id"], keep="last")
    else:
        frqi_df = pd.DataFrame(columns=["pair_id"])
        
    if len(neqr_df) > 0:
        neqr_df = neqr_df.copy()
        neqr_df["pair_id"] = neqr_df.apply(make_id, axis=1)
        neqr_df = neqr_df.drop_duplicates(subset=["pair_id"], keep="last")
    else:
        neqr_df = pd.DataFrame(columns=["pair_id"])
        
    frqi_ids = set(frqi_df["pair_id"].tolist()) if "pair_id" in frqi_df.columns else set()
    neqr_ids = set(neqr_df["pair_id"].tolist()) if "pair_id" in neqr_df.columns else set()
    
    paired_ids = frqi_ids.intersection(neqr_ids)
    frqi_only = len(frqi_ids - neqr_ids)
    neqr_only = len(neqr_ids - frqi_ids)
    
    paired_frqi = frqi_df[frqi_df["pair_id"].isin(paired_ids)].sort_values("pair_id")
    paired_neqr = neqr_df[neqr_df["pair_id"].isin(paired_ids)].sort_values("pair_id")
    
    # Construct pairs array
    pairs = []
    win_loss = {
        "mse": {"frqi": 0, "neqr": 0, "tie": 0},
        "psnr": {"frqi": 0, "neqr": 0, "tie": 0},
        "ssim": {"frqi": 0, "neqr": 0, "tie": 0},
        "qubits": {"frqi": 0, "neqr": 0, "tie": 0},
        "gate_count": {"frqi": 0, "neqr": 0, "tie": 0},
        "circuit_depth": {"frqi": 0, "neqr": 0, "tie": 0},
        "total_time": {"frqi": 0, "neqr": 0, "tie": 0}
    }
    
    # To properly zip, make sure they are aligned
    paired_frqi = paired_frqi.set_index("pair_id")
    paired_neqr = paired_neqr.set_index("pair_id")
    
    for pid in paired_ids:
        f_row = paired_frqi.loc[pid]
        n_row = paired_neqr.loc[pid]
        
        # Determine winners
        # MSE: lower is better
        if f_row["mse"] < n_row["mse"]: win_loss["mse"]["frqi"] += 1
        elif f_row["mse"] > n_row["mse"]: win_loss["mse"]["neqr"] += 1
        else: win_loss["mse"]["tie"] += 1
        
        # PSNR: higher is better
        if f_row["psnr"] > n_row["psnr"]: win_loss["psnr"]["frqi"] += 1
        elif f_row["psnr"] < n_row["psnr"]: win_loss["psnr"]["neqr"] += 1
        else: win_loss["psnr"]["tie"] += 1
        
        # SSIM: higher is better
        if f_row["ssim"] > n_row["ssim"]: win_loss["ssim"]["frqi"] += 1
        elif f_row["ssim"] < n_row["ssim"]: win_loss["ssim"]["neqr"] += 1
        else: win_loss["ssim"]["tie"] += 1
        
        # Qubits: lower is better
        if f_row["qubits"] < n_row["qubits"]: win_loss["qubits"]["frqi"] += 1
        elif f_row["qubits"] > n_row["qubits"]: win_loss["qubits"]["neqr"] += 1
        else: win_loss["qubits"]["tie"] += 1
        
        # Gate Count: lower is better
        if f_row["gate_count"] < n_row["gate_count"]: win_loss["gate_count"]["frqi"] += 1
        elif f_row["gate_count"] > n_row["gate_count"]: win_loss["gate_count"]["neqr"] += 1
        else: win_loss["gate_count"]["tie"] += 1
        
        # Depth: lower is better
        if f_row["circuit_depth"] < n_row["circuit_depth"]: win_loss["circuit_depth"]["frqi"] += 1
        elif f_row["circuit_depth"] > n_row["circuit_depth"]: win_loss["circuit_depth"]["neqr"] += 1
        else: win_loss["circuit_depth"]["tie"] += 1
        
        # Time: lower is better
        if f_row["total_time"] < n_row["total_time"]: win_loss["total_time"]["frqi"] += 1
        elif f_row["total_time"] > n_row["total_time"]: win_loss["total_time"]["neqr"] += 1
        else: win_loss["total_time"]["tie"] += 1
        
        pairs.append({
            "pair_id": str(pid),
            "image_name": str(f_row["image_name"]),
            "defect_category": str(f_row["defect_category"]),
            "resolution": str(f_row["resolution"]),
            "shots": int(f_row["shots"]),
            "frqi": json.loads(f_row.to_json()),
            "neqr": json.loads(n_row.to_json())
        })
        
    # Aggregate stats per class
    classes = df["defect_category"].unique().tolist() if "defect_category" in df.columns else []
    per_class = []
    for cls in classes:
        c_df = df[df["defect_category"] == cls]
        c_f = c_df[c_df["representation"] == "FRQI"]
        c_n = c_df[c_df["representation"] == "NEQR"]
        per_class.append({
            "class": cls,
            "frqi": {
                "count": len(c_f),
                "mse": float(c_f["mse"].mean()) if len(c_f) > 0 else 0,
                "psnr": float(c_f["psnr"].mean()) if len(c_f) > 0 else 0,
                "ssim": float(c_f["ssim"].mean()) if len(c_f) > 0 else 0
            },
            "neqr": {
                "count": len(c_n),
                "mse": float(c_n["mse"].mean()) if len(c_n) > 0 else 0,
                "psnr": float(c_n["psnr"].mean()) if len(c_n) > 0 else 0,
                "ssim": float(c_n["ssim"].mean()) if len(c_n) > 0 else 0
            }
        })
        
    # Aggregate stats per resolution
    resolutions = df["resolution"].unique().tolist() if "resolution" in df.columns else []
    resolutions.sort()
    per_resolution = []
    for res in resolutions:
        r_df = df[df["resolution"] == res]
        r_f = r_df[r_df["representation"] == "FRQI"]
        r_n = r_df[r_df["representation"] == "NEQR"]
        per_resolution.append({
            "resolution": res,
            "frqi": {
                "count": len(r_f),
                "qubits": float(r_f["qubits"].mean()) if len(r_f) > 0 else 0,
                "gate_count": float(r_f["gate_count"].mean()) if len(r_f) > 0 else 0,
                "circuit_depth": float(r_f["circuit_depth"].mean()) if len(r_f) > 0 else 0,
                "total_time": float(r_f["total_time"].mean()) if len(r_f) > 0 else 0
            },
            "neqr": {
                "count": len(r_n),
                "qubits": float(r_n["qubits"].mean()) if len(r_n) > 0 else 0,
                "gate_count": float(r_n["gate_count"].mean()) if len(r_n) > 0 else 0,
                "circuit_depth": float(r_n["circuit_depth"].mean()) if len(r_n) > 0 else 0,
                "total_time": float(r_n["total_time"].mean()) if len(r_n) > 0 else 0
            }
        })
        
    # Aggregate stats per shots
    shot_vals = [int(x) for x in df["shots"].unique().tolist()] if "shots" in df.columns else []
    shot_vals.sort()
    per_shots = []
    for s in shot_vals:
        s_df = df[df["shots"] == s]
        s_f = s_df[s_df["representation"] == "FRQI"]
        s_n = s_df[s_df["representation"] == "NEQR"]
        per_shots.append({
            "shots": s,
            "frqi": {
                "count": len(s_f),
                "mse": float(s_f["mse"].mean()) if len(s_f) > 0 else 0,
                "psnr": float(s_f["psnr"].mean()) if len(s_f) > 0 else 0,
                "ssim": float(s_f["ssim"].mean()) if len(s_f) > 0 else 0
            },
            "neqr": {
                "count": len(s_n),
                "mse": float(s_n["mse"].mean()) if len(s_n) > 0 else 0,
                "psnr": float(s_n["psnr"].mean()) if len(s_n) > 0 else 0,
                "ssim": float(s_n["ssim"].mean()) if len(s_n) > 0 else 0
            }
        })

    # Overall Summary
    overall_frqi = df[df["representation"] == "FRQI"]
    overall_neqr = df[df["representation"] == "NEQR"]
    
    def get_stats(sub_df):
        if len(sub_df) == 0: return {}
        return {
            "mse": {"mean": float(sub_df["mse"].mean()), "median": float(sub_df["mse"].median()), "std": float(sub_df["mse"].std()), "min": float(sub_df["mse"].min()), "max": float(sub_df["mse"].max()), "n": len(sub_df)},
            "psnr": {"mean": float(sub_df["psnr"].mean()), "median": float(sub_df["psnr"].median()), "std": float(sub_df["psnr"].std()), "min": float(sub_df["psnr"].min()), "max": float(sub_df["psnr"].max()), "n": len(sub_df)},
            "ssim": {"mean": float(sub_df["ssim"].mean()), "median": float(sub_df["ssim"].median()), "std": float(sub_df["ssim"].std()), "min": float(sub_df["ssim"].min()), "max": float(sub_df["ssim"].max()), "n": len(sub_df)},
            "gate_count": {"mean": float(sub_df["gate_count"].mean()), "median": float(sub_df["gate_count"].median()), "std": float(sub_df["gate_count"].std()), "min": float(sub_df["gate_count"].min()), "max": float(sub_df["gate_count"].max()), "n": len(sub_df)},
            "circuit_depth": {"mean": float(sub_df["circuit_depth"].mean()), "median": float(sub_df["circuit_depth"].median()), "std": float(sub_df["circuit_depth"].std()), "min": float(sub_df["circuit_depth"].min()), "max": float(sub_df["circuit_depth"].max()), "n": len(sub_df)},
            "total_time": {"mean": float(sub_df["total_time"].mean()), "median": float(sub_df["total_time"].median()), "std": float(sub_df["total_time"].std()), "min": float(sub_df["total_time"].min()), "max": float(sub_df["total_time"].max()), "n": len(sub_df)},
            "qubits": {"mean": float(sub_df["qubits"].mean()), "median": float(sub_df["qubits"].median()), "std": float(sub_df["qubits"].std()), "min": float(sub_df["qubits"].min()), "max": float(sub_df["qubits"].max()), "n": len(sub_df)}
        }
        
    return json.loads(json.dumps({
        "coverage": {
            "paired": int(len(paired_ids)),
            "frqi_only": int(frqi_only),
            "neqr_only": int(neqr_only),
            "total_frqi": int(len(frqi_ids)),
            "total_neqr": int(len(neqr_ids))
        },
        "win_loss": win_loss,
        "per_class": per_class,
        "per_resolution": per_resolution,
        "per_shots": per_shots,
        "overall_stats": {
            "frqi": get_stats(overall_frqi),
            "neqr": get_stats(overall_neqr)
        },
        "pairs": pairs,
        "available_filters": {
            "defect_classes": classes,
            "resolutions": resolutions,
            "shots": shot_vals
        }
    }))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

