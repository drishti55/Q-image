// Visual building blocks for the Algorithm Playground. Everything renders data passed in; nothing is computed or invented here.
import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Pause, Play, RotateCcw, SkipBack, SkipForward } from 'lucide-react';

export const CLASS_NAMES = ['Crazing', 'Inclusion', 'Patches', 'Pitted surface', 'Rolled-in scale', 'Scratches'];
export const CLASS_COLORS = ['#f59e0b', '#22d3ee', '#a78bfa', '#34d399', '#f472b6', '#60a5fa'];
export const fx = (v: number | null | undefined, d = 3) => (v === null || v === undefined || Number.isNaN(v) ? 'unavailable' : v.toFixed(d));

// ── 3×3 / 4×4 pixel grids ──
export type Cell = { r: number; c: number };
export function PixelGrid({ values, highlight = [], padding, size = 64, label, sub, positionIndex, cellText, onSelect, selected }: {
  values: number[][]; highlight?: Cell[]; padding?: (r: number, c: number) => boolean; size?: number; label?: string; sub?: string;
  positionIndex?: boolean; cellText?: (v: number, r: number, c: number) => ReactNode;
  onSelect?: (r: number, c: number) => void; selected?: Cell | null;
}) {
  const [hover, setHover] = useState<{ r: number; c: number; v: number } | null>(null);
  const isHi = (r: number, c: number) => highlight.some((h) => h.r === r && h.c === c);
  const cols = values[0].length;
  return (
    <div>
      {label && <div className="mb-2 text-xs font-medium text-slate-300">{label}</div>}
      <div className="relative inline-block">
        <div className="grid gap-1" style={{ gridTemplateColumns: `repeat(${cols}, ${size}px)` }} role="grid" aria-label={label ?? 'pixel grid'}>
          {values.map((row, r) => row.map((v, c) => {
            const pad = padding?.(r, c);
            const g = Math.max(0, Math.min(255, Math.round(v)));
            const isSel = selected?.r === r && selected?.c === c;
            const clickable = !!onSelect && !pad;
            return (
              <div key={`${r}-${c}`} role={clickable ? 'button' : 'gridcell'} tabIndex={clickable ? 0 : undefined} aria-pressed={clickable ? isSel : undefined}
                aria-label={`row ${r + 1}, column ${c + 1}, intensity ${v}${pad ? ' (padding)' : ''}${clickable ? ' — select pixel' : ''}`}
                data-testid={`cell-${r}-${c}`} onMouseEnter={() => setHover({ r, c, v })} onMouseLeave={() => setHover(null)}
                onClick={clickable ? () => onSelect!(r, c) : undefined}
                onKeyDown={clickable ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect!(r, c); } } : undefined}
                className={`relative grid place-items-center rounded-md text-sm font-semibold tabular-nums transition-all duration-300 ${clickable ? 'cursor-pointer hover:brightness-125' : ''} ${isSel ? 'ring-4 ring-cyan-300 scale-110 z-20 shadow-[0_0_24px_rgba(34,211,238,0.55)]' : isHi(r, c) ? 'ring-2 ring-cyan-500/70 z-10' : 'ring-1 ring-slate-700'}`}
                style={{ width: size, height: size, background: `rgb(${g},${g},${g})`, color: g > 110 ? '#0f172a' : '#e2e8f0',
                  backgroundImage: pad ? 'repeating-linear-gradient(45deg, rgba(148,163,184,.18) 0 4px, transparent 4px 8px)' : undefined }}>
                <span key={String(cellText ? cellText(v, r, c) : v)} className="animate-[fadeUp_.4s_ease-out] px-0.5 text-center leading-tight" style={{ fontSize: size > 70 ? 15 : undefined }}>{cellText ? cellText(v, r, c) : v}</span>
                {pad && <span className="absolute bottom-0.5 text-[9px] font-normal text-slate-400">pad</span>}
                {positionIndex && <span className="absolute left-1 top-0.5 text-[9px] font-normal opacity-70">#{r * cols + c}</span>}
              </div>
            );
          }))}
        </div>
        {hover && (
          <div role="tooltip" className="pointer-events-none absolute -top-9 left-0 whitespace-nowrap rounded-md bg-slate-950 px-2 py-1 text-[11px] text-slate-100 ring-1 ring-slate-700">
            row {hover.r + 1}, column {hover.c + 1} · intensity {hover.v}{padding?.(hover.r, hover.c) ? ' · zero padding (not a given pixel)' : ''}
          </div>
        )}
      </div>
      {sub && <div className="mt-2 max-w-xs text-[11px] text-slate-500">{sub}</div>}
    </div>
  );
}

