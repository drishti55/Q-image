/* eslint-disable @typescript-eslint/no-explicit-any */
// Classical walkthroughs. Every number is read from the V3 playground data (computed with the project's real,
// train-fitted transforms). No classifier output is shown for the artificial grid.
import { ArrayImage, Heatmap, IO, Note, ValueBars, Vec, fx } from './widgets';
import type { Algo, Ctx, Step } from './types';
import { f4 } from './types';

const CLS = ['Crazing', 'Inclusion', 'Patches', 'Pitted', 'Rolled-in', 'Scratches'];
export const NO_PRED = <Note tone="amber">No class is shown for this grid: it is an artificial 3×3 image, not a steel-surface photo, so a model's "answer" for it would be meaningless. Real accuracy on the 360 locked NEU-DET test images is on the Quantum vs Classical page.</Note>;
const tr = (c: Ctx) => c.d.pixel_traces[c.sel];
const delta8 = (c: Ctx) => tr(c).pca8_standard_delta as number[];
const l2 = (v: number[]) => Math.sqrt(v.reduce((a, b) => a + b * b, 0));

function FlatVector({ raw, sel, norm }: { raw: number[]; sel: number; norm?: boolean }) {
  return (
    <div className="flex flex-wrap gap-1 font-mono text-sm" aria-label={norm ? 'normalised vector' : 'flattened vector'}>
      <span className="text-slate-500">[</span>
      {raw.map((v, i) => (
        <span key={i} className={`rounded px-1.5 py-0.5 transition-all duration-500 ${i === sel ? 'bg-cyan-500/25 text-cyan-100 ring-2 ring-cyan-400' : v ? 'text-slate-100' : 'text-slate-500'}`}>
          {norm ? (v / 255).toFixed(3) : v}{i < raw.length - 1 ? ',' : ''}
        </span>
      ))}
      <span className="text-slate-500">]</span>
    </div>
  );
}

