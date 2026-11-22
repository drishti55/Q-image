// Presentation mode (Protocol V4): full-screen slides for a talk or viva. Every number comes from /api/v4
// (versions, results, all-models); the encoding slide reuses the live FRQI/NEQR walkthrough. ← / → / Space to move, Esc to exit.
import { useCallback, useEffect } from 'react';
import type { ReactNode } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';
import { useV4 } from '../api';
import { ErrorState, Loading } from '../ui';
import { FadeIn } from '../theme';
import AllModelsChart from '../AllModelsChart';
import EncodingWalkthrough from '../learn/EncodingWalkthrough';

type MS = { mean: number; std?: number };
type Cmp = { name: string; diff: number; ci95: [number, number]; p_holm: number };
type Version = { id: string; comparable: boolean; latest?: boolean; title: string; what: string; frqi?: MS; neqr?: MS; control?: MS;
  frqi_qubits?: number; neqr_qubits?: number; frqi_group?: string; neqr_group?: string; comparisons?: Cmp[]; models: { name: string; type: string; test_accuracy: MS }[] };
type Versions = { versions: Version[]; n_test: number; execution: string; same_test_set: string };

const FRQI = '#3987e5', NEQR = '#d95926', CLASSICAL = '#199e70';
const p1 = (v?: number) => (v == null ? '—' : `${(100 * v).toFixed(1)}%`);
const pp = (v: number) => `${v >= 0 ? '+' : '−'}${Math.abs(100 * v).toFixed(1)} pp`;
const pv = (p: number) => (p < 0.001 ? 'p < 0.001' : `p = ${p.toFixed(3)}`);

function Slide({ kicker, title, children }: { kicker: string; title: string; children: ReactNode }) {
  return (
    <FadeIn>
      <div className="mx-auto w-full max-w-6xl">
        <div className="text-xs font-semibold uppercase tracking-[0.22em] text-teal-300/80">{kicker}</div>
        <h1 className="mt-2 text-3xl font-semibold leading-tight text-white md:text-5xl">{title}</h1>
        <div className="mt-8">{children}</div>
      </div>
    </FadeIn>
  );
}

function Box({ n, label, sub, tone = '#f8fafc' }: { n: ReactNode; label: string; sub?: ReactNode; tone?: string }) {
  return (
    <div className="rounded-2xl bg-white/[0.04] p-5 ring-1 ring-white/10">
      <div className="text-3xl font-bold tabular-nums md:text-4xl" style={{ color: tone }}>{n}</div>
      <div className="mt-1 text-sm font-medium text-slate-100">{label}</div>
      {sub && <div className="mt-0.5 text-xs text-slate-400">{sub}</div>}
    </div>
  );
}

/** Horizontal bars: FRQI and NEQR test accuracy per version (the story V2 → V3 → V4). */
function Journey({ vs }: { vs: Version[] }) {
  const rows = vs.filter((v) => v.comparable);
  return (
    <div className="space-y-4">
      {rows.map((v) => (
        <div key={v.id} className="grid grid-cols-[3rem_minmax(0,1fr)] items-center gap-4">
          <div className={`text-xl font-bold ${v.latest ? 'text-teal-300' : 'text-slate-400'}`}>{v.id}</div>
          <div className="space-y-1.5">
            {([['FRQI', v.frqi, FRQI], ['NEQR', v.neqr, NEQR]] as const).map(([k, m, c]) => (
              <div key={k} className="flex items-center gap-3">
                <span className="w-12 text-xs text-slate-400">{k}</span>
                <div className="h-5 flex-1 rounded-md bg-white/5"><div className="h-5 rounded-md transition-all duration-700" style={{ width: `${100 * (m?.mean ?? 0)}%`, background: c }} /></div>
                <span className="w-16 text-right text-lg font-semibold tabular-nums text-white">{p1(m?.mean)}</span>
              </div>))}
          </div>
        </div>))}
    </div>
  );
}

