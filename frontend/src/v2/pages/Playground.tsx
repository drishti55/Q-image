/* eslint-disable @typescript-eslint/no-explicit-any */
// 3×3 Algorithm Playground (Protocol V3 educational data, GET /api/v3/playground).
// Left: clickable input image + selected-pixel facts. Centre: stages, controls, the pixel's journey, the visual.
// Right: what / why / formula / actual output / interpretation. Presentation mode: full-screen, larger, auto-play.
import { useCallback, useEffect, useMemo } from 'react';
import type { ReactNode } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Atom, ChevronRight, Info, Layers, Maximize2, X } from 'lucide-react';
import { useV3 } from '../api';
import { ErrorState, Loading } from '../ui';
import { CLASSICAL } from '../playground/classical';
import { QUANTUM } from '../playground/quantum';
import { Formula, Note, PixelGrid, StepControls, useStepper } from '../playground/widgets';
import type { Algo, Ctx, TraceItem } from '../playground/types';
import { GIVEN, bin8, f4, theta } from '../playground/types';
import Sandbox from '../playground/Sandbox';
import Quiz from '../learn/Quiz';

export const ALGOS: Algo[] = [...CLASSICAL, ...QUANTUM];
export const demoPadding = (r: number, c: number) => !(r < 2 && c < 2);
const padding4 = (r: number, c: number) => !(r < 2 && c < 2);

// URL-state helper shared by the page; reads window.location so rapid updates never clobber each other.
function useUrlState() {
  const [sp, setSp] = useSearchParams();
  const update = useCallback((patch: Record<string, string | null>) => {
    setSp(() => {
      const n = new URLSearchParams(window.location.search);
      Object.entries(patch).forEach(([k, v]) => (v === null ? n.delete(k) : n.set(k, v)));
      return n;
    }, { replace: true });
  }, [setSp]);
  return [sp, update] as const;
}

export function makeCtx(d: any, algo: Algo, sp: URLSearchParams): Ctx {
  const o: Record<string, string> = {};
  (algo.options ?? []).forEach((op) => { o[op.key] = sp.get(op.key) ?? op.def; });
  const sel = Math.min(3, Math.max(0, Number(sp.get('px') ?? 0) || 0));
  const { r, c } = GIVEN[sel];
  return { d, o, sel, px: { r, c, v: d.grid[r][c] } };
}

function AlgoBar({ algo, onPick, big }: { algo: string; onPick: (id: string) => void; big?: boolean }) {
  const group = (title: string, Icon: typeof Atom, list: Algo[], tone: string, on: string) => (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className={`mr-1 inline-flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider ${tone}`}><Icon size={13} />{title}</span>
      {list.map((a) => (
        <button key={a.id} onClick={() => onPick(a.id)} data-testid={`algo-${a.id}`} aria-pressed={a.id === algo} title={a.blurb}
          className={`rounded-lg px-3 py-1.5 font-medium ring-1 transition ${big ? 'text-base' : 'text-xs'} ${a.id === algo ? on : 'text-slate-300 ring-slate-700 hover:bg-slate-800'}`}>{a.name}</button>
      ))}
    </div>
  );
  return (
    <div className="space-y-2">
      {group('Classical', Layers, CLASSICAL, 'text-amber-300', 'bg-amber-500/15 text-amber-100 ring-amber-400/60')}
      {group('Quantum (simulated)', Atom, QUANTUM, 'text-cyan-300', 'bg-cyan-500/15 text-cyan-100 ring-cyan-400/60')}
    </div>
  );
}

