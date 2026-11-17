// "How it works": animated, step-by-step walkthrough of the frozen Protocol V4 FRQI model on ONE real locked-test image.
// Every number shown comes from /api/v4 (real image, real frozen checkpoint, real saved predictions, real
// reconstruction records). The live prediction is checked against the prediction saved by the single locked-test run.
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { CheckCircle2, Shuffle, XCircle, Flame } from 'lucide-react';
import { useV4 } from '../api';
import { Card, PageHeader, Gate, Badge } from '../ui';
import { CLASS_COLORS, CLASS_NAMES, StepControls, useStepper } from '../playground/widgets';

type Pipe = {
  image: string; y_true: number; classes: string[]; model_group: string; experiment_id: string; params: any; n_qubits_per_patch: number;
  original128: number[][]; resized: number[][]; stretched: number[][]; patch_grid: { n: number; per_side: number; patch: number; stride: number };
  theta: number[][]; state_dim: number;
  kernel: { top: { train_image: string; class: string; similarity: number; thumb: number[][] }[]; class_mean: Record<string, number>; n_train: number };
  svm: { decision: number[]; n_support: number }; prediction: number; saved_prediction: number; matches_saved_prediction: boolean;
};

const reduced = () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

/** 0 -> 1 over `ms` each time `key` changes (instantly 1 with reduced motion). */
function useProgress(key: string, ms: number, speed: number) {
  const [t, setT] = useState(0);
  useEffect(() => {
    if (reduced()) { setT(1); return; }
    let raf = 0;
    const t0 = performance.now();
    const tick = (now: number) => {
      const v = Math.max(0, Math.min(1, ((now - t0) * speed) / ms)); // rAF timestamps can precede t0
      setT(v);
      if (v < 1) raf = requestAnimationFrame(tick);
    };
    setT(0);
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [key, ms, speed]);
  return t;
}

function Gray({ data, size, children, label }: { data: number[][]; size: number; children?: ReactNode; label?: ReactNode }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const cv = ref.current;
    if (!cv || !data?.length) return;
    const h = data.length, w = data[0].length;
    cv.width = w; cv.height = h;
    const ctx = cv.getContext('2d');
    if (!ctx) return;
    const img = ctx.createImageData(w, h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const g = Math.round(Math.max(0, Math.min(1, data[y][x])) * 255), i = (y * w + x) * 4;
      img.data[i] = g; img.data[i + 1] = g; img.data[i + 2] = g; img.data[i + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);
  }, [data]);
  return (
    <figure className="inline-block">
      <div className="relative" style={{ width: size, height: size }}>
        <canvas ref={ref} style={{ width: size, height: size, imageRendering: 'pixelated' }} className="rounded-md ring-1 ring-slate-700" />
        {children && <svg className="pointer-events-none absolute inset-0" viewBox={`0 0 ${size} ${size}`} width={size} height={size}>{children}</svg>}
      </div>
      {label && <figcaption className="mt-1 text-center text-[11px] text-slate-400">{label}</figcaption>}
    </figure>
  );
}

function Explain({ what, why, children }: { what: ReactNode; why?: ReactNode; children?: ReactNode }) {
  return (
    <div className="space-y-2 text-sm leading-relaxed text-slate-300">
      <p>{what}</p>
      {why && <p className="text-slate-400"><span className="font-medium text-slate-200">Why: </span>{why}</p>}
      {children}
    </div>
  );
}

const Mono = ({ children }: { children: ReactNode }) => <code className="rounded bg-slate-800/80 px-1.5 py-0.5 font-mono text-[12px] text-cyan-200">{children}</code>;

// ─────────────────────────── stages ───────────────────────────
function StageImage({ d, t }: { d: Pipe; t: number }) {
  return (
    <div className="flex flex-wrap items-start gap-6">
      <div style={{ opacity: Math.min(1, t * 2), transform: `scale(${0.92 + 0.08 * Math.min(1, t * 2)})`, transition: 'none' }}>
        <Gray data={d.original128} size={256} label={<>{d.image.split('/').pop()} · true class <b style={{ color: CLASS_COLORS[d.y_true] }}>{CLASS_NAMES[d.y_true]}</b></>} />
      </div>
      <Explain what={<>A real steel-surface photo from the <b>locked test set</b> (the 360 images the model never saw during training or model selection).
        The original is 200 × 200 px; it is shown here at 128 × 128.</>}
        why="Everything on this page is computed for this one image by the frozen V4 model — pick another image at the top to see a different case." />
    </div>
  );
}

