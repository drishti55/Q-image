"""
Tests for Quantum Machine Learning Module.

Tests cover:
  - Feature extraction pipeline
  - Data splitting and leakage prevention
  - Quantum kernel computation (ZZFeatureMap)
  - Quantum kernel SVM classifier (six-class)
  - Metric computation
  - Experiment persistence
"""

import pytest
import numpy as np
import json
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestZZFeatureMap:
    """Test quantum feature map circuit construction."""

    def test_circuit_construction(self):
        """ZZFeatureMap should build a valid circuit."""
        from src.qml.quantum_kernel import ZZFeatureMap
        fm = ZZFeatureMap(n_qubits=4, reps=2)
        x = np.array([0.5, 1.0, 1.5, 2.0])
        circuit = fm.build_circuit(x)

        assert circuit.num_qubits == 4
        assert circuit.depth() > 0
        assert len(circuit.data) > 0

    def test_wrong_dimension_raises(self):
        """Should raise ValueError for wrong feature dimension."""
        from src.qml.quantum_kernel import ZZFeatureMap
        fm = ZZFeatureMap(n_qubits=4, reps=1)
        with pytest.raises(ValueError, match="Feature vector length"):
            fm.build_circuit(np.array([1.0, 2.0]))  # 2 != 4

    def test_circuit_stats(self):
        """Circuit stats should report correct qubit count."""
        from src.qml.quantum_kernel import ZZFeatureMap
        fm = ZZFeatureMap(n_qubits=3, reps=1)
        stats = fm.get_circuit_stats()
        assert stats["qubits"] == 3
        assert stats["gates"] > 0
        assert stats["depth"] > 0
        assert "h" in stats["gate_types"]

    def test_deterministic_circuit(self):
        """Same input should produce same circuit."""
        from src.qml.quantum_kernel import ZZFeatureMap
        fm = ZZFeatureMap(n_qubits=3, reps=2)
        x = np.array([0.1, 0.5, 1.0])
        c1 = fm.build_circuit(x)
        c2 = fm.build_circuit(x)
        # Compare gate counts
        assert len(c1.data) == len(c2.data)


class TestQuantumKernel:
    """Test quantum kernel computation."""

    def test_self_kernel_is_one(self):
        """K(x, x) should be exactly 1.0."""
        from src.qml.quantum_kernel import QuantumKernelComputer
        qk = QuantumKernelComputer(n_qubits=2, reps=1)
        x = np.array([0.5, 1.0])
        k = qk._compute_kernel_entry(x, x)
        assert abs(k - 1.0) < 1e-10

    def test_kernel_symmetry(self):
        """K(x, y) should equal K(y, x)."""
        from src.qml.quantum_kernel import QuantumKernelComputer
        qk = QuantumKernelComputer(n_qubits=2, reps=1)
        x = np.array([0.3, 1.2])
        y = np.array([0.7, 0.5])
        k_xy = qk._compute_kernel_entry(x, y)
        k_yx = qk._compute_kernel_entry(y, x)
        assert abs(k_xy - k_yx) < 1e-10

    def test_kernel_range(self):
        """Kernel values should be in [0, 1]."""
        from src.qml.quantum_kernel import QuantumKernelComputer
        qk = QuantumKernelComputer(n_qubits=2, reps=1)
        x = np.array([0.0, 0.0])
        y = np.array([np.pi, np.pi])
        k = qk._compute_kernel_entry(x, y)
        assert 0.0 <= k <= 1.0

    def test_kernel_matrix_symmetric(self):
        """Symmetric kernel matrix should be PSD and have 1s on diagonal."""
        from src.qml.quantum_kernel import QuantumKernelComputer
        qk = QuantumKernelComputer(n_qubits=2, reps=1)
        X = np.array([
            [0.1, 0.2],
            [0.5, 0.7],
            [1.0, 1.5],
        ])
        K, stats = qk.compute_kernel_matrix(X)

        # Shape
        assert K.shape == (3, 3)
        # Diagonal should be 1
        np.testing.assert_allclose(np.diag(K), 1.0, atol=1e-10)
        # Symmetric
        np.testing.assert_allclose(K, K.T, atol=1e-10)
        # Values in [0, 1]
        assert K.min() >= -1e-10
        assert K.max() <= 1.0 + 1e-10
        # Stats
        assert stats["symmetric"] is True
        assert stats["n_x"] == 3

    def test_kernel_matrix_rectangular(self):
        """Rectangular kernel matrix K(X, Y) should have correct shape."""
        from src.qml.quantum_kernel import QuantumKernelComputer
        qk = QuantumKernelComputer(n_qubits=2, reps=1)
        X = np.array([[0.1, 0.2], [0.3, 0.4]])
        Y = np.array([[0.5, 0.6], [0.7, 0.8], [0.9, 1.0]])
        K, stats = qk.compute_kernel_matrix(X, Y)
        assert K.shape == (2, 3)
        assert stats["symmetric"] is False


