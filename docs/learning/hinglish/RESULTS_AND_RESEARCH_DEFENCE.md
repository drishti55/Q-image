# Results, Metrics aur Research Defence

> Saare numbers saved aggregates se. Accuracy = locked test (360 images), seeds 0–2 ka mean ± s.d.

---

## 1. Metrics, chhote examples ke saath

**Confusion matrix** — rows = asli class, columns = predicted. Example (2 classes, 10 images): asli A predicted A = 4, A→B = 1,
B→A = 2, B→B = 3.
* **Accuracy** = sahi/total = (4+3)/10 = 0.70.
* **Precision**(A) = TP/(TP+FP) = 4/(4+2) = 0.667 — "jab main A bolta hoon, kitni baar sahi hota hoon?"
* **Recall**(A) = TP/(TP+FN) = 4/(4+1) = 0.80 — "saare asli A mein se kitne pakde?"
* **F1**(A) = 2PR/(P+R) = 0.727. F1(B): P = 3/4 = 0.75, R = 3/5 = 0.6 → 0.667.
* **Macro-F1** = classes ka average = 0.697. Har class barabar count hoti hai, toh koi model fail hoti class ko achhi classes ke
  peeche chupa nahi sakta. Yeh humara **selection criterion** (validation) hai; accuracy headline hai (test set balanced hai).

**Reconstruction metrics** (`src/metrics/evaluator.py`, scikit-image SSIM):
* **MSE** = mean (original − reconstructed)²; 0 = perfect; intensities [0, 1] mein.
* **PSNR** = 10·log₁₀(1/MSE) dB; exact ke liye ∞ (None report hota hai); > 40 dB lagbhag perfect dikhta hai.
  Example: MSE 1e-4 → 40 dB.
* **SSIM** ∈ [−1, 1], local mean, contrast aur structure compare karta hai; 1 = identical. MSE se alag ho sakta hai: PCA blur
  karta hai (kam MSE ≈ 4.7e-3 par SSIM 0.59), shot noise speckle hai (similar MSE, kam SSIM).
* **Shots**: FRQI error per position ∝ 1/shots, aur har position ko ≈ shots/N samples milte hain → N ke saath MSE badhta hai.
  NEQR mein quantisation floor (4-bit: 3.68e-4) aur jahan koi shot nahi gira wahan kaale pixels.

**Circuit metrics**: qubits (simulation mein memory 2ⁿ), compiled gate count aur depth (hardware par time/noise), CX count
(sabse noisy gate), shots (measurement cost). Execution time har run ka record hota hai par conclusions mein use nahi hua.

---

## 2. Main findings

| Sawaal | Jawab (evidence) |
|---|---|
| Overall best model | Frozen MobileNetV3 + LogReg/SVM **96.4 %** (V2); classical texture SVM 95.6 % (V3) |
| Best quantum-kernel model | Texture PCA-12 + product-RY QKC 95.3 % (V3) — product-RY classically computable hai |
| Best FRQI/NEQR model | V4 FRQI 8×8 patches **87.8 ± 1.5 %**; NEQR 4×4 patches 82.7 ± 10.1 % |
| FRQI vs NEQR | V4: FRQI +5.1 pp (p = 0.045) aur kaafi zyada stable; V2 whole-image: barabar (60.6 vs 60.2) |
| Resolution | whole-image FRQI 2→16 px: 43 → 58 %; V4 mein 64 px, 32 ya 128 se behtar (validation) |
| Intensity precision (NEQR) | 4 bits best; 8 bits kharab (exact match kam → near-identity kernel); 2 bits bahut coarse |
| Shots | classification: FRQI 8×8 kernel 57.8 % exact → 1,000 shots par 39.3 %; ZZ QKC ~500 shots ke upar robust; reconstruction: 16×16 FRQI ko 10⁴–10⁵ shots |
| Same features par quantum vs classical | barabar: CNN-PCA8 QKC 93.2 vs RBF-SVM 93.0; V4 FRQI vs same-patch control +4.2 pp, p = 0.060 (n.s.) |
| Hybrid vs pure quantum | hybrids (classical features) ≫ pure pixel quantum (93 vs 64 %) |
| VQC | sabse kamzor family (V2 48 %, V3 73 %); V3 encoding-only control 92.6 % trained VQC se behtar |
| Cost | behtar FRQI accuracy ke liye 8,339 gates wale 225 patch states; classical controls saste aur utne hi achhe |

### Sabse important interpretation
60 % se 88 % ki chhalaang **images ko compare karne ke tareeke** se aayi (same-position pixels ki jagah saare patch pairs),
quantum effects se nahi. Same patches par matched classical control yeh prove karta hai. Achha result aur quantum advantage
ek cheez nahi hai.

---

## 3. Limitations aur threats to validity (examiner se pehle khud bolo)
1. Sirf noiseless simulation; hardware nahi; noise model nahi; swap test nahi chala.
2. Ek hi dataset (NEU-DET, 1,800 images).
3. Locked test set V2, V3, V4 mein reuse hua; V4 ka idea V2/V3 results dekhne ke baad aaya (protocol-level adaptivity).
   V4 ke andar: validation-only selection, freeze, ek test evaluation.
4. V4 grid fix karne se pehle kuch patch geometries validation par explore ki gayi (run_v4.py mein disclose).
5. C = 1000 grid ke edge par hai.
6. Ek seed par NEQR instability (folders ke beech rolled-in-scale brightness shift).
7. Saare kernels ke closed forms hain → design se hi classically simulable; is size par advantage possible hi nahi.

**Statistical reliability**: 3 seeds, per-image correctness par paired permutation test (10,000 permutations), bootstrap CI,
har seed ka McNemar, 8 pre-declared comparisons par Holm. **Reproducibility**: hashed manifests aur selections, scripted stages,
17/17 integrity checks, paper ke numbers recompute karne wala independent validator (27/27).

---

## 4. Research paper cross-check (paper vs code)

| Paper statement | Status |
|---|---|
| 288 configurations, 864 runs, 0 failed | ✔ `v4_results.json` counts se match |
| FRQI 87.8 ± 1.5, NEQR 82.7 ± 10.1, control 83.6 ± 0.3, texture 95.6 ± 2.2 | ✔ predictions.csv se recompute |
| 8 comparisons, Holm | ✔ `analyze_v4.py` |
| "swap test se estimable" | ✔ agar *ho sakta hai* likha ho; ✘ agar lage ki "humne swap test chalaya" (nahi chalaya) |
| FRQI 8×8 patch: 7 qubits, 8,339 gates, depth 4,878, 3,584 CX | ✔ (b = 1 encoder par measure; b = 4 ke liye structure same) |
| NEQR 4×4 patch: 8 qubits, 1,998 gates | ✔ V4 sample patches ke liye; data-dependent (doosri images par 2,901) |
| Unit tests: kernel = Qiskit statevectors ka mean squared overlap; shift test | ✔ `tests/test_v4_models.py` |
| 17 integrity checks | ✔ `v4_verification.json` |
| Per-image analysis mein 163 models | ✔ 88 (V2) + 70 (V3) + 5 (V4) |
| Related-work "key results" column | qualitative summaries — har paper padh ke verify karo |
| Python 3.11.0, Qiskit 2.5.2, Aer 0.17.2, sklearn 1.9.1, NumPy 2.4.6 | ✔ installed versions |

Professor kya challenge kar sakte hain: novelty (encoded patches ka mixture natural idea hai — contribution controlled evaluation
aur matched control hai); test-set reuse; kya hardware par results hold karenge; doosre QIRs kyun nahi.
