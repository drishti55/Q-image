# Every Experiment, Explained

> Sources: `scripts/v2/phase*.py`, `scripts/v3/run_v3.py`, `scripts/v4/run_v4.py`, and the aggregates in
> `results/qml_v2/aggregates/analysis.json`, `results/qml_v3/aggregates/v3_results.json`,
> `results/qml_v4/aggregates/v4_results.json`. Accuracy = locked test, mean ± s.d. over seeds 0–2 (360 images).
> All quantum computations: exact noiseless simulation on CPU. Selection always by mean **validation** macro-F1.

---

## 0. Shared protocol (V2–V4)
Manifest with SHA-256 per image → splits per seed (train 1,080 / val 360, blocks of 20 consecutive indices,
3 val blocks per class) → train every configuration × 3 seeds → select per group by validation → freeze →
evaluate the saved model **once** on the 360-image locked test set. Counts: V2 88 groups / 2,583 runs; V3 70 groups /
5,316 runs; V4 5 groups / 864 runs; 0 failed in each.

---

## 1. Master table (selected configuration per group)

| ID | Model | Representation / features | Qubits | Circuit | Shots | Test acc. % |
|---|---|---|---|---|---|---|
| E1-frqi2/4/8/16-qkc | FRQI overlap QKC | whole image 2–16 px | 3/5/7/9 | FRQI encoder | 0 | 43.0 / 52.7 / 57.8 / 57.6 |
| E1b-frqi4/8/16-qkc-scaled | FRQI, angle scale 2 | 4/8/16 px | 5/7/9 | FRQI, b = 2 | 0 | 55.9 / **60.6** / 59.9 |
| E1-frqi8-qkc-shots100/1k/10k | FRQI with shot noise | 8 px | 7 | FRQI | 100/1k/10k | 33.5 / 39.3 / 46.3 |
| E2-neqr{r}-b{q}-qkc | NEQR overlap QKC | r = 2,4,8,16; q = 2,4,8 | 4–16 | NEQR encoder | 0 | best 16×16 4-bit **60.2**; 8×8 4-bit 59.9; 8-bit always worse (e.g. 16×16 8-bit 50.3) |
| E2-neqr8-b4-qkc-shots100/1k/10k | NEQR shot noise | 8 px 4-bit | 10 | NEQR | 100/1k/10k | 56.2 / 59.4 / 60.1 |
| E1/E2-encstats-logreg, legacy-softmax | **classical** (V0 relabelled) | closed-form statistics | — | none | — | 24–56 |
| E3-pca{k}-qkc-{map} | QKC on pixel PCA | k = 4,6,8 | k | product-RY / ZZ-linear / ZZ-full | 0 | best PCA-8 ZZ-full **64.0 ± 3.5** |
| E3-pca{k}-qkc-zz_full-shots | QKC shot study | k = 4,6,8 | k | ZZ-full | 100–5,000 | PCA-8: 57.1 (100) → 63.4 (5,000) |
| E4-pca{k}-vqc | VQC | PCA k = 4,6,8 | k | RY enc + L×(RY,RZ)+CX ring | exact | 34.1 / 44.5 / **48.1** |
| E4-…-ablation-frozen | frozen random circuit + head | PCA | k | same, untrained | exact | 16.4 / 28.3 / 28.6 |
| E5-mnv3pca{k}-qkc-{map} | **hybrid** CNN → QKC | MobileNetV3 576-d → PCA k | 4/6/8 | product-RY / ZZ | 0 | best k = 8 product-RY **93.2 ± 1.1** |
| E5-mnv3pca{k}-rbfsvm / logreg | classical control, identical features | same | — | — | — | k = 8: 93.0 / 92.0 |
| E5-mnv3pca{k}-vqc | hybrid CNN → VQC | same | 4/6/8 | VQC | exact | 86.6 / 85.6 / 81.3 |
| E6-pca{k}-rbfsvm(-angle) / logreg | classical pixels | PCA k | — | — | — | best 64.8 (SVM, k = 8) |
| E7-smallcnn | CNN from scratch | 128 px | — | — | — | 93.0 ± 5.9 |
| E7-mnv3-logreg / rbfsvm | frozen MobileNetV3 | 576-d | — | — | — | **96.4** / 96.4 |
| V3-tex12c-qkc-product_ry | QKC | texture PCA-12, CDF angles | 12 | product-RY | 0 | **95.3 ± 3.2** |
| V3-tex8c-qkc-zz_full | QKC | texture PCA-8 | 8 | ZZ-full | 0 | 93.0 ± 3.0 |
| V3-…-pqk-zz_* | projected quantum kernel | pixels / CNN | 8–12 | ZZ + Bloch vectors | 0 | see v3_results.json |
| V3-mnv8c-qkc-* | hybrid | MobileNetV3 PCA-8 | 8 | all maps | 0 | 91.3 |
| V3-tex8c-vqc | VQC | texture PCA-8 | 8 | VQCv3 | exact | 73.4 ± 3.8 |
| V3-tex8c-vqc-encoding-only | **control** (no trainable gates) | texture PCA-8 | 8 | RY only | exact | 92.6 |
| V3-frqi8 / V3-neqr16 | FRQI / NEQR re-tuned | whole image | 7 / 12 | encoders | 0 | 57.5 / 60.2 |
| V3-tex12c-rbfsvm | classical texture SVM | texture PCA-12 | — | — | — | **95.6 ± 2.2** |
| V4-frqi-p4 | patch-ensemble FRQI | 64 px, p = 4, s = 4, b = 4, stretch, C = 1000 | 5 | FRQI patch | 0 | 85.3 ± 1.7 |
| **V4-frqi-p8** | patch-ensemble FRQI | 64 px, p = 8, s = 4, b = 4, stretch, C = 1000 | 7 | FRQI patch | 0 | **87.8 ± 1.5** |
| V4-neqr-p2 | patch-ensemble NEQR | 64 px, p = 2, s = 2, 4-bit, no stretch | 6 | NEQR patch | 0 | 81.5 ± 10.6 |
| **V4-neqr-p4** | patch-ensemble NEQR | 128 px, p = 4, s = 4, 4-bit, no stretch | 8 | NEQR patch | 0 | **82.7 ± 10.1** |
| V4-patchmom-rbfsvm | classical control | same patches (64, 8, 4), stretch | — | — | — | 83.6 ± 0.3 |

