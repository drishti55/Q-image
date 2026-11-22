// Side-by-side comparison of every model on the 360-image locked test set: all V4 groups plus the V2 / V3
// reference models stored in v4_results.json. Every number comes from /api/v4/results; nothing is hard-coded.
import { useMemo, useState } from 'react';
import { ArrowDown, ArrowUp, ShieldCheck } from 'lucide-react';
import { useV4 } from '../api';
import { Card, Gate, PageHeader, CLASSES, CLASS_LABEL } from '../ui';
import AllModelsChart from '../AllModelsChart';
import FamilyCentre from '../learn/FamilyCentre';

type MS = { mean: number; std?: number; n?: number };
type Row = {
  key: string; name: string; version: string; type: 'quantum' | 'classical'; rep: string;
  qubits?: number | null; input: string; acc: MS; f1?: MS; valF1?: MS; seeds?: number[];
  cx?: number | null; depth?: number | null; perClass?: Record<string, MS>; headline?: boolean;
};
type SortKey = 'acc' | 'f1' | 'valF1' | 'qubits' | 'cx' | 'spread';

// Reference models carried in v4_results.json (earlier protocols, same test set).
const REF_META: Record<string, Omit<Row, 'key' | 'acc' | 'f1' | 'valF1'>> = {
  'E1b-frqi8-qkc-scaled': { name: 'FRQI, whole image', version: 'V2', type: 'quantum', rep: 'FRQI', qubits: 7, input: '8×8 image, one state' },
  'E2-neqr16-b4-qkc': { name: 'NEQR, whole image (4-bit)', version: 'V2', type: 'quantum', rep: 'NEQR', qubits: 12, input: '16×16 image, one state' },
  'V3-frqi8': { name: 'FRQI, whole image (re-tuned)', version: 'V3', type: 'quantum', rep: 'FRQI', qubits: 7, input: '8×8 image, one state' },
  'V3-neqr16': { name: 'NEQR, whole image (re-tuned)', version: 'V3', type: 'quantum', rep: 'NEQR', qubits: 12, input: '16×16 image, one state' },
  'V3-tex12c-rbfsvm': { name: 'RBF-SVM on texture features', version: 'V3', type: 'classical', rep: '—', input: 'LBP + GLCM, PCA-12' },
};

const p1 = (v?: number | null) => (v == null ? '—' : (100 * v).toFixed(1));
const spread = (s?: number[]) => (s && s.length ? Math.max(...s) - Math.min(...s) : undefined);
const C = { frqi: '#3a8ee6', neqr: '#d96a30', classical: '#8a939d' };
const colorOf = (r: Row) => (r.type === 'classical' ? C.classical : r.rep === 'NEQR' ? C.neqr : C.frqi);

function buildRows(d: any): Row[] {
  const H = d.headlines ?? {};
  const v4 = Object.entries(d.groups ?? {}).map(([g, r]: [string, any]) => {
    const q = r.quantum ?? {}, p = r.params ?? {}, c = r.circuit ?? {};
    const isQ = !!q.n_qubits;
    return {
      key: g, version: 'V4', type: isQ ? 'quantum' : 'classical', rep: q.representation ?? '—',
      name: isQ ? `${q.representation} patch ensemble (${p.patch}×${p.patch} patches)` : 'RBF-SVM on patch moments (matched control)',
      qubits: q.n_qubits ?? null,
      input: `${p.image_size}×${p.image_size}, ${p.patch}×${p.patch} patches stride ${p.stride}${p.norm === 'stretch' ? ', stretch' : ''}${p.bits ? `, ${p.bits}-bit` : ''}`,
      acc: r.test_accuracy, f1: r.test_f1_macro, valF1: r.val_f1_macro, seeds: r.per_seed_test_accuracy,
      cx: c.cx_compiled ?? null, depth: c.depth_compiled ?? null,
      perClass: Array.isArray(r.per_class_f1) ? undefined : r.per_class_f1,
      headline: g === H.frqi || g === H.neqr,
    } as Row;
  });
  const refs = Object.entries(d.references ?? {}).filter(([k]) => REF_META[k]).map(([k, r]: [string, any]) => ({
    key: k, ...REF_META[k], acc: r.test_accuracy, f1: r.test_f1_macro, valF1: r.val_f1_macro,
  } as Row));
  return [...v4, ...refs];
}

