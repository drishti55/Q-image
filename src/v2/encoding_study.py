"""
FRQI / NEQR encoding–reconstruction study (Protocol V2, record_type = "reconstruction").
Kept entirely separate from classification.

Evaluation subset (fixed, documented): from the TRAIN folder, file indices {12, 60, 108, 156, 204}
of every class -> 30 images. The locked test set is never used here.
Per image: convert("L") -> BILINEAR resize to r×r -> /255 ("preprocessed image").

Encodings: original FRQIEncoder / NEQREncoder circuits. Simulation: qiskit-aer statevector.
Decoding: original FRQIReconstructor / NEQRReconstructor (statevector and counts paths).
Shot modes: counts are drawn as Multinomial(shots, |ψ|²) from the simulated statevector, keyed with
Qiskit's bit ordering — identical in distribution to an ideal (noiseless) measure_all on the same
circuit; equivalence with Aer sampling is tested in tests/test_v2_encoding.py.

Metrics (each image): MSE, PSNR (MSE = 0 -> PSNR reported as null with exact_match = true, never a
placeholder number), SSIM. SSIM method: r ≥ 7 -> skimage structural_similarity(win_size=7,
data_range=1); r < 7 -> single global-window SSIM (labelled: limited meaning for tiny images).
NEQR is scored (a) against the preprocessed image (end-to-end) and (b) against its own quantised
image (pure encoding/measurement error); the quantisation-only error is reported separately.
"""
from __future__ import annotations

import io
import time
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

from .dataset import CLASSES, load_manifest, manifest_root, preprocess_image
from .paths import assert_writable, v2_root
from .qsim import circuit_resources
from .store import dump_json, environment_info

SUBSET_INDICES = (12, 60, 108, 156, 204)
SHOTS = (100, 1000, 10000, 100000)
RESOLUTIONS = (2, 4, 8, 16)
NEQR_BITS = (2, 4, 8)


def subset(manifest: Optional[Dict] = None) -> List[Dict]:
    m = manifest or load_manifest()
    recs = [r for r in m["records"] if r["role"] == "trainval" and r["index"] in SUBSET_INDICES]
    recs.sort(key=lambda r: (CLASSES.index(r["class"]), r["index"]))
    return recs


def ssim(a: np.ndarray, b: np.ndarray) -> Tuple[float, str]:
    if min(a.shape) >= 7:
        from skimage.metrics import structural_similarity
        return float(structural_similarity(a, b, win_size=7, data_range=1.0)), "skimage win7"
    C1, C2 = 0.01 ** 2, 0.03 ** 2
    ma, mb = a.mean(), b.mean()
    va, vb, cov = a.var(), b.var(), ((a - ma) * (b - mb)).mean()
    return float(((2 * ma * mb + C1) * (2 * cov + C2)) / ((ma ** 2 + mb ** 2 + C1) * (va + vb + C2))), \
        "global single-window (image < 7 px; limited meaning)"


def image_metrics(ref: np.ndarray, rec: np.ndarray) -> Dict:
    mse = float(np.mean((ref - rec) ** 2))
    s, method = ssim(ref, rec)
    return {"mse": mse, "psnr": None if mse < 1e-15 else float(10 * np.log10(1.0 / mse)),
            "exact_match": mse < 1e-15, "ssim": s, "ssim_method": method}


def sample_counts(probs: np.ndarray, shots: int, n_qubits: int, rng: np.random.Generator) -> Dict[str, int]:
    c = rng.multinomial(shots, probs / probs.sum())
    nz = np.nonzero(c)[0]
    return {format(int(i), f"0{n_qubits}b"): int(c[i]) for i in nz}


