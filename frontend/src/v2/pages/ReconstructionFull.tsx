// Full reconstruction study: all 1,800 NEU-DET images x every encoding (results/qml_v4/reconstruction_full via /api/v4).
import { useEffect, useMemo, useState } from 'react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Play, Pause, Shuffle } from 'lucide-react';
import { useV4 } from '../api';
import { Card, Gate, PageHeader, Badge } from '../ui';
import { ArrayImage, CLASS_NAMES } from '../playground/widgets';
import { LegendRow } from '../charts';
import { ExplainThis } from '../learn/ExplainThis';

const MODE_LABEL = (m: string) => (m === 'statevector' ? 'exact (statevector)' : m === 'reconstruction' ? 'PCA reconstruction' : `${Number(m.replace('shots', '')).toLocaleString()} shots`);
const sci = (v: number | null | undefined) => (v == null ? '—' : v < 1e-15 ? '0 (exact)' : v.toExponential(2));
const f3 = (v: number | null | undefined) => (v == null ? '—' : v.toFixed(3));
const RES_COL: Record<string, string> = { '2': '#9fe3c9', '4': '#4cc79a', '8': '#199e70', '16': '#0f6b4c' };

function ShotsChart({ recs, family }: { recs: Record<string, any>; family: 'FRQI' | 'NEQR' }) {
  const ids = Object.keys(recs).filter((r) => r.startsWith(`R-${family}`) && (family === 'FRQI' || r.endsWith('-b4')));
  const shots = [100, 1000, 10000, 100000];
  const data = shots.map((s) => {
    const row: any = { s };
    ids.forEach((id) => { row[id] = recs[id].summary.all[`shots${s}`].vs_preprocessed.mse.mean; });
    return row;
  });
  const res = (id: string) => id.match(/(\d+)x/)?.[1] ?? '';
  return (
    <div>
      <div className="h-56">
        <ResponsiveContainer>
          <LineChart data={data} margin={{ left: 4, right: 12, top: 8, bottom: 4 }}>
            <CartesianGrid stroke="#1e293b" />
            <XAxis dataKey="s" scale="log" type="number" domain={[100, 100000]} ticks={shots} tickFormatter={(v) => `10${'⁰¹²³⁴⁵'[Math.log10(v)]}`} tick={{ fontSize: 11, fill: '#94a3b8' }} stroke="#1e293b" />
            <YAxis scale="log" domain={['auto', 'auto']} tickFormatter={(v) => v.toExponential(0)} tick={{ fontSize: 11, fill: '#94a3b8' }} stroke="#1e293b" width={52} />
            <Tooltip contentStyle={{ background: '#0b1220', border: '1px solid #334155', fontSize: 12 }} formatter={(v: any, n: any) => [Number(v).toExponential(2), n]} labelFormatter={(v) => `${Number(v).toLocaleString()} shots`} />
            {ids.map((id) => <Line key={id} dataKey={id} name={`${res(id)}×${res(id)}`} stroke={RES_COL[res(id)]} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />)}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <LegendRow items={ids.map((id) => ({ name: `${res(id)}×${res(id)}`, color: RES_COL[res(id)], shape: 'line' as const }))} />
    </div>
  );
}

