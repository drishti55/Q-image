// Builds the Q-ImageLab project report (.docx). Two passes: pass 1 with "–" page numbers, then pages.json
// (from the rendered PDF) fills the contents / list of figures / list of tables.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType, HeadingLevel,
  BorderStyle, ShadingType, PageNumber, Footer, LevelFormat, PageBreak, PositionalTab, PositionalTabAlignment,
  PositionalTabRelativeTo, PositionalTabLeader, VerticalAlign, TableLayoutType,
} = require("docx");

const Q = "/Users/drishti/Library/Mobile Documents/com~apple~CloudDocs/Projects/QIP/research_paper_visuals";
const PK = Q + "/V4_paper_pack/figures/";
const RF = Q + "/Project_Report/figures/";
const SS = Q + "/Project_Report/screenshots_jpg/";
const DIMS = JSON.parse(fs.readFileSync(path.join(__dirname, "dims.json"), "utf8"));
const PAGES = fs.existsSync(path.join(__dirname, "pages.json")) ? JSON.parse(fs.readFileSync(path.join(__dirname, "pages.json"), "utf8")) : {};
const OUT = process.argv[2] || path.join(__dirname, "report.docx");
const EDA = JSON.parse(fs.readFileSync(RF + "eda_stats.json", "utf8"));

const FONT = "Times New Roman";
const TW = 9026; // A4 text width in DXA (1-inch margins)
const body = [];
const figs = [], tabs = [], heads = [];
let chap = 0, figN = 0, tabN = 0, eqN = 0;

// ───────────────────────── helpers ─────────────────────────
const run = (t, o = {}) => new TextRun({ text: t, font: FONT, size: o.size || 24, bold: o.bold, italics: o.italics, color: o.color, superScript: o.sup });
function rich(text, o = {}) {
  // **bold** and *italic* inline markup
  const parts = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) parts.push(run(text.slice(last, m.index), o));
    const s = m[0];
    if (s.startsWith("**")) parts.push(run(s.slice(2, -2), { ...o, bold: true }));
    else parts.push(run(s.slice(1, -1), { ...o, italics: true }));
    last = m.index + s.length;
  }
  if (last < text.length) parts.push(run(text.slice(last), o));
  return parts;
}
const P = (text, o = {}) => body.push(new Paragraph({ children: rich(text, o), alignment: o.align || AlignmentType.JUSTIFIED, spacing: { line: 360, after: 120 }, indent: o.indent }));
const bullets = (items) => items.forEach((t) => body.push(new Paragraph({ children: rich(t), numbering: { reference: "bul", level: 0 }, alignment: AlignmentType.JUSTIFIED, spacing: { line: 336, after: 60 } })));
const numbered = (items, ref = "num") => items.forEach((t) => body.push(new Paragraph({ children: rich(t), numbering: { reference: ref, level: 0 }, alignment: AlignmentType.JUSTIFIED, spacing: { line: 336, after: 60 } })));

function chapter(title) {
  chap += 1; figN = 0; tabN = 0; eqN = 0;
  body.push(new Paragraph({ children: [new PageBreak()] }));
  body.push(new Paragraph({ heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER, children: [run(`CHAPTER ${chap}`, { size: 28, bold: true })], spacing: { before: 0, after: 60 } }));
  const t = title.toUpperCase();
  body.push(new Paragraph({ alignment: AlignmentType.CENTER, children: [run(t, { size: 32, bold: true })], spacing: { after: 360 } }));
  heads.push({ level: 1, text: `Chapter ${chap}: ${title}`, key: `CHAPTER ${chap}` });
}
let sec = 0, sub = 0;
function H2(t) { sec += 1; sub = 0; const n = `${chap}.${sec}`; body.push(new Paragraph({ heading: HeadingLevel.HEADING_2, children: [run(`${n} ${t}`, { size: 28, bold: true })] })); heads.push({ level: 2, text: `${n} ${t}`, key: `${n} ${t}` }); }
function H3(t) { sub += 1; const n = `${chap}.${sec}.${sub}`; body.push(new Paragraph({ heading: HeadingLevel.HEADING_3, children: [run(`${n} ${t}`, { size: 24, bold: true })] })); heads.push({ level: 3, text: `${n} ${t}`, key: `${n} ${t}` }); }
const resetSec = () => { sec = 0; sub = 0; };

function img(file, widthIn) {
  const d = DIMS[file];
  if (!d) throw new Error("no dims for " + file);
  const w = Math.round(widthIn * 96), h = Math.round((w * d[1]) / d[0]);
  return new ImageRun({ type: file.endsWith(".jpg") ? "jpg" : "png", data: fs.readFileSync(file), transformation: { width: w, height: h } });
}
function figure(file, caption, widthIn = 6.2) {
  figN += 1;
  const id = `${chap}.${figN}`;
  body.push(new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 }, children: [img(file, widthIn)] }));
  body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [run(`Figure ${id}: `, { bold: true, size: 21 }), ...rich(caption, { size: 21 })] }));
  figs.push({ id, text: caption, key: `Figure ${id}:` });
  return `Figure ${id}`;
}
function equation(file) {
  eqN += 1;
  const d = DIMS[file];
  let w = Math.round((d[0] / 300) * 96 * 0.9); if (w > 560) w = 560;
  const h = Math.round((w * d[1]) / d[0]);
  body.push(new Paragraph({
    alignment: AlignmentType.LEFT, spacing: { before: 80, after: 120 },
    tabStops: [{ type: "center", position: Math.round(TW / 2) }, { type: "right", position: TW }],
    children: [new TextRun({ text: "\t", font: FONT }), new ImageRun({ type: "png", data: fs.readFileSync(file), transformation: { width: w, height: h } }),
      new TextRun({ text: "\t", font: FONT }), run(`(${chap}.${eqN})`)],
  }));
  return `(${chap}.${eqN})`;
}
const border = { style: BorderStyle.SINGLE, size: 4, color: "9AA3AD" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(caption, head, rows, widths, o = {}) {
  tabN += 1;
  const id = `${chap}.${tabN}`;
  const sum = widths.reduce((a, b) => a + b, 0);
  const W = widths.map((w) => Math.round((w / sum) * TW));
  W[W.length - 1] += TW - W.reduce((a, b) => a + b, 0);
  body.push(new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 200, after: 80 }, children: [run(`Table ${id}: `, { bold: true, size: 21 }), ...rich(caption, { size: 21 })] }));
  const fs_ = o.size || 19;
  const cell = (t, i, hdr, shade) => new TableCell({
    width: { size: W[i], type: WidthType.DXA }, borders, verticalAlign: VerticalAlign.CENTER,
    shading: hdr ? { fill: "DCE6F2", type: ShadingType.CLEAR, color: "auto" } : shade ? { fill: "F5F7FA", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: String(t).split("\n").map((line) => new Paragraph({ alignment: i === 0 || o.left ? AlignmentType.LEFT : (o.alignAll || AlignmentType.LEFT), children: rich(line, { size: fs_, bold: hdr || undefined }) })),
  });
  body.push(new Table({
    width: { size: TW, type: WidthType.DXA }, columnWidths: W, layout: TableLayoutType.FIXED,
    rows: [new TableRow({ tableHeader: true, children: head.map((h, i) => cell(h, i, true)) }),
      ...rows.map((r, k) => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, i, false, k % 2 === 1)) }))],
  }));
  body.push(new Paragraph({ spacing: { after: 160 }, children: [] }));
  tabs.push({ id, text: caption, key: `Table ${id}:` });
  return `Table ${id}`;
}
const pg = (key) => (PAGES[key] != null ? String(PAGES[key]) : "–");
function dotLine(left, page, o = {}) {
  return new Paragraph({
    spacing: { after: o.after ?? 40, line: 300 }, indent: { left: o.indent || 0 },
    tabStops: [{ type: "right", position: TW, leader: "dot" }],
    children: [...rich(left, { size: o.size || 22, bold: o.bold }), new TextRun({ text: "\t", font: FONT, size: o.size || 22 }), run(page, { size: o.size || 22 })],
  });
}
const centerTitle = (t, after = 360) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after }, children: [run(t, { size: 32, bold: true })] });
const blank = (n = 1) => Array.from({ length: n }, () => new Paragraph({ children: [] }));

// ───────────────────────── numbers used in the text ─────────────────────────
const B = EDA.brightness, C = EDA.contrast;
const f3 = (v) => v.toFixed(3);

