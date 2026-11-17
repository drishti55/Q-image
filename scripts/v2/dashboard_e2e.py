"""
Real-browser end-to-end check of the Q-ImageLab dashboard (Protocol V2 + Historical V0).

Requires: a running backend (python api_main.py, :8000) and frontend (cd frontend && npm run dev, :5173), and
Playwright (`pip install playwright`, not a project dependency). Uses the installed Google Chrome (channel="chrome").
Usage:  python scripts/v2/dashboard_e2e.py [--base http://127.0.0.1:5173] [--out results/qml_v2/reports/dashboard_screenshots]
Writes <out>/e2e_results.json and screenshots; exit code 1 if any check fails.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def api(base: str, path: str):
    with urllib.request.urlopen(f"{base}/api/v2{path}") as r:
        return json.loads(r.read())


class Run:
    def __init__(self):
        self.checks = []

    def check(self, name: str, ok: bool, detail: str = ""):
        self.checks.append({"check": name, "ok": bool(ok), "detail": detail})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""), flush=True)


def watch(page: Page, bucket: dict):
    page.on("console", lambda m: m.type == "error" and bucket["console"].append(m.text[:300]))
    page.on("pageerror", lambda e: bucket["console"].append("pageerror: " + str(e)[:300]))
    page.on("response", lambda r: ("/api/" in r.url and r.status >= 400) and bucket["http"].append(f"{r.status} {r.url}"))


def visit(page: Page, base: str, path: str, wait_text: str | None = None, timeout=60000):
    page.goto(base + path, wait_until="networkidle", timeout=timeout)
    if wait_text:
        page.get_by_text(wait_text, exact=False).first.wait_for(timeout=timeout)
    page.wait_for_timeout(600)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:5173")
    ap.add_argument("--out", default=str(ROOT / "results/qml_v2/reports/dashboard_screenshots"))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    R = Run()
    summary = api(a.base, "/summary")
    models = api(a.base, "/models")
    bucket = {"console": [], "http": []}

    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        page = ctx.new_page()
        watch(page, bucket)

        # 1. Overview at "/"
        visit(page, a.base, "/", "Three things to remember")
        body = page.inner_text("main")
        R.check("/ opens the Protocol V2 overview", "protocol v2" in body.lower() and "Can quantum machine learning" in body)
        R.check("overview counts come from /api/v2/summary",
                str(summary["counts"]["selected_configurations"]) in body and str(summary["dataset"]["locked_test_images"]) in body
                and f"{summary['counts']['experiments']['total']:,}" in body)
        nav_links = page.locator("aside nav a").count()
        R.check("sidebar is short (≤ 17 links incl. logo; +3 for the V4 pages: How it works, V4 results, Reconstruction all images)", nav_links <= 17, f"{nav_links} links")
        best = summary["best"]["overall"]["test_accuracy"]
        R.check("best overall accuracy displayed", f"{best * 100:.1f}%" in body, f"{best * 100:.1f}%")
        q = summary["best"]["quantum"]["test_accuracy"]
        R.check("best purely quantum accuracy displayed", f"{q * 100:.1f}%" in body, f"{q * 100:.1f}%")
        R.check("no V0 KPI text on V2 overview", "Images evaluated" not in body and "3,632" not in body)
        R.check("simulation disclaimer shown", "no quantum hardware" in body.lower())
        page.screenshot(path=str(out / "01_v2_overview.png"), full_page=True)

        # 2. Experiments V2
        visit(page, a.base, "/experiments-v2", "Run history")
        body = page.inner_text("main")
        R.check("/experiments-v2 shows V2 runs + split integrity", "Run history" in body and "verified" in body)
        opts = page.get_by_label("Status", exact=True).locator("option").all_inner_texts()
        R.check("status filter offers only statuses present in the data", "failed" not in opts, f"options={opts}")
        page.get_by_label("Seed", exact=True).select_option("1")
        page.wait_for_timeout(300)
        seeds = set(page.locator("tbody tr td:nth-child(7)").all_inner_texts())
        R.check("experiments seed filter works", seeds == {"1"}, f"seeds shown={sorted(seeds)}")
        page.get_by_label("Seed", exact=True).select_option("all")
        first = page.locator("table a[href^='/experiments/']").first
        eid = first.inner_text()
        first.click()
        page.wait_for_url(re.compile(r"/experiments/"))
        page.get_by_text("Confusion matrices").first.wait_for()
        R.check("experiment detail page opens from history", eid in page.inner_text("main"), eid)
        page.reload(wait_until="networkidle")
        page.get_by_text("Confusion matrices").first.wait_for()
        R.check("browser refresh on deep link /experiments/:id works", eid in page.inner_text("main"))
        page.screenshot(path=str(out / "02_experiment_detail.png"), full_page=False)

        # 3. Model comparison (all selected configurations)
        visit(page, a.base, "/models", "Leaderboard")
        lb = page.inner_text("main")
        main_models = [m for m in models["models"] if not (m["shots"] or m["is_ablation"] or m["is_legacy_relabelled"])]
        best_main = max(main_models, key=lambda m: m["test_accuracy"]["mean"])
        first_row = page.locator("main ol > li").first.inner_text()
        R.check("leaderboard (default) ranks the best model first", best_main["display_name"] in first_row, first_row.split(chr(10))[1] if chr(10) in first_row else first_row)
        R.check("leaderboard shows top 12 by default", page.locator("main ol > li").count() == min(12, len(main_models)), f"{page.locator('main ol > li').count()} rows")
        page.wait_for_timeout(800)
        page.screenshot(path=str(out / "03a_model_leaderboard.png"), full_page=True)
        page.get_by_role("button", name="Quantum kernel").click()
        page.wait_for_timeout(300)
        nq = sum(1 for m in main_models if m["category"] == "Quantum kernel models")
        R.check("leaderboard family filter", page.locator("main ol > li").count() == min(12, nq), f"expected {min(12, nq)}")
        page.get_by_role("button", name="Advanced", exact=True).click()
        page.get_by_text("Showing").first.wait_for()
        body = page.inner_text("main")
        n = models["count"]
        R.check(f"model comparison lists all {n} configurations", f"Showing {n} of {n}" in body)
        rows = page.locator("tbody tr[id^='row-']").count()
        R.check("table row count equals API count", rows == n, f"rows={rows}")
        # every display name present
        missing = [m["display_name"] for m in models["models"] if m["display_name"] not in body]
        R.check("every configuration name rendered", not missing, f"missing={missing[:3]}")
        first_acc = page.locator("tbody tr[id^='row-'] td:nth-child(6)").first.inner_text()
        top = max(models["models"], key=lambda m: m["test_accuracy"]["mean"])
        R.check("default sort = test accuracy descending", first_acc.startswith(f"{top['test_accuracy']['mean'] * 100:.1f}"), first_acc)
        page.get_by_label("Search models").fill("ZZ-full")
        page.wait_for_timeout(300)
        exp = sum(1 for m in models["models"] if "zz-full" in f"{m['display_name']} {m['group']} {m['model_name']}".lower())
        R.check("search filters configurations", f"Showing {exp} of {n}" in page.inner_text("main"), f"expected {exp}")
        page.get_by_label("Search models").fill("")
        page.get_by_label("Model family", exact=True).select_option("Variational quantum classifiers")
        page.wait_for_timeout(300)
        nv = sum(1 for m in models["models"] if m["category"] == "Variational quantum classifiers")
        R.check("family filter works", f"Showing {nv} of {n}" in page.inner_text("main"), f"expected {nv}")
        page.get_by_label("Model family", exact=True).select_option("all")
        page.get_by_label("Execution", exact=True).select_option("shots")
        page.wait_for_timeout(300)
        ns = sum(1 for m in models["models"] if m["execution"].startswith("finite"))
        R.check("exact vs finite-shot filter works", f"Showing {ns} of {n}" in page.inner_text("main"), f"expected {ns}")
        page.get_by_label("Execution", exact=True).select_option("all")
        page.get_by_label("Qubits", exact=True).select_option("8")
        page.wait_for_timeout(300)
        n8 = sum(1 for m in models["models"] if m["n_qubits"] == 8)
        R.check("qubit filter works", f"Showing {n8} of {n}" in page.inner_text("main"), f"expected {n8}")
        page.get_by_role("button", name="Reset").click()
        page.get_by_text("Macro-F1").first.click()  # sort by F1
        page.wait_for_timeout(300)
        boxes = page.locator("tbody tr[id^='row-'] input[type=checkbox]")
        boxes.nth(0).check()
        boxes.nth(1).check()
        page.wait_for_timeout(400)
        R.check("side-by-side comparison opens", "Side-by-side comparison (2)" in page.inner_text("main"))
        page.locator("tbody tr[id^='row-'] button").first.click()
        page.wait_for_timeout(300)
        R.check("row expands to seed-wise results", "95% CI (acc.)" in page.inner_text("main"))
        page.screenshot(path=str(out / "03_model_comparison.png"), full_page=False)

        # 4. Quantum image encoding
        visit(page, a.base, "/encoding", "FRQI — Flexible Representation")
        body = page.inner_text("main")
        R.check("encoding page shows FRQI and NEQR sections + comparison", "NEQR — Novel Enhanced" in body and "FRQI vs NEQR — what the data shows" in body)
        R.check("encoding page uses recorded compiled gate counts", "16,690" in body and "8,339" in body)
        page.screenshot(path=str(out / "04_quantum_encoding.png"), full_page=True)

        # 5. Circuit explorer
        visit(page, a.base, "/circuits", "circuit configurations")
        page.locator("svg[aria-label^='Circuit diagram']").first.wait_for(timeout=60000)
        R.check("circuit diagram renders", page.locator("svg[aria-label^='Circuit diagram']").count() == 1)
        page.get_by_role("button", name="Quantum kernel feature maps").click()
        page.get_by_text("QKC ZZ-full · 8 qubits").first.click()
        page.wait_for_timeout(1200)
        body = page.inner_text("main")
        circ = next(c for c in api(a.base, "/circuits")["circuits"] if c["circuit_key"] == "qkc|zz_full|reps1|q8")
        det = api(a.base, f"/circuits/{circ['experiment_id']}")
        R.check("selected circuit matches executed experiment", det["experiment_id"] in body and "Measurement configuration" in body)
        R.check("logical gate count of executed circuit displayed", str(det["logical_gates_displayed_circuit"]) in body)
        page.screenshot(path=str(out / "05_circuit_explorer.png"), full_page=False)

        # 6. Reconstruction studio
        visit(page, a.base, "/reconstruction", "Reconstruction record")
        page.locator("img[alt^='reconstructed']").first.wait_for(timeout=60000)
        page.get_by_label("Reconstruction record").select_option("R-NEQR-8x8-b4")
        page.get_by_label("Compare with").select_option("R-FRQI-8x8")
        page.get_by_label("Image", exact=True).select_option("29")
        page.wait_for_timeout(1500)
        imgs = page.locator("main img")
        loaded = page.evaluate("Array.from(document.querySelectorAll('main img')).map(i => i.complete && i.naturalWidth > 0)")
        R.check("reconstruction images load (original/reconstructed/diff × 2 records)", imgs.count() == 6 and all(loaded), f"{sum(loaded)}/{imgs.count()}")
        R.check("scratches image (index 29) available", "Scratches" in page.inner_text("main"))
        page.screenshot(path=str(out / "06_reconstruction_studio.png"), full_page=False)

        # 7. Classification analysis
        visit(page, a.base, "/classification", "Weak classes")
        page.get_by_text("Confusion matrix (locked test)").first.wait_for(timeout=60000)
        body = page.inner_text("main")
        R.check("classification shows confusion matrix, per-class and seed-wise", "Seed-wise performance" in body and "Per-class precision" in body)
        page.get_by_role("button", name="Pixel-based inputs").wait_for(timeout=60000)
        body = page.inner_text("main")
        R.check("weak-class panel shown", "rolled-in scale f1 · pixel models" in body.lower())
        page.screenshot(path=str(out / "07_classification.png"), full_page=False)

        # 8. Historical V0
        visit(page, a.base, "/historical-v0", "Why V0 results are not comparable")
        body = page.inner_text("main")
        R.check("/historical-v0 opens labelled read-only V0", "Historical Results — Protocol V0" in body and "read-only" in body)
        page.screenshot(path=str(out / "08_historical_v0.png"), full_page=False)
        visit(page, a.base, "/historical-v0/qml-lab")
        page.wait_for_timeout(1500)
        R.check("V0 pages carry the historical banner", "Historical Results — Protocol V0 (read-only)" in page.inner_text("main"))
        R.check("breadcrumb marks V0 pages", "Historical V0" in page.inner_text("header"))
        visit(page, a.base, "/quantum-ml-lab?tab=models")
        R.check("old V0 URL redirects into /historical-v0 (query kept)", "/historical-v0/qml-lab?tab=models" in page.url, page.url)

        # 9. Presentation mode
        visit(page, a.base, "/present", "The problem")
        page.wait_for_timeout(800)
        ok_imgs = page.evaluate("Array.from(document.querySelectorAll('main img')).filter(i => i.complete && i.naturalWidth > 0).length")
        R.check("presentation slide 1 shows a real sample image for every class", ok_imgs == summary["dataset"]["n_classes"], f"{ok_imgs} images")
        R.check("presentation renders full-screen (no sidebar)", page.locator("aside").count() == 0)
        page.wait_for_timeout(1000)
        page.screenshot(path=str(out / "10_presentation_slide1.png"))
        page.keyboard.press("ArrowRight")
        page.get_by_text("locked away").first.wait_for()
        R.check("arrow key advances to slide 2", "slide=2" in page.url)
        for _ in range(3):
            page.keyboard.press("ArrowRight")
        page.get_by_text("Best accuracy of each family").first.wait_for()
        R.check("results slide shows best accuracies from the API", f"{best * 100:.1f}%" in page.inner_text("main"))
        page.wait_for_timeout(1500)  # let the slide fade-in finish
        page.screenshot(path=str(out / "11_presentation_results.png"))
        page.keyboard.press("ArrowLeft"); page.keyboard.press("ArrowLeft")
        page.get_by_text("Storing an image inside qubits").first.wait_for()
        page.wait_for_timeout(800)
        enc_imgs = page.evaluate("Array.from(document.querySelectorAll('main img')).filter(i => i.complete && i.naturalWidth > 0).length")
        R.check("encoding slide shows real reconstructions", enc_imgs == 4, f"{enc_imgs} images")
        page.wait_for_timeout(1500)
        page.screenshot(path=str(out / "12_presentation_encoding.png"))
        page.keyboard.press("Escape")
        page.wait_for_url(re.compile(r"/$"))
        R.check("Escape exits the presentation", page.url.endswith("/"))

        # 10. Navigation + responsive
        visit(page, a.base, "/")
        for label, path in [("Model Comparison", "/models"), ("Quantum Circuits", "/circuits"), ("Historical results (V0)", "/historical-v0")]:
            page.locator("aside nav").get_by_role("link", name=label).click()
            page.wait_for_url(re.compile(re.escape(path) + r"$"))
        R.check("sidebar navigation works", True)
        mob = ctx.new_page()
        watch(mob, bucket)
        mob.set_viewport_size({"width": 390, "height": 844})
        visit(mob, a.base, "/", "Three things to remember")
        overflow = mob.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
        R.check("mobile viewport: no horizontal page overflow", not overflow)
        mob.get_by_label("Open navigation").click()
        R.check("mobile navigation drawer opens", mob.get_by_role("link", name="Model Comparison").first.is_visible())
        mob.screenshot(path=str(out / "09_mobile_overview.png"), full_page=False)
        b.close()

    R.check("no console errors on any page", not bucket["console"], "; ".join(bucket["console"][:5]))
    R.check("no failed /api requests", not bucket["http"], "; ".join(bucket["http"][:5]))
    res = {"passed": sum(c["ok"] for c in R.checks), "failed": sum(not c["ok"] for c in R.checks), "checks": R.checks}
    (out / "e2e_results.json").write_text(json.dumps(res, indent=1))
    print(f"\n{res['passed']} passed, {res['failed']} failed")
    sys.exit(0 if res["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
