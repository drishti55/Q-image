// "Open an algorithm → 5 questions": What is it? Why is it used? What is a quantum kernel? What happens inside the circuit?
// What does the result mean? Visual-first; Beginner/Technical wording; step 5 uses the family's real V3 result
// (/api/v4/families) against the classical RBF-SVM on the same features. Circuits in step 4 are schematics (k = 4).
import { useEffect, useState } from 'react';
import { ArrowRight } from 'lucide-react';
import { MiniCircuit } from '../playground/widgets';
import type { Gate } from '../playground/widgets';
import { featureMapGates } from './qsim';
import { Lv } from '../level';

export type AlgoKey = 'qkc' | 'pqk' | 'vqc' | 'hybrid' | 'rbfsvm';
type MS = { mean: number | null } | null;
export type AlgoResult = { name: string; test_accuracy: MS; matched_rbfsvm: { test_accuracy: MS } | null; architecture: string[] } | undefined;

const BLUE = '#3987e5', AQUA = '#199e70';
const pc = (v?: number | null) => (v == null ? '—' : `${(100 * v).toFixed(1)}%`);
const X = [0.6, 1.4, 2.2, 0.9];

const vqcGates = (): Gate[] => {
  const g: Gate[] = X.map((v, i) => ({ name: 'ry', qubits: [i], params: [v] }));
  for (let l = 0; l < 2; l++) {
    for (let i = 0; i < 4; i++) { g.push({ name: 'ry', qubits: [i], params: [0.1] }); g.push({ name: 'rz', qubits: [i], params: [0.1] }); }
    for (let i = 0; i < 4; i++) g.push({ name: 'cx', qubits: [i, (i + 1) % 4].sort((a, b) => a - b) as number[], params: [] });
  }
  return g;
};
const CIRCUIT: Record<AlgoKey, { gates: Gate[] | null; label: [string, string] }> = {
  qkc: { gates: featureMapGates(X, 'zz_linear'), label: ['Each feature turns a qubit; CX pairs link neighbours. Run twice (x, then y reversed) and count all-zero outcomes.', 'U(x) = ZZFeatureMap; K(x,y) = |⟨0|U(y)†U(x)|0⟩|² = P(0…0) of the compute–uncompute circuit.'] },
  pqk: { gates: featureMapGates(X, 'zz_linear'), label: ['Same encoding circuit, then each qubit is measured on its own in three directions (X, Y, Z).', 'Measure ⟨X_q⟩, ⟨Y_q⟩, ⟨Z_q⟩ for every qubit q → Bloch vectors b_q(x); no pairwise circuit needed.'] },
  vqc: { gates: vqcGates(), label: ['Encode the features, then layers of trainable rotations and a ring of CNOTs; training tunes the angles.', 'RY(xᵢ) encoding; L × [RY(θ) RZ(θ) per qubit + CNOT ring]; readout ⟨Zᵢ⟩ → logits; θ by parameter-shift + Adam.'] },
  hybrid: { gates: featureMapGates(X, 'product_ry'), label: ['The CNN’s numbers (squeezed by PCA) become rotation angles, one per qubit.', 'x = b·MinMax[0,π](PCA_k(MobileNetV3(img))); U(x) = ⊗ RY(xᵢ); K = Π cos²((xᵢ−yᵢ)/2).'] },
  rbfsvm: { gates: null, label: ['No circuit at all: the similarity is computed directly from the distance between feature vectors.', 'K(x,y) = exp(−γ‖x−y‖²), computed classically in O(k).'] },
};
const TEXT: Record<AlgoKey, { what: [string, string]; why: [string, string]; kernel: [string, string] }> = {
  qkc: { what: ['A classifier that asks a quantum circuit “how similar are these two images?”', 'Quantum kernel classifier: SVC with a precomputed fidelity Gram matrix.'],
    why: ['To test whether a quantum similarity separates defect types better than a classical one.', 'Quantum feature maps embed data in a 2ᵏ-dimensional Hilbert space; the kernel may capture structure hard to compute classically.'],
    kernel: ['Turn each image into a quantum state; the overlap of the two states (0 to 1) is the similarity.', 'K(x,y) = |⟨φ(x)|φ(y)⟩|² — a positive semi-definite kernel, so a standard SVM can use it.'] },
  pqk: { what: ['A quantum kernel that compares images one qubit at a time.', 'Projected quantum kernel (Huang et al. 2021): RBF on single-qubit reduced density matrices.'],
    why: ['Whole-state overlaps shrink towards 0 as qubits grow; looking at each qubit separately avoids that.', 'Mitigates exponential concentration of fidelity kernels; needs only 3k local expectation values per image.'],
    kernel: ['Each image becomes a few arrows (one per qubit); images with similar arrows are similar.', 'K(x,y) = exp(−γ Σ_q ‖ρ_q(x) − ρ_q(y)‖²_F) on reduced states ρ_q.'] },
  vqc: { what: ['A small quantum circuit whose rotation angles are trained, like a tiny neural network.', 'Variational quantum classifier: parameterised circuit + ⟨Z⟩ readout + softmax, trained end to end.'],
    why: ['To see whether a trainable quantum circuit can learn the defect classes directly.', 'Tests the expressivity/trainability of a hardware-efficient ansatz on the same features as the kernels.'],
    kernel: ['It doesn’t use one: instead of comparing images, the circuit itself is trained to output the class.', 'No Gram matrix; decision function f(x) = softmax(w ⊙ ⟨Z⟩_{θ}(x) + b).'] },
  hybrid: { what: ['A frozen CNN describes the image, then a quantum kernel classifies that description.', 'MobileNetV3-small (frozen) → PCA-k → quantum fidelity kernel → SVM.'],
    why: ['Raw pixels are too many and too noisy for a few qubits; CNN features are short and informative.', 'Reduces input dimension to k qubits while preserving class structure (PCA keeps most variance).'],
    kernel: ['The same overlap idea, but applied to the CNN’s numbers instead of pixels.', 'K(x,y) = |⟨φ(x)|φ(y)⟩|² with φ = Product-RY / ZZ on PCA angles of CNN features.'] },
  rbfsvm: { what: ['The classical baseline: a support-vector machine with a standard similarity.', 'SVC with RBF kernel on the same features the quantum models receive.'],
    why: ['Every quantum model must beat this on the same inputs to show any benefit.', 'Matched control: identical features, splits, seeds and selection protocol.'],
    kernel: ['It uses a classical kernel: images close in feature space count as similar.', 'K(x,y) = exp(−γ‖x−y‖²); γ, C tuned on validation.'] },
};
const STEPS = ['What is it?', 'Why is it used?', 'What is a quantum kernel?', 'What happens inside the circuit?', 'What does the result mean?'];

