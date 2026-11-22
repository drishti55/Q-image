import { Link } from 'react-router-dom';
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useV2 } from '../api';
import type { Model, ModelsResponse } from '../api';
import { Badge, Card, ErrorState, Loading, PageHeader, chartTheme, int, msPct, num , fmt } from '../ui';
import { Collapsible } from '../theme';
import EncodingWalkthrough from '../learn/EncodingWalkthrough';
import Quiz from '../learn/Quiz';
import { ExplainThis } from '../learn/ExplainThis';

type Agg = { mean: number | null; std?: number; n?: number; n_finite?: number; n_exact?: number };
type ModeSummary = Record<string, { mse: Agg; psnr: Agg; ssim: Agg }> & { decode_time_s_mean?: number };
export type ReconRecord = {
  record_id: string; status: string; error?: string | null;
  config: { representation: string; resolution: number; intensity_bits: number | null; shots: number[]; images: string[] } | null;
  summary: Record<string, ModeSummary> | null; timing: { build_time_s_mean: number; statevector_sim_time_s_mean: number } | null;
  circuit_stats: { n_qubits: number; gates_logical: number; depth_logical: number; gates_compiled: number; depth_compiled: number; cx_compiled: number } | null;
};
const MODES = ['statevector', 'shots100', 'shots1000', 'shots10000', 'shots100000'];
const MODE_LABEL: Record<string, string> = { statevector: 'exact', shots100: '10²', shots1000: '10³', shots10000: '10⁴', shots100000: '10⁵' };

const sci = (v: number | null | undefined) => v === null || v === undefined ? 'unavailable' : v === 0 ? '0 (exact)' : v < 1e-12 ? `${v.toExponential(1)} (exact)` : v.toExponential(2);

function clsFor(models: Model[], rep: string, res: number, bits: number | null) {
  return models.filter((m) => m.category === 'FRQI / NEQR encoding kernels' && !m.shots &&
    String(m.params.representation) === rep && m.display_name.includes(`${res}×${res}`) &&
    (rep === 'FRQI' || Number(m.params.bits) === bits));
}

