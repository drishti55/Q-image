"""Phase 4: PCA + quantum kernel classifier (E3) and identical-feature classical controls.
Usage: python scripts/v2/phase4_qkc.py [sv] [control] [shots]"""
from __future__ import annotations

import json
import sys

from common import make_runner

from src.v2.models_classical import SVM_GRID, RBFSVM
from src.v2.providers import PixelPCAProvider
from src.v2.qkernel import QuantumKernelSVC
from src.v2.runner import ModelSpec

KS = (4, 6, 8)
BANDWIDTHS = (0.05, 0.1, 0.2, 0.5, 1.0)
CS = (0.1, 1.0, 10.0, 100.0)
MAPS = (("product_ry", (1,)), ("zz_linear", (1, 2)), ("zz_full", (1, 2)))
SHOTS = (100, 500, 1000, 5000)


def qkc_spec(k, fmap, reps, bw, C, shots=0, group=None):
    prov = PixelPCAProvider(k, "angle")
    group = group or f"E3-pca{k}-qkc-{fmap}"
    note = ("CONTROL: product-RY fidelity kernel is classically computable in closed form"
            if fmap == "product_ry" else "ZZFeatureMap convention (Havlicek et al. 2019 / Qiskit)")
    return ModelSpec(
        "E3", group, f"PCA + QKC ({fmap}, reps={reps})", "quantum_kernel", "hybrid",
        f"64x64 pixels -> PCA({k}) -> MinMax[0,pi] (train-fitted) x bandwidth", f"{fmap} feature map",
        {"feature_map": fmap, "reps": reps, "bandwidth": bw, "C": C, "shots": shots}, QuantumKernelSVC, prov,
        notes=note + "; quantum part = feature-map state overlaps (simulated); classical part = SVC",
        quantum={"n_qubits": k, "n_layers": reps, "shots": shots, "optimizer": None, "learning_rate": None,
                 "feature_map": fmap, "bandwidth": bw})


def sv_groups(r):
    for k in KS:
        for fmap, reps_list in MAPS:
            specs = [qkc_spec(k, fmap, reps, bw, C) for reps in reps_list for bw in BANDWIDTHS for C in CS]
            r.run_group(f"E3-pca{k}-qkc-{fmap}", specs)


def control_groups(r):
    for k in KS:
        prov = PixelPCAProvider(k, "angle")
        r.run_group(f"E6-pca{k}-rbfsvm-angle", [
            ModelSpec("E6", f"E6-pca{k}-rbfsvm-angle", "PCA + RBF-SVM (angle features)", "classical", "classical",
                      f"64x64 pixels -> PCA({k}) -> MinMax[0,pi] (identical inputs to QKC)", None, p, RBFSVM, prov,
                      notes="classical control on exactly the QKC input features") for p in SVM_GRID])


def shot_groups(r):
    """Finite-shot versions of the statevector-selected ZZ configuration for each k (selection made on
    validation in sv_groups; the shot study does not re-select)."""
    from src.v2.paths import v2_root
    for k in KS:
        best = None
        for fmap in ("zz_linear", "zz_full"):
            sel = json.loads((v2_root() / "aggregates" / "selection" / f"E3-pca{k}-qkc-{fmap}.json").read_text())
            if sel["selected"] and (best is None or sel["selected"]["val_mean"] > best["val_mean"]):
                best = sel["selected"]
        p = best["params"]
        for shots in SHOTS:
            g = f"E3-pca{k}-qkc-{p['feature_map']}-shots{shots}"
            r.run_group(g, [qkc_spec(k, p["feature_map"], p["reps"], p["bandwidth"], p["C"], shots, group=g)])


if __name__ == "__main__":
    stages = sys.argv[1:] or ["sv", "control", "shots"]
    r = make_runner("phase4_" + "_".join(stages))
    if "control" in stages:
        control_groups(r)
    if "sv" in stages:
        sv_groups(r)
    if "shots" in stages:
        shot_groups(r)
