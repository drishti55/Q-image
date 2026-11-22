// Interactive sandbox for the 3×3 playground: edit pixels and every visual updates immediately — normalisation, FRQI
// angles, NEQR bits (2/4/8), PCA (k), feature map (Product-RY / ZZ-Linear / ZZ-Full), circuit and kernel matrix.
// Maths runs in the browser (learn/qsim.ts, verified against src/v2/qkernel.py). PCA is fitted on 7 tiny images only:
// your grid + one real NEU-DET training image per class, shrunk to 3×3. Illustrative — not the trained models.
import { useEffect, useMemo, useState } from 'react';
import { Info, RotateCcw, Shuffle } from 'lucide-react';
import { Heatmap, MiniCircuit, Note } from './widgets';
import { encode, featureMapGates, fidelity, pca, toAngles } from '../learn/qsim';
import type { FMap } from '../learn/qsim';
import { loadGray, quant } from '../learn/lab';
import { ExplainThis } from '../learn/ExplainThis';
import { Lv } from '../level';

const START = [[70, 180, 0], [19, 20, 0], [0, 0, 0]];
const CLASSES = ['crazing', 'inclusion', 'patches', 'pitted_surface', 'rolled-in_scale', 'scratches'];
const SHORT = ['Crazing', 'Inclusion', 'Patches', 'Pitted', 'Rolled-in', 'Scratches'];
const TEAL = '#5eead4', AMBER = '#fbbf24', ORANGE = '#d95926';
const FM: [FMap, string][] = [['product_ry', 'Product-RY'], ['zz_linear', 'ZZ-Linear'], ['zz_full', 'ZZ-Full']];

function Grid({ g, size = 150, cell, sel, onPick }: { g: number[][]; size?: number; cell: (v: number, i: number, s: number) => React.ReactNode; sel?: number; onPick?: (i: number) => void }) {
  const s = size / 3;
  return (
    <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size} className="rounded-md ring-1 ring-slate-700">
      {g.flat().map((v, i) => (
        <g key={i} transform={`translate(${(i % 3) * s},${Math.floor(i / 3) * s})`} onClick={() => onPick?.(i)} style={{ cursor: onPick ? 'pointer' : 'default' }}>
          <rect width={s} height={s} fill={`rgb(${v},${v},${v})`} stroke={sel === i ? TEAL : '#0f172a'} strokeWidth={sel === i ? 3 : 1} />
          {cell(v, i, s)}
        </g>))}
    </svg>
  );
}
const Lab = ({ t, sub }: { t: string; sub?: string }) => <div className="mt-1 text-center text-[11px] text-slate-300">{t}{sub && <div className="text-[10px] text-slate-500">{sub}</div>}</div>;
const txt = (v: number) => (v > 128 ? '#0f172a' : '#f8fafc');

