import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Link } from 'react-router-dom';
import { useV2 } from '../api';
import { Badge, Card, ExecBadge, Gate, PageHeader, Stat, int } from '../ui';
import { ExplainThis } from '../learn/ExplainThis';
import { Lv } from '../level';

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

type Role = 'super' | 'encode' | 'entangle' | 'train' | 'select' | 'write' | 'none';
type Kind = 'qkc' | 'vqc' | 'frqi' | 'neqr';
export function circuitKind(d: Pick<Detail, 'params'>): Kind {
  const p = d.params as Record<string, unknown>;
  return p.feature_map ? 'qkc' : p.layers != null ? 'vqc' : p.representation === 'NEQR' ? 'neqr' : 'frqi';
}
/** Role of every recorded instruction, derived from the gate sequence the encoders/feature maps actually emit. */
export function gateRoles(d: Pick<Detail, 'params' | 'instructions' | 'n_qubits'>): Role[] {
  const I = d.instructions, k = circuitKind(d), n = d.n_qubits, out: Role[] = I.map(() => 'none');
  for (let i = 0; i < I.length; i++) {
    const g = I[i], nm = g.name;
    if (nm === 'barrier' || nm === 'measure') continue;
    if (nm === 'h') { out[i] = 'super'; continue; }
    if (k === 'qkc') {
      if (nm === 'cx') out[i] = 'entangle';
      else if (nm === 'p' && I[i - 1]?.name === 'cx' && I[i + 1]?.name === 'cx') out[i] = 'entangle';
      else out[i] = 'encode';
    } else if (k === 'vqc') {
      const block = I.slice(i, i + n);
      if (nm === 'ry' && block.length === n && block.every((b, j) => b.name === 'ry' && b.qubits[0] === j) && (i === 0 || I[i - 1].name === 'cx')) {
        for (let j = 0; j < n; j++) out[i + j] = 'encode';
        i += n - 1;
      } else out[i] = nm === 'cx' ? 'entangle' : 'train';
    } else out[i] = nm === 'x' ? 'select' : 'write';
  }
  return out;
}
const QUESTIONS: Record<Kind, { role: Role | 'measure'; q: string; b: string; t: string }[]> = {
  qkc: [
    { role: 'super', q: 'Where is the superposition?', b: 'Hadamards spread every qubit over 0 and 1.', t: 'H⊗ⁿ|0⟩ — uniform superposition before the phase encoding (ZZ maps only).' },
    { role: 'encode', q: 'Where does the data go in?', b: 'Each feature becomes a rotation on its own qubit.', t: 'Product-RY: RY(xᵢ). ZZ maps: P(2xᵢ) after H.' },
    { role: 'entangle', q: 'Where is the entanglement?', b: 'CX–P–CX blocks couple pairs of qubits. None at all means a product state (classically easy).', t: 'exp(−i(π−xᵢ)(π−xⱼ)ZᵢZⱼ) realised as CX · P(2(π−xᵢ)(π−xⱼ)) · CX.' },
    { role: 'measure', q: 'What is measured?', b: 'Run U(x), then U(y) reversed, and count how often every qubit reads 0.', t: 'K(x,y) = P(0…0) of U(y)†U(x)|0⟩ = |⟨φ(y)|φ(x)⟩|².' },
  ],
  vqc: [
    { role: 'encode', q: 'Where does the data go in?', b: 'The features are written as RY angles (again before each layer if re-uploading).', t: 'RY(aᵢ), a ∈ [0, π] (train-fitted MinMax PCA/CNN features).' },
    { role: 'train', q: 'Which gates were trained?', b: 'These RY/RZ angles were learned; hover a gate to see its value.', t: 'RY(θ_{l,i,0}) RZ(θ_{l,i,1}); θ by parameter-shift gradients + optimiser.' },
    { role: 'entangle', q: 'Where is the entanglement?', b: 'A ring of CNOTs links each qubit to the next.', t: 'CNOT ring i → i+1 mod n after every layer.' },
    { role: 'measure', q: 'What is measured?', b: 'The average Z of a few qubits gives one score per class.', t: '⟨Zᵢ⟩ (and Z⊗Z pairs for n = 4) → w_c⟨O_c⟩ + b_c → softmax.' },
  ],
  frqi: [
    { role: 'super', q: 'Where is the superposition?', b: 'Hadamards put the position qubits into every pixel position at once.', t: 'H⊗²ⁿ|0⟩ = (1/N) Σᵢ |i⟩.' },
    { role: 'select', q: 'Which gates pick a pixel?', b: 'X gates flip position bits so the next rotation fires for exactly one pixel.', t: 'X on the 0-bits of index i (applied before and after).' },
    { role: 'write', q: 'Where is the brightness written?', b: 'Controlled rotations turn the colour qubit by each pixel’s angle (shown split into RY and CCX).', t: 'C^{2n}-RY(2θᵢ) decomposed as RY(θ)·CCX·RY(−θ)·CCX; entangles position and colour.' },
    { role: 'measure', q: 'What is measured?', b: 'Nothing here: two images are compared by the overlap of their exact states.', t: 'K = |⟨I_A|I_B⟩|² from the statevector.' },
  ],
  neqr: [
    { role: 'super', q: 'Where is the superposition?', b: 'Hadamards put the position qubits into every pixel position at once.', t: 'H⊗²ⁿ|0⟩ = (1/N) Σᵢ |i⟩|0…0⟩.' },
    { role: 'select', q: 'Which gates pick a pixel?', b: 'X gates flip position bits so the next gates fire for exactly one pixel.', t: 'X on the 0-bits of index i (applied before and after).' },
    { role: 'write', q: 'Where are the bits written?', b: 'Controlled-NOTs flip each colour qubit whose bit is 1 for that pixel.', t: 'One C^{2n}-X per 1-bit of Cᵢ; entangles position and colour.' },
    { role: 'measure', q: 'What is measured?', b: 'Nothing here: images are compared by the overlap of their exact states.', t: 'K = |⟨I_A|I_B⟩|² from the statevector.' },
  ],
};