function StagePreprocess({ d, t }: { d: Pipe; t: number }) {
  const phase = t < 0.33 ? 0 : t < 0.66 ? 1 : 2;
  const items = [
    { data: d.original128, label: 'grayscale 128 × 128' },
    { data: d.resized, label: `resized ${d.params.image_size} × ${d.params.image_size}` },
    { data: d.stretched, label: 'per-image contrast stretch' },
  ];
  return (
    <div className="flex flex-wrap items-start gap-6">
      <div className="flex flex-wrap gap-4">
        {items.map((it, k) => (
          <div key={k} style={{ opacity: k <= phase ? 1 : 0.15, transition: 'opacity 400ms' }}>
            <Gray data={it.data} size={170} label={<span className={k === phase ? 'text-cyan-300' : ''}>{it.label}</span>} />
          </div>))}
      </div>
      <Explain what={<>Convert to gray values in [0, 1], resize to {d.params.image_size} × {d.params.image_size} (bilinear), then stretch the contrast
        using only this image&apos;s own minimum and maximum: <Mono>x → (x − min) / (max − min)</Mono>.</>}
        why="The stretch was chosen on validation. It removes brightness differences between the two photo folders, which made the old models fail on 'rolled-in scale'." />
    </div>
  );
}

function StagePatches({ d, t }: { d: Pipe; t: number }) {
  const { n, per_side, patch, stride } = d.patch_grid;
  const S = d.params.image_size, px = 256 / S;
  const k = Math.min(n - 1, Math.floor(t * n));
  const r = Math.floor(k / per_side), c = k % per_side;
  const patchData = d.stretched.slice(r * stride, r * stride + patch).map((row) => row.slice(c * stride, c * stride + patch));
  return (
    <div className="flex flex-wrap items-start gap-6">
      <Gray data={d.stretched} size={256} label={`${S} × ${S} image`}>
        {Array.from({ length: k }, (_, j) => {
          const rr = Math.floor(j / per_side), cc = j % per_side;
          return <rect key={j} x={cc * stride * px + 1} y={rr * stride * px + 1} width={2} height={2} fill="#22d3ee" opacity={0.5} />;
        })}
        <rect x={c * stride * px} y={r * stride * px} width={patch * px} height={patch * px} fill="none" stroke="#22d3ee" strokeWidth={2} />
      </Gray>
      <Gray data={patchData} size={140} label={<>patch {k + 1} / {n} (row {r}, col {c})</>} />
      <Explain what={<>Slide a {patch} × {patch} window across the image with stride {stride}: {per_side} × {per_side} = <b>{n} overlapping patches</b>.
        Each patch will become its own small quantum state.</>}
        why="Defects are textures. A kernel built from patches does not care where in the image a texture appears — the old FRQI kernel compared pixels at fixed positions, which is why it was stuck near 60 %." />
    </div>
  );
}

