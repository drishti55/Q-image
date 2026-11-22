// Clickable hybrid pipeline on a real locked-test image: Original → Preprocessing → CNN → Quantum encoding → Classification →
// Result. Data: /api/v4/hybrid-pipeline (live frozen MobileNetV3, seed-0 PCA-8, product-RY kernel vs 1,080 training images,
// and the SAVED locked-test predictions of E5-mnv3pca8-qkc-product_ry). Nothing illustrative.
import { useMemo, useState } from 'react';
import { ArrowRight, CheckCircle2, Pause, Play, Shuffle, XCircle } from 'lucide-react';
import { useV4 } from '../api';
import { Gate } from '../ui';
import { FadeIn } from '../theme';
import { Lv } from '../level';
import { ExplainThis } from './ExplainThis';
import { useStepper } from '../playground/widgets';

type Ch = { channel: number; mean_activation: number; map: string };
type Hyb = {
  image: string; y_true: string; original: string; model_input: string; preprocess: { from: number[]; to: number[]; steps: string };
  stages: { layer: number; label: string; shape: number[]; channels: Ch[] }[]; vector: number[];
  pca: { k: number; explained_variance_ratio: number[]; angles_rad: number[]; bandwidth: number; circuit_angles_rad: number[] };
  kernel: { formula: string; n_train: number; nearest: { class: string; similarity: number; thumb: string }[]; class_mean: Record<string, number> };
  model: { group: string; name: string; test_accuracy: { mean: number; std: number }; n_qubits: number };
  saved_predictions: string[]; correct_seeds: number;
};
const CLASSES = ['crazing', 'inclusion', 'patches', 'pitted_surface', 'rolled-in_scale', 'scratches'];
const NAMES: Record<string, string> = { crazing: 'Crazing', inclusion: 'Inclusion', patches: 'Patches', pitted_surface: 'Pitted surface', 'rolled-in_scale': 'Rolled-in scale', scratches: 'Scratches' };
const BLUE = '#3987e5', TEAL = '#5eead4';
const deg = (r: number) => `${Math.round((r * 180) / Math.PI)}°`;

function Dial({ a, size = 46 }: { a: number; size?: number }) {
  const r = size * 0.38, c = size / 2;
  return (
    <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size} aria-hidden>
      <circle cx={c} cy={c} r={r} fill="#0f172a" stroke="#334155" />
      <line x1={c} y1={c} x2={c + r * Math.sin(a)} y2={c - r * Math.cos(a)} stroke={TEAL} strokeWidth={3} strokeLinecap="round" />
    </svg>
  );
}

function VecGrid({ v, cell = 6 }: { v: number[]; cell?: number }) {
  const n = 24, mx = Math.max(...v, 1e-9);
  return (
    <svg viewBox={`0 0 ${n * cell} ${n * cell}`} width={n * cell} role="img" aria-label="576 CNN features">
      {v.map((x, i) => <rect key={i} x={(i % n) * cell} y={Math.floor(i / n) * cell} width={cell - 1} height={cell - 1} rx={1} fill={x > 0 ? BLUE : '#1e293b'} fillOpacity={x > 0 ? 0.25 + 0.75 * Math.sqrt(x / mx) : 1} />)}
    </svg>
  );
}

const Row = ({ k, children }: { k: string; children: React.ReactNode }) => (
  <div className="grid grid-cols-[5.5rem_minmax(0,1fr)] items-start gap-3 text-[13px]"><span className="pt-0.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">{k}</span><div className="text-slate-200">{children}</div></div>
);