def _png(arr: np.ndarray) -> bytes:
    u8 = (np.clip(arr, 0, 1) * 255).round().astype(np.uint8)
    h, w = u8.shape
    s = max(1, 128 // max(h, w))
    buf = io.BytesIO()
    Image.fromarray(u8, "L").resize((w * s, h * s), Image.Resampling.NEAREST).save(buf, "PNG")
    return buf.getvalue()


def run_config(rep: str, r: int, bits: Optional[int], images: List[Dict], root, out_root,
               shots_list=SHOTS, log=print) -> Dict:
    from src.frqi.encoder import FRQIEncoder
    from src.neqr.encoder import NEQREncoder
    from src.reconstruction.reconstructor import FRQIReconstructor, NEQRReconstructor
    from src.simulation.simulator import QuantumSimulator

    rid = f"R-{rep}-{r}x{r}" + (f"-b{bits}" if rep == "NEQR" else "")
    d = out_root / rid
    (d / "images").mkdir(parents=True, exist_ok=True)
    cfg = {"record_type": "reconstruction", "record_id": rid, "representation": rep, "resolution": r,
           "intensity_bits": bits, "shots": list(shots_list), "subset_indices": list(SUBSET_INDICES),
           "images": [i["rel_path"] for i in images], "simulator": "qiskit-aer statevector (+ multinomial sampling)",
           "encoder": "src/frqi/encoder.py::FRQIEncoder" if rep == "FRQI" else "src/neqr/encoder.py::NEQREncoder",
           "decoder": "src/reconstruction/reconstructor.py", "execution": "classical CPU simulation"}
    dump_json(d / "config.json", cfg)
    dump_json(d / "status.json", {"record_id": rid, "status": "running"})
    t_start = time.perf_counter()
    try:
        sim = QuantumSimulator(seed=0)
        per_image, recon_arrays, circuits = [], {}, []
        mx = (1 << bits) - 1 if bits else None
        for k, rec in enumerate(images):
            img = preprocess_image(root / rec["rel_path"], r)
            t0 = time.perf_counter()
            if rep == "FRQI":
                enc = FRQIEncoder(img)
                qc = enc.build_circuit()
                dec = FRQIReconstructor(enc.n_position_qubits, (r, r))
                quant = None
            else:
                quant = np.clip(np.round(img * mx), 0, mx).astype(int)
                enc = NEQREncoder(quant, intensity_bits=bits)
                qc = enc.build_circuit()
                dec = NEQRReconstructor(enc.n_position_qubits, bits, (r, r))
            t_build = time.perf_counter() - t0
            if k < 5:
                circuits.append(circuit_resources(qc))
            t0 = time.perf_counter()
            sv = sim.run_statevector(qc)
            t_sim = time.perf_counter() - t0
            rng = np.random.default_rng(1000 * k + r)
            modes = {}
            for mode in ["statevector"] + [f"shots{s}" for s in shots_list]:
                t0 = time.perf_counter()
                if mode == "statevector":
                    out = dec.reconstruct_from_statevector(sv["statevector"])
                else:
                    s = int(mode[5:])
                    out = dec.reconstruct_from_counts(sample_counts(sv["probabilities"], s, qc.num_qubits, rng), shots=s)
                t_dec = time.perf_counter() - t0
                rec_img = out["image"].astype(float) / (mx if rep == "NEQR" else 1.0)
                m = {"vs_preprocessed": image_metrics(img, rec_img), "decode_time_s": t_dec}
                if rep == "NEQR":
                    m["vs_quantized"] = image_metrics(quant / mx, rec_img)
                    if mode != "statevector":
                        m["pixels_never_observed"] = int(np.sum(np.asarray(out.get("position_counts", np.ones(r * r))) == 0))
                modes[mode] = m
                recon_arrays[f"{k}:{mode}"] = rec_img
            row = {"image": rec["rel_path"], "class": rec["class"], "build_time_s": t_build,
                   "statevector_sim_time_s": t_sim, "modes": modes}
            if rep == "NEQR":
                row["quantization_only"] = image_metrics(img, quant / mx)
            per_image.append(row)
            if k % 6 == 0:  # one image per class -> saved PNGs
                for name, arr in [("original", img)] + [(mo, recon_arrays[f"{k}:{mo}"]) for mo in modes]:
                    p = d / "images" / f"{k:02d}_{rec['class']}_{name}.png"
                    assert_writable(p)
                    p.write_bytes(_png(arr))
                    if name != "original":
                        q = d / "images" / f"{k:02d}_{rec['class']}_{name}_diff.png"
                        q.write_bytes(_png(np.abs(img - arr)))
        np.savez_compressed(d / "reconstructions.npz", **{k.replace(":", "__"): v for k, v in recon_arrays.items()})

        def agg(mode, key, field):
            vals = [im["modes"][mode][key][field] for im in per_image]
            if field == "psnr":
                finite = [v for v in vals if v is not None]
                return {"mean": float(np.mean(finite)) if finite else None, "n_finite": len(finite),
                        "n_exact": sum(v is None for v in vals)}
            return {"mean": float(np.mean(vals)), "std": float(np.std(vals, ddof=1)), "n": len(vals)}

        summary = {}
        for mode in per_image[0]["modes"]:
            summary[mode] = {key: {f: agg(mode, key, f) for f in ("mse", "psnr", "ssim")}
                             for key in (["vs_preprocessed", "vs_quantized"] if rep == "NEQR" else ["vs_preprocessed"])}
            summary[mode]["decode_time_s_mean"] = float(np.mean([im["modes"][mode]["decode_time_s"] for im in per_image]))
        if rep == "NEQR":
            summary["quantization_only"] = {f: {"mean": float(np.mean([im["quantization_only"][f] for im in per_image
                                                                     if im["quantization_only"][f] is not None]))
                                                if any(im["quantization_only"][f] is not None for im in per_image) else None}
                                            for f in ("mse", "psnr", "ssim")}
        cs = dict(circuits[0])
        for key in ("gates_logical", "depth_logical", "gates_compiled", "depth_compiled", "cx_compiled",
                    "two_qubit_gates_compiled", "single_qubit_gates_compiled"):
            v = [c[key] for c in circuits]
            cs[key] = float(np.mean(v))
            cs[key + "_range"] = [int(min(v)), int(max(v))]
        cs["n_sample_images"] = len(circuits)
        dump_json(d / "circuit_stats.json", cs)
        dump_json(d / "metrics.json", {"summary": summary, "per_image": per_image,
                                       "timing": {"build_time_s_mean": float(np.mean([i["build_time_s"] for i in per_image])),
                                                  "statevector_sim_time_s_mean": float(np.mean([i["statevector_sim_time_s"] for i in per_image]))}})
        dump_json(d / "metadata.json", {"environment": environment_info(), "duration_s": time.perf_counter() - t_start})
        dump_json(d / "status.json", {"record_id": rid, "status": "completed", "record_type": "reconstruction",
                                      "summary": {"representation": rep, "resolution": r, "intensity_bits": bits,
                                                  "n_qubits": cs["n_qubits"], "gates_compiled": cs["gates_compiled"],
                                                  "depth_compiled": cs["depth_compiled"],
                                                  "statevector_mse": summary["statevector"]["vs_preprocessed"]["mse"]["mean"]}})
        log(f"  [ok] {rid}: sv MSE={summary['statevector']['vs_preprocessed']['mse']['mean']:.2e} "
            f"1k-shot MSE={summary.get('shots1000', {}).get('vs_preprocessed', {}).get('mse', {}).get('mean', float('nan')):.2e}")
        return summary
    except Exception as e:
        import traceback
        dump_json(d / "status.json", {"record_id": rid, "status": "failed", "error": {
            "type": type(e).__name__, "message": str(e), "traceback": traceback.format_exc()}})
        log(f"  [FAILED] {rid}: {e}")
        return {}


def run_all(log=print):
    m = load_manifest()
    from pathlib import Path
    root = manifest_root(m)
    imgs = subset(m)
    out = v2_root() / "reconstructions"
    for r in RESOLUTIONS:
        run_config("FRQI", r, None, imgs, root, out, log=log)
        for b in NEQR_BITS:
            run_config("NEQR", r, b, imgs, root, out, log=log)
