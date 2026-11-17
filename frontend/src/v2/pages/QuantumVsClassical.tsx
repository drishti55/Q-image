/* eslint-disable @typescript-eslint/no-explicit-any */
// Quantum vs Classical: separate classical / quantum / hybrid views of Protocol V2 results (GET /api/v2/models)
// plus a side-by-side run of the illustrative 3×3 grid (GET /api/v2/playground). No metric is hardcoded here.
import { Fragment, useMemo } from 'react';
import type { ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Trophy } from 'lucide-react';
import { useV2, useV3 } from '../api';
import type { MS, Model, ModelsResponse } from '../api';
import { AccBar, Collapsible, FAMILY, FamilyChip, familyOfModel } from '../theme';
import { Card, ExecBadge, Gate, PageHeader, UNAVAILABLE, int, msDur, msPct } from '../ui';
import { Note, PixelGrid, fx } from '../playground/widgets';
import { ALGOS, demoPadding, makeCtx } from './Playground';
import { GIVEN } from '../playground/types';
import type { TraceItem } from '../playground/types';
import { ResultsCharts } from '../charts';

// ── derived helpers (pure; tested) ──
export function inputDims(featureSource: string): string {
  const pca = featureSource.match(/PCA (\d+)/);
  if (pca) return pca[1];
  const d = featureSource.match(/\((\d+)-d\)/);
  if (d) return d[1];
  const px = featureSource.match(/(\d+)×(\d+)/);
  if (px) return String(Number(px[1]) * Number(px[2]));
  return UNAVAILABLE;
}
export const bestBy = (ms: Model[]) => ms.reduce<Model | null>((b, m) => ((m.test_accuracy.mean ?? -1) > (b?.test_accuracy.mean ?? -1) ? m : b), null);
export const isMainQuantum = (m: Model) => m.is_quantum && !m.is_ablation && !m.is_legacy_relabelled && m.category !== 'Hybrid CNN + quantum models';
export const isMainClassical = (m: Model) => !m.is_quantum && !m.is_legacy_relabelled && m.category === 'Classical models' && !m.group.startsWith('E5-');

const seeds = (m: Model) => m.per_seed.map((s) => s.test?.accuracy ?? null);
const SeedChips = ({ m }: { m: Model }) => <span className="font-mono text-[11px] text-slate-400">{seeds(m).map((v, i) => <span key={i} className="mr-1.5">s{m.per_seed[i].seed}:{v === null ? UNAVAILABLE : (v * 100).toFixed(1)}</span>)}</span>;
const meanPct = (m?: MS | null) => (m?.mean == null ? UNAVAILABLE : `${(m.mean * 100).toFixed(1)}%`);

type Col = { h: string; cell: (m: Model) => ReactNode; cls?: string };
function ModelTable({ rows, cols, best, testid }: { rows: Model[]; cols: Col[]; best: Model | null; testid: string }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs tabular-nums" data-testid={testid}>
        <thead className="text-left text-[11px] text-slate-500"><tr>{cols.map((c) => <th key={c.h} className={`px-2 py-2 font-medium ${c.cls ?? ''}`}>{c.h}</th>)}</tr></thead>
        <tbody>{rows.map((m) => {
          const isBest = best?.group === m.group;
          return (
            <tr key={m.group} data-testid={`row-${m.group}`} className={`border-t border-slate-800/70 ${isBest ? 'bg-emerald-500/10' : ''}`}>
              {cols.map((c) => <td key={c.h} className={`px-2 py-2 align-top ${c.cls ?? ''}`}>{c.cell(m)}</td>)}
            </tr>
          );
        })}</tbody>
      </table>
    </div>
  );
}

