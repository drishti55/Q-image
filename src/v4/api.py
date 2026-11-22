"""Protocol V4 API (/api/v4). Serves results/qml_v4 (read-only) plus a live, read-only walkthrough of the frozen
V4 FRQI model on one locked-test image. Nothing here trains, selects or writes results; the live prediction is
checked against the prediction saved by the single locked-test evaluation."""
from __future__ import annotations

import csv
import json
import os
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from src.v2.paths import DEFAULT_V4_ROOT, dataset_root

router = APIRouter(prefix="/api/v4", tags=["protocol-v4"])
CLASSES = ["crazing", "inclusion", "patches", "pitted_surface", "rolled-in_scale", "scratches"]

# Lite mode (QIL_LITE=1, used by the free 512 MB hosted demo): features that need PyTorch or NEQR's 256×256 training
# density matrices are switched off with an explicit message. Everything else is unchanged.
LITE = os.environ.get("QIL_LITE") == "1"
LITE_MSG = ("not available in the hosted demo: it needs more memory than the free server has (PyTorch / NEQR density "
            "matrices). Run Q-ImageLab locally to use it.")


def _not_lite(what: str):
    if LITE:
        raise HTTPException(503, f"{what} is {LITE_MSG}")


def _root() -> Path:
    env = os.environ.get("QIL_RESULTS_V4")
    return Path(env).expanduser().resolve() if env else DEFAULT_V4_ROOT


def _read(p: Path):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def _need(d, msg):
    if d is None:
        raise HTTPException(404, msg)
    return d


@router.get("/health")
def health():
    r = _root()
    return {"api": "qimagelab-v4", "results_present": (r / "aggregates" / "v4_results.json").exists(),
            "reconstruction_present": (r / "reconstruction_full" / "summary.json").exists(),
            "per_image_index_present": (r / "aggregates" / "per_image_predictions.json").exists()}


@router.get("/results")
def results():
    return _need(_read(_root() / "aggregates" / "v4_results.json"), "V4 results not built — run scripts/v4/analyze_v4.py")


