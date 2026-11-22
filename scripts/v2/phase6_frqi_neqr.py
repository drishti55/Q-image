"""Phase 6: FRQI / NEQR under Protocol V2.
  classify   : E1 FRQI-overlap QKC, E1b FRQI bandwidth variant, E2 NEQR-overlap QKC, relabelled legacy models
  shots      : finite-shot versions of the validation-selected E1/E2 configurations at 8x8
  recon      : encoding/reconstruction study (separate record type)
Usage: python scripts/v2/phase6_frqi_neqr.py [classify] [shots] [recon]"""
from __future__ import annotations

import json
import sys

from common import make_runner

from src.v2.frqi_neqr import EncodingKernelSVC, EncodingStatsLogReg, LegacyFixedSoftmax
from src.v2.providers import ImageProvider
from src.v2.runner import ModelSpec

CS = (0.1, 1.0, 10.0, 100.0)
RES = (2, 4, 8, 16)


def enc_spec(group, code, rep, r, C, bits=8, scale=1.0, shots=0):
    nq = (2 * (r.bit_length() - 1)) + (1 if rep == "FRQI" else bits)
    name = f"{rep}-overlap QKC {r}x{r}" + (f" {bits}-bit" if rep == "NEQR" else "") + \
           (f" (angle scale {scale})" if rep == "FRQI" and scale != 1.0 else "")
    return ModelSpec(code, group, name, "quantum_kernel", "hybrid", f"{r}x{r} grayscale pixels (no learned transform)",
                     f"{rep}" + (" original" if scale == 1.0 else f" angle-scaled x{scale} (variant; not invertible)"),
                     {"representation": rep, "C": C, "bits": bits, "angle_scale": scale, "shots": shots},
                     EncodingKernelSVC, ImageProvider(r),
                     notes="quantum part: exact overlap of encoded image states; classical part: SVC",
                     quantum={"n_qubits": nq, "n_layers": None, "optimizer": None, "learning_rate": None,
                              "shots": shots, "representation": rep, "intensity_bits": bits if rep == "NEQR" else None})


def classify(r_):
    for r in RES:
        r_.run_group(f"E1-frqi{r}-qkc", [enc_spec(f"E1-frqi{r}-qkc", "E1", "FRQI", r, C) for C in CS])
        if r >= 4:
            g = f"E1b-frqi{r}-qkc-scaled"
            r_.run_group(g, [enc_spec(g, "E1b", "FRQI", r, C, scale=s) for s in (2.0, 4.0, 8.0) for C in CS])
        for b in (2, 4, 8):
            g = f"E2-neqr{r}-b{b}-qkc"
            r_.run_group(g, [enc_spec(g, "E2", "NEQR", r, C, bits=b) for C in CS])
    for r in (4, 8):
        for rep, code in (("FRQI", "E1"), ("NEQR", "E2")):
            g = f"{code}-{rep.lower()}{r}-encstats-logreg"
            r_.run_group(g, [ModelSpec(
                code, g, f"{rep} encoding statistics + Logistic Regression (classical; legacy 'HQCC')",
                "quantum_inspired_classical", "classical", f"{r}x{r} pixels -> closed-form {rep} statistics",
                None, {"representation": rep, "C": C, "bits": 4}, EncodingStatsLogReg, ImageProvider(r),
                notes="No circuit is executed; legacy V0 'HQCC' relabelled") for C in (0.01, 0.1, 1.0, 10.0)])
    for rep, code in (("FRQI", "E1"), ("NEQR", "E2")):
        g = f"{code}-{rep.lower()}4-legacy-softmax"
        r_.run_group(g, [ModelSpec(
            code, g, "Fixed-feature softmax regression (formerly labelled 'VQC' in V0)", "quantum_inspired_classical",
            "classical", "4x4 pixels -> closed-form statistics", None, {"representation": rep, "bits": 4},
            LegacyFixedSoftmax, ImageProvider(4), notes="Unchanged V0 code; contains no parameterised quantum circuit")])


def shots(r_):
    from src.v2.paths import v2_root
    sel_dir = v2_root() / "aggregates" / "selection"
    best_n = max((json.loads((sel_dir / f"E2-neqr8-b{b}-qkc.json").read_text())["selected"] for b in (2, 4, 8)),
                 key=lambda s: s["val_mean"])
    best_f = json.loads((sel_dir / "E1-frqi8-qkc.json").read_text())["selected"]
    for s in (100, 1000, 10000):
        pf = best_f["params"]
        g = f"E1-frqi8-qkc-shots{s}"
        r_.run_group(g, [enc_spec(g, "E1", "FRQI", 8, pf["C"], shots=s)])
        pn = best_n["params"]
        g = f"E2-neqr8-b{pn['bits']}-qkc-shots{s}"
        r_.run_group(g, [enc_spec(g, "E2", "NEQR", 8, pn["C"], bits=pn["bits"], shots=s)])


if __name__ == "__main__":
    stages = sys.argv[1:] or ["classify", "shots", "recon"]
    r = make_runner("phase6_" + "_".join(stages))
    if "classify" in stages:
        classify(r)
    if "shots" in stages:
        shots(r)
    if "recon" in stages:
        from src.v2.encoding_study import run_all
        run_all(log=r.log)
