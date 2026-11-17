/* eslint-disable @typescript-eslint/no-explicit-any */
// Protocol V3 — quantum performance improvement results. Every number from GET /api/v3/results
// (results/qml_v3/aggregates/v3_results.json, built only from saved records). Nothing is hardcoded.
import { useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts';
import { ArrowRight, ShieldCheck } from 'lucide-react';
import { useV3 } from '../api';
import { Card, Gate, PageHeader, UNAVAILABLE } from '../ui';
import { ChartCard, LegendRow } from '../charts';

const pc = (v?: number | null, d = 1) => (v == null ? UNAVAILABLE : `${(v * 100).toFixed(d)}%`);
const pp = (v?: number | null) => (v == null ? UNAVAILABLE : `${v >= 0 ? '+' : ''}${(v * 100).toFixed(1)} pp`);
const msx = (m?: { mean: number | null; std: number | null } | null) => (m?.mean == null ? UNAVAILABLE : `${(m.mean * 100).toFixed(1)}${m.std != null ? ` ± ${(m.std * 100).toFixed(1)}` : ''}%`);
const CAT: Record<string, { label: string; color: string }> = {
  quantum_kernel: { label: 'Quantum kernel', color: '#199e70' }, quantum_encoding: { label: 'FRQI / NEQR', color: '#d55181' },
  vqc: { label: 'VQC', color: '#c98500' }, hybrid: { label: 'Hybrid QKC', color: '#9085e9' }, hybrid_vqc: { label: 'Hybrid VQC', color: '#9085e9' },
  classical_control: { label: 'Classical control', color: '#3987e5' }, vqc_control: { label: 'VQC control', color: '#94a3b8' },
};

function Headline({ label, h, base, baseName, matched, note }: { label: string; h: any; base?: any; baseName?: string; matched?: any; note?: string }) {
  if (!h) return null;
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/50 px-4 py-3" data-testid={`v3-head-${label}`}>
      <div className="text-[11px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className="mt-1 flex items-baseline gap-2">
        {base && <span className="text-sm tabular-nums text-slate-500 line-through decoration-slate-600">{pc(base)}</span>}
        {base && <ArrowRight size={14} className="text-slate-500" />}
        <span className="text-2xl font-semibold tabular-nums text-white">{pc(h.test_accuracy.mean)}</span>
      </div>
      <div className="truncate text-[11px] text-slate-400" title={h.display_name}>{h.display_name}</div>
      <div className="text-[10px] text-slate-500">selected on validation (F1 {h.val_f1_macro.mean?.toFixed(3)}){baseName && <> · V2 baseline: {baseName}</>}</div>
      {matched && <div className="mt-1.5 border-t border-slate-800 pt-1.5 text-[11px] text-slate-300" data-testid={`v3-head-matched-${label}`}>
        Classical RBF-SVM on the same features: <b className="tabular-nums text-white">{pc(matched.test_accuracy.mean)}</b></div>}
      {note && <div className="mt-1 text-[10px] text-amber-200/80">{note}</div>}
    </div>
  );
}

function Stat({ row }: { row: any }) {
  const sig = row.significant_0_05 ?? row['significant_0.05'];
  return <span className={`rounded px-1.5 py-0.5 text-[11px] ${sig ? 'bg-emerald-500/15 text-emerald-200' : 'bg-slate-800 text-slate-300'}`}>p<sub>Holm</sub> = {row.p_holm < 0.0001 ? '<0.0001' : row.p_holm.toFixed(4)}{sig ? ' · significant' : ' · n.s.'}</span>;
}

function Table({ head, rows, testid }: { head: string[]; rows: ReactNode[][]; testid: string }) {
  return (
    <div className="overflow-x-auto"><table className="w-full text-xs tabular-nums" data-testid={testid}>
      <thead className="text-left text-[11px] text-slate-500"><tr>{head.map((h) => <th key={h} className="px-2 py-2 font-medium">{h}</th>)}</tr></thead>
      <tbody>{rows.map((r, i) => <tr key={i} className="border-t border-slate-800/70">{r.map((c, j) => <td key={j} className="px-2 py-2 align-top text-slate-200">{c}</td>)}</tr>)}</tbody>
    </table></div>
  );
}

