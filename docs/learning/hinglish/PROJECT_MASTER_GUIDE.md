# Q-ImageLab — Project Master Guide (Hinglish)

> Source of truth: repository ka code aur saved result files (audit date: 19 Nov 2026).
> Agar code aur documentation mein farak hai, toh code sahi maana gaya hai aur farak §6 mein likha hai.

---

## 0. Ek paragraph mein poora project

Q-ImageLab ek simple sawaal poochta hai: **kya quantum image encodings (FRQI aur NEQR) real steel-surface defects ko
classify kar sakti hain, aur agar help karti hain toh kya woh quantum part ki wajah se hai?** Hum NEU-DET dataset use
karte hain (1,800 images, 6 defect classes). Saara quantum kaam laptop CPU par *exact simulation* se hota hai — koi
quantum hardware use nahi hua. Chaar protocols (V0 → V2 → V3 → V4) mein humne dekha ki poori image compare karne wale
FRQI/NEQR kernels lagbhag 60 % par atak jaate hain, aur naya **patch-ensemble mixed-state kernel** (V4) unhe
**87.8 ± 1.5 % (FRQI)** aur **82.7 ± 10.1 % (NEQR)** tak le jaata hai. Lekin *same patches* par classical SVM
83.6 ± 0.3 % deta hai (FRQI se significant farak nahi, p = 0.060) aur classical texture features 95.6 ± 2.2 % dete hain.
**Matlab: bada improvement, lekin quantum advantage nahi.** React + FastAPI dashboard har result dikhata hai aur final
model ko live replay karta hai.

---

## 1. Repository audit — kya kya hai

### 1.1 Top-level layout

| Path | Kya hai |
|---|---|
| `api_main.py` | FastAPI app. Purane V0 endpoints rakhta hai aur V2/V3/V4 routers jodta hai. |
| `src/frqi/encoder.py`, `src/neqr/encoder.py` | FRQI aur NEQR ke real Qiskit circuit builders. |
| `src/reconstruction/reconstructor.py` | Decoders: statevector ya measurement counts se image wapas banana. |
| `src/simulation/simulator.py` | Qiskit-Aer wrapper (statevector + shot sampling), V0 aur reconstruction study mein. |
| `src/metrics/evaluator.py` | MSE / PSNR / SSIM (SSIM scikit-image se). |
| `src/ml/trainer.py`, `src/qml/*` | **V0 (historical)** classical trainer (SVM/RF/KNN/DT) aur V0 QML code. |
| `src/v2/*` | Protocol V2 engine: dataset & splits, features, NumPy statevector simulator, QKC, VQC, CNN/MobileNetV3, runner, store, API. |
| `src/v3/*` | Protocol V3: texture features (LBP+GLCM), CDF angle view, projected quantum kernel, better VQC, API. |
| `src/v4/*` | Protocol V4: patch-ensemble mixed-state kernel, classical patch control, live walkthrough wala API. |
| `scripts/v2/phase*.py` | V2 experiment phases. |
| `scripts/v3/*`, `scripts/v4/*` | setup → run → select → freeze → test → analyse → verify; V4 reconstruction study. |
| `results/qml`, `results/models`, `results/experiments` | **V0 historical results** (sirf read). |
| `results/qml_v2`, `results/qml_v3`, `results/qml_v4` | Protocol results: manifests, `experiments/<id>/`, `aggregates/`, `reports/`. |
| `frontend/src/v2/pages/*` | Current dashboard pages (V2–V4). |
| `frontend/src/pages/*` | Purane V0 pages, `/historical-v0/*` par. |
| `tests/` | 179 pytest test functions. |
| `frontend/src/**/*.test.ts(x)` | 27 Vitest tests. |
| `research_paper_visuals/` | Figure/table generators, paper pack, Overleaf project, report assets. |

### 1.2 Sabse important files, ek ek karke

Har file ke liye: **kya · kyun · kaun call karta hai · input → output · technique.**