function Overlap() {
  const [d, setD] = useState(60);
  const r = 44, a = 0, b = (d * Math.PI) / 180, K = Math.cos(b / 2 - a / 2) ** 2;
  return (
    <div className="flex flex-wrap items-center gap-6">
      <svg viewBox="0 0 120 120" width={120} role="img" aria-label="two quantum states and their overlap">
        <circle cx={60} cy={60} r={r} fill="none" stroke="#334155" />
        <line x1={60} y1={60} x2={60} y2={60 - r} stroke={BLUE} strokeWidth={3.5} strokeLinecap="round" />
        <line x1={60} y1={60} x2={60 + r * Math.sin(b / 2)} y2={60 - r * Math.cos(b / 2)} stroke="#d95926" strokeWidth={3.5} strokeLinecap="round" />
        <text x={60} y={10} textAnchor="middle" fontSize={9} fill={BLUE}>image A</text><text x={104} y={56} fontSize={9} fill="#d95926">B</text>
      </svg>
      <div className="w-56 space-y-2">
        <input type="range" min={0} max={180} value={d} onChange={(e) => setD(+e.target.value)} className="w-full accent-teal-400" aria-label="how different the images are" />
        <div className="text-xs text-slate-400">how different the images are</div>
        <div className="flex items-baseline gap-2"><span className="text-3xl font-semibold tabular-nums text-white">{K.toFixed(2)}</span><span className="text-xs text-slate-400">similarity</span></div>
        <div className="h-2 rounded-full bg-slate-800"><div className="h-2 rounded-full bg-teal-400" style={{ width: `${100 * K}%` }} /></div>
      </div>
    </div>
  );
}

function Animated({ gates }: { gates: Gate[] }) {
  const [i, setI] = useState(0);
  useEffect(() => { const t = setInterval(() => setI((x) => (x + 1) % (gates.length + 4)), 450); return () => clearInterval(t); }, [gates.length]);
  return <MiniCircuit gates={gates} n={4} highlightFrom={0} highlightTo={Math.min(gates.length, i + 1)} />;
}

