# Technical Viva Questions (150) — repository par based jawab, Hinglish mein

Har sawaal ka format: **S** = simple jawab · **T** = technical jawab · **E** = humare project ka example ·
**F** = likely follow-up → jawab.

---

## Level 1 — Bilkul basics (Q1–30)

**Q1. Project kaunsi problem solve karta hai?**
S: Steel surface ki photo mein chhe mein se kaunsa defect hai, yeh pehchanna — quantum image encodings se, aur imaandaari se check karna ki quantum help karta hai ya nahi.
T: NEU-DET par six-class image classification, FRQI/NEQR encodings aur quantum kernels ke saath, leakage-controlled protocol aur matched classical controls ke saath.
E: V4 FRQI kernel 87.8 % vs same-patch classical 83.6 %.
F: Detection hai ya classification? → Poori image ka classification; NEU-DET ke boxes use nahi hue.

**Q2. NEU-DET kya hai?**
S: 1,800 grey steel images ka public dataset, har class mein 300.
T: 200×200 images (RGB mein stored, content grey), train folder 1,440 / validation folder 360; annotations (boxes) ignore.
E: `src/v2/dataset.py` saari 1,800 files ka SHA-256 manifest banata hai.
F: Yeh dataset kyun? → Real industrial task, balanced, exact simulation ke liye chhota, widely used.

**Q3. Chhe classes ke naam batao.**
S: crazing, inclusion, patches, pitted surface, rolled-in scale, scratches.
T: Sab texture-type defects hain; position image se image badalti hai.
E: Class-average images lagbhag flat hain (report Fig 3.5).
F: Sabse mushkil? → Saare models mein rolled-in scale; sabse aasaan patches.

**Q4. Image classification kya hai?**
S: Poori image ko ek label dena.
T: Labelled examples se f: image → {1..6} seekhna, unseen images par evaluate.
E: Humare SVMs har image ko ek class dete hain.
F: Segmentation se farak? → Segmentation pixels ko label karta hai; hum nahi karte.

**Q5. Machine learning kya hai?**
S: Rules likhne ki jagah examples se seekhna.
T: Training data par loss minimise karke parameters fit karna, held-out data par generalisation check.
E: Har seed par 1,080 training images par RBF-SVM fit.
F: Supervised ya unsupervised? → Supervised (labels pata hain).

**Q6. Deep learning kya hai?**
S: Bahut layers wale neural networks se machine learning.
T: Backpropagation se hierarchical feature learning.
E: SmallCNN (4 conv blocks) aur MobileNetV3.
F: MobileNetV3 train kiya? → Nahi, frozen pretrained features.

**Q7. Qubit kya hai?**
S: Quantum bit jo 0 aur 1 ka combination ho sakta hai.
T: ℂ² ka unit vector α|0⟩+β|1⟩, |α|²+|β|²=1.
E: FRQI ka colour qubit cos θ|0⟩ + sin θ|1⟩ rakhta hai.
F: n qubits ko kitne numbers? → 2ⁿ complex amplitudes.

**Q8. Superposition kya hai?**
S: Qubit ki aisi state jo 0 aur 1 dono ka mix hai (ek hi state ki tarah).
T: Kai basis states par non-zero amplitudes.
E: Saare FRQI position qubits par H saari pixel positions ka superposition banata hai.
F: Kya superposition randomness hai? → Nahi; randomness mixed state hai.

**Q9. Entanglement kya hai?**
S: Qubits jinki values aise judi hain ki unhe alag describe nahi kar sakte.
T: Aisi state jo tensor product nahi likhi ja sakti.
E: FRQI: colour position par depend; ZZ maps CNOT use karte hain.
F: Product-RY entangle karta hai? → Nahi.

**Q10. Measurement kya hai?**
S: Qubit padhna, jo state ke hisaab se random 0 ya 1 deta hai.
T: Born rule: P(x) = |⟨x|ψ⟩|²; state collapse.
E: Reconstruction study sab qubits 100–100,000 baar measure karti hai.
F: Bahut shots kyun? → Probabilities estimate karne ke liye.

**Q11. Quantum circuit kya hai?**
S: Qubits par lagne wale quantum gates ki recipe.
T: Registers par unitaries ka sequence, phir measurements.
E: `FRQIEncoder.build_circuit()`.
F: Kis direction mein padhte hain? → Left se right.

**Q12. Quantum simulator kya hai?**
S: Normal computer program jo calculate karta hai ki quantum computer kya karega.
T: Statevector simulation (exact amplitudes) ya sampling.
E: Qiskit Aer + humara NumPy `qsim.py`.
F: Limits? → Memory 2ⁿ; humare ≤ 16 qubits ke liye theek.

**Q13. Real quantum computer use kiya?**
S: Nahi.
T: Sirf exact noiseless CPU simulation.
E: Har page aur paper "simulated" likhta hai.
F: Kyun? → Hazaaron gates wale circuits ko hardware noise barbaad kar deta; simulation se method khud study hota hai.

**Q14. FRQI kya hai?**
S: Image ko qubits mein rakhne ka tareeka: position qubits + ek colour qubit jisme har pixel ka angle.
T: |I⟩ = N^-½ Σ (cos θᵢ|0⟩ + sin θᵢ|1⟩)|i⟩.
E: 8×8 image → 7 qubits.
F: Kisne propose kiya? → Le, Dong, Hirota 2011.

**Q15. NEQR kya hai?**
S: Har grey value ko kai qubits mein binary digits ki tarah rakhta hai.
T: |I⟩ = N^-½ Σ |cᵢ⟩|i⟩, q-bit codes.
E: 16×16, 4-bit → 12 qubits.
F: Kisne? → Zhang, Lu, Gao, Wang 2013.

**Q16. Kernel kya hai?**
S: Do cheezon ke beech similarity score.
T: Kisi feature space mein K(x,y) = ⟨φ(x), φ(y)⟩; SVM ke liye positive semi-definite hona chahiye.
E: RBF kernel; quantum fidelity kernel; Tr(ρAρB).
F: PSD kyun? → Taaki SVM optimisation convex rahe.

