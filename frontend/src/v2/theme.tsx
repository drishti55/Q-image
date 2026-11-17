// Visual language shared by every V2 page: one colour + icon per model family, accuracy bars, collapsibles.
import { useState } from 'react';
import type { ReactNode } from 'react';
import { Atom, Boxes, Brain, ChevronDown, Cpu, Layers, Sparkles } from 'lucide-react';

export type FamilyKey = 'classical' | 'cnn' | 'qkc' | 'vqc' | 'hybrid' | 'encoding';

// Family colours = validated dark-mode categorical palette (dataviz validator: all checks pass on #0f172a, adjacent order
// classical → cnn → qkc → vqc → hybrid → encoding = blue, orange, aqua, yellow, violet, magenta; the triples
// {classical, qkc, vqc} and {qkc, cnn, hybrid} also pass all-pairs). Do not reorder without re-running the validator.
export const FAMILY: Record<FamilyKey, { label: string; short: string; color: string; soft: string; icon: typeof Atom; blurb: string }> = {
  classical: { label: 'Classical ML on pixels', short: 'Classical', color: '#3987e5', soft: 'rgba(57,135,229,0.14)', icon: Layers, blurb: 'SVM / logistic regression on compressed pixels' },
  cnn: { label: 'CNN models (classical)', short: 'CNN', color: '#d95926', soft: 'rgba(217,89,38,0.14)', icon: Brain, blurb: 'Deep convolutional features' },
  qkc: { label: 'Quantum kernel classifiers', short: 'Quantum kernel', color: '#199e70', soft: 'rgba(25,158,112,0.16)', icon: Atom, blurb: 'Similarity measured by quantum states' },
  vqc: { label: 'Variational quantum classifiers', short: 'VQC', color: '#c98500', soft: 'rgba(201,133,0,0.15)', icon: Cpu, blurb: 'Trainable quantum circuits' },
  hybrid: { label: 'Hybrid quantum-classical', short: 'Hybrid', color: '#9085e9', soft: 'rgba(144,133,233,0.15)', icon: Sparkles, blurb: 'CNN features + quantum classifier' },
  encoding: { label: 'FRQI / NEQR kernels', short: 'FRQI / NEQR', color: '#d55181', soft: 'rgba(213,81,129,0.15)', icon: Boxes, blurb: 'Whole image encoded in a quantum state' },
};

export function familyOfSummary(name: string): FamilyKey {
  if (name.startsWith('Classical')) return 'classical';
  if (name.startsWith('CNN')) return 'cnn';
  if (name.startsWith('Quantum kernel')) return 'qkc';
  if (name.startsWith('Variational')) return 'vqc';
  if (name.startsWith('Hybrid')) return 'hybrid';
  return 'encoding';
}

export function familyOfModel(m: { category: string; feature_source: string }): FamilyKey {
  if (m.category === 'Classical models') return /CNN|MobileNet/.test(m.feature_source) ? 'cnn' : 'classical';
  if (m.category === 'Quantum kernel models') return 'qkc';
  if (m.category === 'Variational quantum classifiers') return 'vqc';
  if (m.category === 'Hybrid CNN + quantum models') return 'hybrid';
  return 'encoding';
}

export function FamilyChip({ fam, size = 'sm' }: { fam: FamilyKey; size?: 'sm' | 'md' }) {
  const f = FAMILY[fam];
  const Icon = f.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-medium ${size === 'md' ? 'px-3 py-1 text-xs' : 'px-2 py-0.5 text-[11px]'}`}
      style={{ background: f.soft, color: '#e2e8f0', boxShadow: `inset 0 0 0 1px ${f.color}66` }}>
      <Icon size={size === 'md' ? 14 : 12} color={f.color} /> {f.short}
    </span>
  );
}

export function AccBar({ value, color = '#22d3ee', max = 1, label }: { value: number | null | undefined; color?: string; max?: number; label?: string }) {
  if (value === null || value === undefined) return <span className="text-xs text-slate-500">unavailable</span>;
  return (
    <div className="flex items-center gap-2 min-w-[140px]">
      <div className="h-2 flex-1 rounded-full bg-slate-800/80 overflow-hidden">
        <div className="h-full rounded-full transition-[width] duration-700" style={{ width: `${Math.max(2, (value / max) * 100)}%`, background: color }} />
      </div>
      <span className="w-14 text-right text-sm font-semibold tabular-nums text-slate-100">{label ?? `${(value * 100).toFixed(1)}%`}</span>
    </div>
  );
}

export function Collapsible({ title, hint, children, defaultOpen = false }: { title: string; hint?: string; children: ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className="rounded-2xl border border-slate-800/70 bg-slate-900/40">
      <button onClick={() => setOpen(!open)} aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left">
        <span>
          <span className="block text-sm font-semibold text-slate-100">{title}</span>
          {hint && <span className="block text-xs text-slate-400 mt-0.5">{hint}</span>}
        </span>
        <ChevronDown size={18} className={`shrink-0 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && <div className="border-t border-slate-800/70 px-5 py-4">{children}</div>}
    </section>
  );
}

export function FadeIn({ children, delay = 0 }: { children: ReactNode; delay?: number }) {
  return <div className="animate-[fadeUp_.5s_ease-out_both]" style={{ animationDelay: `${delay}ms` }}>{children}</div>;
}