function Browser({ recs }: { recs: Record<string, any> }) {
  const ids = Object.keys(recs);
  const [rid, setRid] = useState('R-FRQI-16x16');
  const [i, setI] = useState(1440 + 300);
  const [anim, setAnim] = useState(false);
  const [k, setK] = useState(0);
  const st = useV4<any>(`/reconstruction/image?record=${rid}&i=${i}`);
  const modes = st.data ? Object.keys(st.data.modes) : [];
  useEffect(() => {
    if (!anim || !modes.length) return;
    const h = setInterval(() => setK((x) => (x + 1) % modes.length), 1100);
    return () => clearInterval(h);
  }, [anim, modes.length]);
  const n = recs[rid]?.config?.n_images ?? 1800;
  return (
    <Card title="Browse any image × any method" subtitle="Indices 0–1,439 are the train-folder images, 1,440–1,799 the locked-test folder. Arrays are the saved decoder outputs.">
      <div className="flex flex-wrap items-center gap-3 text-xs">
        <select value={rid} onChange={(e) => setRid(e.target.value)} className="rounded-md bg-slate-900 px-2 py-1 text-slate-200 ring-1 ring-slate-700" aria-label="record">
          {ids.map((x) => <option key={x} value={x}>{x}</option>)}
        </select>
        <input type="range" min={0} max={n - 1} value={i} onChange={(e) => setI(+e.target.value)} className="w-64" aria-label="image index" />
        <span className="font-mono text-slate-400">#{i}</span>
        <button onClick={() => setI(Math.floor(Math.random() * n))} className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-slate-300 ring-1 ring-slate-700"><Shuffle size={13} /> random</button>
        <button onClick={() => setAnim(!anim)} className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-cyan-200 ring-1 ring-cyan-500/40" data-testid="recon-animate">{anim ? <Pause size={13} /> : <Play size={13} />} {anim ? 'stop' : 'animate shots'}</button>
      </div>
      <Gate state={st}>{(d) => (
        <div className="mt-4 space-y-3" data-testid="recon-browser">
          <div className="text-xs text-slate-400"><span className="font-mono text-slate-300">{d.row.image}</span> · {CLASS_NAMES[['crazing', 'inclusion', 'patches', 'pitted_surface', 'rolled-in_scale', 'scratches'].indexOf(d.row.class)]} · <Badge tone={d.row.role === 'locked_test' ? 'amber' : 'slate'}>{d.row.role}</Badge>{' '}
            {d.config.kind === 'classical' ? <Badge tone="blue">classical — no circuit</Badge> : <Badge tone="cyan">{d.config.kind === 'quantum_patch' ? 'patch-wise FRQI/NEQR (V4)' : 'whole-image FRQI/NEQR'} · Qiskit simulation</Badge>}</div>
          <div className="flex flex-wrap gap-4">
            <ArrayImage data={d.original} size={150} label="preprocessed original" />
            {modes.map((m, j) => {
              const mm = d.row.modes[m].vs_preprocessed;
              return <div key={m} className={`rounded-lg p-1 ${anim && j === k ? 'ring-2 ring-cyan-400' : ''}`}>
                <ArrayImage data={d.modes[m]} size={150} label={`${MODE_LABEL(m)} · MSE ${sci(mm.mse)} · SSIM ${f3(mm.ssim)}`} />
              </div>;
            })}
          </div>
          {d.config.shots_note && <div className="text-[11px] text-slate-500">Shots: {d.config.shots_note}.</div>}
        </div>)}
      </Gate>
    </Card>
  );
}

export default function ReconstructionFull() {
  const st = useV4<any>('/reconstruction/summary');
  return (
    <div className="space-y-5">
      <PageHeader title="Reconstruction — all 1,800 images, every method"
        subtitle="Each NEU-DET image was encoded with the real FRQI / NEQR circuits, simulated (Qiskit-Aer statevector), measured with 100 – 100,000 shots and decoded back into an image. Classical PCA reconstructions show what the PCA-input quantum classifiers receive." />
      <Gate state={st}>{(s) => <Body s={s} />}</Gate>
    </div>
  );
}

