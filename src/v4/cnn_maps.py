"""CNN Feature Studio (read-only): what the frozen MobileNetV3-small does to one NEU-DET train-folder image, and the
exact features the Protocol V2 hybrid models received.

Everything is computed live from the real network and the real cached vectors; nothing is trained, selected or saved.
  * feature maps: outputs of model.features[i] for the selected image (same preprocessing as src/v2/cnn.py)
  * 576-d vector: global average pool of model.features[12], checked against the cached vector used in training
  * PCA: StandardScaler -> PCA(k) fitted on the seed-0 train split, i.e. the VectorFeaturizer of the V2 hybrids
Only train-folder images are offered; the locked-test folder is not used here.
"""
from __future__ import annotations

import json
from functools import lru_cache

import numpy as np

STAGES = [  # (index into model.features, label, what it is)
    (0, "Stem convolution", "First 3×3 convolution (stride 2) + batch-norm + hard-swish. Responds to edges and local contrast."),
    (3, "Early block", "Inverted-residual block 3. Combines edges into small textures and blobs."),
    (8, "Intermediate block", "Inverted-residual block 8 (with squeeze-and-excitation). Larger texture patterns."),
    (12, "Final 1×1 convolution", "576 channels at 7×7. Their spatial average is the 576-d feature vector."),
]
MAP_SIZE = 56
PCA_KS = (4, 6, 8)
CLASSES = ["crazing", "inclusion", "patches", "pitted_surface", "rolled-in_scale", "scratches"]


@lru_cache(maxsize=1)
def _state():
    from src.v2.cnn import FrozenMobileNetV3Source
    from src.v2.features import VectorFeaturizer
    from src.v2.providers import neu
    src = FrozenMobileNetV3Source()
    (Ftr, ytr, ptr), (Fva, yva, pva) = src.train_val_vectors(0)
    d = neu(0)
    fz = {k: VectorFeaturizer(k=k, random_state=0).fit(Ftr) for k in PCA_KS}
    cached = {p: F for p, F in zip(list(ptr) + list(pva), np.concatenate([Ftr, Fva]))}
    split = {**{p: "train" for p in ptr}, **{p: "val" for p in pva}}
    S = fz[max(PCA_KS)]._z(Ftr)  # PCA scores of the train split; PC1/PC2 are identical for every k (full SVD)
    return {"src": src, "data": d, "fz": fz, "cached": cached, "split": split, "Ftr": Ftr, "ytr": np.asarray(ytr), "S": S, "train_paths": list(ptr)}


def images(per_class: int = 12):
    st = _state()
    by = {c: [] for c in CLASSES}
    for p, s in sorted(st["split"].items()):
        c = CLASSES[st["data"]._by_path[p]["class_idx"]]
        if len(by[c]) < per_class:
            by[c].append({"image": p, "split": s})
    return {"classes": CLASSES, "images": by, "n_available": len(st["split"])}


