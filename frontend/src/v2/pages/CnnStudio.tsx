// CNN feature studio as an animated step-by-step walkthrough (like "How it works"): real frozen-MobileNetV3 activations
// for one NEU-DET train-folder image → 576-d vector → PCA angles → qubits → the models that used them.
// Every value comes from /api/v4/cnn/*; nothing is illustrative.
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Shuffle } from 'lucide-react';
import { useV4 } from '../api';
import { Card, Gate, PageHeader } from '../ui';
import { StepControls, useStepper } from '../playground/widgets';
import { useProgress } from '../learn/lab';
import { ExplainThis } from '../learn/ExplainThis';
import { Lv } from '../level';
import Quiz from '../learn/Quiz';

type MS = { mean: number; std?: number };
type Stage = { layer: number; label: string; what: string; shape: number[]; channels: { channel: number; mean_activation: number; map: string; size: number }[] };
type PcaK = { k: number; explained_variance_ratio: number[]; scores_standardised: number[]; angles_rad: number[] };
type ModelRow = { group: string; model_name: string; pca_k: number | null; n_qubits: number | null; type: 'hybrid' | 'classical'; test_accuracy: MS; test_f1_macro: MS };
type Resp = {
  image: string; class: string; split: string; network: Record<string, any>; load_info: Record<string, any>;
  original: string; model_input: string; model_input_shape: number[]; stages: Stage[]; vector: number[];
  vector_stats: { dim: number; min: number; max: number; mean: number; nonpositive_fraction: number };
  cache_check: { max_abs_diff: number | null; note: string }; pca: PcaK[];
  pca_fit: { seed: number; split: string; n_images: number; steps: string; in_fit_set: boolean; angle_view: string };
  scatter: { pc1: number[]; pc2: number[]; y: number[]; me: [number, number] }; models: ModelRow[];
};
type ImgList = { classes: string[]; images: Record<string, { image: string; split: string }[]>; n_available: number };

const CLASSES = ['crazing', 'inclusion', 'patches', 'pitted_surface', 'rolled-in_scale', 'scratches'];
const NAMES = ['Crazing', 'Inclusion', 'Patches', 'Pitted surface', 'Rolled-in scale', 'Scratches'];
// Validated dark-surface categorical slots, same as the all-models chart: blue = class highlight, orange = hybrid / this image, aqua = classical.
const HI = '#3987e5', AQUA = '#199e70', MARK = '#d95926', GRID = '#1e293b', FAINT = '#334155';
const Big = ({ children }: { children: React.ReactNode }) => <p className="max-w-xl text-[15px] leading-relaxed text-slate-200">{children}</p>;

// ─────────────── stages ───────────────
function SInput({ d, t }: { d: Resp; t: number }) {
  return (
    <div className="flex flex-wrap items-center gap-8">
      <img src={d.original} width={220} height={220} alt="original" className="rounded-md ring-1 ring-slate-700" style={{ opacity: Math.min(1, t * 2) }} />
      <ArrowRight className="text-slate-600" style={{ opacity: t }} />
      <img src={d.model_input} width={220} height={220} alt="network input" className="rounded-md ring-1 ring-slate-700" style={{ opacity: Math.max(0, t * 2 - 1) }} />
      <div className="space-y-3">
        <Big>The photo is resized to <b>224×224</b> and fed into <b>MobileNetV3</b>, a small neural network already trained on millions of everyday photos. We don’t train it — it’s frozen.</Big>
        <div className="flex gap-2"><ExplainThis id="cnn" /><ExplainThis id="mobilenet" /></div>
      </div>
    </div>
  );
}

