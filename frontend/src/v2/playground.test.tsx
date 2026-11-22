/* eslint-disable @typescript-eslint/no-explicit-any */
// 3×3 Algorithm Playground + Quantum vs Classical tests. The playground data is the REAL built V3 file
// (results/qml_v3/playground/playground_3x3.json, read-only); playground tests skip if it has not been built.
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from '../App';
import { PixelGrid } from './playground/widgets';
import { ALGOS, makeCtx } from './pages/Playground';
import { bestBy, hybridAnalysis, inputDims, isMainClassical, isMainQuantum, summarizeDemo } from './pages/QuantumVsClassical';
import type { Model } from './api';

const files = import.meta.glob('../../../results/qml_v3/playground/playground_3x3.json', { eager: true, import: 'default' });
const PG: any = Object.values(files)[0] ?? null;
const hasPG = PG !== null;

class RO { observe() {} unobserve() {} disconnect() {} }
vi.stubGlobal('ResizeObserver', RO);
HTMLCanvasElement.prototype.getContext = (() => null) as any; // jsdom has no canvas; ArrayImage handles a null context
function mockApi(routes: Record<string, unknown>, fail: string[] = []) {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (fail.some((p) => url.startsWith(p))) return { ok: false, status: 404, statusText: 'Not Found', json: async () => ({ detail: 'V3 playground data not built' }) };
    const key = Object.keys(routes).sort((a, b) => b.length - a.length).find((k) => url.startsWith(k));
    if (!key) return { ok: false, status: 404, statusText: 'Not Found', json: async () => ({ detail: 'Not Found' }) };
    return { ok: true, status: 200, json: async () => routes[key] };
  }));
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.stubGlobal('ResizeObserver', RO); window.history.pushState({}, '', '/'); });
const health = { api: 'qimagelab-v2', api_version: '2.2', results_root_exists: true, analysis_present: true, n_selected: 88 };
const go = (path: string) => window.history.pushState({}, '', path);
const counter = () => screen.getByTestId('step-counter').textContent;
const open = async (path: string) => { go(path); mockApi({ '/api/v2/health': health, '/api/v3/playground': PG }); render(<App />); await screen.findByTestId('algo-title'); };

describe('PixelGrid', () => {
  it('renders the 3×3 values, labels padding and shows a hover tooltip', () => {
    render(<PixelGrid values={[[70, 180, 0], [19, 20, 0], [0, 0, 0]]} padding={(r, c) => !(r < 2 && c < 2)} highlight={[{ r: 0, c: 1 }]} />);
    expect(screen.getByTestId('cell-0-0').textContent).toContain('70');
    expect(screen.getByTestId('cell-0-1').className).toContain('ring-cyan-500');
    expect(screen.getAllByText('pad')).toHaveLength(5);
    fireEvent.mouseEnter(screen.getByTestId('cell-1-1'));
    expect(screen.getByRole('tooltip').textContent).toContain('row 2, column 2 · intensity 20');
    fireEvent.mouseEnter(screen.getByTestId('cell-2-2'));
    expect(screen.getByRole('tooltip').textContent).toContain('zero padding');
  });
  it('image pixels are clickable, padding is not', () => {
    const onSelect = vi.fn();
    render(<PixelGrid values={[[70, 180, 0], [19, 20, 0], [0, 0, 0]]} padding={(r, c) => !(r < 2 && c < 2)} onSelect={onSelect} selected={{ r: 0, c: 0 }} />);
    fireEvent.click(screen.getByTestId('cell-1-0'));
    fireEvent.click(screen.getByTestId('cell-2-2'));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(1, 0);
    expect(screen.getByTestId('cell-0-0').getAttribute('aria-pressed')).toBe('true');
  });
});

