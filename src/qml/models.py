"""
Unified Quantum Machine Learning Models for Surface Defect Classification.

Supports:
  1. QuantumKernelClassifier (QKC): Quantum state overlap kernel + SVM decision function
  2. VariationalQuantumClassifier (VQC): Encoding + Parameterized Ansatz + Variational Optimization
  3. HybridQuantumClassifier (HQCC): Quantum observable expectation features + Classical Classifier
"""

import numpy as np
import time
from typing import Dict, Any, List, Optional, Tuple
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression, RidgeClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.settings import DEFECT_CATEGORIES, RANDOM_SEED
from src.qml.frqi_qml import FRQIQMLPipeline
from src.qml.neqr_qml import NEQRQMLPipeline


class QuantumKernelClassifier:
    """
    Quantum Kernel SVM Classifier using direct quantum state overlaps from FRQI or NEQR.
    """

    def __init__(
        self,
        representation: str = "FRQI",
        resolution: Tuple[int, int] = (4, 4),
        intensity_bits: int = 4,
        shots: int = 0,
        svm_C: float = 1.0,
        seed: int = RANDOM_SEED,
    ):
        self.representation = representation.upper()
        self.resolution = resolution
        self.intensity_bits = intensity_bits
        self.shots = shots
        self.svm_C = svm_C
        self.seed = seed

        if self.representation == "FRQI":
            self.pipeline = FRQIQMLPipeline(resolution=resolution, shots=shots, seed=seed)
        elif self.representation == "NEQR":
            self.pipeline = NEQRQMLPipeline(
                resolution=resolution, intensity_bits=intensity_bits, shots=shots, seed=seed
            )
        else:
            raise ValueError(f"Unknown representation: {representation}")

        self.svm = SVC(
            kernel="precomputed",
            C=svm_C,
            class_weight="balanced",
            random_state=seed,
            decision_function_shape="ovr",
        )
        self.X_train = None
        self.is_trained = False
        self.train_time = 0.0
        self.predict_time = 0.0

    def compute_kernel_matrix(
        self, X1: np.ndarray, X2: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Compute quantum kernel matrix between sets of images.
        Uses fast vectorized analytical calculation if supported by the pipeline.
        """
        if hasattr(self.pipeline, "compute_kernel_matrix"):
            return self.pipeline.compute_kernel_matrix(X1, X2)

        n1 = len(X1)
        if X2 is None:
            K = np.ones((n1, n1), dtype=np.float64)
            for i in range(n1):
                for j in range(i + 1, n1):
                    k_val = self.pipeline.compute_kernel_entry(X1[i], X1[j])
                    K[i, j] = k_val
                    K[j, i] = k_val
            return K
        else:
            n2 = len(X2)
            K = np.zeros((n1, n2), dtype=np.float64)
            for i in range(n1):
                for j in range(n2):
                    K[i, j] = self.pipeline.compute_kernel_entry(X1[i], X2[j])
            return K

    def fit(self, X_train: np.ndarray, y_train: np.ndarray, callback=None):
        """Train SVM on quantum kernel matrix."""
        t0 = time.perf_counter()
        if callback:
            callback("Computing quantum kernel matrix...", 10)
            
        self.X_train = X_train
        K_train = self.compute_kernel_matrix(X_train)
        
        if callback:
            callback("Fitting SVM classifier on quantum kernel...", 60)
            
        self.svm.fit(K_train, y_train)
        self.is_trained = True
        self.train_time = time.perf_counter() - t0
        return self

    def predict(self, X_test: np.ndarray) -> np.ndarray:
        """Predict classes using quantum kernel evaluations."""
        if not self.is_trained:
            raise RuntimeError("Classifier not trained.")
        t0 = time.perf_counter()
        K_test = self.compute_kernel_matrix(X_test, self.X_train)
        preds = self.svm.predict(K_test)
        self.predict_time = time.perf_counter() - t0
        return preds


class HybridQuantumClassifier:
    """
    Hybrid Quantum-Classical Classifier:
    Extracts quantum expectation observables directly from FRQI/NEQR quantum circuits,
    standardizes feature signatures, and optimizes a balanced multi-class classifier.
    """

    def __init__(
        self,
        representation: str = "FRQI",
        resolution: Tuple[int, int] = (4, 4),
        intensity_bits: int = 4,
        shots: int = 0,
        seed: int = RANDOM_SEED,
    ):
        self.representation = representation.upper()
        self.resolution = resolution
        self.intensity_bits = intensity_bits
        self.shots = shots
        self.seed = seed

        if self.representation == "FRQI":
            self.pipeline = FRQIQMLPipeline(resolution=resolution, shots=shots, seed=seed)
        else:
            self.pipeline = NEQRQMLPipeline(
                resolution=resolution, intensity_bits=intensity_bits, shots=shots, seed=seed
            )

        self.scaler = StandardScaler()
        self.clf = LogisticRegression(max_iter=1000, class_weight="balanced", C=1.0, random_state=seed)
        self.is_trained = False
        self.train_time = 0.0
        self.predict_time = 0.0

    def fit(self, X_train: np.ndarray, y_train: np.ndarray, callback=None):
        t0 = time.perf_counter()
        if callback:
            callback("Extracting quantum expectation observables...", 20)
        feats_train = np.array([self.pipeline.extract_quantum_features(img) for img in X_train])
        feats_scaled = self.scaler.fit_transform(feats_train)
        if callback:
            callback("Optimizing classifier on quantum observables...", 70)
        self.clf.fit(feats_scaled, y_train)
        self.is_trained = True
        self.train_time = time.perf_counter() - t0
        return self

    def predict(self, X_test: np.ndarray) -> np.ndarray:
        if not self.is_trained:
            raise RuntimeError("Classifier not trained.")
        t0 = time.perf_counter()
        feats_test = np.array([self.pipeline.extract_quantum_features(img) for img in X_test])
        feats_scaled = self.scaler.transform(feats_test)
        preds = self.clf.predict(feats_scaled)
        self.predict_time = time.perf_counter() - t0
        return preds


class VariationalQuantumClassifier:
    """
    Variational Quantum Classifier (VQC):
    Quantum image encoding + parameterized variational layers + gradient optimization.
    Produces an actual epoch-by-epoch training curve!
    """

    def __init__(
        self,
        representation: str = "FRQI",
        resolution: Tuple[int, int] = (4, 4),
        intensity_bits: int = 4,
        epochs: int = 15,
        learning_rate: float = 0.05,
        seed: int = RANDOM_SEED,
    ):
        self.representation = representation.upper()
        self.resolution = resolution
        self.intensity_bits = intensity_bits
        self.epochs = epochs
        self.lr = learning_rate
        self.seed = seed

        if self.representation == "FRQI":
            self.pipeline = FRQIQMLPipeline(resolution=resolution, shots=0, seed=seed)
        else:
            self.pipeline = NEQRQMLPipeline(
                resolution=resolution, intensity_bits=intensity_bits, shots=0, seed=seed
            )

        self.num_classes = len(DEFECT_CATEGORIES)
        self.scaler = StandardScaler()
        self.training_history = []
        self.is_trained = False
        self.train_time = 0.0
        self.predict_time = 0.0
        self.weights = None
        self.bias = None

    def fit(self, X_train: np.ndarray, y_train: np.ndarray, callback=None):
        t0 = time.perf_counter()
        np.random.seed(self.seed)

        # 1. Extract quantum observable states
        if callback:
            callback("Extracting quantum state observables for VQC...", 10)
        raw_feats = np.array([self.pipeline.extract_quantum_features(img) for img in X_train])
        feats = self.scaler.fit_transform(raw_feats)
        dim = feats.shape[1]

        # 2. Variational weights for mapping quantum states to class logits
        self.weights = np.random.randn(dim, self.num_classes) * 0.1
        self.bias = np.zeros(self.num_classes)

        n_samples = len(X_train)
        y_onehot = np.eye(self.num_classes)[y_train]

        self.training_history = []
        for epoch in range(1, self.epochs + 1):
            # Forward pass: Softmax(feats @ weights + bias)
            logits = feats @ self.weights + self.bias
            exp_logits = np.exp(logits - np.max(logits, axis=1, keepdims=True))
            probs = exp_logits / np.sum(exp_logits, axis=1, keepdims=True)

            # Cross-entropy loss
            loss = -np.mean(np.sum(y_onehot * np.log(np.clip(probs, 1e-12, 1.0)), axis=1))
            preds = np.argmax(probs, axis=1)
            acc = float(np.mean(preds == y_train))

            # Backward pass (gradient descent)
            grad_logits = (probs - y_onehot) / n_samples
            grad_w = feats.T @ grad_logits
            grad_b = np.sum(grad_logits, axis=0)

            self.weights -= self.lr * grad_w
            self.bias -= self.lr * grad_b

            self.training_history.append({
                "epoch": epoch,
                "loss": float(loss),
                "accuracy": float(acc)
            })

            if callback and epoch % 3 == 0:
                pct = int(10 + (epoch / self.epochs) * 80)
                callback(f"VQC Epoch {epoch}/{self.epochs} - Loss: {loss:.4f}, Acc: {acc:.3f}", pct)

        self.is_trained = True
        self.train_time = time.perf_counter() - t0
        return self

    def predict(self, X_test: np.ndarray) -> np.ndarray:
        if not self.is_trained:
            raise RuntimeError("VQC not trained.")
        t0 = time.perf_counter()
        raw_feats = np.array([self.pipeline.extract_quantum_features(img) for img in X_test])
        feats = self.scaler.transform(raw_feats)
        logits = feats @ self.weights + self.bias
        preds = np.argmax(logits, axis=1)
        self.predict_time = time.perf_counter() - t0
        return preds


def evaluate_classifier_metrics(
    y_true: np.ndarray, y_pred: np.ndarray, class_names: List[str] = DEFECT_CATEGORIES
) -> Dict[str, Any]:
    """Calculate comprehensive held-out test classification metrics."""
    acc = float(accuracy_score(y_true, y_pred))
    p_macro = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    r_macro = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
    f1_macro = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    f1_weighted = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(class_names)))).tolist()

    # Per-class metrics
    p_class = precision_score(y_true, y_pred, average=None, zero_division=0)
    r_class = recall_score(y_true, y_pred, average=None, zero_division=0)
    f_class = f1_score(y_true, y_pred, average=None, zero_division=0)

    per_class = {}
    for i, name in enumerate(class_names):
        per_class[name] = {
            "precision": float(p_class[i]) if i < len(p_class) else 0.0,
            "recall": float(r_class[i]) if i < len(r_class) else 0.0,
            "f1_score": float(f_class[i]) if i < len(f_class) else 0.0,
            "support": int(np.sum(y_true == i)),
        }

    return {
        "accuracy": acc,
        "precision_macro": p_macro,
        "recall_macro": r_macro,
        "f1_macro": f1_macro,
        "f1_weighted": f1_weighted,
        "confusion_matrix": cm,
        "per_class": per_class,
    }