// ── 2-D array rendered as an image (feature maps, PCA components, resized inputs) ──
export function ArrayImage({ data, size = 96, label, max = 1 }: { data: number[][]; size?: number; label?: string; max?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const cv = ref.current;
    if (!cv || !data.length) return;
    const h = data.length, w = data[0].length;
    cv.width = w; cv.height = h;
    const ctx = cv.getContext('2d');
    if (!ctx) return;
    const img = ctx.createImageData(w, h);
    data.forEach((row, y) => row.forEach((v, x) => {
      const g = Math.round(Math.max(0, Math.min(1, v / max)) * 255);
      const i = (y * w + x) * 4;
      img.data[i] = g; img.data[i + 1] = g; img.data[i + 2] = g; img.data[i + 3] = 255;
    }));
    ctx.putImageData(img, 0, 0);
  }, [data, max]);
  return (
    <figure className="inline-block">
      <canvas ref={ref} style={{ width: size, height: size, imageRendering: 'pixelated' }} className="rounded-md ring-1 ring-slate-700" />
      {label && <figcaption className="mt-1 text-center text-[10px] text-slate-400">{label}</figcaption>}
    </figure>
  );
}

// ── horizontal value bars (probabilities, kernel values, decision values) ──
export function ValueBars({ items, max, signed = false, digits = 3 }: { items: { label: string; value: number; color?: string; strong?: boolean }[]; max?: number; signed?: boolean; digits?: number }) {
  const m = max ?? Math.max(1e-9, ...items.map((i) => Math.abs(i.value)));
  return (
    <div className="space-y-1.5">
      {items.map((it) => (
        <div key={it.label} className="grid grid-cols-[120px_minmax(0,1fr)_64px] items-center gap-2 text-xs">
          <span className={`truncate ${it.strong ? 'font-semibold text-white' : 'text-slate-300'}`}>{it.label}</span>
          <div className={`relative h-3 rounded-full bg-slate-800 ${signed ? '' : ''}`}>
            {signed ? (
              <div className="absolute top-0 h-3 rounded-full" style={{ left: it.value >= 0 ? '50%' : `${50 - (Math.abs(it.value) / m) * 50}%`, width: `${(Math.abs(it.value) / m) * 50}%`, background: it.color ?? '#22d3ee' }} />
            ) : (
              <div className="h-3 rounded-full transition-[width] duration-500" style={{ width: `${Math.max(1, (Math.abs(it.value) / m) * 100)}%`, background: it.color ?? '#22d3ee' }} />
            )}
            {signed && <div className="absolute left-1/2 top-[-2px] h-4 w-px bg-slate-500" />}
          </div>
          <span className={`text-right tabular-nums ${it.strong ? 'font-semibold text-white' : 'text-slate-300'}`}>{it.value.toFixed(digits)}</span>
        </div>
      ))}
    </div>
  );
}

export function ProbBars({ probs, highlight }: { probs: number[]; highlight?: number }) {
  return <ValueBars max={1} items={probs.map((p, i) => ({ label: CLASS_NAMES[i], value: p, color: CLASS_COLORS[i], strong: i === highlight }))} />;
}

// ── heat map (kernel matrices) ──
export function Heatmap({ m, labels, title, color = '34,211,238', digits = 2 }: { m: number[][]; labels: string[]; title?: string; color?: string; digits?: number }) {
  return (
    <div className="overflow-x-auto">
      {title && <div className="mb-2 text-xs font-medium text-slate-300">{title}</div>}
      <table className="text-[10px] tabular-nums">
        <thead><tr><th />{labels.map((l) => <th key={l} className="w-11 px-0.5 pb-1 font-normal text-slate-400">{l.slice(0, 6)}</th>)}</tr></thead>
        <tbody>{m.map((row, i) => (
          <tr key={i}><th className="pr-1.5 text-right font-normal text-slate-400 whitespace-nowrap">{labels[i]}</th>
            {row.map((v, j) => <td key={j} className="h-9 w-11 text-center text-slate-100 ring-1 ring-slate-900" style={{ background: `rgba(${color},${0.08 + 0.85 * Math.max(0, Math.min(1, v))})` }}>{v.toFixed(digits)}</td>)}</tr>
        ))}</tbody>
      </table>
    </div>
  );
}

