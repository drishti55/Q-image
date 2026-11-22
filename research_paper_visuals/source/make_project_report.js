// Builds the BML Munjal University B.Tech project report (Q-ImageLab) as a .docx in the university template format.
// Results tables are read live from the running API (http://127.0.0.1:8000) and research_paper_visuals/Project_Report/
// figures/eda_stats.json; no result is typed by hand except where quoted from the paper's verified tables.
// Usage: NODE_PATH=<dir with docx> node make_project_report.js [pages.json]
//   pages.json (optional) = page numbers of captions/headings from a previous render (two-pass lists).
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType, PageBreak,
  Footer, PageNumber, NumberFormat, BorderStyle, ShadingType, TabStopType, LevelFormat, HeadingLevel, VerticalAlign,
} = require('docx');

const ROOT = path.resolve(__dirname, '..', '..');
const RPT = path.join(ROOT, 'research_paper_visuals', 'Project_Report');
const PACK = path.join(ROOT, 'research_paper_visuals', 'V4_paper_pack', 'figures');
const OUT = path.join(RPT, 'Q-ImageLab_Project_Report.docx');
const PAGES = process.argv[2] && fs.existsSync(process.argv[2]) ? JSON.parse(fs.readFileSync(process.argv[2], 'utf8')) : {};
const API = 'http://127.0.0.1:8000';

const FONT = 'Times New Roman';
const BODY = 24; // 12 pt
const TEXT_W = 9360; // 6.5 in in DXA

// ───────────────────────── helpers ─────────────────────────
const refsOrder = [];
const REFS = {
  le2011frqi: 'P. Q. Le, F. Dong, and K. Hirota, “A flexible representation of quantum images for polynomial preparation, image compression, and processing operations,” Quantum Information Processing, vol. 10, no. 1, pp. 63–84, 2011, doi: 10.1007/s11128-010-0177-y.',
  zhang2013neqr: 'Y. Zhang, K. Lu, Y. Gao, and M. Wang, “NEQR: a novel enhanced quantum representation of digital images,” Quantum Information Processing, vol. 12, no. 8, pp. 2833–2860, 2013, doi: 10.1007/s11128-013-0567-z.',
  yan2016survey: 'F. Yan, A. M. Iliyasu, and S. E. Venegas-Andraca, “A survey of quantum image representations,” Quantum Information Processing, vol. 15, no. 1, pp. 1–35, 2016, doi: 10.1007/s11128-015-1195-6.',
  song2013neu: 'K. Song and Y. Yan, “A noise robust method based on completed local binary patterns for hot-rolled steel strip surface defects,” Applied Surface Science, vol. 285, pp. 858–864, 2013, doi: 10.1016/j.apsusc.2013.09.002.',
  he2020neudet: 'Y. He, K. Song, Q. Meng, and Y. Yan, “An end-to-end steel surface defect detection approach via fusing multiple hierarchical features,” IEEE Transactions on Instrumentation and Measurement, vol. 69, no. 4, pp. 1493–1504, 2020, doi: 10.1109/TIM.2019.2915404.',
  havlicek2019: 'V. Havlíček, A. D. Córcoles, K. Temme, A. W. Harrow, A. Kandala, J. M. Chow, and J. M. Gambetta, “Supervised learning with quantum-enhanced feature spaces,” Nature, vol. 567, no. 7747, pp. 209–212, 2019, doi: 10.1038/s41586-019-0980-2.',
  schuld2019feature: 'M. Schuld and N. Killoran, “Quantum machine learning in feature Hilbert spaces,” Physical Review Letters, vol. 122, no. 4, p. 040504, 2019, doi: 10.1103/PhysRevLett.122.040504.',
  schuld2021kernel: 'M. Schuld, “Supervised quantum machine learning models are kernel methods,” arXiv:2101.11020, 2021.',
  huang2021power: 'H.-Y. Huang, M. Broughton, M. Mohseni, R. Babbush, S. Boixo, H. Neven, and J. R. McClean, “Power of data in quantum machine learning,” Nature Communications, vol. 12, p. 2631, 2021, doi: 10.1038/s41467-021-22539-9.',
  thanasilp2024: 'S. Thanasilp, S. Wang, M. Cerezo, and Z. Holmes, “Exponential concentration in quantum kernel methods,” Nature Communications, vol. 15, p. 5200, 2024, doi: 10.1038/s41467-024-49287-w.',
  biamonte2017: 'J. Biamonte, P. Wittek, N. Pancotti, P. Rebentrost, N. Wiebe, and S. Lloyd, “Quantum machine learning,” Nature, vol. 549, no. 7671, pp. 195–202, 2017, doi: 10.1038/nature23474.',
  preskill2018: 'J. Preskill, “Quantum computing in the NISQ era and beyond,” Quantum, vol. 2, p. 79, 2018, doi: 10.22331/q-2018-08-06-79.',
  cerezo2021vqa: 'M. Cerezo et al., “Variational quantum algorithms,” Nature Reviews Physics, vol. 3, no. 9, pp. 625–644, 2021, doi: 10.1038/s42254-021-00348-9.',
  mcclean2018barren: 'J. R. McClean, S. Boixo, V. N. Smelyanskiy, R. Babbush, and H. Neven, “Barren plateaus in quantum neural network training landscapes,” Nature Communications, vol. 9, p. 4812, 2018, doi: 10.1038/s41467-018-07090-4.',
  henderson2020quanv: 'M. Henderson, S. Shakya, S. Pradhan, and T. Cook, “Quanvolutional neural networks: powering image recognition with quantum circuits,” Quantum Machine Intelligence, vol. 2, no. 1, p. 2, 2020, doi: 10.1007/s42484-020-00012-y.',
  buhrman2001: 'H. Buhrman, R. Cleve, J. Watrous, and R. de Wolf, “Quantum fingerprinting,” Physical Review Letters, vol. 87, no. 16, p. 167902, 2001, doi: 10.1103/PhysRevLett.87.167902.',
  holm1979: 'S. Holm, “A simple sequentially rejective multiple test procedure,” Scandinavian Journal of Statistics, vol. 6, no. 2, pp. 65–70, 1979.',
  mcnemar1947: 'Q. McNemar, “Note on the sampling error of the difference between correlated proportions or percentages,” Psychometrika, vol. 12, no. 2, pp. 153–157, 1947, doi: 10.1007/BF02295996.',
  efron1993: 'B. Efron and R. J. Tibshirani, An Introduction to the Bootstrap. New York, NY, USA: Chapman & Hall, 1993.',
  cortes1995: 'C. Cortes and V. Vapnik, “Support-vector networks,” Machine Learning, vol. 20, no. 3, pp. 273–297, 1995, doi: 10.1007/BF00994018.',
  pedregosa2011: 'F. Pedregosa et al., “Scikit-learn: Machine learning in Python,” Journal of Machine Learning Research, vol. 12, pp. 2825–2830, 2011.',
  qiskit2024: 'A. Javadi-Abhari et al., “Quantum computing with Qiskit,” arXiv:2405.08810, 2024.',
  ojala2002lbp: 'T. Ojala, M. Pietikäinen, and T. Mäenpää, “Multiresolution gray-scale and rotation invariant texture classification with local binary patterns,” IEEE Transactions on Pattern Analysis and Machine Intelligence, vol. 24, no. 7, pp. 971–987, 2002, doi: 10.1109/TPAMI.2002.1017623.',
  haralick1973glcm: 'R. M. Haralick, K. Shanmugam, and I. Dinstein, “Textural features for image classification,” IEEE Transactions on Systems, Man, and Cybernetics, vol. SMC-3, no. 6, pp. 610–621, 1973, doi: 10.1109/TSMC.1973.4309314.',
  wang2004ssim: 'Z. Wang, A. C. Bovik, H. R. Sheikh, and E. P. Simoncelli, “Image quality assessment: from error visibility to structural similarity,” IEEE Transactions on Image Processing, vol. 13, no. 4, pp. 600–612, 2004, doi: 10.1109/TIP.2003.819861.',
};
/** Citation in IEEE style, numbered by order of first use. */
const c = (...keys) => `[${keys.map((k) => { if (!REFS[k]) throw new Error(`unknown ref ${k}`); if (!refsOrder.includes(k)) refsOrder.push(k); return refsOrder.indexOf(k) + 1; }).join(', ')}]`;

/** Inline markup: **bold**, *italic*. */
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), font: FONT, size: BODY, ...base }));
    const t = m[0];
    out.push(new TextRun({ text: t.replace(/^\*\*?|\*\*?$/g, ''), font: FONT, size: BODY, bold: t.startsWith('**') || base.bold, italics: !t.startsWith('**') || base.italics, ...base, ...(t.startsWith('**') ? { bold: true } : { italics: true }) }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), font: FONT, size: BODY, ...base }));
  return out;
}
const P = (text, o = {}) => new Paragraph({ children: runs(text, o.run), alignment: o.align ?? AlignmentType.JUSTIFIED, spacing: { line: 360, after: o.after ?? 120, before: o.before ?? 0 }, indent: o.indent, keepNext: o.keepNext });
const blank = (n = 1) => Array.from({ length: n }, () => new Paragraph({ children: [new TextRun({ text: '', font: FONT, size: BODY })] }));
const br = () => new Paragraph({ children: [new PageBreak()] });
const bullets = (items, ref = 'bul') => items.map((t) => new Paragraph({ children: runs(t), numbering: { reference: ref, level: 0 }, alignment: AlignmentType.JUSTIFIED, spacing: { line: 330, after: 60 } }));

let CH = 0, SEC = '', figN = 0, tabN = 0, eqN = 0;
const FIGS = [], TABS = [], TOC = [];
function chapter(title) {
  CH += 1; figN = 0; tabN = 0; eqN = 0;
  TOC.push({ level: 0, text: `${CH}  ${title}`, key: `CH${CH}` });
  return [
    new Paragraph({ children: [new TextRun({ text: `CHAPTER ${CH}`, font: FONT, size: 28, bold: true })], alignment: AlignmentType.CENTER, pageBreakBefore: true, spacing: { after: 120 } }),
    new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: title, font: FONT, size: 36, bold: true })], alignment: AlignmentType.CENTER, spacing: { after: 360 } }),
  ];
}
function appendixStart(letter, title) {
  CH = letter; figN = 0; tabN = 0; eqN = 0;
  TOC.push({ level: 0, text: `Appendix ${letter}  ${title}`, key: `APP${letter}`, appendix: true });
  return [
    new Paragraph({ children: [new TextRun({ text: `APPENDIX ${letter}`, font: FONT, size: 28, bold: true })], alignment: AlignmentType.CENTER, pageBreakBefore: true, spacing: { after: 120 } }),
    new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: title, font: FONT, size: 36, bold: true })], alignment: AlignmentType.CENTER, spacing: { after: 360 } }),
  ];
}
function h2(num, title) {
  SEC = `${num}`;
  TOC.push({ level: 1, text: `${num}  ${title}`, key: `H${num}` });
  return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: `${num}  ${title}`, font: FONT, size: 28, bold: true })], spacing: { before: 280, after: 140 }, keepNext: true });
}
function h3(num, title) {
  TOC.push({ level: 2, text: `${num}  ${title}`, key: `H${num}` });
  return new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun({ text: `${num}  ${title}`, font: FONT, size: 25, bold: true })], spacing: { before: 200, after: 100 }, keepNext: true });
}
function pngSize(file) { const b = fs.readFileSync(file); return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) }; }
function img(file, widthIn) {
  const { w, h } = pngSize(file);
  const W = Math.round(widthIn * 96), H = Math.round((W * h) / w);
  return new ImageRun({ type: 'png', data: fs.readFileSync(file), transformation: { width: W, height: H } });
}
function fig(file, caption, widthIn = 6.2) {
  if (!fs.existsSync(file)) throw new Error(`missing figure ${file}`);
  figN += 1; const num = `${CH}.${figN}`;
  FIGS.push({ num, caption });
  return [
    new Paragraph({ children: [img(file, widthIn)], alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 160, after: 60 } }),
    new Paragraph({ children: [new TextRun({ text: `Figure ${num}. `, font: FONT, size: 21, bold: true }), new TextRun({ text: caption, font: FONT, size: 21, italics: true })], alignment: AlignmentType.CENTER, spacing: { after: 220 } }),
  ];
}
const figRef = (offset = 1) => `Figure ${CH}.${figN + offset}`;
const tabRef = (offset = 1) => `Table ${CH}.${tabN + offset}`;
function eq(file, widthIn) {
  eqN += 1;
  return new Paragraph({ children: [img(file, widthIn), new TextRun({ text: `\t(${CH}.${eqN})`, font: FONT, size: BODY })], alignment: AlignmentType.CENTER, tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W }], spacing: { before: 120, after: 120 } });
}
function eqText(t) {
  eqN += 1;
  return new Paragraph({ children: [new TextRun({ text: t, font: 'Cambria Math', size: BODY, italics: true }), new TextRun({ text: `\t(${CH}.${eqN})`, font: FONT, size: BODY })], alignment: AlignmentType.CENTER, tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W }], spacing: { before: 120, after: 120 } });
}
const border = { style: BorderStyle.SINGLE, size: 4, color: '8A939D' };
function cell(text, widthDxa, o = {}) {
  return new TableCell({
    width: { size: widthDxa, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
    shading: o.head ? { type: ShadingType.CLEAR, color: 'auto', fill: 'DCE6F2' } : o.fill ? { type: ShadingType.CLEAR, color: 'auto', fill: o.fill } : undefined,
    margins: { top: 50, bottom: 50, left: 80, right: 80 },
    borders: { top: border, bottom: border, left: border, right: border },
    children: [new Paragraph({ children: runs(String(text), { size: o.size ?? 19, bold: o.head || o.bold }), alignment: o.align ?? AlignmentType.LEFT, spacing: { line: 240 } })],
  });
}
function tbl(caption, head, rows, widthsIn, o = {}) {
  tabN += 1; const num = `${CH}.${tabN}`;
  TABS.push({ num, caption });
  const tot = widthsIn.reduce((a, b) => a + b, 0), dx = widthsIn.map((w) => Math.round((w / tot) * TEXT_W));
  dx[dx.length - 1] += TEXT_W - dx.reduce((a, b) => a + b, 0);
  return [
    new Paragraph({ children: [new TextRun({ text: `Table ${num}. `, font: FONT, size: 21, bold: true }), new TextRun({ text: caption, font: FONT, size: 21, italics: true })], alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 200, after: 80 } }),
    new Table({
      width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: dx,
      rows: [new TableRow({ tableHeader: true, children: head.map((h, i) => cell(h, dx[i], { head: true, align: i && o.numeric ? AlignmentType.CENTER : AlignmentType.LEFT })) }),
        ...rows.map((r, ri) => new TableRow({ cantSplit: true, children: r.map((v, i) => cell(v, dx[i], { align: i && o.numeric ? AlignmentType.CENTER : AlignmentType.LEFT, fill: o.highlight?.includes(ri) ? 'EEF4FC' : undefined, bold: o.highlight?.includes(ri) })) }))],
    }),
    new Paragraph({ children: [], spacing: { after: 160 } }),
  ];
}
const pct = (v, d = 1) => (v == null ? '—' : (100 * v).toFixed(d));
const ms = (m) => (m?.mean == null ? '—' : `${pct(m.mean)} ± ${pct(m.std ?? 0)}`);
const fx = (f) => path.join(RPT, 'figures', f), px = (f) => path.join(PACK, f), sx = (f) => path.join(RPT, 'screenshots_v5', f);