function PixelFacts({ c, current }: { c: Ctx; current?: TraceItem }) {
  const v = c.px.v;
  const q4 = Math.round((v / 255) * 15);
  const rows: [string, ReactNode][] = [
    ['Intensity', <b className="text-white">{v}</b>],
    ['Row, column', `${c.px.r + 1}, ${c.px.c + 1}`],
    ['Normalised', `${v}/255 = ${f4(v / 255)}`],
    ['Binary (8-bit)', <span className="font-mono">{bin8(v)}</span>],
    ['NEQR 4-bit', <span className="font-mono">{q4.toString(2).padStart(4, '0')} (q = {q4})</span>],
    ['FRQI angle', `${f4(theta(v))} rad = ${(theta(v) * 180 / Math.PI).toFixed(2)}°`],
  ];
  return (
    <div className="rounded-xl bg-slate-950/50 p-3 ring-1 ring-slate-800" data-testid="pixel-facts">
      <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-cyan-300">Selected pixel</div>
      <dl className="grid grid-cols-[96px_minmax(0,1fr)] gap-x-2 gap-y-1 text-xs">
        {rows.map(([k, val]) => <FactRow key={k} k={k} v={val} />)}
      </dl>
      {current && <div className="mt-3 rounded-lg bg-cyan-500/10 p-2 text-xs ring-1 ring-cyan-500/30" data-testid="pixel-state">
        <div className="text-[10px] uppercase tracking-wider text-cyan-300">Current processing state</div>
        <div className="mt-0.5 text-slate-100"><span className="text-slate-400">{current.label}: </span>{current.value}</div></div>}
    </div>
  );
}
const FactRow = ({ k, v }: { k: string; v: ReactNode }) => <><dt className="text-slate-500">{k}</dt><dd className="text-slate-200">{v}</dd></>;

function Journey({ items, stage, px }: { items: TraceItem[]; stage?: string; px: number }) {
  const idx = Math.max(0, items.findIndex((t) => t.key === stage));
  return (
    <div className="rounded-xl bg-slate-950/50 p-3 ring-1 ring-slate-800" data-testid="journey" aria-label="pixel journey">
      <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Journey of pixel {px}</div>
      <div className="flex flex-wrap items-center gap-1">
        {items.map((t, i) => (
          <div key={t.key} className="flex items-center gap-1">
            <div data-testid={`journey-${t.key}`} data-active={i === idx}
              className={`rounded-lg px-2.5 py-1.5 text-xs transition-all duration-500 ${i === idx ? 'scale-105 bg-cyan-500/20 text-cyan-50 ring-2 ring-cyan-400 shadow-[0_0_18px_rgba(34,211,238,0.35)]' : i < idx ? 'bg-slate-800/80 text-slate-300 ring-1 ring-cyan-900' : 'bg-slate-900/60 text-slate-500 ring-1 ring-slate-800'}`}>
              <div className="text-[10px] uppercase tracking-wide opacity-80">{t.label}</div>
              <div className="font-mono">{t.value}</div>
            </div>
            {i < items.length - 1 && <ChevronRight size={14} className={i < idx ? 'text-cyan-500' : 'text-slate-700'} />}
          </div>
        ))}
      </div>
    </div>
  );
}

function Explain({ s, big }: { s: ReturnType<Algo['steps']>[number]; big?: boolean }) {
  const t = big ? 'text-base' : 'text-sm';
  const sec = (h: string, children: ReactNode, id: string) => (
    <section data-testid={`explain-${id}`}><h4 className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">{h}</h4><div className={`${t} leading-relaxed text-slate-200`}>{children}</div></section>
  );
  return (
    <div className="space-y-4" key={s.title}>
      {sec('What is happening?', s.explain, 'what')}
      {sec('Why is it needed?', s.why, 'why')}
      {s.formula && sec('Formula', <Formula>{s.formula}</Formula>, 'formula')}
      {s.out && sec('Actual calculated output', <div className="rounded-lg bg-emerald-500/10 px-3 py-2 font-mono text-[13px] text-emerald-100 ring-1 ring-emerald-500/30">{s.out}</div>, 'out')}
      {sec('Interpretation', <span className="text-slate-300">{s.interp}</span>, 'interp')}
    </div>
  );
}

