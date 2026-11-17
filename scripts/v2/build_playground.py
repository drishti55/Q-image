"""
Algorithm Playground data: run the illustrative 3×3 grid through the ACTUAL Q-ImageLab implementations and record every
intermediate value. Output: results/qml_v2/playground/playground_3x3.json (flagged illustrative; never an evaluation
result). Runs in a clean process (Qiskit/torch are not executed inside the web server).

Grid (row-major):  70 180 0 / 19 20 0 / 0 0 0   — four given pixels + five zero padding cells.
Every trained model used is the seed-0 checkpoint of its validation-selected configuration.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.v2.dataset import CLASSES, load_manifest  # noqa: E402
from src.v2.paths import v2_root  # noqa: E402
from src.v2.store import dump_json, environment_info  # noqa: E402

GRID = np.array([[70, 180, 0], [19, 20, 0], [0, 0, 0]], dtype=np.uint8)
GIVEN = [(0, 0), (0, 1), (1, 0), (1, 1)]
SEED = 0
R = v2_root()
A = json.loads((R / "aggregates" / "analysis.json").read_text())


def r(x, d=6):
    """Round floats (recursively) for a compact JSON."""
    if isinstance(x, dict):
        return {k: r(v, d) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [r(v, d) for v in x]
    if isinstance(x, np.ndarray):
        return r(x.tolist(), d)
    if isinstance(x, (float, np.floating)):
        return float(round(float(x), d))
    if isinstance(x, (np.integer,)):
        return int(x)
    return x


def checkpoint(group: str):
    eid = next(e for e in A["selected"][group]["experiment_ids"] if e.endswith(f"__s{SEED}"))
    return eid, joblib.load(R / "experiments" / eid / "model" / "estimator.joblib")


def resize(img_u8: np.ndarray, s: int) -> np.ndarray:
    """Same operation as src/v2/dataset.py::preprocess_image (convert L → BILINEAR resize → /255)."""
    return np.asarray(Image.fromarray(img_u8, "L").resize((s, s), Image.Resampling.BILINEAR), dtype=np.float64) / 255.0


def pool(img: np.ndarray, out: int) -> np.ndarray:
    k = img.shape[0] // out
    return img[: out * k, : out * k].reshape(out, k, out, k).mean(axis=(1, 3))


def norm01(a: np.ndarray) -> np.ndarray:
    lo, hi = float(a.min()), float(a.max())
    return np.zeros_like(a) if hi - lo < 1e-12 else (a - lo) / (hi - lo)


def softmax(z):
    z = np.asarray(z, float) - np.max(z)
    e = np.exp(z)
    return e / e.sum()


def real_sample_u8(cls: str) -> tuple[np.ndarray, str]:
    man = load_manifest()
    rec = sorted((x for x in man["records"] if x["class"] == cls and x["role"] == "trainval"), key=lambda x: x["index"])[0]
    with Image.open(Path(man["dataset_root"]) / rec["rel_path"]) as im:
        return np.asarray(im.convert("L"), dtype=np.uint8), rec["rel_path"]


# ─── classical ──────────────────────────────────────────────────────────────
def classical(out):
    from src.v2.providers import _fitted_pca, neu
    img64 = resize(GRID, 64)
    pca = {}
    for k in (4, 8):
        f = _fitted_pca(SEED, k, 64)
        z = f._pix.transform(img64.reshape(1, -1))[0]
        pca[str(k)] = {
            "scores": f.scores(img64[None])[0], "standard": f.transform(img64[None], "standard")[0],
            "angle": f.transform(img64[None], "angle")[0],
            "explained_variance_ratio": f._pca.explained_variance_ratio_, "fitted_on_n_train": f.fitted_n,
            "standardized_pixels": {"mean": float(z.mean()), "std": float(z.std()), "min": float(z.min()), "max": float(z.max())},
        }
    f8 = _fitted_pca(SEED, 8, 64)
    comps = [norm01(f8._pca.components_[i].reshape(64, 64)) for i in range(3)]
    tr = neu(SEED).train(64)
    S = f8.transform(tr.X, "standard")
    rng = np.random.default_rng(0)
    pick = np.sort(rng.choice(len(S), size=360, replace=False))
    out["preprocessing"] = {
        "normalized_3x3": GRID / 255.0, "flattened_9": (GRID / 255.0).reshape(-1),
        "resized_64": (img64 * 255).round().astype(int), "resize": "PIL BILINEAR 3×3 → 64×64 (as preprocess_image)",
        "pca": pca, "pca_components_64": [pool(c, 32) for c in comps],
        "train_scatter_pc12": {"x": S[pick, 0], "y": S[pick, 1], "label": tr.y[pick], "n_shown": len(pick), "n_train": len(S)},
        "demo_pc12": pca["8"]["standard"][:2],
    }
    # RBF-SVM
    eid, svm = checkpoint("E6-pca8-rbfsvm")
    x = np.asarray(pca["8"]["standard"])
    m = svm.m
    gamma = float(m.gamma)
    sv = m.support_vectors_
    d2 = ((sv - x) ** 2).sum(1)
    K = np.exp(-gamma * d2)
    sv_labels = np.repeat(np.arange(len(m.n_support_)), m.n_support_)
    top = np.argsort(-K)[:8]
    out["svm"] = {
        "experiment_id": eid, "gamma": gamma, "C": float(m.C), "n_support": m.n_support_, "x": x,
        "prediction": int(m.predict(x[None])[0]), "decision_ovr": m.decision_function(x[None])[0],
        "top_support_vectors": [{"class": int(sv_labels[i]), "dist2": float(d2[i]), "K": float(K[i])} for i in top],
        "mean_K_by_class": [float(K[sv_labels == c].mean()) for c in range(6)],
        "example": {"dist2": float(d2[top[0]]), "K": float(K[top[0]]), "class": int(sv_labels[top[0]])},
    }
    eid, lr = checkpoint("E6-pca8-logreg")
    zz = lr.m.decision_function(x[None])[0]
    out["logreg"] = {"experiment_id": eid, "W": lr.m.coef_, "b": lr.m.intercept_, "x": x, "scores": zz,
                     "probabilities": lr.m.predict_proba(x[None])[0], "softmax_of_scores": softmax(zz),
                     "prediction": int(lr.m.predict(x[None])[0])}


# ─── CNNs ───────────────────────────────────────────────────────────────────
def cnns(out):
    import torch
    eid, est = checkpoint("E7-smallcnn")
    net = est._loaded()

    def run_small(u8):
        x = resize(u8, 128)
        t = torch.from_numpy(((x.astype(np.float32) - 0.5) / 0.25)[None, None])
        acts = {}
        hooks = [net.features[2].register_forward_hook(lambda m_, i, o: acts.__setitem__("relu1", o.detach())),
                 net.features[3].register_forward_hook(lambda m_, i, o: acts.__setitem__("pool1", o.detach())),
                 net.features[15].register_forward_hook(lambda m_, i, o: acts.__setitem__("pool4", o.detach()))]
        with torch.no_grad():
            emb = net.embed(t)[0].numpy()
            logits = net.head(torch.from_numpy(emb[None]))[0].numpy()
        for h in hooks:
            h.remove()
        relu1 = acts["relu1"][0].numpy()
        var = relu1.reshape(relu1.shape[0], -1).var(1)
        ch = list(np.argsort(-var)[:8])
        return {"input_128": (pool(x, 64) * 255).round().astype(int),
                "conv1_maps": [{"channel": int(c), "map": pool(norm01(relu1[c]), 32)} for c in ch],
                "conv1_kernels": [norm01(net.features[0].weight[int(c), 0].detach().numpy()) for c in ch],
                "pool4_shape": list(acts["pool4"][0].shape), "embedding_dim": int(emb.shape[0]),
                "embedding_first16": emb[:16], "logits": logits, "probabilities": softmax(logits),
                "prediction": int(np.argmax(logits))}
    real_u8, real_path = real_sample_u8("crazing")
    out["small_cnn"] = {
        "experiment_id": eid, "architecture": [
            ["input", [1, 128, 128]], ["conv 3×3 (16) + BN + ReLU", [16, 128, 128]], ["max-pool 2", [16, 64, 64]],
            ["conv 3×3 (32) + BN + ReLU + pool", [32, 32, 32]], ["conv 3×3 (64) + BN + ReLU + pool", [64, 16, 16]],
            ["conv 3×3 (128) + BN + ReLU + pool", [128, 8, 8]], ["global average pool", [128]], ["dropout + linear", [6]]],
        "demo": run_small(GRID), "real": {**run_small(real_u8), "image": real_path}}

    from src.v2.cnn import FrozenMobileNetV3Source
    from src.v2.providers import VectorProvider
    src = FrozenMobileNetV3Source()
    model = src.model()
    tf = src.weights.transforms()
    prov = VectorProvider(src, None, "standard")
    prov.train_val(SEED)  # fits the train-only StandardScaler exactly as in the experiment
    feat = prov._featurizer(SEED, None)
    eid, lrm = checkpoint("E7-mnv3-logreg")

    def run_mnv3(u8):
        t = tf(Image.fromarray(u8, "L").convert("RGB"))[None]
        with torch.no_grad():
            first = model.features[0](t)[0].numpy()
            f = model.features(t).mean(dim=(2, 3))[0].numpy()
        z = feat.transform(f[None], "standard")
        var = first.reshape(first.shape[0], -1).var(1)
        ch = list(np.argsort(-var)[:6])
        return {"first_layer_maps": [{"channel": int(c), "map": pool(norm01(first[c]), 28)} for c in ch],
                "feature_dim": int(f.shape[0]), "feature_first24": f[:24], "feature_l2": float(np.linalg.norm(f)),
                "feature_nonzero_fraction": float((f > 1e-6).mean()),
                "probabilities": lrm.m.predict_proba(z)[0], "prediction": int(lrm.m.predict(z)[0])}
    out["mobilenet"] = {"experiment_id": eid, "weights": src.weight_id, "load_info": src.load_info,
                        "preprocessing": "grayscale → RGB copy → resize 256 → centre-crop 224 → ImageNet mean/std",
                        "demo": run_mnv3(GRID), "real": {**run_mnv3(real_u8), "image": real_path}}


# ─── FRQI / NEQR (4×4 zero-padded embedding of the 3×3 grid) ─────────────────
def padded4() -> np.ndarray:
    g = np.zeros((4, 4), dtype=np.uint8)
    g[:3, :3] = GRID
    return g


def frqi(out):
    from qiskit.quantum_info import Statevector

    from src.frqi.encoder import FRQIEncoder
    from src.reconstruction.reconstructor import FRQIReconstructor
    from src.v2.encoding_study import sample_counts
    g = padded4()
    norm = g / 255.0
    enc = FRQIEncoder(norm)
    qc = enc.build_circuit()
    sv = np.asarray(Statevector(qc).data)
    n = enc.n_position_qubits
    N = 2 ** n
    pix = norm.reshape(-1)
    rows, blocks = [], []
    for i in range(N):
        th = float(pix[i] * np.pi / 2)
        a0, a1 = sv[i], sv[i + N]
        rows.append({"position": i, "row": i // 4, "col": i % 4, "pixel": int(g.reshape(-1)[i]), "intensity": float(pix[i]),
                     "theta": th, "theta_deg": float(np.degrees(th)), "pos_bits_q3q2q1q0": format(i, "04b"),
                     "amp_colour0": float(a0.real), "amp_colour1": float(a1.real),
                     "formula_amp_colour0": float(np.cos(th) / np.sqrt(N)), "formula_amp_colour1": float(np.sin(th) / np.sqrt(N)),
                     "p_colour1_given_position": float(np.sin(th) ** 2)})
        if pix[i] > 0:
            bits = [(i >> b) & 1 for b in range(n)]
            blocks.append({"position": i, "pixel": int(g.reshape(-1)[i]), "x_on_qubits": [b for b in range(n) if bits[b] == 0],
                           "ry_angle": float(np.pi * pix[i]), "theta": th})
    err = max(max(abs(x["amp_colour0"] - x["formula_amp_colour0"]), abs(x["amp_colour1"] - x["formula_amp_colour1"])) for x in rows)
    dec = FRQIReconstructor(n, (4, 4))
    exact = dec.reconstruct_from_statevector(sv)["image"]
    probs = np.abs(sv) ** 2
    shots = {}
    for s in (100, 1000, 10000):
        counts = sample_counts(probs, s, qc.num_qubits, np.random.default_rng(7))
        rec = dec.reconstruct_from_counts(counts, shots=s)["image"]
        shots[str(s)] = {"reconstructed_255": (rec * 255), "top_counts": sorted(counts.items(), key=lambda kv: -kv[1])[:8]}
    out["frqi"] = {
        "padded_4x4": g, "n_position_qubits": n, "n_qubits": qc.num_qubits, "positions": rows, "blocks": blocks,
        "statevector_formula_max_abs_error": err, "logical_gate_counts": {k: int(v) for k, v in qc.count_ops().items()},
        "logical_gates": len(qc.data), "depth": qc.depth(),
        "reconstructed_exact_255": exact * 255, "shots": shots,
        "notes": "θ = (π/2)·pixel/255; RY(2θ) on the colour qubit controlled by all 4 position qubits; zero pixels add no gates.",
    }


def neqr(out):
    from qiskit.quantum_info import Statevector

    from src.neqr.encoder import NEQREncoder
    from src.reconstruction.reconstructor import NEQRReconstructor
    from src.v2.encoding_study import sample_counts
    from src.v2.frqi_neqr import neqr_quantize
    g = padded4()
    res = {}
    for b in (2, 4, 8):
        mx = (1 << b) - 1
        q = neqr_quantize((g / 255.0)[None], b).reshape(4, 4)
        enc = NEQREncoder(q, intensity_bits=b)
        qc = enc.build_circuit()
        sv = np.asarray(Statevector(qc).data)
        n = enc.n_position_qubits
        basis = []
        for idx in np.nonzero(np.abs(sv) > 1e-9)[0]:
            pos, inten = int(idx % 16), int(idx // 16)
            basis.append({"index": int(idx), "bitstring": format(int(idx), f"0{n + b}b"), "position": pos,
                          "intensity_value": inten, "amplitude": float(sv[idx].real)})
        dec = NEQRReconstructor(n, b, (4, 4))
        exact = dec.reconstruct_from_statevector(sv)["image"]
        probs = np.abs(sv) ** 2
        rec1000 = dec.reconstruct_from_counts(sample_counts(probs, 1000, qc.num_qubits, np.random.default_rng(7)), 1000)["image"]
        pixels = []
        for (rr, cc) in GIVEN:
            v = int(g[rr, cc])
            qv = int(q[rr, cc])
            pixels.append({"row": rr, "col": cc, "pixel": v, "normalized": v / 255, "scaled": v / 255 * mx,
                           "quantized": qv, "binary_msb_first": format(qv, f"0{b}b"), "represented_255": qv / mx * 255,
                           "error_255": qv / mx * 255 - v})
        blocks = []
        flat = q.reshape(-1)
        for i in range(16):
            if flat[i] > 0:
                bits = [(i >> k) & 1 for k in range(n)]
                blocks.append({"position": i, "value": int(flat[i]), "x_on_qubits": [k for k in range(n) if bits[k] == 0],
                               "mcx_targets": [n + k for k in range(b) if (int(flat[i]) >> k) & 1]})
        rep = q / mx * 255
        res[str(b)] = {
            "bits": b, "levels": mx + 1, "n_qubits": qc.num_qubits, "pixels": pixels, "quantized_4x4": q, "blocks": blocks,
            "basis_states": basis, "logical_gate_counts": {k: int(v) for k, v in qc.count_ops().items()},
            "logical_gates": len(qc.data), "depth": qc.depth(),
            "reconstructed_exact_255": exact / mx * 255, "reconstructed_1000shots_255": rec1000 / mx * 255,
            "decode_matches_quantized": bool(np.array_equal(exact, q)),
            "mse_given_pixels_255sq": float(np.mean([(p["represented_255"] - p["pixel"]) ** 2 for p in pixels])),
            "mse_grid_normalized": float(np.mean(((rep[:3, :3] - GRID) / 255.0) ** 2)),
        }
    out["neqr"] = {"padded_4x4": g, "precisions": res, "n_position_qubits": 4,
                   "quantization": "q = round(pixel/255 · (2^b − 1)); represented = q/(2^b − 1)·255 (src/v2/frqi_neqr.py::neqr_quantize)"}


# ─── QKC / VQC on PCA-4 angle features ─────────────────────────────────────
def instr(qc):
    return [{"name": i.operation.name, "qubits": [qc.find_bit(b).index for b in i.qubits],
             "params": [round(float(p), 4) for p in i.operation.params]} for i in qc.data]


def quantum_models(out):
    from sklearn.svm import SVC  # noqa: F401
    from src.v2.providers import neu
    from src.v2.qkernel import encode, fidelity_kernel, states
    a4 = np.asarray(out["preprocessing"]["pca"]["4"]["angle"], float)
    tr = neu(SEED).train(64)
    from src.v2.providers import _fitted_pca
    Atr = _fitted_pca(SEED, 4, 64).transform(tr.X, "angle")
    reps_idx = [int(np.nonzero(tr.y == c)[0][0]) for c in range(6)]
    maps = {}
    for fmap in ("product_ry", "zz_linear", "zz_full"):
        eid, est = checkpoint(f"E3-pca4-qkc-{fmap}")
        p = est.params
        x = a4 * p["bandwidth"]
        sim = encode(x[None], fmap, p["reps"], record=True)
        st = sim.state[0]
        assert np.allclose(est.Xtr, Atr), "checkpoint training features must equal the re-derived PCA-4 angles"
        S = states(est.Xtr * p["bandwidth"], fmap, p["reps"])
        krow = fidelity_kernel(st[None], S)[0]
        top = np.argsort(-krow)[:6]
        pts = np.vstack([x[None], (est.Xtr[reps_idx] * p["bandwidth"])])
        Sp = states(pts, fmap, p["reps"])
        maps[fmap] = {
            "experiment_id": eid, "params": p, "x_scaled": x, "circuit": instr(sim.qc), "n_gates": len(sim.qc.data),
            "depth": sim.qc.depth(), "statevector_abs": np.abs(st), "statevector_phase": np.angle(st),
            "kernel_top_train": [{"class": int(tr.y[j]), "K": float(krow[j])} for j in top],
            "kernel_mean_by_class": [float(krow[tr.y == c].mean()) for c in range(6)],
            "kernel_heatmap": fidelity_kernel(Sp), "heatmap_labels": ["demo"] + [CLASSES[c] for c in range(6)],
            "prediction": int(est.predict(a4[None])[0]),
            "train_kernel_offdiag_mean": est._diag["train_kernel"]["offdiag_mean"],
        }
    # classical RBF on the same angle features, same 7 points (identical-input control)
    eid, rbf = checkpoint("E6-pca4-rbfsvm-angle")
    pts = np.vstack([a4[None], Atr[reps_idx]])
    d2 = ((pts[:, None, :] - pts[None, :, :]) ** 2).sum(-1)
    out["qkc"] = {"features": a4, "feature_source": "64×64 resized demo → train-fitted PCA(4) → MinMax[0,π] (seed 0)",
                  "maps": maps, "rbf_control": {"experiment_id": eid, "gamma": float(rbf.m.gamma),
                                                "kernel_heatmap": np.exp(-float(rbf.m.gamma) * d2),
                                                "prediction": int(rbf.m.predict(a4[None])[0])}}

    eid, vqc = checkpoint("E4-pca4-vqc")
    c = vqc.circ
    theta0 = np.random.default_rng(SEED).uniform(-vqc.params["init_scale"], vqc.params["init_scale"], c.n_params)
    w0, b0 = np.full(6, vqc.params["head_init"]), np.zeros(6)

    def forward(th, w, b):
        E = c.expectations(a4[None], th)[0]
        z = E * w + b
        return E, z, softmax(z)
    E1, z1, p1 = forward(vqc.theta, vqc.w, vqc.b)
    E0, z0, p0 = forward(theta0, w0, b0)
    pidx = 0
    tp, tm = vqc.theta.copy(), vqc.theta.copy()
    tp[pidx] += np.pi / 2
    tm[pidx] -= np.pi / 2
    Ep, Em = c.expectations(a4[None], tp)[0], c.expectations(a4[None], tm)[0]
    target = 0  # illustrative label for the single-example update (crazing)
    loss, gt, gw, gb = vqc.loss_and_grad(a4[None], np.array([target]), vqc.theta, vqc.w, vqc.b)
    lr_ = vqc.params["lr"]
    g = np.concatenate([gt, gw, gb])
    m1, m2 = 0.1 * g, 0.001 * g * g
    step = lr_ * (m1 / (1 - 0.9)) / (np.sqrt(m2 / (1 - 0.999)) + 1e-8)
    v_new = np.concatenate([vqc.theta, vqc.w, vqc.b]) - step
    th_new, w_new, b_new = v_new[:c.n_params], v_new[c.n_params:c.n_params + 6], v_new[c.n_params + 6:]
    E2, z2, p2 = forward(th_new, w_new, b_new)
    hist = json.loads((R / "experiments" / eid / "training_log.json").read_text())
    out["vqc"] = {
        "experiment_id": eid, "n_qubits": c.n, "layers": c.L, "entangler": c.ent, "readout": [f"{k}{q}" for k, q in c.readout],
        "features": a4, "theta_trained": vqc.theta, "theta_initial": theta0, "w": vqc.w, "b": vqc.b,
        "circuit_trained": instr(c.run(a4[None], vqc.theta, record=True).qc),
        "trained": {"expectations": E1, "logits": z1, "probabilities": p1, "prediction": int(np.argmax(z1))},
        "untrained": {"expectations": E0, "logits": z0, "probabilities": p0, "prediction": int(np.argmax(z0))},
        "parameter_shift": {"param_index": pidx, "theta": float(vqc.theta[pidx]), "E_plus": Ep, "E_minus": Em,
                            "dE_dtheta": 0.5 * (Ep - Em)},
        "illustrative_adam_step": {"target_class": target, "loss_before": loss, "grad_theta": gt, "lr": lr_,
                                   "theta_after": th_new, "probabilities_after": p2,
                                   "loss_after": float(-np.log(max(p2[target], 1e-12)))},
        "training_history": hist["history"], "best": hist.get("best"),
    }


def main():
    out = {
        "illustrative": True,
        "disclaimer": ("Educational demonstration on an artificial 3×3 image. Values are produced by the actual Q-ImageLab "
                       "implementations and seed-0 checkpoints, but the image is not from NEU-DET and these outputs are NOT "
                       "evaluation results."),
        "grid": GRID, "given_cells": GIVEN, "classes": CLASSES, "seed": SEED, "created_at": datetime.now().isoformat(),
    }
    classical(out)
    cnns(out)
    frqi(out)
    neqr(out)
    quantum_models(out)
    out["environment"] = environment_info()
    p = R / "playground" / "playground_3x3.json"
    dump_json(p, r(out))
    print("wrote", p, f"{p.stat().st_size / 1024:.0f} KB")
    print("FRQI statevector vs formula max abs error:", out["frqi"]["statevector_formula_max_abs_error"])
    for b, v in out["neqr"]["precisions"].items():
        print(f"NEQR {b}-bit:", [(px["pixel"], px["binary_msb_first"], round(px["represented_255"], 1)) for px in v["pixels"]],
              "decode ok:", v["decode_matches_quantized"])
    print("SVM pred:", CLASSES[out["svm"]["prediction"]], "| LogReg:", CLASSES[out["logreg"]["prediction"]],
          "| small CNN:", CLASSES[out["small_cnn"]["demo"]["prediction"]], "| MNV3:", CLASSES[out["mobilenet"]["demo"]["prediction"]])
    print("QKC preds:", {k: CLASSES[v["prediction"]] for k, v in out["qkc"]["maps"].items()}, "| VQC trained:",
          CLASSES[out["vqc"]["trained"]["prediction"]], "untrained:", CLASSES[out["vqc"]["untrained"]["prediction"]])


if __name__ == "__main__":
    main()