---

## 2. Experiment families, one by one

### E1/E1b — whole-image FRQI kernels (V2)
1 **Testing**: can the FRQI state overlap alone classify defects? 2 **Why**: it is the most direct "quantum image
classifier". 3 **Hypothesis**: more pixels → more information → better. 4 **Input**: grey images resized to 2–16 px.
5 **Preprocessing**: resize, scale to [0, 1]. 6 **Algorithm**: K = [mean cos(θA−θB)]², SVC C ∈ {0.1…100}.
7 **Circuit**: FRQIEncoder (3–9 qubits). 8 **Parameters**: angle scale b ∈ {1, 2, 4, 8} (E1b). 9 **Expected**:
moderate. 10 **Result**: 43 → 58 % with resolution; b = 2 best (60.6 %); shot noise hurts strongly (1,000 shots: 39 %).
11 **Why**: position-locked comparison; tiny downsampled images lose cracks; with b = 1 similar greys give nearly
identical overlaps. 12 **Learned**: the encoding works but this way of *comparing* images is wrong for textures.
13 **Limits**: small images only. 14 **Changing parameters**: larger b sharpens the kernel until it becomes
near-diagonal (overfits); larger images are expensive (16×16 = 77k gates) and still position-locked.

### E2 — whole-image NEQR kernels (V2)
Same logic. Kernel = squared fraction of positions with identical codes. **4 bits is best**; 8 bits is worse
because exact 8-bit matches are rare (kernel → identity); 2 bits is too coarse. Shot noise affects NEQR less
(56 → 60 %) because codes are discrete.

