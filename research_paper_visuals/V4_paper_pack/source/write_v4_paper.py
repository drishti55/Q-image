"""Paper text for Protocol V4 -> research_paper_visuals/V4_paper_pack/content/
PAPER_V4.md   (Markdown, figures linked)       PAPER_V4.docx (Word: text + all figures + all tables embedded)
Every number comes from data/numbers.json / data/tables.json written by make_v4_paper_pack.py (nothing typed by hand)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "research_paper_visuals" / "V4_paper_pack"
OUT = PACK / "content"
OUT.mkdir(exist_ok=True)
N = json.loads((PACK / "data/numbers.json").read_text())
T = {t["name"]: t for t in json.loads((PACK / "data/tables.json").read_text())}
fr, ne, ds, rc, cm = N["frqi"], N["neqr"], N["dataset"], N["recon"], {c["name"]: c for c in N["cmp"]}
fp, nep = fr["params"], ne["params"]
XP = N["xp"]


def c(prefix):
    return next(v for k, v in cm.items() if k.startswith(prefix))


def sci(v):
    return "0 (exact)" if v < 1e-15 else f"{v:.2e}"


cF2, cF3, cN2 = c("V4 FRQI vs V2"), c("V4 FRQI vs V3"), c("V4 NEQR vs V2")
cFN, cFC, cNC = c("V4 FRQI vs V4 NEQR"), c("V4 FRQI vs classical patch"), c("V4 NEQR vs classical patch")
cFT, cNT = c("V4 FRQI vs classical texture"), c("V4 NEQR vs classical texture")
v2f, v2n, tex = N["refs"]["E1b-frqi8-qkc-scaled"], N["refs"]["E2-neqr16-b4-qkc"], N["refs"]["V3-tex12c-rbfsvm"]
ctrl = N["others"]["V4-patchmom-rbfsvm"]

B = []   # (kind, payload)
h1 = lambda s: B.append(("h1", s))  # noqa: E731
h2 = lambda s: B.append(("h2", s))  # noqa: E731
p = lambda s: B.append(("p", s))  # noqa: E731
eq = lambda s: B.append(("eq", s))  # noqa: E731
ul = lambda *s: B.append(("ul", list(s)))  # noqa: E731
fig = lambda f, cap: B.append(("fig", (f, cap)))  # noqa: E731
tab = lambda name: B.append(("tab", name))  # noqa: E731

B.append(("title", "Patch-Ensemble Mixed-State Kernels for FRQI and NEQR Quantum Image Representations: "
                   "A Leakage-Controlled Study on Steel Surface Defect Classification"))
B.append(("sub", "Q-ImageLab — Protocol V4 · draft manuscript text · all numbers generated from the saved result files"))

h1("Abstract")
p(f"Flexible Representation of Quantum Images (FRQI) and the Novel Enhanced Quantum Representation (NEQR) are the two most widely "
  f"used ways of loading an image into a quantum state. Used directly as kernels for classification, they compare two images pixel "
  f"by pixel at fixed positions, which is poorly suited to texture-like defects. On the NEU-DET steel surface defect dataset "
  f"({ds['n']:,} images, {ds['classes']} classes) such whole-image FRQI and NEQR kernels reached only {v2f} % and {v2n} % locked-test "
  f"accuracy in our earlier protocol. We propose a patch-ensemble mixed-state kernel: every p×p patch of an image is encoded as an "
  f"FRQI or NEQR state, the image is represented by the uniform mixture ρ of its patch states, and two images are compared by the "
  f"Hilbert–Schmidt overlap Tr(ρAρB), which a swap test estimates directly. All {N['search']['configs']} candidate configurations "
  f"({N['search']['runs']} runs) were selected on a validation split only, frozen with SHA-256 hashes and evaluated once on a locked "
  f"test set of {ds['test']} images. The selected FRQI model reaches {fr['acc']} % and the NEQR model {ne['acc']} % (mean ± s.d. over three "
  f"splits), improvements of {cF2['diff']} and {cN2['diff']} percentage points over the whole-image baselines (Holm-corrected p {cF2['p']}). "
  f"However, a classical RBF-SVM on the same patches reaches {ctrl} % (FRQI difference {cFC['diff']} pp, p {cFC['p']}, not significant) and "
  f"a classical texture-feature SVM remains best at {tex} %. A complementary study reconstructs all {rc['n']:,} images with {rc['methods']} "
  f"encodings from real Qiskit circuits. All quantum computations are exact classical simulations; we make no claim of quantum advantage.")
p("**Keywords:** quantum image processing; FRQI; NEQR; quantum kernel; mixed state; swap test; steel surface defects; NEU-DET; reproducibility.")

h1("1. Introduction")
p("Quantum image representations (QIRs) describe how pixel positions and intensities are stored in the amplitudes or basis states of a "
  "register of qubits. FRQI [1] stores each intensity in the rotation angle of one colour qubit entangled with a position register; NEQR [2] "
  "stores a q-bit binary intensity in q colour qubits, making intensity retrieval deterministic. Both are standard building blocks of "
  "quantum image processing, and a natural way to use them for classification is as a quantum kernel [4, 5]: the similarity of two images "
  "is the squared overlap of their encoded states, and a support vector machine (SVM) [10] is trained on it.")
p(f"In earlier protocols of this project (V2 and V3), such whole-image FRQI and NEQR kernels stayed near 60 % accuracy on the six NEU-DET "
  f"defect classes [3] although the same data are classified at above 95 % by classical texture features. The reason is structural: the "
  f"overlap of two whole-image FRQI states sums cos(θᵢᴬ − θᵢᴮ) over the same pixel index i, so the kernel compares pixels at identical "
  f"positions. A scratch shifted by a few pixels produces an almost unrelated state, while NEU defect classes are defined by texture, not position.")
p("This paper keeps FRQI and NEQR as the encodings but changes what is encoded and how two images are compared. Our contributions are:")
ul("A patch-ensemble mixed-state kernel for FRQI and NEQR: images are represented by the mixed state of their encoded patches and compared "
   "by Tr(ρAρB), a translation-robust quantity that a swap test measures directly.",
   f"A leakage-controlled evaluation: {N['search']['configs']} configurations searched on validation only, SHA-256-frozen selections, a single "
   f"locked-test evaluation per model ({N['frozen']['test_events']} logged test accesses), 8 pre-declared paired comparisons with Holm correction, "
   f"and {N['verify']['total']} automated integrity checks.",
   "A matched classical control on identical patches, so that the effect of the quantum encoding can be separated from the effect of patching.",
   f"A full reconstruction study of all {rc['n']:,} NEU-DET images under {rc['methods']} encodings (real Qiskit circuits, exact and finite-shot).")

h1("2. Background")
h2("2.1 FRQI and NEQR")
p("For an image with N = 2ⁿ × 2ⁿ pixels and intensities xᵢ ∈ [0, 1], FRQI uses 2n position qubits and one colour qubit:")
eq("|I_FRQI⟩ = N^(-1/2) Σᵢ (cos θᵢ |0⟩ + sin θᵢ |1⟩) ⊗ |i⟩,   θᵢ = (π/2) · b · xᵢ")
p("where b is an angle-scale hyper-parameter (b = 1 is the original definition). NEQR uses q colour qubits that hold the quantised intensity:")
eq("|I_NEQR⟩ = N^(-1/2) Σᵢ |cᵢ⟩ ⊗ |i⟩,   cᵢ = round(xᵢ (2^q − 1))")
p("FRQI therefore needs 2n + 1 qubits and NEQR needs 2n + q qubits.")
h2("2.2 Quantum kernels and the swap test")
p("A fidelity kernel K(A, B) = |⟨ψA|ψB⟩|² can be estimated on hardware with the swap test [6], which outputs 0 on an ancilla with "
  "probability (1 + Tr(ρσ))/2 for any two input states ρ and σ, pure or mixed. We use this property in Section 3.3.")

h1("3. Methodology")
fig("Fig01_methodology_flowchart", "Figure 1. Methodology. (a) Data protocol: validation-only model selection, SHA-256 freeze, one locked-test "
    "evaluation per frozen model and pre-declared statistics. (b) The patch-ensemble mixed-state kernel for one image.")
h2("3.1 Dataset and splits")
p(f"NEU-DET [3] contains {ds['n']:,} grayscale hot-rolled steel images of {ds['classes']} defect classes (crazing, inclusion, patches, pitted "
  f"surface, rolled-in scale, scratches; 300 per class). The 360 images of the official validation folder form the **locked test set**; they "
  f"are not read until every model is frozen. The 1,440 train-folder images are split into {ds['train']:,} training and {ds['val']} validation "
  f"images with a group-blocked strategy ({ds['strategy']}), for three split seeds (0, 1, 2). Table 1 gives the counts.")
tab("Tab01_dataset_splits")
h2("3.2 Preprocessing and patch extraction")
p("Each image is converted to grayscale, resized to S × S pixels (S ∈ {32, 64, 128}) and scaled to [0, 1]. Optionally, a per-image min–max "
  "contrast stretch is applied; it uses only the image itself, never training statistics. The image is cut into p × p patches with stride s, "
  "giving P = ((S − p)/s + 1)² patches.")
h2("3.3 Patch-ensemble mixed-state kernel")
p("Each patch k is encoded as an FRQI state (2·log₂p + 1 qubits) or an NEQR state (2·log₂p + q qubits) with the same encoder circuits used "
  "for whole images. The image I is represented by the mixed state of a uniformly chosen patch:")
eq("ρ_I = (1/P) Σₖ |ψₖ⟩⟨ψₖ|")
p("and two images are compared by the Hilbert–Schmidt overlap")
eq("K(A, B) = Tr(ρ_A ρ_B) = (1 / (P_A P_B)) Σₖ Σₗ |⟨ψₖᴬ | ψₗᴮ⟩|²")
p("This is the average squared overlap over all pairs of patches, so a pattern that appears anywhere in both images contributes, regardless of "
  "its position. On hardware, a swap test between one random patch state of A and one of B estimates K(A, B) directly, because the swap "
  "test measures Tr(ρσ) for mixed inputs. An SVM with a precomputed kernel is trained on K. In this study all overlaps were computed exactly "
  "from statevectors on a CPU; unit tests confirm that the result equals the mean squared overlap of the Qiskit encoder statevectors and that "
  "the kernel is robust to translations of the image content. Figure 2 illustrates every step on a real training image.")
fig("Fig02_patch_encoding_illustration", f"Figure 2. The method on a real NEU-DET training image (frozen FRQI settings: {fp['image_size']}×{fp['image_size']}, "
    f"{fp['patch']}×{fp['patch']} patches, stride {fp['stride']}). (a) image and example patches; (b) one patch; (c) its {fr['qubits']}-qubit FRQI amplitudes; "
    f"(d) the image's mixed state ρ; (e) normalised kernel between classes (10 training images per class).")
h2("3.4 Classical control")
p("To separate the effect of patching from that of the quantum encoding, a classical control uses the identical patches (same S, p, s and "
  "normalisation) and describes each image by classical patch-intensity moments, classified with an RBF-SVM. It has no circuit and is labelled classical throughout.")
h2("3.5 Hyper-parameter search, selection and freezing")
p(f"Table 2 lists the grid: image size, patch size and stride, normalisation, the FRQI angle scale b or the NEQR bit depth q, and the SVM "
  f"regularisation C. In total {N['search']['configs']} configurations were trained for each of three split seeds ({N['search']['runs']} runs, "
  f"{N['search']['failed']} failed). Within each group the configuration with the highest mean validation macro-F1 was selected; the locked "
  f"test set was not consulted. The FRQI and NEQR headline models were chosen by the same rule, declared before testing. Selections were "
  f"written to disk, hashed with SHA-256 and frozen; the test stage aborts if any selection file changes. Each frozen group was then "
  f"evaluated on the locked test set exactly once, and every access was logged. Table 3 lists the selected configurations.")
tab("Tab02_search_space")
tab("Tab03_selected_configs")
fig("Fig09_validation_sweep", "Figure 3. Validation-only hyper-parameter sweep: best validation macro-F1 for each image size / stride and normalisation. "
    "The locked test set was not used.")
h2("3.6 Statistical analysis")
p("Eight comparisons were declared before testing (Table 5). For each, per-image correctness is averaged over the three seeds and compared with "
  "a paired sign-flip permutation test (10,000 permutations); 95 % confidence intervals come from a paired bootstrap, and an exact McNemar "
  "test [8] is reported per seed. p-values are corrected over the eight comparisons with the Holm method [7].")
h2("3.7 Reconstruction study")
p(f"Independently of classification, every one of the {rc['n']:,} NEU-DET images was encoded and reconstructed with {rc['methods']} methods: "
  "whole-image FRQI at 2×2 to 16×16, whole-image NEQR at the same sizes with 2, 4 and 8 bits, the V4 patch representations (FRQI 8×8 patches, "
  "NEQR 4×4 patches) and, for reference, classical PCA with 8 and 12 components (fit on the seed-0 training split). Quantum rows use the real "
  "Qiskit encoder circuits [9], Qiskit-Aer statevector simulation, and both the exact output distribution and multinomial samples of 100 to "
  "100,000 shots, decoded with the project's decoder. Reconstruction uses no labels, so including test-folder images cannot influence model selection.")
h2("3.8 Implementation")
p(f"Python, Qiskit / Qiskit-Aer [9] and scikit-learn [11]. Circuit resources are reported after transpilation to the basis {{cx, rz, sx, x}} at "
  f"optimisation level 1 with all-to-all coupling. Everything ran on a CPU; no quantum hardware and no noise model were used. The selection was "
  f"frozen at {N['frozen']['at'][:19]} (SHA-256 {N['frozen']['sha'][:16]}…). Table 10 lists the {N['verify']['total']} automated integrity checks, "
  f"all of which pass.")

h1("4. Results")
h2("4.1 Main result")
p(f"Table 4 and Figure 4 summarise the locked-test results. The FRQI headline model ({fp['patch']}×{fp['patch']} patches, {fr['qubits']} qubits "
  f"per patch state) reaches **{fr['acc']} %** accuracy (macro-F1 {fr['f1']} %); the NEQR headline model ({nep['patch']}×{nep['patch']} patches, "
  f"{nep['bits']}-bit, {ne['qubits']} qubits) reaches **{ne['acc']} %** (macro-F1 {ne['f1']} %). For FRQI, validation macro-F1 ({fr['val']} %) and test macro-F1 "
  f"({fr['f1'].split(' ')[0]} %) are close; for NEQR the test score is lower and more variable (Section 4.4).")
tab("Tab04_main_results")
fig("Fig03_main_results", "Figure 4. Locked-test accuracy of all V4 groups and reference models (mean ± s.d. over seeds 0–2; dots = individual seeds; ★ = headline chosen by validation).")
h2("4.2 Improvement over whole-image FRQI and NEQR")
p(f"The patch-ensemble kernel improves FRQI by **{cF2['diff']} pp** over the V2 whole-image FRQI kernel (95 % CI {cF2['ci']}, p_Holm {cF2['p']}) and "
  f"by {cF3['diff']} pp over the best V3 FRQI kernel ({cF3['ci']}, p_Holm {cF3['p']}). NEQR improves by **{cN2['diff']} pp** ({cN2['ci']}, p_Holm "
  f"{cN2['p']}). FRQI is now better than NEQR by {cFN['diff']} pp ({cFN['ci']}, p_Holm {cFN['p']}). Figure 5 shows the progression across protocols "
  f"and Figure 6 all eight comparisons.")
fig("Fig04_frqi_neqr_across_protocols", "Figure 5. FRQI and NEQR test accuracy across protocols V2, V3 and V4, with classical references.")
tab("Tab05_statistical_comparisons")
fig("Fig05_comparisons_forest", "Figure 6. The eight pre-declared paired comparisons: accuracy difference with 95 % bootstrap CI and Holm-corrected p-values.")
h2("4.3 Comparison with classical models")
p(f"On identical patches, the classical RBF-SVM control reaches {ctrl} %. The FRQI kernel is {cFC['diff']} pp higher, but the difference is not "
  f"significant after Holm correction (CI {cFC['ci']}, p_Holm {cFC['p']}); NEQR differs by {cNC['diff']} pp (p_Holm {cNC['p']}). Most of the gain "
  f"over the whole-image kernels therefore comes from the patch representation, which classical models can use equally well. The best classical "
  f"texture model of Protocol V3 (RBF-SVM on texture features, {tex} %) remains clearly better than both FRQI ({cFT['diff']} pp, p_Holm {cFT['p']}) "
  f"and NEQR ({cNT['diff']} pp, p_Holm {cNT['p']}).")
h2("4.4 Per-class behaviour and stability")
p(f"Figure 7, Figure 8 and Table 6 show per-class results. Summed over three seeds, FRQI classifies {ne['rolled_correct_frqi']} of 180 rolled-in-scale "
  f"test images correctly, NEQR only {ne['rolled_correct']}. NEQR's seed accuracies are {', '.join(ne['seeds'])} %; on seed 1 it misclassifies every "
  f"rolled-in-scale image (Figure 9). The earlier whole-image kernels also failed on this class, which suggests a brightness difference between "
  f"the train and test folders for it; FRQI, selected with per-image contrast stretch, is not affected. NEQR was selected without stretch and "
  f"was not re-tuned after the test, since that would use the test set for model choice.")
fig("Fig07_per_class_f1", "Figure 7. Per-class F1 on the locked test set (mean over seeds).")
fig("Fig06_confusion_matrices", "Figure 8. Row-normalised confusion matrices summed over seeds 0–2.")
tab("Tab06_per_class_f1")
fig("Fig08_seed_stability", "Figure 9. Test accuracy of each split seed. NEQR's seed-1 drop is caused by the rolled-in-scale class.")
h2("4.5 Circuit resources")
p(f"Table 7 and Figure 10 report the encoder circuit for one patch state. The FRQI headline needs {fr['qubits']} qubits, "
  f"{N['circuit_frqi']['gates_compiled']:,} compiled gates (depth {N['circuit_frqi']['depth_compiled']:,}, {N['circuit_frqi']['cx_compiled']:,} CX). "
  f"A swap test between two patch states needs 2·{fr['qubits']} + 1 = {2 * fr['qubits'] + 1} qubits. Because the whole image is never loaded at "
  f"once, qubit count depends on the patch size, not on the image size.")
tab("Tab07_circuit_resources")
fig("Fig10_circuit_resources", "Figure 10. Qubits, compiled gates and compiled depth of the encoder circuit for one patch.")
h2("4.6 Reconstruction of all images")
p(f"Table 8 and Figures 11–13 summarise the reconstruction of all {rc['n']:,} images. FRQI statevector decoding reproduced "
  f"{'every' if rc['frqi_exact_all'] else 'not every'} image exactly at every resolution; its error comes only from finite shots and grows with image "
  f"size because the shots are spread over more pixels (1,000 shots: MSE {sci(rc['R-FRQI-8x8|shots1000'])} at 8×8 and "
  f"{sci(rc['R-FRQI-16x16|shots1000'])} at 16×16; 100,000 shots: {sci(rc['R-FRQI-16x16|shots100000'])} at 16×16). NEQR is exact up to "
  f"quantisation (4-bit floor MSE {sci(rc['neqr_q4'])}; 8-bit lossless) once every pixel has been observed. The V4 FRQI patch representation "
  f"reaches MSE {sci(rc['P-FRQI-64-p8|shots1000'])} with 1,000 shots per patch on 64×64 images. Classical PCA with 8 components keeps "
  f"little of the image (SSIM {rc['pca8_ssim']:.3f}; 12 components {rc['pca12_ssim']:.3f}), which helps explain why PCA-input quantum classifiers "
  f"in earlier protocols had little texture to work with.")
tab("Tab08_reconstruction")
fig("Fig11_reconstruction_mse_vs_shots", f"Figure 11. Reconstruction MSE versus measurement shots, mean over all {rc['n']:,} images.")
fig("Fig13_reconstruction_ssim_by_method", "Figure 12. Mean SSIM of every reconstruction method (exact and 1,000 shots).")
fig("Fig12_reconstruction_examples", "Figure 13. One locked-test-folder image per class reconstructed by representative methods (saved decoder outputs).")
h2("4.7 Per-image analysis across all protocols")
pi = N["per_image"]
p(f"Using the saved predictions of all {pi['n_models']} selected models of protocols V2–V4 (three seeds each), the median test image is classified "
  f"correctly by {pi['median_pct']:.0f} % of model-seed pairs; {pi['never_correct']} images are never classified correctly and {pi['always_correct']} "
  f"are always classified correctly (Figure 14). Averaged over all models, {pi['hardest_class'].replace('_', ' ')} is the hardest class and "
  f"{pi['easiest_class'].replace('_', ' ')} the easiest. Table 9 and Figure 15 place the V4 models among the key models of all protocols.")
fig("Fig14_per_image_difficulty", "Figure 14. (a) Fraction of all model-seed pairs that classify each test image correctly; (b) mean per class, all models vs V4 FRQI.")
tab("Tab09_cross_protocol")
fig("Fig15_cross_protocol_overview", "Figure 15. Key quantum (simulated) and classical models across protocols V2, V3 and V4.")

h1("5. Discussion")
p("The central result is that the poor accuracy of FRQI and NEQR kernels on NEU-DET was caused by *what* was compared, not by the encodings "
  "themselves. Averaging encoded patches into a mixed state turns a position-sensitive similarity into a texture-sensitive one, and both "
  f"encodings gain more than 20 percentage points. FRQI benefits more than NEQR ({cFN['diff']} pp). A plausible explanation is that its continuous angles combined with the "
  "contrast stretch give a smooth similarity, while NEQR's discrete intensity levels make its overlaps all-or-nothing per pixel and more "
  "sensitive to brightness shifts.")
p("The matched control shows that the improvement should not be read as a quantum effect. A classical model on the same patches is statistically "
  "indistinguishable from the FRQI kernel, and a classical texture model is better still. Every kernel in this study has a closed form and was "
  "computed classically, so the study demonstrates a better *use* of quantum image representations, not a computational advantage.")
p("The method is nevertheless hardware-friendly in one respect: the circuit size is set by the patch (5–8 qubits per patch state here), "
  "not by the image, and the kernel needs only swap tests between random patch pairs. The cost moves into the number of shots, which we did not simulate for classification.")

h1("6. Limitations and threats to validity")
ul("**Simulation only.** No quantum hardware and no noise model were used. Kernel entries were exact; a hardware estimate would require many swap-test shots per entry.",
   "**No quantum advantage.** All overlaps are classically computable, and a classical model on identical patches performs equally well.",
   "**The locked test set is not fresh.** It was used by protocols V2 and V3; V4 was proposed after their weak FRQI/NEQR results. V4 was frozen on validation and tested once, but the protocol-level choice of method was informed by earlier test results.",
   "**Validation-only exploration.** Before the grid was fixed, a few patch geometries were explored on the validation split (never the test set); all but one are part of the reported grid.",
   f"**NEQR instability.** NEQR's accuracy varies strongly across splits (s.d. {ne['acc'].split('±')[1].strip()} pp), driven by one class.",
   "**One dataset.** Results are for NEU-DET only.")

h1("7. Conclusion")
p(f"Representing an image by the mixed state of its encoded patches and comparing images by Tr(ρAρB) raises FRQI kernel accuracy on NEU-DET "
  f"from {v2f} % to {fr['acc']} % and NEQR from {v2n} % to {ne['acc']} % under a leakage-controlled, pre-registered evaluation. The gain is "
  f"real and statistically significant against the whole-image kernels, but it is matched by a classical model on the same patches and does "
  f"not reach the best classical texture model ({tex} %). Future work should estimate the kernel with finite swap-test shots and realistic noise, "
  f"test on a fresh dataset, and study whether patch-ensemble kernels on larger patches retain their accuracy when they are no longer classically simulable.")

h1("Data and code availability")
p("All numbers, tables and figures are generated from the saved result files by `research_paper_visuals/source/make_v4_paper_pack.py` and this text "
  "by `write_v4_paper.py`. Protocol V4 is reproduced by `scripts/v4/` (setup → candidates → select → freeze → test → analyse → verify). "
  "An interactive dashboard page (“How it works”) replays the full pipeline on any test image and recomputes the frozen model's prediction live.")

h1("References")
B.append(("refs", [
    "P. Q. Le, F. Dong, K. Hirota, “A flexible representation of quantum images for polynomial preparation, image compression, and processing operations,” Quantum Information Processing, 10(1):63–84, 2011.",
    "Y. Zhang, K. Lu, Y. Gao, M. Wang, “NEQR: a novel enhanced quantum representation of digital images,” Quantum Information Processing, 12(8):2833–2860, 2013.",
    "K. Song, Y. Yan, “A noise robust method based on completed local binary patterns for hot-rolled steel strip surface defects,” Applied Surface Science, 285:858–864, 2013.",
    "V. Havlíček, A. D. Córcoles, K. Temme, A. W. Harrow, A. Kandala, J. M. Chow, J. M. Gambetta, “Supervised learning with quantum-enhanced feature spaces,” Nature, 567:209–212, 2019.",
    "M. Schuld, N. Killoran, “Quantum machine learning in feature Hilbert spaces,” Physical Review Letters, 122:040504, 2019.",
    "H. Buhrman, R. Cleve, J. Watrous, R. de Wolf, “Quantum fingerprinting,” Physical Review Letters, 87:167902, 2001.",
    "S. Holm, “A simple sequentially rejective multiple test procedure,” Scandinavian Journal of Statistics, 6(2):65–70, 1979.",
    "Q. McNemar, “Note on the sampling error of the difference between correlated proportions or percentages,” Psychometrika, 12(2):153–157, 1947.",
    "A. Javadi-Abhari et al., “Quantum computing with Qiskit,” arXiv:2405.08810, 2024.",
    "C. Cortes, V. Vapnik, “Support-vector networks,” Machine Learning, 20:273–297, 1995.",
    "F. Pedregosa et al., “Scikit-learn: Machine learning in Python,” Journal of Machine Learning Research, 12:2825–2830, 2011.",
]))
B.append(("p", "*Check every reference against the original publication and your journal's citation style before submission.*"))

# ───────────────────────────── Markdown
md = []
for k, v in B:
    if k == "title":
        md.append(f"# {v}\n")
    elif k == "sub":
        md.append(f"*{v}*\n")
    elif k == "h1":
        md.append(f"## {v}\n")
    elif k == "h2":
        md.append(f"### {v}\n")
    elif k == "p":
        md.append(v + "\n")
    elif k == "eq":
        md.append(f"```\n{v}\n```\n")
    elif k == "ul":
        md.append("\n".join(f"- {x}" for x in v) + "\n")
    elif k == "fig":
        md.append(f"![{v[1]}](../figures/{v[0]}.png)\n\n*{v[1]}*\n")
    elif k == "tab":
        md.append((PACK / "tables" / f"{v}.md").read_text())
    elif k == "refs":
        md.append("\n".join(f"[{i + 1}] {r}" for i, r in enumerate(v)) + "\n")
(OUT / "PAPER_V4.md").write_text("\n".join(md))

# ───────────────────────────── Word
import re  # noqa: E402

from docx import Document  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.shared import Inches, Pt, RGBColor  # noqa: E402

doc = Document()
st = doc.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(10.5)
for s in doc.sections:
    s.left_margin = s.right_margin = Inches(0.9)


def runs(par, text):
    for i, part in enumerate(re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)", text)):
        if not part:
            continue
        if part.startswith("**"):
            par.add_run(part[2:-2]).bold = True
        elif part.startswith("*"):
            par.add_run(part[1:-1]).italic = True
        elif part.startswith("`"):
            r = par.add_run(part[1:-1]); r.font.name = "Consolas"; r.font.size = Pt(9)
        else:
            par.add_run(part)


def caption(text):
    cp = doc.add_paragraph(); r = cp.add_run(text); r.italic = True; r.font.size = Pt(9); r.font.color.rgb = RGBColor(0x44, 0x4b, 0x55)


for k, v in B:
    if k == "title":
        t = doc.add_heading(v, 0); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif k == "sub":
        sp = doc.add_paragraph(); sp.alignment = WD_ALIGN_PARAGRAPH.CENTER; r = sp.add_run(v); r.italic = True; r.font.size = Pt(9)
    elif k == "h1":
        doc.add_heading(v, 1)
    elif k == "h2":
        doc.add_heading(v, 2)
    elif k == "p":
        runs(doc.add_paragraph(), v)
    elif k == "eq":
        ep = doc.add_paragraph(); ep.alignment = WD_ALIGN_PARAGRAPH.CENTER; r = ep.add_run(v); r.font.name = "Cambria Math"; r.font.size = Pt(10.5)
    elif k == "ul":
        for x in v:
            runs(doc.add_paragraph(style="List Bullet"), x)
    elif k == "fig":
        doc.add_picture(str(PACK / "figures" / f"{v[0]}.png"), width=Inches(6.4))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        caption(v[1])
    elif k == "tab":
        t = T[v]
        hp = doc.add_paragraph(); r = hp.add_run(t["title"]); r.bold = True; r.font.size = Pt(9.5)
        tbl = doc.add_table(rows=1, cols=len(t["head"])); tbl.style = "Table Grid"
        for i, h in enumerate(t["head"]):
            cell = tbl.rows[0].cells[i]; cell.text = ""; rr = cell.paragraphs[0].add_run(h); rr.bold = True; rr.font.size = Pt(8)
        for row in t["rows"]:
            cells = tbl.add_row().cells
            for i, x in enumerate(row):
                cells[i].text = ""; rr = cells[i].paragraphs[0].add_run(str(x)); rr.font.size = Pt(8)
        if t["notes"]:
            caption(t["notes"])
        doc.add_paragraph()
    elif k == "refs":
        for i, r_ in enumerate(v):
            rp = doc.add_paragraph(f"[{i + 1}] {r_}"); rp.paragraph_format.left_indent = Inches(0.3); rp.paragraph_format.first_line_indent = Inches(-0.3)
            for run in rp.runs:
                run.font.size = Pt(9)
doc.save(OUT / "PAPER_V4.docx")
print("written", OUT / "PAPER_V4.md", OUT / "PAPER_V4.docx")