@router.get("/versions")
def versions():
    """Headline locked-test numbers of every protocol, read from the saved result files (V2 analysis.json,
    V3 v3_results.json, V4 v4_results.json). V0 has no locked test and is listed without a comparable number."""
    from src.v2.paths import DEFAULT_V2_ROOT, DEFAULT_V3_ROOT
    v4 = _need(_read(_root() / "aggregates" / "v4_results.json"), "V4 results not built — run scripts/v4/analyze_v4.py")
    a2 = (_read(DEFAULT_V2_ROOT / "aggregates" / "analysis.json") or {}).get("selected") or {}
    r3 = _read(DEFAULT_V3_ROOT / "aggregates" / "v3_results.json") or {}
    g3 = {g["group"]: g for g in r3.get("groups", [])}
    G, H = v4["groups"], v4["headlines"]

    def m(name, acc, kind, group, note=""):
        return {"name": name, "type": kind, "group": group, "test_accuracy": acc, "note": note} if acc else None

    def best(items, pred):
        c = [(k, v) for k, v in items if pred(k, v)]
        return max(c, key=lambda kv: kv[1]["test_accuracy"]["mean"]) if c else (None, None)

    out = [{"id": "V0", "comparable": False, "title": "First prototype", "link": "/historical-v0",
            "what": "Small ad-hoc runs on a handful of images per class, random splits, no locked test set.",
            "models": []}]
    if a2:
        A = a2.items()
        kq, vq = best(A, lambda k, v: str(v.get("category", "")).startswith(("2.", "3.")))
        kh, vh = best(A, lambda k, v: str(v.get("category", "")).startswith("4."))
        kc, vc = best(A, lambda k, v: str(v.get("category", "")).startswith("1."))
        out.append({"id": "V2", "comparable": True, "title": "Whole-image FRQI / NEQR + feature baselines", "link": "/quantum-vs-classical",
                    "what": "Each whole image (8×8 / 16×16) encoded as one FRQI or NEQR state; quantum kernels on pixels, PCA and CNN features; first locked test set.",
                    "frqi": a2.get("E1b-frqi8-qkc-scaled", {}).get("test_accuracy"), "neqr": a2.get("E2-neqr16-b4-qkc", {}).get("test_accuracy"),
                    "models": [x for x in [
                        m("FRQI, whole image 8×8", a2.get("E1b-frqi8-qkc-scaled", {}).get("test_accuracy"), "quantum", "E1b-frqi8-qkc-scaled"),
                        m("NEQR, whole image 16×16 (4-bit)", a2.get("E2-neqr16-b4-qkc", {}).get("test_accuracy"), "quantum", "E2-neqr16-b4-qkc"),
                        m("Best quantum on pixel features", vq and vq["test_accuracy"], "quantum", kq, vq and vq.get("model_name", "")),
                        m("Best hybrid (CNN features + quantum kernel)", vh and vh["test_accuracy"], "hybrid", kh, vh and vh.get("model_name", "")),
                        m("Best classical", vc and vc["test_accuracy"], "classical", kc, vc and vc.get("model_name", ""))] if x]})
    if g3:
        h3 = r3.get("headlines", {})
        T = g3.items()
        kc, vc = best(T, lambda k, v: v.get("category") == "classical_control")
        out.append({"id": "V3", "comparable": True, "title": "Texture features (LBP + GLCM) into quantum kernels", "link": "/quantum-v3",
                    "what": "Hand-crafted texture features compressed with PCA and fed to quantum kernels and VQCs; FRQI / NEQR re-tuned on validation.",
                    "frqi": h3.get("frqi", {}).get("test_accuracy"), "neqr": h3.get("neqr", {}).get("test_accuracy"),
                    "models": [x for x in [
                        m("FRQI, whole image 8×8 (re-tuned)", h3.get("frqi", {}).get("test_accuracy"), "quantum", h3.get("frqi", {}).get("group")),
                        m("NEQR, whole image 16×16 (re-tuned)", h3.get("neqr", {}).get("test_accuracy"), "quantum", h3.get("neqr", {}).get("group")),
                        m("Best quantum (texture PCA-12 kernel)", h3.get("pure_quantum", {}).get("test_accuracy"), "quantum", h3.get("pure_quantum", {}).get("group"), h3.get("pure_quantum", {}).get("display_name", "")),
                        m("Variational classifier (VQC)", h3.get("vqc", {}).get("test_accuracy"), "quantum", h3.get("vqc", {}).get("group"), h3.get("vqc", {}).get("display_name", "")),
                        m("Best classical", vc and vc["test_accuracy"], "classical", kc, vc and vc.get("display_name", ""))] if x]})
    cmp = {c["name"]: c for c in v4.get("comparisons", [])}
    out.append({"id": "V4", "comparable": True, "latest": True, "title": "Patch-ensemble FRQI / NEQR (mixed-state kernel)", "link": "/quantum-v4",
                "what": "Every image is cut into small patches; each patch is FRQI- or NEQR-encoded and the image becomes the mixture of its patch states. Images are compared with the swap-test kernel Tr(ρσ).",
                "frqi": G[H["frqi"]]["test_accuracy"], "neqr": G[H["neqr"]]["test_accuracy"],
                "frqi_group": H["frqi"], "neqr_group": H["neqr"],
                "frqi_qubits": (G[H["frqi"]].get("quantum") or {}).get("n_qubits"), "neqr_qubits": (G[H["neqr"]].get("quantum") or {}).get("n_qubits"),
                "frqi_per_seed": G[H["frqi"]].get("per_seed_test_accuracy"), "neqr_per_seed": G[H["neqr"]].get("per_seed_test_accuracy"),
                "control": G.get("V4-patchmom-rbfsvm", {}).get("test_accuracy"),
                "comparisons": [{"name": c["name"], "diff": c["diff"], "ci95": c["ci95"], "p_holm": c["p_holm"]} for c in cmp.values()],
                "models": [x for x in [
                    m("FRQI patch ensemble (8×8 patches)", G[H["frqi"]]["test_accuracy"], "quantum", H["frqi"]),
                    m("NEQR patch ensemble (4×4 patches)", G[H["neqr"]]["test_accuracy"], "quantum", H["neqr"]),
                    *[m(f"{'FRQI' if 'frqi' in g else 'NEQR'} patch ensemble ({g.split('-p')[-1]}×{g.split('-p')[-1]} patches)", G[g]["test_accuracy"], "quantum", g)
                      for g in G if g.startswith("V4-") and g not in (H["frqi"], H["neqr"], "V4-patchmom-rbfsvm")],
                    m("Classical RBF-SVM on the same patches", G.get("V4-patchmom-rbfsvm", {}).get("test_accuracy"), "classical", "V4-patchmom-rbfsvm")] if x]})
    return {"versions": out, "n_test": 360, "execution": "Exact noiseless CPU simulation (no quantum hardware).",
            "same_test_set": "V2, V3 and V4 use the same dataset manifest, splits, seeds and 360-image locked test set."}


