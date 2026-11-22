# Technical Viva Questions (150) — with answers grounded in the repository

Format per question: **S** = simple answer · **T** = technical answer · **E** = example from our project ·
**F** = likely follow-up → answer.

---

## Level 1 — Absolute basics (Q1–30)

**Q1. What problem does the project solve?**
S: Recognising which of six defects a steel-surface photo shows, using quantum image encodings, and checking honestly whether quantum helps.
T: Six-class image classification on NEU-DET with FRQI/NEQR encodings and quantum kernels, under a leakage-controlled protocol with matched classical controls.
E: V4 FRQI kernel 87.8 % vs same-patch classical 83.6 %.
F: Is it detection or classification? → Classification of whole images; NEU-DET boxes are not used.

**Q2. What is NEU-DET?**
S: A public set of 1,800 grey steel images, 300 per defect class.
T: 200×200 images (stored RGB, grey content), train folder 1,440 / validation folder 360; annotations (boxes) ignored.
E: `src/v2/dataset.py` builds a SHA-256 manifest of all 1,800 files.
F: Why this dataset? → Real industrial task, balanced, small enough for exact simulation, widely used.

**Q3. Name the six classes.**
S: crazing, inclusion, patches, pitted surface, rolled-in scale, scratches.
T: Each is a texture-type defect; position varies between images.
E: class-average images are nearly flat (report Fig 3.5).
F: Which is hardest? → Rolled-in scale across all models; patches easiest.

**Q4. What is image classification?**
S: Giving one label to a whole image.
T: Learn f: image → {1..6} from labelled examples, evaluated on unseen images.
E: Our SVMs output one of six classes per image.
F: Difference from segmentation? → Segmentation labels pixels; we do not.

**Q5. What is machine learning?**
S: Learning rules from examples instead of writing them.
T: Fit model parameters to minimise a loss on training data, check generalisation on held-out data.
E: RBF-SVM fitted on 1,080 training images per seed.
F: Supervised or unsupervised? → Supervised (labels known).

**Q6. What is deep learning?**
S: Machine learning with many-layer neural networks.
T: Hierarchical feature learning by backpropagation.
E: SmallCNN (4 conv blocks) and MobileNetV3.
F: Did we train MobileNetV3? → No, frozen pretrained features.

**Q7. What is a qubit?**
S: A quantum bit that can be in a combination of 0 and 1.
T: Unit vector α|0⟩+β|1⟩ in ℂ², |α|²+|β|²=1.
E: FRQI's colour qubit holds cos θ|0⟩ + sin θ|1⟩.
F: How many numbers describe n qubits? → 2ⁿ complex amplitudes.

**Q8. What is superposition?**
S: A qubit state that is a mix of 0 and 1 at once (as one state).
T: Non-zero amplitudes on several basis states.
E: H on all FRQI position qubits creates a superposition over all pixel positions.
F: Is superposition the same as randomness? → No; randomness is a mixed state.

**Q9. What is entanglement?**
S: Qubits whose values are linked so they cannot be described separately.
T: A state not expressible as a tensor product.
E: FRQI: colour depends on position; ZZ feature maps use CNOTs.
F: Does product-RY entangle? → No.

**Q10. What is measurement?**
S: Reading a qubit, which gives 0 or 1 randomly according to the state.
T: Born rule: P(x) = |⟨x|ψ⟩|²; state collapses.
E: Reconstruction study measures all qubits 100–100,000 times.
F: Why many shots? → To estimate probabilities.

**Q11. What is a quantum circuit?**
S: A recipe of quantum gates applied to qubits.
T: Sequence of unitaries on registers followed by measurements.
E: `FRQIEncoder.build_circuit()`.
F: Read direction? → Left to right.

**Q12. What is a quantum simulator?**
S: A normal computer program that calculates what a quantum computer would do.
T: Statevector simulation (exact amplitudes) or sampling.
E: Qiskit Aer + our NumPy `qsim.py`.
F: Limits? → Memory 2ⁿ; fine for our ≤ 16 qubits.

**Q13. Did you use a real quantum computer?**
S: No.
T: Exact noiseless CPU simulation only.
E: Every page and the paper say "simulated".
F: Why? → Hardware noise would destroy circuits of thousands of gates; simulation lets us study the method itself.

**Q14. What is FRQI?**
S: A way to store an image in qubits: position qubits + one colour qubit with an angle per pixel.
T: |I⟩ = N^-½ Σ (cos θᵢ|0⟩ + sin θᵢ|1⟩)|i⟩.
E: 8×8 image → 7 qubits.
F: Who proposed it? → Le, Dong, Hirota 2011.

**Q15. What is NEQR?**
S: Stores each grey value as binary digits in several qubits.
T: |I⟩ = N^-½ Σ |cᵢ⟩|i⟩, q-bit codes.
E: 16×16, 4-bit → 12 qubits.
F: Who? → Zhang, Lu, Gao, Wang 2013.

**Q16. What is a kernel?**
S: A similarity score between two items.
T: K(x,y) = ⟨φ(x), φ(y)⟩ in some feature space; must be positive semi-definite for SVMs.
E: RBF kernel; quantum fidelity kernel; Tr(ρAρB).
F: Why PSD? → So the SVM optimisation is convex.

