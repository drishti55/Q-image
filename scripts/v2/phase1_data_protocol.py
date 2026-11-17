"""Phase 1: build + validate the dataset manifest, create blocked splits, verify integrity."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.model_selection import StratifiedShuffleSplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.v2.dataset import (  # noqa: E402
    DEFAULT_SEEDS, adjacency_report, build_manifest, make_split, save_manifest, save_split,
    validate_manifest, verify_split,
)
from src.v2.paths import v2_root  # noqa: E402


def main():
    out = v2_root()
    manifest = build_manifest()
    checks = validate_manifest(manifest)
    mpath = save_manifest(manifest)
    print("manifest:", manifest["manifest_id"], mpath.name)
    print(json.dumps({k: v for k, v in checks.items() if k not in ("index_ranges",)}, indent=1)[:3000])

    integrity = {"manifest_id": manifest["manifest_id"], "dataset_checks": checks, "splits": {}}
    for seed in DEFAULT_SEEDS:
        split = make_split(manifest, seed)
        save_split(split)
        v = verify_split(split, manifest)
        adj = adjacency_report(manifest, split)
        # Comparison: the old protocol's random stratified split of the same pool, same sizes
        pool = [r for r in manifest["records"] if r["role"] == "trainval"]
        y = np.array([r["class_idx"] for r in pool])
        sss = StratifiedShuffleSplit(1, test_size=len(split["val"]), random_state=seed)
        tr, va = next(sss.split(np.zeros(len(y)), y))
        rand = {"train": [pool[i]["rel_path"] for i in tr], "val": [pool[i]["rel_path"] for i in va],
                "test": split["test"]}
        adj_rand = adjacency_report(manifest, rand)
        integrity["splits"][str(seed)] = {
            "split_id": split["split_id"], "counts": split["counts"], "val_groups": split["val_groups"],
            "overlap_checks": v, "adjacency_blocked": adj, "adjacency_random_split_for_comparison": adj_rand,
        }
        print(f"seed {seed}: {split['split_id']} counts={split['counts']} ok={v['ok']} "
              f"adj(val) blocked={adj['val']['nn_within_radius_rate']:.3f} "
              f"random={adj_rand['val']['nn_within_radius_rate']:.3f} test={adj['test']['nn_within_radius_rate']:.3f}")
    integrity["ok"] = checks["ok"] and all(s["overlap_checks"]["ok"] for s in integrity["splits"].values())
    (out / "manifests" / "split_integrity.json").write_text(json.dumps(integrity, indent=1))
    print("ALL OK:", integrity["ok"])
    return 0 if integrity["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
