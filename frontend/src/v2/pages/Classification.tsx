import { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useV2 } from '../api';
import type { Model, ModelsResponse } from '../api';
import { Badge, CLASSES, CLASS_LABEL, CATEGORY_TONE, Card, ConfusionMatrix, ExecBadge, Gate, Loading, PageHeader, Stat, UNAVAILABLE, chartTheme, msNum, msPct, num, pct , fmt } from '../ui';
import { Collapsible } from '../theme';

type SeedDetail = { seed: number; experiment_id: string; test_metrics: { per_class: Record<string, { precision: number; recall: number; f1: number; support: number }>;
  confusion_matrix: number[][]; bootstrap_ci?: { accuracy: [number, number]; f1_macro: [number, number] }; accuracy: number; f1_macro: number; precision_macro: number; recall_macro: number } | null;
  val: Record<string, number> | null };
type Detail = Model & { seeds: SeedDetail[]; selection: { criterion: string; n_candidates: number } };
type PerClass = { rows: { group: string; display_name: string; category: string; feature_source: string; execution: string; per_class_f1: Record<string, number> }[] };

function ModelView({ group }: { group: string }) {
  const st = useV2<Detail>(`/models/${encodeURIComponent(group)}`);
  const [seed, setSeed] = useState(0);
  return (
    <Gate state={st}>
      {(d) => {
        const seeds = d.seeds.filter((s) => s.test_metrics);
        const perClass = CLASSES.map((c) => {
          const v = (k: 'precision' | 'recall' | 'f1') => { const a = seeds.map((s) => s.test_metrics!.per_class[c]?.[k]).filter((x) => x !== undefined); return a.length ? a.reduce((x, y) => x + y, 0) / a.length : null; };
          return { cls: CLASS_LABEL[c], precision: v('precision'), recall: v('recall'), f1: v('f1'), support: seeds[0]?.test_metrics?.per_class[c]?.support ?? null };
        });
        const cur = seeds.find((s) => s.seed === seed) ?? seeds[0];
        return (
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-semibold text-slate-50">{d.display_name}</h2>
              <Badge tone={CATEGORY_TONE[d.category]}>{d.category}</Badge><ExecBadge execution={d.execution} />
              <Link to={`/models?focus=${d.group}`} className="text-xs text-cyan-300 hover:underline">open in Model Comparison</Link>
            </div>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <Stat label="Test accuracy" value={msPct(d.test_accuracy)} hint={`${d.n_test} locked test images · ${d.n_seeds} seeds`} />
              <Stat label="Macro precision" value={msNum(d.test_precision_macro)} />
              <Stat label="Macro recall" value={msNum(d.test_recall_macro)} />
              <Stat label="Macro-F1" value={msNum(d.test_f1_macro)} hint={`val ${msNum(d.val_f1_macro)}`} />
            </div>
            <div className="grid gap-5 xl:grid-cols-2">
              <Card title="Per-class precision, recall and F1" subtitle="Locked test, mean over seeds.">
                <div className="h-64"><ResponsiveContainer><BarChart data={perClass}>
                  <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} vertical={false} />
                  <XAxis dataKey="cls" interval={0} tick={{ fontSize: 10, fill: chartTheme.axis }} />
                  <YAxis domain={[0, 1]} tick={{ fontSize: 10, fill: chartTheme.axis }} />
                  <Tooltip contentStyle={chartTheme.tooltip} formatter={fmt((v) => num(v))} /><Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="precision" fill="#38bdf8" /><Bar dataKey="recall" fill="#fbbf24" /><Bar dataKey="f1" name="F1" fill="#a78bfa" />
                </BarChart></ResponsiveContainer></div>
                <table className="mt-2 w-full text-xs tabular-nums">
                  <thead className="text-left text-slate-500"><tr><th className="py-1">Class</th><th>Precision</th><th>Recall</th><th>F1</th><th>Support</th></tr></thead>
                  <tbody className="divide-y divide-slate-800/60">{perClass.map((r) => (
                    <tr key={r.cls} className={r.f1 !== null && r.f1 < 0.5 ? 'text-rose-300' : ''}><td className="py-1">{r.cls}</td><td>{num(r.precision)}</td><td>{num(r.recall)}</td><td>{num(r.f1)}</td><td>{r.support ?? UNAVAILABLE}</td></tr>))}</tbody>
                </table>
              </Card>
              <Card title="Confusion matrix (locked test)" actions={
                <div className="flex gap-1">{seeds.map((s) => <button key={s.seed} onClick={() => setSeed(s.seed)} className={`rounded-md border px-2 py-0.5 text-xs ${cur?.seed === s.seed ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-200' : 'border-slate-700 text-slate-400'}`}>seed {s.seed}</button>)}</div>}>
                <ConfusionMatrix cm={cur?.test_metrics?.confusion_matrix} title={`Seed ${cur?.seed}`} />
              </Card>
            </div>
            <Card title="Seed-wise performance" subtitle={d.selection?.criterion}>
              <table className="w-full text-xs tabular-nums">
                <thead className="text-left text-slate-500"><tr><th className="py-1">Seed</th><th>Experiment</th><th>Val macro-F1</th><th>Test accuracy</th><th>95% CI accuracy</th><th>Test macro-F1</th><th>95% CI macro-F1</th></tr></thead>
                <tbody className="divide-y divide-slate-800/60">{d.seeds.map((s) => (
                  <tr key={s.seed}><td className="py-1.5">{s.seed}</td>
                    <td><Link to={`/experiments/${encodeURIComponent(s.experiment_id)}`} className="text-cyan-300 hover:underline">{s.experiment_id.split('__').slice(1).join('__')}</Link></td>
                    <td>{num(s.val?.f1_macro)}</td><td>{pct(s.test_metrics?.accuracy)}</td>
                    <td>{s.test_metrics?.bootstrap_ci ? `${pct(s.test_metrics.bootstrap_ci.accuracy[0])} – ${pct(s.test_metrics.bootstrap_ci.accuracy[1])}` : UNAVAILABLE}</td>
                    <td>{num(s.test_metrics?.f1_macro)}</td>
                    <td>{s.test_metrics?.bootstrap_ci ? `${num(s.test_metrics.bootstrap_ci.f1_macro[0])} – ${num(s.test_metrics.bootstrap_ci.f1_macro[1])}` : UNAVAILABLE}</td></tr>))}</tbody>
              </table>
            </Card>
          </div>
        );
      }}
    </Gate>
  );
}

