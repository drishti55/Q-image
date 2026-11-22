# Har Experiment, Samjhaaya Hua

> Sources: `scripts/v2/phase*.py`, `scripts/v3/run_v3.py`, `scripts/v4/run_v4.py`, aur aggregates
> (`analysis.json`, `v3_results.json`, `v4_results.json`). Accuracy = locked test, seeds 0–2 ka mean ± s.d. (360 images).
> Saara quantum compute: exact noiseless CPU simulation. Selection hamesha mean **validation** macro-F1 se.

---

## 0. Common protocol (V2–V4)
Har image ka SHA-256 manifest → har seed ka split (train 1,080 / val 360, 20 consecutive indices ke blocks, har class ke 3 val
blocks) → har configuration × 3 seeds train → group-wise validation se select → freeze → saved model ko 360-image locked test
par **ek baar** evaluate. Counts: V2 88 groups / 2,583 runs; V3 70 groups / 5,316 runs; V4 5 groups / 864 runs; sab mein 0 failed.

---

## 1. Master table (har group ka selected configuration)

| ID | Model | Representation / features | Qubits | Circuit | Shots | Test acc. % |
|---|---|---|---|---|---|---|
| E1-frqi2/4/8/16-qkc | FRQI overlap QKC | whole image 2–16 px | 3/5/7/9 | FRQI encoder | 0 | 43.0 / 52.7 / 57.8 / 57.6 |
| E1b-frqi4/8/16-qkc-scaled | FRQI, angle scale 2 | 4/8/16 px | 5/7/9 | FRQI, b = 2 | 0 | 55.9 / **60.6** / 59.9 |
| E1-frqi8-qkc-shots | FRQI + shot noise | 8 px | 7 | FRQI | 100/1k/10k | 33.5 / 39.3 / 46.3 |
| E2-neqr{r}-b{q}-qkc | NEQR overlap QKC | r = 2,4,8,16; q = 2,4,8 | 4–16 | NEQR encoder | 0 | best 16×16 4-bit **60.2**; 8×8 4-bit 59.9; 8-bit hamesha kharab (16×16 8-bit 50.3) |
| E2-neqr8-b4-qkc-shots | NEQR shot noise | 8 px 4-bit | 10 | NEQR | 100/1k/10k | 56.2 / 59.4 / 60.1 |
| E1/E2-encstats, legacy-softmax | **classical** (V0 relabel) | closed-form statistics | — | none | — | 24–56 |
| E3-pca{k}-qkc-{map} | pixel PCA par QKC | k = 4,6,8 | k | product-RY / ZZ-linear / ZZ-full | 0 | best PCA-8 ZZ-full **64.0 ± 3.5** |
| E3-…-zz_full-shots | QKC shot study | k = 4,6,8 | k | ZZ-full | 100–5,000 | PCA-8: 57.1 (100) → 63.4 (5,000) |
| E4-pca{k}-vqc | VQC | PCA k = 4,6,8 | k | RY enc + L×(RY,RZ)+CX ring | exact | 34.1 / 44.5 / **48.1** |
| E4-…-ablation-frozen | frozen random circuit + head | PCA | k | same, untrained | exact | 16.4 / 28.3 / 28.6 |
| E5-mnv3pca{k}-qkc | **hybrid** CNN → QKC | MobileNetV3 576-d → PCA k | 4/6/8 | product-RY / ZZ | 0 | best k = 8 product-RY **93.2 ± 1.1** |
| E5-…-rbfsvm / logreg | same features par classical control | same | — | — | — | k = 8: 93.0 / 92.0 |
| E5-mnv3pca{k}-vqc | hybrid CNN → VQC | same | 4/6/8 | VQC | exact | 86.6 / 85.6 / 81.3 |
| E6-pca{k}-rbfsvm / logreg | classical pixels | PCA k | — | — | — | best 64.8 (SVM, k = 8) |
| E7-smallcnn | CNN scratch se | 128 px | — | — | — | 93.0 ± 5.9 |
| E7-mnv3-logreg / rbfsvm | frozen MobileNetV3 | 576-d | — | — | — | **96.4** / 96.4 |
| V3-tex12c-qkc-product_ry | QKC | texture PCA-12, CDF angles | 12 | product-RY | 0 | **95.3 ± 3.2** |
| V3-tex8c-qkc-zz_full | QKC | texture PCA-8 | 8 | ZZ-full | 0 | 93.0 ± 3.0 |
| V3-…-pqk-zz_* | projected quantum kernel | pixels / CNN | 8–12 | ZZ + Bloch vectors | 0 | v3_results.json dekho |
| V3-mnv8c-qkc-* | hybrid | MobileNetV3 PCA-8 | 8 | sab maps | 0 | 91.3 |
| V3-tex8c-vqc | VQC | texture PCA-8 | 8 | VQCv3 | exact | 73.4 ± 3.8 |
| V3-tex8c-vqc-encoding-only | **control** (trainable gates nahi) | texture PCA-8 | 8 | sirf RY | exact | 92.6 |
| V3-frqi8 / V3-neqr16 | FRQI / NEQR re-tuned | whole image | 7 / 12 | encoders | 0 | 57.5 / 60.2 |
| V3-tex12c-rbfsvm | classical texture SVM | texture PCA-12 | — | — | — | **95.6 ± 2.2** |
| V4-frqi-p4 | patch-ensemble FRQI | 64 px, p = 4, s = 4, b = 4, stretch, C = 1000 | 5 | FRQI patch | 0 | 85.3 ± 1.7 |
| **V4-frqi-p8** | patch-ensemble FRQI | 64 px, p = 8, s = 4, b = 4, stretch, C = 1000 | 7 | FRQI patch | 0 | **87.8 ± 1.5** |
| V4-neqr-p2 | patch-ensemble NEQR | 64 px, p = 2, s = 2, 4-bit, no stretch | 6 | NEQR patch | 0 | 81.5 ± 10.6 |
| **V4-neqr-p4** | patch-ensemble NEQR | 128 px, p = 4, s = 4, 4-bit, no stretch | 8 | NEQR patch | 0 | **82.7 ± 10.1** |
| V4-patchmom-rbfsvm | classical control | same patches (64, 8, 4), stretch | — | — | — | 83.6 ± 0.3 |

