import { Link } from 'react-router-dom';
import { useV2 } from '../api';
import { Badge, Card, Gate, PageHeader, Stat, int } from '../ui';

type Historical = { label: string; warnings: string[]; counts: Record<string, number>;
  paired_runs: Record<string, string>[]; classical_v0: Record<string, string>[]; source_files: string[] };

const PAGES: [string, string, string][] = [
  ['/historical-v0/dashboard', 'V0 Home', 'The previous landing page'],
  ['/historical-v0/qml-lab', 'V0 Quantum ML Lab', 'Paired FRQI/NEQR runs, per-image records, V0 charts'],
  ['/historical-v0/ml', 'V0 Classical Analytics', 'Random in-folder split classical models'],
  ['/historical-v0/confusion-matrix', 'V0 Confusion Matrix', 'V0 classical confusion matrices'],
  ['/historical-v0/compare', 'V0 Classical Comparison', 'V0 reconstruction benchmark comparison'],
  ['/historical-v0/quantum', 'V0 Quantum Image Lab', 'Interactive single-image encoding'],
  ['/historical-v0/quantum-compare-lab', 'V0 Encoding Lab', 'Custom FRQI vs NEQR comparison'],
  ['/historical-v0/experiments', 'V0 Batch Lab', 'Legacy reconstruction batch results (launching disabled)'],
  ['/historical-v0/dataset', 'Dataset Browser', 'Browse NEU-DET images'],
];

export default function HistoricalHome() {
  const st = useV2<Historical>('/historical');
  return (
    <div className="space-y-5">
      <PageHeader title="Historical Results — Protocol V0" subtitle="Read-only. Results produced before the locked-test protocol. Kept unchanged as evidence (SHA-256 verified) and never mixed into Protocol V2 views.">
        <Badge tone="amber">read-only</Badge>
        <Link to="/" className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800">Current results (all versions) →</Link>
      </PageHeader>
      <Gate state={st}>
        {(d) => (
          <>
            <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-4">
              <div className="text-sm font-semibold text-amber-100">Why V0 results are not comparable with V2</div>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-100/90">{d.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
            </div>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <Stat label="V0 paired runs" value={int(d.counts.paired_run)} />
              <Stat label="V0 per-image records" value={int(d.counts.per_image_record)} hint="0/1 correctness, not aggregate metrics" />
              <Stat label="Unit-test fixture rows" value={int(d.counts.unit_test_fixture)} hint="not experiments" />
              <Stat label="V0 classical models" value={int(d.classical_v0.length)} />
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              {PAGES.map(([to, t, s]) => (
                <Link key={to} to={to} className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 hover:border-amber-500/40">
                  <div className="text-sm font-semibold text-slate-100">{t} →</div><div className="mt-1 text-xs text-slate-400">{s}</div>
                </Link>
              ))}
            </div>
            <Card title="V0 paired QML runs (as saved)" subtitle={`Source: ${d.source_files.join(', ')}`}>
              <div className="max-h-96 overflow-auto">
                <table className="w-full text-xs tabular-nums">
                  <thead className="sticky top-0 bg-[#0f172a] text-left text-slate-500"><tr><th className="py-1.5">experiment_id</th><th>model (V0 label)</th><th>repr.</th><th>res.</th><th>shots</th><th>accuracy</th><th>f1_macro</th><th>timestamp</th></tr></thead>
                  <tbody className="divide-y divide-slate-800/60">{d.paired_runs.map((r, i) => (
                    <tr key={`${r.experiment_id}-${i}`}><td className="py-1 font-mono">{r.experiment_id}</td><td>{r.qml_model_type}</td><td>{r.representation}</td><td>{r.resolution}</td><td>{r.shots}</td><td>{r.accuracy}</td><td>{r.f1_macro}</td><td className="text-slate-500">{r.timestamp}</td></tr>))}</tbody>
                </table>
              </div>
            </Card>
          </>
        )}
      </Gate>
    </div>
  );
}
