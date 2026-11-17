import { useCallback, useEffect } from 'react';
import type { ReactNode } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';
import { useV2, V2 } from '../api';
import { CLASS_LABEL, ErrorState, Loading, int, pct } from '../ui';
import { FAMILY, FadeIn } from '../theme';
import type { FamilyKey } from '../theme';
import { FamilyBars, bestNames } from './Overview';
import type { Summary } from './Overview';
import type { ReconRecord } from './Encoding';

type DatasetResp = { splits: Record<string, { counts: { train: number; val: number; test: number } }>; counts: Record<string, Record<string, number>> };

function Slide({ kicker, title, children }: { kicker: string; title: string; children: ReactNode }) {
  return (
    <FadeIn>
      <div className="mx-auto w-full max-w-6xl">
        <div className="text-xs font-semibold uppercase tracking-[0.22em] text-cyan-300/80">{kicker}</div>
        <h1 className="mt-2 text-3xl font-semibold leading-tight text-white md:text-5xl">{title}</h1>
        <div className="mt-8">{children}</div>
      </div>
    </FadeIn>
  );
}

function Box({ n, label, sub, tone = '#22d3ee' }: { n: ReactNode; label: string; sub?: string; tone?: string }) {
  return (
    <div className="rounded-2xl bg-white/[0.04] p-5 ring-1 ring-white/10">
      <div className="text-3xl font-bold tabular-nums md:text-4xl" style={{ color: tone }}>{n}</div>
      <div className="mt-1 text-sm font-medium text-slate-100">{label}</div>
      {sub && <div className="mt-0.5 text-xs text-slate-400">{sub}</div>}
    </div>
  );
}

