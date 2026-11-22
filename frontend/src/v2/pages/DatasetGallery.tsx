// Dataset gallery: every NEU-DET image of the frozen manifest (1,800), grouped by the six defect classes.
// Click any image to open it large; ← / → step through the current selection, Esc closes. Read-only (/api/v4/dataset).
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';
import { useV4 } from '../api';
import { CLASSES, CLASS_LABEL, Gate, PageHeader, Stat } from '../ui';

export type DatasetImage = {
  path: string; name: string; class: string; folder: 'train' | 'validation'; split_seed0: 'train' | 'val' | 'test' | null;
  index: number; block: number; sha256: string; width: number; height: number; frac_correct: number | null;
};
type DatasetResponse = { manifest_id: string; classes: string[]; n: number; split_id: string | null; n_models: number; images: DatasetImage[] };
type FolderFilter = 'all' | 'train' | 'validation';

export const imageUrl = (path: string) => `/api/v4/dataset/image?path=${encodeURIComponent(path)}`;

const CLASS_HINT: Record<string, string> = {
  crazing: 'A network of fine cracks',
  inclusion: 'Foreign particles pressed into the surface',
  patches: 'Large dark or light regions',
  pitted_surface: 'Small pits and holes',
  'rolled-in_scale': 'Oxide scale pressed in during rolling',
  scratches: 'Long straight lines',
};

const ROLE_LABEL: Record<string, string> = { train: 'Training', val: 'Validation', test: 'Locked test' };

/** Images shown for a class and folder filter, in manifest order. Exported for tests. */
export function filterImages(images: DatasetImage[], cls: string, folder: FolderFilter): DatasetImage[] {
  return images.filter((x) => (cls === 'all' || x.class === cls) && (folder === 'all' || x.folder === folder));
}

export default function DatasetGallery() {
  const st = useV4<DatasetResponse>('/dataset');
  const [cls, setCls] = useState<string>('all');
  const [folder, setFolder] = useState<FolderFilter>('all');
  const [open, setOpen] = useState<number | null>(null);

  const images = st.data?.images ?? [];
  const shown = useMemo(() => filterImages(images, cls, folder), [images, cls, folder]);
  const firstOf = useMemo(() => Object.fromEntries(CLASSES.map((c) => [c, images.find((x) => x.class === c)])), [images]);
  const countOf = (c: string, f: FolderFilter = 'all') => filterImages(images, c, f).length;

  const step = useCallback((d: number) => setOpen((i) => (i === null || !shown.length ? i : (i + d + shown.length) % shown.length)), [shown.length]);
  useEffect(() => {
    if (open === null) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') step(1);
      else if (e.key === 'ArrowLeft') step(-1);
      else if (e.key === 'Escape') setOpen(null);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, step]);
  useEffect(() => { setOpen(null); }, [cls, folder]);

  return (
    <div className="space-y-6">
      <PageHeader title="Dataset · NEU-DET"
        subtitle="All 1,800 hot-rolled steel surface images used in every experiment, grouped by the six defect classes. Click any image to see it large and step through the rest." />
      <Gate state={st}>{() => (<>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Stat label="Images" value={st.data?.n.toLocaleString('en-US')} hint="200 × 200 px, grayscale" />
          <Stat label="Defect classes" value={CLASSES.length} hint="300 images each (balanced)" />
          <Stat label="Training folder" value={countOf('all', 'train').toLocaleString('en-US')} hint="split into 1,080 train + 360 validation" />
          <Stat label="Locked test" value={countOf('all', 'validation')} hint="official validation folder, tested once" />
        </div>

        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6" role="group" aria-label="Defect classes">
          {CLASSES.map((c) => {
            const first = firstOf[c];
            const active = cls === c;
            return (
              <button key={c} type="button" onClick={() => setCls(active ? 'all' : c)} aria-pressed={active}
                className={`group overflow-hidden rounded-xl border text-left transition-colors ${active ? 'border-cyan-400/70 ring-1 ring-cyan-400/50 bg-cyan-500/5' : 'border-slate-800 bg-slate-950/50 hover:border-slate-600'}`}>
                {first && <img src={imageUrl(first.path)} alt={`${CLASS_LABEL[c]} example`} className="aspect-square w-full object-cover" loading="lazy" />}
                <div className="px-3 py-2">
                  <div className="text-sm font-semibold text-slate-100">{CLASS_LABEL[c]}</div>
                  <div className="text-[11px] text-slate-400">{CLASS_HINT[c]}</div>
                  <div className="mt-1 text-[11px] text-slate-500">{countOf(c)} images</div>
                </div>
              </button>
            );
          })}
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-2">
          {['all', ...CLASSES].map((c) => (
            <button key={c} type="button" onClick={() => setCls(c)} aria-pressed={cls === c}
              className={`rounded-full border px-3 py-1 text-xs ${cls === c ? 'border-cyan-400/60 bg-cyan-500/15 text-cyan-100' : 'border-slate-700 text-slate-300 hover:border-slate-500'}`}>
              {c === 'all' ? 'All classes' : CLASS_LABEL[c]}
            </button>
          ))}
          <span className="mx-1 h-5 w-px bg-slate-700" aria-hidden />
          {([['all', 'All folders'], ['train', 'Training folder'], ['validation', 'Locked test']] as [FolderFilter, string][]).map(([f, l]) => (
            <button key={f} type="button" onClick={() => setFolder(f)} aria-pressed={folder === f}
              className={`rounded-full border px-3 py-1 text-xs ${folder === f ? 'border-amber-400/60 bg-amber-500/15 text-amber-100' : 'border-slate-700 text-slate-300 hover:border-slate-500'}`}>
              {l}
            </button>
          ))}
          <span className="ml-auto text-xs text-slate-400" data-testid="dataset-count">Showing {shown.length.toLocaleString('en-US')} images</span>
        </div>

        <div className="mt-4 grid grid-cols-4 gap-2 sm:grid-cols-6 md:grid-cols-8 xl:grid-cols-10">
          {shown.map((x, i) => (
            <button key={x.path} type="button" onClick={() => setOpen(i)} title={`${x.name} · ${CLASS_LABEL[x.class]}`}
              className="group relative overflow-hidden rounded-lg border border-slate-800 bg-slate-950 hover:border-cyan-400/60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-400">
              <img src={imageUrl(x.path)} alt={`${CLASS_LABEL[x.class]} ${x.index}`} loading="lazy" className="aspect-square w-full object-cover transition-transform group-hover:scale-105" />
              {x.folder === 'validation' && <span className="absolute left-1 top-1 rounded bg-amber-500/90 px-1 text-[9px] font-semibold text-slate-950">TEST</span>}
              <span className="absolute inset-x-0 bottom-0 bg-black/60 px-1 py-0.5 text-[10px] text-slate-200 opacity-0 group-hover:opacity-100">{x.name.replace('.jpg', '')}</span>
            </button>
          ))}
        </div>

        {open !== null && shown[open] && (
          <Viewer img={shown[open]} pos={open} total={shown.length} nModels={st.data?.n_models ?? 0}
            onClose={() => setOpen(null)} onPrev={() => step(-1)} onNext={() => step(1)} />
        )}
      </>)}</Gate>
    </div>
  );
}

