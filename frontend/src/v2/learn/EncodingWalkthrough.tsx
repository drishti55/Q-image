// Step-by-step, animated construction of the FRQI and NEQR circuits on a real NEU-DET training image, gate by gate,
// with the quantum state updating live. Circuit structure follows src/frqi/encoder.py and src/neqr/encoder.py exactly
// (H on position qubits; per pixel: X on 0-bits, multi-controlled RY / MCX, undo X). Maths runs in the browser.
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Shuffle } from 'lucide-react';
import { StepControls, useStepper } from '../playground/widgets';
import { encoderGateCounts, log2, posBits, quant, rng, theta, useGray, useProgress } from './lab';
import type { Img } from './lab';
import { Lv } from '../level';

type Rep = 'FRQI' | 'NEQR';
const CLASSES = ['crazing', 'inclusion', 'patches', 'pitted_surface', 'rolled-in_scale', 'scratches'];
const NAMES = ['Crazing', 'Inclusion', 'Patches', 'Pitted surface', 'Rolled-in scale', 'Scratches'];
const BLUE = '#3987e5', ORANGE = '#d95926', TEAL = '#5eead4', AMBER = '#fbbf24', WIRE = '#475569';
const clamp = (v: number) => Math.max(0, Math.min(1, v));
const Big = ({ children }: { children: React.ReactNode }) => <p className="max-w-xl text-[15px] leading-relaxed text-slate-200">{children}</p>;

function Px({ a, size, active, label, overlay }: { a: Img; size: number; active?: number | null; label?: string; overlay?: (i: number, v: number, cell: number) => React.ReactNode }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const cv = ref.current; if (!cv) return;
    const n = a.length; cv.width = n; cv.height = n;
    const ctx = cv.getContext('2d'); if (!ctx) return;
    const im = ctx.createImageData(n, n);
    a.forEach((r, y) => r.forEach((v, x) => { const g = Math.round(clamp(v) * 255); im.data.set([g, g, g, 255], (y * n + x) * 4); }));
    ctx.putImageData(im, 0, 0);
  }, [a]);
  const n = a.length, cell = size / n;
  return (
    <figure className="inline-block">
      <div className="relative" style={{ width: size, height: size }}>
        <canvas ref={ref} style={{ width: size, height: size, imageRendering: 'pixelated' }} className="rounded-md ring-1 ring-slate-700" />
        <svg className="absolute inset-0" viewBox={`0 0 ${size} ${size}`} width={size} height={size}>
          {a.flat().map((v, i) => (
            <g key={i}>
              {overlay?.(i, v, cell)}
              <text x={(i % n) * cell + 5} y={Math.floor(i / n) * cell + 13} fontSize={10} fill={v > 0.55 ? '#0f172a' : '#94a3b8'}>{i}</text>
              {active === i && <rect x={(i % n) * cell + 1.5} y={Math.floor(i / n) * cell + 1.5} width={cell - 3} height={cell - 3} fill="none" stroke={TEAL} strokeWidth={3} rx={3} />}
            </g>))}
        </svg>
      </div>
      {label && <figcaption className="mt-1 text-center text-[11px] text-slate-400">{label}</figcaption>}
    </figure>
  );
}

/** Circuit diagram: position wires on top, colour wire(s) below. Filled control = position bit 1, open = bit 0
 *  (an open control is the encoder's X … X sandwich). Column 0 = Hadamards; then one column per encoded pixel. */