function FRQICircuit({ theta, i }: { theta: number[]; i: number }) {
  const nPos = Math.round(Math.log2(theta.length)), W = 560, rowH = 26, top = 18, left = 44;
  const wires = [...Array.from({ length: nPos }, (_, q) => `p${nPos - 1 - q}`), 'c'];
  const win = 9, start = Math.max(0, Math.min(theta.length - win, i - 4));
  const colW = (W - left - 60) / (win + 1);
  const y = (w: number) => top + w * rowH;
  return (
    <svg viewBox={`0 0 ${W} ${top + wires.length * rowH + 6}`} className="w-full max-w-[620px]" role="img" aria-label="FRQI encoding circuit">
      {wires.map((w, k) => (<g key={w}>
        <text x={6} y={y(k) + 4} fontSize={11} fill="#94a3b8" fontFamily="ui-monospace,monospace">{w === 'c' ? 'color' : w}</text>
        <line x1={left} x2={W - 8} y1={y(k)} y2={y(k)} stroke="#475569" />
      </g>))}
      {wires.slice(0, nPos).map((_, k) => (<g key={`h${k}`}>
        <rect x={left + 4} y={y(k) - 9} width={18} height={18} rx={3} fill="#0e7490" />
        <text x={left + 13} y={y(k) + 4} fontSize={10} fill="white" textAnchor="middle">H</text>
      </g>))}
      {Array.from({ length: win }, (_, j) => {
        const pix = start + j, x = left + colW * (j + 1) + 10, active = pix === i, done = pix < i;
        const bits = pix.toString(2).padStart(nPos, '0');
        const col = active ? '#22d3ee' : done ? '#64748b' : '#334155';
        return (<g key={pix} opacity={active ? 1 : done ? 0.85 : 0.5}>
          <line x1={x} x2={x} y1={y(0)} y2={y(nPos)} stroke={col} strokeWidth={active ? 2 : 1} />
          {bits.split('').map((b, q) => <circle key={q} cx={x} cy={y(q)} r={4.5} fill={b === '1' ? col : '#0b1220'} stroke={col} strokeWidth={1.5} />)}
          <rect x={x - 16} y={y(nPos) - 10} width={32} height={20} rx={3} fill={active ? '#0e7490' : '#1e293b'} stroke={col} />
          <text x={x} y={y(nPos) + 4} fontSize={8.5} fill="white" textAnchor="middle">RY</text>
          <text x={x} y={top - 6} fontSize={9} fill={active ? '#67e8f9' : '#64748b'} textAnchor="middle">i={pix}</text>
        </g>);
      })}
    </svg>
  );
}

function StageEncode({ d, t }: { d: Pipe; t: number }) {
  const kp = Math.floor(d.patch_grid.n / 2);
  const theta = d.theta[kp];
  const N = theta.length, i = Math.min(N - 1, Math.floor(t * N));
  const p = d.patch_grid.patch, per = d.patch_grid.per_side, st = d.patch_grid.stride;
  const r0 = Math.floor(kp / per) * st, c0 = (kp % per) * st;
  const patch = d.stretched.slice(r0, r0 + p).map((row) => row.slice(c0, c0 + p));
  const amp = theta.map((th) => [Math.cos(th) / Math.sqrt(N), Math.sin(th) / Math.sqrt(N)]);
  const pr = Math.floor(i / p), pc = i % p, cell = 140 / p;
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-start gap-6">
        <Gray data={patch} size={140} label={`patch ${kp + 1} — pixel i = ${i}`}>
          <rect x={pc * cell} y={pr * cell} width={cell} height={cell} fill="none" stroke="#22d3ee" strokeWidth={2} />
        </Gray>
        <div className="min-w-[240px] flex-1 space-y-1 font-mono text-[12px] text-slate-300">
          <div>pixel value x<sub>{i}</sub> = <b className="text-white">{patch[pr][pc].toFixed(3)}</b></div>
          <div>θ<sub>{i}</sub> = (π/2)·{d.params.angle_scale}·x = <b className="text-cyan-200">{theta[i].toFixed(3)}</b> rad</div>
          <div>amplitude on |0⟩|{i}⟩ = cos θ / {Math.sqrt(N)} = <b className="text-white">{amp[i][0].toFixed(4)}</b></div>
          <div>amplitude on |1⟩|{i}⟩ = sin θ / {Math.sqrt(N)} = <b className="text-white">{amp[i][1].toFixed(4)}</b></div>
          <div className="pt-1 text-slate-400">{Math.log2(N)} position qubits + 1 color qubit = <b className="text-slate-200">{d.n_qubits_per_patch} qubits</b></div>
        </div>
      </div>
      <FRQICircuit theta={theta} i={i} />
      <div>
        <div className="mb-1 text-[11px] text-slate-400">State vector being built (left half: |0⟩|i⟩ amplitudes, right half: |1⟩|i⟩) — {i + 1} / {N} pixels encoded</div>
        <svg viewBox={`0 0 ${2 * N * 4} 60`} className="h-16 w-full" preserveAspectRatio="none">
          <line x1={0} x2={2 * N * 4} y1={30} y2={30} stroke="#334155" />
          {amp.map(([a0, a1], k) => k <= i && (<g key={k}>
            <rect x={k * 4} width={3} y={a0 >= 0 ? 30 - a0 * 30 * Math.sqrt(N) * 0.9 : 30} height={Math.abs(a0) * 30 * Math.sqrt(N) * 0.9} fill={k === i ? '#22d3ee' : '#3987e5'} />
            <rect x={(N + k) * 4} width={3} y={a1 >= 0 ? 30 - a1 * 30 * Math.sqrt(N) * 0.9 : 30} height={Math.abs(a1) * 30 * Math.sqrt(N) * 0.9} fill={k === i ? '#22d3ee' : '#c98500'} />
          </g>))}
        </svg>
      </div>
      <Explain what={<>FRQI puts the pixel position in superposition with Hadamard gates, then for every pixel a rotation <Mono>RY(2θᵢ)</Mono>, controlled on the
        position register being |i⟩, writes the brightness into the color qubit. The result:
        <Mono>|ψ⟩ = (1/{Math.sqrt(N)}) Σᵢ (cos θᵢ|0⟩ + sin θᵢ|1⟩)|i⟩</Mono>.</>}
        why="Filled dots = control on |1⟩, open dots = control on |0⟩ — the pattern is the binary index of the pixel. This is the same FRQI encoder circuit used throughout the project (src/frqi/encoder.py)." />
    </div>
  );
}

