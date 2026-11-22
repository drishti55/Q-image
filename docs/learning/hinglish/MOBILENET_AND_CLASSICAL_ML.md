# Classical Machine Learning aur MobileNetV3 (Q-ImageLab mein)

> Code: `src/v2/cnn.py`, `src/v2/models_classical.py`, `src/v2/features.py`, `src/v3/features.py`,
> `src/v4/models.py` (`PatchMomentRBF`), legacy `src/ml/trainer.py` (sirf V0).
> Results = locked-test accuracy, seeds 0–2 ka mean ± s.d.

---

## 1. Basics zero se

**Neural network.** Layers se bana function; har layer y = activation(Wx + b) karti hai. Training W, b ko adjust karti hai
taaki *loss* (classification mein cross-entropy) gradient descent (backpropagation) se kam ho.

**CNN.** Network jiski layers *convolutions* hain: chhota filter (kernel), jaise 3×3 weights, image par slide karta hai aur
har jagah weighted sum nikaalta hai → *feature map*. Shuru ke filters edges/spots pakadte hain; gehre filters textures aur
shapes. Same filter har jagah use hota hai, isliye CNN naturally translation-tolerant hote hain — defect textures ke liye
bilkul sahi.

**Pooling.** Feature map ko chhota karna (window par max ya average). *Global average pooling (GAP)* har channel ka poore
map par average → har channel ka ek number.

**Activation functions.** Non-linearities. **ReLU**(z) = max(0, z). **Hard-swish**(z) = z·ReLU6(z+3)/6 — swish ka sasta
approximation jo MobileNetV3 use karta hai. **Hard-sigmoid** = ReLU6(z+3)/6.

**Batch normalisation.** Training ke dauraan har channel ki activations normalise karke scale/shift; training stable.

**Transfer learning / pretrained / feature extraction / fine-tuning.** Bade dataset (ImageNet, 1.28 M photos, 1,000 classes)
par trained network use karna. *Feature extraction*: saare weights freeze karke beech ki layer ka output vector
(**embedding**) lena. *Fine-tuning*: naye task par kuch layers aur train karna.
**Humara project sirf feature extraction karta hai — MobileNetV3 frozen hai, kabhi fine-tune nahi hua.**

---

## 2. MobileNetV3 (Howard et al., ICCV 2019)

**Kyun bana.** Phones par accurate image recognition: kam latency aur kam parameters.

**Building blocks.**
* **Depthwise separable convolution** = *depthwise* conv (har input channel ka apna k×k filter, channels mix nahi) phir
  *pointwise* 1×1 conv (channels mix). Cost ≈ normal conv ka 1/k² + 1/C_out → 3×3 ke liye ~8–9× sasta.
* **Inverted residual block** (MobileNetV2 se): 1×1 *expand* zyada channels mein → depthwise k×k → 1×1 *project* wapas
  kam channels mein (linear); shape match ho toh skip connection.
* **Squeeze-and-excitation (SE)**: har channel ka GAP → chhota 2-layer network → per-channel weights (hard-sigmoid) jo
  channels ko rescale karte hain ("channels par attention").
* Gehri layers mein **hard-swish**; shuru mein ReLU.
* Architecture **neural architecture search** (platform-aware NAS + NetAdapt) se mila.

**Small vs Large.** Small (≈2.5 M parameters, final feature width 576) kam-resource devices ke liye; Large (≈5.4 M
parameters, width 960) zyada accurate par bhaari.

**Humara exact configuration (`FrozenMobileNetV3Source`).**
* `torchvision.models.mobilenet_v3_small`, weights **`MobileNet_V3_Small_Weights.IMAGENET1K_V1`**, `.eval()`, saare
  parameters frozen.
* Preprocessing = weights ke apne transforms: 200×200 grey image → RGB (grey teen channels mein copy) → resize 256
  (bilinear) → centre-crop 224 → ImageNet mean/std normalisation.
* Feature = **`model.features` ka global average pool** → **576-d vector**. ImageNet classifier head (1024 units + 1000
  classes) use **nahi** hota.

**Andar kya hota hai (paper ki architecture table se).**
224×224×3 → 3×3 conv stride 2, 16 ch, h-swish → 112² → bneck(3×3, SE, ReLU, s2) 16 → 56² → bneck 24 (s2) → 28² → bneck 24 →
bneck(5×5, SE, h-swish, s2) 40 → 14² → bneck 40 ×2 → bneck 48 ×2 → bneck 96 (s2) → 7² → bneck 96 ×2 → 1×1 conv **576**
channels → GAP → 576-d embedding.

**Features classifier tak kaise jaate hain.**
* **E7-mnv3-logreg**: 576-d → StandardScaler (train par fit) → multinomial logistic regression, C ∈ {0.001…100}
  → **96.4 ± 1.1 %** (poore project ka best model).
