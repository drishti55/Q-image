"""Phase 3: classical baselines (E6 PCA+SVM/LogReg) and CNN models (E7 small CNN, frozen MobileNetV3).
Usage: python scripts/v2/phase3_classical.py [pca] [cnn] [mnv3]"""
from __future__ import annotations

import sys

from common import make_runner

from src.v2.models_classical import LOGREG_GRID, SVM_GRID, LogReg, RBFSVM
from src.v2.providers import ImageProvider, PixelPCAProvider, VectorProvider
from src.v2.runner import ModelSpec


def pca_groups(r):
    for k in (4, 6, 8):
        prov = PixelPCAProvider(k, "standard")
        fe = f"64x64 pixels -> PCA({k}) -> standardized"
        r.run_group(f"E6-pca{k}-rbfsvm", [
            ModelSpec("E6", f"E6-pca{k}-rbfsvm", "PCA + RBF-SVM", "classical", "classical", fe, None, p,
                      RBFSVM, prov) for p in SVM_GRID])
        r.run_group(f"E6-pca{k}-logreg", [
            ModelSpec("E6", f"E6-pca{k}-logreg", "PCA + Logistic Regression", "classical", "classical", fe, None,
                      p, LogReg, prov) for p in LOGREG_GRID])


def cnn_group(r):
    from src.v2.cnn import SmallCNN
    prov = ImageProvider(128)
    r.run_group("E7-smallcnn", [
        ModelSpec("E7", "E7-smallcnn", "Small CNN (from scratch)", "classical", "classical",
                  "128x128 grayscale, end-to-end CNN", None, p, SmallCNN, prov,
                  notes="4 conv blocks (16-32-64-128), BN, ReLU, maxpool, GAP, dropout 0.3, linear")
        for p in ({"lr": 1e-3}, {"lr": 3e-4})])


def mnv3_groups(r):
    from src.v2.cnn import FrozenMobileNetV3Source
    src = FrozenMobileNetV3Source()
    prov = VectorProvider(src, None, "standard")
    fe = "frozen MobileNetV3-small IMAGENET1K_V1, 576-d GAP features -> standardized"
    r.run_group("E7-mnv3-logreg", [
        ModelSpec("E7", "E7-mnv3-logreg", "Frozen MobileNetV3 + Logistic Regression", "classical", "classical",
                  fe, None, p, LogReg, prov) for p in LOGREG_GRID])
    grid = [{"C": C, "gamma": g} for C in (0.1, 1.0, 10.0, 100.0) for g in (0.0005, 0.002, 0.008)]
    r.run_group("E7-mnv3-rbfsvm", [
        ModelSpec("E7", "E7-mnv3-rbfsvm", "Frozen MobileNetV3 + RBF-SVM", "classical", "classical",
                  fe, None, p, RBFSVM, prov) for p in grid])


if __name__ == "__main__":
    stages = sys.argv[1:] or ["pca", "cnn", "mnv3"]
    r = make_runner("phase3_" + "_".join(stages))
    if "pca" in stages:
        pca_groups(r)
    if "mnv3" in stages:
        mnv3_groups(r)
    if "cnn" in stages:
        cnn_group(r)
