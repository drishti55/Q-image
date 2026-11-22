import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useV2 } from '../api';
import { FAMILY_LABEL, distinct, filterRows } from '../../lib/v2';
import type { ExpRow, Filters } from '../../lib/v2';
import { Badge, CLASS_LABEL, Card, Gate, PageHeader, Select, Stat, chartTheme, int, num, pct } from '../ui';

type Dataset = {
  has_data: boolean; manifest_id: string; created_at: string; total_images: number; classes: string[];
  protocol: Record<string, string | number>; counts: Record<string, Record<string, number>>; dimensions: Record<string, number>;
  warnings: Record<string, number>; exact_duplicates: string[][]; integrity_ok: boolean;
  splits: Record<string, { split_id: string; counts: Record<string, number>; overlap_checks: { ok: boolean };
    adjacency_blocked: { val: { nn_within_radius_rate: number }; test: { nn_within_radius_rate: number } };
    adjacency_random_split_for_comparison: { val: { nn_within_radius_rate: number } } }>;
};

function StatusPill({ s }: { s: string }) {
  return <Badge tone={s === 'completed' ? 'emerald' : s === 'failed' ? 'rose' : 'amber'}>{s}</Badge>;
}

function DatasetPanel() {
  const st = useV2<Dataset>('/dataset');
  return (
    <Gate state={st} empty={(d) => !d.has_data}>
      {(d) => (
        <div className="grid gap-5 xl:grid-cols-5">
          <Card className="xl:col-span-2" title="Dataset & locked-test protocol" subtitle={`Manifest ${d.manifest_id}`}>
            <div className="grid grid-cols-2 gap-3">
              <Stat label="Images" value={int(d.total_images)} hint={Object.keys(d.dimensions).join(', ')} />
              <Stat label="Split integrity" value={d.integrity_ok ? 'verified' : 'FAILED'} hint="no path / hash / group overlap" />
            </div>
            <dl className="mt-4 space-y-2 text-xs">
              <div><dt className="text-slate-500">Locked test</dt><dd className="text-slate-200">{String(d.protocol.locked_test)}</dd></div>
              <div><dt className="text-slate-500">Train / validation pool</dt><dd className="text-slate-200">{String(d.protocol.trainval_pool)}</dd></div>
              <div><dt className="text-slate-500">Grouping</dt><dd className="text-slate-200">{String(d.protocol.group)}; {String(d.protocol.val_blocks_per_class)} validation blocks per class per seed</dd></div>
              <div><dt className="text-slate-500">Preprocessing</dt><dd className="text-slate-200">{String(d.protocol.preprocessing)}</dd></div>
              <div><dt className="text-slate-500">Data notes</dt><dd className="text-slate-300">{d.exact_duplicates.length} exact-duplicate pair(s) kept within one group; {d.warnings?.multi_defect_annotations} images with secondary defect boxes.</dd></div>
            </dl>
          </Card>
          <Card className="xl:col-span-3" title="Class distribution and splits">
            <div className="h-52"><ResponsiveContainer><BarChart data={d.classes.map((c) => ({ cls: CLASS_LABEL[c] ?? c, train: d.counts.train?.[c], test: d.counts.validation?.[c] }))}>
              <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} vertical={false} />
              <XAxis dataKey="cls" tick={{ fontSize: 10, fill: chartTheme.axis }} /><YAxis tick={{ fontSize: 10, fill: chartTheme.axis }} />
              <Tooltip contentStyle={chartTheme.tooltip} /><Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="train" name="Train folder (train + internal val)" fill="#22d3ee" /><Bar dataKey="test" name="Locked test" fill="#f59e0b" />
            </BarChart></ResponsiveContainer></div>
            <table className="mt-3 w-full text-xs tabular-nums">
              <thead className="text-left text-slate-500"><tr><th className="py-1">Seed</th><th>Split id</th><th>Train / val / test</th><th>Val near-duplicates (blocked)</th><th>(random split)</th><th>Test</th></tr></thead>
              <tbody className="divide-y divide-slate-800/60">{Object.entries(d.splits).map(([seed, s]) => (
                <tr key={seed}><td className="py-1.5">{seed}</td><td className="font-mono text-[11px]">{s.split_id}</td>
                  <td>{s.counts.train} / {s.counts.val} / {s.counts.test}</td><td>{pct(s.adjacency_blocked.val.nn_within_radius_rate)}</td>
                  <td className="text-slate-500">{pct(s.adjacency_random_split_for_comparison.val.nn_within_radius_rate)}</td><td>{pct(s.adjacency_blocked.test.nn_within_radius_rate)}</td></tr>))}</tbody>
            </table>
            <p className="mt-2 text-[11px] text-slate-500">“Near-duplicates” = share of images whose most similar same-class training image lies within ±3 file indices.</p>
          </Card>
        </div>
      )}
    </Gate>
  );
}