@lru_cache(maxsize=1)
def _index():
    return _need(_read(_root() / "aggregates" / "per_image_predictions.json"), "run scripts/v4/build_per_image_index.py")


@router.get("/images")
def images():
    """The 360 locked-test images with how many of the 163 selected models (x 3 seeds) classify each correctly."""
    ix = _index()
    out = []
    for img, v in ix["images"].items():
        preds = [p for ps in v["preds"].values() for p in ps]
        out.append({"image": img, "class": CLASSES[v["y_true"]], "frac_correct": float(np.mean([p == v["y_true"] for p in preds]))})
    return {"images": out, "n_models": len(ix["models"])}


@router.get("/image-models")
def image_models(image: str):
    ix = _index()
    v = ix["images"].get(image)
    if v is None:
        raise HTTPException(404, "not a locked-test image")
    rows = [{**m, "preds": v["preds"][m["id"]], "n_correct": sum(p == v["y_true"] for p in v["preds"][m["id"]])} for m in ix["models"]]
    return {"image": image, "y_true": v["y_true"], "classes": CLASSES, "models": rows}


@router.get("/all-models")
def all_models():
    """Every selected model of V2, V3 and V4 (163) with its locked-test accuracy (mean over seeds), copied from the
    per-image index built from saved predictions. Nothing is re-run."""
    ix = _index()
    keep = ("id", "protocol", "name", "family", "kind", "category", "n_qubits", "test_accuracy")
    return {"models": [{k: m.get(k) for k in keep} for m in ix["models"]], "n_test": len(ix["images"])}


@router.get("/families")
def model_families():
    """QKC / PQK / VQC / hybrid / RBF-SVM representatives (best validation F1) with metrics, architecture, confusion
    matrices from saved predictions, and matched quantum-vs-classical pairs. Read-only (src/v4/learning.py)."""
    from src.v2.paths import DEFAULT_V3_ROOT
    from src.v4 import learning
    try:
        return learning.families(DEFAULT_V3_ROOT, _root())
    except (OSError, ValueError, KeyError) as e:
        raise HTTPException(404, f"V3 results or prediction index missing ({e.__class__.__name__})")


# ───────────────────────── live walkthrough of the frozen V4 FRQI model ─────────────────────────
def frozen_rho_path(eid: str, xtr_sha: str) -> Path:
    """File of the frozen FRQI model's training density matrices (float32, one row per training image)."""
    return _root() / "cache" / f"frozen_rho_{eid}_{xtr_sha[:16]}.npy"


