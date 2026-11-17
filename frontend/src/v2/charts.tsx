/* eslint-disable @typescript-eslint/no-explicit-any */
// Results-comparison charts. Every value comes from /api/v2/models (Protocol V2, locked test, mean ± sd over 3 seeds).
// Colour = model family (validated palette in theme.tsx); series inside one family are told apart by an ordinal
// ramp of that family's hue (validated with the dataviz validator, --ordinal) plus dash/marker and a direct label.
import { useState } from 'react';
import type { ReactNode } from 'react';
import {
  Bar, BarChart, CartesianGrid, Cell, ErrorBar, LabelList, Legend, Line, LineChart, ResponsiveContainer,
  Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis,
} from 'recharts';
import type { Model } from './api';
import { FAMILY, familyOfModel } from './theme';
import type { FamilyKey } from './theme';

const GRID = '#1e293b', AXIS = '#94a3b8', INK = '#e2e8f0', MUTED = '#94a3b8', SURFACE = '#0f172a';
const TEAL_RAMP = ['#9fe3c9', '#4cc79a', '#199e70'];            // qkc family, ordinal (validated)
const MAGENTA_RAMP = ['#a8335f', '#d55181', '#e68ab0', '#f5c2d6']; // encoding family, ordinal dark→light (validated)
const pc = (v: number | null | undefined) => (v == null ? null : +(v * 100).toFixed(2));
const fmtPct = (v: unknown) => (typeof v === 'number' ? `${v.toFixed(1)}%` : 'unavailable');
const byGroup = (ms: Model[]) => Object.fromEntries(ms.map((m) => [m.group, m]));
const isVariant = (m: Model) => m.shots > 0 || m.is_ablation || m.is_legacy_relabelled;
const tick = { fontSize: 11, fill: AXIS };

// ── shared chrome: card with chart / table toggle ──
export function ChartCard({ title, subtitle, table, children, testid, height = 300, footer }: {
  title: string; subtitle?: ReactNode; table: { head: string[]; rows: (string | number | null)[][] }; children: ReactNode;
  testid: string; height?: number; footer?: ReactNode;
}) {
  const [asTable, setAsTable] = useState(false);
  return (
    <section className="rounded-2xl border border-slate-800/80 bg-[#0f172a]/70 p-5" data-testid={testid}>
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-[15px] font-semibold text-slate-100">{title}</h3>
          {subtitle && <p className="mt-1 max-w-3xl text-xs leading-relaxed text-slate-400">{subtitle}</p>}
        </div>
        <div className="flex rounded-lg bg-slate-950/60 p-0.5 text-[11px] ring-1 ring-slate-800" role="group" aria-label={`${title} view`}>
          {(['Chart', 'Table'] as const).map((v) => (
            <button key={v} onClick={() => setAsTable(v === 'Table')} aria-pressed={asTable === (v === 'Table')}
              className={`rounded-md px-2.5 py-1 ${asTable === (v === 'Table') ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-slate-200'}`}>{v}</button>
          ))}
        </div>
      </div>
      {asTable ? (
        <div className="overflow-x-auto"><table className="w-full text-xs tabular-nums">
          <thead className="text-left text-[11px] text-slate-500"><tr>{table.head.map((h) => <th key={h} className="px-2 py-1.5 font-medium">{h}</th>)}</tr></thead>
          <tbody>{table.rows.map((r, i) => <tr key={i} className="border-t border-slate-800/70">{r.map((c, j) => <td key={j} className="px-2 py-1.5 text-slate-200">{c ?? 'unavailable'}</td>)}</tr>)}</tbody>
        </table></div>
      ) : <div style={{ height }} className="w-full">{children}</div>}
      {footer && <div className="mt-2 text-[11px] leading-relaxed text-slate-500">{footer}</div>}
    </section>
  );
}

function TipBox({ title, rows }: { title?: ReactNode; rows: { color?: string; label: ReactNode; value: ReactNode; dash?: boolean }[] }) {
  return (
    <div className="max-w-xs rounded-lg bg-[#0b1220] px-3 py-2 text-xs shadow-xl ring-1 ring-slate-700">
      {title && <div className="mb-1 font-medium text-slate-100">{title}</div>}
      {rows.map((r, i) => (
        <div key={i} className="flex items-center gap-2 py-0.5">
          {r.color && <span className="inline-block h-2 w-3 shrink-0 rounded-sm" style={{ background: r.color }} />}
          <span className="text-slate-400">{r.label}</span><span className="ml-auto pl-3 font-medium tabular-nums text-slate-100">{r.value}</span>
        </div>
      ))}
    </div>
  );
}