### E3 — pixel PCA + QKC (V2)
Pixels 64×64 → PCA k → angles × bandwidth → product-RY / ZZ maps (reps 1–2) → SVC. Best ZZ-full PCA-8 64.0 %,
vs classical RBF-SVM on identical angle features 60.7 % and on standard features 64.8 %. **Lesson**: comparable to
classical; PCA of raw pixels keeps little texture (PCA-8 reconstruction SSIM 0.59). Shots: ≥ 500 shots ≈ exact.

### E4 — VQC on pixel PCA (V2)
RY encoding, L ∈ {1,2,3} layers of trainable RY·RZ + CNOT ring, optional re-uploading, 6 ⟨Z⟩ readouts with a
diagonal classical head, cross-entropy, Adam (lr 0.05) / COBYLA / SPSA, parameter-shift gradients, early stopping on
validation. Best 48.1 % (PCA-8, L = 3, re-upload). **Ablation** (frozen random circuit + same head): 16–29 % → the
trained quantum layers do contribute, but the model is weak (hard optimisation; gradient statistics recorded for
barren-plateau checks).

### E5 — hybrid CNN → QKC / VQC (V2)
MobileNetV3 576-d → PCA k → angles → quantum kernel or VQC; **classical controls on identical k-d features**.
k = 8: product-RY 93.2 %, ZZ-full 92.7 %, RBF-SVM 93.0 %, LogReg 92.0 %. **Lesson**: quantum kernels match, not
beat, classical kernels on the same features; the CNN does the feature work. CNN→VQC 81–87 %.

### E6/E7 — classical baselines (V2)
PCA+SVM ≤ 64.8 %; small CNN 93.0 ± 5.9 % (high variance across seeds); frozen MobileNetV3 96.4 %.

### V3 — better features and kernels
Texture features (76-d LBP+GLCM+gradients) and MobileNetV3, PCA 8/12, "c" = CDF angle view (π·Φ(z)).
Best quantum: texture PCA-12 + product-RY QKC 95.3 % ≈ classical texture SVM 95.6 %. **Note**: product-RY is
classically computable, so this is a strong classical-feature result, not quantum evidence. VQCv3 73.4 %, but the
*encoding-only control* (no trainable gates) reaches 92.6 % → the linear head on ⟨Zᵢ⟩ = cos(aᵢ) does most of the
work; trained layers lower accuracy. PQK added (Bloch-vector kernel). FRQI/NEQR re-tuned: still ≈ 60 %.

### V4 — patch-ensemble mixed-state kernels
**Testing**: does comparing *all patch pairs* fix FRQI/NEQR? **Grid** (288 configs): image size, patch/stride,
angle scale (FRQI) or bits (NEQR), stretch on/off, C ∈ {1,10,100,1000}; classical control on the same patches.
**Result**: FRQI-p8 87.8 %, NEQR-p4 82.7 %. **Statistics** (8 pre-declared, Holm): vs V2 FRQI +27.1 pp,
vs V3 FRQI +30.3 pp, NEQR vs V2 +22.5 pp (all p < 0.001); FRQI vs NEQR +5.1 pp (p = 0.045); FRQI vs same-patch
classical +4.2 pp (**p = 0.060, n.s.**); NEQR vs classical −0.9 pp (p = 0.678); vs texture SVM −7.8 / −12.9 pp
(p < 0.001). **Ablation (validation)**: no stretch −8.9 pp, b = 1 −12.2 pp, C = 1 → 53.8 %.
**NEQR variance**: seed 1 misclassifies all rolled-in-scale test images (brightness shift 0.496 → 0.329).
**Proves**: patching fixes the position problem. **Does not prove**: any quantum advantage.

### Reconstruction study (V4, all 1,800 images × 20 methods)
Whole-image FRQI 2–16 px, NEQR 2–16 px × {2,4,8} bits, V4 patch representations, PCA-8/12. Real Qiskit
circuits, Aer statevector + multinomial shots (100 … 100,000). FRQI statevector exact for all images; NEQR exact
at 8 bits; PCA-8 SSIM 0.590.

### Self-check
1. Which experiment shows that the CNN does the heavy lifting? 2. Why is 8-bit NEQR worse than 4-bit?
3. What does the VQC encoding-only control reveal? 4. Which V4 comparison is not significant and why does it matter?
5. Why did V2 test FRQI with shots?
