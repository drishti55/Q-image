# Q-ImageLab — Slide-wise Content

One page per slide. **On the slide** is the only text that goes on the slide; everything else is for the presenter. Figure paths are relative to `research_paper_visuals/` (PACK = `V4_paper_pack/figures/`, RPT = `Project_Report/figures/`, SHOT = `Project_Report/screenshots_v5/`). All numbers are locked-test accuracy, mean ± s.d. over 3 seeds.

## Slide 1: Title

*Section A · Understanding the problem*

### On the slide

- *Can Quantum Image Encodings Classify Real Steel Defects?*
- FRQI, NEQR and Quantum Kernels Against Classical Baselines
- Q-ImageLab · team names, roll numbers · supervisors · BML Munjal University · November 2026

### Visual

One NEU-DET image (e.g. scratches) beside its FRQI circuit (`RPT/C1_frqi_circuit_2x2.png`), joined by an arrow.

### Key takeaway

This is an experiment on real industrial images, with an honest comparison.

### Speaker notes

"We took a real factory problem, recognising defects on steel, and asked a simple question: can quantum ways of storing images help classify them? And if they do, is it really the quantum part that helps? To find out, we compared every quantum model with a classical model given exactly the same input."

## Slide 2: The problem we are solving

*Section A · Understanding the problem*

### On the slide

- Hot-rolled steel sheets get surface defects during production
- 6 defect types: crazing · inclusion · patches · pitted surface · rolled-in scale · scratches
- Manual inspection is slow and inconsistent → automate it
- Hard because defects appear **anywhere** in the image, and in different brightness

### Concepts to explain

- *Crazing*: a network of fine cracks. *Inclusion*: foreign particles pressed in. *Patches*: large dark or light regions. *Pitted surface*: small pits. *Rolled-in scale*: oxide scale pressed in during rolling. *Scratches*: long straight lines.
- Why it's hard for a computer:
  - defects have **no fixed position** (shown by the class-average images on slide 3);
  - classes look similar locally (inclusion vs pitted surface);
  - brightness differs between the training and test folders (rolled-in scale is darker in the test folder).

### Visual

One sample per class, 6 tiles (`PACK/Fig16_dataset_samples.png`).

### Key takeaway

This is a texture-recognition problem, not a "find the object at a fixed place" problem.

### Speaker notes

"Every steel sheet is inspected for defects. Doing it by eye is slow, so factories automate it. What makes it hard is that a crack can be anywhere on the surface. Keep that in mind, because it explains most of our results."

## Slide 3: Understanding our dataset

*Section A · Understanding the problem*

### On the slide

- NEU-DET (Northeastern University), public
- 1,800 grayscale images · 200×200 pixels · 6 classes × 300
- Split per class: **180 train · 60 validation · 60 locked test**
- Test set = the official validation folder, opened only once per final model

### Concepts to explain

- **Balanced**: every class has exactly 300 images, so accuracy is a fair headline metric.
- **Group-blocked split**: neighbouring file numbers are near-duplicates. Files were grouped into blocks of 20, and whole blocks went to validation, so no near-duplicate sits on both sides.
- **Three seeds** (0, 1, 2) = three different train/validation splits. Every result is mean ± standard deviation over the three.
- **SHA-256 manifest**: a fingerprint of every file proves the data never changed.

### Visual

- Class distribution bars (`RPT/E1_class_distribution.png`)
- Split diagram (1,800 → 1,440 + 360 locked; 1,440 → 1,080 + 360)
- Class-average images (`RPT/E4_class_average_images.png`): crazing, pitted and inclusion average to flat grey

### Key takeaway

Clean, balanced data with a test set that was protected from the start.

### Speaker notes

"Three hundred images per class, perfectly balanced. We locked away 360 images as the final exam and never looked at them while choosing models. Look at these class averages: for crazing or pitted surface the average is almost flat grey, because the defects are in random places."

## Slide 4: How does a normal computer process an image?

*Section A · Understanding the problem*

### On the slide

- Image = grid of pixels; each pixel = one brightness number (0 = black, 1 = white)
- 64×64 image = 4,096 numbers
- Preprocessing: resize → scale to [0, 1] → contrast stretch
- Classifier sees only numbers

### Concepts to explain

- **Pixel**: the smallest dot of the image. **Grayscale**: one brightness value per pixel (no colour).
- **Intensity**: the brightness value, stored as 0–255 and scaled to 0–1.
- **Contrast stretch**: `x′ = (x − min) / (max − min)`, using the image's own darkest and brightest pixel. It removes brightness differences between images; on validation it added +8.9 pp for the patch FRQI model.
- **Feature**: any number that describes the image (a pixel, a texture statistic, a CNN output).

### Visual

A zoomed 4×4 corner of a real image beside its number matrix, e.g.

```
0.42 0.45 0.61 0.58
0.40 0.39 0.66 0.70
0.38 0.41 0.72 0.75
0.37 0.36 0.69 0.71
```
Then the same patch after contrast stretch. You can use `PACK/Fig17_preprocessing_and_mixed_state.png` (left half).

### Key takeaway

To a computer, an image is just a table of numbers.

### Speaker notes

"A computer doesn't see a scratch; it sees a table of brightness numbers. Everything we do, classical or quantum, starts from this table."

## Slide 5: Classical machine learning: our baseline

*Section A · Understanding the problem*

### On the slide

- Image → preprocessing → features → classifier → defect class
- Features tried: raw pixels + PCA · texture (LBP + GLCM) · CNN (MobileNetV3)
- Classifiers: RBF-SVM · logistic regression · small CNN · frozen MobileNetV3

### Concepts to explain

- **PCA**: squeezes many numbers into a few (4–12) by keeping the directions where images differ most. It is fitted on training images only.
- **LBP** (Local Binary Patterns): compares each pixel with its 8 neighbours and builds an 8-bit "micro-pattern" code, then a histogram of codes. **GLCM** (grey-level co-occurrence matrix): counts how often brightness *i* sits next to brightness *j*. Both count *which* local patterns occur, not *where*.
- **CNN**: a neural network that learns visual filters. **MobileNetV3-small** is pretrained on ImageNet photos and used **frozen** (no retraining). Its last layer gives 576 numbers per image.
- **SVM**: finds the boundary between classes with the widest gap. The **RBF kernel** measures similarity as `exp(−γ‖x − y‖²)`.
- **Logistic regression**: a straight-line (linear) classifier.
- Note: Random Forest, KNN and Decision Tree were only in the early V0 prototype and are not part of the evaluated protocol.

### Visual

Five-box pipeline in blue (classical colour), with the feature options listed under the "features" box.

### Key takeaway

Classical models are the yardstick, and they are strong.

### Speaker notes

"Before any quantum model we built strong classical ones. This matters, because a quantum model only means something if it is compared with a good classical model on the same input."

## Slide 6: Why explore quantum computing?

*Section B · Classical and quantum computing*

### On the slide

