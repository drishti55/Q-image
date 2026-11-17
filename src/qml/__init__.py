"""
Quantum Machine Learning (QML) Module for Q-ImageLab.

Provides comprehensive quantum machine learning pipelines for NEU surface defect classification
using BOTH FRQI and NEQR quantum image encodings:
  - Pipeline A: FRQI Encoding -> Quantum Overlap Kernel / Observable Features / VQC
  - Pipeline B: NEQR Encoding -> Quantum Overlap Kernel / Observable Features / VQC
  - Models: QuantumKernelClassifier, HybridQuantumClassifier, VariationalQuantumClassifier
  - Full Experiment Manager & Paired Evaluator
"""

from .frqi_qml import FRQIQMLPipeline
from .neqr_qml import NEQRQMLPipeline
from .models import (
    QuantumKernelClassifier,
    HybridQuantumClassifier,
    VariationalQuantumClassifier,
    evaluate_classifier_metrics,
)
from .reconstruction_eval import QuantumReconstructionEvaluator
from .experiment_manager import QMLExperimentManager

__all__ = [
    "FRQIQMLPipeline",
    "NEQRQMLPipeline",
    "QuantumKernelClassifier",
    "HybridQuantumClassifier",
    "VariationalQuantumClassifier",
    "evaluate_classifier_metrics",
    "QuantumReconstructionEvaluator",
    "QMLExperimentManager",
]
