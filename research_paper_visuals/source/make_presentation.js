// Builds the Q-ImageLab presentation (.pptx) from verified project results and real project figures.
// Speaker notes come from research_paper_visuals/Presentation/Q-ImageLab_Slide_Wise_Content.md.
// Usage: NODE_PATH=<dir with pptxgenjs> node make_presentation.js
const fs = require('fs');
const path = require('path');
const pptxgen = require('pptxgenjs');

const ROOT = path.resolve(__dirname, '..');
const OUT = path.join(ROOT, 'Presentation', 'Q-ImageLab_Presentation.pptx');
const PACK = (f) => path.join(ROOT, 'V4_paper_pack', 'figures', f);
const RPT = (f) => path.join(ROOT, 'Project_Report', 'figures', f);
const SHOT = (f) => path.join(ROOT, 'Project_Report', 'screenshots_v5', f);

// ── palette: steel neutrals; orange = quantum, blue = classical, green = frozen CNN (same as project figures)
const K = {
  ink: '1B2430', steel: '2E3A48', mute: '5A6675', line: 'C9D2DC', mist: 'EEF2F6', white: 'FFFFFF',
  q: 'D9581F', qSoft: 'FBE9DF', c: '2B6FD1', cSoft: 'E6EEFB', g: '1A8A5C', gSoft: 'E2F3EB', red: 'B23A48', redSoft: 'F7E3E6',
};
const HEAD = 'Cambria', BODY = 'Calibri';
const THEME = {
  name: 'Q-ImageLab Steel', headFontFace: HEAD, bodyFontFace: BODY,
  colors: { dk1: K.ink, lt1: K.white, dk2: K.steel, lt2: K.mist, accent1: K.q, accent2: K.c, accent3: K.g, accent4: '8A939D', accent5: K.red, accent6: 'E8B04B', hlink: K.c, folHlink: '6B4FA0' },
};

// ── speaker notes from the slide-wise markdown
const MD = fs.readFileSync(path.join(ROOT, 'Presentation', 'Q-ImageLab_Slide_Wise_Content.md'), 'utf8');
const plain = (s) => s.replace(/\*\*([^*]+)\*\*/g, '$1').replace(/`([^`]+)`/g, '$1').replace(/(^|\s)\*([^*\s][^*]*)\*/g, '$1$2').trim();
function notesFor(n) {
  const start = MD.indexOf(`## Slide ${n}:`);
  if (start < 0) return '';
  const rest = MD.slice(start + 5);
  const end = rest.search(/\n## /);
  const block = end < 0 ? rest : rest.slice(0, end);
  const part = (name) => { const m = block.match(new RegExp(`### ${name}\\n([\\s\\S]*?)(?=\\n### |$)`)); return m ? plain(m[1]).replace(/\n{2,}/g, '\n') : ''; };
  const say = part('Speaker notes'), concepts = part('Concepts to explain'), take = part('Key takeaway');
  return [say && `SAY: ${say}`, take && `KEY TAKEAWAY: ${take}`, concepts && `CONCEPTS TO EXPLAIN:\n${concepts}`].filter(Boolean).join('\n\n');
}

// ── image helpers (aspect-preserving fit, centred in the box)
function pngSize(f) { const b = fs.readFileSync(f); return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) }; }
function img(s, file, x, y, w, h, o = {}) {
  if (!fs.existsSync(file)) throw new Error(`missing ${file}`);
  const { w: pw, h: ph } = pngSize(file), r = pw / ph;
  let iw = w, ih = w / r; if (ih > h) { ih = h; iw = h * r; }
  const ix = x + (w - iw) / 2, iy = o.top ? y : y + (h - ih) / 2;
  if (o.frame) s.addShape('rect', { x: ix - 0.06, y: iy - 0.06, w: iw + 0.12, h: ih + 0.12, fill: { color: K.white }, line: { color: K.line, width: 0.75 }, objectName: 'frame' });
  s.addImage({ path: file, x: ix, y: iy, w: iw, h: ih, altText: o.alt || path.basename(file) });
  return { x: ix, y: iy, w: iw, h: ih };
}

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.333 x 7.5
pres.title = 'Can Quantum Image Encodings Classify Real Steel Defects?';
pres.author = 'Drishti, Abhinav Singh';
pres.subject = 'Q-ImageLab project presentation';
pres.theme = { headFontFace: HEAD, bodyFontFace: BODY };
const W = 13.333;

// ── layouts
pres.defineSlideMaster({
  title: 'TITLE_DARK', background: { color: K.ink },
  objects: [{ placeholder: { options: { name: 'title', type: 'title', x: 0.7, y: 1.5, w: 6.6, h: 2.3, fontFace: HEAD, fontSize: 38, bold: true, color: K.white, valign: 'bottom', align: 'left' }, text: '' } }],
});
pres.defineSlideMaster({
  title: 'SECTION_DARK', background: { color: K.steel },
  objects: [{ placeholder: { options: { name: 'title', type: 'title', x: 0.9, y: 3.0, w: 11.5, h: 1.2, fontFace: HEAD, fontSize: 40, bold: true, color: K.white, valign: 'middle', align: 'left' }, text: '' } }],
  slideNumber: { x: 12.4, y: 7.0, w: 0.6, h: 0.3, fontFace: BODY, fontSize: 10, color: 'B8C2CE', align: 'right' },
});
pres.defineSlideMaster({
  title: 'CONTENT', background: { color: K.white },
  objects: [
    { placeholder: { options: { name: 'title', type: 'title', x: 0.6, y: 0.35, w: 12.1, h: 0.85, fontFace: HEAD, fontSize: 30, bold: true, color: K.ink, valign: 'middle', align: 'left' }, text: '' } },
    { text: { text: 'Q-ImageLab', options: { x: 0.6, y: 7.0, w: 3, h: 0.3, fontFace: BODY, fontSize: 10, color: '8A939D' } } },
  ],
  slideNumber: { x: 12.1, y: 7.0, w: 0.6, h: 0.3, fontFace: BODY, fontSize: 10, color: '8A939D', align: 'right' },
});