**Q17. SVM kya hai?**
S: Classifier jo classes ke beech sabse chauda margin wala boundary banata hai.
T: Support vectors par dual optimisation; non-linear boundaries ke liye kernel trick.
E: Saare quantum kernels ke liye `SVC(kernel="precomputed")`.
F: Multi-class kaise? → One-vs-one (15 binary SVMs).

**Q18. Accuracy kya hai?**
S: Sahi predictions ka fraction.
T: Multi-class: sahi/total.
E: FRQI average par ≈ 316/360 = 87.8 %.
F: Kab misleading? → Imbalanced data — humara case nahi.

**Q19. Training/validation/test split kya hai?**
S: Training par seekho, validation par settings chuno, test par report karo.
T: Validation selection guide karta hai; test sirf final unbiased estimate ke liye.
E: 1,080 / 360 / 360.
F: Test par kyun nahi chunte? → Information leak hoti hai aur results phool jaate hain.

**Q20. Locked test set kya hai?**
S: Test images jinhe model freeze hone tak koi nahi dekhta.
T: 360 validation-folder images, har frozen model ke liye ek baar; access log hota hai.
E: `final_evaluation_stage` + 17 verification checks.
F: Kabhi reuse hua? → Haan V2/V3/V4 mein — disclosed limitation.

**Q21. Preprocessing kya hai?**
S: Model se pehle images taiyaar karna: grey, resize, scale.
T: PIL convert('L') → bilinear resize → /255; optional per-image stretch.
E: `src/v2/dataset.py` mein `preprocess_image()`.
F: [0,1] mein kyun? → FRQI angles ko [0,1] intensities chahiye.

**Q22. PCA kya hai?**
S: Bahut saare numbers ko kuch numbers mein compress karta hai jo zyada variation rakhte hain.
T: Training covariance ke top eigenvectors par projection.
E: Pixels 64×64 → PCA 4/6/8 (V2); texture 76-d → 8/12 (V3).
F: Kis par fit? → Sirf training split par.

**Q23. CNN kya hai?**
S: Network jo image par chhote filters slide karke patterns dhoondhta hai.
T: Convolutions + nonlinearity + pooling; weight sharing.
E: SmallCNN 16-32-64-128 channels.
F: Accuracy? → 93.0 ± 5.9 %.

**Q24. MobileNetV3 kya hai?**
S: Phones ke liye bana chhota, fast pretrained CNN.
T: Depthwise separable convs, inverted residuals, SE, hard-swish, NAS se design.
E: `mobilenet_v3_small`, IMAGENET1K_V1, 576-d features.
F: Result? → Logistic regression ke saath 96.4 %.

**Q25. Hybrid quantum-classical model kya hai?**
S: Classical part features nikaalta hai, quantum part classify karta hai (ya ulta).
T: Yahan: CNN → PCA → angle encoding → quantum kernel → classical SVM.
E: E5-mnv3pca8-qkc-product_ry 93.2 %.
F: Asli mehnat kaun karta hai? → CNN features.

**Q26. Dashboard kya hai?**
S: Web app jo results dikhata hai.
T: React SPA jo FastAPI REST API padhta hai.
E: Home page "All versions · V4 latest".
F: Models train karta hai? → Nahi, read-only (sirf frozen model ka live replay).

**Q27. Measurement shots kya hain?**
S: Circuit kitni baar chala ke measure kiya.
T: Output distribution ke finite samples; error ~1/√shots.
E: Reconstruction mein 100–100,000.
F: Kam shots par? → Noisy images; NEQR mein kaale pixels.

**Q28. Reconstruction kya hai?**
S: Quantum state se picture wapas paana.
T: FRQI har position par arcsin√P; NEQR majority code.
E: 1,800 images × 20 methods.
F: Exact? → Statevector se haan (FRQI), quantisation tak (NEQR).

**Q29. Quantum advantage kya hai?**
S: Koi kaam kisi bhi classical method se behtar/tez karna.
T: Same task par best classical approach se fair comparison chahiye, ideally complexity arguments ke saath.
E: Hum claim nahi karte.
F: Kyun nahi? → Classical controls humare quantum models ke barabar ya behtar hain.

**Q30. Ek line mein main result?**
S: Patches ne FRQI ko 61 % se 88 % tak pahunchaya, par same patches par classical model bhi utna hi achha hai.
T: Whole-image FRQI se +27.1 pp (p < 0.001); same-patch classical se +4.2 pp (p = 0.060, n.s.).
E: Paper ka Table V.
F: Overall best? → MobileNetV3 96.4 %.

---

## Level 2 — Intermediate (Q31–60)

**Q31. Images kaise load aur label hoti hain?**
S: NEU-DET folders se; folder ka naam hi label hai.
T: Manifest mein rel_path, class, folder, index, block, SHA-256.
E: `build_manifest()`.
F: File badal jaaye toh? → Hash check fail, stages ruk jaate hain.

**Q32. Train/validation splits kaise bante hain?**
S: 20 padosi images ke groups saath mein train ya validation mein jaate hain.
T: block = (index−1)//20; har seed par har class ke 3 random validation blocks.
E: `make_split(manifest, seed)`.
F: Blocks kyun? → Padosi indices visually similar hote hain; random split near-duplicates leak karta.

**Q33. Teen seeds kyun?**
S: Dekhne ke liye ki alag split par results kitne badalte hain.
T: Seeds 0,1,2 ka mean ± s.d.; paired tests har image ki correctness ko seeds par average karte hain.
E: NEQR seeds 87.5 / 71.1 / 89.4.
F: Kaafi hain? → Minimum; zyada seeds estimates tight karte.

**Q34. Kaunsa leakage roka?**
S: Test ya validation ki information training ya model choice mein na ghuse.
T: Scalers/PCA sirf train par fit; validation-only selection; hash-frozen selections; ek test access.
E: Check "kisi selection file mein test metric nahi".
F: Koi leakage bacha? → Protocol-level test set reuse.