// ═════════════════════════ CHAPTER 1 ═════════════════════════
chapter("Introduction"); resetSec();
H2("Introduction to Project");
H3("Overview");
P("Surface defects on hot-rolled steel strips, such as cracks, scratches, inclusions and rolled-in scale, reduce product quality and must be detected quickly on production lines. Automated visual inspection is therefore an important application of image classification, and the NEU surface defect database (NEU-DET) is a widely used public benchmark for it [5], [6]. At the same time, quantum computing has motivated a new family of image representations and classifiers. Quantum image representations (QIRs) describe how the positions and intensities of pixels can be stored in the amplitudes or basis states of a small number of qubits [4], and quantum kernels use such encodings to measure the similarity of two inputs [2], [9].");
P("This project, **Q-ImageLab**, studies whether the two most widely used quantum image representations, the Flexible Representation of Quantum Images (FRQI) [7] and the Novel Enhanced Quantum Representation (NEQR) [8], can classify real steel defect images, and how they compare with classical methods under a fair and leakage-controlled evaluation. All quantum computations are performed by exact classical simulation with Qiskit [20]; no quantum hardware is used, and no quantum advantage is claimed.");
P("The work was carried out in several protocols (versions). The first prototype (V0) showed that quick experiments on a few images give unreliable numbers. Protocol V2 introduced a locked test set and validation-only model selection and compared 88 quantum, hybrid and classical models; whole-image FRQI and NEQR kernels reached only about 60% test accuracy. Protocol V3 added texture features and showed that quantum kernels on good classical features perform well, but did not improve FRQI or NEQR themselves. The final protocol, V4, proposes a **patch-ensemble mixed-state kernel**: every small patch of an image is encoded with FRQI or NEQR, the image is represented by the mixture of its patch states, and images are compared through the overlap Tr(ρAρB). This raises FRQI accuracy from 60.6% to **87.8 ± 1.5%** and NEQR from 60.2% to **82.7 ± 10.1%**.");
P("Besides the experiments, the project delivers a complete software system: a Python/FastAPI back end that serves every saved result, and a React/TypeScript dashboard that shows all versions, replays the frozen V4 model step by step on any test image, and reconstructs all 1,800 dataset images with 20 encodings. " + "The home page of the dashboard is shown in Figure 1.1.");
figure(SS + "S01_home_all_versions.jpg", "Home page of the Q-ImageLab dashboard, showing the latest (V4) results in large type together with links to the live walkthrough and the reconstruction study.");
H2("Existing System");
P("Steel surface inspection in industry is traditionally performed by human inspectors or by classical machine-vision systems. Manual inspection is slow and subjective, while classical systems rely either on hand-crafted texture descriptors such as local binary patterns (LBP) [17] and grey-level co-occurrence matrices (GLCM) [18], or on deep convolutional networks [6], [26]. These classical approaches are accurate, but they offer no route to quantum processing.");
P("Existing work on quantum images, on the other hand, concentrates on how to prepare and manipulate quantum image states, not on whether they help with real classification tasks [4], [7], [8]. Quantum machine-learning studies usually evaluate on small synthetic data sets or handwritten digits [2], [11]. Our own first prototype (V0) had further practical problems that are typical of early quantum-ML experiments, summarised in Table 1.1.");
table("Limitations of existing approaches and of the first prototype (V0)", ["Existing approach", "What it does well", "Limitation addressed in this project"], [
  ["Manual visual inspection", "Flexible, no training data needed", "Slow, subjective, not reproducible"],
  ["Classical texture features + SVM [5], [17], [18]", "High accuracy on NEU data", "No quantum component; used here as a strong baseline"],
  ["Deep CNN detectors [6], [26]", "End-to-end learning, high accuracy", "Large models; no link to quantum image encodings"],
  ["QIR papers (FRQI, NEQR) [7], [8]", "Compact, well-defined quantum encodings", "No evaluation on classifying real textured images"],
  ["Quantum kernel / VQC demos [2], [11]", "Show that encodings define kernels", "Synthetic or toy data; single split; no matched classical control"],
  ["V0 prototype (this project)", "Working FRQI/NEQR pipeline", "About 42 training and 12–16 test images per run, alphabetical file order, no locked test set; numbers not comparable"],
], [2.4, 2.2, 3.4]);
H2("User Requirement Analysis");
P("The system is intended for three groups of users: researchers and students who run and analyse experiments, reviewers or supervisors who need to verify the results, and visitors who want an intuitive explanation of how quantum image encodings work. Their requirements were collected from the project goals and are listed as functional requirements in Table 1.2 and non-functional requirements in Table 1.3.");
table("Functional requirements", ["ID", "Requirement", "Implemented in"], [
  ["FR1", "Load NEU-DET, verify every file with SHA-256 and build fixed train/validation/test splits", "src/v2/dataset.py, manifest"],
  ["FR2", "Encode images with FRQI and NEQR using real Qiskit circuits", "src/frqi, src/neqr, src/v4/models.py"],
  ["FR3", "Train quantum, hybrid and classical classifiers on the same splits", "src/v2, src/v3, src/v4"],
  ["FR4", "Select models on validation data only and freeze the selection", "src/v2/runner.py, scripts/v4/run_v4.py"],
  ["FR5", "Evaluate each frozen model once on the locked test set and log the access", "final_test() with access log"],
  ["FR6", "Run pre-declared statistical comparisons with multiple-test correction", "scripts/v4/analyze_v4.py"],
  ["FR7", "Reconstruct images from measured quantum states for several shot counts", "scripts/v4/reconstruct_all.py"],
  ["FR8", "Serve all results through a REST API", "api_main.py, /api/v2, /api/v3, /api/v4"],
  ["FR9", "Show results of all versions and replay the final model on any test image", "React dashboard pages"],
  ["FR10", "Export publication-quality figures and tables", "research_paper_visuals/source"],
], [0.7, 5.0, 2.6]);
table("Non-functional requirements", ["Category", "Requirement"], [
  ["Correctness", "Every reported number must be recomputable from saved files; no test-set leakage"],
  ["Reproducibility", "Fixed seeds (0, 1, 2), hashed manifests and selections, scripted pipeline"],
  ["Transparency", "Simulation clearly labelled; no claims of hardware execution or quantum advantage"],
  ["Performance", "All 864 V4 validation runs feasible on one laptop CPU"],
  ["Usability", "Dashboard readable on desktop and phone widths (no horizontal scrolling at 390 px)"],
  ["Maintainability", "Versioned result folders (results/qml_v2 … qml_v4); older results never modified"],
  ["Testability", "Automated unit, API, frontend and browser tests"],
], [2.0, 6.0]);
H2("Feasibility Study");
P("**Technical feasibility.** Exact simulation of a quantum state needs memory that grows exponentially with the number of qubits. The V4 method keeps every register at 5–8 qubits by encoding patches instead of whole images, so the computation fits easily on a laptop CPU (Apple M5, 16 GB RAM). All required libraries (Qiskit, scikit-learn, NumPy, FastAPI, React) are mature and open source.");
P("**Economic feasibility.** The project uses only free software and a public data set. No cloud quantum hardware time is required, which removes the main cost of quantum experiments.");
P("**Operational feasibility.** Experiments are run by scripts with resumable stages (setup, candidates, select, freeze, test, analyse, verify), and the dashboard needs only two commands to start. Results are stored as plain JSON and CSV files that can be inspected without special tools.");
P("**Schedule feasibility.** The work was divided into phases that each produced a usable result, as shown in Table 1.4, so that a complete, honest outcome was available even if a later phase had not improved the accuracy.");
table("Project phases", ["Phase", "Main activities", "Output"], [
  ["V0 prototype", "FRQI/NEQR encoders, first QML runs, first dashboard", "Working pipeline; showed need for a proper protocol"],
  ["V2 protocol", "Locked test set, 88 models (quantum, hybrid, classical), statistics", "Fair baseline; whole-image FRQI/NEQR ≈ 60%"],
  ["V3 protocol", "Texture and CNN features into quantum kernels and VQCs (70 groups)", "Quantum kernels on texture features up to 95.3%"],
  ["V4 protocol", "Patch-ensemble mixed-state kernel, 864 validation runs, 8 comparisons", "FRQI 87.8%, NEQR 82.7%"],
  ["Reconstruction study", "20 encodings × 1,800 images, shots 100–100,000", "Exactness and shot-noise analysis"],
  ["Dashboard and reporting", "React pages, live walkthrough, figures, paper and report", "Interactive system and documentation"],
], [1.8, 3.8, 2.8]);

// ═════════════════════════ CHAPTER 2 ═════════════════════════
chapter("Literature Review"); resetSec();
P("This chapter summarises the research that the project builds on, grouped by topic. The topics are quantum image representations, quantum kernels and their limits, variational and hybrid quantum models, steel surface defect recognition, and evaluation methodology.");
H2("Quantum Machine Learning and Quantum Images");
P("Biamonte et al. [1] reviewed quantum machine learning and described how quantum states in large Hilbert spaces may provide feature spaces that are hard to compute classically. Preskill [3] pointed out that near-term (NISQ) devices are small and noisy, so practical studies must use short circuits and few qubits. Yan et al. [4] surveyed quantum image representations and classified them by how they store position and colour information.");
P("Le et al. [7] introduced FRQI, which stores an image of N pixels in log₂N + 1 qubits: the position register is in uniform superposition and one colour qubit is rotated by an angle proportional to each pixel's intensity. FRQI is compact, but intensities can only be recovered statistically from repeated measurements. Zhang et al. [8] proposed NEQR, which stores each intensity as a q-bit binary code; it allows exact read-out but needs q colour qubits and many multi-controlled NOT gates. Neither paper evaluated the encodings on the classification of real textured images.");
H2("Quantum Kernels and Their Limitations");
P("Havlíček et al. [2] and Schuld and Killoran [9] showed that a circuit that maps data to a quantum state defines a kernel, which a classical support vector machine (SVM) [10] can use. Schuld [14] later argued that most supervised quantum models are, in fact, kernel methods. These demonstrations used small synthetic data designed for the chosen feature map. Huang et al. [13] showed that classical learners given the same data can often match quantum kernels, and Thanasilp et al. [12] proved that kernel values on large registers concentrate exponentially, making them hard to estimate. The swap test of Buhrman et al. [19] measures the overlap Tr(ρσ) of two states, pure or mixed, and is the standard way to estimate such kernels on hardware.");
H2("Variational and Hybrid Quantum Models");
P("Variational quantum algorithms [15] train parameterised circuits with a classical optimiser, but they suffer from barren plateaus in which gradients vanish as circuits grow [16]. Henderson et al. [11] applied small random circuits to image patches (quanvolution) and found performance similar to classical networks with random non-linear layers. Mari et al. [30] combined pre-trained classical networks with small quantum circuits (transfer learning), the same idea used in our hybrid V2 models with MobileNetV3 [26] features.");
H2("Steel Surface Defect Recognition");
P("Song and Yan [5] published the NEU surface defect database and classified it with noise-robust completed local binary patterns. He et al. [6] added bounding-box annotations (NEU-DET) and an end-to-end convolutional detector. Classical texture descriptors such as LBP [17] and GLCM [18] remain strong baselines because they measure how often local intensity patterns occur regardless of their position, which is also the idea behind our patch-ensemble kernel.");
H2("Evaluation Methodology");
P("Comparing several models on one test set requires care. McNemar's test [23] compares two classifiers on the same test images, the bootstrap [22] gives confidence intervals for accuracy differences, and Holm's method [21] controls the error rate when several hypotheses are tested together. Image reconstruction quality is measured with the mean squared error (MSE) and the structural similarity index (SSIM) [25].");
H2("Comparison");
P("Table 2.1 compares eight key papers on problem, method, data, key result and limitation, and states how each one is used in this project.");
table("Comparison of key related work", ["Paper", "Method", "Data", "Key result", "Limitation", "Use in this project"], [
  ["Le et al. [7]", "FRQI angle encoding", "Illustrative images", "Compact log₂N+1-qubit encoding", "Statistical read-out; no classification", "Encoding used in our kernel"],
  ["Zhang et al. [8]", "NEQR basis encoding", "Illustrative images", "Exact intensity retrieval", "q colour qubits; costly gates", "Second encoding compared"],
  ["Havlíček et al. [2]", "Quantum kernel and VQC on hardware", "Synthetic 2-D data", "High accuracy on data built for the map", "Toy data; no real images", "Kernel framework adopted"],
  ["Schuld & Killoran [9]", "Feature Hilbert-space view", "Small demos", "Encodings define SVM kernels", "No large evaluation", "Theoretical basis"],
  ["Huang et al. [13]", "Classical vs quantum kernels", "Engineered labels", "Classical models often match", "Advantage only on special tasks", "Motivates matched control"],
  ["Thanasilp et al. [12]", "Kernel concentration analysis", "Theory, numerics", "Values concentrate on large registers", "Generic encodings", "Motivates small patch registers"],
  ["Henderson et al. [11]", "Quanvolution on patches", "MNIST", "Similar to random-feature layers", "Small digits; no advantage", "Patch-wise quantum processing"],
  ["Song & Yan [5]", "Completed LBP features", "NEU (6 classes)", "High accuracy, robust to noise", "Classical, hand-crafted", "Data set and texture baseline"],
], [1.3, 1.5, 1.1, 1.6, 1.5, 1.5], { size: 17 });
H2("Research Gap");
P("Three gaps follow from the literature. First, FRQI and NEQR have rarely been tested as classifiers on real textured images. Second, quantum kernel studies seldom include a classical model that receives exactly the same input, so it is unclear how much of a result is due to the quantum encoding. Third, model selection and testing are often done on the same data, which makes small differences unreliable. This project addresses all three on a real industrial data set.");
H2("Objectives of Project");
P("The objectives below follow directly from the research gap. Each one was implemented, and Table 2.2 shows where it is implemented and where the evidence is reported.");
numbered([
  "**O1.** Build a reproducible pipeline that encodes NEU-DET images with real FRQI and NEQR circuits and classifies them with quantum kernels.",
  "**O2.** Establish a leakage-controlled protocol: fixed hashed splits, validation-only selection, a SHA-256 freeze and a single locked-test evaluation per model.",
  "**O3.** Find out why whole-image FRQI and NEQR kernels perform poorly and design a method that overcomes the weakness (patch-ensemble mixed-state kernel).",
  "**O4.** Measure whether any gain is due to the quantum encoding by comparing with a classical model on the same input and with the best classical model.",
  "**O5.** Quantify how well FRQI and NEQR states preserve images by reconstructing all 1,800 images from measured states.",
  "**O6.** Provide an interactive dashboard that shows all results and explains the method visually on real images.",
]);
table("Objectives, implementation and evidence", ["Objective", "Implementation", "Evidence in this report"], [
  ["O1", "src/frqi, src/neqr encoders; src/v4/models.py", "Chapter 4 (algorithms), Figure 4.7"],
  ["O2", "src/v2/runner.py, scripts/v4/run_v4.py, verify_v4.py", "Section 4.10, Table 5.10 (17/17 checks pass)"],
  ["O3", "Patch-ensemble kernel (V4)", "Tables 5.4–5.6, Figures 5.2–5.4"],
  ["O4", "Classical patch-moment RBF-SVM; V3 texture SVM", "Table 5.5 (p = 0.060 vs. same-patch control)"],
  ["O5", "scripts/v4/reconstruct_all.py (20 methods)", "Section 5.7, Figures 5.10–5.15"],
  ["O6", "FastAPI back end + React front end", "Section 4.11, Figures 4.9–4.26"],
], [1.0, 3.6, 3.4]);

