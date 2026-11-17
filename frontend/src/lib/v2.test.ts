import { describe, expect, it } from 'vitest';
import { UNAVAILABLE, category, filterRows, fmtMeanStd, fmtNum, fmtPct } from './v2';
import type { ExpRow } from './v2';

describe('formatting never invents numbers', () => {
  it('returns "unavailable" for missing values', () => {
    expect(fmtNum(null)).toBe(UNAVAILABLE);
    expect(fmtNum(undefined)).toBe(UNAVAILABLE);
    expect(fmtNum(Number.NaN)).toBe(UNAVAILABLE);
    expect(fmtPct(null)).toBe(UNAVAILABLE);
    expect(fmtMeanStd({ mean: null, std: null, n: 0 })).toBe(UNAVAILABLE);
    expect(fmtMeanStd(undefined)).toBe(UNAVAILABLE);
  });
  it('formats real values, including a real zero', () => {
    expect(fmtNum(0)).toBe('0.000');
    expect(fmtPct(0.5)).toBe('50.0%');
    expect(fmtMeanStd({ mean: 0.9, std: 0.01, n: 3 })).toBe('90.0 ± 1.0%');
    expect(fmtMeanStd({ mean: 0.9, std: 0.01, n: 3 }, false)).toBe('0.900 ± 0.010');
  });
});

const rows: ExpRow[] = [
  { experiment_id: 'a', status: 'completed', family: 'classical', experiment_code: 'E6', seed: 0, shots: null, feature_extraction: 'PCA(8)' },
  { experiment_id: 'b', status: 'failed', family: 'quantum_kernel', experiment_code: 'E3', n_qubits: 8, seed: 1, shots: 1000, feature_extraction: 'PCA(8)' },
  { experiment_id: 'c', status: 'completed', family: 'variational_quantum', experiment_code: 'E4', n_qubits: 4, n_layers: 2, optimizer: 'adam', seed: 2, selected: true, feature_extraction: 'MobileNet PCA(4)' },
];

describe('filters', () => {
  it('filter by each field', () => {
    expect(filterRows(rows, { status: 'failed' }).map((r) => r.experiment_id)).toEqual(['b']);
    expect(filterRows(rows, { family: 'classical' }).map((r) => r.experiment_id)).toEqual(['a']);
    expect(filterRows(rows, { n_qubits: '4' }).map((r) => r.experiment_id)).toEqual(['c']);
    expect(filterRows(rows, { optimizer: 'adam', n_layers: '2' }).map((r) => r.experiment_id)).toEqual(['c']);
    expect(filterRows(rows, { shots: '0' }).map((r) => r.experiment_id)).toEqual(['a', 'c']);
    expect(filterRows(rows, { shots: '1000' }).map((r) => r.experiment_id)).toEqual(['b']);
    expect(filterRows(rows, { seed: '2', selectedOnly: true }).map((r) => r.experiment_id)).toEqual(['c']);
    expect(filterRows(rows, { feature: 'mobilenet' }).map((r) => r.experiment_id)).toEqual(['c']);
    expect(filterRows(rows, { family: 'all' })).toHaveLength(3);
  });
  it('separates task categories', () => {
    expect(category({ family: 'classical' })).not.toBe(category({ family: 'quantum_kernel' }));
    expect(category({ family: 'quantum_inspired_classical' })).toMatch(/legacy/);
  });
});