def _png(a: np.ndarray, s: int) -> str:
    """Min-max normalise one 2-D array and return it as a grayscale PNG data URL (s×s, bilinear)."""
    import base64
    import io
    from PIL import Image
    lo, hi = float(a.min()), float(a.max())
    z = (a - lo) / (hi - lo) if hi > lo else np.zeros_like(a)
    im = Image.fromarray((z * 255).astype(np.uint8))
    if im.size[0] != s:
        im = im.resize((s, s), Image.Resampling.BILINEAR)
    b = io.BytesIO()
    im.save(b, format="PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def _forward(path):
    """Grayscale image, network input tensor and the outputs of the STAGES layers for one image file."""
    import torch
    from PIL import Image
    st = _state()
    src = st["src"]
    m, tf = src.model(), src.weights.transforms()
    with Image.open(path) as im:
        gray = np.asarray(im.convert("L"), float) / 255.0
        x = tf(im.convert("L").convert("RGB"))[None]
    keep = {i for i, _, _ in STAGES}
    outs = {}
    with torch.no_grad():
        h = x
        for i, layer in enumerate(m.features):
            h = layer(h)
            if i in keep:
                outs[i] = h[0].numpy()
    return gray, x, outs


def _stages(outs, top=None):
    """Feature maps per stage, channels sorted by mean activation (all of them unless `top` is given)."""
    stages = []
    for i, label, what in STAGES:
        A = outs[i]
        means = A.mean(axis=(1, 2))
        order = np.argsort(-means)[:top] if top else np.argsort(-means)
        stages.append({"layer": i, "label": label, "what": what, "shape": list(A.shape),
                       "channels": [{"channel": int(c), "mean_activation": round(float(means[c]), 4),
                                     "map": _png(A[c], min(MAP_SIZE, A.shape[1])), "size": int(A.shape[1])} for c in order]})
    return stages


def analyse(image: str):
    st = _state()
    if image not in st["split"]:
        raise KeyError("not a train-folder image of the seed-0 train/val split")
    d = st["data"]
    src = st["src"]
    gray, x, outs = _forward(d.root / image)
    vec = outs[12].mean(axis=(1, 2))
    stages = _stages(outs)
    inp = x[0].numpy().mean(axis=0)  # ImageNet-normalised input (channels identical for a gray image)
    pca = []
    for k in PCA_KS:
        f = st["fz"][k]
        pca.append({"k": k, "explained_variance_ratio": [round(float(v), 4) for v in f._pca.explained_variance_ratio_],
                    "scores_standardised": [round(float(v), 4) for v in f.transform(vec[None], "standard")[0]],
                    "angles_rad": [round(float(v), 4) for v in f.transform(vec[None], "angle")[0]]})
    S, me = st["S"], st["fz"][max(PCA_KS)]._z(vec[None])[0]
    cached = st["cached"].get(image)
    return {
        "image": image, "class": CLASSES[d._by_path[image]["class_idx"]], "split": st["split"][image],
        "network": src.describe(), "load_info": src.load_info,
        "original": _png(gray, 128), "model_input": _png(inp, 112), "model_input_shape": list(x.shape[1:]),
        "stages": stages,
        "vector": [round(float(v), 4) for v in vec],
        "vector_stats": {"dim": int(vec.size), "min": float(vec.min()), "max": float(vec.max()), "mean": float(vec.mean()),
                         "nonpositive_fraction": float((vec <= 0).mean())},
        "cache_check": {"max_abs_diff": float(np.abs(vec - cached).max()) if cached is not None else None,
                        "note": "difference between this live vector and the cached vector the V2 hybrid models were trained on"},
        "pca": pca,
        "pca_fit": {"seed": 0, "angle_view": "MinMaxScaler to [0, π] fitted on the same train split; this is what every E5 model (quantum and classical controls) received", "split": "train", "n_images": int(len(st["Ftr"])), "steps": "StandardScaler -> PCA(k, full SVD)",
                    "in_fit_set": st["split"][image] == "train"},
        "scatter": {"pc1": np.round(S[:, 0], 3).tolist(), "pc2": np.round(S[:, 1], 3).tolist(),
                    "y": [int(v) for v in st["ytr"]], "me": [round(float(me[0]), 3), round(float(me[1]), 3)]},
        "models": _models(),
    }


@lru_cache(maxsize=1)
def _models():
    from src.v2.paths import DEFAULT_V2_ROOT
    try:
        a = json.loads((DEFAULT_V2_ROOT / "aggregates" / "analysis.json").read_text())["selected"]
    except (OSError, ValueError, KeyError):
        return []
    rows = []
    for g, v in a.items():
        if "mnv3" not in g.lower():
            continue
        k = next((int(s[len("mnv3pca"):]) for s in g.split("-") if s.startswith("mnv3pca")), None)
        rows.append({"group": g, "model_name": v.get("model_name"), "pca_k": k, "n_qubits": v.get("n_qubits"),
                     "type": "hybrid" if str(v.get("category", "")).startswith("4") else "classical",
                     "test_accuracy": v.get("test_accuracy"), "test_f1_macro": v.get("test_f1_macro")})
    return sorted(rows, key=lambda r: (r["pca_k"] or 999, r["type"], r["group"]))


HYBRID = "E5-mnv3pca8-qkc-product_ry"  # best V2 hybrid; its inputs are exactly the seed-0 PCA-8 angle features below


@lru_cache(maxsize=1)
def _index():
    from src.v2.paths import DEFAULT_V2_ROOT, DEFAULT_V4_ROOT
    ix = json.loads((DEFAULT_V4_ROOT / "aggregates" / "per_image_predictions.json").read_text())
    a = json.loads((DEFAULT_V2_ROOT / "aggregates" / "analysis.json").read_text())["selected"][HYBRID]
    return ix, a


def _thumb(path, s=48):
    from PIL import Image
    with Image.open(path) as im:
        return _png(np.asarray(im.convert("L"), float), s)


def hybrid(image: str):
    """One locked-test image through the hybrid pipeline: frozen MobileNetV3 → 576-d → seed-0 PCA-8 angles → bandwidth →
    product-RY kernel against the 1,080 seed-0 training images. The class decision shown is the model's SAVED
    locked-test prediction (3 seeds); the kernel values are recomputed live from the same features."""
    st = _state()
    ix, a = _index()
    rec = ix["images"].get(image)
    if rec is None:
        raise KeyError("not a locked-test image")
    d = st["data"]
    gray, x, outs = _forward(d.root / image)
    vec = outs[12].mean(axis=(1, 2))
    f = st["fz"][8]
    b = float(a["params"]["bandwidth"])
    ang = f.transform(vec[None], "angle")[0]
    tr = b * f.transform(st["Ftr"], "angle")
    xq = b * ang
    K = np.prod(np.cos((tr - xq) / 2.0) ** 2, axis=1)  # Product-RY kernel, closed form = statevector overlap
    paths = st["train_paths"]
    top = np.argsort(-K)[:5]
    cls_mean = {CLASSES[c]: float(K[st["ytr"] == c].mean()) for c in range(6)}
    preds = rec["preds"].get(HYBRID, [])
    return {
        "image": image, "y_true": CLASSES[rec["y_true"]], "original": _png(gray, 160), "model_input": _png(x[0].numpy().mean(axis=0), 160),
        "preprocess": {"from": list(gray.shape), "to": list(x.shape[1:]), "steps": "grey → RGB copy → resize 256 → centre-crop 224 → ImageNet mean/std"},
        "stages": _stages(outs, top=4), "vector": [round(float(v), 4) for v in vec],
        "pca": {"k": 8, "explained_variance_ratio": [round(float(v), 4) for v in f._pca.explained_variance_ratio_],
                "angles_rad": [round(float(v), 4) for v in ang], "bandwidth": b, "circuit_angles_rad": [round(float(v), 4) for v in xq]},
        "kernel": {"formula": "K(x, y) = Π_i cos²((x_i − y_i)/2)", "n_train": int(len(K)),
                   "nearest": [{"class": CLASSES[int(st["ytr"][i])], "similarity": round(float(K[i]), 4), "thumb": _thumb(d.root / paths[i])} for i in top],
                   "class_mean": {k: round(v, 5) for k, v in cls_mean.items()}},
        "model": {"group": HYBRID, "name": a["model_name"], "test_accuracy": a["test_accuracy"], "n_qubits": a["n_qubits"]},
        "saved_predictions": [CLASSES[p] for p in preds],
        "correct_seeds": int(sum(p == rec["y_true"] for p in preds)),
    }
