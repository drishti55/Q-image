"""
Verify that historical (Protocol V0) result files are byte-identical to the
preservation manifest captured before v2 work began.

Usage:  python scripts/v2/verify_historical.py [--label PHASE] [--json OUT]
Exit code 0 = all mandatory files unchanged and none removed; 1 otherwise.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "results/qml_v2/manifests/historical_preservation_manifest.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify() -> dict:
    manifest = json.loads(MANIFEST.read_text())
    original = manifest["files"]
    mandatory_roots = manifest["mandatory_immutable"]
    changed, missing = [], []
    for rel, meta in original.items():
        p = ROOT / rel
        if not p.exists():
            missing.append(rel)
        elif sha256(p) != meta["sha256"]:
            changed.append(rel)
    current = {
        str(p.relative_to(ROOT)) for p in (ROOT / "results").rglob("*")
        if p.is_file() and not str(p.relative_to(ROOT)).startswith("results/qml_v2")
    }
    added = sorted(current - set(original))

    def in_mandatory(rel):
        return any(rel.startswith(r + "/") for r in mandatory_roots)

    report = {
        "checked_at": datetime.now().isoformat(),
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "original_file_count": len(original),
        "current_file_count": len(current),
        "changed": changed,
        "missing": missing,
        "added": added,
        "mandatory": {
            r: {
                "original": sum(1 for k in original if k.startswith(r + "/")),
                "current": sum(1 for k in current if k.startswith(r + "/")),
            } for r in mandatory_roots
        },
        "mandatory_ok": not any(in_mandatory(x) for x in changed + missing + added),
        "all_ok": not (changed or missing or added),
    }
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    r = verify()
    r["label"] = a.label
    print(f"[{a.label}] original={r['original_file_count']} current={r['current_file_count']} "
          f"changed={len(r['changed'])} missing={len(r['missing'])} added={len(r['added'])} "
          f"mandatory_ok={r['mandatory_ok']} all_ok={r['all_ok']}")
    for k in ("changed", "missing", "added"):
        for x in r[k][:20]:
            print(f"  {k}: {x}")
    log = ROOT / "results/qml_v2/logs/historical_verification.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a") as f:
        f.write(json.dumps({k: r[k] for k in ("label", "checked_at", "original_file_count",
                                               "current_file_count", "changed", "missing", "added",
                                               "mandatory_ok", "all_ok")}) + "\n")
    if a.json:
        Path(a.json).write_text(json.dumps(r, indent=2))
    sys.exit(0 if r["all_ok"] else 1)
