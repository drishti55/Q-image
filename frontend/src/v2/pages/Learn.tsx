// Visual learning lab: a real NEU-DET training image goes through pixels → qubit → FRQI → NEQR → shots → kernel → patches,
// step by step and animated. All maths runs in the browser on the real pixels (see learn/lab.ts); it teaches the ideas
// and is labelled as such — trained-model results live on the results pages.
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Clapperboard, Network, Shuffle } from 'lucide-react';
import { Card, PageHeader } from '../ui';
import { StepControls, useStepper } from '../playground/widgets';
import { ExplainThis } from '../learn/ExplainThis';
import HybridPipeline from '../learn/HybridPipeline';
import Quiz from '../learn/Quiz';
import {
  frqiAmps, frqiOverlap, frqiQubits, frqiShots, loadGray, mse, neqrQubits, neqrShots, patchKernel, quant, roll, theta, useGray, useProgress,
} from '../learn/lab';
import type { Img } from '../learn/lab';

const CLASSES = ['crazing', 'inclusion', 'patches', 'pitted_surface', 'rolled-in_scale', 'scratches'];
const NAMES = ['Crazing', 'Inclusion', 'Patches', 'Pitted surface', 'Rolled-in scale', 'Scratches'];
const BLUE = '#3987e5', ORANGE = '#d95926';
const url = (c: string, n: number) => `/api/v2/dataset/sample/${c}.png?n=${n}`;

function Px({ a, size, label, children }: { a: Img | null; size: number; label?: React.ReactNode; children?: React.ReactNode }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const cv = ref.current; if (!cv || !a) return;
    const n = a.length; cv.width = n; cv.height = n;
    const ctx = cv.getContext('2d'); if (!ctx) return;
    const im = ctx.createImageData(n, n);
    a.forEach((r, y) => r.forEach((v, x) => { const g = Math.round(Math.max(0, Math.min(1, v)) * 255), i = (y * n + x) * 4; im.data.set([g, g, g, 255], i); }));
    ctx.putImageData(im, 0, 0);
  }, [a]);
  return (
    <figure className="inline-block">
      <div className="relative" style={{ width: size, height: size }}>
        <canvas ref={ref} style={{ width: size, height: size, imageRendering: 'pixelated' }} className="rounded-md ring-1 ring-slate-700" />
        {children && <svg className="absolute inset-0" viewBox={`0 0 ${size} ${size}`} width={size} height={size}>{children}</svg>}
      </div>
      {label && <figcaption className="mt-1 text-center text-[11px] text-slate-400">{label}</figcaption>}
    </figure>
  );
}

const Big = ({ children }: { children: React.ReactNode }) => <p className="text-[15px] leading-relaxed text-slate-200">{children}</p>;
const Chip = ({ children }: { children: React.ReactNode }) => <span className="rounded-md bg-slate-950/70 px-2 py-1 font-mono text-[12px] text-teal-200 ring-1 ring-slate-800">{children}</span>;
const Stat = ({ k, v, tone }: { k: string; v: React.ReactNode; tone?: string }) => (
  <div className="rounded-lg bg-slate-950/50 px-3 py-2 ring-1 ring-slate-800"><div className="text-[10px] uppercase tracking-wider text-slate-500">{k}</div><div className="text-xl font-semibold tabular-nums" style={{ color: tone ?? '#f8fafc' }}>{v}</div></div>
);
function Toggle<T extends number>({ v, set, opts, label }: { v: T; set: (x: T) => void; opts: T[]; label: string }) {
  return (
    <div className="flex items-center gap-1.5 text-xs text-slate-400">{label}
      {opts.map((o) => <button key={o} type="button" onClick={() => set(o)} className={`rounded-md px-2 py-0.5 ring-1 ${o === v ? 'bg-teal-500/15 text-teal-100 ring-teal-500/40' : 'ring-slate-700 hover:text-slate-200'}`}>{o}</button>)}
    </div>
  );
}

type Ctx = {
  big: Img; small: Img; img8: Img; N: 2 | 4 | 8; setN: (n: 2 | 4 | 8) => void; q: 2 | 4 | 8; setQ: (q: 2 | 4 | 8) => void;
  rows: Img[] | null; cols: Img[] | null; cls: number;
};