* **E7-mnv3-rbfsvm**: same features → RBF-SVM, C ∈ {0.1,1,10,100}, γ ∈ {0.0005,0.002,0.008} → **96.4 ± 1.7 %**.
* **Hybrid E5**: 576-d → StandardScaler → PCA(k = 4, 6, 8) → MinMax[0, π] → quantum kernel ya VQC.
MobileNetV3 part mein koi loss/optimiser nahi (frozen). LogReg cross-entropy par L-BFGS; SVM apna convex dual solve karta hai.

**Baseline kyun useful.** Batata hai ki strong, sasta, *pretrained* classical feature extractor same splits par kya
achieve karta hai — yahi woh ceiling hai jisse har quantum pipeline ko compare karna chahiye.

---

## 3. Har classical model jo sach mein implemented hai

| Model | Kahan | Principle & intuition | Hyper-parameters | Result (locked test) | Kyun include kiya |
|---|---|---|---|---|---|
| **RBF-SVM** | `models_classical.RBFSVM` | maximum-margin separator; RBF kernel exp(−γ‖x−y‖²) similarity | C ∈ {0.1,1,10,100}, γ ∈ {0.03,0.1,0.3,1} | pixel PCA-8: 64.8 ± 3.3 %; texture PCA-12: **95.6 ± 2.2 %** | quantum kernels ka matched control |
| **Logistic regression** | `models_classical.LogReg` | linear model + softmax | C ∈ {0.001…100}, lbfgs | MobileNetV3: 96.4 % | sabse simple linear baseline |
| **Small CNN** | `cnn.SmallCNN` | 4 conv blocks (16-32-64-128, 3×3, BN, ReLU, max-pool) → GAP → dropout 0.3 → linear | Adam lr 1e-3/3e-4, wd 1e-4, batch 32, ≤ 60 epochs, patience 10, flips; 128×128 | **93.0 ± 5.9 %** | scratch se trained network |
| **Frozen MobileNetV3 + LogReg / SVM** | `cnn.py` | pretrained embeddings | §2 | 96.4 % | sabse strong baseline |
| **Texture RBF-SVM (V3)** | `src/v3/features.py` | LBP (8/1, 16/2, 24/3 → 54) + GLCM (32 levels; d = 1,2,4; 4 angles; 6 props → 18) + std, Sobel, Laplacian (4) = 76-d → PCA | k = 8, 12; CDF view "c" | **95.6 ± 2.2 %** | best classical texture reference |
| **Patch-moment RBF-SVM (V4 control)** | `PatchMomentRBF` | mean patch vector + raw patch intensities ka mean outer product (= quantum feature map ke bina ρ) | (S,p,s), γ, C, stretch | **83.6 ± 0.3 %** | patching ka effect quantum encoding se alag karta hai |
| **"HQCC" / legacy softmax** | `frqi_neqr.py` | closed-form FRQI/NEQR statistics par classical regression | — | 26–56 % | V0 models ka imaandaar relabel |
| **SVM / RF / KNN / Decision Tree (V0)** | `src/ml/trainer.py` | flattened 64×64 pixels (4,096-d); train folder ka random split (1,008 / 360 / 432), seed 42 | RF 200 trees; KNN k = 5; DT depth 20; SVM C = 10 | SVM 76.6 %, RF 70.6 %, KNN 49.8 %, DT 50.7 % | **sirf historical — alag split, compare nahi** |

> Random Forest, KNN aur Decision Tree **sirf** V0 mein hain. Inhe V2–V4 baselines ki tarah present mat karna.

### Models ki chhoti intuition
* **SVM**: classes ke beech sabse chauda gap wala boundary; sirf "support vectors" matter karte hain; kernels se boundary
  non-linear. sklearn multi-class: one-vs-one (6 classes ke liye 15 binary SVMs), majority vote.
* **Logistic regression**: har class ka weighted sum → softmax probabilities; fast, linear.
* **Random forest** (V0): bootstrap samples par bahut trees; vote. Raw pixels par kamzor.
* **KNN** (V0): k nearest training images ki class — raw pixels ki distance textures ke liye achhi similarity nahi.
* **Decision tree** (V0): yes/no splits; overfit (train 100 %, test 50.7 %).

### Classical results kya batate hain
Representation sabse important: pixels ≈ 55–65 %, CNN ya texture features ≈ 92–96 %. Quantum kernels bhi yahi pattern follow
karte hain (pixel QKC 64.0 %, CNN+QKC 93.2 %, texture QKC 95.3 %) — asli kaam classical feature karta hai.

### Self-check
1. Depthwise separable convolution sasta kyun? 2. 576-d vector exactly kya hai? 3. Kya MobileNetV3 fine-tune hua?
4. QKC ko same features par RBF-SVM se compare kyun karte hain? 5. Patch-moment control kya prove karta hai?
6. V0 RF/KNN numbers compare kyun nahi kar sakte?
