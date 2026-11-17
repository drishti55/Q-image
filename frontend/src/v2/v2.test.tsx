import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import App from '../App';
import { filterModels, sortModels } from './pages/Models';
import type { Model } from './api';

class RO { observe() {} unobserve() {} disconnect() {} }
vi.stubGlobal('ResizeObserver', RO);

function mockApi(routes: Record<string, unknown>, fail404: string[] = []) {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (fail404.some((p) => url.startsWith(p))) return { ok: false, status: 404, statusText: 'Not Found', json: async () => ({ detail: 'Not Found' }) };
    const key = Object.keys(routes).sort((a, b) => b.length - a.length).find((k) => url.startsWith(k));
    if (!key) return { ok: false, status: 404, statusText: 'Not Found', json: async () => ({ detail: 'Not Found' }) };
    return { ok: true, status: 200, json: async () => routes[key] };
  }));
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.stubGlobal('ResizeObserver', RO); window.history.pushState({}, '', '/'); });

const MS = (m: number | null, s: number | null = 0.01) => ({ mean: m, std: s, n: 3 });
const best = (name: string, acc: number, exec = 'classical') => ({ test_accuracy: acc, models: [{ group: name, display_name: name, category: 'x', test_accuracy: MS(acc), test_f1_macro: MS(acc - 0.01), execution: exec, n_qubits: null }] });
const summary = {
  has_data: true,
  dataset: { name: 'NEU-DET', manifest_id: 'neu-test', total_images: 1234, classes: ['crazing', 'inclusion'], n_classes: 7, locked_test_images: 321, trainval_images: 913 },
  protocol: { locked_test: 'x', selection: 'y', seeds: [0, 1, 2], execution: 'All quantum models are classical (CPU) simulations — no quantum hardware.' },
  counts: { selected_configurations: 77, experiments: { completed: 4321, failed: 2, total: 4323 }, reconstruction_runs: 15, reconstruction_failed: 1,
    quantum_configurations: 50, classical_configurations: 27, by_category: {} },
  best: { overall: best('Model Alpha', 0.9512), quantum: best('QKC Beta', 0.6111, 'exact statevector, simulated'), hybrid: best('Hybrid Gamma', 0.9001, 'exact statevector, simulated'), classical_pixel: best('Pixel Delta', 0.6543) },
  families: [{ family: 'Fam A', n_models: 3, best_name: 'Model Alpha', best_group: 'a', best_test_accuracy: MS(0.9512), best_test_f1_macro: MS(0.95), median_test_accuracy: 0.8 }],
  findings: [{ id: 'cnn_features', title: 'Finding title one', text: 'Finding text one', groups: [] }],
};
const health = { api: 'qimagelab-v2', api_version: '2.2', results_root_exists: true, analysis_present: true, n_selected: 77 };

describe('routing and V2-first shell', () => {
  it('"/" shows every version with V4 first, numbers only from the API', async () => {
    const acc = (m: number, s = 0.01) => ({ mean: m, std: s, n: 3 });
    const cmp = (name: string, diff: number, p: number) => ({ name, diff, ci95: [diff - 0.02, diff + 0.02], p_holm: p });
    mockApi({ '/api/v2/health': health, '/api/v4/versions': {
      n_test: 360, execution: 'Exact noiseless CPU simulation (no quantum hardware).', same_test_set: 'Same locked test.',
      versions: [
        { id: 'V0', comparable: false, title: 'Proto', what: 'w0', link: '/historical-v0', models: [] },
        { id: 'V2', comparable: true, title: 'Whole', what: 'w2', link: '/overview-v2', frqi: acc(0.6111), neqr: acc(0.6222),
          models: [{ name: 'Old FRQI', type: 'quantum', group: 'g2', test_accuracy: acc(0.6111), note: '' }] },
        { id: 'V4', comparable: true, latest: true, title: 'Patch thing', what: 'w4', link: '/quantum-v4', frqi: acc(0.8888, 0.015), neqr: acc(0.8333),
          frqi_qubits: 7, neqr_qubits: 8, frqi_per_seed: [0.88, 0.89, 0.9], neqr_per_seed: [0.8, 0.83, 0.86], control: acc(0.8444),
          comparisons: [cmp('V4 FRQI vs V2 FRQI (x)', 0.2777, 0.0008), cmp('V4 NEQR vs V2 NEQR (y)', 0.2111, 0.0008), cmp('V4 FRQI vs V4 NEQR', 0.0555, 0.045),
            cmp('V4 FRQI vs classical patch-moment RBF-SVM', 0.0444, 0.06)],
          models: [{ name: 'New FRQI', type: 'quantum', group: 'g4', test_accuracy: acc(0.8888), note: '' }] },
      ] } });
    const { container } = render(<App />);
    await screen.findByTestId('v4-hero');
    expect(screen.getByTestId('hero-frqi').textContent).toContain('88.9');
    expect(screen.getByTestId('hero-neqr').textContent).toContain('83.3');
    const t = container.textContent ?? '';
    for (const v of ['Latest result · Protocol V4', '61.1%', '+27.8 pp', 'p = 0.060', 'not significant', 'no quantum advantage', 'not comparable', 'Old FRQI', 'New FRQI']) expect(t).toContain(v);
  });

  it('/overview-v2 renders the Protocol V2 overview with numbers only from the API', async () => {
    window.history.pushState({}, '', '/overview-v2');
    mockApi({ '/api/v2/health': health, '/api/v2/summary': summary });
    const { container } = render(<App />);
    await screen.findByText('Can quantum machine learning recognise steel surface defects?');
    const t = container.textContent ?? '';
    for (const v of ['77', '4,323', '321', '95.1%', '61.1%', '34.0 percentage', 'Model Alpha', 'QKC Beta', 'Finding title one', 'no quantum hardware', 'Start presentation']) expect(t).toContain(v);
    expect(t).not.toContain('1,800 Images Ready');
    expect(t).toContain('V2 API online · 77 selected models');
  });

  it('shows an explicit stale-backend banner when /api/v2 is missing (pre-V2 backend)', async () => {
    mockApi({}, ['/api/v2']);
    render(<App />);
    await screen.findByText('Protocol V2 data cannot be loaded');
    expect(screen.getAllByText(/started before Protocol V2 existed/).length).toBeGreaterThan(0);
  });

  it('shows an empty state (no numbers) when there are no V2 results', async () => {
    window.history.pushState({}, '', '/overview-v2');
    mockApi({ '/api/v2/health': { ...health, analysis_present: false, n_selected: 0 }, '/api/v2/summary': { has_data: false } });
    render(<App />);
    await screen.findByText('No experiment results available.');
  });

  it('/historical-v0 is labelled historical and read-only', async () => {
    window.history.pushState({}, '', '/historical-v0');
    mockApi({ '/api/v2/health': health, '/api/v2/historical': { label: 'Historical Results — Protocol V0', warnings: ['w1'], counts: { paired_run: 2, per_image_record: 3, unit_test_fixture: 16 }, paired_runs: [], classical_v0: [], source_files: ['results/qml/qml_experiments.csv'] } });
    render(<App />);
    await screen.findByText('Why V0 results are not comparable with V2');
    expect(screen.getByText('Protocol V0 · read-only')).toBeTruthy();
    expect(screen.getByText('Historical V0')).toBeTruthy();
  });

  it('old V0 URLs redirect into /historical-v0 keeping the query string', async () => {
    window.history.pushState({}, '', '/quantum-ml-lab?tab=models');
    mockApi({ '/api/v2/health': health });
    render(<App />);
    await waitFor(() => expect(window.location.pathname + window.location.search).toBe('/historical-v0/qml-lab?tab=models'));
    expect(screen.getAllByText(/Historical Results — Protocol V0 \(read-only\)/).length).toBeGreaterThan(0);
  });

  it('unknown paths show a not-found page linking to V2', async () => {
    window.history.pushState({}, '', '/does-not-exist');
    mockApi({ '/api/v2/health': health });
    render(<App />);
    await screen.findByText('Page not found');
  });
});