// ═════════════════════════ CHAPTER 3 ═════════════════════════
chapter("Exploratory Data Analysis"); resetSec();
H2("Dataset");
P("The project uses the NEU-DET steel surface defect data set [5], [6]. It contains 1,800 images of hot-rolled steel strips in six defect classes: crazing, inclusion, patches, pitted surface, rolled-in scale and scratches, with 300 images per class. All images are 200 × 200 pixels; they are stored as RGB JPEG files but contain grayscale content, so they are converted to a single grayscale channel. The data set is distributed in two folders, *train* (1,440 images) and *validation* (360 images), each with an images and an annotations sub-folder. The annotations contain bounding boxes, which this project does not use; only the class label of each image is needed.");
table("Summary of the NEU-DET data set", ["Property", "Value"], [
  ["Source", "NEU surface defect database (Song & Yan [5]; NEU-DET annotations, He et al. [6])"],
  ["Number of images", "1,800 (300 per class)"],
  ["Classes", "crazing, inclusion, patches, pitted surface, rolled-in scale, scratches"],
  ["Image size and format", `${EDA.sizes.map((s) => s.join(" × ")).join(", ")} pixels; stored as ${EDA.modes.join(", ")} JPEG, grayscale content`],
  ["Folders", "train (240 per class), validation (60 per class)"],
  ["Use in this project", "train folder → training and validation splits; validation folder → locked test set"],
], [2.2, 6.0]);
P("**Data pipeline.** Instead of scraping, the images are read from the local NEU-DET folders. A manifest is built once: for every image it stores the relative path, class, folder, index, size and a SHA-256 hash of the file. Every later stage reads the manifest and checks the hashes, so a changed or missing file is detected immediately. The 1,440 train-folder images are split into 1,080 training and 360 validation images with a group-blocked split (blocks of 20 consecutive file indices, three validation blocks per class), so that near-duplicate neighbouring images do not end up in both sets. The split is repeated with three seeds (0, 1, 2). The 360 validation-folder images form the locked test set, which is read only after a model has been frozen. Table 3.2 shows the resulting counts.");
table("Splits per class (identical for seeds 0, 1 and 2)", ["Class", "Train", "Validation", "Locked test", "Total"], [
  ...["crazing", "inclusion", "patches", "pitted surface", "rolled-in scale", "scratches"].map((c) => [c, "180", "60", "60", "300"]),
  ["**All classes**", "**1,080**", "**360**", "**360**", "**1,800**"],
], [2.6, 1.3, 1.3, 1.4, 1.2]);
P("Figure 3.1 shows six unmodified training images of each class. The classes are defined by texture rather than by a fixed shape: crazing is a fine network of cracks, inclusions are dark streaks, patches are large dark regions, pitted surfaces show small pits, rolled-in scale shows scattered dark flakes, and scratches are thin bright lines.");
figure(PK + "Fig16_dataset_samples.png", "Six unmodified training images (200 × 200, grayscale) of each NEU-DET defect class.", 6.0);
H2("Exploratory Data Analysis and Visualizations");
P("Figure 3.2 shows the class distribution. The data set is perfectly balanced: every class has 240 images in the train folder and 60 in the validation folder. Accuracy is therefore a meaningful headline metric, and no class re-weighting is needed.");
figure(RF + "E1_class_distribution.png", "Number of images per class in the train folder (used for training and validation) and the validation folder (used as the locked test set).", 5.6);
P("Figure 3.3 compares the mean brightness and the contrast (standard deviation of intensity) of every image, separately for the two folders, and Table 3.3 lists the class means. Brightness varies strongly between images of the same class, which is one reason why a comparison of raw pixel values at fixed positions performs poorly. The most important finding is a clear **brightness shift between the folders for rolled-in scale**: its training images have a mean intensity of " + f3(B.train["rolled-in_scale"][0]) + ", but its test images only " + f3(B.validation["rolled-in_scale"][0]) + ". Crazing images are brighter in the test folder (" + f3(B.validation.crazing[0]) + " vs. " + f3(B.train.crazing[0]) + "). This shift later explains why the NEQR model, which was selected without contrast stretch, misclassifies rolled-in scale on one seed, while FRQI with per-image contrast stretch is not affected (Section 5.6).");
figure(RF + "E2_brightness_contrast.png", "Mean intensity (left) and contrast (right) of every image, per class, for the train folder and the validation folder (locked test).", 6.3);
table("Mean intensity and contrast per class (mean over images, 0 = black, 1 = white)", ["Class", "Brightness, train folder", "Brightness, test folder", "Contrast, train folder", "Contrast, test folder"],
  ["crazing", "inclusion", "patches", "pitted_surface", "rolled-in_scale", "scratches"].map((c) => [c.replace("_", " "), f3(B.train[c][0]), f3(B.validation[c][0]), f3(C.train[c][0]), f3(C.validation[c][0])]),
  [2.2, 1.6, 1.6, 1.6, 1.6]);
P("Figure 3.4 shows the full intensity histograms. Patches and pitted surface use almost the whole intensity range, including saturated white pixels, while inclusion and rolled-in scale occupy a narrow band. The rolled-in scale histogram of the test folder is shifted far to the left of the training histogram, confirming the shift seen in Table 3.3.");
figure(RF + "E3_intensity_histograms.png", "Pixel-intensity histograms per class for the train folder and the validation folder (locked test).", 6.3);
P("Figure 3.5 shows the average of all 300 images of each class. The averages are almost uniform: defects appear at different positions in different images, so they cancel out when the images are averaged. Only the overall brightness and a weak vertical structure remain. This confirms that position carries little class information and that a useful representation must be **position-independent**.");
figure(RF + "E4_class_average_images.png", "Average image of each class (mean of all 300 images).", 6.3);
H2("Feature Engineering and Preprocessing");
P("Different versions of the project used different input representations, summarised in Table 3.4. In all of them, an image is converted to grayscale, resized and scaled to [0, 1]. V4 adds an optional per-image contrast stretch and the patch extraction that the patch-ensemble kernel needs.");
table("Input representations used in the different protocols", ["Protocol", "Representation", "Dimension"], [
  ["V2", "Raw pixels (8×8 or 16×16) encoded with whole-image FRQI / NEQR", "64 or 256 pixels (7–16 qubits)"],
  ["V2", "PCA of 64×64 pixels; MobileNetV3 CNN features [26] → PCA", "8 features"],
  ["V3", "Texture features (LBP [17] + GLCM [18]) → PCA; MobileNetV3 → PCA", "8 or 12 features"],
  ["V4", "64×64 or 128×128 image → p×p patches → FRQI/NEQR patch states → mixed state ρ", "ρ of size 32×32 to 256×256"],
  ["V4 control", "Same patches → mean patch vector + mean outer product (classical)", "patch moments"],
], [1.1, 5.0, 2.2]);
P("Figure 3.6 shows the V4 preprocessing for one training image of each class: the original image, the resized 64 × 64 image, the contrast-stretched image, the 8 × 8 patch grid and the resulting 128 × 128 mixed state ρ. The contrast stretch makes dark and bright images comparable, and the block pattern of ρ differs visibly between classes.");
figure(PK + "Fig17_preprocessing_and_mixed_state.png", "One training image per class before and after each V4 preprocessing step: (a) original, (b) resized to 64 × 64, (c) contrast stretch, (d) 8 × 8 patch grid (the model uses stride 4, i.e. 225 overlapping patches), (e) mixed state ρ.", 5.6);
P("Figure 3.7 shows why whole-image encodings were limited. A whole image must be downsampled to fit a register of 3–9 qubits, and at 8 × 8 pixels or below the cracks, pits and thin scratches that define the classes disappear. Patch encoding avoids this loss because each small register only has to hold one patch.");
figure(PK + "Fig20_resolution_whole_image.png", "One training image per class at the resolutions available to whole-image FRQI encodings (exact statevector reconstruction; 3–9 qubits).", 5.8);