// ───────────────────────── content ─────────────────────────
async function getJSON(p) { const r = await fetch(API + p); if (!r.ok) throw new Error(`${p}: ${r.status}`); return r.json(); }

async function build() {
  const v4 = await getJSON('/api/v4/results');
  const fam = await getJSON('/api/v4/families');
  const v2 = await getJSON('/api/v2/summary');
  const v3 = await getJSON('/api/v3/results');
  const eda = JSON.parse(fs.readFileSync(fx('eda_stats.json'), 'utf8'));
  const G = v4.groups, R = v4.references, H = v4.headlines;
  const fr = G[H.frqi], ne = G[H.neqr], ctrl = G['V4-patchmom-rbfsvm'];
  const cmp = (s) => v4.comparisons.find((x) => x.name.startsWith(s));
  const CL = ['crazing', 'inclusion', 'patches', 'pitted_surface', 'rolled-in_scale', 'scratches'];
  const CLN = { crazing: 'Crazing', inclusion: 'Inclusion', patches: 'Patches', pitted_surface: 'Pitted surface', 'rolled-in_scale': 'Rolled-in scale', scratches: 'Scratches' };
  const bT = eda.brightness.train, bV = eda.brightness.validation;

  const body = [], appx = [];
  let target = body;
  const add = (...xs) => xs.flat().forEach((x) => target.push(x));

  // ═════════════ CHAPTER 1 ═════════════
  add(chapter('Introduction'));
  add(h2('1.1', 'Introduction to Project'));
  add(P(`Quantum computing promises new ways of representing and processing information because a register of *n* qubits is described by 2ⁿ complex amplitudes. Quantum machine learning (QML) tries to use this large state space as a feature space for learning ${c('biamonte2017')}. Present-day devices are, however, small and noisy ${c('preskill2018')}, so most practical studies rely on short circuits, few qubits and exact classical simulation. Images are an attractive test case: many industrial inspection tasks are image-based, and a dedicated line of research describes how pixel positions and intensities can be stored in qubits ${c('yan2016survey')}.`));
  add(P(`This project, **Q-ImageLab**, studies whether the two most widely used quantum image representations, the Flexible Representation of Quantum Images (FRQI) ${c('le2011frqi')} and the Novel Enhanced Quantum Representation (NEQR) ${c('zhang2013neqr')}, can classify real industrial images. The application is hot-rolled steel surface inspection on the public NEU-DET database ${c('song2013neu', 'he2020neudet')}, which contains six defect classes: crazing, inclusion, patches, pitted surface, rolled-in scale and scratches. Images are encoded as quantum states and compared through quantum kernels ${c('havlicek2019', 'schuld2019feature')}; a support vector machine (SVM) ${c('cortes1995')} then predicts the defect class.`));
  add(P('The project has two outcomes. The first is a research result: a **patch-ensemble mixed-state kernel** that raises FRQI from about 61 % to 87.8 % and NEQR from about 60 % to 82.7 % test accuracy, evaluated under a leakage-controlled protocol and compared honestly with classical models that receive the same input. The second is a software outcome: **Q-ImageLab**, a FastAPI + React research and learning platform that exposes every saved result, replays the trained models live on real images, lets users upload their own images for FRQI/NEQR encoding, and teaches the algorithms through interactive visualisations.'));
  add(h2('1.2', 'Overview'));
  add(P('The work was carried out in five protocol versions. Each version reused the same dataset manifest, splits, seeds and 360-image locked test set from V2 onwards, so that results are directly comparable:'));
  add(bullets([
    '**V0 (prototype):** ad-hoc experiments on a handful of images with random splits and no locked test set. Kept only as a historical record.',
    `**V2:** a locked-test protocol and ${v2.counts.selected_configurations} selected configurations from ${v2.counts.experiments.completed.toLocaleString()} runs: classical models on pixels, CNN features, quantum kernel classifiers (QKC), variational quantum classifiers (VQC), whole-image FRQI/NEQR kernels and hybrid CNN + quantum models.`,
    `**V3:** validation-driven improvements (${v3.counts.groups} groups, ${v3.counts.candidate_runs.toLocaleString()} validation runs): texture features (LBP + GLCM), projected quantum kernels (PQK), longer VQC training and matched classical controls. FRQI and NEQR stayed near 60 %.`,
    `**V4 (proposed method):** patch-ensemble FRQI/NEQR kernels: ${v4.counts.candidate_runs} validation runs, a SHA-256-frozen selection, one locked-test evaluation per model and eight pre-declared, Holm-corrected comparisons.`,
    '**Platform:** the Q-ImageLab web application, used to inspect results, explain the algorithms visually and present the work.',
  ]));
  add(P('Two research questions guide the project. **RQ1:** does representing an image as the mixed state of its FRQI- or NEQR-encoded patches improve locked-test accuracy over whole-image FRQI and NEQR kernels? **RQ2:** is the improvement due to the quantum encoding, that is, does the quantum kernel outperform a classical model on the same patches and the best classical texture model?'));
  add(P('The report is organised as follows. Chapter 2 reviews the literature and states the objectives. Chapter 3 analyses the dataset. Chapter 4 describes the methodology, the system design, the algorithms and the implementation of the platform. Chapter 5 presents the results, and Chapter 6 concludes with the future scope.'));
  add(h2('1.3', 'Existing System'));
  add(P(`Steel surface inspection is traditionally done by human inspectors or by classical computer-vision systems. On NEU-DET, hand-crafted texture descriptors such as local binary patterns (LBP) ${c('ojala2002lbp')} and grey-level co-occurrence matrices (GLCM) ${c('haralick1973glcm')}, and convolutional neural networks ${c('he2020neudet')}, already classify the six classes with high accuracy. On the quantum side, existing work on FRQI and NEQR focuses on state preparation, storage and image operations rather than on classifying real textured images ${c('le2011frqi', 'zhang2013neqr', 'yan2016survey')}, and quantum kernel demonstrations mostly use synthetic data or handwritten digits ${c('havlicek2019', 'henderson2020quanv')}.`));
  add(P('Our own first prototype (V0) also had serious weaknesses. Table 1.1 summarises the limitations of the existing approaches and how this project addresses them.'));
  add(tbl('Limitations of the existing system and how Q-ImageLab addresses them', ['Existing system', 'Limitation', 'Q-ImageLab'], [
    ['FRQI / NEQR literature', 'Studies preparation and image operations; no classification of real textured images', 'Classifies all 1,800 NEU-DET images with FRQI and NEQR kernels'],
    ['Whole-image quantum kernels (our V2/V3)', 'Compare pixel i with pixel i only; a shifted texture looks unrelated (≈60 % accuracy)', 'Patch-ensemble mixed state: compares every patch with every patch'],
    ['Quantum kernel demonstrations', 'Toy data; hyper-parameters chosen on the data used for the final score', 'Validation-only selection, SHA-256 freeze, one locked-test evaluation'],
    ['Quantum-vs-classical claims', 'Classical baselines often receive different inputs', 'Matched classical control on exactly the same patches and features'],
    ['V0 prototype', 'Tiny samples, random in-folder splits, mislabelled “VQC/HQCC” models', 'Fixed manifest and splits; every model relabelled and re-run'],
    ['Result reporting', 'Static tables only; models cannot be inspected', 'Interactive platform: live replay, upload lab, visual explanations'],
  ], [1.6, 2.6, 2.6]));
  add(h2('1.4', 'User Requirement Analysis'));
  add(P('Three groups of users were identified: **researchers/students** who run experiments and compare models; **reviewers/supervisors** who check results, statistics and reproducibility; and **learners/visitors** who want to understand how quantum image processing works without reading the code. Their needs were turned into the functional and non-functional requirements in Table 1.2 and Table 1.3.'));
  add(tbl('Functional requirements', ['ID', 'Requirement'], [
    ['FR1', 'Load NEU-DET, build a hashed manifest and fixed group-blocked splits for three seeds.'],
    ['FR2', 'Encode images with FRQI and NEQR using real Qiskit circuits and simulate them exactly or with shots.'],
    ['FR3', 'Train classical, quantum-kernel, variational, hybrid and patch-ensemble models and record every run.'],
    ['FR4', 'Select configurations on validation data only, freeze them with SHA-256 hashes and test each once.'],
    ['FR5', 'Compute accuracy, precision, recall, F1, confusion matrices, bootstrap intervals and Holm-corrected tests.'],
    ['FR6', 'Reconstruct all 1,800 images with 20 encoding methods and report MSE, PSNR and SSIM.'],
    ['FR7', 'Show all results in a web dashboard with model comparison, circuits and reconstruction pages.'],
    ['FR8', 'Replay the frozen model live on any test image and accept user-uploaded images (FRQI, NEQR or both).'],
    ['FR9', 'Explain the algorithms visually: step players, circuit highlighting, playground sandbox, CNN feature maps and quizzes.'],
    ['FR10', 'Provide a presentation mode built from the saved V4 results.'],
  ], [0.7, 5.8]));
  add(tbl('Non-functional requirements', ['Category', 'Requirement'], [
    ['Integrity', 'No test-set leakage: the locked test set is opened only by the final stage and every access is logged.'],
    ['Reproducibility', 'Fixed seeds, hashed manifests and selections; every number in the platform is read from saved files.'],
    ['Honesty', 'Every quantum model is shown next to a classical model on the same input; no quantum advantage is claimed without evidence.'],
    ['Performance', 'All 864 V4 runs and the 1,800-image reconstruction study must run on a laptop CPU.'],
    ['Usability', 'Visual-first pages, short text, Beginner/Technical explanation levels, responsive layout.'],
    ['Reliability', 'Automated backend, frontend and browser tests; worker processes isolate native-library crashes.'],
  ], [1.4, 5.1]));
  add(h2('1.5', 'Feasibility Study'));
  add(P(`**Technical feasibility.** Exact simulation is limited by register size. By encoding small patches instead of whole images, every quantum register in the proposed method has at most 8 qubits, and the kernel can be computed in O(PD²) per image instead of O(P²D) per image pair (*P* patches, *D* the state dimension). This made the 864 V4 runs and the reconstruction of all 1,800 images feasible on one laptop (Apple M5, 16 GB RAM). Mature open-source tools exist for every part: Qiskit ${c('qiskit2024')}, scikit-learn ${c('pedregosa2011')}, PyTorch, FastAPI and React.`));
  add(P('**Economic feasibility.** All software is open source and the dataset is public, so no licence or quantum-hardware cost was incurred. The only resources were student time and a laptop.'));
  add(P('**Operational feasibility.** The platform runs locally with two commands (backend and frontend) and works in any modern browser. All results are already saved, so users can explore them without re-running experiments.'));
  add(P('**Schedule feasibility.** The work was carried out from July to December 2026 in protocol versions, each building on the previous one, which kept every stage small enough to complete and verify.'));
  add(P('**Legal and ethical feasibility.** NEU-DET is a public research dataset of steel surfaces and contains no personal information.'));

  // ═════════════ CHAPTER 2 ═════════════
  add(chapter('Literature Review'));
  add(P('This chapter reviews the research the project builds on, grouped by topic, compares the most relevant papers and derives the objectives of the project from the gaps they leave.'));
  add(h2('2.1', 'Quantum Image Representations'));
  add(P(`Le et al. ${c('le2011frqi')} introduced FRQI, which encodes an image of *N* pixels in log₂N + 1 qubits: a position register in uniform superposition and a single colour qubit rotated by an angle proportional to the intensity. Its strengths are compactness and a preparation circuit built from controlled rotations, but intensities can only be recovered statistically from many measurements. Zhang et al. ${c('zhang2013neqr')} proposed NEQR, which replaces the angle with a *q*-bit binary code so that intensities can be read out exactly, at the cost of extra qubits and many multi-controlled gates. The survey by Yan et al. ${c('yan2016survey')} lists many variants that trade qubits against precision. These papers mainly study preparation complexity and geometric image operations; they rarely ask whether the encodings are useful for classifying real images. Preparation cost is also significant: an FRQI circuit needs one multi-controlled rotation per pixel, and our measurements show more than 8,000 transpiled gates for a single 8×8 patch.`));
  add(h2('2.2', 'Quantum Kernels and Their Limits'));
  add(P(`Havlíček et al. ${c('havlicek2019')} and Schuld and Killoran ${c('schuld2019feature')} showed that a circuit mapping data to a quantum state defines a kernel that a classical SVM can use, and Schuld ${c('schuld2021kernel')} argued that most supervised quantum models are in fact kernel methods. These demonstrations used small synthetic datasets designed for the feature map. Huang et al. ${c('huang2021power')} showed that classical learners with access to the same data can often match quantum kernels, and Thanasilp et al. ${c('thanasilp2024')} proved that kernel values on large registers concentrate exponentially, making them hard to estimate with finite measurements. Both results motivate small registers and matched classical controls.`));
  add(h2('2.3', 'Variational and Convolution-Style Quantum Models'));
  add(P(`Variational quantum algorithms ${c('cerezo2021vqa')} train parameterised circuits with classical optimisers but suffer from barren plateaus, where gradients vanish as circuits grow ${c('mcclean2018barren')}. Henderson et al. ${c('henderson2020quanv')} applied small random circuits to local image patches (quanvolution) and found performance similar to classical networks with comparable random layers. Our method shares the idea of processing local patches with small circuits, but uses fixed, interpretable FRQI/NEQR encodings and a kernel, and it averages patch states on purpose so that the representation is tolerant to shifts.`));
  add(h2('2.4', 'Steel Surface Defect Recognition'));
  add(P(`Song and Yan ${c('song2013neu')} published the NEU database and classified it with noise-robust completed local binary patterns; He et al. ${c('he2020neudet')} added bounding boxes (NEU-DET) and an end-to-end convolutional detector. Texture descriptors such as LBP ${c('ojala2002lbp')} and GLCM ${c('haralick1973glcm')} summarise how often local intensity patterns occur, independently of where they occur, and remain strong baselines. The patch-ensemble kernel follows the same principle but measures the similarity of local patterns through the overlap of their quantum states.`));
  add(h2('2.5', 'Comparison'));
  add(P('Table 2.1 compares the eight most relevant papers with respect to method, data, key result, limitation and relevance to this project.'));
  add(tbl('Comparison of key related work', ['Paper', 'Method', 'Data', 'Key result', 'Limitation', 'Relevance here'], [
    [`Le et al. ${c('le2011frqi')}`, 'FRQI angle encoding', 'Illustrative images', 'Compact log₂N+1-qubit encoding', 'Statistical read-out; no classification', 'Encoding used in our kernel'],
    [`Zhang et al. ${c('zhang2013neqr')}`, 'NEQR basis encoding', 'Illustrative images', 'Exact intensity retrieval', 'q colour qubits; costly gates', 'Second encoding compared'],
    [`Havlíček et al. ${c('havlicek2019')}`, 'Quantum kernel and VQC on hardware', 'Synthetic 2-D data', 'High accuracy on data built for the feature map', 'Toy data; no real images', 'Kernel framework adopted'],
    [`Schuld & Killoran ${c('schuld2019feature')}`, 'Feature Hilbert-space view', 'Small demos', 'Encodings define kernels', 'No large evaluation', 'Theoretical basis'],
    [`Huang et al. ${c('huang2021power')}`, 'Classical vs quantum kernels', 'Engineered labels', 'Classical models often match quantum ones', 'Advantage only on special tasks', 'Motivates matched control'],
    [`Thanasilp et al. ${c('thanasilp2024')}`, 'Kernel concentration analysis', 'Theory, numerics', 'Kernel values concentrate on large registers', 'Generic encodings', 'Motivates small patch registers'],
    [`Henderson et al. ${c('henderson2020quanv')}`, 'Quanvolution on patches', 'MNIST', 'Similar to classical random layers', 'Digits only; no advantage', 'Patch-wise quantum processing'],
    [`Song & Yan ${c('song2013neu')}`, 'Completed LBP features', 'NEU (6 classes)', 'High accuracy, robust to noise', 'Classical, hand-crafted', 'Dataset and texture baseline'],
  ], [1.25, 1.2, 0.95, 1.3, 1.25, 1.15]));
  add(h2('2.6', 'Research Gap'));
  add(P('Work on quantum image representations does not test classification on real textured images; work on quantum kernels uses synthetic data; and work on steel defects is purely classical. None of the compared papers reports a classical control that receives exactly the same input as the quantum model, and none protects a test set against repeated use during model selection. This project fills that gap.'));
  add(h2('2.7', 'Objectives of Project'));
  add(P('The objectives below follow from the gaps above. Each was implemented and is evaluated in Chapter 5.'));
  add(tbl('Objectives of the project and where they are implemented', ['No.', 'Objective', 'Implemented in'], [
    ['O1', 'Build a leakage-controlled evaluation protocol on NEU-DET (hashed manifest, group-blocked splits, validation-only selection, SHA-256 freeze, one locked-test evaluation).', 'Sections 3.1, 4.10.9; Algorithm 4.2'],
    ['O2', 'Implement and evaluate FRQI and NEQR encodings with real Qiskit circuits, quantum kernels (Product-RY, ZZ-Linear, ZZ-Full), PQK, VQC and hybrid CNN + quantum models.', 'Sections 4.10.1–4.10.6; Chapter 5'],
    ['O3', 'Design a patch-ensemble mixed-state kernel that makes FRQI/NEQR comparison translation-tolerant and keeps registers ≤ 8 qubits (RQ1).', 'Section 4.10.7; Section 5.4'],
    ['O4', 'Test whether any gain comes from the quantum encoding using matched classical controls and pre-declared statistics (RQ2).', 'Sections 5.2, 5.5'],
    ['O5', 'Measure circuit resources and reconstruction quality of all 1,800 images with 20 methods.', 'Section 5.8'],
    ['O6', 'Build an interactive research and learning platform that shows every saved result and explains the algorithms visually.', 'Section 4.11'],
  ], [0.5, 4.3, 1.7]));

  // ═════════════ CHAPTER 3 ═════════════
  add(chapter('Exploratory Data Analysis'));
  add(h2('3.1', 'Dataset'));
  add(P(`NEU-DET ${c('song2013neu', 'he2020neudet')} contains ${eda.n.toLocaleString()} grayscale images of hot-rolled steel strips, each ${eda.sizes[0][0]}×${eda.sizes[0][1]} pixels, with 300 images in each of six classes. The dataset is distributed in a training folder (240 images per class) and a validation folder (60 per class). No scraping was needed: the official folders were read directly, every file was hashed with SHA-256, and the result was stored as a dataset manifest (manifest id ${v2.dataset.manifest_id}).`));
  add(P('**Split protocol.** The 360 images of the official validation folder form the **locked test set**, which is read only by the final evaluation stage. The 1,440 images of the training folder are split into 1,080 training and 360 validation images by a **group-blocked split**: consecutive file indices are grouped into blocks of 20 and three blocks per class go to validation, so that near-duplicate neighbouring images never fall on both sides. The split is repeated with seeds 0, 1 and 2. Table 3.1 shows that every split is balanced.'));
  add(tbl('NEU-DET splits per class (identical for seeds 0, 1 and 2)', ['Class', 'Train', 'Validation', 'Locked test', 'Total'], [
    ...CL.map((k) => [CLN[k], '180', '60', String(eda.counts.validation[k]), String(eda.counts.train[k] + eda.counts.validation[k])]),
    ['All six classes', '1,080', '360', '360', '1,800'],
  ], [2.4, 1, 1, 1, 1], { numeric: true, highlight: [6] }));
  add(fig(px('Fig16_dataset_samples.png'), 'Sample NEU-DET images of the six defect classes.', 6.2));
  add(h2('3.2', 'Exploratory Data Analysis and Visualizations'));
  add(P(`**Class balance.** ${figRef()} confirms that the dataset is perfectly balanced in both folders, so accuracy is a fair headline metric and macro-F1 equals the average of per-class F1 scores.`));
  add(fig(fx('E1_class_distribution.png'), 'Class distribution in the training and test (official validation) folders.', 5.6));
  add(P(`**Brightness and contrast.** ${figRef()} and Table 3.2 show the mean brightness of each class in the two folders. Most classes are similar, but **rolled-in scale** is much darker in the test folder (${bV['rolled-in_scale'][0].toFixed(3)}) than in the training folder (${bT['rolled-in_scale'][0].toFixed(3)}), and crazing is brighter (${bT.crazing[0].toFixed(3)} → ${bV.crazing[0].toFixed(3)}). This distribution shift matters later: models that use absolute intensities are sensitive to it, and per-image contrast stretching removes it.`));
  add(fig(fx('E2_brightness_contrast.png'), 'Mean brightness and contrast per class in the training and test folders.', 6.3));
  add(tbl('Mean image brightness per class (± standard deviation over images)', ['Class', 'Training folder', 'Test folder', 'Shift'], CL.map((k) => [CLN[k], `${bT[k][0].toFixed(3)} ± ${bT[k][1].toFixed(3)}`, `${bV[k][0].toFixed(3)} ± ${bV[k][1].toFixed(3)}`, `${bV[k][0] - bT[k][0] >= 0 ? '+' : '−'}${Math.abs(bV[k][0] - bT[k][0]).toFixed(3)}`]), [2, 1.6, 1.6, 1], { numeric: true, highlight: [4] }));
  add(P(`**Intensity distributions.** The histograms in ${figRef()} show that each class occupies a characteristic range of grey levels, but the ranges overlap strongly; brightness alone cannot separate the classes.`));
  add(fig(fx('E3_intensity_histograms.png'), 'Pixel-intensity histograms per class.', 6.2));
  add(P(`**Class-average images.** ${figRef()} averages all images of each class. Scratches and rolled-in scale keep a visible structure, whereas crazing, pitted surface and inclusion average out to nearly uniform grey: their defects appear at random positions. This is the key observation behind the proposed method: a classifier that compares pixels at fixed positions cannot recognise textures whose position varies.`));
  add(fig(fx('E4_class_average_images.png'), 'Average image of each class over all 300 images.', 6.2));
  add(h2('3.3', 'Preprocessing and Feature Engineering'));
  add(P('Several input representations were engineered across the protocols:'));
  add(bullets([
    '**Resizing and scaling:** images are converted to grayscale, resized to S×S pixels (2 to 128) and scaled to [0, 1].',
    '**Per-image contrast stretch:** x′ = (x − min x)/(max x − min x), computed from the image itself, so no statistics leak between images; it removes the brightness shift found above.',
    '**Patch extraction (V4):** the image is cut into p×p patches with stride s, giving P = ((S − p)/s + 1)² patches; p is a power of two so that it maps onto a position register.',
    '**Pixel PCA (V2):** 64×64 pixels → StandardScaler → PCA with k = 4, 6 or 8 components, fitted on the training split only, then min–max scaled to angles in [0, π].',
    `**Texture features (V3):** LBP ${c('ojala2002lbp')} and GLCM ${c('haralick1973glcm')} descriptors compressed to 8 or 12 principal components.`,
    '**CNN features:** a frozen ImageNet-pretrained MobileNetV3-small turns each image into 576 numbers (global average of its last 576 feature maps), followed by PCA to k = 4, 6 or 8.',
  ]));
  add(P(`${figRef()} shows preprocessing on a real image and the resulting mixed state, and ${figRef(2)} shows how patching changes what the kernel sees compared with whole-image PCA.`));
  add(fig(px('Fig17_preprocessing_and_mixed_state.png'), 'Preprocessing of a real image (resize, contrast stretch, patches) and its mixed state.', 6.3));
  add(fig(px('Fig21_patch_and_pca_before_after.png'), 'Patch representation versus whole-image PCA representation of the same images.', 6.3));

  // ═════════════ CHAPTER 4 ═════════════
  add(chapter('Methodology'));
  add(P('This chapter describes the languages and packages used, the users and constraints, the system design (use cases, data flows, data storage), the algorithms and the implementation of the platform.'));
  add(h2('4.1', 'Introduction to Languages (Front End and Back End)'));
  add(P('**Back end: Python 3.11.** Python was chosen for its scientific ecosystem: Qiskit for quantum circuits, NumPy for exact statevector algebra, scikit-learn for SVMs and statistics, and PyTorch for the CNN. The REST API is written with **FastAPI**, served by Uvicorn, with three read-only routers (/api/v2, /api/v3, /api/v4) and live endpoints for the walkthrough, upload lab, CNN studio and hybrid pipeline.'));
  add(P('**Front end: TypeScript with React 19.** The dashboard is a single-page application built with Vite, styled with Tailwind CSS and charted with Recharts and hand-written SVG. React Router provides 19 pages. TypeScript types mirror the API responses, so mistakes in data handling are caught at compile time.'));
  add(h2('4.2', 'Supporting Languages and Packages'));
  add(tbl('Main packages and versions', ['Package', 'Version', 'Purpose'], [
    ['Qiskit / Qiskit Aer', '2.5.2 / 0.17.2', 'FRQI/NEQR encoder circuits, transpilation, statevector and shot simulation'],
    ['NumPy / SciPy', '2.4.6 / 1.17.1', 'Exact statevector simulator, density matrices, kernels'],
    ['scikit-learn', '1.9.1', 'SVM with precomputed kernels, PCA, scalers, metrics'],
    ['PyTorch / torchvision', '2.15.0 / 0.29.2', 'Frozen MobileNetV3-small features, small CNN'],
    ['scikit-image / Pillow', '0.26.0 / 12.3.0', 'LBP, GLCM, SSIM, image loading'],
    ['FastAPI / Uvicorn', '0.142.2 / 0.54.0', 'REST API and server'],
    ['pandas / Matplotlib', '3.0.6 / 3.11.2', 'Tables and report figures'],
    ['React / React Router', '19.2 / 7.18', 'Front-end components and routing'],
    ['Vite / TypeScript', '8.3 / 6.0', 'Build tool and typed front end'],
    ['Tailwind CSS / Recharts', '3.4 / 3.10', 'Styling and charts'],
    ['Vitest / Testing Library / Playwright', '5.1 / 16.3 / —', 'Front-end unit tests and browser tests'],
    ['pytest', '—', 'Back-end and API tests'],
  ], [2.2, 1.4, 3.4]));
  add(h2('4.3', 'User Characteristics'));
  add(bullets([
    '**Researcher/student:** comfortable with Python and machine learning; runs experiment scripts, inspects runs and compares models.',
    '**Reviewer/supervisor:** checks protocol integrity, statistics and conclusions; uses the results pages, model comparison and presentation mode.',
    '**Learner/visitor:** may have no quantum background; uses the learning pages, Explain buttons, playground and quizzes, with a Beginner/Technical switch for explanation depth.',
  ]));
  add(h2('4.4', 'Constraints'));
  add(bullets([
    'Every quantum register has at most 8 qubits (exact classical simulation; no quantum hardware or noise model).',
    'Models are chosen without access to the test images, and each frozen model is tested exactly once.',
    'All computation runs on a single laptop CPU; experiments must finish within the project period.',
    'The platform is read-only with respect to results: it never retrains or re-selects models.',
    'One defect class per image; defect localisation and quantum-advantage claims are out of scope.',
  ]));
  add(h2('4.5', 'Use Case Model, Flow Chart and DFDs'));
  add(P(`${figRef()} shows the use-case model. The researcher runs experiments and explores results, the reviewer compares models and statistics, and the experiment runner (scripts) performs selection, freezing and the locked test.`));
  add(fig(fx('D1_use_case_diagram.png'), 'Use-case diagram of the Q-ImageLab system.', 5.4));
  add(P(`${figRef()} gives the data-flow diagrams: the level-0 context diagram and the level-1 decomposition into data, encoding, training, evaluation and presentation processes.`));
  add(fig(fx('D2_data_flow_diagrams.png'), 'Data-flow diagrams: (a) level 0 (context) and (b) level 1.', 6.0));
  add(P(`${figRef()} is the flow chart of the experiment pipeline, and ${figRef(2)} the overall system architecture. Orange blocks contain the quantum part, which is simulated exactly on a CPU.`));
  add(fig(fx('D3_pipeline_flowchart.png'), 'Flow chart of the experiment pipeline.', 3.9));
  add(fig(fx('A1_architecture.png'), 'System architecture: classification path (solid arrows) and modules that reuse its outputs (dashed).', 6.0));
  add(fig(px('Fig01_methodology_flowchart.png'), 'Methodology: (a) leakage-controlled protocol; (b) patch-ensemble mixed-state kernel for one image.', 6.3));
  add(h2('4.6', 'Database Design'));
  add(P('The project does not need a relational database. All data are immutable experiment records, so they are stored as **versioned JSON/CSV files** in a result store per protocol (results/qml_v2, qml_v3, qml_v4). Each protocol may only write to its own folder; earlier folders are read-only, and copied inputs (manifest, splits, image caches) are verified by SHA-256 against their source. The API reads these files and caches them in memory. Table 4.2 lists the stores.'));
  add(tbl('Result store layout (results/qml_v4; V2 and V3 follow the same pattern)', ['Path', 'Contents'], [
    ['manifests/', 'Dataset manifest (every image path, class, block, SHA-256), split files for seeds 0–2, split-integrity report, provenance'],
    ['experiments/<experiment_id>/', 'One folder per run: config.json, validation_metrics.json, predictions.csv, confusion_matrix.json, circuit_stats.json, status.json, model/'],
    ['aggregates/selection/', 'Best configuration per group (validation-selected)'],
    ['aggregates/frozen_selection.json', 'Frozen selections, pre-declared comparison plan and SHA-256 hashes'],
    ['aggregates/v4_results.json', 'Locked-test metrics, references and the eight comparisons'],
    ['aggregates/per_image_predictions.json', 'Saved prediction of every selected model of V2–V4 for each of the 360 test images'],
    ['reconstruction_full/', 'Reconstruction of all 1,800 images by 20 methods (arrays, metrics, summary)'],
    ['logs/', 'Run logs and the locked-test access log'],
  ], [2.4, 4.1]));
  add(h2('4.7', 'Table Structure'));
  add(P('The main records and their fields are shown in Table 4.3. Each experiment record is identified by experiment_id = group + configuration hash + seed, which makes every run traceable from the platform back to its files.'));
  add(tbl('Structure of the main records', ['Record', 'Key', 'Main fields'], [
    ['Image (manifest)', 'rel_path', 'class, class_idx, folder/role, index, block, group_id, sha256'],
    ['Split', 'seed', 'train, val, locked-test image lists; split hash'],
    ['Configuration', 'config_key', 'group, representation, S, p, s, b or q, norm, C, γ'],
    ['Experiment run', 'experiment_id', 'config_key, seed, validation metrics, status, circuit_stats, train/inference time'],
    ['Prediction (CSV)', 'experiment_id + image', 'split, y_true, y_pred, true_class, pred_class, confidence'],
    ['Selection', 'group', 'selected config_key, val mean ± std, SHA-256'],
    ['Test result', 'group', 'test accuracy, precision, recall, F1 (mean ± std), per-seed values, confusion matrix, per-class F1'],
  ], [1.5, 1.4, 3.6]));
  add(h2('4.8', 'ER Diagram'));
  add(P(`${figRef()} shows the entity-relationship model of the result store. An image belongs to many splits and configurations; a configuration is run once per seed (1 : 3); each run produces predictions for many images; and each group has exactly one frozen selection.`));
  add(fig(fx('D4_er_diagram.png'), 'Entity-relationship diagram of the result store (stored as JSON/CSV files).', 6.0));
  add(h2('4.9', 'Assumptions and Dependencies'));
  add(bullets([
    'Each image contains one dominant defect class, as labelled by its folder.',
    'The official NEU-DET validation folder is representative of unseen data and is used only as the locked test set.',
    'Exact noiseless simulation is an upper bound on what hardware could achieve with the same circuits.',
    'The closed-form patch amplitudes equal the Qiskit encoder statevectors (verified by unit tests).',
    'Dependencies: the packages in Table 4.1, the public ImageNet weights of MobileNetV3-small and a modern web browser.',
  ]));
  add(h2('4.10', 'Algorithm Discussion'));
  add(P(`${figRef()} gives an overview of the pipeline of every model family evaluated in this project, from the classical RBF-SVM baseline to the proposed patch-ensemble kernel. The quantum steps (orange) are executed as exact simulations on a CPU. The subsections below describe each algorithm.`));
  add(fig(fx('M1_model_architectures.png'), 'Pipelines of the model families: classical RBF-SVM, QKC, PQK, VQC, hybrid CNN + quantum and the proposed patch-ensemble kernel (blue: classical step; orange: quantum step; green: frozen pretrained CNN).', 6.3));
  add(h3('4.10.1', 'FRQI'));
  add(P(`Consider a patch of N = 2ⁿ×2ⁿ pixels with intensities xᵢ ∈ [0, 1]. FRQI ${c('le2011frqi')} uses 2n position qubits and one colour qubit (Equation 4.1). The encoder applies Hadamard gates to the position qubits and then, for each pixel, a multi-controlled RY(2θᵢ) rotation on the colour qubit, surrounded by X gates that select the pixel's position. b is an angle scale (b = 1 is the original definition).`));
  add(eq(fx('Q1_frqi.png'), 5.2));
  add(h3('4.10.2', 'NEQR'));
  add(P(`NEQR ${c('zhang2013neqr')} uses q colour qubits that hold the quantised intensity cᵢ = round(xᵢ(2^q − 1)) (Equation 4.2). For each pixel, a multi-controlled X gate flips every colour qubit whose bit is 1. FRQI therefore needs 2n + 1 qubits and NEQR 2n + q.`));
  add(eq(fx('Q2_neqr.png'), 4.8));
  add(P(`For two FRQI states of the same size the overlap is ⟨ψᴬ|ψᴮ⟩ = (1/N) Σᵢ cos(θᵢᴬ − θᵢᴮ): it compares pixels at the same index only. ${figRef()} and ${figRef(2)} show the circuits that the project's FRQI and NEQR encoders build for the 2×2 example image [[0.2, 0.6], [0.9, 0.4]] (NEQR with q = 2 bits, i.e. codes 1, 2, 3, 1).`));
  add(fig(fx('C1_frqi_circuit_2x2.png'), 'FRQI circuit for a 2×2 image built by the project encoder: Hadamards on the two position qubits, then, for each pixel, a controlled RY rotation (built from RY gates and CNOTs), framed by X gates that select its position.', 6.3));
  add(fig(fx('C2_neqr_circuit_2x2.png'), 'NEQR circuit for the same 2×2 image (q = 2): multi-controlled X gates write the binary code of each pixel into the colour qubits.', 6.0));
  add(h3('4.10.3', 'Quantum Kernel Classifier (QKC) and Feature Maps'));
  add(P(`A feature map U(x) prepares |φ(x)⟩ = U(x)|0⟩ and the fidelity kernel K(x, y) = |⟨φ(x)|φ(y)⟩|² (Equation 4.3) is used by an SVM ${c('havlicek2019', 'schuld2019feature')}. Three feature maps were implemented on PCA, texture or CNN features scaled to angles: **Product-RY** (one RY(xᵢ) per qubit; no entanglement, so the kernel equals Πᵢ cos²((xᵢ − yᵢ)/2) and is classically computable), **ZZ-Linear** (Hadamards, P(2xᵢ) and CX–P(2(π − xᵢ)(π − xⱼ))–CX blocks on neighbouring qubits) and **ZZ-Full** (the same on all pairs). A bandwidth b rescales the angles to control kernel concentration ${c('thanasilp2024')}.`));
  add(eq(fx('Q7_fidelity.png'), 5.6));
  add(P(`${figRef()} to ${figRef(3)} show the three feature maps on four qubits for the example input x = (0.6, 1.4, 2.2, 0.9). Product-RY has no entangling gates; ZZ-Linear entangles neighbouring qubits and ZZ-Full every pair, so its CX count grows quadratically with the number of qubits.`));
  add(fig(fx('C3_product_ry.png'), 'Product-RY feature map (4 qubits): one RY(xᵢ) rotation per qubit, no entanglement.', 1.3));
  add(fig(fx('C4_zz_linear.png'), 'ZZ-Linear feature map (4 qubits): Hadamard and phase layer, then CX–P–CX blocks on neighbouring qubits.', 5.4));
  add(fig(fx('C5_zz_full.png'), 'ZZ-Full feature map (4 qubits): the same CX–P–CX block on all six qubit pairs.', 6.3));
  add(h3('4.10.4', 'Projected Quantum Kernel (PQK)'));
  add(P(`Following Huang et al. ${c('huang2021power')}, each encoded state is projected onto its single-qubit reduced density matrices, described by Bloch vectors bq = (⟨Xq⟩, ⟨Yq⟩, ⟨Zq⟩). The kernel is K(x, y) = exp(−γ Σq ‖bq(x) − bq(y)‖²/2). It needs only 3k local expectation values per image and avoids the concentration of global overlaps.`));
  add(h3('4.10.5', 'Variational Quantum Classifier (VQC)'));
  add(P(`Features are encoded with RY gates, followed by L layers of trainable RY(θ)·RZ(θ) rotations and a CNOT ring; expectation values ⟨Zᵢ⟩ form the class scores. Gradients are computed with the parameter-shift rule ∂⟨O⟩/∂θ = (⟨O⟩(θ + π/2) − ⟨O⟩(θ − π/2))/2 and optimised with Adam, COBYLA or SPSA ${c('cerezo2021vqa')}. Frozen-circuit and encoding-only controls check whether the trained circuit adds anything beyond the classical read-out. ${figRef()} shows the ansatz with L = 2 layers on four qubits.`));
  add(fig(fx('C6_vqc_ansatz.png'), 'VQC ansatz (4 qubits, L = 2): RY encoding of the input angles, then two layers of trainable RY·RZ rotations and a CNOT ring, followed by measurement (parameter values are illustrative).', 6.3));
  add(h3('4.10.6', 'Hybrid CNN + Quantum Models'));
  add(P('A frozen MobileNetV3-small turns each image into 576 numbers; StandardScaler and PCA (fitted on the training split) reduce them to k = 4, 6 or 8 angles, one per qubit; a QKC or VQC then classifies them. Classical RBF-SVM and logistic-regression controls receive exactly the same k features.'));
  add(h3('4.10.7', 'Proposed Patch-Ensemble Mixed-State Kernel'));
  add(P('Each patch k of an image is encoded as |ψₖ⟩ with FRQI or NEQR. The image is represented by the uniform mixture of its patch states (Equation 4.4), a D×D density matrix with D = 2^(2·log₂p + 1) for FRQI and 2^(2·log₂p + q) for NEQR. Two images are compared by the Hilbert–Schmidt inner product (Equation 4.5), the average squared overlap over all pairs of patches, so a texture element that appears anywhere in both images contributes regardless of its position.'));
  add(eq(fx('Q3_rho.png'), 3.8));
  add(eq(fx('Q4_kernel.png'), 4.2));
  add(P(`K is positive semi-definite because it is an inner product of density matrices. The swap test ${c('buhrman2001')} estimates it directly: an ancilla measured after a controlled swap of two registers gives Pr[0] = ½(1 + Tr(ρσ)) for any states ρ and σ (Equation 4.6). Averaging single-shot swap tests between randomly drawn patches of A and B therefore estimates K(A, B) without preparing ρ as a whole, using two patch registers plus one ancilla.`));
  add(eq(fx('Q5_swap.png'), 3.0));
  add(P(`${figRef()} shows the swap-test circuit for two 3-qubit patch registers; for the frozen FRQI model each register has 7 qubits, giving 15 qubits in total.`));
  add(fig(fx('C7_swap_test.png'), 'Swap test between two patch registers: Hadamard on the ancilla, controlled swaps of corresponding qubits, Hadamard and measurement; Pr[ancilla = 0] = ½(1 + Tr(ρσ)).', 5.0));
  add(P(`**Properties.** (i) *Shift tolerance:* shifting the content by a multiple of the stride only re-orders interior patches, and the mixture does not depend on order. (ii) *Cost:* forming each ρ once costs O(PD²) per image and each kernel entry O(D²), much cheaper than O(P²D) per pair when P² ≫ D. For the frozen FRQI model (64×64 image, 8×8 patches, stride 4) there are P = 225 patches of 7 qubits, so ρ is 128×128. ${figRef()} illustrates the method on a real training image.`));
  add(fig(px('Fig02_patch_encoding_illustration.png'), 'The method on a real training image with the frozen FRQI settings: image and patches, one patch, its 7-qubit amplitudes, the mixed state ρ and the kernel between classes.', 6.3));
  add(h3('4.10.8', 'Classifier'));
  add(P(`A multi-class SVM ${c('cortes1995')} with a precomputed kernel (one-versus-one, scikit-learn ${c('pedregosa2011')}) is trained on the kernel matrix between the 1,080 training images. Algorithm 4.1 summarises training and prediction.`));
  add(...algorithm('4.1', 'Patch-ensemble kernel classifier', [
    'Input: training images {(Iⱼ, yⱼ)}, query image I*, encoding E ∈ {FRQI, NEQR}, S, p, s, b or q, stretch flag, C',
    'for each image I in {I₁ … Iₙ, I*}:',
    '    resize I to S×S, scale to [0, 1], apply the contrast stretch if enabled',
    '    extract the P patches of side p and stride s',
    '    for k = 1 … P: prepare |ψₖ⟩ with encoder E',
    '    ρ_I ← (1/P) Σₖ |ψₖ⟩⟨ψₖ|',
    'K_jj′ ← Tr(ρ_Iⱼ ρ_Iⱼ′) for all training pairs',
    'train a one-vs-one SVM with precomputed kernel K and parameter C',
    'k* ← [Tr(ρ_I* ρ_Iⱼ)] for j = 1 … n;  ŷ* ← SVM prediction for k*',
  ]));
  add(h3('4.10.9', 'Leakage-Controlled Evaluation Protocol'));
  add(P(`Algorithm 4.2 gives the protocol. Every configuration is trained with three seeds and scored on validation data only; the best configuration per group is written to disk with its SHA-256 hash; only then is the locked test set read, once per frozen model, and every access is logged. Eight comparisons were declared before testing and are tested with a paired sign-flip permutation test (10,000 permutations), paired-bootstrap 95 % confidence intervals ${c('efron1993')}, McNemar's test per seed ${c('mcnemar1947')} and Holm correction ${c('holm1979')}.`));
  add(...algorithm('4.2', 'Leakage-controlled selection and evaluation', [
    'Input: model groups 𝒢, grid Θ_g per group, seeds r ∈ {0, 1, 2}, splits (train_r, val_r), locked test set T',
    'for each g ∈ 𝒢, θ ∈ Θ_g, r ∈ {0, 1, 2}: train on train_r; record macro-F1 on val_r',
    'for each g ∈ 𝒢: θ*_g ← argmax over θ of the mean validation macro-F1 over seeds',
    'write the selections to disk and store their SHA-256 hashes',
    'for each g ∈ 𝒢: abort if any selection hash has changed;',
    '    for r = 0 … 2: evaluate the saved model (θ*_g, train_r) on T once; log the access',
    'run the eight pre-declared comparisons with Holm correction',
  ]));
  add(h3('4.10.10', 'Evaluation Metrics'));
  add(P(`Accuracy is the headline metric because the test set is balanced; macro-F1 (Equation 4.7) weights all classes equally and is the selection criterion; per-class F1 shows which defects fail. Reconstruction quality is measured with the mean squared error (MSE), PSNR = 10·log₁₀(1/MSE) and SSIM ${c('wang2004ssim')}.`));
  add(eq(fx('Q8_f1.png'), 3.9));
  add(h2('4.11', 'Implementation of Algorithm with Screenshots'));
  add(P(`The algorithms are implemented in Python modules (src/v2 for data, features, quantum kernels, VQC and CNN; src/v3 for texture features and PQK; src/v4 for the patch-ensemble kernel, upload lab, CNN studio and learning centre) and driven by experiment scripts (scripts/v2–v4). The FRQI and NEQR encoders build real Qiskit circuits ${c('qiskit2024')}; a unit test checks that the kernel computed from density matrices equals the mean squared overlap of the Qiskit statevectors. The platform reads only saved results.`));
  add(P('Screenshots of all the main screens of the platform (results, model families, interactive pipeline, live model replay, circuits, learning lab, sandbox, CNN studio, upload lab, reconstruction study, quantum-versus-classical view, quiz and presentation mode) are given in Appendix A.'));
  add(P('**Testing.** The implementation is verified by 201 back-end tests (pytest: encoders, kernels, protocol integrity, every API endpoint, including a check that the live walkthrough reproduces all 360 saved predictions), 48 front-end tests (Vitest: pages, learning components, the in-browser simulator checked against the Python kernel to 10⁻¹² and gate counts checked against Qiskit) and browser end-to-end checks (16/16 for V4 pages and 10/10 for V3 pages).'));

  // ═════════════ CHAPTER 5 ═════════════
  add(chapter('Results'));
  add(h2('5.1', 'Results Across Protocol Versions'));
  add(P(`${figRef()} shows the history of the project. Both encodings stayed near 60 % in protocols V2 and V3, even after re-tuning, and rose above 80 % with the patch-ensemble kernel of V4.`));
  add(fig(px('Fig04_frqi_neqr_across_protocols.png'), 'Locked-test accuracy of FRQI and NEQR models across protocols V2, V3 and V4 (mean ± s.d. over three seeds); dashed line: chance (16.7 %).', 5.6));
  add(P(`Table 5.1 summarises the best model of each family in protocol V2. A frozen MobileNetV3 with a linear classifier is the strongest model overall, hybrid CNN + quantum models are close behind, and every model that works on raw pixels, quantum or classical, stays near 60 %.`));
  add(tbl('Protocol V2: best model of each family (locked test, mean over three seeds)', ['Family', 'Models', 'Best model', 'Test accuracy (%)'],
    v2.families.map((f) => [f.family, String(f.n_models), f.best_name, ms(f.best_test_accuracy)]), [2, 0.8, 2.9, 1.3], { numeric: true }));
  add(P(`${figRef()} places all 163 models selected in protocols V2–V4 on one axis. Quantum models on pixel or PCA features form a broad cloud, mostly between 30 % and 65 %; quantum, hybrid and classical models on CNN or texture features cluster above 85 %; and the four V4 patch-ensemble models (81–88 %) are the only pixel-based quantum models above 80 %.`));
  add(fig(fx('M4_all_models.png'), 'Locked-test accuracy of all 163 selected models of V2–V4 (one dot per model, mean over three seeds), coloured by model type; dashed line: chance (16.7 %).', 6.3));
  add(h2('5.2', 'Model Family Comparison (Protocol V3)'));
  add(P('Protocol V3 ran every model family on the same feature sets. For each family, the representative was chosen by **validation** macro-F1 (never by test score). Table 5.2 lists their locked-test metrics and timings, and Table 5.3 the representative architectures.'));
  add(tbl('Model families in V3 (validation-selected; locked test, mean over three seeds)', ['Family', 'Accuracy', 'Precision', 'Recall', 'F1', 'Train time', 'Inference / image'],
    fam.families.map((f) => [f.label, pct(f.test_accuracy?.mean), pct(f.test_precision_macro?.mean), pct(f.test_recall_macro?.mean), pct(f.test_f1_macro?.mean),
      f.train_time_s?.mean >= 1 ? `${f.train_time_s.mean.toFixed(1)} s` : `${(1000 * f.train_time_s.mean).toFixed(0)} ms`, `${(f.inference_ms_per_image?.mean ?? 0).toPrecision(2)} ms`]),
    [2.1, 0.8, 0.8, 0.8, 0.7, 0.9, 1.0], { numeric: true }));
  add(P(`${figRef()} plots the four metrics of each family representative and ${figRef(2)} their training and inference times on a log scale. QKC on texture features and the hybrid model reach the highest scores; PQK and VQC fall about 20 pp behind on the same CNN features. VQC is by far the most expensive to train (about 10³ s per run against milliseconds for the RBF-SVM), and every quantum family is one to three orders of magnitude slower at inference than the classical baseline, because the quantum steps are simulated.`));
  add(fig(fx('M2_family_metrics.png'), 'Locked-test accuracy, macro-precision, macro-recall and macro-F1 of the validation-selected representative of each model family (V3, mean over three seeds).', 6.2));
  add(fig(fx('M3_family_timing.png'), 'Training time per run and inference time per image of each family representative (log scale; quantum families simulated on a CPU).', 6.3));
  add(tbl('Architecture and main limitation of each family representative', ['Family', 'Architecture', 'Main limitation (from the results)'],
    fam.families.map((f) => {
      const m = f.matched_rbfsvm?.test_accuracy?.mean, d = m != null ? `${(100 * (f.test_accuracy.mean - m) >= 0 ? '+' : '−')}${Math.abs(100 * (f.test_accuracy.mean - m)).toFixed(1)} pp vs RBF-SVM on the same features` : 'Classical baseline';
      return [f.label, f.architecture.join(' → '), f.key === 'vqc' ? `${d}; slowest to train` : d];
    }), [1.6, 3.0, 2.0]));
  add(P(`Two findings stand out. First, **the features decide the ceiling**: the best quantum model on normalised pixels reaches ${pct(fam.quantum_by_feature_source[0].test_accuracy)} %, while the same kind of model on texture features reaches ${pct(fam.quantum_by_feature_source[fam.quantum_by_feature_source.length - 1].test_accuracy)} %. Second, **on identical inputs quantum and classical kernels are within ${(100 * Math.max(...fam.matched_pairs.map((x) => Math.abs(x.quantum_acc - x.rbfsvm_acc)))).toFixed(1)} percentage points** of each other for every matched feature set (Table 5.4).`));
  add(tbl('Matched pairs: quantum kernel vs classical RBF-SVM on the same features (test accuracy, %)', ['Features', 'Feature set', 'Quantum kernel', 'RBF-SVM', 'Difference (pp)'],
    fam.matched_pairs.map((x) => [x.features, x.feature_set, pct(x.quantum_acc), pct(x.rbfsvm_acc), `${x.quantum_acc - x.rbfsvm_acc >= 0 ? '+' : '−'}${Math.abs(100 * (x.quantum_acc - x.rbfsvm_acc)).toFixed(1)}`]),
    [2, 1.2, 1.2, 1.1, 1.2], { numeric: true }));
  add(h2('5.3', 'Main Results of the Proposed Method (V4)'));
  const mainRows = [
    ['**Proposed:** FRQI, 8×8 patches', 'quantum (sim.)', pct(fr.val_f1_macro.mean), ms(fr.test_accuracy), ms(fr.test_f1_macro)],
    ['**Proposed:** NEQR, 4×4 patches', 'quantum (sim.)', pct(ne.val_f1_macro.mean), ms(ne.test_accuracy), ms(ne.test_f1_macro)],
    ...Object.entries(G).filter(([g]) => g !== H.frqi && g !== H.neqr && g !== 'V4-patchmom-rbfsvm').map(([g, r]) => [`${/frqi/.test(g) ? 'FRQI' : 'NEQR'}, ${r.params.patch}×${r.params.patch} patches`, 'quantum (sim.)', pct(r.val_f1_macro.mean), ms(r.test_accuracy), ms(r.test_f1_macro)]),
    ['Whole-image FRQI (V2)', 'quantum (sim.)', pct(R['E1b-frqi8-qkc-scaled'].val_f1_macro.mean), ms(R['E1b-frqi8-qkc-scaled'].test_accuracy), ms(R['E1b-frqi8-qkc-scaled'].test_f1_macro)],
    ['Whole-image NEQR (V2)', 'quantum (sim.)', pct(R['E2-neqr16-b4-qkc'].val_f1_macro.mean), ms(R['E2-neqr16-b4-qkc'].test_accuracy), ms(R['E2-neqr16-b4-qkc'].test_f1_macro)],
    ['Whole-image FRQI, re-tuned (V3)', 'quantum (sim.)', pct(R['V3-frqi8'].val_f1_macro.mean), ms(R['V3-frqi8'].test_accuracy), ms(R['V3-frqi8'].test_f1_macro)],
    ['Classical RBF-SVM, same patches', 'classical', pct(ctrl.val_f1_macro.mean), ms(ctrl.test_accuracy), ms(ctrl.test_f1_macro)],
    ['Classical texture RBF-SVM (V3)', 'classical', pct(R['V3-tex12c-rbfsvm'].val_f1_macro.mean), ms(R['V3-tex12c-rbfsvm'].test_accuracy), ms(R['V3-tex12c-rbfsvm'].test_f1_macro)],
  ];
  add(P(`Table 5.5 compares the patch-ensemble models with all baselines. The FRQI model with 8×8 patches reaches ${ms(fr.test_accuracy)} % test accuracy against ${ms(R['E1b-frqi8-qkc-scaled'].test_accuracy)} % for the whole-image FRQI kernel; the NEQR model with 4×4 patches reaches ${ms(ne.test_accuracy)} % against ${ms(R['E2-neqr16-b4-qkc'].test_accuracy)} %. Validation and test scores are close for FRQI, so its selection did not overfit the validation split.`));
  add(tbl('Locked-test results, mean ± s.d. over three seeds (360 images; F1 = macro-F1)', ['Model', 'Type', 'Val. F1 (%)', 'Test accuracy (%)', 'Test F1 (%)'], mainRows, [2.6, 1.2, 0.9, 1.2, 1.1], { numeric: true, highlight: [0, 1] }));
  add(fig(px('Fig03_main_results.png'), 'Main locked-test results of the V4 models and baselines.', 6.0));
  add(h2('5.4', 'RQ1: Improvement Over Whole-Image Kernels'));
  const fUp = cmp('V4 FRQI vs V2 FRQI'), nUp = cmp('V4 NEQR vs V2 NEQR'), fvn = cmp('V4 FRQI vs V4 NEQR'), fc = cmp('V4 FRQI vs classical patch-moment'), nc = cmp('V4 NEQR vs classical patch-moment');
  const pv = (p) => (p < 0.001 ? '< 0.001' : p.toFixed(3));
  const sgn = (v) => `${v >= 0 ? '+' : '−'}${Math.abs(100 * v).toFixed(1)}`;
  add(P(`${figRef()} and Table 5.6 give the paired statistics. The FRQI gain over the V2 whole-image kernel is ${sgn(fUp.diff)} percentage points (95 % CI ${sgn(fUp.ci95[0])} to ${sgn(fUp.ci95[1])}) and the NEQR gain ${sgn(nUp.diff)} pp; both are significant after Holm correction (p ${pv(fUp.p_holm)}). FRQI is also better than NEQR by ${sgn(fvn.diff)} pp (p = ${pv(fvn.p_holm)}). **The answer to RQ1 is yes, for both encodings.**`));
  add(fig(px('Fig05_comparisons_forest.png'), 'Accuracy differences of the eight pre-declared comparisons with paired-bootstrap 95 % confidence intervals and Holm-corrected p-values.', 6.2));
  add(tbl('Pre-declared paired comparisons (Holm-corrected over eight tests)', ['Comparison (A vs B)', 'A (%)', 'B (%)', 'Δ (pp)', '95 % CI (pp)', 'p (Holm)', 'Significant'],
    v4.comparisons.map((x) => [x.name, pct(x.acc_a), pct(x.acc_b), sgn(x.diff), `${sgn(x.ci95[0])} to ${sgn(x.ci95[1])}`, pv(x.p_holm), x.p_holm < 0.05 ? 'yes' : 'no']),
    [2.7, 0.6, 0.6, 0.6, 1.1, 0.7, 0.8], { numeric: true }));
  add(h2('5.5', 'RQ2: Is the Gain Due to the Quantum Encoding?'));
  add(P(`On identical patches the classical control reaches ${ms(ctrl.test_accuracy)} %. FRQI is ${sgn(fc.diff)} pp higher, but the difference is not significant after correction (p = ${pv(fc.p_holm)}), and NEQR is ${sgn(nc.diff)} pp (p = ${pv(nc.p_holm)}). The classical texture SVM is clearly better than both (p < 0.001). Most of the gain over whole-image kernels therefore comes from the patch representation, which a classical model can exploit equally well. **The answer to RQ2 is no:** the evidence does not support an advantage from the quantum encoding, consistent with Huang et al. ${c('huang2021power')}.`));
  add(h2('5.6', 'Ablation Study'));
  add(P('Table 5.7 changes one component at a time (values from the paper\'s verified tables). Removing patching costs 27.1 pp for FRQI; replacing the quantum feature map by classical patch moments costs 4.2 pp; halving the patch side costs 2.5 pp. On validation data, contrast stretch adds 8.9 pp, the angle scale b = 4 adds 12.2 pp over b = 1, and a weakly regularised SVM (C = 1000) is essential.'));
  add(tbl('Ablation study for the FRQI model', ['Variant', 'Metric', 'Value (%)'], [
    ['Full model (FRQI, 8×8 patches, b = 4, stretch, C = 1000)', 'test accuracy', '87.8 ± 1.5'],
    ['– without patches (whole-image FRQI kernel)', 'test accuracy', '60.6 ± 1.2'],
    ['– quantum encoding replaced by classical patch moments', 'test accuracy', '83.6 ± 0.3'],
    ['– 4×4 instead of 8×8 patches', 'test accuracy', '85.3 ± 1.7'],
    ['Full model', 'val. macro-F1', '88.0 ± 1.4'],
    ['– without contrast stretch', 'val. macro-F1', '79.1 ± 4.6'],
    ['– angle scale b = 2 / b = 1', 'val. macro-F1', '84.9 ± 3.0 / 75.8 ± 2.3'],
    ['– image size 32 / 128 instead of 64', 'val. macro-F1', '79.1 ± 4.7 / 85.4 ± 2.5'],
    ['– C = 100 / C = 1 instead of 1000', 'val. macro-F1', '81.5 ± 2.6 / 53.8 ± 4.2'],
  ], [3.8, 1.2, 1.5], { highlight: [0, 4] }));
  add(fig(px('Fig09_validation_sweep.png'), 'Validation macro-F1 of the best configuration for each value of the main hyper-parameters (validation split only).', 6.3));
  add(h2('5.7', 'Error Analysis'));
  add(P(`${figRef()} shows the confusion matrices of the two headline models, summed over seeds, and ${figRef(2)} the per-class F1. FRQI is strongest on patches and crazing; its largest errors are inclusion predicted as pitted surface and scratches predicted as rolled-in scale, classes whose local patches look alike once global layout is discarded.`));
  add(fig(px('Fig06_confusion_matrices.png'), 'Confusion matrices on the locked test set, summed over three seeds, for the FRQI (8×8) and NEQR (4×4) models.', 6.2));
  add(fig(px('Fig07_per_class_f1.png'), 'Per-class F1 on the locked test set (mean over three seeds) for the four patch-ensemble groups and the classical control.', 5.8));
  add(P(`${figRef()} explains the large standard deviation of NEQR: its seed accuracies are ${ne.per_seed_test_accuracy.map((x) => pct(x)).join(', ')} %, and on seed 1 it misclassifies every rolled-in-scale test image. This matches the brightness shift found in Section 3.2 (rolled-in scale is ${Math.abs(bV['rolled-in_scale'][0] - bT['rolled-in_scale'][0]).toFixed(3)} darker in the test folder). FRQI, selected with per-image contrast stretch, is not affected (${fr.per_seed_test_accuracy.map((x) => pct(x)).join(', ')} %). NEQR was not re-tuned after the test, because that would use the test set for model choice.`));
  add(fig(px('Fig08_seed_stability.png'), 'Test accuracy per seed for each V4 group.', 5.2));
  add(h2('5.8', 'Circuit Resources and Reconstruction'));
  add(P(`One FRQI patch state uses 7 qubits and, after transpilation, 8,339 gates (depth 4,878, 3,584 CX); one NEQR patch state uses 8 qubits and 1,998 gates (${figRef()}). A swap test between two FRQI patch states needs 2·7 + 1 = 15 qubits, independent of image size. In the reconstruction study of all 1,800 images (${figRef(2)}), FRQI statevector decoding reproduced every image exactly; with finite shots the error grows with image size because shots are spread over more pixels. NEQR is exact up to quantisation (4-bit MSE floor 3.7×10⁻⁴). Classical PCA with eight components keeps an SSIM of only 0.59, which helps explain why earlier PCA-input quantum models had little texture to work with.`));
  add(fig(px('Fig10_circuit_resources.png'), 'Circuit resources (qubits, gates, depth, CX) of the FRQI and NEQR encoders.', 6.0));
  add(fig(px('Fig11_reconstruction_mse_vs_shots.png'), 'Reconstruction error (MSE, log scale) versus number of measurement shots over all 1,800 images.', 6.2));
  add(fig(px('Fig12_reconstruction_examples.png'), 'Reconstruction examples for FRQI and NEQR at different shot counts.', 6.2));
  add(h2('5.9', 'Per-Image Analysis'));
  add(P(`Combining the saved test predictions of all 163 selected models of V2–V4 (three seeds each) shows that the median test image is classified correctly by 67 % of model–seed pairs, that no image is misclassified by every model and that no image is classified correctly by every model (${figRef()}). Rolled-in scale is the hardest class and patches the easiest. Errors are spread over many images rather than caused by a few corrupted samples.`));
  add(fig(px('Fig14_per_image_difficulty.png'), 'Fraction of all model–seed pairs that classify each test image correctly, and mean per class.', 6.2));
  add(h2('5.10', 'Discussion'));
  add(P('The main lesson is that the low accuracy of FRQI and NEQR kernels was caused by **what was being compared**, not by the encodings. A whole-image overlap asks whether two images have similar intensities at the same pixels, which is the wrong question for textures; the mixture of patch states asks how often local patterns of one image resemble those of the other. FRQI benefits more than NEQR, plausibly because FRQI overlaps vary smoothly with intensity whereas NEQR overlaps are all-or-nothing per quantised pixel.'));
  add(P('The matched control changes how the result should be read: a classical SVM on the same patches is statistically tied with the FRQI kernel, and every kernel here has a closed form computed on a laptop. The study shows a better way to use quantum image representations, not a computational advantage. **Threats to validity:** results come from noiseless simulation; only one dataset was used; C = 1000 lies at the edge of the grid; and the locked test set was also used in V2 and V3, so the choice of method at the protocol level was informed by earlier test results, although within V4 every model was selected on validation data and tested once.'));

  // ═════════════ CHAPTER 6 ═════════════
  add(chapter('Conclusion and Future Scope'));
  add(h2('6.1', 'Conclusion'));
  add(P(`This project asked whether quantum image representations can classify real steel surface defects. Under a leakage-controlled protocol on NEU-DET, whole-image FRQI and NEQR kernels stayed at about 60 % accuracy across protocols V2 and V3. Representing an image as the mixed state of its FRQI- or NEQR-encoded patches and comparing images with the swap-test quantity Tr(ρ_A ρ_B) raised FRQI to ${ms(fr.test_accuracy)} % and NEQR to ${ms(ne.test_accuracy)} % (p < 0.001), answering RQ1 positively. For RQ2, a classical SVM on the same patches performs equally well (${ms(ctrl.test_accuracy)} %, p = ${pv(fc.p_holm)}) and a classical texture model remains best (${ms(R['V3-tex12c-rbfsvm'].test_accuracy)} %), so the improvement is not attributable to the quantum encoding.`));
  add(P(`${tabRef()} summarises the main results of the project, from the whole-image kernels of the earlier protocols to the proposed patch-ensemble kernel and its classical controls.`));
  const qkcF = fam.families.find((f) => f.key === 'qkc'), hybF = fam.families.find((f) => f.key === 'hybrid');
  add(tbl('Summary of the main results (locked test, 360 images, mean ± s.d. over three seeds)', ['Model', 'Type', 'Test accuracy (%)', 'What it shows'], [
    ['Whole-image FRQI kernel (V2)', 'quantum (sim.)', ms(R['E1b-frqi8-qkc-scaled'].test_accuracy), 'Position-locked pixel comparison fails on textures'],
    ['Whole-image NEQR kernel (V2)', 'quantum (sim.)', ms(R['E2-neqr16-b4-qkc'].test_accuracy), 'Same limitation for NEQR'],
    ['Whole-image FRQI, re-tuned (V3)', 'quantum (sim.)', ms(R['V3-frqi8'].test_accuracy), 'Re-tuning does not remove the limitation'],
    ['QKC on texture features (V3)', 'quantum (sim.)', ms(qkcF.test_accuracy), 'Good features set the ceiling, not the kernel'],
    ['Hybrid CNN + quantum kernel (V3)', 'hybrid', ms(hybF.test_accuracy), 'Matches the RBF-SVM on the same CNN features'],
    ['**Proposed:** patch-ensemble FRQI, 8×8 (V4)', 'quantum (sim.)', ms(fr.test_accuracy), `+${pct(fUp.diff)} pp over whole-image FRQI (RQ1: yes)`],
    ['**Proposed:** patch-ensemble NEQR, 4×4 (V4)', 'quantum (sim.)', ms(ne.test_accuracy), `+${pct(nUp.diff)} pp over whole-image NEQR; unstable across seeds`],
    ['RBF-SVM on the same patches (V4)', 'classical', ms(ctrl.test_accuracy), `Tied with FRQI, p = ${pv(fc.p_holm)} (RQ2: no)`],
    ['Texture RBF-SVM (V3)', 'classical', ms(R['V3-tex12c-rbfsvm'].test_accuracy), 'Best texture model; frozen MobileNetV3 + linear reaches 96.4 % (V2)'],
  ], [2.5, 1.1, 1.2, 2.6], { numeric: false, highlight: [5, 6] }));
  add(P(`${tabRef()} lists the research questions and objectives with their outcome. For practitioners, the main message is that **how images are compared matters more than which quantum encoding is chosen**, and that a classical model on the same input should always be reported next to a quantum one.`));
  add(tbl('Outcome of the research questions and objectives', ['Item', 'Outcome', 'Evidence'], [
    ['RQ1: does the patch-ensemble kernel beat whole-image kernels?', `**Yes**, for both encodings (FRQI ${sgn(fUp.diff)} pp, NEQR ${sgn(nUp.diff)} pp; Holm p ${pv(fUp.p_holm)})`, 'Section 5.4'],
    ['RQ2: is the gain due to the quantum encoding?', `**No**: a classical SVM on the same patches is tied (p = ${pv(fc.p_holm)}) and texture features are better`, 'Section 5.5'],
    ['O1  Leakage-controlled protocol', 'Met: hashed manifest, validation-only selection, SHA-256 freeze, one locked-test pass', 'Sections 3.1, 4.10.9'],
    ['O2  FRQI/NEQR encoders, QKC, PQK, VQC, hybrid', 'Met: real Qiskit circuits and five model families evaluated', 'Sections 4.10, 5.1–5.2'],
    ['O3  Patch-ensemble mixed-state kernel', 'Met: registers of at most 8 qubits; swap test needs 15', 'Sections 4.10.7, 5.3'],
    ['O4  Matched controls and pre-declared statistics', 'Met: eight comparisons with bootstrap CIs and Holm correction', 'Sections 5.4–5.5'],
    ['O5  Circuit resources and reconstruction', 'Met: all 1,800 images, every method, error versus shots', 'Section 5.8'],
    ['O6  Interactive research and learning platform', 'Met: Q-ImageLab shows every saved result, replays models live, accepts uploads and teaches visually', 'Section 4.11, Appendix A'],
  ], [2.4, 3.2, 1.3]));
  add(h2('6.2', 'Future Scope'));
  add(bullets([
    '**Finite-shot and noisy estimation:** estimate the kernel with swap-test shots and realistic noise models to measure how many shots the reported accuracy needs.',
    '**Fresh test data:** evaluate on a new steel defect dataset whose test images were never used for any design decision.',
    '**Harder-to-simulate encoders:** study larger patches or entangling encoders to see whether patch-ensemble kernels keep their accuracy once they are no longer cheap to simulate classically.',
    '**Real hardware:** run the 15-qubit swap test on a quantum device for a subset of image pairs.',
    '**Platform:** add multi-user deployment, experiment launching from the browser and export of the learning modules for teaching.',
  ]));

  // ═════════════ APPENDIX A ═════════════
  target = appx;
  add(appendixStart('A', 'Screenshots of the Q-ImageLab Platform'));
  add(P('This appendix shows the main screens of the Q-ImageLab web platform (FastAPI back end, React front end). Every number on these screens is read from the saved result files; the live pages replay the frozen models on real images.'));
  add(h2('A.1', 'Results and Model Comparison'));
  add(fig(sx('P01_overview.png'), 'Overview page: headline FRQI and NEQR accuracy of every protocol version on the same 360 test images.', 6.3));
  add(fig(sx('P02_v4_results.png'), 'V4 results page: before → after tiles, forest plot of the eight pre-declared comparisons and per-seed accuracy of every V4 group.', 6.3));
  add(fig(sx('P03_all_models_chart.png'), 'Model comparison: all 163 selected models of V2–V4, one dot per model, coloured by type.', 6.3));
  add(fig(sx('P04_model_families.png'), 'Model families centre: QKC, PQK, VQC, hybrid and RBF-SVM with metrics, timings, architecture, confusion matrix and the “why did this model perform better?” analysis.', 6.3));
  add(fig(sx('P19_quantum_vs_classical.png'), 'Quantum vs classical page: classical, quantum and hybrid models shown separately on the same test images.', 6.3));
  add(h2('A.2', 'Interactive Pipeline and Live Model'));
  add(fig(sx('P05_pipeline_cnn.png'), 'Interactive hybrid pipeline on a real test image: the CNN stage with real MobileNetV3 feature maps.', 6.3));
  add(fig(sx('P06_pipeline_classification.png'), 'Hybrid pipeline, classification stage: quantum-kernel similarity to the 1,080 training images and the five most similar images.', 6.3));
  add(fig(sx('P17_how_it_works_mixed_state.png'), '“How it works (live)”: the frozen V4 FRQI model mixing all patch states of a real test image into ρ.', 6.3));
  add(h2('A.3', 'Circuits and Encoding Walkthroughs'));
  add(fig(sx('P10_circuit_highlight.png'), 'Quantum circuits page: “Explain this circuit” lights up the gates that write the brightness in a real FRQI circuit.', 6.3));
  add(fig(sx('P08_encoding_frqi_gates.png'), 'FRQI encoding walkthrough: controlled rotations write each pixel into the colour qubit while the state amplitudes update.', 6.3));
  add(fig(sx('P09_encoding_neqr_gates.png'), 'NEQR encoding walkthrough: controlled-NOT gates write the 4-bit code of each pixel.', 6.3));
  add(h2('A.4', 'Learning Tools'));
  add(fig(sx('P07_learn_frqi.png'), 'Learning lab: FRQI step on a real image, with one arrow per pixel and the 32 state amplitudes.', 6.3));
  add(fig(sx('P11_playground_sandbox.png'), 'Playground sandbox: editable 3×3 image with normalisation, FRQI angles, NEQR bits, PCA, feature-map circuit and kernel matrix updating instantly.', 6.3));
  add(fig(sx('P12_cnn_layer1.png'), 'CNN feature studio: real first-layer MobileNetV3 feature maps of a training image.', 6.3));
  add(fig(sx('P13_cnn_qubits.png'), 'CNN feature studio: 576 CNN features reduced by PCA to qubit rotation angles.', 6.3));
  add(fig(sx('P18_quiz.png'), 'Knowledge check page: 27 questions in seven topics with instant feedback and an overall score.', 6.3));
  add(h2('A.5', 'Upload Lab, Reconstruction and Presentation'));
  add(fig(sx('P14_upload_frqi.png'), 'Upload lab: a user image encoded with FRQI and reconstructed from the exact state and from 100, 1,000 and 10,000 shots.', 6.3));
  add(fig(sx('P15_upload_classify.png'), 'Upload lab: classification of the uploaded image by the frozen V4 FRQI model, with nearest training images and an out-of-distribution check.', 6.3));
  add(fig(sx('P16_reconstruction.png'), 'Reconstruction study page: all 1,800 images, every method, error versus shots.', 6.3));
  add(fig(sx('P20_presentation.png'), 'Presentation mode (V4): results slide generated from the saved results.', 6.3));

  return { body, appx, refsOrder: [...refsOrder] };
}

