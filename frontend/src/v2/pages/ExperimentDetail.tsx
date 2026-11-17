import { Link, useParams } from 'react-router-dom';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useV2 } from '../api';
import { Badge, CLASSES, CLASS_LABEL, Card, ConfusionMatrix, Gate, PageHeader, Stat, chartTheme, num, pct } from '../ui';

type Metrics = { accuracy: number; precision_macro: number; recall_macro: number; f1_macro: number;
  per_class: Record<string, { precision: number; recall: number; f1: number; support: number }>; confusion_matrix: number[][];
  bootstrap_ci?: { accuracy: [number, number]; f1_macro: [number, number] } } | null;
type Detail = {
  experiment_id: string; config: Record<string, any> | null; metadata: Record<string, any> | null;
  status: { status: string; summary?: Record<string, any>; error?: { type: string; message: string; traceback: string } } | null;
  validation_metrics: Metrics; test_metrics: Metrics; training_log: { history?: Record<string, number>[]; [k: string]: unknown } | null;
  circuit_stats: Record<string, any> | null; diagnostics: Record<string, any> | null;
  confusion_matrix: { val?: number[][]; test?: number[][] } | null;
};

function Curves({ hist }: { hist: Record<string, number>[] }) {
  const x = ['epoch', 'iteration', 'evaluation'].find((k) => k in hist[0]) ?? 'epoch';
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {[['train_loss', 'val_loss', 'Loss (cross-entropy)'], ['train_acc', 'val_acc', 'Accuracy']].map(([a, b, t]) => (
        <div key={t} className="h-60">
          <div className="mb-1 text-xs text-slate-400">{t}</div>
          <ResponsiveContainer><LineChart data={hist}>
            <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
            <XAxis dataKey={x} tick={{ fontSize: 10, fill: chartTheme.axis }} /><YAxis tick={{ fontSize: 10, fill: chartTheme.axis }} />
            <Tooltip contentStyle={chartTheme.tooltip} /><Legend wrapperStyle={{ fontSize: 11 }} />
            <Line dataKey={a} name="train" stroke="#22d3ee" dot={false} /><Line dataKey={b} name="internal validation" stroke="#f59e0b" dot={false} />
          </LineChart></ResponsiveContainer>
        </div>
      ))}
    </div>
  );
}

export default function ExperimentDetail() {
  const { id = '' } = useParams();
  const st = useV2<Detail>(`/experiments/${encodeURIComponent(id)}`);
  const circ = useV2<{ experiment_id: string }>(id ? `/circuits/${encodeURIComponent(id)}` : null);
  return (
    <div className="space-y-5">
      <PageHeader title="Experiment details" subtitle={<span className="font-mono text-xs">{id}</span>}>
        <Link to="/experiments-v2" className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800">← All runs</Link>
      </PageHeader>
      <Gate state={st}>
        {(d) => {
          const s = d.status?.summary ?? {};
          const m = d.test_metrics ?? d.validation_metrics;
          const hist = d.training_log?.history ?? [];
          return (
            <div className="space-y-5">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={d.status?.status === 'completed' ? 'emerald' : d.status?.status === 'failed' ? 'rose' : 'amber'}>{d.status?.status ?? 'unknown'}</Badge>
                <span className="text-sm text-slate-100">{d.config?.model_name}</span>
                <Badge>{d.config?.family_label}</Badge>
                {s.selected ? <Badge tone="cyan">selected → locked test</Badge> : <Badge>validation only (not selected)</Badge>}
                {s.group && <Link className="text-xs text-cyan-300 hover:underline" to={`/models?focus=${s.group}`}>configuration in Model Comparison</Link>}
                {circ.data && <Link className="text-xs text-cyan-300 hover:underline" to={`/circuits?id=${encodeURIComponent(id)}`}>view circuit</Link>}
              </div>
              {d.status?.error && (
                <div role="alert" className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-sm">
                  <div className="font-semibold text-rose-200">{d.status.error.type}: {d.status.error.message}</div>
                  <pre className="mt-2 overflow-x-auto text-[11px] text-rose-200/80">{d.status.error.traceback}</pre>
                </div>
              )}
              <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
                <Stat label="Validation macro-F1" value={num(d.validation_metrics?.f1_macro)} hint={`n = ${s.n_val ?? '?'}`} />
                <Stat label="Test accuracy" value={d.test_metrics ? pct(d.test_metrics.accuracy) : '—'} hint={d.test_metrics?.bootstrap_ci ? `95% CI ${pct(d.test_metrics.bootstrap_ci.accuracy[0])}–${pct(d.test_metrics.bootstrap_ci.accuracy[1])}` : 'not evaluated'} />
                <Stat label="Test macro-F1" value={d.test_metrics ? num(d.test_metrics.f1_macro) : '—'} />
                <Stat label="Seed / split" value={String(d.config?.seed ?? '?')} hint={d.config?.split_id} />
                <Stat label="Train time" value={`${num(s.train_time_s, 2)} s`} hint="CPU, perf_counter" />
              </div>
              {hist.length > 0 ? <Card title="Training curves" subtitle="Saved per-epoch / per-iteration log."><Curves hist={hist} /></Card>
                : <Card><div className="text-sm text-slate-400">This model has no iterative training log (closed-form or kernel SVM fit).</div></Card>}
              <div className="grid gap-5 xl:grid-cols-2">
                <Card title="Confusion matrices"><div className="space-y-4">
                  <ConfusionMatrix cm={d.confusion_matrix?.test} title="Locked test" />
                  <ConfusionMatrix cm={d.confusion_matrix?.val} title="Internal validation" />
                </div></Card>
                <Card title={`Per-class metrics (${d.test_metrics ? 'locked test' : 'internal validation'})`}>
                  {m ? (
                    <table className="w-full text-xs tabular-nums">
                      <thead className="text-left text-slate-500"><tr><th className="py-1">Class</th><th>Precision</th><th>Recall</th><th>F1</th><th>Support</th></tr></thead>
                      <tbody className="divide-y divide-slate-800/60">{CLASSES.map((c) => (
                        <tr key={c}><td className="py-1">{CLASS_LABEL[c]}</td><td>{num(m.per_class[c]?.precision)}</td><td>{num(m.per_class[c]?.recall)}</td><td>{num(m.per_class[c]?.f1)}</td><td>{m.per_class[c]?.support}</td></tr>))}</tbody>
                    </table>) : <div className="text-sm text-slate-400">No metrics saved.</div>}
                </Card>
              </div>
              {(['config', 'metadata', 'diagnostics', 'circuit_stats'] as const).map((k) => (
                <details key={k} className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                  <summary className="cursor-pointer text-sm text-slate-300">{k}{d[k] ? '' : ' — not saved for this experiment'}</summary>
                  {d[k] && <pre className="mt-2 max-h-96 overflow-auto text-[11px] text-slate-400">{JSON.stringify(d[k], null, 1)}</pre>}
                </details>
              ))}
            </div>
          );
        }}
      </Gate>
    </div>
  );
}
