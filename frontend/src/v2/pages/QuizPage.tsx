// Knowledge check: every quiz set in one place, with section progress and an overall score ring.
import { useCallback, useState } from 'react';
import { Atom, BarChart3, Brain, Cpu, Image as ImageIcon, Layers, Network, Trophy } from 'lucide-react';
import Quiz from '../learn/Quiz';
import { QUIZZES } from '../learn/quizzes';

const SECTIONS: { id: keyof typeof QUIZZES; title: string; icon: typeof Atom }[] = [
  { id: 'pipeline', title: 'The pipeline', icon: Layers },
  { id: 'encoding', title: 'FRQI & NEQR', icon: Atom },
  { id: 'algorithms', title: 'QKC · PQK · VQC', icon: Cpu },
  { id: 'cnn', title: 'CNN features', icon: Network },
  { id: 'playground', title: 'Playground', icon: Brain },
  { id: 'reconstruction', title: 'Reconstruction', icon: ImageIcon },
  { id: 'results', title: 'Reading results', icon: BarChart3 },
];
type S = Record<string, { score: number; answered: number; total: number }>;

function Ring({ v, size = 120 }: { v: number; size?: number }) {
  const r = size / 2 - 8, c = 2 * Math.PI * r;
  return (
    <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size} role="img" aria-label={`${Math.round(100 * v)}% correct`}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#1e293b" strokeWidth={10} />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#5eead4" strokeWidth={10} strokeLinecap="round" strokeDasharray={`${c * v} ${c}`} transform={`rotate(-90 ${size / 2} ${size / 2})`} style={{ transition: 'stroke-dasharray .5s' }} />
    </svg>
  );
}

export default function QuizPage() {
  const [sec, setSec] = useState<keyof typeof QUIZZES>('pipeline');
  const [st, setSt] = useState<S>({});
  const onScore = useCallback((id: string, score: number, answered: number, total: number) => setSt((s) => (s[id]?.score === score && s[id]?.answered === answered ? s : { ...s, [id]: { score, answered, total } })), []);
  const total = SECTIONS.reduce((n, s) => n + QUIZZES[s.id].length, 0);
  const score = Object.values(st).reduce((n, x) => n + x.score, 0), answered = Object.values(st).reduce((n, x) => n + x.answered, 0);
  return (
    <div className="space-y-6" data-testid="quiz-page">
      <div className="flex flex-wrap items-center gap-6">
        <div className="relative">
          <Ring v={total ? score / total : 0} />
          <div className="absolute inset-0 grid place-items-center text-center"><div><div className="text-2xl font-semibold tabular-nums text-white" data-testid="quiz-total">{score}/{total}</div><div className="text-[10px] text-slate-500">{answered} answered</div></div></div>
        </div>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-50">Knowledge check</h1>
          <p className="mt-1 text-sm text-slate-400">{SECTIONS.length} topics · {total} questions · instant feedback</p>
          {answered === total && <div className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-teal-500/15 px-3 py-1 text-xs text-teal-100 ring-1 ring-teal-500/40"><Trophy size={13} /> All done — {Math.round((100 * score) / total)}%</div>}
        </div>
      </div>
      <div className="grid gap-2 sm:grid-cols-4 lg:grid-cols-7" role="tablist" aria-label="quiz topics">
        {SECTIONS.map((s) => {
          const x = st[s.id], n = QUIZZES[s.id].length, Icon = s.icon;
          return (
            <button key={s.id} type="button" role="tab" aria-selected={sec === s.id} onClick={() => setSec(s.id)} data-testid={`quiz-tab-${s.id}`}
              className={`rounded-xl px-3 py-3 text-left ring-1 transition ${sec === s.id ? 'bg-teal-500/10 ring-teal-400/60' : 'bg-slate-950/50 ring-slate-800 hover:ring-slate-600'}`}>
              <Icon size={16} className={sec === s.id ? 'text-teal-300' : 'text-slate-500'} />
              <div className="mt-1.5 text-xs font-medium text-slate-200">{s.title}</div>
              <div className="mt-1 flex gap-0.5">{Array.from({ length: n }, (_, k) => <span key={k} className={`h-1 flex-1 rounded-full ${k < (x?.answered ?? 0) ? 'bg-teal-400' : 'bg-slate-700'}`} />)}</div>
              <div className="mt-1 text-[10px] tabular-nums text-slate-500">{x?.score ?? 0}/{n}</div>
            </button>);
        })}
      </div>
      {SECTIONS.map((s) => <div key={s.id} hidden={sec !== s.id}><Quiz id={s.id} title={s.title} onScore={onScore} /></div>)}
    </div>
  );
}
