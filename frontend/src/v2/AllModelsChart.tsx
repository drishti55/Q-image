// Every selected model of V2, V3 and V4 (163) as one interactive dot chart: x = locked-test accuracy, one row per protocol,
// colour = model type. Data: /api/v4/all-models (copied from saved predictions).
import { useMemo, useState } from 'react';
import { useV4 } from './api';
import { Gate } from './ui';

type M = { id: string; protocol: string; name: string; kind: string; n_qubits: number | null; test_accuracy: number };
type Kind = 'quantum' | 'hybrid' | 'classical' | 'control';
const KIND_OF = (k: string): Kind => (k === 'quantum' || k === 'hybrid' || k === 'classical' ? k : k === 'control' ? 'control' : 'classical');
// Validated dark-surface categorical slots 1-3 (all-pairs pass); controls are hollow quantum-blue rings.
const COLOR: Record<Kind, string> = { quantum: '#3987e5', hybrid: '#d95926', classical: '#199e70', control: '#3987e5' };
const LABEL: Record<Kind, string> = { quantum: 'Quantum', hybrid: 'Hybrid (CNN + quantum)', classical: 'Classical', control: 'Quantum controls / ablations' };
const ROWS = ['V4', 'V3', 'V2'];
const W = 900, L = 56, R = 16, DOT = 5;
const X = (a: number) => L + a * (W - L - R);

function swarm(ms: M[]) {
  // deterministic beeswarm: place in accuracy order, nudge up/down until no overlap
  const placed: { m: M; x: number; y: number }[] = [];
  for (const m of [...ms].sort((a, b) => a.test_accuracy - b.test_accuracy)) {
    const x = X(m.test_accuracy);
    for (let k = 0; ; k++) {
      const y = (k % 2 ? 1 : -1) * Math.ceil(k / 2) * (DOT * 2 + 1);
      if (!placed.some((p) => (p.x - x) ** 2 + (p.y - y) ** 2 < (DOT * 2 + 0.5) ** 2)) { placed.push({ m, x, y }); break; }
    }
  }
  return placed;
}

export default function AllModelsChart() {
  const st = useV4<{ models: M[]; n_test: number }>('/all-models');
  const [off, setOff] = useState<Kind[]>([]);
  const [hover, setHover] = useState<M | null>(null);
  return (
    <Gate state={st}>{(d) => <Chart d={d.models} off={off} setOff={setOff} hover={hover} setHover={setHover} />}</Gate>
  );
}

