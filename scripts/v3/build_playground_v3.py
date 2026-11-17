"""
Build results/qml_v3/playground/playground_3x3.json — the educational data for the 3×3 Algorithm Playground (V3).

Starts from the V2 playground file (read-only; every intermediate value there was computed with the real
implementations) and:
  * REMOVES every classifier output on the artificial grid (predicted classes, class probabilities, logits,
    decision values). The grid is not a steel image, so a "prediction" for it would be meaningless.
  * ADDS per-pixel traces computed with the same real, train-fitted transforms (seed 0): for each of the four given
    pixels, the PCA-8 standard features and PCA-4 angle features of the grid with that pixel set to 0, and the
    resulting change. This shows exactly how one pixel moves the feature vector the classical / quantum models see.
Run: python scripts/v3/build_playground_v3.py
"""
from __future__ import annotations

import json
from datetime import datetime

import numpy as np
from PIL import Image

from common import V2, V3

from src.v2.providers import _fitted_pca

GRID = np.array([[70, 180, 0], [19, 20, 0], [0, 0, 0]], dtype=np.uint8)
GIVEN = [(0, 0), (0, 1), (1, 0), (1, 1)]
DROP = {
    "svm": ("prediction", "decision_ovr"),
    "logreg": ("scores", "probabilities", "softmax_of_scores", "prediction"),
    "qkc.maps.*": ("prediction",), "qkc.rbf_control": ("prediction",),
    "small_cnn.demo": ("logits", "probabilities", "prediction"), "small_cnn.real": ("logits", "probabilities", "prediction"),
    "mobilenet.demo": ("probabilities", "prediction"), "mobilenet.real": ("probabilities", "prediction"),
    "vqc.trained": ("logits", "probabilities", "prediction"), "vqc.untrained": ("logits", "probabilities", "prediction"),
    "vqc.illustrative_adam_step": ("probabilities_after",),
}


def resize(u8, s):
    return np.asarray(Image.fromarray(u8, "L").resize((s, s), Image.Resampling.BILINEAR), dtype=np.float64) / 255.0


def r6(a):
    return np.round(np.asarray(a, float), 6).tolist()


def drop(d):
    removed = []
    for path, keys in DROP.items():
        parts = path.split(".")
        nodes = [d]
        for p in parts:
            nodes = [v for n in nodes for v in (n.values() if p == "*" else [n.get(p)]) if isinstance(v, dict)]
        for n in nodes:
            for k in keys:
                if k in n:
                    del n[k]
                    removed.append(f"{path}.{k}")
    return sorted(set(removed))


def main():
    d = json.loads((V2 / "playground" / "playground_3x3.json").read_text())
    removed = drop(d)
    f8, f4 = _fitted_pca(0, 8, 64), _fitted_pca(0, 4, 64)
    base64 = resize(GRID, 64)[None]
    b8, b4 = f8.transform(base64, "standard")[0], f4.transform(base64, "angle")[0]
    assert np.allclose(b8, d["preprocessing"]["pca"]["8"]["standard"], atol=1e-5), "PCA reproduction mismatch"
    assert np.allclose(b4, d["qkc"]["features"], atol=1e-5), "PCA-4 angle reproduction mismatch"
    traces = []
    for (rr, cc) in GIVEN:
        g = GRID.copy()
        g[rr, cc] = 0
        x64 = resize(g, 64)[None]
        s8, a4 = f8.transform(x64, "standard")[0], f4.transform(x64, "angle")[0]
        v = int(GRID[rr, cc])
        traces.append({"row": rr, "col": cc, "value": v, "normalized": round(v / 255, 6), "flat_index": 3 * rr + cc,
                       "cnn_input": round((v / 255 - 0.5) / 0.25, 6),
                       "pca8_standard_without": r6(s8), "pca8_standard_delta": r6(b8 - s8),
                       "pca4_angle_without": r6(a4), "pca4_angle_delta": r6(b4 - a4)})
    d["pixel_traces"] = traces
    d["flattened_raw_9"] = GRID.reshape(-1).astype(int).tolist()
    d["protocol"] = "V3 educational data"
    d["illustrative"] = True
    d["disclaimer"] = ("Illustrative 3×3 grid (70, 180, 19, 20 + zero padding). It is not a NEU-DET image: no classifier "
                       "output is shown for it, and nothing here is an evaluation result.")
    d["v3_build"] = {"created_at": datetime.now().isoformat(), "source": "results/qml_v2/playground/playground_3x3.json (read-only)",
                     "removed_classifier_outputs": removed,
                     "added": "pixel_traces (real seed-0 train-fitted PCA-8 standard / PCA-4 angle transforms)"}
    out = V3 / "playground" / "playground_3x3.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(d))
    print(f"wrote {out} ({out.stat().st_size // 1024} KB); removed {len(removed)} output fields")
    for t in traces:
        print(t["value"], "Δpca8 L2=%.3f" % np.linalg.norm(t["pca8_standard_delta"]), "Δangle4", np.round(t["pca4_angle_delta"], 3))


if __name__ == "__main__":
    main()
