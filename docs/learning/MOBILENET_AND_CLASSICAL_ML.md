# Classical Machine Learning and MobileNetV3 in Q-ImageLab

> Code: `src/v2/cnn.py`, `src/v2/models_classical.py`, `src/v2/features.py`, `src/v3/features.py`,
> `src/v4/models.py` (`PatchMomentRBF`), legacy `src/ml/trainer.py` (V0 only).
> Results quoted are locked-test accuracy, mean ± s.d. over seeds 0–2, from `results/qml_v2|v3|v4/aggregates`.

---

## 1. Foundations from zero

**Neural network.** A function made of layers; each layer computes y = activation(Wx + b). Training adjusts W, b to
reduce a *loss* (for classification: cross-entropy) by gradient descent (backpropagation).

**CNN.** A network whose layers are *convolutions*: a small filter (kernel), e.g. 3×3 weights, slides over the
image and computes a weighted sum at every position → a *feature map*. Early filters detect edges/spots; deeper
filters detect textures and shapes. Because the same filter is used everywhere, CNNs are naturally
translation-tolerant — exactly what defect textures need.

**Pooling.** Down-samples a feature map (max or average over a window). *Global average pooling (GAP)* averages each
channel over the whole map → one number per channel.

**Activation functions.** Non-linearities. **ReLU**(z) = max(0, z). **Hard-swish**(z) = z·ReLU6(z+3)/6 — a cheap
approximation of swish used by MobileNetV3. **Hard-sigmoid** = ReLU6(z+3)/6.

**Batch normalisation.** Normalises activations per channel during training, then scales/shifts; stabilises training.

**Transfer learning / pretrained / feature extraction / fine-tuning.** Use a network trained on a large data set
(ImageNet, 1.28 M photos, 1,000 classes). *Feature extraction*: freeze all weights and use an intermediate layer's
output as a vector (an **embedding**). *Fine-tuning*: continue training some layers on the new task.
**Our project uses feature extraction only — MobileNetV3 is frozen, never fine-tuned.**

---

## 2. MobileNetV3 (Howard et al., ICCV 2019)

**Why it exists.** Accurate image recognition on phones: minimise latency and parameters.

**Building blocks.**
* **Depthwise separable convolution** = *depthwise* conv (one k×k filter per input channel, no channel mixing)
  followed by *pointwise* 1×1 conv (mixes channels). Cost ≈ 1/k² + 1/C_out of a standard conv → ~8–9× cheaper for 3×3.
* **Inverted residual block** (from MobileNetV2): 1×1 *expand* to many channels → depthwise k×k → 1×1 *project*
  back to few channels (linear, no activation); a skip connection when shapes match.
* **Squeeze-and-excitation (SE)**: GAP each channel → tiny 2-layer network → per-channel weights (hard-sigmoid) that
  rescale channels ("attention over channels").
* **Hard-swish** in deeper layers; ReLU in early layers.
* Architecture found by **neural architecture search** (platform-aware NAS + NetAdapt).

**Small vs Large.** Small (≈2.5 M parameters, final feature width 576) targets low-resource devices; Large
(≈5.4 M parameters, width 960) is more accurate but heavier.

**Our exact configuration (`FrozenMobileNetV3Source`).**
* `torchvision.models.mobilenet_v3_small`, weights **`MobileNet_V3_Small_Weights.IMAGENET1K_V1`**, `.eval()`,
  all parameters frozen.
* Preprocessing = the weights' own transforms: 200×200 grey image → RGB (grey copied to 3 channels) → resize 256
  (bilinear) → centre-crop 224 → ImageNet mean/std normalisation.
* Feature = **global average pool of `model.features`** → **576-d vector**. The ImageNet classifier head
  (1024-unit layer + 1000 classes) is **not** used.