// ─── 1. Preprocessing ───
export const preprocessing: Algo = {
  id: 'preprocessing', family: 'classical', name: 'Preprocessing', blurb: 'Pixels → normalised vector',
  trace: (c) => [
    { key: 'raw', label: 'pixel', value: `${c.px.v}`, short: `${c.px.v}` },
    { key: 'norm', label: 'normalised', value: `${c.px.v}/255 = ${f4(c.px.v / 255)}`, short: (c.px.v / 255).toFixed(3) },
    { key: 'flat', label: 'vector entry', value: `x[${tr(c).flat_index}] = ${f4(c.px.v / 255)}`, short: `x[${tr(c).flat_index}]` },
    { key: 'resize', label: '64×64 resize', value: 'spread over a ≈21×21 block', short: '64²' },
    { key: 'scale', label: 'standardised', value: 'z = (x − mean) / std', short: 'z' },
  ],
  steps: (c): Step[] => {
    const { d, px } = c;
    const raw: number[] = d.flattened_raw_9;
    const p8 = d.preprocessing.pca['8'];
    return [
      { title: 'Original grayscale image', stage: 'raw', hl: 'given',
        explain: 'A 3×3 grayscale image. Four cells hold real pixel values (70, 180, 19, 20); the other five are zero padding.',
        why: 'Every algorithm on this page starts from exactly these nine numbers, so differences come only from the processing.',
        out: <>Selected pixel: <b>{px.v}</b> at row {px.r + 1}, column {px.c + 1}</>,
        interp: 'Classical view: an image is simply a grid of brightness numbers (0 = black, 255 = white).',
        body: <IO input="3×3 grid of 8-bit intensities" output="9 numbers: 4 image pixels + 5 zero-padding cells" /> },
      { title: 'Pixel extraction', stage: 'raw', hl: 'selected',
        explain: 'Each cell is read as one number together with its position (row, column).',
        why: 'Algorithms work on numbers, so the picture is turned into a list of (position, intensity) pairs.',
        out: <>({px.r + 1}, {px.c + 1}) → {px.v}</>, interp: 'Classical: position is implicit in the order of the numbers.',
        body: (
          <table className="text-sm tabular-nums"><thead className="text-left text-xs text-slate-500"><tr><th className="pr-6">cell (row, col)</th><th className="pr-6">intensity</th><th>kind</th></tr></thead>
            <tbody>{(d.grid as number[][]).flatMap((row, r) => row.map((v, cc) => (
              <tr key={`${r}${cc}`} className={r === px.r && cc === px.c ? 'bg-cyan-500/15 text-cyan-100' : v ? 'text-white' : 'text-slate-500'}>
                <td className="pr-6">({r + 1}, {cc + 1})</td><td className="pr-6">{v}</td><td>{r < 2 && cc < 2 ? 'image pixel' : 'zero padding'}</td></tr>)))}</tbody></table>
        ) },
      { title: 'Normalisation', stage: 'norm', hl: 'selected',
        explain: 'Every intensity is divided by 255 so all values lie between 0 and 1 — the same operation preprocess_image applies to every NEU-DET image.',
        why: 'Models train more stably when inputs share a small, fixed range; it also makes images with different bit depths comparable.',
        formula: <>normalized_pixel = pixel / 255</>,
        out: <>{px.v} / 255 = <b>{f4(px.v / 255)}</b></>, interp: 'Classical: a simple rescaling; no information is lost.',
        body: <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">{(d.pixel_traces as any[]).map((t, i) => (
          <div key={i} className={`rounded-lg p-2 ring-1 transition ${i === c.sel ? 'bg-cyan-500/15 ring-cyan-400' : 'bg-slate-900/60 ring-slate-800'}`}>
            <div className="text-xs text-slate-400">({t.row + 1},{t.col + 1})</div><div className="font-mono text-white">{t.value}/255 = {f4(t.normalized)}</div></div>))}</div> },
      { title: 'Flattening', stage: 'flat', hl: 'selected',
        explain: 'The grid is read row by row into a single vector of 9 numbers. The selected pixel becomes one entry of that vector.',
        why: 'Classical models such as logistic regression or an SVM expect one flat vector per image.',
        formula: <>x = [p₁₁, p₁₂, p₁₃, p₂₁, p₂₂, p₂₃, p₃₁, p₃₂, p₃₃]</>,
        out: <>x[{tr(c).flat_index}] = {px.v} → {f4(px.v / 255)}</>, interp: 'Classical: the 2-D neighbourhood structure is no longer explicit after flattening.',
        body: <div className="space-y-3"><div className="text-xs text-slate-400">raw pixel vector</div><FlatVector raw={raw} sel={tr(c).flat_index} />
          <div className="text-xs text-slate-400">normalised vector</div><FlatVector raw={raw} sel={tr(c).flat_index} norm /></div> },
      { title: 'Pixel vector vs reduced feature vector', stage: 'flat', hl: 'given',
        explain: 'A pixel vector has one number per pixel (9 here; 4,096 for a 64×64 NEU-DET image). A reduced feature vector keeps only a few numbers that summarise the image (8 PCA features in this project).',
        why: 'Thousands of correlated pixel values are hard to learn from with only 1,080 training images, and a quantum circuit needs one qubit per feature.',
        out: <>4,096 pixel values → 8 features ({fx(p8.explained_variance_ratio.reduce((a: number, b: number) => a + b, 0) * 100, 1)}% of the training-image variance kept)</>,
        interp: 'Classical: dimensionality reduction trades detail for robustness and fewer inputs.',
        body: <div className="grid gap-3 sm:grid-cols-2"><div className="rounded-xl bg-slate-900/60 p-3 ring-1 ring-slate-800"><div className="text-xs text-slate-400">pixel vector</div><div className="mt-1 text-2xl font-semibold text-white">4,096</div><div className="text-xs text-slate-500">values per 64×64 image</div></div>
          <div className="rounded-xl bg-cyan-500/10 p-3 ring-1 ring-cyan-500/30"><div className="text-xs text-cyan-200">reduced feature vector</div><div className="mt-1 text-2xl font-semibold text-white">8</div><div className="text-xs text-slate-400">PCA features (see the PCA walkthrough)</div></div></div> },
      { title: 'Resize to the model input size', stage: 'resize', hl: 'selected',
        explain: 'The trained pixel models expect 64×64 images, so the 3×3 grid goes through the same bilinear resize as every NEU-DET image. Each original pixel now covers a block of about 21×21 resized pixels.',
        why: 'All images must have the same size as the training images for the learned transforms to apply.',
        out: <>3×3 → 64×64 = 4,096 values</>, interp: 'Classical: interpolation smooths the sharp pixel boundaries.',
        body: <div className="flex flex-wrap items-end gap-6"><ArrayImage data={d.grid} max={255} size={120} label="3×3 input" /><ArrayImage data={d.preprocessing.resized_64} max={255} size={180} label="64×64 after bilinear resize" /></div> },
      { title: 'Feature scaling', stage: 'scale', hl: 'selected',
        explain: 'Each of the 4,096 resized pixels is standardised with the mean and standard deviation learned from the 1,080 training images (never from test images).',
        why: 'Standardisation puts every pixel on a comparable scale before PCA, so bright regions do not dominate.',
        formula: <>zⱼ = (xⱼ − meanⱼ) / stdⱼ</>,
        out: <>z of the demo image: mean {fx(p8.standardized_pixels.mean, 3)}, min {fx(p8.standardized_pixels.min, 3)}, max {fx(p8.standardized_pixels.max, 3)}</>,
        interp: 'Classical: a fixed affine transform fitted on training data only.',
        body: <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">{(['mean', 'std', 'min', 'max'] as const).map((k) => <div key={k} className="rounded-lg bg-slate-900/60 p-2 ring-1 ring-slate-800"><div className="text-xs text-slate-400">{k} of z</div><div className="font-mono text-white">{fx(p8.standardized_pixels[k], 3)}</div></div>)}</div> },
    ];
  },
};

