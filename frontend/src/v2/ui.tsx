// Shared V2 UI primitives. Missing values always render as "unavailable"; nothing is substituted.
import type { ReactNode } from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';
import type { MS } from './api';

export const UNAVAILABLE = 'unavailable';
export const CLASSES = ['crazing', 'inclusion', 'patches', 'pitted_surface', 'rolled-in_scale', 'scratches'];
export const CLASS_LABEL: Record<string, string> = {
  crazing: 'Crazing', inclusion: 'Inclusion', patches: 'Patches', pitted_surface: 'Pitted surface',
  'rolled-in_scale': 'Rolled-in scale', scratches: 'Scratches',
};

export const pct = (v: number | null | undefined, d = 1) =>
  v === null || v === undefined || Number.isNaN(v) ? UNAVAILABLE : `${(v * 100).toFixed(d)}%`;
export const num = (v: number | null | undefined, d = 3) =>
  v === null || v === undefined || Number.isNaN(v) ? UNAVAILABLE : v.toFixed(d);
export const msPct = (m?: MS | null) =>
  !m || m.mean === null || m.mean === undefined ? UNAVAILABLE
    : m.std === null || m.std === undefined ? pct(m.mean) : `${(m.mean * 100).toFixed(1)} ± ${(m.std * 100).toFixed(1)}%`;
export const msNum = (m?: MS | null, d = 3) =>
  !m || m.mean === null || m.mean === undefined ? UNAVAILABLE
    : m.std === null || m.std === undefined ? m.mean.toFixed(d) : `${m.mean.toFixed(d)} ± ${m.std.toFixed(d)}`;
export const int = (v: number | null | undefined) =>
  v === null || v === undefined || Number.isNaN(v) ? UNAVAILABLE : Math.round(v).toLocaleString('en-US');

export function PageHeader({ title, subtitle, children }: { title: string; subtitle?: ReactNode; children?: ReactNode }) {
  return (
    <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between mb-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-50 tracking-tight">{title}</h1>
        {subtitle && <p className="text-sm text-slate-400 mt-1 max-w-4xl leading-relaxed">{subtitle}</p>}
      </div>
      {children && <div className="flex flex-wrap gap-2">{children}</div>}
    </div>
  );
}