**Q35. Features ka "angle" view kya hai?**
S: Features ko [0, π] mein scale karna taaki rotation angles ban sakein.
T: Train par fit MinMaxScaler [0, π]; test values clip nahi.
E: `PCAFeaturizer.transform(view="angle")`.
F: V3 mein badlaav? → CDF view π·Φ(z), outliers se robust.

**Q36. QKC mein bandwidth kya hai?**
S: Multiplier jo similarity kitni sharp hai woh control karta hai.
T: Encoding se pehle x = b·a; b ∈ {0.05,0.1,0.2,0.5,1}.
E: `QuantumKernelSVC._scale`.
F: Bahut bada? → Kernel → identity, overfit.

**Q37. Product-RY feature map samjhao.**
S: Har feature apna qubit ghumata hai; aur kuch nahi.
T: K = Πᵢ cos²((xᵢ−yᵢ)/2), closed form.
E: E5 aur V3 mein best map.
F: Kyun include? → Classical-equivalent control.

**Q38. ZZ feature map samjhao.**
S: Rotations plus pairwise entangling terms.
T: H; P(2xᵢ); pairs ke liye CX·P(2(π−xᵢ)(π−xⱼ))·CX; reps baar.
E: zz_linear (neighbour pairs), zz_full (sab pairs).
F: Product-RY ko beat kiya? → Nahi, consistently nahi.

**Q39. Kernel matrix kaise banti hai?**
S: Har training image pair ki similarity nikaalo.
T: Statevectors / density matrices se K_train (1,080×1,080) aur K_test (360×1,080).
E: V4: K = R Rᵀ, R = flattened ρ.
F: Memory? → ~1 M entries, theek.

**Q40. SVM precomputed kernel kaise use karta hai?**
S: Use sirf similarity table chahiye, features nahi.
T: `SVC(kernel="precomputed").fit(K_train, y)`, `predict(K_test)`.
E: `MixedStateEncodingKernelSVC.fit`.
F: Kernel par k-NN kyun nahi? → Margin-based, convex, quantum kernels ke liye standard.

**Q41. VQC kya hai?**
S: Adjustable angles wala quantum circuit jo neural network ki tarah train hota hai.
T: Encoding + parameterised layers + measured expectations + classical loss.
E: RY encoding, L×(RY,RZ)+CNOT ring, 6 ⟨Z⟩ readouts.
F: Kitne parameters? → 2·k·L (k=8, L=3 par 48).

**Q42. VQC kaise train hota hai?**
S: Prediction error kam karne ke liye angles adjust karna.
T: Softmax cross-entropy; parameter-shift gradients; Adam lr 0.05, ya COBYLA, SPSA; validation par early stopping.
E: `VQC.fit`.
F: Best V2 VQC? → 48.1 % (PCA-8, L=3, re-upload).

**Q43. Data re-uploading kya hai?**
S: Har layer se pehle input dobara dena.
T: Har layer par RY(aᵢ) encoding repeat, expressivity badhti hai.
E: k=6,8 ke liye `reupload=True` select hua.
F: Effect? → Chhota fayda.

**Q44. Frozen-circuit ablation kya dikhata hai?**
S: Quantum part ko train karna matter karta hai ya nahi.
T: Random untrained circuit + trained head: 16–29 % vs trained 34–48 %.
E: E4-…-ablation-frozen.
F: V3 encoding-only control? → 92.6 % — cos(aᵢ) par linear head trained VQC ko beat karta hai.

**Q45. Projected quantum kernel kya hai?**
S: Poori state ki jagah do states ke chhote hisse (single-qubit summaries) compare karta hai.
T: Har qubit ke Bloch vectors; K = exp(−(γ/2)Σ‖b_q(x)−b_q(y)‖²).
E: V3 `ProjectedQuantumKernelSVC`.
F: Kyun? → Global overlaps ke kernel concentration se bachne ke liye.

**Q46. V3 ne kaunse features add kiye?**
S: Texture descriptors.
T: LBP uniform (8,1),(16,2),(24,3) → 54; GLCM 32 levels, d=1,2,4, 4 angles, 6 props → 18; std, Sobel mean/std, Laplacian var → 4; total 76.
E: `texture_features()`.
F: Mean brightness kyun hataya? → Illumination nuisance.

**Q47. V4 ka idea kya hai?**
S: Poori images ko pixel-by-pixel compare karne ki jagah saare chhote patches compare karo.
T: ρ = patch density matrices ka mean; K = Tr(ρAρB).
E: FRQI 8×8 patches: 87.8 %.
F: Density matrices kyun? → Order-free mixture; swap-test se measurable.

**Q48. Frozen FRQI model kitne patches use karta hai?**
S: 225.
T: S = 64, p = 8, s = 4 → ((64−8)/4+1)² = 15² = 225.
E: `patches()`.
F: NEQR? → 1,024 (128 px, p 4, s 4).

**Q49. Contrast stretch kyun?**
S: Dark aur bright images ko comparable banata hai.
T: Per-image min–max [0,1]; koi cross-image statistics nahi.
E: FRQI ke liye +8.9 pp validation macro-F1.
F: NEQR ne kyun nahi use kiya? → Uska best validation mean bina stretch tha (par zyada variance).

**Q50. Angle scale b kya hai?**
S: Rotation angles ko multiply karta hai taaki grey values alag dikhein.
T: θ = (π/2)·b·x; b ∈ {1,2,4}; b=4 select hua.
E: b=1 → 75.8 % vs b=4 88.0 % (validation).
F: b>1 invertible? → arcsin se nahi; sirf kernels ke liye.

**Q51. V4 mein classical control kya hai?**
S: Same patches, bina quantum encoding.
T: Mean patch vector + raw patch intensities ka mean outer product → standardise → RBF-SVM.
E: 83.6 ± 0.3 %.
F: "Outer product" kyun? → Yeh quantum feature map ke bina ρ hai.