// ─── 2. PCA ───
export const pca: Algo = {
  id: 'pca', family: 'classical', name: 'PCA', blurb: 'Real fitted transform: 4,096 → 8 features',
  trace: (c) => [
    { key: 'in', label: 'normalised', value: f4(c.px.v / 255), short: (c.px.v / 255).toFixed(3) },
    { key: 'comp', label: 'components', value: 'weights learned from 1,080 images', short: 'w' },
    { key: 'delta', label: 'effect on features', value: `‖Δ‖ = ${l2(delta8(c)).toFixed(3)}`, short: `Δ${l2(delta8(c)).toFixed(2)}` },
    { key: 'out', label: 'feature vector', value: '8 numbers', short: '8-d' },
  ],
  steps: (c): Step[] => {
    const p8 = c.d.preprocessing.pca['8'];
    const dl = delta8(c);
    const big = dl.map(Math.abs).indexOf(Math.max(...dl.map(Math.abs))) + 1;
    return [
      { title: 'Input: standardised pixels', stage: 'in', hl: 'selected',
        explain: 'PCA receives the 4,096 standardised pixels of the resized image (Preprocessing walkthrough).',
        why: 'PCA needs zero-mean, comparably scaled inputs.', out: <>4,096 values</>,
        interp: 'Classical: the image is a point in a 4,096-dimensional space.', body: <IO input="64×64 standardised pixels" output="8 principal-component scores" /> },
      { title: 'Principal components (learned on training images)', stage: 'comp', hl: 'none',
        explain: `These are the first three of eight real principal components, fitted on ${p8.fitted_on_n_train} training images (seed 0). Each is a 64×64 weight pattern.`,
        why: 'Components point in the directions along which steel images vary most; projecting onto them keeps the most information in few numbers.',
        out: <>variance captured by component 1: {fx(p8.explained_variance_ratio[0] * 100, 1)}%</>, interp: 'Classical: an orthogonal change of basis learned from data.',
        body: <div className="flex flex-wrap gap-3">{c.d.preprocessing.pca_components_64.map((m: number[][], i: number) => <ArrayImage key={i} data={m} size={110} label={`component ${i + 1} (${fx(p8.explained_variance_ratio[i] * 100, 1)}%)`} />)}</div> },
      { title: 'Projection', stage: 'delta', hl: 'none',
        explain: 'Each PCA feature is a weighted sum of all 4,096 standardised pixels, using that component as the weights.',
        why: 'This compresses the image to 8 numbers while keeping the main patterns.',
        formula: <>score_k = component_k · z      (k = 1 … 8)</>,
        out: <>8 scores: <Vec v={p8.scores} digits={1} /></>, interp: 'Classical: a linear map, fully determined by the training data.',
        body: <ValueBars signed items={(p8.standard as number[]).map((v, i) => ({ label: `feature ${i + 1}`, value: v }))} /> },
      { title: "The selected pixel's contribution", stage: 'delta', hl: 'selected',
        explain: `How much each standardised PCA feature changes when pixel ${c.px.v} is removed (set to 0). Computed with the real fitted transform.`,
        why: 'Shows that one pixel influences every feature: PCA features mix information from the whole image.',
        formula: <>Δ = features(image) − features(image with this pixel = 0)</>,
        out: <>‖Δ‖ = {l2(dl).toFixed(3)} · largest change on feature {big}</>,
        interp: 'Classical: the brighter the pixel, the larger its effect (compare 180 with 19).',
        body: <ValueBars signed items={dl.map((v, i) => ({ label: `Δ feature ${i + 1}`, value: v }))} /> },
      { title: 'Reduced feature vector', stage: 'out', hl: 'given',
        explain: 'The 8 standardised scores are the input of the classical classifiers (and, rescaled to angles, of the quantum circuits).',
        why: 'Eight numbers can be learned from reliably and map onto eight qubits.',
        out: <Vec v={p8.standard} digits={3} />, interp: 'Classical: a compact numerical summary of the image.',
        body: <><IO input="4,096 pixel values" output={<>8 features (<Vec v={p8.standard} digits={2} />)</>} /><Note>Real fitted PCA (seed 0). It is applied to the demo image, not fitted on it: four pixels cannot define principal components.</Note></> },
    ];
  },
};