const nameCol: Col = { h: 'Model', cell: (m) => <div className="min-w-[200px]"><Link to={`/models?model=${encodeURIComponent(m.group)}`} className="font-medium text-slate-100 hover:text-cyan-300">{m.display_name}</Link><div className="mt-0.5"><FamilyChip fam={familyOfModel(m)} /></div></div> };
const accCol: Col = { h: 'Test accuracy (mean ± sd, 3 seeds)', cell: (m) => <div className="min-w-[170px]"><AccBar value={m.test_accuracy.mean} color={FAMILY[familyOfModel(m)].color} /><div className="mt-0.5 text-[10px] text-slate-500">{msPct(m.test_accuracy)}</div></div> };
const prfCols: Col[] = [
  { h: 'Macro-F1', cell: (m) => meanPct(m.test_f1_macro) },
  { h: 'Precision', cell: (m) => meanPct(m.test_precision_macro) },
  { h: 'Recall', cell: (m) => meanPct(m.test_recall_macro) },
];
const timeCols: Col[] = [
  { h: 'Train time', cell: (m) => msDur(m.train_time_s) },
  { h: 'Inference / image', cell: (m) => (m.test_inference_ms_per_image.mean == null ? UNAVAILABLE : `${fx(m.test_inference_ms_per_image.mean, 3)} ms`) },
  { h: 'Per-seed accuracy (%)', cell: (m) => <SeedChips m={m} /> },
];

function BestBanner({ m, label }: { m: Model | null; label: string }) {
  if (!m) return null;
  return (
    <div className="mb-4 flex flex-wrap items-center gap-3 rounded-xl bg-emerald-500/10 px-4 py-3 ring-1 ring-emerald-500/30" data-testid={`best-${label}`}>
      <Trophy size={16} className="text-emerald-300" />
      <span className="text-sm text-emerald-100">Best {label}: <b>{m.display_name}</b> — {msPct(m.test_accuracy)} test accuracy</span>
    </div>
  );
}

function ClassicalView({ models }: { models: Model[] }) {
  const rows = models.filter(isMainClassical).sort((a, b) => (b.test_accuracy.mean ?? 0) - (a.test_accuracy.mean ?? 0));
  const best = bestBy(rows);
  return (
    <Card title="A · Classical models" subtitle="Every model here runs on ordinary hardware. Features: raw pixels compressed with PCA, a small CNN trained from scratch, or a frozen ImageNet MobileNetV3. Best model highlighted in green.">
      <BestBanner m={best} label="classical model" />
      <ModelTable testid="table-classical" best={best} rows={rows} cols={[nameCol,
        { h: 'Feature representation', cell: (m) => <span className="text-slate-300">{m.feature_source}</span> },
        { h: 'Input dims', cell: (m) => inputDims(m.feature_source) },
        accCol, ...prfCols, ...timeCols]} />
    </Card>
  );
}

function QuantumView({ models }: { models: Model[] }) {
  const rows = models.filter(isMainQuantum).sort((a, b) => (b.test_accuracy.mean ?? 0) - (a.test_accuracy.mean ?? 0));
  const best = bestBy(rows);
  const ablations = models.filter((m) => m.is_ablation);
  const cols: Col[] = [nameCol,
    { h: 'Encoding / feature map', cell: (m) => <span className="text-slate-300">{m.encoding}</span> },
    { h: 'Qubits', cell: (m) => m.n_qubits ?? UNAVAILABLE },
    accCol, { h: 'Macro-F1', cell: (m) => meanPct(m.test_f1_macro) },
    { h: 'Depth (logical / compiled)', cell: (m) => (m.circuit ? `${int(m.circuit.depth_logical)} / ${int(m.circuit.depth_compiled)}` : UNAVAILABLE) },
    { h: 'Gates (logical / compiled)', cell: (m) => (m.circuit ? `${int(m.circuit.gates_logical)} / ${int(m.circuit.gates_compiled)}` : UNAVAILABLE) },
    { h: 'Shots', cell: (m) => <div className="space-y-1"><div>{m.shots ? m.shots.toLocaleString() : 'exact'}</div><ExecBadge execution={m.execution} /></div> },
    ...timeCols];
  const groups: [string, (m: Model) => boolean, string][] = [
    ['Quantum kernel classifiers (PCA features)', (m) => m.category === 'Quantum kernel models', 'qkc'],
    ['FRQI / NEQR image-encoding kernels', (m) => m.category === 'FRQI / NEQR encoding kernels', 'encoding'],
    ['Variational quantum classifiers', (m) => m.category === 'Variational quantum classifiers', 'vqc'],
  ];
  return (
    <Card title="B · Quantum models (noiseless classical simulation)" subtitle="Quantum kernels, FRQI / NEQR image-encoding kernels and variational classifiers. All circuits were simulated on a CPU — no quantum hardware. Historical V0 methods and frozen-circuit ablations are excluded here.">
      <BestBanner m={best} label="quantum model" />
      <div className="space-y-4">
        {groups.map(([title, f, id], i) => {
          const r = rows.filter(f);
          return (
            <Collapsible key={id} title={`${title} (${r.length})`} hint={`best: ${bestBy(r)?.display_name ?? UNAVAILABLE} · ${msPct(bestBy(r)?.test_accuracy)}`} defaultOpen={i === 0}>
              <ModelTable testid={`table-quantum-${id}`} best={best} rows={r} cols={cols} />
            </Collapsible>
          );
        })}
        {ablations.length > 0 && <Collapsible title={`Controls: VQC with a frozen random circuit (${ablations.length})`} hint="shows how much training the circuit matters">
          <ModelTable testid="table-ablation" best={null} rows={ablations} cols={[nameCol, { h: 'Qubits', cell: (m) => m.n_qubits ?? UNAVAILABLE }, accCol]} />
        </Collapsible>}
      </div>
    </Card>
  );
}