- *n* qubits are described by 2ⁿ numbers → a huge "feature space"
- Quantum circuits can turn data into states that a normal computer may find hard to compare
- Our question: **does this help on a real image task, under practical limits?**
- Not assumed: faster or more accurate

### Concepts to explain

- **Quantum state space**: 7 qubits are described by 128 numbers (amplitudes), 8 qubits by 256, 50 qubits by about 10¹⁵. Quantum machine learning hopes to use this as a rich space in which to compare data.
- **Superposition**: a qubit can be in a combination of 0 and 1 (see slide 8).
- **Entanglement**: qubits whose states can no longer be described separately. A CNOT gate creates it.
- **Quantum feature map**: a circuit that turns a list of numbers into a quantum state.
- **Quantum kernel**: similarity of two data points = overlap of their quantum states.
- The honest framing: theory says advantage appears only for special data (Huang et al. 2021), and large circuits suffer "kernel concentration" (Thanasilp et al. 2024). So we **test** rather than assume.

### Visual

- Left: bar showing 2ⁿ growth (n = 1 … 10).
- Right: "data → circuit → quantum state → similarity", with a question mark on the last arrow.

### Key takeaway

We explored quantum computing to test a hypothesis, not to promise an advantage.

### Speaker notes

"Quantum computers store information very differently. A few qubits describe a very large space, and the idea in quantum machine learning is to compare data in that space. Whether that actually helps on real images is an open question, so we treated it as an experiment."

## Slide 7: Classical vs quantum computing

*Section B · Classical and quantum computing*

### On the slide

| | Classical | Quantum |
|---|---|---|
| Basic unit | bit: 0 or 1 | qubit: a state with amplitudes for 0 and 1 |
| Data | list of numbers | quantum state made by a circuit |
| Similarity | distance between number lists | overlap between states (kernel) |
| Read-out | read directly | measure many times (shots) |

**Explain:** Keep it visual. The one key difference for this project: in our quantum models, similarity is the **overlap of two quantum states**, `|⟨ψ|φ⟩|²`, which is 1 for identical states and 0 for completely different ones.

### Visual

Two-column comparison graphic: bit as a switch vs qubit as an arrow on a sphere; number list vs circuit; ruler (distance) vs two overlapping waves (overlap).

### Key takeaway

In this project, the quantum part is mainly a new way of measuring similarity.

### Speaker notes

"For us, the important change is how two images are compared. Classically we measure a distance between two lists of numbers. In the quantum version we prepare two quantum states and measure how much they overlap."

## Slide 8: How does a qubit represent information?

*Section B · Classical and quantum computing*

### On the slide

- `|ψ⟩ = α|0⟩ + β|1⟩`, with |α|² + |β|² = 1
- Measurement gives 0 with probability |α|² and 1 with probability |β|²
- One measurement = one 0 or 1 → repeat many times (**shots**) to estimate probabilities

### Concepts to explain