describe.skipIf(!hasPG)('3×3 Algorithm Playground (real V3 playground data)', () => {
  it('playground data carries no classifier outputs for the artificial grid', () => {
    const txt = JSON.stringify(PG);
    expect(txt).not.toMatch(/"prediction"|"probabilities"|"decision_ovr"|"logits"/);
    expect(PG.pixel_traces).toHaveLength(4);
  });

  it('every algorithm builds every step and trace for every pixel and option', () => {
    expect(ALGOS.map((a) => a.id)).toEqual(['preprocessing', 'pca', 'logreg', 'svm', 'cnn', 'mnv3', 'frqi', 'neqr', 'qkc', 'vqc']);
    for (const a of ALGOS) {
      const opts = a.options?.length ? a.options[0].values.map(([v]) => v) : [''];
      for (const v of opts) for (const px of [0, 1, 2, 3]) {
        const sp = new URLSearchParams({ px: String(px), ...(a.options?.length ? { [a.options[0].key]: v } : {}) });
        const c = makeCtx(PG, a, sp);
        const steps = a.steps(c), tr = a.trace(c);
        expect(steps.length).toBeGreaterThanOrEqual(4);
        expect(tr.length).toBeGreaterThanOrEqual(4);
        for (const s of steps) { expect(s.explain && s.why && s.interp).toBeTruthy(); render(<div>{s.body}{s.out}{s.formula}</div>); }
        cleanup();
      }
    }
    expect(ALGOS.find((a) => a.id === 'frqi')!.steps(makeCtx(PG, ALGOS[6], new URLSearchParams())).length).toBe(10);
    expect(ALGOS.find((a) => a.id === 'vqc')!.steps(makeCtx(PG, ALGOS[9], new URLSearchParams())).length).toBe(10);
  });

  it('step controls: next, previous, go-to, reset', async () => {
    await open('/playground?algo=frqi');
    expect(counter()).toBe('Step 1 of 10');
    fireEvent.click(screen.getByLabelText('Next step'));
    await waitFor(() => expect(counter()).toBe('Step 2 of 10'));
    fireEvent.click(screen.getByLabelText('Previous step'));
    await waitFor(() => expect(counter()).toBe('Step 1 of 10'));
    fireEvent.click(screen.getByLabelText('Go to step 3'));
    await waitFor(() => expect(counter()).toBe('Step 3 of 10'));
    const t = document.body.textContent ?? '';
    for (const v of [70, 180, 19, 20]) expect(t).toContain(((Math.PI / 2) * v / 255).toFixed(4));
    expect(t).toContain('0.0000'); // padding cells: theta = 0
    fireEvent.click(screen.getByLabelText('Reset'));
    await waitFor(() => expect(counter()).toBe('Step 1 of 10'));
    expect(screen.getByLabelText('Previous step')).toHaveProperty('disabled', true);
  });

  it('clicking pixel 70 then 180 follows each pixel through FRQI', async () => {
    await open('/playground?algo=frqi&step=2');
    fireEvent.click(screen.getByTestId('cell-0-0'));
    await waitFor(() => expect(screen.getByTestId('pixel-facts').textContent).toContain('0.2745'));
    expect(screen.getByTestId('explain-out').textContent).toContain('0.4312');
    expect(screen.getByTestId('journey-theta').getAttribute('data-active')).toBe('true');
    expect(screen.getByTestId('cell-0-0').textContent).toContain('θ0.43');
    fireEvent.click(screen.getByTestId('cell-0-1'));
    await waitFor(() => expect(screen.getByTestId('explain-out').textContent).toContain('1.1088'));
    expect(screen.getByTestId('pixel-facts').textContent).toContain('10110100');
  });

  it('NEQR binary of the selected pixel at 2, 4 and 8 bits', async () => {
    await open('/playground?algo=neqr&step=2&px=0');
    const expectBits = async (bits: string, code: string) => {
      fireEvent.click(screen.getByTestId(`opt-bits-${bits}`));
      await waitFor(() => expect(screen.getByTestId('neqr-bits').textContent).toBe(code));
    };
    await expectBits('2', '01');
    await expectBits('4', '0100');
    await expectBits('8', '01000110');
    fireEvent.click(screen.getByTestId('cell-1-0')); // pixel 19
    await waitFor(() => expect(screen.getByTestId('neqr-bits').textContent).toBe('00010011'));
  });

  it('presentation mode opens full-screen and exits', async () => {
    await open('/playground?algo=qkc');
    fireEvent.click(screen.getByTestId('enter-present'));
    await screen.findByTestId('present-mode');
    fireEvent.click(screen.getByLabelText('Exit presentation mode'));
    await waitFor(() => expect(screen.queryByTestId('present-mode')).toBeNull());
  });

  it('shows an explicit error state when the playground endpoint is missing', async () => {
    go('/playground');
    mockApi({ '/api/v2/health': health }, ['/api/v3/playground']);
    render(<App />);
    await screen.findByText(/V3 playground data not built/);
    expect(screen.queryByTestId('step-counter')).toBeNull();
  });

  it('side-by-side summaries come from the data and contain no predictions', () => {
    const f = summarizeDemo('frqi', PG);
    expect(f.cost.join(' ')).toContain(String(PG.frqi.logical_gates));
    expect(JSON.stringify(summarizeDemo('qkc', PG))).not.toMatch(/prediction/);
  });
});