// Legend in the same order as the series are drawn (Recharts would otherwise sort it).
export function LegendRow({ items }: { items: { name: string; color: string; dash?: string; shape?: 'line' | 'square' | 'dot' }[] }) {
  return (
    <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 pt-2 text-[11px] text-slate-300">
      {items.map((it) => (
        <span key={it.name} className="inline-flex items-center gap-1.5">
          <svg width={18} height={10} aria-hidden>{it.shape === 'line'
            ? <line x1={1} x2={17} y1={5} y2={5} stroke={it.color} strokeWidth={2} strokeDasharray={it.dash} />
            : it.shape === 'dot' ? <circle cx={9} cy={5} r={4} fill={it.color} /> : <rect x={3} y={1} width={10} height={8} rx={2} fill={it.color} />}</svg>
          {it.name}
        </span>
      ))}
    </div>
  );
}

// Spread end-of-line labels so they never overlap: returns a pixel dy per series (approximate px per unit of y).
export function spreadLabels(vals: { key: string; v: number | null }[], pxPerUnit: number, minGap = 13) {
  const pts = vals.filter((x) => x.v != null).map((x) => ({ key: x.key, y: -(x.v as number) * pxPerUnit })).sort((a, b) => a.y - b.y);
  const placed: number[] = [];
  pts.forEach((p, i) => { placed.push(i === 0 ? p.y : Math.max(p.y, placed[i - 1] + minGap)); });
  return Object.fromEntries(pts.map((p, i) => [p.key, placed[i] - p.y]));
}

// Direct label at the last point of a line (selective labelling: one label per series).
const endLabel = (text: string, n: number, dy = 0) => (p: any) => (p.index === n - 1 && p.value != null
  ? <text x={p.x + 8} y={p.y + 4 + dy} fontSize={11} fill={INK}>{text}</text> : null);

// ── 1. Best model per family ──
export function familyBest(models: Model[]) {
  const fams = Object.keys(FAMILY) as FamilyKey[];
  return fams.map((f) => {
    const pool = models.filter((m) => familyOfModel(m) === f && !isVariant(m) && m.test_accuracy.mean != null);
    const best = pool.reduce<Model | null>((b, m) => ((m.test_accuracy.mean ?? -1) > (b?.test_accuracy.mean ?? -1) ? m : b), null);
    return best ? { fam: f, label: FAMILY[f].short, model: best.display_name, acc: pc(best.test_accuracy.mean)!, sd: pc(best.test_accuracy.std) ?? 0, color: FAMILY[f].color, n: pool.length } : null;
  }).filter(Boolean).sort((a, b) => b!.acc - a!.acc) as { fam: FamilyKey; label: string; model: string; acc: number; sd: number; color: string; n: number }[];
}