**Q17. What is an SVM?**
S: A classifier that draws the widest-margin boundary between classes.
T: Dual optimisation over support vectors; kernel trick for non-linear boundaries.
E: `SVC(kernel="precomputed")` for all quantum kernels.
F: Multi-class how? → One-vs-one (15 binary SVMs).

**Q18. What is accuracy?**
S: Fraction of correct predictions.
T: (TP+TN)/N; multi-class: correct/total.
E: 316/360 ≈ 87.8 % for FRQI on average.
F: When misleading? → Imbalanced data — not our case.

**Q19. What is a training/validation/test split?**
S: Learn on training, choose settings on validation, report on test.
T: Validation guides selection; test only for the final unbiased estimate.
E: 1,080 / 360 / 360.
F: Why not choose on test? → It leaks information and inflates results.

**Q20. What is the locked test set?**
S: Test images nobody looks at until the model is frozen.
T: The 360 validation-folder images, read once per frozen model; access logged.
E: `final_evaluation_stage` + 17 verification checks.
F: Was it ever reused? → Yes across V2/V3/V4 — a disclosed limitation.

**Q21. What is preprocessing?**
S: Preparing images before the model: grey, resize, scale.
T: PIL convert('L') → bilinear resize → /255; optional per-image stretch.
E: `preprocess_image()` in `src/v2/dataset.py`.
F: Why scale to [0,1]? → FRQI angles need intensities in [0,1].

**Q22. What is PCA?**
S: Compresses many numbers into a few that keep most variation.
T: Projects onto top eigenvectors of the training covariance.
E: Pixels 64×64 → PCA 4/6/8 (V2); texture 76-d → 8/12 (V3).
F: Fitted on? → Training split only.

**Q23. What is a CNN?**
S: A network that slides small filters over an image to find patterns.
T: Convolutions + nonlinearity + pooling; weight sharing.
E: SmallCNN 16-32-64-128 channels.
F: Accuracy? → 93.0 ± 5.9 %.

**Q24. What is MobileNetV3?**
S: A small, fast pretrained CNN made for phones.
T: Depthwise separable convs, inverted residuals, SE, hard-swish, NAS-designed.
E: `mobilenet_v3_small`, IMAGENET1K_V1, 576-d features.
F: Result? → 96.4 % with logistic regression.

**Q25. What is a hybrid quantum-classical model?**
S: Classical part extracts features, quantum part classifies (or the reverse).
T: Here: CNN → PCA → angle encoding → quantum kernel → classical SVM.
E: E5-mnv3pca8-qkc-product_ry 93.2 %.
F: Which part does the heavy lifting? → The CNN features.

**Q26. What is a dashboard?**
S: A web app that shows the results.
T: React SPA reading a FastAPI REST API.
E: Home page "All versions · V4 latest".
F: Does it train models? → No, read-only (except the live recomputation of the frozen model).

**Q27. What are measurement shots?**
S: How many times the circuit is run and measured.
T: Finite samples of the output distribution; error ~1/√shots.
E: 100–100,000 in reconstruction.
F: Effect at low shots? → Noisy images; NEQR shows black pixels.

**Q28. What is reconstruction?**
S: Getting the picture back from the quantum state.
T: FRQI arcsin√P per position; NEQR majority code.
E: All 1,800 images × 20 methods.
F: Exact? → From the statevector yes (FRQI), up to quantisation (NEQR).

**Q29. What is quantum advantage?**
S: Doing something better/faster than any classical method.
T: Requires a fair comparison against the best classical approach on the same task, ideally with complexity arguments.
E: We do not claim it.
F: Why not? → Classical controls match or beat our quantum models.

**Q30. What is the main result in one sentence?**
S: Patches lifted FRQI from 61 % to 88 %, but a classical model on the same patches is just as good.
T: +27.1 pp (p < 0.001) vs whole-image FRQI; +4.2 pp vs same-patch classical (p = 0.060, n.s.).
E: Table V of the paper.
F: Best overall? → MobileNetV3 96.4 %.

---

## Level 2 — Intermediate (Q31–60)

**Q31. How are images loaded and labelled?**
S: From the NEU-DET folders; the folder name is the label.
T: Manifest records rel_path, class, folder, index, block, SHA-256.
E: `build_manifest()`.
F: What if a file changes? → Hash check fails, stages stop.

**Q32. How are train/validation splits made?**
S: Groups of 20 neighbouring images go together into train or validation.
T: block = (index−1)//20; 3 random validation blocks per class per seed.
E: `make_split(manifest, seed)`.
F: Why blocks? → Neighbouring indices are visually correlated; random splitting would leak near-duplicates.

**Q33. Why three seeds?**
S: To see how much results change with a different split.
T: Mean ± s.d. over seeds 0,1,2; paired tests average per-image correctness over seeds.
E: NEQR seeds 87.5 / 71.1 / 89.4.
F: Enough? → Minimum; more seeds would tighten estimates.

**Q34. What leakage did you prevent?**
S: Information from test or validation sneaking into training or model choice.
T: Train-only fitting of scalers/PCA; validation-only selection; hash-frozen selections; one test access.
E: Check "no selection file contains a test metric".
F: Any remaining leakage? → Protocol-level reuse of the test set.

