"""Phase 7: frozen-CNN features -> PCA(k) -> quantum classifier (E5), with classical controls on the
IDENTICAL k-dimensional features. Usage: python scripts/v2/phase7_hybrid.py"""
from __future__ import annotations

from common import make_runner
from phase5_vqc import vqc_spec

from src.v2.cnn import FrozenMobileNetV3Source
from src.v2.models_classical import LOGREG_GRID, SVM_GRID, LogReg, RBFSVM
from src.v2.providers import VectorProvider
from src.v2.qkernel import QuantumKernelSVC
from src.v2.runner import ModelSpec

KS = (4, 6, 8)
BW = (0.05, 0.1, 0.2, 0.5, 1.0)
CS = (0.1, 1.0, 10.0, 100.0)


def main():
    r = make_runner("phase7_hybrid")
    src = FrozenMobileNetV3Source()
    for k in KS:
        prov = VectorProvider(src, k, "angle")
        fe = f"frozen MobileNetV3-small (IMAGENET1K_V1) 576-d -> StandardScaler -> PCA({k}) -> MinMax[0,pi]"
        # classical controls on exactly these features
        r.run_group(f"E5-mnv3pca{k}-rbfsvm", [ModelSpec(
            "E5", f"E5-mnv3pca{k}-rbfsvm", "CNN features + RBF-SVM (control)", "classical", "classical", fe, None, p,
            RBFSVM, prov) for p in SVM_GRID])
        r.run_group(f"E5-mnv3pca{k}-logreg", [ModelSpec(
            "E5", f"E5-mnv3pca{k}-logreg", "CNN features + Logistic Regression (control)", "classical", "classical",
            fe, None, p, LogReg, prov) for p in LOGREG_GRID])
        # CNN + QKC
        for fmap in ("product_ry", "zz_linear", "zz_full"):
            g = f"E5-mnv3pca{k}-qkc-{fmap}"
            r.run_group(g, [ModelSpec(
                "E5", g, f"CNN features + QKC ({fmap})", "hybrid", "hybrid", fe, f"{fmap} feature map",
                {"feature_map": fmap, "reps": 1, "bandwidth": bw, "C": C, "shots": 0}, QuantumKernelSVC, prov,
                notes="Classical CNN feature extractor + simulated quantum fidelity kernel + classical SVC",
                quantum={"n_qubits": k, "n_layers": 1, "shots": 0, "optimizer": None, "learning_rate": None,
                         "feature_map": fmap, "bandwidth": bw}) for bw in BW for C in CS])
        # CNN + VQC
        g = f"E5-mnv3pca{k}-vqc"
        r.run_group(g, [vqc_spec(k, L, "adam", group=g, prov=prov, fe=fe, code="E5", family="hybrid")
                        for L in (1, 2, 3)])


if __name__ == "__main__":
    main()
