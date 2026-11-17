"""Per-image prediction index: for each of the 360 locked-test images, the saved prediction of EVERY selected model
(V2: 88 groups, V3: 70, V4: 5) for each seed. Read-only over results/qml_v2, qml_v3, qml_v4; writes
results/qml_v4/aggregates/per_image_predictions.json. No model is re-run; values are copied from predictions.csv."""
import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "results"
CLASSES = ["crazing", "inclusion", "patches", "pitted_surface", "rolled-in_scale", "scratches"]


def kind(family, category=""):
    f = (family or "") + " " + (category or "")
    if "classical" in f and "quantum_inspired" not in f and "quantum" not in f.replace("quantum_inspired", ""):
        return "classical"
    if "quantum_inspired" in f:
        return "quantum-inspired (classical)"
    if "hybrid" in f:
        return "hybrid"
    return "quantum"


models = []
A2 = json.loads((R / "qml_v2/aggregates/analysis.json").read_text())["selected"]
for g, v in A2.items():
    models.append({"id": g, "protocol": "V2", "name": v["model_name"], "family": v["family"], "kind": kind(v["family"]),
                   "category": v["category"], "n_qubits": v.get("n_qubits"), "dirs": [R / "qml_v2/experiments" / e for e in v["experiment_ids"]],
                   "test_accuracy": v["test_accuracy"]["mean"]})
for v in json.loads((R / "qml_v3/aggregates/v3_results.json").read_text())["groups"]:
    k = "classical" if v["category"] == "classical_control" else "hybrid" if v["category"] in ("hybrid", "hybrid_vqc") else \
        "control" if v["category"] == "vqc_control" else "quantum"
    models.append({"id": v["group"], "protocol": "V3", "name": v["display_name"], "family": v["family"], "kind": k, "category": v["category"],
                   "n_qubits": v.get("n_qubits"), "dirs": [R / "qml_v3/experiments" / e for e in v["experiment_ids"]],
                   "test_accuracy": v["test_accuracy"]["mean"]})
D4 = json.loads((R / "qml_v4/aggregates/v4_results.json").read_text())
for g, v in D4["groups"].items():
    models.append({"id": g, "protocol": "V4", "name": v["model_name"], "family": "classical" if "patchmom" in g else "quantum_kernel",
                   "kind": "classical" if "patchmom" in g else "quantum", "category": "V4", "n_qubits": (v.get("quantum") or {}).get("n_qubits"),
                   "dirs": [R / "qml_v4/experiments" / e for e in v["experiment_ids"]], "test_accuracy": v["test_accuracy"]["mean"]})

per_image = defaultdict(dict)
truth = {}
for m in models:
    for s, d in enumerate(m["dirs"]):
        with open(d / "predictions.csv", newline="") as f:
            for row in csv.DictReader(f):
                if row["split"] != "test":
                    continue
                truth[row["image"]] = int(row["y_true"])
                per_image[row["image"]].setdefault(m["id"], [None, None, None])[s] = int(row["y_pred"])
assert len(per_image) == 360 and all(len(v) == len(models) for v in per_image.values())
out = {"classes": CLASSES, "note": "copied from each selected model's saved predictions.csv (seeds 0,1,2); nothing re-run",
       "models": [{k: v for k, v in m.items() if k != "dirs"} for m in models],
       "images": {img: {"y_true": truth[img], "preds": per_image[img]} for img in sorted(per_image)}}
(R / "qml_v4/aggregates/per_image_predictions.json").write_text(json.dumps(out))
hard = sorted(out["images"], key=lambda i: sum(p == out["images"][i]["y_true"] for ps in out["images"][i]["preds"].values() for p in ps))
print(f"{len(models)} models x {len(per_image)} images; hardest image: {hard[0]}")
