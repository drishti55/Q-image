// Results of every protocol on one page, newest (V4) first and largest. All numbers come from /api/v4/versions,
// which reads the saved aggregates of V2, V3 and V4; nothing is hard-coded here.
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Clapperboard, History, Layers, ShieldCheck, Sparkles } from 'lucide-react';
import { useV4 } from '../api';
import { Gate } from '../ui';
import { FadeIn } from '../theme';

type MS = { mean: number; std?: number; n?: number };
type Row = { name: string; type: 'quantum' | 'hybrid' | 'classical'; group: string; test_accuracy: MS; note: string };
type Cmp = { name: string; diff: number; ci95: [number, number]; p_holm: number };
type Version = {
  id: string; comparable: boolean; latest?: boolean; title: string; what: string; link: string; models: Row[];
  frqi?: MS; neqr?: MS; control?: MS; frqi_qubits?: number; neqr_qubits?: number; frqi_per_seed?: number[]; neqr_per_seed?: number[];
  frqi_group?: string; neqr_group?: string; comparisons?: Cmp[];
};
type Resp = { versions: Version[]; n_test: number; execution: string; same_test_set: string };

// Validated pair (dark surface): FRQI blue / NEQR orange; classical neutral.
const C = { frqi: '#3a8ee6', neqr: '#d96a30', classical: '#8a939d' };
const p1 = (v?: number) => (v == null ? '—' : (100 * v).toFixed(1));
const pp = (v: number) => `${v >= 0 ? '+' : '−'}${Math.abs(100 * v).toFixed(1)} pp`;
const pval = (p: number) => (p < 0.001 ? 'p < 0.001' : `p = ${p.toFixed(3)}`);
const TYPE_CLS: Record<string, string> = {
  quantum: 'bg-cyan-500/10 text-cyan-200 ring-cyan-500/30',
  hybrid: 'bg-violet-500/10 text-violet-200 ring-violet-500/30',
  classical: 'bg-slate-500/10 text-slate-300 ring-slate-500/30',
};

function BigNumber({ label, color, value, sub, from, delta, testid }: {
  label: string; color: string; value: MS; sub: string; from?: { v: string; m: MS }; delta?: Cmp; testid: string;
}) {
  return (
    <div className="relative overflow-hidden rounded-3xl bg-white/[0.04] p-6 ring-1 ring-white/10 md:p-8" data-testid={testid}>
      <div className="absolute inset-x-0 top-0 h-1.5" style={{ background: color }} />
      <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.18em] text-slate-300">
        <span className="h-3 w-3 rounded-sm" style={{ background: color }} />{label}
      </div>
      <div className="mt-2 flex flex-wrap items-baseline gap-x-3">
        <span className="text-7xl font-bold leading-none tracking-tight text-white tabular-nums md:text-8xl">{p1(value.mean)}<span className="text-4xl md:text-5xl">%</span></span>
        <span className="text-lg text-slate-400 tabular-nums">± {p1(value.std)}</span>
      </div>
      <div className="mt-2 text-sm text-slate-300">{sub}</div>
      {from && (
        <div className="mt-4 flex flex-wrap items-center gap-2 rounded-xl bg-black/20 px-3 py-2 text-sm">
          <span className="text-slate-400">{from.v}</span>
          <span className="tabular-nums text-slate-400 line-through decoration-slate-500">{p1(from.m.mean)}%</span>
          <ArrowRight size={15} className="text-slate-400" />
          <span className="font-semibold tabular-nums text-white">{p1(value.mean)}%</span>
          {delta && <span className="ml-auto rounded-md bg-emerald-500/15 px-2 py-0.5 font-semibold tabular-nums text-emerald-300">{pp(delta.diff)} · {pval(delta.p_holm)}</span>}
        </div>
      )}
    </div>
  );
}