// ── drawing helpers
let N = 0, SECTION = '', NK = null, NOTES = '';
function section(t) { SECTION = t; pres.addSection({ title: t }); }
function slide(title, master = 'CONTENT') {
  N += 1;
  const s = pres.addSlide({ masterName: master, sectionTitle: SECTION });
  s.addText(title, { placeholder: 'title' });
  const n = NK != null ? notesFor(NK) : NOTES; if (n) s.addNotes(n);
  NOTES = '';
  return s;
}
function T(s, text, x, y, w, h, o = {}) {
  s.addText(text, { x, y, w, h, isTextBox: true, fontFace: o.font || BODY, fontSize: o.size || 16, color: o.color || K.ink, bold: o.bold, italic: o.italic,
    align: o.align || 'left', valign: o.valign || 'top', margin: o.margin ?? 0, paraSpaceAfter: o.psa, lineSpacingMultiple: o.lsm, fit: 'none', objectName: o.name });
}
function bullets(s, items, x, y, w, h, o = {}) {
  const arr = items.map((it, i) => {
    const parts = Array.isArray(it) ? it : [{ text: it }];
    return parts.map((p, j) => {
      const op = { bold: p.bold, color: p.color || o.color || K.ink, breakLine: j === parts.length - 1 && i < items.length - 1 };
      if (j === 0) op.bullet = { indent: 16 };
      return { text: p.text, options: op };
    });
  }).flat();
  s.addText(arr, { x, y, w, h, isTextBox: true, fontFace: BODY, fontSize: o.size || 16, color: o.color || K.ink, valign: 'top', paraSpaceAfter: o.psa ?? 8, margin: 0, fit: 'none' });
}
function box(s, x, y, w, h, fill, line, text, o = {}) {
  s.addShape('roundRect', { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: line, width: o.lw ?? 1.25 }, objectName: o.name || 'box' });
  if (text != null) s.addText(text, { x: x + 0.08, y: y + 0.05, w: w - 0.16, h: h - 0.1, isTextBox: true, fontFace: BODY, fontSize: o.size || 13, color: o.color || K.ink, bold: o.bold,
    align: o.align || 'center', valign: 'middle', margin: 0, fit: 'none' });
}
function arrow(s, x1, y1, x2, y2, color = '8A939D') {
  s.addShape('line', { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001, flipH: x2 < x1, flipV: y2 < y1,
    line: { color, width: 1.75, endArrowType: 'triangle' }, objectName: 'arrow' });
}
// horizontal pipeline of steps: [{t, kind:'c'|'q'|'g'}]
function pipeline(s, steps, x, y, w, h, o = {}) {
  const gap = o.gap ?? 0.32, bw = (w - gap * (steps.length - 1)) / steps.length;
  steps.forEach((st, i) => {
    const bx = x + i * (bw + gap);
    const [fill, line] = st.kind === 'q' ? [K.qSoft, K.q] : st.kind === 'g' ? [K.gSoft, K.g] : [K.cSoft, K.c];
    box(s, bx, y, bw, h, fill, line, st.t, { size: o.size || 13 });
    if (i < steps.length - 1) arrow(s, bx + bw + 0.04, y + h / 2, bx + bw + gap - 0.04, y + h / 2);
  });
}
// card with a coloured heading and body text
function card(s, x, y, w, h, head, body, color = K.c, fill = K.mist, o = {}) {
  s.addShape('roundRect', { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: fill, width: 0.5 }, objectName: 'card' });
  T(s, head, x + 0.2, y + 0.15, w - 0.4, 0.45, { size: o.hs || 17, bold: true, color });
  T(s, body, x + 0.2, y + 0.62, w - 0.4, h - 0.75, { size: o.bs || 14, color: K.ink });
}
function stat(s, x, y, w, value, label, color = K.q, o = {}) {
  T(s, value, x, y, w, 0.85, { font: HEAD, size: o.vs || 44, bold: true, color });
  T(s, label, x, y + 0.85, w, 0.6, { size: o.ls || 13, color: K.mute });
}
function chip(s, x, y, w, text, color, fill) {
  s.addShape('roundRect', { x, y, w, h: 0.38, rectRadius: 0.19, fill: { color: fill }, line: { color: fill, width: 0.5 }, objectName: 'chip' });
  T(s, text, x, y, w, 0.38, { size: 13, bold: true, color, align: 'center', valign: 'middle' });
}
function table(s, rows, x, y, w, colW, o = {}) {
  const fs_ = o.size || 13;
  const data = rows.map((r, ri) => r.map((v) => {
    const hl = o.hl?.includes(ri);
    return { text: String(v), options: { fontFace: BODY, fontSize: fs_, bold: ri === 0 || hl, color: ri === 0 ? K.white : K.ink,
      fill: { color: ri === 0 ? K.steel : hl ? K.qSoft : ri % 2 ? K.white : 'F6F8FA' }, valign: 'middle', margin: [3, 6, 3, 6] } };
  }));
  s.addTable(data, { x, y, w, colW, border: { type: 'solid', pt: 0.75, color: K.line }, rowH: o.rowH || 0.36, autoPage: false });
}
const AX = { catAxisLabelColor: K.mute, valAxisLabelColor: K.mute, catAxisLabelFontFace: '+mn-lt', valAxisLabelFontFace: '+mn-lt', dataLabelFontFace: '+mn-lt', legendFontFace: '+mn-lt', titleFontFace: '+mn-lt',
  valGridLine: { color: 'E3E8EE', size: 0.75 }, catGridLine: { style: 'none' }, catAxisLabelFontSize: 12, valAxisLabelFontSize: 11, dataLabelFontSize: 11, dataLabelColor: K.ink };

// ════════════════════════ A. Introduction ════════════════════════
section('A. Introduction');

NK = 1;
// 1 — Title
{
  const s = slide('Can Quantum Image Encodings Classify Real Steel Defects?', 'TITLE_DARK');
  T(s, 'FRQI, NEQR and quantum kernels against classical baselines', 0.7, 3.95, 6.6, 0.8, { size: 20, color: 'F4B393' });
  T(s, 'Q-IMAGELAB', 0.7, 1.0, 6, 0.4, { size: 14, bold: true, color: 'B8C2CE' });
  T(s, [{ text: 'Drishti (230527)  ·  Abhinav Singh (230528)', options: { breakLine: true } },
    { text: 'Supervisors: Maheshwar Dwivedy and Kiran Khatter', options: { breakLine: true } },
    { text: 'BML Munjal University  ·  November 2026' }], 0.7, 5.3, 6.6, 1.2, { size: 14, color: 'D5DCE4', psa: 4 });
  img(s, PACK('Fig16_dataset_samples.png'), 7.75, 0.75, 5.0, 6.0, { frame: true, alt: 'Sample NEU-DET images of the six defect classes' });
}

NK = 2;
// 2 — Problem
{
  const s = slide('Problem statement');
  const rows = [
    ['Steel sheets get surface defects', 'Hot-rolled steel is inspected for six defect types during production.'],
    ['Manual inspection is slow', 'Human inspectors are slow and inconsistent, so factories automate it.'],
    ['Defects can be anywhere', 'A crack or pit has no fixed position, and brightness varies between images.'],
    ['Our question', 'Can FRQI/NEQR quantum image encodings classify these defects, and does any gain come from the quantum part?'],
  ];
  rows.forEach(([h, b], i) => {
    const y = 1.55 + i * 1.28;
    s.addShape('ellipse', { x: 0.6, y: y + 0.05, w: 0.55, h: 0.55, fill: { color: i === 3 ? K.q : K.steel }, line: { color: K.white, width: 0 }, objectName: 'num' });
    T(s, String(i + 1), 0.6, y + 0.05, 0.55, 0.55, { size: 18, bold: true, color: K.white, align: 'center', valign: 'middle' });
    T(s, h, 1.4, y, 5.6, 0.42, { size: 19, bold: true });
    T(s, b, 1.4, y + 0.45, 5.6, 0.7, { size: 15, color: K.mute });
  });
  img(s, PACK('Fig16_dataset_samples.png'), 7.4, 1.45, 5.3, 5.35, { frame: true, alt: 'One sample image of each defect class' });
}

NK = null;
// S — Solution
{
  NOTES = 'SAY: We answered the question in three parts. First, a fair benchmark: every quantum model is placed next to a classical model that gets exactly the same input, and the final test set was protected from the start. Second, our own method, the patch-ensemble kernel, which takes FRQI and NEQR from about 60 % to 88 %. Third, Q-ImageLab, a web platform where every result can be inspected and replayed.\n\nKEY TAKEAWAY: The project is a method, an honest benchmark and a platform.';
  const s = slide('Our solution');
  const cols = [
    ['1', 'A fair benchmark', 'Every quantum model next to a classical model with the same input. Models chosen on validation data only, frozen with SHA-256, tested once.', K.steel, K.mist],
    ['2', 'A new quantum kernel', 'Encode small patches with FRQI/NEQR, mix them into one state, compare images with Tr(ρ_A ρ_B). FRQI: 60.6 % → 87.8 %.', K.q, K.qSoft],
    ['3', 'The Q-ImageLab platform', 'A web app that shows every saved result, replays the models live on real images and teaches the algorithms visually.', K.c, K.cSoft],
  ];
  cols.forEach(([n, h, b, col, fill], i) => {
    const x = 0.6 + i * 4.1;
    s.addShape('roundRect', { x, y: 1.5, w: 3.9, h: 3.9, rectRadius: 0.08, fill: { color: fill }, line: { color: fill, width: 0.5 }, objectName: 'pillar' });
    s.addShape('ellipse', { x: x + 0.25, y: 1.75, w: 0.75, h: 0.75, fill: { color: col }, line: { color: K.white, width: 0 }, objectName: 'num' });
    T(s, n, x + 0.25, 1.75, 0.75, 0.75, { size: 22, bold: true, color: K.white, align: 'center', valign: 'middle' });
    T(s, h, x + 0.25, 2.75, 3.4, 0.5, { size: 20, bold: true, color: col });
    T(s, b, x + 0.25, 3.35, 3.4, 1.9, { size: 15 });
  });
  T(s, 'Built and compared', 0.6, 5.7, 4, 0.4, { size: 15, bold: true, color: K.steel });
  ['FRQI', 'NEQR', 'QKC', 'PQK', 'VQC', 'Hybrid CNN + quantum', 'Patch-ensemble', 'Classical baselines'].forEach((t, i) => {
    const w = [1.0, 1.1, 0.95, 0.95, 0.95, 2.4, 1.8, 2.05][i], x = 0.6 + [0, 1.1, 2.3, 3.35, 4.4, 5.45, 7.95, 9.85][i];
    chip(s, x, 6.15, w, t, i === 7 ? K.c : K.q, i === 7 ? K.cSoft : K.qSoft);
  });
}