export function hybridAnalysis(models: Model[]) {
  const g = (id: string) => models.find((m) => m.group === id) ?? null;
  return [4, 6, 8].map((k) => {
    const classical = [g(`E5-mnv3pca${k}-logreg`), g(`E5-mnv3pca${k}-rbfsvm`)].filter(Boolean) as Model[];
    const quantum = ['product_ry', 'zz_linear', 'zz_full'].map((f) => g(`E5-mnv3pca${k}-qkc-${f}`)).concat([g(`E5-mnv3pca${k}-vqc`)]).filter(Boolean) as Model[];
    const bc = bestBy(classical), bq = bestBy(quantum);
    const pixelQ = bestBy(['product_ry', 'zz_linear', 'zz_full'].map((f) => g(`E3-pca${k}-qkc-${f}`)).filter(Boolean) as Model[]);
    const diff = bc?.test_accuracy.mean != null && bq?.test_accuracy.mean != null ? bq.test_accuracy.mean - bc.test_accuracy.mean : null;
    const sd = Math.max(bc?.test_accuracy.std ?? 0, bq?.test_accuracy.std ?? 0);
    const featureGain = bq?.test_accuracy.mean != null && pixelQ?.test_accuracy.mean != null ? bq.test_accuracy.mean - pixelQ.test_accuracy.mean : null;
    return { k, classical, quantum, bestClassical: bc, bestQuantum: bq, pixelQuantum: pixelQ, classifierDiff: diff, maxSd: sd, featureGain };
  });
}

function HybridView({ models }: { models: Model[] }) {
  const rows = hybridAnalysis(models);
  const pp = (v: number | null) => (v === null ? UNAVAILABLE : `${v >= 0 ? '+' : ''}${(v * 100).toFixed(1)} pp`);
  return (
    <Card title="C · Hybrid models: CNN features + quantum classifier" subtitle="A frozen MobileNetV3 turns each image into 576 numbers, PCA keeps k of them, and a quantum kernel or VQC classifies them. The classical controls use exactly the same k features.">
      <div className="space-y-5">
        {rows.map((r) => (
          <div key={r.k} className="rounded-xl bg-slate-950/40 p-4 ring-1 ring-slate-800" data-testid={`hybrid-k${r.k}`}>
            <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="text-sm font-semibold text-white">MobileNetV3 → PCA {r.k} features ({r.k} qubits for the quantum classifiers)</h3>
              <div className="flex flex-wrap gap-2 text-[11px]">
                <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-emerald-200 ring-1 ring-emerald-500/30">feature effect (CNN vs pixel features, best QKC): {pp(r.featureGain)}</span>
                <span className="rounded-full bg-cyan-500/10 px-2 py-0.5 text-cyan-200 ring-1 ring-cyan-500/30">classifier effect (best quantum − best classical): {pp(r.classifierDiff)}</span>
              </div>
            </div>
            <ModelTable testid={`table-hybrid-k${r.k}`} best={bestBy([...r.classical, ...r.quantum])}
              rows={[...r.classical, ...r.quantum, ...(r.pixelQuantum ? [r.pixelQuantum] : [])]}
              cols={[nameCol, { h: 'Classifier', cell: (m) => (m.is_quantum ? <span className="text-cyan-300">quantum (simulated)</span> : <span className="text-amber-300">classical</span>) },
                { h: 'Features', cell: (m) => m.feature_source }, accCol, { h: 'Macro-F1', cell: (m) => meanPct(m.test_f1_macro) }, { h: 'Per-seed accuracy (%)', cell: (m) => <SeedChips m={m} /> }]} />
            <p className="mt-2 text-[11px] text-slate-400">
              {r.classifierDiff !== null && Math.abs(r.classifierDiff) <= 2 * r.maxSd
                ? `The quantum−classical gap (${pp(r.classifierDiff)}) is within two seed standard deviations (±${(2 * r.maxSd * 100).toFixed(1)} pp): no meaningful difference.`
                : r.classifierDiff !== null ? `The gap (${pp(r.classifierDiff)}) exceeds two seed standard deviations (±${(2 * r.maxSd * 100).toFixed(1)} pp).` : ''}
            </p>
          </div>
        ))}
        <Note tone="cyan"><b>Why this is not a quantum advantage.</b> The big jump in accuracy comes from the CNN features (the "feature effect"), which are computed classically. Given the same features, classical classifiers perform about as well as the quantum ones (the "classifier effect"), and the quantum classifiers were simulated exactly on a classical computer.</Note>
      </div>
    </Card>
  );
}