function sortVal(r: Row, k: SortKey): number {
  switch (k) {
    case 'acc': return r.acc?.mean ?? -1;
    case 'f1': return r.f1?.mean ?? -1;
    case 'valF1': return r.valF1?.mean ?? -1;
    case 'qubits': return r.qubits ?? -1;
    case 'cx': return r.cx ?? -1;
    case 'spread': return spread(r.seeds) ?? -1;
  }
}

export default function ModelCompare() {
  const st = useV4<any>('/results');
  const [sort, setSort] = useState<{ k: SortKey; desc: boolean }>({ k: 'acc', desc: true });
  const [filter, setFilter] = useState<'all' | 'V4' | 'quantum' | 'classical'>('all');

  return (
    <div className="space-y-5">
      <PageHeader title="Model comparison" subtitle="All models on the same 360 locked-test images." />
      <Card title="All 163 models at a glance" subtitle="V2, V3 and V4. Mean test accuracy over 3 seeds. Click a type to hide it.">
        <AllModelsChart />
      </Card>
      <Card title="Model families, side by side" subtitle="QKC · PQK · VQC · Hybrid · classical RBF-SVM — Protocol V3, same features and test images. Click a family.">
        <FamilyCentre />
      </Card>
      <Gate state={st}>{(d) => <Body d={d} sort={sort} setSort={setSort} filter={filter} setFilter={setFilter} />}</Gate>
    </div>
  );
}