export function Card({ title, subtitle, actions, children, className = '' }: {
  title?: ReactNode; subtitle?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string;
}) {
  return (
    <section className={`rounded-2xl border border-slate-800/80 bg-[#0f172a]/70 p-5 ${className}`}>
      {(title || actions) && (
        <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
          <div>
            {title && <h2 className="text-[15px] font-semibold text-slate-100">{title}</h2>}
            {subtitle && <p className="text-xs text-slate-400 mt-1 leading-relaxed max-w-3xl">{subtitle}</p>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/50 px-4 py-3">
      <div className="text-[11px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className="text-xl font-semibold text-slate-50 mt-1 tabular-nums">{value}</div>
      {hint && <div className="text-[11px] text-slate-500 mt-0.5">{hint}</div>}
    </div>
  );
}

export function Loading({ text = 'Loading Protocol V2 data…' }: { text?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 p-6 text-sm text-slate-400">
      <Loader2 size={16} className="animate-spin" /> {text}
    </div>
  );
}

export function ErrorState({ error }: { error: string }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-200">
      <AlertTriangle size={18} className="mt-0.5 shrink-0" />
      <div>
        <div className="font-semibold">Could not load Protocol V2 data</div>
        <div className="text-rose-300/90 mt-0.5">{error}</div>
        {error.startsWith('404') && (
          <div className="text-rose-300/80 mt-1 text-xs">
            The backend does not expose this V2 endpoint — it is probably an older process. Restart it with
            <code className="mx-1 px-1 rounded bg-rose-950/60">python api_main.py</code>.
          </div>
        )}
      </div>
    </div>
  );
}

export function Empty({ text = 'No experiment results available.' }: { text?: string }) {
  return <div className="rounded-xl border border-dashed border-slate-700 p-6 text-center text-sm text-slate-400">{text}</div>;
}

export function Gate<T>({ state, children, empty }: {
  state: { data: T | null; error: string | null; loading: boolean };
  children: (d: T) => ReactNode;
  empty?: (d: T) => boolean;
}) {
  if (state.loading) return <Loading />;
  if (state.error) return <ErrorState error={state.error} />;
  if (!state.data || (empty && empty(state.data))) return <Empty />;
  return <>{children(state.data)}</>;
}

const toneCls: Record<string, string> = {
  cyan: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
  blue: 'bg-blue-500/10 text-blue-300 border-blue-500/30',
  violet: 'bg-violet-500/10 text-violet-300 border-violet-500/30',
  amber: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
  emerald: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
  slate: 'bg-slate-800/80 text-slate-300 border-slate-700',
  rose: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
};

export function Badge({ children, tone = 'slate', title }: { children: ReactNode; tone?: keyof typeof toneCls; title?: string }) {
  return <span title={title} className={`inline-flex items-center rounded-md border px-1.5 py-0.5 text-[11px] font-medium whitespace-nowrap ${toneCls[tone]}`}>{children}</span>;
}

export const CATEGORY_TONE: Record<string, keyof typeof toneCls> = {
  'Classical models': 'slate',
  'Quantum kernel models': 'cyan',
  'FRQI / NEQR encoding kernels': 'violet',
  'Variational quantum classifiers': 'blue',
  'Hybrid CNN + quantum models': 'emerald',
};

export function ExecBadge({ execution }: { execution: string }) {
  if (execution === 'classical') return <Badge>classical</Badge>;
  if (execution.startsWith('finite')) return <Badge tone="amber" title="Kernel entries estimated from finite measurement shots (simulated)">{execution.replace(', simulated', '')}</Badge>;
  return <Badge tone="cyan" title="Exact statevector simulation (no shot noise)">exact statevector</Badge>;
}

export function Select({ label, value, onChange, options, all = true }: {
  label: string; value: string; onChange: (v: string) => void; options: (string | [string, string])[]; all?: boolean;
}) {
  return (
    <label className="flex flex-col gap-1 text-[11px] text-slate-400">
      {label}
      <select aria-label={label} value={value} onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none">
        {all && <option value="all">All</option>}
        {options.map((o) => {
          const [v, l] = Array.isArray(o) ? o : [o, o];
          return <option key={v} value={v}>{l}</option>;
        })}
      </select>
    </label>
  );
}

export function ConfusionMatrix({ cm, title }: { cm: number[][] | null | undefined; title: string }) {
  if (!cm || !cm.length) return <Empty text={`${title}: not available.`} />;
  const mx = Math.max(1, ...cm.flat());
  return (
    <div className="overflow-x-auto">
      <div className="text-xs text-slate-400 mb-2">{title} <span className="text-slate-500">· rows = true class, columns = predicted</span></div>
      <table className="text-[11px] tabular-nums">
        <thead>
          <tr><th />{CLASSES.map((c) => <th key={c} className="px-1 pb-1 font-medium text-slate-400 w-14">{CLASS_LABEL[c].split(' ')[0]}</th>)}</tr>
        </thead>
        <tbody>
          {cm.map((row, i) => (
            <tr key={i}>
              <th className="pr-2 text-right font-medium text-slate-400 whitespace-nowrap">{CLASS_LABEL[CLASSES[i]]}</th>
              {row.map((v, j) => (
                <td key={j} className="h-9 w-14 text-center border border-slate-900 text-slate-100"
                  style={{ background: i === j ? `rgba(34,211,238,${0.12 + 0.6 * v / mx})` : v ? `rgba(244,63,94,${0.1 + 0.6 * v / mx})` : 'rgba(15,23,42,0.6)' }}>
                  {v}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export const chartTheme = {
  grid: '#1e293b', axis: '#94a3b8',
  tooltip: { background: '#0b1220', border: '1px solid #334155', borderRadius: 8, fontSize: 12 },
};

// Recharts tooltip formatter: non-numeric / missing values render as "unavailable".
export const fmt = (f: (v: number) => string) => (v: unknown) => (typeof v === 'number' && !Number.isNaN(v) ? f(v) : UNAVAILABLE);

// Duration (seconds, mean ± std over seeds) with a readable unit; sub-second values shown in ms.
export const msDur = (m?: MS | null) => {
  if (!m || m.mean === null || m.mean === undefined) return UNAVAILABLE;
  const ms = m.mean < 1;
  const f = (x: number) => (ms ? (x * 1000).toFixed(1) : x.toFixed(2));
  return `${f(m.mean)}${m.std !== null && m.std !== undefined ? ` ± ${f(m.std)}` : ''} ${ms ? 'ms' : 's'}`;
};
