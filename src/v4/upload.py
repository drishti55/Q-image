"""Upload lab (/api/v4/upload): encode a user-supplied image with FRQI and NEQR on the real Qiskit encoder circuits,
reconstruct it (exact statevector + finite shots), and classify it with the frozen V4 FRQI and NEQR models.

Read-only with respect to all results: nothing is written to disk, nothing is trained or re-selected, and the locked test
set is not touched. The uploaded image is not part of NEU-DET, so predictions are illustrative; an out-of-distribution
score compares the image's similarity to the training set with the similarities seen among training images themselves.
"""
from __future__ import annotations

import io
from functools import lru_cache
from typing import Dict, List

import numpy as np
from PIL import Image

CLASSES = ["crazing", "inclusion", "patches", "pitted_surface", "rolled-in_scale", "scratches"]
RESOLUTIONS = (2, 4, 8, 16)
BITS = (2, 4, 8)
SHOTS = (100, 1000, 10000)
MAX_BYTES = 10 * 1024 * 1024


def load_upload(data: bytes) -> np.ndarray:
    """Bytes -> grayscale float image in [0, 1], centre-cropped to a square (NEU-DET images are square)."""
    if len(data) > MAX_BYTES:
        raise ValueError("image larger than 10 MB")
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"not a readable image ({e.__class__.__name__})")
    g = im.convert("L")
    w, h = g.size
    if min(w, h) < 2:
        raise ValueError("image too small")
    s = min(w, h)
    g = g.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
    return np.asarray(g, dtype=np.float64) / 255.0


def resize(img: np.ndarray, size: int) -> np.ndarray:
    """Same operation as src/v2/dataset.preprocess_image: 8-bit grayscale, bilinear resize, /255."""
    g = Image.fromarray(np.clip(np.round(img * 255), 0, 255).astype(np.uint8))
    if g.size != (size, size):
        g = g.resize((size, size), Image.Resampling.BILINEAR)
    return np.asarray(g, dtype=np.float64) / 255.0


def run_with_big_stack(fn, stack_mb: int = 256):
    """Run fn() in a thread with a large stack. Qiskit transpilation of deep encoder circuits recurses deeply and overflows the
    small default stack of worker threads (512 KB on macOS), which crashes the process."""
    import threading
    box = {}

    def target():
        try:
            box["value"] = fn()
        except BaseException as e:  # noqa: BLE001
            box["error"] = e
    old = threading.stack_size(stack_mb * 1024 * 1024)
    try:
        t = threading.Thread(target=target, name="upload-lab")
        t.start()
    finally:
        threading.stack_size(old)
    t.join()
    if "error" in box:
        raise box["error"]
    return box["value"]


def r3(a) -> List:
    return np.round(np.asarray(a, float), 3).tolist()


# ───────────────────────── encoding + reconstruction ─────────────────────────
def encode_and_reconstruct(img: np.ndarray, rep: str, res: int, bits: int, seed: int = 0) -> Dict:
    from src.frqi.encoder import FRQIEncoder
    from src.neqr.encoder import NEQREncoder
    from src.reconstruction.reconstructor import FRQIReconstructor, NEQRReconstructor
    from src.simulation.simulator import QuantumSimulator
    from src.v2.encoding_study import image_metrics, sample_counts
    from src.v2.qsim import circuit_resources

    x = resize(img, res)
    if rep == "FRQI":
        enc = FRQIEncoder(x)
        qc = enc.build_circuit()
        dec = FRQIReconstructor(enc.n_position_qubits, (res, res))
        scale, quant = 1.0, None
    else:
        mx = (1 << bits) - 1
        q = np.clip(np.round(x * mx), 0, mx).astype(int)
        enc = NEQREncoder(q, intensity_bits=bits)
        qc = enc.build_circuit()
        dec = NEQRReconstructor(enc.n_position_qubits, bits, (res, res))
        scale, quant = float(mx), q / mx
    sv = QuantumSimulator(seed=seed).run_statevector(qc)
    rng = np.random.default_rng(seed)
    outs = {"statevector": dec.reconstruct_from_statevector(sv["statevector"])["image"].astype(float) / scale}
    for s in SHOTS:
        counts = sample_counts(sv["probabilities"], s, qc.num_qubits, rng)
        outs[f"shots{s}"] = dec.reconstruct_from_counts(counts, shots=s)["image"].astype(float) / scale
    stats = enc.get_circuit_stats()
    circuit = {"n_qubits": int(qc.num_qubits), "gates_logical": int(stats["gates"]), "depth_logical": int(stats["depth"]),
               "gate_types_logical": stats["gate_types"]}
    if res <= 8:  # transpiling 16x16 circuits takes too long for an interactive request
        circuit.update({k: v for k, v in circuit_resources(qc).items() if k in ("gates_compiled", "depth_compiled", "cx_compiled")})
    modes = []
    for k, y in outs.items():
        m = image_metrics(x, y)
        modes.append({"mode": k, "label": "exact statevector" if k == "statevector" else f"{int(k[5:]):,} shots",
                      "image": r3(np.clip(y, 0, 1)), "mse": m["mse"], "psnr": m["psnr"], "ssim": m["ssim"],
                      "exact": bool(m["exact_match"])})
    return {"representation": rep, "resolution": res, "bits": bits if rep == "NEQR" else None,
            "input": r3(x), "quantised": r3(quant) if quant is not None else None, "circuit": circuit, "modes": modes}