function Circuit({ rep, a, q, hActive, pix, all }: { rep: Rep; a: Img; q: number; hActive: number; pix: number | null; all?: boolean }) {
  const v = a.flat(), nPos = 2 * log2(a.length);
  const codes = v.map((x) => quant(x, q));
  const cols = v.map((x, i) => i).filter((i) => (rep === 'FRQI' ? Math.abs(Math.PI * v[i]) >= 1e-10 : codes[i] > 0));
  const wires = [...Array.from({ length: nPos }, (_, b) => `pos q${b}`), ...(rep === 'FRQI' ? ['colour'] : Array.from({ length: q }, (_, k) => `bit ${q - 1 - k}`))];
  const WY = 26, LX = 62, CW = 34, Y = (w: number) => 16 + w * WY, W = LX + 40 + cols.length * CW + 20, H = Y(wires.length - 1) + 18;
  return (
    <div className="overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} role="img" aria-label={`${rep} encoder circuit`} data-testid="enc-circuit">
        {wires.map((w, k) => (
          <g key={w}><text x={LX - 8} y={Y(k) + 4} textAnchor="end" fontSize={10} fill={k < nPos ? '#94a3b8' : rep === 'FRQI' ? ORANGE : AMBER}>{w}</text>
            <line x1={LX} x2={W - 10} y1={Y(k)} y2={Y(k)} stroke={WIRE} /></g>))}
        {Array.from({ length: nPos }, (_, b) => (
          <g key={b} opacity={0.35 + 0.65 * hActive}>
            <rect x={LX + 8} y={Y(b) - 10} width={20} height={20} rx={3} fill={hActive > 0 ? '#134e4a' : '#1e293b'} stroke={TEAL} />
            <text x={LX + 18} y={Y(b) + 4} textAnchor="middle" fontSize={11} fontWeight={700} fill={TEAL}>H</text>
          </g>))}
        {cols.map((i, c) => {
          const x = LX + 52 + c * CW, on = pix === i, bits = posBits(i, nPos), done = all || (pix != null && cols.indexOf(pix) > c);
          const targets = rep === 'FRQI' ? [nPos] : Array.from({ length: q }, (_, k) => k).filter((k) => (codes[i] >> (q - 1 - k)) & 1).map((k) => nPos + k);
          const op = on ? 1 : done ? 0.75 : 0.25, col = rep === 'FRQI' ? ORANGE : AMBER;
          return (
            <g key={i} opacity={op}>
              {on && <rect x={x - 14} y={2} width={28} height={H - 4} rx={4} fill="#14b8a610" stroke="#14b8a640" />}
              <line x1={x} x2={x} y1={Y(0)} y2={Y(Math.max(...targets))} stroke={col} strokeWidth={1.5} />
              {bits.map((bt, b) => <circle key={b} cx={x} cy={Y(b)} r={4.5} fill={bt ? col : '#0f172a'} stroke={col} strokeWidth={1.5} />)}
              {rep === 'FRQI'
                ? <g><rect x={x - 12} y={Y(nPos) - 10} width={24} height={20} rx={3} fill="#0f172a" stroke={col} /><text x={x} y={Y(nPos) + 4} textAnchor="middle" fontSize={9} fontWeight={700} fill={col}>RY</text></g>
                : targets.map((w) => <g key={w}><circle cx={x} cy={Y(w)} r={7} fill="#0f172a" stroke={col} strokeWidth={1.5} /><line x1={x - 7} x2={x + 7} y1={Y(w)} y2={Y(w)} stroke={col} /><line x1={x} x2={x} y1={Y(w) - 7} y2={Y(w) + 7} stroke={col} /></g>)}
              <text x={x} y={H - 2} textAnchor="middle" fontSize={9} fill="#64748b">px {i}</text>
            </g>);
        })}
      </svg>
    </div>
  );
}

