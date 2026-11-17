import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Link } from 'react-router-dom';
import { useV2 } from '../api';
import { Badge, Card, ExecBadge, Gate, PageHeader, Stat, int } from '../ui';

type CircuitRow = { circuit_key: string; experiment_id: string; n_qubits: number; encoding: string;
  resources: { gates_logical: number; gates_compiled: number; depth_compiled: number; cx_compiled: number } | null;
  used_by: { group: string; display_name: string; execution: string }[] };
type Instr = { i: number; name: string; qubits: number[]; params: number[] };
type Detail = {
  experiment_id: string; group: string; kind: string; params: Record<string, unknown>; n_qubits: number; input: string;
  registers: { name: string; size: number }[];
  logical_counts_displayed_circuit: Record<string, number>; logical_gates_displayed_circuit: number; logical_depth_displayed_circuit: number;
  recorded_resources: Record<string, any> | null; entanglement: (number[] | string[])[]; measurement: string;
  instructions: Instr[]; instructions_truncated: boolean; text_diagram: string | null; used_by?: CircuitRow['used_by'];
};

const FAMILY: Record<string, string> = { qkc: 'Quantum kernel feature maps', vqc: 'Variational classifiers', frqi: 'FRQI encodings', neqr: 'NEQR encodings' };

export function layoutCircuit(instr: Instr[], nq: number) {
  const free = new Array(nq).fill(0);
  return instr.map((g) => {
    const lo = Math.min(...g.qubits), hi = Math.max(...g.qubits);
    const span = g.qubits.length > 1 ? Array.from({ length: hi - lo + 1 }, (_, k) => lo + k) : g.qubits;
    const col = Math.max(...span.map((q) => free[q]));
    span.forEach((q) => { free[q] = col + 1; });
    return { ...g, col };
  });
}

function CircuitDiagram({ d, maxGates = 160 }: { d: Detail; maxGates?: number }) {
  const shown = d.instructions.slice(0, maxGates);
  const placed = useMemo(() => layoutCircuit(shown, d.n_qubits), [shown, d.n_qubits]);
  const cols = Math.max(1, ...placed.map((g) => g.col + 1));
  const W = 46, Hq = 34, left = 54, top = 18;
  const width = left + cols * W + 20, height = top + d.n_qubits * Hq + 6;
  const short = (n: string) => ({ ry: 'RY', rz: 'RZ', h: 'H', p: 'P', x: 'X', cry: 'RY', mcry: 'RY', mcx: 'X', ccx: 'X', cx: 'X', measure: 'M' } as Record<string, string>)[n] ?? n.toUpperCase().slice(0, 3);
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800 bg-[#050913] p-2">
      <svg width={width} height={height} role="img" aria-label={`Circuit diagram of ${d.experiment_id}`}>
        {Array.from({ length: d.n_qubits }, (_, q) => (
          <g key={q}>
            <text x={8} y={top + q * Hq + 4} fontSize={11} fill="#94a3b8" fontFamily="ui-monospace">q{q}</text>
            <line x1={left - 10} x2={width - 10} y1={top + q * Hq} y2={top + q * Hq} stroke="#334155" />
          </g>
        ))}
        {placed.map((g) => {
          const x = left + g.col * W + W / 2;
          const ys = g.qubits.map((q) => top + q * Hq);
          const multi = g.qubits.length > 1;
          const target = g.qubits[g.qubits.length - 1];
          const label = short(g.name);
          const tip = `${g.name}(${g.params.join(', ')}) on q${g.qubits.join(',q')}`;
          return (
            <g key={g.i}>
              <title>{tip}</title>
              {multi && <line x1={x} x2={x} y1={Math.min(...ys)} y2={Math.max(...ys)} stroke="#22d3ee" strokeWidth={1.5} />}
              {multi && g.qubits.slice(0, -1).map((q) => <circle key={q} cx={x} cy={top + q * Hq} r={4} fill="#22d3ee" />)}
              {multi && label === 'X' ? (
                <g><circle cx={x} cy={top + target * Hq} r={9} fill="#050913" stroke="#22d3ee" strokeWidth={1.5} />
                  <line x1={x - 9} x2={x + 9} y1={top + target * Hq} y2={top + target * Hq} stroke="#22d3ee" strokeWidth={1.5} />
                  <line x1={x} x2={x} y1={top + target * Hq - 9} y2={top + target * Hq + 9} stroke="#22d3ee" strokeWidth={1.5} /></g>
              ) : (
                <g>
                  <rect x={x - 17} y={top + target * Hq - 11} width={34} height={22} rx={4}
                    fill={label === 'H' ? '#1e3a8a' : label === 'P' ? '#4c1d95' : label === 'RZ' ? '#164e63' : label === 'X' ? '#7f1d1d' : '#0e7490'} stroke="#475569" />
                  <text x={x} y={top + target * Hq + 4} fontSize={10} fill="#e2e8f0" textAnchor="middle" fontFamily="ui-monospace">{label}</text>
                </g>
              )}
            </g>
          );
        })}
      </svg>
      {d.instructions.length > shown.length || d.instructions_truncated ? (
        <div className="px-2 pt-2 text-[11px] text-amber-300/90">
          Showing the first {shown.length} of {int(d.logical_gates_displayed_circuit)} gates of this circuit (all counts below refer to the full circuit).
        </div>
      ) : null}
    </div>
  );
}