| File | Kya & kyun | Called by | Input → Output | Technique |
|---|---|---|---|---|
| `src/v2/dataset.py` | 1,800 images ka hashed **manifest** aur **group-blocked splits** banata hai, taaki har protocol same, verify-able data use kare. | sab providers, V3/V4 setup | NEU-DET folders → manifest JSON (path, class, folder, block, SHA-256), har seed ka split | SHA-256; 20 consecutive indices ke blocks; har class ke 3 val blocks; seeds 0,1,2 |
| `src/v2/providers.py` | Model ko seed ke hisaab se train/val/test arrays deta hai. | `runner.py` | seed → `FeatureSet(X, y, paths)` | caching, sirf train par fit |
| `src/v2/features.py` | Pixel PCA aur vector featurisers, do views: *standard* (z-score) aur *angle* (MinMax [0, π]). | providers | images → k-dim features | StandardScaler → PCA → MinMax, **sirf train par fit** |
| `src/v2/qsim.py` | Chhota batched **NumPy statevector simulator** (H, RY, RZ, P, CX), gates ko Qiskit circuit mein bhi record karta hai. | `qkernel.py`, `vqc.py`, V3 | angles → statevectors | exact matrix algebra; Qiskit se 1e-10 tak test |
| `src/v2/qkernel.py` | **Quantum kernel classifier**: `product_ry`, `zz_linear`, `zz_full`; fidelity kernel; optional shot noise; SVC. | phase4, phase7 | angle features → kernel matrix → SVM | K = \|⟨φ(x)\|φ(y)⟩\|², Binomial shot model |
| `src/v2/vqc.py` | **Variational quantum classifier**: RY encoding, L layers trainable RY·RZ + CNOT ring, re-uploading, 6 expectation readouts. | phase5, phase7 | features → class probabilities | parameter-shift; Adam / COBYLA / SPSA |
| `src/v2/cnn.py` | `SmallCNN` (scratch se train) aur `FrozenMobileNetV3Source` (576-d features). | phase3, phase7 | images → logits / 576-d | PyTorch; `mobilenet_v3_small` IMAGENET1K_V1 |
| `src/v2/models_classical.py` | RBF-SVM aur logistic regression. | bahut phases | features → predictions | scikit-learn |
| `src/v2/frqi_neqr.py` | Whole-image FRQI/NEQR **overlap kernels** closed form mein, plus V0 "HQCC"/"VQC" ka imaandaar relabel. | phase6 | images → kernel → SVM | FRQI: [mean cos(θA−θB)]²; NEQR: [equal codes ka fraction]² |
| `src/v2/runner.py` | **Experiment runner**: har config × seed train, validation par select, freeze, ek locked-test evaluation. | sab run scripts | ModelSpecs → experiment folders, selection, test metrics | validation-only selection |
| `src/v2/store.py`, `paths.py` | Result store aur purane results ka **write-protection**. | runner, APIs | — | `assert_writable`, `QIL_PROTECT_V2/V3` |
| `src/v3/features.py` | Texture descriptors (LBP 54 + GLCM 18 + 4 gradient stats = 76-d), CDF angle view. | `run_v3.py` | 128×128 → 76-d → PCA | scikit-image |
| `src/v3/models.py` | V3 QKC, **projected quantum kernel (PQK)**, VQCv3, FRQI/NEQR *overlap* kernels + stretch. | `run_v3.py` | features → predictions | Huang et al. 2021 |
| `src/v4/models.py` | **Patch-ensemble mixed-state kernel** aur **classical patch-moment control**. | `run_v4.py`, V4 API | images → patches → ρ → Tr(ρAρB) → SVM | density matrices |
| `scripts/v4/run_v4.py` | V4 stages `candidates / select / freeze / test`. | `chain_v4.sh` | grid → 864 runs → frozen selection → test | SHA-256 freeze |
| `scripts/v4/analyze_v4.py` | 8 pre-declared comparisons. | test ke baad | predictions → `v4_results.json` | permutation, bootstrap, McNemar, Holm |
| `scripts/v4/verify_v4.py` | 17 integrity checks. | analysis ke baad | files → `v4_verification.json` | hash checks |
| `scripts/v4/reconstruct_all.py` | **1,800 images × 20 methods** reconstruction. | `chain_recon.sh` | images → reconstructions.npz | Qiskit circuits + Aer + shots |
| `src/v4/api.py` | `/api/v4/*`: results, versions, images, **live pipeline**, reconstruction. | frontend | HTTP → JSON | read-only |
| `frontend/src/App.tsx` | Routes, sidebar, header. | browser | — | React Router |
| `frontend/src/v2/api.ts` | `useV2/useV3/useV4` hooks (loading/error/empty states). | sab pages | path → `{data, error, loading}` | fetch |