**Q52. Kaunse statistics use kiye?**
S: Tests jo batate hain ki farak asli hai ya luck.
T: Paired sign-flip permutation (10,000), bootstrap 95 % CI, har seed ka McNemar, 8 tests par Holm.
E: `analyze_v4.py`.
F: Paired kyun? → Dono models ki same test images.

**Q53. Holm correction kya hai?**
S: Bahut saare comparisons test karte waqt significance ko strict banata hai.
T: p-values sort karo; i-th sabse chhote ko α/(m−i+1) se compare; step-down.
E: 8 pre-declared V4 comparisons.
F: Pre-declare kyun? → Cherry-picking rokta hai.

**Q54. Macro-F1 kya hai aur selection ke liye kyun?**
S: Classes ka average F1.
T: Sab classes ko barabar treat karta hai; fail hoti class par sensitive.
E: Har group ka selection criterion.
F: Headline accuracy kyun? → Balanced test set; padhna aasaan.

**Q55. SHA-256 freezing kya karta hai?**
S: Chuni hui settings ko lock karta hai taaki test results dekh ke badal na sakein.
T: Selection files ka hash store; badla toh test stage abort.
E: Freeze hash b1735fdc… (V4).
F: Protocol-level adaptation rok sakta hai? → Nahi.

**Q56. MSE / PSNR / SSIM kya hain?**
S: Error, signal-to-noise, structural similarity.
T: MSE = mean squared difference; PSNR = 10 log₁₀(1/MSE); SSIM luminance/contrast/structure se.
E: FRQI 8×8, 1,000 shots MSE 8.7e-3.
F: SSIM bhi kyun? → MSE structure ignore karta hai (blur vs speckle).

**Q57. FRQI ko shots se kaise decode karte hain?**
S: Har pixel ke liye gino ki colour qubit kitni baar 1 aaya.
T: θ̂ = arcsin√P̂(1|i); x̂ = θ̂/(π/2).
E: `FRQIReconstructor.reconstruct_from_counts`.
F: Error ka source? → Har position par kam shots.

**Q58. NEQR ko shots se kaise decode karte hain?**
S: Har pixel par sabse zyada aaya code lo.
T: Har position par majority vote.
E: `NEQRReconstructor`.
F: Jo pixels observe nahi hue? → 0 (kaala) decode.

**Q59. Dashboard home kya dikhata hai?**
S: Saare versions, V4 bada.
T: Saved aggregates se bana `/api/v4/versions`.
E: AllVersions.tsx.
F: Hard-coded? → Nahi; tests verify karte hain.

**Q60. "How it works" kya karta hai?**
S: Final model ko real test image par step by step replay karta hai.
T: `/api/v4/pipeline` ρ, kernel row, SVM decision recompute karta hai aur saved prediction se check karta hai.
E: Nau steps, Play/Pause/Next.
F: Wahan swap test real hai? → Schematic; values exact compute.

---

## Level 3 — Advanced technical (Q61–95)

**Q61. Do images ka FRQI overlap derive karo.**
S: Angles ko pixel-by-pixel compare karo.
T: ⟨IA|IB⟩ = (1/N) Σᵢ (cos θᵢᴬ cos θᵢᴮ + sin θᵢᴬ sin θᵢᴮ) = (1/N) Σᵢ cos(θᵢᴬ−θᵢᴮ).
E: `frqi_kernel` ise square karta hai.
F: Square kyun? → Fidelity kernel |⟨·|·⟩|²; V3 ne unsquared overlap bhi try kiya.

**Q62. NEQR overlap derive karo.**
S: Equal codes gino.
T: ⟨IA|IB⟩ = (1/N) Σᵢ δ(cᵢᴬ, cᵢᴮ).
E: `neqr_kernel`.
F: 8-bit kyun nuksaan karta hai? → 8-bit codes ka exact match kam → near-identity kernel.

**Q63. Dikhao ki Tr(ρAρB) mean squared patch overlap ke barabar hai.**
S: Dono mixtures expand karo.
T: Tr[(1/PA Σₖ|a_k⟩⟨a_k|)(1/PB Σₗ|b_l⟩⟨b_l|)] = (1/PAPB) Σₖₗ ⟨a_k|b_l⟩⟨b_l|a_k⟩ = (1/PAPB) Σ |⟨a_k|b_l⟩|².
E: `MixedStateEncodingKernelSVC` ka docstring.
F: PSD hai? → Haan, Hilbert–Schmidt inner product.

**Q64. Patch kernel shift-tolerant kyun hai?**
S: Content khiskane par patches sirf reorder hote hain.
T: Uniform mixture permutation-invariant; stride ke multiple shift par sirf border patches badalte hain.
E: Unit test: cyclic shift ke baad normalised kernel > 0.999.
F: Rotation-invariant? → Nahi.

**Q65. V4 kernel compute karne ki complexity.**
S: ρ use karna saare patch pairs se kaafi sasta.
T: Pairs: O(P²D) per image pair; ρ: O(PD²) per image + O(D²) per entry; P²=50,625 ≫ D=128.
E: `einsum("npi,npj->nij")`.
F: ρ ki memory? → Har image ke 128×128 floats.

**Q66. Swap test probability.**
S: 0 aane ki probability overlap encode karti hai.
T: P(0) = ½(1 + Tr(ρσ)); Tr estimate 2p̂−1, s.e. ≤ 1/√M.
E: Paper Eq. (3).
F: 0.01 precision ke liye kitne shots? → Har entry ~10⁴.

**Q67. Random patches ke saath swap-test estimate unbiased kyun?**
S: Average mein sahi value deta hai.
T: Uniform k,l par |⟨a_k|b_l⟩|² ka expectation = Tr(ρAρB); random pair par swap test iska unbiased estimate.
E: Paper "Estimation on hardware".
F: Simulate kiya? → Nahi.