function FrqiState({ a, h, rot }: { a: Img; h: number; rot: (i: number) => number }) {
  const v = a.flat(), N = v.length, W = 460, H = 150, gw = W / N, bw = Math.min(14, gw / 2 - 2);
  // before H: all amplitude on |pos 0, colour 0⟩; H spreads it evenly; rotation moves each pixel's share to colour 1
  return (
    <svg viewBox={`0 0 ${W} ${H + 22}`} className="w-full max-w-[480px]" role="img" aria-label="FRQI state amplitudes" data-testid="enc-state">
      <line x1={0} x2={W} y1={H} y2={H} stroke="#334155" />
      {v.map((x, i) => {
        const spread = i === 0 ? 1 - h + h / Math.sqrt(N) : h / Math.sqrt(N);
        const th = theta(x) * rot(i), a0 = spread * Math.cos(th), a1 = spread * Math.sin(th), cx = i * gw + gw / 2;
        return (
          <g key={i}>
            <rect x={cx - bw - 1} y={H - a0 * H} width={bw} height={a0 * H} rx={2} fill={BLUE} />
            <rect x={cx + 1} y={H - a1 * H} width={bw} height={a1 * H} rx={2} fill={ORANGE} />
            {N <= 16 && <text x={cx} y={H + 12} textAnchor="middle" fontSize={9} fill="#64748b">{i}</text>}
          </g>);
      })}
      <text x={0} y={H + 21} fontSize={10} fill={BLUE}>■ colour |0⟩ (cos θ)</text>
      <text x={W} y={H + 21} textAnchor="end" fontSize={10} fill={ORANGE}>■ colour |1⟩ (sin θ)</text>
    </svg>
  );
}

function NeqrState({ a, q, h, set }: { a: Img; q: number; h: number; set: (i: number) => number }) {
  const v = a.flat(), N = v.length, nPos = 2 * log2(a.length);
  return (
    <div className={`grid gap-1 ${N > 4 ? 'sm:grid-cols-2' : ''}`} data-testid="enc-state">
      {v.map((x, i) => {
        const amp = i === 0 ? 1 - h + h / Math.sqrt(N) : h / Math.sqrt(N), code = quant(x, q), k = set(i);
        const bits = code.toString(2).padStart(q, '0').split('').map((b, j) => (j < Math.round(k * q) ? b : '0'));
        return (
          <div key={i} className="flex items-center gap-2 font-mono text-[12px]" style={{ opacity: 0.25 + 0.75 * Math.min(1, amp * Math.sqrt(N)) }}>
            <span className="w-14 text-right tabular-nums text-slate-500">P {(amp * amp).toFixed(2)}</span>
            <span className="text-slate-400">|{i.toString(2).padStart(nPos, '0')}⟩</span>
            <span style={{ color: AMBER }}>|{bits.join('')}⟩</span>
            <span className="h-2 w-40 rounded-full bg-slate-800"><span className="block h-2 rounded-full" style={{ width: `${Math.min(100, 100 * amp * amp)}%`, background: AMBER }} /></span>
          </div>);
      })}
    </div>
  );
}