// ─── 3. Logistic regression ───
const dzOf = (c: Ctx) => (c.d.logreg.W as number[][]).map((w) => w.reduce((a, wi, i) => a + wi * delta8(c)[i], 0));
export const logreg: Algo = {
  id: 'logreg', family: 'classical', name: 'Logistic regression', blurb: 'Weighted sums → probabilities',
  trace: (c) => [
    { key: 'in', label: 'feature change', value: `‖Δx‖ = ${l2(delta8(c)).toFixed(3)}`, short: 'Δx' },
    { key: 'w', label: 'weights', value: '6 × 8 learned weights', short: 'W' },
    { key: 'sum', label: 'score change', value: `largest |Δz| = ${Math.max(...dzOf(c).map(Math.abs)).toFixed(3)}`, short: 'Δz' },
    { key: 'soft', label: 'softmax', value: 'scores → probabilities', short: 'σ' },
  ],
  steps: (c): Step[] => {
    const lr = c.d.logreg;
    const dz = dzOf(c);
    const ex = [2.0, 0.5, -1.0, 0.0, 1.0, -0.5];
    const ez = ex.map(Math.exp), s = ez.reduce((a, b) => a + b, 0);
    return [
      { title: 'Input features', stage: 'in', hl: 'selected', explain: 'The 8 standardised PCA features (PCA walkthrough).',
        why: 'Logistic regression needs a fixed-length numeric vector.', out: <Vec v={lr.x} digits={3} />,
        interp: 'Classical: each feature is one coordinate.', body: <ValueBars signed items={(lr.x as number[]).map((v, i) => ({ label: `x${i + 1}`, value: v }))} /> },
      { title: 'Learned weights', stage: 'w', hl: 'none',
        explain: 'The trained model (seed 0) has one weight per (class, feature) pair plus one bias per class. These are its real weights.',
        why: 'The weights encode which features push towards which defect class.', out: <>{lr.W.length} × {lr.W[0].length} weights + {lr.b.length} biases</>,
        interp: 'Classical: 54 numbers fitted by gradient descent on the training images.',
        body: <Heatmap m={(lr.W as number[][]).map((r) => r.map((v) => Math.min(1, Math.abs(v) / 3)))} labels={CLS} title="|weight| per class (rows) × feature (columns), scaled to [0, 1]" digits={2} /> },
      { title: 'Weighted sum (score) per class', stage: 'sum', hl: 'selected',
        explain: `Each class score is a weighted sum of the features plus a bias. Shown here: how much each class score changes because of pixel ${c.px.v} (real weights × real feature change).`,
        why: 'A higher score means more evidence for that class.',
        formula: <>z_c = w_c · x + b_c        Δz_c = w_c · Δx</>,
        out: <>Δz = <Vec v={dz} digits={3} /></>, interp: 'Classical: a linear decision rule per class.',
        body: <ValueBars signed items={dz.map((v, i) => ({ label: CLS[i], value: v }))} /> },
      { title: 'Softmax: scores → probabilities', stage: 'soft', hl: 'none',
        explain: 'Scores can be any real number; softmax turns them into positive numbers that add up to 1. The numbers below illustrate the arithmetic only — they are not model outputs for this grid.',
        why: 'Probabilities are easier to interpret and are what cross-entropy training needs.',
        formula: <>p_c = e^(z_c) / Σ_j e^(z_j)</>,
        out: <>example z = [{ex.join(', ')}] → p = [{ez.map((e) => (e / s).toFixed(3)).join(', ')}]</>,
        interp: 'Classical: for a real image the class with the largest probability is the prediction.',
        body: <><table className="text-xs tabular-nums"><thead className="text-left text-slate-500"><tr><th className="pr-4">score z (example)</th><th className="pr-4">e^z</th><th>probability</th></tr></thead>
          <tbody>{ex.map((z, i) => <tr key={i}><td className="pr-4 font-mono">{z.toFixed(2)}</td><td className="pr-4 font-mono">{ez[i].toFixed(3)}</td><td className="font-mono text-cyan-200">{(ez[i] / s).toFixed(3)}</td></tr>)}</tbody></table>{NO_PRED}</> },
    ];
  },
};

