# Quick Revision Cheat Sheet

## Data
NEU-DET · 1,800 images · 6 classes × 300 · 200×200 grey · train folder 1,440 → train 1,080 / val 360 (blocks of
20 indices, 3 val blocks/class, seeds 0,1,2) · validation folder 360 = **locked test** · SHA-256 manifest.
EDA: rolled-in scale brightness 0.496 (train) vs 0.329 (test) → explains NEQR seed-1 failure.

## Formulas
* FRQI: |I⟩ = N^-½ Σ (cos θᵢ|0⟩ + sin θᵢ|1⟩)|i⟩, θᵢ = (π/2)·b·xᵢ; qubits 2·log₂side + 1; code rotates RY(xᵢπ).
* NEQR: |I⟩ = N^-½ Σ |cᵢ⟩|i⟩, cᵢ = round(xᵢ(2^q−1)); qubits 2·log₂side + q.
* FRQI whole-image kernel: [(1/N)Σcos(θᵢᴬ−θᵢᴮ)]²; NEQR: [(1/N)Σδ(cᵢᴬ,cᵢᴮ)]².
* Patches: P = ((S−p)/s+1)²; ρ = (1/P)Σ|ψₖ⟩⟨ψₖ|; K = Tr(ρAρB) = mean |⟨ψₖᴬ|ψₗᴮ⟩|².
* Swap test: P(0) = ½(1+Tr ρσ) (described, not executed). Stretch: (x−min)/(max−min).
* Product-RY kernel: Π cos²((xᵢ−yᵢ)/2). ZZ: H; P(2xᵢ); CX·P(2(π−xᵢ)(π−xⱼ))·CX.
* Parameter shift: ∂⟨O⟩/∂θ = [⟨O⟩(θ+π/2) − ⟨O⟩(θ−π/2)]/2.
* Decoding: FRQI θ̂ = arcsin√P(1|i); NEQR majority code.
* Precision P = TP/(TP+FP); Recall R = TP/(TP+FN); F1 = 2PR/(P+R); macro-F1 = mean over 6 classes.
* MSE = mean(Δ²); PSNR = 10 log₁₀(1/MSE); SSIM ∈ [−1,1].

## Frozen V4 models
FRQI: 64 px, p 8, s 4, b 4, stretch, C 1000 → 225 patches, 7 qubits, ρ 128×128, 8,339 gates/patch (depth 4,878).
NEQR: 128 px, p 4, s 4, 4-bit, no stretch, C 1000 → 1,024 patches, 8 qubits, ρ 256×256.
Grid 288 configs × 3 seeds = 864 runs, 0 failed; freeze SHA-256; 1 test access per group; 17/17 checks.

## Key results (locked test, mean ± s.d.)
| Model | % |
|---|---|
| MobileNetV3 (frozen) + LogReg (V2) | **96.4 ± 1.1** |
| Texture PCA-12 RBF-SVM (V3) | 95.6 ± 2.2 |
| Texture PCA-12 + product-RY QKC (V3) | 95.3 ± 3.2 |
| CNN PCA-8 + product-RY QKC (V2 hybrid) | 93.2 ± 1.1 |
| Small CNN (V2) | 93.0 ± 5.9 |
| **V4 FRQI patches 8×8** | **87.8 ± 1.5** |
| V4 classical same-patch control | 83.6 ± 0.3 |
| **V4 NEQR patches 4×4** | **82.7 ± 10.1** |
| V3 VQC texture PCA-8 | 73.4 ± 3.8 |
| V2 pixel PCA-8 ZZ-full QKC | 64.0 ± 3.5 |
| V2 whole-image FRQI 8×8 (b = 2) | 60.6 ± 1.2 |
| V2 whole-image NEQR 16×16 4-bit | 60.2 ± 0.4 |
| V2 VQC pixel PCA-8 | 48.1 ± 1.9 |

## V4 comparisons (Holm over 8)
vs V2 FRQI +27.1 pp · vs V3 FRQI +30.3 · NEQR vs V2 +22.5 (all p < 0.001) · FRQI vs NEQR +5.1 (p 0.045) ·
**FRQI vs same-patch classical +4.2 (p 0.060, n.s.)** · NEQR vs classical −0.9 (0.678) · vs texture SVM −7.8 / −12.9.

## Reconstruction (all 1,800 images)
FRQI statevector exact; 1,000 shots MSE 8.7e-3 (8×8), 6.4e-2 (16×16); 100k shots 16×16 2.6e-4.
NEQR 4-bit floor 3.68e-4; 8-bit lossless. PCA-8 SSIM 0.590.

## Stack
Python 3.11 · FastAPI · Qiskit 2.5.2 + Aer 0.17.2 · own NumPy statevector sim · scikit-learn 1.9.1 · PyTorch 2.15 /
torchvision (mobilenet_v3_small IMAGENET1K_V1, 576-d) · React 19 + TypeScript + Vite + Tailwind · pytest 179 ·
Vitest 27 · Playwright.

## Must-say honesty lines
Simulation only · swap test not executed · no quantum advantage · test set reused across protocols ·
V0 not comparable (and its "VQC/HQCC" were classical) · RF/KNN/DT exist only in V0.