function stagesOf(d: Hyb) {
  const pred = d.saved_predictions[0], ok = pred === d.y_true;
  const cm = Object.entries(d.kernel.class_mean), mx = Math.max(...cm.map(([, v]) => v)), mn = Math.min(...cm.map(([, v]) => v));
  return [
    { key: 'orig', title: 'Original image', preview: <img src={d.original} alt="" className="h-14 w-14 rounded ring-1 ring-slate-700" />,
      body: (<div className="flex flex-wrap items-start gap-6"><img src={d.original} width={200} height={200} alt="original" className="rounded-md ring-1 ring-slate-700" />
        <div className="space-y-2"><Row k="Input">locked-test photo · true class <b>{NAMES[d.y_true]}</b></Row><Row k="Output">{d.preprocess.from.join('×')} grey pixels</Row>
          <Row k="Purpose">The model never saw this image while training.</Row></div></div>) },
    { key: 'pre', title: 'Preprocessing', preview: <img src={d.model_input} alt="" className="h-14 w-14 rounded ring-1 ring-slate-700" />,
      body: (<div className="flex flex-wrap items-center gap-4"><img src={d.original} width={130} height={130} alt="" className="rounded-md ring-1 ring-slate-700" /><ArrowRight className="text-slate-600" />
        <img src={d.model_input} width={130} height={130} alt="network input" className="rounded-md ring-1 ring-slate-700" />
        <div className="space-y-2"><Row k="Operation"><div className="flex flex-wrap gap-1">{d.preprocess.steps.split(' → ').map((s) => <span key={s} className="rounded bg-slate-800 px-1.5 py-0.5 text-xs">{s}</span>)}</div></Row>
          <Row k="Output">{d.preprocess.to.join('×')} tensor</Row><Row k="Purpose">Same format the network was trained on.</Row></div></div>) },
    { key: 'cnn', title: 'CNN features', preview: <img src={d.stages[0].channels[0].map} alt="" className="h-14 w-14 rounded ring-1 ring-slate-700 [image-rendering:pixelated]" />,
      body: (<div className="space-y-4"><div className="flex flex-wrap items-end gap-4">{d.stages.map((s, si) => (
          <FadeIn key={s.layer} delay={si * 120}><div><div className="mb-1 text-[11px] text-slate-400">{s.label} · {s.shape[0]}×{s.shape[1]}²</div>
            <div className="grid grid-cols-2 gap-1">{s.channels.map((c) => <img key={c.channel} src={c.map} alt="" className="h-14 w-14 rounded-sm ring-1 ring-slate-800 [image-rendering:pixelated]" />)}</div></div></FadeIn>))}
          <ArrowRight className="mb-10 text-slate-600" /><div><div className="mb-1 text-[11px] text-slate-400">576 numbers</div><VecGrid v={d.vector} /></div></div>
        <div className="flex items-center gap-2"><Row k="Purpose"><Lv beginner="Filters find edges → textures → shapes; each final map becomes one number." technical="Frozen MobileNetV3-small features[0…12]; global average pool of the 576×7×7 output." /></Row><ExplainThis id="cnn" /></div></div>) },
    { key: 'q', title: 'Quantum encoding', preview: <div className="grid grid-cols-4 gap-0.5">{d.pca.circuit_angles_rad.map((a, i) => <Dial key={i} a={a} size={16} />)}</div>,
      body: (<div className="space-y-4"><div className="flex flex-wrap items-center gap-5">
          <div className="text-center"><div className="text-2xl font-semibold text-white">576</div><div className="text-[11px] text-slate-500">numbers</div></div><ArrowRight className="text-slate-600" />
          <div className="text-center"><div className="text-2xl font-semibold text-teal-300">{d.pca.k}</div><div className="text-[11px] text-slate-500">PCA angles</div></div><ArrowRight className="text-slate-600" />
          <svg viewBox={`0 0 220 ${d.pca.k * 22 + 6}`} width={220} role="img" aria-label="product-RY circuit with this image's angles">
            {d.pca.circuit_angles_rad.map((a, i) => (<g key={i}><text x={0} y={i * 22 + 18} fontSize={9} fill="#94a3b8">q{i}</text><line x1={18} x2={214} y1={i * 22 + 14} y2={i * 22 + 14} stroke="#475569" />
              <rect x={70} y={i * 22 + 5} width={70} height={18} rx={3} fill="#0f172a" stroke={TEAL} /><text x={105} y={i * 22 + 17.5} textAnchor="middle" fontSize={9} fill={TEAL}>RY {deg(a)}</text></g>))}
          </svg>
          <div className="grid grid-cols-4 gap-1">{d.pca.circuit_angles_rad.map((a, i) => <Dial key={i} a={a} />)}</div></div>
        <div className="flex flex-wrap items-center gap-2"><Row k="Purpose"><Lv beginner={`One qubit per number: ${d.pca.k} qubits, each turned by its angle.`} technical={`Seed-0 StandardScaler → PCA(8) → MinMax[0, π], × bandwidth ${d.pca.bandwidth}; U(x) = ⊗ RY(xᵢ). Keeps ${(100 * d.pca.explained_variance_ratio.reduce((s, v) => s + v, 0)).toFixed(0)}% of variance.`} /></Row><ExplainThis id="pca" /><ExplainThis id="product-ry" /></div></div>) },
    { key: 'cls', title: 'Classification', preview: <div className="flex h-14 items-end gap-0.5">{CLASSES.map((c) => <div key={c} className="w-2 rounded-t" style={{ height: `${10 + 44 * ((d.kernel.class_mean[c] - mn) / (mx - mn || 1))}px`, background: c === pred ? TEAL : '#475569' }} />)}</div>,
      body: (<div className="flex flex-wrap items-start gap-8">
          <div className="w-72 space-y-1.5"><div className="text-[11px] text-slate-400">mean quantum similarity to each class ({d.kernel.n_train} training images)</div>
            {cm.map(([c, v]) => (<div key={c} className="grid grid-cols-[6.5rem_minmax(0,1fr)_3rem] items-center gap-2 text-xs"><span className={c === pred ? 'font-semibold text-white' : 'text-slate-400'}>{NAMES[c]}</span>
              <div className="h-2.5 rounded-full bg-slate-800"><div className="h-2.5 rounded-full transition-all duration-700" style={{ width: `${100 * ((v - mn) / (mx - mn || 1))}%`, background: c === pred ? TEAL : '#64748b' }} /></div><span className="tabular-nums text-slate-400">{v.toFixed(3)}</span></div>))}
            <div className="pt-1 text-[11px] text-slate-500">Averages only — the SVM weighs individual training images (right).</div></div>
          <div><div className="mb-1 text-[11px] text-slate-400">most similar training images</div><div className="flex gap-2">{d.kernel.nearest.map((n, i) => (
            <figure key={i} className="text-center"><img src={n.thumb} width={56} height={56} alt="" className="rounded ring-1 ring-slate-700" /><figcaption className="text-[10px] text-slate-400">{NAMES[n.class]}<br /><span className="tabular-nums">{n.similarity.toFixed(3)}</span></figcaption></figure>))}</div></div>
          <div className="flex items-center gap-2"><Row k="Purpose"><Lv beginner="An SVM compares the image with every training image using these quantum similarities." technical={`${d.kernel.formula}; SVC(kernel='precomputed') on the Gram matrix.`} /></Row><ExplainThis id="kernel" /></div></div>) },
    { key: 'res', title: 'Result', preview: <div className={`flex h-14 items-center gap-1 text-sm font-semibold ${ok ? 'text-emerald-300' : 'text-rose-300'}`}>{ok ? <CheckCircle2 size={18} /> : <XCircle size={18} />}{NAMES[pred]}</div>,
      body: (<div className="flex flex-wrap items-center gap-8">
          <div className="text-center"><div className="text-[11px] uppercase tracking-wider text-slate-500">true</div><div className="text-2xl font-semibold text-white">{NAMES[d.y_true]}</div></div>
          <div className="flex gap-2">{d.saved_predictions.map((p, i) => (
            <div key={i} className={`rounded-xl px-4 py-3 text-center ring-1 ${p === d.y_true ? 'bg-emerald-500/10 ring-emerald-500/40' : 'bg-rose-500/10 ring-rose-500/40'}`}>
              <div className="text-[10px] uppercase tracking-wider text-slate-400">seed {i}</div><div className="text-sm font-semibold text-white">{NAMES[p]}</div></div>))}</div>
          <div className="text-sm text-slate-300"><b className="text-white">{d.correct_seeds}/3</b> seeds correct · model {d.model.name} · <span className="tabular-nums">{(100 * d.model.test_accuracy.mean).toFixed(1)}%</span> on all 360 test images
            <div className="text-[11px] text-slate-500">saved predictions from the locked-test run</div></div></div>) },
  ];
}