// ── side-by-side processing of the 3×3 demo (V3 educational data; no classifier outputs) ──
type Summary = { name: string; group: string; pipeline: string[]; representation: string; math: string; similarity: string; cost: string[]; output: string };
export function summarizeDemo(id: string, d: any): Summary {
  const nsv = (d.svm.n_support as number[]).reduce((x, y) => x + y, 0);
  switch (id) {
    case 'svm': return { name: 'Pixels → PCA 8 → RBF-SVM', group: 'E6-pca8-rbfsvm', pipeline: ['resize 3×3 → 64×64 (4,096 pixels)', 'standardise, PCA → 8 numbers', `RBF similarity to ${nsv} support vectors`, 'one-vs-one votes'], representation: '8 real numbers', math: 'dot products, exponentials', similarity: `exp(−γ‖x−y‖²), γ = ${d.svm.gamma}`, cost: [`${nsv} kernel evaluations per image`, 'O(n_SV · d)'], output: 'one class from 6 (vote)' };
    case 'logreg': return { name: 'Pixels → PCA 8 → logistic regression', group: 'E6-pca8-logreg', pipeline: ['resize 3×3 → 64×64', 'standardise, PCA → 8 numbers', '6 weighted sums', 'softmax → probabilities'], representation: '8 real numbers', math: 'matrix-vector product, softmax', similarity: 'none (linear scores)', cost: [`${d.logreg.W.length * d.logreg.W[0].length + d.logreg.b.length} trained parameters`, 'O(d · classes)'], output: '6 probabilities' };
    case 'cnn': return { name: 'Small CNN', group: 'E7-smallcnn', pipeline: ['resize 3×3 → 128×128', '4 conv blocks (conv, ReLU, pool)', `global pool → ${d.small_cnn.demo.embedding_dim} features`, 'linear layer + softmax'], representation: `${d.small_cnn.demo.embedding_dim}-d learned feature vector`, math: 'convolutions, max, averages', similarity: 'none (learned filters)', cost: ['16,384 input pixels', '≈ millions of multiply-adds'], output: '6 probabilities' };
    case 'mnv3': return { name: 'Frozen MobileNetV3 + logistic regression', group: 'E7-mnv3-logreg', pipeline: ['RGB copy, resize 256, crop 224', 'frozen ImageNet MobileNetV3', `${d.mobilenet.demo.feature_dim}-d feature vector`, 'logistic regression'], representation: `${d.mobilenet.demo.feature_dim}-d pretrained features`, math: 'convolutions + linear head', similarity: 'none (linear scores)', cost: [`${d.mobilenet.load_info?.n_parameters?.toLocaleString?.() ?? UNAVAILABLE} frozen parameters`], output: '6 probabilities' };
    case 'frqi': return { name: 'FRQI encoding (4×4 embedding)', group: 'E1-frqi4-qkc', pipeline: ['embed 3×3 in 4×4 (zero padding)', 'θ = (π/2)·pixel/255', 'H on 4 position qubits', 'multi-controlled RY on the colour qubit', 'measure / reconstruct'], representation: `${d.frqi.n_qubits} qubits (2^${d.frqi.n_qubits} = ${2 ** d.frqi.n_qubits} amplitudes)`, math: 'unitary rotations (cos θ, sin θ amplitudes)', similarity: 'state overlap |⟨ψ(x)|ψ(y)⟩|² in the FRQI kernel model', cost: [`${d.frqi.logical_gates} gates, depth ${d.frqi.depth}`, `${d.frqi.n_qubits} qubits`], output: 'a quantum state (encoding, not a classifier)' };
    case 'neqr': { const p = d.neqr.precisions['4']; return { name: 'NEQR encoding (4-bit, 4×4 embedding)', group: 'E2-neqr4-b4-qkc', pipeline: ['embed 3×3 in 4×4', 'quantise to 4 bits', 'H on 4 position qubits', 'MCX for each 1-bit', 'measure / decode'], representation: `${p.n_qubits} qubits (2^${p.n_qubits} = ${2 ** p.n_qubits} amplitudes)`, math: 'bit flips (basis states)', similarity: 'state overlap (counts exactly matching intensities)', cost: [`${p.logical_gates} logical gates, depth ${p.depth}`, `${p.n_qubits} qubits`], output: 'a quantum state (encoding, not a classifier)' }; }
    case 'qkc': { const m = d.qkc.maps.zz_full; return { name: 'Quantum kernel (ZZ-full, 4 qubits)', group: 'E3-pca4-qkc-zz_full', pipeline: ['resize 3×3 → 64×64', 'PCA 4 → angles in [0, π]', 'ZZ-full feature-map circuit', 'overlap with training states', 'classical SVM on the kernel'], representation: '4 qubits (16 amplitudes)', math: 'unitary gates + overlap; SVM is classical', similarity: '|⟨φ(x)|φ(y)⟩|²', cost: [`${m.n_gates} gates, depth ${m.depth}`, 'one overlap circuit per training image'], output: 'one class from 6 (classical SVM vote)' }; }
    case 'vqc': return { name: 'Variational classifier (4 qubits, 2 layers)', group: 'E4-pca4-vqc', pipeline: ['resize 3×3 → 64×64', 'PCA 4 → angles', 'RY encoding + 2 trainable layers', `measure ${d.vqc.readout.length} expectations`, 'scale + softmax'], representation: '4 qubits (16 amplitudes)', math: 'rotations, CNOTs, expectation values', similarity: 'none (trained circuit)', cost: [`${d.vqc.circuit_trained.length} gates`, `${d.vqc.theta_trained.length} trainable angles + ${d.vqc.w.length * 2} head parameters`], output: '6 probabilities' };
    default: return { name: id, group: '', pipeline: [], representation: UNAVAILABLE, math: UNAVAILABLE, similarity: UNAVAILABLE, cost: [], output: UNAVAILABLE };
  }
}

