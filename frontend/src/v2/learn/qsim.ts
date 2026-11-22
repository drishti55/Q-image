// Tiny exact statevector simulator + PCA for the playground sandbox. Feature maps follow src/v2/qkernel.py:
//   product_ry : RY(x_i) on each qubit
//   zz_linear  : H on all; P(2x_i); for (i, i+1): CX(i,j) · P(2(π−x_i)(π−x_j)) on j · CX(i,j)
//   zz_full    : same, all pairs i < j
import type { Gate } from '../playground/widgets';

export type FMap = 'product_ry' | 'zz_linear' | 'zz_full';
type State = { re: Float64Array; im: Float64Array; n: number };

const zero = (n: number): State => { const re = new Float64Array(1 << n), im = new Float64Array(1 << n); re[0] = 1; return { re, im, n }; };
function apply1(s: State, q: number, m: [number, number, number, number, number, number, number, number]) {
  // m = [a_re, a_im, b_re, b_im, c_re, c_im, d_re, d_im] for [[a, b], [c, d]]
  const bit = 1 << q;
  for (let i = 0; i < s.re.length; i++) {
    if (i & bit) continue;
    const j = i | bit, xr = s.re[i], xi = s.im[i], yr = s.re[j], yi = s.im[j];
    s.re[i] = m[0] * xr - m[1] * xi + m[2] * yr - m[3] * yi; s.im[i] = m[0] * xi + m[1] * xr + m[2] * yi + m[3] * yr;
    s.re[j] = m[4] * xr - m[5] * xi + m[6] * yr - m[7] * yi; s.im[j] = m[4] * xi + m[5] * xr + m[6] * yi + m[7] * yr;
  }
}
const H = 1 / Math.SQRT2;
const ops = {
  h: (s: State, q: number) => apply1(s, q, [H, 0, H, 0, H, 0, -H, 0]),
  ry: (s: State, q: number, t: number) => { const c = Math.cos(t / 2), n = Math.sin(t / 2); apply1(s, q, [c, 0, -n, 0, n, 0, c, 0]); },
  p: (s: State, q: number, f: number) => apply1(s, q, [1, 0, 0, 0, 0, 0, Math.cos(f), Math.sin(f)]),
  cx: (s: State, c: number, t: number) => {
    const cb = 1 << c, tb = 1 << t;
    for (let i = 0; i < s.re.length; i++) if (i & cb && !(i & tb)) { const j = i | tb; [s.re[i], s.re[j]] = [s.re[j], s.re[i]]; [s.im[i], s.im[j]] = [s.im[j], s.im[i]]; }
  },
};

export function featureMapGates(x: number[], fmap: FMap): Gate[] {
  const k = x.length, g: Gate[] = [];
  if (fmap === 'product_ry') { x.forEach((v, i) => g.push({ name: 'ry', qubits: [i], params: [+v.toFixed(3)] })); return g; }
  for (let i = 0; i < k; i++) g.push({ name: 'h', qubits: [i], params: [] });
  for (let i = 0; i < k; i++) g.push({ name: 'p', qubits: [i], params: [+(2 * x[i]).toFixed(3)] });
  const pairs: [number, number][] = [];
  for (let i = 0; i < k; i++) for (let j = i + 1; j < k; j++) if (fmap === 'zz_full' || j === i + 1) pairs.push([i, j]);
  for (const [i, j] of pairs) {
    g.push({ name: 'cx', qubits: [i, j], params: [] });
    g.push({ name: 'p', qubits: [j], params: [+(2 * (Math.PI - x[i]) * (Math.PI - x[j])).toFixed(3)] });
    g.push({ name: 'cx', qubits: [i, j], params: [] });
  }
  return g;
}

