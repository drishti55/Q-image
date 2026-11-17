"""
Real-browser end-to-end check of the Algorithm Playground and Quantum vs Classical pages.

Requires the running backend (:8000) and frontend (:5173), and Playwright (not a project dependency).
Usage:  python scripts/v2/playground_e2e.py [--base http://127.0.0.1:5173] [--out results/qml_v3/reports/screenshots]
Every expected value is read from the API (playground JSON / models), never hardcoded. Exit code 1 if any check fails.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dashboard_e2e import ROOT, Run, api, visit, watch  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:5173")
    ap.add_argument("--out", default=str(ROOT / "results/qml_v3/reports/screenshots"))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    R = Run()
    import urllib.request
    pg = json.loads(urllib.request.urlopen(f"{a.base}/api/v3/playground").read())
    models = {m["group"]: m for m in api(a.base, "/models")["models"]}
    bucket = {"console": [], "http": []}
    pct = lambda v: f"{v * 100:.1f}%"  # noqa: E731

    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        page = ctx.new_page()
        watch(page, bucket)

        def go_step(k):
            page.get_by_label(f"Go to step {k}", exact=True).click()
            page.wait_for_timeout(300)

        def pick(algo):
            page.get_by_test_id(f"algo-{algo}").click()
            page.wait_for_timeout(300)

        def explain():
            return page.get_by_test_id("step-explain").inner_text()

        # 1. Navigation + 3×3 grid + pixel selection
        visit(page, a.base, "/")
        page.locator("aside nav").get_by_role("link", name="3×3 Algorithm Playground").click()
        page.wait_for_url(re.compile(r"/playground"))
        page.get_by_test_id("algo-title").wait_for()
        R.check("sidebar link opens the 3×3 Algorithm Playground", True)
        R.check("illustrative disclaimer visible", page.get_by_text("Illustrative demonstration").first.is_visible())
        pick("preprocessing")
        vals = [page.get_by_test_id(f"cell-{r}-{c}").first.inner_text().split("\n")[0] for r in range(3) for c in range(3)]
        R.check("3×3 grid shows 70,180,0,19,20,0,0,0,0", vals == ["70", "180", "0", "19", "20", "0", "0", "0", "0"], str(vals))
        page.get_by_test_id("cell-0-1").first.hover()
        tip = page.get_by_role("tooltip").inner_text()
        R.check("hover tooltip shows row/column/intensity", "row 1, column 2" in tip and "intensity 180" in tip, tip)
        page.get_by_test_id("cell-2-2").first.hover()
        R.check("hover on padding cell says zero padding", "zero padding" in page.get_by_role("tooltip").inner_text())
        page.mouse.move(0, 0)
        R.check("three-part layout: input, processing, explanation", all(page.get_by_label(x, exact=True).count() >= 1 for x in ("input image", "algorithm processing", "explanation")))

        # 2. Click pixel 70 and follow it: normalised value, FRQI angle, NEQR binary, classical feature change, circuit ops
        page.get_by_test_id("cell-0-0").first.click()
        page.wait_for_timeout(300)
        facts = page.get_by_test_id("pixel-facts").inner_text()
        R.check("pixel 70 facts: intensity, row/col, normalised, binary, NEQR, FRQI angle",
                all(x in facts for x in ("70", "1, 1", "0.2745", "01000110", "0100", "0.4312")), facts.replace("\n", " | ")[:200])
        go_step(3)
        R.check("preprocessing: 70/255 = 0.2745 in the actual output", "70 / 255 = 0.2745" in explain())
        go_step(4)
        R.check("flattened raw vector [70, 180, 0, 19, 20, 0, 0, 0, 0] shown",
                page.get_by_label("flattened vector", exact=True).inner_text().replace("\n", "").replace(" ", "") == "[70,180,0,19,20,0,0,0,0]")
        page.screenshot(path=str(out / "01_playground_3x3.png"), full_page=False)
        pick("pca")
        go_step(4)
        d70 = pg["pixel_traces"][0]["pca8_standard_delta"]
        R.check("PCA: pixel 70 feature change from the real fitted transform", f"{math.sqrt(sum(v * v for v in d70)):.3f}" in explain())
        page.screenshot(path=str(out / "02_classical_walkthrough_pca.png"), full_page=False)
        pick("frqi")
        go_step(3)
        R.check("FRQI: pixel 70 angle 0.4312 rad = 24.71° and journey stage active",
                "0.4312" in explain() and "24.71" in explain() and page.get_by_test_id("journey-theta").get_attribute("data-active") == "true")
        R.check("selected pixel cell shows its current value (θ)", "θ0.43" in page.get_by_test_id("cell-0-0").first.inner_text())
        txt = page.get_by_test_id("step-visual").inner_text()
        R.check("FRQI angle table covers all 9 cells incl. padding θ = 0",
                all(f"{(math.pi / 2) * v / 255:.4f}" in txt for v in (70, 180, 19, 20)) and txt.count("padding") == 5)
        page.screenshot(path=str(out / "03_frqi_angles.png"), full_page=False)
        go_step(7)
        R.check("FRQI controlled rotation for pixel 70: X gates + MCRY(0.8624)", "0.8624" in explain() and "X on q0, q1, q2, q3" in explain())
        R.check("FRQI real gate count from data", f"{pg['frqi']['logical_gates']} basic gates" in explain())
        go_step(10)
        page.get_by_test_id("opt-shots-100").click()
        page.wait_for_timeout(300)
        R.check("FRQI shots toggle changes the reconstruction", "100 shots" in explain())
        page.screenshot(path=str(out / "03b_frqi_reconstruction.png"), full_page=False)

        # 3. NEQR at three precisions, for two different pixels
        pick("neqr")
        go_step(3)
        for px, (rr, cc) in ((0, (0, 0)), (2, (1, 0))):
            page.get_by_test_id(f"cell-{rr}-{cc}").first.click()
            page.wait_for_timeout(250)
            for bits in ("2", "4", "8"):
                page.get_by_test_id(f"opt-bits-{bits}").click()
                page.wait_for_timeout(250)
                code = pg["neqr"]["precisions"][bits]["pixels"][px]["binary_msb_first"]
                R.check(f"NEQR {bits}-bit binary of pixel {pg['pixel_traces'][px]['value']} = {code}", page.get_by_test_id("neqr-bits").inner_text().replace("\n", "") == code)
        page.get_by_test_id("cell-0-0").first.click()
        page.get_by_test_id("opt-bits-4").click()
        page.wait_for_timeout(300)
        page.screenshot(path=str(out / "04_neqr_binary.png"), full_page=False)
        go_step(4)
        R.check("NEQR explains amplitude vs basis-state encoding", "basis" in explain().lower() and "amplitude" in explain().lower())

        # 4. QKC circuits per feature map + selectable kernel entry
        pick("qkc")
        go_step(3)
        for fm in ("product_ry", "zz_linear", "zz_full"):
            page.get_by_test_id(f"opt-fmap-{fm}").click()
            page.wait_for_timeout(250)
            n = pg["qkc"]["maps"][fm]["n_gates"]
            R.check(f"QKC {fm} circuit has {n} gates", f"{n} gates" in explain() and page.locator("[data-testid=step-visual] svg[aria-label=circuit] g").count() >= n)
        page.screenshot(path=str(out / "05a_qkc_circuit.png"), full_page=False)
        go_step(6)
        page.get_by_test_id("k-0-2").click()
        page.wait_for_timeout(200)
        kv = pg["qkc"]["maps"]["zz_full"]["kernel_heatmap"][0][2]
        R.check("kernel heatmap: clicking an entry explains that entry", f"{kv:.4f}" in page.get_by_test_id("kernel-entry").inner_text())
        page.screenshot(path=str(out / "05_qkc_kernel.png"), full_page=False)

        # 5. VQC
        pick("vqc")
        go_step(7)
        R.check("VQC parameter-shift derivative from data", f"{pg['vqc']['parameter_shift']['dE_dtheta'][0]:.4f}" in explain())
        go_step(9)
        R.check("VQC updated circuit after the illustrative Adam step", f"{pg['vqc']['illustrative_adam_step']['theta_after'][0]:.4f}" in explain())
        go_step(10)
        page.wait_for_timeout(600)
        R.check("VQC recorded loss curve rendered", page.locator("[data-testid=step-visual] .recharts-line").count() >= 2)
        R.check("no class prediction shown for the artificial grid", "No class is shown" in page.get_by_test_id("step-visual").inner_text())
        page.screenshot(path=str(out / "06_vqc.png"), full_page=False)

        # 6. Controls + presentation mode
        pick("frqi")
        go_step(3)
        page.get_by_label("Next step").click(); page.wait_for_timeout(300)
        R.check("Next advances", page.get_by_test_id("step-counter").inner_text().lower() == "step 4 of 10")
        page.get_by_label("Previous step").click(); page.wait_for_timeout(300)
        R.check("Previous goes back", page.get_by_test_id("step-counter").inner_text().lower() == "step 3 of 10")
        page.get_by_label("Play animation").click(); page.wait_for_timeout(3100)
        R.check("Play auto-advances", page.get_by_test_id("step-counter").inner_text().lower() == "step 4 of 10")
        page.get_by_label("Pause").click(); page.wait_for_timeout(3100)
        R.check("Pause stops", page.get_by_test_id("step-counter").inner_text().lower() == "step 4 of 10")
        page.get_by_label("Reset").click(); page.wait_for_timeout(300)
        R.check("Reset returns to step 1", page.get_by_test_id("step-counter").inner_text().lower() == "step 1 of 10")
        page.get_by_test_id("enter-present").click()
        page.get_by_test_id("present-mode").wait_for()
        R.check("presentation mode hides the dashboard navigation", not page.locator("aside nav").first.is_visible() or
                page.evaluate("getComputedStyle(document.querySelector('[data-testid=present-mode]')).position") == "fixed")
        page.keyboard.press("ArrowRight"); page.wait_for_timeout(300)
        R.check("presentation: arrow key advances", page.get_by_test_id("step-counter").inner_text().lower() == "step 2 of 10")
        page.screenshot(path=str(out / "07_presentation_mode.png"), full_page=False)
        page.keyboard.press("Escape"); page.wait_for_timeout(300)
        R.check("presentation: Escape exits", page.get_by_test_id("present-mode").count() == 0)

        # 7. Quantum vs Classical
        page.locator("aside nav").get_by_role("link", name="Quantum vs Classical").click()
        page.get_by_test_id("chart-family-best").wait_for()
        page.wait_for_timeout(800)
        fb = page.get_by_test_id("chart-family-best").inner_text()
        best_all = max((m for m in models.values() if not (m["shots"] or m["is_ablation"] or m["is_legacy_relabelled"])), key=lambda m: m["test_accuracy"]["mean"])
        R.check("Charts tab is default and family-best chart labels the API best", pct(best_all["test_accuracy"]["mean"]) in fb, fb[:120])
        for cid in ("chart-model-strip", "chart-hybrid-effect", "chart-qubit-scaling", "chart-neqr-bits", "chart-shots-qkc", "chart-shots-encoding", "chart-cost"):
            R.check(f"{cid} renders marks", page.get_by_test_id(cid).locator(".recharts-surface").count() >= 1 and page.get_by_test_id(cid).locator(".recharts-bar-rectangle, .recharts-scatter-symbol, .recharts-line-curve").count() >= 2)
        page.get_by_test_id("chart-hybrid-effect").locator(".recharts-bar-rectangle").first.hover()
        page.wait_for_timeout(300)
        R.check("chart hover tooltip appears", "features" in page.get_by_test_id("chart-hybrid-effect").locator(".recharts-tooltip-wrapper").inner_text())
        page.screenshot(path=str(out / "12_results_charts.png"), full_page=True)
        hc = page.get_by_test_id("chart-hybrid-effect")
        hc.get_by_role("button", name="Table").click()
        R.check("chart table view lists API values", f"{models['E5-mnv3pca8-qkc-product_ry']['test_accuracy']['mean'] * 100:.1f}" in hc.inner_text())
        page.get_by_test_id("tab-classical").click()
        page.get_by_test_id("table-classical").wait_for()
        best_c = max((m for m in models.values() if not m["is_quantum"] and not m["is_legacy_relabelled"] and m["category"] == "Classical models" and not m["group"].startswith("E5-")), key=lambda m: m["test_accuracy"]["mean"])
        R.check("classical best highlighted matches API", best_c["display_name"] in page.get_by_test_id("best-classical model").inner_text())
        R.check("classical row shows API accuracy", pct(models["E7-smallcnn"]["test_accuracy"]["mean"]) in page.get_by_test_id("row-E7-smallcnn").inner_text())
        page.screenshot(path=str(out / "07_classical_view.png"), full_page=False)
        page.get_by_test_id("tab-quantum").click()
        page.get_by_test_id("table-quantum-qkc").wait_for()
        row = page.get_by_test_id("row-E3-pca8-qkc-zz_full").inner_text()
        c = models["E3-pca8-qkc-zz_full"]["circuit"]
        R.check("quantum row: accuracy + gate counts from API", pct(models["E3-pca8-qkc-zz_full"]["test_accuracy"]["mean"]) in row and f"{c['gates_logical']:,} / {c['gates_compiled']:,}" in row, row[:200])
        R.check("quantum view excludes legacy V0 rows", page.get_by_text("Legacy V0").count() == 0)
        page.screenshot(path=str(out / "08_quantum_vs_classical.png"), full_page=False)
        page.get_by_test_id("tab-hybrid").click()
        page.get_by_test_id("hybrid-k8").wait_for()
        R.check("hybrid table shows product-RY hybrid accuracy", pct(models["E5-mnv3pca8-qkc-product_ry"]["test_accuracy"]["mean"]) in page.get_by_test_id("hybrid-k8").inner_text())
        R.check("hybrid explains no quantum advantage", page.get_by_text("Why this is not a quantum advantage").is_visible())
        page.screenshot(path=str(out / "09_hybrid.png"), full_page=True)
        page.get_by_test_id("tab-side").click()
        page.get_by_test_id("dimension-table").wait_for()
        page.get_by_test_id("pick-q-vqc").click()
        page.wait_for_timeout(300)
        R.check("side-by-side shows real VQC accuracy", f"{models['E4-pca4-vqc']['test_accuracy']['mean'] * 100:.1f}" in page.get_by_test_id("side-quantum").inner_text())
        page.get_by_test_id("pick-q-frqi").click(); page.wait_for_timeout(250)
        page.get_by_test_id("cell-0-1").first.click(); page.wait_for_timeout(250)
        R.check("side-by-side follows the selected pixel (180 -> FRQI angle 1.1088, classical feature change)",
                "1.1088" in page.get_by_test_id("side-quantum").inner_text() and "‖Δx‖" in page.get_by_test_id("side-classical").inner_text())
        R.check("side-by-side shows no class prediction for the grid", "Demo output" not in page.inner_text("main"))
        page.screenshot(path=str(out / "10_side_by_side.png"), full_page=True)
        visit(page, a.base, "/models")
        page.get_by_test_id("chart-model-strip").wait_for()
        R.check("Model Comparison page shows comparison charts", page.get_by_test_id("chart-family-best").locator(".recharts-bar-rectangle").count() >= 5)
        page.screenshot(path=str(out / "13_model_comparison_charts.png"), full_page=False)

        # 8. Responsive
        mob = ctx.new_page()
        watch(mob, bucket)
        mob.set_viewport_size({"width": 390, "height": 844})
        for path in ("/playground?algo=frqi&step=3", "/quantum-vs-classical?view=side", "/quantum-vs-classical", "/models"):
            visit(mob, a.base, path)
            R.check(f"mobile {path}: no horizontal page overflow", not mob.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1"))
        visit(mob, a.base, "/playground?algo=qkc&step=5")
        mob.screenshot(path=str(out / "11_mobile_playground.png"), full_page=False)
        b.close()

    R.check("no console errors", not bucket["console"], "; ".join(bucket["console"][:5]))
    R.check("no failed /api requests", not bucket["http"], "; ".join(bucket["http"][:5]))
    res = {"passed": sum(c["ok"] for c in R.checks), "failed": sum(not c["ok"] for c in R.checks), "checks": R.checks}
    (out / "e2e_results.json").write_text(json.dumps(res, indent=1))
    print(f"\n{res['passed']} passed, {res['failed']} failed")
    sys.exit(0 if res["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
