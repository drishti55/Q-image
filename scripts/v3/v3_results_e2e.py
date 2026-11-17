"""Browser check of /quantum-v3 against aggregates/v3_results.json.
Usage: python scripts/v3/v3_results_e2e.py [--base http://127.0.0.1:5173] [--out results/qml_v3/reports/screenshots]"""
import argparse, json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser(); ap.add_argument("--base", default="http://127.0.0.1:5173")
ap.add_argument("--out", default=str(ROOT / "results/qml_v3/reports/screenshots")); a = ap.parse_args()
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
D = json.loads((ROOT / "results/qml_v3/aggregates/v3_results.json").read_text())
res, errs = [], []
def ok(n, c, d=""): res.append({"check": n, "ok": bool(c), "detail": d}); print("PASS" if c else "FAIL", n, d)
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome"); pg = b.new_page(viewport={"width": 1440, "height": 1000})
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
    pg.goto(a.base + "/quantum-v3"); pg.wait_for_selector('[data-testid="v3-groups"]', timeout=20000)
    ok("before/after table has one row per V2 baseline", len(pg.query_selector_all('[data-testid="v3-before-after"] tbody tr')) == len(D["before_after"]))
    ok("statistics table has one row per planned comparison", len(pg.query_selector_all('[data-testid="v3-stats"] tbody tr')) == len(D["comparisons"]))
    ok("group table lists every frozen group", len(pg.query_selector_all('[data-testid="v3-groups"] tbody tr')) == len(D["groups"]))
    h = D["headlines"]["pure_quantum"]; t = pg.inner_text('[data-testid="v3-head-Pure quantum (V3)"]')
    ok("pure-quantum tile shows the validation-selected model and its test accuracy", h["display_name"] in t and f"{100*h['test_accuracy']['mean']:.1f}%" in t, t.replace("\n", " | "))
    ok("headline tiles show the matched classical control", all(pg.query_selector(f'[data-testid="v3-head-matched-{l}"]') for l in ("Pure quantum (V3)", "VQC (V3)", "Hybrid quantum (V3)")))
    ok("product-RY headline carries the classically-computable note", "classically computable" in t)
    ok("protocol banner shows the frozen-selection hash", D["frozen_selection_sha256"][:12] in pg.inner_text('[data-testid="v3-protocol"]'))
    pg.locator('[data-testid="chart-before-after"]').get_by_role('button', name='Table', exact=True).click(); pg.wait_for_timeout(300)
    ok("before/after chart has a table view", pg.query_selector('[data-testid="chart-before-after"] table') is not None)
    pg.screenshot(path=str(out / "v3_results_full.png"), full_page=True)
    m = b.new_page(viewport={"width": 390, "height": 844}); m.goto(a.base + "/quantum-v3"); m.wait_for_timeout(2000)
    ok("no horizontal page scroll at 390 px", not m.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1"))
    m.screenshot(path=str(out / "v3_results_mobile.png"))
    ok("no console or page errors", not errs, str(errs[:3]))
(out / "v3_results_e2e.json").write_text(json.dumps(res, indent=1))
print(f"{sum(r['ok'] for r in res)}/{len(res)} passed"); sys.exit(0 if all(r["ok"] for r in res) else 1)