export default function EncodingWalkthrough() {
  const [rep, setRep] = useState<Rep>('FRQI');
  const [cls, setCls] = useState(5), [idx, setIdx] = useState(0);
  const [N, setN] = useState<2 | 4>(2), [q, setQ] = useState<2 | 4>(4);
  const [step, setStep] = useState(0);
  const g = useGray(`/api/v2/dataset/sample/${CLASSES[cls]}.png?n=${idx}`, N);
  const a = g.img;
  const STEPS = rep === 'FRQI'
    ? ['Pixels become angles', 'All qubits start at |0⟩', 'Hadamard: every position at once', 'Controlled rotations paint each pixel', 'Read it back', 'FRQI vs NEQR']
    : ['Pixels become bits', 'All qubits start at |0⟩', 'Hadamard: every position at once', 'Controlled-NOTs write each pixel’s bits', 'Read it back', 'FRQI vs NEQR'];
  const MS = [1600, 900, 1500, N === 2 ? 4800 : 11200, 1500, 1200];
  const { playing, setPlaying } = useStepper(STEPS.length, step, setStep, MS[step] + 1800);
  const t = useProgress(`${rep}:${step}:${N}:${q}:${cls}:${idx}`, MS[step]);
  const reset = (f: () => void) => { f(); setStep(0); setPlaying(false); };
  const nPos = 2 * log2(N);
  const counts = useMemo(() => (a ? encoderGateCounts(a, q) : null), [a, q]);
  const pix = step === 3 ? Math.min(N * N - 1, Math.floor(t * N * N)) : null;
  const rot = (i: number) => (step < 3 ? 0 : step > 3 ? 1 : clamp(t * N * N - i));
  const h = step < 2 ? 0 : step === 2 ? t : 1;
  const btn = (on: boolean) => `rounded-md px-2.5 py-1 ring-1 ${on ? 'bg-teal-500/15 text-teal-100 ring-teal-500/40' : 'text-slate-400 ring-slate-700 hover:text-slate-200'}`;

  return (
    <div className="space-y-4" data-testid="enc-walkthrough" data-step={step}>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <div className="mr-2 flex rounded-lg bg-slate-900 p-0.5 ring-1 ring-slate-700" role="radiogroup" aria-label="Representation">
          {(['FRQI', 'NEQR'] as Rep[]).map((r) => (
            <button key={r} type="button" role="radio" aria-checked={rep === r} onClick={() => reset(() => setRep(r))}
              className={`rounded-md px-4 py-1.5 text-sm font-semibold ${rep === r ? (r === 'FRQI' ? 'bg-orange-500/20 text-orange-200' : 'bg-amber-400/20 text-amber-200') : 'text-slate-400'}`}>{r}</button>))}
        </div>
        {NAMES.map((n, i) => <button key={n} type="button" onClick={() => reset(() => setCls(i))} className={btn(cls === i)}>{n}</button>)}
        <button type="button" onClick={() => reset(() => setIdx((idx + 1) % 20))} className="inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-slate-300 ring-1 ring-slate-700"><Shuffle size={12} /> another</button>
        <span className="ml-auto flex items-center gap-1 text-slate-400">size {([2, 4] as const).map((s) => <button key={s} type="button" onClick={() => reset(() => setN(s))} className={btn(N === s)}>{s}×{s}</button>)}</span>
        {rep === 'NEQR' && <span className="flex items-center gap-1 text-slate-400">bits {([2, 4] as const).map((s) => <button key={s} type="button" onClick={() => reset(() => setQ(s))} className={btn(q === s)}>{s}</button>)}</span>}
      </div>
      <StepControls step={step} n={STEPS.length} setStep={setStep} playing={playing} setPlaying={setPlaying} title={`${rep} · ${STEPS[step]}`} />
      <div className="min-h-[330px]">
        {g.err ? <div className="text-sm text-amber-300">Could not load the image. Is the backend running?</div> : !a || !counts ? <div className="text-sm text-slate-400">Loading image…</div> : (
          step === 5 ? <Compare a={a} q={q} counts={counts} /> : (
            <div className="flex flex-wrap items-start gap-6">
              <Px a={a} size={200} active={pix} label={`${NAMES[cls]} · ${N}×${N}, contrast-stretched`}
                overlay={step === 0 ? (i, v, cell) => {
                  const show = clamp(t * N * N * 1.2 - i);
                  const cx = (i % N) * cell + cell / 2, cy = Math.floor(i / N) * cell + cell / 2;
                  return show > 0 && (rep === 'FRQI'
                    ? <g opacity={show}><circle cx={cx} cy={cy + 4} r={cell * 0.3} fill="#0f172acc" /><line x1={cx} y1={cy + 4} x2={cx + cell * 0.3 * Math.sin(theta(v) * show)} y2={cy + 4 - cell * 0.3 * Math.cos(theta(v) * show)} stroke={ORANGE} strokeWidth={3} strokeLinecap="round" />
                      <text x={cx} y={cy + cell * 0.45} textAnchor="middle" fontSize={11} fill="#f8fafc">{(theta(v) * 180 / Math.PI).toFixed(0)}°</text></g>
                    : <g opacity={show}><rect x={cx - cell * 0.4} y={cy - 9} width={cell * 0.8} height={22} rx={4} fill="#0f172add" /><text x={cx} y={cy + 6} textAnchor="middle" fontSize={N === 2 ? 16 : 12} fontFamily="monospace" fill={AMBER}>{quant(v, q).toString(2).padStart(q, '0')}</text></g>);
                } : undefined} />
              <div className="min-w-0 flex-1 space-y-3">
                <Big><Lv beginner={caption(rep, step, nPos, q, N)} technical={techCaption(rep, step, nPos, q, N)} /></Big>
                {step >= 1 && <Circuit rep={rep} a={a} q={q} hActive={step === 1 ? 0 : step === 2 ? t : 1} pix={pix} all={step >= 4} />}
                {step >= 1 && (rep === 'FRQI' ? <FrqiState a={a} h={h} rot={rot} /> : <NeqrState a={a} q={q} h={h} set={rot} />)}
                {step === 4 && <ReadBack rep={rep} a={a} q={q} />}
              </div>
            </div>)
        )}
      </div>
      <p className="text-[11px] text-slate-500">Same circuit structure as the project’s encoders (src/frqi/encoder.py, src/neqr/encoder.py). An open control dot = the X … X pair the encoder puts around a position bit that is 0. Maths in your browser on real pixels.</p>
    </div>
  );
}