function Walkthrough({ d, present }: { d: any; present: boolean }) {
  const [sp, update] = useUrlState();
  const algo = ALGOS.find((a) => a.id === sp.get('algo')) ?? ALGOS.find((a) => a.id === 'frqi')!;
  const c = useMemo(() => makeCtx(d, algo, sp), [d, algo, sp]);
  const steps = algo.steps(c);
  const trace = algo.trace(c);
  const step = Math.min(steps.length - 1, Math.max(0, Number(sp.get('step') ?? 0) || 0));
  const setStep = useCallback((s: number) => update({ step: String(s) }), [update]);
  const { playing, setPlaying } = useStepper(steps.length, step, setStep, present ? 4200 : 2800);
  const cur = steps[step];
  const curTrace = trace.find((t) => t.key === cur.stage);
  const big = present;

  useEffect(() => {
    if (!present) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') { setPlaying(false); setStep(Math.min(steps.length - 1, step + 1)); }
      if (e.key === 'ArrowLeft') { setPlaying(false); setStep(Math.max(0, step - 1)); }
      if (e.key === 'Escape') update({ present: null });
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [present, step, steps.length, setStep, setPlaying, update]);

  const padded = cur.grid === 'padded';
  const hl = cur.hl === 'given' ? GIVEN : [];
  const cellText = (v: number, r: number, cc: number) => (r === c.px.r && cc === c.px.c && curTrace?.short ? curTrace.short : v);
  const size = big ? (padded ? 72 : 100) : (padded ? 50 : 72);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start gap-4 rounded-2xl border border-slate-800/80 bg-[#0f172a]/70 p-4">
        <div className="min-w-0 flex-1"><AlgoBar algo={algo.id} onPick={(id) => update({ algo: id, step: '0' })} big={big} /></div>
        <div className="flex flex-wrap items-center gap-2">
          {(algo.options ?? []).map((op) => (
            <div key={op.key} className="flex items-center gap-1 rounded-lg bg-slate-950/60 p-1 ring-1 ring-slate-800" role="group" aria-label={op.label}>
              <span className="px-2 text-[11px] text-slate-400">{op.label}</span>
              {op.values.map(([v, l]) => (
                <button key={v} onClick={() => update({ [op.key]: v })} aria-pressed={c.o[op.key] === v} data-testid={`opt-${op.key}-${v}`}
                  className={`rounded-md px-2.5 py-1 ${big ? 'text-sm' : 'text-xs'} ${c.o[op.key] === v ? 'bg-cyan-500/20 text-cyan-100' : 'text-slate-300 hover:bg-slate-800'}`}>{l}</button>
              ))}
            </div>
          ))}
          {!present && <button onClick={() => update({ present: '1' })} data-testid="enter-present" className="inline-flex items-center gap-1.5 rounded-lg bg-cyan-500/15 px-3 py-1.5 text-xs font-medium text-cyan-100 ring-1 ring-cyan-500/40 hover:bg-cyan-500/25"><Maximize2 size={14} /> Presentation mode</button>}
        </div>
      </div>

      <div className={`grid gap-4 ${big ? 'lg:grid-cols-[340px_minmax(0,1fr)] xl:grid-cols-[350px_minmax(0,1fr)_380px]' : 'lg:grid-cols-[260px_minmax(0,1fr)] xl:grid-cols-[260px_minmax(0,1fr)_300px]'}`}>
        {/* LEFT: input image */}
        <aside className="space-y-3 rounded-2xl border border-slate-800/80 bg-[#0f172a]/70 p-4" aria-label="input image">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Input image{padded ? ' (embedded in 4×4)' : ''}</div>
          <PixelGrid values={padded ? d.frqi.padded_4x4 : d.grid} padding={padded ? padding4 : demoPadding} size={size}
            highlight={hl} selected={{ r: c.px.r, c: c.px.c }} positionIndex={padded} cellText={cellText}
            onSelect={(r, cc) => { const i = GIVEN.findIndex((g) => g.r === r && g.c === cc); if (i >= 0) update({ px: String(i) }); }} />
          <div className="text-[11px] leading-relaxed text-slate-500">Click 70, 180, 19 or 20 to follow that pixel. Hatched cells are zero padding{padded ? '; FRQI / NEQR need 2ⁿ pixels, so the grid sits in a 4×4 grid' : ''}.</div>
          <PixelFacts c={c} current={curTrace} />
        </aside>

        {/* CENTRE: processing */}
        <section className="min-w-0 space-y-3" aria-label="algorithm processing">
          <div className="rounded-2xl border border-slate-800/80 bg-[#0f172a]/70 p-4">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${algo.family === 'quantum' ? 'bg-cyan-500/15 text-cyan-200' : 'bg-amber-500/15 text-amber-200'}`}>{algo.family === 'quantum' ? 'Quantum · noiseless CPU simulation' : 'Classical'}</span>
              <h2 className={`${big ? 'text-2xl' : 'text-lg'} font-semibold text-white`} data-testid="algo-title">{algo.name}</h2>
            </div>
            <StepControls step={step} n={steps.length} setStep={setStep} playing={playing} setPlaying={setPlaying} title={cur.title} />
            <div className="mt-2 flex flex-wrap gap-1 text-[10px]" aria-label="stages">{steps.map((s, i) => <button key={i} onClick={() => { setPlaying(false); setStep(i); }} className={`rounded px-1.5 py-0.5 ${i === step ? 'bg-cyan-500/20 text-cyan-100' : 'text-slate-500 hover:text-slate-300'}`}>{i + 1}. {s.title}</button>)}</div>
          </div>
          <Journey items={trace} stage={cur.stage} px={c.px.v} />
          <div key={`${algo.id}-${step}-${c.sel}-${JSON.stringify(c.o)}`} className="min-w-0 rounded-2xl border border-slate-800/80 bg-[#0f172a]/70 p-4 animate-[fadeUp_.35s_ease-out]" data-testid="step-visual">{cur.body}</div>
        </section>

        {/* RIGHT: explanation */}
        <aside className="rounded-2xl border border-slate-800/80 bg-[#0f172a]/70 p-4 lg:col-span-2 xl:col-span-1" aria-label="explanation" data-testid="step-explain">
          <Explain s={cur} big={big} />
        </aside>
      </div>
    </div>
  );
}

export default function Playground() {
  const pg = useV3<any>('/playground');
  const [sp, update] = useUrlState();
  const present = sp.get('present') === '1';
  const body = pg.loading ? <Loading text="Loading playground data…" /> : pg.error ? <ErrorState error={pg.error} /> : <Walkthrough d={pg.data} present={present} />;
  if (present) {
    return (
      <div className="fixed inset-0 z-50 overflow-auto bg-[#070b14] p-4 md:p-6" data-testid="present-mode">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div><div className="text-[11px] uppercase tracking-[0.2em] text-cyan-300">Q-ImageLab · presentation</div><h1 className="text-2xl font-semibold text-white md:text-3xl">3×3 Algorithm Playground</h1></div>
          <div className="flex items-center gap-2 text-xs text-slate-400"><span className="hidden md:inline">← → step · Esc exit</span>
            <button onClick={() => update({ present: null })} aria-label="Exit presentation mode" className="inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-slate-200 ring-1 ring-slate-700 hover:bg-slate-800"><X size={14} /> Exit</button></div>
        </div>
        {body}
      </div>
    );
  }
  return (
    <div>
      <div className="mb-4">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-50">3×3 Algorithm Playground</h1>
        <p className="mt-1 max-w-4xl text-sm leading-relaxed text-slate-400">Click a pixel, pick an algorithm and step through it. Every number is computed by the project's real code and trained transforms.</p>
      </div>
      <section className="mb-6 rounded-2xl border border-slate-800/80 bg-[#0f172a]/70 p-5">
        <h2 className="mb-3 text-[15px] font-semibold text-slate-100">Try it: edit the pixels</h2>
        <Sandbox />
      </section>
      <h2 className="mb-3 text-[15px] font-semibold text-slate-100">Step through each algorithm</h2>
      <div className="mb-4"><Note tone="amber"><Info size={13} className="mr-1 inline" /><b>Illustrative demonstration.</b> The grid (70, 180, 19, 20 + zero padding) is not a NEU-DET image. No classifier output is shown for it and it is never mixed into reported results; those come from the 360 locked test images.</Note></div>
      {body}
      <div className="mt-6"><Quiz id="playground" /></div>
    </div>
  );
}