function DetailView({ id }: { id: string }) {
  const st = useV2<Detail>(`/circuits/${encodeURIComponent(id)}`);
  return (
    <Gate state={st}>
      {(d) => {
        const rec = d.recorded_resources ?? {};
        const counts = Object.entries(d.logical_counts_displayed_circuit).sort((a, b) => b[1] - a[1]);
        const compiled = Object.entries((rec.gate_counts_compiled ?? {}) as Record<string, number>).sort((a, b) => b[1] - a[1]);
        return (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-semibold text-slate-50">{d.kind}</h2>
              <Badge tone="cyan">{d.n_qubits} qubits</Badge>
              {d.registers.map((r) => <Badge key={r.name}>{r.name}[{r.size}]</Badge>)}
            </div>
            <p className="text-xs text-slate-400 break-words">Rebuilt from the saved checkpoint of <Link className="text-cyan-300 hover:underline" to={`/experiments/${encodeURIComponent(d.experiment_id)}`}>{d.experiment_id}</Link>. Input: {d.input}.</p>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <Stat label="Logical gates (this circuit)" value={int(d.logical_gates_displayed_circuit)} hint={`depth ${int(d.logical_depth_displayed_circuit)}`} />
              <Stat label="Compiled gates (recorded)" value={int(rec.gates_compiled)} hint={rec.n_sample_images ? `mean of ${rec.n_sample_images} images` : 'basis cx, rz, sx, x'} />
              <Stat label="Compiled depth" value={int(rec.depth_compiled)} />
              <Stat label="Two-qubit / CX (compiled)" value={`${int(rec.two_qubit_gates_compiled)} / ${int(rec.cx_compiled)}`} />
            </div>
            <CircuitDiagram d={d} />
            <div className="grid gap-4 lg:grid-cols-3">
              <Card title="Gate sequence counts">
                <div className="space-y-3 text-xs">
                  <div><div className="mb-1 text-slate-500">Logical (displayed circuit)</div><div className="flex flex-wrap gap-1.5">{counts.map(([g, n]) => <Badge key={g}>{g} × {int(n)}</Badge>)}</div></div>
                  <div><div className="mb-1 text-slate-500">Compiled to {(rec.transpilation?.basis_gates ?? []).join(', ')} (opt. level {rec.transpilation?.optimization_level ?? '?'})</div>
                    <div className="flex flex-wrap gap-1.5">{compiled.length ? compiled.map(([g, n]) => <Badge key={g} tone="cyan">{g} × {int(n)}</Badge>) : 'unavailable'}</div></div>
                </div>
              </Card>
              <Card title="Feature map / structure">
                <dl className="space-y-1.5 text-xs">
                  {Object.entries(d.params).map(([k, v]) => <div key={k} className="flex justify-between gap-2"><dt className="text-slate-500">{k}</dt><dd className="text-slate-200">{String(v)}</dd></div>)}
                  <div className="pt-2 text-slate-500">Entanglement</div>
                  <dd className="text-slate-300">{d.entanglement.length ? d.entanglement.slice(0, 40).map((e) => Array.isArray(e) && typeof e[0] === 'number' ? `(${e.join('→')})` : e.join(' · ')).join(' ') : 'none (product state)'}</dd>
                </dl>
              </Card>
              <Card title="Measurement configuration"><p className="text-xs leading-relaxed text-slate-300">{d.measurement}</p></Card>
            </div>
            {d.text_diagram && (
              <details className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                <summary className="cursor-pointer text-xs text-slate-300">Qiskit text drawing of this exact circuit</summary>
                <pre className="mt-2 overflow-x-auto text-[10px] leading-tight text-slate-300">{d.text_diagram}</pre>
              </details>
            )}
            {d.used_by && <div className="text-xs text-slate-400">Used by: {d.used_by.map((u) => <span key={u.group} className="mr-3 inline-flex items-center gap-1"><Link className="text-cyan-300 hover:underline" to={`/models?focus=${u.group}`}>{u.display_name}</Link> <ExecBadge execution={u.execution} /></span>)}</div>}
          </div>
        );
      }}
    </Gate>
  );
}