**Q68. FRQI patches ke swap test ko kitne qubits?**
S: 15.
T: 2 × 7 + 1 ancilla.
E: 8×8 patch → 7 qubits.
F: NEQR 4×4 4-bit? → 2×8+1 = 17.

**Q69. FRQI shot error resolution ke saath kyun badhta hai?**
S: Shots zyada pixels mein bant jaate hain.
T: Har position ko ~M/N samples; P̂ ka variance ~ P(1−P)N/M.
E: 1,000 shots: 8.7e-3 (8×8) vs 6.4e-2 (16×16).
F: Fix? → Zyada shots (100k: 2.6e-4).

**Q70. FRQI ki gate complexity.**
S: Har pixel par ek controlled rotation.
T: n controls wale N MCRY; har ek O(n) ya zyada basic gates mein decompose.
E: 8×8: 8,339 compiled gates.
F: Theory mein behtar constructions? → Haan (jaise uniformly-controlled rotations), yahan use nahi.

**Q71. NEQR gate count data par kyun depend karta hai?**
S: Sirf 1-bits ko gates chahiye.
T: Har pixel ke har set bit par MCX.
E: Alag patches par 1,998 vs 2,901.
F: Worst case? → N·q MCX.

**Q72. Parameter-shift rule.**
S: Do shifted circuit runs se exact gradient.
T: Pauli/2 se generated gates ke liye ∂⟨O⟩/∂θ = [⟨O⟩(θ+π/2) − ⟨O⟩(θ−π/2)]/2.
E: `param_shift_jacobian`.
F: Cost? → Har parameter par 2 circuits.

**Q73. Barren plateau kya hai?**
S: Gradients lagbhag zero ho jaate hain, training ruk jaati hai.
T: Random circuits mein gradient variance qubits/depth ke saath exponentially ghatta hai.
E: VQC initialisation par gradient statistics record karta hai.
F: Kernels isse kaise bachte hain? → Circuit ki gradient training nahi hoti.

**Q74. Kernel concentration kya hai?**
S: Saari similarity values lagbhag same ho jaati hain.
T: Bade registers par fidelity kernels exponentially concentrate hote hain (Thanasilp et al.).
E: Chhote patch registers aur PQK ki motivation.
F: Data mein kaise dikhta hai? → Near-identity ya near-constant kernel matrices (diagnostics record).

**Q75. MinMax angles problem kyun ban sakte hain.**
S: Outliers baaki values ko daba dete hain.
T: Ek extreme training value range compress kar deti hai; V3 CDF π·Φ(z) robust hai.
E: Views "angle" vs "cdf".
F: Test values clip karna? → Nahi kiya (data-dependent hota).

**Q76. NEQR selection mein bias–variance.**
S: Best mean par unstable.
T: No-stretch NEQR val 89.2 ± 7.2 vs stretch 86.8 ± 2.3; test ne instability confirm ki.
E: Seed 1 par rolled-in scale sab galat.
F: Ab stretch par switch karna chahiye? → Nahi — woh test set ko selection ke liye use karna hoga.

**Q77. Rolled-in-scale failure samjhao.**
S: Us class ki test images zyada dark hain.
T: Mean intensity 0.496 (train) vs 0.329 (test); bina per-image stretch NEQR codes levels khisak jaate hain.
E: EDA Table 3.3; NEQR 118/180 vs FRQI 178/180 sahi.
F: FRQI theek kyun? → Stretch brightness normalise karta hai.

**Q78. One-vs-one SVM kyun?**
S: sklearn SVC ka default.
T: 15 binary classifiers, voting; decision_function ovr shape mein dikhta hai.
E: `/pipeline` ovr-shaped scores deta hai.
F: Results par effect? → Predictions par koi nahi.

**Q79. C = 1000 kyun?**
S: Validation par select hua.
T: Weak regularisation kernel ko zyada closely fit karta hai; C=1 se 53.8 %.
E: Ablation table.
F: Grid ka edge? → Haan, limitation.

**Q80. Paired permutation test details.**
S: Bahut baar randomly swap karo ki kis model ko har image ka score mila.
T: d = per-image correctness difference (seed-averaged); 10,000 random sign flips; p = observed se bade ya barabar |mean| ka fraction.
E: `analyze_v4.py`.
F: t-test kyun nahi? → Kam assumptions.

**Q81. McNemar test.**
S: Woh images gino jo ek model sahi aur doosra galat karta hai.
T: Har seed ke discordant pairs (a-only : b-only).
E: FRQI vs V2 seed 0: 114:25.
F: Har seed alag kyun? → Har seed alag classifier pair hai.

**Q82. Bootstrap CI.**
S: Difference ka spread dekhne ke liye test images resample karo.
T: Per-image differences ke 10,000 resamples; 2.5–97.5 percentiles.
E: FRQI vs V2: [+21.7, +32.7] pp.
F: CI 0 cross kare toh? → Significant nahi (jaise NEQR vs control).

**Q83. FRQI vs control CI ne 0 exclude kiya par p = 0.060 kyun?**
S: Alag tests aur Holm correction.
T: Uncorrected bootstrap CI [+0.5,+7.7]; Holm-adjusted permutation p = 0.060.
E: Table VI.
F: Conclusion? → Pre-declared rule ke hisaab se significant nahi.

**Q84. V2 kernels mein shot model.**
S: Har kernel entry mein realistic sampling noise daalna.
T: K̂ᵢⱼ ~ Binomial(shots, Kᵢⱼ)/shots — ideal compute–uncompute ke liye exact.
E: `sample_shot_kernel`.
F: Validate hua? → Entries Aer par cross-check.

**Q85. Kernels ke liye Aer ki jagah NumPy simulation kyun?**
S: Hazaaron states ke liye kaafi tez.
T: Poore dataset par batched statevector; gates Qiskit jaise; tests 1e-10.
E: `src/v2/qsim.py`.
F: Risk? → Tests aur Recorder-based resource counts se kam.

**Q86. Transpilation basis aur kyun.**
S: Fair counting ke liye standard gate set mein convert.
T: {cx, rz, sx, x}, optimisation level 1, all-to-all.
E: `circuit_resources`.
F: Real topology ke saath? → Zyada CX (SWAPs).

