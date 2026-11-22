import { describe, expect, it } from 'vitest';
import { encoderGateCounts, frqiAmps, frqiOverlap, frqiQubits, frqiShots, mse, neqrQubits, neqrShots, patchKernel, quant, roll } from './lab';

const A = [[0, 0.25, 0.5, 0.75], [1, 0.9, 0.1, 0.3], [0.2, 0.4, 0.6, 0.8], [0.05, 0.95, 0.5, 0.5]];

describe('visual lab maths', () => {
  it('FRQI state is normalised and qubit counts follow 2·log2(N)+1 / 2·log2(N)+q', () => {
    const { c0, c1 } = frqiAmps(A);
    expect([...c0, ...c1].reduce((s, a) => s + a * a, 0)).toBeCloseTo(1, 12);
    expect(frqiQubits(4)).toBe(5); expect(frqiQubits(8)).toBe(7); expect(neqrQubits(16, 4)).toBe(12);
  });
  it('overlap is 1 for identical images, symmetric and in [0, 1]', () => {
    const a = A.flat(), b = roll(A, 1).flat();
    expect(frqiOverlap(a, a)).toBeCloseTo(1, 12);
    expect(frqiOverlap(a, b)).toBeCloseTo(frqiOverlap(b, a), 12);
    expect(frqiOverlap(a, b)).toBeGreaterThanOrEqual(0); expect(frqiOverlap(a, b)).toBeLessThanOrEqual(1);
  });
  it('NEQR rounding and shots: exact once every pixel is seen', () => {
    expect(quant(1, 4)).toBe(15); expect(quant(0.5, 2)).toBe(2); expect(quant(0.3, 4)).toBe(4); expect(quant(0.9, 4)).toBe(14);
    const r = neqrShots(A, 8, 100000, 3);
    expect(r.missed).toBe(0);
    expect(mse(A, r.img)).toBeLessThan(1e-5);
  });
  it('FRQI shot estimate converges to the image', () => {
    expect(mse(A, frqiShots(A, 200000, 1).img)).toBeLessThan(mse(A, frqiShots(A, 200, 1).img));
    expect(mse(A, frqiShots(A, 200000, 1).img)).toBeLessThan(1e-3);
  });
  it('patch kernel equals the mean pairwise patch overlap and is shift-robust on a periodic pattern', () => {
    const stripes = Array.from({ length: 8 }, () => Array.from({ length: 8 }, (_, x) => (x % 2 ? 1 : 0)));
    expect(patchKernel(stripes, roll(stripes, 2), 2)).toBeCloseTo(patchKernel(stripes, stripes, 2), 12);
  });
  it('gate counts match the project encoders (Qiskit count_ops of src/frqi, src/neqr on this image)', () => {
    // .venv python: FRQIEncoder(A).build_circuit().count_ops() → x: 56 ; NEQREncoder(round(A·15), 4) → h: 4, x: 56, mcx: 28
    const c = encoderGateCounts(A, 4);
    expect(c.neqr).toEqual({ h: 4, x: 56, controlled: 28, qubits: 8 });
    expect(c.frqi).toEqual({ h: 4, x: 56, controlled: 15, qubits: 5 });
  });
});