function Chart({ d, off, setOff, hover, setHover }: { d: M[]; off: Kind[]; setOff: (k: Kind[]) => void; hover: M | null; setHover: (m: M | null) => void }) {
  const rows = useMemo(() => ROWS.map((p) => {
    const pts = swarm(d.filter((m) => m.protocol === p));
    const h = Math.max(...pts.map((q) => Math.abs(q.y)), 0) * 2 + DOT * 2 + 18;
    return { p, pts, h };
  }), [d]);
  const bands = rows.map((r, i) => ({ ...r, top: 8 + rows.slice(0, i).reduce((a, x) => a + x.h, 0) }));
  const H = 8 + rows.reduce((a, x) => a + x.h, 0) + 28;
  const best = (k: Kind) => d.filter((m) => KIND_OF(m.kind) === k).reduce<M | null>((a, m) => (!a || m.test_accuracy > a.test_accuracy ? m : a), null);
  const tops = (['quantum', 'hybrid', 'classical'] as Kind[]).map((k) => best(k)).filter(Boolean) as M[];
  const counts = (k: Kind) => d.filter((m) => KIND_OF(m.kind) === k).length;
  return (
    <div data-testid="all-models-chart">
      <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
        {(Object.keys(LABEL) as Kind[]).map((k) => {
          const on = !off.includes(k);
          return (
            <button key={k} type="button" aria-pressed={on} onClick={() => setOff(on ? [...off, k] : off.filter((x) => x !== k))}
              className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 ring-1 transition ${on ? 'text-slate-100 ring-slate-600' : 'text-slate-500 ring-slate-800 opacity-60'}`}>
              <span className="inline-block h-2.5 w-2.5 rounded-full" style={k === 'control' ? { border: `2px solid ${COLOR[k]}` } : { background: COLOR[k] }} />
              {LABEL[k]} <span className="text-slate-500">{counts(k)}</span>
            </button>);
        })}
        <span className="ml-auto text-slate-500">{d.length} models · hover a dot</span>
      </div>
      <div className="mb-3 grid gap-2 sm:grid-cols-3">
        {tops.map((m) => {
          const k = KIND_OF(m.kind);
          return (
            <button key={m.id} type="button" onMouseEnter={() => setHover(m)} onFocus={() => setHover(m)}
              className={`rounded-lg px-3 py-2 text-left ring-1 transition ${hover?.id === m.id ? 'bg-slate-800/80 ring-slate-500' : 'bg-slate-950/50 ring-slate-800'}`}>
              <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-slate-500"><span className="inline-block h-2 w-2 rounded-full" style={{ background: COLOR[k] }} />best {k}</div>
              <div className="text-xl font-semibold tabular-nums text-white">{(100 * m.test_accuracy).toFixed(1)}%</div>
              <div className="truncate text-[11px] text-slate-400" title={m.name}>{m.protocol} · {m.name}</div>
            </button>);
        })}
      </div>
      <div className="relative">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Test accuracy of every model, by protocol and type" onMouseLeave={() => setHover(null)}>
          {[0, 0.2, 0.4, 0.6, 0.8, 1].map((a) => (
            <g key={a}>
              <line x1={X(a)} x2={X(a)} y1={4} y2={H - 22} stroke="#1e293b" />
              <text x={X(a)} y={H - 8} textAnchor="middle" fontSize={11} fill="#64748b">{a * 100}%</text>
            </g>))}
          <line x1={X(1 / 6)} x2={X(1 / 6)} y1={4} y2={H - 22} stroke="#475569" strokeDasharray="3 3" />
          <text x={X(1 / 6) + 4} y={14} fontSize={10} fill="#64748b">chance 16.7%</text>
          {bands.map((b) => (
            <g key={b.p}>
              <text x={8} y={b.top + b.h / 2 + 4} fontSize={13} fontWeight={600} fill={b.p === 'V4' ? '#5eead4' : '#cbd5e1'}>{b.p}</text>
              <line x1={L} x2={W - R} y1={b.top + b.h} y2={b.top + b.h} stroke="#0f172a" />
              {b.pts.map(({ m, x, y }) => {
                const k = KIND_OF(m.kind), dim = off.includes(k), h = hover?.id === m.id;
                return (
                  <circle key={m.id} cx={x} cy={b.top + b.h / 2 + y} r={h ? DOT + 2 : DOT}
                    fill={k === 'control' ? '#0f172a' : COLOR[k]} stroke={h ? '#f8fafc' : k === 'control' ? COLOR[k] : '#0f172a'} strokeWidth={h ? 2 : k === 'control' ? 1.5 : 1}
                    opacity={dim ? 0.08 : 1} onMouseEnter={() => !dim && setHover(m)} style={{ cursor: 'pointer', transition: 'opacity .2s' }} data-testid="model-dot" />);
              })}
            </g>))}
        </svg>
        <div className="mt-2 min-h-[44px] rounded-lg bg-slate-950/60 px-3 py-2 text-xs ring-1 ring-slate-800" aria-live="polite">
          {hover ? (<>
            <div className="font-medium text-slate-100">{hover.name}</div>
            <div className="text-slate-400">{hover.protocol} · {LABEL[KIND_OF(hover.kind)]}{hover.n_qubits ? ` · ${hover.n_qubits} qubits` : ''} · <span className="font-semibold tabular-nums text-white">{(100 * hover.test_accuracy).toFixed(1)}%</span> test accuracy</div>
          </>) : <div className="text-slate-500">Each dot is one model. Right = more accurate. Hover to see which one.</div>}
        </div>
      </div>
    </div>
  );
}