function BeforeAfterChart({ rows }: { rows: any[] }) {
  const data = rows.filter((r) => r.v3_best).map((r, i) => ({ i, model: r.model, v2: +(r.v2_test_accuracy.mean * 100).toFixed(2), v3: +(r.v3_best.test_accuracy.mean * 100).toFixed(2), v3name: r.v3_best.display_name }));
  const H = Math.max(260, data.length * 34);
  return (
    <ChartCard testid="chart-before-after" title="Before (Protocol V2) → after (Protocol V3)" height={H}
      subtitle="Test accuracy on the 360 locked images, mean of 3 seeds. Grey = V2 baseline, green = V3 configuration chosen on validation. The V3 pick may use a different representation — see the table for like-for-like results."
      table={{ head: ['Model', 'V2 %', 'V3 %', 'V3 configuration'], rows: data.map((d) => [d.model, d.v2.toFixed(1), d.v3.toFixed(1), d.v3name]) }}>
      <ResponsiveContainer>
        <ScatterChart margin={{ left: 8, right: 24, top: 8, bottom: 4 }}>
          <CartesianGrid horizontal={false} stroke="#1e293b" />
          <XAxis type="number" dataKey="x" domain={[0, 100]} unit="%" tick={{ fontSize: 11, fill: '#94a3b8' }} stroke="#1e293b" />
          <YAxis type="number" dataKey="y" domain={[-0.6, data.length - 0.4]} ticks={data.map((d) => data.length - 1 - d.i)} width={150}
            tickFormatter={(v) => data[data.length - 1 - v]?.model ?? ''} tick={{ fontSize: 11, fill: '#e2e8f0' }} stroke="#1e293b" />
          <ZAxis range={[80, 80]} />
          <Tooltip cursor={false} content={({ active, payload }) => {
            const p: any = active && payload?.[0]?.payload;
            if (!p) return null;
            return <div className="rounded-lg bg-[#0b1220] px-3 py-2 text-xs ring-1 ring-slate-700"><div className="font-medium text-slate-100">{p.model}</div><div className="text-slate-400">{p.kind}: <b className="text-slate-100">{p.x.toFixed(1)}%</b></div>{p.name && <div className="text-slate-500">{p.name}</div>}</div>;
          }} />
          {data.map((d) => <Scatter key={`l${d.i}`} data={[{ x: d.v2, y: data.length - 1 - d.i }, { x: d.v3, y: data.length - 1 - d.i }]} line={{ stroke: '#475569', strokeWidth: 2 }} shape={() => <g />} isAnimationActive={false} />)}
          <Scatter name="V2" data={data.map((d) => ({ x: d.v2, y: data.length - 1 - d.i, model: d.model, kind: 'V2 baseline' }))} fill="#94a3b8" stroke="#0f172a" strokeWidth={2} isAnimationActive={false} />
          <Scatter name="V3" data={data.map((d) => ({ x: d.v3, y: data.length - 1 - d.i, model: d.model, kind: 'V3 (validation-selected)', name: d.v3name }))} fill="#199e70" stroke="#0f172a" strokeWidth={2} isAnimationActive={false} />
        </ScatterChart>
      </ResponsiveContainer>
      <LegendRow items={[{ name: 'V2 baseline', color: '#94a3b8', shape: 'dot' }, { name: 'V3, chosen on validation', color: '#199e70', shape: 'dot' }]} />
    </ChartCard>
  );
}

export default function V3Results() {
  const st = useV3<any>('/results');
  const [cat, setCat] = useState('all');
  return (
    <div>
      <PageHeader title="Quantum Performance — Protocol V3"
        subtitle="Validation-driven improvements to the quantum models, frozen before a single locked-test evaluation. Same dataset, splits, seeds and 360 locked test images as Protocol V2; V2 results are unchanged." />
      <Gate state={st}>{(d: any) => <Body d={d} cat={cat} setCat={setCat} />}</Gate>
    </div>
  );
}