NK = 3;
// 3 — Dataset
{
  const s = slide('Our dataset: NEU-DET');
  stat(s, 0.6, 1.45, 2.6, '1,800', 'grayscale images, 200×200 px', K.steel);
  stat(s, 3.4, 1.45, 2.2, '6', 'defect classes', K.steel);
  stat(s, 5.8, 1.45, 2.4, '300', 'images per class (balanced)', K.steel);
  // split diagram
  box(s, 0.6, 3.35, 2.4, 0.8, K.mist, K.steel, '1,800 images', { size: 15, bold: true });
  box(s, 3.6, 2.95, 2.6, 0.75, K.cSoft, K.c, 'Training folder · 1,440', { size: 14 });
  box(s, 3.6, 3.85, 2.6, 0.75, K.qSoft, K.q, 'Locked test · 360', { size: 14, bold: true });
  arrow(s, 3.02, 3.65, 3.55, 3.32); arrow(s, 3.02, 3.85, 3.55, 4.2);
  box(s, 6.8, 2.6, 2.5, 0.65, K.cSoft, K.c, 'Train · 1,080 (180/class)', { size: 13 });
  box(s, 6.8, 3.4, 2.5, 0.65, K.cSoft, K.c, 'Validation · 360 (60/class)', { size: 13 });
  arrow(s, 6.22, 3.2, 6.75, 2.95); arrow(s, 6.22, 3.4, 6.75, 3.7);
  T(s, 'Test set = the official validation folder, opened once per final model. Train/validation split by blocks of 20 files, repeated for 3 seeds.', 6.8, 4.25, 5.9, 0.8, { size: 13, color: K.mute });
  T(s, 'Average image of each class: crazing, pitted surface and inclusion average to flat grey, because the defects sit in random places', 0.6, 5.05, 12.1, 0.4, { size: 13, color: K.mute, italic: true });
  img(s, RPT('E4_class_average_images.png'), 0.6, 5.45, 12.1, 1.45, { alt: 'Average image of each class' });
}

NK = null;
// L — Literature survey
{
  NOTES = 'SAY: Four lines of research meet in this project. The FRQI and NEQR papers designed the encodings but did not classify real images. Quantum-kernel papers used synthetic or toy data, and two later papers warn that classical models often match quantum kernels and that large registers make kernels useless. Steel-defect work is purely classical. Nobody had tested FRQI and NEQR on real textured images with a matched classical control and a protected test set. That is the gap we fill.\n\nKEY TAKEAWAY: The gap is a fair test of quantum image encodings on a real classification task.';
  const s = slide('Literature survey');
  table(s, [
    ['Paper', 'Method', 'Key result', 'Gap for us'],
    ['Le et al. (2011)', 'FRQI angle encoding', 'Compact: log₂N + 1 qubits', 'No classification of real images'],
    ['Zhang et al. (2013)', 'NEQR binary encoding', 'Exact intensity read-out', 'Costly gates; no classification'],
    ['Havlíček et al. (2019)', 'Quantum kernel + VQC on hardware', 'High accuracy on 2-D data built for the map', 'Toy data only'],
    ['Schuld & Killoran (2019)', 'Encodings as feature maps', 'Every encoding defines a kernel', 'No large evaluation'],
    ['Henderson et al. (2020)', 'Quantum circuits on patches', 'Similar to classical random layers', 'Handwritten digits only'],
    ['Huang et al. (2021)', 'Classical vs quantum kernels', 'Classical models often match', 'Motivates matched controls'],
    ['Thanasilp et al. (2024)', 'Kernel concentration', 'Large registers make kernels flat', 'Motivates small registers'],
    ['Song & Yan (2013)', 'LBP texture features on NEU', 'High accuracy, classical', 'No quantum comparison'],
  ], 0.6, 1.4, 12.1, [2.6, 3.0, 3.4, 3.1], { size: 13, rowH: 0.47 });
  box(s, 0.6, 5.85, 12.1, 0.85, K.qSoft, K.qSoft, 'Research gap: no study tested FRQI/NEQR classification on real textured images with a matched classical control and a protected test set', { size: 15, bold: true, color: K.q });
}

// ════════════════════════ B. Background ════════════════════════
section('B. Background');

NK = 4;
// 4 — Pixels
{
  const s = slide('How a computer sees an image: a table of numbers');
  const raw = [[0.42, 0.45, 0.61, 0.58], [0.40, 0.39, 0.66, 0.70], [0.38, 0.41, 0.72, 0.75], [0.37, 0.36, 0.69, 0.71]];
  const mn = 0.36, mx = 0.75, str = raw.map((r) => r.map((v) => (v - mn) / (mx - mn)));
  const grid = (m, x0, y0, label) => {
    T(s, label, x0, y0 - 0.5, 3.4, 0.4, { size: 15, bold: true, color: K.steel });
    m.forEach((r, i) => r.forEach((v, j) => {
      const g = Math.round(255 * v).toString(16).padStart(2, '0').toUpperCase();
      s.addShape('rect', { x: x0 + j * 0.82, y: y0 + i * 0.82, w: 0.82, h: 0.82, fill: { color: g + g + g }, line: { color: K.white, width: 1 }, objectName: 'pixel' });
      T(s, v.toFixed(2), x0 + j * 0.82, y0 + i * 0.82, 0.82, 0.82, { size: 12, bold: true, color: v > 0.55 ? K.ink : K.white, align: 'center', valign: 'middle' });
    }));
  };
  grid(raw, 0.6, 2.0, 'A real 4×4 patch (0 = black)');
  arrow(s, 4.05, 3.65, 4.95, 3.65, K.steel);
  T(s, 'contrast\nstretch', 4.0, 3.75, 1.0, 0.6, { size: 12, color: K.mute, align: 'center' });
  grid(str, 5.1, 2.0, 'After contrast stretch');
  T(s, 'x′ = (x − min) / (max − min)', 5.1, 5.45, 3.4, 0.4, { size: 14, font: 'Cambria', italic: true, color: K.steel });
  card(s, 9.1, 1.5, 3.6, 5.2, 'What the computer gets', '• Grayscale = one brightness number per pixel\n\n• A 64×64 image = 4,096 numbers\n\n• Preprocessing: resize → scale to 0–1 → contrast stretch\n\n• Contrast stretch removed a brightness shift between folders (+8.9 pp on validation)', K.steel, K.mist, { bs: 14 });
}

