import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { BrowserRouter, Link, Navigate, NavLink, Route, Routes, useLocation, useParams } from 'react-router-dom';
import {
  Activity, Atom, BarChart3, ChevronRight, Cpu, FlaskConical, History,
  Clapperboard, Layers, Menu, Microscope, Presentation, Scale, Sparkles, Table2, TrendingUp, Trophy, Wand2, X, ImageUp,
  BookOpen, Network, ChevronDown, GraduationCap, Images,
} from 'lucide-react';

import ExperimentsPage from './v2/pages/Experiments';
import ModelsPage from './v2/pages/Models';
import EncodingPage from './v2/pages/Encoding';
import CircuitsPage from './v2/pages/Circuits';
import ClassificationPage from './v2/pages/Classification';
import ExperimentDetail from './v2/pages/ExperimentDetail';
import HistoricalHome from './v2/pages/HistoricalHome';
import Present from './v2/pages/Present';
import Playground from './v2/pages/Playground';
import QuantumVsClassical from './v2/pages/QuantumVsClassical';
import V3Results from './v2/pages/V3Results';
import V4Results from './v2/pages/V4Results';
import AllVersions from './v2/pages/AllVersions';
import ModelCompare from './v2/pages/ModelCompare';
import UploadLab from './v2/pages/UploadLab';
import HowItWorks from './v2/pages/HowItWorks';
import ReconstructionFull from './v2/pages/ReconstructionFull';
import Learn from './v2/pages/Learn';
import CnnStudio from './v2/pages/CnnStudio';
import QuizPage from './v2/pages/QuizPage';
import DatasetGallery from './v2/pages/DatasetGallery';
import { LevelProvider, LevelSwitch } from './v2/level';
import { getJSON } from './v2/api';

// Historical Protocol V0 pages (unchanged implementations, read-only)
import Dashboard from './pages/Dashboard';
import DatasetExplorer from './pages/DatasetExplorer';
import MLAnalytics from './pages/MLAnalytics';
import QuantumLab from './pages/QuantumLab';
import ExperimentsV0 from './pages/Experiments';
import ConfusionMatrixV0 from './pages/ConfusionMatrix';
import { Comparison } from './pages/Comparison';
import QuantumCompareLab from './pages/QuantumCompareLab';
import QuantumMLLab from './pages/QuantumMLLab';

type NavItem = { to: string; label: string; icon: typeof Activity; end?: boolean };

type NavGroup = { id: 'start' | 'results' | 'learn' | 'images' | 'project'; title: string; items: NavItem[] };

// Pages grouped by what they are for. Every route is unchanged; only the sidebar grouping moved.
const NAV_GROUPS: NavGroup[] = [
  { id: 'start', title: 'Start here', items: [
    { to: '/', label: 'Overview · all versions', icon: Trophy, end: true },
    { to: '/present', label: 'Presentation mode (V4)', icon: Presentation },
  ] },
  { id: 'results', title: 'Results', items: [
    { to: '/quantum-v4', label: 'V4 results (FRQI / NEQR)', icon: Sparkles },
    { to: '/compare', label: 'Model comparison table (V4)', icon: Table2 },
    { to: '/models', label: 'Model comparison (V2, all 88)', icon: Table2 },
    { to: '/quantum-vs-classical', label: 'Quantum vs Classical', icon: Scale },
    { to: '/classification', label: 'Classification analysis', icon: BarChart3 },
    { to: '/quantum-v3', label: 'V3 results (texture features)', icon: TrendingUp },
    { to: '/experiments-v2', label: 'Experiment log', icon: FlaskConical },
  ] },
  { id: 'learn', title: 'Learn & explore', items: [
    { to: '/learn', label: 'Concepts & pipeline', icon: BookOpen },
    { to: '/how-it-works', label: 'How it works (live)', icon: Clapperboard },
    { to: '/playground', label: '3×3 Algorithm Playground', icon: Wand2 },
    { to: '/cnn', label: 'CNN feature studio', icon: Network },
    { to: '/encoding', label: 'Quantum image encoding', icon: Atom },
    { to: '/circuits', label: 'Quantum circuits', icon: Cpu },
    { to: '/quiz', label: 'Knowledge check (quiz)', icon: GraduationCap },
  ] },
  { id: 'images', title: 'Images', items: [
    { to: '/dataset', label: 'Dataset (all 1,800 images)', icon: Images },
    { to: '/upload', label: 'Upload your image', icon: ImageUp },
    { to: '/reconstruction-full', label: 'Reconstruction (all 1,800)', icon: Layers },
  ] },
  { id: 'project', title: 'Archive', items: [
    { to: '/historical-v0', label: 'Historical results (V0)', icon: History },
  ] },
];

