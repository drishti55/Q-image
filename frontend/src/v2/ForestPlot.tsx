// Forest plot for paired comparisons: one row per comparison, dot = difference (pp), bar = 95 % CI, zero line,
// teal = significant after Holm correction, grey = not significant. Hover a row for the numbers.
import { useState } from 'react';
import type { ReactNode } from 'react';

export type ForestRow = { name: string; diff: number; ci95: [number, number]; p_holm: number; acc_a?: number; acc_b?: number };
const SIG = '#5eead4', NS = '#64748b';

export function ForestPlot({ rows, testid }: { rows: ForestRow[]; testid?: string }) {
  const [h, setH] = useState<number | null>(null);
  const lo = Math.min(0, ...rows.map((r) => r.ci95[0])), hi = Math.max(0, ...rows.map((r) => r.ci95[1]));
  const pad = (hi - lo) * 0.06 || 0.02, a = lo - pad, b = hi + pad;
  const W = 760, L = 300, R = 24, row = 30, H = rows.length * row + 30;
  const X = (v: number) => L + ((v - a) / (b - a)) * (W - L - R);
  const step = (b - a) > 0.4 ? 0.1 : 0.05, ticks: number[] = [];
  for (let t = Math.ceil(a / step) * step; t <= b + 1e-9; t += step) ticks.push(+t.toFixed(3));
  const cur = h == null ? null : rows[h];
  return (
    <div data-testid={testid}>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="paired comparisons with 95% confidence intervals" onMouseLeave={() => setH(null)}>
        {ticks.map((t) => (
          <g key={t}><line x1={X(t)} x2={X(t)} y1={4} y2={H - 22} stroke={t === 0 ? '#94a3b8' : '#1e293b'} strokeDasharray={t === 0 ? '0' : '2 3'} />
            <text x={X(t)} y={H - 8} textAnchor="middle" fontSize={10} fill="#64748b">{t > 0 ? '+' : ''}{Math.round(t * 100)} pp</text></g>))}
        {rows.map((r, i) => {
          const y = i * row + 16, sig = r.p_holm < 0.05, c = sig ? SIG : NS, on = h === i;
          return (
            <g key={r.name} onMouseEnter={() => setH(i)} style={{ cursor: 'default' }}>
              <rect x={0} y={y - row / 2} width={W} height={row} fill={on ? '#0f172a' : 'transparent'} />
              <text x={L - 12} y={y + 4} textAnchor="end" fontSize={11} fill={on ? '#f8fafc' : '#cbd5e1'}>{r.name.length > 46 ? `${r.name.slice(0, 45)}…` : r.name}</text>
              <line x1={X(r.ci95[0])} x2={X(r.ci95[1])} y1={y} y2={y} stroke={c} strokeWidth={on ? 3 : 2} strokeLinecap="round" />
              <circle cx={X(r.diff)} cy={y} r={on ? 6.5 : 5} fill={sig ? c : '#0f172a'} stroke={c} strokeWidth={2} />
            </g>);
        })}
      </svg>
      <div className="mt-1 flex min-h-[36px] flex-wrap items-center gap-x-4 gap-y-1 rounded-lg bg-slate-950/60 px-3 py-2 text-xs ring-1 ring-slate-800">
        {cur ? (<>
          <span className="font-medium text-slate-100">{cur.name}</span>
          {cur.acc_a != null && cur.acc_b != null && <span className="tabular-nums text-slate-400">{(100 * cur.acc_a).toFixed(1)}% vs {(100 * cur.acc_b).toFixed(1)}%</span>}
          <span className="tabular-nums text-white">{cur.diff >= 0 ? '+' : '−'}{Math.abs(100 * cur.diff).toFixed(1)} pp [{(100 * cur.ci95[0]).toFixed(1)}, {(100 * cur.ci95[1]).toFixed(1)}]</span>
          <span className={cur.p_holm < 0.05 ? 'text-teal-300' : 'text-slate-400'}>{cur.p_holm < 0.001 ? 'p < 0.001' : `p = ${cur.p_holm.toFixed(3)}`} · {cur.p_holm < 0.05 ? 'significant' : 'not significant'}</span>
        </>) : (
          <span className="flex items-center gap-4 text-slate-500"><span><span className="mr-1 inline-block h-2.5 w-2.5 rounded-full" style={{ background: SIG }} />significant (Holm)</span>
            <span><span className="mr-1 inline-block h-2.5 w-2.5 rounded-full ring-2 ring-slate-500" />not significant</span><span>bar = 95 % CI · right of 0 = A better · hover a row</span></span>)}
      </div>
    </div>
  );
}

/** Keeps a full table in the page but folded away under a small toggle. */
export function TableDetails({ label = 'Show full table', children }: { label?: string; children: ReactNode }) {
  return (
    <details className="group mt-3 rounded-lg ring-1 ring-slate-800">
      <summary className="cursor-pointer select-none px-3 py-2 text-xs text-slate-400 hover:text-slate-200">{label}</summary>
      <div className="border-t border-slate-800 p-2">{children}</div>
    </details>
  );
}
