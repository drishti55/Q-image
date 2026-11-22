// Model-family learning centre: QKC, PQK, VQC, Hybrid and classical RBF-SVM side by side (Protocol V3, same features,
// splits, seeds and 360 locked test images). Representatives chosen by VALIDATION F1. Data: /api/v4/families.
// Limitations and "why" statements are computed from those numbers, never typed in.
import { useState } from 'react';
import { ArrowRight } from 'lucide-react';
import { useV4 } from '../api';
import { ConfusionMatrix, Gate } from '../ui';
import { ExplainThis } from './ExplainThis';
import { Lv } from '../level';
import AlgorithmExplainer from './AlgorithmExplainer';
import type { AlgoKey } from './AlgorithmExplainer';

type MS = { mean: number | null; std?: number | null } | null;
type Fam = {
  key: string; label: string; n_configs: number; group: string; name: string; feature_set: string; n_qubits: number | null;
  test_accuracy: MS; test_precision_macro: MS; test_recall_macro: MS; test_f1_macro: MS; train_time_s: MS; inference_ms_per_image: MS;
  architecture: string[]; confusion_matrix: number[][] | null; matched_rbfsvm: { group: string; test_accuracy: MS; train_time_s: MS } | null;
};
type Resp = { families: Fam[]; matched_pairs: { feature_set: string; features: string; quantum_acc: number; rbfsvm_acc: number }[];
  quantum_by_feature_source: { features: string; group: string; test_accuracy: number }[]; n_test: number; selection: string };

const TEAL = '#5eead4', GREY = '#475569', BLUE = '#3987e5', AQUA = '#199e70';
const pc = (v?: number | null) => (v == null ? '—' : `${(100 * v).toFixed(1)}%`);
const pp = (v: number) => `${v >= 0 ? '+' : '−'}${Math.abs(100 * v).toFixed(1)} pp`;
const sec = (v?: number | null) => (v == null ? '—' : v >= 1 ? `${v.toFixed(v >= 100 ? 0 : 1)} s` : v >= 0.01 ? `${(1000 * v).toFixed(0)} ms` : `${(1000 * v).toPrecision(2)} ms`);
const EXPLAIN: Record<string, string> = { qkc: 'qkc', pqk: 'pqk', vqc: 'vqc', hybrid: 'cnn', rbfsvm: 'kernel' };

function limitation(f: Fam, all: Fam[]) {
  const acc = f.test_accuracy?.mean ?? 0, m = f.matched_rbfsvm, mAcc = m?.test_accuracy?.mean;
  const qkc = all.find((x) => x.key === 'qkc');
  if (f.key === 'rbfsvm') return 'No quantum part: the classical baseline every quantum model has to beat.';
  const vs = mAcc != null ? `${pp(acc - mAcc)} vs a classical RBF-SVM on the same features` : '';
  if (f.key === 'vqc') return `${vs}; slowest to train (${sec(f.train_time_s?.mean)} vs ${sec(m?.train_time_s?.mean)}).`;
  if (f.key === 'pqk') return `${vs}; ${qkc ? `${pp(acc - (qkc.test_accuracy?.mean ?? 0))} vs the best QKC` : ''}.`;
  if (f.key === 'hybrid') return `${vs} — the CNN features do most of the work.`;
  return `${vs}; the kernel needs one circuit per pair of images (${sec(f.train_time_s?.mean)} to train).`;
}