function algorithm(num, title, lines) {
  // algorithms are boxed listings, numbered separately from tables
  const rows = [
    new TableRow({ children: [new TableCell({ width: { size: TEXT_W, type: WidthType.DXA }, shading: { type: ShadingType.CLEAR, color: 'auto', fill: 'F2F4F7' }, margins: { top: 60, bottom: 60, left: 120, right: 120 },
      borders: { top: border, bottom: border, left: border, right: border },
      children: [new Paragraph({ children: [new TextRun({ text: `Algorithm ${num}: `, font: FONT, size: 21, bold: true }), new TextRun({ text: title, font: FONT, size: 21, bold: true })] })] })] }),
    new TableRow({ children: [new TableCell({ width: { size: TEXT_W, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 },
      borders: { top: border, bottom: border, left: border, right: border },
      children: lines.map((l, i) => new Paragraph({ children: [new TextRun({ text: `${i + 1}  `, font: 'Consolas', size: 17, color: '6B7280' }), new TextRun({ text: l, font: 'Consolas', size: 18 })], spacing: { line: 260 } })) })] }),
  ];
  return [new Table({ width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: [TEXT_W], rows }), new Paragraph({ children: [], spacing: { after: 160 } })];
}

// ───────────────────────── front matter ─────────────────────────
const TITLE = 'Quantum Image Representations for Steel Surface Defect Classification: Patch-Ensemble FRQI and NEQR Kernels with an Interactive Research and Learning Platform (Q-ImageLab)';
const STUDENTS = [['Drishti', '230527'], ['Abhinav Singh', '230528']];
const SUPERVISORS = 'Maheshwar Dwivedy and Kiran Khatter';
const hl = (t) => new TextRun({ text: t, font: FONT, size: BODY, highlight: 'yellow' });
const center = (children, o = {}) => new Paragraph({ children, alignment: AlignmentType.CENTER, spacing: { after: o.after ?? 120, before: o.before ?? 0, line: o.line ?? 300 } });
const T = (t, o = {}) => new TextRun({ text: t, font: FONT, size: o.size ?? BODY, bold: o.bold, italics: o.italics, allCaps: o.caps });
const pageNo = (k) => (PAGES[k] != null ? String(PAGES[k]) : '00');