// ═════════════════════════ CHAPTER 4 ═════════════════════════
chapter("Methodology"); resetSec();
P("This chapter describes the software system and the algorithms. Figure 4.1 shows the overall architecture: a data module, preprocessing, the quantum encoder, the mixed-state and kernel modules, the SVM classifier, and supporting modules for evaluation, reconstruction and the dashboard.");
figure(RF + "A1_architecture.png", "System architecture. Solid arrows show the classification path for one image; dashed arrows show modules that reuse its outputs. Orange blocks contain the quantum part, which is simulated exactly on a CPU.", 6.0);
H2("Introduction to Languages (Front End and Back End)");
P("**Back end: Python 3.11.** Python was chosen because the quantum (Qiskit), machine-learning (scikit-learn, PyTorch) and scientific (NumPy, SciPy) libraries are all Python-based. The back end is a **FastAPI** application (api_main.py) served by Uvicorn. It exposes read-only REST endpoints under /api/v2, /api/v3 and /api/v4 that read the saved result files; it never trains or selects models.");
P("**Front end: TypeScript with React.** The dashboard is a single-page application written in TypeScript with **React 19**, built with **Vite** and styled with **Tailwind CSS**. Charts use Recharts and custom SVG, and the pages are organised with React Router. TypeScript's static types catch interface mismatches between the API and the pages at compile time. Table 4.1 summarises the languages and frameworks.");
table("Languages and frameworks", ["Layer", "Language / framework", "Purpose"], [
  ["Back end", "Python 3.11, FastAPI 0.142, Uvicorn 0.54", "REST API that serves saved results and the live walkthrough"],
  ["Quantum layer", "Qiskit 2.5.2, Qiskit Aer 0.17.2 [20]", "FRQI/NEQR circuits, statevector simulation, shot sampling"],
  ["Machine learning", "scikit-learn 1.9.1 [27], PyTorch 2.15 [24], torchvision 0.29", "SVMs, PCA, logistic regression, CNN feature extraction"],
  ["Front end", "TypeScript 6.0, React 19.2, React Router 7.18", "Interactive dashboard pages"],
  ["Build and style", "Vite 8.3, Tailwind CSS 3.4", "Fast development server and production build; styling"],
], [1.6, 3.2, 3.4]);
H2("Supporting Languages and Packages");
table("Supporting packages and tools", ["Package", "Version", "Used for"], [
  ["NumPy", "2.4.6", "Arrays, density matrices, kernel computation [29]"],
  ["SciPy", "1.17.1", "Statistics helpers"],
  ["pandas", "3.0.6", "Reading predictions and result tables"],
  ["Matplotlib", "3.11.2", "All figures in the paper and this report [28]"],
  ["Pillow", "12.3.0", "Image loading and resizing"],
  ["joblib", "—", "Saving trained models (checkpoints)"],
  ["Recharts", "3.10", "Dashboard charts"],
  ["lucide-react", "1.52", "Dashboard icons"],
  ["pytest", "—", "179 back-end unit and API test functions"],
  ["Vitest + Testing Library", "5.1 / 16.3", "27 front-end tests"],
  ["Playwright", "1.65", "Browser end-to-end checks and screenshots"],
], [2.4, 1.4, 4.4]);
H2("User Characteristics");
table("User groups and their characteristics", ["User", "Background", "Main use of the system"], [
  ["Researcher / student", "Python, machine learning, basic quantum computing", "Runs experiment scripts, inspects results, exports figures"],
  ["Reviewer / supervisor", "Domain or ML expertise; may not run code", "Checks numbers, protocol and statistics in the dashboard and reports"],
  ["Visitor / learner", "No quantum background required", "Uses the live walkthrough and playground to understand FRQI/NEQR"],
], [2.0, 3.0, 3.2]);
H2("Constraints");
bullets([
  "**No quantum hardware:** all circuits are simulated exactly on a CPU; finite-shot effects are simulated only for reconstruction.",
  "**Register size:** V4 registers are limited to at most 8 qubits so that exact simulation of 864 runs is feasible.",
  "**Single locked test set:** each frozen model may be evaluated on the test set only once; no re-tuning after testing.",
  "**Hardware:** one laptop CPU (Apple M5, 16 GB RAM); no GPU.",
  "**Data:** one public data set (NEU-DET) with 1,800 images.",
  "**Immutability:** results of earlier protocols (V0, V2, V3) must never be modified; checks enforce this.",
]);
H2("Use Case Model, Flow Chart and Data Flow Diagrams");
P("Figure 4.2 shows the use case model. The researcher runs experiments and reconstructions and explores the results; the reviewer inspects and verifies results; and the experiment scripts act as a system actor that performs selection, freezing and the locked-test evaluation.");
figure(RF + "D1_use_case_diagram.png", "Use case diagram of the Q-ImageLab system.", 5.6);
P("Figure 4.3 is the flow chart of the experiment pipeline. The decision node is the key safeguard: if any selection file changes after the freeze, the test stage aborts.");
figure(RF + "D3_pipeline_flowchart.png", "Flow chart of the leakage-controlled experiment pipeline.", 3.9);
P("Figure 4.4 shows the data flow diagrams. At level 0, the system takes images and labels from the NEU-DET folders, writes metrics and predictions to the result store, and serves dashboards and figures to the user. Level 1 shows the eight internal processes from loading the manifest to the dashboard.");
figure(RF + "D2_data_flow_diagrams.png", "Data flow diagrams: (a) level 0 (context diagram), (b) level 1.", 6.0);
P("Figure 4.5 gives the step-by-step workflow used in the paper: panel (a) is the data protocol, and panel (b) follows one image through the patch-ensemble kernel.");
figure(PK + "Fig01_methodology_flowchart.png", "Workflow: (a) leakage-controlled protocol; (b) patch-ensemble mixed-state kernel for one image.", 6.2);
H2("Database Design");
P("The project does not use a relational database. All results are stored as **versioned files** in a folder per protocol (results/qml_v2, results/qml_v3, results/qml_v4). This design was chosen because results are written once and then only read, files are easy to hash, version and inspect, and no database server is needed. The FastAPI back end reads these files and caches them in memory. Logically, the files form the entities shown in the ER diagram of Section 4.8.");
H2("Table Structure");
P("The most important file structures are listed in Tables 4.4 to 4.7.");
table("Manifest record (one per image, results/qml_v*/manifests)", ["Field", "Type", "Description"], [
  ["rel_path", "string (key)", "Path relative to the NEU-DET root, e.g. train/images/crazing/crazing_1.jpg"],
  ["class, class_idx", "string, int", "Defect class name and index 0–5"],
  ["folder, role", "string", "train / validation folder; trainval or locked_test role"],
  ["index, block, group_id", "int, int, string", "File index and its block for the group-blocked split"],
  ["width, height, mode", "int, int, string", "Image size (200 × 200) and colour mode"],
  ["sha256, file_size", "string, int", "Hash and size used to detect any change to the file"],
], [2.2, 1.6, 4.4]);
table("Files in one experiment folder (experiments/<experiment_id>)", ["File", "Content"], [
  ["config.json", "Group, configuration key, all hyper-parameters, seed"],
  ["metadata.json, status.json", "Timing, versions, completed/failed status"],
  ["validation_metrics.json", "Accuracy, macro-F1, per-class metrics on the validation split"],
  ["test_metrics.json", "Same metrics on the locked test set (only for frozen configurations)"],
  ["predictions.csv", "One row per image: split, image, y_true, y_pred, classes"],
  ["confusion_matrix.json", "Validation and test confusion matrices"],
  ["circuit_stats.json", "Qubits, gate counts and depth of the encoder circuit (quantum models)"],
  ["model/estimator.joblib", "Saved trained model used by the single test evaluation"],
], [2.6, 5.6]);
table("Columns of predictions.csv", ["Column", "Description"], [
  ["split", "val or test"], ["image", "Relative image path (foreign key to the manifest)"], ["y_true, y_pred", "True and predicted class index"],
  ["true_class, pred_class", "Class names"], ["confidence", "Optional score (empty for SVMs without probabilities)"],
], [2.6, 5.6]);
table("Selection file (aggregates/selection/<group>.json)", ["Field", "Description"], [
  ["group", "Model group, e.g. V4-frqi-p8"], ["criterion", "Selection rule: maximum mean validation macro-F1 over seeds; test not consulted"],
  ["candidates", "Every configuration with its validation mean and standard deviation"], ["selected", "The chosen configuration and its experiment ids"],
  ["(freeze file)", "SHA-256 hash of all selection files, checked before every test access"],
], [2.6, 5.6]);
H2("ER Diagram");
P("Figure 4.6 shows the logical entities and their relationships. An IMAGE belongs to SPLITs; a CONFIGURATION is trained in one EXPERIMENT_RUN per seed; each run produces PREDICTIONs for images; and a SELECTION chooses one configuration per group.");
figure(RF + "D4_er_diagram.png", "Entity–relationship diagram of the file-based result store.", 6.0);
H2("Assumptions and Dependencies");
bullets([
  "Each NEU-DET image contains exactly one defect class; the folder structure gives the label.",
  "The official train/validation folder split is used, and the validation folder serves as the locked test set.",
  "Exact statevector simulation is a faithful model of the ideal circuits; noise is not modelled.",
  "The project depends on Qiskit, Qiskit Aer, scikit-learn, NumPy, PyTorch (for CNN features), FastAPI and React; versions are pinned in requirements.txt and package.json.",
  "The dashboard depends on the result folders being present; it shows explicit empty or error states otherwise.",
]);
H2("Algorithm Discussion");
H3("FRQI encoding");
P("For a patch of N = 2ⁿ × 2ⁿ pixels with intensities xᵢ in [0, 1], FRQI uses 2n position qubits and one colour qubit, as in Equation (4.1), where b is an angle-scale parameter (b = 1 is the original definition [7]).");
equation(RF + "Q1_frqi.png");
H3("NEQR encoding");
P("NEQR stores the quantised intensity cᵢ in q colour qubits (Equation (4.2)). It needs 2n + q qubits, and its read-out is exact up to quantisation.");
equation(RF + "Q2_neqr.png");
H3("Whole-image fidelity kernel (V2/V3)");
P("Earlier protocols compared two whole images by the fidelity kernel in Equation (4.3). For FRQI, the overlap is the average of cos(θᵢᴬ − θᵢᴮ) over the *same* pixel index i, so the kernel compares pixels only at identical positions. A defect shifted by a few pixels gives an almost unrelated state, which explains the poor accuracy of these kernels.");
equation(RF + "Q7_fidelity.png");
H3("Patch-ensemble mixed-state kernel (V4)");
P("After the optional contrast stretch (Equation (4.4)), the image is cut into P patches of size p × p with stride s. Each patch is encoded with FRQI or NEQR, and the image is represented by the uniform mixture of its patch states (Equation (4.5)). Two images are compared with the Hilbert–Schmidt inner product (Equation (4.6)), which is the average squared overlap over all pairs of patches. A texture element that occurs in both images therefore contributes regardless of its position.");
equation(RF + "Q6_stretch.png");
equation(RF + "Q3_rho.png");
equation(RF + "Q4_kernel.png");
P("By Equation (4.7), a swap test [19] between two states measures exactly this overlap, so on a quantum device the kernel could be estimated by swap tests between randomly drawn patch states of the two images, using only two patch registers and one ancilla qubit. In this project no swap test was executed: ρ was computed exactly from the statevectors. Because patches are small, the registers have only 5–8 qubits, independent of the image size.");
equation(RF + "Q5_swap.png");
P("Figure 4.7 illustrates the method on a real training image, and Figure 4.8 and Table 4.8 give the circuit resources of one patch state.");
figure(PK + "Fig02_patch_encoding_illustration.png", "The patch-ensemble method on a real NEU-DET training image (frozen FRQI settings: 64 × 64, 8 × 8 patches, stride 4): (a) image and patches, (b) one patch, (c) its 7-qubit FRQI amplitudes, (d) the mixed state ρ, (e) normalised kernel between classes.", 6.2);
figure(PK + "Fig10_circuit_resources.png", "Encoder circuit resources for one patch state after transpilation (qubits, gates, depth, CX gates).", 6.0);
table("Encoder circuit resources for one patch state (Qiskit, transpiled to {cx, rz, sx, x})", ["Group", "Qubits", "Compiled gates", "Compiled depth", "CX gates", "Patches per image"], [
  ["FRQI patches 4×4", "5", "1,070", "710", "384", "256"], ["FRQI patches 8×8", "7", "8,339", "4,878", "3,584", "225"],
  ["NEQR patches 2×2", "6", "150", "99", "55", "1,024"], ["NEQR patches 4×4", "8", "1,998", "1,634", "694", "1,024"],
], [2.2, 1, 1.4, 1.4, 1.2, 1.4]);
H3("Classifiers");
P("All kernel models use a multi-class SVM [10] with a precomputed kernel (scikit-learn [27], one-versus-one). V2 and V3 also included variational quantum classifiers (VQCs) [15], hybrid models with frozen MobileNetV3 features [26], [30], and classical baselines (RBF-SVM, logistic regression). The V4 classical control uses exactly the same patches but describes an image by the mean patch vector and the mean outer product of raw patch intensities (the classical analogue of ρ without the quantum feature map), classified with an RBF-SVM.");
H3("Selection, freezing and statistics");
P("The protocol of every version follows the same steps:");
numbered([
  "Train every configuration of the grid with seeds 0, 1 and 2 on the training split and score it on the validation split.",
  "Within each model group, select the configuration with the highest mean validation macro-F1 (Equation (4.8)).",
  "Write the selection files and store their SHA-256 hashes (freeze).",
  "Check the hashes, then evaluate each saved frozen model once on the locked test set and log every access.",
  "Run the pre-declared comparisons: a paired sign-flip permutation test (10,000 permutations), a paired bootstrap 95% confidence interval [22], McNemar's test per seed [23] and Holm correction over all comparisons [21].",
], "num2");
equation(RF + "Q8_f1.png");
H2("Implementation of Algorithm with Screenshots and Figures");
P("The implementation consists of the experiment code (src/ and scripts/), the result folders (results/), the API (api_main.py) and the dashboard (frontend/). Table 4.9 lists the repository structure, and Table 4.10 the most important API endpoints. The following figures show the main dashboard pages; every number on them is read from the saved result files.");
table("Repository structure", ["Path", "Content"], [
  ["src/frqi, src/neqr, src/reconstruction", "FRQI/NEQR encoders and the decoder"], ["src/v2", "Data set, manifest, runner, quantum kernels, VQC, CNN features, API"],
  ["src/v3, src/v4", "Texture features and V3 models; patch-ensemble models and V4 API"], ["scripts/v4", "V4 stages: setup, run, select, freeze, test, analyse, verify, reconstruct"],
  ["results/qml_v2 … qml_v4", "Manifests, experiment folders, aggregates, reports"], ["frontend/src", "React pages (v2/pages), API client, charts"],
  ["tests/", "Back-end unit and API tests (pytest)"], ["research_paper_visuals/", "Figure and table generators, paper pack, this report's figures"],
], [3.0, 5.2]);
table("Main REST API endpoints", ["Endpoint", "Returns"], [
  ["GET /api/v2/summary, /api/v2/models", "V2 overview, all 88 selected models with metrics"], ["GET /api/v2/experiments/{id}", "One experiment with its configuration and metrics"],
  ["GET /api/v3/results", "V3 groups, headlines and comparisons"], ["GET /api/v4/results", "V4 groups, frozen selection hash and the 8 comparisons"],
  ["GET /api/v4/versions", "Headline numbers of every protocol for the home page"], ["GET /api/v4/pipeline?image=…", "Live, read-only walkthrough of the frozen FRQI model on one test image"],
  ["GET /api/v4/images, /api/v4/image-models", "Test images and the saved predictions of all 163 models for one image"], ["GET /api/v4/reconstruction/summary, /image", "Reconstruction metrics and images for all 1,800 images"],
], [3.6, 4.6]);
figure(SS + "S02_home_versions_chart.jpg", "Home page, lower part: FRQI and NEQR accuracy in every version (V4 outlined) and one card per version.");
figure(SS + "S03_v4_results.jpg", "V4 results page: headline tiles, the eight pre-declared comparisons with Holm-corrected p-values, and every V4 group.");
P("The **How it works** page replays the frozen V4 FRQI model on any locked-test image in nine animated steps (Figures 4.11 to 4.17). Each step is computed live by the back end from the real image and the saved model, and the final prediction is checked against the prediction saved during the single test evaluation.");
figure(SS + "S06_howitworks_step1.jpg", "How it works, step 1: choosing a real locked-test image; each image shows the percentage of the project's 163 models that classify it correctly.");
figure(SS + "S07_howitworks_encode.jpg", "How it works: encoding one 8 × 8 patch as a 7-qubit FRQI state, with the computed angle and amplitudes for each pixel.");
figure(SS + "S08_howitworks_mixed_state.jpg", "How it works: the 225 patch states are mixed into one 128 × 128 density matrix ρ.");
figure(SS + "S09_howitworks_kernel.jpg", "How it works: comparing the image with training images through the swap-test kernel Tr(ρA ρB).");
figure(SS + "S10_howitworks_svm_verdict.jpg", "How it works: the SVM decision scores; the live prediction is identical to the saved locked-test prediction.");
figure(SS + "S11_howitworks_measurement.jpg", "How it works: what finite measurement shots do to the encoded image (real shot reconstructions).");
figure(SS + "S12_howitworks_all_models.jpg", "How it works, final step: the saved predictions of every selected model in the project (163 models × 3 seeds) for the same image.");
figure(SS + "S04_reconstruction_full.jpg", "Reconstruction page: metrics of all 20 methods over all 1,800 images and error-versus-shots charts.");
figure(SS + "S05_reconstruction_browser.jpg", "Reconstruction browser: any image and any method, with the exact statevector and shot-based reconstructions side by side.");
figure(SS + "S13_v3_results.jpg", "V3 results page (texture features into quantum kernels and VQCs).");
figure(SS + "S14_v2_overview.jpg", "V2 overview page with the best model of each family on the locked test set.");
figure(SS + "S15_model_comparison.jpg", "Model comparison page: all 88 V2 models with filters and family charts.");
figure(SS + "S16_encoding_page.jpg", "Quantum image encoding page explaining FRQI and NEQR and their measured costs.");
figure(SS + "S17_circuits_page.jpg", "Quantum circuits page: the exact simulated circuits with gate counts and depth.");
figure(SS + "S19_playground.jpg", "3 × 3 algorithm playground (illustrative demo): every step of FRQI, NEQR and classical pipelines on a tiny image.");
figure(SS + "S20_historical_v0.jpg", "Historical V0 page: the first prototype's results, kept read-only and marked as not comparable.");