function RhoCanvas({ theta, k }: { theta: number[][]; k: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const acc = useRef<{ rho: Float64Array; k: number } | null>(null);
  const N = theta[0].length, D = 2 * N;
  const [purity, setPurity] = useState(0);
  useEffect(() => {
    if (!acc.current || acc.current.k > k) acc.current = { rho: new Float64Array(D * D), k: 0 };
    const a = acc.current;
    const psi = new Float64Array(D);
    for (; a.k < k; a.k++) {
      const th = theta[a.k];
      for (let i = 0; i < N; i++) { psi[i] = Math.cos(th[i]) / Math.sqrt(N); psi[N + i] = Math.sin(th[i]) / Math.sqrt(N); }
      for (let i = 0; i < D; i++) { const pi = psi[i]; if (pi === 0) continue; const row = i * D; for (let j = 0; j < D; j++) a.rho[row + j] += pi * psi[j]; }
    }
    const cv = ref.current;
    if (!cv || k === 0) return;
    cv.width = D; cv.height = D;
    const ctx = cv.getContext('2d');
    if (!ctx) return;
    let mx = 1e-12, pur = 0;
    for (let q = 0; q < D * D; q++) { const v = a.rho[q] / k; mx = Math.max(mx, Math.abs(v)); pur += v * v; }
    setPurity(pur);
    const img = ctx.createImageData(D, D);
    for (let q = 0; q < D * D; q++) {
      const v = a.rho[q] / k / mx, o = q * 4;
      if (v >= 0) { img.data[o] = 15 + 210 * v; img.data[o + 1] = 23 + 110 * v; img.data[o + 2] = 42; }
      else { img.data[o] = 15; img.data[o + 1] = 23 + 120 * -v; img.data[o + 2] = 42 + 200 * -v; }
      img.data[o + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);
  }, [theta, k, N, D]);
  return (
    <figure className="inline-block">
      <canvas ref={ref} style={{ width: 256, height: 256, imageRendering: 'pixelated' }} className="rounded-md bg-slate-900 ring-1 ring-slate-700" />
      <figcaption className="mt-1 text-center text-[11px] text-slate-400">ρ after {k} patch states · purity Tr(ρ²) = {purity.toFixed(4)}</figcaption>
    </figure>
  );
}

function StageMix({ d, t }: { d: Pipe; t: number }) {
  const k = Math.max(1, Math.round(t * d.patch_grid.n));
  return (
    <div className="flex flex-wrap items-start gap-6">
      <RhoCanvas theta={d.theta} k={k} />
      <Explain what={<>Each of the {d.patch_grid.n} patch states |ψₖ⟩ is a {d.state_dim}-dimensional vector. The image becomes the <b>mixed state</b>
        <Mono>ρ = (1/{d.patch_grid.n}) Σₖ |ψₖ⟩⟨ψₖ|</Mono> — physically, "prepare the FRQI state of a randomly chosen patch".
        The {d.state_dim} × {d.state_dim} matrix on the left is being summed patch by patch (orange = positive, blue = negative entries).</>}
        why="Averaging over patches throws away *where* each patch was and keeps *what textures* the image contains. Purity Tr(ρ²) drops as more different patches are mixed in." />
    </div>
  );
}

function SwapTest({ t }: { t: number }) {
  const x = 30 + t * 380;
  return (
    <svg viewBox="0 0 440 120" className="w-full max-w-[460px]" role="img" aria-label="swap test circuit">
      {[['ancilla', 20], ['ρ (this image)', 60], ['σ (train image)', 100]].map(([l, y]) => (<g key={l as string}>
        <text x={2} y={(y as number) - 6} fontSize={9} fill="#94a3b8">{l}</text>
        <line x1={20} x2={430} y1={y as number} y2={y as number} stroke="#475569" />
      </g>))}
      <rect x={70} y={10} width={20} height={20} rx={3} fill="#0e7490" /><text x={80} y={24} fontSize={10} fill="white" textAnchor="middle">H</text>
      <line x1={180} x2={180} y1={20} y2={100} stroke="#94a3b8" /><circle cx={180} cy={20} r={4.5} fill="#94a3b8" />
      {[60, 100].map((y) => <g key={y}><line x1={174} x2={186} y1={y - 6} y2={y + 6} stroke="#e2e8f0" strokeWidth={2} /><line x1={174} x2={186} y1={y + 6} y2={y - 6} stroke="#e2e8f0" strokeWidth={2} /></g>)}
      <rect x={270} y={10} width={20} height={20} rx={3} fill="#0e7490" /><text x={280} y={24} fontSize={10} fill="white" textAnchor="middle">H</text>
      <rect x={350} y={8} width={30} height={24} rx={3} fill="#1e293b" stroke="#64748b" /><text x={365} y={24} fontSize={9} fill="#e2e8f0" textAnchor="middle">M</text>
      <circle cx={x} cy={60} r={4} fill="#22d3ee" opacity={0.8} /><circle cx={x} cy={100} r={4} fill="#c98500" opacity={0.8} />
    </svg>
  );
}

function StageKernel({ d, t }: { d: Pipe; t: number }) {
  const top = d.kernel.top;
  const mx = Math.max(...top.map((x) => x.similarity));
  const cm = d.kernel.class_mean, cmMax = Math.max(...Object.values(cm)), cmMin = Math.min(...Object.values(cm));
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start gap-6">
        <SwapTest t={t} />
        <Explain what={<>To compare this image with a training image, a <b>swap test</b> takes one copy of each state: <Mono>P(ancilla = 0) = ½ + ½ Tr(ρσ)</Mono>.
          Repeating it estimates the kernel <Mono>K = Tr(ρ_this ρ_train)</Mono>. Here it is computed exactly against all <b>{d.kernel.n_train}</b> training images.</>}
          why="Images with similar textures have overlapping mixed states, so their kernel value is high — whatever the position of the defect." />
      </div>
      <div>
        <div className="mb-2 text-xs font-medium text-slate-300">Most similar training images (normalised kernel)</div>
        <div className="flex flex-wrap gap-3">
          {top.map((x, k) => (
            <div key={x.train_image} className="w-[96px]" style={{ opacity: t > k / 8 ? 1 : 0.1, transition: 'opacity 300ms' }}>
              <Gray data={x.thumb} size={96} />
              <div className="mt-1 h-1.5 rounded-full bg-slate-800"><div className="h-1.5 rounded-full bg-cyan-400" style={{ width: `${(100 * x.similarity * Math.min(1, t * 1.4)) / mx}%` }} /></div>
              <div className="mt-0.5 text-[10px] text-slate-400"><span style={{ color: CLASS_COLORS[d.classes.indexOf(x.class)] }}>■</span> {CLASS_NAMES[d.classes.indexOf(x.class)]} · {x.similarity.toFixed(3)}</div>
            </div>))}
        </div>
      </div>
      <div>
        <div className="mb-2 text-xs font-medium text-slate-300">Average similarity to each class of training images</div>
        <div className="space-y-1">{d.classes.map((c, j) => {
          const w = ((cm[c] - cmMin) / Math.max(1e-9, cmMax - cmMin)) * 85 + 15;
          return (<div key={c} className="flex items-center gap-2 text-[11px]">
            <span className="w-28 text-slate-300">{CLASS_NAMES[j]}</span>
            <div className="h-3 flex-1 rounded bg-slate-800"><div className="h-3 rounded" style={{ width: `${w * Math.min(1, t * 1.3)}%`, background: CLASS_COLORS[j] }} /></div>
            <span className="w-12 text-right font-mono text-slate-400">{cm[c].toFixed(3)}</span>
          </div>);
        })}</div>
      </div>
    </div>
  );
}

function StageSVM({ d, t }: { d: Pipe; t: number }) {
  const dec = d.svm.decision, lo = Math.min(...dec), hi = Math.max(...dec);
  const right = d.prediction === d.y_true;
  return (
    <div className="space-y-4">
      <Explain what={<>A support-vector machine trained on the 1,080 × 1,080 kernel matrix (it kept <b>{d.svm.n_support}</b> training images as support vectors)
        turns the kernel values into one score per class. The highest score wins.</>} />
      <div className="space-y-1.5">{dec.map((v, j) => {
        const w = ((v - lo) / Math.max(1e-9, hi - lo)) * 85 + 10, win = j === d.prediction && t > 0.85;
        return (<div key={j} className="flex items-center gap-2 text-xs">
          <span className={`w-28 ${win ? 'font-semibold text-white' : 'text-slate-300'}`}>{CLASS_NAMES[j]}</span>
          <div className="h-4 flex-1 rounded bg-slate-800"><div className="h-4 rounded transition-[width]" style={{ width: `${w * Math.min(1, t * 1.25)}%`, background: CLASS_COLORS[j], boxShadow: win ? '0 0 0 2px #fff' : 'none' }} /></div>
          <span className="w-14 text-right font-mono text-slate-400">{v.toFixed(2)}</span>
        </div>);
      })}</div>
      {t > 0.85 && (
        <div className={`flex flex-wrap items-center gap-3 rounded-xl px-4 py-3 ring-1 ${right ? 'bg-emerald-500/10 ring-emerald-500/30' : 'bg-rose-500/10 ring-rose-500/30'}`} data-testid="hiw-verdict">
          {right ? <CheckCircle2 className="text-emerald-300" size={20} /> : <XCircle className="text-rose-300" size={20} />}
          <span className="text-sm text-slate-100">Predicted <b>{CLASS_NAMES[d.prediction]}</b> · true class <b>{CLASS_NAMES[d.y_true]}</b> — {right ? 'correct' : 'wrong'}</span>
          <Badge tone={d.matches_saved_prediction ? 'emerald' : 'rose'}>{d.matches_saved_prediction ? 'identical to the saved locked-test prediction' : 'DIFFERS from saved prediction'}</Badge>
        </div>)}
    </div>
  );
}

const SHOT_MODES = ['shots100', 'shots1000', 'shots10000', 'shots100000', 'statevector'];
function StageMeasure({ d, t }: { d: Pipe; t: number }) {
  const w = useV4<any>(`/reconstruction/image?record=R-FRQI-16x16&image=${encodeURIComponent(d.image)}`);
  const pch = useV4<any>(`/reconstruction/image?record=P-FRQI-64-p8&image=${encodeURIComponent(d.image)}`);
  const whole = w.data, patch = pch.data;
  const k = Math.min(SHOT_MODES.length - 1, Math.floor(t * SHOT_MODES.length));
  const pModes = ['shots100', 'shots1000', 'shots10000', 'statevector'];
  const kp = Math.min(pModes.length - 1, Math.floor(t * pModes.length));
  if (w.error || pch.error) return <Explain what="The full reconstruction study (all 1,800 images) has not finished yet — this step will show real measurement results once it has." />;
  if (!whole || !patch) return <div className="text-sm text-slate-400">Loading measured reconstructions…</div>;
  const m = SHOT_MODES[k], mp = pModes[kp];
  const mse = (v: number) => (v < 1e-15 ? '0 (exact)' : v.toExponential(1));
  const lab = (s: string) => (s === 'statevector' ? 'exact (statevector)' : `${Number(s.slice(5)).toLocaleString()} shots`);
  return (
    <div className="space-y-4">
      <Explain what={<>A real quantum computer cannot read amplitudes directly — it <b>measures</b>, and each run ("shot") gives one random outcome.
        Below, the FRQI state of this image was measured with more and more shots and decoded back into an image (real Qiskit circuits, real decoder).</>}
        why="This is why shot counts matter: with few shots the decoded image is noisy; the exact statevector reproduces the encoded image perfectly." />
      <div className="flex flex-wrap gap-6">
        <div className="flex gap-3">
          <Gray data={whole.original} size={150} label="16 × 16 encoded image" />
          <Gray data={whole.modes[m]} size={150} label={<span className="text-cyan-300">{lab(m)} · MSE {mse(whole.row.modes[m].vs_preprocessed.mse)}</span>} />
        </div>
        <div className="flex gap-3">
          <Gray data={patch.original} size={150} label="64 × 64 (V4 patches)" />
          <Gray data={patch.modes[mp]} size={150} label={<span className="text-cyan-300">{lab(mp)} per patch · MSE {mse(patch.row.modes[mp].vs_preprocessed.mse)}</span>} />
        </div>
      </div>
    </div>
  );
}

function StageVerdicts({ d }: { d: Pipe }) {
  const s = useV4<any>(`/image-models?image=${encodeURIComponent(d.image)}`);
  const [kind, setKind] = useState('all');
  if (s.error) return <div className="text-sm text-rose-300">{s.error}</div>;
  if (!s.data) return <div className="text-sm text-slate-400">Loading…</div>;
  const rows = (s.data.models as any[]).filter((m) => kind === 'all' || m.kind === kind);
  const byP = ['V2', 'V3', 'V4'].map((p) => ({ p, ms: rows.filter((m) => m.protocol === p) }));
  const shade = ['#7f1d1d', '#b45309', '#65a30d', '#059669'];
  const total = rows.length, allRight = rows.filter((m) => m.n_correct === 3).length;
  return (
    <div className="space-y-3">
      <Explain what={<>Every selected model from all protocols ({s.data.models.length} models × 3 seeds) on this same image — copied from each model&apos;s saved
        locked-test predictions, nothing re-run. {allRight} of {total} shown models get it right on all three seeds.</>} />
      <div className="flex flex-wrap items-center gap-2 text-[11px]">
        {['all', 'quantum', 'hybrid', 'classical', 'quantum-inspired (classical)', 'control'].map((k) => (
          <button key={k} onClick={() => setKind(k)} className={`rounded-md px-2 py-1 ring-1 ${kind === k ? 'bg-cyan-500/15 text-cyan-200 ring-cyan-500/40' : 'text-slate-400 ring-slate-700'}`}>{k}</button>))}
        <span className="ml-auto flex items-center gap-2 text-slate-400">seeds correct: {shade.map((c, k) => <span key={k} className="flex items-center gap-1"><i className="inline-block h-3 w-3 rounded-sm" style={{ background: c }} />{k}/3</span>)}</span>
      </div>
      {byP.map(({ p, ms }) => ms.length > 0 && (
        <div key={p}>
          <div className="mb-1 text-[11px] uppercase tracking-wider text-slate-500">Protocol {p} · {ms.length} models</div>
          <div className="flex flex-wrap gap-1">{ms.map((m: any) => (
            <div key={m.id} title={`${m.name} (${m.kind}) — predicted ${m.preds.map((x: number) => CLASS_NAMES[x]).join(' / ')}`}
              className="h-5 w-5 rounded-sm ring-1 ring-black/40" style={{ background: shade[m.n_correct] }} data-testid="verdict-cell" />))}</div>
        </div>))}
    </div>
  );
}

// ─────────────────────────── page ───────────────────────────
const STAGES = [
  { title: 'A real test image', ms: 1200, C: StageImage },
  { title: 'Preprocess', ms: 2400, C: StagePreprocess },
  { title: 'Cut into overlapping patches', ms: 5200, C: StagePatches },
  { title: 'Encode one patch as an FRQI quantum state', ms: 7000, C: StageEncode },
  { title: 'Mix all patch states into one density matrix ρ', ms: 5200, C: StageMix },
  { title: 'Compare with every training image (swap test)', ms: 3200, C: StageKernel },
  { title: 'The SVM decides', ms: 2600, C: StageSVM },
  { title: 'Measuring: what shots do to the image', ms: 5000, C: StageMeasure },
  { title: 'Every model in the project on this image', ms: 800, C: ({ d }: { d: Pipe; t: number }) => <StageVerdicts d={d} /> },
];

export default function HowItWorks() {
  const list = useV4<{ images: { image: string; class: string; frac_correct: number }[]; n_models: number }>('/images');
  const [image, setImage] = useState<string | null>(null);
  const [cls, setCls] = useState('scratches');
  useEffect(() => {
    if (!image && list.data) setImage(list.data.images.find((x) => x.class === 'scratches')?.image ?? list.data.images[0].image);
  }, [list.data, image]);
  const pipe = useV4<Pipe>(image ? `/pipeline?image=${encodeURIComponent(image)}` : null);
  const [step, setStep] = useState(0);
  const [speed, setSpeed] = useState(1);
  const { playing, setPlaying } = useStepper(STAGES.length, step, setStep, (STAGES[step].ms + 1800) / speed);
  const t = useProgress(`${image}:${step}`, STAGES[step].ms, speed);
  const imgs = useMemo(() => (list.data?.images ?? []).filter((x) => x.class === cls), [list.data, cls]);
  const pick = (im: string) => { setImage(im); setStep(0); setPlaying(false); };
  const Stage = STAGES[step].C;
  return (
    <div className="space-y-5">
      <PageHeader title="How it works — live, on a real image"
        subtitle="Watch the frozen Protocol V4 FRQI model classify one locked-test image, step by step. Every number is computed from the real image, the real frozen checkpoint and the saved results; the quantum circuits are simulated exactly on a CPU (no quantum hardware)." />
      <Card title="Choose an image" subtitle="All 360 locked-test images; the % shows how many of the project's 163 models (× 3 seeds) classify it correctly.">
        <div className="flex flex-wrap items-center gap-2">
          {CLASS_NAMES.map((n, j) => {
            const c = ['crazing', 'inclusion', 'patches', 'pitted_surface', 'rolled-in_scale', 'scratches'][j];
            return <button key={c} onClick={() => setCls(c)} className={`rounded-md px-2.5 py-1 text-xs ring-1 ${cls === c ? 'bg-slate-800 text-white ring-slate-500' : 'text-slate-400 ring-slate-700'}`}>
              <span style={{ color: CLASS_COLORS[j] }}>■</span> {n}</button>;
          })}
          <button className="ml-auto inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs text-slate-300 ring-1 ring-slate-700"
            onClick={() => { const all = list.data?.images ?? []; if (all.length) pick(all[Math.floor(Math.random() * all.length)].image); }}><Shuffle size={13} /> Random</button>
          <button className="inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs text-slate-300 ring-1 ring-slate-700"
            onClick={() => { const all = [...(list.data?.images ?? [])].sort((a, b) => a.frac_correct - b.frac_correct); if (all.length) pick(all[0].image); }}><Flame size={13} /> Hardest</button>
        </div>
        <div className="mt-3 flex max-h-28 flex-wrap gap-1 overflow-y-auto">
          {imgs.map((x) => (
            <button key={x.image} onClick={() => pick(x.image)} data-testid="hiw-image"
              className={`rounded px-1.5 py-0.5 font-mono text-[10px] ring-1 ${x.image === image ? 'bg-cyan-500/15 text-cyan-200 ring-cyan-500/50' : 'text-slate-400 ring-slate-800 hover:text-slate-200'}`}>
              {x.image.split('/').pop()?.replace('.jpg', '')} · {Math.round(100 * x.frac_correct)}%
            </button>))}
        </div>
      </Card>
      <Gate state={pipe}>{(d) => (
        <Card title="" className="overflow-hidden">
          <div className="space-y-4" data-testid="hiw-stage" data-step={step}>
            <StepControls step={step} n={STAGES.length} setStep={setStep} playing={playing} setPlaying={setPlaying} title={STAGES[step].title} />
            <div className="flex items-center gap-2 text-[11px] text-slate-400">speed
              {[0.5, 1, 2].map((s) => <button key={s} onClick={() => setSpeed(s)} className={`rounded px-1.5 py-0.5 ring-1 ${speed === s ? 'text-cyan-200 ring-cyan-500/50' : 'ring-slate-700'}`}>{s}×</button>)}
              <span className="ml-auto">model <Mono>{d.model_group}</Mono> · checkpoint <Mono>{d.experiment_id}</Mono></span>
            </div>
            <div className="min-h-[320px]"><Stage d={d} t={t} /></div>
          </div>
        </Card>)}
      </Gate>
    </div>
  );
}