---

## 2. Architecture map

```
 NEU-DET train (1,440) + validation (360)
        │  src/v2/dataset.py → manifest (SHA-256) → splits seed 0/1/2 (train 1,080 | val 360)
        │  locked test = validation folder (360), har model ke liye ek hi baar
        ▼
 ┌──────────────┬─────────────────────────────┬──────────────────────────────┐
 PIXELS (V2)    CLASSICAL FEATURES            PATCHES (V4)
 FRQI/NEQR      PCA, MobileNetV3 576-d,       64/128 px → p×p patches, stride s
 whole image    texture 76-d → PCA k          FRQI/NEQR patch states → ρ
 │              │                              │
 overlap kernel fidelity / projected kernel   Tr(ρA ρB)
 │              ya VQC                         │
 └──────────────┴──────────────┬───────────────┘
                               ▼
                 SVC(kernel=precomputed)  +  same input par classical controls
                               ▼
 runner: validation selection → SHA-256 freeze → EK locked-test evaluation → predictions.csv
                               ▼
 analyse (permutation / bootstrap / McNemar / Holm) → aggregates → verify (17 checks)
                               ▼
 FastAPI (/api/v2, /api/v3, /api/v4, read-only) ──JSON──► React dashboard
```

---

## 3. Implementation status (code mein verify kiya, UI se andaaza nahi)

| Feature | Status | Saboot |
|---|---|---|
| FRQI / NEQR Qiskit encoders | **Poora implemented** | H + X-sandwich MCRY (FRQI), MCX per set bit (NEQR); tests |
| Statevector / shots se reconstruction | **Poora implemented** | 1,800 × 20 study saved |
| V2 QKC (product-RY, ZZ-linear, ZZ-full) | **Poora implemented** | `qkernel.py` |
| V2 shot-noise kernels | **Implemented (statistical model)** | Binomial(shots, K)/shots; Aer se cross-check |
| VQC (V2/V3) | **Poora implemented** | parameter shift, Adam/COBYLA/SPSA |
| MobileNetV3 features | **Implemented, frozen** (fine-tune nahi) | `cnn.py` |
| Small CNN | **Implemented** | 93.0 ± 5.9 % |
| Hybrid CNN → PCA → QKC / VQC | **Implemented** | `phase7_hybrid.py` |
| V3 texture, PQK, CDF | **Implemented** | `src/v3/*` |
| V4 patch kernel + control | **Implemented** | 864 runs, 0 failed |
| Swap test (hardware ya simulation) | **Implemented nahi** (sirf describe kiya) | kernel exact Tr(ρAρB) se |
| Quantum hardware / noise | **Implemented nahi** | — |
| Live "How it works" | **Implemented, read-only** | `/api/v4/pipeline` saved prediction se match karta hai |
| Dashboard V2–V4 pages | **Implemented, read-only** | numbers API se; Vitest check karta hai |
| Image upload (V0 Encoding Lab) | **Implemented (legacy V0)** | `POST /api/quantum/compare-custom` |
| V0 "run / batch / suite" buttons | **UI mein hain, disabled** | HTTP 409 |
| 3×3 Playground | **Illustrative demo** | precomputed JSON, `illustrative: true` |
| V0 "VQC" aur "HQCC" | **V0 mein galat label** — quantum nahi | V2 mein classical label |
| Random Forest / KNN / Decision Tree | **Sirf V0 (historical)** | random split; compare nahi kar sakte |

---

## 4. Pipeline aasaan bhasha mein