**Q87. MobileNetV3 yahan itna strong kyun?**
S: Uske pretrained filters textures achhe se pakadte hain.
T: Generic ImageNet features texture classes par transfer hote hain; 576-d rich representation.
E: 96.4 %.
F: Fine-tuning? → Nahi kiya; aur badha sakta tha.

**Q88. Pixels ka PCA kharab kyun perform karta hai?**
S: Woh brightness patterns rakhta hai, textures nahi.
T: Leading components global intensity gradients pakadte hain; PCA-8 SSIM 0.59.
E: Fig 5.14 ke PCA columns blurry.
F: Behtar? → Texture ya CNN features.

**Q89. LBP samjhao.**
S: Har pixel ko uske padosiyon se compare karke encode karta hai.
T: Radius R par P neighbours → binary code; "uniform" patterns; histogram.
E: (8,1),(16,2),(24,3).
F: Rotation invariant? → Uniform LBP ho sakta hai.

**Q90. GLCM samjhao.**
S: Ginta hai ki ek distance par grey levels kitni baar saath aate hain.
T: Co-occurrence matrix → contrast, dissimilarity, homogeneity, energy, correlation, ASM.
E: 32 levels, d=1,2,4, 4 angles ka average.
F: Pehle stretch kyun? → Levels ka comparable use.

**Q91. CDF angle mapping.**
S: Standardised values ko smoothly angles mein badalta hai.
T: angle = π·Φ(z), Φ = normal CDF.
E: V3 groups mein suffix "c".
F: Fayda? → Clipping nahi, outliers se robust.

**Q92. Kernel diagonal par purity.**
S: Mixed state ki self-similarity.
T: K(A,A) = Tr(ρA²) ≤ 1; diverse textures ke liye kam.
E: `purity_mean` diagnostic.
F: Normalised kernel? → Sirf display ke liye K/√(K_AA K_BB).

**Q93. Patch states concatenate kyun nahi kiye?**
S: Usse positions phir fix ho jaati.
T: Patches ka tensor product = bahut bada register aur position-dependent.
E: Methodology ka design choice.
F: Mixture kya kho deta hai? → Spatial layout (inclusion vs pitted confusion).

**Q94. Confusion matrix FRQI ke baare mein kya batata hai?**
S: Kaunsi classes mix hoti hain.
T: Inclusion→pitted 38/180, scratches→rolled-in 40/180.
E: Fig 7 / 5.6.
F: Kyun? → Layout ke bina local patches ek jaise dikhte hain.

**Q95. Image difficulty kaise naapi?**
S: Saare models mein se kitno ne har image sahi ki.
T: 163 models × 3 seeds; median image 67 %; koi image hamesha sahi ya hamesha galat nahi.
E: `/api/v4/images`, Fig 11.
F: Mislabelled images? → Koi saboot nahi (errors faile hue hain).

---

## Level 4 — Project-specific (Q96–125)

**Q96. FRQI circuit kahan banta hai?** S: `src/frqi/encoder.py`. T: H, X-sandwich, har pixel par `mcry(angle)`, kaala skip. E: 2×2 → 3 qubits. F: Kaunsa angle diya? → xᵢπ (=2θ).

**Q97. V2 ke FRQI/NEQR kernels kahan hain?** S: `src/v2/frqi_neqr.py`. T: Closed forms encoder statevectors se verify (`tests/test_v2_frqi_neqr.py`). E: E1/E2 groups. F: Closed form kyun? → Speed; same results.

**Q98. Selection aur testing kaunsi file chalaati hai?** S: `src/v2/runner.py`. T: `final_evaluation_stage` ke andar `run_candidate`, `select`, `final_test`. E: V2–V4 mein use. F: Test se pehle retrain? → Nahi; saved estimator apply hota hai.

**Q99. V4 kahan implemented hai?** S: `src/v4/models.py`. T: `mixed_states`, `MixedStateEncodingKernelSVC`, `PatchMomentRBF`. E: `scripts/v4/run_v4.py` se 864 runs. F: Grid size? → 288 configs.

**Q100. V2 mein kitne models aur runs?** S: 88 selected, 2,583 runs. T: 0 failed. E: `/api/v2/summary`. F: Families? → classical, CNN, QKC, VQC, hybrid, FRQI/NEQR.

**Q101. Best V2 pure quantum model?** S: Pixel PCA-8 par QKC ZZ-full. T: 64.0 ± 3.5 %. E: E3-pca8-qkc-zz_full. F: Classical equivalent? → RBF-SVM PCA-8 64.8 %.

**Q102. Best V2 hybrid?** S: CNN PCA-8 + product-RY QKC. T: 93.2 ± 1.1 % vs same features par RBF-SVM 93.0. E: E5. F: Quantum gain? → Koi significant nahi.

**Q103. Best V3 quantum?** S: Texture PCA-12 + product-RY QKC 95.3 %. T: product-RY classically computable. E: V3-tex12c-qkc-product_ry. F: Classical? → 95.6 %.

**Q104. Kaunse V4 groups hain?** S: FRQI p4/p8, NEQR p2/p4, patch-moment control. T: 5 groups. E: v4_results.json. F: Headline rule? → Har encoding ka best validation, test se pehle declare.

**Q105. Frozen FRQI configuration?** S: 64 px, 8×8 patches, stride 4, b=4, stretch, C=1000. T: 7 qubits, 225 patches. E: V4-frqi-p8. F: Val macro-F1? → 88.0.

**Q106. Frozen NEQR configuration?** S: 128 px, 4×4, stride 4, 4-bit, bina stretch, C=1000. T: 8 qubits, 1,024 patches. E: V4-neqr-p4. F: Val? → 89.2.

**Q107. Test access kaise log hota hai?** S: Har test evaluation record hota hai. T: aggregates mein test_access_log; verification: freeze ke baad har frozen group ka ek access. E: verify_v4.py. F: Count? → 5 (har group ka ek).