const CL_OPTS: [string, string][] = [['svm', 'RBF-SVM'], ['logreg', 'Logistic regression'], ['cnn', 'Small CNN'], ['mnv3', 'MobileNetV3']];
const Q_OPTS: [string, string][] = [['qkc', 'Quantum kernel'], ['vqc', 'VQC'], ['frqi', 'FRQI'], ['neqr', 'NEQR']];

function SidePanel({ s, models, tone, trace }: { s: Summary; models: Model[]; tone: 'amber' | 'cyan'; trace: TraceItem[] }) {
  const real = models.find((m) => m.group === s.group);
  const c = tone === 'amber' ? 'text-amber-300' : 'text-cyan-300';
  return (
    <div className="space-y-3 rounded-xl bg-slate-950/40 p-4 ring-1 ring-slate-800" data-testid={`side-${tone === 'amber' ? 'classical' : 'quantum'}`}>
      <div className={`text-sm font-semibold ${c}`}>{s.name}</div>
      <ol className="space-y-1 text-xs text-slate-300">{s.pipeline.map((p, i) => <li key={i} className="flex gap-2"><span className={`w-4 shrink-0 ${c}`}>{i + 1}.</span>{p}</li>)}</ol>
      <div className="rounded-lg bg-slate-900/60 p-2 ring-1 ring-slate-800">
        <div className="mb-1 text-[10px] uppercase tracking-wider text-slate-500">Selected pixel, stage by stage</div>
        <ol className="space-y-0.5 text-xs">{trace.map((t) => <li key={t.key} className="flex gap-2"><span className="w-28 shrink-0 text-slate-500">{t.label}</span><span className="font-mono text-slate-100">{t.value}</span></li>)}</ol>
      </div>
      <dl className="grid grid-cols-[120px_minmax(0,1fr)] gap-x-2 gap-y-1 text-xs">
        <dt className="text-slate-500">Representation</dt><dd className="text-slate-200">{s.representation}</dd>
        <dt className="text-slate-500">Maths</dt><dd className="text-slate-200">{s.math}</dd>
        <dt className="text-slate-500">Similarity</dt><dd className="text-slate-200">{s.similarity}</dd>
        <dt className="text-slate-500">Cost</dt><dd className="text-slate-200">{s.cost.filter(Boolean).join(' · ')}</dd>
        <dt className="text-slate-500">Output</dt><dd className="text-slate-200">{s.output}</dd>
      </dl>
      <div className="rounded-lg bg-slate-900/60 p-2 text-[11px] text-slate-400 ring-1 ring-slate-800">
        Real NEU-DET result of the matching Protocol V2 model ({real?.display_name ?? s.group}): <b className="text-slate-200">{real ? msPct(real.test_accuracy) : UNAVAILABLE}</b> test accuracy
      </div>
    </div>
  );
}

