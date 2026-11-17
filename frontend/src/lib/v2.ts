// Pure helpers for the Experiments V2 page. Missing values are always shown as "unavailable" —
// never replaced by a number.

export type MeanStd = { mean: number | null; std: number | null; n: number };

export type ExpRow = {
  experiment_id: string;
  status: string;
  error?: string | null;
  experiment_code?: string;
  group?: string;
  model_name?: string;
  family?: string;
  compute_type?: string;
  feature_extraction?: string;
  encoding?: string | null;
  n_qubits?: number | null;
  n_layers?: number | null;
  optimizer?: string | null;
  shots?: number | null;
  seed?: number;
  params?: Record<string, unknown>;
  val?: Record<string, number> | null;
  test?: Record<string, number> | null;
  selected?: boolean;
  train_time_s?: number | null;
  inference_ms_per_image?: number | null;
  has_training_log?: boolean;
  has_circuit?: boolean;
};

export const UNAVAILABLE = 'unavailable';

export function fmtNum(v: number | null | undefined, digits = 3): string {
  return v === null || v === undefined || Number.isNaN(v) ? UNAVAILABLE : v.toFixed(digits);
}

export function fmtPct(v: number | null | undefined, digits = 1): string {
  return v === null || v === undefined || Number.isNaN(v) ? UNAVAILABLE : `${(v * 100).toFixed(digits)}%`;
}

export function fmtMeanStd(m: MeanStd | null | undefined, pct = true): string {
  if (!m || m.mean === null || m.mean === undefined) return UNAVAILABLE;
  const f = (x: number) => (pct ? `${(x * 100).toFixed(1)}` : x.toFixed(3));
  return m.std === null || m.std === undefined ? f(m.mean) : `${f(m.mean)} ± ${f(m.std)}${pct ? '%' : ''}`;
}

export type Filters = {
  family?: string;
  code?: string;
  n_qubits?: string;
  n_layers?: string;
  optimizer?: string;
  shots?: string;
  seed?: string;
  status?: string;
  feature?: string;
  selectedOnly?: boolean;
};

const eqOpt = (want: string | undefined, have: unknown) =>
  !want || want === 'all' || String(have ?? 'none') === want;

export function filterRows(rows: ExpRow[], f: Filters): ExpRow[] {
  return rows.filter(
    (r) =>
      eqOpt(f.family, r.family) &&
      eqOpt(f.code, r.experiment_code) &&
      eqOpt(f.n_qubits, r.n_qubits) &&
      eqOpt(f.n_layers, r.n_layers) &&
      eqOpt(f.optimizer, r.optimizer) &&
      eqOpt(f.shots, r.shots ?? 0) &&
      eqOpt(f.seed, r.seed) &&
      eqOpt(f.status, r.status) &&
      (!f.feature || (r.feature_extraction ?? '').toLowerCase().includes(f.feature.toLowerCase())) &&
      (!f.selectedOnly || !!r.selected),
  );
}

export function distinct(rows: ExpRow[], key: keyof ExpRow): string[] {
  const s = new Set<string>();
  rows.forEach((r) => s.add(String(r[key] ?? 'none')));
  return [...s].sort((a, b) => (Number(a) - Number(b)) || a.localeCompare(b));
}

export const FAMILY_LABEL: Record<string, string> = {
  classical: 'Classical',
  quantum_kernel: 'Quantum kernel (simulated)',
  variational_quantum: 'Variational quantum (simulated)',
  hybrid: 'Hybrid CNN + quantum (simulated)',
  quantum_inspired_classical: 'Classical statistics of quantum encodings',
};

// Comparison rows are grouped into task categories that must not be ranked together.
export function category(row: { family?: string; experiment_code?: string }): string {
  if (row.family === 'classical') return 'Classical classification';
  if (row.family === 'quantum_kernel') return 'Quantum kernel classification';
  if (row.family === 'variational_quantum') return 'Variational quantum classification';
  if (row.family === 'hybrid') return 'Hybrid classification';
  return 'Relabelled legacy (classical) methods';
}

export function confusionMax(cm: number[][] | null | undefined): number {
  if (!cm || !cm.length) return 0;
  return Math.max(...cm.flat());
}
