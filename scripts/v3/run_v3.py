"""
Protocol V3 experiment driver.  All outputs: results/qml_v3 (results/qml_v2 is write-protected in this process).

Stages (run in this order):
  candidates --worker i --of n   fit every (configuration, seed) on TRAIN, score on internal VAL. Work is split
                                 deterministically across n parallel worker processes (resumable).
  select                         per group: configuration with the best mean validation macro-F1 (Runner.select).
  controls                       VQC controls that depend on a selection: frozen-random-circuit ablation and
                                 encoding-only (L = 0) control with the selected readout; then rerun candidates+select
                                 for them (`controls` again after their candidates have run).
  freeze                         writes aggregates/frozen_selection.json (all selected configs + the pre-declared
                                 comparison family + SHA-256 of every selection file). No test data touched so far.
  test                           verifies every selection file is unchanged since freeze, then evaluates each frozen
                                 configuration on the locked test set exactly once (Runner.final_test).
Usage: python scripts/v3/run_v3.py <stage> [--worker i --of n]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Tuple

from common import V3, make_runner

from src.v2.models_classical import LogReg, RBFSVM
from src.v2.providers import ImageProvider
from src.v2.runner import ModelSpec
from src.v3.features import MobileNetProvider, PixelProvider, TextureProvider
from src.v3.models import EncodingKernelSVCv3, ProjectedQuantumKernelSVC, QuantumKernelSVCv3, VQCv3

SEL = V3 / "aggregates" / "selection"

# ─────────────────────────── feature sets ───────────────────────────
FEATS = {
    # key: (provider factory, k, short description, family for quantum models)
    "pix8a": (lambda: PixelProvider(8, "angle"), 8, "64x64 pixels -> PCA(8) -> MinMax[0,pi] (V2 view)"),
    "pix8c": (lambda: PixelProvider(8, "cdf"), 8, "64x64 pixels -> PCA(8) -> pi*Phi(z)"),
    "pix12c": (lambda: PixelProvider(12, "cdf"), 12, "64x64 pixels -> PCA(12) -> pi*Phi(z)"),
    "pixn8c": (lambda: PixelProvider(8, "cdf", norm="image"), 8, "64x64 pixels, per-image z-scored -> PCA(8) -> pi*Phi(z)"),
    "tex8c": (lambda: TextureProvider(8, "cdf"), 8, "LBP+GLCM texture (76-d, non-learned) -> PCA(8) -> pi*Phi(z)"),
    "tex12c": (lambda: TextureProvider(12, "cdf"), 12, "LBP+GLCM texture (76-d, non-learned) -> PCA(12) -> pi*Phi(z)"),
    "mnv8c": (lambda: MobileNetProvider(8, "cdf"), 8, "frozen MobileNetV3 576-d -> PCA(8) -> pi*Phi(z)"),
    "mnv12c": (lambda: MobileNetProvider(12, "cdf"), 12, "frozen MobileNetV3 576-d -> PCA(12) -> pi*Phi(z)"),
}
_PROV: Dict[str, object] = {}


def prov(f):
    if f not in _PROV:
        _PROV[f] = FEATS[f][0]()
    return _PROV[f]


def is_hybrid(f):
    return f.startswith("mnv")


def qfamily(f):
    return "hybrid" if is_hybrid(f) else "quantum_kernel"


BW8, C8 = (0.25, 0.5, 1.0, 1.5, 2.0, 3.0), (1.0, 10.0, 100.0, 1000.0)
BW12, C12 = (0.5, 1.0, 2.0), (10.0, 100.0, 1000.0)
GAMMA8, GAMMA12 = (0.1, 0.3, 1.0, 3.0), (0.1, 0.3, 1.0)
RBF_GRID = [{"C": C, "gamma": g} for C in (0.1, 1.0, 10.0, 100.0, 1000.0) for g in (0.01, 0.03, 0.1, 0.3, 1.0, 3.0)]
LR_GRID = [{"C": C} for C in (0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0)]


def qkc_specs(f, fmap) -> List[ModelSpec]:
    k = FEATS[f][1]
    if f == "pix8a":
        grid = [(1, bw, C) for bw in (0.5, 1.0, 1.5, 2.0, 3.0) for C in (10.0, 100.0, 1000.0)]
    elif k == 12:
        grid = [(1, bw, C) for bw in BW12 for C in C12]
    else:
        reps = (1,) if fmap == "product_ry" else (1, 2)
        grid = [(r, bw, C) for r in reps for bw in BW8 for C in C8]
    g = f"V3-{f}-qkc-{fmap}"
    return [ModelSpec("V3Q", g, f"QKC {fmap} (fidelity kernel)", qfamily(f), "hybrid", FEATS[f][2], f"{fmap} feature map",
                      {"feature_map": fmap, "reps": r, "bandwidth": bw, "C": C, "shots": 0}, QuantumKernelSVCv3, prov(f),
                      notes="simulated fidelity kernel |<phi(x)|phi(y)>|^2 + classical SVC" +
                            ("; product-RY kernel is classically computable (control)" if fmap == "product_ry" else ""),
                      quantum={"n_qubits": k, "n_layers": r, "shots": 0, "optimizer": None, "learning_rate": None,
                               "feature_map": fmap, "bandwidth": bw, "kernel": "fidelity"}) for r, bw, C in grid]


def pqk_specs(f, fmap) -> List[ModelSpec]:
    k = FEATS[f][1]
    grid = [(bw, gm, C) for bw in (0.5, 1.0, 2.0) for gm in (GAMMA12 if k == 12 else GAMMA8) for C in (C12 if k == 12 else C8)]
    g = f"V3-{f}-pqk-{fmap}"
    return [ModelSpec("V3P", g, f"Projected quantum kernel ({fmap})", qfamily(f), "hybrid", FEATS[f][2],
                      f"{fmap} feature map, projected (1-qubit RDMs)",
                      {"feature_map": fmap, "reps": 1, "bandwidth": bw, "gamma": gm, "C": C}, ProjectedQuantumKernelSVC,
                      prov(f), notes="simulated feature-map states -> 3n single-qubit Pauli expectations -> Gaussian kernel "
                                     "on reduced density matrices (Huang et al. 2021) + classical SVC",
                      quantum={"n_qubits": k, "n_layers": 1, "shots": 0, "optimizer": None, "learning_rate": None,
                               "feature_map": fmap, "bandwidth": bw, "kernel": "projected"}) for bw, gm, C in grid]


def classical_specs(f, kind) -> List[ModelSpec]:
    g = f"V3-{f}-{kind}"
    est, grid, name = (RBFSVM, RBF_GRID, "RBF-SVM (matched control)") if kind == "rbfsvm" else (LogReg, LR_GRID, "Logistic Regression (matched control)")
    return [ModelSpec("V3C", g, name, "classical", "classical", FEATS[f][2], None, p, est, prov(f),
                      notes="classical control on exactly the quantum models' input features") for p in grid]


def vqc_spec(f, layers, readout, opt="adam", train_quantum=True, group=None, name=None) -> ModelSpec:
    k = FEATS[f][1]
    params = {"layers": layers, "optimizer": opt, "entangler": "ring", "reupload": layers > 0, "readout": readout,
              "train_quantum": train_quantum, "lr": 0.05, "epochs": 120, "patience": 15}
    g = group or f"V3-{f}-vqc"
    nm = name or f"VQC ({opt}, L={layers}, readout {readout}{', re-upload' if layers > 0 else ''})"
    fam = "hybrid" if is_hybrid(f) else "variational_quantum"
    return ModelSpec("V3V", g, nm, fam, "hybrid", FEATS[f][2], "RY angle encoding (+ re-upload) + RY/RZ layers + CNOT ring",
                     params, VQCv3, prov(f),
                     notes="genuine parameterised circuit, exact expectation values, parameter-shift gradients (Adam) "
                           "or calibrated SPSA; classical head = per-class scale+bias (diag6) or linear map on all <Z_i> (zall)",
                     quantum={"n_qubits": k, "n_layers": layers, "optimizer": opt, "learning_rate": 0.05 if opt == "adam" else None,
                              "shots": 0, "entangler": "ring", "data_reuploading": layers > 0, "readout": readout,
                              "train_quantum": train_quantum})


def enc_specs(rep, r) -> List[ModelSpec]:
    g = f"V3-{rep.lower()}{r}"
    out = []
    for norm in ("none", "stretch"):
        for kern in ("fidelity", "overlap"):
            for C in C8:
                if rep == "FRQI":
                    for s in (1.0, 2.0, 4.0):
                        out.append((norm, kern, C, {"angle_scale": s, "bits": 8}))
                else:
                    for b in (2, 3, 4, 8):
                        out.append((norm, kern, C, {"bits": b, "angle_scale": 1.0}))
    specs = []
    for norm, kern, C, extra in out:
        bits = extra["bits"]
        nq = 2 * (r.bit_length() - 1) + (1 if rep == "FRQI" else bits)
        specs.append(ModelSpec("V3E", g, f"{rep} state kernel {r}x{r}", "quantum_kernel", "hybrid",
                               f"{r}x{r} grayscale pixels" + (" (per-image contrast stretch)" if norm == "stretch" else ""),
                               rep, {"representation": rep, "C": C, "kernel": kern, "norm": norm, "shots": 0, **extra},
                               EncodingKernelSVCv3, ImageProvider(r),
                               notes="exact overlap of encoded image states (fidelity = swap test, overlap = Hadamard test) + SVC",
                               quantum={"n_qubits": nq, "n_layers": None, "optimizer": None, "learning_rate": None, "shots": 0,
                                        "representation": rep, "intensity_bits": bits if rep == "NEQR" else None,
                                        "kernel": kern}))
    return specs


def all_groups() -> Dict[str, List[ModelSpec]]:
    G: Dict[str, List[ModelSpec]] = {}
    for f in FEATS:
        maps = ("zz_full", "product_ry") if f == "pixn8c" else ("product_ry", "zz_linear", "zz_full")
        for m in maps:
            G[f"V3-{f}-qkc-{m}"] = qkc_specs(f, m)
        if f not in ("pix8a", "pixn8c"):
            for m in ("zz_linear", "zz_full"):
                G[f"V3-{f}-pqk-{m}"] = pqk_specs(f, m)
        for kind in ("rbfsvm", "logreg"):
            G[f"V3-{f}-{kind}"] = classical_specs(f, kind)
    for f in ("pix8c", "tex8c", "mnv8c"):
        G[f"V3-{f}-vqc"] = [vqc_spec(f, L, ro) for ro in ("diag6", "zall") for L in (2, 4)]
    for f in ("pix8c", "tex8c"):
        g = f"V3-{f}-vqc-spsa"
        G[g] = [vqc_spec(f, 2, "zall", opt="spsa", group=g)]
    for rep in ("FRQI", "NEQR"):
        for r in (2, 4, 8, 16):
            G[f"V3-{rep.lower()}{r}"] = enc_specs(rep, r)
    return G


def control_groups() -> Dict[str, List[ModelSpec]]:
    """Depend on VQC selections (available after `select`)."""
    G = {}
    for f in ("pix8c", "tex8c", "mnv8c"):
        p = json.loads((SEL / f"V3-{f}-vqc.json").read_text())["selected"]["params"]
        g = f"V3-{f}-vqc-ablation-frozen"
        G[g] = [vqc_spec(f, p["layers"], p["readout"], train_quantum=False, group=g,
                         name=f"ABLATION frozen random circuit + trained head (L={p['layers']}, {p['readout']})")]
        g = f"V3-{f}-vqc-encoding-only"
        G[g] = [vqc_spec(f, 0, p["readout"], group=g, name=f"CONTROL encoding only, no trainable gates ({p['readout']} head)")]
    return G


def cost(group: str, specs: List[ModelSpec]) -> float:
    if "-vqc" in group and "spsa" not in group:
        return 1e9  # handled per (spec, seed)
    w = 1.0
    if "12c" in group:
        w = 6.0
    if "-pqk-" in group:
        w *= 1.2
    if group.startswith("V3-neqr16") or group.startswith("V3-frqi16"):
        w = 2.0
    return w * len(specs)


def work_units(G) -> List[Tuple[float, str, object]]:
    units = []
    for g, specs in G.items():
        if "-vqc" in g and "spsa" not in g:
            for sp in specs:
                L = sp.params["layers"]
                for s in (0, 1, 2):
                    units.append((float(1 + L * L) * 100, g, (sp, s)))
        else:
            units.append((cost(g, specs), g, None))
    return sorted(units, key=lambda u: (-u[0], u[1], str(u[2][1]) if u[2] else ""))


def assign(units, n):
    load = [0.0] * n
    out = [[] for _ in range(n)]
    for u in units:
        i = min(range(n), key=lambda j: load[j])
        out[i].append(u)
        load[i] += u[0]
    return out


def stage_candidates(G, worker, of, tag):
    r = make_runner(f"v3_{tag}_w{worker}of{of}")
    mine = assign(work_units(G), of)[worker]
    r.log(f"worker {worker}/{of}: {len(mine)} units")
    for _, g, unit in mine:
        if unit is None:
            for sp in G[g]:
                for s in r.seeds:
                    r.run_candidate(sp, s)
        else:
            sp, s = unit
            r.run_candidate(sp, s)


def stage_select(G, tag):
    r = make_runner(f"v3_select_{tag}")
    for g, specs in G.items():
        r.run_group(g, specs, final=False)


PLANNED = {
    "headline_rule": "Within each category the headline model is the group with the highest mean validation macro-F1 "
                     "(test not consulted). Categories: pure quantum (non-CNN features, incl. FRQI/NEQR), VQC, hybrid.",
    "comparisons": "For every feature set: best-by-validation quantum group vs the matched RBF-SVM (identical features); "
                   "V3 headline vs the corresponding V2 baseline (E3-pca8-qkc-zz_full, E4-pca8-vqc, E1b-frqi8-qkc-scaled, "
                   "E2-neqr16-b4-qkc, E5-mnv3pca8-qkc-product_ry, E5-mnv3pca8-vqc); each selected VQC vs its frozen-circuit "
                   "ablation and encoding-only control. Paired sign-flip permutation test on per-image correctness averaged "
                   "over seeds (10,000 permutations) + per-seed exact McNemar; Holm correction over the whole family.",
}


def stage_freeze():
    files = sorted(SEL.glob("V3-*.json"))
    groups = {}
    for p in files:
        d = json.loads(p.read_text())
        groups[d["group"]] = {"selected_config_key": (d["selected"] or {}).get("config_key"),
                              "val_mean_f1_macro": (d["selected"] or {}).get("val_mean"),
                              "n_candidates": d["n_candidates"], "selection_sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    out = {"frozen_at": datetime.now().isoformat(), "n_groups": len(groups), "groups": groups, "plan": PLANNED,
           "statement": "All configurations frozen using validation data only. The locked test set had not been "
                        "accessed in Protocol V3 when this file was written."}
    p = V3 / "aggregates" / "frozen_selection.json"
    if p.exists():
        raise SystemExit("frozen_selection.json already exists — selections are frozen; refusing to overwrite")
    p.write_text(json.dumps(out, indent=1))
    print(f"frozen {len(groups)} groups; sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")


def stage_test(G):
    fz = json.loads((V3 / "aggregates" / "frozen_selection.json").read_text())
    r = make_runner("v3_final_test")
    for g, info in fz["groups"].items():
        p = SEL / f"{g}.json"
        if hashlib.sha256(p.read_bytes()).hexdigest() != info["selection_sha256"]:
            raise SystemExit(f"selection file for {g} changed after freeze — aborting")
    for g, info in fz["groups"].items():
        key = info["selected_config_key"]
        if key is None:
            r.log(f"  {g}: no eligible configuration, no test")
            continue
        spec = next(s for s in G[g] if s.config_key() == key)
        done = all((r.store.dir(spec.experiment_id(s)) / "test_metrics.json").exists() for s in r.seeds)
        if done:
            r.log(f"  {g}: locked test already evaluated — not re-evaluated")
            continue
        r.final_test(spec)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["candidates", "select", "controls", "freeze", "test", "plan"])
    ap.add_argument("--worker", type=int, default=0)
    ap.add_argument("--of", type=int, default=1)
    a = ap.parse_args()
    if a.stage == "plan":
        G = all_groups()
        print(len(G), "groups,", sum(len(v) for v in G.values()), "configurations,",
              3 * sum(len(v) for v in G.values()), "candidate runs")
        for g, v in G.items():
            print(f"  {g}: {len(v)}")
    elif a.stage == "candidates":
        stage_candidates(all_groups(), a.worker, a.of, "main")
    elif a.stage == "select":
        stage_select(all_groups(), "main")
    elif a.stage == "controls":
        C = control_groups()
        stage_candidates(C, a.worker, a.of, "controls")
        if a.of == 1:
            stage_select(C, "controls")
    elif a.stage == "freeze":
        stage_freeze()
    elif a.stage == "test":
        G = all_groups()
        G.update(control_groups())
        stage_test(G)