function WeakClasses() {
  const st = useV2<PerClass>('/per-class');
  const [src, setSrc] = useState('pixels');
  return (
    <Card title="Weak classes: rolled-in scale and inclusion"
      subtitle="Test F1 per class (mean over seeds) for every selected configuration. Pixel-based models — quantum or classical — largely fail on rolled-in scale and inclusion; CNN features recover them.">
      <Gate state={st} empty={(d) => !d.rows.length}>
        {(d) => {
          const isPix = (r: PerClass['rows'][0]) => r.feature_source.startsWith('Pixels') || r.feature_source.startsWith('Raw');
          const rows = d.rows.filter((r) => (src === 'pixels' ? isPix(r) : !isPix(r)) && r.execution !== '' && !r.execution.startsWith('finite'))
            .sort((a, b) => (b.per_class_f1['rolled-in_scale'] ?? 0) - (a.per_class_f1['rolled-in_scale'] ?? 0));
          const mean = (c: string, f: (r: PerClass['rows'][0]) => boolean) => { const v = d.rows.filter(f).map((r) => r.per_class_f1[c]).filter((x) => x !== undefined); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null; };
          return (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <Stat label="Rolled-in scale F1 · pixel models (mean)" value={num(mean('rolled-in_scale', isPix))} />
                <Stat label="Rolled-in scale F1 · CNN-feature models" value={num(mean('rolled-in_scale', (r) => !isPix(r)))} />
                <Stat label="Inclusion F1 · pixel models (mean)" value={num(mean('inclusion', isPix))} />
                <Stat label="Inclusion F1 · CNN-feature models" value={num(mean('inclusion', (r) => !isPix(r)))} />
              </div>
              <div className="flex gap-1.5">{[['pixels', 'Pixel-based inputs'], ['cnn', 'CNN-based inputs']].map(([k, l]) => (
                <button key={k} onClick={() => setSrc(k)} className={`rounded-md border px-2.5 py-1 text-xs ${src === k ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-200' : 'border-slate-700 text-slate-400'}`}>{l}</button>))}</div>
              <Collapsible title={`Per-class F1 of every ${src === 'pixels' ? 'pixel-based' : 'CNN-based'} model`} hint="Red < 0.3 · amber < 0.6 · green ≥ 0.6">
              <div className="max-h-[420px] overflow-auto">
                <table className="w-full text-xs tabular-nums">
                  <thead className="sticky top-0 bg-[#0f172a] text-left text-slate-500"><tr><th className="py-1.5">Model (exact / classical)</th>{CLASSES.map((c) => <th key={c} className="px-1 text-right">{CLASS_LABEL[c]}</th>)}</tr></thead>
                  <tbody className="divide-y divide-slate-800/60">{rows.map((r) => (
                    <tr key={r.group}><td className="py-1.5 pr-2"><Link to={`/classification?model=${r.group}`} className="text-slate-200 hover:text-cyan-300">{r.display_name}</Link></td>
                      {CLASSES.map((c) => { const v = r.per_class_f1[c]; return <td key={c} className="px-1 text-right" style={{ color: v === undefined ? undefined : v < 0.3 ? '#fda4af' : v < 0.6 ? '#fcd34d' : '#a7f3d0' }}>{num(v, 2)}</td>; })}</tr>))}</tbody>
                </table>
              </div>
              </Collapsible>
            </div>
          );
        }}
      </Gate>
    </Card>
  );
}