function SLayer({ s, t, line }: { s: Stage; t: number; line: string }) {
  const [all, setAll] = useState(false);
  const [pick, setPick] = useState(0);
  const cur = s.channels[pick] ?? s.channels[0];
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Big>{line}</Big>
        <span className="rounded-md bg-slate-950/70 px-2 py-1 font-mono text-[12px] text-teal-200 ring-1 ring-slate-800">{s.shape[0]} maps × {s.shape[1]}×{s.shape[2]}</span>
        <ExplainThis id="cnn" />
      </div>
      {!all ? (
        <div className="grid grid-cols-4 gap-3 sm:grid-cols-8">
          {s.channels.slice(0, 8).map((c, i) => {
            const o = Math.max(0, Math.min(1, t * 10 - i));
            return (
              <figure key={c.channel} style={{ opacity: o, transform: `translateY(${(1 - o) * 12}px)` }}>
                <img src={c.map} alt={`filter ${c.channel}`} className="aspect-square w-full rounded-md ring-1 ring-slate-800 [image-rendering:pixelated]" />
                <figcaption className="mt-0.5 text-center text-[10px] text-slate-500">filter {c.channel}</figcaption>
              </figure>);
          })}
        </div>
      ) : (
        <div className="flex flex-wrap items-start gap-5" data-testid="cnn-explore">
          <figure>
            <img src={cur.map} width={200} height={200} alt={`filter ${cur.channel}`} className="rounded-md ring-2 ring-teal-400/60 [image-rendering:pixelated]" />
            <figcaption className="mt-1 text-center text-xs text-slate-300">filter {cur.channel} · strength {cur.mean_activation.toFixed(2)} · rank {pick + 1}/{s.channels.length}</figcaption>
          </figure>
          <div className="grid max-h-[260px] min-w-0 flex-1 grid-cols-[repeat(auto-fill,minmax(30px,1fr))] gap-1 overflow-y-auto pr-1">
            {s.channels.map((c, i) => (
              <button key={c.channel} type="button" onClick={() => setPick(i)} onMouseEnter={() => setPick(i)} title={`filter ${c.channel}`}
                className={`rounded-sm ring-1 ${i === pick ? 'ring-2 ring-teal-400' : 'ring-slate-800'}`}>
                <img src={c.map} alt="" className="aspect-square w-full rounded-sm [image-rendering:pixelated]" />
              </button>))}
          </div>
        </div>)}
      <div className="flex items-center gap-3 text-xs">
        <button type="button" onClick={() => setAll(!all)} className="rounded-md px-2.5 py-1 text-teal-200 ring-1 ring-teal-500/40 hover:bg-teal-500/10" data-testid="cnn-explore-toggle">
          {all ? 'Show the 8 strongest' : `Explore all ${s.channels.length} maps`}
        </button>
        <span className="text-slate-500"><Lv beginner="Bright = this filter found its pattern there. Sorted strongest first." technical={`model.features[${s.layer}] output, per-channel min–max scaled; sorted by spatial mean activation.`} /></span>
      </div>
    </div>
  );
}

function SVector({ d, t }: { d: Resp; t: number }) {
  const [hover, setHover] = useState<number | null>(null);
  const v = d.vector, max = Math.max(...v, 1e-9), n = 24, cell = 13, shown = Math.round(t * v.length);
  return (
    <div className="flex flex-wrap items-start gap-8">
      <div>
        <svg viewBox={`0 0 ${n * cell} ${n * cell}`} width={n * cell} role="img" aria-label="576 feature values" onMouseLeave={() => setHover(null)}>
          {v.map((x, i) => {
            const z = Math.max(0, x) / max;
            return <rect key={i} x={(i % n) * cell} y={Math.floor(i / n) * cell} width={cell - 1.5} height={cell - 1.5} rx={2}
              fill={i >= shown || z <= 0 ? GRID : HI} fillOpacity={i >= shown || z <= 0 ? 1 : 0.2 + 0.8 * Math.sqrt(z)}
              stroke={hover === i ? '#f8fafc' : 'none'} onMouseEnter={() => setHover(i)} />;
          })}
        </svg>
        <div className="mt-1 h-4 text-xs tabular-nums text-slate-300">{hover != null ? `feature ${hover}: ${v[hover].toFixed(3)}` : 'hover a square'}</div>
      </div>
      <div className="space-y-3">
        <Big>Each of the last <b>576 maps</b> is averaged into <b>one number</b>. This list of 576 numbers is the image’s “fingerprint”.</Big>
        <div className="flex gap-3">
          <div className="rounded-lg bg-slate-950/50 px-3 py-2 ring-1 ring-slate-800"><div className="text-[10px] uppercase tracking-wider text-slate-500">numbers</div><div className="text-2xl font-semibold text-white">{d.vector_stats.dim}</div></div>
          <div className="rounded-lg bg-slate-950/50 px-3 py-2 ring-1 ring-slate-800"><div className="text-[10px] uppercase tracking-wider text-slate-500">mostly quiet</div><div className="text-2xl font-semibold text-white">{Math.round(100 * d.vector_stats.nonpositive_fraction)}%</div></div>
        </div>
        {d.cache_check.max_abs_diff != null && <p className="text-xs text-emerald-300/80">✓ identical to the vector the hybrid models were trained on</p>}
      </div>
    </div>
  );
}