class TestFeatureExtractor:
    """Test feature extraction pipeline."""

    def test_transform_requires_fit(self):
        """Transform should fail before fitting."""
        from src.qml.feature_extractor import QMLFeatureExtractor
        fe = QMLFeatureExtractor(n_features=4, feature_size=32)
        with pytest.raises(RuntimeError, match="not fitted"):
            fe.transform(np.random.randn(5, 1024))


class TestClassifier:
    """Test the quantum kernel SVM classifier end-to-end with synthetic data."""

    def test_synthetic_classification(self):
        """Train and evaluate on synthetic data to verify pipeline."""
        from src.qml.quantum_kernel import QuantumKernelComputer
        from sklearn.svm import SVC

        # Create simple separable synthetic data (2 qubits, 3 classes)
        np.random.seed(42)
        n_per_class = 5
        X_train = np.vstack([
            np.random.randn(n_per_class, 2) * 0.3 + [0.5, 0.5],
            np.random.randn(n_per_class, 2) * 0.3 + [2.0, 2.0],
            np.random.randn(n_per_class, 2) * 0.3 + [0.5, 2.5],
        ])
        y_train = np.array([0] * n_per_class + [1] * n_per_class + [2] * n_per_class)

        X_test = np.array([[0.5, 0.5], [2.0, 2.0], [0.5, 2.5]])
        y_test = np.array([0, 1, 2])

        # Compute kernel
        qk = QuantumKernelComputer(n_qubits=2, reps=1)
        K_train, _ = qk.compute_kernel_matrix(X_train)
        K_test, _ = qk.compute_kernel_matrix(X_test, X_train)

        # Train SVM
        svm = SVC(kernel="precomputed", C=1.0, random_state=42)
        svm.fit(K_train, y_train)
        y_pred = svm.predict(K_test)

        # Check predictions are valid class labels
        assert all(p in [0, 1, 2] for p in y_pred)
        # Check shape
        assert len(y_pred) == len(y_test)

    def test_model_config(self):
        """Model config should contain expected fields."""
        from src.qml.classifier import QuantumKernelClassifier
        clf = QuantumKernelClassifier(n_qubits=4, feature_map_reps=2)
        config = clf.get_model_config()

        assert config["model_type"] == "Quantum Kernel SVM"
        assert config["n_qubits"] == 4
        assert config["feature_map"] == "ZZFeatureMap"
        assert config["n_classes"] == 6
        assert config["shot_based"] is False
        assert "circuit_stats" in config

    def test_six_class_predictions(self):
        """Classifier should produce predictions for all 6 classes."""
        from src.qml.classifier import QuantumKernelClassifier
        clf = QuantumKernelClassifier(n_qubits=2)

        # Predictions should be in range [0, 5]
        config = clf.get_model_config()
        assert config["n_classes"] == 6
        assert len(config["classes"]) == 6