**Q35. What is the "angle" view of features?**
S: Features scaled to [0, π] so they can be rotation angles.
T: Train-fitted MinMaxScaler to [0, π]; test values not clipped.
E: `PCAFeaturizer.transform(view="angle")`.
F: V3 change? → CDF view π·Φ(z), robust to outliers.

**Q36. What is the bandwidth in the QKC?**
S: A multiplier that controls how sharp the similarity is.
T: x = b·a before encoding; b ∈ {0.05,0.1,0.2,0.5,1}.
E: `QuantumKernelSVC._scale`.
F: Too large? → Kernel → identity, overfits.

**Q37. Explain the product-RY feature map.**
S: Each feature rotates its own qubit; nothing else.
T: K = Πᵢ cos²((xᵢ−yᵢ)/2), closed form.
E: Best map in E5 and V3.
F: Why include it? → Classical-equivalent control.

**Q38. Explain the ZZ feature map.**
S: Rotations plus pairwise entangling terms.
T: H; P(2xᵢ); for pairs CX·P(2(π−xᵢ)(π−xⱼ))·CX; reps times.
E: zz_linear (neighbour pairs), zz_full (all pairs).
F: Did it beat product-RY? → No, not consistently.

**Q39. How is a kernel matrix built?**
S: Compute similarity for every pair of training images.
T: K_train (1,080×1,080) and K_test (360×1,080) from statevectors / density matrices.
E: V4: K = R Rᵀ with R = flattened ρ.
F: Memory? → ~1 M entries, fine.

**Q40. How does the SVM use a precomputed kernel?**
S: It only needs the similarity table, not the features.
T: `SVC(kernel="precomputed").fit(K_train, y)`, `predict(K_test)`.
E: `MixedStateEncodingKernelSVC.fit`.
F: Why SVM and not k-NN on the kernel? → Margin-based, convex, standard for quantum kernels.

**Q41. What is a VQC?**
S: A quantum circuit with adjustable angles trained like a neural network.
T: Encoding + parameterised layers + measured expectations + classical loss.
E: RY encoding, L×(RY,RZ)+CNOT ring, 6 ⟨Z⟩ readouts.
F: Number of parameters? → 2·k·L (48 for k=8, L=3).

**Q42. How is the VQC trained?**
S: Adjust angles to reduce prediction error.
T: Softmax cross-entropy; parameter-shift gradients; Adam lr 0.05, or COBYLA, SPSA; early stopping on validation.
E: `VQC.fit`.
F: Best V2 VQC? → 48.1 % (PCA-8, L=3, re-upload).

**Q43. What is data re-uploading?**
S: Feeding the input again before each layer.
T: Repeats RY(aᵢ) encoding at each layer, increasing expressivity.
E: `reupload=True` selected for k=6,8.
F: Effect? → Small gain.

**Q44. What does the frozen-circuit ablation show?**
S: Whether training the quantum part matters.
T: Random untrained circuit + trained head: 16–29 % vs 34–48 % trained.
E: E4-…-ablation-frozen.
F: V3 encoding-only control? → 92.6 % — linear head on cos(aᵢ) beats trained VQC.

**Q45. What is the projected quantum kernel?**
S: Compares small pieces (single-qubit summaries) of two states instead of the whole state.
T: Bloch vectors per qubit; K = exp(−(γ/2)Σ‖b_q(x)−b_q(y)‖²).
E: V3 `ProjectedQuantumKernelSVC`.
F: Why? → Avoids kernel concentration of global overlaps.

**Q46. What features did V3 add?**
S: Texture descriptors.
T: LBP uniform (8,1),(16,2),(24,3) → 54; GLCM 32 levels, d=1,2,4, 4 angles, 6 props → 18; std, Sobel mean/std, Laplacian var → 4; total 76.
E: `texture_features()`.
F: Why exclude mean brightness? → Illumination nuisance.

**Q47. What is the V4 idea?**
S: Compare all small patches of two images instead of whole images pixel by pixel.
T: ρ = mean of patch density matrices; K = Tr(ρAρB).
E: FRQI 8×8 patches: 87.8 %.
F: Why density matrices? → Order-free mixture; swap-test measurable.

**Q48. How many patches does the frozen FRQI model use?**
S: 225.
T: S = 64, p = 8, s = 4 → ((64−8)/4+1)² = 15² = 225.
E: `patches()`.
F: NEQR? → 1,024 (128 px, p 4, s 4).

**Q49. Why contrast stretch?**
S: Makes dark and bright images comparable.
T: Per-image min–max to [0,1]; no cross-image statistics.
E: +8.9 pp validation macro-F1 for FRQI.
F: Why did NEQR not use it? → Its best validation mean was without stretch (but more variance).

**Q50. What is the angle scale b?**
S: Multiplies the rotation angles to spread grey values.
T: θ = (π/2)·b·x; b ∈ {1,2,4}; b=4 selected.
E: b=1 → 75.8 % vs b=4 88.0 % (validation).
F: Is b>1 invertible? → Not by arcsin; used only for kernels.

**Q51. What is the classical control in V4?**
S: Same patches, no quantum encoding.
T: mean patch vector + mean outer product of raw patch intensities → standardised → RBF-SVM.
E: 83.6 ± 0.3 %.
F: Why "outer product"? → It is ρ without the quantum feature map.