@lru_cache(maxsize=1)
def _frqi_model():
    from src.v2.dataset import NEUData
    from src.v4.models import _sha, mixed_states
    D = _need(_read(_root() / "aggregates" / "v4_results.json"), "V4 results not built")
    g = D["headlines"]["frqi"]
    eid = D["groups"][g]["experiment_ids"][0]  # seed 0
    est = joblib.load(_root() / "experiments" / eid / "model" / "estimator.joblib")
    tr = NEUData(0, cache_dir=_root() / "cache").train(est.params["image_size"])
    if _sha(tr.X) != est._xtr_sha:
        raise HTTPException(500, "training images do not match the frozen checkpoint")
    est._xtr = np.asarray(tr.X, float)
    pre = frozen_rho_path(eid, est._xtr_sha)
    # Precomputed at build time by scripts/v4/precompute_frozen.py (hosted demo): memory-mapped, so loading it needs no
    # temporary memory. Otherwise computed here (identical values).
    R = np.load(pre, mmap_mode="r") if pre.exists() else mixed_states(est._xtr, est.params)
    saved = {}
    with open(_root() / "experiments" / eid / "predictions.csv", newline="") as f:
        for row in csv.DictReader(f):
            if row["split"] == "test":
                saved[row["image"]] = int(row["y_pred"])
    return {"group": g, "eid": eid, "est": est, "R": R, "tr": tr, "saved": saved,
            "purity": np.einsum("ij,ij->i", R, R)}


def _small(img, s):
    from PIL import Image
    return (np.asarray(Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).resize((s, s), Image.Resampling.BILINEAR)) / 255.0).round(3).tolist()


@router.get("/pipeline")
def pipeline(image: str = Query(..., description="locked-test image rel_path")):
    from src.v2.dataset import preprocess_image
    from src.v4.models import mixed_states, patches, stretch
    M = _frqi_model()
    if image not in M["saved"]:
        raise HTTPException(404, "not a locked-test image")
    est, p = M["est"], M["est"].params
    root = dataset_root()
    orig = preprocess_image(root / image, 128)
    x = preprocess_image(root / image, p["image_size"])
    xs = stretch(x[None])[0] if p["norm"] == "stretch" else x
    P = patches(xs[None], p["patch"], p["stride"])[0]                         # (n_patches, p*p)
    theta = P * (np.pi / 2) * p["angle_scale"]
    r = mixed_states(x[None], p)                                             # (1, D^2)
    k = (r @ M["R"].T)[0].astype(float)                                       # Tr(rho_x rho_train) for all 1,080 train images
    knorm = k / np.sqrt(np.einsum("ij,ij->i", r, r)[0] * M["purity"])        # normalised for display
    dec = est.svm.decision_function(k[None])[0]
    pred = int(est.svm.predict(k[None])[0])
    order = np.argsort(-knorm)[:6]
    tr = M["tr"]
    y_true = CLASSES.index(image.split("/")[2])
    s = int(np.sqrt(len(theta[0])))
    rho_diag_n = 2 * s * s
    return {
        "image": image, "y_true": y_true, "classes": CLASSES, "model_group": M["group"], "experiment_id": M["eid"],
        "params": p, "n_qubits_per_patch": 2 * (p["patch"].bit_length() - 1) + 1,
        "original128": orig.round(3).tolist(), "resized": x.round(3).tolist(), "stretched": xs.round(3).tolist(),
        "patch_grid": {"n": int(len(P)), "per_side": int(round(np.sqrt(len(P)))), "patch": p["patch"], "stride": p["stride"]},
        "theta": theta.round(4).tolist(),
        "state_dim": rho_diag_n,
        "kernel": {"top": [{"train_image": tr.paths[i], "class": CLASSES[int(tr.y[i])], "similarity": float(knorm[i]),
                            "thumb": _small(tr.X[i], 32)} for i in order],
                   "class_mean": {c: float(knorm[tr.y == j].mean()) for j, c in enumerate(CLASSES)},
                   "n_train": int(len(k))},
        "svm": {"decision": dec.round(4).tolist(), "decision_shape": "one-vs-rest scores (sklearn ovr)",
                "n_support": int(est.svm.support_.size)},
        "prediction": pred, "saved_prediction": M["saved"][image], "matches_saved_prediction": pred == M["saved"][image],
    }


# ───────────────────────── full reconstruction study ─────────────────────────
@router.get("/reconstruction/summary")
def recon_summary():
    return _need(_read(_root() / "reconstruction_full" / "summary.json"),
                 "full reconstruction study not finished — run scripts/v4/chain_recon.sh")


@lru_cache(maxsize=1 if LITE else 24)
def _recon(record: str):
    d = _root() / "reconstruction_full" / record
    z = np.load(d / "reconstructions.npz")
    return {m: z[m] for m in z.files}, _read(d / "metrics.json")