export default function Present() {
  const sum = useV2<Summary>('/summary');
  const ds = useV2<DatasetResp>('/dataset');
  const rec = useV2<{ records: ReconRecord[] }>('/reconstructions');
  const [params, setParams] = useSearchParams();
  const nav = useNavigate();
  const i = Math.max(0, Number(params.get('slide') ?? 1) - 1);
  const N = 6;
  const clamp = (k: number) => String(Math.min(N, Math.max(1, k)));
  // Absolute jump (dots, buttons) and relative step (keys). Steps read the slide from the CURRENT URL so that several
  // fast key presses each advance one slide (a value captured at render time would repeat the same target).
  const go = useCallback((k: number) => setParams({ slide: clamp(k + 1) }), [setParams]);
  // Read the live URL (window.location), not router state: router search params are only refreshed on re-render.
  const step = useCallback((delta: number) => {
    const cur = Number(new URLSearchParams(window.location.search).get('slide') ?? 1);
    setParams({ slide: clamp(cur + delta) });
  }, [setParams]);
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') { e.preventDefault(); step(1); }
      if (e.key === 'ArrowLeft' || e.key === 'PageUp') { e.preventDefault(); step(-1); }
      if (e.key === 'Escape') nav('/');
    };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [step, nav]);

  if (sum.loading || ds.loading || rec.loading) return <div className="grid min-h-screen place-items-center"><Loading /></div>;
  if (sum.error || ds.error || rec.error) return <div className="p-8"><ErrorState error={(sum.error ?? ds.error ?? rec.error)!} /></div>;
  const d = sum.data!;
  if (!d.has_data) return <div className="p-8 text-slate-300">No experiment results available.</div>;
  const split = ds.data ? Object.values(ds.data.splits)[0]?.counts : undefined;
  const recs = rec.data?.records ?? [];
  const frqi = recs.find((r) => r.record_id === 'R-FRQI-8x8');
  const neqr = recs.find((r) => r.record_id === 'R-NEQR-8x8-b4');
  const imgIdx = 24; // a rolled-in scale image of the fixed 30-image subset

  const slides: ReactNode[] = [
    <Slide key="1" kicker="1 · The problem" title="Detecting defects on steel surfaces">
      <div className="grid grid-cols-3 gap-3 md:grid-cols-6">
        {d.dataset.classes.map((c, k) => (
          <FadeIn key={c} delay={k * 60}>
            <figure>
              <img src={`${V2}/dataset/sample/${c}.png`} alt={c} className="aspect-square w-full rounded-xl object-cover ring-1 ring-white/10" />
              <figcaption className="mt-2 text-center text-sm text-slate-200">{CLASS_LABEL[c] ?? c}</figcaption>
            </figure>
          </FadeIn>
        ))}
      </div>
      <div className="mt-8 grid gap-4 md:grid-cols-3">
        <Box n={int(d.dataset.total_images)} label={`${d.dataset.name} images`} sub="200 × 200 grayscale" />
        <Box n={d.dataset.n_classes} label="defect classes" sub="balanced: same number per class" />
        <Box n={d.counts.selected_configurations} label="model configurations compared" sub="classical, quantum, hybrid" tone="#a78bfa" />
      </div>
    </Slide>,

    <Slide key="2" kicker="2 · Fair evaluation" title="The test images were locked away until the very end">
      <div className="grid items-stretch gap-4 md:grid-cols-[1fr_auto_1fr_auto_1fr]">
        <Box n={int(d.dataset.trainval_images)} label="training-folder images" sub="split into neighbouring-image blocks so near-duplicates never cross over" />
        <div className="hidden place-items-center text-3xl text-slate-600 md:grid">→</div>
        <Box n={split ? `${int(split.train)} / ${int(split.val)}` : 'unavailable'} label="train / validation" sub={`best settings chosen on validation · seeds ${d.protocol.seeds.join(', ')}`} />
        <div className="hidden place-items-center text-3xl text-slate-600 md:grid">→</div>
        <Box n={int(d.dataset.locked_test_images)} label="locked test images" sub="each chosen model scored once" tone="#f59e0b" />
      </div>
      <p className="mt-8 max-w-3xl text-lg leading-relaxed text-slate-300">
        Every number in this presentation is accuracy on test images that no model or setting ever saw during development.
        <span className="mt-2 block text-base text-amber-200/90">{d.protocol.execution}</span>
      </p>
    </Slide>,

    <Slide key="3" kicker="3 · Quantum image encoding" title="Storing an image inside qubits">
      <div className="grid gap-5 md:grid-cols-2">
        {[['FRQI', frqi, 'Brightness stored in the angle of one colour qubit', FAMILY.qkc.color], ['NEQR', neqr, 'Brightness stored as bits in intensity qubits', FAMILY.encoding.color]].map(([name, r, desc, col]) => {
          const rr = r as ReconRecord | undefined;
          return (
            <div key={name as string} className="rounded-2xl bg-white/[0.04] p-5 ring-1 ring-white/10">
              <div className="flex items-baseline justify-between"><div className="text-2xl font-semibold" style={{ color: col as string }}>{name as string}</div>
                <div className="text-sm text-slate-400">{rr?.config ? `${rr.config.resolution}×${rr.config.resolution}${rr.config.intensity_bits && name === 'NEQR' ? ` · ${rr.config.intensity_bits}-bit` : ''}` : ''}</div></div>
              <div className="mt-1 text-sm text-slate-300">{desc as string}</div>
              {rr ? (
                <>
                  <div className="mt-4 grid grid-cols-2 gap-3">
                    {['original', 'reconstructed'].map((k) => (
                      <figure key={k}><img alt={`${name} ${k}`} src={`${V2}/reconstructions/${rr.record_id}/render/${imgIdx}/shots1000/${k}.png`} className="w-full rounded-lg ring-1 ring-white/10" style={{ imageRendering: 'pixelated' }} />
                        <figcaption className="mt-1 text-center text-xs text-slate-400">{k === 'original' ? 'input (8×8)' : 'rebuilt from 1,000 measurements'}</figcaption></figure>
                    ))}
                  </div>
                  <div className="mt-4 grid grid-cols-3 gap-2 text-center">
                    <div><div className="text-xl font-semibold text-white">{rr.circuit_stats?.n_qubits ?? 'unavailable'}</div><div className="text-[11px] text-slate-400">qubits</div></div>
                    <div><div className="text-xl font-semibold text-white">{int(rr.circuit_stats?.gates_compiled)}</div><div className="text-[11px] text-slate-400">basic gates</div></div>
                    <div><div className="text-xl font-semibold text-white">{rr.summary?.shots1000?.vs_preprocessed?.mse?.mean?.toExponential(1) ?? 'unavailable'}</div><div className="text-[11px] text-slate-400">error (MSE)</div></div>
                  </div>
                </>
              ) : <div className="mt-4 text-sm text-slate-400">No reconstruction record available.</div>}
            </div>
          );
        })}
      </div>
    </Slide>,

    <Slide key="4" kicker="4 · What we compared" title="Six families of models, the same test images">
      <div className="grid gap-4 md:grid-cols-3">
        {([['classical', 'Classical models'], ['cnn', 'Classical models'], ['qkc', 'Quantum kernel models'], ['vqc', 'Variational quantum classifiers'],
          ['encoding', 'FRQI / NEQR encoding kernels'], ['hybrid', 'Hybrid CNN + quantum models']] as [FamilyKey, string][]).map(([k], j) => {
          const f = FAMILY[k];
          const Icon = f.icon;
          const fam = d.families.find((x) => FAMILY[k].label === x.family);
          return (
            <FadeIn key={k} delay={j * 70}>
              <div className="h-full rounded-2xl p-5 ring-1 ring-white/10" style={{ background: f.soft }}>
                <Icon size={22} style={{ color: f.color }} />
                <div className="mt-3 text-lg font-semibold text-white">{f.label}</div>
                <div className="mt-1 text-sm text-slate-300">{f.blurb}</div>
                <div className="mt-3 text-xs text-slate-400">{fam ? `${fam.n_models} configurations` : ''}</div>
              </div>
            </FadeIn>
          );
        })}
      </div>
    </Slide>,

    <Slide key="5" kicker="5 · Results" title="Best accuracy of each family">
      <div className="rounded-2xl bg-white/[0.03] p-6 ring-1 ring-white/10"><FamilyBars d={d} /></div>
      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <Box n={pct(d.best.overall?.test_accuracy)} label="best overall" sub={bestNames(d.best.overall)} tone={FAMILY.cnn.color} />
        <Box n={pct(d.best.hybrid?.test_accuracy)} label="best hybrid" sub={bestNames(d.best.hybrid)} tone={FAMILY.hybrid.color} />
        <Box n={pct(d.best.quantum?.test_accuracy)} label="best purely quantum" sub={bestNames(d.best.quantum)} tone={FAMILY.qkc.color} />
      </div>
    </Slide>,

    <Slide key="6" kicker="6 · Conclusion" title="What the experiments show">
      <div className="grid gap-4 md:grid-cols-2">
        {d.findings.map((f, k) => (
          <FadeIn key={f.id} delay={k * 70}>
            <div className="h-full rounded-2xl bg-white/[0.04] p-5 ring-1 ring-white/10">
              <div className="text-lg font-semibold text-white">{f.title}</div>
              <p className="mt-2 text-sm leading-relaxed text-slate-300">{f.text}</p>
            </div>
          </FadeIn>
        ))}
      </div>
      <div className="mt-6 flex flex-wrap gap-3">
        <Link to="/models" className="rounded-xl bg-cyan-500 px-4 py-2.5 text-sm font-semibold text-slate-950">Explore all models</Link>
        <Link to="/" className="rounded-xl bg-white/5 px-4 py-2.5 text-sm text-slate-100 ring-1 ring-white/15">Back to dashboard</Link>
      </div>
    </Slide>,
  ];

  return (
    <div className="flex min-h-screen flex-col bg-[radial-gradient(ellipse_at_top,_#0f1d3a,_#060a14_60%)] text-slate-200">
      <div className="flex items-center justify-between px-6 py-4">
        <div className="text-sm font-semibold text-white">Q-ImageLab <span className="text-cyan-300/80">· Protocol V2</span></div>
        <Link to="/" aria-label="Exit presentation" className="inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-sm text-slate-300 hover:bg-white/10"><X size={16} /> Exit</Link>
      </div>
      <main className="flex flex-1 items-center px-6 pb-6 md:px-12" key={i}>{slides[i]}</main>
      <div className="flex items-center justify-between px-6 pb-6">
        <button aria-label="Previous slide" onClick={() => go(i - 1)} disabled={i === 0} className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm text-slate-200 ring-1 ring-white/15 disabled:opacity-30"><ChevronLeft size={16} /> Back</button>
        <div className="flex gap-2">{Array.from({ length: N }, (_, k) => (
          <button key={k} aria-label={`Slide ${k + 1}`} onClick={() => go(k)} className={`h-2 rounded-full transition-all ${k === i ? 'w-8 bg-cyan-400' : 'w-2 bg-slate-600'}`} />))}</div>
        <button aria-label="Next slide" onClick={() => go(i + 1)} disabled={i === N - 1} className="inline-flex items-center gap-1 rounded-lg bg-cyan-500 px-3 py-2 text-sm font-semibold text-slate-950 disabled:opacity-30">Next <ChevronRight size={16} /></button>
      </div>
    </div>
  );
}
