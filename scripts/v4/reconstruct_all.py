"""
Full reconstruction study: EVERY image of NEU-DET (1,800) x EVERY encoding method.
Output: results/qml_v4/reconstruction_full/<record>/{config.json, metrics.json, reconstructions.npz, status.json}
        results/qml_v4/reconstruction_full/summary.json

Quantum records (real Qiskit circuits: src/frqi/encoder.py, src/neqr/encoder.py -> qiskit-aer statevector ->
src/reconstruction/reconstructor.py; shots = multinomial samples of the exact output distribution):
  R-FRQI-{2,4,8,16}            whole image, statevector + 100 / 1k / 10k / 100k shots
  R-NEQR-{2,4,8,16}-b{2,4,8}   whole image, same modes
  P-FRQI-64-p8                 V4 representation: 64x64 image, every 8x8 patch encoded (7 qubits) and decoded, stitched;
                               statevector + 100 / 1k / 10k shots PER PATCH
  P-NEQR-64-p4-b4              V4 representation: 64x64 image, every 4x4 patch, 4-bit (8 qubits); same modes
Classical reference (no quantum circuit; labelled classical):
  C-PCA8-64, C-PCA12-64        64x64 pixels -> PCA(k) fitted on the seed-0 TRAIN split only -> inverse transform.
                               Shows how much of the image the PCA-input QKC / VQC models receive.

Reconstruction involves no learning from labels, so evaluating test-folder images here cannot leak into model selection.
Stages:  run --worker i --of n   |   merge
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from common import V4

from src.v2.dataset import CLASSES, load_manifest, load_split, preprocess_image
from src.v2.encoding_study import image_metrics, sample_counts
from src.v2.paths import dataset_root
from src.v2.qsim import circuit_resources

OUT = V4 / "reconstruction_full"
SHOTS_FULL = (100, 1000, 10000, 100000)
SHOTS_PATCH = (100, 1000, 10000)
CHUNK = 100


def records():
    rs = []
    for r in [("FRQI", s, None) for s in (2, 4, 8, 16)] + [("NEQR", s, b) for s in (2, 4, 8, 16) for b in (2, 4, 8)]:
        rep, s, b = r
        rs.append({"id": f"R-{rep}-{s}x{s}" + (f"-b{b}" if b else ""), "kind": "quantum_whole", "representation": rep,
                   "resolution": s, "bits": b, "shots": list(SHOTS_FULL)})
    rs.append({"id": "P-FRQI-64-p8", "kind": "quantum_patch", "representation": "FRQI", "resolution": 64, "patch": 8, "bits": None,
               "shots": list(SHOTS_PATCH)})
    rs.append({"id": "P-NEQR-64-p4-b4", "kind": "quantum_patch", "representation": "NEQR", "resolution": 64, "patch": 4, "bits": 4,
               "shots": list(SHOTS_PATCH)})
    rs.append({"id": "C-PCA8-64", "kind": "classical", "resolution": 64, "k": 8})
    rs.append({"id": "C-PCA12-64", "kind": "classical", "resolution": 64, "k": 12})
    return rs


def images():
    m = load_manifest()
    recs = sorted(m["records"], key=lambda r: (r["role"] != "trainval", CLASSES.index(r["class"]), r["index"]))
    return recs


class Codec:
    """One FRQI / NEQR encoder + simulator + decoder for a fixed (rep, size, bits)."""

    def __init__(self, rep, r, bits):
        from src.simulation.simulator import QuantumSimulator
        self.rep, self.r, self.bits = rep, r, bits
        self.mx = (1 << bits) - 1 if bits else None
        self.sim = QuantumSimulator(seed=0)

    def run(self, img, shots, rng):
        from src.frqi.encoder import FRQIEncoder
        from src.neqr.encoder import NEQREncoder
        from src.reconstruction.reconstructor import FRQIReconstructor, NEQRReconstructor
        r = self.r
        if self.rep == "FRQI":
            enc = FRQIEncoder(img)
            qc = enc.build_circuit()
            dec = FRQIReconstructor(enc.n_position_qubits, (r, r))
            quant = None
        else:
            quant = np.clip(np.round(img * self.mx), 0, self.mx).astype(int)
            enc = NEQREncoder(quant, intensity_bits=self.bits)
            qc = enc.build_circuit()
            dec = NEQRReconstructor(enc.n_position_qubits, self.bits, (r, r))
        sv = self.sim.run_statevector(qc)
        scale = self.mx if self.rep == "NEQR" else 1.0
        out = {"statevector": dec.reconstruct_from_statevector(sv["statevector"])["image"].astype(float) / scale}
        for s in shots:
            o = dec.reconstruct_from_counts(sample_counts(sv["probabilities"], s, qc.num_qubits, rng), shots=s)
            out[f"shots{s}"] = o["image"].astype(float) / scale
        return out, qc, (quant / self.mx if quant is not None else None)


def metrics(ref, rec):
    m = image_metrics(ref, rec)
    return {k: m[k] for k in ("mse", "psnr", "ssim", "exact_match")}


def run_unit(rec, imgs, idx, root):
    rid = rec["id"]
    part = OUT / rid / "parts" / f"{idx[0]:04d}.npz"
    if part.exists():
        return
    rows, arrays = [], {}
    t0 = time.perf_counter()
    if rec["kind"] == "classical":
        from sklearn.decomposition import PCA
        tr = set(load_split(0)["train"])
        fit = np.stack([preprocess_image(root / r["rel_path"], 64).ravel() for r in imgs if r["rel_path"] in tr])
        pca = PCA(n_components=rec["k"], random_state=0).fit(fit)
    else:
        codec = Codec(rec["representation"], rec.get("patch") or rec["resolution"], rec["bits"])
    circ = None
    for i in idx:
        im = imgs[i]
        img = preprocess_image(root / im["rel_path"], rec["resolution"])
        rng = np.random.default_rng(10_000 * i + hash(rid) % 9973)
        row = {"i": i, "image": im["rel_path"], "class": im["class"], "role": im["role"], "modes": {}}
        if rec["kind"] == "classical":
            outs = {"reconstruction": pca.inverse_transform(pca.transform(img.reshape(1, -1))).reshape(64, 64)}
            quant = None
        elif rec["kind"] == "quantum_whole":
            outs, qc, quant = codec.run(img, rec["shots"], rng)
            circ = circ or circuit_resources(qc)
        else:  # patch: encode + decode every patch with the real circuits, stitch
            p, S = rec["patch"], rec["resolution"]
            outs = {m: np.zeros((S, S)) for m in ["statevector"] + [f"shots{s}" for s in rec["shots"]]}
            quant = np.zeros((S, S)) if rec["representation"] == "NEQR" else None
            for a in range(0, S, p):
                for b in range(0, S, p):
                    o, qc, q = codec.run(img[a:a + p, b:b + p], rec["shots"], rng)
                    circ = circ or circuit_resources(qc)
                    for m in outs:
                        outs[m][a:a + p, b:b + p] = o[m]
                    if quant is not None:
                        quant[a:a + p, b:b + p] = q
        for m, arr in outs.items():
            arr = np.clip(arr, 0, 1)
            row["modes"][m] = {"vs_preprocessed": metrics(img, arr)}
            if quant is not None:
                row["modes"][m]["vs_quantized"] = metrics(quant, arr)
            arrays.setdefault(m, []).append(arr.astype(np.float16))
        if quant is not None:
            row["quantization_only"] = metrics(img, quant)
        rows.append(row)
    part.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(part, idx=np.array(idx), **{m: np.stack(v) for m, v in arrays.items()})
    (part.with_suffix(".json")).write_text(json.dumps({"rows": rows, "circuit": circ, "seconds": time.perf_counter() - t0}))
    print(f"  [ok] {rid} images {idx[0]}-{idx[-1]}  {time.perf_counter() - t0:.0f}s", flush=True)


def stage_run(worker, of):
    imgs, root = images(), dataset_root()
    cost = {"quantum_patch": 40.0, "quantum_whole": 1.0, "classical": 0.2}
    units = []
    for rec in records():
        w = cost[rec["kind"]] * (8.0 if rec.get("resolution") == 16 and rec["kind"] == "quantum_whole" else 1.0)
        for a in range(0, len(imgs), CHUNK):
            units.append((w, rec, list(range(a, min(a + CHUNK, len(imgs))))))
    units.sort(key=lambda u: (-u[0], u[1]["id"], u[2][0]))
    load, mine = [0.0] * of, [[] for _ in range(of)]
    for u in units:
        j = min(range(of), key=lambda k: load[k])
        mine[j].append(u)
        load[j] += u[0]
    print(f"worker {worker}/{of}: {len(mine[worker])} units", flush=True)
    for _, rec, idx in mine[worker]:
        run_unit(rec, imgs, idx, root)


def agg(vals):
    v = [x for x in vals if x is not None]
    return {"mean": float(np.mean(v)) if v else None, "std": float(np.std(v, ddof=1)) if len(v) > 1 else None,
            "n": len(v), "n_none": len(vals) - len(v)}


def stage_merge():
    imgs = images()
    summary = {"created_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "n_images": len(imgs), "records": {}}
    for rec in records():
        d = OUT / rec["id"]
        parts = sorted((d / "parts").glob("*.npz"))
        rows, arrays, circ, secs = [], {}, None, 0.0
        for p in parts:
            j = json.loads(p.with_suffix(".json").read_text())
            rows += j["rows"]
            circ = circ or j["circuit"]
            secs += j["seconds"]
            z = np.load(p)
            for m in z.files:
                if m != "idx":
                    arrays.setdefault(m, []).append(z[m])
        rows.sort(key=lambda r: r["i"])
        assert [r["i"] for r in rows] == list(range(len(imgs))), f"{rec['id']}: missing images"
        modes = list(rows[0]["modes"])
        keys = list(rows[0]["modes"][modes[0]])

        def summ(sel):
            out = {}
            for m in modes:
                out[m] = {k: {f: agg([r["modes"][m][k][f] for r in sel]) for f in ("mse", "psnr", "ssim")} for k in keys}
                out[m]["n_exact"] = sum(r["modes"][m]["vs_preprocessed"]["exact_match"] for r in sel)
            if "quantization_only" in rows[0]:
                out["quantization_only"] = {f: agg([r["quantization_only"][f] for r in sel]) for f in ("mse", "psnr", "ssim")}
            return out

        s = {"all": summ(rows), "by_role": {ro: summ([r for r in rows if r["role"] == ro]) for ro in ("trainval", "locked_test")},
             "by_class": {c: summ([r for r in rows if r["class"] == c]) for c in CLASSES}}
        cfg = {**rec, "n_images": len(rows), "execution": "classical CPU simulation" if rec["kind"] != "classical" else "classical (no circuit)",
               "simulator": "qiskit-aer statevector + multinomial sampling" if rec["kind"] != "classical" else None,
               "encoder": {"FRQI": "src/frqi/encoder.py::FRQIEncoder", "NEQR": "src/neqr/encoder.py::NEQREncoder"}.get(rec.get("representation")),
               "decoder": "src/reconstruction/reconstructor.py" if rec["kind"] != "classical" else "sklearn PCA inverse_transform (fit on seed-0 train split)",
               "shots_note": "shots per patch (total per image = shots x number of patches)" if rec["kind"] == "quantum_patch" else
                             ("shots per image" if rec["kind"] == "quantum_whole" else None),
               "compute_seconds": secs}
        (d / "config.json").write_text(json.dumps(cfg, indent=1))
        (d / "metrics.json").write_text(json.dumps({"summary": s, "per_image": rows, "circuit": circ}))
        np.savez_compressed(d / "reconstructions.npz", **{m: np.concatenate(v) for m, v in arrays.items()})
        (d / "status.json").write_text(json.dumps({"record_id": rec["id"], "status": "completed", "n_images": len(rows)}))
        summary["records"][rec["id"]] = {"config": cfg, "summary": s, "circuit": circ}
        print(f"  merged {rec['id']}: {len(rows)} images, modes {modes}")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    print("summary written")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["run", "merge", "plan"])
    ap.add_argument("--worker", type=int, default=0)
    ap.add_argument("--of", type=int, default=1)
    a = ap.parse_args()
    if a.stage == "plan":
        print(len(records()), "records x", len(images()), "images")
    elif a.stage == "run":
        stage_run(a.worker, a.of)
    else:
        stage_merge()