function frontMatter(refsCount) {
  const fm = [];
  // Title page
  fm.push(center([T('Project Report', { size: 32, bold: true })], { before: 600, after: 240 }));
  fm.push(center([hl('[Course name and code]')], { after: 480 }));
  fm.push(center([T(TITLE, { size: 32, bold: true })], { after: 480, line: 360 }));
  fm.push(center([T('Submitted in partial fulfilment of the requirements for the award of the degree of', { italics: true })], { after: 60 }));
  fm.push(center([T('Bachelor of Technology', { bold: true })], { after: 60 }));
  fm.push(center([T('in Computer Science and Engineering', {})], { after: 480 }));
  fm.push(center([T('By', { bold: true })], { after: 120 }));
  STUDENTS.forEach(([n, r]) => fm.push(center([T(`${n}  (${r})`, { size: 26 })], { after: 60 })));
  fm.push(center([T('Under the supervision of', { italics: true })], { before: 360, after: 60 }));
  fm.push(center([T(SUPERVISORS, { bold: true })], { after: 600 }));
  fm.push(center([T('Department of Computer Science and Engineering')], { after: 40 }));
  fm.push(center([T('School of Engineering and Technology')], { after: 40 }));
  fm.push(center([T('BML Munjal University, Gurugram', { bold: true })], { after: 40 }));
  fm.push(center([T('November 2026')], { after: 40 }));
  // Candidate's declaration
  const heading = (t) => new Paragraph({ children: [T(t, { size: 30, bold: true })], alignment: AlignmentType.CENTER, pageBreakBefore: true, spacing: { after: 360 } });
  fm.push(heading('CANDIDATE’S DECLARATION'));
  fm.push(new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { line: 360, after: 240 }, children: [
    T('We hereby certify that the work on the project entitled “'), T(TITLE, { bold: true }),
    T('”, in partial fulfilment of the requirements for the award of the Degree of Bachelor of Technology in the School of Engineering and Technology at BML Munjal University, having University Roll Nos. 230527 and 230528, is an authentic record of our own work carried out during the period from July 2026 to December 2026 under the supervision of '),
    T(SUPERVISORS), T('.')] }));
  fm.push(...blank(2));
  fm.push(new Paragraph({ children: [T('Drishti (230527)'), new TextRun({ text: '\tAbhinav Singh (230528)', font: FONT, size: BODY })], tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W }], spacing: { after: 600 } }));
  fm.push(new Paragraph({ children: [T('SUPERVISOR’S DECLARATION', { size: 30, bold: true })], alignment: AlignmentType.CENTER, spacing: { before: 480, after: 360 } }));
  fm.push(P('This is to certify that the above statement made by the candidates is correct to the best of my knowledge.'));
  fm.push(...blank(2));
  fm.push(new Paragraph({ children: [T('Faculty Supervisor Name: '), T(SUPERVISORS)], spacing: { after: 240 } }));
  fm.push(new Paragraph({ children: [T('Signature:')], spacing: { after: 240 } }));
  // Acknowledgement
  fm.push(heading('ACKNOWLEDGEMENT'));
  fm.push(new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { line: 360, after: 200 }, children: [T('We are highly grateful to '), T(SUPERVISORS), T(', '), hl('[Designation]'), T(', BML Munjal University, Gurugram, for supervising this project from July to December 2026.')] }));
  fm.push(P(`${SUPERVISORS} provided great help in carrying out this work and are acknowledged with reverential thanks. Without their wise counsel and able guidance, it would have been impossible to complete the project in this manner.`));
  fm.push(P(`We want to express our sincere thanks to ${SUPERVISORS} for continually stimulating us. We would also like to thank the entire team at BML Munjal University, and our friends, who devoted their valuable time and helped us in every possible way toward the successful completion of this project.`));
  fm.push(...blank(2));
  fm.push(new Paragraph({ children: [T('Drishti (230527)'), new TextRun({ text: '\tAbhinav Singh (230528)', font: FONT, size: BODY })], tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W }] }));
  // Abstract
  fm.push(heading('ABSTRACT'));
  fm.push(P('Quantum image representations such as the Flexible Representation of Quantum Images (FRQI) and the Novel Enhanced Quantum Representation (NEQR) are often proposed as inputs to quantum classifiers, but when two images are compared through the overlap of their whole-image states, the similarity is computed pixel by pixel at fixed positions. Steel surface defects are textures whose position varies, and on the NEU-DET dataset such whole-image kernels reached only about 60 % accuracy in our earlier protocols. This project proposes a patch-ensemble mixed-state kernel: every small patch of an image is encoded with FRQI or NEQR, the image is represented by the uniform mixture of its patch states, and two images are compared through the Hilbert–Schmidt overlap Tr(ρ_A ρ_B), which a swap test can estimate directly. We evaluated 288 configurations (864 runs over three splits) on validation data only, froze the selected settings with SHA-256 hashes and tested each frozen model once on 360 held-out images. The FRQI model reaches 87.8 ± 1.5 % accuracy and the NEQR model 82.7 ± 10.1 %, gains of 27.1 and 22.5 percentage points over the whole-image kernels (Holm-corrected p < 0.001). A classical support vector machine on the same patches reaches 83.6 ± 0.3 %, which is not significantly different from FRQI (p = 0.060), and a classical texture model remains best at 95.6 ± 2.2 %. The low accuracy of FRQI and NEQR kernels therefore came from position-locked comparison rather than from the encodings, and the improvement is not evidence of quantum advantage. The project also delivers Q-ImageLab, a FastAPI and React platform that shows every saved result, replays the frozen models live on real images, encodes uploaded images with FRQI and NEQR, and teaches the algorithms through interactive visualisations and quizzes. All quantum computations were exact classical simulations.'));
  fm.push(new Paragraph({ children: [T('Keywords: ', { bold: true }), T('FRQI, NEQR, quantum image representation, mixed-state quantum kernel, swap test, steel surface defect classification, quantum machine learning', { italics: true })], spacing: { before: 120 } }));
  // Table of contents
  const leaderLine = (text, page, o = {}) => new Paragraph({ children: [new TextRun({ text, font: FONT, size: o.size ?? 22, bold: o.bold }), new TextRun({ text: `\t${page}`, font: FONT, size: o.size ?? 22, bold: o.bold })],
    tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W, leader: 'dot' }], indent: { left: o.indent ?? 0 }, spacing: { after: o.after ?? 40 } });
  fm.push(heading('TABLE OF CONTENTS'));
  const tocLine = (e) => fm.push(leaderLine(e.level === 0 ? (e.appendix ? e.text : `Chapter ${e.text}`) : e.text, pageNo(e.key), { bold: e.level === 0, indent: e.level * 400, after: e.level === 0 ? 80 : 30, size: e.level === 2 ? 20 : 22 }));
  const appAt = TOC.findIndex((e) => e.appendix);
  (appAt < 0 ? TOC : TOC.slice(0, appAt)).forEach(tocLine);
  fm.push(leaderLine('Bibliography', pageNo('BIB'), { bold: true, after: 80 }));
  if (appAt >= 0) TOC.slice(appAt).forEach(tocLine);
  // List of figures / tables (template: number | description | page)
  const listTable = (head, items, prefix) => new Table({
    width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: [1300, 7060, 1000],
    rows: [new TableRow({ tableHeader: true, children: head.map((h, i) => cell(h, [1300, 7060, 1000][i], { head: true, align: i === 2 ? AlignmentType.CENTER : AlignmentType.LEFT, size: 20 })) }),
      ...items.map((f) => new TableRow({ cantSplit: true, children: [cell(`${prefix} ${f.num}`, 1300, { size: 19 }), cell(f.caption, 7060, { size: 19 }), cell(pageNo(`${prefix} ${f.num}`), 1000, { size: 19, align: AlignmentType.CENTER })] }))],
  });
  fm.push(heading('LIST OF FIGURES'));
  fm.push(listTable(['Figure No.', 'Figure Description', 'Page No.'], FIGS, 'Figure'));
  fm.push(heading('LIST OF TABLES'));
  fm.push(listTable(['Table No.', 'Table Description', 'Page No.'], TABS, 'Table'));
  fm.push(heading('LIST OF ABBREVIATIONS'));
  const AB = [['API', 'Application Programming Interface'], ['CI', 'Confidence Interval'], ['CKA', 'Centred Kernel Alignment'], ['CNN', 'Convolutional Neural Network'], ['CNOT / CX', 'Controlled-NOT gate'],
    ['CPU', 'Central Processing Unit'], ['CSV', 'Comma-Separated Values'], ['DFD', 'Data-Flow Diagram'], ['EDA', 'Exploratory Data Analysis'], ['ER', 'Entity–Relationship'],
    ['FRQI', 'Flexible Representation of Quantum Images'], ['GLCM', 'Grey-Level Co-occurrence Matrix'], ['JSON', 'JavaScript Object Notation'], ['LBP', 'Local Binary Patterns'],
    ['MSE', 'Mean Squared Error'], ['NEQR', 'Novel Enhanced Quantum Representation'], ['NEU-DET', 'Northeastern University surface defect database (detection version)'], ['NISQ', 'Noisy Intermediate-Scale Quantum'],
    ['PCA', 'Principal Component Analysis'], ['pp', 'Percentage points'], ['PQK', 'Projected Quantum Kernel'], ['PSNR', 'Peak Signal-to-Noise Ratio'], ['QKC', 'Quantum Kernel Classifier'],
    ['QML', 'Quantum Machine Learning'], ['RBF', 'Radial Basis Function'], ['REST', 'Representational State Transfer'], ['RQ', 'Research Question'], ['SHA-256', 'Secure Hash Algorithm (256-bit)'],
    ['SSIM', 'Structural Similarity Index Measure'], ['SVM', 'Support Vector Machine'], ['UI', 'User Interface'], ['VQC', 'Variational Quantum Classifier']];
  fm.push(new Table({ width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: [2200, 7160],
    rows: [new TableRow({ tableHeader: true, children: [cell('Abbreviation', 2200, { head: true, size: 20 }), cell('Full Form', 7160, { head: true, size: 20 })] }),
      ...AB.map(([a, f]) => new TableRow({ children: [cell(a, 2200, { size: 19 }), cell(f, 7160, { size: 19 })] }))] }));
  return fm;
}

