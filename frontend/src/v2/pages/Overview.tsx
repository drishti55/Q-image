import { Link } from 'react-router-dom';
import { ArrowRight, Atom, Cpu, Image as ImageIcon, Play, Scale, ShieldCheck } from 'lucide-react';
import { useV2 } from '../api';
import type { MS } from '../api';
import { Gate, int, msPct, pct } from '../ui';
import { AccBar, Collapsible, FAMILY, FadeIn, familyOfSummary } from '../theme';

type BestModel = { group: string; display_name: string; category: string; test_accuracy: MS; test_f1_macro: MS; execution: string; n_qubits: number | null };
type BestEntry = { models: BestModel[]; test_accuracy: number } | null;
export type Summary = {
  has_data: boolean;
  dataset: { name: string; manifest_id: string; total_images: number; classes: string[]; n_classes: number; locked_test_images: number; trainval_images: number };
  protocol: { locked_test: string; selection: string; seeds: number[]; execution: string };
  counts: { selected_configurations: number; experiments: { completed: number; failed: number; total: number }; reconstruction_runs: number;
    reconstruction_failed: number; quantum_configurations: number; classical_configurations: number; by_category: Record<string, number> };
  best: { overall: BestEntry; quantum: BestEntry; hybrid: BestEntry; classical_pixel: BestEntry };
  families: { family: string; n_models: number; best_name?: string; best_group?: string; best_test_accuracy?: MS; best_test_f1_macro?: MS; median_test_accuracy?: number }[];
  findings: { id: string; title: string; text: string; groups: string[] }[];
};

export const bestNames = (e: BestEntry) => (e ? e.models.map((m) => m.display_name).join(' / ') : 'unavailable');

export function FamilyBars({ d }: { d: Summary }) {
  const rows = d.families.filter((f) => f.n_models && f.best_test_accuracy).sort((a, b) => (b.best_test_accuracy!.mean ?? 0) - (a.best_test_accuracy!.mean ?? 0));
  return (
    <div className="space-y-3">
      {rows.map((f, i) => {
        const fam = FAMILY[familyOfSummary(f.family)];
        const Icon = fam.icon;
        return (
          <FadeIn key={f.family} delay={i * 70}>
            <div className="grid grid-cols-[minmax(0,1fr)] gap-1.5 sm:grid-cols-[250px_minmax(0,1fr)] sm:items-center sm:gap-4">
              <div className="flex items-center gap-2.5 min-w-0">
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg" style={{ background: fam.soft, color: fam.color }}><Icon size={16} /></span>
                <div className="min-w-0">
                  <div className="text-sm font-medium text-slate-100 truncate">{fam.label}</div>
                  <div className="text-[11px] text-slate-500 truncate" title={f.best_name}>best: {f.best_name}</div>
                </div>
              </div>
              <AccBar value={f.best_test_accuracy!.mean} color={fam.color} />
            </div>
          </FadeIn>
        );
      })}
    </div>
  );
}

