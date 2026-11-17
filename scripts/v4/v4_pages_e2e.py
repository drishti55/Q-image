"""Browser checks for /how-it-works, /reconstruction-full and /quantum-v4 (needs backend :8000 + Vite :5173).
Usage: <playwright python> scripts/v4/v4_pages_e2e.py [--base http://127.0.0.1:5173] [--out results/qml_v4/reports/screenshots]"""
import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
ap.add_argument("--base", default="http://127.0.0.1:5173")
ap.add_argument("--out", default=str(ROOT / "results/qml_v4/reports/screenshots"))
a = ap.parse_args()
out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)
D = json.loads((ROOT / "results/qml_v4/aggregates/v4_results.json").read_text())
res, errs = [], []


def ok(n, c, d=""):
    res.append({"check": n, "ok": bool(c), "detail": str(d)[:200]})
    print("PASS" if c else "FAIL", n, "" if c else d)


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1440, "height": 1100})
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errs.append(m.text))

    # ── how it works ──
    pg.goto(a.base + "/how-it-works")
    pg.wait_for_selector('[data-testid="hiw-stage"]', timeout=60000)
    ok("how-it-works: image list shows the 60 test images of the chosen class", pg.locator('[data-testid="hiw-image"]').count() == 60)
    ok("breadcrumb names Protocol V4", "Protocol V4" in pg.inner_text("nav[aria-label=Breadcrumb]"))
    pg.click('button[aria-label="Play animation"]')
    pg.wait_for_timeout(4000)
    ok("play advances the animation", pg.get_attribute('[data-testid="hiw-stage"]', "data-step") not in ("0", None))
    pg.click('button[aria-label="Pause"]')
    for s, wait, name in ((3, 7600, "04_encode"), (4, 5800, "05_mix"), (5, 3600, "06_kernel"), (6, 3000, "07_svm"), (7, 5600, "08_measure"), (8, 1500, "09_verdicts")):
        pg.click(f'button[aria-label="Go to step {s + 1}"]')
        pg.wait_for_timeout(wait)
        pg.screenshot(path=str(out / f"hiw_{name}.png"))
    pg.click('button[aria-label="Go to step 7"]')
    pg.wait_for_timeout(3200)
    v = pg.inner_text('[data-testid="hiw-verdict"]')
    ok("SVM step shows a verdict identical to the saved locked-test prediction", "identical to the saved locked-test prediction" in v, v)
    pg.click('button[aria-label="Go to step 9"]')
    pg.wait_for_selector('[data-testid="verdict-cell"]', timeout=20000)
    ok("verdict grid has one cell per model (163)", pg.locator('[data-testid="verdict-cell"]').count() == 163)
    pg.click('button[aria-label="Go to step 8"]')
    pg.wait_for_timeout(5600)
    ok("measurement step shows real shot reconstructions", "shots" in pg.inner_text('[data-testid="hiw-stage"]') and "MSE" in pg.inner_text('[data-testid="hiw-stage"]'))
    pg.get_by_role("button", name="Hardest").click()
    pg.wait_for_timeout(2500)
    ok("hardest-image button loads a new image", pg.get_attribute('[data-testid="hiw-stage"]', "data-step") == "0")

    # ── reconstruction (all) ──
    pg.goto(a.base + "/reconstruction-full")
    pg.wait_for_selector('[data-testid="recon-table"]', timeout=60000)
    ok("reconstruction table lists all 20 methods", pg.locator('[data-testid="recon-table"] tbody tr').count() == 20)
    ok("banner reports 1,800 images", "1,800 images" in pg.inner_text('[data-testid="recon-banner"]'))
    pg.wait_for_selector('[data-testid="recon-browser"]', timeout=30000)
    pg.click('[data-testid="recon-animate"]')
    pg.wait_for_timeout(1500)
    pg.screenshot(path=str(out / "reconstruction_full.png"), full_page=True)
    ok("browser shows original + 5 measured modes", pg.locator('[data-testid="recon-browser"] canvas').count() == 6)

    # ── V4 results ──
    pg.goto(a.base + "/quantum-v4")
    pg.wait_for_selector('[data-testid="v4-comparisons"]', timeout=30000)
    ok("V4 comparisons table has the 8 pre-declared rows", pg.locator('[data-testid="v4-comparisons"] tbody tr').count() == 8)
    fr = D["groups"][D["headlines"]["frqi"]]["test_accuracy"]["mean"]
    ok("FRQI tile shows the frozen FRQI test accuracy", f"{100 * fr:.1f}%" in pg.inner_text('[data-testid="v4-tile-FRQI"]'))
    pg.screenshot(path=str(out / "v4_results.png"), full_page=True)

    m = b.new_page(viewport={"width": 390, "height": 844})
    for path in ("/how-it-works", "/reconstruction-full", "/quantum-v4"):
        m.goto(a.base + path)
        m.wait_for_timeout(3500)
        ok(f"{path}: no horizontal scroll at 390 px", not m.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1"))
    ok("no console or page errors", not errs, errs[:3])

(out / "v4_pages_e2e.json").write_text(json.dumps(res, indent=1))
print(f"{sum(r['ok'] for r in res)}/{len(res)} passed")
sys.exit(0 if all(r["ok"] for r in res) else 1)