const TITLES: [RegExp, string, string][] = [
  [/^\/$/, 'Results — all versions', 'Protocol V4 · latest'],
  [/^\/present/, 'Presentation', 'Protocol V4'],
  [/^\/playground/, '3×3 Algorithm Playground', 'Illustrative demo · V3'],
  [/^\/quantum-vs-classical/, 'Quantum vs Classical', 'Protocol V2'],
  [/^\/quantum-v3/, 'Quantum Improvement', 'Protocol V3'],
  [/^\/quantum-v4/, 'FRQI / NEQR Improvement', 'Protocol V4'],
  [/^\/learn/, 'Concepts & pipeline', 'Learn'],
  [/^\/cnn/, 'CNN feature studio', 'Protocol V2 hybrids · live'],
  [/^\/quiz/, 'Knowledge check', 'Learn'],
  [/^\/compare/, 'Model comparison', 'V2 · V3 · V4 · same test set'],
  [/^\/how-it-works/, 'How it works (live)', 'Protocol V4 · real image'],
  [/^\/upload/, 'Upload your image', 'Protocol V4 · FRQI & NEQR'],
  [/^\/dataset/, 'Dataset · NEU-DET', 'Protocol V4 · all 1,800 images'],
  [/^\/reconstruction-full/, 'Reconstruction — all images', 'Protocol V4 study'],
  [/^\/experiments-v2/, 'Experiment log', 'Protocol V2'],
  [/^\/experiments\//, 'Experiment Details', 'Protocol V2'],
  [/^\/models/, 'Model Comparison', 'Protocol V2'],
  [/^\/encoding/, 'Quantum Image Encoding', 'Protocol V2'],
  [/^\/circuits/, 'Quantum Circuits', 'Protocol V2'],
  [/^\/reconstruction/, 'Reconstruction Studio', 'Protocol V2'],
  [/^\/classification/, 'Classification Analysis', 'Protocol V2'],
  [/^\/historical-v0\/?$/, 'Historical Results', 'Protocol V0 · read-only'],
  [/^\/historical-v0\//, 'Historical page', 'Protocol V0 · read-only'],
];

function titleFor(path: string): [string, string] {
  const hit = TITLES.find(([re]) => re.test(path));
  return hit ? [hit[1], hit[2]] : ['Not found', ''];
}

type Health = { state: 'checking' | 'ok' | 'stale' | 'offline'; detail?: string; n_selected?: number; version?: string };

function useV2Health(): Health {
  const [h, setH] = useState<Health>({ state: 'checking' });
  useEffect(() => {
    getJSON<{ api_version: string; n_selected: number; analysis_present: boolean }>('/health')
      .then((d) => setH({ state: d.analysis_present ? 'ok' : 'stale', version: d.api_version, n_selected: d.n_selected,
        detail: d.analysis_present ? undefined : 'results/qml_v2/aggregates/analysis.json missing' }))
      .catch((e) => setH({ state: String(e?.message ?? e).startsWith('404') ? 'stale' : 'offline', detail: String(e?.message ?? e) }));
  }, []);
  return h;
}

function SideLink({ item, onClick }: { item: NavItem; onClick?: () => void }) {
  const Icon = item.icon;
  return (
    <NavLink to={item.to} end={item.end} onClick={onClick}
      className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2 text-[13px] transition-colors ${
        isActive ? 'bg-cyan-500/10 text-cyan-200 ring-1 ring-cyan-500/30' : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-100'}`}>
      <Icon size={16} className="shrink-0" />
      <span className="truncate">{item.label}</span>
    </NavLink>
  );
}

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const [collapsed, setCollapsed] = useState<string[]>(() => {
    try { return JSON.parse(window.localStorage.getItem('qil-nav-collapsed') ?? '[]'); } catch { return []; }
  });
  const toggle = (id: string) => setCollapsed((c) => {
    const n = c.includes(id) ? c.filter((x) => x !== id) : [...c, id];
    try { window.localStorage.setItem('qil-nav-collapsed', JSON.stringify(n)); } catch { /* ignore */ }
    return n;
  });
  return (
    <nav aria-label="Main navigation" className="flex h-full flex-col">
      <Link to="/" onClick={onNavigate} className="flex items-center gap-3 px-5 h-16 border-b border-slate-800/80">
        <div className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/20">
          <Microscope size={18} className="text-white" />
        </div>
        <div>
          <div className="text-sm font-semibold text-white">Q-ImageLab</div>
          <div className="text-[11px] text-cyan-300/80">Protocol V4 · NEU-DET</div>
        </div>
      </Link>
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-5">
        {NAV_GROUPS.map((g) => {
          const id = g.id;
          const open = !collapsed.includes(id);
          return (
            <div key={id} data-testid={`nav-${id}`}>
              <button type="button" onClick={() => toggle(id)} aria-expanded={open}
                className="flex w-full items-center justify-between px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500 hover:text-slate-300">
                {g.title}<ChevronDown size={12} className={`transition-transform ${open ? '' : '-rotate-90'}`} />
              </button>
              {open && <div className="space-y-0.5">{g.items.map((i) => <SideLink key={i.to} item={i} onClick={onNavigate} />)}</div>}
            </div>);
        })}
      </div>
    </nav>
  );
}

function HealthPill({ h }: { h: Health }) {
  const map = {
    checking: ['bg-slate-800 text-slate-300 border-slate-700', 'Checking V2 API…'],
    ok: ['bg-emerald-500/10 text-emerald-300 border-emerald-500/30', `V2 API online · ${h.n_selected ?? '?'} selected models`],
    stale: ['bg-amber-500/10 text-amber-300 border-amber-500/30', 'V2 API unavailable'],
    offline: ['bg-rose-500/10 text-rose-300 border-rose-500/30', 'Backend offline'],
  } as const;
  const [cls, text] = map[h.state];
  return <span className={`rounded-full border px-3 py-1 text-xs ${cls}`}>{text}</span>;
}

function Shell({ children }: { children: ReactNode }) {
  const loc = useLocation();
  const [open, setOpen] = useState(false);
  const health = useV2Health();
  const [title, section] = titleFor(loc.pathname);
  const historical = loc.pathname.startsWith('/historical-v0');
  useEffect(() => {
    document.title = `${title} · Q-ImageLab ${historical ? '(V0 historical)' : (section.match(/V\d/)?.[0] ?? 'V2')}`;
  }, [title, historical, section]);
  if (loc.pathname.startsWith('/present')) return <>{children}</>;
  return (
    <div className="min-h-screen bg-[#070b16] text-slate-200">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-slate-800/80 bg-[#0a0f1e] lg:block">
        <Sidebar />
      </aside>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-72 border-r border-slate-800 bg-[#0a0f1e]">
            <button aria-label="Close navigation" className="absolute right-3 top-4 p-1 text-slate-400" onClick={() => setOpen(false)}><X size={18} /></button>
            <Sidebar onNavigate={() => setOpen(false)} />
          </aside>
        </div>
      )}
      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-3 border-b border-slate-800/80 bg-[#070b16]/90 px-4 backdrop-blur md:px-8">
          <div className="flex items-center gap-3 min-w-0">
            <button aria-label="Open navigation" className="p-1.5 text-slate-300 lg:hidden" onClick={() => setOpen(true)}><Menu size={20} /></button>
            <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-sm min-w-0">
              <Link to={historical ? '/historical-v0' : '/'} className="text-slate-400 hover:text-slate-200 whitespace-nowrap">
                {historical ? 'Historical V0' : (section.match(/Protocol V\d/)?.[0] ?? (section || 'Protocol V2'))}
              </Link>
              <ChevronRight size={14} className="text-slate-600 shrink-0" />
              <span className="font-medium text-slate-100 truncate">{title}</span>
            </nav>
          </div>
          <div className="flex items-center gap-2">
            <LevelSwitch />
            {historical && <span className="hidden sm:inline rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs text-amber-300">{section}</span>}
            <span className="hidden md:inline"><HealthPill h={health} /></span>
          </div>
        </header>
        {(health.state === 'stale' || health.state === 'offline') && !historical && (
          <div role="alert" className="mx-4 mt-4 rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-100 md:mx-8">
            <div className="font-semibold">Protocol V2 data cannot be loaded</div>
            <div className="mt-1 text-amber-200/90">
              {health.state === 'stale'
                ? 'The running backend does not provide the /api/v2 endpoints (it was probably started before Protocol V2 existed). Stop it and start it again with `python api_main.py`.'
                : 'The backend at http://127.0.0.1:8000 is not reachable. Start it with `python api_main.py`.'}
              {health.detail && <span className="block text-xs mt-1 opacity-80">Detail: {health.detail}</span>}
            </div>
          </div>
        )}
        <main className="mx-auto max-w-[1500px] px-4 py-6 md:px-8">{children}</main>
      </div>
    </div>
  );
}

function HistoricalFrame({ children }: { children: ReactNode }) {
  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
        <span className="font-semibold">Historical Results — Protocol V0 (read-only).</span>{' '}
        Generated before the locked-test protocol (tiny samples, random in-folder splits, mislabelled “VQC/HQCC”). Not comparable with
        Protocol V2. <Link to="/" className="underline text-amber-200">Go to the current results (all versions)</Link>.
      </div>
      {children}
    </div>
  );
}

// Redirect that preserves the query string (old V0 URLs → /historical-v0/...)
function RedirectKeepSearch({ to }: { to: string }) {
  const loc = useLocation();
  return <Navigate to={`${to}${loc.search}`} replace />;
}

function LegacyExperimentRedirect() {
  const { id } = useParams();
  return <Navigate to={`/experiments/${id ?? ''}`} replace />;
}

function NotFound() {
  return (
    <div className="py-20 text-center">
      <h1 className="text-xl font-semibold text-slate-100">Page not found</h1>
      <p className="mt-2 text-sm text-slate-400">This address does not exist. <Link to="/" className="text-cyan-300 underline">Open the results overview</Link>.</p>
    </div>
  );
}

const H = (el: ReactNode) => <HistoricalFrame>{el}</HistoricalFrame>;

export default function App() {
  return (
    <BrowserRouter>
      <LevelProvider>
      <Shell>
        <Routes>
          {/* Protocol V2 — current */}
          <Route path="/" element={<AllVersions />} />
          <Route path="/overview-v2" element={<Navigate to="/" replace />} />
          <Route path="/present" element={<Present />} />
          <Route path="/playground" element={<Playground />} />
          <Route path="/quantum-vs-classical" element={<QuantumVsClassical />} />
          <Route path="/quantum-v3" element={<V3Results />} />
          <Route path="/quantum-v4" element={<V4Results />} />
          <Route path="/compare" element={<ModelCompare />} />
          <Route path="/learn" element={<Learn />} />
          <Route path="/how-to-run" element={<Navigate to="/" replace />} />
          <Route path="/code" element={<Navigate to="/" replace />} />
          <Route path="/versions" element={<Navigate to="/" replace />} />
          <Route path="/cnn" element={<CnnStudio />} />
          <Route path="/quiz" element={<QuizPage />} />
          <Route path="/how-it-works" element={<HowItWorks />} />
          <Route path="/upload" element={<UploadLab />} />
          <Route path="/dataset" element={<DatasetGallery />} />
          <Route path="/reconstruction-full" element={<ReconstructionFull />} />
          <Route path="/experiments-v2" element={<ExperimentsPage />} />
          <Route path="/experiments/:id" element={<ExperimentDetail />} />
          <Route path="/models" element={<ModelsPage />} />
          <Route path="/encoding" element={<EncodingPage />} />
          <Route path="/circuits" element={<CircuitsPage />} />
          <Route path="/reconstruction" element={<Navigate to="/reconstruction-full" replace />} />
          <Route path="/classification" element={<ClassificationPage />} />

          {/* Protocol V0 — historical, read-only */}
          <Route path="/historical-v0" element={<HistoricalHome />} />
          <Route path="/historical-v0/dashboard" element={H(<Dashboard />)} />
          <Route path="/historical-v0/qml-lab" element={H(<QuantumMLLab />)} />
          <Route path="/historical-v0/ml" element={H(<MLAnalytics />)} />
          <Route path="/historical-v0/confusion-matrix" element={H(<ConfusionMatrixV0 />)} />
          <Route path="/historical-v0/compare" element={H(<Comparison />)} />
          <Route path="/historical-v0/quantum" element={H(<QuantumLab />)} />
          <Route path="/historical-v0/quantum-compare-lab" element={H(<QuantumCompareLab />)} />
          <Route path="/historical-v0/experiments" element={H(<ExperimentsV0 />)} />
          <Route path="/historical-v0/dataset" element={H(<DatasetExplorer />)} />
          <Route path="/settings" element={<Navigate to="/" replace />} />

          {/* Old URLs */}
          <Route path="/quantum-ml-lab" element={<RedirectKeepSearch to="/historical-v0/qml-lab" />} />
          <Route path="/ml" element={<RedirectKeepSearch to="/historical-v0/ml" />} />
          <Route path="/confusion-matrix" element={<RedirectKeepSearch to="/historical-v0/confusion-matrix" />} />
          <Route path="/compare" element={<RedirectKeepSearch to="/historical-v0/compare" />} />
          <Route path="/quantum" element={<RedirectKeepSearch to="/historical-v0/quantum" />} />
          <Route path="/quantum-compare-lab" element={<RedirectKeepSearch to="/historical-v0/quantum-compare-lab" />} />
          <Route path="/dataset" element={<RedirectKeepSearch to="/historical-v0/dataset" />} />
          <Route path="/circuit" element={<Navigate to="/circuits" replace />} />
          <Route path="/experiments" element={<Navigate to="/experiments-v2" replace />} />
          <Route path="/experiments-v2/:id" element={<LegacyExperimentRedirect />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Shell>
      </LevelProvider>
    </BrowserRouter>
  );
}