export default function AlgorithmExplainer({ algo, result }: { algo: AlgoKey; result?: AlgoResult }) {
  const [s, setS] = useState(0);
  useEffect(() => setS(0), [algo]);
  const T = TEXT[algo], C = CIRCUIT[algo], acc = result?.test_accuracy?.mean ?? null, base = result?.matched_rbfsvm?.test_accuracy?.mean ?? null;
  const body = [
    <div key="0" className="flex flex-wrap items-center gap-3">
      {(result?.architecture ?? []).map((a, i, arr) => (
        <span key={i} className="flex items-center gap-2"><span className={`rounded-lg px-3 py-2 text-sm ring-1 ${/qubit|⟨|Bloch/.test(a) ? 'bg-sky-500/10 text-sky-100 ring-sky-500/40' : 'bg-slate-900 text-slate-200 ring-slate-700'}`}>{a}</span>{i < arr.length - 1 && <ArrowRight size={14} className="text-slate-600" />}</span>))}
    </div>,
    <div key="1" className="flex items-end gap-6">
      {[['this model', acc, algo === 'rbfsvm' ? AQUA : BLUE], ['classical, same features', algo === 'rbfsvm' ? acc : base, AQUA]].map(([l, v, c]) => (
        <div key={l as string} className="text-center"><div className="text-sm font-semibold tabular-nums text-white">{pc(v as number | null)}</div>
          <div className="mx-auto w-14 rounded-t transition-all duration-700" style={{ height: `${120 * ((v as number | null) ?? 0)}px`, background: c as string }} /><div className="mt-1 w-24 text-[11px] text-slate-400">{l as string}</div></div>))}
      <div className="max-w-xs pb-6 text-xs text-slate-500">The comparison every quantum model is judged by.</div>
    </div>,
    <Overlap key="2" />,
    C.gates ? <Animated key="3" gates={C.gates} /> : (
      <div key="3" className="flex items-center gap-4 font-mono text-sm text-slate-200"><span className="rounded-lg bg-slate-900 px-3 py-2 ring-1 ring-slate-700">x</span><span className="rounded-lg bg-slate-900 px-3 py-2 ring-1 ring-slate-700">y</span><ArrowRight size={14} className="text-slate-600" /><span className="rounded-lg bg-slate-900 px-3 py-2 ring-1 ring-slate-700">‖x − y‖</span><ArrowRight size={14} className="text-slate-600" /><span className="rounded-lg bg-teal-500/10 px-3 py-2 text-teal-100 ring-1 ring-teal-500/40">exp(−γ‖x−y‖²)</span></div>),
    <div key="4" className="flex flex-wrap items-center gap-8">
      <div><div className="text-[11px] uppercase tracking-wider text-slate-500">test accuracy</div><div className="text-4xl font-semibold tabular-nums text-white">{pc(acc)}</div><div className="text-xs text-slate-400">{result?.name}</div></div>
      {algo !== 'rbfsvm' && base != null && acc != null && (
        <div className={`rounded-xl px-4 py-3 ring-1 ${Math.abs(acc - base) < 0.02 ? 'bg-slate-800/60 ring-slate-600' : acc > base ? 'bg-emerald-500/10 ring-emerald-500/40' : 'bg-rose-500/10 ring-rose-500/40'}`}>
          <div className="text-2xl font-semibold tabular-nums text-white">{acc >= base ? '+' : '−'}{Math.abs(100 * (acc - base)).toFixed(1)} pp</div>
          <div className="text-xs text-slate-300">vs classical RBF-SVM on the same features ({pc(base)})</div>
          <div className="mt-1 text-[11px] text-slate-400">{Math.abs(acc - base) < 0.02 ? 'About the same — no quantum benefit.' : acc > base ? 'Slightly better here, on 360 test images.' : 'The classical baseline wins.'}</div>
        </div>)}
    </div>,
  ];
  const caption = [T.what, T.why, T.kernel, C.label, null][s];
  return (
    <div className="space-y-4" data-testid="algo-explainer">
      <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="questions">
        {STEPS.map((q, i) => (
          <button key={q} type="button" role="tab" aria-selected={i === s} onClick={() => setS(i)}
            className={`rounded-full px-3 py-1 text-xs ring-1 transition ${i === s ? 'bg-teal-500/15 text-teal-100 ring-teal-400/60' : 'text-slate-400 ring-slate-700 hover:text-slate-200'}`}>
            <span className="mr-1 tabular-nums text-slate-500">{i + 1}</span>{q}</button>))}
      </div>
      <div className="min-h-[170px] space-y-4" key={`${algo}-${s}`}>
        {caption && <p className="max-w-2xl text-[15px] leading-relaxed text-slate-200"><Lv beginner={caption[0]} technical={<span className="font-mono text-[13px] text-teal-100">{caption[1]}</span>} /></p>}
        {body[s]}
      </div>
      <div className="flex gap-2">
        <button type="button" disabled={s === 0} onClick={() => setS(s - 1)} className="rounded-md px-3 py-1 text-xs text-slate-300 ring-1 ring-slate-700 disabled:opacity-30">Previous</button>
        <button type="button" disabled={s === 4} onClick={() => setS(s + 1)} className="rounded-md bg-teal-500/15 px-3 py-1 text-xs text-teal-100 ring-1 ring-teal-500/40 disabled:opacity-30">Next question</button>
      </div>
      <p className="text-[10px] text-slate-600">Circuits in question 4 are 4-qubit schematics of the same structure; results in 1, 2 and 5 are the real V3 numbers.</p>
    </div>
  );
}