**What happens inside (MobileNetV3-Small, from the paper's architecture table).**
224×224×3 → 3×3 conv stride 2, 16 ch, h-swish → 112² → bneck(3×3, SE, ReLU, s2) 16 → 56² → bneck 24 (s2) → 28² →
bneck 24 → bneck(5×5, SE, h-swish, s2) 40 → 14² → bneck 40 ×2 → bneck 48 ×2 → bneck 96 (s2) → 7² → bneck 96 ×2 →
1×1 conv to **576** channels → GAP → 576-d embedding.

**How features reach the classifier.**
* **E7-mnv3-logreg**: 576-d → StandardScaler (train-fitted) → multinomial logistic regression, C ∈ {0.001…100}.
  → **96.4 ± 1.1 %** (best model of the whole project).
* **E7-mnv3-rbfsvm**: same features → RBF-SVM, C ∈ {0.1,1,10,100}, γ ∈ {0.0005,0.002,0.008} → **96.4 ± 1.7 %**.
* **Hybrid E5**: 576-d → StandardScaler → PCA(k = 4, 6, 8) → MinMax[0, π] → quantum kernel or VQC (see
  EXPERIMENTS_EXPLAINED.md).
No loss or optimiser is involved in the MobileNetV3 part (frozen). LogReg uses L-BFGS on cross-entropy; SVM solves
its convex dual.

**Why it is a useful baseline.** It shows what a strong, cheap, *pretrained* classical feature extractor achieves on
the same splits — the ceiling any quantum pipeline must be compared with.

---

## 3. Every classical model actually implemented

| Model | Where | Principle & intuition | Hyper-parameters | Result (locked test) | Why included |
|---|---|---|---|---|---|
| **RBF-SVM** | `models_classical.RBFSVM` | maximum-margin separator; RBF kernel exp(−γ‖x−y‖²) measures similarity | C ∈ {0.1,1,10,100}, γ ∈ {0.03,0.1,0.3,1} (pixel/texture), other grids per phase | pixel PCA-8: 64.8 ± 3.3 %; texture PCA-12: **95.6 ± 2.2 %** | strong, matched control for quantum kernels (same SVM, classical kernel) |
| **Logistic regression** | `models_classical.LogReg` | linear model + softmax, cross-entropy | C ∈ {0.001…100}, lbfgs, max_iter 5000 | MobileNetV3: 96.4 % | simplest linear baseline |
| **Small CNN** | `cnn.SmallCNN` | 4 conv blocks (16-32-64-128 ch, 3×3 conv, BN, ReLU, max-pool) → GAP → dropout 0.3 → linear | Adam lr 1e-3 or 3e-4, wd 1e-4, batch 32, ≤ 60 epochs, early stop patience 10, random flips; 128×128 input | **93.0 ± 5.9 %** | shows an end-to-end network trained from scratch |
| **Frozen MobileNetV3 + LogReg / SVM** | `cnn.py` + above | pretrained embeddings | see §2 | 96.4 % | strongest baseline |
| **Texture RBF-SVM (V3)** | `src/v3/features.py` | LBP histograms (P/R = 8/1, 16/2, 24/3 → 54) + GLCM (32 levels; d = 1,2,4; 4 angles; 6 props → 18) + std, Sobel mean/std, Laplacian var (4) = 76-d → PCA | k = 8, 12; CDF angle view "c" | **95.6 ± 2.2 %** | the best classical texture reference |
| **Patch-moment RBF-SVM (V4 control)** | `v4/models.PatchMomentRBF` | per image: mean patch vector + mean outer product of raw patch intensities (= ρ without the quantum feature map), standardised, RBF-SVM | (S,p,s) ∈ {(64,4,4),(64,8,4),(128,4,4)}, γ ∈ {0.3,1,3}/d, C ∈ {1…1000}, stretch | **83.6 ± 0.3 %** | separates the effect of patching from the quantum encoding |
| **"HQCC" / legacy softmax** | `frqi_neqr.EncodingStatsLogReg`, `LegacyFixedSoftmax` | classical regression on closed-form FRQI/NEQR statistics | — | 26–56 % | honest relabelling of V0 models (they were never quantum) |
| **SVM / RF / KNN / Decision Tree (V0)** | `src/ml/trainer.py` | flattened 64×64 pixels (4,096-d); random stratified split of the train folder (1,008 / 360 / 432), seed 42 | RF 200 trees; KNN k = 5; DT depth 20; SVM C = 10 | SVM 76.6 %, RF 70.6 %, KNN 49.8 %, DT 50.7 % | **historical only — different split, not comparable** |

> Random Forest, KNN and Decision Tree exist **only** in V0. Do not present them as V2–V4 baselines.

### Brief model intuitions
* **SVM**: find the boundary with the widest gap between classes; only "support vectors" matter; kernels let the
  boundary be non-linear. Multi-class in sklearn: one-vs-one (15 binary SVMs for 6 classes), majority vote.
* **Logistic regression**: weighted sum per class → softmax probabilities; fast, interpretable, linear.
* **Random forest** (V0): many decision trees on bootstrap samples; vote. Robust but on raw pixels weak.
* **KNN** (V0): class of the k nearest training images — distance on raw pixels is a poor similarity for textures.
* **Decision tree** (V0): axis-aligned yes/no splits; overfits (train 100 %, test 50.7 %).

### What the classical results tell us
Representation dominates: pixels ≈ 55–65 %, CNN or texture features ≈ 92–96 %. Quantum kernels follow the same
pattern (pixel QKC 64.0 %, CNN+QKC 93.2 %, texture QKC 95.3 %) — the classical feature does the heavy lifting.

### Self-check
1. Why is depthwise separable convolution cheaper? 2. What is the 576-d vector exactly? 3. Did we fine-tune
MobileNetV3? 4. Why compare a QKC with an RBF-SVM on identical features? 5. What does the patch-moment control
prove? 6. Why are V0 RF/KNN numbers not comparable?