const MS = (m: number | null, s = 0.01) => ({ mean: m, std: s, n: 3 });
const mk = (group: string, acc: number, o: Partial<Model> = {}): Model => ({
  group, display_name: group, model_name: group, experiment_code: '', category: 'Classical models', family: '', is_quantum: false,
  is_legacy_relabelled: false, is_ablation: false, feature_source: 'Pixels 64×64 → PCA 8', feature_extraction: '', encoding: 'none (classical)',
  n_qubits: null, n_layers: null, optimizer: null, shots: 0, execution: 'classical', params: {}, experiment_ids: [], n_seeds: 3, n_test: 360,
  n_candidates: null, val_f1_macro: MS(acc), test_accuracy: MS(acc), test_precision_macro: MS(acc), test_recall_macro: MS(acc),
  test_f1_macro: MS(acc), test_f1_weighted: MS(acc), train_time_s: MS(1), test_inference_ms_per_image: MS(0.1), circuit: null,
  per_seed: [{ seed: 0, experiment_id: `${group}__s0`, val: null, test: { accuracy: acc } }], ...o,
});

describe('Quantum vs Classical helpers', () => {
  it('derives input dimensions from the feature source', () => {
    expect(inputDims('Pixels 64×64 → PCA 8')).toBe('8');
    expect(inputDims('MobileNetV3 features (576-d)')).toBe('576');
    expect(inputDims('Raw pixels 16×16')).toBe('256');
    expect(inputDims('End-to-end CNN (128×128 pixels)')).toBe('16384');
  });
  it('separates classical / quantum views and excludes legacy + ablations', () => {
    const ms = [mk('E6-pca8-rbfsvm', 0.6), mk('legacy', 0.4, { is_legacy_relabelled: true }), mk('E5-mnv3pca8-logreg', 0.9),
      mk('E3-q', 0.64, { is_quantum: true, category: 'Quantum kernel models' }), mk('E4-abl', 0.2, { is_quantum: true, is_ablation: true, category: 'Variational quantum classifiers' }),
      mk('E5-h', 0.93, { is_quantum: true, category: 'Hybrid CNN + quantum models' })];
    expect(ms.filter(isMainClassical).map((m) => m.group)).toEqual(['E6-pca8-rbfsvm']);
    expect(ms.filter(isMainQuantum).map((m) => m.group)).toEqual(['E3-q']);
    expect(bestBy(ms)?.group).toBe('E5-h');
  });
  it('hybrid analysis splits feature effect from classifier effect', () => {
    const q = { is_quantum: true, category: 'Hybrid CNN + quantum models' } as const;
    const ms = [mk('E5-mnv3pca8-logreg', 0.92), mk('E5-mnv3pca8-rbfsvm', 0.93), mk('E5-mnv3pca8-qkc-zz_full', 0.927, q),
      mk('E5-mnv3pca8-qkc-product_ry', 0.932, q), mk('E3-pca8-qkc-zz_full', 0.64, { is_quantum: true, category: 'Quantum kernel models' })];
    const k8 = hybridAnalysis(ms).find((r) => r.k === 8)!;
    expect(k8.classifierDiff).toBeCloseTo(0.002, 6);
    expect(k8.featureGain).toBeCloseTo(0.292, 6);
    expect(k8.bestQuantum?.group).toBe('E5-mnv3pca8-qkc-product_ry');
  });
});

describe('Quantum vs Classical page', () => {
  it('renders tabs and switches views from API data', async () => {
    const models = [mk('E7-mnv3-logreg', 0.964, { display_name: 'Frozen MNV3 LR', feature_source: 'MobileNetV3 features (576-d)' }),
      mk('E3-pca8-qkc-zz_full', 0.64, { display_name: 'QKC ZZ-full 8q', is_quantum: true, category: 'Quantum kernel models', n_qubits: 8, encoding: 'ZZ feature map (full)', circuit: { n_qubits: 8, gates_logical: 50, depth_logical: 20, gates_compiled: 108, depth_compiled: 40, cx_compiled: 56, two_qubit_gates_compiled: 56 } })];
    go('/quantum-vs-classical?view=classical');
    mockApi({ '/api/v2/health': health, '/api/v2/models': { count: 2, categories: [], models } });
    render(<App />);
    await screen.findByTestId('table-classical');
    expect(screen.getByTestId('best-classical model').textContent).toContain('Frozen MNV3 LR');
    expect(screen.getByTestId('headline-qkc').textContent).toContain('64.0%');
    fireEvent.click(screen.getByTestId('tab-quantum'));
    await screen.findByTestId('table-quantum-qkc');
    expect(screen.getByTestId('row-E3-pca8-qkc-zz_full').textContent).toContain('50 / 108');
  });
});