// ─── 4. RBF-SVM ───
function Scatter({ d }: { d: any }) {
  const sc = d.preprocessing.train_scatter_pc12;
  const xs: number[] = [...sc.x, d.preprocessing.demo_pc12[0]], ys: number[] = [...sc.y, d.preprocessing.demo_pc12[1]];
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const W = 420, H = 240, px = (v: number) => 10 + ((v - x0) / (x1 - x0 || 1)) * (W - 20), py = (v: number) => H - 10 - ((v - y0) / (y1 - y0 || 1)) * (H - 20);
  const COL = ['#3987e5', '#d95926', '#199e70', '#c98500', '#9085e9', '#d55181'];
  return (
    <div><svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-md rounded-xl bg-slate-950/60 ring-1 ring-slate-800" role="img" aria-label="training scatter">
      {(sc.x as number[]).map((x, i) => <circle key={i} cx={px(x)} cy={py(sc.y[i])} r={2.6} fill={COL[sc.label[i]]} opacity={0.7} />)}
      <circle cx={px(d.preprocessing.demo_pc12[0])} cy={py(d.preprocessing.demo_pc12[1])} r={7} fill="#fff" stroke="#0f172a" strokeWidth={2} />
    </svg>
    <div className="mt-1 flex flex-wrap gap-3 text-[11px] text-slate-400">{CLS.map((n, i) => <span key={n} className="inline-flex items-center gap-1"><span className="h-2 w-2 rounded-full" style={{ background: COL[i] }} />{n}</span>)}<span>⚪ demo</span></div></div>
  );
}