// ─────────────── stages ───────────────
function SImage({ c, t }: { c: Ctx; t: number }) {
  return (
    <div className="flex flex-wrap items-center gap-8">
      <div style={{ opacity: t, transform: `scale(${0.9 + 0.1 * t})`, transition: 'none' }}><Px a={c.big} size={260} label={`${NAMES[c.cls]} · real NEU-DET training image`} /></div>
      <div className="max-w-md space-y-3">
        <Big>A camera photo of a steel surface. Our job: say which of <b>6 defect types</b> it shows.</Big>
        <div className="flex flex-wrap gap-1.5">{NAMES.map((n, i) => <span key={n} className={`rounded-full px-2.5 py-1 text-xs ring-1 ${i === c.cls ? 'bg-teal-500/15 text-teal-100 ring-teal-500/40' : 'text-slate-500 ring-slate-800'}`}>{n}</span>)}</div>
      </div>
    </div>
  );
}

function SPixels({ c, t }: { c: Ctx; t: number }) {
  const n = c.N, cell = 260 / n;
  return (
    <div className="flex flex-wrap items-center gap-8">
      <Px a={c.big} size={160} label="original" />
      <ArrowRight className="text-slate-600" />
      <Px a={c.small} size={260} label={`${n}×${n} = ${n * n} numbers`}>
        {c.small.flat().map((v, i) => {
          const show = t * c.small.flat().length > i;
          return show && n <= 8 && <text key={i} x={(i % n) * cell + cell / 2} y={Math.floor(i / n) * cell + cell / 2 + 4} textAnchor="middle" fontSize={n === 8 ? 10 : 15} fontWeight={600} fill={v > 0.55 ? '#0f172a' : '#f8fafc'}>{v.toFixed(2)}</text>;
        })}
      </Px>
      <div className="space-y-3">
        <Big>Shrink it and read each pixel as a number: <b>0 = black, 1 = white</b>.</Big>
        <Toggle v={c.N} set={c.setN} opts={[2, 4, 8] as (2 | 4 | 8)[]} label="size" />
      </div>
    </div>
  );
}

function QubitDial({ x, size = 220 }: { x: number; size?: number }) {
  const th = theta(x), r = size * 0.38, cx = size * 0.2, cy = size * 0.8;
  const ex = cx + r * Math.sin(th), ey = cy - r * Math.cos(th);
  return (
    <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size} role="img" aria-label="qubit state arrow">
      <path d={`M ${cx} ${cy - r} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`} fill="none" stroke="#334155" strokeDasharray="4 4" />
      <line x1={cx} y1={cy} x2={cx} y2={cy - r - 8} stroke="#475569" /><line x1={cx} y1={cy} x2={cx + r + 8} y2={cy} stroke="#475569" />
      <text x={cx - 6} y={cy - r - 12} fontSize={13} fill={BLUE} fontWeight={700}>|0⟩</text>
      <text x={cx + r + 10} y={cy + 4} fontSize={13} fill={ORANGE} fontWeight={700}>|1⟩</text>
      <line x1={cx} y1={cy} x2={ex} y2={ey} stroke="#5eead4" strokeWidth={4} strokeLinecap="round" />
      <circle cx={ex} cy={ey} r={6} fill="#5eead4" />
      <text x={cx + 10} y={cy - 10} fontSize={12} fill="#94a3b8">θ = {(th * 180 / Math.PI).toFixed(0)}°</text>
    </svg>
  );
}