function MiniBars({ title, fams, get, sel, fmt = pc, log = false }: { title: string; fams: Fam[]; get: (f: Fam) => number | null | undefined; sel: string; fmt?: (v?: number | null) => string; log?: boolean }) {
  const vals = fams.map((f) => get(f) ?? 0), mx = Math.max(...vals, 1e-9), mn = log ? Math.min(...vals.filter((v) => v > 0)) : 0;
  const h = (v: number) => (log ? (v > 0 ? 8 + 72 * (Math.log10(v / mn) / (Math.log10(mx / mn) || 1)) : 0) : 80 * (v / mx));
  return (
    <div className="min-w-0 rounded-xl bg-slate-950/50 p-3 ring-1 ring-slate-800">
      <div className="mb-2 text-[11px] uppercase tracking-wider text-slate-500">{title}{log && ' (log)'}</div>
      <div className="flex h-[96px] items-end gap-1.5">
        {fams.map((f, i) => (
          <div key={f.key} className="flex min-w-0 flex-1 flex-col items-center gap-1" title={`${f.label}: ${fmt(vals[i])}`}>
            <span className={`text-[10px] tabular-nums ${f.key === sel ? 'text-white' : 'text-slate-500'}`}>{fmt(vals[i]).replace('%', '')}</span>
            <div className="w-full rounded-t transition-all duration-500" style={{ height: `${h(vals[i])}px`, background: f.key === sel ? TEAL : GREY }} />
          </div>))}
      </div>
      <div className="mt-1 flex gap-1.5">{fams.map((f) => <span key={f.key} className={`flex-1 truncate text-center text-[9px] ${f.key === sel ? 'text-teal-200' : 'text-slate-500'}`}>{f.key.toUpperCase()}</span>)}</div>
    </div>
  );
}

function Dumbbell({ pairs }: { pairs: Resp['matched_pairs'] }) {
  const W = 460, row = 26, L = 150, X = (v: number) => L + v * (W - L - 20);
  return (
    <svg viewBox={`0 0 ${W} ${pairs.length * row + 26}`} className="w-full max-w-[520px]" role="img" aria-label="quantum vs classical on the same features">
      {[0.4, 0.6, 0.8, 1].map((v) => <g key={v}><line x1={X(v)} x2={X(v)} y1={0} y2={pairs.length * row} stroke="#1e293b" /><text x={X(v)} y={pairs.length * row + 14} textAnchor="middle" fontSize={10} fill="#64748b">{v * 100}%</text></g>)}
      {pairs.map((p, i) => { const y = i * row + 13; return (
        <g key={p.feature_set}>
          <text x={L - 8} y={y + 4} textAnchor="end" fontSize={10.5} fill="#cbd5e1">{p.features} · <tspan fontFamily="monospace" fill="#94a3b8">{p.feature_set}</tspan></text>
          <line x1={X(p.quantum_acc)} x2={X(p.rbfsvm_acc)} y1={y} y2={y} stroke="#64748b" strokeWidth={2} />
          <circle cx={X(p.rbfsvm_acc)} cy={y} r={6} fill={AQUA} stroke="#0f172a" strokeWidth={2}><title>RBF-SVM {pc(p.rbfsvm_acc)}</title></circle>
          <circle cx={X(p.quantum_acc)} cy={y} r={6} fill={BLUE} stroke="#0f172a" strokeWidth={2}><title>quantum kernel {pc(p.quantum_acc)}</title></circle>
        </g>); })}
    </svg>
  );
}