**Q52. What statistics did you use?**
S: Tests that check whether differences are real or luck.
T: Paired sign-flip permutation (10,000), bootstrap 95 % CI, McNemar per seed, Holm over 8 tests.
E: `analyze_v4.py`.
F: Why paired? → Same test images for both models.

**Q53. What is Holm correction?**
S: Makes significance stricter when testing many comparisons.
T: Sort p-values; compare the i-th smallest with α/(m−i+1); step-down.
E: 8 pre-declared V4 comparisons.
F: Why pre-declare? → Prevents cherry-picking.

**Q54. What is macro-F1 and why use it for selection?**
S: Average F1 over classes.
T: Treats all classes equally; sensitive to a failing class.
E: Selection criterion for every group.
F: Why accuracy as headline? → Balanced test set; easier to read.

**Q55. What does SHA-256 freezing do?**
S: Locks the chosen settings so they cannot be changed after seeing test results.
T: Hash of selection files stored; test stage aborts if changed.
E: Freeze hash b1735fdc… (V4).
F: Can it stop protocol-level adaptation? → No.

**Q56. What is MSE / PSNR / SSIM?**
S: Error, signal-to-noise, structural similarity.
T: MSE = mean squared difference; PSNR = 10 log₁₀(1/MSE); SSIM via luminance/contrast/structure.
E: FRQI 8×8 1,000 shots MSE 8.7e-3.
F: Why SSIM too? → MSE ignores structure (blur vs speckle).

**Q57. How is FRQI decoded from shots?**
S: For each pixel, count how often the colour qubit was 1.
T: θ̂ = arcsin√P̂(1|i); x̂ = θ̂/(π/2).
E: `FRQIReconstructor.reconstruct_from_counts`.
F: Error source? → Few shots per position.

**Q58. How is NEQR decoded from shots?**
S: Take the most frequent code at each pixel.
T: Majority vote per position.
E: `NEQRReconstructor`.
F: Unobserved pixels? → Decoded as 0 (black).

**Q59. What does the dashboard home show?**
S: All versions with V4 big.
T: `/api/v4/versions` built from saved aggregates.
E: AllVersions.tsx.
F: Hard-coded? → No; tests verify.

**Q60. What does "How it works" do?**
S: Replays the final model on a real test image step by step.
T: `/api/v4/pipeline` recomputes ρ, kernel row, SVM decision and checks it against the saved prediction.
E: Nine steps, Play/Pause/Next.
F: Is the swap test real there? → Schematic; values computed exactly.

---

## Level 3 — Advanced technical (Q61–95)

**Q61. Derive the FRQI overlap of two images.**
S: Compare angles pixel by pixel.
T: ⟨IA|IB⟩ = (1/N) Σᵢ (cos θᵢᴬ cos θᵢᴮ + sin θᵢᴬ sin θᵢᴮ) = (1/N) Σᵢ cos(θᵢᴬ−θᵢᴮ).
E: `frqi_kernel` squares it.
F: Why squared? → Fidelity kernel |⟨·|·⟩|²; V3 also tried the unsquared overlap.

**Q62. Derive the NEQR overlap.**
S: Count equal codes.
T: ⟨IA|IB⟩ = (1/N) Σᵢ δ(cᵢᴬ, cᵢᴮ).
E: `neqr_kernel`.
F: Why does 8-bit hurt? → Exact equality of 8-bit codes is rare → near-identity kernel.

**Q63. Show Tr(ρAρB) equals the mean squared patch overlap.**
S: Expand both mixtures.
T: Tr[(1/PA Σₖ|a_k⟩⟨a_k|)(1/PB Σₗ|b_l⟩⟨b_l|)] = (1/PAPB) Σₖₗ ⟨a_k|b_l⟩⟨b_l|a_k⟩ = (1/PAPB) Σ |⟨a_k|b_l⟩|².
E: Docstring of `MixedStateEncodingKernelSVC`.
F: Is it PSD? → Yes, Hilbert–Schmidt inner product.

**Q64. Why is the patch kernel shift-tolerant?**
S: Moving content just reorders patches.
T: Uniform mixture is permutation-invariant; only border patches change for shifts by multiples of the stride.
E: Unit test: normalised kernel > 0.999 after a cyclic shift.
F: Rotation-invariant? → No.

**Q65. Complexity of computing the V4 kernel.**
S: Using ρ is much cheaper than all patch pairs.
T: Pairs: O(P²D) per image pair; ρ: O(PD²) per image + O(D²) per entry; P²=50,625 ≫ D=128.
E: `einsum("npi,npj->nij")`.
F: Memory of ρ? → 128×128 floats per image.

**Q66. Swap test probability.**
S: Probability of 0 encodes the overlap.
T: P(0) = ½(1 + Tr(ρσ)); Tr estimate 2p̂−1, s.e. ≤ 1/√M.
E: Paper Eq. (3).
F: Shots needed for 0.01 precision? → ~10⁴ per entry.

**Q67. Why is the swap-test estimate unbiased with random patches?**
S: On average it gives the right value.
T: E over uniform k,l of |⟨a_k|b_l⟩|² = Tr(ρAρB); swap test on random pair is unbiased for it.
E: Paper "Estimation on hardware".
F: Was it simulated? → No.