function SQubit({ c, t }: { c: Ctx; t: number }) {
  const px = c.small.flat();
  const [i, setI] = useState(() => px.indexOf(Math.max(...px)));
  const [manual, setManual] = useState<number | null>(null);
  const x = manual ?? px[Math.min(i, px.length - 1)] * t;
  const p0 = Math.cos(theta(x)) ** 2, p1 = 1 - p0;
  return (
    <div className="flex flex-wrap items-center gap-8">
      <div className="space-y-2">
        <Px a={c.small} size={150} label="click a pixel">
          {px.map((_, k) => { const s = 150 / c.N; return <rect key={k} x={(k % c.N) * s} y={Math.floor(k / c.N) * s} width={s} height={s} fill="transparent" stroke={k === i && manual == null ? '#5eead4' : 'none'} strokeWidth={3} style={{ cursor: 'pointer' }} onClick={() => { setI(k); setManual(null); }} />; })}
        </Px>
      </div>
      <QubitDial x={x} />
      <div className="w-64 space-y-3">
        <Big>One qubit stores one pixel as an <b>arrow</b>. Brighter pixel → arrow turns further toward |1⟩.</Big>
        <input type="range" min={0} max={1} step={0.01} value={x} onChange={(e) => setManual(+e.target.value)} className="w-full accent-teal-400" aria-label="pixel brightness" />
        <div className="text-xs text-slate-400">brightness <b className="text-slate-100">{x.toFixed(2)}</b></div>
        {[['P(0)', p0, BLUE], ['P(1)', p1, ORANGE]].map(([k, v, col]) => (
          <div key={k as string} className="flex items-center gap-2 text-xs"><span className="w-10 text-slate-400">{k}</span>
            <div className="h-3 flex-1 rounded-full bg-slate-800"><div className="h-3 rounded-full" style={{ width: `${100 * (v as number)}%`, background: col as string }} /></div>
            <span className="w-10 text-right tabular-nums text-slate-200">{(v as number).toFixed(2)}</span></div>))}
        <Chip>θ = brightness × 90°</Chip>
      </div>
    </div>
  );
}

function SFRQI({ c, t }: { c: Ctx; t: number }) {
  const n = c.N, S = 260, cell = S / n, px = c.small.flat();
  const [hov, setHov] = useState<number | null>(null);
  const { c0, c1 } = useMemo(() => frqiAmps(c.small), [c.small]);
  const amps = [...c0, ...c1], W = 420, H = 150, bw = W / amps.length, mx = Math.max(...amps.map(Math.abs));
  return (
    <div className="flex flex-wrap items-start gap-8">
      <Px a={c.small} size={S}>
        {px.map((v, i) => {
          const cx = (i % n) * cell + cell / 2, cy = Math.floor(i / n) * cell + cell / 2, r = cell * 0.36, th = theta(v) * Math.min(1, t * 1.4);
          return (
            <g key={i} onMouseEnter={() => setHov(i)} onMouseLeave={() => setHov(null)}>
              <rect x={cx - cell / 2} y={cy - cell / 2} width={cell} height={cell} fill="transparent" stroke={hov === i ? '#5eead4' : 'none'} strokeWidth={2} />
              <circle cx={cx} cy={cy} r={r} fill="#0f172acc" />
              <line x1={cx} y1={cy} x2={cx + r * Math.sin(th)} y2={cy - r * Math.cos(th)} stroke="#5eead4" strokeWidth={n === 8 ? 2 : 3} strokeLinecap="round" />
            </g>);
        })}
      </Px>
      <div className="min-w-0 flex-1 space-y-3">
        <Big>FRQI does it for <b>every pixel at once</b>: one shared “colour” qubit, plus position qubits that say which pixel.</Big>
        <div className="flex flex-wrap gap-3">
          <Stat k="pixels" v={n * n} /><Stat k="qubits needed" v={frqiQubits(n)} tone="#5eead4" /><Stat k="amplitudes" v={2 * n * n} />
        </div>
        <svg viewBox={`0 0 ${W} ${H + 16}`} className="w-full max-w-[460px]" role="img" aria-label="FRQI amplitudes">
          {amps.map((a, k) => {
            const pix = k % (n * n), on = hov == null || hov === pix, h = (Math.abs(a) / (mx || 1)) * H * t;
            return <rect key={k} x={k * bw + 0.5} y={H - h} width={Math.max(1, bw - 1)} height={h} rx={1} fill={k < n * n ? BLUE : ORANGE} opacity={on ? 1 : 0.15} />;
          })}
          <text x={0} y={H + 13} fontSize={10} fill={BLUE}>cos θ part (|0⟩)</text>
          <text x={W} y={H + 13} fontSize={10} fill={ORANGE} textAnchor="end">sin θ part (|1⟩)</text>
        </svg>
        <div className="flex flex-wrap items-center gap-3"><Toggle v={c.N} set={c.setN} opts={[2, 4, 8] as (2 | 4 | 8)[]} label="size" /><ExplainThis id="frqi" /></div>
      </div>
    </div>
  );
}

