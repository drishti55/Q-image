// Exact in-browser maths for the visual learning lab. Images are real NEU-DET train-folder samples
// (/api/v2/dataset/sample/<class>.png); every number shown is computed here from their pixels.
import { useEffect, useState } from 'react';

export type Img = number[][];

/** Per-image contrast stretch to [0, 1] (the "stretch" normalisation of the V4 FRQI model). */
export function stretchImg(a: Img): Img {
  const v = a.flat(), lo = Math.min(...v), hi = Math.max(...v);
  return hi > lo ? a.map((r) => r.map((x) => (x - lo) / (hi - lo))) : a;
}

/** Load a URL and return it as an N×N grayscale array in [0, 1] (browser bilinear resize, optional contrast stretch). */
export function loadGray(url: string, n: number, stretch = true): Promise<Img> {
  return new Promise((res, rej) => {
    const im = new Image();
    im.onload = () => {
      const cv = document.createElement('canvas');
      cv.width = n; cv.height = n;
      const ctx = cv.getContext('2d');
      if (!ctx) return rej(new Error('no canvas'));
      ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high';
      ctx.drawImage(im, 0, 0, n, n);
      const d = ctx.getImageData(0, 0, n, n).data;
      const g = Array.from({ length: n }, (_, y) => Array.from({ length: n }, (_, x) => {
        const i = (y * n + x) * 4;
        return (0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]) / 255;
      }));
      res(stretch ? stretchImg(g) : g);
    };
    im.onerror = () => rej(new Error(`could not load ${url}`));
    im.src = url;
  });
}

export function useGray(url: string | null, n: number) {
  const [s, set] = useState<{ img: Img | null; err: string | null; key: string }>({ img: null, err: null, key: '' });
  const key = `${url}|${n}`;
  useEffect(() => {
    if (!url) return;
    let live = true;
    loadGray(url, n).then((img) => live && set({ img, err: null, key }), (e) => live && set({ img: null, err: String(e.message ?? e), key }));
    return () => { live = false; };
  }, [url, n, key]);
  return s.key === key ? s : { img: null, err: null, key };
}

export const flat = (a: Img) => a.flat();
export const theta = (x: number) => (Math.PI / 2) * x;                // FRQI angle
/** Round half to even, like np.round (used by the project's NEQR quantisation). */
const roundEven = (v: number) => { const f = Math.floor(v), d = v - f; return d > 0.5 + 1e-12 ? f + 1 : d < 0.5 - 1e-12 ? f : f % 2 === 0 ? f : f + 1; };
export const quant = (x: number, q: number) => Math.min(2 ** q - 1, Math.max(0, roundEven(x * (2 ** q - 1)))); // NEQR code, = np.clip(np.round(x·(2^q−1)))
export const log2 = (n: number) => Math.round(Math.log2(n));
export const frqiQubits = (n: number) => 2 * log2(n) + 1;
export const neqrQubits = (n: number, q: number) => 2 * log2(n) + q;

/** FRQI amplitudes, ordered [colour 0 for every pixel …, colour 1 for every pixel …]. */
export function frqiAmps(a: Img) {
  const v = flat(a), s = 1 / Math.sqrt(v.length);
  return { c0: v.map((x) => s * Math.cos(theta(x))), c1: v.map((x) => s * Math.sin(theta(x))) };
}

/** |<ψ_A|ψ_B>|² for two FRQI images of the same size. */
export function frqiOverlap(a: number[], b: number[]) {
  let s = 0;
  for (let i = 0; i < a.length; i++) s += Math.cos(theta(a[i]) - theta(b[i]));
  return (s / a.length) ** 2;
}

/** Patch mixed-state kernel Tr(ρ_A ρ_B) with p×p FRQI patches, stride 1 (the Protocol V4 idea). */
export function patchKernel(A: Img, B: Img, p: number) {
  const patches = (M: Img) => {
    const out: number[][] = [];
    for (let y = 0; y + p <= M.length; y++) for (let x = 0; x + p <= M.length; x++) {
      const v: number[] = [];
      for (let dy = 0; dy < p; dy++) for (let dx = 0; dx < p; dx++) v.push(M[y + dy][x + dx]);
      out.push(v);
    }
    return out;
  };
  const pa = patches(A), pb = patches(B);
  let s = 0;
  for (const u of pa) for (const w of pb) s += frqiOverlap(u, w);
  return s / (pa.length * pb.length);
}

export const roll = (A: Img, s: number): Img => A.map((r) => r.map((_, x) => r[(x - s + r.length * 8) % r.length]));

