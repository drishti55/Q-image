// Compact multiple-choice knowledge check: immediate feedback, a small diagram for the correct idea, running score.
import { useEffect, useState } from 'react';
import { CheckCircle2, RotateCcw, XCircle } from 'lucide-react';
import { TopicDiagram } from './diagrams';

import { QUIZZES } from './quizzes';

export default function Quiz({ id, title = 'Quick check', onScore }: { id: keyof typeof QUIZZES; title?: string; onScore?: (id: string, score: number, answered: number, total: number) => void }) {
  const qs = QUIZZES[id];
  const [ans, setAns] = useState<(number | null)[]>(() => qs.map(() => null));
  const score = ans.filter((a, i) => a === qs[i].answer).length, done = ans.filter((a) => a != null).length;
  useEffect(() => { onScore?.(String(id), score, done, qs.length); }, [id, score, done, qs.length, onScore]);
  return (
    <section className="rounded-2xl border border-slate-800/80 bg-[#0f172a]/70 p-5" data-testid={`quiz-${id}`}>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-[15px] font-semibold text-slate-100">{title}</h2>
        <div className="flex items-center gap-3 text-sm">
          <span className="tabular-nums text-slate-300" data-testid="quiz-score">{score} / {qs.length}</span>
          {done > 0 && <button type="button" onClick={() => setAns(qs.map(() => null))} className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200"><RotateCcw size={12} /> retry</button>}
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {qs.map((q, i) => {
          const a = ans[i], right = a === q.answer;
          return (
            <div key={q.q} className="rounded-xl bg-slate-950/50 p-4 ring-1 ring-slate-800">
              <div className="mb-2 text-[13px] font-medium text-slate-100">{i + 1}. {q.q}</div>
              <div className="grid gap-1.5">
                {q.options.map((o, k) => {
                  const state = a == null ? 'idle' : k === q.answer ? 'right' : k === a ? 'wrong' : 'dim';
                  return (
                    <button key={o} type="button" disabled={a != null} onClick={() => setAns(ans.map((x, j) => (j === i ? k : x)))}
                      className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-left text-xs ring-1 transition ${
                        state === 'right' ? 'bg-emerald-500/15 text-emerald-100 ring-emerald-500/50' : state === 'wrong' ? 'bg-rose-500/15 text-rose-100 ring-rose-500/50'
                          : state === 'dim' ? 'text-slate-500 ring-slate-800' : 'text-slate-300 ring-slate-700 hover:bg-slate-800/70'}`}>
                      {state === 'right' ? <CheckCircle2 size={13} /> : state === 'wrong' ? <XCircle size={13} /> : <span className="inline-block h-[13px] w-[13px] rounded-full ring-1 ring-slate-600" />}{o}
                    </button>);
                })}
              </div>
              {a != null && (
                <div className="mt-3 space-y-2" data-testid="quiz-feedback">
                  <div className={`text-xs font-medium ${right ? 'text-emerald-300' : 'text-rose-300'}`}>{right ? 'Correct.' : 'Not quite.'} <span className="font-normal text-slate-300">{q.why}</span></div>
                  {q.topic && <TopicDiagram id={q.topic} />}
                </div>)}
            </div>);
        })}
      </div>
    </section>
  );
}
