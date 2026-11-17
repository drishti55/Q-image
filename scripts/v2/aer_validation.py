"""Validate shot-based kernel estimates on REAL NEU PCA features (train split, seed 0 — never test images):
for the validation-selected ZZ configurations, run the actual compute–uncompute circuit on qiskit-aer and
compare P(0...0) with the exact statevector fidelity. Output: aggregates/aer_kernel_validation.json"""
from __future__ import annotations

import json

import numpy as np

from common import make_runner  # noqa: F401  (sets sys.path)

from src.v2.paths import v2_root
from src.v2.providers import PixelPCAProvider
from src.v2.qkernel import aer_kernel_entry, fidelity_kernel, states
from src.v2.store import dump_json

SHOTS = 4000


def main():
    out = {"shots": SHOTS, "data": "train split of seed 0 (locked test never used)", "configs": []}
    for k, fmap in ((4, "zz_full"), (8, "zz_full")):
        sel = json.loads((v2_root() / "aggregates" / "selection" / f"E3-pca{k}-qkc-{fmap}.json").read_text())["selected"]
        p = sel["params"]
        tr, _, _ = PixelPCAProvider(k, "angle").train_val(0)
        rng = np.random.default_rng(0)
        idx = rng.choice(len(tr.X), size=(25, 2), replace=False)
        X = tr.X * p["bandwidth"]
        rows = []
        for i, j in [(a, a) for a in idx[:5, 0]] + [tuple(r) for r in idx[5:]]:
            exact = float(fidelity_kernel(states(X[i:i + 1], fmap, p["reps"]), states(X[j:j + 1], fmap, p["reps"]))[0, 0])
            est = aer_kernel_entry(X[i], X[j], fmap, p["reps"], SHOTS, seed=int(i) * 7 + int(j))
            sd = np.sqrt(max(exact * (1 - exact), 1.0 / SHOTS) / SHOTS)
            rows.append({"i": int(i), "j": int(j), "identical": bool(i == j), "exact": exact, "aer": est,
                         "z": (est - exact) / sd})
        z = np.array([r["z"] for r in rows])
        out["configs"].append({
            "k": k, "feature_map": fmap, "reps": p["reps"], "bandwidth": p["bandwidth"], "pairs": rows,
            "identical_pairs_all_one": all(r["aer"] == 1.0 for r in rows if r["identical"]),
            "max_abs_z": float(np.max(np.abs(z))), "mean_abs_error": float(np.mean([abs(r["aer"] - r["exact"]) for r in rows])),
            "passes": bool(np.max(np.abs(z)) < 5 and all(r["aer"] == 1.0 for r in rows if r["identical"]))})
        c = out["configs"][-1]
        print(f"k={k} {fmap}: identical->1: {c['identical_pairs_all_one']}  max|z|={c['max_abs_z']:.2f}  "
              f"MAE={c['mean_abs_error']:.4f}  passes={c['passes']}")
    dump_json(v2_root() / "aggregates" / "aer_kernel_validation.json", out)


if __name__ == "__main__":
    main()