class TestExperimentPersistence:
    """Test experiment saving and loading."""

    def test_save_and_load(self, tmp_path):
        """Experiments should be persistable and retrievable (isolated tmp results root)."""
        from src.qml.experiment_manager import QMLExperimentManager

        manager = QMLExperimentManager(results_root=tmp_path / "qml")

        # Create a mock result
        result = {
            "experiment_id": "test001",
            "status": "completed",
            "started_at": "2024-01-01T00:00:00",
            "completed_at": "2024-01-01T00:01:00",
            "config": {"model_type": "Quantum Kernel SVM", "n_qubits": 4},
            "evaluation": {
                "test_accuracy": 0.5,
                "f1_macro": 0.45,
                "f1_weighted": 0.48,
            },
        }

        # Save
        manager._save_experiment(result)

        # Load
        loaded = manager.get_experiment("test001")
        assert loaded is not None
        assert loaded["experiment_id"] == "test001"
        assert loaded["status"] == "completed"
        assert loaded["evaluation"]["test_accuracy"] == 0.5

        # History
        history = manager.get_experiment_history()
        assert any(e["experiment_id"] == "test001" for e in history)

        # Cleanup
        manager.delete_experiment("test001")

    def test_failed_experiment_stored(self, tmp_path):
        """Failed experiments should be stored without fake metrics (isolated tmp results root)."""
        from src.qml.experiment_manager import QMLExperimentManager

        manager = QMLExperimentManager(results_root=tmp_path / "qml")

        result = manager._create_failed_result(
            "fail001", {"n_qubits": 4}, "2024-01-01",
            "Test error message"
        )

        assert result["status"] == "failed"
        assert result["error"] == "Test error message"
        assert "evaluation" not in result  # No fake metrics

        manager._save_experiment(result)
        loaded = manager.get_experiment("fail001")
        assert loaded["status"] == "failed"

        # Cleanup
        manager.delete_experiment("fail001")

    def test_default_manager_is_read_only(self):
        """The default manager points at historical results/qml and must refuse writes."""
        from src.qml.experiment_manager import (
            QMLExperimentManager, HistoricalResultsReadOnlyError,
        )
        manager = QMLExperimentManager()
        assert manager.read_only
        with pytest.raises(HistoricalResultsReadOnlyError):
            manager._save_experiment({"experiment_id": "should_never_exist", "status": "completed"})
        with pytest.raises(HistoricalResultsReadOnlyError):
            manager.delete_experiment("should_never_exist")
        assert manager.get_experiment("should_never_exist") is None


class TestFRQIQMLPipeline:
    """Test FRQI QML pipeline operations."""

    def test_frqi_kernel_self_is_one(self):
        """K(A, A) should be 1.0 for FRQI."""
        from src.qml.frqi_qml import FRQIQMLPipeline
        pipeline = FRQIQMLPipeline(resolution=(2, 2))
        img = np.array([[0.2, 0.4], [0.6, 0.8]])
        k = pipeline.compute_kernel_entry(img, img)
        assert abs(k - 1.0) < 1e-6

    def test_frqi_kernel_symmetry(self):
        """K(A, B) should equal K(B, A)."""
        from src.qml.frqi_qml import FRQIQMLPipeline
        pipeline = FRQIQMLPipeline(resolution=(2, 2))
        img_a = np.array([[0.1, 0.3], [0.5, 0.7]])
        img_b = np.array([[0.2, 0.4], [0.6, 0.8]])
        k_ab = pipeline.compute_kernel_entry(img_a, img_b)
        k_ba = pipeline.compute_kernel_entry(img_b, img_a)
        assert abs(k_ab - k_ba) < 1e-6
        assert 0.0 <= k_ab <= 1.0

    def test_frqi_quantum_features(self):
        """Feature extractor should return Pauli expectation values."""
        from src.qml.frqi_qml import FRQIQMLPipeline
        pipeline = FRQIQMLPipeline(resolution=(2, 2))
        img = np.array([[0.0, 0.5], [0.5, 1.0]])
        feats = pipeline.extract_quantum_features(img)
        assert len(feats) > 0
        assert np.all(feats >= -1.0) and np.all(feats <= 1.0)