function SQubits({ d, t }: { d: Resp; t: number }) {
  const [k, setK] = useState(4);
  const row = d.pca.find((p) => p.k === k) ?? d.pca[0];
  const keep = row.explained_variance_ratio.reduce((a, b) => a + b, 0);
  return (
    <div className="flex flex-wrap items-start gap-8">
      <div className="flex flex-col items-center">
        <div className="text-3xl font-semibold text-white">576</div>
        <div className="my-1 h-10 w-px bg-gradient-to-b from-slate-500 to-teal-400" />
        <div className="text-3xl font-semibold text-teal-300">{k}</div>
        <div className="text-[11px] text-slate-500">keeps {(100 * keep).toFixed(0)}% of the information</div>
      </div>
      <div className="flex flex-wrap gap-4">
        {row.angles_rad.map((a, i) => {
          const th = a * Math.min(1, t * 1.3), r = 34;
          return (
            <figure key={i} className="text-center">
              <svg viewBox="0 0 90 90" width={90} role="img" aria-label={`qubit ${i} angle`}>
                <circle cx={45} cy={45} r={r} fill="#0f172a" stroke="#334155" />
                <line x1={45} y1={45} x2={45 + r * Math.sin(th)} y2={45 - r * Math.cos(th)} stroke="#5eead4" strokeWidth={3.5} strokeLinecap="round" />
                <circle cx={45} cy={45} r={3} fill="#5eead4" />
              </svg>
              <figcaption className="text-[11px] text-slate-400">qubit {i}<br /><span className="tabular-nums text-slate-200">{(a * 180 / Math.PI).toFixed(0)}°</span></figcaption>
            </figure>);
        })}
      </div>
      <div className="space-y-3">
        <Big><Lv beginner={<><b>PCA</b> squeezes 576 numbers into just <b>{k}</b>. Each becomes the angle of <b>one qubit</b> — that’s all the quantum model sees.</>} technical={<>StandardScaler → PCA({k}) on the seed-0 train split → MinMax to [0, π]; θᵢ drives RY(θᵢ) on qubit i.</>} /></Big>
        <div className="flex items-center gap-1.5 text-xs text-slate-400">qubits
          {d.pca.map((p) => <button key={p.k} type="button" onClick={() => setK(p.k)} className={`rounded-md px-2 py-0.5 ring-1 ${p.k === k ? 'bg-teal-500/15 text-teal-100 ring-teal-500/40' : 'ring-slate-700 hover:text-slate-200'}`}>{p.k}</button>)}
        </div>
        <ExplainThis id="pca" />
      </div>
    </div>
  );
}

function SMap({ d, t }: { d: Resp; t: number }) {
  const s = d.scatter, me = d.scatter.me, W = 200, H = 150, P = 8;
  const { x0, x1, y0, y1 } = useMemo(() => {
    const xs = [...s.pc1, me[0]], ys = [...s.pc2, me[1]];
    return { x0: Math.min(...xs), x1: Math.max(...xs), y0: Math.min(...ys), y1: Math.max(...ys) };
  }, [s, me]);
  const X = (v: number) => P + ((v - x0) / (x1 - x0 || 1)) * (W - 2 * P), Y = (v: number) => H - P - ((v - y0) / (y1 - y0 || 1)) * (H - 2 * P);
  return (
    <div className="space-y-3">
      <Big>Every training image as a dot (first 2 of those numbers). <b>Same defect → same neighbourhood.</b> The orange dot is your image.</Big>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" data-testid="cnn-pca-facets">
        {CLASSES.map((c, ci) => (
          <figure key={c} className="rounded-lg border border-slate-800 bg-slate-950/40 p-2">
            <figcaption className="mb-1 text-[12px] font-medium text-slate-200">{NAMES[ci]}</figcaption>
            <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={`${NAMES[ci]} highlighted`}>
              {s.pc1.map((x, i) => s.y[i] !== ci && <circle key={i} cx={X(x)} cy={Y(s.pc2[i])} r={1.3} fill={FAINT} />)}
              {s.pc1.map((x, i) => s.y[i] === ci && <circle key={i} cx={X(x)} cy={Y(s.pc2[i])} r={2} fill={HI} opacity={Math.min(1, t * 1.5)} />)}
              {c === d.class && <circle cx={X(me[0])} cy={Y(me[1])} r={4 + 4 * (1 - t)} fill={MARK} stroke="#0f172a" strokeWidth={2} />}
            </svg>
          </figure>))}
      </div>
    </div>
  );
}