// ═════════════════════════ CHAPTER 5 ═════════════════════════
chapter("Results"); resetSec();
H2("Results Across All Versions");
P("Table 5.1 summarises each protocol and its headline numbers, and Figure 5.1 places the key models of all versions on one chart. V2, V3 and V4 use the same data set manifest, splits, seeds and 360-image locked test set, so their numbers are directly comparable; V0 is not.");
table("Summary of all protocols", ["Protocol", "What was tested", "Scale", "Headline result (locked test)"], [
  ["V0", "First FRQI/NEQR prototype", "≈ 42 train / 12–16 test images per run", "Not comparable (no locked test)"],
  ["V2", "Whole-image FRQI/NEQR, PCA and CNN features, VQC, hybrids, classical", "88 models, 2,583 runs", "FRQI 60.6%, NEQR 60.2%; best overall 96.4% (CNN + logistic regression)"],
  ["V3", "Texture and CNN features into quantum kernels and VQCs", "70 groups, 5,316 runs", "Quantum kernel on texture PCA-12: 95.3%; classical texture SVM 95.6%"],
  ["V4", "Patch-ensemble mixed-state FRQI/NEQR kernels", "5 groups, 288 configs, 864 runs", "**FRQI 87.8 ± 1.5%**, **NEQR 82.7 ± 10.1%**"],
], [1.0, 3.0, 2.0, 3.0]);
figure(PK + "Fig15_cross_protocol_overview.png", "Key models of protocols V2, V3 and V4 on the same locked test set (mean ± s.d. over three seeds).", 6.2);
H2("Protocol V2 Results");
P("Table 5.2 lists the best model of each family in V2. Frozen CNN features with a classical classifier were best (96.4%). Hybrid models that feed CNN features into a quantum kernel reached 93.2%. All models that worked on raw pixels, including the whole-image FRQI and NEQR kernels, stayed between 48% and 65%, which shows that the pixel representation, not only the classifier, limited them.");
table("Best model of each V2 family (locked test accuracy, mean ± s.d. over 3 seeds)", ["Family", "Models", "Best model", "Test accuracy %"], [
  ["CNN models (classical)", "9", "Frozen MobileNetV3 + logistic regression", "96.4 ± 1.1"], ["Hybrid quantum-classical", "12", "MobileNetV3 features → PCA 8 + QKC product-RY", "93.2 ± 1.1"],
  ["Classical ML on pixels", "9", "Pixels 64×64 → PCA 8 + RBF-SVM", "64.8 ± 3.3"], ["Quantum kernel classifiers", "9", "QKC ZZ-full, 8 qubits", "64.0 ± 3.5"],
  ["FRQI / NEQR kernels", "19", "FRQI kernel 8×8, angle ×2", "60.6 ± 1.2"], ["Variational quantum classifiers", "3", "VQC, 8 qubits, 3 layers, re-upload", "48.1 ± 1.9"],
], [2.4, 0.9, 3.4, 1.5]);
H2("Protocol V3 Results");
P("V3 replaced pixels with texture features. Table 5.3 shows that quantum kernels on 12 texture principal components reached 95.3%, statistically close to the classical texture SVM (95.6%). VQCs remained weaker (73.4%), and re-tuned whole-image FRQI and NEQR kernels did not improve (57.5% and 60.2%). V3 therefore showed that quantum kernels work well *on good classical features*, but it left the question of FRQI and NEQR open.");
table("Selected V3 results (locked test accuracy, mean ± s.d.)", ["Model", "Type", "Test accuracy %"], [
  ["Texture PCA-12 + RBF-SVM", "classical", "95.6 ± 2.2"], ["Texture PCA-12 + QKC product-RY", "quantum kernel", "95.3 ± 3.2"],
  ["Texture PCA-8 + QKC ZZ-full", "quantum kernel", "93.0 ± 3.0"], ["MobileNetV3 PCA-8 + QKC product-RY", "hybrid", "91.3 ± 0.8"],
  ["Texture PCA-8 + VQC (2 layers)", "variational", "73.4 ± 3.8"], ["NEQR 16×16, 4-bit, fidelity kernel", "quantum encoding", "60.2 ± 0.4"],
  ["FRQI 8×8, angle ×2, fidelity kernel", "quantum encoding", "57.5 ± 2.1"],
], [4.0, 2.0, 2.0]);
H2("Protocol V4 Results (Final)");
P("Table 5.4 gives the locked-test results of V4 together with the baselines. The FRQI patch-ensemble model with 8 × 8 patches reaches **87.8 ± 1.5%** test accuracy (macro-F1 87.5 ± 1.6%), and the NEQR model with 4 × 4 patches **82.7 ± 10.1%**. Validation and test scores are close for FRQI (88.0 vs. 87.5 macro-F1), which shows that its selection did not overfit the validation split. Figure 5.2 shows the jump of both encodings from about 60% in V2 and V3 to more than 80% in V4, and Figure 5.3 compares all V4 groups with the controls.");
table("V4 locked-test results, mean ± s.d. over three seeds (best value per column in bold)", ["Model", "Type", "Val. F1 %", "Test acc. %", "Test F1 %"], [
  ["**Proposed: FRQI, 8×8 patches**", "quantum (sim.)", "88.0", "87.8 ± 1.5", "87.5 ± 1.6"], ["**Proposed: NEQR, 4×4 patches**", "quantum (sim.)", "89.2", "82.7 ± 10.1", "80.4 ± 13.5"],
  ["FRQI, 4×4 patches", "quantum (sim.)", "85.7", "85.3 ± 1.7", "85.0 ± 1.6"], ["NEQR, 2×2 patches", "quantum (sim.)", "88.2", "81.5 ± 10.6", "79.2 ± 14.1"],
  ["Whole-image FRQI (V2)", "quantum (sim.)", "69.3", "60.6 ± 1.2", "58.3 ± 1.3"], ["Whole-image NEQR (V2)", "quantum (sim.)", "72.7", "60.2 ± 0.4", "56.5 ± 0.4"],
  ["Whole-image FRQI, re-tuned (V3)", "quantum (sim.)", "69.4", "57.5 ± 2.1", "55.3 ± 2.4"], ["Classical RBF-SVM, same patches", "classical", "83.8", "83.6 ± 0.3", "83.3 ± 0.3"],
  ["Classical texture RBF-SVM (V3)", "classical", "**95.3**", "**95.6 ± 2.2**", "**95.5 ± 2.2**"],
], [3.2, 1.6, 1.1, 1.4, 1.4]);
figure(PK + "Fig04_frqi_neqr_across_protocols.png", "Locked-test accuracy of FRQI and NEQR models across protocols V2, V3 and V4 (bars: mean; error bars: s.d.; dots: seeds; lines: classical references).", 5.6);
figure(PK + "Fig03_main_results.png", "V4 main results: test accuracy of every V4 group with the classical controls.", 6.0);
P("Table 5.5 and Figure 5.4 give the eight pre-declared paired comparisons. The gains over the whole-image kernels (+27.1, +30.3 and +22.5 percentage points) are significant after Holm correction (p < 0.001), and FRQI is significantly better than NEQR (+5.1 pp, p = 0.045). However, FRQI is **not** significantly better than the classical SVM on the same patches (+4.2 pp, p = 0.060), and the classical texture SVM remains clearly better than both quantum models. The improvement therefore comes mainly from the patch representation, which classical models can exploit too; it is not evidence of a quantum advantage.");
table("Pre-declared paired comparisons (Holm-corrected over eight tests)", ["Comparison (A vs. B)", "Δ (pp)", "95% CI (pp)", "p (Holm)", "Significant"], [
  ["FRQI patches vs. whole-image FRQI (V2)", "+27.1", "[+21.7, +32.7]", "< 0.001", "yes"], ["FRQI patches vs. whole-image FRQI (V3)", "+30.3", "[+25.1, +35.4]", "< 0.001", "yes"],
  ["NEQR patches vs. whole-image NEQR (V2)", "+22.5", "[+18.5, +26.7]", "< 0.001", "yes"], ["FRQI patches vs. NEQR patches", "+5.1", "[+1.1, +9.0]", "0.045", "yes"],
  ["FRQI patches vs. classical, same patches", "+4.2", "[+0.5, +7.7]", "0.060", "no"], ["NEQR patches vs. classical, same patches", "−0.9", "[−4.9, +3.1]", "0.678", "no"],
  ["FRQI patches vs. classical texture SVM", "−7.8", "[−10.9, −4.7]", "< 0.001", "yes"], ["NEQR patches vs. classical texture SVM", "−12.9", "[−15.8, −10.0]", "< 0.001", "yes"],
], [3.8, 1.0, 1.6, 1.0, 1.0]);
figure(PK + "Fig05_comparisons_forest.png", "Accuracy differences of the eight pre-declared comparisons with paired-bootstrap 95% confidence intervals and Holm-corrected p-values.", 6.2);
H2("Ablation Study");
P("Table 5.6 changes one component of the FRQI model at a time. Removing patching costs 27.1 pp, replacing the quantum encoding by classical patch moments costs 4.2 pp, and halving the patch size costs 2.5 pp of test accuracy. On the validation split, contrast stretch adds 8.9 pp of macro-F1, the angle scale b = 4 adds 12.2 pp over b = 1, and weak regularisation (C = 1000) is essential. Figure 5.5 shows the validation sweep for all groups. For NEQR, the configuration without contrast stretch had the highest validation score but a three times larger spread across seeds (± 7.2 vs. ± 2.3), a warning sign that was confirmed on the test set.");
table("Ablation study for the FRQI model", ["Variant", "Metric", "Value %"], [
  ["Full model (FRQI, 8×8 patches, b = 4, stretch, C = 1000)", "test accuracy", "**87.8 ± 1.5**"], ["– without patches (whole-image FRQI kernel)", "test accuracy", "60.6 ± 1.2"],
  ["– quantum encoding replaced by classical patch moments", "test accuracy", "83.6 ± 0.3"], ["– 4×4 instead of 8×8 patches", "test accuracy", "85.3 ± 1.7"],
  ["Full model", "validation macro-F1", "**88.0 ± 1.4**"], ["– without contrast stretch", "validation macro-F1", "79.1 ± 4.6"],
  ["– angle scale b = 2 / b = 1", "validation macro-F1", "84.9 ± 3.0 / 75.8 ± 2.3"], ["– image size 32 / 128 instead of 64", "validation macro-F1", "79.1 ± 4.7 / 85.4 ± 2.5"],
  ["– C = 100 / C = 1 instead of 1000", "validation macro-F1", "81.5 ± 2.6 / 53.8 ± 4.2"],
], [4.6, 1.8, 1.8]);
figure(PK + "Fig09_validation_sweep.png", "Validation macro-F1 of the best configuration for each image size and stride, with and without contrast stretch (validation split only).", 6.2);
H2("Error Analysis");
P("Figure 5.6 shows the confusion matrices and Figure 5.7 the per-class F1 (also listed in Table 5.7). FRQI is strongest on patches (95.8%) and crazing (93.1%). Its largest errors are inclusion images predicted as pitted surface (38 of 180) and scratches predicted as rolled-in scale (40 of 180). NEQR loses most on rolled-in scale: summed over seeds it classifies only 118 of 180 such test images correctly, against 178 for FRQI.");
figure(PK + "Fig06_confusion_matrices.png", "Row-normalised confusion matrices (%) on the locked test set, summed over three seeds, for FRQI (8×8 patches), NEQR (4×4 patches) and the classical SVM on the same patches.", 6.3);
figure(PK + "Fig07_per_class_f1.png", "Per-class F1 on the locked test set (mean over three seeds).", 6.0);
table("Per-class F1 % on the locked test set (mean over three seeds)", ["Model", "crazing", "inclusion", "patches", "pitted", "rolled-in", "scratches"], [
  ["FRQI patches 4×4", "85.8", "85.5", "94.8", "74.7", "89.8", "79.6"], ["FRQI patches 8×8", "93.1", "84.0", "95.8", "81.5", "89.5", "81.3"],
  ["NEQR patches 2×2", "88.6", "72.7", "91.6", "82.8", "62.1", "77.3"], ["NEQR patches 4×4", "89.5", "72.7", "91.4", "80.0", "65.0", "84.0"],
  ["Classical RBF-SVM, same patches", "83.5", "67.8", "92.9", "66.7", "93.0", "95.9"],
], [2.8, 1, 1, 1, 1, 1, 1]);
P("Figure 5.8 explains the large standard deviation of NEQR. Its seed accuracies are 87.5, 71.1 and 89.4%; on seed 1 it misclassifies every rolled-in-scale test image. This matches the brightness shift found in the exploratory analysis (Table 3.3): rolled-in-scale test images are much darker than the training images, and NEQR was selected without contrast stretch. FRQI, selected with per-image contrast stretch, is stable (86.7, 87.2 and 89.4%). NEQR was not re-tuned after the test, because that would use the test set for model choice. Figure 5.9 shows real test images with the FRQI model's predictions.");
figure(PK + "Fig08_seed_stability.png", "Test accuracy per seed for each V4 group; NEQR drops on seed 1 because of the rolled-in-scale class.", 5.4);
figure(PK + "Fig22_classification_examples.png", "Locked-test images with the predictions of the frozen V4 FRQI model (seed 0): correct (green) and misclassified (red, with the predicted class).", 5.2);
H2("Reconstruction Study");
P("Independently of classification, all 1,800 images were encoded and reconstructed with 20 methods using the real Qiskit circuits, the Qiskit Aer statevector and multinomial shot sampling. Table 5.8 summarises the main results. FRQI statevector decoding reproduces every image exactly; with finite shots the error grows with resolution because the shots are spread over more pixels. NEQR is exact up to quantisation (4-bit floor MSE 3.68e-4, 8-bit lossless).");
table("Reconstruction of all 1,800 images (mean over images)", ["Method", "Qubits", "MSE exact", "MSE 1,000 shots", "SSIM 1,000 shots", "Images exact"], [
  ["FRQI 8×8", "7", "0 (exact)", "8.66e-3", "0.518", "1,800"], ["FRQI 16×16", "9", "0 (exact)", "6.40e-2", "0.156", "1,800"],
  ["NEQR 16×16, 2-bit", "10", "8.93e-3", "1.48e-2", "0.385", "0"], ["NEQR 16×16, 4-bit", "12", "3.68e-4", "6.12e-3", "0.630", "0"],
  ["NEQR 16×16, 8-bit", "16", "0 (exact)", "5.75e-3", "0.673", "1,800"], ["V4 FRQI patches (64×64, p = 8)", "7", "0 (exact)", "8.67e-3", "0.323", "1,800"],
  ["V4 NEQR patches (64×64, p = 4, 4-bit)", "8", "3.67e-4", "3.67e-4", "0.888", "0"], ["Classical PCA, 8 components", "—", "4.66e-3", "—", "0.590", "—"],
], [3.0, 0.8, 1.2, 1.4, 1.3, 1.1]);
P("Figures 5.10 and 5.11 show the error versus the number of shots and the SSIM of every method. Figures 5.12 to 5.14 show real images before and after encoding and measurement: FRQI images become recognisable only with 10⁴–10⁵ shots, NEQR loses detail through quantisation and shows black pixels for unobserved positions at low shot counts, and the V4 patch representation keeps the full 64 × 64 texture once each patch receives 10⁴ shots, whereas classical PCA keeps only blurred brightness patterns. Figure 5.15 gives further reconstruction examples.");
figure(PK + "Fig11_reconstruction_mse_vs_shots.png", "Reconstruction error (MSE, log scale) versus measurement shots for whole-image FRQI and NEQR over all 1,800 images.", 6.0);
figure(PK + "Fig13_reconstruction_ssim_by_method.png", "SSIM of every reconstruction method at 1,000 shots, over all 1,800 images.", 6.0);
figure(PK + "Fig18_frqi_before_after.png", "Whole-image FRQI (16 × 16, 9 qubits): input (before) and reconstructions with the exact statevector and 100 to 100,000 shots; MSE above each image.", 5.6);
figure(PK + "Fig19_neqr_before_after.png", "Whole-image NEQR (16 × 16): input (before) and reconstructions with 2, 4 and 8 bits (exact) and 4 bits after 100 and 1,000 shots.", 5.6);
figure(PK + "Fig21_patch_and_pca_before_after.png", "64 × 64 inputs (before) rebuilt from the V4 patch representations and from classical PCA with 8 and 12 components.", 6.2);
figure(PK + "Fig12_reconstruction_examples.png", "Further reconstruction examples from the full study.", 6.0);
H2("Per-Image Analysis");
P("Using the saved test predictions of all 163 selected models of V2 to V4 (three seeds each), the median test image is classified correctly by 67% of model–seed pairs; no image is misclassified by every model and no image is classified correctly by every model (Figure 5.16). Rolled-in scale is the hardest class and patches the easiest. The errors are therefore spread over many images rather than caused by a few mislabelled samples.");
figure(PK + "Fig14_per_image_difficulty.png", "(a) Fraction of all model–seed pairs that classify each test image correctly; (b) mean per class, for all models and for the V4 FRQI model.", 6.0);
H2("Testing and Verification");
P("The system was tested at four levels (Table 5.9), and 17 automated integrity checks verify the V4 protocol itself (Table 5.10). An independent script also recomputes the key numbers of the paper from the raw prediction files; all 27 of its checks pass.");
table("Testing summary", ["Level", "Tool", "What is checked", "Result"], [
  ["Back-end unit and API tests", "pytest", "179 test functions: encoders, kernels, runner, protection of old results, API responses", "pass"],
  ["Front-end tests", "Vitest + Testing Library", "27 tests: routing, numbers only from the API, empty and error states", "27 / 27 pass"],
  ["Browser end-to-end", "Playwright", "V4 pages: walkthrough steps, 163-model grid, no horizontal scroll at 390 px, no console errors", "pass"],
  ["Numbers in the paper", "validate_v4_pack.py", "Accuracies recomputed from predictions.csv, selections, figures and tables present", "27 / 27 pass"],
], [2.2, 1.7, 3.4, 1.1]);
table("Automated V4 integrity checks (all pass)", ["Check", "Result"], [
  ["Historical V0 results: 0 changed, 0 missing", "PASS"], ["V2 manifest, splits and caches unchanged (SHA-256)", "PASS"], ["V4 copies of manifest, splits and caches identical to originals", "PASS"],
  ["No V2 or V3 result file modified or added since V3 was finalised", "PASS"], ["All 70 V3 selection files unchanged since the V3 freeze", "PASS"], ["V4 selection files unchanged since the V4 freeze", "PASS"],
  ["Exactly one locked-test access per frozen group, after the freeze", "PASS"], ["Test predictions exist only for frozen configurations", "PASS"], ["No selection file contains a test metric", "PASS"],
  ["864 candidate runs, 0 failed", "PASS"], ["Test accuracy recomputed from predictions.csv (360 images per run)", "PASS"], ["FRQI and NEQR headlines chosen by validation", "PASS"],
  ["Comparisons are exactly the 8 pre-declared ones", "PASS"], ["Every V4 quantum group records a real transpiled encoder circuit", "PASS"], ["Classical control has no circuit and is labelled classical", "PASS"],
], [6.6, 1.4]);