(async () => {
  const { body, appx, refsOrder: order } = await build();
  if (order.length !== Object.keys(REFS).length) console.warn(`only ${order.length} of ${Object.keys(REFS).length} references cited:`, Object.keys(REFS).filter((k) => !order.includes(k)));
  const bib = [new Paragraph({ children: [T('BIBLIOGRAPHY', { size: 32, bold: true })], alignment: AlignmentType.CENTER, pageBreakBefore: true, spacing: { after: 360 } }),
    ...order.map((k, i) => new Paragraph({ children: [T(`[${i + 1}]\t`), ...runs(REFS[k].replace(/\*/g, ''), { size: 22 })], tabStops: [{ type: TabStopType.LEFT, position: 560 }], indent: { left: 560, hanging: 560 }, alignment: AlignmentType.LEFT, spacing: { after: 100, line: 276 } })),
    new Paragraph({ children: [T('Declaration on the Use of AI Tools', { bold: true, size: 26 })], spacing: { before: 480, after: 120 } }),
    P('A generative AI assistant (Claude, Anthropic) was used to help write and debug the experiment and dashboard code, to generate figures and tables from our saved results, and to prepare a first draft of this report. The authors reviewed and rewrote the text, checked every number against the result files and verified every reference. All experimental results come from our own runs; none were generated by the AI.')];
  const footer = new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 20 })] })] });
  const page = { size: { width: 12240, height: 15840 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } };
  const doc = new Document({
    creator: 'Drishti, Abhinav Singh', title: TITLE, description: 'B.Tech project report — Q-ImageLab',
    styles: {
      default: { document: { run: { font: FONT, size: BODY } } },
      paragraphStyles: [
        { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: 36, bold: true }, paragraph: { spacing: { before: 0, after: 360 }, keepNext: true, outlineLevel: 0 } },
        { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: 28, bold: true }, paragraph: { spacing: { before: 280, after: 140 }, keepNext: true, outlineLevel: 1 } },
        { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: 25, bold: true }, paragraph: { spacing: { before: 200, after: 100 }, keepNext: true, outlineLevel: 2 } },
      ],
    },
    numbering: { config: [{ reference: 'bul', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] }] },
    sections: [
      { properties: { page: { ...page, pageNumbers: { start: 1, formatType: NumberFormat.LOWER_ROMAN } } }, footers: { default: footer }, children: frontMatter(order.length) },
      { properties: { page: { ...page, pageNumbers: { start: 1, formatType: NumberFormat.DECIMAL } } }, footers: { default: footer }, children: [...body, ...bib, ...appx] },
    ],
  });
  fs.writeFileSync(OUT, await Packer.toBuffer(doc));
  fs.writeFileSync(path.join(RPT, '.report_lists.json'), JSON.stringify({ figs: FIGS.map((f) => `Figure ${f.num}`), tabs: TABS.map((t) => `Table ${t.num}`), toc: TOC }, null, 1));
  console.log(`wrote ${OUT}: ${FIGS.length} figures, ${TABS.length} tables, ${order.length} references`);
})().catch((e) => { console.error(e); process.exit(1); });
