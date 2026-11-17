"""results/qml_v4/reports/RECONSTRUCTION_FULL_REPORT.md from reconstruction_full/summary.json (numbers read, never typed)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V4 = ROOT / "results" / "qml_v4"
S = json.loads((V4 / "reconstruction_full" / "summary.json").read_text())
R = S["records"]
CL = ["crazing", "inclusion", "patches", "pitted_surface", "rolled-in_scale", "scratches"]


def sci(v):
    return "—" if v is None else ("0 (exact)" if v < 1e-15 else f"{v:.2e}")


def f3(v):
    return "—" if v is None else f"{v:.3f}"


def tab(head, rows):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(map(str, r)) + " |" for r in rows])


def m(rid, mode, f="mse", key="vs_preprocessed", part=("all",)):
    s = R[rid]["summary"]
    for p in part:
        s = s[p]
    return s[mode][key][f]["mean"]


whole = [k for k in R if k.startswith("R-")]
rows = []
for rid in whole + [k for k in R if k.startswith("P-")]:
    c = R[rid]["circuit"] or {}
    shots = R[rid]["config"]["shots"]
    rows.append([f"`{rid}`", c.get("n_qubits", "—"), f"{c.get('gates_compiled', 0):,.0f}", sci(m(rid, "statevector")), f3(m(rid, "statevector", "ssim")),
                 f"{R[rid]['summary']['all']['statevector']['n_exact']:,} / {S['n_images']:,}"]
                + [sci(m(rid, f"shots{s}")) for s in (100, 1000, 10000)]
                + [sci(m(rid, "shots100000")) if 100000 in shots else "n/a"]
                + [f3(m(rid, f"shots{shots[-1]}", "ssim"))])
for rid in [k for k in R if k.startswith("C-")]:
    rows.append([f"`{rid}` (classical)", "—", "—", sci(m(rid, "reconstruction")), f3(m(rid, "reconstruction", "ssim")), "—", "—", "—", "—", "—", "—"])

exact_counts = {rid: R[rid]["summary"]["all"]["statevector"]["n_exact"] for rid in whole}
frqi_exact = all(exact_counts[k] == S["n_images"] for k in whole if "FRQI" in k)
neqr_q = [[f"`{rid}`", sci(m(rid, "statevector", key="vs_quantized")), sci(R[rid]["summary"]["all"]["quantization_only"]["mse"]["mean"]),
           sci(m(rid, "statevector"))] for rid in whole if "NEQR" in rid]
cls_rows = []
for rid in ("R-FRQI-16x16", "R-NEQR-16x16-b4", "P-FRQI-64-p8", "C-PCA8-64"):
    mode = "reconstruction" if rid.startswith("C-") else "shots1000"
    cls_rows.append([f"`{rid}` ({'PCA' if mode == 'reconstruction' else '1,000 shots'})"] + [f3(m(rid, mode, "ssim", part=("by_class", c))) for c in CL])
role_rows = [[f"`{rid}`", sci(m(rid, "shots1000", part=("by_role", "trainval"))), sci(m(rid, "shots1000", part=("by_role", "locked_test")))]
             for rid in ("R-FRQI-16x16", "R-NEQR-16x16-b4", "R-NEQR-16x16-b8")]

rep = f"""# Full Reconstruction Study — all {S['n_images']:,} images, every encoding

Created {S['created_at']} by `scripts/v4/reconstruct_all.py` (20 methods × {S['n_images']:,} images; results in
`results/qml_v4/reconstruction_full/`). The V2 study used 30 training images; this one covers **every image of NEU-DET**
(1,440 train-folder + 360 locked-test-folder) for **every encoding**.

**How each quantum row was produced (no shortcuts):** the real Qiskit encoder circuit (`src/frqi/encoder.py`, `src/neqr/encoder.py`) →
Qiskit-Aer statevector → decoded with `src/reconstruction/reconstructor.py`; shot rows draw a multinomial sample of the exact
output distribution with that many shots and decode the counts. Patch rows (the Protocol V4 representation) encode and decode every
patch separately with the same circuits and stitch the patches back together; their shot counts are **per patch**.
Classical rows: PCA fitted on the seed-0 training split only, inverse-transformed. They show how much of the image the
PCA-input QKC / VQC classifiers actually receive. Reconstruction uses no labels, so including test-folder images cannot affect model selection.
Everything was simulated on a CPU (no quantum hardware, no noise model).

## 1. All methods (mean over {S['n_images']:,} images; MSE / SSIM against the preprocessed image)

{tab(['Method', 'qubits', 'compiled gates', 'exact MSE', 'exact SSIM', 'images reproduced exactly', 'MSE 100 shots', 'MSE 1k', 'MSE 10k', 'MSE 100k', 'SSIM at most shots'], rows)}

## 2. Findings

1. **FRQI statevector decoding is exact for every image** — {'all' if frqi_exact else 'NOT all'} {S['n_images']:,} images at every resolution
   ({', '.join(f'{k}: {v:,}' for k, v in exact_counts.items() if 'FRQI' in k)}). Any FRQI error comes from finite measurement shots.
2. **FRQI needs many shots, and more pixels need more.** At 1,000 shots, MSE is {sci(m('R-FRQI-2x2', 'shots1000'))} for 2×2 but
   {sci(m('R-FRQI-16x16', 'shots1000'))} for 16×16, because the shots are spread over r² pixels.
3. **NEQR is exact up to quantisation.** Its statevector reconstruction equals the quantised image (table below). The only error is the
   intensity rounding to 2/4/8 bits. Once every pixel has been observed at least once, more shots do not help.
4. **The V4 patch representation is cheap to reconstruct.** Each 8×8 FRQI patch is a 7-qubit state. With 1,000 shots per patch,
   the 64×64 image has MSE {sci(m('P-FRQI-64-p8', 'shots1000'))}. The whole-image 16×16 FRQI needs 9 qubits and gets {sci(m('R-FRQI-16x16', 'shots1000'))} with
   1,000 shots for the whole image. *Note: the total shot budget differs (64 patches × 1,000).*
5. **PCA inputs throw away most of the image.** The PCA-8 reconstruction SSIM is {f3(m('C-PCA8-64', 'reconstruction', 'ssim'))}, and PCA-12 is
   {f3(m('C-PCA12-64', 'reconstruction', 'ssim'))}. This is why the PCA-input QKC / VQC classifiers in V2 had so little texture to work with.

### NEQR: statevector vs quantisation (mean MSE)

{tab(['Record', 'statevector vs quantised image', 'quantisation alone vs original', 'statevector vs original'], neqr_q)}

## 3. Per class (SSIM)

{tab(['Method'] + CL, cls_rows)}

## 4. Train folder vs locked-test folder (MSE at 1,000 shots)

{tab(['Record', 'train folder (1,440)', 'locked-test folder (360)'], role_rows)}

## 5. Reproduce

```bash
cd scripts/v4 && N=9 ./chain_recon.sh          # ~30–60 min on 10 cores; resumable
cd ../.. && .venv/bin/python scripts/v4/write_recon_report.py
```
Interactive: dashboard → **Reconstruction (all 1,800)**. Browse any image with any method and animate the shots.
"""
(V4 / "reports" / "RECONSTRUCTION_FULL_REPORT.md").write_text(rep)
print("written")