---

## 2. Experiment families, ek ek karke

### E1/E1b — whole-image FRQI kernels (V2)
1 **Kya test kiya**: kya sirf FRQI state overlap se defects classify ho sakte hain? 2 **Kyun**: yeh sabse seedha "quantum
image classifier" hai. 3 **Hypothesis**: zyada pixels → zyada information → behtar. 4 **Input**: 2–16 px tak resize ki gayi
grey images. 5 **Preprocessing**: resize, [0, 1] scale. 6 **Algorithm**: K = [mean cos(θA−θB)]², SVC C ∈ {0.1…100}.
7 **Circuit**: FRQIEncoder (3–9 qubits). 8 **Parameters**: angle scale b ∈ {1, 2, 4, 8} (E1b). 9 **Expected**: moderate.
10 **Result**: resolution ke saath 43 → 58 %; b = 2 best (60.6 %); shot noise bahut nuksaan karta hai (1,000 shots: 39 %).
11 **Kyun**: position-locked comparison; chhoti images mein cracks gayab; b = 1 par milte-julte greys ke overlaps lagbhag
same. 12 **Seekha**: encoding kaam karta hai, par images ko is tarah *compare* karna textures ke liye galat hai.
13 **Limits**: sirf chhoti images. 14 **Parameters badle toh**: bada b kernel ko sharp karta hai jab tak woh near-diagonal
(overfit) na ho jaaye; badi images mehngi (16×16 = 77k gates) aur phir bhi position-locked.

### E2 — whole-image NEQR kernels (V2)
Same logic. Kernel = identical codes wali positions ka fraction ka square. **4 bits best**; 8 bits kharab kyunki exact 8-bit
match bahut kam hote hain (kernel → identity); 2 bits bahut coarse. Shot noise NEQR ko kam affect karta hai (56 → 60 %) kyunki
codes discrete hain.

### E3 — pixel PCA + QKC (V2)
Pixels 64×64 → PCA k → angles × bandwidth → product-RY / ZZ maps (reps 1–2) → SVC. Best ZZ-full PCA-8 64.0 %, vs same angle
features par classical RBF-SVM 60.7 % aur standard features par 64.8 %. **Lesson**: classical jaisa hi; raw pixels ka PCA bahut
kam texture rakhta hai (PCA-8 reconstruction SSIM 0.59). Shots: ≥ 500 shots ≈ exact.