export default function Present() {
  const ver = useV4<Versions>('/versions');
  const [params, setParams] = useSearchParams();
  const nav = useNavigate();
  const N = 7;
  const i = Math.min(N - 1, Math.max(0, Number(params.get('slide') ?? 1) - 1));
  const clamp = (k: number) => String(Math.min(N, Math.max(1, k)));
  const go = useCallback((k: number) => setParams({ slide: clamp(k + 1) }), [setParams]);
  const step = useCallback((delta: number) => {
    const cur = Number(new URLSearchParams(window.location.search).get('slide') ?? 1);
    setParams({ slide: clamp(cur + delta) });
  }, [setParams]);
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.closest?.('input, button[role=radio]')) return;
      if (e.key === 'ArrowRight' || e.key === 'PageDown') { e.preventDefault(); step(1); }
      if (e.key === 'ArrowLeft' || e.key === 'PageUp') { e.preventDefault(); step(-1); }
      if (e.key === 'Escape') nav('/');
    };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [step, nav]);

  let body: ReactNode;
  if (ver.loading) body = <Loading text="Loading results…" />;
  else if (ver.error || !ver.data) body = <ErrorState error={ver.error ?? 'no data'} />;
  else {
    const d = ver.data, v4 = d.versions.find((v) => v.latest)!, v2 = d.versions.find((v) => v.id === 'V2');
    const cmp = (s: string) => v4.comparisons?.find((c) => c.name.startsWith(s));
    const fUp = cmp('V4 FRQI vs V2 FRQI'), nUp = cmp('V4 NEQR vs V2 NEQR'), ctrl = cmp('V4 FRQI vs classical patch-moment'), fvn = cmp('V4 FRQI vs V4 NEQR');
    const slides = [
      <Slide key="1" kicker="Q-ImageLab · Protocol V4" title="Can quantum image encodings recognise steel surface defects?">
        <div className="grid gap-4 md:grid-cols-4">
          <Box n="6" label="defect classes" sub="NEU-DET steel surfaces" />
          <Box n={d.n_test} label="locked test images" sub="opened once, at the very end" />
          <Box n="2" label="quantum encodings" sub="FRQI and NEQR" />
          <Box n={p1(v4.frqi?.mean)} label="best V4 quantum model" sub={`FRQI · ${v4.frqi_qubits} qubits per patch`} tone="#5eead4" />
        </div>
        <p className="mt-8 max-w-3xl text-sm text-amber-200/90">{d.execution}</p>
      </Slide>,

      <Slide key="2" kicker="1 · Encoding" title="Storing an image inside qubits">
        <div className="rounded-2xl bg-[#0f172a]/80 p-5 ring-1 ring-white/10"><EncodingWalkthrough /></div>
      </Slide>,

      <Slide key="3" kicker="2 · The problem" title={`Whole-image encodings peaked at ${p1(Math.max(...d.versions.filter((v) => v.comparable && !v.latest).flatMap((v) => [v.frqi?.mean ?? 0, v.neqr?.mean ?? 0])))}`}>
        <div className="grid gap-8 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <div className="rounded-2xl bg-white/[0.03] p-6 ring-1 ring-white/10"><Journey vs={d.versions.filter((v) => v.id !== 'V4')} /></div>
          <div className="space-y-4 text-lg leading-relaxed text-slate-300">
            <p>V2 and V3 encoded the <b className="text-white">whole image</b> as one quantum state and compared images pixel by pixel.</p>
            <p>Defects are <b className="text-white">textures</b>. Shift a scratch by two pixels and the whole-image state looks like a different image.</p>
          </div>
        </div>
      </Slide>,

      <Slide key="4" kicker="3 · The V4 idea" title="Encode patches, mix them into one state">
        <div className="flex flex-wrap items-center gap-2 text-center text-sm">
          {[['Image', 'one steel photo'], ['Patches', 'small p×p tiles'], ['|ψₖ⟩', 'FRQI / NEQR state per patch'], ['ρ = (1/P) Σ |ψₖ⟩⟨ψₖ|', 'mixed state of the image'], ['Tr(ρ_A ρ_B)', 'similarity (swap test)'], ['SVM', 'defect class']].map(([a, b], k, arr) => (
            <div key={a} className="flex items-center gap-2">
              <FadeIn delay={k * 120}><div className="rounded-2xl bg-white/[0.05] px-3 py-3 ring-1 ring-white/10"><div className="font-mono text-base text-teal-200">{a}</div><div className="mt-1 text-xs text-slate-400">{b}</div></div></FadeIn>
              {k < arr.length - 1 && <ChevronRight size={18} className="text-slate-600" />}
            </div>))}
        </div>
        <p className="mt-8 max-w-3xl text-lg leading-relaxed text-slate-300">Every patch is compared with every patch, so <b className="text-white">where</b> a texture sits no longer matters.</p>
        <Link to="/how-it-works" className="mt-4 inline-block text-sm text-teal-300 hover:underline">Watch it run on a real image →</Link>
      </Slide>,

      <Slide key="5" kicker="4 · Results" title={fUp && nUp ? `V4 lifts FRQI by ${(100 * fUp.diff).toFixed(0)} and NEQR by ${(100 * nUp.diff).toFixed(0)} points` : 'V4 results'}>
        <div className="grid gap-8 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <div className="rounded-2xl bg-white/[0.03] p-6 ring-1 ring-white/10"><Journey vs={d.versions} /></div>
          <div className="grid gap-4">
            <Box n={p1(v4.frqi?.mean)} label="FRQI, V4" tone={FRQI} sub={fUp ? <>{pp(fUp.diff)} vs V2 ({p1(v2?.frqi?.mean)}) · {pv(fUp.p_holm)}</> : undefined} />
            <Box n={p1(v4.neqr?.mean)} label="NEQR, V4" tone={NEQR} sub={nUp ? <>{pp(nUp.diff)} vs V2 ({p1(v2?.neqr?.mean)}) · {pv(nUp.p_holm)}</> : undefined} />
          </div>
        </div>
        <p className="mt-4 text-xs text-slate-500">{d.same_test_set} Mean over 3 seeds; p-values are paired permutation tests, Holm-corrected.</p>
      </Slide>,

      <Slide key="6" kicker="5 · Honest comparison" title="Is the quantum part doing the work?">
        <div className="grid gap-4 md:grid-cols-3">
          <Box n={p1(v4.frqi?.mean)} label="FRQI patch ensemble" tone={FRQI} />
          <Box n={p1(v4.control?.mean)} label="classical SVM on the same patches" tone={CLASSICAL}
            sub={ctrl ? <>FRQI {pp(ctrl.diff)} · {pv(ctrl.p_holm)} · {ctrl.p_holm < 0.05 ? 'significant' : 'not significant'}</> : undefined} />
          <Box n={fvn ? pp(fvn.diff) : '—'} label="FRQI vs NEQR" sub={fvn ? <>{pv(fvn.p_holm)} · {fvn.p_holm < 0.05 ? 'significant' : 'not significant'}</> : undefined} />
        </div>
        <div className="mt-6 rounded-2xl bg-[#0f172a]/80 p-5 ring-1 ring-white/10"><AllModelsChart /></div>
      </Slide>,

      <Slide key="7" kicker="6 · Conclusion" title="What the experiments show">
        <div className="grid gap-4 md:grid-cols-3">
          {[
            ['Patches fixed the encodings', `Mixing patch states raised FRQI to ${p1(v4.frqi?.mean)} and NEQR to ${p1(v4.neqr?.mean)}, from about 60% with whole images.`],
            ['FRQI vs NEQR', `FRQI needs ${v4.frqi_qubits} qubits per patch versus ${v4.neqr_qubits} for NEQR; seed-to-seed spread ±${(100 * (v4.frqi?.std ?? 0)).toFixed(1)} vs ±${(100 * (v4.neqr?.std ?? 0)).toFixed(1)} points.`],
            ['No quantum advantage claimed', `A classical SVM on the same patches reaches ${p1(v4.control?.mean)}; every kernel here has a classical closed form and was simulated on a CPU.`],
          ].map(([t, x], k) => (
            <FadeIn key={t} delay={k * 90}>
              <div className="h-full rounded-2xl bg-white/[0.04] p-5 ring-1 ring-white/10"><div className="text-lg font-semibold text-white">{t}</div><p className="mt-2 text-sm leading-relaxed text-slate-300">{x}</p></div>
            </FadeIn>))}
        </div>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link to="/quantum-v4" className="rounded-xl bg-teal-400 px-4 py-2.5 text-sm font-semibold text-slate-950">Full V4 results</Link>
          <Link to="/" className="rounded-xl bg-white/5 px-4 py-2.5 text-sm text-slate-100 ring-1 ring-white/15">Back to dashboard</Link>
        </div>
      </Slide>,
    ];
    body = slides[i];
  }

  return (
    <div className="flex min-h-screen flex-col bg-[radial-gradient(ellipse_at_top,_#0f1d3a,_#060a14_60%)] text-slate-200" data-testid="present" data-slide={i + 1}>
      <div className="flex items-center justify-between px-6 py-4">
        <div className="text-sm font-semibold text-white">Q-ImageLab <span className="text-teal-300/80">· Protocol V4</span></div>
        <Link to="/" aria-label="Exit presentation" className="inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-sm text-slate-300 hover:bg-white/10"><X size={16} /> Exit</Link>
      </div>
      <main className="flex flex-1 items-center px-6 pb-6 md:px-12" key={i}>{body}</main>
      <div className="flex items-center justify-between px-6 pb-6">
        <button aria-label="Previous slide" onClick={() => go(i - 1)} disabled={i === 0} className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm text-slate-200 ring-1 ring-white/15 disabled:opacity-30"><ChevronLeft size={16} /> Back</button>
        <div className="flex gap-2">{Array.from({ length: N }, (_, k) => (
          <button key={k} aria-label={`Slide ${k + 1}`} onClick={() => go(k)} className={`h-2 rounded-full transition-all ${k === i ? 'w-8 bg-teal-400' : 'w-2 bg-slate-600'}`} />))}</div>
        <button aria-label="Next slide" onClick={() => go(i + 1)} disabled={i === N - 1} className="inline-flex items-center gap-1 rounded-lg bg-teal-400 px-3 py-2 text-sm font-semibold text-slate-950 disabled:opacity-30">Next <ChevronRight size={16} /></button>
      </div>
    </div>
  );
}