function SNEQR({ c, t }: { c: Ctx; t: number }) {
  const n = c.N, S = 260, cell = S / n, px = c.small.flat(), q = c.q;
  const qi = useMemo(() => c.small.map((r) => r.map((v) => quant(v, q) / (2 ** q - 1))), [c.small, q]);
  const err = mse(c.small, qi);
  return (
    <div className="flex flex-wrap items-start gap-8">
      <Px a={qi} size={S}>
        {n <= 4 && px.map((v, i) => {
          const bits = quant(v, q).toString(2).padStart(q, '0'), shown = Math.round(t * q * 1.3);
          const cx = (i % n) * cell + cell / 2, cy = Math.floor(i / n) * cell + cell / 2;
          return (
            <g key={i}><rect x={cx - cell * 0.42} y={cy - 12} width={cell * 0.84} height={24} rx={4} fill="#0f172add" />
              <text x={cx} y={cy + 5} textAnchor="middle" fontSize={n === 2 ? 18 : q === 8 ? 10 : 14} fontFamily="monospace" fill="#fbbf24">{bits.slice(0, shown).padEnd(q, '·')}</text></g>);
        })}
      </Px>
      <div className="min-w-0 flex-1 space-y-3">
        <Big>NEQR writes each brightness as <b>binary bits</b> instead of an angle. More bits → closer to the real image, but more qubits.</Big>
        <Toggle v={q} set={c.setQ} opts={[2, 4, 8] as (2 | 4 | 8)[]} label="bits" />
        <div className="flex flex-wrap gap-3">
          <Stat k="shades" v={2 ** q} /><Stat k="qubits needed" v={neqrQubits(n, q)} tone="#fbbf24" /><Stat k="FRQI needs" v={frqiQubits(n)} /><Stat k="rounding error (MSE)" v={err.toFixed(4)} />
        </div>
        <div className="flex items-center gap-3"><Toggle v={c.N} set={c.setN} opts={[2, 4, 8] as (2 | 4 | 8)[]} label="size" /><ExplainThis id="neqr" /></div>
      </div>
    </div>
  );
}

function SShots({ c, t }: { c: Ctx; t: number }) {
  const [manual, setManual] = useState<number | null>(null);
  const [seed, setSeed] = useState(1);
  const lg = manual ?? 1 + 3 * t;
  const shots = Math.round(10 ** lg);
  const f = useMemo(() => frqiShots(c.small, shots, seed), [c.small, shots, seed]);
  const ne = useMemo(() => neqrShots(c.small, c.q, shots, seed), [c.small, c.q, shots, seed]);
  return (
    <div className="space-y-4">
      <Big>You can’t read a quantum state directly — you <b>measure it many times (“shots”)</b> and rebuild the image from the counts.</Big>
      <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
        shots <input type="range" min={1} max={5} step={0.05} value={lg} onChange={(e) => setManual(+e.target.value)} className="w-64 accent-teal-400" aria-label="shots" />
        <b className="w-16 tabular-nums text-lg text-white">{shots.toLocaleString()}</b>
        <button type="button" onClick={() => setSeed((s) => s + 1)} className="inline-flex items-center gap-1 rounded-md px-2 py-1 ring-1 ring-slate-700 hover:text-slate-200"><Shuffle size={12} /> measure again</button>
      </div>
      <div className="flex flex-wrap items-end gap-6">
        <Px a={c.small} size={170} label="original" />
        <div className="space-y-1"><Px a={f.img} size={170} label={<span style={{ color: '#5eead4' }}>FRQI rebuilt</span>} /><div className="text-center text-xs tabular-nums text-slate-300">error {mse(c.small, f.img).toFixed(4)}</div></div>
        <div className="space-y-1"><Px a={ne.img} size={170} label={<span style={{ color: '#fbbf24' }}>NEQR rebuilt ({c.q}-bit)</span>} /><div className="text-center text-xs tabular-nums text-slate-300">error {mse(c.small, ne.img).toFixed(4)} · {ne.missed} pixels never seen</div></div>
      </div>
      <p className="text-xs text-slate-500">FRQI gets smoothly better with more shots; NEQR is exact for every pixel it has seen. Simulated in your browser. <Link to="/reconstruction-full" className="text-teal-300 hover:underline">Real results on all 1,800 images →</Link></p>
    </div>
  );
}

