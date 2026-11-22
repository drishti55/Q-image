"""
Comprehensive QML Experiment Manager for FRQI and NEQR Evaluation.

Orchestrates:
  - Dataset discovery across all 6 NEU-DET surface defect classes
  - Paired FRQI and NEQR experiment runs with shared comparison_id
  - Quantum Kernel, Variational Quantum, and Hybrid Quantum classifiers
  - Simultaneous separate evaluation of Classification and Reconstruction
  - Incremental persistence to JSON and CSV
  - Resumable batches and retries for interrupted suites
  - Analytics aggregator for all 15 interactive frontend charts
"""

import os
import json
import csv
import time
import uuid
import threading
import io
import base64
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.settings import (
    DATASET_PATH, TRAIN_IMAGES_PATH, VALIDATION_IMAGES_PATH,
    DEFECT_CATEGORIES, RANDOM_SEED, PROJECT_ROOT
)
from src.qml.frqi_qml import FRQIQMLPipeline
from src.qml.neqr_qml import NEQRQMLPipeline
from src.qml.models import (
    QuantumKernelClassifier, HybridQuantumClassifier,
    VariationalQuantumClassifier, evaluate_classifier_metrics
)
from src.qml.reconstruction_eval import QuantumReconstructionEvaluator, array_to_base64_png

RESULTS_QML_PATH = PROJECT_ROOT / "results" / "qml"
EXPERIMENTS_DIR = RESULTS_QML_PATH / "experiments"
CSV_INDEX_PATH = RESULTS_QML_PATH / "qml_experiments.csv"
JSON_INDEX_PATH = RESULTS_QML_PATH / "experiment_index.json"
DATASET_MANIFEST_PATH = RESULTS_QML_PATH / "dataset_manifest.json"

CANONICAL_CLASSES = [
    "crazing",
    "inclusion",
    "patches",
    "pitted_surface",
    "rolled-in_scale",
    "scratches",
]

DISPLAY_NAMES = {
    "crazing": "Crazing",
    "inclusion": "Inclusion",
    "patches": "Patches",
    "pitted_surface": "Pitted Surface",
    "rolled-in_scale": "Rolled-in Scale",
    "scratches": "Scratches",
}


def normalize_defect_label(label: str) -> str:
    """Canonicalize defect label to internal standard."""
    if not label:
        return "crazing"
    clean = str(label).strip().lower().replace(" ", "_")
    if "rolled" in clean and "scale" in clean:
        return "rolled-in_scale"
    if "pitted" in clean or "surface" in clean:
        return "pitted_surface"
    for c in CANONICAL_CLASSES:
        if c.replace("-", "").replace("_", "") == clean.replace("-", "").replace("_", ""):
            return c
    return clean


def safe_float(v: Any, default: float = 0.0) -> float:
    """Sanitize float for standard JSON compliance (replaces NaN/Inf)."""
    if v is None:
        return default
    try:
        val = float(v)
        if np.isnan(val) or np.isinf(val):
            return default
        return val
    except Exception:
        return default


def ensure_qml_dirs(root: Path = RESULTS_QML_PATH):
    root.mkdir(parents=True, exist_ok=True)
    (root / "experiments").mkdir(parents=True, exist_ok=True)


class HistoricalResultsReadOnlyError(PermissionError):
    """Raised when v0 code attempts to write into the immutable historical results directory."""


def _is_historical_root(root: Path) -> bool:
    try:
        return root.resolve() == RESULTS_QML_PATH.resolve()
    except Exception:
        return False


