// Protocol V4 results: patch-ensemble (mixed-state) FRQI / NEQR kernels (results/qml_v4 via /api/v4).
// Visual first (before→after tiles, forest plot, per-seed group chart); every table kept under "Show full table".
import { Link } from 'react-router-dom';
import { ArrowRight, ShieldCheck } from 'lucide-react';
import { useV4 } from '../api';
import { Card, Gate, PageHeader, Badge } from '../ui';
import { ForestPlot, TableDetails } from '../ForestPlot';
import { ExplainThis } from '../learn/ExplainThis';

const pc = (v: number) => `${(100 * v).toFixed(1)}%`;
const ms = (m: any) => `${(100 * m.mean).toFixed(1)} ± ${(100 * (m.std ?? 0)).toFixed(1)}`;
const FRQI = '#3987e5', NEQR = '#d95926', CLASSICAL = '#199e70';
const colorOf = (g: string, r: any) => (!r.quantum?.n_qubits ? CLASSICAL : /neqr/i.test(g) ? NEQR : FRQI);

function GroupChart({ G }: { G: Record<string, any> }) {
  const rows = Object.entries(G).sort((a, b) => b[1].test_accuracy.mean - a[1].test_accuracy.mean);
  const W = 760, L = 210, R = 70, row = 34, lo = 0.6, X = (v: number) => L + ((v - lo) / (1 - lo)) * (W - L - R);
  return (
    <svg viewBox={`0 0 ${W} ${rows.length * row + 26}`} className="w-full" role="img" aria-label="test accuracy of every V4 group with per-seed results">
      {[0.6, 0.7, 0.8, 0.9, 1].map((t) => <g key={t}><line x1={X(t)} x2={X(t)} y1={2} y2={rows.length * row} stroke="#1e293b" /><text x={X(t)} y={rows.length * row + 16} textAnchor="middle" fontSize={10} fill="#64748b">{t * 100}%</text></g>)}
      {rows.map(([g, r], i) => {
        const y = i * row + 17, c = colorOf(g, r);
        return (
          <g key={g}>
            <text x={L - 10} y={y + 4} textAnchor="end" fontSize={11.5} fill="#e2e8f0">{g.replace('V4-', '')}<tspan fill="#64748b" fontSize={10}> · {r.quantum?.n_qubits ? `${r.quantum.n_qubits} qubits` : 'classical'}</tspan></text>
            <rect x={X(lo)} y={y - 7} width={X(r.test_accuracy.mean) - X(lo)} height={14} rx={4} fill={c} fillOpacity={0.85}><title>{g}: {ms(r.test_accuracy)} %</title></rect>
            {(r.per_seed_test_accuracy as number[]).map((s, k) => <circle key={k} cx={X(s)} cy={y} r={4} fill="#0f172a" stroke="#f8fafc" strokeWidth={1.5}><title>seed {k}: {pc(s)}</title></circle>)}
            <text x={W - R + 8} y={y + 4} fontSize={11.5} fill="#f8fafc" className="tabular-nums">{pc(r.test_accuracy.mean)}</text>
          </g>);
      })}
    </svg>
  );
}