// ═════════════════════════ CHAPTER 6 ═════════════════════════
chapter("Conclusion and Future Scope"); resetSec();
H2("Conclusion");
P("This project built Q-ImageLab, a complete and reproducible system for studying quantum image representations on a real industrial classification task, and used it to answer whether FRQI and NEQR can classify steel surface defects. Under a leakage-controlled protocol with hashed splits, validation-only selection, frozen configurations and a single locked-test evaluation per model, the following conclusions were reached.");
bullets([
  "Whole-image FRQI and NEQR kernels perform poorly (about 60%) because they compare pixels only at identical positions, while NEU defect classes are defined by position-independent texture (Sections 3.2 and 4.10).",
  "The proposed patch-ensemble mixed-state kernel removes this weakness: FRQI improves to **87.8 ± 1.5%** and NEQR to **82.7 ± 10.1%**, gains of 27.1 and 22.5 percentage points (p < 0.001).",
  "The gain is not due to the quantum encoding: a classical SVM on the same patches reaches 83.6 ± 0.3% (FRQI difference not significant, p = 0.060), and a classical texture SVM remains best at 95.6 ± 2.2%. No quantum advantage is claimed.",
  "FRQI is more stable than NEQR; the NEQR instability is explained by a brightness shift of rolled-in scale between the training and test folders, found in the exploratory analysis.",
  "FRQI states reproduce all 1,800 images exactly from the statevector, but finite shots add large errors for whole images; patch encoding keeps registers at 5–8 qubits independent of image size.",
  "The dashboard makes every result inspectable and explains the method step by step on real images.",
]);
H2("Future Scope");
numbered([
  "**Finite-shot and noisy kernels:** estimate the kernel with simulated swap tests and realistic noise models to find how many shots are needed for the reported accuracy, and then test on real quantum hardware.",
  "**A fresh data set:** evaluate the method on another steel defect data set whose test images were never used for any design decision.",
  "**Richer encoders:** study larger patches, entangling encoders or learned patch weights, and test whether the kernels keep their accuracy once they can no longer be simulated cheaply.",
  "**Deployment:** extend the dashboard so that a user can upload an image and receive a prediction, with the same live explanation.",
], "num3");

