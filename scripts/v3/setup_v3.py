"""Create results/qml_v3 and copy (never move) the Protocol V2 dataset manifest, the three split files and the
derived image / MobileNetV3 feature caches. Every copy is verified byte-for-byte (SHA-256), so V3 uses exactly
the V2 dataset, split protocol and seeds. Writes manifests/v3_provenance.json."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime

from common import V2, V3

from src.v2.dataset import DEFAULT_SEEDS, load_manifest, load_split, verify_split


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    copied = []
    for sub in ("manifests", "manifests/splits", "cache"):
        src_dir, dst_dir = V2 / sub, V3 / sub
        dst_dir.mkdir(parents=True, exist_ok=True)
        for f in sorted(src_dir.iterdir()):
            if not f.is_file():
                continue
            if sub == "manifests" and not (f.name.startswith("dataset_manifest") or f.name == "split_integrity.json"):
                continue
            d = dst_dir / f.name
            if not d.exists():
                shutil.copy2(f, d)
            h1, h2 = sha(f), sha(d)
            assert h1 == h2, f"copy mismatch {f}"
            copied.append({"file": f"{sub}/{f.name}", "sha256": h1})
    m = load_manifest()
    checks = {s: verify_split(load_split(s), m) for s in DEFAULT_SEEDS}
    prov = {"created_at": datetime.now().isoformat(), "source": "results/qml_v2 (read-only copy)",
            "manifest_id": m["manifest_id"], "seeds": list(DEFAULT_SEEDS),
            "split_ids": {s: load_split(s)["split_id"] for s in DEFAULT_SEEDS},
            "split_verification": checks, "files": copied,
            "note": "Dataset, splits, seeds and locked test set are identical to Protocol V2."}
    (V3 / "manifests" / "v3_provenance.json").write_text(json.dumps(prov, indent=1, default=str))
    print(f"copied+verified {len(copied)} files; manifest {m['manifest_id']}; splits {prov['split_ids']}")
    for s, c in checks.items():
        print(s, {k: v for k, v in c.items() if not isinstance(v, (list, dict))})


if __name__ == "__main__":
    main()