/** Exact feature-map state (gate list above is rounded for display only). */
export function encode(x: number[], fmap: FMap): State {
  const s = zero(x.length), k = x.length;
  if (fmap === 'product_ry') { x.forEach((v, i) => ops.ry(s, i, v)); return s; }
  for (let i = 0; i < k; i++) ops.h(s, i);
  for (let i = 0; i < k; i++) ops.p(s, i, 2 * x[i]);
  for (let i = 0; i < k; i++) for (let j = i + 1; j < k; j++) if (fmap === 'zz_full' || j === i + 1) {
    ops.cx(s, i, j); ops.p(s, j, 2 * (Math.PI - x[i]) * (Math.PI - x[j])); ops.cx(s, i, j);
  }
  return s;
}

export function fidelity(a: State, b: State) {
  let r = 0, i = 0;
  for (let k = 0; k < a.re.length; k++) { r += a.re[k] * b.re[k] + a.im[k] * b.im[k]; i += a.re[k] * b.im[k] - a.im[k] * b.re[k]; }
  return r * r + i * i;
}

/** Symmetric eigen-decomposition (cyclic Jacobi). Returns eigenvalues (desc) and eigenvectors as columns. */
export function eigSym(A: number[][]) {
  const n = A.length, a = A.map((r) => [...r]), V: number[][] = A.map((_, i) => A.map((__, j) => (i === j ? 1 : 0)));
  for (let sweep = 0; sweep < 100; sweep++) {
    let off = 0;
    for (let p = 0; p < n; p++) for (let q = p + 1; q < n; q++) off += a[p][q] ** 2;
    if (off < 1e-20) break;
    for (let p = 0; p < n; p++) for (let q = p + 1; q < n; q++) {
      if (Math.abs(a[p][q]) < 1e-300) continue;
      const th = (a[q][q] - a[p][p]) / (2 * a[p][q]), t = Math.sign(th || 1) / (Math.abs(th) + Math.sqrt(th * th + 1)), c = 1 / Math.sqrt(t * t + 1), s = t * c;
      for (let k = 0; k < n; k++) { const akp = a[k][p], akq = a[k][q]; a[k][p] = c * akp - s * akq; a[k][q] = s * akp + c * akq; }
      for (let k = 0; k < n; k++) { const apk = a[p][k], aqk = a[q][k]; a[p][k] = c * apk - s * aqk; a[q][k] = s * apk + c * aqk; }
      for (let k = 0; k < n; k++) { const vkp = V[k][p], vkq = V[k][q]; V[k][p] = c * vkp - s * vkq; V[k][q] = s * vkp + c * vkq; }
    }
  }
  const order = a.map((r, i) => [r[i], i] as const).sort((x, y) => y[0] - x[0]);
  return { values: order.map(([v]) => v), vectors: order.map(([, i]) => V.map((r) => r[i])) };
}

/** PCA fitted on the rows of X (centred, no scaling). Returns k scores per row and explained-variance ratios. */
export function pca(X: number[][], k: number) {
  const n = X.length, d = X[0].length, mu = Array.from({ length: d }, (_, j) => X.reduce((s, r) => s + r[j], 0) / n);
  const Z = X.map((r) => r.map((v, j) => v - mu[j]));
  const C = Array.from({ length: d }, (_, i) => Array.from({ length: d }, (_, j) => Z.reduce((s, r) => s + r[i] * r[j], 0) / Math.max(1, n - 1)));
  const { values, vectors } = eigSym(C), tot = values.reduce((s, v) => s + Math.max(0, v), 0) || 1;
  const comps = vectors.slice(0, k);
  return { scores: Z.map((r) => comps.map((c) => r.reduce((s, v, j) => s + v * c[j], 0))), ratio: values.slice(0, k).map((v) => Math.max(0, v) / tot) };
}

/** Min–max each column to [0, π] across rows (the project's "angle" view). */
export function toAngles(S: number[][]) {
  const k = S[0].length;
  const lo = Array.from({ length: k }, (_, j) => Math.min(...S.map((r) => r[j]))), hi = Array.from({ length: k }, (_, j) => Math.max(...S.map((r) => r[j])));
  return S.map((r) => r.map((v, j) => (hi[j] > lo[j] ? (Math.PI * (v - lo[j])) / (hi[j] - lo[j]) : 0)));
}