export default function Sandbox() {
  const [g, setG] = useState(START);
  const [sel, setSel] = useState(1);
  const [bits, setBits] = useState<2 | 4 | 8>(4);
  const [k, setK] = useState(3);
  const [fmap, setFmap] = useState<FMap>('zz_linear');
  const [bw, setBw] = useState(1);
  const [refs, setRefs] = useState<number[][][] | null>(null);
  useEffect(() => {
    let live = true;
    Promise.all(CLASSES.map((c) => loadGray(`/api/v2/dataset/sample/${c}.png?n=0`, 3, false)))
      .then((r) => live && setRefs(r.map((a) => a.map((row) => row.map((v) => Math.round(v * 255))))), () => live && setRefs([]));
    return () => { live = false; };
  }, []);
  const set = (v: number) => setG(g.map((r, y) => r.map((x, c) => (y * 3 + c === sel ? v : x))));
  const flat = g.flat(), sv = flat[sel];

  const q = useMemo(() => {
    if (!refs?.length) return null;
    const rows = [flat, ...refs.map((r) => r.flat())];
    const p = pca(rows.map((r) => r.map((v) => v / 255)), k);
    const ang = toAngles(p.scores).map((r) => r.map((a) => a * bw));
    const S = ang.map((a) => encode(a, fmap));
    const K = S.map((a) => S.map((b) => fidelity(a, b)));
    return { p, ang, K };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [g, refs, k, fmap, bw]);

  return (
    <div className="space-y-5" data-testid="sandbox">
      <Note tone="amber"><Info size={13} className="mr-1 inline" />Illustrative sandbox: maths runs live in your browser on your 3×3 grid and 6 real NEU-DET images shrunk to 3×3. Not the trained models.</Note>
      <div className="flex flex-wrap items-start gap-5">
        <div>
          <Grid g={g} sel={sel} onPick={setSel} cell={(v, i, s) => <text x={s / 2} y={s / 2 + 5} textAnchor="middle" fontSize={15} fontWeight={600} fill={txt(v)}>{v}</text>} />
          <Lab t="your 3×3 image" sub="click a pixel" />
        </div>
        <div className="w-44 space-y-2 pt-2">
          <div className="text-xs text-slate-400">pixel {sel} · <b className="tabular-nums text-white">{sv}</b></div>
          <input type="range" min={0} max={255} value={sv} onChange={(e) => set(+e.target.value)} className="w-full accent-teal-400" aria-label="pixel value" data-testid="sandbox-slider" />
          <div className="flex gap-1.5 text-[11px]">
            <button type="button" onClick={() => setG(Array.from({ length: 3 }, () => Array.from({ length: 3 }, () => Math.floor(Math.random() * 256))))} className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-slate-300 ring-1 ring-slate-700"><Shuffle size={11} /> random</button>
            <button type="button" onClick={() => setG(START)} className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-slate-300 ring-1 ring-slate-700"><RotateCcw size={11} /> reset</button>
          </div>
        </div>
        <div>
          <Grid g={g} sel={sel} cell={(v, _i, s) => <text x={s / 2} y={s / 2 + 5} textAnchor="middle" fontSize={13} fill={txt(v)}>{(v / 255).toFixed(2)}</text>} />
          <Lab t="normalised" sub="value ÷ 255" />
        </div>
        <div>
          <Grid g={g} sel={sel} cell={(v, _i, s) => { const th = (Math.PI / 2) * (v / 255), r = s * 0.32; return (
            <g><circle cx={s / 2} cy={s / 2} r={r} fill="#0f172acc" /><line x1={s / 2} y1={s / 2} x2={s / 2 + r * Math.sin(th)} y2={s / 2 - r * Math.cos(th)} stroke={ORANGE} strokeWidth={3} strokeLinecap="round" />
              <text x={s / 2} y={s - 4} textAnchor="middle" fontSize={10} fill="#f8fafc">{Math.round((th * 180) / Math.PI)}°</text></g>); }} />
          <Lab t="FRQI angle" sub="θ = 90° × value/255" />
        </div>
        <div>
          <Grid g={g.map((r) => r.map((v) => Math.round((quant(v / 255, bits) / (2 ** bits - 1)) * 255)))} sel={sel} cell={(v, i, s) => (
            <g><rect x={4} y={s / 2 - 9} width={s - 8} height={18} rx={3} fill="#0f172add" /><text x={s / 2} y={s / 2 + 4} textAnchor="middle" fontSize={bits === 8 ? 8.5 : 12} fontFamily="monospace" fill={AMBER}>{quant(flat[i] / 255, bits).toString(2).padStart(bits, '0')}</text></g>)} />
          <Lab t={`NEQR ${bits}-bit`} sub={`${2 ** bits} shades`} />
          <div className="mt-1 flex justify-center gap-1">{([2, 4, 8] as const).map((b) => <button key={b} type="button" onClick={() => setBits(b)} className={`rounded px-1.5 py-0.5 text-[11px] ring-1 ${bits === b ? 'bg-amber-400/15 text-amber-100 ring-amber-400/50' : 'text-slate-400 ring-slate-700'}`}>{b}</button>)}</div>
        </div>
        <div className="space-y-1.5 pt-2 text-xs">
          <div className="rounded-lg bg-slate-950/60 px-3 py-2 ring-1 ring-slate-800"><div className="text-[10px] uppercase tracking-wider text-slate-500">FRQI qubits (4×4 padded)</div><div className="text-lg font-semibold text-white">5</div></div>
          <div className="rounded-lg bg-slate-950/60 px-3 py-2 ring-1 ring-slate-800"><div className="text-[10px] uppercase tracking-wider text-slate-500">NEQR qubits</div><div className="text-lg font-semibold" style={{ color: AMBER }}>{4 + bits}</div></div>
          <div className="flex gap-1"><ExplainThis id="frqi" /><ExplainThis id="neqr" /></div>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="space-y-3 rounded-xl bg-slate-950/40 p-4 ring-1 ring-slate-800">
          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
            PCA components <input type="range" min={1} max={4} value={k} onChange={(e) => setK(+e.target.value)} className="w-24 accent-teal-400" aria-label="PCA components" /> <b className="text-white">{k}</b> → {k} qubits
            <ExplainThis id="pca" />
          </div>
          {q ? (<>
            <div className="flex items-end gap-1.5">{q.p.ratio.map((r, i) => (
              <div key={i} className="text-center"><div className="mx-auto w-8 rounded-t bg-teal-500/70" style={{ height: `${Math.max(3, 70 * r)}px` }} /><div className="text-[10px] text-slate-400">PC{i + 1}<br />{(100 * r).toFixed(0)}%</div></div>))}
              <div className="ml-3 text-[11px] text-slate-500">variance kept per component</div></div>
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">feature map
              {FM.map(([f, l]) => <button key={f} type="button" onClick={() => setFmap(f)} className={`rounded-md px-2 py-0.5 ring-1 ${fmap === f ? 'bg-teal-500/15 text-teal-100 ring-teal-500/40' : 'ring-slate-700 hover:text-slate-200'}`}>{l}</button>)}
              <ExplainThis id={fmap === 'product_ry' ? 'product-ry' : fmap === 'zz_linear' ? 'zz-linear' : 'zz-full'} />
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-400">bandwidth
              {[0.25, 0.5, 1].map((b) => <button key={b} type="button" onClick={() => setBw(b)} className={`rounded-md px-2 py-0.5 ring-1 ${bw === b ? 'bg-teal-500/15 text-teal-100 ring-teal-500/40' : 'ring-slate-700'}`}>{b}</button>)}
            </div>
            <MiniCircuit gates={featureMapGates(q.ang[0], fmap)} n={k} />
            <div className="text-[11px] text-slate-500"><Lv beginner="Your image’s circuit: the angles come from your pixels." technical={`x = ${bw}·MinMax[0,π](PCA_${k}(pixels/255)); ${fmap === 'product_ry' ? 'U(x) = ⊗ RY(xᵢ)' : `H⊗ᵏ · P(2xᵢ) · CX·P(2(π−xᵢ)(π−xⱼ))·CX on ${fmap === 'zz_full' ? 'all pairs' : 'neighbours'}`}`} /></div>
          </>) : <div className="text-sm text-slate-400">{refs && !refs.length ? 'Could not load the reference images (is the backend running?).' : 'Loading 6 reference images…'}</div>}
        </div>
        <div className="space-y-3 rounded-xl bg-slate-950/40 p-4 ring-1 ring-slate-800">
          <div className="flex items-center gap-2 text-xs text-slate-400">kernel similarity |⟨φ(x)|φ(y)⟩|² <ExplainThis id="kernel-matrix" /></div>
          {q && (<>
            <Heatmap m={q.K} labels={['You', ...SHORT]} />
            <div className="space-y-1">{SHORT.map((c, i) => (
              <div key={c} className="grid grid-cols-[4.5rem_minmax(0,1fr)_3rem] items-center gap-2 text-xs"><span className="text-slate-400">{c}</span>
                <div className="h-2 rounded-full bg-slate-800"><div className="h-2 rounded-full bg-teal-400 transition-all duration-300" style={{ width: `${100 * q.K[0][i + 1]}%` }} /></div><span className="tabular-nums text-slate-300">{q.K[0][i + 1].toFixed(3)}</span></div>))}</div>
          </>)}
        </div>
      </div>
    </div>
  );
}