function CircuitExplorer({ d }: { d: Detail }) {
  const k = circuitKind(d), roles = useMemo(() => gateRoles(d), [d]);
  const [q, setQ] = useState<number | null>(null);
  const cur = q == null ? null : QUESTIONS[k][q];
  const count = cur && cur.role !== 'measure' ? roles.filter((r) => r === cur.role).length : 0;
  return (
    <div className="space-y-3" data-testid="circuit-explorer">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="mr-1 text-xs font-medium text-slate-300">Explain this circuit:</span>
        {QUESTIONS[k].map((x, i) => (
          <button key={x.q} type="button" aria-pressed={q === i} onClick={() => setQ(q === i ? null : i)} data-testid={`circuit-q-${x.role}`}
            className={`rounded-full px-3 py-1 text-xs ring-1 transition ${q === i ? 'bg-teal-500/15 text-teal-100 ring-teal-400/60' : 'text-slate-300 ring-slate-700 hover:bg-slate-800'}`}>{x.q}</button>))}
      </div>
      {cur && (
        <div className="flex flex-wrap items-center gap-3 rounded-lg bg-teal-500/[0.06] px-3 py-2 text-[13px] ring-1 ring-teal-500/25" data-testid="circuit-answer">
          <span className="text-slate-100"><Lv beginner={cur.b} technical={<span className="font-mono text-[12px] text-teal-100">{cur.t}</span>} /></span>
          {cur.role !== 'measure' && <span className="rounded bg-slate-900 px-2 py-0.5 text-[11px] tabular-nums text-teal-200 ring-1 ring-slate-700">{count} gate{count === 1 ? '' : 's'} highlighted</span>}
          {cur.role === 'entangle' && count === 0 && <span className="text-[11px] text-amber-200">none in this circuit</span>}
        </div>)}
      <CircuitDiagram d={d} roles={roles} hl={cur && cur.role !== 'measure' ? cur.role : null} />
    </div>
  );
}

function CircuitDiagram({ d, maxGates = 160, roles, hl }: { d: Detail; maxGates?: number; roles?: Role[]; hl?: Role | null }) {
  const shown = d.instructions.slice(0, maxGates);
  const placed = useMemo(() => layoutCircuit(shown, d.n_qubits), [shown, d.n_qubits]);
  const cols = Math.max(1, ...placed.map((g) => g.col + 1));
  const W = 46, Hq = 34, left = 54, top = 18;
  const width = left + cols * W + 20, height = top + d.n_qubits * Hq + 6;
  const short = (n: string) => ({ ry: 'RY', rz: 'RZ', h: 'H', p: 'P', x: 'X', cry: 'RY', mcry: 'RY', mcx: 'X', ccx: 'X', cx: 'X', measure: 'M' } as Record<string, string>)[n] ?? n.toUpperCase().slice(0, 3);
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800 bg-[#050913] p-2">
      <svg width={width} height={height} role="img" aria-label={`Circuit diagram of ${d.experiment_id}`}>
        <defs><filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feDropShadow dx="0" dy="0" stdDeviation="2.5" floodColor="#5eead4" floodOpacity="0.9" /></filter></defs>
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
          const on = !hl || roles?.[g.i] === hl;
          return (
            <g key={g.i} opacity={on ? 1 : 0.15} style={{ transition: 'opacity .25s' }} filter={hl && on ? 'url(#glow)' : undefined} data-role={roles?.[g.i]}>
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
            <CircuitExplorer d={d} />
            <div className="grid gap-4 lg:grid-cols-3">
              <Card title="Gate sequence counts" actions={<span className="flex flex-wrap gap-1"><ExplainThis id="gates" /></span>}>
                <div className="space-y-3 text-xs">
                  <div><div className="mb-1 text-slate-500">Logical (displayed circuit)</div><div className="flex flex-wrap gap-1.5">{counts.map(([g, n]) => <Badge key={g}>{g} × {int(n)}</Badge>)}</div></div>
                  <div><div className="mb-1 text-slate-500">Compiled to {(rec.transpilation?.basis_gates ?? []).join(', ')} (opt. level {rec.transpilation?.optimization_level ?? '?'})</div>
                    <div className="flex flex-wrap gap-1.5">{compiled.length ? compiled.map(([g, n]) => <Badge key={g} tone="cyan">{g} × {int(n)}</Badge>) : 'unavailable'}</div></div>
                </div>
              </Card>
              <Card title="Feature map / structure" actions={<span className="flex flex-wrap gap-1"><ExplainThis id="product-ry" /><ExplainThis id="zz-linear" /><ExplainThis id="zz-full" /><ExplainThis id="vqc" /></span>}>
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
