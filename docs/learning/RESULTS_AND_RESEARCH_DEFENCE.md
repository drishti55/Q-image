# Results, Metrics and Research Defence

> All numbers from the saved aggregates. Accuracy = locked test (360 images), mean ± s.d. over seeds 0–2.

---

## 1. Metrics, with small examples

**Confusion matrix** — rows = true class, columns = predicted. Example (2 classes, 10 images): true A predicted A = 4,
A→B = 1, B→A = 2, B→B = 3.
* **Accuracy** = correct/total = (4+3)/10 = 0.70.
* **Precision**(A) = TP/(TP+FP) = 4/(4+2) = 0.667 — "when I say A, how often am I right?"
* **Recall**(A) = TP/(TP+FN) = 4/(4+1) = 0.80 — "of all real A, how many did I find?"
* **F1**(A) = 2PR/(P+R) = 0.727. F1(B): P = 3/4 = 0.75, R = 3/5 = 0.6 → 0.667.
* **Macro-F1** = mean over classes = 0.697. Every class counts equally, so a model cannot hide a failing class behind
  good ones. It is our **selection criterion** (validation); accuracy is the headline (test set is balanced).

**Reconstruction metrics** (`src/metrics/evaluator.py`, scikit-image SSIM):
* **MSE** = mean (original − reconstructed)²; 0 is perfect; intensities in [0, 1].
* **PSNR** = 10·log₁₀(1/MSE) dB; ∞ for exact (reported as None); > 40 dB is visually near-perfect.
  Example: MSE 1e-4 → 40 dB.
* **SSIM** ∈ [−1, 1] compares local mean, contrast and structure; 1 is identical. It can disagree with MSE: PCA
  blurs (low MSE ≈ 4.7e-3 but SSIM 0.59), shot noise is speckle (similar MSE, lower SSIM).
* **Shots**: FRQI error ∝ 1/shots per position, and each position gets ≈ shots/N samples → MSE grows with N.
  NEQR has a quantisation floor (4-bit: 3.68e-4) and black pixels where no shot landed.

**Circuit metrics**: qubits (memory 2ⁿ in simulation), compiled gate count and depth (time/noise exposure on
hardware), CX count (the noisiest gate), shots (measurement cost). Execution time is recorded per run but not used
for conclusions.

---

## 2. Main findings

| Question | Answer (evidence) |
|---|---|
| Best model overall | Frozen MobileNetV3 + LogReg/SVM **96.4 %** (V2); classical texture SVM 95.6 % (V3) |
| Best quantum-kernel model | Texture PCA-12 + product-RY QKC 95.3 % (V3) — product-RY is classically computable |
| Best FRQI/NEQR model | V4 FRQI 8×8 patches **87.8 ± 1.5 %**; NEQR 4×4 patches 82.7 ± 10.1 % |
| FRQI vs NEQR | V4: FRQI +5.1 pp (p = 0.045) and far more stable; V2 whole-image: tied (60.6 vs 60.2) |
| Resolution | whole-image FRQI 2→16 px: 43 → 58 %; in V4, 64 px better than 32 or 128 (validation) |
| Intensity precision (NEQR) | 4 bits best; 8 bits worse (exact matches rare → near-identity kernel); 2 bits too coarse |
| Shots | classification: FRQI 8×8 kernel 57.8 % exact → 39.3 % at 1,000 shots; ZZ QKC robust above ~500 shots; reconstruction: FRQI needs 10⁴–10⁵ shots at 16×16 |
| Quantum vs classical, same features | tied: CNN-PCA8 QKC 93.2 vs RBF-SVM 93.0; V4 FRQI vs same-patch control +4.2 pp, p = 0.060 (n.s.) |
| Hybrid vs pure quantum | hybrids (classical features) ≫ pure pixel quantum (93 vs 64 %) |
| VQC | weakest family (48 % V2, 73 % V3); V3 encoding-only control 92.6 % beats trained VQC |
| Cost | better FRQI accuracy needs 225 patch states of 8,339 gates each; classical controls are cheaper and as good |

### The single most important interpretation
The jump from 60 % to 88 % comes from **how images are compared** (all patch pairs instead of same-position pixels),
not from quantum effects. The matched classical control on identical patches proves this. A good result is not the
same as a quantum advantage.

---

## 3. Limitations and threats to validity (say them before the examiner does)
1. Noiseless simulation only; no hardware; no noise model; swap test not executed.
2. One data set (NEU-DET, 1,800 images).
3. The locked test set was reused across V2, V3, V4; V4's idea came after seeing V2/V3 results (protocol-level
   adaptivity). Within V4: validation-only selection, freeze, one test evaluation.
4. A few patch geometries were explored on validation before the V4 grid was fixed (disclosed in run_v4.py).
5. C = 1000 is at the edge of the grid.
6. NEQR instability on one seed (rolled-in-scale brightness shift between folders).
7. All kernels have closed forms → classically simulable by construction; no advantage is possible at this size.

**Statistical reliability**: 3 seeds, paired permutation test on per-image correctness (10,000 permutations),
bootstrap CI, McNemar per seed, Holm over 8 pre-declared comparisons. **Reproducibility**: hashed manifests and
selections, scripted stages, 17/17 integrity checks, an independent validator recomputing the paper's numbers (27/27).

---

## 4. Research paper cross-check (paper vs code)

| Paper statement | Status |
|---|---|
| 288 configurations, 864 runs, 0 failed | ✔ matches `v4_results.json` counts |
| FRQI 87.8 ± 1.5, NEQR 82.7 ± 10.1, control 83.6 ± 0.3, texture 95.6 ± 2.2 | ✔ recomputed from predictions.csv |
| 8 comparisons, Holm | ✔ `analyze_v4.py` |
| "estimable with a swap test" | ✔ if worded as *could be*; ✘ if read as "we ran swap tests" (we did not) |
| FRQI 8×8 patch: 7 qubits, 8,339 gates, depth 4,878, 3,584 CX | ✔ (measured on the b = 1 encoder; structure identical for b = 4) |
| NEQR 4×4 patch: 8 qubits, 1,998 gates | ✔ for V4's sample patches; data-dependent (2,901 on other images) |
| Unit tests: kernel = mean squared overlap of Qiskit statevectors; shift test | ✔ `tests/test_v4_models.py` |
| 17 integrity checks | ✔ `v4_verification.json` |
| 163 models in per-image analysis | ✔ 88 (V2) + 70 (V3) + 5 (V4) |
| Related-work "key results" column | qualitative summaries — verify by reading each paper |
| Python 3.11.0, Qiskit 2.5.2, Aer 0.17.2, sklearn 1.9.1, NumPy 2.4.6 | ✔ installed versions |

What a professor may challenge: novelty (mixtures of encoded patches are a natural idea — the contribution is the
controlled evaluation and the matched control); test-set reuse; whether results hold on hardware; why not other QIRs.