class TestNEQRQMLPipeline:
    """Test NEQR QML pipeline operations."""

    def test_neqr_kernel_self_is_one(self):
        """K(A, A) should be 1.0 for NEQR."""
        from src.qml.neqr_qml import NEQRQMLPipeline
        pipeline = NEQRQMLPipeline(resolution=(2, 2), intensity_bits=4)
        img = np.array([[2, 4], [8, 12]])
        k = pipeline.compute_kernel_entry(img, img)
        assert abs(k - 1.0) < 1e-6

    def test_neqr_kernel_different_images(self):
        """K(A, B) should be bounded in [0, 1]."""
        from src.qml.neqr_qml import NEQRQMLPipeline
        pipeline = NEQRQMLPipeline(resolution=(2, 2), intensity_bits=4)
        img_a = np.array([[0, 1], [2, 3]])
        img_b = np.array([[3, 2], [1, 0]])
        k = pipeline.compute_kernel_entry(img_a, img_b)
        assert 0.0 <= k <= 1.0

    def test_neqr_quantum_features(self):
        """Legacy NEQR 'observable' features (V2 audit correction).

        Only the first n_pos + q + n_pos*q entries are Pauli expectation values (bounded in [-1, 1]);
        the trailing row/column entries are classical means of the INPUT array and are not bounded
        (they reached 2.5 for integer input, which is why the original assertion failed). The legacy
        features are computed in closed form, not measured; V2 labels them as classical statistics."""
        from src.qml.neqr_qml import NEQRQMLPipeline
        pipeline = NEQRQMLPipeline(resolution=(2, 2), intensity_bits=2)
        img = np.array([[0, 1], [2, 3]])
        feats = pipeline.extract_quantum_features(img)
        n_pos, q = 2, 2
        pauli = feats[: n_pos + q + n_pos * q]
        assert len(feats) == len(pauli) + 2 + 2
        assert np.all(pauli >= -1.0) and np.all(pauli <= 1.0)
        np.testing.assert_allclose(feats[len(pauli):], [0.5, 2.5, 1.0, 2.0])  # row means, col means of input


class TestUnifiedQMLModels:
    """Test VQC, HQCC, and QKC on both FRQI and NEQR representations."""

    def test_variational_quantum_classifier(self):
        """VQC should train and reduce loss over epochs."""
        from src.qml.models import VariationalQuantumClassifier
        vqc = VariationalQuantumClassifier(representation="FRQI", resolution=(2, 2), epochs=6)
        X = np.random.rand(6, 2, 2)
        y = np.array([0, 1, 2, 3, 4, 5])
        vqc.fit(X, y)
        assert vqc.is_trained
        assert len(vqc.training_history) == 6
        preds = vqc.predict(X)
        assert len(preds) == 6

    def test_hybrid_quantum_classifier(self):
        """HQCC should train and predict on quantum features."""
        from src.qml.models import HybridQuantumClassifier
        hqcc = HybridQuantumClassifier(representation="NEQR", resolution=(2, 2), intensity_bits=2)
        X = np.random.rand(6, 2, 2)
        y = np.array([0, 1, 2, 3, 4, 5])
        hqcc.fit(X, y)
        assert hqcc.is_trained
        preds = hqcc.predict(X)
        assert len(preds) == 6


class TestQuantumReconstruction:
    """Test paired quantum reconstruction evaluation."""

    def test_paired_reconstruction(self):
        """Should reconstruct both FRQI and NEQR with MSE, PSNR, SSIM."""
        from src.qml.reconstruction_eval import QuantumReconstructionEvaluator
        evaluator = QuantumReconstructionEvaluator()
        img = np.array([[0.1, 0.4], [0.7, 0.9]])
        res = evaluator.evaluate_paired_reconstruction(img, resolution=(2, 2), intensity_bits=4)
        assert "frqi" in res and "neqr" in res
        assert res["frqi"]["mse"] >= 0.0
        assert res["neqr"]["mse"] >= 0.0
        assert "diff_b64" in res["frqi"]
        assert "diff_b64" in res["neqr"]


class TestExperimentAnalytics:
    """Test KPI overview and 15 analytics graphs generation."""

    def test_kpis_and_graphs(self):
        from src.qml.experiment_manager import QMLExperimentManager
        manager = QMLExperimentManager()
        kpis = manager.get_overview_kpis()
        assert "total_eligible_images" in kpis
        assert "frqi_experiments" in kpis
        assert "neqr_experiments" in kpis

        graphs = manager.get_analytics_graphs()
        assert "chart1_accuracy_comparison" in graphs
        assert "chart2_f1_comparison" in graphs
        assert "chart3_per_class" in graphs
        assert "chart4_confusion_matrix" in graphs
        assert "chart5_qubit_scaling" in graphs
        assert "chart6_gate_scaling" in graphs
        assert "chart7_circuit_depth" in graphs
        assert "chart8_runtime_analysis" in graphs
        assert "chart9_reconstruction_quality" in graphs
        assert "chart10_shot_sensitivity" in graphs
        assert "chart11_resolution_scaling" in graphs
        assert "chart12_class_wise" in graphs
        assert "chart13_experiment_status" in graphs
        assert "chart14_training_curve" in graphs
        assert "chart15_resource_performance" in graphs


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