// ── qubit circuit drawn from recorded instructions ──
export type Gate = { name: string; qubits: number[]; params: number[] };
export function MiniCircuit({ gates, n, highlightFrom, highlightTo, labels }: { gates: Gate[]; n: number; highlightFrom?: number; highlightTo?: number; labels?: string[] }) {
  const free = new Array(n).fill(0);
  const placed = gates.map((g, i) => {
    const lo = Math.min(...g.qubits), hi = Math.max(...g.qubits);
    const span = g.qubits.length > 1 ? Array.from({ length: hi - lo + 1 }, (_, k) => lo + k) : g.qubits;
    const col = Math.max(...span.map((q) => free[q]));
    span.forEach((q) => { free[q] = col + 1; });
    return { ...g, col, i };
  });
  const cols = Math.max(1, ...placed.map((g) => g.col + 1));
  const W = 40, H = 30, L = 64, T = 16;
  const name = (g: Gate) => ({ ry: 'RY', rz: 'RZ', h: 'H', p: 'P', x: 'X', cx: 'X', mcx: 'X', mcry: 'RY' } as Record<string, string>)[g.name] ?? g.name.toUpperCase();
  return (
    <div className="overflow-x-auto rounded-xl bg-[#050913] p-2 ring-1 ring-slate-800">
      <svg width={L + cols * W + 10} height={T + n * H} role="img" aria-label="circuit">
        {Array.from({ length: n }, (_, q) => (
          <g key={q}><text x={4} y={T + q * H + 4} fontSize={10} fill="#94a3b8" fontFamily="ui-monospace, SFMono-Regular, Menlo, monospace">{labels?.[q] ?? `q${q}`}</text>
            <line x1={L - 8} x2={L + cols * W} y1={T + q * H} y2={T + q * H} stroke="#334155" /></g>
        ))}
        {placed.map((g) => {
          const x = L + g.col * W + W / 2;
          const on = highlightFrom === undefined || (g.i >= highlightFrom && g.i < (highlightTo ?? highlightFrom + 1));
          const op = on ? 1 : 0.25;
          const t = g.qubits[g.qubits.length - 1];
          const tip = `${g.name}${g.params.length ? `(${g.params.join(', ')})` : ''} on q${g.qubits.join(', q')}`;
          if (g.qubits.length > 1) {
            return (
              <g key={g.i} opacity={op}><title>{tip}</title>
                <line x1={x} x2={x} y1={T + Math.min(...g.qubits) * H} y2={T + Math.max(...g.qubits) * H} stroke="#22d3ee" strokeWidth={1.5} />
                {g.qubits.slice(0, -1).map((q) => <circle key={q} cx={x} cy={T + q * H} r={3.5} fill="#22d3ee" />)}
                <circle cx={x} cy={T + t * H} r={8} fill="#050913" stroke="#22d3ee" strokeWidth={1.5} />
                <line x1={x - 8} x2={x + 8} y1={T + t * H} y2={T + t * H} stroke="#22d3ee" strokeWidth={1.5} />
                <line x1={x} x2={x} y1={T + t * H - 8} y2={T + t * H + 8} stroke="#22d3ee" strokeWidth={1.5} />
              </g>
            );
          }
          const fill = ({ H: '#1e3a8a', P: '#4c1d95', RZ: '#164e63', RY: '#0e7490', X: '#7f1d1d' } as Record<string, string>)[name(g)] ?? '#334155';
          return (
            <g key={g.i} opacity={op}><title>{tip}</title>
              <rect x={x - 15} y={T + t * H - 10} width={30} height={20} rx={4} fill={fill} stroke="#475569" />
              <text x={x} y={T + t * H + 4} fontSize={9} fill="#e2e8f0" textAnchor="middle" fontFamily="ui-monospace, SFMono-Regular, Menlo, monospace">{name(g)}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ── step player: prev / play / pause / next / reset ──
export function useStepper(n: number, step: number, setStep: (s: number) => void, intervalMs = 2600) {
  const [playing, setPlaying] = useState(false);
  useEffect(() => {
    if (!playing) return;
    if (step >= n - 1) { setPlaying(false); return; }
    const t = setTimeout(() => setStep(step + 1), intervalMs);
    return () => clearTimeout(t);
  }, [playing, step, n, setStep, intervalMs]);
  return { playing, setPlaying };
}

export function StepControls({ step, n, setStep, playing, setPlaying, title }: {
  step: number; n: number; setStep: (s: number) => void; playing: boolean; setPlaying: (p: boolean) => void; title: string;
}) {
  const btn = 'inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium ring-1 transition disabled:opacity-30';
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="mr-auto min-w-0">
        <div className="text-[11px] uppercase tracking-wider text-cyan-300/80" data-testid="step-counter">Step {step + 1} of {n}</div>
        <div className="text-lg font-semibold text-white">{title}</div>
      </div>
      <button className={`${btn} text-slate-200 ring-slate-700 hover:bg-slate-800`} onClick={() => { setPlaying(false); setStep(Math.max(0, step - 1)); }} disabled={step === 0} aria-label="Previous step"><SkipBack size={14} /> Previous</button>
      {playing
        ? <button className={`${btn} bg-amber-500/15 text-amber-200 ring-amber-500/40`} onClick={() => setPlaying(false)} aria-label="Pause"><Pause size={14} /> Pause</button>
        : <button className={`${btn} bg-cyan-500/15 text-cyan-200 ring-cyan-500/40`} onClick={() => { if (step >= n - 1) setStep(0); setPlaying(true); }} aria-label="Play animation"><Play size={14} /> Play</button>}
      <button className={`${btn} text-slate-200 ring-slate-700 hover:bg-slate-800`} onClick={() => { setPlaying(false); setStep(Math.min(n - 1, step + 1)); }} disabled={step === n - 1} aria-label="Next step">Next <SkipForward size={14} /></button>
      <button className={`${btn} text-slate-300 ring-slate-700 hover:bg-slate-800`} onClick={() => { setPlaying(false); setStep(0); }} aria-label="Reset"><RotateCcw size={14} /> Reset</button>
      <div className="flex w-full gap-1">{Array.from({ length: n }, (_, k) => (
        <button key={k} aria-label={`Go to step ${k + 1}`} onClick={() => { setPlaying(false); setStep(k); }}
          className={`h-1.5 flex-1 rounded-full transition ${k === step ? 'bg-cyan-400' : k < step ? 'bg-cyan-700/70' : 'bg-slate-700'}`} />))}</div>
    </div>
  );
}

// ── small text helpers ──
export function Formula({ children }: { children: ReactNode }) {
  return <div className="rounded-lg bg-slate-950/70 px-3 py-2 font-mono text-[13px] text-cyan-100 ring-1 ring-slate-800 overflow-x-auto">{children}</div>;
}
export function Note({ children, tone = 'slate' }: { children: ReactNode; tone?: 'slate' | 'amber' | 'cyan' }) {
  const c = { slate: 'bg-slate-900/60 text-slate-300 ring-slate-800', amber: 'bg-amber-500/10 text-amber-100 ring-amber-500/30', cyan: 'bg-cyan-500/10 text-cyan-100 ring-cyan-500/30' }[tone];
  return <div className={`rounded-lg px-3 py-2 text-xs leading-relaxed ring-1 ${c}`}>{children}</div>;
}
export function IO({ input, output }: { input: ReactNode; output: ReactNode }) {
  return (
    <div className="grid gap-2 text-xs sm:grid-cols-2">
      <div className="rounded-lg bg-slate-900/60 p-2.5 ring-1 ring-slate-800"><div className="mb-1 text-[10px] uppercase tracking-wider text-slate-500">Input</div><div className="text-slate-200">{input}</div></div>
      <div className="rounded-lg bg-slate-900/60 p-2.5 ring-1 ring-slate-800"><div className="mb-1 text-[10px] uppercase tracking-wider text-slate-500">Output</div><div className="text-slate-200">{output}</div></div>
    </div>
  );
}
export function Vec({ v, digits = 3, max = 12 }: { v: number[]; digits?: number; max?: number }) {
  const s = v.slice(0, max).map((x) => x.toFixed(digits)).join(', ');
  return <span className="font-mono">[{s}{v.length > max ? `, … (${v.length} values)` : ''}]</span>;
}
