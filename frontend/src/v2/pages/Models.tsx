import { Fragment, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ChevronDown, ChevronRight, X } from 'lucide-react';
import { useV2 } from '../api';
import type { Model, ModelsResponse } from '../api';
import { FamilyBestChart, ModelStripChart } from '../charts';
import { AccBar, FAMILY, FamilyChip, familyOfModel } from '../theme';
import type { FamilyKey } from '../theme';
import { Badge, CATEGORY_TONE, Card, ExecBadge, Gate, PageHeader, Select, UNAVAILABLE, chartTheme, int, msDur, msNum, msPct, num, pct , fmt } from '../ui';

type SortKey = 'accuracy' | 'f1' | 'name' | 'qubits';

export function filterModels(models: Model[], f: { q: string; category: string; qubits: string; source: string; encoding: string; exec: string }) {
  const q = f.q.trim().toLowerCase();
  return models.filter((m) =>
    (!q || `${m.display_name} ${m.group} ${m.model_name}`.toLowerCase().includes(q)) &&
    (f.category === 'all' || m.category === f.category) &&
    (f.qubits === 'all' || String(m.n_qubits ?? 'none') === f.qubits) &&
    (f.source === 'all' || m.feature_source === f.source) &&
    (f.encoding === 'all' || m.encoding === f.encoding) &&
    (f.exec === 'all' || (f.exec === 'exact' ? m.execution.startsWith('exact') : f.exec === 'shots' ? m.execution.startsWith('finite') : m.execution === 'classical')));
}

export function sortModels(models: Model[], key: SortKey, desc: boolean) {
  const v = (m: Model) => key === 'accuracy' ? m.test_accuracy.mean ?? -1 : key === 'f1' ? m.test_f1_macro.mean ?? -1
    : key === 'qubits' ? m.n_qubits ?? -1 : m.display_name;
  return [...models].sort((a, b) => {
    const x = v(a), y = v(b);
    const c = typeof x === 'string' ? x.localeCompare(y as string) : (x as number) - (y as number);
    return desc ? -c : c;
  });
}

