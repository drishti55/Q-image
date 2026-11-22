import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../App';
import { LevelProvider, LevelSwitch } from './level';
import { ExplainThis } from './learn/ExplainThis';
import Quiz from './learn/Quiz';
import Sandbox from './playground/Sandbox';

class RO { observe() {} unobserve() {} disconnect() {} }
vi.stubGlobal('ResizeObserver', RO);
function mockApi(routes: Record<string, unknown>) {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    const key = Object.keys(routes).sort((a, b) => b.length - a.length).find((k) => url.startsWith(k));
    return key ? { ok: true, status: 200, json: async () => routes[key] } : { ok: false, status: 404, statusText: 'Not Found', json: async () => ({ detail: 'Not Found' }) };
  }));
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.stubGlobal('ResizeObserver', RO); try { localStorage.clear(); } catch { /* */ } window.history.pushState({}, '', '/'); });
const wrap = (el: React.ReactNode) => render(<MemoryRouter><LevelProvider><LevelSwitch />{el}</LevelProvider></MemoryRouter>);

describe('learning features', () => {
  it('Explain This shows 3 beginner questions, and formula + detail in Technical mode', async () => {
    wrap(<ExplainThis id="qkc" />);
    fireEvent.click(screen.getByTestId('explain-qkc'));
    const b = await screen.findByTestId('explain-beginner');
    for (const q of ['What am I looking at?', 'What happens here?', 'Why does it matter?']) expect(b.textContent).toContain(q);
    fireEvent.click(screen.getByRole('radio', { name: /technical/i }));
    const t = await screen.findByTestId('explain-technical');
    expect(t.textContent).toContain('precomputed');
  });

  it('quiz gives immediate feedback and keeps score', () => {
    wrap(<Quiz id="pipeline" />);
    fireEvent.click(screen.getByRole('button', { name: /Reduce the number of features/ }));
    expect(screen.getByTestId('quiz-score').textContent).toBe('1 / 4');
    fireEvent.click(screen.getByRole('button', { name: /To save GPU memory/ }));
    expect(screen.getByTestId('quiz-score').textContent).toBe('1 / 4');
    expect(screen.getAllByTestId('quiz-feedback').length).toBe(2);
  });

  it('sandbox updates normalised value, FRQI angle and NEQR bits when a pixel changes', () => {
    wrap(<Sandbox />);
    fireEvent.change(screen.getByTestId('sandbox-slider'), { target: { value: '255' } });
    const t = screen.getByTestId('sandbox').textContent ?? '';
    expect(t).toContain('1.00'); expect(t).toContain('90°'); expect(t).toContain('1111');
  });

  it('pipeline stages expand on click with real (mocked) API data', async () => {
    const ch = { channel: 0, mean_activation: 1, map: 'data:image/png;base64,' };
    const hyb = { image: 'validation/images/inclusion/inclusion_241.jpg', y_true: 'inclusion', original: '', model_input: '', preprocess: { from: [200, 200], to: [3, 224, 224], steps: 'grey → RGB copy → resize 256' },
      stages: [0, 3, 8, 12].map((l) => ({ layer: l, label: `L${l}`, shape: [16, 7, 7], channels: [ch, ch, ch, ch] })), vector: Array(576).fill(0.1),
      pca: { k: 8, explained_variance_ratio: Array(8).fill(0.05), angles_rad: Array(8).fill(1), bandwidth: 0.5, circuit_angles_rad: Array(8).fill(0.5) },
      kernel: { formula: 'K', n_train: 1080, nearest: [{ class: 'inclusion', similarity: 0.98, thumb: '' }], class_mean: { crazing: 0.9, inclusion: 0.95, patches: 0.7, pitted_surface: 0.8, 'rolled-in_scale': 0.7, scratches: 0.7 } },
      model: { group: 'E5-mnv3pca8-qkc-product_ry', name: 'CNN features + QKC (product_ry)', test_accuracy: { mean: 0.9324, std: 0.01 }, n_qubits: 8 },
      saved_predictions: ['inclusion', 'inclusion', 'pitted_surface'], correct_seeds: 2 };
    window.history.pushState({}, '', '/learn');
    mockApi({ '/api/v2/health': { api: 'qimagelab-v2', n_selected: 88, analysis_present: true, results_root_exists: true }, '/api/v4/images': { images: [{ image: hyb.image, class: 'scratches', frac_correct: 1 }] }, '/api/v4/hybrid-pipeline': hyb });
    render(<App />);
    fireEvent.click(await screen.findByTestId('stage-res'));
    await waitFor(() => expect(screen.getByTestId('hybrid-pipeline').textContent).toContain('2/3'));
    expect(screen.getByTestId('hybrid-pipeline').textContent).toContain('93.2%');
    fireEvent.click(screen.getByTestId('stage-q'));
    await waitFor(() => expect(screen.getByTestId('hybrid-pipeline').textContent).toContain('PCA angles'));
  });

  it('model family centre shows metrics from /api/v4/families and computes the limitation', async () => {
    const ms = (m: number) => ({ mean: m, std: 0.01 });
    const fam = (key: string, acc: number, rbf: number | null) => ({ key, label: key.toUpperCase(), n_configs: 3, group: `V3-${key}`, name: `${key} model`, feature_set: 'mnv8c', n_qubits: 8,
      test_accuracy: ms(acc), test_precision_macro: ms(acc), test_recall_macro: ms(acc), test_f1_macro: ms(acc), train_time_s: ms(1), inference_ms_per_image: ms(1),
      architecture: ['MobileNetV3 CNN', 'PCA → 8', 'SVM'], confusion_matrix: Array.from({ length: 6 }, (_, i) => Array.from({ length: 6 }, (__, j) => (i === j ? 50 : 2))),
      matched_rbfsvm: rbf == null ? null : { group: 'V3-mnv8c-rbfsvm', test_accuracy: ms(rbf), train_time_s: ms(0.01) } });
    window.history.pushState({}, '', '/compare');
    mockApi({ '/api/v2/health': { api: 'qimagelab-v2', n_selected: 88, analysis_present: true, results_root_exists: true },
      '/api/v4/families': { n_test: 360, selection: 'val', families: [fam('qkc', 0.953, 0.956), fam('pqk', 0.697, 0.906), fam('vqc', 0.724, 0.906), fam('hybrid', 0.913, 0.906), fam('rbfsvm', 0.906, null)],
        matched_pairs: [{ feature_set: 'mnv8c', features: 'MobileNetV3 CNN', quantum_acc: 0.913, rbfsvm_acc: 0.906 }], quantum_by_feature_source: [{ features: 'Pixels', group: 'a', test_accuracy: 0.64 }, { features: 'Texture', group: 'b', test_accuracy: 0.953 }] } });
    render(<App />);
    const c = await screen.findByTestId('family-centre');
    expect(c.textContent).toContain('91.3%');
    expect(c.textContent).toContain('+0.7 pp vs a classical RBF-SVM on the same features');
    fireEvent.click(screen.getByTestId('family-pqk'));
    await waitFor(() => expect(screen.getByTestId('family-centre').textContent).toContain('−20.9 pp vs a classical RBF-SVM'));
  });
});