const DIMENSIONS: [string, string, string][] = [
  ['Input representation', 'Vector of real numbers (pixels, PCA scores or CNN features)', 'Quantum state of n qubits: 2ⁿ complex amplitudes (angles, FRQI or NEQR encoding)'],
  ['Processing', 'Arithmetic on the vector (dot products, convolutions)', 'Unitary gates: rotations and entangling CNOT / ZZ interactions'],
  ['Similarity', 'RBF kernel exp(−γ‖x−y‖²) or none', 'State overlap |⟨φ(x)|φ(y)⟩|² (quantum kernels)'],
  ['Training', 'Gradient descent / SVM optimisation on a CPU', 'Kernel: classical SVM. VQC: parameter-shift gradients + Adam'],
  ['Measurement', 'Not needed — values are read directly', 'Probabilistic: exact statevector here, or finite shots (100–10,000) in the shot studies'],
  ['Complexity', 'Grows with the number of features and training images', 'State size doubles with every qubit; simulating it on a CPU is exponential in qubits'],
  ['Hardware used here', 'CPU', 'CPU (noiseless statevector simulation) — no quantum hardware'],
];

function SideBySide({ models }: { models: Model[] }) {
  const pg = useV3<any>('/playground');
  const [sp, setSp] = useSearchParams();
  const a = sp.get('c') ?? 'svm', b = sp.get('q') ?? 'frqi';
  const sel = Math.min(3, Math.max(0, Number(sp.get('px') ?? 0) || 0));
  const set = (k: string, v: string) => { const n = new URLSearchParams(window.location.search); n.set(k, v); setSp(n, { replace: true }); };
  const pick = (k: string, cur: string, opts: [string, string][], tone: string) => (
    <div className="flex flex-wrap gap-1" role="group" aria-label={k === 'c' ? 'classical algorithm' : 'quantum algorithm'}>
      {opts.map(([v, l]) => <button key={v} data-testid={`pick-${k}-${v}`} aria-pressed={cur === v} onClick={() => set(k, v)} className={`rounded-md px-2.5 py-1 text-xs ring-1 ${cur === v ? `${tone} ring-current` : 'text-slate-300 ring-slate-700 hover:bg-slate-800'}`}>{l}</button>)}
    </div>
  );
  const traceOf = (id: string, d: any) => {
    const algo = ALGOS.find((x) => x.id === id)!;
    const ctx = makeCtx(d, algo, new URLSearchParams({ px: String(sel) }));
    return algo.trace(ctx);
  };
  return (
    <Card title="D · Side by side on the same 3×3 image" subtitle="Pick one classical and one quantum algorithm and a pixel. Both panels show how that pixel is transformed at every stage (real values) and what fundamentally differs. No classifier output is shown for the artificial grid; the real NEU-DET accuracy of the matching model is shown instead.">
      <Gate state={pg}>{(d: any) => (
        <div className="space-y-5">
          <div className="flex flex-wrap items-start gap-6">
            <PixelGrid values={d.grid} padding={demoPadding} size={48} label="Illustrative input (click a pixel)" selected={GIVEN[sel]}
              onSelect={(r, cc) => { const i = GIVEN.findIndex((g) => g.r === r && g.c === cc); if (i >= 0) set('px', String(i)); }} />
            <div className="space-y-3"><div><div className="mb-1 text-[11px] uppercase tracking-wider text-amber-300">Classical</div>{pick('c', a, CL_OPTS, 'bg-amber-500/15 text-amber-200')}</div>
              <div><div className="mb-1 text-[11px] uppercase tracking-wider text-cyan-300">Quantum</div>{pick('q', b, Q_OPTS, 'bg-cyan-500/15 text-cyan-200')}</div></div>
          </div>
          <div className="grid gap-4 lg:grid-cols-2"><SidePanel s={summarizeDemo(a, d)} models={models} tone="amber" trace={traceOf(a, d)} /><SidePanel s={summarizeDemo(b, d)} models={models} tone="cyan" trace={traceOf(b, d)} /></div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs" data-testid="dimension-table">
              <thead className="text-left text-[11px] text-slate-500"><tr><th className="px-2 py-2">Dimension</th><th className="px-2 py-2 text-amber-300">Classical</th><th className="px-2 py-2 text-cyan-300">Quantum (this project)</th></tr></thead>
              <tbody>{DIMENSIONS.map(([k, c, q]) => <tr key={k} className="border-t border-slate-800/70"><td className="px-2 py-2 font-medium text-slate-200">{k}</td><td className="px-2 py-2 text-slate-300">{c}</td><td className="px-2 py-2 text-slate-300">{q}</td></tr>)}</tbody>
            </table>
          </div>
        </div>
      )}</Gate>
    </Card>
  );
}