NK = 5;
// 5 — Classical baselines
{
  const s = slide('Classical machine learning: our yardstick');
  pipeline(s, [{ t: 'Image' }, { t: 'Preprocess\nresize · scale · stretch' }, { t: 'Features' }, { t: 'Classifier' }, { t: 'Defect class' }], 0.6, 1.55, 12.1, 0.95, { size: 14 });
  const cards = [
    ['Raw pixels + PCA', 'Squeeze 4,096 pixels into 4–12 numbers that keep the most variation.'],
    ['Texture: LBP + GLCM', 'Count which tiny brightness patterns occur, wherever they are.'],
    ['CNN: MobileNetV3', 'A pretrained network turns each image into 576 descriptive numbers.'],
  ];
  T(s, 'Features we tried', 0.6, 2.85, 6, 0.4, { size: 17, bold: true, color: K.c });
  cards.forEach(([h, b], i) => card(s, 0.6 + i * 4.1, 3.3, 3.9, 1.9, h, b, K.c, K.cSoft));
  T(s, 'Classifiers', 0.6, 5.45, 6, 0.4, { size: 17, bold: true, color: K.c });
  ['RBF-SVM', 'Logistic regression', 'Small CNN (from scratch)', 'Frozen MobileNetV3 + linear'].forEach((t, i) => chip(s, 0.6 + i * 3.05, 5.95, 2.85, t, K.c, K.cSoft));
}