function SKernel({ c, t }: { c: Ctx; t: number }) {
  const [sel, setSel] = useState<[number, number]>([c.cls, (c.cls + 1) % 6]);
  if (!c.rows || !c.cols) return <div className="text-sm text-slate-400">Loading the six classes…</div>;
  const K = c.rows.map((a) => c.cols!.map((b) => frqiOverlap(a.flat(), b.flat())));
  const lo = Math.min(...K.flat()), hi = Math.max(...K.flat()), cell = 46;
  const v = K[sel[0]][sel[1]];
  return (
    <div className="flex flex-wrap items-start gap-8">
      <svg viewBox={`0 0 ${cell * 6 + 90} ${cell * 6 + 90}`} width={cell * 6 + 90} role="img" aria-label="FRQI similarity between classes">
        {NAMES.map((nm, i) => <text key={`r${i}`} x={84} y={90 + i * cell + cell / 2 + 4} textAnchor="end" fontSize={10} fill="#94a3b8">{nm.split(' ')[0]}</text>)}
        {NAMES.map((nm, j) => <text key={`c${j}`} transform={`translate(${90 + j * cell + cell / 2}, 84) rotate(-45)`} fontSize={10} fill="#94a3b8">{nm.split(' ')[0]}</text>)}
        {K.map((r, i) => r.map((k, j) => {
          const s = (k - lo) / (hi - lo || 1), on = sel[0] === i && sel[1] === j;
          return (
            <g key={`${i}${j}`} onClick={() => setSel([i, j])} style={{ cursor: 'pointer' }}>
              <rect x={90 + j * cell + 1} y={90 + i * cell + 1} width={cell - 2} height={cell - 2} rx={3} fill={BLUE} fillOpacity={(0.12 + 0.88 * s) * Math.min(1, t * 1.5)} stroke={on ? '#f8fafc' : 'none'} strokeWidth={2} />
              <text x={90 + j * cell + cell / 2} y={90 + i * cell + cell / 2 + 4} textAnchor="middle" fontSize={10} fill={s > 0.6 ? '#f8fafc' : '#cbd5e1'}>{k.toFixed(2)}</text>
            </g>);
        }))}
      </svg>
      <div className="space-y-3">
        <Big>To classify, compare images: the <b>overlap</b> of two quantum states is their similarity (1 = identical, 0 = totally different). Click a square.</Big>
        <div className="flex items-center gap-4">
          <Px a={c.rows[sel[0]]} size={110} label={NAMES[sel[0]]} />
          <div className="text-center"><div className="text-3xl font-semibold tabular-nums text-white">{v.toFixed(3)}</div><div className="text-[11px] text-slate-500">similarity</div></div>
          <Px a={c.cols[sel[1]]} size={110} label={NAMES[sel[1]]} />
        </div>
        <p className="max-w-md text-xs text-slate-400">Notice the matching-class squares aren’t always the brightest: whole-image similarity mixes classes up. That’s why whole-image FRQI only reached ~60% (V2).</p>
        <Chip>K = |⟨ψ_A|ψ_B⟩|²</Chip> <ExplainThis id="kernel" />
      </div>
    </div>
  );
}