function SModels({ d, t }: { d: Resp; t: number }) {
  const [hover, setHover] = useState<ModelRow | null>(null);
  const ks = [...new Set(d.models.map((m) => m.pca_k))].sort((a, b) => (a ?? 999) - (b ?? 999));
  const groups = ks.map((k) => ({ k, ms: d.models.filter((m) => m.pca_k === k).sort((a, b) => (a.type === b.type ? b.test_accuracy.mean - a.test_accuracy.mean : a.type === 'hybrid' ? -1 : 1)) }));
  const W = 760, H = 230, lo = 0.75, hi = 1, Y = (v: number) => H - 24 - ((v - lo) / (hi - lo)) * (H - 40);
  const bw = 16, gap = 46, span = (g: { ms: unknown[] }) => g.ms.length * (bw + 3) + gap;
  const pos = groups.map((g, i) => ({ ...g, start: 44 + groups.slice(0, i).reduce((a, x) => a + span(x), 0) }));
  const x = 44 + groups.reduce((a, g) => a + span(g), 0);
  return (
    <div className="space-y-3">
      <Big>All models that used these CNN numbers. <span style={{ color: MARK }}>■ hybrid (CNN + quantum)</span> vs <span style={{ color: AQUA }}>■ classical</span>, given <b>exactly the same numbers</b>.</Big>
      <svg viewBox={`0 0 ${Math.max(W, x)} ${H}`} className="w-full" role="img" aria-label="test accuracy of models on CNN features" onMouseLeave={() => setHover(null)} data-testid="cnn-models-chart">
        {[0.75, 0.8, 0.85, 0.9, 0.95, 1].map((v) => <g key={v}><line x1={40} x2={x - gap + 10} y1={Y(v)} y2={Y(v)} stroke={GRID} /><text x={34} y={Y(v) + 4} textAnchor="end" fontSize={10} fill="#64748b">{Math.round(v * 100)}%</text></g>)}
        {pos.map((g) => (
          <g key={String(g.k)}>
            {g.ms.map((m, i) => {
              const cy = Y(lo) - (Y(lo) - Y(m.test_accuracy.mean)) * Math.min(1, t * 1.4), cx = g.start + i * (bw + 3) + bw / 2, on = hover?.group === m.group;
              return (
                <g key={m.group} onMouseEnter={() => setHover(m)} style={{ cursor: 'pointer' }} opacity={hover && !on ? 0.35 : 1}>
                  <rect x={cx - bw / 2} y={20} width={bw} height={Y(lo) - 20} fill="transparent" />
                  <circle cx={cx} cy={cy} r={on ? 8 : 6.5} fill={m.type === 'hybrid' ? MARK : AQUA} stroke={on ? '#f8fafc' : '#0f172a'} strokeWidth={2} />
                </g>);
            })}
            <text x={g.start + (g.ms.length * (bw + 3)) / 2} y={H - 6} textAnchor="middle" fontSize={11} fill="#cbd5e1">{g.k ? `${g.k} numbers` : 'all 576'}</text>
          </g>))}
      </svg>
      <div className="min-h-[40px] rounded-lg bg-slate-950/60 px-3 py-2 text-xs ring-1 ring-slate-800">
        {hover ? <><span className="text-slate-100">{hover.model_name}</span> · <span className="tabular-nums font-semibold text-white">{(100 * hover.test_accuracy.mean).toFixed(1)}%</span> <span className="text-slate-500">± {(100 * (hover.test_accuracy.std ?? 0)).toFixed(1)} · {hover.type}{hover.n_qubits ? ` · ${hover.n_qubits} qubits` : ''}</span></>
          : <span className="text-slate-500">Hover a dot. Same features → hybrid and classical land within about a point of each other: the CNN does most of the work.</span>}
      </div>
      <Link to="/quantum-vs-classical" className="inline-flex items-center gap-1 text-xs text-teal-300 hover:underline">Quantum vs Classical in detail <ArrowRight size={12} /></Link>
    </div>
  );
}