function Body({ d, sort, setSort, filter, setFilter }: {
  d: any; sort: { k: SortKey; desc: boolean }; setSort: (s: { k: SortKey; desc: boolean }) => void;
  filter: 'all' | 'V4' | 'quantum' | 'classical'; setFilter: (f: 'all' | 'V4' | 'quantum' | 'classical') => void;
}) {
  const all = useMemo(() => buildRows(d), [d]);
  const rows = useMemo(() => {
    const f = all.filter((r) => filter === 'all' || (filter === 'V4' ? r.version === 'V4' : r.type === filter));
    return [...f].sort((a, b) => (sort.desc ? -1 : 1) * (sortVal(a, sort.k) - sortVal(b, sort.k)));
  }, [all, filter, sort]);
  const best = Math.max(...all.map((r) => r.acc?.mean ?? 0));
  const v4q = all.filter((r) => r.version === 'V4' && r.perClass);

  const Th = ({ k, children, title }: { k?: SortKey; children: string; title?: string }) => (
    <th className="whitespace-nowrap px-2 py-2 font-medium" title={title}>
      {k ? (
        <button type="button" onClick={() => setSort({ k, desc: sort.k === k ? !sort.desc : true })}
          className={`inline-flex items-center gap-1 hover:text-slate-200 ${sort.k === k ? 'text-cyan-300' : ''}`}>
          {children}{sort.k === k && (sort.desc ? <ArrowDown size={11} /> : <ArrowUp size={11} />)}
        </button>
      ) : children}
    </th>
  );

  return (<>
    <Card title="All models, one table"
      actions={
        <div className="flex gap-1 text-xs">
          {(['all', 'V4', 'quantum', 'classical'] as const).map((f) => (
            <button key={f} type="button" onClick={() => setFilter(f)}
              className={`rounded-md px-2 py-1 ring-1 ${filter === f ? 'bg-cyan-500/15 text-cyan-200 ring-cyan-500/40' : 'text-slate-400 ring-slate-700 hover:text-slate-200'}`}>
              {f === 'all' ? 'All' : f === 'V4' ? 'V4 only' : f[0].toUpperCase() + f.slice(1)}
            </button>))}
        </div>}>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[980px] text-xs tabular-nums" data-testid="model-compare-table">
          <thead className="text-left text-[11px] text-slate-500">
            <tr>
              <Th>Model</Th><Th>Ver.</Th><Th>Type</Th><Th>Input</Th>
              <Th k="qubits" title="Qubits per encoded state (per patch for V4)">Qubits</Th>
              <Th k="acc">Test acc. %</Th><Th k="f1">Test F1 %</Th><Th k="valF1">Val F1 %</Th>
              <Th k="spread" title="Best minus worst seed, test accuracy">Seed spread pp</Th>
              <Th k="cx" title="CNOTs in one compiled patch-state circuit">CX (compiled)</Th>
              <Th>Depth</Th>
              <th className="w-[14%] px-2" />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const top = r.acc?.mean === best;
              return (
                <tr key={r.key} className={`border-t border-slate-800/70 ${r.version === 'V4' ? 'bg-cyan-500/[0.04]' : ''}`}>
                  <td className="px-2 py-2">
                    <div className={`flex items-center gap-2 ${r.headline ? 'font-semibold text-white' : 'text-slate-200'}`}>
                      <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: colorOf(r) }} />
                      {r.name}
                      {r.headline && <span className="rounded bg-cyan-400 px-1.5 text-[10px] font-bold text-slate-950">headline</span>}
                      {top && <span className="rounded bg-emerald-500/20 px-1.5 text-[10px] text-emerald-200 ring-1 ring-emerald-500/40">best</span>}
                    </div>
                    <div className="pl-[18px] font-mono text-[10px] text-slate-500">{r.key}</div>
                  </td>
                  <td className="px-2">{r.version}</td>
                  <td className="px-2"><span className={`rounded-md px-1.5 py-0.5 text-[11px] ring-1 ${r.type === 'quantum' ? 'bg-cyan-500/10 text-cyan-200 ring-cyan-500/30' : 'bg-slate-500/10 text-slate-300 ring-slate-500/30'}`}>{r.type}</span></td>
                  <td className="px-2 text-slate-400">{r.input}</td>
                  <td className="px-2">{r.qubits ?? '—'}</td>
                  <td className="px-2 text-sm font-semibold text-white">{p1(r.acc?.mean)} <span className="text-[11px] font-normal text-slate-500">± {p1(r.acc?.std)}</span></td>
                  <td className="px-2">{p1(r.f1?.mean)} <span className="text-slate-500">± {p1(r.f1?.std)}</span></td>
                  <td className="px-2">{p1(r.valF1?.mean)}</td>
                  <td className={`px-2 ${(spread(r.seeds) ?? 0) > 0.1 ? 'text-amber-300' : ''}`}>{p1(spread(r.seeds))}</td>
                  <td className="px-2">{r.cx ?? '—'}</td>
                  <td className="px-2">{r.depth ?? '—'}</td>
                  <td className="px-2">
                    <div className="h-2 rounded-full bg-slate-800">
                      <div className="h-2 rounded-full" style={{ width: `${100 * (r.acc?.mean ?? 0)}%`, background: colorOf(r) }} />
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-3 flex items-start gap-2 text-[11px] text-amber-200/80">
        <ShieldCheck size={14} className="mt-0.5 shrink-0" />
        Exact noiseless CPU simulation. Settings were frozen on validation data, then tested once. Seed spread above 10 pp is highlighted
        (NEQR seed 1). V2/V3 rows have no stored per-seed or circuit numbers here. No quantum advantage is claimed.
      </p>
    </Card>

    {v4q.length > 0 && (
      <Card title="Per-class F1 (V4 models)" subtitle="Macro F1 per defect class on the locked test set, mean over 3 seeds. The best value in each column is bold.">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-xs tabular-nums" data-testid="model-compare-perclass">
            <thead className="text-left text-[11px] text-slate-500">
              <tr><th className="px-2 py-2 font-medium">Model</th>{CLASSES.map((c) => <th key={c} className="px-2 font-medium">{CLASS_LABEL[c] ?? c}</th>)}</tr>
            </thead>
            <tbody>
              {v4q.map((r) => (
                <tr key={r.key} className="border-t border-slate-800/70 text-slate-200">
                  <td className="px-2 py-1.5">
                    <span className="mr-2 inline-block h-2.5 w-2.5 rounded-sm align-middle" style={{ background: colorOf(r) }} />{r.name}
                  </td>
                  {CLASSES.map((c) => {
                    const v = r.perClass?.[c]?.mean;
                    const colBest = Math.max(...v4q.map((x) => x.perClass?.[c]?.mean ?? 0));
                    return <td key={c} className={`px-2 ${v === colBest ? 'font-bold text-white' : ''}`}>{p1(v)}</td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    )}
  </>);
}