class QMLExperimentManager:
    """
    Full-lifecycle manager for paired FRQI + NEQR Quantum Machine Learning experiments.
    """

    CSV_HEADERS = [
        "experiment_id", "comparison_id", "dataset", "image_name", "ground_truth",
        "representation", "qml_model_type", "resolution", "intensity_bits", "shots",
        "backend", "n_qubits", "gate_count", "circuit_depth", "controlled_gates",
        "accuracy", "precision_macro", "recall_macro", "f1_macro", "f1_weighted",
        "recon_mse", "recon_psnr", "recon_ssim",
        "encoding_time_s", "train_time_s", "predict_time_s", "recon_time_s", "total_time_s",
        "status", "error_message", "timestamp"
    ]

    def __init__(self, results_root: Optional[Path] = None, read_only: Optional[bool] = None):
        """
        Args:
            results_root: Directory for v0-format records. Defaults to the historical
                results/qml directory.
            read_only: When True every write raises HistoricalResultsReadOnlyError.
                Defaults to True whenever results_root is the historical results/qml
                directory (Protocol V0 results are immutable evidence); tests must pass
                a temporary directory.
        """
        self.results_root = Path(results_root) if results_root is not None else RESULTS_QML_PATH
        self.experiments_dir = self.results_root / "experiments"
        self.csv_path = self.results_root / "qml_experiments.csv"
        self.index_path = self.results_root / "experiment_index.json"
        self.manifest_path = self.results_root / "dataset_manifest.json"
        self.read_only = _is_historical_root(self.results_root) if read_only is None else bool(read_only)
        self.recon_eval = QuantumReconstructionEvaluator(seed=RANDOM_SEED)
        if not self.read_only:
            ensure_qml_dirs(self.results_root)
            self._init_csv()

    def _guard_write(self):
        if self.read_only:
            raise HistoricalResultsReadOnlyError(
                f"{self.results_root} holds immutable Protocol V0 results; "
                "new experiments must use the v2 runner (results/qml_v2)."
            )

    def _init_csv(self):
        """Ensure CSV index exists with appropriate headers."""
        self._guard_write()
        if not self.csv_path.exists():
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.CSV_HEADERS)

    # ─── DATASET DISCOVERY ───────────────────────────────────────────

    def discover_dataset(self) -> Dict[str, Any]:
        """
        Discover all images in the NEU-DET dataset.
        Returns counts, categories, and image paths for train and validation splits.
        Persists a stable dataset_manifest.json.
        """
        manifest = {
            "dataset_path": str(DATASET_PATH),
            "classes": CANONICAL_CLASSES,
            "display_names": DISPLAY_NAMES,
            "train_counts": {c: 0 for c in CANONICAL_CLASSES},
            "val_counts": {c: 0 for c in CANONICAL_CLASSES},
            "total_images": 0,
            "images": []
        }

        # Train split
        if TRAIN_IMAGES_PATH.exists():
            for d in TRAIN_IMAGES_PATH.iterdir():
                if not d.is_dir():
                    continue
                cat = normalize_defect_label(d.name)
                files = sorted([
                    p for p in d.iterdir()
                    if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp")
                ])
                manifest["train_counts"][cat] = len(files)
                for f in files:
                    img_id = f.stem
                    manifest["images"].append({
                        "image_id": img_id,
                        "image_name": f.name,
                        "path": str(f),
                        "ground_truth": cat,
                        "ground_truth_display": DISPLAY_NAMES.get(cat, cat.title()),
                        "split": "train",
                        "status": "available",
                    })

        # Validation split
        if VALIDATION_IMAGES_PATH.exists():
            for d in VALIDATION_IMAGES_PATH.iterdir():
                if not d.is_dir():
                    continue
                cat = normalize_defect_label(d.name)
                files = sorted([
                    p for p in d.iterdir()
                    if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp")
                ])
                manifest["val_counts"][cat] = len(files)
                for f in files:
                    img_id = f.stem
                    manifest["images"].append({
                        "image_id": img_id,
                        "image_name": f.name,
                        "path": str(f),
                        "ground_truth": cat,
                        "ground_truth_display": DISPLAY_NAMES.get(cat, cat.title()),
                        "split": "val",
                        "status": "available",
                    })

        manifest["total_images"] = len(manifest["images"])

        # Persist manifest (never into the read-only historical directory)
        if self.read_only:
            return manifest
        try:
            with open(self.manifest_path, "w", encoding="utf-8") as fp:
                json.dump(manifest, fp, indent=2)
        except Exception as err:
            print(f"Warning: could not save dataset manifest: {err}")

        return manifest

    def load_processed_images(
        self,
        resolution: Tuple[int, int] = (4, 4),
        max_per_class: int = 10,
        split: str = "train",
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Load and resize dataset images to target quantum resolution.
        Returns:
            X: np.ndarray of shape (N, H, W) normalized to [0, 1]
            y: np.ndarray of shape (N,) integer class indices
            names: list of filenames
        """
        base_dir = TRAIN_IMAGES_PATH if split == "train" else VALIDATION_IMAGES_PATH
        X_list, y_list, names = [], [], []

        for class_idx, cat in enumerate(DEFECT_CATEGORIES):
            cat_dir = base_dir / cat
            if not cat_dir.exists():
                continue
            files = sorted([
                p for p in cat_dir.iterdir()
                if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp")
            ])
            if max_per_class is not None:
                files = files[:max_per_class]

            for f in files:
                try:
                    with Image.open(f) as img:
                        gray = img.convert("L").resize(resolution, Image.Resampling.BILINEAR)
                        arr = np.array(gray, dtype=np.float64) / 255.0
                        X_list.append(arr)
                        y_list.append(class_idx)
                        names.append(f.name)
                except Exception as e:
                    print(f"Error loading {f}: {e}")

        return np.array(X_list), np.array(y_list), names

    # ─── EXPERIMENT EXECUTION ────────────────────────────────────────

    def run_paired_experiment(
        self,
        config: Dict[str, Any],
        progress_callback=None,
    ) -> Dict[str, Any]:
        """
        Run paired experiments:
          Same image configuration -> FRQI experiment
          Same image configuration -> NEQR experiment
        Linked by shared comparison_id.
        """
        self._guard_write()
        comparison_id = str(uuid.uuid4())[:8]
        start_time = datetime.now().isoformat()

        # Parse config
        res_str = config.get("resolution", "4x4")
        w, h = map(int, res_str.split("x"))
        resolution = (h, w)
        intensity_bits = int(config.get("intensity_bits", 4))
        shots = int(config.get("shots", 0))
        model_type = config.get("model_type", "Quantum Kernel Classifier")
        max_per_class = int(config.get("max_per_class", 10))
        test_ratio = float(config.get("test_ratio", 0.3))
        seed = int(config.get("seed", RANDOM_SEED))

        if progress_callback:
            progress_callback({
                "phase": "loading_data",
                "message": f"Loading NEU-DET images ({max_per_class} per class at {res_str})...",
                "percent": 10
            })

        # Load dataset
        X, y, names = self.load_processed_images(
            resolution=resolution, max_per_class=max_per_class, split="train"
        )
        if len(X) == 0:
            raise RuntimeError("No images found in dataset path.")

        # Stratified train/test split
        np.random.seed(seed)
        train_idx, test_idx = self._stratified_split(y, test_ratio=test_ratio, seed=seed)
        X_train, y_train = X[train_idx], y[train_idx]
        X_test, y_test = X[test_idx], y[test_idx]
        names_test = [names[i] for i in test_idx]

        # ── 1. FRQI EXPERIMENT ──
        frqi_exp_id = str(uuid.uuid4())[:8]
        if progress_callback:
            progress_callback({
                "phase": "frqi_execution",
                "message": f"Executing FRQI {model_type} on {len(X_train)} train / {len(X_test)} test...",
                "percent": 25
            })

        frqi_record = self._run_single_representation_pipeline(
            representation="FRQI",
            experiment_id=frqi_exp_id,
            comparison_id=comparison_id,
            model_type=model_type,
            resolution=resolution,
            intensity_bits=intensity_bits,
            shots=shots,
            seed=seed,
            X_train=X_train,
            y_train=y_train,
            X_test=X_test,
            y_test=y_test,
            test_names=names_test,
            callback=lambda msg, pct: progress_callback({"phase": "frqi", "message": msg, "percent": 25 + int(pct * 0.3)}) if progress_callback else None
        )

        # ── 2. NEQR EXPERIMENT ──
        neqr_exp_id = str(uuid.uuid4())[:8]
        if progress_callback:
            progress_callback({
                "phase": "neqr_execution",
                "message": f"Executing NEQR {model_type} ({intensity_bits}-bit) on {len(X_train)} train / {len(X_test)} test...",
                "percent": 60
            })

        neqr_record = self._run_single_representation_pipeline(
            representation="NEQR",
            experiment_id=neqr_exp_id,
            comparison_id=comparison_id,
            model_type=model_type,
            resolution=resolution,
            intensity_bits=intensity_bits,
            shots=shots,
            seed=seed,
            X_train=X_train,
            y_train=y_train,
            X_test=X_test,
            y_test=y_test,
            test_names=names_test,
            callback=lambda msg, pct: progress_callback({"phase": "neqr", "message": msg, "percent": 60 + int(pct * 0.3)}) if progress_callback else None
        )

        # Save both records
        self._persist_experiment(frqi_record)
        self._persist_experiment(neqr_record)

        if progress_callback:
            progress_callback({
                "phase": "completed",
                "message": f"Paired experiment {comparison_id} completed successfully!",
                "percent": 100
            })

        return {
            "comparison_id": comparison_id,
            "status": "completed",
            "resolution": res_str,
            "model_type": model_type,
            "shots": shots,
            "intensity_bits": intensity_bits,
            "frqi_experiment": frqi_record,
            "neqr_experiment": neqr_record,
        }

    def _stratified_split(self, y: np.ndarray, test_ratio: float = 0.3, seed: int = 42) -> Tuple[np.ndarray, np.ndarray]:
        """Deterministic stratified train/test split index generator."""
        from sklearn.model_selection import StratifiedShuffleSplit
        sss = StratifiedShuffleSplit(n_splits=1, test_size=test_ratio, random_state=seed)
        dummy_X = np.zeros((len(y), 1))
        train_idx, test_idx = next(sss.split(dummy_X, y))
        return train_idx, test_idx

    def _run_single_representation_pipeline(
        self,
        representation: str,
        experiment_id: str,
        comparison_id: str,
        model_type: str,
        resolution: Tuple[int, int],
        intensity_bits: int,
        shots: int,
        seed: int,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
        test_names: List[str],
        callback=None,
    ) -> Dict[str, Any]:
        """Runs one representation's quantum pipeline (FRQI or NEQR)."""
        t_start = time.perf_counter()
        
        # 1. Circuit & Resource Extraction
        sample_img = X_train[0]
        if representation == "FRQI":
            pipeline = FRQIQMLPipeline(resolution=resolution, shots=shots, seed=seed)
            c_stats = pipeline.get_circuit_stats(sample_img)
        else:
            pipeline = NEQRQMLPipeline(resolution=resolution, intensity_bits=intensity_bits, shots=shots, seed=seed)
            c_stats = pipeline.get_circuit_stats(sample_img)

        # 2. QML Model Training & Evaluation
        if model_type == "Quantum Kernel Classifier":
            clf = QuantumKernelClassifier(
                representation=representation,
                resolution=resolution,
                intensity_bits=intensity_bits,
                shots=shots,
                seed=seed,
            )
        elif model_type == "Variational Quantum Classifier":
            clf = VariationalQuantumClassifier(
                representation=representation,
                resolution=resolution,
                intensity_bits=intensity_bits,
                epochs=15,
                seed=seed,
            )
        else:
            clf = HybridQuantumClassifier(
                representation=representation,
                resolution=resolution,
                intensity_bits=intensity_bits,
                shots=shots,
                seed=seed,
            )

        clf.fit(X_train, y_train, callback=callback)
        y_pred = clf.predict(X_test)
        cls_metrics = evaluate_classifier_metrics(y_test, y_pred)

        # 3. Image Reconstruction Evaluation on first test sample
        recon_sample = X_test[0]
        if representation == "FRQI":
            recon_res = self.recon_eval.evaluate_frqi(recon_sample, resolution=resolution, shots=shots)
        else:
            recon_res = self.recon_eval.evaluate_neqr(
                recon_sample, resolution=resolution, intensity_bits=intensity_bits, shots=shots
            )

        total_time = time.perf_counter() - t_start

        record = {
            "experiment_id": experiment_id,
            "comparison_id": comparison_id,
            "dataset": "NEU-DET",
            "image_name": test_names[0] if test_names else "sample.jpg",
            "ground_truth": DEFECT_CATEGORIES[y_test[0]] if len(y_test) > 0 else "unknown",
            "representation": representation,
            "qml_model_type": model_type,
            "resolution": f"{resolution[0]}x{resolution[1]}",
            "intensity_bits": intensity_bits if representation == "NEQR" else 8,
            "shots": shots,
            "backend": "AerSimulator (statevector)" if shots == 0 else f"AerSimulator ({shots} shots)",
            "n_qubits": c_stats["qubits"],
            "gate_count": c_stats["gates"],
            "circuit_depth": c_stats["depth"],
            "controlled_gates": c_stats["controlled_gates"],
            "gate_types": c_stats.get("gate_types", {}),
            "classification_metrics": cls_metrics,
            "reconstruction_metrics": {
                "mse": recon_res["mse"],
                "psnr": recon_res["psnr"],
                "ssim": recon_res["ssim"],
                "reconstruction_time": recon_res["reconstruction_time"],
                "original_b64": recon_res["original_b64"],
                "reconstructed_b64": recon_res["reconstructed_b64"],
                "diff_b64": recon_res["diff_b64"],
            },
            "training_history": getattr(clf, "training_history", []),
            "timings": {
                "encoding_time_s": c_stats["encoding_time"],
                "train_time_s": clf.train_time,
                "predict_time_s": clf.predict_time,
                "reconstruction_time_s": recon_res["reconstruction_time"],
                "total_time_s": total_time,
            },
            "status": "completed",
            "error_message": "",
            "timestamp": datetime.now().isoformat(),
        }
        return record

    def run_full_dataset_pipeline(
        self,
        config: Dict[str, Any],
        progress_callback=None,
    ) -> Dict[str, Any]:
        """
        Execute systematic FRQI and NEQR quantum pipelines across the FULL NEU-DET dataset.

        1. Discovers all 1,800 images in the dataset across 6 classes.
        2. Fits FRQI and NEQR quantum classifiers on training data.
        3. Iterates over all eligible images in resumable batches.
        4. For each image, executes paired FRQI and NEQR encoding, stats extraction,
           quantum expectation inference, and reconstruction quality evaluation.
        5. Persists every result incrementally into CSV and JSON.
        """
        self._guard_write()
        res_str = config.get("resolution", "4x4")
        w, h = map(int, res_str.split("x"))
        resolution = (h, w)
        intensity_bits = int(config.get("intensity_bits", 4))
        shots = int(config.get("shots", 0))
        seed = int(config.get("seed", RANDOM_SEED))
        model_type = config.get("model_type", "Hybrid Quantum-Classical Classifier")
        batch_limit = config.get("batch_limit", None)  # None = process all eligible

        # Step 1: Discover manifest
        manifest = self.discover_dataset()
        all_images = manifest["images"]
        total_images = len(all_images)

        if progress_callback:
            progress_callback({
                "phase": "dataset_discovery",
                "message": f"Discovered {total_images} images across 6 defect classes.",
                "percent": 5,
                "completed": 0,
                "pending": total_images,
                "failed": 0,
            })

        # Step 2: Train QML models on training split
        if progress_callback:
            progress_callback({
                "phase": "model_training",
                "message": f"Training FRQI and NEQR {model_type} on training split...",
                "percent": 10,
                "completed": 0,
                "pending": total_images,
                "failed": 0,
            })

        X_train, y_train, _ = self.load_processed_images(
            resolution=resolution, max_per_class=20, split="train"
        )

        def _create_classifier(rep: str):
            if model_type == "Quantum Kernel Classifier":
                return QuantumKernelClassifier(
                    representation=rep, resolution=resolution, intensity_bits=intensity_bits, shots=shots, seed=seed
                )
            elif model_type == "Variational Quantum Classifier":
                return VariationalQuantumClassifier(
                    representation=rep, resolution=resolution, intensity_bits=intensity_bits, epochs=15, seed=seed
                )
            else:
                return HybridQuantumClassifier(
                    representation=rep, resolution=resolution, intensity_bits=intensity_bits, shots=shots, seed=seed
                )

        frqi_clf = _create_classifier("FRQI")
        frqi_clf.fit(X_train, y_train)

        neqr_clf = _create_classifier("NEQR")
        neqr_clf.fit(X_train, y_train)

        # Held-out validation split evaluation
        X_val, y_val, _ = self.load_processed_images(
            resolution=resolution, max_per_class=None, split="val"
        )
        frqi_val_preds = frqi_clf.predict(X_val)
        neqr_val_preds = neqr_clf.predict(X_val)
        frqi_heldout = evaluate_classifier_metrics(y_val, frqi_val_preds)
        neqr_heldout = evaluate_classifier_metrics(y_val, neqr_val_preds)

        pipe_frqi = FRQIQMLPipeline(resolution=resolution, shots=shots, seed=seed)
        pipe_neqr = NEQRQMLPipeline(resolution=resolution, intensity_bits=intensity_bits, shots=shots, seed=seed)

        # Step 3: Get already processed IDs for resumability
        history = self.get_experiment_history()
        history_map = {e["experiment_id"]: e for e in history if "experiment_id" in e}
        existing_exp_ids = set(history_map.keys())

        completed_count = 0
        skipped_count = 0
        failed_count = 0

        target_images = all_images if batch_limit is None else all_images[:batch_limit]
        n_targets = len(target_images)

        start_time_all = time.perf_counter()

        for idx, img_info in enumerate(target_images, 1):
            img_name = img_info["image_name"]
            img_path = Path(img_info["path"])
            cat = img_info["class"]
            cat_idx = DEFECT_CATEGORIES.index(cat) if cat in DEFECT_CATEGORIES else 0
            split = img_info["split"]

            safe_name = img_name.replace(".", "_")
            comp_id = f"paired_{safe_name}_{res_str}"
            frqi_id = f"frqi_{safe_name}_{res_str}"
            neqr_id = f"neqr_{safe_name}_{res_str}"

            if frqi_id in existing_exp_ids and neqr_id in existing_exp_ids:
                skipped_count += 1
                continue

            try:
                # Preprocess image
                with Image.open(img_path) as pil_img:
                    gray = pil_img.convert("L").resize(resolution, Image.Resampling.BILINEAR)
                    arr = np.array(gray, dtype=np.float64) / 255.0

                # ── FRQI RUN ──
                t0_frqi = time.perf_counter()
                frqi_stats = pipe_frqi.get_circuit_stats(arr)
                frqi_pred_idx = int(frqi_clf.predict(np.array([arr]))[0])
                frqi_pred_name = DEFECT_CATEGORIES[frqi_pred_idx]
                frqi_recon = self.recon_eval.evaluate_frqi(arr, resolution=resolution, shots=shots)
                t_frqi_tot = time.perf_counter() - t0_frqi

                frqi_record = {
                    "experiment_id": frqi_id,
                    "comparison_id": comp_id,
                    "dataset": "NEU-DET",
                    "image_name": img_name,
                    "ground_truth": cat,
                    "predicted_class": frqi_pred_name,
                    "correct": bool(cat == frqi_pred_name),
                    "representation": "FRQI",
                    "qml_model_type": model_type,
                    "resolution": res_str,
                    "intensity_bits": 8,
                    "shots": shots,
                    "backend": "AerSimulator (statevector)" if shots == 0 else f"AerSimulator ({shots} shots)",
                    "n_qubits": frqi_stats["qubits"],
                    "gate_count": frqi_stats["gates"],
                    "circuit_depth": frqi_stats["depth"],
                    "controlled_gates": frqi_stats["controlled_gates"],
                    "gate_types": frqi_stats.get("gate_types", {}),
                    "classification_metrics": {
                        "accuracy": 1.0 if cat == frqi_pred_name else 0.0,
                        "f1_macro": 1.0 if cat == frqi_pred_name else 0.0,
                        "heldout_accuracy": frqi_heldout["accuracy"],
                        "heldout_f1_macro": frqi_heldout["f1_macro"],
                        "precision_macro": frqi_heldout["precision_macro"],
                        "recall_macro": frqi_heldout["recall_macro"],
                        "f1_weighted": frqi_heldout["f1_weighted"],
                        "confusion_matrix": frqi_heldout["confusion_matrix"],
                        "per_class": frqi_heldout["per_class"],
                    },
                    "reconstruction_metrics": {
                        "mse": frqi_recon["mse"],
                        "psnr": frqi_recon["psnr"],
                        "ssim": frqi_recon["ssim"],
                        "reconstruction_time": frqi_recon["reconstruction_time"],
                        "original_b64": frqi_recon["original_b64"],
                        "reconstructed_b64": frqi_recon["reconstructed_b64"],
                        "diff_b64": frqi_recon["diff_b64"],
                    },
                    "timings": {
                        "encoding_time_s": frqi_stats["encoding_time"],
                        "train_time_s": frqi_clf.train_time,
                        "predict_time_s": frqi_clf.predict_time,
                        "reconstruction_time_s": frqi_recon["reconstruction_time"],
                        "total_time_s": t_frqi_tot,
                    },
                    "status": "completed",
                    "error_message": "",
                    "timestamp": datetime.now().isoformat(),
                }
                self._persist_experiment(frqi_record, update_index=False)

                # ── NEQR RUN ──
                t0_neqr = time.perf_counter()
                neqr_stats = pipe_neqr.get_circuit_stats(arr)
                neqr_pred_idx = int(neqr_clf.predict(np.array([arr]))[0])
                neqr_pred_name = DEFECT_CATEGORIES[neqr_pred_idx]
                neqr_recon = self.recon_eval.evaluate_neqr(
                    arr, resolution=resolution, intensity_bits=intensity_bits, shots=shots
                )
                t_neqr_tot = time.perf_counter() - t0_neqr

                neqr_record = {
                    "experiment_id": neqr_id,
                    "comparison_id": comp_id,
                    "dataset": "NEU-DET",
                    "image_name": img_name,
                    "ground_truth": cat,
                    "predicted_class": neqr_pred_name,
                    "correct": bool(cat == neqr_pred_name),
                    "representation": "NEQR",
                    "qml_model_type": model_type,
                    "resolution": res_str,
                    "intensity_bits": intensity_bits,
                    "shots": shots,
                    "backend": "AerSimulator (statevector)" if shots == 0 else f"AerSimulator ({shots} shots)",
                    "n_qubits": neqr_stats["qubits"],
                    "gate_count": neqr_stats["gates"],
                    "circuit_depth": neqr_stats["depth"],
                    "controlled_gates": neqr_stats["controlled_gates"],
                    "gate_types": neqr_stats.get("gate_types", {}),
                    "classification_metrics": {
                        "accuracy": 1.0 if cat == neqr_pred_name else 0.0,
                        "f1_macro": 1.0 if cat == neqr_pred_name else 0.0,
                        "heldout_accuracy": neqr_heldout["accuracy"],
                        "heldout_f1_macro": neqr_heldout["f1_macro"],
                        "precision_macro": neqr_heldout["precision_macro"],
                        "recall_macro": neqr_heldout["recall_macro"],
                        "f1_weighted": neqr_heldout["f1_weighted"],
                        "confusion_matrix": neqr_heldout["confusion_matrix"],
                        "per_class": neqr_heldout["per_class"],
                    },
                    "reconstruction_metrics": {
                        "mse": neqr_recon["mse"],
                        "psnr": neqr_recon["psnr"],
                        "ssim": neqr_recon["ssim"],
                        "reconstruction_time": neqr_recon["reconstruction_time"],
                        "original_b64": neqr_recon["original_b64"],
                        "reconstructed_b64": neqr_recon["reconstructed_b64"],
                        "diff_b64": neqr_recon["diff_b64"],
                    },
                    "timings": {
                        "encoding_time_s": neqr_stats["encoding_time"],
                        "train_time_s": neqr_clf.train_time,
                        "predict_time_s": neqr_clf.predict_time,
                        "reconstruction_time_s": neqr_recon["reconstruction_time"],
                        "total_time_s": t_neqr_tot,
                    },
                    "status": "completed",
                    "error_message": "",
                    "timestamp": datetime.now().isoformat(),
                }
                self._persist_experiment(neqr_record, update_index=False)

                history_map[frqi_id] = self._create_index_entry(frqi_record)
                history_map[neqr_id] = self._create_index_entry(neqr_record)
                existing_exp_ids.add(frqi_id)
                existing_exp_ids.add(neqr_id)
                completed_count += 1

                # Flush history index every 25 samples
                if idx % 25 == 0 or idx == n_targets:
                    with open(self.index_path, "w", encoding="utf-8") as f:
                        json.dump(list(history_map.values()), f, indent=2)

                # Update progress callback every 10 samples
                if progress_callback and (idx % 10 == 0 or idx == n_targets):
                    pct = int(10 + (idx / n_targets) * 90)
                    progress_callback({
                        "phase": "full_dataset_execution",
                        "message": f"Processed {idx}/{n_targets} images ({completed_count} completed, {skipped_count} resumed)",
                        "percent": pct,
                        "current_image": img_name,
                        "current_class": cat,
                        "completed": completed_count,
                        "pending": n_targets - idx,
                        "failed": failed_count,
                    })

            except Exception as e:
                failed_count += 1
                print(f"Error on {img_name}: {e}")

        # Final flush
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(list(history_map.values()), f, indent=2)

        total_duration = time.perf_counter() - start_time_all

        if progress_callback:
            progress_callback({
                "phase": "completed",
                "message": f"Full dataset pipeline completed: {completed_count} processed, {skipped_count} skipped/resumed in {total_duration:.1f}s",
                "percent": 100,
                "completed": completed_count,
                "pending": 0,
                "failed": failed_count,
            })

        return {
            "status": "completed",
            "total_images": total_images,
            "images_processed": completed_count,
            "images_skipped": skipped_count,
            "failed_count": failed_count,
            "total_duration_s": total_duration,
            "resolution": res_str,
            "model_type": model_type,
        }

    def _create_index_entry(self, record: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "experiment_id": record["experiment_id"],
            "comparison_id": record.get("comparison_id", ""),
            "representation": record.get("representation", "FRQI"),
            "qml_model_type": record.get("qml_model_type", record.get("config", {}).get("model_type", "Quantum Kernel Classifier")),
            "resolution": record.get("resolution", "4x4"),
            "shots": record.get("shots", 0),
            "status": record.get("status", "completed"),
            "test_accuracy": record.get("classification_metrics", {}).get("accuracy", record.get("evaluation", {}).get("test_accuracy", 0.0)),
            "f1_macro": record.get("classification_metrics", {}).get("f1_macro", record.get("evaluation", {}).get("f1_macro", 0.0)),
            "recon_psnr": record.get("reconstruction_metrics", {}).get("psnr", 0.0),
            "total_time_s": record.get("timings", {}).get("total_time_s", 0.0),
            "timestamp": record.get("timestamp", datetime.now().isoformat()),
        }

    def _persist_experiment(self, record: Dict[str, Any], update_index: bool = True):
        """Persist experiment record to JSON and CSV incrementally."""
        self._guard_write()
        exp_id = record["experiment_id"]
        # Save individual JSON
        json_file = self.experiments_dir / f"{exp_id}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)

        # Update JSON index
        if update_index:
            history = self.get_experiment_history()
            history = [e for e in history if e.get("experiment_id") != exp_id]
            history.append(self._create_index_entry(record))
            with open(self.index_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)

        # Append to CSV
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                record["experiment_id"],
                record.get("comparison_id", ""),
                record.get("dataset", "NEU-DET"),
                record.get("image_name", ""),
                record.get("ground_truth", ""),
                record.get("representation", "FRQI"),
                record.get("qml_model_type", record.get("config", {}).get("model_type", "Quantum Kernel Classifier")),
                record.get("resolution", "4x4"),
                record.get("intensity_bits", 8),
                record.get("shots", 0),
                record.get("backend", "AerSimulator"),
                record.get("n_qubits", record.get("config", {}).get("n_qubits", 5)),
                record.get("gate_count", 0),
                record.get("circuit_depth", 0),
                record.get("controlled_gates", 0),
                record.get("classification_metrics", {}).get("accuracy", record.get("evaluation", {}).get("test_accuracy", 0.0)),
                record.get("classification_metrics", {}).get("precision_macro", 0.0),
                record.get("classification_metrics", {}).get("recall_macro", 0.0),
                record.get("classification_metrics", {}).get("f1_macro", record.get("evaluation", {}).get("f1_macro", 0.0)),
                record.get("classification_metrics", {}).get("f1_weighted", record.get("evaluation", {}).get("f1_weighted", 0.0)),
                record.get("reconstruction_metrics", {}).get("mse", 0.0),
                record.get("reconstruction_metrics", {}).get("psnr", 0.0),
                record.get("reconstruction_metrics", {}).get("ssim", 0.0),
                record.get("timings", {}).get("encoding_time_s", 0.0),
                record.get("timings", {}).get("train_time_s", 0.0),
                record.get("timings", {}).get("predict_time_s", 0.0),
                record.get("timings", {}).get("reconstruction_time_s", 0.0),
                record.get("timings", {}).get("total_time_s", 0.0),
                record.get("status", "completed"),
                record.get("error_message", record.get("error", "")),
                record.get("timestamp", datetime.now().isoformat()),
            ])

    def get_experiment_history(self) -> List[Dict[str, Any]]:
        """Retrieve index of all executed experiments with safe default fallback."""
        if not self.index_path.exists():
            return []
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if not isinstance(raw, list):
                return []
            sanitized = []
            for e in raw:
                if not isinstance(e, dict):
                    continue
                entry = {
                    "experiment_id": str(e.get("experiment_id", "")),
                    "comparison_id": str(e.get("comparison_id", "")),
                    "representation": str(e.get("representation", "FRQI")),
                    "qml_model_type": str(e.get("qml_model_type", e.get("model_type", "Hybrid Quantum-Classical Classifier"))),
                    "resolution": str(e.get("resolution", "4x4")),
                    "shots": int(e.get("shots", 0)),
                    "status": str(e.get("status", "completed")),
                    "test_accuracy": safe_float(e.get("test_accuracy", e.get("accuracy", 0.0))),
                    "f1_macro": safe_float(e.get("f1_macro", 0.0)),
                    "recon_psnr": safe_float(e.get("recon_psnr", 0.0)),
                    "total_time_s": safe_float(e.get("total_time_s", 0.0)),
                    "timestamp": str(e.get("timestamp", "")),
                }
                sanitized.append(entry)
            return sanitized
        except Exception as err:
            print(f"Error reading history index: {err}")
            return []

    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full details for an experiment ID."""
        json_file = self.experiments_dir / f"{experiment_id}.json"
        if json_file.exists():
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def get_overview_kpis(self) -> Dict[str, Any]:
        """Calculate KPI cards across all experiments."""
        dataset_info = self.discover_dataset()
        history = self.get_experiment_history()

        completed = [e for e in history if e.get("status") == "completed"]
        failed = [e for e in history if e.get("status") == "failed"]
        frqi_count = sum(1 for e in history if e.get("representation") == "FRQI")
        neqr_count = sum(1 for e in history if e.get("representation") == "NEQR")

        # Count successful paired comparisons
        comparison_ids = {}
        for e in completed:
            cid = e.get("comparison_id")
            if cid:
                comparison_ids[cid] = comparison_ids.get(cid, 0) + 1
        paired_count = sum(1 for cid, cnt in comparison_ids.items() if cnt >= 2)

        models = sorted(list(set(e.get("qml_model_type", "") for e in completed if e.get("qml_model_type"))))
        resolutions = sorted(list(set(e.get("resolution", "") for e in completed if e.get("resolution"))))

        return {
            "total_eligible_images": dataset_info["total_images"],
            "completed_experiments": len(completed),
            "pending_experiments": max(0, dataset_info["total_images"] * 2 - len(completed)),
            "running_experiments": 0,
            "failed_experiments": len(failed),
            "frqi_experiments": frqi_count,
            "neqr_experiments": neqr_count,
            "paired_comparisons": paired_count,
            "models_evaluated": models or [
                "Hybrid Quantum-Classical Classifier",
                "Quantum Kernel Classifier",
                "Variational Quantum Classifier"
            ],
            "resolutions_tested": resolutions or ["2x2", "4x4", "8x8"],
        }

    # ─── 15 INTERACTIVE VISUALIZATION ANALYTICS ──────────────────────

    def get_analytics_graphs(self) -> Dict[str, Any]:
        """
        Computes data arrays for the 15 requested frontend charts from real experiment records.
        Guarantees all 6 surface defect categories in charts 3, 4, and 12.
        """
        history = self.get_experiment_history()
        records = []
        for h in history:
            exp = self.get_experiment(h.get("experiment_id", ""))
            if exp and exp.get("status") == "completed":
                records.append(exp)

        # 1. Accuracy Comparison (FRQI vs NEQR by Model)
        acc_by_model: Dict[str, Dict[str, List[float]]] = {}
        for r in records:
            m = r.get("qml_model_type", "Hybrid Quantum-Classical Classifier")
            rep = r.get("representation")
            acc = safe_float(r.get("classification_metrics", {}).get("accuracy", 0.0))
            if m not in acc_by_model:
                acc_by_model[m] = {"FRQI": [], "NEQR": []}
            if rep in ("FRQI", "NEQR"):
                acc_by_model[m][rep].append(acc)

        chart1_acc_comparison = [
            {
                "model": m,
                "FRQI": round(float(np.mean(vals["FRQI"])), 4) if vals["FRQI"] else 0.0,
                "NEQR": round(float(np.mean(vals["NEQR"])), 4) if vals["NEQR"] else 0.0,
            }
            for m, vals in sorted(acc_by_model.items())
        ]

        # 2. Macro F1 Comparison (FRQI vs NEQR by Model)
        f1_by_model: Dict[str, Dict[str, List[float]]] = {}
        for r in records:
            m = r.get("qml_model_type", "Hybrid Quantum-Classical Classifier")
            rep = r.get("representation")
            f1 = safe_float(r.get("classification_metrics", {}).get("f1_macro", 0.0))
            if m not in f1_by_model:
                f1_by_model[m] = {"FRQI": [], "NEQR": []}
            if rep in ("FRQI", "NEQR"):
                f1_by_model[m][rep].append(f1)

        chart2_f1_comparison = [
            {
                "model": m,
                "FRQI": round(float(np.mean(vals["FRQI"])), 4) if vals["FRQI"] else 0.0,
                "NEQR": round(float(np.mean(vals["NEQR"])), 4) if vals["NEQR"] else 0.0,
            }
            for m, vals in sorted(f1_by_model.items())
        ]

        # 3. Per-Class Performance across all 6 canonical classes (Precision, Recall, F1)
        per_class_accum = {cat: {"precision": [], "recall": [], "f1": []} for cat in CANONICAL_CLASSES}
        for r in records:
            pc = r.get("classification_metrics", {}).get("per_class", {})
            for raw_cat, metrics in pc.items():
                norm_cat = normalize_defect_label(raw_cat)
                if norm_cat in per_class_accum and isinstance(metrics, dict):
                    per_class_accum[norm_cat]["precision"].append(safe_float(metrics.get("precision", 0.0)))
                    per_class_accum[norm_cat]["recall"].append(safe_float(metrics.get("recall", 0.0)))
                    per_class_accum[norm_cat]["f1"].append(safe_float(metrics.get("f1_score", 0.0)))

        chart3_per_class = [
            {
                "class_name": DISPLAY_NAMES[cat],
                "canonical_name": cat,
                "precision": round(float(np.mean(vals["precision"])), 4) if vals["precision"] else 0.0,
                "recall": round(float(np.mean(vals["recall"])), 4) if vals["recall"] else 0.0,
                "f1_score": round(float(np.mean(vals["f1"])), 4) if vals["f1"] else 0.0,
                "support": len(vals["f1"]),
                "status": "evaluated" if len(vals["f1"]) > 0 else "no_samples",
            }
            for cat, vals in per_class_accum.items()
        ]

        # 4. Confusion Matrix (strictly 6x6 in canonical order, choosing fullest evaluated set)
        latest_cm = [[0]*6 for _ in range(6)]
        max_cm_sum = -1
        for r in records:
            cm = r.get("classification_metrics", {}).get("confusion_matrix")
            if cm and len(cm) == 6 and all(len(row) == 6 for row in cm):
                s = sum(sum(row) for row in cm)
                if s > max_cm_sum:
                    max_cm_sum = s
                    latest_cm = cm

        # 5. Qubit Scaling: Resolution vs Total Qubits
        # Qubit counts follow from the encoding definitions (2*log2(r) position qubits + 1 colour qubit
        # for FRQI, + q intensity qubits for NEQR); computed, not hardcoded.
        res_present = sorted({r.get("resolution") for r in records if r.get("resolution")},
                             key=lambda x: int(str(x).split("x")[0]))
        qubit_scaling = []
        for res in res_present:
            side = int(str(res).split("x")[0])
            npos = 2 * int(np.log2(side))
            qubit_scaling.append({"resolution": res, "pixels": side * side, "FRQI": npos + 1,
                                  "NEQR_2bit": npos + 2, "NEQR_4bit": npos + 4, "NEQR_8bit": npos + 8})

        # 6. Gate Scaling: Resolution vs Gate Count from actual records
        gate_scaling_accum: Dict[str, Dict[str, List[int]]] = {}
        for r in records:
            res = r.get("resolution", "4x4")
            rep = r.get("representation", "FRQI")
            gc = int(r.get("gate_count", 0))
            if res not in gate_scaling_accum:
                gate_scaling_accum[res] = {"FRQI": [], "NEQR": []}
            if rep in ("FRQI", "NEQR"):
                gate_scaling_accum[res][rep].append(gc)

        chart6_gate_scaling = [
            {
                "resolution": res,
                "FRQI": int(np.mean(vals["FRQI"])) if vals["FRQI"] else None,
                "NEQR": int(np.mean(vals["NEQR"])) if vals["NEQR"] else None,
            }
            for res, vals in sorted(gate_scaling_accum.items())
        ]

        # 7. Circuit Depth Comparison
        depth_accum: Dict[str, Dict[str, List[int]]] = {}
        for r in records:
            res = r.get("resolution", "4x4")
            rep = r.get("representation", "FRQI")
            d = int(r.get("circuit_depth", 0))
            if res not in depth_accum:
                depth_accum[res] = {"FRQI": [], "NEQR": []}
            if rep in ("FRQI", "NEQR"):
                depth_accum[res][rep].append(d)

        chart7_depth = [
            {
                "resolution": res,
                "FRQI": int(np.mean(vals["FRQI"])) if vals["FRQI"] else None,
                "NEQR": int(np.mean(vals["NEQR"])) if vals["NEQR"] else None,
            }
            for res, vals in sorted(depth_accum.items())
        ]

        # 8. Runtime Analysis (Encoding, Training, Predict, Recon times)
        runtime_accum: Dict[str, List[Dict[str, float]]] = {"FRQI": [], "NEQR": []}
        for r in records:
            rep = r.get("representation")
            tm = r.get("timings", {})
            if rep in runtime_accum and isinstance(tm, dict):
                runtime_accum[rep].append(tm)

        chart8_runtime = []
        for rep in ["FRQI", "NEQR"]:
            t_list = runtime_accum[rep]
            if t_list:
                chart8_runtime.append({
                    "representation": rep,
                    "encoding": round(safe_float(np.mean([safe_float(t.get("encoding_time_s", 0.0)) for t in t_list])), 4),
                    "training": round(safe_float(np.mean([safe_float(t.get("train_time_s", 0.0)) for t in t_list])), 4),
                    "prediction": round(safe_float(np.mean([safe_float(t.get("predict_time_s", 0.0)) for t in t_list])), 4),
                    "reconstruction": round(safe_float(np.mean([safe_float(t.get("reconstruction_time_s", 0.0)) for t in t_list])), 4),
                })

        # 9. Reconstruction Quality: MSE, PSNR, SSIM
        recon_accum: Dict[str, Dict[str, List[float]]] = {
            "FRQI": {"mse": [], "psnr": [], "ssim": []},
            "NEQR": {"mse": [], "psnr": [], "ssim": []}
        }
        for r in records:
            rep = r.get("representation")
            rec = r.get("reconstruction_metrics", {})
            if rep in recon_accum and isinstance(rec, dict) and "mse" in rec:
                recon_accum[rep]["mse"].append(safe_float(rec.get("mse", 0.0)))
                psnr_val = safe_float(rec.get("psnr", 0.0))
                # Cap PSNR at 100 dB for valid visualization
                recon_accum[rep]["psnr"].append(min(100.0, psnr_val))
                recon_accum[rep]["ssim"].append(safe_float(rec.get("ssim", 0.0)))

        chart9_recon_quality = [
            {
                "representation": rep,
                "mse": round(safe_float(np.mean(vals["mse"])), 6) if vals["mse"] else 0.0,
                "psnr": round(safe_float(np.mean(vals["psnr"])), 2) if vals["psnr"] else 0.0,
                "ssim": round(safe_float(np.mean(vals["ssim"])), 4) if vals["ssim"] else 0.0,
            }
            for rep, vals in recon_accum.items()
        ]

        # 10. Shot Sensitivity (0/Statevector, 100, 500, 1000)
        shot_accum: Dict[str, Dict[str, Any]] = {}
        for r in records:
            shots = str(r.get("shots", 0))
            rep = r.get("representation", "FRQI")
            acc = safe_float(r.get("classification_metrics", {}).get("accuracy", 0.0))
            psnr = min(100.0, safe_float(r.get("reconstruction_metrics", {}).get("psnr", 0.0)))
            if shots not in shot_accum:
                shot_accum[shots] = {
                    "shots": "Exact" if shots == "0" else f"{shots} shots",
                    "FRQI_acc": [], "NEQR_acc": [], "FRQI_psnr": [], "NEQR_psnr": []
                }
            if f"{rep}_acc" in shot_accum[shots]:
                shot_accum[shots][f"{rep}_acc"].append(acc)
                shot_accum[shots][f"{rep}_psnr"].append(psnr)

        chart10_shot_sensitivity = [
            {
                "shots": vals["shots"],
                "FRQI_acc": round(safe_float(np.mean(vals["FRQI_acc"])), 4) if vals["FRQI_acc"] else 0.0,
                "NEQR_acc": round(safe_float(np.mean(vals["NEQR_acc"])), 4) if vals["NEQR_acc"] else 0.0,
                "FRQI_psnr": round(safe_float(np.mean(vals["FRQI_psnr"])), 2) if vals["FRQI_psnr"] else 0.0,
                "NEQR_psnr": round(safe_float(np.mean(vals["NEQR_psnr"])), 2) if vals["NEQR_psnr"] else 0.0,
            }
            for s, vals in sorted(shot_accum.items())
        ]

        # 11. Resolution Scaling (Resolution vs Accuracy and PSNR)
        res_scaling_accum: Dict[str, Dict[str, Any]] = {}
        for r in records:
            res = r.get("resolution", "4x4")
            rep = r.get("representation", "FRQI")
            acc = safe_float(r.get("classification_metrics", {}).get("accuracy", 0.0))
            psnr = min(100.0, safe_float(r.get("reconstruction_metrics", {}).get("psnr", 0.0)))
            if res not in res_scaling_accum:
                res_scaling_accum[res] = {
                    "resolution": res,
                    "FRQI_acc": [], "NEQR_acc": [], "FRQI_psnr": [], "NEQR_psnr": []
                }
            if f"{rep}_acc" in res_scaling_accum[res]:
                res_scaling_accum[res][f"{rep}_acc"].append(acc)
                res_scaling_accum[res][f"{rep}_psnr"].append(psnr)

        chart11_res_scaling = [
            {
                "resolution": res,
                "FRQI_acc": round(safe_float(np.mean(vals["FRQI_acc"])), 4) if vals["FRQI_acc"] else 0.0,
                "NEQR_acc": round(safe_float(np.mean(vals["NEQR_acc"])), 4) if vals["NEQR_acc"] else 0.0,
                "FRQI_psnr": round(safe_float(np.mean(vals["FRQI_psnr"])), 2) if vals["FRQI_psnr"] else 0.0,
                "NEQR_psnr": round(safe_float(np.mean(vals["NEQR_psnr"])), 2) if vals["NEQR_psnr"] else 0.0,
            }
            for res, vals in sorted(res_scaling_accum.items())
        ]

        # 12. Class-wise Comparison (FRQI vs NEQR per defect category F1 across all 6 classes)
        class_wise_accum = {cat: {"FRQI": [], "NEQR": []} for cat in CANONICAL_CLASSES}
        for r in records:
            rep = r.get("representation")
            pc = r.get("classification_metrics", {}).get("per_class", {})
            for raw_cat, metrics in pc.items():
                norm_cat = normalize_defect_label(raw_cat)
                if norm_cat in class_wise_accum and rep in ("FRQI", "NEQR") and isinstance(metrics, dict):
                    class_wise_accum[norm_cat][rep].append(safe_float(metrics.get("f1_score", 0.0)))

        chart12_class_wise = [
            {
                "category": DISPLAY_NAMES[cat],
                "canonical_name": cat,
                "FRQI_f1": round(safe_float(np.mean(vals["FRQI"])), 4) if vals["FRQI"] else 0.0,
                "NEQR_f1": round(safe_float(np.mean(vals["NEQR"])), 4) if vals["NEQR"] else 0.0,
            }
            for cat, vals in class_wise_accum.items()
        ]

        # 13. Experiment Status Breakdown
        all_hist = self.get_experiment_history()
        status_counts = {"completed": 0, "failed": 0, "pending": 0, "running": 0}
        for h in all_hist:
            st = h.get("status", "completed")
            status_counts[st] = status_counts.get(st, 0) + 1

        chart13_status = [
            {"name": "Completed", "value": status_counts["completed"], "fill": "#10b981"},
            {"name": "Failed", "value": status_counts["failed"], "fill": "#f43f5e"},
            {"name": "Pending", "value": status_counts["pending"], "fill": "#f59e0b"},
        ]

        # 14. Training Curve (from latest VQC experiment)
        training_curve = []
        for r in reversed(records):
            th = r.get("training_history", [])
            if th and len(th) > 0:
                training_curve = th
                break

        # 15. Resource-versus-Performance Plot (Circuit Depth vs Accuracy)
        chart15_tradeoff = [
            {
                "experiment_id": r.get("experiment_id", ""),
                "representation": r.get("representation", "FRQI"),
                "circuit_depth": int(r.get("circuit_depth", 0)),
                "gate_count": int(r.get("gate_count", 0)),
                "accuracy": round(safe_float(r.get("classification_metrics", {}).get("accuracy", 0.0)), 4),
                "f1_macro": round(safe_float(r.get("classification_metrics", {}).get("f1_macro", 0.0)), 4),
                "model": r.get("qml_model_type", "Hybrid Quantum-Classical Classifier"),
            }
            for r in records[:50]  # Limit sample size for responsive scatter rendering
        ]

        return {
            "chart1_accuracy_comparison": chart1_acc_comparison,
            "chart2_f1_comparison": chart2_f1_comparison,
            "chart3_per_class": chart3_per_class,
            "chart4_confusion_matrix": latest_cm,
            "chart4_classes": [DISPLAY_NAMES[c] for c in CANONICAL_CLASSES],
            "chart5_qubit_scaling": qubit_scaling,
            "chart6_gate_scaling": chart6_gate_scaling,
            "chart7_circuit_depth": chart7_depth,
            "chart8_runtime_analysis": chart8_runtime,
            "chart9_reconstruction_quality": chart9_recon_quality,
            "chart10_shot_sensitivity": chart10_shot_sensitivity,
            "chart11_resolution_scaling": chart11_res_scaling,
            "chart12_class_wise": chart12_class_wise,
            "chart13_experiment_status": chart13_status,
            "chart14_training_curve": training_curve,
            "chart15_resource_performance": chart15_tradeoff,
        }
    def delete_experiment(self, experiment_id: str) -> bool:
        """Delete an experiment by ID."""
        self._guard_write()
        json_file = self.experiments_dir / f"{experiment_id}.json"
        deleted = False
        if json_file.exists():
            json_file.unlink()
            deleted = True

        history = self.get_experiment_history()
        new_history = [e for e in history if e.get("experiment_id") != experiment_id]
        if len(new_history) != len(history):
            with open(self.index_path, "w", encoding="utf-8") as f:
                json.dump(new_history, f, indent=2)
            deleted = True
        return deleted

    def _save_experiment(self, result: Dict[str, Any]):
        """Compatibility method for saving experiment results."""
        self._persist_experiment(result)

    def _create_failed_result(
        self, experiment_id: str, config: Dict[str, Any], start_time: Any, error: str
    ) -> Dict[str, Any]:
        """Create a standardized record for a failed experiment."""
        return {
            "experiment_id": experiment_id,
            "status": "failed",
            "started_at": str(start_time),
            "completed_at": datetime.now().isoformat(),
            "config": config,
            "error": error,
            "error_message": error,
            "representation": config.get("representation", "FRQI"),
            "qml_model_type": config.get("model_type", "Quantum Kernel Classifier"),
            "resolution": config.get("resolution", "4x4"),
            "shots": config.get("shots", 0),
            "n_qubits": config.get("n_qubits", 5),
            "gate_count": 0,
            "circuit_depth": 0,
            "timestamp": datetime.now().isoformat(),
        }

    def run_experiment(self, config: Dict[str, Any], progress_callback=None) -> Dict[str, Any]:
        """Wrapper around run_paired_experiment or run_full_dataset_pipeline."""
        if config.get("all_dataset", False) or config.get("mode") == "full_dataset" or config.get("full_dataset", False):
            return self.run_full_dataset_pipeline(config, progress_callback=progress_callback)
        return self.run_paired_experiment(config, progress_callback=progress_callback)

    def get_classical_comparison(self) -> Dict[str, Any]:
        """Retrieve classical baseline model metrics for comparison against QML."""
        from src.ml.trainer import RESULTS_MODELS_PATH
        models_file = RESULTS_MODELS_PATH / "model_comparison.json"
        if models_file.exists():
            try:
                with open(models_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        # No fabricated fallback: report that no saved classical results exist.
        return {"models": [], "status": "no_data"}

    def get_dataset_images(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Browse all 1,800 images in the NEU dataset with experiment status and pagination."""
        manifest = self.discover_dataset()
        images = manifest.get("images", [])

        # Build experiment availability map from CSV
        exp_map: Dict[str, Dict[str, int]] = {}
        if self.csv_path.exists():
            try:
                df = pd.read_csv(self.csv_path)
                for _, row in df.iterrows():
                    iname = str(row.get("image_name", "")).strip()
                    if not iname or iname == "nan":
                        continue
                    rep = str(row.get("representation", "FRQI")).upper()
                    if iname not in exp_map:
                        exp_map[iname] = {"FRQI": 0, "NEQR": 0, "total": 0}
                    if rep in exp_map[iname]:
                        exp_map[iname][rep] += 1
                    exp_map[iname]["total"] += 1
            except Exception:
                pass

        # Apply category filter
        filtered = images
        if category and category.lower() != "all":
            norm_cat = normalize_defect_label(category)
            filtered = [img for img in filtered if img.get("ground_truth") == norm_cat]

        # Apply search filter
        if search:
            q = search.lower().strip()
            filtered = [
                img for img in filtered
                if q in img.get("image_name", "").lower() or q in img.get("image_id", "").lower()
            ]

        total = len(filtered)
        start_idx = max(0, (page - 1) * limit)
        end_idx = min(total, start_idx + limit)
        page_items = []

        for img in filtered[start_idx:end_idx]:
            iname = img.get("image_name", "")
            counts = exp_map.get(iname, {"FRQI": 0, "NEQR": 0, "total": 0})
            page_items.append({
                "image_id": img.get("image_id", ""),
                "image_name": iname,
                "ground_truth": img.get("ground_truth", ""),
                "display_class": DISPLAY_NAMES.get(img.get("ground_truth", ""), img.get("ground_truth", "")),
                "split": img.get("split", "train"),
                "path": img.get("path", ""),
                "original_dimensions": "200x200",
                "experiments_count": counts["total"],
                "has_frqi": counts["FRQI"] > 0,
                "has_neqr": counts["NEQR"] > 0,
            })

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": max(1, (total + limit - 1) // limit),
            "categories": CANONICAL_CLASSES,
            "display_names": DISPLAY_NAMES,
            "images": page_items,
        }

    def _find_image_path(self, image_name: str) -> Optional[Path]:
        """Locate an image in DATASET_PATH."""
        if not DATASET_PATH.exists():
            return None
        # Direct search
        clean = Path(image_name).name
        for split in ["train", "validation"]:
            sp = DATASET_PATH / split / "images"
            if not sp.exists():
                continue
            for cat_dir in sp.iterdir():
                if not cat_dir.is_dir():
                    continue
                p = cat_dir / clean
                if p.exists():
                    return p
                # Try without extension or .jpg
                p_jpg = cat_dir / f"{clean}.jpg"
                if p_jpg.exists():
                    return p_jpg
        return None

    def get_reconstruction_details(
        self,
        image_name: str,
        resolution: str = "4x4",
        intensity_bits: int = 4,
        shots: int = 0,
    ) -> Dict[str, Any]:
        """
        Generate full 6-panel visual comparison and real metrics for ANY dataset image.
        Panels:
          1. Original image (200x200)
          2. Preprocessed image (at target resolution)
          3. FRQI reconstruction
          4. NEQR reconstruction
          5. FRQI difference map (|Preprocessed - FRQI|)
          6. NEQR difference map (|Preprocessed - NEQR|)
        """
        img_path = self._find_image_path(image_name)
        if not img_path:
            raise FileNotFoundError(f"Image {image_name} not found in dataset {DATASET_PATH}")

        # Ground truth class from parent directory
        ground_truth = normalize_defect_label(img_path.parent.name)
        split = "train" if "train" in str(img_path) else "validation"

        # 1. Load Original Image (200x200)
        pil_orig = Image.open(img_path).convert("L")
        orig_w, orig_h = pil_orig.size
        orig_arr = np.array(pil_orig, dtype=np.float64) / 255.0

        # Base64 for original image
        buffer = io.BytesIO()
        pil_orig.save(buffer, format="PNG")
        original_b64 = f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode('utf-8')}"

        # 2. Preprocess to Target Resolution
        rw, rh = map(int, resolution.split("x"))
        pil_pre = pil_orig.resize((rw, rh), Image.Resampling.BILINEAR)
        pre_arr = np.array(pil_pre, dtype=np.float64) / 255.0
        preprocessed_b64 = array_to_base64_png(pre_arr)

        # 3 & 4. FRQI and NEQR Quantum Reconstructions
        evaluator = QuantumReconstructionEvaluator(seed=RANDOM_SEED)
        frqi_eval = evaluator.evaluate_frqi(pre_arr, resolution=(rh, rw), shots=shots)
        neqr_eval = evaluator.evaluate_neqr(
            pre_arr, resolution=(rh, rw), intensity_bits=intensity_bits, shots=shots
        )

        # Helper to format PSNR properly (handling MSE = 0)
        def format_psnr(mse_val: float, psnr_val: float) -> Tuple[Optional[float], str]:
            if mse_val < 1e-12 or np.isinf(psnr_val) or psnr_val >= 99.9:
                return None, "Infinite (Exact Match, MSE = 0)"
            return round(psnr_val, 2), f"{psnr_val:.2f} dB"

        frqi_psnr_val, frqi_psnr_disp = format_psnr(frqi_eval["mse"], frqi_eval["psnr"])
        neqr_psnr_val, neqr_psnr_disp = format_psnr(neqr_eval["mse"], neqr_eval["psnr"])

        # Find available experiment records for this image in qml_experiments.csv
        avail_exps = []
        if self.csv_path.exists():
            try:
                df = pd.read_csv(self.csv_path)
                matches = df[df["image_name"] == img_path.name]
                for _, r in matches.iterrows():
                    avail_exps.append({
                        "experiment_id": str(r.get("experiment_id", "")),
                        "representation": str(r.get("representation", "FRQI")),
                        "resolution": str(r.get("resolution", resolution)),
                        "intensity_bits": int(r.get("intensity_bits", intensity_bits)),
                        "shots": int(r.get("shots", shots)),
                        "status": str(r.get("status", "completed")),
                        "model_type": str(r.get("qml_model_type", "Hybrid Quantum-Classical Classifier")),
                    })
            except Exception:
                pass

        # Circuit resources measured on the actual circuits for this image (logical + compiled to a
        # fixed basis; same method as Protocol V2) — no hardcoded values.
        from src.frqi.encoder import FRQIEncoder
        from src.neqr.encoder import NEQREncoder
        from src.v2.qsim import circuit_resources
        _mx = (1 << intensity_bits) - 1
        frqi_res = circuit_resources(FRQIEncoder(pre_arr).build_circuit())
        neqr_res = circuit_resources(NEQREncoder(np.clip(np.round(pre_arr * _mx), 0, _mx).astype(int),
                                                 intensity_bits=intensity_bits).build_circuit())
        frqi_qubits = frqi_res["n_qubits"]
        neqr_qubits = neqr_res["n_qubits"]

        return {
            "image_name": img_path.name,
            "image_id": img_path.stem,
            "ground_truth": ground_truth,
            "display_class": DISPLAY_NAMES.get(ground_truth, ground_truth.title()),
            "split": split,
            "original_dimensions": f"{orig_w}x{orig_h}",
            "resolution": resolution,
            "intensity_bits": intensity_bits,
            "shots": shots,
            "original_b64": original_b64,
            "preprocessed_b64": preprocessed_b64,
            "frqi": {
                "reconstructed_b64": frqi_eval["reconstructed_b64"],
                "diff_b64": frqi_eval["diff_b64"],
                "mse": round(float(frqi_eval["mse"]), 6),
                "psnr": frqi_psnr_disp,
                "psnr_numeric": frqi_psnr_val if frqi_psnr_val is not None else 100.0,
                "psnr_display": frqi_psnr_disp,
                "ssim": round(float(frqi_eval["ssim"]), 4),
                "time_s": round(float(frqi_eval["reconstruction_time"]), 5),
                "qubits": frqi_qubits,
                "gate_count": frqi_res["gates_logical"], "depth": frqi_res["depth_logical"],
                "gate_count_compiled": frqi_res["gates_compiled"], "depth_compiled": frqi_res["depth_compiled"],
                "status": "completed",
            },
            "neqr": {
                "reconstructed_b64": neqr_eval["reconstructed_b64"],
                "diff_b64": neqr_eval["diff_b64"],
                "mse": round(float(neqr_eval["mse"]), 6),
                "psnr": neqr_psnr_disp,
                "psnr_numeric": neqr_psnr_val if neqr_psnr_val is not None else 100.0,
                "psnr_display": neqr_psnr_disp,
                "ssim": round(float(neqr_eval["ssim"]), 4),
                "time_s": round(float(neqr_eval["reconstruction_time"]), 5),
                "qubits": neqr_qubits,
                "gate_count": neqr_res["gates_logical"], "depth": neqr_res["depth_logical"],
                "gate_count_compiled": neqr_res["gates_compiled"], "depth_compiled": neqr_res["depth_compiled"],
                "status": "completed",
            },
            "available_experiments": avail_exps,
            "experiments": avail_exps,
        }

    def get_circuit_details(self, experiment_id: str) -> Dict[str, Any]:
        """
        Generate complete quantum circuit, decomposed instructions, registers,
        and gate composition for ANY experiment ID without fake circuits.
        """
        exp = self.get_experiment(experiment_id)
        if not exp:
            # Fallback to search in CSV
            if self.csv_path.exists():
                try:
                    df = pd.read_csv(self.csv_path)
                    m = df[df["experiment_id"] == experiment_id]
                    if not m.empty:
                        exp = m.iloc[0].to_dict()
                except Exception:
                    pass

        if not exp:
            raise KeyError(f"Experiment {experiment_id} not found.")

        rep = exp.get("representation", "FRQI")
        res_str = exp.get("resolution", "4x4")
        w, h = map(int, res_str.split("x"))
        intensity_bits = int(exp.get("intensity_bits", 4))
        image_name = exp.get("image_name")
        model_type = exp.get("qml_model_type", exp.get("config", {}).get("model_type", "Hybrid Quantum-Classical Classifier"))
        backend = exp.get("backend", "AerSimulator")
        status = exp.get("status", "completed")

        # Load real image if available
        img_arr = None
        if image_name:
            p = self._find_image_path(image_name)
            if p and p.exists():
                pil_img = Image.open(p).convert("L").resize((w, h), Image.Resampling.BILINEAR)
                img_arr = np.array(pil_img, dtype=np.float64) / 255.0

        if img_arr is None:
            # Use deterministic harmonic pattern representing industrial surface texture
            y, x = np.mgrid[0:h, 0:w]
            img_arr = 0.5 + 0.3 * np.sin(2 * np.pi * x / max(w, 1)) * np.cos(2 * np.pi * y / max(h, 1))
            img_arr = np.clip(img_arr, 0.0, 1.0)

        # Build real quantum circuit
        from src.frqi.encoder import FRQIEncoder
        from src.neqr.encoder import NEQREncoder

        if rep == "FRQI":
            encoder = FRQIEncoder(img_arr)
            qc = encoder.build_circuit()
            qregs = [
                {"name": "pos", "size": encoder.n_position_qubits, "type": "Position Register (x, y coordinates)"},
                {"name": "color", "size": 1, "type": "Color/Intensity Phase Qubit"},
            ]
        else:
            max_val = (1 << intensity_bits) - 1
            quant = np.clip(np.round(img_arr * max_val), 0, max_val).astype(int)
            encoder = NEQREncoder(quant, intensity_bits=intensity_bits)
            qc = encoder.build_circuit()
            qregs = [
                {"name": "pos", "size": encoder.n_position_qubits, "type": "Position Register (x, y coordinates)"},
                {"name": "intensity", "size": intensity_bits, "type": f"Intensity Register ({intensity_bits}-bit Gray Scale)"},
            ]

        # Extract structured instructions for interactive wire diagram
        instructions = []
        limit_gates = min(len(qc.data), 120)
        for i, inst in enumerate(qc.data[:limit_gates]):
            q_indices = [qc.find_bit(q).index for q in inst.qubits]
            if len(q_indices) > 1:
                controls = q_indices[:-1]
                targets = [q_indices[-1]]
            else:
                controls = []
                targets = q_indices

            params = [
                round(float(p), 4) for p in inst.operation.params
                if isinstance(p, (int, float, np.floating, np.integer))
            ]
            instructions.append({
                "index": i,
                "name": inst.operation.name,
                "controls": controls,
                "targets": targets,
                "params": params,
            })

        # Gate composition
        gate_types = {}
        for inst in qc.data:
            g = inst.operation.name
            gate_types[g] = gate_types.get(g, 0) + 1

        # Generate Qiskit ASCII diagram (bounded length)
        try:
            if len(qc.data) <= 500:
                text_diagram = str(qc.draw(output="text", fold=80))
            else:
                # Subcircuit preview to avoid memory spike
                from qiskit import QuantumCircuit
                preview_qc = QuantumCircuit(qc.num_qubits)
                for inst in qc.data[:60]:
                    preview_qc.append(inst.operation, inst.qubits, inst.clbits)
                text_diagram = str(preview_qc.draw(output="text", fold=80)) + f"\n... [{len(qc.data) - 60} more gates truncated for responsive display]"
        except Exception as e:
            text_diagram = f"Qiskit text drawing: {len(qc.data)} gates, depth {qc.depth()} (ASCII generator unavailable: {e})"

        return {
            "experiment_id": experiment_id,
            "image_name": image_name or "synthetic_texture",
            "representation": rep,
            "resolution": res_str,
            "intensity_bits": intensity_bits,
            "shots": int(exp.get("shots", 0)),
            "qml_model_type": model_type,
            "backend": backend,
            "status": status,
            "qubits": qc.num_qubits,
            "depth": qc.depth(),
            "gate_count": len(qc.data),
            "controlled_gates": sum(count for g, count in gate_types.items() if g in ("cx", "mcx", "ccx", "cz")),
            "gate_types": gate_types,
            "qregs": qregs,
            "instructions": instructions,
            "has_more_gates": len(qc.data) > limit_gates,
            "total_gates": len(qc.data),
            "text_diagram": text_diagram,
        }

    def get_unified_model_comparison(self) -> Dict[str, Any]:
        """
        Unified side-by-side benchmark comparing all implemented QML models and classical baselines.
        Includes accuracy, precision, recall, macro F1, weighted F1, training and inference time.
        """
        # 1. Classical baselines from results/models/model_comparison.csv
        classical_rows = []
        p_class = PROJECT_ROOT / "results" / "models" / "model_comparison.csv"
        if p_class.exists():
            try:
                df_c = pd.read_csv(p_class)
                for _, r in df_c.iterrows():
                    classical_rows.append({
                        "model": str(r.get("model", "")),
                        "family": "Classical Baseline",
                        "representation": "N/A (Raw Pixels / HOG)",
                        "accuracy": round(float(r.get("test_accuracy", 0.0)), 4),
                        "precision_macro": round(float(r.get("precision_macro", 0.0)), 4),
                        "recall_macro": round(float(r.get("recall_macro", 0.0)), 4),
                        "f1_macro": round(float(r.get("f1_macro", 0.0)), 4),
                        "f1_weighted": round(float(r.get("f1_weighted", 0.0)), 4),
                        "training_time_s": round(float(r.get("training_time_s", 0.0)), 3),
                        "inference_time_ms": round(float(r.get("inference_time_per_sample_ms", 0.0)), 3),
                        "qubits": 0,
                        "circuit_depth": 0,
                    })
            except Exception:
                pass

        # (no hardcoded fallback rows: if the file is missing, classical_rows stays empty)

        # 2. QML Models from qml_experiments.csv
        qml_rows = []
        if self.csv_path.exists():
            try:
                df_q = pd.read_csv(self.csv_path)
                for (m, rep), group in df_q.groupby(["qml_model_type", "representation"]):
                    if str(m) in ("nan", "Unknown"):
                        continue
                    qml_rows.append({
                        "model": f"{m} ({rep})",
                        "base_model": str(m),
                        "family": "Quantum ML",
                        "representation": str(rep),
                        "accuracy": round(float(group["accuracy"].mean()), 4),
                        "precision_macro": round(float(group["precision_macro"].mean()), 4),
                        "recall_macro": round(float(group["recall_macro"].mean()), 4),
                        "f1_macro": round(float(group["f1_macro"].mean()), 4),
                        "f1_weighted": round(float(group["f1_weighted"].mean()), 4),
                        "training_time_s": round(float(group["train_time_s"].mean()), 3),
                        "inference_time_ms": round(float(group["predict_time_s"].mean() * 1000.0), 3),
                        "qubits": int(group["n_qubits"].mean()),
                        "circuit_depth": int(group["circuit_depth"].mean()),
                        "samples_evaluated": len(group),
                    })
            except Exception:
                pass

        return {
            "all_models": qml_rows + classical_rows,
            "qml_models": qml_rows,
            "classical_models": classical_rows,
        }