// ═════════════════════════ BIBLIOGRAPHY ═════════════════════════
body.push(new Paragraph({ children: [new PageBreak()] }));
body.push(new Paragraph({ heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER, children: [run("BIBLIOGRAPHY", { size: 32, bold: true })], spacing: { after: 300 } }));
heads.push({ level: 1, text: "Bibliography", key: "BIBLIOGRAPHY" });
const REFS = [
  "J. Biamonte, P. Wittek, N. Pancotti, P. Rebentrost, N. Wiebe, and S. Lloyd, “Quantum machine learning,” *Nature*, vol. 549, no. 7671, pp. 195–202, 2017.",
  "V. Havlíček, A. D. Córcoles, K. Temme, A. W. Harrow, A. Kandala, J. M. Chow, and J. M. Gambetta, “Supervised learning with quantum-enhanced feature spaces,” *Nature*, vol. 567, no. 7747, pp. 209–212, 2019.",
  "J. Preskill, “Quantum computing in the NISQ era and beyond,” *Quantum*, vol. 2, p. 79, 2018.",
  "F. Yan, A. M. Iliyasu, and S. E. Venegas-Andraca, “A survey of quantum image representations,” *Quantum Information Processing*, vol. 15, no. 1, pp. 1–35, 2016.",
  "K. Song and Y. Yan, “A noise robust method based on completed local binary patterns for hot-rolled steel strip surface defects,” *Applied Surface Science*, vol. 285, pp. 858–864, 2013.",
  "Y. He, K. Song, Q. Meng, and Y. Yan, “An end-to-end steel surface defect detection approach via fusing multiple hierarchical features,” *IEEE Transactions on Instrumentation and Measurement*, vol. 69, no. 4, pp. 1493–1504, 2020.",
  "P. Q. Le, F. Dong, and K. Hirota, “A flexible representation of quantum images for polynomial preparation, image compression, and processing operations,” *Quantum Information Processing*, vol. 10, no. 1, pp. 63–84, 2011.",
  "Y. Zhang, K. Lu, Y. Gao, and M. Wang, “NEQR: a novel enhanced quantum representation of digital images,” *Quantum Information Processing*, vol. 12, no. 8, pp. 2833–2860, 2013.",
  "M. Schuld and N. Killoran, “Quantum machine learning in feature Hilbert spaces,” *Physical Review Letters*, vol. 122, no. 4, p. 040504, 2019.",
  "C. Cortes and V. Vapnik, “Support-vector networks,” *Machine Learning*, vol. 20, no. 3, pp. 273–297, 1995.",
  "M. Henderson, S. Shakya, S. Pradhan, and T. Cook, “Quanvolutional neural networks: powering image recognition with quantum circuits,” *Quantum Machine Intelligence*, vol. 2, no. 1, p. 2, 2020.",
  "S. Thanasilp, S. Wang, M. Cerezo, and Z. Holmes, “Exponential concentration in quantum kernel methods,” *Nature Communications*, vol. 15, p. 5200, 2024.",
  "H.-Y. Huang, M. Broughton, M. Mohseni, R. Babbush, S. Boixo, H. Neven, and J. R. McClean, “Power of data in quantum machine learning,” *Nature Communications*, vol. 12, p. 2631, 2021.",
  "M. Schuld, “Supervised quantum machine learning models are kernel methods,” arXiv:2101.11020, 2021.",
  "M. Cerezo, A. Arrasmith, R. Babbush, S. C. Benjamin, S. Endo, K. Fujii, J. R. McClean, K. Mitarai, X. Yuan, L. Cincio, and P. J. Coles, “Variational quantum algorithms,” *Nature Reviews Physics*, vol. 3, no. 9, pp. 625–644, 2021.",
  "J. R. McClean, S. Boixo, V. N. Smelyanskiy, R. Babbush, and H. Neven, “Barren plateaus in quantum neural network training landscapes,” *Nature Communications*, vol. 9, p. 4812, 2018.",
  "T. Ojala, M. Pietikäinen, and T. Mäenpää, “Multiresolution gray-scale and rotation invariant texture classification with local binary patterns,” *IEEE Transactions on Pattern Analysis and Machine Intelligence*, vol. 24, no. 7, pp. 971–987, 2002.",
  "R. M. Haralick, K. Shanmugam, and I. Dinstein, “Textural features for image classification,” *IEEE Transactions on Systems, Man, and Cybernetics*, vol. SMC-3, no. 6, pp. 610–621, 1973.",
  "H. Buhrman, R. Cleve, J. Watrous, and R. de Wolf, “Quantum fingerprinting,” *Physical Review Letters*, vol. 87, no. 16, p. 167902, 2001.",
  "A. Javadi-Abhari, M. Treinish, K. Krsulich, C. J. Wood, J. Lishman, J. Gacon, S. Martiel, P. D. Nation, L. S. Bishop, A. W. Cross, B. R. Johnson, and J. M. Gambetta, “Quantum computing with Qiskit,” arXiv:2405.08810, 2024.",
  "S. Holm, “A simple sequentially rejective multiple test procedure,” *Scandinavian Journal of Statistics*, vol. 6, no. 2, pp. 65–70, 1979.",
  "B. Efron and R. J. Tibshirani, *An Introduction to the Bootstrap*. New York, NY, USA: Chapman & Hall, 1993.",
  "Q. McNemar, “Note on the sampling error of the difference between correlated proportions or percentages,” *Psychometrika*, vol. 12, no. 2, pp. 153–157, 1947.",
  "A. Paszke et al., “PyTorch: An imperative style, high-performance deep learning library,” in *Advances in Neural Information Processing Systems 32 (NeurIPS)*, 2019, pp. 8024–8035.",
  "Z. Wang, A. C. Bovik, H. R. Sheikh, and E. P. Simoncelli, “Image quality assessment: from error visibility to structural similarity,” *IEEE Transactions on Image Processing*, vol. 13, no. 4, pp. 600–612, 2004.",
  "A. Howard, M. Sandler, G. Chu, L.-C. Chen, B. Chen, M. Tan, W. Wang, Y. Zhu, R. Pang, V. Vasudevan, Q. V. Le, and H. Adam, “Searching for MobileNetV3,” in *Proc. IEEE/CVF International Conference on Computer Vision (ICCV)*, 2019, pp. 1314–1324.",
  "F. Pedregosa et al., “Scikit-learn: Machine learning in Python,” *Journal of Machine Learning Research*, vol. 12, pp. 2825–2830, 2011.",
  "J. D. Hunter, “Matplotlib: A 2D graphics environment,” *Computing in Science & Engineering*, vol. 9, no. 3, pp. 90–95, 2007.",
  "C. R. Harris et al., “Array programming with NumPy,” *Nature*, vol. 585, pp. 357–362, 2020.",
  "A. Mari, T. R. Bromley, J. Izaac, M. Schuld, and N. Killoran, “Transfer learning in hybrid classical-quantum neural networks,” *Quantum*, vol. 4, p. 340, 2020.",
];
REFS.forEach((r, i) => body.push(new Paragraph({ spacing: { after: 100, line: 300 }, indent: { left: 560, hanging: 560 }, alignment: AlignmentType.LEFT, children: [run(`[${i + 1}]`, { size: 22 }), new TextRun({ text: "\t", font: FONT }), ...rich(r, { size: 22 })], tabStops: [{ type: "left", position: 560 }] })));