export default function CircuitsPage() {
  const list = useV2<{ count: number; circuits: CircuitRow[] }>('/circuits');
  const [params, setParams] = useSearchParams();
  const [fam, setFam] = useState('all');
  const sel = params.get('id');
  return (
    <div className="space-y-5">
      <PageHeader title="Quantum Circuits"
        subtitle="Every circuit configuration executed by a selected Protocol V2 quantum model, rebuilt from the saved checkpoint (first training image of the split; trained parameters for VQCs). Gate counts are measured, never estimated." />
      <Gate state={list} empty={(d) => !d.count}>
        {(d) => {
          const rows = d.circuits.filter((c) => fam === 'all' || c.circuit_key.startsWith(fam));
          const current = sel ?? rows[0]?.experiment_id;
          return (
            <div className="grid gap-5 xl:grid-cols-[340px_1fr]">
              <Card title={`${d.count} circuit configurations`}>
                <div className="mb-3 flex flex-wrap gap-1.5">
                  {['all', 'qkc', 'vqc', 'frqi', 'neqr'].map((f) => (
                    <button key={f} onClick={() => setFam(f)} className={`rounded-md border px-2 py-1 text-xs ${fam === f ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-200' : 'border-slate-700 text-slate-400'}`}>{f === 'all' ? 'All' : FAMILY[f]}</button>
                  ))}
                </div>
                <ul className="max-h-[70vh] space-y-1 overflow-y-auto pr-1">
                  {rows.map((c) => (
                    <li key={c.circuit_key}>
                      <button onClick={() => setParams({ id: c.experiment_id })}
                        className={`w-full rounded-lg px-3 py-2 text-left text-xs ${current === c.experiment_id ? 'bg-cyan-500/10 ring-1 ring-cyan-500/40' : 'hover:bg-slate-800/60'}`}>
                        <div className="font-medium text-slate-100">{c.used_by[0]?.display_name.replace(/,? ?\d+ shots/, '')}</div>
                        <div className="mt-0.5 text-slate-500">{c.n_qubits} qubits · {int(c.resources?.gates_compiled)} compiled gates · depth {int(c.resources?.depth_compiled)} · {c.used_by.length} model(s)</div>
                      </button>
                    </li>
                  ))}
                </ul>
              </Card>
              <div className="min-w-0">{current ? <DetailView key={current} id={current} /> : null}</div>
            </div>
          );
        }}
      </Gate>
    </div>
  );
}