import { gateRoles } from './pages/Circuits';
import QuizPage from './pages/QuizPage';
import AlgorithmExplainer from './learn/AlgorithmExplainer';
import { ForestPlot } from './ForestPlot';

const ins = (s: string) => s.split(' ').map((t, i) => { const m = t.match(/^(\w+)\[([\d,]+)\]$/)!; return { i, name: m[1], qubits: m[2].split(',').map(Number), params: [] as number[] }; });

describe('circuit highlighting, quiz page, algorithm explainer, forest plot', () => {
  it('labels the real gate sequences by role (QKC ZZ, VQC, FRQI, NEQR)', () => {
    // sequences copied from /api/v2/circuits/<id> (E3-pca4-qkc-zz_linear, E4-pca4-vqc, E1-frqi2-qkc, E2-neqr2-b2-qkc)
    const zz = gateRoles({ params: { feature_map: 'zz_linear' }, n_qubits: 4, instructions: ins('h[0] h[1] h[2] h[3] p[0] p[1] p[2] p[3] cx[0,1] p[1] cx[0,1] cx[1,2] p[2] cx[1,2]') });
    expect(zz).toEqual(['super', 'super', 'super', 'super', 'encode', 'encode', 'encode', 'encode', 'entangle', 'entangle', 'entangle', 'entangle', 'entangle', 'entangle']);
    const vqc = gateRoles({ params: { layers: 1 }, n_qubits: 2, instructions: ins('ry[0] ry[1] ry[0] rz[0] ry[1] rz[1] cx[0,1] cx[1,0]') });
    expect(vqc).toEqual(['encode', 'encode', 'train', 'train', 'train', 'train', 'entangle', 'entangle']);
    const frqi = gateRoles({ params: { representation: 'FRQI' }, n_qubits: 3, instructions: ins('h[0] h[1] barrier[0,1,2] x[0] x[1] ry[2] ccx[0,1,2] ry[2] ccx[0,1,2] x[0] x[1]') });
    expect(frqi).toEqual(['super', 'super', 'none', 'select', 'select', 'write', 'write', 'write', 'write', 'select', 'select']);
    const neqr = gateRoles({ params: { representation: 'NEQR' }, n_qubits: 4, instructions: ins('h[0] h[1] x[0] x[1] ccx[0,1,3] x[0] x[1]') });
    expect(neqr).toEqual(['super', 'super', 'select', 'select', 'write', 'select', 'select']);
  });

  it('quiz page tracks the overall score across topics', async () => {
    wrap(<QuizPage />);
    expect(screen.getByTestId('quiz-total').textContent).toMatch(/^0\/\d+$/);
    fireEvent.click(screen.getByRole('button', { name: /Reduce the number of features/ }));
    await waitFor(() => expect(screen.getByTestId('quiz-total').textContent).toMatch(/^1\//));
    fireEvent.click(screen.getByTestId('quiz-tab-encoding'));
    fireEvent.click(screen.getAllByRole('button', { name: /^5$/ })[0]);
    await waitFor(() => expect(screen.getByTestId('quiz-total').textContent).toMatch(/^2\//));
  });

  it('algorithm explainer walks the 5 questions and step 5 shows the real result vs the classical baseline', () => {
    wrap(<AlgorithmExplainer algo="hybrid" result={{ name: 'MobileNetV3 PCA-8 + QKC', test_accuracy: { mean: 0.913 }, matched_rbfsvm: { test_accuracy: { mean: 0.906 } }, architecture: ['MobileNetV3 CNN', 'PCA → 8', 'SVM'] }} />);
    expect(screen.getAllByRole('tab').map((t) => t.textContent)).toEqual(['1What is it?', '2Why is it used?', '3What is a quantum kernel?', '4What happens inside the circuit?', '5What does the result mean?']);
    fireEvent.click(screen.getByRole('tab', { name: /What does the result mean/ }));
    const t = screen.getByTestId('algo-explainer').textContent ?? '';
    expect(t).toContain('91.3%'); expect(t).toContain('+0.7 pp'); expect(t).toContain('no quantum benefit');
  });

  it('forest plot marks significance and shows numbers on hover', () => {
    render(<ForestPlot testid="fp" rows={[{ name: 'A vs B', diff: 0.27, ci95: [0.21, 0.33], p_holm: 0.0008 }, { name: 'C vs D', diff: 0.04, ci95: [-0.01, 0.08], p_holm: 0.06 }]} />);
    fireEvent.mouseEnter(screen.getByText('C vs D').parentElement as Element);
    expect(screen.getByTestId('fp').textContent).toContain('not significant');
  });
});