**Q68. How many qubits for the swap test of FRQI patches?**
S: 15.
T: 2 × 7 + 1 ancilla.
E: 8×8 patch → 7 qubits.
F: NEQR 4×4 4-bit? → 2×8+1 = 17.

**Q69. Why does FRQI shot error grow with resolution?**
S: Shots are shared among more pixels.
T: Each position gets ~M/N samples; variance of P̂ ~ P(1−P)N/M.
E: 1,000 shots: 8.7e-3 (8×8) vs 6.4e-2 (16×16).
F: Fix? → More shots (100k: 2.6e-4).

**Q70. Gate complexity of FRQI.**
S: One controlled rotation per pixel.
T: N MCRY with n controls; each decomposes into O(n) or more basic gates.
E: 8×8: 8,339 compiled gates.
F: Theoretical better constructions? → Yes (e.g. uniformly-controlled rotations), not used here.

**Q71. Why is NEQR gate count data-dependent?**
S: Only 1-bits need gates.
T: MCX per set bit per pixel.
E: 1,998 vs 2,901 for different patches.
F: Worst case? → N·q MCX.

**Q72. Parameter-shift rule.**
S: Exact gradient from two shifted circuit runs.
T: ∂⟨O⟩/∂θ = [⟨O⟩(θ+π/2) − ⟨O⟩(θ−π/2)]/2 for gates generated by Pauli/2.
E: `param_shift_jacobian`.
F: Cost? → 2 circuits per parameter.

**Q73. What is a barren plateau?**
S: Gradients become almost zero, so training stalls.
T: Variance of gradients decays exponentially with qubits/depth for random circuits.
E: VQC records gradient statistics at initialisation.
F: Why kernels avoid it? → No gradient training of the circuit.

**Q74. What is kernel concentration?**
S: All similarity values become nearly the same.
T: Fidelity kernels concentrate exponentially on large registers (Thanasilp et al.).
E: Motivation for small patch registers and PQK.
F: Sign in data? → Near-identity or near-constant kernel matrices (diagnostics recorded).

**Q75. Why MinMax angles can be problematic.**
S: Outliers squeeze other values.
T: A single extreme training value compresses the range; V3 CDF π·Φ(z) is robust.
E: Views "angle" vs "cdf".
F: Clipping test values? → Not done (would be data-dependent).

**Q76. Bias–variance in NEQR selection.**
S: Best mean but unstable.
T: No-stretch NEQR val 89.2 ± 7.2 vs stretch 86.8 ± 2.3; test confirmed instability.
E: Seed 1 rolled-in scale all wrong.
F: Should you switch to stretch now? → No — that would use the test set for selection.

**Q77. Explain the rolled-in-scale failure.**
S: Test images of that class are darker.
T: Mean intensity 0.496 (train) vs 0.329 (test); without per-image stretch NEQR codes shift levels.
E: EDA Table 3.3; NEQR 118/180 vs FRQI 178/180 correct.
F: Why FRQI fine? → Stretch normalises brightness.

**Q78. Why one-vs-one SVM?**
S: sklearn's SVC default.
T: 15 binary classifiers, voting; decision_function shown as ovr shape.
E: `/pipeline` returns ovr-shaped scores.
F: Effect on results? → None for predictions.

**Q79. Why C = 1000?**
S: Selected on validation.
T: Weak regularisation fits the kernel more closely; C=1 gives 53.8 %.
E: Ablation table.
F: Edge of grid? → Yes, a limitation.

**Q80. Paired permutation test details.**
S: Randomly swap which model got each image's score many times.
T: d = per-image correctness difference (seed-averaged); random sign flips 10,000×; p = fraction with |mean| ≥ observed.
E: `analyze_v4.py`.
F: Why not t-test? → Fewer assumptions.

**Q81. McNemar's test.**
S: Counts images one model gets right and the other wrong.
T: Uses discordant pairs (a-only : b-only) per seed.
E: FRQI vs V2 seed 0: 114:25.
F: Why per seed? → Each seed is a separate pair of classifiers.

**Q82. Bootstrap CI.**
S: Resample test images to see the spread of the difference.
T: 10,000 resamples of per-image differences; 2.5–97.5 percentiles.
E: FRQI vs V2: [+21.7, +32.7] pp.
F: CI crossing 0? → Not significant (e.g. NEQR vs control).

**Q83. Why did FRQI vs control CI exclude 0 but p = 0.060?**
S: Different tests and the Holm correction.
T: Uncorrected bootstrap CI [+0.5,+7.7]; Holm-adjusted permutation p = 0.060.
E: Table VI.
F: Conclusion? → Not significant under the pre-declared rule.

**Q84. Shot model in V2 kernels.**
S: Add realistic sampling noise to each kernel entry.
T: K̂ᵢⱼ ~ Binomial(shots, Kᵢⱼ)/shots — exact for ideal compute–uncompute.
E: `sample_shot_kernel`.
F: Validated? → Entries cross-checked on Aer.

**Q85. Why simulate with NumPy instead of Aer for kernels?**
S: Much faster for thousands of states.
T: Batched statevector over the whole data set; gates mirror Qiskit; tests 1e-10.
E: `src/v2/qsim.py`.
F: Risk? → Mitigated by tests and Recorder-based resource counts.

**Q86. Transpilation basis and why.**
S: Convert to a standard gate set to count fairly.
T: {cx, rz, sx, x}, optimisation level 1, all-to-all.
E: `circuit_resources`.
F: With real topology? → More CX (SWAPs).

