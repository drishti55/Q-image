"""Integrity checks for Protocol V4 -> results/qml_v4/aggregates/v4_verification.json"""
import csv, hashlib, json, subprocess, sys
from datetime import datetime
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
V2, V3, V4 = (ROOT / "results" / x for x in ("qml_v2", "qml_v3", "qml_v4"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
C = []
def ok(n, c, d=""): C.append({"check": n, "ok": bool(c), "detail": str(d)[:300]})
D = json.loads((V4 / "aggregates" / "v4_results.json").read_text()); FZ = json.loads((V4 / "aggregates" / "frozen_selection.json").read_text())
subprocess.run([sys.executable, str(ROOT / "scripts/v2/verify_historical.py"), "--label", "v4_verify"], capture_output=True, cwd=ROOT)
last = json.loads((V2 / "logs" / "historical_verification.jsonl").read_text().strip().splitlines()[-1])
ok("historical V0 results: 0 changed, 0 missing", not last["changed"] and not last["missing"], f"{last['original_file_count']} files")
v3p = json.loads((V3 / "manifests" / "v3_provenance.json").read_text())["files"]
ok("V2 manifest/splits/caches unchanged (SHA-256, in qml_v2 and qml_v3)", all(sha(r / e["file"]) == e["sha256"] for e in v3p for r in (V2, V3)), f"{len(v3p)} files x 2")
v4p = json.loads((V4 / "manifests" / "v4_provenance.json").read_text())["files"]
ok("V4 copies of manifest/splits/image caches identical to the V3/V2 originals", all(sha(V4 / e["file"]) == e["sha256"] for e in v4p), f"{len(v4p)} files")
t0 = (V3 / "aggregates" / "v3_verification.json").stat().st_mtime
for name, root in (("V2", V2), ("V3", V3)):
    newer = [str(p.relative_to(ROOT)) for p in root.rglob("*") if p.is_file() and p.stat().st_mtime > t0 and p.name != ".DS_Store"
             and "/reports/" not in str(p) and not p.name.startswith("historical_verification")]
    ok(f"no Protocol {name} result file modified or added since V3 was finalised", not newer, newer[:3])
v3fz = json.loads((V3 / "aggregates" / "frozen_selection.json").read_text())
ok("all 70 V3 selection files unchanged since the V3 freeze", all(sha(V3 / "aggregates" / "selection" / f"{g}.json") == v["selection_sha256"] for g, v in v3fz["groups"].items()))
ok("V4 selection files unchanged since the V4 freeze", all(sha(V4 / "aggregates" / "selection" / f"{g}.json") == v["selection_sha256"] for g, v in FZ["groups"].items()))
tal = D["test_access_log"]
ok("every V4 locked-test access after the freeze, one per frozen group", all(e["time"] > FZ["frozen_at"] for e in tal) and len(tal) == len(FZ["groups"]), f"{len(tal)} events")
with_test = set()
for d in (V4 / "experiments").iterdir():
    with open(d / "predictions.csv", newline="") as f:
        if any(r["split"] == "test" for r in csv.DictReader(f)): with_test.add(d.name)
sel = {f"{v['selected_config_key']}__s{s}" for v in FZ["groups"].values() for s in (0, 1, 2)}
ok("test predictions exist only for the frozen configurations", with_test == sel, f"{len(with_test)} vs {len(sel)}")
ok("no selection file contains a test metric", not any('"test_' in f.read_text() for f in (V4 / "aggregates" / "selection").glob("*.json")))
ok("864 candidate runs, 0 failed", D["counts"]["candidate_runs"] == 864 and D["counts"]["failed_runs"] == 0)
bad = []
for g, r in D["groups"].items():
    accs = []
    for e in r["experiment_ids"]:
        with open(V4 / "experiments" / e / "predictions.csv", newline="") as f:
            rows = [x for x in csv.DictReader(f) if x["split"] == "test"]
        if len(rows) != 360 or any(not x["image"].startswith("validation/") for x in rows): bad.append(e)
        accs.append(np.mean([x["y_true"] == x["y_pred"] for x in rows]))
    if abs(np.mean(accs) - r["test_accuracy"]["mean"]) > 1e-12: bad.append(g)
ok("test accuracy recomputed from predictions.csv (360 locked images per run)", not bad, bad)
for k, gs in (("frqi", ("V4-frqi-p4", "V4-frqi-p8")), ("neqr", ("V4-neqr-p2", "V4-neqr-p4"))):
    ok(f"{k.upper()} headline chosen by validation", D["headlines"][k] == max(gs, key=lambda g: D["groups"][g]["val_f1_macro"]["mean"]))
ok("comparisons are exactly the 8 pre-declared ones", len(D["comparisons"]) == len(FZ["plan"]["comparisons"]) == 8)
q = [g for g in D["groups"] if g != "V4-patchmom-rbfsvm"]
ok("every V4 quantum group records a real FRQI/NEQR encoder circuit (Qiskit, transpiled)", all(D["groups"][g]["circuit"] and D["groups"][g]["circuit"]["gates_compiled"] > 0 for g in q))
ok("classical control has no circuit and is labelled classical", D["groups"]["V4-patchmom-rbfsvm"]["circuit"] is None)
notes = ["Before the V4 grid was written, patch geometries were explored on the internal VALIDATION split only (no test data). "
         "That exploration used the V3 data loader and wrote six 32x32 train/val image-cache files into results/qml_v3/cache; "
         "they were deleted minutes later (they were additions, not modifications; all V3 records and hashes are unchanged).",
         "A first V4 launch failed after 1 minute (disk full: checkpoints stored training density matrices). Its partial "
         "candidate outputs (validation only, no test access) were deleted and the grid was re-run from scratch with small "
         "checkpoints; a reloaded checkpoint was verified to reproduce its validation predictions exactly.",
         "The locked test set has been used by Protocols V2 and V3 before; V4 is a new method frozen on validation and "
         "evaluated once, but readers should know the test set is not 'fresh' for the project as a whole."]
out = {"created_at": datetime.now().isoformat(timespec="seconds"), "checks": C, "notes": notes}
(V4 / "aggregates" / "v4_verification.json").write_text(json.dumps(out, indent=1))
for c in C: print("PASS" if c["ok"] else "FAIL", c["check"], "" if c["ok"] else c["detail"])
print(f"{len(C)} checks, {sum(not c['ok'] for c in C)} failed"); sys.exit(any(not c["ok"] for c in C))
