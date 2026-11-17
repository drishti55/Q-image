"""Phase 5: genuine VQC on PCA angle features (E4) + frozen-circuit ablation.
Usage: python scripts/v2/phase5_vqc.py [grid] [ablation]"""
from __future__ import annotations

import json
import sys

from common import make_runner

from src.v2.providers import PixelPCAProvider
from src.v2.runner import ModelSpec
from src.v2.vqc import VQC

KS = (4, 6, 8)


def vqc_spec(k, layers, opt, reupload=False, train_quantum=True, group=None, prov=None,
             fe=None, code="E4", family="variational_quantum"):
    prov = prov or PixelPCAProvider(k, "angle")
    params = {"layers": layers, "optimizer": opt, "entangler": "ring", "reupload": reupload,
              "train_quantum": train_quantum}
    lr = 0.05 if opt == "adam" else None
    name = f"VQC ({opt}, L={layers}{', re-upload' if reupload else ''})"
    if not train_quantum:
        name = f"ABLATION frozen random circuit + trained head (L={layers})"
    return ModelSpec(
        code, group or f"E4-pca{k}-vqc", name, family, "hybrid",
        fe or f"64x64 pixels -> PCA({k}) -> MinMax[0,pi] (train-fitted)", "RY angle encoding", params, VQC, prov,
        notes="Quantum: RY encoding + trainable RY/RZ layers + CNOT ring, exact expectation values (simulated). "
              "Classical: 6 per-class scales + 6 biases on the 6 expectation values.",
        quantum={"n_qubits": k, "n_layers": layers, "optimizer": opt, "learning_rate": lr, "shots": 0,
                 "entangler": "ring", "data_reuploading": reupload, "train_quantum": train_quantum})


def grid_groups(r):
    for k in KS:
        specs = [vqc_spec(k, L, opt) for opt in ("adam", "cobyla", "spsa") for L in (1, 2, 3)]
        specs += [vqc_spec(k, L, "adam", reupload=True) for L in (2, 3)]
        r.run_group(f"E4-pca{k}-vqc", specs)


def ablation_groups(r):
    from src.v2.paths import v2_root
    for k in KS:
        sel = json.loads((v2_root() / "aggregates" / "selection" / f"E4-pca{k}-vqc.json").read_text())["selected"]
        p = sel["params"]
        g = f"E4-pca{k}-vqc-ablation-frozen"
        r.run_group(g, [vqc_spec(k, p["layers"], "adam", p["reupload"], train_quantum=False, group=g)])


if __name__ == "__main__":
    stages = sys.argv[1:] or ["grid", "ablation"]
    r = make_runner("phase5_" + "_".join(stages))
    if "grid" in stages:
        grid_groups(r)
    if "ablation" in stages:
        ablation_groups(r)