function Viewer({ img, pos, total, nModels, onClose, onPrev, onNext }: {
  img: DatasetImage; pos: number; total: number; nModels: number; onClose: () => void; onPrev: () => void; onNext: () => void;
}) {
  const rows: [string, string][] = [
    ['Class', CLASS_LABEL[img.class]],
    ['Folder', img.folder === 'train' ? 'Training folder' : 'Validation folder (locked test)'],
    ['Role in split (seed 0)', img.split_seed0 ? ROLE_LABEL[img.split_seed0] : 'unavailable'],
    ['File index · block', `${img.index} · block ${img.block}`],
    ['Size', `${img.width} × ${img.height} px`],
    ['SHA-256', `${img.sha256.slice(0, 16)}…`],
  ];
  return (
    <div role="dialog" aria-modal="true" aria-label={`Image ${img.name}`} className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4" onClick={onClose}>
      <div className="relative flex w-full max-w-5xl flex-col gap-4 rounded-2xl border border-slate-700 bg-[#0b1222] p-4 md:flex-row" onClick={(e) => e.stopPropagation()}>
        <button type="button" aria-label="Close" onClick={onClose} className="absolute right-3 top-3 rounded-full p-1.5 text-slate-300 hover:bg-slate-800"><X size={18} /></button>
        <div className="relative flex flex-1 items-center justify-center">
          <button type="button" aria-label="Previous image" onClick={onPrev} className="absolute left-0 z-10 rounded-full bg-slate-900/80 p-2 text-slate-100 hover:bg-slate-700"><ChevronLeft size={22} /></button>
          <img src={imageUrl(img.path)} alt={`${CLASS_LABEL[img.class]} ${img.index}`} className="max-h-[70vh] w-full max-w-[560px] rounded-lg object-contain" />
          <button type="button" aria-label="Next image" onClick={onNext} className="absolute right-0 z-10 rounded-full bg-slate-900/80 p-2 text-slate-100 hover:bg-slate-700"><ChevronRight size={22} /></button>
        </div>
        <div className="w-full shrink-0 md:w-72">
          <div className="text-xs text-slate-500">Image {pos + 1} of {total.toLocaleString('en-US')} in this view</div>
          <h2 className="mt-1 text-lg font-semibold text-slate-50">{img.name}</h2>
          <dl className="mt-3 space-y-2 text-sm">
            {rows.map(([k, v]) => (
              <div key={k} className="flex justify-between gap-3 border-b border-slate-800 pb-1.5">
                <dt className="text-slate-400">{k}</dt><dd className="text-right text-slate-100">{v}</dd>
              </div>
            ))}
          </dl>
          {img.frac_correct !== null && (
            <div className="mt-4 rounded-lg border border-slate-700 bg-slate-950/60 p-3 text-sm">
              <div className="text-slate-400">Classified correctly by</div>
              <div className="text-2xl font-semibold text-cyan-200">{Math.round(100 * img.frac_correct)}%</div>
              <div className="text-xs text-slate-500">of {nModels} selected models × 3 seeds (V2–V4)</div>
            </div>
          )}
          <p className="mt-4 text-xs text-slate-500">Use ← and → to move, Esc to close.</p>
        </div>
      </div>
    </div>
  );
}
