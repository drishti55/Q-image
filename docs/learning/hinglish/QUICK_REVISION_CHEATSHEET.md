# Quick Revision Cheat Sheet (Hinglish)

## Data
NEU-DET · 1,800 images · 6 classes × 300 · 200×200 grey · train folder 1,440 → train 1,080 / val 360 (20 indices ke blocks,
har class ke 3 val blocks, seeds 0,1,2) · validation folder 360 = **locked test** · SHA-256 manifest.
EDA: rolled-in scale brightness 0.496 (train) vs 0.329 (test) → NEQR seed-1 failure ki wajah.

## Formulas
* FRQI: |I⟩ = N^-½ Σ (cos θᵢ|0⟩ + sin θᵢ|1⟩)|i⟩, θᵢ = (π/2)·b·xᵢ; qubits 2·log₂side + 1; code RY(xᵢπ) ghumata hai.
* NEQR: |I⟩ = N^-½ Σ |cᵢ⟩|i⟩, cᵢ = round(xᵢ(2^q−1)); qubits 2·log₂side + q.
* FRQI whole-image kernel: [(1/N)Σcos(θᵢᴬ−θᵢᴮ)]²; NEQR: [(1/N)Σδ(cᵢᴬ,cᵢᴮ)]².
* Patches: P = ((S−p)/s+1)²; ρ = (1/P)Σ|ψₖ⟩⟨ψₖ|; K = Tr(ρAρB) = mean |⟨ψₖᴬ|ψₗᴮ⟩|².
* Swap test: P(0) = ½(1+Tr ρσ) (sirf describe, chalaya nahi). Stretch: (x−min)/(max−min).
* Product-RY kernel: Π cos²((xᵢ−yᵢ)/2). ZZ: H; P(2xᵢ); CX·P(2(π−xᵢ)(π−xⱼ))·CX.
* Parameter shift: ∂⟨O⟩/∂θ = [⟨O⟩(θ+π/2) − ⟨O⟩(θ−π/2)]/2.
* Decoding: FRQI θ̂ = arcsin√P(1|i); NEQR majority code.
* Precision P = TP/(TP+FP); Recall R = TP/(TP+FN); F1 = 2PR/(P+R); macro-F1 = 6 classes ka mean.
* MSE = mean(Δ²); PSNR = 10 log₁₀(1/MSE); SSIM ∈ [−1,1].

## Frozen V4 models
FRQI: 64 px, p 8, s 4, b 4, stretch, C 1000 → 225 patches, 7 qubits, ρ 128×128, har patch 8,339 gates (depth 4,878).
NEQR: 128 px, p 4, s 4, 4-bit, bina stretch, C 1000 → 1,024 patches, 8 qubits, ρ 256×256.
Grid 288 configs × 3 seeds = 864 runs, 0 failed; SHA-256 freeze; har group ka 1 test access; 17/17 checks.

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

## V4 comparisons (8 par Holm)
V2 FRQI se +27.1 pp · V3 FRQI se +30.3 · NEQR V2 se +22.5 (sab p < 0.001) · FRQI vs NEQR +5.1 (p 0.045) ·
**FRQI vs same-patch classical +4.2 (p 0.060, n.s.)** · NEQR vs classical −0.9 (0.678) · texture SVM se −7.8 / −12.9.

## Reconstruction (saari 1,800 images)
FRQI statevector exact; 1,000 shots MSE 8.7e-3 (8×8), 6.4e-2 (16×16); 100k shots 16×16 2.6e-4.
NEQR 4-bit floor 3.68e-4; 8-bit lossless. PCA-8 SSIM 0.590.

## Stack
Python 3.11 · FastAPI · Qiskit 2.5.2 + Aer 0.17.2 · apna NumPy statevector sim · scikit-learn 1.9.1 · PyTorch 2.15 /
torchvision (mobilenet_v3_small IMAGENET1K_V1, 576-d) · React 19 + TypeScript + Vite + Tailwind · pytest 179 · Vitest 27 · Playwright.

## Imaandaari wali lines (viva mein zaroor bolo)
Sirf simulation · swap test nahi chala · quantum advantage nahi · test set protocols mein reuse hua ·
V0 compare nahi kar sakte (aur uske "VQC/HQCC" classical the) · RF/KNN/DT sirf V0 mein hain.