// ═════════════════════════ APPENDIX ═════════════════════════
body.push(new Paragraph({ children: [new PageBreak()] }));
body.push(new Paragraph({ heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER, children: [run("APPENDIX", { size: 32, bold: true })], spacing: { after: 300 } }));
heads.push({ level: 1, text: "Appendix", key: "APPENDIX" });
chap = "A"; figN = 0; tabN = 0;
body.push(new Paragraph({ children: [run("A. Hyper-parameter grid searched on the validation split (V4)", { bold: true, size: 26 })], spacing: { before: 120, after: 120 } }));
table("V4 search space (selected values in bold); the test set was never used for selection", ["Group", "Image / patch / stride", "Encoding option", "Stretch", "SVM C", "Configs (runs)"], [
  ["FRQI 4×4", "32² p4 s2; **64² p4 s4**", "angle ×1, 2, **4**", "none, **on**", "1, 10, 100, **1000**", "48 (144)"],
  ["FRQI 8×8", "32² p8 s4; **64² p8 s4**; 128² p8 s8", "angle ×1, 2, **4**", "none, **on**", "1, 10, 100, **1000**", "72 (216)"],
  ["NEQR 2×2", "32² p2 s1; **64² p2 s2**", "**4**, 5, 6 bits", "**none**, on", "1, 10, 100, **1000**", "48 (144)"],
  ["NEQR 4×4", "32² p4 s2; 64² p4 s4; **128² p4 s4**", "3, **4** bits", "**none**, on", "1, 10, 100, **1000**", "48 (144)"],
  ["Classical control", "64² p4 s4; **64² p8 s4**; 128² p4 s4", "γ 0.3, **1**, 3", "none, **on**", "1, 10, 100, **1000**", "72 (216)"],
  ["**Total**", "", "", "", "", "**288 (864)**"],
], [1.4, 2.6, 1.5, 1.1, 1.5, 1.2], { size: 17 });
body.push(new Paragraph({ children: [run("B. How to run the system", { bold: true, size: 26 })], spacing: { before: 200, after: 120 } }));
bullets([
  "Back end: `.venv/bin/python -m uvicorn api_main:app --port 8000` (with QIL_PROTECT_V2=1 and QIL_PROTECT_V3=1 to protect older results).".replace(/`/g, ""),
  "Front end: `cd frontend && npx vite --port 5173`, then open http://localhost:5173.".replace(/`/g, ""),
  "V4 pipeline: scripts/v4/run_v4.py with the stages candidates → select → freeze → test, followed by analyze_v4.py and verify_v4.py.",
  "Reconstruction study: scripts/v4/reconstruct_all.py (run, then merge).",
  "Figures and tables: the scripts in research_paper_visuals/source regenerate every figure and table from the saved results.",
]);
body.push(new Paragraph({ children: [run("C. Use of AI tools", { bold: true, size: 26 })], spacing: { before: 200, after: 120 } }));
P("Generative AI tools were used to assist with writing and debugging parts of the code, generating figures and tables from the saved results, and drafting and editing parts of this report. All experiments were run by the project team, every number was checked against the result files, and no result was generated by AI.");

// ═════════════════════════ FRONT MATTER ═════════════════════════
const front = [];
const TITLE = "Quantum Image Representations for Steel Surface Defect Classification: FRQI and NEQR Encodings, Patch-Ensemble Mixed-State Quantum Kernels and an Interactive Analysis Dashboard";
front.push(...blank(3));
front.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 360, line: 360 }, children: [run(TITLE, { size: 34, bold: true })] }));
front.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [run("A Project Report", { size: 26, italics: true })] }));
front.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [run("submitted in partial fulfillment of the requirements for the award of the degree of", { size: 24 })] }));
front.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 360 }, children: [run("BACHELOR OF TECHNOLOGY", { size: 28, bold: true })] }));
front.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 }, children: [run("Submitted by", { size: 24, italics: true })] }));
front.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 360 }, children: [run("[STUDENT NAME] ([ROLL NO.])", { size: 26, bold: true })] }));
front.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 }, children: [run("Under the supervision of", { size: 24, italics: true })] }));
front.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 }, children: [run("[SUPERVISOR NAME], [DESIGNATION]", { size: 26, bold: true })] }));
front.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 }, children: [run("School of Engineering and Technology", { size: 26, bold: true })] }));
front.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 }, children: [run("BML Munjal University, Gurugram", { size: 26, bold: true })] }));
front.push(new Paragraph({ alignment: AlignmentType.CENTER, children: [run("December 2026", { size: 24 })] }));
// declarations
front.push(new Paragraph({ children: [new PageBreak()] }));
front.push(centerTitle("CANDIDATE’S DECLARATION", 480));
front.push(new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { line: 360, after: 240 }, children: rich(`I hereby certify that the work on the project entitled “${TITLE}”, in partial fulfillment of the requirements for the award of the Degree of Bachelor of Technology in the School of Engineering and Technology at BML Munjal University, having University Roll No. [ROLL NO.], is an authentic record of my own work carried out during the period from July 2026 to December 2026 under the supervision of [SUPERVISOR NAME].`) }));
front.push(...blank(2));
front.push(new Paragraph({ alignment: AlignmentType.RIGHT, children: [run("([STUDENT NAME])")] }));
front.push(...blank(3));
front.push(centerTitle("SUPERVISOR’S DECLARATION", 360));
front.push(new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { line: 360, after: 480 }, children: rich("This is to certify that the above statement made by the candidate is correct to the best of my knowledge.") }));
front.push(new Paragraph({ spacing: { after: 240 }, children: [run("Faculty Supervisor Name: [SUPERVISOR NAME]")] }));
front.push(new Paragraph({ children: [run("Signature:")] }));
// acknowledgement
front.push(new Paragraph({ children: [new PageBreak()] }));
front.push(centerTitle("ACKNOWLEDGEMENT", 480));
[`I am highly grateful to [SUPERVISOR NAME], [DESIGNATION], BML Munjal University, Gurugram, for supervising the project from July to December 2026.`,
  `[SUPERVISOR NAME] has provided great help in carrying out my work and is acknowledged with reverential thanks. Without wise counsel and able guidance, it would have been impossible to complete the project in this manner.`,
  `I want to express my sincere thanks to [SUPERVISOR NAME] for continually stimulating me. I would also like to thank the entire team at BML Munjal University. I would also like to thank my friends, who devoted their valuable time and helped me in every possible way toward the successful completion.`].forEach((t) =>
  front.push(new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { line: 360, after: 200 }, children: rich(t) })));
front.push(...blank(2));
front.push(new Paragraph({ alignment: AlignmentType.RIGHT, children: [run("([STUDENT NAME])")] }));
// contents
front.push(new Paragraph({ children: [new PageBreak()] }));
front.push(centerTitle("TABLE OF CONTENTS", 360));
for (const k of ["LIST OF FIGURES", "LIST OF TABLES", "LIST OF ABBREVIATIONS"]) front.push(dotLine(k.charAt(0) + k.slice(1).toLowerCase(), pg(k), { bold: true }));
for (const h of heads) front.push(dotLine(h.text, pg(h.key), { indent: (h.level - 1) * 360, bold: h.level === 1, size: h.level === 3 ? 20 : 22, after: h.level === 1 ? 80 : 30 }));
// list of figures
const listTable = (rows, head) => {
  const W = [1300, 6526, 1200];
  const cell = (t, i, hdr) => new TableCell({ width: { size: W[i], type: WidthType.DXA }, borders, shading: hdr ? { fill: "DCE6F2", type: ShadingType.CLEAR, color: "auto" } : undefined, margins: { top: 40, bottom: 40, left: 80, right: 80 }, children: [new Paragraph({ alignment: i === 2 ? AlignmentType.CENTER : AlignmentType.LEFT, children: rich(t, { size: 20, bold: hdr || undefined }) })] });
  return new Table({ width: { size: TW, type: WidthType.DXA }, columnWidths: W, layout: TableLayoutType.FIXED, rows: [new TableRow({ tableHeader: true, children: head.map((h, i) => cell(h, i, true)) }), ...rows.map((r) => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, i, false)) }))] });
};
const short = (t) => { const s = t.replace(/\*/g, ""); const cut = s.split(/\.\s/)[0].replace(/\.$/, ""); return cut.length > 160 ? cut.slice(0, 157) + "…" : cut; };
front.push(new Paragraph({ children: [new PageBreak()] }));
front.push(centerTitle("LIST OF FIGURES", 240));
front.push(listTable(figs.map((f) => [`Figure ${f.id}`, short(f.text), pg(f.key)]), ["Figure No.", "Figure Description", "Page No."]));
front.push(new Paragraph({ children: [new PageBreak()] }));
front.push(centerTitle("LIST OF TABLES", 240));
front.push(listTable(tabs.map((t) => [`Table ${t.id}`, short(t.text), pg(t.key)]), ["Table No.", "Table Description", "Page No."]));
front.push(new Paragraph({ children: [new PageBreak()] }));
front.push(centerTitle("LIST OF ABBREVIATIONS", 240));
const ABBR = [["API", "Application Programming Interface"], ["CNN", "Convolutional Neural Network"], ["CSV", "Comma-Separated Values"], ["CX", "Controlled-NOT gate"],
  ["DFD", "Data Flow Diagram"], ["ER", "Entity–Relationship"], ["FRQI", "Flexible Representation of Quantum Images"], ["GLCM", "Grey-Level Co-occurrence Matrix"],
  ["JSON", "JavaScript Object Notation"], ["LBP", "Local Binary Pattern"], ["MSE", "Mean Squared Error"], ["NEQR", "Novel Enhanced Quantum Representation"],
  ["NEU-DET", "Northeastern University surface defect detection data set"], ["NISQ", "Noisy Intermediate-Scale Quantum"], ["PCA", "Principal Component Analysis"],
  ["pp", "Percentage points"], ["QIR", "Quantum Image Representation"], ["QKC", "Quantum Kernel Classifier"], ["QML", "Quantum Machine Learning"],
  ["RBF", "Radial Basis Function"], ["REST", "Representational State Transfer"], ["SHA-256", "Secure Hash Algorithm, 256-bit"], ["SSIM", "Structural Similarity Index"],
  ["SVM", "Support Vector Machine"], ["UI", "User Interface"], ["VQC", "Variational Quantum Classifier"]];
{
  const W = [2200, 6826];
  const cell = (t, i, hdr) => new TableCell({ width: { size: W[i], type: WidthType.DXA }, borders, shading: hdr ? { fill: "DCE6F2", type: ShadingType.CLEAR, color: "auto" } : undefined, margins: { top: 40, bottom: 40, left: 80, right: 80 }, children: [new Paragraph({ children: rich(t, { size: 21, bold: hdr || undefined }) })] });
  front.push(new Table({ width: { size: TW, type: WidthType.DXA }, columnWidths: W, layout: TableLayoutType.FIXED, rows: [new TableRow({ tableHeader: true, children: ["Abbreviation", "Full Form"].map((h, i) => cell(h, i, true)) }), ...ABBR.map((r) => new TableRow({ children: r.map((c, i) => cell(c, i, false)) }))] }));
}

// ───────────────────────── document ─────────────────────────
const H = (size) => ({ run: { font: FONT, size, bold: true }, paragraph: { spacing: { before: 240, after: 120 }, keepNext: true } });
const doc = new Document({
  creator: "Q-ImageLab project", title: TITLE,
  styles: {
    default: { document: { run: { font: FONT, size: 24 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, ...H(28), paragraph: { spacing: { before: 0, after: 60 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, ...H(28), paragraph: { spacing: { before: 280, after: 120 }, keepNext: true, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, ...H(24), paragraph: { spacing: { before: 200, after: 100 }, keepNext: true, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      ...["num", "num2", "num3"].map((r) => ({ reference: r, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] })),
    ],
  },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 20 })] })] }) },
    children: [...front, ...body],
  }],
});
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  fs.writeFileSync(path.join(__dirname, "keys.json"), JSON.stringify({ heads: heads.map((h) => h.key), figs: figs.map((f) => f.key), tabs: tabs.map((t) => t.key), front: ["LIST OF FIGURES", "LIST OF TABLES", "LIST OF ABBREVIATIONS"] }, null, 1));
  console.log("wrote", OUT, "figures", figs.length, "tables", tabs.length, "headings", heads.length);
});