function EncodingTable({ rep, recs, models }: { rep: string; recs: ReconRecord[]; models: Model[] }) {
  const rows = recs.filter((r) => r.config?.representation === rep).sort((a, b) =>
    (a.config!.resolution - b.config!.resolution) || ((a.config!.intensity_bits ?? 0) - (b.config!.intensity_bits ?? 0)));
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs tabular-nums">
        <thead className="text-left text-[11px] uppercase tracking-wider text-slate-500">
          <tr>
            <th className="pb-2">Image</th>{rep === 'NEQR' && <th className="pb-2">Precision</th>}<th className="pb-2">Qubits</th>
            <th className="pb-2">Gates logical → compiled</th><th className="pb-2">Depth (compiled)</th><th className="pb-2">CX</th>
            <th className="pb-2">MSE exact</th><th className="pb-2">MSE 10³ shots</th><th className="pb-2">MSE 10⁵ shots</th><th className="pb-2">SSIM 10³</th>
            <th className="pb-2">Classification (exact kernel)</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60">
          {rows.map((r) => {
            const c = r.config!, cs = r.circuit_stats, s = r.summary;
            const cls = clsFor(models, rep, c.resolution, c.intensity_bits);
            return (
              <tr key={r.record_id}>
                <td className="py-2">{c.resolution}×{c.resolution}</td>
                {rep === 'NEQR' && <td>{c.intensity_bits}-bit</td>}
                <td>{cs?.n_qubits ?? 'unavailable'}</td>
                <td>{cs ? `${int(cs.gates_logical)} → ${int(cs.gates_compiled)}` : 'unavailable'}</td>
                <td>{int(cs?.depth_compiled)}</td>
                <td>{int(cs?.cx_compiled)}</td>
                <td>{sci(s?.statevector?.vs_preprocessed?.mse?.mean)}</td>
                <td>{sci(s?.shots1000?.vs_preprocessed?.mse?.mean)}</td>
                <td>{sci(s?.shots100000?.vs_preprocessed?.mse?.mean)}</td>
                <td>{num(s?.shots1000?.vs_preprocessed?.ssim?.mean)}</td>
                <td>{cls.length ? cls.map((m) => <Link key={m.group} to={`/models?focus=${m.group}`} className="mr-2 text-cyan-300 hover:underline">{msPct(m.test_accuracy)}{m.params.angle_scale && m.params.angle_scale !== 1 ? ` (×${m.params.angle_scale})` : ''}</Link>) : '—'}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function EncodingPage() {
  const rec = useV2<{ count: number; records: ReconRecord[] }>('/reconstructions');
  const mod = useV2<ModelsResponse>('/models');
  if (rec.loading || mod.loading) return <Loading />;
  if (rec.error || mod.error) return <ErrorState error={(rec.error ?? mod.error)!} />;
  const recs = (rec.data?.records ?? []).filter((r) => r.status === 'completed' && r.config);
  const models = mod.data?.models ?? [];
  const res = [...new Set(recs.map((r) => r.config!.resolution))].sort((a, b) => a - b);
  const find = (rep: string, r: number, b: number | null) => recs.find((x) => x.config!.representation === rep && x.config!.resolution === r && (rep === 'FRQI' || x.config!.intensity_bits === b));
  const resourceData = res.map((r) => ({
    res: `${r}×${r}`, FRQI: find('FRQI', r, null)?.circuit_stats?.gates_compiled,
    'NEQR 2-bit': find('NEQR', r, 2)?.circuit_stats?.gates_compiled, 'NEQR 4-bit': find('NEQR', r, 4)?.circuit_stats?.gates_compiled,
    'NEQR 8-bit': find('NEQR', r, 8)?.circuit_stats?.gates_compiled }));
  const clsData = res.map((r) => {
    const a = (rep: string, b: number | null) => clsFor(models, rep, r, b).filter((m) => !m.params.angle_scale || m.params.angle_scale === 1)[0]?.test_accuracy.mean ?? null;
    return { res: `${r}×${r}`, FRQI: a('FRQI', null), 'NEQR 2-bit': a('NEQR', 2), 'NEQR 4-bit': a('NEQR', 4), 'NEQR 8-bit': a('NEQR', 8) };
  });
  const shotData = MODES.slice(1).map((m) => ({ shots: MODE_LABEL[m], ...Object.fromEntries(
    [['FRQI 8×8', find('FRQI', 8, null)], ['NEQR 8×8 4-bit', find('NEQR', 8, 4)], ['FRQI 16×16', find('FRQI', 16, null)], ['NEQR 16×16 8-bit', find('NEQR', 16, 8)]]
      .map(([k, r]) => [k as string, (r as ReconRecord | undefined)?.summary?.[m]?.vs_preprocessed?.mse?.mean ?? null])) }));
  const colors = { FRQI: '#22d3ee', 'NEQR 2-bit': '#c4b5fd', 'NEQR 4-bit': '#a78bfa', 'NEQR 8-bit': '#7c3aed' } as Record<string, string>;

  return (
    <div className="space-y-6">
      <PageHeader title="Quantum Image Encoding"
        subtitle="FRQI and NEQR encode a whole image into one quantum state. Encoding / reconstruction quality and classification accuracy are different tasks and are reported side by side, never ranked together. Resources: original encoder circuits transpiled to {cx, rz, sx, x} (optimization level 1, all-to-all, seed 0); NEQR values are means over 5 images because its gate count depends on pixel bits." >
        <Link to="/circuits" className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800">Inspect circuits →</Link>
        <Link to="/reconstruction-full" className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800">Reconstruction (all 1,800) →</Link>
      </PageHeader>
      <Card actions={<span className="flex flex-wrap gap-1"><ExplainThis id="frqi" /><ExplainThis id="neqr" /><ExplainThis id="qubit" /></span>} title="How FRQI and NEQR work — step by step" subtitle="Press Play. A real steel image is written into qubits, gate by gate.">
        <EncodingWalkthrough />
      </Card>
      <Quiz id="encoding" />
      {!recs.length ? <Card><div className="text-sm text-slate-400">No reconstruction records available.</div></Card> : (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            <Card title="FRQI — Flexible Representation of Quantum Images" subtitle="|I⟩ = N^-½ Σᵢ (cos θᵢ|0⟩ + sin θᵢ|1⟩) ⊗ |i⟩, θᵢ = intensity · π/2">
              <ul className="list-disc space-y-1 pl-5 text-sm text-slate-400">
                <li>2·log₂(r) position qubits + 1 colour qubit (intensity stored in an amplitude).</li>
                <li>One multi-controlled RY per pixel; decoding from shots needs P(colour=1 | position) → many shots per pixel.</li>
                <li>Statevector decoding is exact (consistency check of encoder + decoder).</li>
              </ul>
            </Card>
            <Card title="NEQR — Novel Enhanced Quantum Representation" subtitle="|I⟩ = N^-½ Σᵢ |Cᵢ⟩ ⊗ |i⟩, Cᵢ = q-bit intensity">
              <ul className="list-disc space-y-1 pl-5 text-sm text-slate-400">
                <li>2·log₂(r) position qubits + q intensity qubits (2, 4 or 8 bits; basis-state encoding).</li>
                <li>Multi-controlled X gates per set bit; exact once every position is sampled (majority vote).</li>
                <li>Error = quantisation (vs the preprocessed image) unless positions are never sampled.</li>
              </ul>
            </Card>
          </div>
          {(() => {
            const f8 = find('FRQI', 8, null), n8 = find('NEQR', 8, 4);
            const c8 = clsData.find((x) => x.res === '8×8');
            const rows: [string, string, string, string][] = [
              ['Qubits needed', String(f8?.circuit_stats?.n_qubits ?? 'unavailable'), String(n8?.circuit_stats?.n_qubits ?? 'unavailable'), 'fewer is better'],
              ['Basic gates (compiled)', int(f8?.circuit_stats?.gates_compiled), int(n8?.circuit_stats?.gates_compiled), 'fewer is better'],
              ['Reconstruction error, 1,000 shots (MSE)', sci(f8?.summary?.shots1000?.vs_preprocessed?.mse?.mean), sci(n8?.summary?.shots1000?.vs_preprocessed?.mse?.mean), 'lower is better'],
              ['Defect classification accuracy', c8?.FRQI != null ? `${(c8.FRQI * 100).toFixed(1)}%` : 'unavailable', c8?.['NEQR 4-bit'] != null ? `${(c8['NEQR 4-bit']! * 100).toFixed(1)}%` : 'unavailable', 'higher is better'],
            ];
            return (
              <section className="rounded-2xl bg-slate-900/40 p-5 ring-1 ring-slate-800">
                <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
                  <div><h2 className="text-lg font-semibold text-white">FRQI vs NEQR at a glance</h2>
                    <p className="text-sm text-slate-400">8×8 images (NEQR with 4-bit brightness), measured values</p></div>
                </div>
                <div className="grid grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,1fr)] gap-x-4 text-sm">
                  <div /><div className="pb-2 text-center text-base font-semibold" style={{ color: '#22d3ee' }}>FRQI</div><div className="pb-2 text-center text-base font-semibold" style={{ color: '#a78bfa' }}>NEQR</div>
                  {rows.map(([lbl, a, b, hint]) => (
                    <div key={lbl} className="contents">
                      <div className="border-t border-slate-800 py-3"><div className="text-slate-200">{lbl}</div><div className="text-[11px] text-slate-500">{hint}</div></div>
                      <div className="border-t border-slate-800 py-3 text-center text-lg font-semibold tabular-nums text-white">{a}</div>
                      <div className="border-t border-slate-800 py-3 text-center text-lg font-semibold tabular-nums text-white">{b}</div>
                    </div>
                  ))}
                </div>
              </section>
            );
          })()}
          <Card title="FRQI vs NEQR — what the data shows">
            <ul className="grid gap-2 text-sm text-slate-400 md:grid-cols-2">
              {(() => {
                const f8 = find('FRQI', 8, null), n84 = find('NEQR', 8, 4);
                const out: string[] = [];
                if (f8?.circuit_stats && n84?.circuit_stats) out.push(`At 8×8, NEQR 4-bit needs ${int(n84.circuit_stats.gates_compiled)} compiled gates vs ${int(f8.circuit_stats.gates_compiled)} for FRQI (${(n84.circuit_stats.gates_compiled / f8.circuit_stats.gates_compiled).toFixed(1)}×) although its logical count is smaller (${int(n84.circuit_stats.gates_logical)} vs ${int(f8.circuit_stats.gates_logical)}).`);
                if (f8?.summary && n84?.summary) out.push(`With 10³ shots, FRQI 8×8 MSE is ${sci(f8.summary.shots1000.vs_preprocessed.mse.mean)} while NEQR 8×8 4-bit MSE is ${sci(n84.summary.shots1000.vs_preprocessed.mse.mean)} (its quantisation error).`);
                const c = clsData.find((x) => x.res === '8×8');
                if (c) out.push(`Classification at 8×8 (exact kernel): FRQI ${c.FRQI !== null ? (c.FRQI * 100).toFixed(1) + '%' : 'unavailable'}, NEQR 4-bit ${c['NEQR 4-bit'] !== null ? (c['NEQR 4-bit']! * 100).toFixed(1) + '%' : 'unavailable'}, NEQR 8-bit ${c['NEQR 8-bit'] !== null ? (c['NEQR 8-bit']! * 100).toFixed(1) + '%' : 'unavailable'} — the encoding that reconstructs best (8-bit) classifies worst.`);
                return out.map((t) => <li key={t} className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">{t}</li>);
              })()}
            </ul>
            <div className="mt-3 flex gap-2"><Badge tone="cyan">all values from results/qml_v2</Badge><Badge>simulated (Aer statevector + sampled shots)</Badge></div>
          </Card>
          <div className="grid gap-6 xl:grid-cols-3">
            <Card title="Compiled gates (log scale)" subtitle="Lower is cheaper. NEQR's logical counts hide multi-controlled X decompositions.">
              <div className="h-64"><ResponsiveContainer><BarChart data={resourceData}>
                <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} vertical={false} />
                <XAxis dataKey="res" tick={{ fontSize: 11, fill: chartTheme.axis }} />
                <YAxis scale="log" domain={['auto', 'auto']} allowDataOverflow tick={{ fontSize: 10, fill: chartTheme.axis }} tickFormatter={(v) => v >= 1000 ? `${Math.round(v / 1000)}k` : v} />
                <Tooltip contentStyle={chartTheme.tooltip} formatter={fmt((v) => int(v))} /><Legend wrapperStyle={{ fontSize: 11 }} />
                {Object.keys(colors).map((k) => <Bar key={k} dataKey={k} fill={colors[k]} />)}
              </BarChart></ResponsiveContainer></div>
            </Card>
            <Card title="Classification accuracy (exact kernel)" subtitle="Locked test, mean of 3 seeds; original encodings (no angle scaling).">
              <div className="h-64"><ResponsiveContainer><LineChart data={clsData}>
                <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
                <XAxis dataKey="res" tick={{ fontSize: 11, fill: chartTheme.axis }} />
                <YAxis domain={[0.2, 0.7]} tickFormatter={(v) => `${Math.round(v * 100)}%`} tick={{ fontSize: 10, fill: chartTheme.axis }} />
                <Tooltip contentStyle={chartTheme.tooltip} formatter={fmt((v) => `${(v * 100).toFixed(1)}%`)} /><Legend wrapperStyle={{ fontSize: 11 }} />
                {Object.keys(colors).map((k) => <Line key={k} dataKey={k} stroke={colors[k]} strokeWidth={2} dot />)}
              </LineChart></ResponsiveContainer></div>
            </Card>
            <Card actions={<span className="flex flex-wrap gap-1"><ExplainThis id="recon-metrics" /></span>} title="Reconstruction MSE vs shots (log)" subtitle="Mean over 30 images vs the preprocessed image. Exact (0) values are not plotted on a log axis.">
              <div className="h-64"><ResponsiveContainer><LineChart data={shotData.map((r) => Object.fromEntries(Object.entries(r).map(([k, v]) => [k, typeof v === 'number' && v <= 0 ? null : v])))}>
                <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
                <XAxis dataKey="shots" tick={{ fontSize: 11, fill: chartTheme.axis }} />
                <YAxis scale="log" domain={['auto', 'auto']} allowDataOverflow tick={{ fontSize: 10, fill: chartTheme.axis }} tickFormatter={(v) => Number(v).toExponential(0)} />
                <Tooltip contentStyle={chartTheme.tooltip} formatter={(v: unknown) => (typeof v === 'number' ? v.toExponential(2) : 'exact (0) — not drawn on a log axis')} /><Legend wrapperStyle={{ fontSize: 11 }} />
                {['FRQI 8×8', 'NEQR 8×8 4-bit', 'FRQI 16×16', 'NEQR 16×16 8-bit'].map((k, i) => <Line key={k} dataKey={k} stroke={['#22d3ee', '#a78bfa', '#0891b2', '#7c3aed'][i]} strokeWidth={2} dot connectNulls={false} />)}
              </LineChart></ResponsiveContainer></div>
            </Card>
          </div>
          <Collapsible title="FRQI — every resolution" hint="Circuit resources, reconstruction error per shot count, classification accuracy"><EncodingTable rep="FRQI" recs={recs} models={models} /></Collapsible>
          <Collapsible title="NEQR — every resolution and brightness precision" hint="2-, 4- and 8-bit intensity encodings"><EncodingTable rep="NEQR" recs={recs} models={models} /></Collapsible>
        </>
      )}
    </div>
  );
}
