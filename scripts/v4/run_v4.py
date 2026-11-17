"""
Protocol V4 driver: patch-ensemble (mixed-state) FRQI / NEQR kernels + matched classical control.
All outputs: results/qml_v4 (results/qml_v2 and results/qml_v3 are write-protected in this process).

Stages: candidates --worker i --of n | select | freeze | test | plan   (same freeze-then-test protocol as V3)

Pre-test exploration (disclosed in the V4 report): before this grid was written, a few patch geometries were tried on
the internal VALIDATION split only (seeds 0-2); every geometry tried there is included in the grid below, except
NEQR 2x2 patches at stride 1 on 64x64 images (too slow; val F1 0.876, kept at 32x32 / 64x64-stride-2 instead).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from typing import Dict, List

from common import V4, make_runner

from src.v2.providers import ImageProvider
from src.v2.runner import ModelSpec
from src.v4.models import MixedStateEncodingKernelSVC, PatchMomentRBF, patch_qubits

SEL = V4 / "aggregates" / "selection"
CS = (1.0, 10.0, 100.0, 1000.0)
_PROV: Dict[int, ImageProvider] = {}


def img(S):
    if S not in _PROV:
        _PROV[S] = ImageProvider(S)
    return _PROV[S]


GEOMS = {  # group -> (representation, [(image size, patch, stride)], bit options)
    "V4-frqi-p4": ("FRQI", [(32, 4, 2), (64, 4, 4)], None),
    "V4-frqi-p8": ("FRQI", [(32, 8, 4), (64, 8, 4), (128, 8, 8)], None),
    "V4-neqr-p2": ("NEQR", [(32, 2, 1), (64, 2, 2)], (4, 5, 6)),
    "V4-neqr-p4": ("NEQR", [(32, 4, 2), (64, 4, 4), (128, 4, 4)], (3, 4)),
}


def enc_group(g) -> List[ModelSpec]:
    rep, geoms, bit_opts = GEOMS[g]
    specs = []
    for S, p, s in geoms:
        for norm in ("none", "stretch"):
            for extra in ([{"angle_scale": b} for b in (1.0, 2.0, 4.0)] if rep == "FRQI" else [{"bits": q} for q in bit_opts]):
                for C in CS:  # C innermost: consecutive candidates reuse the cached mixed states
                    params = {"representation": rep, "image_size": S, "patch": p, "stride": s, "norm": norm, "C": C, **extra}
                    bits = extra.get("bits", 4)
                    nq = patch_qubits(rep, p, bits)
                    specs.append(ModelSpec(
                        "V4E", g, f"{rep} patch-ensemble kernel ({p}x{p} patches)", "quantum_kernel", "hybrid",
                        f"{S}x{S} grayscale, {p}x{p} patches stride {s}" + (", per-image contrast stretch" if norm == "stretch" else ""),
                        rep, params, MixedStateEncodingKernelSVC, img(S),
                        notes="each patch encoded as an FRQI/NEQR state; image = uniform mixture of its patch states; "
                              "kernel Tr(rho_A rho_B) (swap test), exact; + SVC",
                        quantum={"n_qubits": nq, "n_layers": None, "optimizer": None, "learning_rate": None, "shots": 0,
                                 "representation": rep, "intensity_bits": bits if rep == "NEQR" else None,
                                 "kernel": "mixed-state Hilbert-Schmidt (swap test)"}))
    return specs


def control_group() -> List[ModelSpec]:
    g = "V4-patchmom-rbfsvm"
    specs = []
    for S, p, s in ((64, 4, 4), (64, 8, 4), (128, 4, 4)):
        for norm in ("none", "stretch"):
            for gamma in (0.3, 1.0, 3.0):
                for C in CS:
                    specs.append(ModelSpec("V4C", g, "RBF-SVM on classical patch moments (matched control)", "classical", "classical",
                                           f"{S}x{S} grayscale, {p}x{p} patches stride {s}" + (", per-image contrast stretch" if norm == "stretch" else ""),
                                           None, {"image_size": S, "patch": p, "stride": s, "norm": norm, "gamma": gamma, "C": C},
                                           PatchMomentRBF, img(S),
                                           notes="classical control: same patches, mean + second moment of raw intensities, no quantum feature map"))
    return specs


def all_groups() -> Dict[str, List[ModelSpec]]:
    G = {g: enc_group(g) for g in GEOMS}
    G["V4-patchmom-rbfsvm"] = control_group()
    return G


def units(G):
    """(group, seed) work units, heavy first; within a unit candidates run in spec order (C innermost)."""
    w = {"V4-neqr-p4": 6.0, "V4-neqr-p2": 5.0, "V4-frqi-p8": 2.0, "V4-frqi-p4": 1.0, "V4-patchmom-rbfsvm": 1.5}
    us = [(w[g] * len(G[g]), g, s) for g in G for s in (0, 1, 2)]
    return sorted(us, key=lambda u: (-u[0], u[1], u[2]))


def stage_candidates(G, worker, of):
    r = make_runner(f"v4_main_w{worker}of{of}")
    load, mine = [0.0] * of, [[] for _ in range(of)]
    for u in units(G):
        i = min(range(of), key=lambda j: load[j])
        mine[i].append(u)
        load[i] += u[0]
    r.log(f"worker {worker}/{of}: {[(g, s) for _, g, s in mine[worker]]}")
    for _, g, s in mine[worker]:
        for sp in G[g]:
            r.run_candidate(sp, s)


PLANNED = {
    "headline_rule": "FRQI headline = V4 FRQI group (p4 or p8) with the highest mean validation macro-F1; NEQR headline likewise "
                     "(p2 or p4). Test not consulted.",
    "comparisons": [
        "V4 FRQI headline vs V2 E1b-frqi8-qkc-scaled (published FRQI baseline)",
        "V4 FRQI headline vs V3-frqi8 (best V3 FRQI by validation)",
        "V4 NEQR headline vs V2 E2-neqr16-b4-qkc (published NEQR baseline; V3-neqr16 re-selected the same configuration)",
        "V4 FRQI headline vs V4 NEQR headline",
        "V4 FRQI headline vs V4-patchmom-rbfsvm (classical control, same patches)",
        "V4 NEQR headline vs V4-patchmom-rbfsvm",
        "V4 FRQI headline vs V3-tex12c-rbfsvm (best V3 non-CNN classical control by validation)",
        "V4 NEQR headline vs V3-tex12c-rbfsvm",
    ],
    "statistics": "paired sign-flip permutation test on per-image correctness averaged over seeds (10,000), bootstrap 95% CI, "
                  "per-seed exact McNemar; Holm correction over these 8 comparisons; per-comparison RNG seeded from its name.",
}


def stage_freeze():
    groups = {}
    for p in sorted(SEL.glob("V4-*.json")):
        d = json.loads(p.read_text())
        groups[d["group"]] = {"selected_config_key": (d["selected"] or {}).get("config_key"),
                              "val_mean_f1_macro": (d["selected"] or {}).get("val_mean"),
                              "n_candidates": d["n_candidates"], "selection_sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    out = {"frozen_at": datetime.now().isoformat(), "n_groups": len(groups), "groups": groups, "plan": PLANNED,
           "statement": "All V4 configurations frozen using validation data only; the locked test set had not been accessed "
                        "in Protocol V4 when this file was written."}
    p = V4 / "aggregates" / "frozen_selection.json"
    if p.exists():
        raise SystemExit("frozen_selection.json already exists — refusing to overwrite")
    p.write_text(json.dumps(out, indent=1))
    print(f"frozen {len(groups)} groups; sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")


def stage_test(G):
    fz = json.loads((V4 / "aggregates" / "frozen_selection.json").read_text())
    r = make_runner("v4_final_test")
    for g, info in fz["groups"].items():
        if hashlib.sha256((SEL / f"{g}.json").read_bytes()).hexdigest() != info["selection_sha256"]:
            raise SystemExit(f"selection file for {g} changed after freeze — aborting")
    for g, info in fz["groups"].items():
        spec = next(s for s in G[g] if s.config_key() == info["selected_config_key"])
        if all((r.store.dir(spec.experiment_id(s)) / "test_metrics.json").exists() for s in r.seeds):
            r.log(f"  {g}: locked test already evaluated — not re-evaluated")
            continue
        r.final_test(spec)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["candidates", "select", "freeze", "test", "plan"])
    ap.add_argument("--worker", type=int, default=0)
    ap.add_argument("--of", type=int, default=1)
    a = ap.parse_args()
    G = all_groups()
    if a.stage == "plan":
        print(len(G), "groups,", sum(len(v) for v in G.values()), "configurations,", 3 * sum(len(v) for v in G.values()), "candidate runs")
        for g, v in G.items():
            print(f"  {g}: {len(v)}")
    elif a.stage == "candidates":
        stage_candidates(G, a.worker, a.of)
    elif a.stage == "select":
        r = make_runner("v4_select")
        for g, specs in G.items():
            r.run_group(g, specs, final=False)
    elif a.stage == "freeze":
        stage_freeze()
    elif a.stage == "test":
        stage_test(G)
