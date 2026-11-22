// Learning level: changes only how explanations are worded (Explain popovers, step captions). Data and pages never change.
import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';

export type Level = 'beginner' | 'technical';
const KEY = 'qil-level';
const Ctx = createContext<{ level: Level; setLevel: (l: Level) => void }>({ level: 'beginner', setLevel: () => {} });

function initial(): Level {
  try { const s = window.localStorage.getItem(KEY); if (s === 'beginner' || s === 'technical') return s; } catch { /* storage blocked */ }
  return 'beginner';
}

export function LevelProvider({ children }: { children: ReactNode }) {
  const [level, setLevel] = useState<Level>(initial);
  useEffect(() => { try { window.localStorage.setItem(KEY, level); } catch { /* ignore */ } }, [level]);
  return <Ctx.Provider value={{ level, setLevel }}>{children}</Ctx.Provider>;
}

export const useLevel = () => useContext(Ctx);

/** Renders `beginner` or `technical` content depending on the learning level. */
export function Lv({ beginner, technical }: { beginner: ReactNode; technical: ReactNode }) {
  return <>{useLevel().level === 'technical' ? technical : beginner}</>;
}

export function LevelSwitch() {
  const { level, setLevel } = useLevel();
  return (
    <div role="radiogroup" aria-label="Learning level" className="flex rounded-lg border border-slate-700/80 bg-slate-900/70 p-0.5 text-xs" data-testid="level-switch">
      {(['beginner', 'technical'] as Level[]).map((l) => (
        <button key={l} type="button" role="radio" aria-checked={level === l} onClick={() => setLevel(l)}
          title={l === 'beginner' ? 'Simple words and pictures' : 'Formulas and circuit details'}
          className={`rounded-md px-2.5 py-1 capitalize transition-colors ${level === l ? 'bg-teal-500/15 text-teal-200 ring-1 ring-teal-500/40' : 'text-slate-400 hover:text-slate-200'}`}>{l}</button>))}
    </div>
  );
}
