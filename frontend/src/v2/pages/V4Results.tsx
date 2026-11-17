// Protocol V4 results: patch-ensemble (mixed-state) FRQI / NEQR kernels (results/qml_v4 via /api/v4).
import { Link } from 'react-router-dom';
import { ArrowRight, ShieldCheck } from 'lucide-react';
import { useV4 } from '../api';
import { Card, Gate, PageHeader, Badge } from '../ui';

const pc = (v: number) => `${(100 * v).toFixed(1)}%`;
const ms = (m: any) => `${(100 * m.mean).toFixed(1)} ± ${(100 * (m.std ?? 0)).toFixed(1)}`;

export default function V4Results() {
  const st = useV4<any>('/results');
  return (
    <div className="space-y-5">
      <PageHeader title="FRQI / NEQR Improvement — Protocol V4"
        subtitle="Each image is represented as the mixed quantum state of its FRQI- or NEQR-encoded patches; images are compared with the swap-test kernel Tr(ρσ). Frozen on validation, evaluated once on the 360 locked test images." />
      <Gate state={st}>{(d) => {
        const G = d.groups, R = d.references, fr = G[d.headlines.frqi], ne = G[d.headlines.neqr];
        const tiles = [
          { label: 'FRQI', before: R['E1b-frqi8-qkc-scaled'].test_accuracy.mean, after: fr.test_accuracy.mean, sub: d.headlines.frqi },
          { label: 'NEQR', before: R['E2-neqr16-b4-qkc'].test_accuracy.mean, after: ne.test_accuracy.mean, sub: d.headlines.neqr },
          { label: 'Classical, same patches', after: G['V4-patchmom-rbfsvm'].test_accuracy.mean, sub: 'RBF-SVM on patch moments' },
          { label: 'Classical, texture features', after: R['V3-tex12c-rbfsvm'].test_accuracy.mean, sub: 'V3 RBF-SVM (LBP + GLCM)' },
        ];
        return (<>
          <div className="flex flex-wrap items-center gap-2 rounded-xl bg-emerald-500/5 px-4 py-3 text-xs text-slate-300 ring-1 ring-emerald-500/20" data-testid="v4-protocol">
            <ShieldCheck size={16} className="text-emerald-300" />
            {d.counts.groups} groups · {d.counts.candidate_runs} validation runs ({d.counts.failed_runs} failed) · frozen {new Date(d.frozen_at).toLocaleString()} (SHA-256 {d.frozen_selection_sha256.slice(0, 12)}…) · {d.counts.test_access_events} locked-test stages
            <Link to="/how-it-works" className="ml-auto inline-flex items-center gap-1 text-cyan-300">watch it work on a real image <ArrowRight size={13} /></Link>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{tiles.map((t) => (
            <div key={t.label} className="rounded-xl border border-slate-800 bg-slate-950/50 px-4 py-3" data-testid={`v4-tile-${t.label}`}>
              <div className="text-[11px] uppercase tracking-wider text-slate-500">{t.label}</div>
              <div className="mt-1 flex items-baseline gap-2">
                {t.before != null && <span className="text-sm text-slate-500 line-through">{pc(t.before)}</span>}
                {t.before != null && <ArrowRight size={14} className="text-slate-500" />}
                <span className="text-2xl font-semibold text-white">{pc(t.after)}</span>
              </div>
              <div className="text-[11px] text-slate-400">{t.sub}</div>
            </div>))}
          </div>
          <Card title="Pre-declared comparisons" subtitle="Paired sign-flip permutation test over the 360 images (seed-averaged), 95 % bootstrap CI, Holm-corrected over these 8.">
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
          </Card>
          <Card title="Every V4 group (selected on validation)">
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
            <div className="mt-3 text-[11px] text-amber-200/80">NEQR seed 1 misclassifies every rolled-in-scale test image (selected without contrast stretch); FRQI, selected with it, does not. Not re-tuned after testing. No quantum advantage is claimed: all kernels have closed forms and a classical SVM on the same patches is statistically tied with FRQI.</div>
          </Card>
        </>);
      }}</Gate>
    </div>
  );
}