export default function HybridPipeline() {
  const list = useV4<{ images: { image: string; class: string }[] }>('/images');
  const [cls, setCls] = useState('scratches');
  const [k, setK] = useState(0);
  const pool = useMemo(() => (list.data?.images ?? []).filter((x) => x.class === cls), [list.data, cls]);
  const image = pool.length ? pool[k % pool.length].image : null;
  const st = useV4<Hyb>(image ? `/hybrid-pipeline?image=${encodeURIComponent(image)}` : null);
  const [open, setOpen] = useState(0);
  const { playing, setPlaying } = useStepper(6, open, setOpen, 2600);
  return (
    <div className="space-y-4" data-testid="hybrid-pipeline">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {CLASSES.map((c) => <button key={c} type="button" onClick={() => { setCls(c); setK(0); setOpen(0); }} className={`rounded-md px-2.5 py-1 ring-1 ${cls === c ? 'bg-teal-500/15 text-teal-100 ring-teal-500/40' : 'text-slate-400 ring-slate-700 hover:text-slate-200'}`}>{NAMES[c]}</button>)}
        <button type="button" onClick={() => { setK(k + 1); setOpen(0); }} className="inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-slate-300 ring-1 ring-slate-700"><Shuffle size={12} /> another test image</button>
        <button type="button" onClick={() => { if (open >= 5) setOpen(0); setPlaying(!playing); }} className="ml-auto inline-flex items-center gap-1 rounded-md bg-teal-500/15 px-3 py-1 text-teal-100 ring-1 ring-teal-500/40">{playing ? <><Pause size={12} /> pause</> : <><Play size={12} /> play</>}</button>
      </div>
      <Gate state={st}>{(d) => {
        const S = stagesOf(d);
        return (<>
          <ol className="flex flex-wrap items-stretch gap-1.5" aria-label="pipeline stages">
            {S.map((s, i) => (
              <li key={s.key} className="flex items-center gap-1.5">
                <button type="button" onClick={() => { setPlaying(false); setOpen(i); }} aria-expanded={open === i} data-testid={`stage-${s.key}`}
                  className={`flex w-[120px] flex-col items-center gap-1.5 rounded-xl px-2 py-2.5 ring-1 transition ${open === i ? 'bg-teal-500/10 ring-teal-400/60' : i < open ? 'bg-slate-900/60 ring-slate-700' : 'bg-slate-950/40 ring-slate-800 hover:ring-slate-600'}`}>
                  <div className="flex h-14 items-center">{s.preview}</div><div className={`text-center text-[11px] font-medium ${open === i ? 'text-teal-100' : 'text-slate-300'}`}>{s.title}</div>
                </button>
                {i < S.length - 1 && <ArrowRight size={16} className={i < open ? 'text-teal-400' : 'text-slate-700'} />}
              </li>))}
          </ol>
          <div className="min-h-[230px] rounded-xl bg-slate-950/40 p-5 ring-1 ring-slate-800" key={`${d.image}-${open}`}><FadeIn>{S[open].body}</FadeIn></div>
          <p className="text-[11px] text-slate-500">{d.image.split('/').pop()} · live frozen MobileNetV3 + seed-0 PCA + product-RY kernel; class decision = saved prediction of {d.model.group}.</p>
        </>);
      }}</Gate>
    </div>
  );
}