function caption(rep: Rep, step: number, nPos: number, q: number, N: number) {
  if (rep === 'FRQI') return [
    <>Each pixel’s brightness becomes an <b>angle</b>: black = 0°, white = 90°.</>,
    <>{nPos} <b>position</b> qubits (which pixel) + 1 <b>colour</b> qubit (how bright). Everything starts at |0⟩.</>,
    <>Hadamards put the position qubits into <b>all {N * N} positions at once</b>, each with equal weight.</>,
    <>For each pixel, a rotation fires <b>only at that position</b> and turns the colour qubit by its angle: weight moves from <span style={{ color: BLUE }}>blue</span> to <span style={{ color: ORANGE }}>orange</span>. Black pixels need no gate.</>,
    <>The whole image now lives in {nPos + 1} qubits. Measuring gives P(orange) / P(blue) per pixel → the angle → the brightness.</>,
  ][step];
  return [
    <>Each pixel’s brightness is rounded to a <b>{q}-bit number</b> ({2 ** q} shades).</>,
    <>{nPos} <b>position</b> qubits + {q} <b>colour</b> qubits (one per bit). Everything starts at |0⟩.</>,
    <>Hadamards put the position qubits into <b>all {N * N} positions at once</b>.</>,
    <>For each pixel, a controlled-NOT flips a colour qubit <b>only at that position</b> — once for every 1-bit of its code. Pixels with code 0 need no gate.</>,
    <>Each measurement returns one position and its <b>exact</b> bits. No angles to estimate.</>,
  ][step];
}

function techCaption(rep: Rep, step: number, nPos: number, q: number, N: number) {
  const f = (t: string) => <span className="font-mono text-[14px] text-teal-200">{t}</span>;
  if (rep === 'FRQI') return [
    <>{f('θᵢ = (π/2)·xᵢ')} — the encoder applies {f('RY(2θᵢ)')} so the colour qubit becomes cos θᵢ|0⟩ + sin θᵢ|1⟩.</>,
    <>{f(`|0⟩^⊗${nPos + 1}`)}: {nPos} = 2·log₂{N} position qubits + 1 colour qubit.</>,
    <>{f(`H^⊗${nPos}|0⟩ = (1/${N}) Σᵢ |i⟩`)} — uniform superposition over {N * N} positions.</>,
    <>Per pixel i: {f('X^(0-bits of i) · C^' + nPos + '-RY(2θᵢ) · X^(0-bits of i)')}; black pixels (θ = 0) skipped.</>,
    <>{f('|I⟩ = (1/N) Σᵢ (cos θᵢ|0⟩ + sin θᵢ|1⟩)|i⟩')}; decode {f('θᵢ = atan √(P(1,i)/P(0,i))')}.</>,
  ][step];
  return [
    <>{f(`Cᵢ = round(xᵢ·(2^${q} − 1))`)} (half to even, as np.round).</>,
    <>{f(`|0⟩^⊗${nPos + q}`)}: {nPos} position qubits + {q} colour qubits.</>,
    <>{f(`H^⊗${nPos}|0⟩ = (1/${N}) Σᵢ |i⟩|0…0⟩`)}.</>,
    <>Per pixel i, per 1-bit b of Cᵢ: {f('X^(0-bits of i) · C^' + nPos + '-X on bit b · X^(0-bits of i)')}.</>,
    <>{f('|I⟩ = (1/N) Σᵢ |Cᵢ⟩|i⟩')}; one shot returns (i, Cᵢ) exactly.</>,
  ][step];
}

