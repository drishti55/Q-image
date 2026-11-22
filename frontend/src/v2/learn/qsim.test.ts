import { describe, expect, it } from 'vitest';
import { eigSym, encode, fidelity, pca, toAngles } from './qsim';

describe('sandbox statevector simulator and PCA', () => {
  const x = [0.3, 1.2, 2.5], y = [2.0, 0.4, 1.1];
  it('matches the project qkernel (src/v2/qkernel.py states + fidelity_kernel) for all three feature maps', () => {
    // reference values computed with .venv python: states(X, fmap, 1) → fidelity_kernel → K[0, 1]
    expect(fidelity(encode(x, 'product_ry'), encode(y, 'product_ry'))).toBeCloseTo(0.21616538025325913, 12);
    expect(fidelity(encode(x, 'zz_linear'), encode(y, 'zz_linear'))).toBeCloseTo(0.20199440649732156, 12);
    expect(fidelity(encode(x, 'zz_full'), encode(y, 'zz_full'))).toBeCloseTo(0.218351536031853, 12);
  });
  it('kernel is 1 on the diagonal and Product-RY has its closed form', () => {
    for (const f of ['product_ry', 'zz_linear', 'zz_full'] as const) expect(fidelity(encode(x, f), encode(x, f))).toBeCloseTo(1, 12);
    expect(fidelity(encode(x, 'product_ry'), encode(y, 'product_ry'))).toBeCloseTo(x.reduce((p, v, i) => p * Math.cos((v - y[i]) / 2) ** 2, 1), 12);
  });
  it('eigen-decomposition and PCA are correct', () => {
    const { values } = eigSym([[2, 1], [1, 2]]);
    expect(values[0]).toBeCloseTo(3, 10); expect(values[1]).toBeCloseTo(1, 10);
    const X = [[1, 2], [2, 4], [3, 6], [4, 8]];  // rank 1
    const p = pca(X, 2);
    expect(p.ratio[0]).toBeCloseTo(1, 10);
    const a = toAngles(p.scores);
    expect(Math.min(...a.map((r) => r[0]))).toBeCloseTo(0, 12); expect(Math.max(...a.map((r) => r[0]))).toBeCloseTo(Math.PI, 12);
  });
});