export default function ClassificationPage() {
  const list = useV2<ModelsResponse>('/models');
  const [params, setParams] = useSearchParams();
  const best = useMemo(() => {
    const m = list.data?.models ?? [];
    return m.length ? [...m].sort((a, b) => (b.test_accuracy.mean ?? 0) - (a.test_accuracy.mean ?? 0))[0].group : '';
  }, [list.data]);
  const group = params.get('model') || best;
  return (
    <div className="space-y-5">
      <PageHeader title="Classification Analysis" subtitle="Locked-test evaluation of any selected configuration: overall and per-class metrics, confusion matrices per seed, seed-wise results and bootstrap confidence intervals (resampling the 360 test images)." />
      {list.loading ? <Loading /> : (
        <Gate state={list} empty={(d) => !d.count}>
          {(d) => (
            <Card>
              <label className="flex flex-col gap-1 text-[11px] text-slate-400 max-w-xl">
                Model configuration
                <select aria-label="Model configuration" value={group} onChange={(e) => setParams({ model: e.target.value })}
                  className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-sm text-slate-200">
                  {d.categories.map((c) => (
                    <optgroup key={c} label={c}>
                      {d.models.filter((m) => m.category === c).sort((a, b) => (b.test_accuracy.mean ?? 0) - (a.test_accuracy.mean ?? 0))
                        .map((m) => <option key={m.group} value={m.group}>{m.display_name} — {pct(m.test_accuracy.mean)}</option>)}
                    </optgroup>
                  ))}
                </select>
              </label>
            </Card>
          )}
        </Gate>
      )}
      {group && <ModelView key={group} group={group} />}
      <WeakClasses />
    </div>
  );
}