**Q108. 17 checks kya cover karte hain?** S: Data, results aur protocol integrity. T: V0/V2/V3 unchanged, manifests identical, freeze unchanged, single access, predictions sirf frozen configs ke, selection mein test metrics nahi, 864 runs 0 failed, recomputed accuracy, headlines validation se, 8 comparisons, real circuits, control mein circuit nahi. E: v4_verification.json. F: Sab pass? → 17/17.

**Q109. V0 results kaise protect hue?** S: Write-guards aur hashes. T: `assert_writable`, env flags, verify_historical.py; V0 launch endpoints 409 dete hain. E: HistoricalHome page. F: V0 kyun rakha? → Project history ka saboot.

**Q110. V0 mein kya galat tha?** S: Chhote runs aur galat labels. T: Har run ~42 train/12–16 test, alphabetical order, locked test nahi, "VQC" softmax regression tha. E: E1/E2-legacy-softmax 24–26 %. F: Seekh? → Pehle protocol.

**Q111. MobileNetV3 features cache kaise hote hain?** S: Har image set ke liye ek baar compute. T: Hashed caches ke saath `FrozenMobileNetV3Source._pool`. E: cnn.py. F: Determinism? → `torch.use_deterministic_algorithms(True)`.

**Q112. Experiment folder mein kya hota hai?** S: Config, metrics, predictions, model. T: config.json, validation/test metrics, predictions.csv, confusion_matrix.json, circuit_stats.json, model/estimator.joblib. E: results/qml_v4/experiments/V4-frqi-p8__09d3a4f853__s0. F: Sabke test metrics? → Sirf frozen configs.

**Q113. `/api/v4/versions` numbers kahan se laata hai?** S: Saved aggregates padhta hai. T: V2 analysis.json, V3 v3_results.json, V4 v4_results.json; V0 not comparable mark. E: AllVersions page. F: Test hua? → pytest files se compare karta hai.

**Q114. Circuits page diagrams kahan se laata hai?** S: Rebuilt real circuits. T: Checkpoints se build_circuit_artifacts.py → instructions + Qiskit text diagram → SVG. E: 33 configurations. F: Trained VQC params? → Included.

**Q115. Reconstruction (all 1,800) page kya dikhata hai?** S: 20 methods ki quality aur image browser. T: `/reconstruction/summary` + `/reconstruction/image`. E: Shot animation. F: Data source? → reconstructions.npz.

**Q116. Kitne tests?** S: Bahut. T: 179 pytest functions, 27 Vitest, Playwright e2e. E: tests/, frontend tests. F: Paper numbers verify? → validate_v4_pack.py 27/27.

**Q117. Paper ka har number kahan se aata hai?** S: Results padhne wale scripts se. T: make_v4_paper_pack.py aggregates se tables/figures likhta hai. E: research_paper_visuals/. F: Manual edits? → Text haan; numbers validator check karta hai.

**Q118. Upload feature V4 ka hissa hai?** S: Nahi, legacy V0 lab. T: `/api/quantum/compare-custom` uploaded image ko FRQI+NEQR se encode, Aer, reconstruct, metrics. E: V0 Encoding Lab. F: Save hota hai? → Nahi.

**Q119. 3×3 playground kya hai?** S: Chhoti image par teaching demo. T: Precomputed JSON, `illustrative: true`. E: /playground. F: Real dataset? → Nahi, illustrative label.

**Q120. "Hard-coding nahi" kaunsa page prove karta hai?** S: Tests karte hain. T: Vitest unusual numbers mock karke display check karta hai. E: v2.test.tsx. F: Browser check? → e2e tile ko v4_results.json se compare karta hai.

**Q121. NEQR ke ρ matrices kitne bade?** S: 256×256. T: 8 qubits → D=256. E: Frozen NEQR. F: Har image ki memory? → 65,536 floats.

**Q122. Kaunsi V4 setting sabse zyada matter karti hai (validation)?** S: C aur angle scale. T: C=1 → 53.8 %; b=1 → 75.8 %; stretch off → 79.1 %. E: Ablation table. F: Test-based ablation? → Sirf pre-declared frozen groups ke liye.

**Q123. FRQI ke liye 64×64 kyun?** S: Best validation. T: 32 → 79.1, 64 → 88.0, 128 → 85.4 (val). E: Ablation. F: Wajah? → Detail aur patch scale ka balance.

**Q124. Per-class F1 kya dikhata hai?** S: Class-wise strengths/weaknesses. T: FRQI p8: crazing 93.1, patches 95.8, pitted 81.5, scratches 81.3; NEQR rolled-in 65.0. E: Table 5.7. F: Classical control kahan strong? → rolled-in 93.0, scratches 95.9.

**Q125. Reconstruction exactness counts.** S: FRQI saari images ke liye exact. T: Statevector se 1,800/1,800; NEQR sirf 8 bits par exact. E: Table 5.8. F: PCA? → Exact nahi; SSIM 0.59.

---

## Level 5 — Examiner ke challenges (Q126–150)

**Q126. Kya project quantum advantage dikhata hai?** S: Nahi. T: Same-patch classical control barabar (p=0.060); texture SVM behtar (p<0.001); kernels classically simulable. E: Table VI. F: Phir kyun kiya? → Yeh pata karne ke liye ki quantum image encodings ko kya rokta hai aur claims ko fairly test karne ke liye.

**Q127. Novelty kya hai?** S: FRQI/NEQR images ko position-free compare karne ka tareeka plus strict evaluation. T: Patch-ensemble mixed-state kernel, matched control, leakage-controlled protocol, poori reconstruction study. E: Whole-image kernels se +27 pp. F: Kya mixture ka idea naya hai? → Natural idea hai; contribution uska controlled evaluation hai.

**Q128. Test set reuse kiya. Results biased nahi?** S: Shayad thoda. T: Protocol-level adaptivity; V4 ke andar single access. E: Discussion mein disclose. F: Fix? → Fresh dataset.