export default function ExperimentsPage() {
  const st = useV2<{ count: number; experiments: ExpRow[] }>('/experiments');
  const [f, setF] = useState<Filters>({});
  const [limit, setLimit] = useState(25);
  const rows = st.data?.experiments ?? [];
  const shown = useMemo(() => filterRows(rows, f), [rows, f]);
  const set = (k: keyof Filters) => (v: string) => { setF({ ...f, [k]: v }); setLimit(200); };
  return (
    <div className="space-y-5">
      <PageHeader title="Experiments V2" subtitle="Protocol, dataset integrity and the complete run history: every configuration × seed that was trained (validation metrics) and, for validation-selected configurations only, evaluated on the locked test set." />
      <DatasetPanel />
      <Gate state={st} empty={(d) => !d.count}>
        {(d) => (
          <Card title="Run history" subtitle={`${int(d.count)} runs. Click a run for its training curves, confusion matrices, provenance and configuration.`}>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4 mb-4">
              <Stat label="Completed" value={int(rows.filter((r) => r.status === 'completed').length)} />
              <Stat label="Failed" value={int(rows.filter((r) => r.status === 'failed').length)} />
              <Stat label="Running / interrupted" value={int(rows.filter((r) => r.status === 'running').length)} />
              <Stat label="With locked-test result" value={int(rows.filter((r) => r.test).length)} hint="selected configurations × seeds" />
            </div>
            <div className="flex flex-wrap items-end gap-3">
              <Select label="Model family" value={f.family ?? 'all'} onChange={set('family')} options={distinct(rows, 'family').map((v) => [v, FAMILY_LABEL[v] ?? v] as [string, string])} />
              <Select label="Experiment" value={f.code ?? 'all'} onChange={set('code')} options={distinct(rows, 'experiment_code')} />
              <Select label="Qubits" value={f.n_qubits ?? 'all'} onChange={set('n_qubits')} options={distinct(rows, 'n_qubits')} />
              <Select label="Layers / reps" value={f.n_layers ?? 'all'} onChange={set('n_layers')} options={distinct(rows, 'n_layers')} />
              <Select label="Optimizer" value={f.optimizer ?? 'all'} onChange={set('optimizer')} options={distinct(rows, 'optimizer')} />
              <Select label="Shots" value={f.shots ?? 'all'} onChange={set('shots')} options={[...new Set(rows.map((r) => String(r.shots ?? 0)))].sort((a, b) => +a - +b)} />
              <Select label="Seed" value={f.seed ?? 'all'} onChange={set('seed')} options={distinct(rows, 'seed')} />
              <Select label="Status" value={f.status ?? 'all'} onChange={set('status')} options={distinct(rows, 'status')} />
              <label className="flex items-center gap-2 text-xs text-slate-300"><input type="checkbox" checked={!!f.selectedOnly} onChange={(e) => setF({ ...f, selectedOnly: e.target.checked })} />selected only</label>
            </div>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-xs tabular-nums">
                <thead className="text-left text-[11px] uppercase tracking-wider text-slate-500"><tr><th className="py-2">Run</th><th>Family</th><th>Qubits</th><th>Layers</th><th>Optimizer</th><th>Shots</th><th>Seed</th><th>Status</th><th className="text-right">Val F1</th><th className="text-right">Test acc.</th><th className="text-right">Train s</th></tr></thead>
                <tbody className="divide-y divide-slate-800/60">
                  {shown.slice(0, limit).map((r) => (
                    <tr key={r.experiment_id} className="hover:bg-slate-800/30">
                      <td className="py-1.5 pr-2"><Link to={`/experiments/${encodeURIComponent(r.experiment_id)}`} className="font-mono text-[11px] text-cyan-300 hover:underline">{r.experiment_id}</Link>{r.selected && <Badge tone="cyan">selected</Badge>}</td>
                      <td>{FAMILY_LABEL[r.family ?? ''] ?? r.family}</td><td>{r.n_qubits ?? '—'}</td><td>{r.n_layers ?? '—'}</td><td>{r.optimizer ?? '—'}</td><td>{r.shots ?? 0}</td><td>{r.seed}</td>
                      <td><StatusPill s={r.status} /></td><td className="text-right">{num(r.val?.f1_macro)}</td><td className="text-right">{r.test ? pct(r.test.accuracy) : '—'}</td><td className="text-right">{num(r.train_time_s, 2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!shown.length && <div className="p-6 text-center text-sm text-slate-400">No runs match these filters.</div>}
              {shown.length > limit && <button onClick={() => setLimit(limit + 100)} className="mt-3 rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800">Show more ({int(shown.length - limit)} remaining)</button>}
            </div>
          </Card>
        )}
      </Gate>
    </div>
  );
}
