"""
Quantum Kernel SVM Classifier for NEU Surface Defect Classification.

This is a hybrid quantum-classical classifier:
  - QUANTUM: Feature encoding via ZZFeatureMap + kernel computation via statevector overlap
  - CLASSICAL: SVM decision function with precomputed quantum kernel matrix

The quantum kernel captures feature-space similarities in a Hilbert space
that may be exponentially large. However, this does NOT constitute a proof
of quantum advantage — it is a simulation on a classical computer.

Multiclass strategy: scikit-learn SVC handles 6-class classification via
one-vs-one (OVO) internally when using a precomputed kernel.
"""

import numpy as np
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from sklearn.svm import SVC
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix
)
import joblib

from .quantum_kernel import QuantumKernelComputer
from .feature_extractor import QMLFeatureExtractor

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import DEFECT_CATEGORIES, RANDOM_SEED


class QuantumKernelClassifier:
    """
    Quantum Kernel SVM classifier for six-class surface defect detection.

    Pipeline:
      1. Feature extraction: Image → Flatten → Scale → PCA → [0, π]
      2. Quantum kernel: ZZFeatureMap → statevector overlap → kernel matrix
      3. Classification: SVM with precomputed kernel → 6-class prediction

    This is explicitly a hybrid quantum-classical approach.
    """

    CLASS_NAMES = DEFECT_CATEGORIES

    def __init__(
        self,
        n_qubits: int = 8,
        feature_map_reps: int = 2,
        svm_C: float = 1.0,
        random_seed: int = RANDOM_SEED,
        feature_size: int = 64,
    ):
        """
        Args:
            n_qubits: Number of qubits (= PCA feature dimension)
            feature_map_reps: Repetitions in ZZFeatureMap
            svm_C: SVM regularization parameter
            random_seed: For reproducibility
            feature_size: Image resize dimension
        """
        self.n_qubits = n_qubits
        self.feature_map_reps = feature_map_reps
        self.svm_C = svm_C
        self.random_seed = random_seed
        self.feature_size = feature_size

        self.feature_extractor = QMLFeatureExtractor(
            n_features=n_qubits,
            feature_size=feature_size,
            random_seed=random_seed,
        )
        self.kernel_computer = QuantumKernelComputer(
            n_qubits=n_qubits,
            reps=feature_map_reps,
            seed=random_seed,
        )
        self.svm = SVC(
            kernel="precomputed",
            C=svm_C,
            random_state=random_seed,
            decision_function_shape="ovr",
        )

        self._is_trained = False
        self._X_train = None  # Needed for test kernel computation
        self._train_kernel_matrix = None
        self._train_kernel_stats = None

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """
        Train the quantum kernel SVM classifier.

        Steps:
          1. Compute training kernel matrix K_train[i,j] = |⟨Φ(xᵢ)|Φ(xⱼ)⟩|²
          2. Train SVM with precomputed kernel

        Args:
            X_train: Training features (n_train, n_qubits), already in [0, π]
            y_train: Training labels (n_train,)
            progress_callback: Optional callable(current, total) for kernel progress

        Returns:
            Training statistics dictionary
        """
        self._X_train = X_train.copy()

        # Step 1: Compute training kernel matrix
        print(f"  Computing training kernel matrix ({len(X_train)}×{len(X_train)})...")
        kernel_start = time.perf_counter()
        self._train_kernel_matrix, self._train_kernel_stats = \
            self.kernel_computer.compute_kernel_matrix(X_train, progress_callback=progress_callback)
        kernel_time = time.perf_counter() - kernel_start

        # Step 2: Train SVM
        print(f"  Training SVM with precomputed quantum kernel...")
        svm_start = time.perf_counter()
        self.svm.fit(self._train_kernel_matrix, y_train)
        svm_time = time.perf_counter() - svm_start

        self._is_trained = True

        # Training predictions
        y_pred_train = self.svm.predict(self._train_kernel_matrix)
        train_acc = float(accuracy_score(y_train, y_pred_train))

        train_stats = {
            "kernel_compute_time_s": kernel_time,
            "svm_train_time_s": svm_time,
            "total_train_time_s": kernel_time + svm_time,
            "train_accuracy": train_acc,
            "kernel_stats": self._train_kernel_stats,
            "n_support_vectors": int(np.sum(self.svm.n_support_)),
            "support_vectors_per_class": self.svm.n_support_.tolist(),
        }

        print(f"    Kernel computation: {kernel_time:.2f}s")
        print(f"    SVM training:       {svm_time:.2f}s")
        print(f"    Train accuracy:     {train_acc:.4f}")
        print(f"    Support vectors:    {np.sum(self.svm.n_support_)}")

        return train_stats

    def predict(
        self,
        X_test: np.ndarray,
        progress_callback=None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Predict labels for test samples.

        Steps:
          1. Compute test kernel matrix K_test[i,j] = |⟨Φ(x_test_i)|Φ(x_train_j)⟩|²
          2. Predict using SVM with precomputed kernel

        Args:
            X_test: Test features (n_test, n_qubits), already in [0, π]
            progress_callback: Optional callable(current, total)

        Returns:
            Tuple of (predictions, prediction_stats)
        """
        if not self._is_trained:
            raise RuntimeError("Classifier not trained. Call train() first.")

        # Compute test kernel matrix
        print(f"  Computing test kernel matrix ({len(X_test)}×{len(self._X_train)})...")
        kernel_start = time.perf_counter()
        test_kernel_matrix, test_kernel_stats = \
            self.kernel_computer.compute_kernel_matrix(
                X_test, self._X_train, progress_callback=progress_callback
            )
        kernel_time = time.perf_counter() - kernel_start

        # Predict
        pred_start = time.perf_counter()
        y_pred = self.svm.predict(test_kernel_matrix)
        svm_pred_time = time.perf_counter() - pred_start

        predict_stats = {
            "kernel_compute_time_s": kernel_time,
            "svm_predict_time_s": svm_pred_time,
            "total_predict_time_s": kernel_time + svm_pred_time,
            "n_test_samples": int(len(X_test)),
            "kernel_stats": test_kernel_stats,
        }

        return y_pred, predict_stats

    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """
        Full evaluation: predict + compute all metrics.

        Args:
            X_test: Test features (n_test, n_qubits)
            y_test: True test labels (n_test,)
            progress_callback: Optional callable

        Returns:
            Complete evaluation results dictionary
        """
        y_pred, predict_stats = self.predict(X_test, progress_callback)

        # Compute metrics
        report = classification_report(
            y_test, y_pred,
            target_names=self.CLASS_NAMES,
            output_dict=True,
            zero_division=0,
        )
        cm = confusion_matrix(y_test, y_pred)

        results = {
            "test_accuracy": float(accuracy_score(y_test, y_pred)),
            "precision_macro": float(precision_score(y_test, y_pred, average="macro", zero_division=0)),
            "recall_macro": float(recall_score(y_test, y_pred, average="macro", zero_division=0)),
            "f1_macro": float(f1_score(y_test, y_pred, average="macro", zero_division=0)),
            "f1_weighted": float(f1_score(y_test, y_pred, average="weighted", zero_division=0)),
            "confusion_matrix": cm.tolist(),
            "per_class": {
                cls: {
                    "precision": float(report[cls]["precision"]),
                    "recall": float(report[cls]["recall"]),
                    "f1": float(report[cls]["f1-score"]),
                    "support": int(report[cls]["support"]),
                }
                for cls in self.CLASS_NAMES
                if cls in report
            },
            "predict_stats": predict_stats,
        }

        print(f"\n  QML Evaluation Results:")
        print(f"    Test accuracy:  {results['test_accuracy']:.4f}")
        print(f"    Macro F1:       {results['f1_macro']:.4f}")
        print(f"    Weighted F1:    {results['f1_weighted']:.4f}")

        return results

    def get_model_config(self) -> Dict[str, Any]:
        """Get the full model configuration."""
        circuit_stats = self.kernel_computer.get_feature_map_stats()
        return {
            "model_type": "Quantum Kernel SVM",
            "model_description": (
                "Hybrid quantum-classical classifier. "
                "Quantum: ZZFeatureMap encodes features into quantum states; "
                "kernel K(x,y) = |⟨Φ(x)|Φ(y)⟩|² computed via statevector overlap. "
                "Classical: SVM decision function with precomputed quantum kernel."
            ),
            "n_qubits": self.n_qubits,
            "feature_map": "ZZFeatureMap",
            "feature_map_reps": self.feature_map_reps,
            "svm_C": self.svm_C,
            "multiclass_strategy": "one-vs-one (SVM internal)",
            "n_classes": len(self.CLASS_NAMES),
            "classes": self.CLASS_NAMES,
            "simulator": "AerSimulator (statevector method, exact)",
            "shot_based": False,
            "random_seed": self.random_seed,
            "feature_size": self.feature_size,
            "circuit_stats": circuit_stats,
        }

    def get_circuit_instructions(self, x: Optional[np.ndarray] = None) -> list:
        """
        Get circuit gate instructions for visualization.

        Args:
            x: Feature vector (if None, uses sample values)

        Returns:
            List of gate instruction dicts
        """
        if x is None:
            x = np.linspace(0, np.pi, self.n_qubits)
        circuit = self.kernel_computer.get_feature_map_circuit(x)

        instructions = []
        for i, instr in enumerate(circuit.data):
            gate_name = instr.operation.name
            qubits = [circuit.find_bit(q).index for q in instr.qubits]
            controls, targets = [], qubits
            if gate_name.startswith('c') and hasattr(instr.operation, 'num_ctrl_qubits'):
                num_ctrl = instr.operation.num_ctrl_qubits
                controls = qubits[:num_ctrl]
                targets = qubits[num_ctrl:]
            params = []
            if hasattr(instr.operation, 'params'):
                for p in instr.operation.params:
                    try:
                        params.append(float(p))
                    except (TypeError, ValueError):
                        pass
            instructions.append({
                "index": i,
                "name": gate_name,
                "controls": controls,
                "targets": targets,
                "qubits": qubits,
                "params": params,
            })
        return instructions

    def get_train_kernel_matrix(self) -> Optional[np.ndarray]:
        """Return the training kernel matrix (for visualization)."""
        return self._train_kernel_matrix

    def save(self, save_dir: Path):
        """Save the trained model and transformers."""
        save_dir.mkdir(parents=True, exist_ok=True)
        self.feature_extractor.save(save_dir)
        if self._is_trained:
            joblib.dump(self.svm, save_dir / "qml_svm.joblib")
            np.save(save_dir / "qml_X_train.npy", self._X_train)
            if self._train_kernel_matrix is not None:
                np.save(save_dir / "qml_train_kernel.npy", self._train_kernel_matrix)
        # Save config
        with open(save_dir / "qml_model_config.json", "w") as f:
            json.dump(self.get_model_config(), f, indent=2, default=str)

    def load(self, save_dir: Path):
        """Load a trained model from disk."""
        self.feature_extractor.load(save_dir)
        self.svm = joblib.load(save_dir / "qml_svm.joblib")
        self._X_train = np.load(save_dir / "qml_X_train.npy")
        kernel_path = save_dir / "qml_train_kernel.npy"
        if kernel_path.exists():
            self._train_kernel_matrix = np.load(kernel_path)
        self._is_trained = True