export const svm: Algo = {
  id: 'svm', family: 'classical', name: 'RBF-SVM', blurb: 'Similarity to stored training examples',
  trace: (c) => [
    { key: 'in', label: 'feature change', value: `‖Δx‖ = ${l2(delta8(c)).toFixed(3)}`, short: 'Δx' },
    { key: 'dist', label: 'squared distance', value: '‖x − y‖²', short: 'd²' },
    { key: 'k', label: 'kernel', value: 'exp(−γ d²)', short: 'K' },
    { key: 'sv', label: 'support vectors', value: `${(c.d.svm.n_support as number[]).reduce((a, b) => a + b, 0)} stored examples`, short: 'SV' },
  ],
  steps: (c): Step[] => {
    const s = c.d.svm;
    const nsv = (s.n_support as number[]).reduce((a, b) => a + b, 0);
    return [
      { title: 'Feature input', stage: 'in', hl: 'selected', explain: 'The SVM receives the same 8 standardised PCA features.',
        why: 'Distances are only meaningful on comparably scaled features.', out: <Vec v={s.x} digits={3} />,
        interp: 'Classical: the image is a point in an 8-dimensional space.', body: <ValueBars signed items={(s.x as number[]).map((v: number, i: number) => ({ label: `x${i + 1}`, value: v }))} /> },
      { title: 'Distance to a stored example', stage: 'dist', hl: 'none',
        explain: `The model stores ${nsv} support vectors (training images). For each one it computes the squared distance to the input.`,
        why: 'Images that are close in feature space are likely to look alike.', formula: <>d² = ‖x − y‖²</>,
        out: <>nearest support vector: d² = {fx(s.example.dist2, 3)}</>, interp: 'Classical: plain Euclidean geometry.',
        body: <Note>Distances are computed to every one of the {nsv} support vectors.</Note> },
      { title: 'RBF kernel', stage: 'k', hl: 'none',
        explain: 'The distance becomes a similarity between 0 and 1. γ and C were chosen on the validation split. Bars: the 8 most similar support vectors.',
        why: 'The kernel lets a linear method draw curved decision boundaries.',
        formula: <>K(x, y) = exp(−γ · ‖x − y‖²)</>,
        out: <>K = exp(−{fx(s.gamma, 2)} × {fx(s.example.dist2, 3)}) = <b>{fx(s.example.K, 4)}</b></>,
        interp: 'Classical: the quantum-kernel walkthrough replaces exactly this similarity with a quantum state overlap.',
        body: <ValueBars max={Math.max(...(s.top_support_vectors as any[]).map((t) => t.K))} items={(s.top_support_vectors as any[]).map((t, i) => ({ label: `support vector #${i + 1}`, value: t.K }))} digits={4} /> },
      { title: 'Decision boundary intuition', stage: 'sv', hl: 'none',
        explain: 'Training images on the first two PCA features, coloured by class, with the demo image in white. The real boundary lives in 8 dimensions.',
        why: 'The SVM separates classes using only the support vectors near the boundaries.',
        formula: <>f(x) = Σᵢ αᵢ yᵢ K(x, xᵢ) + b</>, out: <>{nsv} support vectors, C = {fx(s.C, 0)}, γ = {fx(s.gamma, 2)}</>,
        interp: 'Classical: training solves a convex optimisation for the weights αᵢ.',
        body: <><Scatter d={c.d} />{NO_PRED}</> },
    ];
  },
};