function SPatches({ c, t }: { c: Ctx; t: number }) {
  const [manual, setManual] = useState<number | null>(null);
  const s = manual ?? Math.round(4 * t);
  const curve = useMemo(() => Array.from({ length: 7 }, (_, k) => {
    const B = roll(c.img8, k);
    return { k, whole: frqiOverlap(c.img8.flat(), B.flat()), patch: patchKernel(c.img8, B, 2) / patchKernel(c.img8, c.img8, 2) };
  }), [c.img8]);
  const cur = curve[s], W = 320, H = 170, X = (k: number) => 40 + (k / 6) * (W - 70);
  const lo = Math.floor(Math.min(...curve.flatMap((p) => [p.whole, p.patch])) * 50 - 0.5) / 50, Y = (v: number) => H - 10 - ((v - lo) / (1 - lo || 1)) * (H - 30);
  return (
    <div className="flex flex-wrap items-start gap-8">
      <div className="space-y-2">
        <div className="flex gap-3"><Px a={c.img8} size={150} label="16×16 image" /><Px a={roll(c.img8, s)} size={150} label={`shifted ${s} px`} /></div>
        <input type="range" min={0} max={6} step={1} value={s} onChange={(e) => setManual(+e.target.value)} className="w-full accent-teal-400" aria-label="shift" />
      </div>
      <div className="space-y-3">
        <Big>A defect slightly <b>moved</b> is still the same defect. Whole-image FRQI says “different!”; Protocol V4 compares <b>small patches</b> instead, so it doesn’t care.</Big>
        <svg viewBox={`0 0 ${W} ${H + 20}`} width={W} role="img" aria-label="similarity versus shift">
          {[lo, (lo + 1) / 2, 1].map((v) => <g key={v}><line x1={40} x2={W - 30} y1={Y(v)} y2={Y(v)} stroke="#1e293b" /><text x={34} y={Y(v) + 4} textAnchor="end" fontSize={10} fill="#64748b">{v.toFixed(2)}</text></g>)}
          {curve.map((p) => <text key={p.k} x={X(p.k)} y={H + 14} textAnchor="middle" fontSize={10} fill="#64748b">{p.k}px</text>)}
          {([['whole', '#9aa3ad', 'whole image'], ['patch', '#5eead4', 'patches (V4)']] as const).map(([key, col, lab]) => (
            <g key={key}>
              <polyline fill="none" stroke={col} strokeWidth={2} points={curve.map((p) => `${X(p.k)},${Y(p[key])}`).join(' ')} />
              {curve.map((p) => <circle key={p.k} cx={X(p.k)} cy={Y(p[key])} r={p.k === s ? 6 : 4} fill={col} stroke="#0f172a" strokeWidth={2} />)}
              <text x={X(6) + 4} y={Y(curve[6][key]) + (key === 'whole' ? 14 : -8)} fontSize={10} fill="#cbd5e1" textAnchor="end">{lab}</text>
            </g>))}
        </svg>
        <div className="flex gap-3"><Stat k="whole image" v={cur.whole.toFixed(3)} /><Stat k="patches (V4)" v={cur.patch.toFixed(3)} tone="#5eead4" /></div>
        <ExplainThis id="density" />
      </div>
    </div>
  );
}

function SNext() {
  const cards = [
    { to: '/how-it-works', icon: Clapperboard, title: 'Watch the real model decide', sub: 'The frozen V4 FRQI model on a real test image.' },
    { to: '/cnn', icon: Network, title: 'See what a CNN sees', sub: 'Live MobileNetV3 feature maps → qubits.' },
    { to: '/compare', icon: ArrowRight, title: 'All 163 models on one chart', sub: 'Quantum vs hybrid vs classical.' },
  ];
  return (
    <div className="space-y-4">
      <Big>A classifier (SVM) uses those similarities to pick the defect type. Now see it on the <b>real trained models</b>:</Big>
      <div className="grid gap-3 md:grid-cols-3">{cards.map((k) => (
        <Link key={k.to} to={k.to} className="group rounded-xl border border-slate-800 bg-slate-950/50 p-4 hover:border-teal-500/50">
          <k.icon size={20} className="text-teal-300" /><div className="mt-2 font-semibold text-slate-100 group-hover:text-white">{k.title}</div><div className="text-xs text-slate-400">{k.sub}</div>
        </Link>))}</div>
    </div>
  );
}