export default function Overview() {
  const s = useV2<Summary>('/summary');
  return (
    <Gate state={s} empty={(d) => !d.has_data}>
      {(d) => {
        const take = ['cnn_features', 'no_advantage', 'vqc'].map((id) => d.findings.find((f) => f.id === id)).filter(Boolean) as Summary['findings'];
        const more = d.findings.filter((f) => !take.includes(f));
        const icons = [ImageIcon, Scale, Cpu];
        return (
          <div className="space-y-8">
            <FadeIn>
              <section className="relative overflow-hidden rounded-3xl border border-cyan-500/20 bg-gradient-to-br from-[#0b1a33] via-[#0a1226] to-[#120c2a] p-6 md:p-10">
                <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-cyan-500/10 blur-3xl" />
                <div className="pointer-events-none absolute -bottom-24 left-1/3 h-72 w-72 rounded-full bg-violet-500/10 blur-3xl" />
                <div className="relative">
                  <div className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300/80">Q-ImageLab · Protocol V2 · {d.dataset.name}</div>
                  <h1 className="mt-3 max-w-3xl text-2xl font-semibold leading-tight text-white md:text-4xl">
                    Can quantum machine learning recognise steel surface defects?
                  </h1>
                  <p className="mt-2 text-sm text-amber-200/90">{d.protocol.execution}</p>
                  <div className="mt-6 grid max-w-4xl gap-4 md:grid-cols-2">
                    <div className="rounded-2xl bg-white/[0.04] p-5 ring-1 ring-white/10">
                      <div className="text-xs text-slate-400">Best model overall</div>
                      <div className="mt-1 text-4xl font-bold tabular-nums" style={{ color: FAMILY.cnn.color }}>{pct(d.best.overall?.test_accuracy)}</div>
                      <div className="mt-1 text-sm text-slate-200">{bestNames(d.best.overall)}</div>
                      <div className="text-xs text-slate-500">classical deep features</div>
                    </div>
                    <div className="rounded-2xl bg-white/[0.04] p-5 ring-1 ring-white/10">
                      <div className="text-xs text-slate-400">Best purely quantum model</div>
                      <div className="mt-1 text-4xl font-bold tabular-nums" style={{ color: FAMILY.qkc.color }}>{pct(d.best.quantum?.test_accuracy)}</div>
                      <div className="mt-1 text-sm text-slate-200">{bestNames(d.best.quantum)}</div>
                      <div className="text-xs text-slate-500">simulated, exact statevector</div>
                    </div>
                  </div>
                  {d.best.overall && d.best.quantum && (
                    <p className="mt-5 max-w-3xl text-sm leading-relaxed text-slate-300">
                      The best purely quantum model is {((d.best.overall.test_accuracy - d.best.quantum.test_accuracy) * 100).toFixed(1)} percentage
                      points behind the best model.{' '}
                      {d.findings.find((f) => f.id === 'no_advantage')?.title ?? ''}
                      {d.findings.find((f) => f.id === 'no_advantage') ? '. ' : ''}
                      {d.findings.find((f) => f.id === 'qkc_competitive')?.title ?? ''}{d.findings.find((f) => f.id === 'qkc_competitive') ? '.' : ''}
                    </p>
                  )}
                  <div className="mt-6 flex flex-wrap gap-3">
                    <Link to="/present" className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-cyan-400">
                      <Play size={16} /> Start presentation
                    </Link>
                    <Link to="/models" className="inline-flex items-center gap-2 rounded-xl bg-white/5 px-4 py-2.5 text-sm font-medium text-slate-100 ring-1 ring-white/15 hover:bg-white/10">
                      Compare all {d.counts.selected_configurations} models <ArrowRight size={16} />
                    </Link>
                  </div>
                </div>
              </section>
            </FadeIn>

            <FadeIn delay={80}>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                {[[int(d.counts.selected_configurations), 'models compared'], [int(d.dataset.locked_test_images), 'unseen test images'],
                  [int(d.dataset.n_classes), 'defect classes'], [`${int(d.counts.experiments.failed)} / ${int(d.counts.experiments.total)}`, 'failed runs']].map(([v, l]) => (
                  <div key={l} className="rounded-2xl bg-slate-900/50 px-5 py-4 ring-1 ring-slate-800">
                    <div className="text-2xl font-semibold text-white tabular-nums">{v}</div>
                    <div className="text-xs text-slate-400">{l}</div>
                  </div>
                ))}
              </div>
            </FadeIn>

            <section>
              <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
                <div>
                  <h2 className="text-lg font-semibold text-white">How each family of models performed</h2>
                  <p className="text-sm text-slate-400">Best model of each family · accuracy on the {d.dataset.locked_test_images} locked test images</p>
                </div>
                <Link to="/models" className="text-sm text-cyan-300 hover:underline">See every model →</Link>
              </div>
              <div className="rounded-2xl bg-slate-900/40 p-5 ring-1 ring-slate-800"><FamilyBars d={d} /></div>
            </section>

            <section>
              <h2 className="mb-4 text-lg font-semibold text-white">Three things to remember</h2>
              <div className="grid gap-4 md:grid-cols-3">
                {take.map((f, i) => {
                  const Icon = icons[i];
                  return (
                    <FadeIn key={f.id} delay={i * 90}>
                      <div className="h-full rounded-2xl bg-slate-900/50 p-5 ring-1 ring-slate-800">
                        <div className="flex items-center gap-3">
                          <span className="grid h-9 w-9 place-items-center rounded-xl bg-cyan-500/10 text-sm font-bold text-cyan-300">{i + 1}</span>
                          <Icon size={18} className="text-slate-500" />
                        </div>
                        <div className="mt-3 text-base font-semibold text-slate-100">{f.title}</div>
                        <p className="mt-2 text-sm leading-relaxed text-slate-400">{f.text}</p>
                      </div>
                    </FadeIn>
                  );
                })}
              </div>
            </section>

            <section>
              <h2 className="mb-4 text-lg font-semibold text-white">Explore</h2>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {([['/encoding', Atom, 'Quantum image encoding', 'How FRQI and NEQR store an image in qubits'],
                  ['/circuits', Cpu, 'Quantum circuits', 'The exact circuits that were simulated'],
                  ['/reconstruction', ImageIcon, 'Reconstruction studio', 'Images rebuilt from quantum states'],
                  ['/classification', ShieldCheck, 'Classification analysis', 'Which defects each model gets right']] as const).map(([to, Icon, t, s2]) => (
                  <Link key={to} to={to} className="group rounded-2xl bg-slate-900/40 p-5 ring-1 ring-slate-800 transition hover:ring-cyan-500/40">
                    <Icon size={20} className="text-cyan-300" />
                    <div className="mt-3 text-sm font-semibold text-slate-100">{t}</div>
                    <div className="mt-1 text-xs text-slate-400">{s2}</div>
                  </Link>
                ))}
              </div>
            </section>

            <div className="space-y-3">
              {more.length > 0 && (
                <Collapsible title="More findings" hint="Shot noise, reconstruction vs classification, kernel comparisons">
                  <div className="grid gap-3 md:grid-cols-2">
                    {more.map((f) => (
                      <div key={f.id} className="rounded-xl bg-slate-950/40 p-4 ring-1 ring-slate-800">
                        <div className="text-sm font-semibold text-slate-100">{f.title}</div>
                        <p className="mt-1.5 text-sm text-slate-400">{f.text}</p>
                      </div>
                    ))}
                  </div>
                </Collapsible>
              )}
              <Collapsible title="Methodology and run statistics" hint="Protocol, dataset manifest and every count behind this page">
                <div className="grid gap-4 text-sm text-slate-300 md:grid-cols-2">
                  <ul className="space-y-1.5">
                    <li><span className="text-slate-500">Dataset:</span> {d.dataset.name}, {int(d.dataset.total_images)} images, {d.dataset.n_classes} classes ({d.dataset.classes.join(', ').replace(/_/g, ' ')}); manifest {d.dataset.manifest_id}</li>
                    <li><span className="text-slate-500">Locked test:</span> {d.protocol.locked_test} ({d.dataset.locked_test_images} images)</li>
                    <li><span className="text-slate-500">Model selection:</span> {d.protocol.selection}</li>
                    <li className="text-amber-200/90">{d.protocol.execution}</li>
                  </ul>
                  <ul className="space-y-1.5">
                    <li><span className="text-slate-500">Selected configurations:</span> {d.counts.selected_configurations} ({d.counts.quantum_configurations} quantum / hybrid, {d.counts.classical_configurations} classical)</li>
                    <li><span className="text-slate-500">Experiment runs:</span> {int(d.counts.experiments.completed)} completed, {int(d.counts.experiments.failed)} failed</li>
                    <li><span className="text-slate-500">Reconstruction runs:</span> {d.counts.reconstruction_runs} ({d.counts.reconstruction_failed} failed)</li>
                    <li><span className="text-slate-500">Best hybrid:</span> {bestNames(d.best.hybrid)} — {pct(d.best.hybrid?.test_accuracy)}</li>
                    <li><span className="text-slate-500">Best classical on pixels:</span> {bestNames(d.best.classical_pixel)} — {pct(d.best.classical_pixel?.test_accuracy)}</li>
                    <li><span className="text-slate-500">Best overall macro-F1:</span> {msPct(d.best.overall?.models[0].test_f1_macro)}</li>
                  </ul>
                </div>
              </Collapsible>
            </div>
          </div>
        );
      }}
    </Gate>
  );
}