**Q87. Why is MobileNetV3 so strong here?**
S: Its pretrained filters capture textures well.
T: Generic ImageNet features transfer to texture classes; 576-d rich representation.
E: 96.4 %.
F: Fine-tuning? → Not done; could improve further.

**Q88. Why does PCA of pixels perform poorly?**
S: It keeps brightness patterns, not textures.
T: Leading components capture global intensity gradients; PCA-8 SSIM 0.59.
E: Fig 5.14 PCA columns are blurry.
F: Better? → Texture or CNN features.

**Q89. LBP explained.**
S: Encodes each pixel by comparing it with neighbours.
T: P neighbours at radius R → binary code; "uniform" patterns; histogram.
E: (8,1),(16,2),(24,3).
F: Rotation invariant? → Uniform LBP can be.

**Q90. GLCM explained.**
S: Counts how often grey levels co-occur at a distance.
T: Co-occurrence matrix → contrast, dissimilarity, homogeneity, energy, correlation, ASM.
E: 32 levels, d=1,2,4, 4 angles averaged.
F: Why stretch first? → Comparable level usage.

**Q91. CDF angle mapping.**
S: Turns standardised values into angles smoothly.
T: angle = π·Φ(z), Φ = normal CDF.
E: Suffix "c" in V3 groups.
F: Benefit? → No clipping, outlier-robust.

**Q92. Purity on the kernel diagonal.**
S: Self-similarity of a mixed state.
T: K(A,A) = Tr(ρA²) ≤ 1; lower for diverse textures.
E: `purity_mean` diagnostic.
F: Normalised kernel? → K/√(K_AA K_BB) for display only.

**Q93. Why not concatenate patch states?**
S: That would fix positions again.
T: Tensor product of patches = huge register and position-dependent.
E: Design choice in methodology.
F: Mixture loses? → Spatial layout (inclusion vs pitted confusions).

**Q94. What does the confusion matrix tell us about FRQI?**
S: Which classes get mixed.
T: Inclusion→pitted 38/180, scratches→rolled-in 40/180.
E: Fig 7 / 5.6.
F: Why? → Local patches look alike without layout.

**Q95. How was image difficulty measured?**
S: How many of all models got each image right.
T: 163 models × 3 seeds; median image 67 %; none always right or always wrong.
E: `/api/v4/images`, Fig 11.
F: Mislabelled images? → No evidence (errors spread out).

---

## Level 4 — Project-specific (Q96–125)

**Q96. Where is the FRQI circuit built?** S: `src/frqi/encoder.py`. T: H, X-sandwich, `mcry(angle)` per pixel, skip black. E: 2×2 → 3 qubits. F: Angle passed? → xᵢπ (=2θ).

**Q97. Where are FRQI/NEQR kernels for V2?** S: `src/v2/frqi_neqr.py`. T: Closed forms verified vs encoder statevectors (`tests/test_v2_frqi_neqr.py`). E: E1/E2 groups. F: Why closed form? → Speed; identical results.

**Q98. Which file runs selection and testing?** S: `src/v2/runner.py`. T: `run_candidate`, `select`, `final_test` inside `final_evaluation_stage`. E: Used by V2–V4. F: Retrain before test? → No; saved estimator applied.

**Q99. Where is V4 implemented?** S: `src/v4/models.py`. T: `mixed_states`, `MixedStateEncodingKernelSVC`, `PatchMomentRBF`. E: 864 runs via `scripts/v4/run_v4.py`. F: Grid size? → 288 configs.

**Q100. How many V2 models and runs?** S: 88 selected, 2,583 runs. T: 0 failed. E: `/api/v2/summary`. F: Families? → classical, CNN, QKC, VQC, hybrid, FRQI/NEQR.

**Q101. Best V2 pure quantum model?** S: QKC ZZ-full on pixel PCA-8. T: 64.0 ± 3.5 %. E: E3-pca8-qkc-zz_full. F: Classical equivalent? → RBF-SVM PCA-8 64.8 %.

**Q102. Best V2 hybrid?** S: CNN PCA-8 + product-RY QKC. T: 93.2 ± 1.1 % vs RBF-SVM same features 93.0. E: E5. F: Quantum gain? → None significant.

**Q103. Best V3 quantum?** S: Texture PCA-12 + product-RY QKC 95.3 %. T: product-RY is classically computable. E: V3-tex12c-qkc-product_ry. F: Classical? → 95.6 %.

**Q104. Which V4 groups exist?** S: FRQI p4/p8, NEQR p2/p4, patch-moment control. T: 5 groups. E: v4_results.json. F: Headline rule? → Best validation per encoding, declared before test.

**Q105. Frozen FRQI configuration?** S: 64 px, 8×8 patches, stride 4, b=4, stretch, C=1000. T: 7 qubits, 225 patches. E: V4-frqi-p8. F: Val macro-F1? → 88.0.

**Q106. Frozen NEQR configuration?** S: 128 px, 4×4, stride 4, 4-bit, no stretch, C=1000. T: 8 qubits, 1,024 patches. E: V4-neqr-p4. F: Val? → 89.2.