const TABS: [string, string][] = [['charts', 'Charts'], ['classical', 'Classical'], ['quantum', 'Quantum'], ['hybrid', 'Hybrid'], ['side', 'Side by side']];

export default function QuantumVsClassical() {
  const st = useV2<ModelsResponse>('/models');
  const [sp, setSp] = useSearchParams();
  const tab = TABS.some(([t]) => t === sp.get('view')) ? sp.get('view')! : 'charts';
  const models = useMemo(() => st.data?.models ?? [], [st.data]);
  const head = useMemo(() => {
    const c = bestBy(models.filter(isMainClassical)), q = bestBy(models.filter(isMainQuantum)), h = bestBy(models.filter((m) => m.category === 'Hybrid CNN + quantum models'));
    return [['Best classical', c, 'cnn'], ['Best quantum', q, 'qkc'], ['Best hybrid', h, 'hybrid']] as const;
  }, [models]);
  return (
    <div>
      <PageHeader title="Quantum vs Classical" subtitle="Protocol V2 results on the 360 locked NEU-DET test images, mean over seeds 0, 1, 2. Classical, quantum and hybrid models are shown separately so they are never confused." />
      <Gate state={st}>{() => (
        <Fragment>
          <div className="mb-5 grid gap-3 sm:grid-cols-3">{head.map(([l, m, f]) => (
            <div key={l} className="rounded-xl border border-slate-800 bg-slate-950/50 px-4 py-3" data-testid={`headline-${f}`}>
              <div className="text-[11px] uppercase tracking-wider text-slate-500">{l}</div>
              <div className="mt-1 text-2xl font-semibold tabular-nums" style={{ color: FAMILY[f].color }}>{meanPct(m?.test_accuracy)}</div>
              <div className="truncate text-[11px] text-slate-400">{m?.display_name ?? UNAVAILABLE}</div>
            </div>))}
          </div>
          <div className="mb-5 flex flex-wrap gap-1 rounded-xl bg-slate-950/60 p-1 ring-1 ring-slate-800" role="tablist">
            {TABS.map(([t, l]) => <button key={t} role="tab" aria-selected={tab === t} data-testid={`tab-${t}`} onClick={() => { const n = new URLSearchParams(window.location.search); n.set('view', t); setSp(n, { replace: true }); }}
              className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium transition ${tab === t ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-slate-200'}`}>{l}</button>)}
          </div>
          {tab === 'charts' && <ResultsCharts models={models} />}
          {tab === 'classical' && <ClassicalView models={models} />}
          {tab === 'quantum' && <QuantumView models={models} />}
          {tab === 'hybrid' && <HybridView models={models} />}
          {tab === 'side' && <SideBySide models={models} />}
        </Fragment>
      )}</Gate>
    </div>
  );
}