const mk = (g: string, over: Partial<Model>): Model => ({
  group: g, display_name: g, model_name: g, experiment_code: 'E3', category: 'Quantum kernel models', family: 'quantum_kernel',
  is_quantum: true, is_legacy_relabelled: false, is_ablation: false, feature_source: 'Pixels 64×64 → PCA 8', feature_extraction: '',
  encoding: 'ZZ feature map (full)', n_qubits: 8, n_layers: 1, optimizer: null, shots: 0, execution: 'exact statevector, simulated',
  params: {}, experiment_ids: [], n_seeds: 3, n_test: 360, n_candidates: 1, val_f1_macro: MS(0.5), test_accuracy: MS(0.5),
  test_precision_macro: MS(0.5), test_recall_macro: MS(0.5), test_f1_macro: MS(0.5), test_f1_weighted: MS(0.5),
  train_time_s: MS(1), test_inference_ms_per_image: MS(1), circuit: null, per_seed: [], ...over,
});

describe('model comparison logic', () => {
  const ms = [
    mk('a', { test_accuracy: MS(0.6), test_f1_macro: MS(0.7), display_name: 'QKC ZZ-full · 8 qubits' }),
    mk('b', { test_accuracy: MS(0.9), test_f1_macro: MS(0.5), category: 'Classical models', n_qubits: null, execution: 'classical', feature_source: 'MobileNetV3 features (576-d)', encoding: 'none (classical)' }),
    mk('c', { test_accuracy: MS(0.4), shots: 100, execution: 'finite shots (100), simulated', n_qubits: 4 }),
  ];
  const all = { q: '', category: 'all', qubits: 'all', source: 'all', encoding: 'all', exec: 'all' };
  it('filters by search, family, qubits, representation, encoding and execution', () => {
    expect(filterModels(ms, { ...all, q: 'zz-full' }).map((m) => m.group)).toEqual(['a']);
    expect(filterModels(ms, { ...all, category: 'Classical models' }).map((m) => m.group)).toEqual(['b']);
    expect(filterModels(ms, { ...all, qubits: 'none' }).map((m) => m.group)).toEqual(['b']);
    expect(filterModels(ms, { ...all, qubits: '4' }).map((m) => m.group)).toEqual(['c']);
    expect(filterModels(ms, { ...all, source: 'MobileNetV3 features (576-d)' }).map((m) => m.group)).toEqual(['b']);
    expect(filterModels(ms, { ...all, encoding: 'none (classical)' }).map((m) => m.group)).toEqual(['b']);
    expect(filterModels(ms, { ...all, exec: 'shots' }).map((m) => m.group)).toEqual(['c']);
    expect(filterModels(ms, { ...all, exec: 'exact' }).map((m) => m.group)).toEqual(['a']);
    expect(filterModels(ms, all)).toHaveLength(3);
  });
  it('sorts by accuracy and by macro-F1', () => {
    expect(sortModels(ms, 'accuracy', true).map((m) => m.group)).toEqual(['b', 'a', 'c']);
    expect(sortModels(ms, 'f1', true).map((m) => m.group)).toEqual(['a', 'b', 'c']);
    expect(sortModels(ms, 'accuracy', false).map((m) => m.group)).toEqual(['c', 'a', 'b']);
  });
});