function Body({ s }: { s: any }) {
  const recs = s.records as Record<string, any>;
  const [cls, setCls] = useState('R-FRQI-16x16');
  const rows = useMemo(() => Object.entries(recs).map(([id, r]: [string, any]) => {
    const a = r.summary.all, mode = a.statevector ? 'statevector' : 'reconstruction';
    return { id, kind: r.config.kind, q: r.circuit?.n_qubits, gates: r.circuit?.gates_compiled, sv: a[mode].vs_preprocessed, s1k: a.shots1000?.vs_preprocessed,
      exact: a[mode].n_exact, test: r.summary.by_role.locked_test[mode].vs_preprocessed.mse.mean, train: r.summary.by_role.trainval[mode].vs_preprocessed.mse.mean };
  }), [recs]);
  const pc = recs[cls]?.summary.by_class;
  const pcMode = recs[cls]?.summary.all.statevector ? 'shots1000' : 'reconstruction';
  return (
    <>
      <div className="flex flex-wrap items-center gap-2 rounded-xl bg-emerald-500/5 px-4 py-3 text-xs text-slate-300 ring-1 ring-emerald-500/20" data-testid="recon-banner">
        {s.n_images.toLocaleString()} images × {Object.keys(recs).length} methods · every image, every class, both folders · created {s.created_at}
      </div>
      <div className="grid gap-5 xl:grid-cols-2">
        <Card actions={<span className="flex flex-wrap gap-1"><ExplainThis id="recon-metrics" /><ExplainThis id="shots" /></span>} title="FRQI: error vs shots (all 1,800 images)" subtitle="Mean MSE against the preprocessed image. More pixels need more shots for the same quality."><ShotsChart recs={recs} family="FRQI" /></Card>
        <Card title="NEQR 4-bit: error vs shots (all 1,800 images)" subtitle="NEQR stores intensities as bits, so a pixel is exact once it is observed; the floor is the 4-bit quantisation error."><ShotsChart recs={recs} family="NEQR" /></Card>
      </div>
      <Browser recs={recs} />
      <Card actions={<span className="flex flex-wrap gap-1"><ExplainThis id="recon-metrics" /></span>} title="Every method, summarised" subtitle="Exact = decoded from the statevector (or PCA inverse for the classical rows).">
        <div className="overflow-x-auto"><table className="w-full text-xs tabular-nums" data-testid="recon-table">
          <thead className="text-left text-[11px] text-slate-500"><tr>{['Method', 'type', 'qubits', 'compiled gates', 'exact MSE', 'exact SSIM', 'exactly reproduced', 'MSE @1k shots', 'MSE train-folder / test-folder'].map((h) => <th key={h} className="px-2 py-2 font-medium">{h}</th>)}</tr></thead>
          <tbody>{rows.map((r) => (
            <tr key={r.id} className="border-t border-slate-800/70 text-slate-200">
              <td className="px-2 py-1.5 font-mono">{r.id}</td>
              <td className="px-2 py-1.5">{r.kind === 'classical' ? <Badge tone="blue">classical</Badge> : r.kind === 'quantum_patch' ? <Badge tone="violet">patch (V4)</Badge> : <Badge tone="cyan">whole image</Badge>}</td>
              <td className="px-2 py-1.5">{r.q ?? '—'}</td><td className="px-2 py-1.5">{r.gates ? Math.round(r.gates).toLocaleString() : '—'}</td>
              <td className="px-2 py-1.5">{sci(r.sv.mse.mean)}</td><td className="px-2 py-1.5">{f3(r.sv.ssim.mean)}</td>
              <td className="px-2 py-1.5">{r.exact.toLocaleString()} / 1,800</td><td className="px-2 py-1.5">{sci(r.s1k?.mse.mean)}</td>
              <td className="px-2 py-1.5">{sci(r.train)} / {sci(r.test)}</td>
            </tr>))}</tbody>
        </table></div>
        <div className="mt-2 text-[11px] text-slate-500">Patch (V4) rows: shots are per patch (64 patches × shots per image for FRQI 8×8, 256 for NEQR 4×4).</div>
      </Card>
      <Card title="Per class" subtitle={`Mean MSE and SSIM per defect class (${MODE_LABEL(pcMode)}).`} actions={
        <select value={cls} onChange={(e) => setCls(e.target.value)} className="rounded-md bg-slate-900 px-2 py-1 text-xs text-slate-200 ring-1 ring-slate-700" aria-label="record for per-class table">
          {Object.keys(recs).map((x) => <option key={x}>{x}</option>)}</select>}>
        {pc && <div className="overflow-x-auto"><table className="w-full text-xs tabular-nums"><thead className="text-left text-[11px] text-slate-500"><tr><th className="px-2 py-2">class</th><th className="px-2">MSE</th><th className="px-2">SSIM</th><th className="px-2">images</th></tr></thead>
          <tbody>{Object.entries(pc).map(([c, v]: [string, any]) => <tr key={c} className="border-t border-slate-800/70 text-slate-200"><td className="px-2 py-1.5">{c}</td><td className="px-2">{sci(v[pcMode].vs_preprocessed.mse.mean)}</td><td className="px-2">{f3(v[pcMode].vs_preprocessed.ssim.mean)}</td><td className="px-2">{v[pcMode].vs_preprocessed.mse.n}</td></tr>)}</tbody></table></div>}
      </Card>
    </>
  );
}