const STAGES = [
  { title: 'A real steel image', ms: 900, C: SImage },
  { title: 'Pixels are just numbers', ms: 2200, C: SPixels },
  { title: 'One pixel → one qubit', ms: 1800, C: SQubit },
  { title: 'FRQI: the whole image in a few qubits', ms: 2200, C: SFRQI },
  { title: 'NEQR: brightness as bits', ms: 2400, C: SNEQR },
  { title: 'Measuring: shots', ms: 4000, C: SShots },
  { title: 'Similarity between images', ms: 1500, C: SKernel },
  { title: 'Patches: shift-proof similarity (V4)', ms: 3000, C: SPatches },
  { title: 'Decide — and see the real models', ms: 500, C: SNext },
] as const;

export default function Learn() {
  const [cls, setCls] = useState(5);
  const [idx, setIdx] = useState(0);
  const [N, setN] = useState<2 | 4 | 8>(4);
  const [q, setQ] = useState<2 | 4 | 8>(4);
  const [step, setStep] = useState(0);
  const { playing, setPlaying } = useStepper(STAGES.length, step, setStep, STAGES[step].ms + 2200);
  const u = url(CLASSES[cls], idx);
  const big = useGray(u, 128), small = useGray(u, N), img8 = useGray(u, 16);
  const [grid, setGrid] = useState<{ n: number; rows: Img[]; cols: Img[] } | null>(null);
  useEffect(() => {
    let live = true;
    Promise.all([
      Promise.all(CLASSES.map((k) => loadGray(url(k, 0), N))), Promise.all(CLASSES.map((k) => loadGray(url(k, 1), N))),
    ]).then(([rows, cols]) => live && setGrid({ n: N, rows, cols })).catch(() => {});
    return () => { live = false; };
  }, [N]);
  const t = useProgress(`${step}:${u}:${N}:${q}`, STAGES[step].ms);
  const ready = big.img && small.img && img8.img;
  const ctx: Ctx | null = ready ? { big: big.img!, small: small.img!, img8: img8.img!, N, setN, q, setQ, rows: grid?.n === N ? grid.rows : null, cols: grid?.n === N ? grid.cols : null, cls } : null;
  const Stage = STAGES[step].C as (p: { c: Ctx; t: number }) => React.ReactElement;
  return (
    <div className="space-y-5">
      <PageHeader title="Learn by seeing" subtitle="Click through the pipeline, then press Play below to see how an image becomes qubits." />
      <Card title="The whole pipeline on one test image" subtitle="Click a stage. Real CNN, real PCA, real quantum kernel, saved model decision.">
        <HybridPipeline />
      </Card>
      <Card title="" className="overflow-hidden">
        <div className="space-y-4" data-testid="lab-stage" data-step={step}>
          <StepControls step={step} n={STAGES.length} setStep={setStep} playing={playing} setPlaying={setPlaying} title={STAGES[step].title} />
          <div className="flex flex-wrap items-center gap-2 text-xs">
            {NAMES.map((n, i) => (
              <button key={n} type="button" onClick={() => setCls(i)} className={`rounded-md px-2.5 py-1 ring-1 ${cls === i ? 'bg-teal-500/15 text-teal-100 ring-teal-500/40' : 'text-slate-400 ring-slate-700 hover:text-slate-200'}`}>{n}</button>))}
            <button type="button" onClick={() => setIdx((idx + 1) % 20)} className="ml-auto inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-slate-300 ring-1 ring-slate-700"><Shuffle size={12} /> another image</button>
          </div>
          <div className="min-h-[340px]">
            {big.err ? <div className="text-sm text-amber-300">Could not load this image ({big.err}). Try “another image”, or check the backend is running.</div>
              : ctx ? <Stage key={`${step}-${u}`} c={ctx} t={t} /> : <div className="text-sm text-slate-400">Loading image…</div>}
          </div>
          <p className="text-[11px] text-slate-500">Teaching demo: real NEU-DET pixels (contrast-stretched per image, as the V4 model does), maths computed in your browser. Trained-model results are on the results pages.</p>
        </div>
      </Card>
      <Quiz id="pipeline" />
    </div>
  );
}