function ReadBack({ rep, a, q }: { rep: Rep; a: Img; q: number }) {
  const v = a.flat(), N = v.length;
  if (rep === 'FRQI') return (
    <div className="flex flex-wrap gap-1.5 text-[11px]">
      {v.map((x, i) => { const p1 = Math.sin(theta(x)) ** 2 / N, p0 = Math.cos(theta(x)) ** 2 / N, back = (2 / Math.PI) * Math.atan(Math.sqrt(p1 / (p0 || 1e-12)));
        return <span key={i} className="rounded bg-slate-900 px-1.5 py-0.5 font-mono text-slate-300 ring-1 ring-slate-800">px{i}: {back.toFixed(2)}</span>; })}
      <span className="text-slate-500">← brightness recovered exactly from the state</span>
    </div>);
  const r = rng(7), shots = Array.from({ length: 8 }, () => Math.floor(r() * N));
  return (
    <div className="flex flex-wrap gap-1.5 text-[11px]">
      {shots.map((i, k) => <span key={k} className="rounded bg-slate-900 px-1.5 py-0.5 font-mono ring-1 ring-slate-800"><span className="text-slate-400">shot {k + 1}: px{i} →</span> <span style={{ color: AMBER }}>{quant(v[i], q).toString(2).padStart(q, '0')}</span></span>)}
      <Link to="/learn" className="text-teal-300 hover:underline">try shots on the Learn page →</Link>
    </div>);
}

function Compare({ a, q, counts }: { a: Img; q: number; counts: ReturnType<typeof encoderGateCounts> }) {
  const rows = [
    { k: 'Qubits', f: counts.frqi.qubits, n: counts.neqr.qubits },
    { k: 'Controlled gates', f: counts.frqi.controlled, n: counts.neqr.controlled },
    { k: 'X gates', f: counts.frqi.x, n: counts.neqr.x },
  ];
  return (
    <div className="space-y-4">
      <Big>Same {a.length}×{a.length} image, two encodings. FRQI is <b>smaller</b>; NEQR is <b>exact</b> to {q} bits but needs more qubits and many more controlled gates.</Big>
      <div className="grid gap-4 md:grid-cols-3">
        {rows.map((r) => { const mx = Math.max(r.f, r.n, 1); return (
          <div key={r.k} className="rounded-xl bg-slate-950/50 p-4 ring-1 ring-slate-800">
            <div className="mb-2 text-[11px] uppercase tracking-wider text-slate-500">{r.k}</div>
            {([['FRQI', r.f, ORANGE], [`NEQR ${q}-bit`, r.n, AMBER]] as const).map(([lab, val, col]) => (
              <div key={lab} className="mb-1.5 flex items-center gap-2 text-xs"><span className="w-20 text-slate-300">{lab}</span>
                <div className="h-4 flex-1 rounded bg-slate-800"><div className="h-4 rounded" style={{ width: `${(100 * val) / mx}%`, background: col }} /></div>
                <span className="w-8 text-right font-semibold tabular-nums text-white">{val}</span></div>))}
          </div>); })}
      </div>
      <p className="text-xs text-slate-500">Logical gates for this image, counted the way the project’s encoders build them (each multi-controlled gate expands into many CNOTs on real hardware — see the compiled counts below).</p>
    </div>
  );
}