- |0⟩ and |1⟩ are the two basic states (like a bit's 0 and 1).
- α and β are **amplitudes**; their squares are probabilities.
- **Superposition is not "storing both values"**. A measurement gives only one result. The amplitudes decide the odds, and to know them you must prepare and measure the state many times.
- **Statevector**: the full list of amplitudes. In our simulations we compute it exactly. On real hardware it can only be estimated through shots.
- Example: RY(θ) rotates |0⟩ to cos(θ/2)|0⟩ + sin(θ/2)|1⟩. For θ = π/2: 50 % / 50 %.

### Visual

- Bloch sphere with an arrow between the |0⟩ (north) and |1⟩ (south) poles.
- A small histogram of 1,000 shots: about 500 zeros, about 500 ones.

### Key takeaway

Qubits hold probabilities that you only see by repeating measurements. That cost (shots) shows up in our results.

### Speaker notes

"A qubit is like an arrow on a globe. Point it north and it's 0, south and it's 1, anywhere in between and it's a mix. But when you look, you only get 0 or 1. To learn where the arrow points you repeat the experiment many times. Those repetitions are called shots, and they matter a lot later."

## Slide 9: How do we convert images into quantum information?

*Section C · Quantum image representation*

### On the slide

- A quantum circuit cannot "open" an image file
- Pixel values must be written into qubits by gates: **encoding**
- Image → pixel values → encoding circuit → quantum state
- Two classic encodings: **FRQI** and **NEQR**

### Concepts to explain

- **Quantum gate**: an operation on qubits (like a logic gate). **Quantum circuit**: a sequence of gates.
- Encoding has to store two things: **where** each pixel is (position) and **how bright** it is (intensity).
- Both encodings put all positions into superposition with Hadamard (H) gates, then write each pixel's intensity with gates that only act on that position (**controlled gates**).

### Visual

Pipeline: 2×2 image [[0.2, 0.6], [0.9, 0.4]] → numbers → circuit (`RPT/C1_frqi_circuit_2x2.png`).

### Key takeaway

Encoding is a real cost: it is a circuit with many gates.

### Speaker notes

"You can't upload a JPEG into a quantum computer. You have to build a circuit that writes the image into qubits, gate by gate. The two standard recipes are called FRQI and NEQR."

## Slide 10: FRQI: Flexible Representation of Quantum Images

*Section C · Quantum image representation*

### On the slide

- Position qubits hold **where**; one colour qubit holds **how bright** as an **angle**
- `|I⟩ = (1/√N) Σᵢ (cos θᵢ|0⟩ + sin θᵢ|1⟩) ⊗ |i⟩`, θᵢ = (π/2)·b·xᵢ
- 2×2 image: 2 + 1 = 3 qubits · 8×8 patch: 6 + 1 = 7 qubits
- + very few qubits · − brightness read only statistically (needs many shots)

### Concepts to explain

- *N*: number of pixels. *i*: pixel position. |i⟩: the position state (2 position qubits for 4 pixels, 6 for 64).
- *xᵢ*: brightness of pixel *i*, from 0 to 1. θᵢ: its angle. *b*: angle scale (b = 1 is the original FRQI; our best model uses b = 4).
- The colour qubit's cos and sin parts carry the brightness.
- **Example**: pixel 0.2 → θ = 0.31 rad → probability of reading 0 = cos²θ = 0.905. Pixel 0.6 → probability of reading 1 = sin²θ = 0.655.
- **Circuit** (our encoder): H on the position qubits, then for each pixel: X gates select its position → controlled RY(2θᵢ) on the colour qubit → X gates undo.

### Visual

- `RPT/C1_frqi_circuit_2x2.png`
- Platform walkthrough screenshot `SHOT/P08_encoding_frqi_gates.png`

### Key takeaway

FRQI is compact, but brightness hides inside an angle.

### Speaker notes

"FRQI says: put all pixel positions in superposition, and store each pixel's brightness as a rotation angle of one extra qubit. Very few qubits. The catch is that you can only read that angle back by measuring many times."

## Slide 11: NEQR: Novel Enhanced Quantum Representation

*Section C · Quantum image representation*

### On the slide

- Same position qubits; brightness stored as a **q-bit binary number**
- `|I⟩ = (1/√N) Σᵢ |cᵢ⟩ ⊗ |i⟩`, cᵢ = round(xᵢ·(2^q − 1))
- Precision tested: q = 2, 4, 8 bits
- + exact read-out · − more qubits, many multi-controlled gates

### Concepts to explain

- *q*: number of colour qubits (bits). 4 bits give 16 grey levels; 8 bits give 256.
- **Example**: pixel 0.6 with 4 bits → round(0.6 × 15) = 9 → binary **1001**. In FRQI the same pixel is an angle of 0.94 rad.
- **Circuit**: for each pixel, multi-controlled X gates flip exactly the colour qubits whose bit is 1.
- Qubits: 2×2 image with 4 bits = 2 + 4 = 6; 4×4 patch with 4 bits = 4 + 4 = 8; 16×16 image with 8 bits = 16 qubits.

### Visual

- `RPT/C2_neqr_circuit_2x2.png`
- A side-by-side "one pixel, two encodings" graphic: FRQI = arrow at angle 0.94; NEQR = 4 boxes 1 0 0 1

### Key takeaway

NEQR trades qubits for exactness.

### Speaker notes

"NEQR writes brightness as an ordinary binary number, 1001 for this pixel. More qubits, but when you measure you get the exact value back."

## Slide 12: FRQI vs NEQR (implementation facts)

*Section C · Quantum image representation*

### On the slide

(verified numbers)

| | FRQI | NEQR |
|---|---|---|
| Qubits (4×4 image) | 5 | 4 + q (8 with 4 bits) |
| Brightness stored as | angle | q-bit binary |
| Compiled gates, 4×4 | 1,070 | 1,736 (4-bit) · 3,086 (8-bit) |
| Compiled gates, 8×8 | 8,339 (3,584 CX) | 16,041 (4-bit) |
| Gate count | fixed | depends on pixel values |
| Read-out | statistical (shots) | exact (up to quantisation) |
| Reconstruction, 8×8, 1,000 shots (1,800 images) | MSE 0.0087, SSIM 0.52 | MSE 0.00037, SSIM 0.94 (4-bit) |

### Concepts to explain

- **Compiled (transpiled) gates**: real hardware only has simple gates (CX, RZ, SX, X), so every multi-controlled gate is broken into many of them. That is why counts are in the thousands.
- **CX gates** are the noisiest on real hardware, so the CX count matters most.
- **MSE**: mean squared error between original and rebuilt image (lower is better). **SSIM**: structural similarity, 0–1 (higher is better).
- NEQR with 4 bits has a fixed error floor (MSE 3.7×10⁻⁴) from rounding to 16 grey levels.
- Correction to the README: NEQR uses fewer *logical* gates, but more *compiled* gates.

### Visual

- `PACK/Fig10_circuit_resources.png`
- `PACK/Fig11_reconstruction_mse_vs_shots.png`

### Key takeaway

FRQI saves qubits; NEQR saves shots. Neither is cheap in gates.

### Speaker notes

"FRQI needs fewer qubits. NEQR gives the exact value back with far fewer measurements. Both need thousands of basic gates even for a tiny 8×8 image, which is why we kept everything small."

## Slide 13: What is a quantum kernel?

*Section D · Quantum machine learning algorithms*

### On the slide

- Kernel = similarity score between two images (1 = same, 0 = unrelated)
- Quantum kernel: `K(x, y) = |⟨φ(x)|φ(y)⟩|²`, the overlap of their quantum states
- Kernel matrix = similarity of every pair → given to a classical SVM

### Concepts to explain

- |φ(x)⟩ is the state that the feature-map circuit makes from image *x*. ⟨φ(x)|φ(y)⟩ is their overlap, and the square makes it a number between 0 and 1.
- **Worked example** (Product-RY map, 2 features; kernel = cos²(Δ₁/2)·cos²(Δ₂/2)):
  - A = (0.5, 1.0), B = (0.6, 1.1), C = (2.5, 0.2)

| | A | B | C |
|---|---|---|---|
| A | 1 | **0.995** | 0.248 |
| B | 0.995 | 1 | 0.274 |
| C | 0.248 | 0.274 | 1 |

  A and B are near-identical; C is different.
- The kernel matrix for training is 1,080 × 1,080. For each test image we compute its similarity to all 1,080 training images.

### Visual

Three thumbnails labelled A, B, C, and a 3×3 heat-map of the matrix above.

### Key takeaway

The quantum part produces similarity scores; a normal SVM does the classifying.

### Speaker notes

"Classification often comes down to: is this new image more similar to the scratches or to the cracks? A kernel is that similarity score. In a quantum kernel the score is how much two quantum states overlap."

## Slide 14: QKC: Quantum Kernel Classifier

*Section D · Quantum machine learning algorithms*

### On the slide

- Image → features → PCA (k = 4–12) → scale to angles → feature-map circuit → kernel matrix → SVM → class
- k features = k qubits
- Feature maps: Product-RY · ZZ-Linear · ZZ-Full

### Concepts to explain

- **Why PCA**: one qubit per feature, and exact simulation is limited to about 8–12 qubits, so 4,096 pixels or 576 CNN numbers must be squeezed to k = 4, 6, 8 or 12.
- **Why scaling**: each number becomes a rotation angle, so it is min–max scaled to [0, π] and multiplied by a **bandwidth** (0.05–1.0) that controls how sensitive the kernel is.
- **Why a classical SVM**: the quantum circuit only computes similarities. Training the boundary is a standard optimisation that a classical computer does well.
- **Shots**: kernels were computed exactly and also with 100–10,000 shots. With ZZ-Full on 8 PCA pixels: exact 64.0 %, 100 shots 57.1 %, 500+ shots about 63.4 %.

### Visual

QKC row of `RPT/M1_model_architectures.png` (blue/orange boxes).

### Key takeaway

QKC = quantum similarity + classical SVM.

### Speaker notes

"QKC takes a short list of numbers, turns each into a qubit rotation, measures how similar two images' states are, and hands those scores to a normal SVM."

## Slide 15: Understanding quantum feature maps

*Section D · Quantum machine learning algorithms*

### On the slide

- **Product-RY**: one rotation per qubit, no links
- **ZZ-Linear**: neighbouring qubits linked (entangled)
- **ZZ-Full**: every pair linked
- More links ≠ better accuracy

### Concepts to explain

- **Product-RY**: RY(xᵢ) on each qubit. No entanglement, so the kernel is just Π cos²((xᵢ − yᵢ)/2), which an ordinary computer can calculate directly.
- **ZZ-Linear**: H on all qubits, phase P(2xᵢ), then for neighbouring pairs a CX – P(2(π − xᵢ)(π − xⱼ)) – CX block that makes the qubits depend on each other's values (entanglement).
- **ZZ-Full**: the same block on every pair; the CX count grows with the square of the qubit count.
- **Evidence that more entanglement does not mean better**:
  - V3, 12 texture features: Product-RY **95.3 %**, ZZ-Full 89.1 %, ZZ-Linear **60.6 %**.
  - V3, 12 CNN features: 91.2 / 88.1 / 63.2 %.
  - V2, 8 PCA pixels: here entanglement *did* help, ZZ-Full 64.0 vs Product-RY 58.1 %. ZZ-Full even beat an RBF-SVM on the identical angle features (60.7 %) in 2 of 3 seeds. But an RBF-SVM on normally scaled PCA features gets 64.8 %, so the classical model catches up once its input is scaled its own way.
- **Why (kernel concentration)**: with too much entanglement or too large angles, almost every pair of images becomes nearly orthogonal. At 8 qubits, ZZ-Full, reps = 2, bandwidth 1.0, the average off-diagonal kernel value was **0.010**, so every image looks "different from everything" and the SVM has nothing to learn from. With too small a bandwidth (Product-RY, 0.05) the average was **0.999**, so everything looks the same. Bandwidth tuning avoids both extremes.

### Visual

- `RPT/C3_product_ry.png`, `RPT/C4_zz_linear.png`, `RPT/C5_zz_full.png` side by side
- A small bar chart of the three V3 texture-12 accuracies

### Key takeaway

Entanglement makes kernels harder to compute classically, but not automatically better.

### Speaker notes

"We tried three ways of turning numbers into states: no links, neighbour links, and all links. You might expect more quantum entanglement to be better. It wasn't. With 12 qubits the neighbour-linked version dropped to 60 %, because every image started to look unlike every other."

## Slide 16: PQK: Projected Quantum Kernels

*Section D · Quantum machine learning algorithms*

### On the slide

- QKC compares whole states (global overlap)
- PQK looks at **each qubit separately**: its Bloch vector (⟨X⟩, ⟨Y⟩, ⟨Z⟩)
- Then classical RBF similarity on those vectors
- Result: weakest kernel family (best 69.7 %)

### Concepts to explain

- **Reduced density matrix**: the state of one qubit on its own, ignoring the rest. For one qubit it is fully described by 3 numbers (a Bloch vector).
- Kernel: `K = exp(−γ Σ_q ‖b_q(x) − b_q(y)‖² / 2)`.
- **Why tried**: Huang et al. (2021) proposed it to avoid the concentration of global overlaps.
- **What happened** (V3, test accuracy):
  - CNN 8 features: ZZ-Linear PQK 69.7 % vs QKC 91.3 % vs RBF-SVM 90.6 %
  - texture 8 features: PQK 68.9 % vs QKC 93.1 %
  - ZZ-Full PQK: 33–50 % everywhere
- **Hypothesis** (not tested directly): single-qubit summaries throw away the correlations between features that the classifier needed.

### Visual

- Two-row diagram: QKC (state → global overlap) vs PQK (state → 3 numbers per qubit → RBF)
- PQK row of `RPT/M1_model_architectures.png`

### Key takeaway

Looking at qubits one by one lost useful information on this task.

### Speaker notes

"PQK only looks at each qubit on its own instead of the whole state. It's cheaper and avoids one known problem, but on our data it lost about 20 points compared with the normal quantum kernel."

## Slide 17: VQC: Variational Quantum Classifier

*Section D · Quantum machine learning algorithms*

### On the slide

- A quantum circuit with **trainable knobs** (angles), like a tiny neural network
- Input → RY encoding → L layers [RY·RZ + CNOT ring] → measure ⟨Z⟩ → class scores
- Train: prediction → error → gradient (parameter-shift) → update (Adam)
- Result: never beat classical; the encoding-only control beat the trained circuit

### Concepts to explain

- **Trainable parameters**: the angles of the RY and RZ gates in each layer.
- **RY / RZ**: rotate the qubit around the Y / Z axis.
- **CNOT ring**: CX from qubit 0→1→2→…→0, which spreads information between qubits.
- **Measurement ⟨Z⟩**: the average of +1/−1 outcomes on each qubit. These become class scores, then softmax gives probabilities.
- **Parameter-shift rule**: `∂⟨O⟩/∂θ = [⟨O⟩(θ + π/2) − ⟨O⟩(θ − π/2)] / 2`. Run the circuit twice with the angle nudged ±90° to get the exact gradient.
- **Optimisers tried in V2**: Adam (gradient-based, main one), COBYLA and SPSA (gradient-free). Grid: k = 4, 6, 8; L = 1, 2, 3; data re-upload on/off. V3 adds an SPSA group.
- **Results**:
  - pixel PCA 8: VQC 48.1 % vs RBF-SVM 64.8 %; VQC was worse in all 3 seeds (significant);
  - trained vs frozen random circuit: 48.1 vs 28.6 %, so training does help over random;
  - V3: **encoding-only control 90.8 % vs trained VQC 72.4 %** (CNN 8) and **92.6 vs 73.4 %** (texture 8). The trained layers hurt;
  - VQC is also the slowest to train: about 1,060 s per run vs 0.007 s for RBF-SVM.
- **Barren plateaus (evidence)**: the measured variance of gradients at initialisation drops as circuits grow, from 5.1×10⁻³ (4 qubits, 3 layers) to 9.3×10⁻⁵ (8 qubits, 3 layers), about 55× smaller. Small gradients make training hard.

### Visual

- `RPT/C6_vqc_ansatz.png`
- Training loop arrow cycle: input → circuit → measure → loss → parameter-shift → Adam → back

### Key takeaway

A trainable quantum circuit was the hardest model to train and the least accurate.

### Speaker notes

"VQC is the quantum cousin of a neural network: the circuit has knobs that training adjusts. In our tests the knobs made things worse. A version without the trainable layers scored 18 points higher. As circuits grew, the gradients became tiny, which is a known problem called barren plateaus."

## Slide 18: Hybrid quantum-classical architecture

*Section D · Quantum machine learning algorithms*

### On the slide

- Image → **MobileNetV3 (frozen)** → 576 features → PCA → k = 4–8 → quantum classifier (QKC or VQC) → class
- Classical part: sees the image · Quantum part: classifies a short vector
- Best hybrid: **93.2 ± 1.1 %** (V2, PCA 8 + QKC Product-RY)

### Concepts to explain

- **CNN feature extraction**: a pretrained network converts the image into 576 numbers that describe edges, textures and shapes. It is frozen (not retrained).
- **576-dimensional vector**: the average activation of each of the 576 feature channels in the last layer.
- **PCA → k**: one qubit per feature, so 576 must shrink to 4–8.
- The quantum circuit only ever sees those k numbers; all image understanding is classical.

### Visual

- Hybrid row of `RPT/M1_model_architectures.png` (green CNN box, orange quantum boxes)
- `SHOT/P12_cnn_layer1.png` (real feature maps) and `SHOT/P13_cnn_qubits.png` (576 → angles)

### Key takeaway

In the hybrid, the CNN does the seeing; the quantum part only does the final comparison.

### Speaker notes

"Hybrids give the quantum circuit a head start: a pretrained network turns the image into 576 meaningful numbers, we shrink them to 8, and a quantum kernel classifies them. They score over 90 %, but as you'll see, the credit belongs mostly to the CNN."

## Slide 19: Patch-ensemble mixed-state kernel (our proposed method, V4)

*Section D · Quantum machine learning algorithms*

### On the slide

- Cut the image into small patches → encode **each patch** with FRQI/NEQR
- Image = average of its patch states: **ρ = (1/P) Σₖ |ψₖ⟩⟨ψₖ|** (a mixed state)
- Similarity: **K(A, B) = Tr(ρ_A ρ_B)**, every patch of A compared with every patch of B
- FRQI: 64×64 image · 8×8 patches · stride 4 → 225 patches · 7 qubits each

### Concepts to explain

- **Why patches**: a whole-image FRQI overlap is (1/N) Σᵢ cos(θᵢᴬ − θᵢᴮ), which compares pixel *i* only with pixel *i*. Shift a texture and the score drops.
  - Example: a 2×2 patch [0.2, 0.6, 0.9, 0.4] compared with itself gives overlap 1.0. Compared with a rearranged version [0.6, 0.2, 0.4, 0.9] it gives only 0.758 (fidelity 0.575), even though it contains the same pixel values.
- **Patch size and stride**: P = ((S − p)/s + 1)² = ((64 − 8)/4 + 1)² = 15² = 225.
- **Pure vs mixed state**: one patch = one definite state (pure). An image = a probability mix of 225 patch states (mixed), stored as a **density matrix** ρ (128×128 for 7 qubits).
- **Kernel**: Tr(ρ_A ρ_B) = (1/P²) Σₖ Σₗ |⟨ψₖᴬ|ψₗᴮ⟩|², the average squared overlap over all patch pairs. A texture element anywhere in both images contributes.
- **Properties**: a valid kernel (positive semi-definite); tolerant to shifts; cheap to compute exactly (O(P·D²) per image); registers of at most 8 qubits.
- **On hardware**: a swap test on two 7-qubit patch registers + 1 ancilla (15 qubits) would estimate it: Pr[ancilla = 0] = ½(1 + Tr(ρσ)). In this project it was computed exactly; the swap test was not run.
- **Final settings**:
  - FRQI: 64×64, 8×8 patches, stride 4, angle scale b = 4, contrast stretch, C = 1000.
  - NEQR: 128×128, 4×4 patches, stride 4 (1,024 patches), 4 bits, no stretch, C = 1000 (8 qubits).

### Visual

- `PACK/Fig02_patch_encoding_illustration.png` (image → patches → amplitudes → ρ → kernel)
- Patch-ensemble row of `RPT/M1_model_architectures.png`
- `RPT/C7_swap_test.png` (small, in a corner)

### Key takeaway

Same FRQI/NEQR encoding, compared in a position-free way.

### Speaker notes

"Here's our idea. Don't encode the whole image as one state. Cut it into 225 small patches, encode each one, and describe the image as a mix of all of them. Then two images are similar if their patches look alike, wherever those patches are. That's exactly what textures need."

## Slide 20: How we kept the test fair

*Section E · Experiments and results*

### On the slide

- Choose models on **validation data only** (macro-F1)
- Freeze choices with SHA-256 → test each model **once**
- 3 seeds · matched classical control · 8 comparisons declared **before** testing

### Concepts to explain

- **Leakage**: when information from the test set influences model choice, the test score becomes optimistic.
- **Macro-F1**: F1 averaged equally over all six classes, so no class can fail unnoticed.
- **SHA-256 freeze**: the selected settings are fingerprinted; if anything changes before testing, the run aborts.
- **Locked-test access log**: every test access is recorded (V3: 70 events for 70 groups; V4: 5 for 5).
- **Matched control**: a classical model given exactly the same input (same patches, same features).
- **Statistics**: paired permutation test (10,000 sign flips), paired bootstrap 95 % CI, McNemar per seed, and Holm correction for testing 8 comparisons at once.
- **Honest caveat**: the same 360 test images were also used in V2 and V3, so the decision to try patches was informed by earlier test results. Within V4, every model was selected on validation only.

### Visual

`PACK/Fig01_methodology_flowchart.png` panel (a).

### Key takeaway

The numbers that follow are trustworthy because the test set was protected.

### Speaker notes

"We never looked at the final exam while choosing models. Choices were made on a practice set, locked with a digital fingerprint, and then each model sat the exam once."

## Slide 21: Experimental setup

*Section E · Experiments and results*

### On the slide

(compact table)

| Item | Values tried |
|---|---|
| Image sizes | 2×2 … 128×128 (whole-image), 32/64/128 (V4) |
| FRQI | angle scale b = 1, 2, 4 |
| NEQR precision | 2, 4, 8 bits (V2/V3); 3–6 bits (V4) |
| Shots | exact; 100, 500, 1,000, 5,000, 10,000 |
| PCA dimensions | 4, 6, 8 (V2); 8, 12 (V3) |
| Feature maps | Product-RY, ZZ-Linear, ZZ-Full; reps 1–2; bandwidth 0.05–1.0 |
| PQK | ZZ-Linear, ZZ-Full on 8/12 features |
| VQC | k = 4, 6, 8; L = 1–3; Adam / COBYLA / SPSA; re-upload on/off |
| Hybrid | MobileNetV3 → PCA 4/6/8/12 → QKC or VQC |
| V4 patches | FRQI 4×4, 8×8; NEQR 2×2, 4×4; strides 1–8; stretch on/off; C up to 1000 |
| Classical | RBF-SVM, logistic regression, small CNN, frozen MobileNetV3; matched patch-moment RBF-SVM |
| Hardware | one laptop CPU (Apple M5, 16 GB); exact simulation; at most 16 qubits (whole-image NEQR 16×16, 8-bit) |

### Key takeaway

Many configurations, all on the same data and test set.

### Speaker notes

"This is the search space. Every one of these settings was tried on the practice set before the final test."

## Slide 22: Complete experiment coverage

*Section E · Experiments and results*

### On the slide

- V2: **2,583 runs → 88 models**
- V3: **5,316 runs → 70 models**
- V4: **864 runs → 5 models**
- **163 models** on the same 360 test images · 0 failed runs
- Reconstruction: all **1,800 images × 20 methods**

### Concepts to explain

- V2 by category: 24 classical, 21 quantum-kernel, 25 FRQI/NEQR kernel, 6 VQC and 12 hybrid groups.
- "Selected model" = the best configuration of a group, averaged over 3 seeds.
- Every run saves its configuration, validation metrics, predictions, confusion matrix and circuit statistics.

### Visual

- Stacked bar by version
- `RPT/M4_all_models.png` (163 dots)

### Key takeaway

This is a broad, systematic benchmark, not a single lucky run.

### Speaker notes

"Over eight and a half thousand training runs, 163 final models, all scored on the same 360 images."

## Slide 23: Classical model results

*Section E · Experiments and results*

### On the slide

| Model (V2/V3) | Test accuracy |
|---|---|
| Frozen MobileNetV3 + LogReg (576 features) | **96.4 ± 1.1** |
| Frozen MobileNetV3 + RBF-SVM | 96.4 ± 1.7 |
| Texture (LBP+GLCM, 12) + RBF-SVM | 95.6 ± 2.2 |
| Small CNN from scratch | 93.0 ± 5.9 |
| MobileNet PCA 8 + RBF-SVM | 93.0 ± 0.7 |
| Pixel PCA 8 + RBF-SVM | 64.8 ± 3.3 |
| Pixel PCA 8 + LogReg | 38.1 ± 1.4 |

### Concepts to explain

- **Accuracy** = correct / total. **Precision** = of the images predicted "crazing", how many were crazing. **Recall** = of the real crazing images, how many were found. **F1** = 2PR/(P + R).
- Macro-F1 values track accuracy closely here (e.g. MobileNet + LogReg F1 96.3 %).
- The pattern: **features matter more than the classifier**. Raw pixels → 38–65 %; texture or CNN features → 93–96 %.

### Visual

Horizontal bar chart of the table (blue). If you want a confusion matrix, take it from the platform's Model families page (`SHOT/P04_model_families.png`).

### Key takeaway

Good features reach about 96 %; raw pixels don't.

### Speaker notes

"A pretrained network with a simple classifier gets 96 %. The same classifier on raw pixels gets 65 % at best. Remember this gap; it explains the quantum results."

## Slide 24: Quantum model results

*Section E · Experiments and results*

### On the slide

(V3 family representatives, chosen by validation)

| Family | Input | Acc | Prec | Rec | F1 | Train | Inference/img |
|---|---|---|---|---|---|---|---|
| QKC | texture, 12 qubits | **95.3** | 96 | 95 | 95 | 3.5 s | 1.44 ms |
| PQK | CNN, 8 qubits | 69.7 | 72 | 70 | 69 | 0.7 s | 0.047 ms |
| VQC | CNN, 8 qubits | 72.4 | 74 | 72 | 72 | ~1,060 s | 0.036 ms |
| Whole-image FRQI | pixels 8×8 | 57.5 | — | — | — | — | — |
| Whole-image NEQR | pixels 16×16, 4-bit | 60.2 | — | — | — | — | — |
| *RBF-SVM (classical)* | *CNN* | *90.6* | *92* | *91* | *90* | *0.007 s* | *0.003 ms* |

### Concepts to explain

- QKC is only as good as its input: normalised pixels 48.0 %, pixels 64.0 %, CNN 91.3 %, texture 95.3 %.
- Every quantum family is 1–3 orders of magnitude slower than RBF-SVM, because the quantum part is simulated.

### Visual

- `RPT/M2_family_metrics.png`
- `RPT/M3_family_timing.png`

### Key takeaway

The best quantum model is excellent, but only on texture features that already work classically.

### Speaker notes

"The best quantum kernel hits 95 %, but on texture features that give a classical SVM 95.6 % as well. The trained quantum circuit and the projected kernel lag far behind, and everything quantum is slower."

## Slide 25: Hybrid model results

*Section E · Experiments and results*

### On the slide

(V2, MobileNet features, test accuracy %)

| PCA k | QKC Product-RY | QKC ZZ-Linear | QKC ZZ-Full | VQC | RBF-SVM | LogReg |
|---|---|---|---|---|---|---|
| 4 | 88.4 | 89.0 | 87.8 | 86.6 | 88.4 | 85.9 |
| 6 | 90.6 | 91.0 | 90.0 | 85.6 | 91.1 | 90.6 |
| 8 | **93.2** | 91.9 | 92.7 | 81.3 ± 7.2 | 93.0 | 92.0 |

### Concepts to explain

- **More PCA components helped** every kernel model (k = 4 → 8: +4.8 pp for Product-RY), because more information survives.
- **Feature map made little difference** on CNN features (all within about 1.5 pp).
- **QKC > VQC** at every k; VQC got worse and unstable at k = 8.
- **QKC ≈ RBF-SVM** at every k. The paired McNemar tests found no significant difference in any seed at k = 4, and in at most 1 of 3 seeds at k = 6.
- The full 576 features with plain logistic regression (96.4 %) beat every hybrid: PCA to 8 loses information.

### Visual

Line chart: x = k (4, 6, 8), one line per model; QKC lines overlap the RBF-SVM line.

### Key takeaway

In the hybrid, swapping the quantum kernel for a classical one changes nothing.

### Speaker notes

"Here's the hybrid table. More PCA components help, the choice of quantum circuit hardly matters, and the classical SVM on the very same 8 numbers matches the quantum kernel line for line."

## Slide 26: FRQI vs NEQR results

*Section E · Experiments and results*

### On the slide

- Whole-image classification: FRQI **60.6 %** (8×8, angle ×2) · NEQR **60.2 %** (16×16, 4-bit)
- Patch-ensemble (V4): FRQI **87.8 ± 1.5 %** vs NEQR **82.7 ± 10.1 %** (+5.1 pp, Holm p = 0.045)
- With shots, NEQR is robust and FRQI collapses

### Concepts to explain

- **Resolution** (FRQI whole image): 2×2 43.0 → 4×4 52.7 → 8×8 57.8 → 16×16 57.6 %.
- **NEQR bits** (16×16): 2-bit 53.1, **4-bit 60.2**, 8-bit 50.3 %. More bits is *worse*. NEQR's overlap is all-or-nothing per pixel (codes must match exactly), so with 256 levels almost nothing matches.
- **Shots** (8×8 whole-image kernels):

| | exact | 10,000 | 1,000 | 100 |
|---|---|---|---|---|
| FRQI | 57.8 | 46.3 | 39.3 | 33.5 |
| NEQR 4-bit | 59.9 | 60.1 | 59.4 | 56.2 |

- **Reconstruction** (all 1,800 images, 8×8):
  - FRQI is exact from the statevector, but needs 100,000 shots for SSIM 0.99;
  - NEQR 4-bit reaches SSIM 0.94 from 1,000 shots, limited only by rounding.
- **Why FRQI wins the patch kernel**: its overlap changes smoothly with brightness (cos of the angle difference), so similar patches score as similar. NEQR's seed-1 result (71.1 %) failed on rolled-in scale, which is darker in the test folder, and the NEQR model has no contrast stretch.

### Visual

- `PACK/Fig04_frqi_neqr_across_protocols.png`
- `PACK/Fig12_reconstruction_examples.png`

### Key takeaway

NEQR is better for reading images back; FRQI is better for comparing textures.

### Speaker notes

"Which encoding is better depends on the job. To rebuild an image from few measurements, NEQR wins clearly. To compare textures, FRQI's smooth similarity wins, and it's far more stable across splits."

## Slide 27: Patch-ensemble results (V4)

*Section E · Experiments and results*

### On the slide

| Model | Test accuracy |
|---|---|
| Whole-image FRQI (V2) | 60.6 ± 1.2 |
| Whole-image NEQR (V2) | 60.2 ± 0.4 |
| **Patch FRQI 8×8** | **87.8 ± 1.5** |
| **Patch NEQR 4×4** | **82.7 ± 10.1** |
| Classical, same patches | 83.6 ± 0.3 |
| Classical texture | 95.6 ± 2.2 |

- FRQI +27.1 pp (95 % CI 21.7–32.7, p < 0.001) · NEQR +22.5 pp (p < 0.001)

### Concepts to explain

- **Forest plot**: each line is one comparison with its 95 % CI. If the line doesn't cross 0, the difference is real.
- **Ablation** (FRQI):
  - remove patches: −27.1 pp;
  - replace quantum states by classical patch moments: −4.2 pp (not significant);
  - 4×4 instead of 8×8 patches: −2.5 pp;
  - on validation, no stretch −8.9 pp; b = 1 instead of 4: −12.2 pp; C = 1 instead of 1000: −34 pp.
- Confusions: inclusion ↔ pitted surface, scratches → rolled-in scale.

### Visual

- `PACK/Fig03_main_results.png`
- `PACK/Fig05_comparisons_forest.png`
- `PACK/Fig06_confusion_matrices.png` (backup slide)

### Key takeaway

Patching made quantum image kernels competitive, raising them by about 25 points.

### Speaker notes

"With the patch method, FRQI jumps from 61 to 88 %, and NEQR from 60 to 83 %. Those are big, statistically solid gains. The next slide asks the important question: whose gain is it?"

## Slide 28: Understanding the results

*Section E · Experiments and results*

### On the slide

(six questions, six answers)

- Did more PCA components help? **Yes** (e.g. pixels + ZZ-Full: 52.4 → 64.0 %)
- Did trainable quantum layers help? **No** (encoding-only 90.8 % > trained VQC 72.4 %)
- Did entanglement help? **Not consistently** (Product-RY 95.3 % > ZZ-Linear 60.6 % on texture)
- Did FRQI beat NEQR? **Yes, for patch kernels** (+5.1 pp); **NEQR for read-out**
- Did patching help? **Yes, the biggest single effect** (+27.1 pp)
- Best / worst: MobileNet + LogReg 96.4 % · VQC with SPSA on pixels 21.0 % (a frozen random-circuit control scored 16.4 %, at chance level)

### Concepts to explain

- **Evidence** sits with every answer above; cite it when asked.
- **Hypotheses** (label them as such):
  - (a) VQC suffers from small gradients (measured gradient variance shrinks 55× from 4 to 8 qubits).
  - (b) Strong entanglement concentrates kernels (measured off-diagonal mean 0.010 at 8 qubits, ZZ-Full reps 2).
  - (c) FRQI's smooth overlap suits texture similarity.

### Visual

A 6-row "question → yes/no → evidence number" grid with green/red markers.

### Key takeaway

Input representation and comparison method mattered; added quantum complexity didn't.

### Speaker notes

"Let me answer the six questions people usually ask. Notice the pattern: what helped was better inputs and a better way to compare images. Extra quantum machinery, trainable layers and more entanglement, didn't help."

## Slide 29: Did quantum actually perform better than classical?

*Section E · Experiments and results*

### On the slide

| Comparison (same input) | Quantum | Classical | Verdict |
|---|---|---|---|
| Patches (V4) | FRQI 87.8 | 83.6 | +4.2 pp, **p = 0.060, not significant** |
| Patches (V4) | NEQR 82.7 | 83.6 | −0.9 pp, p = 0.68 |
| CNN PCA 8 (V2) | QKC 93.2 | RBF-SVM 93.0 | tie |
| Texture 12 (V3) | QKC 95.3 | RBF-SVM 95.6 | tie |
| Best overall | 95.3 (QKC) | **96.4** (MobileNet + LogReg) | classical |

- **Answer: no measurable quantum advantage**
- Quantum is also slower (simulated), needs thousands of gates per patch, and has only been run in noiseless simulation

### Concepts to explain

- Cost:
  - FRQI 8×8 patch: 7 qubits, 8,339 compiled gates, depth 4,878, 3,584 CX;
  - swap test: 15 qubits;
  - QKC inference 1.44 ms/image vs 0.003 ms for RBF-SVM;
  - VQC training about 1,060 s vs 0.007 s.
- **Why the tie matters**: it shows the patch improvement comes from the **representation** (comparing local patterns anywhere), which classical methods can use equally well.
- Every kernel here has a closed form that a laptop computes exactly. Real advantage would need circuits that classical computers *cannot* simulate.

### Visual

Side-by-side bars (orange quantum vs blue classical) for each matched pair, with "n.s." labels.

### Key takeaway

On this task, quantum models matched classical ones at best, at a higher cost.

### Speaker notes

"This is the most important slide. Against a classical model on the same input, the quantum model never wins by a statistically reliable margin. The closest is the patch FRQI, 4 points ahead, but that could be chance (p = 0.06). We don't claim a quantum advantage, and we can show why."

## Slide 30: What did we actually learn?

*Section E · Experiments and results*

### On the slide

- **Worked**: patch-ensemble comparison (+27 pp) · fair protocol · FRQI for texture, NEQR for read-out
- **Didn't**: trained VQC · PQK · more entanglement · many qubits per pixel (8-bit NEQR)
- **Surprised us**: no-training VQC beat trained VQC · more NEQR bits = worse
- **Uncertain**: behaviour with real noise and finite swap-test shots

**Explain:** A lower-scoring quantum model is still a result. It tells future work where *not* to look, and the matched controls show *why* the scores are what they are. Many published demos skip the matched classical control. Including it is a contribution of this project.

### Visual

A 2×2 grid (worked / didn't / surprising / uncertain).

### Key takeaway

The main lesson is about **how to compare images and how to evaluate fairly**.

### Speaker notes

"Our biggest learning isn't a number. How you compare images matters more than which quantum encoding you choose. And every quantum result needs a classical model with the same input next to it."

## Slide 31: Limitations and practical challenges

*Section F · Limitations and conclusion*

### On the slide

- Noiseless CPU simulation only; no quantum hardware
- Max 8 qubits per register (16 for whole-image NEQR); deep circuits (thousands of CX)
- FRQI read-out needs many shots; swap test not yet run with shots
- PCA throws information away before the quantum step
- One dataset; the test set was reused across V2–V4

### Concepts to explain

- Simulation gives an **upper bound**: hardware noise would only lower accuracy.
- 3,584 CX gates per FRQI patch is far beyond what today's noisy devices run reliably.
- Hybrid and QKC results depend on classical preprocessing (CNN, texture, PCA).
- C = 1000 lies at the edge of the V4 grid; a larger C was not tried.
- NEQR's seed-1 failure shows sensitivity to brightness shift when there is no contrast stretch.

### Visual

Icon list, or `PACK/Fig10_circuit_resources.png` again.

### Key takeaway

The results show the method's potential under ideal conditions, not proven performance on today's hardware.

### Speaker notes

"Everything ran in perfect simulation on a laptop. Real quantum hardware is noisy, and our circuits are deep, so real-device accuracy would be lower."

## Slide 32: Future scope

*Section F · Limitations and conclusion*

### On the slide

- Run the 15-qubit swap test with finite shots and noise models
- Test on a fresh steel dataset never used for decisions
- Try encoders that are hard to simulate classically
- Small real-hardware trial on selected image pairs
- Platform: multi-user deployment, run experiments from the browser

**Explain:** Each item tests a specific open question:
- How many shots does the 87.8 % need?
- Does the result hold on data that was never used for decisions?
- Is there any regime where the quantum version is not classically easy?

No improvement is promised.

### Visual

Roadmap arrow with 4–5 milestones.

### Key takeaway

Next steps are about realism and fresh evidence, not bigger claims.

### Speaker notes

"The next steps are about making the experiment more realistic: finite measurements, noise, real hardware, and a dataset we've never touched."

## Slide 33: The Q-ImageLab platform (optional / live demo)

*Section F · Limitations and conclusion*

### On the slide

- FastAPI (Python) + React 19 web app, reading only saved results
- Live replay of the frozen V4 model on real images
- Upload your own image → FRQI/NEQR encode, reconstruct, classify
- Learning tools: circuit highlighting, 3×3 sandbox, CNN studio, 27-question quiz
- 201 back-end + 48 front-end tests; live replay reproduces all 360 saved predictions

### Visual

2×2 screenshot grid:

- `SHOT/P01_overview.png`
- `SHOT/P17_how_it_works_mixed_state.png`
- `SHOT/P14_upload_frqi.png`
- `SHOT/P11_playground_sandbox.png`

### Key takeaway

Every number in this talk can be inspected and replayed.

### Speaker notes

"Everything I showed is in our platform. You can open any model, replay it on a test image, or upload your own picture and watch it being encoded."

## Slide 34: Final conclusion

*Section F · Limitations and conclusion*

### On the slide

- **Problem**: classify 6 steel defect types (NEU-DET)
- **Built**: FRQI/NEQR encoders, QKC, PQK, VQC, hybrids, and a new patch-ensemble kernel, all against matched classical models
- **Found**: patching lifts quantum image kernels from about 60 % to 88 %, but classical models on the same input match them
- **Lesson**: *how* images are compared matters more than *which* quantum encoding is used

### Visual

One summary figure: `PACK/Fig04_frqi_neqr_across_protocols.png` with the classical 83.6 % line added, or `RPT/M4_all_models.png`.

### Key takeaway

A careful, honest answer: quantum image encodings can work well, but on this task they gave no advantage over classical methods.

### Speaker notes

"To sum up: quantum image encodings can classify real steel defects well, up to 88 %, once images are compared patch by patch. But a classical model with the same patches does just as well, and the best classical model reaches 96 %. Our contribution is the method, the fair benchmark, and an honest answer."

## Backup: questions the audience may ask

**Why did you use quantum computing at all?**
To test, not assume, whether quantum states give a useful way to compare images. Quantum machine learning claims a rich feature space; FRQI and NEQR had never been properly tested on real textured images.

**Why not use only classical machine learning?**
For the factory task, classical is the right choice: 96.4 % and fast. The project's question is scientific: can quantum representations compete? Answering it needs both.

**What is the actual difference between QKC and VQC?**
QKC has no trainable quantum parts. A fixed circuit produces similarity scores and a classical SVM learns from them. VQC has trainable angles inside the circuit, optimised with gradients (parameter-shift + Adam). QKC trains in seconds; VQC took about 1,060 s per run and scored lower.

**Why is PCA required?**
One feature needs one qubit, and exact simulation stays practical only up to about 8–12 qubits. PCA compresses 4,096 pixels or 576 CNN numbers to 4–12 while keeping the most varied directions. It is fitted on training data only.

**What does entanglement contribute?**
It makes the kernel harder for a classical computer to compute. In our data it didn't improve accuracy: on 12 texture features Product-RY (no entanglement) got 95.3 % and ZZ-Linear 60.6 %. Too much entanglement made almost all kernel values near 0 (kernel concentration).

**Why did some quantum approaches perform poorly?**
- Whole-image kernels compare pixels at fixed positions, so they miss shifted textures.
- PQK discards correlations between qubits.
- VQC suffers from tiny gradients; its encoding-only version did better.
- FRQI with finite shots loses information (57.8 → 33.5 % at 100 shots).

**Did quantum provide any advantage?**
No measurable advantage. The patch FRQI is +4.2 pp over the same-input classical control, but p = 0.060 after Holm correction. The only consistent quantum win is ZZ-Full on 8 pixel-PCA angle features (64.0 vs 60.7 %, significant in 2 of 3 seeds), and an RBF-SVM with normal feature scaling reaches 64.8 %. Every other matched pair is a tie or favours classical.

**Why is a classical SVM used in QKC?**
The quantum circuit's job is only to compute similarities. Finding the best separating boundary from a similarity matrix is a well-solved classical optimisation. This is the standard quantum-kernel design (Havlíček et al. 2019).

**Can this approach run on real quantum hardware?**
In principle, yes. The swap test needs 15 qubits for FRQI patches. In practice, one FRQI 8×8 patch needs 8,339 basic gates (3,584 CX), which is too deep for today's noisy devices. That's why hardware is future work. Nothing in this project ran on hardware.

**What would you improve next?**
- Finite-shot and noisy swap-test estimates
- A fresh test dataset
- Shallower encoders
- A larger C grid for V4
- Contrast stretch for the NEQR model

**Is 87.8 % trustworthy?**
Within V4, yes. The model was selected on validation only, frozen with SHA-256 and tested once, with 3 seeds (86.7, 87.2, 89.4 %). The caveat is that the same test set was seen in V2 and V3, which informed the decision to try patches.

**Why is NEQR's ±10.1 so large?**
On seed 1 it misclassified every rolled-in-scale test image (71.1 %). That class is darker in the test folder, and the selected NEQR model has no contrast stretch. It was not re-tuned after the test, because that would have used the test set for model choice.

**Your README says SVM 76.6 % and Random Forest 70.6 %. Which is right?**
Those are V0 prototype numbers with random splits and no locked test set. They were superseded and are not comparable. The protocol baselines are on slide 23.

---

## Slide-design notes

- Colour code throughout: **blue = classical step, orange = quantum step, green = frozen CNN**. This matches every project figure.
- Put at most one table *or* one figure per slide. Move the detailed tables (slides 21, 24, 25) into backup slides if time is short.
- A 15-minute talk: present slides 1–4, 6, 8–11, 13, 14, 19, 20, 27, 29, 30, 34 and keep the rest as backup.
- Always state the protocol (V2/V3/V4) next to a number. Most apparent "contradictions" between figures are different protocols.