const LINES = [
  'First layer: simple filters light up on edges and bright/dark spots.',
  'A few layers in: edges combine into small textures.',
  'Deeper: bigger patterns — the shape of the defect.',
  'Last layer: 576 detectors, each looking for something different.',
];
const STEPS: { title: string; ms: number; C: (p: { d: Resp; t: number }) => React.ReactElement }[] = [
  { title: 'Into the network', ms: 1600, C: SInput },
  ...[0, 1, 2, 3].map((i) => ({ title: ['Layer 1: edges', 'Layer 3: textures', 'Layer 8: patterns', 'Layer 12: 576 detectors'][i], ms: 1800,
    C: ({ d, t }: { d: Resp; t: number }) => <SLayer s={d.stages[i]} t={t} line={LINES[i]} /> })),
  { title: '576 numbers per image', ms: 2200, C: SVector },
  { title: 'Squeeze into a few qubits', ms: 1600, C: SQubits },
  { title: 'Where does this image sit?', ms: 1400, C: SMap },
  { title: 'Hybrid vs classical on these numbers', ms: 1400, C: SModels },
];

export default function CnnStudio() {
  const list = useV4<ImgList>('/cnn/images');
  const [cls, setCls] = useState('scratches');
  const [picked, setImg] = useState<string | null>(null);
  const img = picked ?? list.data?.images[cls]?.[0]?.image ?? null;
  const st = useV4<Resp>(img ? `/cnn/features?image=${encodeURIComponent(img)}` : null);
  const [step, setStep] = useState(0);
  const { playing, setPlaying } = useStepper(STEPS.length, step, setStep, STEPS[step].ms + 2000);
  const t = useProgress(`${step}:${img}`, STEPS[step].ms);
  const pool = list.data?.images[cls] ?? [];
  const Stage = STEPS[step].C;
  return (
    <div className="space-y-5">
      <PageHeader title="What a CNN sees" subtitle="Press Play. A real image goes through the frozen MobileNetV3 and becomes qubit angles. All live, nothing faked." />
      <Card title="" className="overflow-hidden">
        <div className="space-y-4" data-testid="cnn-stage" data-step={step}>
          <StepControls step={step} n={STEPS.length} setStep={setStep} playing={playing} setPlaying={setPlaying} title={STEPS[step].title} />
          <div className="flex flex-wrap items-center gap-2 text-xs">
            {CLASSES.map((c, i) => (
              <button key={c} type="button" onClick={() => { setCls(c); setImg(null); }}
                className={`rounded-md px-2.5 py-1 ring-1 ${c === cls ? 'bg-teal-500/15 text-teal-100 ring-teal-500/40' : 'text-slate-400 ring-slate-700 hover:text-slate-200'}`}>{NAMES[i]}</button>))}
            <button type="button" disabled={!pool.length} onClick={() => { const i = pool.findIndex((x) => x.image === img); setImg(pool[(i + 1) % pool.length].image); }}
              className="ml-auto inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-slate-300 ring-1 ring-slate-700" data-testid="cnn-next-image"><Shuffle size={12} /> another image</button>
          </div>
          <div className="min-h-[340px]">
            <Gate state={list.error ? { data: null, error: list.error, loading: false } : st}>{(d) => <Stage d={d} t={t} />}</Gate>
          </div>
          {st.data && <p className="text-[11px] text-slate-500">{st.data.image.split('/').pop()} · {st.data.network.architecture} · frozen ImageNet weights · computed live</p>}
        </div>
      </Card>
      <Quiz id="cnn" />
    </div>
  );
}