export function FamilyBestChart({ models }: { models: Model[] }) {
  const data = familyBest(models);
  return (
    <ChartCard testid="chart-family-best" title="Best model in each family" height={Math.max(220, data.length * 44)}
      subtitle="Test accuracy of the strongest configuration per family; whiskers show ± 1 standard deviation over seeds 0, 1, 2."
      table={{ head: ['Family', 'Best model', 'Test accuracy %', 'sd (pp)', 'models in family'], rows: data.map((d) => [d.label, d.model, d.acc.toFixed(1), d.sd.toFixed(1), d.n]) }}>
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 56, top: 4, bottom: 4 }} barCategoryGap={10}>
          <CartesianGrid horizontal={false} stroke={GRID} />
          <XAxis type="number" domain={[0, 100]} tick={tick} unit="%" stroke={GRID} />
          <YAxis type="category" dataKey="label" width={112} tick={{ ...tick, fill: INK }} stroke={GRID} />
          <Tooltip cursor={{ fill: 'rgba(148,163,184,0.08)' }} content={({ active, payload }) => active && payload?.length
            ? <TipBox title={payload[0].payload.model} rows={[{ color: payload[0].payload.color, label: payload[0].payload.label, value: `${payload[0].payload.acc.toFixed(1)}% ± ${payload[0].payload.sd.toFixed(1)}` }]} /> : null} />
          <Bar dataKey="acc" radius={[0, 4, 4, 0]} barSize={20} isAnimationActive={false}>
            {data.map((d) => <Cell key={d.fam} fill={d.color} />)}
            <ErrorBar dataKey="sd" direction="x" width={6} stroke={INK} strokeWidth={1.5} />
            <LabelList dataKey="acc" position="right" offset={14} formatter={fmtPct as any} style={{ fill: INK, fontSize: 11, fontWeight: 600 }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

// ── 2. Every model, one lane per family ──
export function ModelStripChart({ models }: { models: Model[] }) {
  const fams = (Object.keys(FAMILY) as FamilyKey[]).filter((f) => models.some((m) => familyOfModel(m) === f && !isVariant(m)));
  const lane = Object.fromEntries(fams.map((f, i) => [f, fams.length - 1 - i]));
  const series = fams.map((f) => ({
    fam: f,
    pts: models.filter((m) => familyOfModel(m) === f && !isVariant(m) && m.test_accuracy.mean != null)
      .map((m, i) => ({ x: pc(m.test_accuracy.mean)!, y: lane[f] + ((i % 5) - 2) * 0.09, name: m.display_name, sd: pc(m.test_accuracy.std) ?? 0, q: m.n_qubits })),
  }));
  return (
    <ChartCard testid="chart-model-strip" title="Every selected model, by family" height={Math.max(260, fams.length * 52)}
      subtitle="Each dot is one configuration (shot-noise variants, ablations and relabelled V0 rows excluded). Hover for the model."
      table={{ head: ['Family', 'Model', 'Test accuracy %'], rows: series.flatMap((s) => [...s.pts].sort((a, b) => b.x - a.x).map((p) => [FAMILY[s.fam].short, p.name, p.x.toFixed(1)])) }}>
      <ResponsiveContainer>
        <ScatterChart margin={{ left: 8, right: 16, top: 8, bottom: 4 }}>
          <CartesianGrid horizontal={false} stroke={GRID} />
          <XAxis type="number" dataKey="x" domain={[0, 100]} unit="%" tick={tick} stroke={GRID} name="accuracy" />
          <YAxis type="number" dataKey="y" domain={[-0.6, fams.length - 0.4]} ticks={fams.map((f) => lane[f])} width={112}
            tickFormatter={(v) => FAMILY[fams[fams.length - 1 - v]]?.short ?? ''} tick={{ ...tick, fill: INK }} stroke={GRID} />
          <ZAxis range={[64, 64]} />
          <Tooltip cursor={false} content={({ active, payload }) => {
            const p = active && payload?.[0]?.payload;
            if (!p) return null;
            const f = series.find((s) => s.pts.includes(p))?.fam;
            return <TipBox title={p.name} rows={[{ color: f ? FAMILY[f].color : undefined, label: f ? FAMILY[f].short : '', value: `${p.x.toFixed(1)}% ± ${p.sd.toFixed(1)}` }, ...(p.q ? [{ label: 'qubits', value: p.q }] : [])]} />;
          }} />
          {series.map((s) => <Scatter key={s.fam} name={FAMILY[s.fam].short} data={s.pts} fill={FAMILY[s.fam].color} stroke={SURFACE} strokeWidth={2} isAnimationActive={false} />)}
        </ScatterChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

// ── 3. Hybrid: feature effect vs classifier effect ──
export function hybridEffectData(models: Model[]) {
  const g = byGroup(models);
  const best = (ids: string[]) => ids.map((i) => g[i]).filter(Boolean).reduce<Model | null>((b, m) => ((m.test_accuracy.mean ?? -1) > (b?.test_accuracy.mean ?? -1) ? m : b), null);
  return [4, 6, 8].map((k) => {
    const pix = best(['product_ry', 'zz_linear', 'zz_full'].map((f) => `E3-pca${k}-qkc-${f}`));
    const cls = best([`E5-mnv3pca${k}-logreg`, `E5-mnv3pca${k}-rbfsvm`]);
    const hyb = best([...['product_ry', 'zz_linear', 'zz_full'].map((f) => `E5-mnv3pca${k}-qkc-${f}`), `E5-mnv3pca${k}-vqc`]);
    return { k: `${k} features`, pix: pc(pix?.test_accuracy.mean), pixSd: pc(pix?.test_accuracy.std), pixName: pix?.display_name,
      cls: pc(cls?.test_accuracy.mean), clsSd: pc(cls?.test_accuracy.std), clsName: cls?.display_name,
      hyb: pc(hyb?.test_accuracy.mean), hybSd: pc(hyb?.test_accuracy.std), hybName: hyb?.display_name };
  });
}

export function HybridEffectChart({ models }: { models: Model[] }) {
  const data = hybridEffectData(models);
  const S = [
    { key: 'pix', sd: 'pixSd', name: 'Pixel PCA + best quantum kernel', color: FAMILY.qkc.color },
    { key: 'cls', sd: 'clsSd', name: 'CNN features + best classical', color: FAMILY.cnn.color },
    { key: 'hyb', sd: 'hybSd', name: 'CNN features + best quantum (hybrid)', color: FAMILY.hybrid.color },
  ] as const;
  return (
    <ChartCard testid="chart-hybrid-effect" title="Where the hybrid accuracy comes from" height={320}
      subtitle="Same number of features k for all three bars. The jump from the first bar to the other two is the feature effect (CNN vs pixels); the gap between the last two is the classifier effect (quantum vs classical)."
      footer="The orange and violet bars use identical MobileNetV3 features; their difference stays within seed noise. The CNN features are computed classically, so this is not a quantum advantage."
      table={{ head: ['k', ...S.map((s) => `${s.name} %`), 'model names'], rows: data.map((d: any) => [d.k, ...S.map((s) => (d[s.key] == null ? null : `${d[s.key].toFixed(1)} ± ${d[s.sd].toFixed(1)}`)), [d.pixName, d.clsName, d.hybName].join(' | ')]) }}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ left: 0, right: 8, top: 18, bottom: 4 }} barGap={2} barCategoryGap="22%">
          <CartesianGrid vertical={false} stroke={GRID} />
          <XAxis dataKey="k" tick={{ ...tick, fill: INK }} stroke={GRID} />
          <YAxis domain={[0, 100]} unit="%" tick={tick} stroke={GRID} width={44} />
          <Tooltip cursor={{ fill: 'rgba(148,163,184,0.08)' }} content={({ active, payload, label }) => active && payload?.length
            ? <TipBox title={label} rows={S.map((s) => { const d: any = payload[0].payload; return { color: s.color, label: d[`${s.key}Name`] ?? s.name, value: d[s.key] == null ? 'unavailable' : `${d[s.key].toFixed(1)}%` }; })} /> : null} />
          <Legend content={() => <LegendRow items={S.map((x) => ({ name: x.name, color: x.color }))} />} />
          {S.map((s) => (
            <Bar key={s.key} dataKey={s.key} name={s.name} fill={s.color} radius={[4, 4, 0, 0]} maxBarSize={44} isAnimationActive={false}>
              <ErrorBar dataKey={s.sd} width={5} stroke={INK} strokeWidth={1.2} />
              <LabelList dataKey={s.key} position="top" offset={8} formatter={fmtPct as any} style={{ fill: INK, fontSize: 10 }} />
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

// ── 4. Accuracy vs number of qubits / features ──
export function QubitScalingChart({ models }: { models: Model[] }) {
  const g = byGroup(models);
  const ks = [4, 6, 8];
  const S = [
    { key: 'rbf', id: (k: number) => `E6-pca${k}-rbfsvm-angle`, name: 'Classical RBF-SVM (same features)', color: FAMILY.classical.color, dash: '6 4' },
    { key: 'prod', id: (k: number) => `E3-pca${k}-qkc-product_ry`, name: 'QKC product-RY', color: TEAL_RAMP[0], dash: '2 3' },
    { key: 'zzl', id: (k: number) => `E3-pca${k}-qkc-zz_linear`, name: 'QKC ZZ-linear', color: TEAL_RAMP[1], dash: '8 3 2 3' },
    { key: 'zzf', id: (k: number) => `E3-pca${k}-qkc-zz_full`, name: 'QKC ZZ-full', color: TEAL_RAMP[2], dash: undefined },
    { key: 'vqc', id: (k: number) => `E4-pca${k}-vqc`, name: 'VQC', color: FAMILY.vqc.color, dash: undefined },
  ];
  const data = ks.map((k) => Object.fromEntries([['k', k], ...S.map((s) => [s.key, pc(g[s.id(k)]?.test_accuracy.mean)])]));
  const short: Record<string, string> = { rbf: 'RBF-SVM', prod: 'product-RY', zzl: 'ZZ-linear', zzf: 'ZZ-full', vqc: 'VQC' };
  const last: any = data[data.length - 1];
  const dy = spreadLabels(S.map((x) => ({ key: x.key, v: last[x.key] })), 230 / 60);
  return (
    <ChartCard testid="chart-qubit-scaling" title="Accuracy as qubits grow (pixel PCA features)" height={320}
      subtitle="k PCA features → k qubits. The classical RBF-SVM receives exactly the same angle features as the quantum kernels."
      table={{ head: ['qubits / features', ...S.map((s) => `${s.name} %`)], rows: data.map((d: any) => [d.k, ...S.map((s) => (d[s.key] == null ? null : d[s.key].toFixed(1)))]) }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ left: 0, right: 92, top: 12, bottom: 4 }}>
          <CartesianGrid vertical={false} stroke={GRID} />
          <XAxis dataKey="k" tick={{ ...tick, fill: INK }} stroke={GRID} tickFormatter={(v) => `${v} qubits`} padding={{ left: 16, right: 16 }} />
          <YAxis domain={[20, 80]} unit="%" tick={tick} stroke={GRID} width={44} />
          <Tooltip cursor={{ stroke: '#475569' }} content={({ active, payload, label }) => active && payload?.length
            ? <TipBox title={`${label} qubits / features`} rows={[...payload].sort((a: any, b: any) => b.value - a.value).map((p: any) => ({ color: p.color, label: p.name, value: fmtPct(p.value) }))} /> : null} />
          <Legend content={() => <LegendRow items={S.map((x) => ({ name: x.name, color: x.color, dash: x.dash, shape: 'line' as const }))} />} />
          {S.map((s) => (
            <Line key={s.key} dataKey={s.key} name={s.name} stroke={s.color} strokeWidth={2} strokeDasharray={s.dash} isAnimationActive={false}
              dot={{ r: 4, fill: s.color, stroke: SURFACE, strokeWidth: 2 }} activeDot={{ r: 6, stroke: SURFACE, strokeWidth: 2 }}>
              <LabelList dataKey={s.key} content={endLabel(short[s.key], ks.length, dy[s.key] ?? 0)} />
            </Line>
          ))}
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

// ── 5. Finite shots vs exact simulation (two small multiples, same y scale) ──
const SHOT_X = ['100', '500', '1,000', '5,000', '10,000', 'exact'];
function shotRow(g: Record<string, Model>, base: string, shots: number[]) {
  const row: Record<string, number | null> = {};
  shots.forEach((s) => { row[s.toLocaleString('en-US')] = pc(g[`${base}-shots${s}`]?.test_accuracy.mean); });
  row.exact = pc(g[base]?.test_accuracy.mean);
  return row;
}
export function ShotsCharts({ models }: { models: Model[] }) {
  const g = byGroup(models);
  const qk = [4, 6, 8].map((k, i) => ({ key: `q${k}`, name: `ZZ-full · ${k} qubits`, color: TEAL_RAMP[i], row: shotRow(g, `E3-pca${k}-qkc-zz_full`, [100, 500, 1000, 5000]) }));
  const enc = [
    { key: 'frqi', name: 'FRQI 8×8', color: MAGENTA_RAMP[3], dash: undefined, row: shotRow(g, 'E1-frqi8-qkc', [100, 1000, 10000]) },
    { key: 'neqr', name: 'NEQR 8×8 · 4-bit', color: MAGENTA_RAMP[1], dash: '6 4', row: shotRow(g, 'E2-neqr8-b4-qkc', [100, 1000, 10000]) },
  ];
  const build = (ser: { key: string; row: Record<string, number | null> }[]) => SHOT_X.map((x) => Object.fromEntries([['x', x], ...ser.map((s) => [s.key, s.row[x] ?? null])])).filter((d: any) => ser.some((s) => d[s.key] != null));
  const one = (title: string, ser: { key: string; name: string; color: string; dash?: string; row: any }[], testid: string, sub: string) => {
    const data = build(ser);
    return (
      <ChartCard testid={testid} title={title} subtitle={sub} height={280}
        table={{ head: ['shots', ...ser.map((s) => `${s.name} %`)], rows: data.map((d: any) => [d.x, ...ser.map((s) => (d[s.key] == null ? null : d[s.key].toFixed(1)))]) }}>
        <ResponsiveContainer>
          <LineChart data={data} margin={{ left: 0, right: 16, top: 12, bottom: 4 }}>
            <CartesianGrid vertical={false} stroke={GRID} />
            <XAxis dataKey="x" tick={{ ...tick, fill: INK }} stroke={GRID} padding={{ left: 12, right: 12 }} />
            <YAxis domain={[20, 80]} unit="%" tick={tick} stroke={GRID} width={44} />
            <Tooltip cursor={{ stroke: '#475569' }} content={({ active, payload, label }) => active && payload?.length
              ? <TipBox title={label === 'exact' ? 'exact statevector' : `${label} shots`} rows={payload.map((p: any) => ({ color: p.color, label: p.name, value: fmtPct(p.value) }))} /> : null} />
            <Legend content={() => <LegendRow items={ser.map((x) => ({ name: x.name, color: x.color, dash: x.dash, shape: 'line' as const }))} />} />
            {ser.map((s) => <Line key={s.key} dataKey={s.key} name={s.name} stroke={s.color} strokeWidth={2} strokeDasharray={s.dash} connectNulls isAnimationActive={false}
              dot={{ r: 4, fill: s.color, stroke: SURFACE, strokeWidth: 2 }} activeDot={{ r: 6, stroke: SURFACE, strokeWidth: 2 }} />)}
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>
    );
  };
  return (
    <div className="grid gap-5 xl:grid-cols-2">
      {one('Shot noise: quantum kernels', qk, 'chart-shots-qkc', 'Accuracy when the kernel is estimated from a finite number of measurements, compared with exact simulation.')}
      {one('Shot noise: FRQI / NEQR kernels', enc, 'chart-shots-encoding', 'FRQI kernels lose much more accuracy under finite shots than NEQR kernels.')}
    </div>
  );
}

// ── 6. NEQR bit depth × image resolution ──
export function NeqrBitsChart({ models }: { models: Model[] }) {
  const g = byGroup(models);
  const res = [2, 4, 8, 16];
  const data = [2, 4, 8].map((b) => Object.fromEntries([['bits', `${b}-bit`], ...res.map((r) => [`r${r}`, pc(g[`E2-neqr${r}-b${b}-qkc`]?.test_accuracy.mean)])]));
  const dy = spreadLabels(res.map((r) => ({ key: `r${r}`, v: (data[2] as any)[`r${r}`] })), 210 / 60);
  return (
    <ChartCard testid="chart-neqr-bits" title="NEQR: more bits per pixel ≠ better classification" height={300}
      subtitle="Higher precision reconstructs the image better, yet 8-bit kernels score below 4-bit: the NEQR overlap only rewards exactly equal intensities, which become rare at 256 levels."
      table={{ head: ['precision', ...res.map((r) => `${r}×${r} %`)], rows: data.map((d: any) => [d.bits, ...res.map((r) => (d[`r${r}`] == null ? null : d[`r${r}`].toFixed(1)))]) }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ left: 0, right: 64, top: 12, bottom: 4 }}>
          <CartesianGrid vertical={false} stroke={GRID} />
          <XAxis dataKey="bits" tick={{ ...tick, fill: INK }} stroke={GRID} padding={{ left: 16, right: 16 }} />
          <YAxis domain={[20, 80]} unit="%" tick={tick} stroke={GRID} width={44} />
          <Tooltip cursor={{ stroke: '#475569' }} content={({ active, payload, label }) => active && payload?.length
            ? <TipBox title={`NEQR ${label}`} rows={payload.map((p: any) => ({ color: p.color, label: p.name, value: fmtPct(p.value) }))} /> : null} />
          <Legend content={() => <LegendRow items={res.map((r, i) => ({ name: `${r}×${r} image`, color: MAGENTA_RAMP[i], shape: 'line' as const }))} />} />
          {res.map((r, i) => (
            <Line key={r} dataKey={`r${r}`} name={`${r}×${r} image`} stroke={MAGENTA_RAMP[i]} strokeWidth={2} isAnimationActive={false}
              dot={{ r: 4, fill: MAGENTA_RAMP[i], stroke: SURFACE, strokeWidth: 2 }} activeDot={{ r: 6, stroke: SURFACE, strokeWidth: 2 }}>
              <LabelList dataKey={`r${r}`} content={endLabel(`${r}×${r}`, 3, dy[`r${r}`] ?? 0)} />
            </Line>
          ))}
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

// ── 7. Accuracy vs inference cost ── (paradigm triple orange / aqua / violet: validated all-pairs for scatter)
export function CostChart({ models }: { models: Model[] }) {
  const groups: { key: string; name: string; color: string; pick: (m: Model) => boolean }[] = [
    { key: 'classical', name: 'Classical (pixels / CNN)', color: FAMILY.cnn.color, pick: (m) => !m.is_quantum },
    { key: 'quantum', name: 'Quantum (simulated)', color: FAMILY.qkc.color, pick: (m) => m.is_quantum && familyOfModel(m) !== 'hybrid' },
    { key: 'hybrid', name: 'Hybrid (CNN + quantum)', color: FAMILY.hybrid.color, pick: (m) => familyOfModel(m) === 'hybrid' },
  ];
  const ok = models.filter((m) => !isVariant(m) && m.test_accuracy.mean != null && (m.test_inference_ms_per_image.mean ?? 0) > 0);
  const series = groups.map((gr) => ({ ...gr, pts: ok.filter(gr.pick).map((m) => ({ x: m.test_inference_ms_per_image.mean!, y: pc(m.test_accuracy.mean)!, name: m.display_name })) }));
  const xs = series.flatMap((s) => s.pts.map((p) => p.x));
  const lo = xs.length ? Math.floor(Math.log10(Math.min(...xs))) : -3, hi = xs.length ? Math.ceil(Math.log10(Math.max(...xs))) : 1;
  const ticks = Array.from({ length: hi - lo + 1 }, (_, i) => 10 ** (lo + i));
  return (
    <ChartCard testid="chart-cost" title="Accuracy vs prediction time" height={320}
      subtitle="Prediction time per test image (log scale) on this CPU. Quantum times are classical simulation times, not quantum-hardware times."
      table={{ head: ['Group', 'Model', 'Test accuracy %', 'ms / image'], rows: series.flatMap((s) => s.pts.map((p) => [s.name, p.name, p.y.toFixed(1), p.x.toFixed(3)])) }}>
      <ResponsiveContainer>
        <ScatterChart margin={{ left: 0, right: 16, top: 8, bottom: 4 }}>
          <CartesianGrid stroke={GRID} />
          <XAxis type="number" dataKey="x" scale="log" domain={[ticks[0], ticks[ticks.length - 1]]} ticks={ticks} tick={tick} stroke={GRID} tickFormatter={(v) => `${v >= 1 ? v : v.toString()} ms`} />
          <YAxis type="number" dataKey="y" domain={[0, 100]} unit="%" tick={tick} stroke={GRID} width={44} />
          <ZAxis range={[64, 64]} />
          <Tooltip cursor={false} content={({ active, payload }) => {
            const p = active && payload?.[0]?.payload;
            if (!p) return null;
            const s = series.find((x) => x.pts.includes(p));
            return <TipBox title={p.name} rows={[{ color: s?.color, label: s?.name, value: `${p.y.toFixed(1)}%` }, { label: 'time / image', value: `${p.x.toFixed(3)} ms` }]} />;
          }} />
          <Legend content={() => <LegendRow items={series.map((x) => ({ name: x.name, color: x.color, shape: 'dot' as const }))} />} />
          {series.map((s) => <Scatter key={s.key} name={s.name} data={s.pts} fill={s.color} stroke={SURFACE} strokeWidth={2} isAnimationActive={false} />)}
        </ScatterChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function ResultsCharts({ models }: { models: Model[] }) {
  return (
    <div className="space-y-5">
      <div className="grid gap-5 xl:grid-cols-2"><FamilyBestChart models={models} /><ModelStripChart models={models} /></div>
      <HybridEffectChart models={models} />
      <div className="grid gap-5 xl:grid-cols-2"><QubitScalingChart models={models} /><NeqrBitsChart models={models} /></div>
      <ShotsCharts models={models} />
      <CostChart models={models} />
    </div>
  );
}