function SeedTable({ m }: { m: Model }) {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <div className="lg:col-span-2 overflow-x-auto">
        <table className="w-full text-xs tabular-nums">
          <thead className="text-left text-slate-500">
            <tr><th className="py-1">Seed</th><th>Experiment</th><th>Val macro-F1</th><th>Test acc.</th><th>95% CI (acc.)</th><th>Test macro-F1</th><th>Precision</th><th>Recall</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {m.per_seed.map((s) => (
              <tr key={s.experiment_id}>
                <td className="py-1.5">{s.seed}</td>
                <td><Link className="text-cyan-300 hover:underline" to={`/experiments/${encodeURIComponent(s.experiment_id)}`}>{s.experiment_id.split('__').slice(1).join('__')}</Link></td>
                <td>{num(s.val?.f1_macro)}</td>
                <td>{pct(s.test?.accuracy)}</td>
                <td>{s.test_ci ? `${pct(s.test_ci.accuracy[0])} – ${pct(s.test_ci.accuracy[1])}` : UNAVAILABLE}</td>
                <td>{num(s.test?.f1_macro)}</td>
                <td>{num(s.test?.precision_macro)}</td>
                <td>{num(s.test?.recall_macro)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-xs">
        <dt className="text-slate-500">Feature source</dt><dd className="text-slate-200">{m.feature_source}</dd>
        <dt className="text-slate-500">Encoding</dt><dd className="text-slate-200">{m.encoding}</dd>
        <dt className="text-slate-500">Selected params</dt><dd className="text-slate-200 break-all">{JSON.stringify(m.params)}</dd>
        <dt className="text-slate-500">Candidates searched</dt><dd className="text-slate-200">{m.n_candidates ?? UNAVAILABLE}</dd>
        <dt className="text-slate-500">Train time (mean)</dt><dd className="text-slate-200">{msDur(m.train_time_s)}</dd>
        <dt className="text-slate-500">Inference</dt><dd className="text-slate-200">{msNum(m.test_inference_ms_per_image, 3)} ms/img</dd>
        {m.circuit && <><dt className="text-slate-500">Circuit (compiled)</dt><dd className="text-slate-200">{int(m.circuit.gates_compiled)} gates · depth {int(m.circuit.depth_compiled)} · {int(m.circuit.cx_compiled)} CX</dd></>}
        <dt className="text-slate-500">Group id</dt><dd className="font-mono text-[11px] text-slate-400">{m.group}</dd>
      </dl>
    </div>
  );
}

function CompareView({ models, onRemove }: { models: Model[]; onRemove: (g: string) => void }) {
  const metrics: [string, (m: Model) => number | null][] = [
    ['Accuracy', (m) => m.test_accuracy.mean], ['Macro precision', (m) => m.test_precision_macro.mean],
    ['Macro recall', (m) => m.test_recall_macro.mean], ['Macro-F1', (m) => m.test_f1_macro.mean], ['Weighted F1', (m) => m.test_f1_weighted.mean],
  ];
  const data = metrics.map(([name, f]) => Object.fromEntries([['metric', name], ...models.map((m) => [m.group, f(m)])]));
  const colors = ['#22d3ee', '#a78bfa', '#34d399', '#fbbf24'];
  return (
    <Card title={`Side-by-side comparison (${models.length})`} subtitle="Locked-test metrics, mean over seeds. Only metrics present in the saved records are shown.">
      <div className="grid gap-4 xl:grid-cols-2">
        <div className="overflow-x-auto">
          <table className="w-full text-xs tabular-nums">
            <thead><tr><th className="text-left text-slate-500 py-1">Metric</th>{models.map((m, i) => (
              <th key={m.group} className="text-left py-1 pr-2">
                <div className="flex items-start gap-1"><span className="mt-1 h-2 w-2 rounded-full shrink-0" style={{ background: colors[i] }} />
                  <span className="text-slate-100 font-medium">{m.display_name}</span>
                  <button aria-label={`Remove ${m.display_name}`} onClick={() => onRemove(m.group)} className="text-slate-500 hover:text-slate-200"><X size={12} /></button></div>
              </th>))}</tr></thead>
            <tbody className="divide-y divide-slate-800/60">
              {[['Category', (m: Model) => m.category], ['Execution', (m: Model) => m.execution], ['Qubits', (m: Model) => String(m.n_qubits ?? '—')],
                ['Test accuracy', (m: Model) => msPct(m.test_accuracy)], ['Macro-F1', (m: Model) => msNum(m.test_f1_macro)],
                ['Precision', (m: Model) => msNum(m.test_precision_macro)], ['Recall', (m: Model) => msNum(m.test_recall_macro)],
                ['Val macro-F1', (m: Model) => msNum(m.val_f1_macro)], ['Compiled gates / depth', (m: Model) => m.circuit ? `${int(m.circuit.gates_compiled)} / ${int(m.circuit.depth_compiled)}` : '—'],
                ['Train time', (m: Model) => msDur(m.train_time_s)]].map(([lbl, f]) => (
                <tr key={lbl as string}><td className="py-1.5 text-slate-500">{lbl as string}</td>{models.map((m) => <td key={m.group} className="pr-2 text-slate-200">{(f as (m: Model) => string)(m)}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="h-72">
          <ResponsiveContainer>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} vertical={false} />
              <XAxis dataKey="metric" tick={{ fontSize: 11, fill: chartTheme.axis }} />
              <YAxis domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} tick={{ fontSize: 11, fill: chartTheme.axis }} />
              <Tooltip contentStyle={chartTheme.tooltip} formatter={fmt((v) => pct(v))} />
              <Legend wrapperStyle={{ fontSize: 11 }} formatter={(g) => models.find((m) => m.group === g)?.display_name ?? g} />
              {models.map((m, i) => <Bar key={m.group} dataKey={m.group} fill={colors[i]} radius={[3, 3, 0, 0]} />)}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </Card>
  );
}


function Leaderboard({ models, onAdvanced }: { models: Model[]; onAdvanced: () => void }) {
  const [fam, setFam] = useState<FamilyKey | 'all'>('all');
  const [variants, setVariants] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const isVariant = (m: Model) => m.shots > 0 || m.is_ablation || m.is_legacy_relabelled;
  const pool = models.filter((m) => (fam === 'all' || familyOfModel(m) === fam) && (variants || !isVariant(m)))
    .sort((a, b) => (b.test_accuracy.mean ?? 0) - (a.test_accuracy.mean ?? 0));
  const hidden = models.filter((m) => (fam === 'all' || familyOfModel(m) === fam) && isVariant(m)).length;
  const rows = showAll ? pool : pool.slice(0, 12);
  const top = pool[0]?.test_accuracy.mean ?? 1;
  return (
    <div className="space-y-4">
      <div className="grid gap-5 xl:grid-cols-2"><FamilyBestChart models={models} /><ModelStripChart models={models} /></div>
      <div className="flex flex-wrap items-center gap-2">
        <button onClick={() => setFam('all')} className={`rounded-full px-3 py-1 text-xs font-medium ring-1 ${fam === 'all' ? 'bg-white/10 text-white ring-white/30' : 'text-slate-400 ring-slate-700 hover:text-slate-200'}`}>All families</button>
        {(Object.keys(FAMILY) as FamilyKey[]).map((k) => (
          <button key={k} onClick={() => setFam(k)} aria-pressed={fam === k}
            className={`rounded-full px-3 py-1 text-xs font-medium ring-1 transition`}
            style={fam === k ? { background: FAMILY[k].soft, color: FAMILY[k].color, boxShadow: `inset 0 0 0 1px ${FAMILY[k].color}` } : { color: '#94a3b8', boxShadow: 'inset 0 0 0 1px #334155' }}>
            {FAMILY[k].short}
          </button>
        ))}
        <label className="ml-auto flex items-center gap-2 text-xs text-slate-400">
          <input type="checkbox" checked={variants} onChange={(e) => setVariants(e.target.checked)} />
          include shot-noise, ablation & legacy variants ({hidden})
        </label>
      </div>
      <ol className="space-y-2">
        {rows.map((m, i) => {
          const f = FAMILY[familyOfModel(m)];
          return (
            <li key={m.group}>
              <Link to={`/classification?model=${encodeURIComponent(m.group)}`}
                className="grid grid-cols-[2rem_minmax(0,1fr)] items-center gap-3 rounded-xl bg-slate-900/40 px-4 py-3 ring-1 ring-slate-800 transition hover:ring-cyan-500/40 md:grid-cols-[2rem_minmax(0,1fr)_minmax(220px,340px)]">
                <span className="text-sm font-semibold tabular-nums text-slate-500">{i + 1}</span>
                <span className="min-w-0">
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-slate-100">{m.display_name}</span>
                    <FamilyChip fam={familyOfModel(m)} />
                    {m.shots > 0 && <Badge tone="amber">{m.shots} shots</Badge>}
                  </span>
                  <span className="block truncate text-xs text-slate-500">{m.feature_source}{m.n_qubits ? ` · ${m.n_qubits} qubits` : ''}</span>
                </span>
                <span className="col-span-2 md:col-span-1"><AccBar value={m.test_accuracy.mean} color={f.color} max={Math.max(top, 1e-9)} label={pct(m.test_accuracy.mean)} /></span>
              </Link>
            </li>
          );
        })}
      </ol>
      <div className="flex flex-wrap items-center gap-3">
        {pool.length > 12 && <button onClick={() => setShowAll(!showAll)} className="rounded-lg px-3 py-1.5 text-xs text-slate-200 ring-1 ring-slate-700 hover:bg-slate-800">{showAll ? 'Show top 12' : `Show all ${pool.length}`}</button>}
        <button onClick={onAdvanced} className="rounded-lg px-3 py-1.5 text-xs text-cyan-300 ring-1 ring-cyan-500/30 hover:bg-cyan-500/10">Advanced: filters, every metric, side-by-side compare →</button>
        <span className="text-xs text-slate-500">Bars are relative to the best model shown. Accuracy on 360 locked test images, mean of 3 seeds. Click a model for its details.</span>
      </div>
    </div>
  );
}

export default function ModelsPage() {
  const state = useV2<ModelsResponse>('/models');
  const [params, setParams] = useSearchParams();
  const focus = params.get('focus');
  const [q, setQ] = useState('');
  const [category, setCategory] = useState(params.get('category') ?? 'all');
  const [qubits, setQubits] = useState('all');
  const [source, setSource] = useState('all');
  const [encoding, setEncoding] = useState('all');
  const [exec, setExec] = useState('all');
  const [sort, setSort] = useState<SortKey>('accuracy');
  const [desc, setDesc] = useState(true);
  const [open, setOpen] = useState<Set<string>>(new Set(focus ? [focus] : []));
  const [cmp, setCmp] = useState<string[]>([]);
  const [advanced, setAdvanced] = useState(!!focus || params.get('view') === 'advanced');

  useEffect(() => {
    if (focus && state.data) document.getElementById(`row-${focus}`)?.scrollIntoView({ block: 'center' });
  }, [focus, state.data]);

  const all = state.data?.models ?? [];
  const shown = useMemo(() => sortModels(filterModels(all, { q, category, qubits, source, encoding, exec }), sort, desc), [all, q, category, qubits, source, encoding, exec, sort, desc]);
  const uniq = (f: (m: Model) => string) => [...new Set(all.map(f))].sort((a, b) => (Number(a) - Number(b)) || a.localeCompare(b));
  const toggle = (g: string) => setOpen((s) => { const n = new Set(s); if (n.has(g)) n.delete(g); else n.add(g); return n; });
  const toggleCmp = (g: string) => setCmp((c) => c.includes(g) ? c.filter((x) => x !== g) : c.length >= 4 ? c : [...c, g]);
  const setSortKey = (k: SortKey) => { if (k === sort) setDesc(!desc); else { setSort(k); setDesc(k !== 'name'); } };
  const reset = () => { setQ(''); setCategory('all'); setQubits('all'); setSource('all'); setEncoding('all'); setExec('all'); setParams({}); };

  return (
    <div className="space-y-5">
      <PageHeader title="Model Comparison"
        subtitle={advanced ? 'All selected configurations with every metric. Each was chosen on validation data and evaluated once per seed (0, 1, 2) on the 360 locked test images; mean ± std over seeds.'
          : 'Every model ranked by accuracy on images it never saw during development. Start with the main models; switch on variants or the advanced view for detail.'}>
        <div className="inline-flex rounded-lg bg-slate-900 p-1 ring-1 ring-slate-800">
          {([['Leaderboard', false], ['Advanced', true]] as const).map(([l, v]) => (
            <button key={l} onClick={() => setAdvanced(v)} aria-pressed={advanced === v}
              className={`rounded-md px-3 py-1.5 text-xs font-medium ${advanced === v ? 'bg-cyan-500/15 text-cyan-200' : 'text-slate-400 hover:text-slate-200'}`}>{l}</button>
          ))}
        </div>
      </PageHeader>
      <Gate state={state} empty={(d) => !d.count}>
        {(d) => !advanced ? <Leaderboard models={d.models} onAdvanced={() => setAdvanced(true)} /> : (
          <>
            <Card>
              <div className="flex flex-wrap items-end gap-3">
                <label className="flex flex-col gap-1 text-[11px] text-slate-400 grow min-w-[220px]">
                  Search
                  <input aria-label="Search models" value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. ZZ-full, NEQR, MobileNet…"
                    className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-100 focus:border-cyan-500 focus:outline-none" />
                </label>
                <Select label="Model family" value={category} onChange={setCategory} options={d.categories} />
                <Select label="Qubits" value={qubits} onChange={setQubits} options={uniq((m) => String(m.n_qubits ?? 'none')).map((v) => [v, v === 'none' ? 'no circuit' : v] as [string, string])} />
                <Select label="Feature representation" value={source} onChange={setSource} options={uniq((m) => m.feature_source)} />
                <Select label="Encoding" value={encoding} onChange={setEncoding} options={uniq((m) => m.encoding)} />
                <Select label="Execution" value={exec} onChange={setExec} options={[['exact', 'Exact statevector'], ['shots', 'Finite shots'], ['classical', 'Classical']]} />
                <button onClick={reset} className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800">Reset</button>
              </div>
              <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-400">
                <span>Showing <b className="text-slate-200">{shown.length}</b> of {d.count} configurations.</span>
                {d.categories.map((c) => <Badge key={c} tone={CATEGORY_TONE[c]}>{c}: {all.filter((m) => m.category === c).length}</Badge>)}
              </div>
            </Card>

            {cmp.length > 0 && <CompareView models={cmp.map((g) => all.find((m) => m.group === g)!).filter(Boolean)} onRemove={toggleCmp} />}

            <Card>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-[11px] uppercase tracking-wider text-slate-500">
                    <tr>
                      <th className="w-8 pb-2" title="Compare (max 4)">Cmp</th>
                      <th className="pb-2 cursor-pointer" onClick={() => setSortKey('name')}>Model {sort === 'name' ? (desc ? '↓' : '↑') : ''}</th>
                      <th className="pb-2">Category</th>
                      <th className="pb-2 cursor-pointer" onClick={() => setSortKey('qubits')}>Qubits {sort === 'qubits' ? (desc ? '↓' : '↑') : ''}</th>
                      <th className="pb-2">Execution</th>
                      <th className="pb-2 text-right cursor-pointer" onClick={() => setSortKey('accuracy')}>Test accuracy {sort === 'accuracy' ? (desc ? '↓' : '↑') : ''}</th>
                      <th className="pb-2 text-right cursor-pointer" onClick={() => setSortKey('f1')}>Macro-F1 {sort === 'f1' ? (desc ? '↓' : '↑') : ''}</th>
                      <th className="pb-2 text-right">Precision</th>
                      <th className="pb-2 text-right">Recall</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/70">
                    {shown.map((m) => (
                      <Fragment key={m.group}>
                        <tr id={`row-${m.group}`} className={`hover:bg-slate-800/30 ${focus === m.group ? 'bg-cyan-500/[0.07]' : ''}`}>
                          <td className="py-2"><input type="checkbox" aria-label={`Compare ${m.display_name}`} checked={cmp.includes(m.group)}
                            disabled={!cmp.includes(m.group) && cmp.length >= 4} onChange={() => toggleCmp(m.group)} /></td>
                          <td className="py-2 pr-3">
                            <button onClick={() => toggle(m.group)} className="flex items-start gap-1.5 text-left text-slate-100 hover:text-cyan-200">
                              {open.has(m.group) ? <ChevronDown size={14} className="mt-1 shrink-0" /> : <ChevronRight size={14} className="mt-1 shrink-0" />}
                              <span>{m.display_name}{m.is_legacy_relabelled && <Badge tone="amber">legacy · classical</Badge>}{m.is_ablation && <Badge tone="rose">ablation</Badge>}</span>
                            </button>
                            <div className="pl-5 text-[11px] text-slate-500">{m.feature_source}</div>
                          </td>
                          <td className="py-2 pr-2"><Badge tone={CATEGORY_TONE[m.category]}>{m.category}</Badge></td>
                          <td className="py-2 tabular-nums">{m.n_qubits ?? '—'}</td>
                          <td className="py-2"><ExecBadge execution={m.execution} /></td>
                          <td className="py-2 text-right tabular-nums text-slate-100">{msPct(m.test_accuracy)}</td>
                          <td className="py-2 text-right tabular-nums">{msNum(m.test_f1_macro)}</td>
                          <td className="py-2 text-right tabular-nums text-slate-400">{num(m.test_precision_macro.mean)}</td>
                          <td className="py-2 text-right tabular-nums text-slate-400">{num(m.test_recall_macro.mean)}</td>
                        </tr>
                        {open.has(m.group) && (
                          <tr><td colSpan={9} className="bg-slate-950/50 px-4 py-4"><SeedTable m={m} /></td></tr>
                        )}
                      </Fragment>
                    ))}
                  </tbody>
                </table>
                {!shown.length && <div className="p-6 text-center text-sm text-slate-400">No configurations match these filters.</div>}
              </div>
              <p className="mt-3 text-[11px] text-slate-500">Recall equals accuracy because the locked test set is balanced (60 images per class). Finite-shot rows re-evaluate the statevector-selected configuration with sampled kernel estimates.</p>
            </Card>
          </>
        )}
      </Gate>
    </div>
  );
}