**Q107. How is the test access logged?** S: Every test evaluation is recorded. T: test_access_log in aggregates; verification: one access per frozen group after freeze. E: verify_v4.py. F: Count? → 5 (one per group).

**Q108. What do the 17 checks cover?** S: Data, results and protocol integrity. T: V0/V2/V3 unchanged, manifests identical, freeze unchanged, single access, predictions only for frozen configs, no test metrics in selection, 864 runs 0 failed, recomputed accuracy, headlines by validation, 8 comparisons, real circuits, control has no circuit. E: v4_verification.json. F: All pass? → 17/17.

**Q109. How were V0 results protected?** S: Write-guards and hashes. T: `assert_writable`, env flags, verify_historical.py; V0 launch endpoints return 409. E: HistoricalHome page. F: Why keep V0? → Evidence of the project's history.

**Q110. What was wrong with V0?** S: Tiny runs and wrong labels. T: ~42 train/12–16 test per run, alphabetical order, no locked test, "VQC" was softmax regression. E: E1/E2-legacy-softmax 24–26 %. F: Lesson? → Protocol first.

**Q111. How are MobileNetV3 features cached?** S: Computed once per image set. T: `FrozenMobileNetV3Source._pool` with hashed caches. E: cnn.py. F: Determinism? → `torch.use_deterministic_algorithms(True)`.

**Q112. What is in an experiment folder?** S: Config, metrics, predictions, model. T: config.json, validation/test metrics, predictions.csv, confusion_matrix.json, circuit_stats.json, model/estimator.joblib. E: results/qml_v4/experiments/V4-frqi-p8__09d3a4f853__s0. F: Test metrics for all? → Only frozen configs.

**Q113. How does `/api/v4/versions` get numbers?** S: Reads saved aggregates. T: V2 analysis.json, V3 v3_results.json, V4 v4_results.json; V0 marked not comparable. E: AllVersions page. F: Tested? → pytest compares with files.

**Q114. How does the Circuits page get diagrams?** S: Rebuilt real circuits. T: build_circuit_artifacts.py from checkpoints → instructions + Qiskit text diagram → SVG. E: 33 configurations. F: Trained VQC params? → Included.

**Q115. What does the Reconstruction (all 1,800) page show?** S: 20 methods' quality and an image browser. T: `/reconstruction/summary` + `/reconstruction/image`. E: shot animation. F: Data source? → reconstructions.npz.

**Q116. How many tests?** S: Many. T: 179 pytest functions, 27 Vitest, Playwright e2e. E: tests/, frontend tests. F: Paper numbers verified? → validate_v4_pack.py 27/27.

**Q117. Where does the paper's every number come from?** S: Scripts reading results. T: make_v4_paper_pack.py writes tables/figures from aggregates. E: research_paper_visuals/. F: Manual edits? → Text yes; numbers checked by validator.

**Q118. Is the upload feature part of V4?** S: No, legacy V0 lab. T: `/api/quantum/compare-custom` encodes uploaded image with FRQI+NEQR, Aer, reconstruct, metrics. E: V0 Encoding Lab. F: Saved? → No.

**Q119. What is the 3×3 playground?** S: A teaching demo on a tiny image. T: Precomputed JSON, `illustrative: true`. E: /playground. F: Real dataset? → No, labelled illustrative.

**Q120. Which page proves "no hard-coding"?** S: Tests do. T: Vitest mocks unusual numbers and asserts display. E: v2.test.tsx. F: Browser check? → e2e compares tile with v4_results.json.

**Q121. How long are ρ matrices for NEQR?** S: 256×256. T: 8 qubits → D=256. E: frozen NEQR. F: Memory per image? → 65,536 floats.

**Q122. Which V4 setting matters most (validation)?** S: C and angle scale. T: C=1 → 53.8 %; b=1 → 75.8 %; stretch off → 79.1 %. E: Ablation table. F: Test-based ablation? → Only for pre-declared frozen groups.

**Q123. Why 64×64 for FRQI?** S: Best validation. T: 32 → 79.1, 64 → 88.0, 128 → 85.4 (val). E: Ablation. F: Reason? → Balance of detail vs patch scale.

**Q124. What does the per-class F1 show?** S: Strengths/weaknesses by class. T: FRQI p8: crazing 93.1, patches 95.8, pitted 81.5, scratches 81.3; NEQR rolled-in 65.0. E: Table 5.7. F: Classical control strong where? → rolled-in 93.0, scratches 95.9.

**Q125. Reconstruction exactness counts.** S: FRQI exact for all images. T: 1,800/1,800 statevector; NEQR exact only at 8 bits. E: Table 5.8. F: PCA? → Not exact; SSIM 0.59.

---

## Level 5 — Examiner challenges (Q126–150)

**Q126. Does the project demonstrate quantum advantage?** S: No. T: Same-patch classical control tied (p=0.060); texture SVM better (p<0.001); kernels classically simulable. E: Table VI. F: Then why do it? → To find what limits quantum image encodings and test claims fairly.

**Q127. What is the novelty?** S: A position-free way to compare FRQI/NEQR images plus a strict evaluation. T: Patch-ensemble mixed-state kernel, matched control, leakage-controlled protocol, full reconstruction study. E: +27 pp over whole-image kernels. F: Is the mixture idea new? → It is natural; the contribution is its controlled evaluation.