### E4 — pixel PCA par VQC (V2)
RY encoding, L ∈ {1,2,3} layers trainable RY·RZ + CNOT ring, optional re-uploading, 6 ⟨Z⟩ readouts aur diagonal classical
head, cross-entropy, Adam (lr 0.05) / COBYLA / SPSA, parameter-shift gradients, validation par early stopping. Best 48.1 %
(PCA-8, L = 3, re-upload). **Ablation** (frozen random circuit + same head): 16–29 % → trained quantum layers contribute karte
hain, par model kamzor hai (mushkil optimisation; barren-plateau check ke liye gradient statistics record hote hain).

### E5 — hybrid CNN → QKC / VQC (V2)
MobileNetV3 576-d → PCA k → angles → quantum kernel ya VQC; **same k-d features par classical controls**.
k = 8: product-RY 93.2 %, ZZ-full 92.7 %, RBF-SVM 93.0 %, LogReg 92.0 %. **Lesson**: same features par quantum kernels classical
ke barabar, behtar nahi; feature ka kaam CNN karta hai. CNN→VQC 81–87 %.

### E6/E7 — classical baselines (V2)
PCA+SVM ≤ 64.8 %; small CNN 93.0 ± 5.9 % (seeds mein zyada variance); frozen MobileNetV3 96.4 %.

### V3 — behtar features aur kernels
Texture features (76-d LBP+GLCM+gradients) aur MobileNetV3, PCA 8/12, "c" = CDF angle view (π·Φ(z)).
Best quantum: texture PCA-12 + product-RY QKC 95.3 % ≈ classical texture SVM 95.6 %. **Dhyaan do**: product-RY classically
computable hai, toh yeh strong classical-feature result hai, quantum evidence nahi. VQCv3 73.4 %, par *encoding-only control*
(koi trainable gate nahi) 92.6 % deta hai → ⟨Zᵢ⟩ = cos(aᵢ) par linear head hi zyada kaam karta hai; trained layers accuracy
ghata dete hain. PQK add hua (Bloch-vector kernel). FRQI/NEQR re-tuned: phir bhi ≈ 60 %.

### V4 — patch-ensemble mixed-state kernels
**Test**: kya *saare patch pairs* compare karna FRQI/NEQR ko theek karta hai? **Grid** (288 configs): image size, patch/stride,
angle scale (FRQI) ya bits (NEQR), stretch on/off, C ∈ {1,10,100,1000}; same patches par classical control.
**Result**: FRQI-p8 87.8 %, NEQR-p4 82.7 %. **Statistics** (8 pre-declared, Holm): V2 FRQI se +27.1 pp, V3 FRQI se +30.3 pp,
NEQR V2 se +22.5 pp (sab p < 0.001); FRQI vs NEQR +5.1 pp (p = 0.045); FRQI vs same-patch classical +4.2 pp
(**p = 0.060, n.s.**); NEQR vs classical −0.9 pp (p = 0.678); texture SVM se −7.8 / −12.9 pp (p < 0.001).
**Ablation (validation)**: bina stretch −8.9 pp, b = 1 se −12.2 pp, C = 1 → 53.8 %.
**NEQR variance**: seed 1 par saari rolled-in-scale test images galat (brightness shift 0.496 → 0.329).
**Kya prove hota hai**: patching position problem theek karta hai. **Kya prove nahi hota**: koi quantum advantage.

### Reconstruction study (V4, 1,800 images × 20 methods)
Whole-image FRQI 2–16 px, NEQR 2–16 px × {2,4,8} bits, V4 patch representations, PCA-8/12. Real Qiskit circuits, Aer
statevector + multinomial shots (100 … 100,000). FRQI statevector sab images ke liye exact; NEQR 8 bits par exact; PCA-8 SSIM 0.590.

### Self-check
1. Kaunsa experiment dikhata hai ki asli kaam CNN karta hai? 2. 8-bit NEQR 4-bit se kharab kyun? 3. VQC encoding-only control
kya batata hai? 4. V4 ka kaunsa comparison significant nahi aur kyun important hai? 5. V2 ne FRQI ko shots ke saath kyun test kiya?