export default function FamilyCentre() {
  const st = useV4<Resp>('/families');
  const [sel, setSel] = useState('hybrid');
  return (
    <Gate state={st}>{(d) => {
      const F = d.families, f = F.find((x) => x.key === sel) ?? F[0];
      const gaps = d.matched_pairs.map((p) => p.quantum_acc - p.rbfsvm_acc), maxGap = Math.max(...gaps.map(Math.abs));
      const src = d.quantum_by_feature_source, best = src[src.length - 1], worst = src[0];
      return (
        <div className="space-y-5" data-testid="family-centre">
          <div className="grid gap-2 sm:grid-cols-5" role="tablist" aria-label="model family">
            {F.map((x) => (
              <button key={x.key} type="button" role="tab" aria-selected={x.key === sel} onClick={() => setSel(x.key)} data-testid={`family-${x.key}`}
                className={`rounded-xl px-3 py-2.5 text-left ring-1 transition ${x.key === sel ? 'bg-teal-500/10 ring-teal-400/60' : 'bg-slate-950/50 ring-slate-800 hover:ring-slate-600'}`}>
                <div className="text-[11px] text-slate-400">{x.label}</div>
                <div className="text-xl font-semibold tabular-nums text-white">{pc(x.test_accuracy?.mean)}</div>
              </button>))}
          </div>
          <div className="rounded-xl bg-slate-950/40 p-4 ring-1 ring-slate-800">
            <div className="mb-3 text-sm font-semibold text-white">Open {f.label.split(' · ')[0]}: 5 questions</div>
            <AlgorithmExplainer algo={f.key as AlgoKey} result={f} />
          </div>
          <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-6">
            <MiniBars title="Accuracy" fams={F} sel={sel} get={(x) => x.test_accuracy?.mean} />
            <MiniBars title="Precision" fams={F} sel={sel} get={(x) => x.test_precision_macro?.mean} />
            <MiniBars title="Recall" fams={F} sel={sel} get={(x) => x.test_recall_macro?.mean} />
            <MiniBars title="F1" fams={F} sel={sel} get={(x) => x.test_f1_macro?.mean} />
            <MiniBars title="Train time" fams={F} sel={sel} get={(x) => x.train_time_s?.mean} fmt={sec} log />
            <MiniBars title="Inference / image" fams={F} sel={sel} get={(x) => (x.inference_ms_per_image?.mean ?? 0) / 1000} fmt={sec} log />
          </div>
          <div className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
            <div className="space-y-4 rounded-xl bg-slate-950/40 p-4 ring-1 ring-slate-800">
              <div className="flex flex-wrap items-center gap-2"><span className="text-sm font-semibold text-white">{f.name}</span><span className="font-mono text-[10px] text-slate-500">{f.group}</span><ExplainThis id={EXPLAIN[f.key]} /></div>
              <div className="flex flex-wrap items-center gap-1.5">{f.architecture.map((a, i) => (
                <span key={i} className="flex items-center gap-1.5"><span className={`rounded-lg px-2.5 py-1.5 text-xs ring-1 ${/qubit|⟨|Bloch/.test(a) ? 'bg-sky-500/10 text-sky-100 ring-sky-500/40' : 'bg-slate-900 text-slate-200 ring-slate-700'}`}>{a}</span>
                  {i < f.architecture.length - 1 && <ArrowRight size={13} className="text-slate-600" />}</span>))}</div>
              <div className="rounded-lg bg-amber-500/5 px-3 py-2 text-xs text-amber-100 ring-1 ring-amber-500/20"><b>Main limitation:</b> {limitation(f, F)}</div>
              <div className="text-[11px] text-slate-500">Best of {f.n_configs} configurations by validation F1 · mean of 3 seeds on {d.n_test} test images</div>
            </div>
            <div className="rounded-xl bg-slate-950/40 p-4 ring-1 ring-slate-800"><ConfusionMatrix cm={f.confusion_matrix} title="Confusion matrix (3 seeds summed)" /></div>
          </div>
          <div className="space-y-3 rounded-xl bg-slate-950/40 p-4 ring-1 ring-slate-800">
            <div className="text-sm font-semibold text-white">Why did this model perform better?</div>
            <div className="grid gap-6 lg:grid-cols-2">
              <div>
                <div className="mb-2 text-xs text-slate-400">1 · The features decide the ceiling (best quantum model per feature source)</div>
                {src.map((s) => (
                  <div key={s.features} className="mb-1.5 grid grid-cols-[9.5rem_minmax(0,1fr)_3.5rem] items-center gap-2 text-xs"><span className="text-slate-300">{s.features}</span>
                    <div className="h-3 rounded-full bg-slate-800"><div className="h-3 rounded-full" style={{ width: `${100 * s.test_accuracy}%`, background: BLUE }} /></div><span className="tabular-nums text-slate-200">{pc(s.test_accuracy)}</span></div>))}
                <p className="mt-2 text-xs text-slate-400"><Lv beginner={`Same kind of quantum model: ${pc(worst.test_accuracy)} on ${worst.features} → ${pc(best.test_accuracy)} on ${best.features}.`} technical={`Range ${pp(best.test_accuracy - worst.test_accuracy)} across feature sources; representatives chosen by validation F1.`} /></p>
              </div>
              <div>
                <div className="mb-2 flex items-center gap-3 text-xs text-slate-400">2 · Same features: <span style={{ color: BLUE }}>● quantum kernel</span> <span style={{ color: AQUA }}>● RBF-SVM</span></div>
                <Dumbbell pairs={d.matched_pairs} />
                <p className="mt-2 text-xs text-slate-400">On identical inputs the two never differ by more than {(100 * maxGap).toFixed(1)} points. No quantum advantage is claimed.</p>
              </div>
            </div>
          </div>
        </div>
      );
    }}</Gate>
  );
}