NK = 6;
// 6 — Why quantum
{
  const s = slide('Why quantum?');
  s.addChart(pres.ChartType.bar, [{ name: 'Numbers needed to describe n qubits', labels: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'], values: [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024] }], {
    x: 0.6, y: 1.45, w: 6.2, h: 4.6, barDir: 'col', chartColors: [K.q], showValue: true, dataLabelPosition: 'outEnd', showTitle: true, title: 'n qubits are described by 2ⁿ numbers', titleFontSize: 14, titleColor: K.ink,
    showCatAxisTitle: true, catAxisTitle: 'number of qubits', catAxisTitleFontSize: 12, catAxisTitleColor: K.mute, showLegend: false, valAxisHidden: true, ...AX, valGridLine: { style: 'none' }, objectName: 'chart-2n' });
  const items = [
    ['Huge state space', '7 qubits = 128 numbers; 8 qubits = 256. Hoped to be a rich space for comparing data.'],
    ['Feature map', 'A circuit that turns a list of numbers into a quantum state.'],
    ['Quantum kernel', 'Similarity of two images = overlap of their quantum states.'],
  ];
  items.forEach(([h, b], i) => card(s, 7.2, 1.45 + i * 1.5, 5.5, 1.35, h, b, K.q, K.qSoft, { bs: 14 }));
  box(s, 0.6, 6.25, 12.1, 0.6, K.mist, K.mist, 'Our question: does this help on a real image task, under practical limits? Faster or more accurate was not assumed.', { size: 15, bold: true, color: K.steel });
}

NK = 7;
// 7 — Classical vs quantum
{
  const s = slide('Classical vs quantum, in four rows');
  const rows = [
    ['Basic unit', 'Bit: 0 or 1', 'Qubit: amplitudes for 0 and 1'],
    ['Data', 'A list of numbers', 'A quantum state made by a circuit'],
    ['Similarity', 'Distance between number lists', 'Overlap between two states (kernel)'],
    ['Reading out', 'Read the value directly', 'Measure many times (shots)'],
  ];
  T(s, 'CLASSICAL', 3.35, 1.5, 4.3, 0.4, { size: 15, bold: true, color: K.c, align: 'center' });
  T(s, 'QUANTUM', 8.1, 1.5, 4.6, 0.4, { size: 15, bold: true, color: K.q, align: 'center' });
  rows.forEach(([a, b, c], i) => {
    const y = 2.0 + i * 1.15;
    T(s, a, 0.6, y, 2.6, 0.95, { size: 17, bold: true, color: K.steel, valign: 'middle' });
    box(s, 3.35, y, 4.3, 0.95, K.cSoft, K.cSoft, b, { size: 16 });
    box(s, 8.1, y, 4.6, 0.95, K.qSoft, K.qSoft, c, { size: 16 });
  });
  T(s, 'In this project, the quantum part is mainly a new way of measuring similarity: |⟨ψ|φ⟩|², 1 for identical states, 0 for unrelated ones.', 0.6, 6.4, 12.1, 0.5, { size: 15, italic: true, color: K.mute });
}

NK = 8;
// 8 — Qubit
{
  const s = slide('How a qubit holds information');
  T(s, '|ψ⟩ = α|0⟩ + β|1⟩', 0.6, 1.6, 6.2, 0.8, { font: 'Cambria', size: 34, color: K.ink });
  T(s, '|α|² + |β|² = 1', 0.6, 2.4, 6.2, 0.5, { font: 'Cambria', size: 20, color: K.mute });
  bullets(s, [
    [{ text: 'α, β are amplitudes; ', bold: true }, { text: 'their squares are probabilities' }],
    [{ text: 'Measuring ', bold: true }, { text: 'gives one result: 0 with probability |α|², 1 with |β|²' }],
    [{ text: 'Superposition is not "both values stored": ', bold: true }, { text: 'you only see the odds by repeating the measurement' }],
    [{ text: 'Shots ', bold: true }, { text: '= repetitions. Exact simulation skips them; real hardware cannot' }],
  ], 0.6, 3.2, 6.3, 3.4, { size: 16, psa: 10 });
  // simple Bloch-circle illustration
  s.addShape('ellipse', { x: 7.6, y: 1.55, w: 2.6, h: 2.6, fill: { color: K.mist }, line: { color: K.steel, width: 1.5 }, objectName: 'bloch' });
  s.addShape('line', { x: 8.9, y: 1.75, w: 0.001, h: 2.2, line: { color: 'A6B4C2', width: 1, dashType: 'dash' }, objectName: 'axis' });
  arrow(s, 8.9, 2.85, 9.98, 2.85, K.q);
  T(s, '|0⟩', 8.6, 1.15, 0.6, 0.35, { size: 15, bold: true, align: 'center' });
  T(s, '|1⟩', 8.6, 4.2, 0.6, 0.35, { size: 15, bold: true, align: 'center' });
  T(s, 'RY(π/2)|0⟩: arrow on the equator', 7.2, 4.6, 3.4, 0.35, { size: 12, color: K.mute, align: 'center' });
  s.addChart(pres.ChartType.bar, [{ name: 'Probability', labels: ['0', '1'], values: [50, 50] }], {
    x: 10.6, y: 1.45, w: 2.2, h: 3.4, barDir: 'col', chartColors: [K.q], showValue: true, dataLabelPosition: 'outEnd', dataLabelFormatCode: '0"%"', showLegend: false,
    showTitle: true, title: 'Outcome odds', titleFontSize: 12, titleColor: K.ink, valAxisHidden: true, valAxisMaxVal: 70, ...AX, valGridLine: { style: 'none' }, objectName: 'chart-prob' });
  card(s, 7.2, 5.15, 5.5, 1.6, 'Example', 'For an equal superposition you get 0 about half the time and 1 about half the time. Only many shots reveal that it is 50/50.', K.q, K.qSoft, { bs: 14 });
}

// ════════════════════════ C. Quantum image representation ════════════════════════
section('C. Quantum image representation');

NK = 9;
// 9 — Encoding
{
  const s = slide('Turning an image into a quantum state');
  // 2x2 example image
  const px = [[0.2, 0.6], [0.9, 0.4]];
  px.forEach((r, i) => r.forEach((v, j) => {
    const g = Math.round(255 * v).toString(16).padStart(2, '0').toUpperCase();
    s.addShape('rect', { x: 0.7 + j * 0.9, y: 1.9 + i * 0.9, w: 0.9, h: 0.9, fill: { color: g + g + g }, line: { color: K.white, width: 1.5 }, objectName: 'pixel' });
  }));
  T(s, '2×2 image', 0.7, 3.75, 1.8, 0.35, { size: 13, color: K.mute, align: 'center' });
  arrow(s, 2.7, 2.8, 3.3, 2.8, K.steel);
  box(s, 3.4, 2.05, 2.5, 1.5, K.cSoft, K.c, 'Pixel values\n0.2  0.6\n0.9  0.4', { size: 15 });
  arrow(s, 6.0, 2.8, 6.6, 2.8, K.steel);
  box(s, 6.7, 2.05, 2.6, 1.5, K.qSoft, K.q, 'Encoding circuit\nwrites position + brightness', { size: 14 });
  arrow(s, 9.4, 2.8, 10.0, 2.8, K.steel);
  box(s, 10.1, 2.05, 2.6, 1.5, K.qSoft, K.q, 'Quantum state\nready to compare', { size: 14 });
  img(s, RPT('C1_frqi_circuit_2x2.png'), 0.6, 4.35, 12.1, 1.55, { alt: 'FRQI circuit for the 2x2 example image' });
  T(s, 'A circuit cannot open an image file: every pixel is written in by gates. The two classic recipes are FRQI and NEQR.', 0.6, 6.2, 12.1, 0.5, { size: 15, italic: true, color: K.mute });
}

NK = 10;
// 10 — FRQI
{
  const s = slide('FRQI: brightness stored as an angle');
  T(s, '|I⟩ = (1/√N) Σᵢ (cos θᵢ|0⟩ + sin θᵢ|1⟩) ⊗ |i⟩', 0.6, 1.45, 7.6, 0.6, { font: 'Cambria', size: 22 });
  T(s, 'θᵢ = (π/2) · b · xᵢ', 0.6, 2.05, 7.6, 0.45, { font: 'Cambria', size: 18, color: K.mute });
  bullets(s, [
    [{ text: 'Position qubits ', bold: true }, { text: 'hold where the pixel is (|i⟩)' }],
    [{ text: 'One colour qubit ', bold: true }, { text: 'holds how bright it is, as the angle θᵢ' }],
    [{ text: 'b ', bold: true }, { text: '= angle scale (1 in the original; our best model uses 4)' }],
    [{ text: 'Qubits: ', bold: true }, { text: '2×2 image → 3 · 8×8 patch → 7' }],
  ], 0.6, 2.75, 7.4, 2.4, { size: 16, psa: 8 });
  card(s, 8.5, 1.45, 4.2, 1.7, 'Pixel 0.2 → angle 0.31', 'Probability of reading 0 = cos²θ = 0.905', K.q, K.qSoft, { bs: 14 });
  box(s, 8.5, 3.35, 2.05, 1.1, K.gSoft, K.gSoft, '+ very few qubits', { size: 14, bold: true, color: K.g });
  box(s, 10.65, 3.35, 2.05, 1.1, K.redSoft, K.redSoft, '− brightness read only from many shots', { size: 13, bold: true, color: K.red });
  img(s, RPT('C1_frqi_circuit_2x2.png'), 0.6, 5.2, 12.1, 1.6, { alt: 'FRQI circuit: H gates, then a controlled RY rotation per pixel' });
}

NK = 11;
// 11 — NEQR
{
  const s = slide('NEQR: brightness stored as a binary number');
  T(s, '|I⟩ = (1/√N) Σᵢ |cᵢ⟩ ⊗ |i⟩,   cᵢ = round(xᵢ · (2^q − 1))', 0.6, 1.45, 8, 0.6, { font: 'Cambria', size: 21 });
  bullets(s, [
    [{ text: 'q colour qubits ', bold: true }, { text: '= q bits of brightness; we tested 2, 4 and 8' }],
    [{ text: 'Circuit: ', bold: true }, { text: 'multi-controlled X gates flip the bits that are 1' }],
    [{ text: 'Qubits: ', bold: true }, { text: '4×4 patch with 4 bits → 8 · 16×16 with 8 bits → 16' }],
  ], 0.6, 2.25, 7.4, 1.9, { size: 16, psa: 8 });
  // one pixel, two encodings
  T(s, 'One pixel (0.6), two encodings', 8.6, 1.45, 4.1, 0.4, { size: 15, bold: true, color: K.steel });
  box(s, 8.6, 1.95, 4.1, 0.95, K.qSoft, K.q, 'FRQI: one qubit at angle 0.94 rad', { size: 14 });
  ['1', '0', '0', '1'].forEach((b, i) => box(s, 8.6 + i * 1.04, 3.05, 0.95, 0.75, b === '1' ? K.q : K.white, K.q, b, { size: 20, bold: true, color: b === '1' ? K.white : K.q }));
  T(s, 'NEQR, 4 bits: round(0.6 × 15) = 9 = 1001', 8.6, 3.9, 4.1, 0.4, { size: 13, color: K.mute });
  img(s, RPT('C2_neqr_circuit_2x2.png'), 0.6, 4.45, 7.6, 2.35, { alt: 'NEQR circuit for the 2x2 image with 2 bits' });
  box(s, 8.6, 4.65, 2.0, 1.2, K.gSoft, K.gSoft, '+ exact read-out', { size: 14, bold: true, color: K.g });
  box(s, 10.7, 4.65, 2.0, 1.2, K.redSoft, K.redSoft, '− more qubits and gates', { size: 14, bold: true, color: K.red });
}

NK = 12;
// 12 — FRQI vs NEQR
{
  const s = slide('FRQI vs NEQR: what we measured');
  table(s, [
    ['', 'FRQI', 'NEQR'],
    ['Qubits, 4×4 image', '5', '4 + q  (8 with 4 bits)'],
    ['Brightness stored as', 'an angle', 'a q-bit binary number'],
    ['Compiled gates, 4×4', '1,070', '1,736 (4-bit) · 3,086 (8-bit)'],
    ['Compiled gates, 8×8', '8,339 (3,584 CX)', '16,041 (4-bit)'],
    ['Gate count', 'fixed', 'depends on pixel values'],
    ['Read-out', 'statistical (needs shots)', 'exact, up to rounding'],
    ['Rebuild 8×8 from 1,000 shots (1,800 images)', 'SSIM 0.52', 'SSIM 0.94 (4-bit)'],
  ], 0.6, 1.5, 8.2, [3.4, 2.2, 2.6], { size: 14, rowH: 0.52 });
  card(s, 9.2, 1.5, 3.5, 2.2, 'FRQI saves qubits', 'Fewest qubits, but the brightness has to be estimated from many measurements.', K.q, K.qSoft, { bs: 14 });
  card(s, 9.2, 3.9, 3.5, 2.2, 'NEQR saves shots', 'Exact values back, but more qubits, and more basic gates once compiled.', K.c, K.cSoft, { bs: 14 });
  T(s, 'Compiled = broken into the simple gates real hardware runs (CX, RZ, SX, X). CX gates are the noisiest.', 0.6, 6.35, 12.1, 0.5, { size: 13, italic: true, color: K.mute });
}

// ════════════════════════ D. Quantum machine learning models ════════════════════════
section('D. Quantum machine learning models');

NK = 13;
// 13 — Kernel
{
  const s = slide('What is a quantum kernel?');
  T(s, 'K(x, y) = |⟨φ(x)|φ(y)⟩|²', 0.6, 1.45, 6, 0.7, { font: 'Cambria', size: 28 });
  bullets(s, [
    [{ text: 'Kernel ', bold: true }, { text: '= similarity score: 1 = same, 0 = unrelated' }],
    [{ text: '|φ(x)⟩ ', bold: true }, { text: 'is the state the circuit makes from image x' }],
    [{ text: 'Kernel matrix ', bold: true }, { text: '= the score for every pair; a classical SVM learns from it' }],
    [{ text: 'Training matrix: ', bold: true }, { text: '1,080 × 1,080 images' }],
  ], 0.6, 2.35, 6.0, 3.0, { size: 16, psa: 10 });
  T(s, 'Worked example (Product-RY, 2 features)', 7.1, 1.45, 5.6, 0.4, { size: 15, bold: true, color: K.steel });
  T(s, 'A = (0.5, 1.0)   B = (0.6, 1.1)   C = (2.5, 0.2)', 7.1, 1.9, 5.6, 0.4, { size: 14, color: K.mute });
  const M = [[1, 0.995, 0.248], [0.995, 1, 0.274], [0.248, 0.274, 1]], L = ['A', 'B', 'C'];
  const heat = (v) => { const a = Math.round(255 - v * (255 - 0xD9)), b = Math.round(255 - v * (255 - 0x58)), c = Math.round(255 - v * (255 - 0x1F)); return [a, b, c].map((n) => n.toString(16).padStart(2, '0')).join('').toUpperCase(); };
  L.forEach((l, i) => { T(s, l, 8.0 + i * 1.3, 2.4, 1.3, 0.4, { size: 15, bold: true, align: 'center' }); T(s, l, 7.5, 2.85 + i * 1.1, 0.45, 1.1, { size: 15, bold: true, align: 'center', valign: 'middle' }); });
  M.forEach((r, i) => r.forEach((v, j) => {
    s.addShape('rect', { x: 8.0 + j * 1.3, y: 2.85 + i * 1.1, w: 1.3, h: 1.1, fill: { color: heat(v) }, line: { color: K.white, width: 1.5 }, objectName: 'heat' });
    T(s, v === 1 ? '1' : v.toFixed(3), 8.0 + j * 1.3, 2.85 + i * 1.1, 1.3, 1.1, { size: 16, bold: true, color: v > 0.6 ? K.white : K.ink, align: 'center', valign: 'middle' });
  }));
  T(s, 'A and B are near-identical (0.995); C is different', 7.1, 6.25, 5.6, 0.4, { size: 14, italic: true, color: K.mute });
}

NK = 14;
// 14 — QKC
{
  const s = slide('QKC: quantum kernel + classical SVM');
  pipeline(s, [{ t: 'Image' }, { t: 'Features' }, { t: 'PCA → k numbers' }, { t: 'Scale to angles' }, { t: 'Feature-map circuit\nk qubits', kind: 'q' }, { t: 'Kernel matrix', kind: 'q' }, { t: 'SVM → class' }], 0.6, 1.6, 12.1, 1.1, { size: 13, gap: 0.28 });
  const cards = [
    ['Why PCA?', 'One qubit per feature, and exact simulation is practical up to about 8–12 qubits. So 4,096 pixels or 576 CNN numbers shrink to 4–12.'],
    ['Why scale?', 'Each number becomes a rotation angle: scaled to [0, π] and multiplied by a bandwidth (0.05–1.0) that sets how sensitive the kernel is.'],
    ['Why a classical SVM?', 'The circuit only computes similarities. Finding the best boundary from a similarity matrix is a solved classical problem.'],
  ];
  cards.forEach(([h, b], i) => card(s, 0.6 + i * 4.1, 3.15, 3.9, 2.55, h, b, i === 1 ? K.q : K.steel, K.mist, { bs: 14 }));
  T(s, 'Shots matter: ZZ-Full on 8 pixel features scores 64.0 % exact, 57.1 % with 100 shots, about 63.4 % with 500+ shots.', 0.6, 6.05, 12.1, 0.6, { size: 14, italic: true, color: K.mute });
}

NK = 16;
// 16 — PQK
{
  const s = slide('PQK: looking at each qubit separately');
  T(s, 'QKC', 0.6, 1.55, 1.2, 0.5, { size: 17, bold: true, color: K.q });
  pipeline(s, [{ t: 'Features' }, { t: 'Circuit', kind: 'q' }, { t: 'Whole-state overlap', kind: 'q' }, { t: 'SVM' }], 1.8, 1.45, 5.6, 0.75, { size: 13, gap: 0.25 });
  T(s, 'PQK', 0.6, 2.65, 1.2, 0.5, { size: 17, bold: true, color: K.q });
  pipeline(s, [{ t: 'Features' }, { t: 'Circuit', kind: 'q' }, { t: '3 numbers per qubit (Bloch vector)', kind: 'q' }, { t: 'RBF + SVM' }], 1.8, 2.55, 5.6, 0.75, { size: 12, gap: 0.25 });
  bullets(s, [
    [{ text: 'Bloch vector ', bold: true }, { text: '(⟨X⟩, ⟨Y⟩, ⟨Z⟩) describes one qubit on its own' }],
    [{ text: 'Why tried: ', bold: true }, { text: 'proposed by Huang et al. (2021) to avoid kernel concentration' }],
    [{ text: 'Hypothesis: ', bold: true }, { text: 'per-qubit summaries discard correlations the classifier needed' }],
  ], 0.6, 3.75, 6.8, 2.6, { size: 15, psa: 10 });
  s.addChart(pres.ChartType.bar, [{ name: 'Test accuracy (%)', labels: ['PQK', 'QKC', 'RBF-SVM'], values: [69.7, 91.3, 90.6] }], {
    x: 7.8, y: 1.4, w: 4.9, h: 4.6, barDir: 'col', chartColors: [K.q, K.q, K.c], showValue: true, dataLabelPosition: 'outEnd', dataLabelFormatCode: '0.0', showLegend: false,
    showTitle: true, title: 'Same 8 CNN features (V3)', titleFontSize: 13, titleColor: K.ink, valAxisMinVal: 0, valAxisMaxVal: 100, ...AX, objectName: 'chart-pqk' });
  T(s, 'PQK was the weakest kernel family: about 20 points behind QKC', 7.8, 6.15, 4.9, 0.6, { size: 13, italic: true, color: K.mute });
}

NK = 17;
// 17 — VQC
{
  const s = slide('VQC: a quantum circuit that learns');
  img(s, RPT('C6_vqc_ansatz.png'), 0.6, 1.4, 7.4, 1.9, { alt: 'VQC circuit: RY encoding, two trainable layers, CNOT ring, measurement' });
  T(s, 'Training loop', 0.6, 3.55, 6, 0.4, { size: 16, bold: true, color: K.steel });
  pipeline(s, [{ t: 'Input' }, { t: 'Encode + trainable layers', kind: 'q' }, { t: 'Measure Z', kind: 'q' }, { t: 'Error' }, { t: 'Gradient: parameter-shift' }, { t: 'Update: Adam' }], 0.6, 4.05, 7.4, 1.05, { size: 12, gap: 0.22 });
  T(s, 'Parameter-shift: run the circuit with each angle nudged ±90° to get its exact gradient.', 0.6, 5.35, 7.4, 0.6, { size: 13, color: K.mute });
  T(s, 'Gradients shrank 55× from 4 to 8 qubits (3 layers): a sign of barren plateaus.', 0.6, 5.95, 7.4, 0.6, { size: 13, color: K.mute });
  s.addChart(pres.ChartType.bar, [{ name: 'Test accuracy (%)', labels: ['Encoding only', 'Trained VQC'], values: [90.8, 72.4] }], {
    x: 8.4, y: 1.4, w: 4.3, h: 4.4, barDir: 'col', chartColors: [K.q], showValue: true, dataLabelPosition: 'outEnd', dataLabelFormatCode: '0.0', showLegend: false,
    showTitle: true, title: 'Same 8 CNN features (V3)', titleFontSize: 13, titleColor: K.ink, valAxisMinVal: 0, valAxisMaxVal: 100, ...AX, objectName: 'chart-vqc' });
  T(s, 'Training the circuit made it worse, and took about 1,060 s per run (RBF-SVM: 0.007 s)', 8.4, 5.95, 4.3, 0.8, { size: 13, italic: true, color: K.mute });
}

NK = 18;
// 18 — Hybrid
{
  const s = slide('Hybrid: a CNN sees, a quantum kernel compares');
  pipeline(s, [{ t: 'Image' }, { t: 'MobileNetV3 (frozen)', kind: 'g' }, { t: '576 features' }, { t: 'PCA → 4–8' }, { t: 'QKC or VQC', kind: 'q' }, { t: 'Defect class' }], 0.6, 1.55, 12.1, 1.0, { size: 14 });
  img(s, SHOT('P13_cnn_qubits.png'), 0.6, 2.95, 7.6, 3.55, { frame: true, alt: 'Platform CNN studio: 576 CNN features reduced by PCA to qubit angles' });
  stat(s, 8.7, 2.95, 4, '93.2 %', 'best hybrid (V2): MobileNet PCA 8 + QKC Product-RY', K.q);
  stat(s, 8.7, 4.55, 4, '93.0 %', 'RBF-SVM on the same 8 numbers', K.c);
  T(s, 'The CNN does the seeing; the quantum part only compares 8 numbers.', 8.7, 6.05, 4, 0.7, { size: 14, italic: true, color: K.mute });
}

NK = 19;
// 19 — Patch ensemble
{
  const s = slide('Our innovation: the patch-ensemble mixed-state kernel');
  img(s, PACK('Fig02_patch_encoding_illustration.png'), 0.6, 1.35, 7.4, 5.5, { alt: 'Image, patches, one patch, its amplitudes, the mixed state and the kernel' });
  const steps = [
    ['1 · Cut into patches', '64×64 image, 8×8 patches, stride 4 → 225 patches'],
    ['2 · Encode each patch', 'FRQI: 7 qubits per patch'],
    ['3 · Mix them', 'ρ = (1/P) Σₖ |ψₖ⟩⟨ψₖ|  (a 128×128 density matrix)'],
    ['4 · Compare', 'K(A, B) = Tr(ρ_A ρ_B): every patch of A vs every patch of B'],
  ];
  steps.forEach(([h, b], i) => {
    const y = 1.35 + i * 1.22;
    s.addShape('roundRect', { x: 8.3, y, w: 4.4, h: 1.08, rectRadius: 0.08, fill: { color: K.qSoft }, line: { color: K.qSoft, width: 0.5 }, objectName: 'step' });
    T(s, h, 8.45, y + 0.1, 4.1, 0.38, { size: 15, bold: true, color: K.q });
    T(s, b, 8.45, y + 0.5, 4.1, 0.55, { size: 13 });
  });
  T(s, 'A texture element anywhere in both images adds to the score.', 8.3, 6.3, 4.4, 0.55, { size: 13, italic: true, color: K.mute });
}

// ════════════════════════ E. Methodology and results ════════════════════════
section('E. Methodology and results');

NK = null;
// M — Methodology flow chart
{
  NOTES = 'SAY: This is the whole pipeline. We start from the 1,800 NEU-DET images, fingerprint every file and lock away 360 test images. The rest is split into training and validation, three times with different seeds. Images go through preprocessing and one of several feature routes. Every model family is trained on those features, the best setting of each is chosen on validation data only, frozen with a digital fingerprint, and only then tested once. The statistics compare quantum and classical models, and the platform shows everything.\n\nKEY TAKEAWAY: Every model goes through the same pipeline and the same locked test.';
  const s = slide('Methodology: the whole project pipeline');
  const rowsY = [1.45, 2.85, 4.25, 5.65], lab = ['DATA', 'FEATURES', 'MODELS', 'EVALUATION'];
  lab.forEach((l, i) => T(s, l, 0.6, rowsY[i], 1.4, 0.9, { size: 13, bold: true, color: K.mute, valign: 'middle' }));
  pipeline(s, [{ t: 'NEU-DET\n1,800 images' }, { t: 'SHA-256 manifest' }, { t: 'Group-blocked split\n3 seeds' }, { t: 'Train 1,080 · Val 360' }, { t: 'Locked test 360\n(set aside)', kind: 'q' }], 2.0, rowsY[0], 10.7, 0.9, { size: 13 });
  pipeline(s, [{ t: 'Resize · scale\ncontrast stretch' }, { t: 'Pixels → PCA' }, { t: 'Texture\nLBP + GLCM' }, { t: 'MobileNetV3\n576 → PCA', kind: 'g' }, { t: 'p×p patches' }], 2.0, rowsY[1], 10.7, 0.9, { size: 13 });
  const models = [['Classical', 'c'], ['QKC', 'q'], ['PQK', 'q'], ['VQC', 'q'], ['Hybrid', 'q'], ['FRQI / NEQR', 'q'], ['Patch-ensemble', 'q']];
  const mw = (10.7 - 0.15 * 6) / 7;
  models.forEach(([t, k], i) => box(s, 2.0 + i * (mw + 0.15), rowsY[2], mw, 0.9, k === 'q' ? K.qSoft : K.cSoft, k === 'q' ? K.q : K.c, t, { size: 13, bold: true }));
  pipeline(s, [{ t: 'Select on validation\nmacro-F1' }, { t: 'Freeze\nSHA-256' }, { t: 'Test once\nlocked set', kind: 'q' }, { t: 'Statistics\nbootstrap · Holm' }, { t: 'Q-ImageLab\nplatform' }], 2.0, rowsY[3], 10.7, 0.9, { size: 13 });
  [0, 1, 2].forEach((i) => arrow(s, 7.35, rowsY[i] + 0.93, 7.35, rowsY[i + 1] - 0.03, K.steel));
}

NK = null;
// V — Versions table
{
  NOTES = 'SAY: We got here in versions. V0 was an early prototype with random splits and no locked test, so its numbers cannot be compared and we do not use them. V2 introduced the locked test: whole-image FRQI and NEQR stayed near 60 %, while classical models on CNN features reached 96 %. V3 added texture features and new quantum models; good features lifted every model, but FRQI and NEQR stayed stuck. V4 is our patch-ensemble method: FRQI 87.8 % and NEQR 82.7 %, and a classical model on the same patches gets 83.6 %.\n\nKEY TAKEAWAY: Each version answered one question, and the patch method in V4 is what finally moved FRQI and NEQR.';
  const s = slide('How we got there: every version and its results');
  table(s, [
    ['Version', 'What we tried', 'Runs → models', 'FRQI', 'NEQR', 'Best quantum', 'Best classical', 'What we learned'],
    ['V0', 'SVM, RF, KNN, DT on raw pixels; FRQI/NEQR demo', '—', '—', '—', '—', 'SVM 76.6*', 'Random splits, no locked test: not comparable'],
    ['V2', 'Locked test; QKC, VQC, whole-image FRQI/NEQR, hybrid', '2,583 → 88', '60.6', '60.2', '93.2 (hybrid QKC)', '96.4 (MobileNet)', 'Whole-image encodings stuck near 60 %'],
    ['V3', 'Texture features, PQK, VQC controls', '5,316 → 70', '57.5', '60.2', '95.3 (QKC, texture)', '95.6 (texture SVM)', 'Features set the ceiling'],
    ['V4', 'Patch-ensemble FRQI/NEQR + matched control', '864 → 5', '87.8', '82.7', '87.8 (patch FRQI)', '83.6 (same patches)', 'Patching +27 pp; tied with classical'],
  ], 0.6, 1.5, 12.1, [0.85, 2.85, 1.3, 0.75, 0.75, 1.75, 1.7, 2.15], { size: 13, rowH: 0.85, hl: [4] });
  T(s, 'Test accuracy (%) on the same 360 locked test images, mean of 3 seeds.  *V0 used random in-folder splits; not comparable with V2–V4.', 0.6, 6.0, 12.1, 0.6, { size: 13, italic: true, color: K.mute });
}

NK = null;
// R — Results in one slide
{
  NOTES = 'SAY: Four charts summarise the results. Top left: FRQI and NEQR stayed around 60 % until the patch method in V4 lifted them to 88 % and 83 %. Top right: on the same input, quantum and classical models score almost the same; the closest call is patch FRQI at +4.2 points, which is not significant (p = 0.060). Bottom left: among model families, the quantum kernel on texture features is best, while PQK and the trained VQC fall far behind. Bottom right: more entanglement did not help; the simplest feature map was the most accurate.\n\nKEY TAKEAWAY: Patching made quantum image kernels competitive, but no quantum model beat a classical model given the same input.';
  const s = slide('Results at a glance');
  const small = { ...AX, catAxisLabelFontSize: 10, valAxisLabelFontSize: 9, dataLabelFontSize: 10, titleFontSize: 12, titleColor: K.ink, showTitle: true, showValue: true, dataLabelFormatCode: '0.0', legendFontSize: 10 };
  s.addChart(pres.ChartType.bar, [
    { name: 'FRQI', labels: ['V2', 'V3', 'V4 (patches)'], values: [60.6, 57.5, 87.8] },
    { name: 'NEQR', labels: ['V2', 'V3', 'V4 (patches)'], values: [60.2, 60.2, 82.7] },
  ], { x: 0.6, y: 1.3, w: 5.9, h: 2.6, barDir: 'col', barGrouping: 'clustered', chartColors: [K.q, 'F0A27A'], dataLabelPosition: 'outEnd', showLegend: true, legendPos: 'r',
    valAxisMinVal: 0, valAxisMaxVal: 100, title: '1 · FRQI and NEQR across versions (%)', ...small, objectName: 'chart-versions' });
  s.addChart(pres.ChartType.bar, [
    { name: 'Quantum', labels: ['Same patches', 'CNN PCA 8', 'Texture 12', 'Best overall'], values: [87.8, 93.2, 95.3, 95.3] },
    { name: 'Classical', labels: ['Same patches', 'CNN PCA 8', 'Texture 12', 'Best overall'], values: [83.6, 93.0, 95.6, 96.4] },
  ], { x: 6.8, y: 1.3, w: 5.9, h: 2.6, barDir: 'col', barGrouping: 'clustered', chartColors: [K.q, K.c], dataLabelPosition: 'outEnd', showLegend: true, legendPos: 'r',
    valAxisMinVal: 60, valAxisMaxVal: 100, title: '2 · Quantum vs classical on the same input (%)', ...small, objectName: 'chart-qvc' });
  s.addChart(pres.ChartType.bar, [{ name: 'Accuracy', labels: ['QKC', 'Hybrid', 'RBF-SVM', 'VQC', 'PQK'], values: [95.3, 91.3, 90.6, 72.4, 69.7] }],
    { x: 0.6, y: 4.05, w: 5.9, h: 2.4, barDir: 'col', chartColors: [K.q, K.q, K.c, K.q, K.q], dataLabelPosition: 'outEnd', showLegend: false,
      valAxisMinVal: 0, valAxisMaxVal: 100, title: '3 · Model families, V3 (%)', ...small, objectName: 'chart-families' });
  s.addChart(pres.ChartType.bar, [{ name: 'Accuracy', labels: ['Product-RY (no links)', 'ZZ-Full (all pairs)', 'ZZ-Linear (neighbours)'], values: [95.3, 89.1, 60.6] }],
    { x: 6.8, y: 4.05, w: 5.9, h: 2.4, barDir: 'col', chartColors: [K.q], dataLabelPosition: 'outEnd', showLegend: false,
      valAxisMinVal: 0, valAxisMaxVal: 100, title: '4 · More entanglement did not help: QKC, 12 texture features (%)', ...small, objectName: 'chart-entangle' });
  box(s, 0.6, 6.5, 12.1, 0.45, K.mist, K.mist, 'Patching: +27.1 pp for FRQI (p < 0.001)  ·  Quantum vs classical on the same input: no significant difference (closest: +4.2 pp, p = 0.060)', { size: 13, bold: true, color: K.steel });
}

// ════════════════════════ F. Limitations, future scope and platform ════════════════════════
section('F. Limitations, future scope and platform');

NK = 31;
// 31 — Limitations
{
  const s = slide('Limitations and practical challenges');
  bullets(s, [
    [{ text: 'Simulation only: ', bold: true }, { text: 'noiseless, on a laptop CPU; no quantum hardware' }],
    [{ text: 'Deep circuits: ', bold: true }, { text: '3,584 CX gates for one 8×8 FRQI patch' }],
    [{ text: 'Shots: ', bold: true }, { text: 'FRQI read-out needs many; the swap test was not run with shots' }],
    [{ text: 'PCA ', bold: true }, { text: 'throws information away before the quantum step' }],
    [{ text: 'One dataset; ', bold: true }, { text: 'the test set was reused across V2–V4' }],
  ], 0.6, 1.5, 6.0, 5.0, { size: 17, psa: 14 });
  img(s, PACK('Fig10_circuit_resources.png'), 6.9, 1.6, 5.8, 3.3, { frame: true, alt: 'Circuit resources of the FRQI and NEQR encoders' });
  T(s, 'Real-device accuracy would be lower than these simulated results.', 6.9, 5.3, 5.8, 0.6, { size: 14, italic: true, color: K.mute });
}

NK = 32;
// 32 — Future scope
{
  const s = slide('Future scope');
  const f = [['Finite shots + noise', 'Run the 15-qubit swap test with shots and noise models'], ['Fresh data', 'A new steel dataset never used for decisions'], ['Harder encoders', 'Circuits that are hard to simulate classically'], ['Real hardware', 'A small trial on selected image pairs'], ['Platform', 'Multi-user; launch experiments from the browser']];
  s.addShape('line', { x: 0.9, y: 2.6, w: 11.5, h: 0.001, line: { color: K.line, width: 2.5 }, objectName: 'timeline' });
  f.forEach(([h, b], i) => {
    const x = 0.6 + i * 2.48;
    s.addShape('ellipse', { x: x + 0.85, y: 2.3, w: 0.6, h: 0.6, fill: { color: i === 3 ? K.q : K.steel }, line: { color: K.white, width: 2 }, objectName: 'dot' });
    T(s, h, x, 3.15, 2.3, 0.5, { size: 17, bold: true, align: 'center' });
    T(s, b, x, 3.7, 2.3, 1.3, { size: 14, color: K.mute, align: 'center' });
  });
  box(s, 0.6, 5.5, 12.1, 0.8, K.mist, K.mist, 'Each step tests an open question. None promises an improvement.', { size: 16, bold: true, color: K.steel });
}

NK = 33;
// 33 — Platform
{
  const s = slide('The Q-ImageLab platform');
  const shots = [[SHOT('P01_overview.png'), 'Overview of every protocol'], [SHOT('P17_how_it_works_mixed_state.png'), 'Frozen model replayed live'], [SHOT('P11_playground_sandbox.png'), '3×3 playground sandbox'], [SHOT('P13_cnn_qubits.png'), 'CNN feature studio']];
  shots.forEach(([f, cap], i) => {
    const x = 0.6 + (i % 2) * 4.15, y = 1.4 + Math.floor(i / 2) * 2.75;
    img(s, f, x, y, 3.95, 2.2, { alt: cap });
    T(s, cap, x, y + 2.25, 3.95, 0.35, { size: 12, color: K.mute, align: 'center' });
  });
  bullets(s, [
    'FastAPI (Python) + React 19, reading only saved results',
    'Upload your own image: encode, rebuild and classify',
    'Circuit highlighting, sandbox, 27-question quiz',
    '201 back-end + 48 front-end tests; live replay reproduces all 360 saved predictions',
  ], 9.1, 1.5, 3.6, 5.2, { size: 15, psa: 12 });
}

pres.writeFile({ fileName: OUT }).then(async (f) => {
  const { applyTheme } = require(process.env.APPLY_THEME);
  await applyTheme(OUT, THEME);
  console.log(`wrote ${f}: ${N} slides`);
});