export default function V4Results() {
  const st = useV4<any>('/results');
  return (
    <div className="space-y-5">
      <PageHeader title="FRQI / NEQR Improvement — Protocol V4"
        subtitle="Each image becomes the mixed quantum state of its encoded patches; images are compared with Tr(ρσ). Frozen on validation, tested once on 360 locked images.">
        <ExplainThis id="density" /><ExplainThis id="frqi" /><ExplainThis id="neqr" />
      </PageHeader>
      <Gate state={st}>{(d) => {
        const G = d.groups, R = d.references, fr = G[d.headlines.frqi], ne = G[d.headlines.neqr];
        const tiles = [
          { label: 'FRQI', before: R['E1b-frqi8-qkc-scaled'].test_accuracy.mean, after: fr.test_accuracy.mean, sub: d.headlines.frqi, c: FRQI },
          { label: 'NEQR', before: R['E2-neqr16-b4-qkc'].test_accuracy.mean, after: ne.test_accuracy.mean, sub: d.headlines.neqr, c: NEQR },
          { label: 'Classical, same patches', after: G['V4-patchmom-rbfsvm'].test_accuracy.mean, sub: 'RBF-SVM on patch moments', c: CLASSICAL },
          { label: 'Classical, texture features', after: R['V3-tex12c-rbfsvm'].test_accuracy.mean, sub: 'V3 RBF-SVM (LBP + GLCM)', c: CLASSICAL },
        ];
        return (<>
          <div className="flex flex-wrap items-center gap-2 rounded-xl bg-emerald-500/5 px-4 py-3 text-xs text-slate-300 ring-1 ring-emerald-500/20" data-testid="v4-protocol">
            <ShieldCheck size={16} className="text-emerald-300" />
            {d.counts.groups} groups · {d.counts.candidate_runs} validation runs ({d.counts.failed_runs} failed) · frozen {new Date(d.frozen_at).toLocaleString()} (SHA-256 {d.frozen_selection_sha256.slice(0, 12)}…) · {d.counts.test_access_events} locked-test stages
            <Link to="/compare" className="ml-auto inline-flex items-center gap-1 text-cyan-300">model comparison table <ArrowRight size={13} /></Link>
            <Link to="/how-it-works" className="inline-flex items-center gap-1 text-cyan-300">watch it work on a real image <ArrowRight size={13} /></Link>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{tiles.map((t) => (
            <div key={t.label} className="rounded-xl border border-slate-800 bg-slate-950/50 px-4 py-3" data-testid={`v4-tile-${t.label}`}>
              <div className="text-[11px] uppercase tracking-wider text-slate-500">{t.label}</div>
              <div className="mt-1 flex items-baseline gap-2">
                {t.before != null && <span className="text-sm text-slate-500 line-through">{pc(t.before)}</span>}
                {t.before != null && <ArrowRight size={14} className="text-slate-500" />}
                <span className="text-2xl font-semibold text-white">{pc(t.after)}</span>
              </div>
              <div className="mt-2 space-y-1">
                {t.before != null && <div className="h-1.5 rounded-full bg-slate-800"><div className="h-1.5 rounded-full bg-slate-600" style={{ width: `${100 * t.before}%` }} /></div>}
                <div className="h-1.5 rounded-full bg-slate-800"><div className="h-1.5 rounded-full transition-all duration-700" style={{ width: `${100 * t.after}%`, background: t.c }} /></div>
              </div>
              <div className="mt-1.5 text-[11px] text-slate-400">{t.sub}</div>
            </div>))}
          </div>
          <Card title="Pre-declared comparisons" subtitle="Paired over the 360 test images (seed-averaged) · 95 % bootstrap CI · Holm-corrected over these 8.">
            <ForestPlot rows={d.comparisons} testid="v4-forest" />
            <TableDetails>
              <div className="overflow-x-auto"><table className="w-full text-xs tabular-nums" data-testid="v4-comparisons">
                <thead className="text-left text-[11px] text-slate-500"><tr>{['Comparison', 'A %', 'B %', 'Δ (95 % CI) pp', 'p (Holm)', ''].map((h) => <th key={h} className="px-2 py-2 font-medium">{h}</th>)}</tr></thead>
                <tbody>{d.comparisons.map((c: any) => (
                  <tr key={c.name} className="border-t border-slate-800/70 text-slate-200">
                    <td className="px-2 py-1.5">{c.name}</td><td className="px-2">{(100 * c.acc_a).toFixed(1)}</td><td className="px-2">{(100 * c.acc_b).toFixed(1)}</td>
                    <td className="px-2">{(100 * c.diff).toFixed(1)} [{(100 * c.ci95[0]).toFixed(1)}, {(100 * c.ci95[1]).toFixed(1)}]</td>
                    <td className="px-2">{c.p_holm < 0.001 ? '<0.001' : c.p_holm.toFixed(3)}</td>
                    <td className="px-2">{c.p_holm < 0.05 ? <Badge tone="emerald">significant</Badge> : <Badge>n.s.</Badge>}</td>
                  </tr>))}</tbody>
              </table></div>
            </TableDetails>
          </Card>
          <Card title="Every V4 group" subtitle="Bar = mean test accuracy · white dots = the 3 seeds. Selected on validation.">
            <div className="mb-2 flex gap-4 text-[11px] text-slate-400">{[['FRQI', FRQI], ['NEQR', NEQR], ['classical', CLASSICAL]].map(([l, c]) => <span key={l}><span className="mr-1 inline-block h-2.5 w-2.5 rounded-sm" style={{ background: c }} />{l}</span>)}</div>
            <GroupChart G={G} />
            <TableDetails>
              <div className="overflow-x-auto"><table className="w-full text-xs tabular-nums" data-testid="v4-groups">
                <thead className="text-left text-[11px] text-slate-500"><tr>{['Group', 'qubits / patch', 'configuration', 'val F1 %', 'test acc. %', 'test F1 %', 'per seed %'].map((h) => <th key={h} className="px-2 py-2 font-medium">{h}</th>)}</tr></thead>
                <tbody>{Object.entries(G).map(([g, r]: [string, any]) => (
                  <tr key={g} className="border-t border-slate-800/70 text-slate-200">
                    <td className="px-2 py-1.5 font-mono">{g}</td><td className="px-2">{r.quantum?.n_qubits ?? 'classical'}</td>
                    <td className="px-2 text-slate-400">{Object.entries(r.params).map(([k, v]) => `${k}=${v}`).join(', ')}</td>
                    <td className="px-2">{(100 * r.val_f1_macro.mean).toFixed(1)}</td><td className="px-2">{ms(r.test_accuracy)}</td><td className="px-2">{ms(r.test_f1_macro)}</td>
                    <td className="px-2">{r.per_seed_test_accuracy.map((x: number) => (100 * x).toFixed(1)).join(' / ')}</td>
                  </tr>))}</tbody>
              </table></div>
            </TableDetails>
            <div className="mt-3 text-[11px] text-amber-200/80">NEQR seed 1 misclassifies every rolled-in-scale test image (selected without contrast stretch); FRQI, selected with it, does not. Not re-tuned after testing. No quantum advantage is claimed: all kernels have closed forms and a classical SVM on the same patches is statistically tied with FRQI.</div>
          </Card>
        </>);
      }}</Gate>
    </div>
  );
}