function Body({ d, cat, setCat }: { d: any; cat: string; setCat: (c: string) => void }) {
  const v2 = (g: string) => d.before_after.find((b: any) => b.v2_group === g)?.v2_test_accuracy.mean;
  const comps = d.comparisons as any[];
  const groups = useMemo(() => (d.groups as any[]).filter((g) => cat === 'all' || g.category === cat).sort((a, b) => (b.test_accuracy.mean ?? 0) - (a.test_accuracy.mean ?? 0)), [d.groups, cat]);
  const H = d.headlines;
  const rbf = (h: any) => { const g = h && (d.groups as any[]).find((x) => x.group === h.group); return g && (d.groups as any[]).find((x) => x.group === `V3-${g.feature_set}-rbfsvm`); };
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2 rounded-xl bg-emerald-500/5 px-4 py-3 text-xs text-slate-300 ring-1 ring-emerald-500/20" data-testid="v3-protocol">
        <ShieldCheck size={16} className="text-emerald-300" />
        <span>{d.counts.groups} groups · {d.counts.candidate_runs.toLocaleString()} validation runs ({d.counts.failed_runs} failed, kept) · selections frozen {new Date(d.frozen_at).toLocaleString()} (SHA-256 {d.frozen_selection_sha256.slice(0, 12)}…) · {d.counts.test_access_events} locked-test evaluation stages, one per frozen group</span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Headline label="Pure quantum (V3)" h={H.pure_quantum} base={v2('E3-pca8-qkc-product_ry')} baseName="pixel PCA-8 product-RY" matched={rbf(H.pure_quantum)}
          note={H.pure_quantum?.group.includes('product_ry') ? 'Product-RY kernels are classically computable in closed form.' : undefined} />
        <Headline label="VQC (V3)" h={H.vqc} base={v2('E4-pca8-vqc')} baseName="pixel PCA-8 VQC" matched={rbf(H.vqc)} />
        <Headline label="Hybrid quantum (V3)" h={H.hybrid_quantum} base={v2('E5-mnv3pca8-qkc-product_ry')} baseName="MobileNetV3 PCA-8 product-RY" matched={rbf(H.hybrid_quantum)} />
        <Headline label="Best classical control" h={H.classical_control_best} />
      </div>

      <BeforeAfterChart rows={d.before_after} />

      <Card title="Before and after, model by model" subtitle="V3 like-for-like keeps the V2 representation family (pixels for pixel models, MobileNetV3 for hybrids); V3 best allows any V3 representation. Both picks are made on validation macro-F1.">
        <Table testid="v3-before-after" head={['Model', 'V2 test acc.', 'V3 like-for-like', 'V3 best (by validation)', 'Δ best vs V2']}
          rows={(d.before_after as any[]).map((b) => [b.model,
            <span>{msx(b.v2_test_accuracy)}<div className="text-[10px] text-slate-500">{b.v2_group}</div></span>,
            b.v3_like_for_like ? <span>{msx(b.v3_like_for_like.test_accuracy)}<div className="text-[10px] text-slate-500">{b.v3_like_for_like.display_name}</div></span> : UNAVAILABLE,
            b.v3_best ? <span>{msx(b.v3_best.test_accuracy)}<div className="text-[10px] text-slate-500">{b.v3_best.display_name}</div></span> : UNAVAILABLE,
            b.v3_best ? pp(b.v3_best.test_accuracy.mean - b.v2_test_accuracy.mean) : UNAVAILABLE])} />
      </Card>

      <Card title="Statistical evidence" subtitle="Paired over the same 360 test images, averaged over seeds: difference with 95% bootstrap CI, sign-flip permutation test, Holm-corrected over the whole pre-declared family.">
        <Table testid="v3-stats" head={['Comparison', 'A', 'B', 'acc A', 'acc B', 'Δ (95% CI)', 'test']}
          rows={comps.map((c) => [c.name, <span className="text-[11px]">{c.a}</span>, <span className="text-[11px]">{c.b}</span>, pc(c.acc_a), pc(c.acc_b),
            <span>{pp(c.diff)} <span className="text-slate-500">[{pp(c.ci95[0])}, {pp(c.ci95[1])}]</span></span>, <Stat row={c} />])} />
      </Card>

      <Card title="Kernel diagnostics of the selected quantum kernels" subtitle="Training kernel of seed 0. Off-diagonal mean near 0 = concentration (all states nearly orthogonal); CKA = centred alignment with the labels; effective dimension of the eigenvalue spectrum.">
        <Table testid="v3-kernel" head={['Group', 'off-diag mean', 'CKA', 'eff. dim', 'top-10 eig. share', 'PSD']}
          rows={(d.groups as any[]).filter((g) => g.kernel_diagnostics_seed0).sort((a, b) => (b.kernel_diagnostics_seed0.centered_kernel_alignment ?? 0) - (a.kernel_diagnostics_seed0.centered_kernel_alignment ?? 0)).slice(0, 24)
            .map((g) => [g.display_name, g.kernel_diagnostics_seed0.offdiag_mean?.toFixed(3), g.kernel_diagnostics_seed0.centered_kernel_alignment?.toFixed(3),
              g.kernel_spectrum_seed0?.effective_dimension?.toFixed(1) ?? UNAVAILABLE, g.kernel_spectrum_seed0 ? pc(g.kernel_spectrum_seed0.top10_fraction) : UNAVAILABLE,
              g.kernel_diagnostics_seed0.psd_within_tol ? 'yes' : 'no'])} />
      </Card>

      <Card title="Every V3 group" subtitle="Selected configuration per group (validation), then evaluated once on the locked test set."
        actions={<select aria-label="category" value={cat} onChange={(e) => setCat(e.target.value)} className="rounded-lg bg-slate-900 px-2 py-1 text-xs text-slate-200 ring-1 ring-slate-700">
          <option value="all">all categories</option>{Object.entries(CAT).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}</select>}>
        <Table testid="v3-groups" head={['Model', 'Category', 'Qubits', 'Val F1', 'Test acc.', 'Macro-F1', 'Seeds (acc %)', 'Gates log/comp', 'Train time']}
          rows={groups.map((g) => [<span>{g.display_name}<div className="text-[10px] text-slate-500">{g.group}</div></span>,
            <span className="inline-flex items-center gap-1"><span className="h-2 w-2 rounded-full" style={{ background: CAT[g.category]?.color }} />{CAT[g.category]?.label ?? g.category}</span>,
            g.n_qubits ?? '—', g.val_f1_macro.mean?.toFixed(3), msx(g.test_accuracy), msx(g.test_f1_macro),
            <span className="font-mono text-[11px] text-slate-400">{(g.per_seed_test_accuracy as number[]).map((v) => (v * 100).toFixed(1)).join(' / ')}</span>,
            g.circuit?.gates_logical != null ? `${g.circuit.gates_logical} / ${g.circuit.gates_compiled ?? '—'}` : '—',
            g.train_time_s?.mean != null ? `${g.train_time_s.mean.toFixed(1)} s` : UNAVAILABLE])} />
      </Card>
      <div className="space-y-1 text-[11px] text-slate-500">{(d.notes as string[]).map((n) => <div key={n}>• {n}</div>)}</div>
    </div>
  );
}