REPRESENTATIONS = ("FRQI", "NEQR")


def _encode_pair(img: np.ndarray, res: int, bits: int, reps=REPRESENTATIONS) -> List[Dict]:
    return [encode_and_reconstruct(img, r, res, bits) for r in reps]


_POOL = None


def encode_both(img: np.ndarray, res: int, bits: int, timeout: float = 300.0, reps=REPRESENTATIONS) -> List[Dict]:
    """Run the Qiskit encoding/simulation in a separate worker process. Building and simulating large multi-controlled
    circuits in the same process as the NumPy/scikit-learn classifier occasionally crashed natively; a worker process
    isolates that, so a crash returns an error instead of taking the API server down."""
    global _POOL
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor
    from concurrent.futures.process import BrokenProcessPool
    if _POOL is None:
        _POOL = ProcessPoolExecutor(max_workers=1, mp_context=mp.get_context("spawn"))
    try:
        return _POOL.submit(_encode_pair, img, res, bits, tuple(reps)).result(timeout=timeout)
    except BrokenProcessPool:
        _POOL = None
        raise RuntimeError("the encoding worker crashed; please try again (smaller resolution is faster)")
    finally:
        import os
        if os.environ.get("QIL_LITE") == "1" and _POOL is not None:  # hosted demo: free the worker's memory after each upload
            _POOL.shutdown(wait=True)
            _POOL = None


# ───────────────────────── classification with the frozen V4 models ─────────────────────────
@lru_cache(maxsize=2)
def frozen(rep: str) -> Dict:
    """Frozen V4 headline model for FRQI or NEQR (seed 0 checkpoint) + training density matrices + OOD reference."""
    import json
    import joblib
    from src.v2.dataset import NEUData
    from src.v4.api import _root
    from src.v4.models import _sha, mixed_states
    D = json.loads((_root() / "aggregates" / "v4_results.json").read_text())
    g = D["headlines"][rep.lower()]
    eid = D["groups"][g]["experiment_ids"][0]
    if rep.upper() == "FRQI":
        # same frozen checkpoint as the live walkthrough: reuse its training density matrices instead of building a
        # second ~140 MB copy
        from src.v4.api import _frqi_model
        W = _frqi_model()
        assert W["eid"] == eid
        est, tr, R, pur = W["est"], W["tr"], W["R"], W["purity"]
    else:
        est = joblib.load(_root() / "experiments" / eid / "model" / "estimator.joblib")
        tr = NEUData(0, cache_dir=_root() / "cache").train(est.params["image_size"])
        if _sha(tr.X) != est._xtr_sha:
            raise RuntimeError("training images do not match the frozen checkpoint")
        est._xtr = np.asarray(tr.X, float)
        R = mixed_states(est._xtr, est.params)
        pur = np.einsum("ij,ij->i", R, R)
    Kn = (R @ R.T) / np.sqrt(np.outer(pur, pur))
    np.fill_diagonal(Kn, -np.inf)
    nn = Kn.max(axis=1)                                   # each training image's most similar *other* training image
    return {"group": g, "eid": eid, "est": est, "R": R, "pur": pur, "tr": tr, "nn_ref": np.sort(nn),
            "test_accuracy": D["groups"][g]["test_accuracy"]}


def classify(img: np.ndarray, rep: str) -> Dict:
    from src.v4.models import mixed_states, stretch
    M = frozen(rep)
    est, p = M["est"], M["est"].params
    x = resize(img, p["image_size"])
    r = mixed_states(x[None], p)
    k = (r @ M["R"].T)[0].astype(float)
    kn = k / np.sqrt(float(np.dot(r[0], r[0])) * M["pur"])
    dec = est.svm.decision_function(k[None])[0]
    pred = int(est.svm.predict(k[None])[0])
    order = np.argsort(-kn)[:5]
    nn = float(kn.max())
    pct = float(np.searchsorted(M["nn_ref"], nn) / len(M["nn_ref"]) * 100)
    xs = stretch(x[None])[0] if p["norm"] == "stretch" else x
    from src.v4.api import _small
    return {"representation": rep, "group": M["group"], "experiment_id": M["eid"], "params": p,
            "locked_test_accuracy": M["test_accuracy"], "input": _small(xs, 64),
            "prediction": CLASSES[pred], "decision": [{"class": c, "score": float(s)} for c, s in zip(CLASSES, dec)],
            "class_similarity": [{"class": c, "mean": float(kn[M["tr"].y == j].mean())} for j, c in enumerate(CLASSES)],
            "nearest": [{"class": CLASSES[int(M["tr"].y[i])], "similarity": float(kn[i]), "thumb": _small(M["tr"].X[i], 40)} for i in order],
            "ood": {"max_similarity": nn, "percentile_vs_training": pct,
                    "unusual": pct < 1.0,
                    "note": "Compares this image's best match in the training set with how closely training images match each other."}}