export function rng(seed: number) {
  let t = seed >>> 0;
  return () => { t += 0x6d2b79f5; let r = Math.imul(t ^ (t >>> 15), 1 | t); r ^= r + Math.imul(r ^ (r >>> 7), 61 | r); return ((r ^ (r >>> 14)) >>> 0) / 4294967296; };
}

function sampleCounts(p: number[], shots: number, rand: () => number) {
  const cum: number[] = []; let c = 0;
  for (const x of p) { c += x; cum.push(c); }
  const counts = new Array(p.length).fill(0);
  for (let k = 0; k < shots; k++) {
    const r = rand() * c; let lo = 0, hi = cum.length - 1;
    while (lo < hi) { const m = (lo + hi) >> 1; if (cum[m] < r) lo = m + 1; else hi = m; }
    counts[lo]++;
  }
  return counts;
}

/** Measure an FRQI state `shots` times and decode: x̂ = (2/π)·atan2(√n₁, √n₀); unobserved pixels → 0. */
export function frqiShots(a: Img, shots: number, seed: number) {
  const v = flat(a), N = v.length, { c0, c1 } = frqiAmps(a);
  const cnt = sampleCounts([...c0.map((x) => x * x), ...c1.map((x) => x * x)], shots, rng(seed));
  let missed = 0;
  const out = v.map((_, i) => {
    const n0 = cnt[i], n1 = cnt[N + i];
    if (n0 + n1 === 0) { missed++; return 0; }
    return (2 / Math.PI) * Math.atan2(Math.sqrt(n1), Math.sqrt(n0));
  });
  return { img: reshape(out, a.length), missed };
}

/** Measure an NEQR state: each shot reveals one pixel's exact q-bit code; unobserved pixels → 0. */
export function neqrShots(a: Img, q: number, shots: number, seed: number) {
  const v = flat(a), N = v.length, seen = new Array(N).fill(false), r = rng(seed);
  for (let k = 0; k < shots; k++) seen[Math.floor(r() * N)] = true;
  const out = v.map((x, i) => (seen[i] ? quant(x, q) / (2 ** q - 1) : 0));
  return { img: reshape(out, a.length), missed: seen.filter((s) => !s).length };
}

export const reshape = (v: number[], n: number): Img => Array.from({ length: n }, (_, y) => v.slice(y * n, y * n + n));
export const mse = (a: Img, b: Img) => { const x = flat(a), y = flat(b); return x.reduce((s, v, i) => s + (v - y[i]) ** 2, 0) / x.length; };

/** 0 → 1 over `ms` every time `key` changes (instantly 1 with reduced motion). */
export function useProgress(key: string, ms: number) {
  const [t, setT] = useState(0);
  useEffect(() => {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { setT(1); return; }
    let raf = 0; const t0 = performance.now();
    const tick = (now: number) => { const v = Math.max(0, Math.min(1, (now - t0) / ms)); setT(v); if (v < 1) raf = requestAnimationFrame(tick); };
    setT(0); raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [key, ms]);
  return t;
}

/** Position bits of pixel i, [q0 (LSB), q1, …] — same order as the project's encoders (_index_to_bits). */
export const posBits = (i: number, nPos: number) => Array.from({ length: nPos }, (_, b) => (i >> b) & 1);

/** Logical gate counts of the project's encoder circuits (src/frqi/encoder.py, src/neqr/encoder.py) for one image:
 *  H on every position qubit; per pixel X on its 0-bits (and again to undo) + one MC-RY (FRQI, skipped for black pixels)
 *  or one MCX per 1-bit of its q-bit code (NEQR, skipped for code 0). */
export function encoderGateCounts(a: Img, q: number) {
  const v = a.flat(), nPos = 2 * log2(a.length);
  const zeros = (i: number) => posBits(i, nPos).filter((b) => b === 0).length;
  const frqiPix = v.map((x, i) => [x, i] as const).filter(([x]) => Math.abs(Math.PI * x) >= 1e-10);
  const codes = v.map((x) => quant(x, q));
  const neqrPix = codes.map((c, i) => [c, i] as const).filter(([c]) => c > 0);
  const ones = (c: number) => c.toString(2).split('').filter((b) => b === '1').length;
  return {
    frqi: { h: nPos, x: frqiPix.reduce((s, [, i]) => s + 2 * zeros(i), 0), controlled: frqiPix.length, qubits: nPos + 1 },
    neqr: { h: nPos, x: neqrPix.reduce((s, [, i]) => s + 2 * zeros(i), 0), controlled: neqrPix.reduce((s, [c]) => s + ones(c), 0), qubits: nPos + q },
  };
}