@router.get("/reconstruction/image")
def recon_image(record: str, i: int | None = None, image: str | None = None):
    from src.v2.dataset import preprocess_image
    if "/" in record or ".." in record or not (_root() / "reconstruction_full" / record).is_dir():
        raise HTTPException(404, "unknown record")
    arrs, met = _recon(record)
    if image is not None:
        i = next((r["i"] for r in met["per_image"] if r["image"] == image), None)
    if i is None or not 0 <= i < len(met["per_image"]):
        raise HTTPException(404, "image index out of range")
    row = met["per_image"][i]
    cfg = _read(_root() / "reconstruction_full" / record / "config.json")
    orig = preprocess_image(dataset_root() / row["image"], cfg["resolution"])
    return {"record": record, "config": cfg, "row": row, "original": orig.round(4).tolist(),
            "modes": {m: a[i].astype(float).round(4).tolist() for m, a in arrs.items()}}


# ───────────────────────── upload lab: any image → FRQI / NEQR encoding + frozen V4 classifiers ─────────────────────────
@router.post("/upload")
async def upload(file: UploadFile = File(...), resolution: int = Form(8), bits: int = Form(4),
                 representations: str = Form("FRQI,NEQR")):
    """Encode an uploaded image with FRQI and/or NEQR (real Qiskit circuits, statevector + 100/1,000/10,000 shots), and
    classify it with the matching frozen V4 models. Nothing is saved; the locked test set is not used."""
    from src.v4 import upload as up
    reps = [r for r in up.REPRESENTATIONS if r in {x.strip().upper() for x in representations.split(",")}]
    if not reps or len(reps) != len({x.strip() for x in representations.split(",") if x.strip()}):
        raise HTTPException(422, "representations must be FRQI, NEQR or FRQI,NEQR")
    if resolution not in up.RESOLUTIONS:
        raise HTTPException(422, f"resolution must be one of {up.RESOLUTIONS}")
    if LITE and resolution > 8:
        raise HTTPException(422, f"In the hosted demo the upload lab encodes up to 8×8 (larger circuits are {LITE_MSG})")
    if bits not in up.BITS:
        raise HTTPException(422, f"bits must be one of {up.BITS}")
    try:
        img = up.load_upload(await file.read())
    except ValueError as e:
        raise HTTPException(422, str(e))
    import anyio

    cls_reps = [r for r in reps if not (LITE and r == "NEQR")]

    def work():
        return up.encode_both(img, resolution, bits, reps=reps), [up.classify(img, r) for r in cls_reps]
    try:
        enc, cls = await anyio.to_thread.run_sync(work)
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    return {"filename": file.filename, "original": _small(img, 128), "original_size": int(img.shape[0]),
            "encodings": enc, "classifications": cls,
            **({"note": f"NEQR classification is {LITE_MSG}"} if LITE and "NEQR" in reps else {}),
            "execution": "Exact noiseless CPU simulation of real Qiskit FRQI/NEQR circuits (no quantum hardware). Nothing is saved.",
            "caveat": "Uploaded images are not part of NEU-DET; the frozen models only know six steel-defect classes, so any image gets one of them."}


# ───────────────────────── CNN Feature Studio (frozen MobileNetV3, read-only) ─────────────────────────
# torch runs in a separate worker process (src/v4/cnn_worker.py) that never imports Qiskit: once Qiskit-Aer has run in a
# process, its bundled OpenMP runtime and torch's can deadlock or segfault each other (macOS). The worker stays alive so
# the network and cached features are loaded once; it is restarted if it dies.
import threading  # noqa: E402

_CNN = {"proc": None, "lock": threading.Lock()}