/** Grouped bars: FRQI and NEQR test accuracy in each comparable protocol (one axis, 0–100 %). */
function AcrossVersions({ vs }: { vs: Version[] }) {
  const [hover, setHover] = useState<string | null>(null);
  const rows = vs.filter((v) => v.comparable && v.frqi && v.neqr);
  const ticks = [0, 25, 50, 75, 100];
  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-4 text-xs text-slate-300" aria-label="Legend">
        <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: C.frqi }} />FRQI</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: C.neqr }} />NEQR</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-0 w-4 border-t border-dashed border-slate-500" />chance (16.7 %)</span>
      </div>
      <div className="relative h-72 pl-9" role="img" aria-label="FRQI and NEQR locked-test accuracy for protocols V2, V3 and V4">
        {ticks.map((t) => (
          <div key={t} className="absolute left-9 right-0 border-t border-slate-800" style={{ bottom: `${t}%` }}>
            <span className="absolute -left-9 -translate-y-1/2 text-[11px] tabular-nums text-slate-500">{t}%</span>
          </div>
        ))}
        <div className="absolute left-9 right-0 border-t border-dashed border-slate-500/70" style={{ bottom: `${100 / 6}%` }} />
        <div className="relative grid h-full items-end" style={{ gridTemplateColumns: `repeat(${rows.length}, minmax(0, 1fr))` }}>
          {rows.map((v) => (
            <div key={v.id} className="flex h-full items-end justify-center gap-1.5 px-2 sm:gap-3">
              {([['FRQI', v.frqi!, C.frqi], ['NEQR', v.neqr!, C.neqr]] as const).map(([lab, m, col]) => {
                const k = `${v.id}-${lab}`;
                return (
                  <div key={k} className="relative flex h-full w-full max-w-[64px] items-end" onMouseEnter={() => setHover(k)} onMouseLeave={() => setHover(null)}>
                    <div className={`w-full rounded-t-[4px] transition-opacity ${hover && hover !== k ? 'opacity-50' : ''}`}
                      style={{ height: `${100 * m.mean}%`, background: col, outline: v.latest ? '2px solid rgba(255,255,255,.55)' : undefined, outlineOffset: 2 }} />
                    <span className={`absolute left-1/2 -translate-x-1/2 whitespace-nowrap tabular-nums ${v.latest ? 'text-sm font-bold text-white' : 'text-[11px] text-slate-300'}`}
                      style={{ bottom: `calc(${100 * m.mean}% + 6px)` }}>{p1(m.mean)}</span>
                    {hover === k && (
                      <div className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-8 w-44 -translate-x-1/2 rounded-lg bg-slate-900 px-3 py-2 text-xs text-slate-200 shadow-xl ring-1 ring-slate-700">
                        <div className="font-semibold">{v.id} · {lab}</div>
                        <div className="tabular-nums">{p1(m.mean)} ± {p1(m.std)} % test accuracy</div>
                        <div className="text-slate-400">3 seeds × 360 locked-test images</div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
      <div className="grid pl-9 pt-2" style={{ gridTemplateColumns: `repeat(${rows.length}, minmax(0, 1fr))` }}>
        {rows.map((v) => (
          <div key={v.id} className="text-center">
            <div className={v.latest ? 'text-base font-bold text-white' : 'text-sm font-medium text-slate-300'}>{v.id}{v.latest && ' · latest'}</div>
            <div className="mx-auto max-w-[180px] text-[11px] leading-tight text-slate-500">{v.title}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function VersionCard({ v }: { v: Version }) {
  const best = v.models.length ? v.models.reduce((a, b) => (b.test_accuracy.mean > a.test_accuracy.mean ? b : a)) : null;
  return (
    <div className={`flex h-full flex-col rounded-2xl p-5 ring-1 ${v.latest ? 'bg-cyan-500/[0.07] ring-cyan-400/50' : v.comparable ? 'bg-slate-900/50 ring-slate-800' : 'bg-amber-500/[0.04] ring-amber-500/25'}`}
      data-testid={`version-card-${v.id}`}>
      <div className="flex items-center gap-2">
        <span className={`rounded-lg px-2.5 py-1 text-sm font-bold ${v.latest ? 'bg-cyan-400 text-slate-950' : 'bg-slate-800 text-slate-200'}`}>{v.id}</span>
        {v.latest && <span className="text-[11px] font-semibold uppercase tracking-wider text-cyan-300">latest</span>}
        {!v.comparable && <span className="text-[11px] font-semibold uppercase tracking-wider text-amber-300">not comparable</span>}
      </div>
      <div className="mt-3 text-sm font-semibold text-slate-100">{v.title}</div>
      <p className="mt-1 text-xs leading-relaxed text-slate-400">{v.what}</p>
      {v.comparable && v.frqi && v.neqr ? (
        <div className="mt-4 grid grid-cols-2 gap-2">
          {([['FRQI', v.frqi, C.frqi], ['NEQR', v.neqr, C.neqr]] as const).map(([l, m, col]) => (
            <div key={l} className="rounded-xl bg-black/20 px-3 py-2">
              <div className="flex items-center gap-1.5 text-[11px] text-slate-400"><span className="h-2 w-2 rounded-sm" style={{ background: col }} />{l}</div>
              <div className={`font-semibold tabular-nums text-white ${v.latest ? 'text-2xl' : 'text-xl'}`}>{p1(m.mean)}%</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-4 rounded-xl bg-black/20 px-3 py-2 text-xs text-amber-100/80">No locked test set, so its accuracies cannot be compared with V2–V4. Kept read-only as history.</div>
      )}
      {best && <div className="mt-2 text-[11px] text-slate-500">Best model in {v.id}: <span className="text-slate-300">{best.name} {p1(best.test_accuracy.mean)}%</span></div>}
      <Link to={v.link} className="mt-auto inline-flex items-center gap-1 pt-4 text-xs font-medium text-cyan-300 hover:underline">
        Open {v.id} details <ArrowRight size={13} />
      </Link>
    </div>
  );
}

export default function AllVersions() {
  const st = useV4<Resp>('/versions');
  return (
    <Gate state={st}>
      {(d) => {
        const v4 = d.versions.find((v) => v.latest)!;
        const v2 = d.versions.find((v) => v.id === 'V2');
        const cmp = (s: string) => v4.comparisons?.find((c) => c.name.startsWith(s));
        const ctrl = cmp('V4 FRQI vs classical patch-moment');
        const fvn = cmp('V4 FRQI vs V4 NEQR');
        const all = d.versions.filter((v) => v.comparable).flatMap((v) => v.models.map((m) => ({ ...m, v: v.id, latest: !!v.latest })));
        return (
          <div className="space-y-8">
            {/* ── V4, big ── */}
            <FadeIn>
              <section className="relative overflow-hidden rounded-3xl border border-cyan-400/30 bg-gradient-to-br from-[#0b1a33] via-[#0a1226] to-[#120c2a] p-6 md:p-10" data-testid="v4-hero">
                <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-cyan-500/10 blur-3xl" />
                <div className="relative">
                  <div className="inline-flex items-center gap-2 rounded-full bg-cyan-400 px-3 py-1 text-xs font-bold uppercase tracking-[0.16em] text-slate-950">
                    <Sparkles size={14} /> Latest result · Protocol V4
                  </div>
                  <h1 className="mt-4 max-w-4xl text-3xl font-semibold leading-tight text-white md:text-5xl">{v4.title}</h1>
                  <p className="mt-3 max-w-3xl text-base leading-relaxed text-slate-300">{v4.what}</p>
                  <div className="mt-7 grid gap-5 lg:grid-cols-2">
                    <BigNumber testid="hero-frqi" label="FRQI" color={C.frqi} value={v4.frqi!}
                      sub={`Test accuracy on ${d.n_test} unseen images · ${v4.frqi_qubits} qubits per patch · seeds ${v4.frqi_per_seed?.map((x) => p1(x)).join(' / ')}`}
                      from={v2?.frqi ? { v: 'V2', m: v2.frqi } : undefined} delta={cmp('V4 FRQI vs V2 FRQI')} />
                    <BigNumber testid="hero-neqr" label="NEQR" color={C.neqr} value={v4.neqr!}
                      sub={`Test accuracy on ${d.n_test} unseen images · ${v4.neqr_qubits} qubits per patch · seeds ${v4.neqr_per_seed?.map((x) => p1(x)).join(' / ')}`}
                      from={v2?.neqr ? { v: 'V2', m: v2.neqr } : undefined} delta={cmp('V4 NEQR vs V2 NEQR')} />
                  </div>
                  <div className="mt-5 grid gap-3 text-sm sm:grid-cols-3">
                    <div className="rounded-2xl bg-white/[0.03] px-4 py-3 ring-1 ring-white/10">
                      <div className="text-xs text-slate-400">Classical SVM on the same patches</div>
                      <div className="text-2xl font-semibold tabular-nums text-white">{p1(v4.control?.mean)}%</div>
                      {ctrl && <div className="text-xs text-slate-400">FRQI {pp(ctrl.diff)} · {pval(ctrl.p_holm)} · {ctrl.p_holm < 0.05 ? 'significant' : 'not significant'}</div>}
                    </div>
                    <div className="rounded-2xl bg-white/[0.03] px-4 py-3 ring-1 ring-white/10">
                      <div className="text-xs text-slate-400">FRQI vs NEQR</div>
                      <div className="text-2xl font-semibold tabular-nums text-white">{fvn ? pp(fvn.diff) : '—'}</div>
                      {fvn && <div className="text-xs text-slate-400">{pval(fvn.p_holm)} · Holm-corrected · FRQI is more stable across seeds</div>}
                    </div>
                    <div className="rounded-2xl bg-white/[0.03] px-4 py-3 ring-1 ring-white/10">
                      <div className="text-xs text-slate-400">Best model in any version</div>
                      {(() => { const b = all.reduce((a, x) => (x.test_accuracy.mean > a.test_accuracy.mean ? x : a)); return (<>
                        <div className="text-2xl font-semibold tabular-nums text-white">{p1(b.test_accuracy.mean)}%</div>
                        <div className="text-xs text-slate-400">{b.v} · {b.name} ({b.type})</div></>); })()}
                    </div>
                  </div>
                  <p className="mt-5 flex max-w-4xl items-start gap-2 text-sm text-amber-200/90">
                    <ShieldCheck size={16} className="mt-0.5 shrink-0" />
                    {d.execution} Settings chosen on validation data only, then tested once. FRQI is not significantly better than the classical model on the same patches, so no quantum advantage is claimed.
                  </p>
                  <div className="mt-6 flex flex-wrap gap-3">
                    <Link to="/quantum-v4" className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-cyan-400">Full V4 results <ArrowRight size={16} /></Link>
                    <Link to="/how-it-works" className="inline-flex items-center gap-2 rounded-xl bg-white/5 px-4 py-2.5 text-sm font-medium text-slate-100 ring-1 ring-white/15 hover:bg-white/10"><Clapperboard size={16} /> Watch it work on a real image</Link>
                    <Link to="/reconstruction-full" className="inline-flex items-center gap-2 rounded-xl bg-white/5 px-4 py-2.5 text-sm font-medium text-slate-100 ring-1 ring-white/15 hover:bg-white/10"><Layers size={16} /> Reconstruction of all 1,800 images</Link>
                  </div>
                </div>
              </section>
            </FadeIn>

            {/* ── across versions ── */}
            <section className="rounded-2xl bg-slate-900/40 p-5 ring-1 ring-slate-800 md:p-6">
              <h2 className="text-lg font-semibold text-white">FRQI and NEQR accuracy in every version</h2>
              <p className="mb-5 text-sm text-slate-400">{d.same_test_set} V4 is outlined.</p>
              <AcrossVersions vs={d.versions} />
            </section>

            {/* ── version cards ── */}
            <section>
              <h2 className="mb-4 text-lg font-semibold text-white">What each version did</h2>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {[...d.versions].reverse().map((v, i) => <FadeIn key={v.id} delay={i * 60}><VersionCard v={v} /></FadeIn>)}
              </div>
            </section>

            {/* ── every key model ── */}
            <section className="rounded-2xl bg-slate-900/40 p-5 ring-1 ring-slate-800 md:p-6">
              <h2 className="text-lg font-semibold text-white">Key models from every version</h2>
              <p className="mb-4 text-sm text-slate-400">Test accuracy, mean ± standard deviation over 3 seeds, on the same {d.n_test} locked-test images. V4 rows are highlighted.</p>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-sm tabular-nums" data-testid="all-versions-table">
                  <thead className="text-left text-xs text-slate-500">
                    <tr><th className="px-2 py-2 font-medium">Version</th><th className="px-2 font-medium">Model</th><th className="px-2 font-medium">Type</th><th className="px-2 font-medium">Test accuracy %</th><th className="w-[30%] px-2 font-medium" /></tr>
                  </thead>
                  <tbody>
                    {[...d.versions].reverse().filter((v) => v.comparable).flatMap((v) => v.models.map((m, i) => (
                      <tr key={`${v.id}-${m.group}`} className={`border-t border-slate-800/70 ${v.latest ? 'bg-cyan-500/[0.06]' : ''}`}>
                        <td className="px-2 py-2">{i === 0 && <span className={`rounded-md px-2 py-0.5 text-xs font-bold ${v.latest ? 'bg-cyan-400 text-slate-950' : 'bg-slate-800 text-slate-200'}`}>{v.id}</span>}</td>
                        <td className="px-2 py-2">
                          <div className={v.latest ? 'font-semibold text-white' : 'text-slate-200'}>{m.name}</div>
                          {m.note && <div className="text-[11px] text-slate-500">{m.note}</div>}
                        </td>
                        <td className="px-2"><span className={`rounded-md px-2 py-0.5 text-[11px] ring-1 ${TYPE_CLS[m.type]}`}>{m.type}</span></td>
                        <td className={`px-2 ${v.latest ? 'text-base font-bold text-white' : 'text-slate-200'}`}>{p1(m.test_accuracy.mean)} <span className="text-xs font-normal text-slate-500">± {p1(m.test_accuracy.std)}</span></td>
                        <td className="px-2">
                          <div className="h-2 rounded-full bg-slate-800">
                            <div className="h-2 rounded-full" style={{ width: `${100 * m.test_accuracy.mean}%`,
                              background: m.type === 'classical' ? C.classical : /NEQR/.test(m.name) ? C.neqr : /FRQI/.test(m.name) ? C.frqi : '#22b8cf' }} />
                          </div>
                        </td>
                      </tr>
                    )))}
                  </tbody>
                </table>
              </div>
              <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-400">
                <Link to="/historical-v0" className="inline-flex items-center gap-1 text-amber-300 hover:underline"><History size={13} /> V0 history (not comparable)</Link>
                <Link to="/quantum-vs-classical" className="text-cyan-300 hover:underline">V2: Quantum vs Classical →</Link>
                <Link to="/quantum-v3" className="text-cyan-300 hover:underline">V3 results →</Link>
                <Link to="/quantum-v4" className="text-cyan-300 hover:underline">V4 results →</Link>
                <Link to="/compare" className="text-cyan-300 hover:underline">Full model comparison table →</Link>
              </div>
            </section>
          </div>
        );
      }}
    </Gate>
  );
}