1. **Dataset** — 1,800 grey photos, har class mein 300. *Validation folder* (360) humara **locked test set** hai.
2. **Preprocessing** — grey, resize (2×2 … 128×128), pixels 0–1, optional per-image *contrast stretch*.
3. **Representation** — whole-image FRQI/NEQR state; ya PCA/CNN/texture features ko angles banana; ya (V4) chhote
   patch states ko mix karke density matrix ρ.
4. **Model** — lagbhag hamesha SVM. Quantum models SVM ko *kernel* (similarity table) dete hain; VQC alag hai (gradient
   descent se train hota hai).
5. **Prediction** — SVM vote / VQC probability sabse zyada wali class.
6. **Evaluation** — validation par chunna, locked test par ek baar report karna, 3 seeds, paired statistics.
7. **Results** — JSON/CSV files.
8. **Dashboard** — FastAPI files serve karta hai; React draw karta hai.

---

## 5. Protocol history (versions kyun hain)

| Version | Sawaal | Result |
|---|---|---|
| **V0** | Pehla prototype: pipeline chalta hai? | Chhote runs (~42 train / 12–16 test images), random splits; kuch models galat label. **Read-only, compare nahi.** |
| **V2** | Locked test ke saath fair benchmark: 88 models, 2,583 runs. | Whole-image FRQI 60.6 %, NEQR 60.2 %; pixel QKC 64.0 %; CNN+QKC 93.2 %; MobileNetV3+LogReg 96.4 % (best). |
| **V3** | Behtar features: 70 groups, 5,316 runs. | Texture-PCA12 + QKC 95.3 % ≈ texture SVM 95.6 %; FRQI/NEQR abhi bhi ≈ 60 %. |
| **V4** | FRQI/NEQR ko khud theek karna: 288 configs, 864 runs. | FRQI 87.8 ± 1.5 %, NEQR 82.7 ± 10.1 %; same-patch classical 83.6 ± 0.3 %. |

---

## 6. Audit mein mile discrepancies aur caveats

Inhe chupaaya nahi gaya; viva se pehle zaroor yaad rakho.

1. **Swap test describe kiya, run nahi kiya.** Kernel Tr(ρAρB) statevectors se exact compute hota hai. Sahi wording:
   *swap test se estimate ho sakta hai*.
2. **V4 FRQI circuit resources standard encoder se.** Encoder ka angle `intensity × π` (b = 1) hai, model b = 4 use
   karta hai. Gate *structure* same hai (har non-zero pixel par ek MCRY), sirf angles alag — counts valid hain.
3. **NEQR gate count image par depend karta hai.** Har "1" bit ke liye ek MCX. Paper table (1,998) aur reconstruction
   study (2,901) mein alag sample patches the.
4. **V2 shot-noise classification statistical model hai.** Har kernel entry Binomial(shots, K)/shots; ek type Aer
   se cross-check hua, poore kernels Aer par shot-by-shot nahi chale.
5. **V4 ke liye locked test fresh nahi hai.** V2/V3 ne same test set use kiya; V4 ka idea unke weak results ke baad aaya.
   V4 ke andar selection sirf validation par, test ek hi baar.
6. **NEQR bina stretch ke** best validation mean tha par 3× zyada variance; seed 1 par saari rolled-in-scale images
   galat. Wajah: rolled-in scale ki brightness 0.496 (train folder) vs 0.329 (test folder).
7. **SVM decision shape**: sklearn OvO train karta hai, `decision_function` ovr shape dikhata hai.
8. **V0 labels**: V0 ne softmax regression ko "VQC" aur logistic regression ko "HQCC" kaha tha. Kabhi quantum result
   ki tarah present mat karna.
9. **V3 re-tuned FRQI (57.5 %) V2 (60.6 %) se kam**: validation same (69.4 vs 69.3), test alag — normal selection noise.

---

## 7. Learning path (modules)
1 Audit · 2 Overview · 3 Fundamentals · 4 Dataset · 5 Classical ML · 6 MobileNetV3 · 7 Quantum basics · 8 FRQI ·
9 NEQR · 10 Quantum ML · 11 Hybrids · 12 Experiments · 13 Circuits · 14 Metrics · 15 Backend · 16 Frontend ·
17 Results · 18 Paper · 19 Viva.