**Q129. Failure dekh ke NEQR tune kyun nahi kiya?** S: Woh cheating hoti. T: Test ko selection ke liye use karna estimate ko invalid kar deta. E: Jaisa tha waisa rakha. F: Kya report karoge? → Dono, change ko post-hoc mark karke.

**Q130. 3 seeds kaafi hain?** S: Minimum. T: Variance estimates rough; paired per-image tests power badhate hain. E: NEQR s.d. 10.1. F: Improve? → Zyada seeds / repeated CV.

**Q131. Kya classical control jaan-boojh ke kamzor ho sakta hai?** S: Nahi, use same grid treatment mila. T: 72 configs, validation selection, same patches, stretch option. E: 83.6 ± 0.3. F: Strong control? → Texture SVM 95.6 %.

**Q132. Kya tumhare kernels sach mein "quantum" hain?** S: Woh real quantum encodings se aate hain. T: FRQI/NEQR states; par closed forms hain → classically computable. E: Qiskit statevectors se verify. F: Kab simulable nahi honge? → Kaafi bade registers par.

**Q133. Product-RY toh classical kernel hi hai na?** S: Haan. T: Πcos² closed form; control ki tarah use. E: E5/V3 mein best. F: Matlab? → Yahan entanglement ne help nahi ki.

**Q134. Gate counts bahut bade hain — practical hai?** S: Aaj ke hardware par nahi. T: Har patch 8,339 gates, 225 patches, plus swap tests. E: Resources table. F: Improvement? → Shallower encoders, approximate state prep.

**Q135. Noise ka kya?** S: Model nahi kiya. T: Overlap estimates kam karega; gehre circuits fail. E: Future work. F: Kaise test karoge? → Aer noise models, shot-based kernels.

**Q136. Simulator sahi hai kaise pata?** S: Qiskit ke against tests. T: qsim vs Statevector 1e-10; closed-form kernels vs encoder statevectors; V4 kernel vs Qiskit overlaps. E: tests/test_v2_qsim.py, test_v4_models.py. F: Aer check? → aer_validation.py.

**Q137. Preprocessing se leakage ho sakta hai?** S: Nahi. T: Scalers/PCA sirf train par; stretch per image. E: features.py docstrings. F: CNN ImageNet par pretrained — leakage? → ImageNet mein NEU images nahi hain.

**Q138. FRQI NEQR se behtar kyun?** S: Smoother similarity. T: Continuous angles vs exact-match codes; stretch brightness shift hatata hai. E: +5.1 pp. F: Cause prove hua? → Plausible explanation, proven nahi.

**Q139. Doosre data par results hold karenge?** S: Pata nahi. T: Texture-type defects par shayad similar; test karna padega. E: Limitation. F: Kaunsa data? → Doosra steel/fabric defect set.

**Q140. Doosre QIRs (GQIR, MCQI, QPIE) kyun nahi?** S: FRQI aur NEQR canonical do hain (angle vs basis). T: Dono encoding principles cover; baaki variants hain. E: Yan et al. survey. F: Amplitude encoding (QPIE) help karta? → Kam qubits par same position-locking jab tak patch na karo.

**Q141. MobileNetV3 fine-tune kyun nahi kiya?** S: Frozen hi 96 % tha aur fixed feature ki tarah zyada fair. T: Fine-tuning variance aur cost badhata. E: E7. F: Expected gain? → Chhota.

**Q142. VQC kamzor hai — implementation bug?** S: Shayad nahi. T: Parameter-shift gradients tested; ablations expected jaisa behave karte hain; known optimisation difficulties. E: tests/test_v2_vqc.py. F: Encoding-only control 92.6 % — matlab? → Head kaam karta hai.

**Q143. V0 numbers kahin zyada kyun (jaise SVM 76.6 %)?** S: Alag, aasaan, leaky split. T: Train folder ka random 70/30, near-duplicates dono sets mein. E: results/models. F: Use kyun nahi kiye? → Comparable nahi.

**Q144. V4 classification ke liye shots kam karte toh?** S: Accuracy girti. T: Har kernel entry mein estimation noise; V4 ke liye simulate nahi kiya. E: V2 FRQI 8×8: 1,000 shots par 57.8 → 39.3 %. F: Kitne shots chahiye estimate karo? → Future work.

**Q145. 2×2 par SSIM meaningful hai?** S: Mushkil se. T: Window fit honi chahiye; evaluator win_size chhota karta hai; chhoti images par SSIM unstable. E: Metrics evaluator. F: Toh MSE use karo. → Haan.

**Q146. Seeds par accuracy ± s.d. sahi uncertainty hai?** S: Split variability dikhata hai. T: Test-sampling uncertainty include nahi karta — isliye bootstrap/permutation tests add kiye. E: Dono report. F: Kis par trust? → Comparisons ke liye paired tests.

**Q147. V3 ka re-tuned FRQI kharab kyun hua (57.5 vs 60.6)?** S: Normal selection noise. T: Same validation (≈69 %), alag config chuna; test alag. E: V3-frqi8. F: Contradiction? → Nahi.

**Q148. Kya dashboard users ko mislead kar sakta hai?** S: Sab label kiya hai. T: Simulation banners, "not comparable" V0, illustrative playground, numbers API se. E: Home hero note. F: Koi live computation? → Sirf frozen model ka replay.

**Q149. Sabse badi limitation?** S: Hardware nahi aur quantum advantage nahi. T: Classically simulable kernels, ek dataset, test-set reuse. E: Discussion. F: Sabse important future step? → Finite-shot + noise kernel study, fresh data.

**Q150. Project kaise improve karoge?** S: Hardware/noise aur naye data par test. T: Noise ke saath shot-based swap-test kernels, fresh test set, bade/entangling patch encoders, learned patch weighting, fine-tuned CNN baseline. E: Conclusion. F: Pehle kaunsa? → Finite-shot noisy kernels — yeh batata hai ki method usable hai bhi ya nahi.