**Q128. You reused the test set. Aren't results biased?** S: Possibly a little. T: Protocol-level adaptivity; within V4 single access. E: Disclosed in Discussion. F: Fix? → Fresh data set.

**Q129. Why not tune NEQR after seeing failure?** S: That would cheat. T: Using test for selection invalidates the estimate. E: Kept as is. F: What would you report? → Both, with the change marked post-hoc.

**Q130. Is 3 seeds enough?** S: Minimal. T: Variance estimates are rough; paired per-image tests add power. E: NEQR s.d. 10.1. F: Improve? → More seeds / repeated CV.

**Q131. Could the classical control be weaker on purpose?** S: No, it got the same grid treatment. T: 72 configs, validation selection, same patches, stretch option. E: 83.6 ± 0.3. F: Stronger control? → Texture SVM 95.6 %.

**Q132. Are your kernels really "quantum"?** S: They come from real quantum encodings. T: FRQI/NEQR states; but with closed forms → classically computable. E: verified vs Qiskit statevectors. F: When would they not be simulable? → Much larger registers.

**Q133. Isn't product-RY just a classical kernel?** S: Yes. T: Πcos² closed form; used as control. E: best in E5/V3. F: Implication? → Entanglement did not help here.

**Q134. Gate counts are huge — is this practical?** S: Not on today's hardware. T: 8,339 gates per patch, 225 patches, plus swap tests. E: Table resources. F: Improvement? → Shallower encoders, approximate state prep.

**Q135. What about noise?** S: Not modelled. T: Would reduce overlap estimates; deep circuits fail. E: Future work. F: How to test? → Aer noise models, shot-based kernels.

**Q136. How do you know the simulator is correct?** S: Tests against Qiskit. T: qsim vs Statevector 1e-10; closed-form kernels vs encoder statevectors; V4 kernel vs Qiskit overlaps. E: tests/test_v2_qsim.py, test_v4_models.py. F: Aer check? → aer_validation.py.

**Q137. Could leakage occur through preprocessing?** S: No. T: Scalers/PCA train-only; stretch per image. E: features.py docstrings. F: CNN pretrained on ImageNet — leakage? → No NEU images in ImageNet.

**Q138. Why is FRQI better than NEQR?** S: Smoother similarity. T: Continuous angles vs exact-match codes; stretch removes brightness shift. E: +5.1 pp. F: Proven cause? → Plausible explanation, not proven.

**Q139. Would results hold on other data?** S: Unknown. T: Texture-type defects likely similar; needs testing. E: Limitation. F: Which data? → Another steel/fabric defect set.

**Q140. Why not other QIRs (e.g. GQIR, MCQI, QPIE)?** S: FRQI and NEQR are the canonical two (angle vs basis). T: Covering both encoding principles; others are variants. E: Yan et al. survey. F: Would amplitude encoding (QPIE) help? → Fewer qubits but same position-locking unless patched.

**Q141. Why not fine-tune MobileNetV3?** S: Frozen was already 96 % and fairer as a fixed feature. T: Fine-tuning adds variance and cost. E: E7. F: Expected gain? → Small.

**Q142. VQC is weak — implementation bug?** S: Unlikely. T: Parameter-shift gradients tested; ablations behave as expected; known optimisation difficulties. E: tests/test_v2_vqc.py. F: Encoding-only control 92.6 % — meaning? → Head does the work.

**Q143. Why are V0 numbers higher in places (e.g. SVM 76.6 %)?** S: Different, easier, leaky split. T: Random 70/30 of train folder, near-duplicates in both sets. E: results/models. F: Why not use them? → Not comparable.

**Q144. What if shots were reduced for V4 classification?** S: Accuracy would drop. T: Each kernel entry gets estimation noise; not simulated for V4. E: V2 FRQI 8×8: 57.8 → 39.3 % at 1,000 shots. F: Estimate needed shots? → Future work.

**Q145. Is SSIM meaningful at 2×2?** S: Barely. T: Window must fit; evaluator shrinks win_size; small images give unstable SSIM. E: metrics evaluator. F: Use MSE then. → Yes.

**Q146. Is accuracy ± s.d. over seeds the right uncertainty?** S: It shows split variability. T: Does not include test-sampling uncertainty — that is why bootstrap/permutation tests were added. E: Both reported. F: Which to trust? → Paired tests for comparisons.

**Q147. Why did V3's re-tuned FRQI get worse (57.5 vs 60.6)?** S: Normal selection noise. T: Same validation (≈69 %), different chosen config; test differs. E: V3-frqi8. F: Contradiction? → No.

**Q148. Could the dashboard mislead users?** S: It labels everything. T: Simulation banners, "not comparable" V0, illustrative playground, numbers from API. E: Home hero note. F: Any live computation? → Only the frozen model replay.

**Q149. Biggest limitation?** S: No hardware and no quantum advantage. T: Classically simulable kernels, one data set, test-set reuse. E: Discussion. F: Most important future step? → Finite-shot + noise kernel study, fresh data.

**Q150. How would you improve the project?** S: Test on hardware/noise and new data. T: Shot-based swap-test kernels with noise, fresh test set, larger/entangling patch encoders, learned patch weighting, fine-tuned CNN baseline. E: Conclusion. F: Which first? → Finite-shot noisy kernels — it tells whether the method is usable at all.