def _cnn_call(fn: str, *args):
    _not_lite("The CNN feature studio")
    import subprocess
    import sys
    root = Path(__file__).resolve().parents[2]
    with _CNN["lock"]:
        for attempt in (0, 1):
            p = _CNN["proc"]
            if p is None or p.poll() is not None:
                env = {**os.environ, "PYTHONPATH": str(root)}
                p = _CNN["proc"] = subprocess.Popen([sys.executable, "-m", "src.v4.cnn_worker"], cwd=root, env=env, text=True,
                                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            try:
                p.stdin.write(json.dumps({"fn": fn, "args": list(args)}) + "\n")
                p.stdin.flush()
                line = p.stdout.readline()
            except (BrokenPipeError, OSError):
                line = ""
            if line:
                r = json.loads(line)
                if r["ok"]:
                    return r["result"]
                raise HTTPException(404 if r["kind"] == "KeyError" else 500, r["error"])
            p.kill()
            _CNN["proc"] = None
    raise HTTPException(500, "CNN worker process failed")


@router.get("/cnn/images")
def cnn_images():
    return _cnn_call("images")


@router.get("/cnn/features")
def cnn_features(image: str = Query(..., description="train-folder image rel_path")):
    """Real MobileNetV3 feature maps, the 576-d vector and its seed-0 PCA projection for one train-folder image."""
    return _cnn_call("analyse", image)


@router.get("/hybrid-pipeline")
def hybrid_pipeline(image: str = Query(..., description="locked-test image rel_path")):
    """One locked-test image through frozen MobileNetV3 → PCA-8 → product-RY kernel, with the saved predictions of the
    best V2 hybrid model (E5-mnv3pca8-qkc-product_ry). Read-only."""
    return _cnn_call("hybrid", image)


# ───────────────────────── dataset gallery (all 1,800 NEU-DET images) ─────────────────────────
@lru_cache(maxsize=1)
def _dataset_index():
    """Every image of the frozen dataset manifest with its class, folder and role in the seed-0 split (read-only)."""
    from src.v2.paths import DEFAULT_V2_ROOT
    man_dir = DEFAULT_V2_ROOT / "manifests"
    cur = _need(_read(man_dir / "dataset_manifest_current.json"), "dataset manifest missing (run scripts/v2/phase1_data_protocol.py)")
    man = _need(_read(Path(cur["path"]) if Path(cur["path"]).is_absolute() else man_dir / Path(cur["path"]).name), "dataset manifest file missing")
    split_ptr = _read(man_dir / "splits" / "current_seed0.json") or {}
    split = _read(man_dir / "splits" / f"{split_ptr.get('split_id', '')}.json") or {}
    role = {p: r for r in ("train", "val", "test") for p in split.get(r, [])}
    pix = _read(_root() / "aggregates" / "per_image_predictions.json") or {}
    frac = {}
    for img, v in (pix.get("images") or {}).items():
        preds = [p for ps in v["preds"].values() for p in ps]
        frac[img] = float(np.mean([p == v["y_true"] for p in preds])) if preds else None
    recs = sorted(man["records"], key=lambda r: (r["class_idx"], r["folder"] != "train", r["index"]))
    images = [{"path": r["rel_path"], "name": Path(r["rel_path"]).name, "class": r["class"], "folder": r["folder"],
               "split_seed0": role.get(r["rel_path"]), "index": r["index"], "block": r["block"], "sha256": r["sha256"],
               "width": r["width"], "height": r["height"], "frac_correct": frac.get(r["rel_path"])} for r in recs]
    return {"manifest_id": man["manifest_id"], "classes": man["classes"], "n": len(images), "split_id": split.get("split_id"),
            "n_models": len(pix.get("models") or []), "images": images, "allowed": {r["rel_path"] for r in recs}}


@router.get("/dataset")
def dataset():
    """All NEU-DET images from the frozen manifest (class, folder, seed-0 split role, and for locked-test images the
    fraction of the 163 selected models x 3 seeds that classify it correctly)."""
    d = _dataset_index()
    return {k: v for k, v in d.items() if k != "allowed"}


@router.get("/dataset/image")
def dataset_image(path: str = Query(..., description="rel_path from /api/v4/dataset")):
    """Serve one dataset image. Only paths listed in the frozen manifest are served."""
    from fastapi.responses import FileResponse
    if path not in _dataset_index()["allowed"]:
        raise HTTPException(404, "not a dataset image")
    p = dataset_root() / path
    if not p.is_file():
        raise HTTPException(404, "image file missing")
    return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})