// ─── 5. Small CNN ───
export const cnn: Algo = {
  id: 'cnn', family: 'classical', name: 'CNN features', blurb: 'Learned filters and feature maps',
  trace: (c) => [
    { key: 'in', label: 'network input', value: `(${f4(c.px.v / 255)} − 0.5)/0.25 = ${tr(c).cnn_input.toFixed(3)}`, short: tr(c).cnn_input.toFixed(2) },
    { key: 'conv', label: '3×3 filters', value: '16 learned filters', short: '∗' },
    { key: 'maps', label: 'feature maps', value: 'local pattern responses', short: 'map' },
    { key: 'pool', label: 'pooling', value: '128 → 8 spatial size', short: '↓' },
    { key: 'vec', label: 'feature vector', value: '128 numbers', short: '128' },
  ],
  steps: (c): Step[] => {
    const s = c.d.small_cnn;
    const maps = (x: any, label: string) => <div><div className="mb-2 text-xs text-slate-400">{label}</div><div className="flex flex-wrap gap-2">{x.conv1_maps.map((f: any) => <ArrayImage key={f.channel} data={f.map} size={70} label={`ch ${f.channel}`} />)}</div></div>;
    return [
      { title: 'Input image', stage: 'in', hl: 'selected', explain: 'The small CNN reads 128×128 images scaled as (x − 0.5)/0.25. A real NEU-DET training image is shown for comparison.',
        why: 'Centred inputs make the first layer train faster.', formula: <>input = (pixel/255 − 0.5) / 0.25</>,
        out: <>pixel {c.px.v} → {tr(c).cnn_input.toFixed(4)}</>, interp: 'Classical: the 2-D layout is kept (no flattening).',
        body: <div className="flex flex-wrap gap-6"><ArrayImage data={s.demo.input_128} max={255} size={150} label="3×3 demo → 128×128" /><ArrayImage data={s.real.input_128} max={255} size={150} label={`real training image: ${s.real.image.split('/').pop()}`} /></div> },
      { title: 'Convolution', stage: 'conv', hl: 'selected', explain: 'The first layer slides 16 learned 3×3 filters over the image. These are the actual trained filters (8 shown).',
        why: 'Filters detect local patterns — edges, spots, lines — wherever they occur.',
        formula: <>feature(i, j) = Σ filter(a, b) · image(i + a, j + b) + bias</>, out: <>16 filters × 9 weights</>,
        interp: 'Classical: weight sharing makes the detector position-independent.',
        body: <div className="flex flex-wrap gap-2">{s.demo.conv1_kernels.map((k: number[][], i: number) => <ArrayImage key={i} data={k} size={56} label={`filter ${s.demo.conv1_maps[i].channel}`} />)}</div> },
      { title: 'Feature maps + ReLU', stage: 'maps', hl: 'none', explain: 'Each filter produces a map that lights up where its pattern occurs; ReLU keeps only positive responses. Captured from the trained network.',
        why: 'Maps tell the next layers where each pattern is.', formula: <>ReLU(v) = max(0, v)</>, out: <>16 maps of 128×128</>,
        interp: 'Classical: the demo grid has only a few edges; the real image has rich texture.',
        body: <div className="grid gap-4 lg:grid-cols-2">{maps(s.demo, '3×3 demo')}{maps(s.real, 'real training image')}</div> },
      { title: 'Pooling and deeper layers', stage: 'pool', hl: 'none', explain: 'Max-pooling halves the size; three more blocks learn larger patterns.',
        why: 'Pooling adds tolerance to small shifts and reduces computation.', out: <>128×128 → 8×8 × 128 channels</>,
        interp: 'Classical: a hierarchy from edges to textures.',
        body: <table className="text-sm"><tbody>{s.architecture.map(([n, shape]: [string, number[]]) => <tr key={n}><td className="py-1 pr-6 text-slate-300">{n}</td><td className="font-mono text-cyan-200">{shape.join(' × ')}</td></tr>)}</tbody></table> },
      { title: 'Feature vector', stage: 'vec', hl: 'none', explain: `Global average pooling gives one vector of ${s.demo.embedding_dim} numbers per image; a linear layer then maps it to 6 class scores.`,
        why: 'This learned vector is the representation the classifier uses.', out: <Vec v={s.demo.embedding_first16} digits={2} max={8} />,
        interp: 'Classical: learned features, unlike PCA, are trained to separate the defect classes.',
        body: <><ValueBars items={(s.demo.embedding_first16 as number[]).map((v, i) => ({ label: `f${i + 1}`, value: v }))} />{NO_PRED}</> },
    ];
  },
};

