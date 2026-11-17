"""Create results/qml_v4 and copy (never move) the dataset manifest, the three split files and the image caches
from results/qml_v3 (themselves verified copies of Protocol V2). Every copy is verified by SHA-256 against the
source AND against the V3 provenance record. Writes manifests/v4_provenance.json."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime

from common import V3, V4

from src.v2.dataset import DEFAULT_SEEDS, load_manifest, load_split, verify_split


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    v3prov = {e["file"]: e["sha256"] for e in json.loads((V3 / "manifests" / "v3_provenance.json").read_text())["files"]}
    copied = []
    for rel, h in v3prov.items():
        if rel.startswith("cache/") and "img_" not in rel:
            continue  # only image caches are needed (V4 uses raw images only)
        src, dst = V3 / rel, V4 / rel
        assert sha(src) == h, f"V3 file changed since V3 setup: {rel}"
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(src, dst)
        assert sha(dst) == h, f"copy mismatch {rel}"
        copied.append({"file": rel, "sha256": h})
    m = load_manifest()
    checks = {s: verify_split(load_split(s), m) for s in DEFAULT_SEEDS}
    assert all(c["ok"] for c in checks.values())
    prov = {"created_at": datetime.now().isoformat(), "source": "results/qml_v3 (read-only copy of the V2 manifest, splits, image caches)",
            "manifest_id": m["manifest_id"], "seeds": list(DEFAULT_SEEDS),
            "split_ids": {s: load_split(s)["split_id"] for s in DEFAULT_SEEDS}, "split_verification": checks, "files": copied,
            "note": "Dataset, splits, seeds and locked test set are identical to Protocols V2 and V3."}
    (V4 / "manifests" / "v4_provenance.json").write_text(json.dumps(prov, indent=1, default=str))
    print(f"copied+verified {len(copied)} files; manifest {m['manifest_id']}; splits {prov['split_ids']}")


if __name__ == "__main__":
    main()
