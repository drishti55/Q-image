// "Explain this" chip + popover with a beginner explanation of one glossary topic.
import { useEffect, useRef, useState } from 'react';
import { HelpCircle, X } from 'lucide-react';
import { TOPIC } from './glossary';
import { TopicDiagram } from './diagrams';
import { useLevel } from '../level';
import type { Topic } from './glossary';

function Q({ k, v }: { k: string; v?: string }) {
  return v ? <div><div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{k}</div><p className="text-slate-300">{v}</p></div> : null;
}

export function TopicBody({ t }: { t: Topic }) {
  const { level } = useLevel();
  return level === 'technical' ? (
    <div className="space-y-2.5 text-[13px] leading-relaxed" data-testid="explain-technical">
      {t.formula && <div className="rounded-md bg-slate-950/70 px-3 py-2 font-mono text-[12px] text-teal-200 ring-1 ring-slate-800">{t.formula}</div>}
      <Q k="Definition" v={t.what} />
      <Q k="Details" v={t.tech ?? t.how} />
      <Q k="Reading the numbers" v={t.numbers} />
    </div>
  ) : (
    <div className="space-y-2.5 text-[13px] leading-relaxed" data-testid="explain-beginner">
      <TopicDiagram id={t.id} />
      <Q k="1 · What am I looking at?" v={t.look ?? t.short} />
      <Q k="2 · What happens here?" v={t.how} />
      <Q k="3 · Why does it matter?" v={t.why} />
    </div>
  );
}

/** Small chip that opens a beginner explanation of one glossary topic. */
export function ExplainThis({ id, label }: { id: string; label?: string }) {
  const [open, setOpen] = useState(false);
  const [right, setRight] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (!open) return;
    const off = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', off); document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('mousedown', off); document.removeEventListener('keydown', esc); };
  }, [open]);
  const t = TOPIC[id];
  if (!t) return null;
  return (
    <span ref={ref} className="relative inline-block align-middle">
      <button type="button" onClick={() => { setRight((ref.current?.getBoundingClientRect().left ?? 0) > window.innerWidth / 2); setOpen((o) => !o); }} aria-expanded={open} data-testid={`explain-${id}`}
        className="inline-flex items-center gap-1 rounded-md border border-teal-500/30 bg-teal-500/10 px-1.5 py-0.5 text-[11px] text-teal-200 hover:bg-teal-500/20">
        <HelpCircle size={11} />{label ?? `Explain ${t.title.split(' (')[0]}`}
      </button>
      {open && (
        <div role="dialog" aria-label={t.title}
          className={`absolute ${right ? 'right-0' : 'left-0'} top-full z-40 mt-2 w-[min(90vw,360px)] rounded-xl border border-slate-700 bg-[#0d1424] p-4 text-left shadow-2xl shadow-black/50`}>
          <div className="mb-2 flex items-start justify-between gap-2">
            <div><div className="text-sm font-semibold text-white">{t.title}</div><div className="text-xs text-slate-400">{t.short}</div></div>
            <button type="button" aria-label="Close" onClick={() => setOpen(false)} className="text-slate-500 hover:text-slate-200"><X size={14} /></button>
          </div>
          <TopicBody t={t} />
        </div>
      )}
    </span>
  );
}
