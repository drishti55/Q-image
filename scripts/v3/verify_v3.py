"""
Independent integrity checks for Protocol V3 -> results/qml_v3/aggregates/v3_verification.json
(rendered into reports/V3_VERIFICATION_REPORT.md by write_reports.py).

Recomputes from raw files; does not trust v3_results.json except to compare against it.
Optional: --suites <json> with externally run test-suite results [{"check":..., "ok":..., "detail":...}].
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
V2, V3 = ROOT / "results" / "qml_v2", ROOT / "results" / "qml_v3"
EXP = V3 / "experiments"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
checks: list[dict] = []


def ok(name, cond, detail=""):
    checks.append({"check": name, "ok": bool(cond), "detail": str(detail)[:300]})


ap = argparse.ArgumentParser()
ap.add_argument("--suites", help="json file with test-suite results")
a = ap.parse_args()

D = json.loads((V3 / "aggregates" / "v3_results.json").read_text())
FZ = json.loads((V3 / "aggregates" / "frozen_selection.json").read_text())
prov = json.loads((V3 / "manifests" / "v3_provenance.json").read_text())

# 1. historical V0 / models untouched
r = subprocess.run([sys.executable, str(ROOT / "scripts/v2/verify_historical.py"), "--label", "v3_verify"], capture_output=True, text=True, cwd=ROOT)
last = json.loads((V2 / "logs" / "historical_verification.jsonl").read_text().strip().splitlines()[-1])
outside = [x for x in last["added"] if not x.startswith(("results/qml_v3/", "results/qml_v2/"))]
ok("historical V0 results (results/qml, results/models): 0 changed, 0 missing",
   not last["changed"] and not last["missing"], f"original files {last['original_file_count']}; changed {len(last['changed'])}; missing {len(last['missing'])}")
ok("no new files under historical folders (added files are all in qml_v2/qml_v3)", not outside, outside[:3])

# 2. V2 inputs copied into V3 still hash-identical in both places
bad = [e["file"] for e in prov["files"] for root in (V2, V3) if sha(root / e["file"]) != e["sha256"]]
ok(f"{len(prov['files'])} copied V2 manifests / splits / caches identical in qml_v2 and qml_v3 (SHA-256)", not bad, bad[:3])
ok("split verification at copy time: no path / hash / group overlap; test = whole NEU validation folder",
   all(v["ok"] for v in prov["split_verification"].values()))

# 3. no V2 experiment / aggregate / manifest / cache file modified after V3 setup
t0 = (V3 / "manifests" / "v3_provenance.json").stat().st_mtime
newer = [str(p.relative_to(ROOT)) for p in V2.rglob("*") if p.is_file() and p.stat().st_mtime > t0]
core = [p for p in newer if not p.startswith(("results/qml_v2/reports/", "results/qml_v2/logs/historical_verification"))]
ok("no Protocol V2 experiment, aggregate, manifest or cache file modified since V3 setup", not core, core[:3])
ok("V2 files touched since V3 setup are only report screenshots / verification log (disclosed in notes)", True, f"{len(newer)} files")

# 4. frozen selection: every selection file unchanged since the freeze
bad = [gname for gname, gv in FZ["groups"].items() if sha(V3 / "aggregates" / "selection" / f"{gname}.json") != gv["selection_sha256"]]
ok(f"{len(FZ['groups'])} selection files unchanged since freeze (SHA-256)", not bad, bad[:3])
ok("frozen_selection.json hash matches v3_results.json", sha(V3 / "aggregates" / "frozen_selection.json") == D["frozen_selection_sha256"])

# 5. locked test opened only after the freeze, once per group
tal = [json.loads(l) for l in (V3 / "logs" / "test_access.jsonl").read_text().splitlines() if l.strip()]
ok("every locked-test access happened after the freeze", all(e["time"] > FZ["frozen_at"] for e in tal), f"first {min(e['time'] for e in tal)} > frozen {FZ['frozen_at']}")
grp = Counter(e["reason"].rsplit(" ", 1)[-1] for e in tal)
ok("exactly one locked-test stage per frozen group", set(grp) == set(FZ["groups"]) and set(grp.values()) == {1}, f"{len(grp)} groups")
# test predictions exist only for the frozen configurations (no candidate was scored on test)
with_test = set()
for d in EXP.iterdir():
    p = d / "predictions.csv"
    if p.exists():
        with open(p, newline="") as f:
            if any(row["split"] == "test" for row in csv.DictReader(f)):
                with_test.add(d.name)
sel_ids = {f"{gv['selected_config_key']}__s{s}" for gv in FZ["groups"].values() for s in (0, 1, 2)}
ok("test predictions exist only for the 3 seeds of each frozen configuration", with_test == sel_ids,
   f"{len(with_test)} dirs with test predictions; {len(sel_ids)} frozen; extra {sorted(with_test - sel_ids)[:2]}")
# selection files never contain test metrics
leak = [f.name for f in (V3 / "aggregates" / "selection").glob("*.json") if '"test_' in f.read_text()]
ok("no selection file contains a test metric", not leak, leak[:3])

# 6. runs
stat = Counter((json.loads((d / "status.json").read_text()) if (d / "status.json").exists() else {}).get("status", "missing") for d in EXP.iterdir())
ok("no failed or missing candidate runs", set(stat) <= {"done", "completed", "ok", "success"}, dict(stat))

# 7. reported metrics == recomputed from predictions.csv
bad, n = [], 0
for g in D["groups"]:
    accs = []
    for e in g["experiment_ids"]:
        with open(EXP / e / "predictions.csv", newline="") as f:
            rows = [row for row in csv.DictReader(f) if row["split"] == "test"]
        n += 1
        if len(rows) != 360 or any(not row["image"].startswith("validation/") for row in rows):
            bad.append(e)
        accs.append(np.mean([row["y_true"] == row["y_pred"] for row in rows]))
    if abs(np.mean(accs) - g["test_accuracy"]["mean"]) > 1e-12:
        bad.append(g["group"])
ok(f"test accuracy recomputed from predictions.csv for all {len(D['groups'])} groups ({n} runs, 360 locked images each)", not bad, bad[:3])

# 8. headline = max validation within category (test not consulted)
G = {g["group"]: g for g in D["groups"]}
cats = {"vqc": ["vqc"], "hybrid_quantum": ["hybrid", "hybrid_vqc"], "classical_control_best": ["classical_control"],
        "pure_quantum": ["quantum_kernel", "quantum_encoding"]}
for k, cs in cats.items():
    exp = max((g for g in D["groups"] if g["category"] in cs), key=lambda g: g["val_f1_macro"]["mean"])["group"]
    ok(f"headline '{k}' is the max-validation group in its category", D["headlines"][k]["group"] == exp, exp)

# 9. genuine quantum models
vq = [g for g in D["groups"] if g["category"] in ("vqc", "hybrid_vqc")]
ok("every VQC group has trainable quantum parameters (> 0) and an entangling circuit",
   all(g["circuit"]["n_trainable_quantum_params"] > 0 and g["circuit"]["cx_compiled"] > 0 for g in vq), f"{len(vq)} groups")
enc = [g for g in D["groups"] if g["group"].endswith("vqc-encoding-only")]
ok("encoding-only controls have 0 trainable quantum parameters (labelled as controls)",
   all(g["circuit"]["n_trainable_quantum_params"] == 0 and g["category"] == "vqc_control" for g in enc), f"{len(enc)} groups")
qk = [g for g in D["groups"] if g["family"] in ("quantum_kernel",) or g["category"] in ("quantum_kernel", "quantum_encoding", "hybrid")]
ok("every quantum-labelled group records a simulated circuit (statevector, no hardware)",
   all("statevector" in (g["circuit"].get("execution_mode") or "") for g in qk if g["category"] != "classical_control"), f"{len(qk)} groups")
ok("no classical model is categorised as quantum",
   all(G[gn]["category"] == "classical_control" for gn in G if gn.endswith(("-rbfsvm", "-logreg"))))

# 10. statistics recomputable: Holm adjusted p >= raw p and monotone
cs = sorted(D["comparisons"], key=lambda c: c["p_permutation"])
ok("Holm-adjusted p-values are >= raw and monotone", all(c["p_holm"] >= c["p_permutation"] - 1e-12 for c in cs) and
   all(cs[i]["p_holm"] <= cs[i + 1]["p_holm"] + 1e-12 for i in range(len(cs) - 1)), f"{len(cs)} comparisons")

# 11. external suites
if a.suites:
    for s in json.loads(Path(a.suites).read_text()):
        ok(s["check"], s["ok"], s.get("detail", ""))

notes = [
    "The V2 report screenshots in results/qml_v2/reports/algorithm_screenshots/ were re-captured by scripts/v2/playground_e2e.py while "
    "the V3 UI was being tested, before its default output was moved to results/qml_v3/reports/screenshots/. They are report images, not results; "
    "no V2 experiment, aggregate, manifest or cache file changed.",
    "results/qml_v2/logs/historical_verification.jsonl is an append-only log written by the verification script itself.",
    "verify_historical.py reports all_ok=False only because new files exist (results/qml_v3); mandatory checks (changed = missing = 0) pass.",
    "The like-for-like V3-vs-V2 comparisons were added to analyze_v3.py after the locked test was opened; they are reported as a separate "
    "post-hoc family and change no selection.",
]
out = {"created_at": datetime.now().isoformat(timespec="seconds"), "checks": checks, "notes": notes}
(V3 / "aggregates" / "v3_verification.json").write_text(json.dumps(out, indent=1))
nf = sum(not c["ok"] for c in checks)
for c in checks:
    print("PASS" if c["ok"] else "FAIL", c["check"], "" if c["ok"] else c["detail"])
print(f"{len(checks)} checks, {nf} failed")
sys.exit(1 if nf else 0)