// ─── 6. MobileNetV3 ───
export const mnv3: Algo = {
  id: 'mnv3', family: 'classical', name: 'MobileNetV3 features', blurb: 'Frozen pretrained feature extractor',
  trace: (c) => [
    { key: 'in', label: 'RGB copy', value: `(${c.px.v}, ${c.px.v}, ${c.px.v})`, short: 'RGB' },
    { key: 'norm', label: 'frozen network', value: 'ImageNet weights', short: 'net' },
    { key: 'maps', label: 'first layer', value: '16 maps', short: 'map' },
    { key: 'vec', label: '576-d vector', value: `‖f‖ = ${fx(c.d.mobilenet.demo.feature_l2, 2)} (whole image)`, short: '576' },
  ],
  steps: (c): Step[] => {
    const m = c.d.mobilenet;
    return [
      { title: 'Preprocessing for ImageNet', stage: 'in', hl: 'selected', explain: `${m.preprocessing}. The gray value is copied into three colour channels.`,
        why: 'The network was pretrained on colour ImageNet photos and expects that input format.', out: <>pixel {c.px.v} → (R, G, B) = ({c.px.v}, {c.px.v}, {c.px.v})</>,
        interp: 'Classical: transfer learning re-uses features learned on other images.', body: <IO input="3×3 gray grid" output="3 × 224 × 224 normalised tensor" /> },
      { title: 'Frozen pretrained network', stage: 'norm', hl: 'none', explain: `MobileNetV3-small (${m.weights}) with ${m.load_info?.n_parameters?.toLocaleString?.()} parameters, all frozen.`,
        why: 'Only a small classifier on top is trained on NEU-DET, which needs few labelled images.', out: <>0 trainable parameters in the extractor</>,
        interp: 'Classical: the extractor is never updated on steel images.', body: <Note>Weights loaded from the local cache, checksum {String(m.load_info?.checkpoint_sha256 ?? '').slice(0, 12)}…</Note> },
      { title: 'First-layer feature maps', stage: 'maps', hl: 'none', explain: 'Real maps from the first convolution for the demo grid and for a real training image.',
        why: 'Shows what the pretrained filters respond to.', out: <>{m.demo.first_layer_maps.length} maps shown</>, interp: 'Classical: generic edge and contrast detectors.',
        body: <div className="grid gap-4 lg:grid-cols-2">{([['3×3 demo', m.demo], ['real training image', m.real]] as [string, any][]).map(([l, x]) => <div key={l}><div className="mb-2 text-xs text-slate-400">{l}</div><div className="flex flex-wrap gap-2">{x.first_layer_maps.map((f: any) => <ArrayImage key={f.channel} data={f.map} size={64} label={`ch ${f.channel}`} />)}</div></div>)}</div> },
      { title: '576-dimensional feature vector', stage: 'vec', hl: 'none', explain: 'Global average pooling of the last feature maps gives 576 numbers per image. In the hybrid models PCA reduces them to 8 or 12 before the quantum classifier.',
        why: 'These pretrained features separate NEU-DET classes far better than raw pixels.', out: <>‖f‖ = {fx(m.demo.feature_l2, 3)}; {fx(m.demo.feature_nonzero_fraction * 100, 1)}% non-zero</>,
        interp: "Classical: this representation, not the classifier on top, explains most of the hybrid models' accuracy.",
        body: <><ValueBars signed items={(m.demo.feature_first24 as number[]).slice(0, 16).map((v, i) => ({ label: `f${i + 1}`, value: v }))} />{NO_PRED}</> },
    ];
  },
};

export const CLASSICAL: Algo[] = [preprocessing, pca, logreg, svm, cnn, mnv3];
