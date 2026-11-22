"""
NEU-DET dataset manifest, validation, blocked splits and the locked test set (Protocol V2).

Protocol
--------
* Locked test set  = every image in <dataset>/validation/images  (official NEU-DET split,
  per-class file indices 241-300). It is only readable inside `final_evaluation_stage()`.
* Train/val pool   = every image in <dataset>/train/images (indices 1-240 per class).
* Groups           = contiguous index blocks of BLOCK_SIZE images within a class
  (block = (index-1)//BLOCK_SIZE). Neighbouring indices are visually correlated (measured in
  Phase 1, see reports/PHASE1_DATA_PROTOCOL.md), so whole blocks are assigned to train or val.
* Per seed, VAL_BLOCKS_PER_CLASS blocks of each class are drawn for internal validation.

Preprocessing (identical for every model unless a model documents otherwise)
---------------------------------------------------------------------------
PIL open -> convert("L") (the JPEGs are stored as 3-channel RGB copies of grayscale) ->
resize((s, s), BILINEAR) -> float64 / 255  ==> values in [0, 1].
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import re
import threading
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image

from .paths import dataset_root, v2_root

CLASSES: List[str] = [
    "crazing", "inclusion", "patches", "pitted_surface", "rolled-in_scale", "scratches",
]
DISPLAY_NAMES = {
    "crazing": "Crazing", "inclusion": "Inclusion", "patches": "Patches",
    "pitted_surface": "Pitted Surface", "rolled-in_scale": "Rolled-in Scale", "scratches": "Scratches",
}
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".bmp")
BLOCK_SIZE = 20
VAL_BLOCKS_PER_CLASS = 3
DEFAULT_SEEDS = (0, 1, 2)
RESIZE_FILTER = "BILINEAR"


class TestSetLockedError(PermissionError):
    """Raised when code outside the final-evaluation stage tries to read the locked test set."""


# ─── locked-test access control ──────────────────────────────────────────────
_lock_state = threading.local()


def _final_eval_active() -> bool:
    return getattr(_lock_state, "depth", 0) > 0


@contextlib.contextmanager
def final_evaluation_stage(reason: str, log_dir: Optional[Path] = None) -> Iterator[None]:
    """Only inside this context may the locked test set be read. Every entry is logged."""
    log_dir = log_dir or (v2_root() / "logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / "test_access.jsonl", "a") as f:
        f.write(json.dumps({"time": datetime.now().isoformat(), "reason": reason}) + "\n")
    _lock_state.depth = getattr(_lock_state, "depth", 0) + 1
    try:
        yield
    finally:
        _lock_state.depth -= 1


# ─── manifest ────────────────────────────────────────────────────────────────
def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_index(stem: str) -> int:
    nums = re.findall(r"\d+", stem)
    if not nums:
        raise ValueError(f"No numeric index in filename {stem!r}")
    return int(nums[-1])


def _annotation_labels(xml_path: Path) -> Optional[List[str]]:
    if not xml_path.exists():
        return None
    try:
        root = ET.parse(xml_path).getroot()
        return sorted({o.findtext("name", "").strip() for o in root.findall("object")})
    except ET.ParseError:
        return ["<unparseable>"]


def build_manifest(root: Optional[Path] = None) -> Dict:
    """Scan the real dataset folders and build a full per-file manifest (no assumptions)."""
    root = Path(root) if root else dataset_root()
    records = []
    for folder, role in (("train", "trainval"), ("validation", "locked_test")):
        img_root = root / folder / "images"
        if not img_root.exists():
            raise FileNotFoundError(f"Missing dataset folder: {img_root}")
        class_dirs = sorted(d for d in img_root.iterdir() if d.is_dir())
        for d in class_dirs:
            for p in sorted(d.iterdir()):
                if p.suffix.lower() not in IMAGE_EXTS:
                    continue
                rec = {
                    "rel_path": str(p.relative_to(root)),
                    "class": d.name,
                    "class_idx": CLASSES.index(d.name) if d.name in CLASSES else None,
                    "folder": folder,
                    "role": role,
                    "index": _file_index(p.stem),
                    "file_size": p.stat().st_size,
                    "sha256": _sha256(p),
                }
                try:
                    with Image.open(p) as im:
                        im.load()
                        rec.update(width=im.width, height=im.height, mode=im.mode, readable=True)
                except Exception as e:  # corrupt image
                    rec.update(width=None, height=None, mode=None, readable=False, error=str(e))
                rec["block"] = (rec["index"] - 1) // BLOCK_SIZE
                rec["group_id"] = f"{folder}:{d.name}:b{rec['block']:02d}"
                rec["annotation_labels"] = _annotation_labels(root / folder / "annotations" / f"{p.stem}.xml")
                records.append(rec)
    payload = json.dumps([{k: r[k] for k in ("rel_path", "class", "sha256")} for r in records], sort_keys=True)
    manifest_id = "neu-" + hashlib.sha256(payload.encode()).hexdigest()[:12]
    return {
        "manifest_id": manifest_id,
        "created_at": datetime.now().isoformat(),
        "dataset_root": str(root),
        "classes": CLASSES,
        "protocol": {
            "locked_test": "validation/images (all files)",
            "trainval_pool": "train/images (all files)",
            "group": f"contiguous file-index blocks of {BLOCK_SIZE} within class",
            "val_blocks_per_class": VAL_BLOCKS_PER_CLASS,
            "preprocessing": f"PIL convert('L') -> resize(s, s, {RESIZE_FILTER}) -> /255",
        },
        "records": records,
    }


def validate_manifest(manifest: Dict) -> Dict:
    recs = manifest["records"]
    checks: Dict = {}
    counts = {f: {c: 0 for c in CLASSES} for f in ("train", "validation")}
    unknown_classes = sorted({r["class"] for r in recs if r["class"] not in CLASSES})
    for r in recs:
        if r["class"] in CLASSES:
            counts[r["folder"]][r["class"]] += 1
    checks["total_images"] = len(recs)
    checks["counts"] = counts
    checks["unknown_class_folders"] = unknown_classes
    checks["unreadable"] = [r["rel_path"] for r in recs if not r["readable"]]
    dims = {}
    for r in recs:
        key = f"{r['width']}x{r['height']}:{r['mode']}"
        dims[key] = dims.get(key, 0) + 1
    checks["dimensions_modes"] = dims
    by_hash: Dict[str, List[str]] = {}
    for r in recs:
        by_hash.setdefault(r["sha256"], []).append(r["rel_path"])
    checks["exact_duplicates"] = [v for v in by_hash.values() if len(v) > 1]
    checks["missing_annotation"] = [r["rel_path"] for r in recs if r["annotation_labels"] is None]
    checks["annotation_label_mismatch"] = [
        {"file": r["rel_path"], "folder_class": r["class"], "annotation": r["annotation_labels"]}
        for r in recs if r["annotation_labels"] is not None and r["annotation_labels"] != [r["class"]]
    ]
    # Folder label must be among the annotated object names (extra objects = multi-defect image).
    checks["folder_label_absent_from_annotation"] = [
        m for m in checks["annotation_label_mismatch"] if m["folder_class"] not in m["annotation"]]
    group_of = {r["rel_path"]: r["group_id"] for r in recs}
    checks["duplicates_crossing_groups"] = [
        v for v in checks["exact_duplicates"] if len({group_of[p] for p in v}) > 1]
    idx_ranges = {}
    for f in ("train", "validation"):
        for c in CLASSES:
            ids = sorted(r["index"] for r in recs if r["folder"] == f and r["class"] == c)
            idx_ranges[f"{f}/{c}"] = [ids[0], ids[-1], len(ids), len(set(ids))] if ids else None
    checks["index_ranges"] = idx_ranges
    checks["warnings"] = {
        "exact_duplicates_within_one_group": len(checks["exact_duplicates"]) - len(checks["duplicates_crossing_groups"]),
        "multi_defect_annotations": len(checks["annotation_label_mismatch"]),
        "missing_annotation_files": len(checks["missing_annotation"]),
    }
    checks["ok"] = (
        not unknown_classes and not checks["unreadable"] and not checks["duplicates_crossing_groups"]
        and not checks["folder_label_absent_from_annotation"]
        and all(counts["train"][c] > 0 and counts["validation"][c] > 0 for c in CLASSES)
    )
    return checks


def save_manifest(manifest: Dict, out_dir: Optional[Path] = None) -> Path:
    out_dir = out_dir or (v2_root() / "manifests")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"dataset_manifest_{manifest['manifest_id']}.json"
    path.write_text(json.dumps(manifest, indent=1))
    (out_dir / "dataset_manifest_current.json").write_text(
        json.dumps({"manifest_id": manifest["manifest_id"], "path": path.name}, indent=1))
    return path


def load_manifest(out_dir: Optional[Path] = None) -> Dict:
    out_dir = out_dir or (v2_root() / "manifests")
    cur = json.loads((out_dir / "dataset_manifest_current.json").read_text())
    return json.loads((out_dir / cur["path"]).read_text())


# ─── blocked group splits ───────────────────────────────────────────────────
def make_split(manifest: Dict, seed: int, val_blocks_per_class: int = VAL_BLOCKS_PER_CLASS) -> Dict:
    """Assign whole index blocks of the train folder to train or val (stratified by class)."""
    rng = np.random.default_rng(seed)
    pool = [r for r in manifest["records"] if r["role"] == "trainval"]
    train, val, val_groups = [], [], []
    for c in CLASSES:
        groups = sorted({r["group_id"] for r in pool if r["class"] == c})
        chosen = set(rng.choice(groups, size=val_blocks_per_class, replace=False).tolist())
        val_groups += sorted(chosen)
        for r in pool:
            if r["class"] == c:
                (val if r["group_id"] in chosen else train).append(r["rel_path"])
    test = [r["rel_path"] for r in manifest["records"] if r["role"] == "locked_test"]
    body = {"train": sorted(train), "val": sorted(val), "test": sorted(test)}
    split_id = f"split-s{seed}-" + hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:10]
    return {
        "split_id": split_id, "seed": seed, "manifest_id": manifest["manifest_id"],
        "strategy": f"group-blocked (blocks of {BLOCK_SIZE} indices), {val_blocks_per_class} val blocks/class",
        "val_groups": val_groups, "counts": {k: len(v) for k, v in body.items()}, **body,
    }


def save_split(split: Dict, out_dir: Optional[Path] = None) -> Path:
    out_dir = out_dir or (v2_root() / "manifests" / "splits")
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{split['split_id']}.json"
    p.write_text(json.dumps(split, indent=1))
    (out_dir / f"current_seed{split['seed']}.json").write_text(json.dumps({"split_id": split["split_id"]}))
    return p


def load_split(seed: int, out_dir: Optional[Path] = None) -> Dict:
    out_dir = out_dir or (v2_root() / "manifests" / "splits")
    sid = json.loads((out_dir / f"current_seed{seed}.json").read_text())["split_id"]
    return json.loads((out_dir / f"{sid}.json").read_text())


def verify_split(split: Dict, manifest: Dict) -> Dict:
    """Overlap checks between train / val / locked test by path, hash and group."""
    by_path = {r["rel_path"]: r for r in manifest["records"]}
    sets = {k: set(split[k]) for k in ("train", "val", "test")}
    hashes = {k: {by_path[p]["sha256"] for p in v} for k, v in sets.items()}
    groups = {k: {by_path[p]["group_id"] for p in v} for k, v in sets.items()}
    res = {}
    for a, b in (("train", "val"), ("train", "test"), ("val", "test")):
        res[f"{a}_{b}"] = {
            "path_overlap": len(sets[a] & sets[b]),
            "hash_overlap": len(hashes[a] & hashes[b]),
            "group_overlap": len(groups[a] & groups[b]),
        }
    res["test_is_entire_validation_folder"] = sets["test"] == {
        r["rel_path"] for r in manifest["records"] if r["role"] == "locked_test"}
    res["union_covers_dataset"] = len(sets["train"] | sets["val"] | sets["test"]) == len(manifest["records"])
    res["ok"] = all(v["path_overlap"] == 0 and v["hash_overlap"] == 0 and v["group_overlap"] == 0
                    for k, v in res.items() if isinstance(v, dict)) and res["test_is_entire_validation_folder"] \
        and res["union_covers_dataset"]
    return res


# ─── image loading ───────────────────────────────────────────────────────────
def preprocess_image(path: Path, size: int) -> np.ndarray:
    with Image.open(path) as im:
        g = im.convert("L")
        if g.size != (size, size):
            g = g.resize((size, size), Image.Resampling.BILINEAR)
        return np.asarray(g, dtype=np.float64) / 255.0


@dataclass
class SplitArrays:
    X: np.ndarray            # (n, size, size) in [0, 1]
    y: np.ndarray            # (n,) int class index
    paths: List[str]


class NEUData:
    """Typed access to train / val / locked-test arrays for one split seed."""

    def __init__(self, seed: int, manifest: Optional[Dict] = None, root: Optional[Path] = None,
                 cache_dir: Optional[Path] = None, split: Optional[Dict] = None):
        self.manifest = manifest or load_manifest()
        self.root = Path(root) if root else Path(self.manifest["dataset_root"])
        self.split = split or load_split(seed)
        if self.split["manifest_id"] != self.manifest["manifest_id"]:
            raise ValueError("Split was built from a different dataset manifest.")
        self.seed = seed
        self._by_path = {r["rel_path"]: r for r in self.manifest["records"]}
        self.cache_dir = cache_dir or (v2_root() / "cache")

    def _arrays(self, paths: Sequence[str], size: int, tag: str) -> SplitArrays:
        key = hashlib.sha256(json.dumps([self.manifest["manifest_id"], list(paths), size, RESIZE_FILTER])
                             .encode()).hexdigest()[:16]
        cache = self.cache_dir / f"img_{tag}_{size}_{key}.npz"
        if cache.exists():
            z = np.load(cache, allow_pickle=False)
            return SplitArrays(z["X"], z["y"], list(paths))
        X = np.stack([preprocess_image(self.root / p, size) for p in paths])
        y = np.array([self._by_path[p]["class_idx"] for p in paths], dtype=int)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache, X=X, y=y)
        return SplitArrays(X, y, list(paths))

    def train(self, size: int) -> SplitArrays:
        return self._arrays(self.split["train"], size, "trainval")

    def val(self, size: int) -> SplitArrays:
        return self._arrays(self.split["val"], size, "trainval")

    def test(self, size: int) -> SplitArrays:
        if not _final_eval_active():
            raise TestSetLockedError(
                "The locked test set may only be read inside final_evaluation_stage(); "
                "model selection must use train/val only.")
        return self._arrays(self.split["test"], size, "lockedtest")

    def groups(self, which: str) -> np.ndarray:
        return np.array([self._by_path[p]["group_id"] for p in self.split[which]])


def adjacency_report(manifest: Dict, split: Dict, size: int = 64, root: Optional[Path] = None,
                     radius: int = 3) -> Dict:
    """For each val (and test) image find its most similar same-class TRAIN image and report how
    often it lies within ±radius file indices — a proxy for near-duplicate leakage."""
    root = Path(root) if root else Path(manifest["dataset_root"])
    by_path = {r["rel_path"]: r for r in manifest["records"]}

    def feats(paths):
        X = np.stack([preprocess_image(root / p, size).ravel() for p in paths])
        X = (X - X.mean(1, keepdims=True)) / (X.std(1, keepdims=True) + 1e-12)
        return X

    out = {}
    tr = split["train"]
    Xtr = feats(tr)
    ctr = np.array([by_path[p]["class"] for p in tr])
    itr = np.array([by_path[p]["index"] for p in tr])
    for which in ("val", "test"):
        ps = split[which]
        Xq = feats(ps)
        hits = []
        for i, p in enumerate(ps):
            m = ctr == by_path[p]["class"]
            j = np.argmax(Xtr[m] @ Xq[i])
            hits.append(abs(int(itr[m][j]) - by_path[p]["index"]) <= radius)
        out[which] = {"nn_within_radius_rate": float(np.mean(hits)), "n": len(ps)}
    out["radius"] = radius
    return out
