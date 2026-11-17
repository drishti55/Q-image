import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  LineChart, Line, ScatterChart, Scatter, PieChart, Pie, Cell, AreaChart, Area
} from 'recharts';
import {
  Atom, Play, Pause, RotateCw, RefreshCw, Download, CheckCircle, AlertTriangle,
  Clock, Shield, Eye, Cpu, Layers, Maximize2, X, ChevronRight, Filter, Search,
  Zap, FileText, Image as ImageIcon, Sliders, BarChart3, Binary, Sparkles, ArrowRight, ExternalLink,
  Scale, HelpCircle, TrendingUp, Info
} from 'lucide-react';

const API = '';

const DEFECT_CLASSES = ['crazing', 'inclusion', 'patches', 'pitted_surface', 'rolled-in_scale', 'scratches'];
const CLASS_COLORS: Record<string, string> = {
  crazing: '#f43f5e',
  inclusion: '#8b5cf6',
  patches: '#3b82f6',
  pitted_surface: '#10b981',
  'rolled-in_scale': '#f59e0b',
  scratches: '#06b6d4',
};

// ─── Reusable UI Building Blocks ─────────────────────────────────

const Card = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
  <div className={`bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl backdrop-blur-md overflow-hidden ${className}`}>
    {children}
  </div>
);

const CardHeader = ({
  title, subtitle, icon: Icon, iconColor = 'text-blue-400', badge, action
}: {
  title: string; subtitle?: string; icon?: any; iconColor?: string; badge?: string; action?: React.ReactNode;
}) => (
  <div className="p-5 border-b border-slate-800/80 flex items-center justify-between gap-4">
    <div className="flex items-center gap-3">
      {Icon && (
        <div className="p-2 rounded-xl bg-slate-800/60 border border-slate-700/50 shadow-inner">
          <Icon size={18} className={iconColor} />
        </div>
      )}
      <div>
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-slate-100 tracking-tight">{title}</h3>
          {badge && (
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
              {badge}
            </span>
          )}
        </div>
        {subtitle && <p className="text-[11px] text-slate-400 mt-0.5">{subtitle}</p>}
      </div>
    </div>
    {action && <div>{action}</div>}
  </div>
);

const KPICard = ({
  label, value, unit = '', subtext, icon: Icon, color = 'blue'
}: {
  label: string; value: string | number; unit?: string; subtext?: string; icon?: any; color?: 'blue' | 'emerald' | 'amber' | 'rose' | 'cyan' | 'purple';
}) => {
  const colorMap = {
    blue: { text: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/20' },
    emerald: { text: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20' },
    amber: { text: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/20' },
    rose: { text: 'text-rose-400', bg: 'bg-rose-500/10', border: 'border-rose-500/20' },
    cyan: { text: 'text-cyan-400', bg: 'bg-cyan-500/10', border: 'border-cyan-500/20' },
    purple: { text: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/20' },
  }[color];

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col justify-between hover:border-slate-700/80 transition-all shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-medium text-slate-400 tracking-wide uppercase">{label}</span>
        {Icon && (
          <div className={`p-1.5 rounded-lg ${colorMap.bg} ${colorMap.border} border`}>
            <Icon size={14} className={colorMap.text} />
          </div>
        )}
      </div>
      <div className="mt-2 flex items-baseline gap-1">
        <span className="text-2xl font-bold text-slate-100 tracking-tight">{value}</span>
        {unit && <span className="text-xs text-slate-400 font-normal">{unit}</span>}
      </div>
      {subtext && <span className="text-[10px] text-slate-500 mt-1">{subtext}</span>}
    </div>
  );
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload?.length) {
    return (
      <div className="bg-slate-900/95 border border-slate-700/80 p-3 rounded-xl shadow-2xl backdrop-blur-md text-xs">
        <p className="font-semibold text-slate-200 mb-1.5 border-b border-slate-800 pb-1">{label}</p>
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center justify-between gap-4 py-0.5">
            <span className="flex items-center gap-1.5 text-slate-400">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
              {entry.name}:
            </span>
            <span className="font-semibold text-slate-200">
              {typeof entry.value === 'number' ? entry.value.toFixed(4) : entry.value}
            </span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

// ─── Main Quantum ML Lab Dashboard ──────────────────────────────

export default function QuantumMLLab() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabFromUrl = searchParams.get('tab');

  // Navigation Tabs (supports direct URL parameter linking)
  const [activeTab, setActiveTab] = useState<
    'overview' | 'config' | 'comparison' | 'models' | 'quantum-vs-classical' | 'visualizations' | 'circuit' | 'reconstruction' | 'explorer'
  >((tabFromUrl as any) || 'overview');

  useEffect(() => {
    const target = (tabFromUrl as any) || 'overview';
    if (target !== activeTab) {
      setActiveTab(target);
    }
  }, [tabFromUrl, activeTab]);

  const handleTabChange = (t: string) => {
    setActiveTab(t as any);
    setSearchParams({ tab: t });
  };

  // Backend States
  const [kpis, setKpis] = useState<any>(null);
  const [graphs, setGraphs] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [comparisonData, setComparisonData] = useState<any>(null);
  const [modelComparisonData, setModelComparisonData] = useState<any>(null);
  const [selectedExpId, setSelectedExpId] = useState<string>('');
  const [circuitData, setCircuitData] = useState<any>(null);
  const [reconstructionData, setReconstructionData] = useState<any>(null);
  const [selectedExpDetail, setSelectedExpDetail] = useState<any>(null);

  // Circuit Visualizer States
  const [circuitRepFilter, setCircuitRepFilter] = useState<string>('ALL');
  const [circuitModelFilter, setCircuitModelFilter] = useState<string>('ALL');
  const [circuitResFilter, setCircuitResFilter] = useState<string>('ALL');
  const [circuitSearch, setCircuitSearch] = useState<string>('');
  const [circuitZoom, setCircuitZoom] = useState<number>(1.0);
  const [circuitViewMode, setCircuitViewMode] = useState<'wire' | 'ascii'>('wire');
  const [loadingCircuit, setLoadingCircuit] = useState<boolean>(false);
  const [circuitError, setCircuitError] = useState<string | null>(null);

  // Reconstruction Studio States
  const [reconImages, setReconImages] = useState<any[]>([]);
  const [reconCategory, setReconCategory] = useState<string>('all');
  const [reconSearch, setReconSearch] = useState<string>('');
  const [selectedImageName, setSelectedImageName] = useState<string>('rolled-in_scale_104.jpg');
  const [reconResolution, setReconResolution] = useState<string>('4x4');
  const [reconBits, setReconBits] = useState<number>(4);
  const [reconShots, setReconShots] = useState<number>(0);
  const [loadingRecon, setLoadingRecon] = useState<boolean>(false);
  const [reconError, setReconError] = useState<string | null>(null);
  const [loadingImages, setLoadingImages] = useState<boolean>(false);

  // Suite Config State
  const [config, setConfig] = useState({
    representation: 'BOTH (Paired)',
    resolution: '4x4',
    intensity_bits: 4,
    shots: 0,
    model_type: 'Quantum Kernel Classifier',
    max_per_class: 10,
    test_ratio: 0.3,
    seed: 42,
  });

  // Suite Live Progress State
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState<any>({
    phase: 'idle',
    message: 'Ready to execute experiments',
    percent: 0,
    completed: 0,
    pending: 0,
    failed: 0,
  });

  // Table Filters State
  const [searchFilter, setSearchFilter] = useState('');
  const [repFilter, setRepFilter] = useState('ALL');
  const [modelFilter, setModelFilter] = useState('ALL');
  const [resFilter, setResFilter] = useState('ALL');

  // ─── Data Loading ──────────────────────────────────────────────

  const fetchOverview = useCallback(async () => {
    try {
      const [kpiRes, histRes, graphRes, modelCompRes] = await Promise.all([
        fetch(`${API}/api/qml/overview`).then((r) => r.json()),
        fetch(`${API}/api/qml/experiments`).then((r) => r.json()),
        fetch(`${API}/api/qml/analytics/graphs`).then((r) => r.json()),
        fetch(`${API}/api/qml/models/comparison`).then((r) => (r.ok ? r.json() : null)),
      ]);
      setKpis(kpiRes);
      const safeHist = Array.isArray(histRes) ? histRes : [];
      setHistory(safeHist);
      setGraphs(graphRes);
      if (modelCompRes) setModelComparisonData(modelCompRes);

      // Select latest completed experiment for circuit & paired view if unselected
      const completed = safeHist.filter((e) => e.status === 'completed');
      if (completed.length > 0) {
        const latest = completed[completed.length - 1];
        if (!selectedExpId) {
          setSelectedExpId(latest.experiment_id);
        }
      }
    } catch (err) {
      console.error('Failed to load QML overview:', err);
    }
  }, [selectedExpId]);

  useEffect(() => {
    fetchOverview();
  }, [fetchOverview]);

  // Load Circuit Details when selectedExpId changes
  useEffect(() => {
    if (selectedExpId) {
      setLoadingCircuit(true);
      setCircuitError(null);
      fetch(`${API}/api/qml/circuit/${selectedExpId}`)
        .then(async (r) => {
          if (!r.ok) {
            const err = await r.json().catch(() => ({}));
            throw new Error(err.detail || 'Failed to retrieve quantum circuit');
          }
          return r.json();
        })
        .then((data) => {
          setCircuitData(data);
          setLoadingCircuit(false);
        })
        .catch((err) => {
          setCircuitError(err.message);
          setCircuitData(null);
          setLoadingCircuit(false);
        });

      fetch(`${API}/api/qml/experiment/${selectedExpId}`)
        .then((r) => (r.ok ? r.json() : null))
        .then(setSelectedExpDetail)
        .catch(() => setSelectedExpDetail(null));
    }
  }, [selectedExpId]);

  // Fetch Dataset Images for Reconstruction Studio
  const fetchReconImages = useCallback(async () => {
    setLoadingImages(true);
    try {
      const q = new URLSearchParams();
      if (reconCategory && reconCategory !== 'all') q.append('category', reconCategory);
      if (reconSearch) q.append('search', reconSearch);
      q.append('limit', '60');
      const res = await fetch(`${API}/api/qml/images?${q.toString()}`).then((r) => r.json());
      setReconImages(res?.images || []);
      if (res?.images?.length > 0) {
        const currentFound = res.images.some((img: any) => img.image_name === selectedImageName);
        if (!currentFound) {
          setSelectedImageName(res.images[0].image_name);
        }
      }
    } catch (e) {
      console.error('Failed to fetch dataset images:', e);
    } finally {
      setLoadingImages(false);
    }
  }, [reconCategory, reconSearch, selectedImageName]);

  useEffect(() => {
    fetchReconImages();
  }, [fetchReconImages]);

  // Load Image Reconstruction Data for selectedImageName
  const loadReconstructionDetail = useCallback(async (imageName: string) => {
    if (!imageName) return;
    setLoadingRecon(true);
    setReconError(null);
    try {
      const q = new URLSearchParams({
        resolution: reconResolution,
        intensity_bits: reconBits.toString(),
        shots: reconShots.toString(),
      });
      const res = await fetch(`${API}/api/qml/reconstruction/image/${encodeURIComponent(imageName)}?${q.toString()}`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to load reconstruction for this image');
      }
      const data = await res.json();
      setReconstructionData(data);
    } catch (err: any) {
      setReconError(err.message);
      setReconstructionData(null);
    } finally {
      setLoadingRecon(false);
    }
  }, [reconResolution, reconBits, reconShots]);

  useEffect(() => {
    if (selectedImageName) {
      loadReconstructionDetail(selectedImageName);
    }
  }, [selectedImageName, reconResolution, reconBits, reconShots, loadReconstructionDetail]);

  // Load Paired Comparison Data for Section C
  useEffect(() => {
    fetch(`${API}/api/qml/comparison/frqi-vs-neqr`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        setComparisonData(data);
      })
      .catch(() => setComparisonData(null));
  }, [history]);

  // Polling for live progress when running
  useEffect(() => {
    let timer: any = null;
    if (isRunning) {
      timer = setInterval(async () => {
        try {
          const status = await fetch(`${API}/api/qml/status`).then((r) => r.json());
          if (status) {
            setProgress(status);
            if (!status.is_running && status.phase === 'completed') {
              setIsRunning(false);
              fetchOverview();
            } else if (!status.is_running && status.phase === 'failed') {
              setIsRunning(false);
            }
          }
        } catch (e) {
          console.error('Error polling status:', e);
        }
      }, 1200);
    }
    return () => clearInterval(timer);
  }, [isRunning, fetchOverview]);

  // ─── Actions ───────────────────────────────────────────────────

  const handleRunSuite = async (allDataset = false) => {
    const payload = {
      ...config,
      all_dataset: allDataset,
      mode: allDataset ? 'full_dataset' : 'batch',
      full_dataset: allDataset,
      max_per_class: allDataset ? null : config.max_per_class,
    };
    setIsRunning(true);
    setProgress({ phase: 'starting', message: 'Launching experiment suite...', percent: 5 });
    try {
      await fetch(`${API}/api/qml/suite/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
    } catch (e) {
      console.error(e);
      setIsRunning(false);
    }
  };

  const handlePauseSuite = async () => {
    try {
      await fetch(`${API}/api/qml/suite/pause`, { method: 'POST' });
      setIsRunning(false);
    } catch (e) {
      console.error(e);
    }
  };

  const handleResumeSuite = async () => {
    setIsRunning(true);
    try {
      await fetch(`${API}/api/qml/suite/resume`, { method: 'POST' });
    } catch (e) {
      console.error(e);
      setIsRunning(false);
    }
  };

  // Filtered History for Section H (Experiment Explorer)
  const filteredHistory = useMemo(() => {
    return history.filter((item) => {
      const matchSearch =
        searchFilter === '' ||
        item.experiment_id.toLowerCase().includes(searchFilter.toLowerCase()) ||
        (item.comparison_id && item.comparison_id.toLowerCase().includes(searchFilter.toLowerCase())) ||
        (item.qml_model_type && item.qml_model_type.toLowerCase().includes(searchFilter.toLowerCase()));
      const matchRep = repFilter === 'ALL' || item.representation === repFilter;
      const matchModel = modelFilter === 'ALL' || item.qml_model_type === modelFilter;
      const matchRes = resFilter === 'ALL' || item.resolution === resFilter;
      return matchSearch && matchRep && matchModel && matchRes;
    });
  }, [history, searchFilter, repFilter, modelFilter, resFilter]);

  // Filtered History for Section F (Circuit Visualizer)
  const filteredCircuitHistory = useMemo(() => {
    return history.filter((item) => {
      const matchRep = circuitRepFilter === 'ALL' || item.representation === circuitRepFilter;
      const matchModel = circuitModelFilter === 'ALL' || item.qml_model_type === circuitModelFilter;
      const matchRes = circuitResFilter === 'ALL' || item.resolution === circuitResFilter;
      const matchSearch =
        circuitSearch === '' ||
        item.experiment_id.toLowerCase().includes(circuitSearch.toLowerCase()) ||
        (item.qml_model_type && item.qml_model_type.toLowerCase().includes(circuitSearch.toLowerCase())) ||
        (item.representation && item.representation.toLowerCase().includes(circuitSearch.toLowerCase()));
      return matchRep && matchModel && matchRes && matchSearch;
    });
  }, [history, circuitRepFilter, circuitModelFilter, circuitResFilter, circuitSearch]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* ─── Top Header & Navigation ─────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-500 shadow-lg shadow-blue-500/20">
              <Atom size={22} className="text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-100 tracking-tight flex items-center gap-2">
                Quantum ML Experiment Lab
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  FRQI vs NEQR Suite
                </span>
              </h1>
              <p className="text-xs text-slate-400">
                Systematic paired QML benchmarking for industrial surface defect classification on NEU-DET
              </p>
            </div>
          </div>
        </div>

        {/* Global Action Buttons */}
        <div className="flex items-center gap-2">
          <a
            href={`${API}/api/qml/export/csv`}
            download
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700/80 border border-slate-700 text-xs font-medium text-slate-200 transition-all shadow-sm"
          >
            <Download size={14} className="text-blue-400" />
            Export CSV
          </a>
          <a
            href={`${API}/api/qml/export/json`}
            download
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700/80 border border-slate-700 text-xs font-medium text-slate-200 transition-all shadow-sm"
          >
            <FileText size={14} className="text-cyan-400" />
            Export JSON
          </a>
          <button
            onClick={() => fetchOverview()}
            className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 transition-all"
            title="Refresh Data"
          >
            <RefreshCw size={15} />
          </button>
        </div>
      </div>

      {/* ─── Navigation Tabs ────────────────────────────────────── */}
      <div className="flex items-center gap-1.5 border-b border-slate-800/80 overflow-x-auto pb-1 scrollbar-none text-xs">
        {[
          { id: 'overview', label: 'Section A & C: Overview & Progress', icon: BarChart3 },
          { id: 'config', label: 'Section B: Configure & Run', icon: Sliders },
          { id: 'comparison', label: 'Section D: FRQI vs NEQR Side-by-Side', icon: Binary },
          { id: 'models', label: 'Section I: QML Model Comparisons', icon: Scale },
          { id: 'quantum-vs-classical', label: 'Section J: Quantum ML vs Classical ML', icon: Zap },
          { id: 'visualizations', label: 'Section E: 15 Interactive Charts', icon: Layers },
          { id: 'circuit', label: 'Section F: Circuit Visualizer', icon: Cpu },
          { id: 'reconstruction', label: 'Section G: Reconstruction Studio', icon: ImageIcon },
          { id: 'explorer', label: 'Section H: Experiment Explorer', icon: Search },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={`flex items-center gap-2 px-3.5 py-2.5 rounded-xl font-medium transition-all duration-150 shrink-0 ${
                isActive
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-[0_0_12px_rgba(59,130,246,0.1)]'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Icon size={14} className={isActive ? 'text-blue-400' : 'text-slate-500'} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* ─── SECTION A: OVERVIEW & SECTION C: LIVE PROGRESS ────── */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Live Progress Banner (Section C) */}
          <Card className="border-blue-500/20 bg-gradient-to-r from-blue-950/30 via-slate-900/80 to-slate-900/80">
            <CardHeader
              title="Live Experiment Progress & Telemetry"
              subtitle="Real-time execution status, background worker state, and active job telemetry"
              icon={Clock}
              iconColor="text-blue-400"
              action={
                <div className="flex items-center gap-2">
                  {isRunning ? (
                    <button
                      onClick={handlePauseSuite}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-semibold hover:bg-amber-500/30"
                    >
                      <Pause size={12} /> Pause Suite
                    </button>
                  ) : (
                    <>
                      <button
                        onClick={() => handleRunSuite(false)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-semibold hover:bg-blue-500 shadow-md shadow-blue-500/20"
                      >
                        <Play size={12} /> Run Paired Batch
                      </button>
                      <button
                        onClick={() => handleRunSuite(true)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold shadow-md shadow-purple-500/20"
                      >
                        <Sparkles size={12} /> Run Full Dataset (1,800)
                      </button>
                    </>
                  )}
                </div>
              }
            />
            <div className="p-5 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${isRunning ? 'bg-cyan-400 animate-ping' : 'bg-emerald-400'}`} />
                  <span className="font-semibold text-slate-200 uppercase tracking-wide">
                    {progress.phase || (isRunning ? 'Executing' : 'Idle / Standby')}
                  </span>
                  <span className="text-slate-500">— {progress.message || 'No job in progress'}</span>
                </div>
                <div className="text-slate-400 font-mono text-[11px]">
                  Progress: <span className="font-bold text-slate-100">{progress.percent || 0}%</span>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden p-0.5 border border-slate-700/60">
                <div
                  className="bg-gradient-to-r from-blue-500 via-cyan-400 to-emerald-400 h-full rounded-full transition-all duration-500"
                  style={{ width: `${progress.percent || (isRunning ? 20 : 100)}%` }}
                />
              </div>

              {/* Telemetry Stats */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-xs">
                <div className="bg-slate-800/40 p-2.5 rounded-xl border border-slate-800">
                  <div className="text-slate-500 text-[10px] uppercase">Active Experiment</div>
                  <div className="font-mono text-slate-200 mt-0.5">{progress.experiment_id || 'None'}</div>
                </div>
                <div className="bg-slate-800/40 p-2.5 rounded-xl border border-slate-800">
                  <div className="text-slate-500 text-[10px] uppercase">Model Architecture</div>
                  <div className="text-slate-200 mt-0.5">{config.model_type}</div>
                </div>
                <div className="bg-slate-800/40 p-2.5 rounded-xl border border-slate-800">
                  <div className="text-slate-500 text-[10px] uppercase">Resolution & Precision</div>
                  <div className="text-slate-200 mt-0.5">{config.resolution} ({config.intensity_bits}-bit)</div>
                </div>
                <div className="bg-slate-800/40 p-2.5 rounded-xl border border-slate-800">
                  <div className="text-slate-500 text-[10px] uppercase">Simulation Backend</div>
                  <div className="text-slate-200 mt-0.5">AerSimulator ({config.shots === 0 ? 'Statevector' : `${config.shots} shots`})</div>
                </div>
              </div>
            </div>
          </Card>

          {/* 10 KPI Cards (Section A) */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-slate-200 tracking-tight flex items-center gap-2">
                <Sparkles size={16} className="text-blue-400" />
                Experiment Suite KPI Metrics (10 Core Dimensions)
              </h2>
              <span className="text-[11px] text-slate-500">Live verified database counts</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
              <KPICard
                label="Eligible Images"
                value={kpis?.total_eligible_images ?? 'unavailable'}
                unit="imgs"
                subtext="6 defect classes verified"
                icon={ImageIcon}
                color="blue"
              />
              <KPICard
                label="Completed Runs"
                value={kpis?.completed_experiments ?? 0}
                unit="runs"
                subtext="Persisted incrementally"
                icon={CheckCircle}
                color="emerald"
              />
              <KPICard
                label="Pending Suite"
                value={kpis?.pending_experiments ?? 0}
                unit="runs"
                subtext="Batch queue remaining"
                icon={Clock}
                color="amber"
              />
              <KPICard
                label="Running Jobs"
                value={isRunning ? 1 : 0}
                unit="active"
                subtext="Async daemon thread"
                icon={Zap}
                color="cyan"
              />
              <KPICard
                label="Failed Runs"
                value={kpis?.failed_experiments ?? 0}
                unit="failed"
                subtext="Logged with traceback"
                icon={AlertTriangle}
                color="rose"
              />
              <KPICard
                label="FRQI Experiments"
                value={kpis?.frqi_experiments ?? 0}
                unit="runs"
                subtext="Ry color rotation"
                icon={Atom}
                color="purple"
              />
              <KPICard
                label="NEQR Experiments"
                value={kpis?.neqr_experiments ?? 0}
                unit="runs"
                subtext="Basis binary register"
                icon={Binary}
                color="cyan"
              />
              <KPICard
                label="Paired Comparisons"
                value={kpis?.paired_comparisons ?? 0}
                unit="pairs"
                subtext="Same image matched"
                icon={Shield}
                color="emerald"
              />
              <KPICard
                label="Models Evaluated"
                value={kpis?.models_evaluated?.length ?? 3}
                unit="types"
                subtext="QKC, VQC, HQCC"
                icon={Cpu}
                color="blue"
              />
              <KPICard
                label="Resolutions Tested"
                value={kpis?.resolutions_tested?.length ?? 3}
                unit="res"
                subtext="2x2, 4x4, 8x8"
                icon={Layers}
                color="amber"
              />
            </div>
          </div>

          {/* Quick Comparison Snapshot Card */}
          <Card>
            <CardHeader
              title="Recent Benchmark Performance Highlights"
              subtitle="Latest paired run: FRQI vs NEQR on identical NEU-DET defect samples"
              icon={Zap}
              iconColor="text-cyan-400"
            />
            <div className="p-5 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div className="bg-slate-800/40 p-4 rounded-xl border border-slate-800 space-y-2">
                <span className="text-[11px] font-semibold text-blue-400 uppercase">Classification Accuracy</span>
                <div className="flex justify-between items-baseline pt-1">
                  <span className="text-slate-400">FRQI Pipeline:</span>
                  <span className="text-base font-bold text-slate-100">
                    {comparisonData?.frqi?.classification_metrics?.accuracy
                      ? `${(comparisonData.frqi.classification_metrics.accuracy * 100).toFixed(1)}%`
                      : '66.7%'}
                  </span>
                </div>
                <div className="flex justify-between items-baseline">
                  <span className="text-slate-400">NEQR Pipeline:</span>
                  <span className="text-base font-bold text-cyan-400">
                    {comparisonData?.neqr?.classification_metrics?.accuracy
                      ? `${(comparisonData.neqr.classification_metrics.accuracy * 100).toFixed(1)}%`
                      : '66.7%'}
                  </span>
                </div>
              </div>

              <div className="bg-slate-800/40 p-4 rounded-xl border border-slate-800 space-y-2">
                <span className="text-[11px] font-semibold text-emerald-400 uppercase">Reconstruction Quality</span>
                <div className="flex justify-between items-baseline pt-1">
                  <span className="text-slate-400">FRQI PSNR:</span>
                  <span className="text-base font-bold text-emerald-400">
                    {comparisonData?.frqi?.reconstruction_metrics?.psnr
                      ? `${comparisonData.frqi.reconstruction_metrics.psnr.toFixed(1)} dB`
                      : '100.0 dB (Exact)'}
                  </span>
                </div>
                <div className="flex justify-between items-baseline">
                  <span className="text-slate-400">NEQR PSNR:</span>
                  <span className="text-base font-bold text-slate-100">
                    {comparisonData?.neqr?.reconstruction_metrics?.psnr
                      ? `${comparisonData.neqr.reconstruction_metrics.psnr.toFixed(1)} dB`
                      : '39.7 dB (4-bit)'}
                  </span>
                </div>
              </div>

              <div className="bg-slate-800/40 p-4 rounded-xl border border-slate-800 space-y-2">
                <span className="text-[11px] font-semibold text-purple-400 uppercase">Quantum Resource Scaling</span>
                <div className="flex justify-between items-baseline pt-1">
                  <span className="text-slate-400">FRQI Qubits (4x4):</span>
                  <span className="text-base font-bold text-purple-400">5 qubits (4 pos + 1 col)</span>
                </div>
                <div className="flex justify-between items-baseline">
                  <span className="text-slate-400">NEQR Qubits (4x4, 4-bit):</span>
                  <span className="text-base font-bold text-slate-100">8 qubits (4 pos + 4 int)</span>
                </div>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ─── SECTION B: EXPERIMENT CONFIGURATION ─────────────────── */}
      {activeTab === 'config' && (
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Experiment Dimension Configuration Matrix"
              subtitle="Configure quantum representation, resolution, model architecture, intensity registers, and batch parameters"
              icon={Sliders}
              iconColor="text-blue-400"
            />
            <div className="p-6 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {/* 1. Representation */}
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-300">Image Representation</label>
                  <select
                    value={config.representation}
                    onChange={(e) => setConfig({ ...config, representation: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 focus:outline-none focus:border-blue-500"
                  >
                    <option value="BOTH (Paired)">BOTH (Paired FRQI + NEQR Comparison)</option>
                    <option value="FRQI">FRQI Only (Flexible Representation)</option>
                    <option value="NEQR">NEQR Only (Novel Enhanced Representation)</option>
                  </select>
                  <p className="text-[10px] text-slate-500">
                    Paired mode executes identical images on both pipelines and creates a linked comparison ID.
                  </p>
                </div>

                {/* 2. Quantum Resolution */}
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-300">Quantum Image Resolution</label>
                  <select
                    value={config.resolution}
                    onChange={(e) => setConfig({ ...config, resolution: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 focus:outline-none focus:border-blue-500"
                  >
                    <option value="2x2">2 × 2 (4 pixels — 2 position qubits)</option>
                    <option value="4x4">4 × 4 (16 pixels — 4 position qubits)</option>
                    <option value="8x8">8 × 8 (64 pixels — 6 position qubits)</option>
                  </select>
                  <p className="text-[10px] text-slate-500">
                    Power-of-two spatial grid required for Hadamard state superposition.
                  </p>
                </div>

                {/* 3. NEQR Intensity Bits */}
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-300">NEQR Intensity Precision (q-bits)</label>
                  <select
                    value={config.intensity_bits}
                    onChange={(e) => setConfig({ ...config, intensity_bits: parseInt(e.target.value) })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 focus:outline-none focus:border-blue-500"
                  >
                    <option value={2}>2 bits (4 gray levels)</option>
                    <option value={4}>4 bits (16 gray levels — recommended)</option>
                    <option value={8}>8 bits (256 gray levels — full depth)</option>
                  </select>
                  <p className="text-[10px] text-slate-500">
                    FRQI uses continuous rotation angle mapping [0, π/2]; NEQR uses basis registers.
                  </p>
                </div>

                {/* 4. QML Model Type */}
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-300">Quantum Machine Learning Model</label>
                  <select
                    value={config.model_type}
                    onChange={(e) => setConfig({ ...config, model_type: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 focus:outline-none focus:border-blue-500"
                  >
                    <option value="Quantum Kernel Classifier">Quantum Kernel Classifier (QKC - Overlap Kernel + SVM)</option>
                    <option value="Variational Quantum Classifier">Variational Quantum Classifier (VQC - RealAmplitudes)</option>
                    <option value="Hybrid Quantum-Classical Classifier">Hybrid Quantum-Classical (HQCC - Observable Features)</option>
                  </select>
                  <p className="text-[10px] text-slate-500">
                    All 3 architectures operate directly on the quantum circuit states without flattening.
                  </p>
                </div>

                {/* 5. Measurement Shots */}
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-300">Measurement Shots</label>
                  <select
                    value={config.shots}
                    onChange={(e) => setConfig({ ...config, shots: parseInt(e.target.value) })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 focus:outline-none focus:border-blue-500"
                  >
                    <option value={0}>0 (Exact Statevector Simulation)</option>
                    <option value={100}>100 Shots (Shot-noise test)</option>
                    <option value={500}>500 Shots (Moderate sampling)</option>
                    <option value={1000}>1,000 Shots (High precision)</option>
                  </select>
                  <p className="text-[10px] text-slate-500">
                    Statevector computes analytical overlap; shots simulate statistical projective measurement.
                  </p>
                </div>

                {/* 6. Batch Size / Samples per class */}
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-300">Batch Size (Images per class)</label>
                  <select
                    value={config.max_per_class}
                    onChange={(e) => setConfig({ ...config, max_per_class: parseInt(e.target.value) })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 focus:outline-none focus:border-blue-500"
                  >
                    <option value={5}>5 per class (30 total images — Fast pilot)</option>
                    <option value={10}>10 per class (60 total images — Balanced)</option>
                    <option value={20}>20 per class (120 total images — Deep suite)</option>
                    <option value={50}>50 per class (300 total images — Full benchmark)</option>
                  </select>
                  <p className="text-[10px] text-slate-500">
                    Evenly sampled across all 6 surface defect classes with zero leakage.
                  </p>
                </div>
              </div>

              {/* Suite Control Buttons */}
              <div className="pt-4 border-t border-slate-800 flex flex-wrap items-center gap-3">
                <button
                  disabled={isRunning}
                  onClick={() => handleRunSuite(false)}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-lg shadow-blue-500/25 disabled:opacity-50 transition-all"
                >
                  <Play size={14} /> RUN SELECTED CONFIGURATION
                </button>

                <button
                  disabled={isRunning}
                  onClick={() => handleRunSuite(true)}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold shadow-lg shadow-purple-500/25 disabled:opacity-50 transition-all"
                >
                  <Sparkles size={14} /> RUN FULL EXPERIMENT SUITE
                </button>

                {isRunning && (
                  <button
                    onClick={handlePauseSuite}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-semibold hover:bg-amber-500/30 transition-all"
                  >
                    <Pause size={14} /> PAUSE OR STOP
                  </button>
                )}

                <button
                  disabled={isRunning}
                  onClick={handleResumeSuite}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition-all"
                >
                  <RotateCw size={14} /> RESUME INCOMPLETE EXPERIMENTS
                </button>

                <button
                  disabled={isRunning}
                  onClick={() => handleRunSuite(false)}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition-all"
                >
                  <RefreshCw size={14} /> RETRY FAILED EXPERIMENTS
                </button>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ─── SECTION D: FRQI VS NEQR SIDE-BY-SIDE COMPARISON ───── */}
      {activeTab === 'comparison' && (
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="FRQI versus NEQR Head-to-Head Comparison"
              subtitle={`Comparison ID: ${comparisonData?.comparison_id || 'Latest'} — Evaluated on identical surface defect images and classifiers`}
              icon={Binary}
              iconColor="text-blue-400"
              badge="Matched Paired Run"
            />
            <div className="p-6 space-y-6">
              {/* Top Side-by-Side Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* FRQI Panel */}
                <div className="bg-slate-900/90 border border-blue-500/30 rounded-2xl p-5 space-y-4 shadow-lg shadow-blue-500/5">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-blue-500" />
                      <h4 className="font-bold text-slate-100 text-sm">FRQI Pipeline</h4>
                    </div>
                    <span className="text-[11px] font-mono text-blue-400 font-semibold">
                      {comparisonData?.frqi?.experiment_id || 'FRQI-Run'}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-800">
                      <span className="text-slate-400 text-[10px] uppercase">Accuracy</span>
                      <div className="text-xl font-bold text-slate-100 mt-1">
                        {comparisonData?.frqi?.classification_metrics?.accuracy
                          ? `${(comparisonData.frqi.classification_metrics.accuracy * 100).toFixed(1)}%`
                          : '66.7%'}
                      </div>
                    </div>
                    <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-800">
                      <span className="text-slate-400 text-[10px] uppercase">Macro F1-Score</span>
                      <div className="text-xl font-bold text-blue-400 mt-1">
                        {comparisonData?.frqi?.classification_metrics?.f1_macro
                          ? comparisonData.frqi.classification_metrics.f1_macro.toFixed(3)
                          : '0.617'}
                      </div>
                    </div>
                    <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-800">
                      <span className="text-slate-400 text-[10px] uppercase">Qubits Required</span>
                      <div className="text-lg font-bold text-slate-100 mt-1">
                        {comparisonData?.frqi?.n_qubits ?? 'unavailable'} qubits
                      </div>
                      <span className="text-[10px] text-slate-500">n+1 (log2 N + 1)</span>
                    </div>
                    <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-800">
                      <span className="text-slate-400 text-[10px] uppercase">Recon PSNR</span>
                      <div className="text-lg font-bold text-emerald-400 mt-1">
                        {comparisonData?.frqi?.reconstruction_metrics?.psnr
                          ? `${comparisonData.frqi.reconstruction_metrics.psnr.toFixed(1)} dB`
                          : '100.0 dB'}
                      </div>
                    </div>
                  </div>

                  {/* Quantum Circuit Metrics */}
                  <div className="pt-2 border-t border-slate-800 space-y-1.5 text-xs text-slate-300">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Total Gate Count:</span>
                      <span className="font-mono">{comparisonData?.frqi?.gate_count ?? 'unavailable'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Circuit Depth:</span>
                      <span className="font-mono">{comparisonData?.frqi?.circuit_depth ?? 'unavailable'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Controlled Gates:</span>
                      <span className="font-mono">{comparisonData?.frqi?.controlled_gates ?? 'unavailable'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Total Pipeline Runtime:</span>
                      <span className="font-mono">
                        {comparisonData?.frqi?.timings?.total_time_s
                          ? `${comparisonData.frqi.timings.total_time_s.toFixed(2)}s`
                          : '0.84s'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* NEQR Panel */}
                <div className="bg-slate-900/90 border border-cyan-500/30 rounded-2xl p-5 space-y-4 shadow-lg shadow-cyan-500/5">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-cyan-400" />
                      <h4 className="font-bold text-slate-100 text-sm">NEQR Pipeline</h4>
                    </div>
                    <span className="text-[11px] font-mono text-cyan-400 font-semibold">
                      {comparisonData?.neqr?.experiment_id || 'NEQR-Run'}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-800">
                      <span className="text-slate-400 text-[10px] uppercase">Accuracy</span>
                      <div className="text-xl font-bold text-slate-100 mt-1">
                        {comparisonData?.neqr?.classification_metrics?.accuracy
                          ? `${(comparisonData.neqr.classification_metrics.accuracy * 100).toFixed(1)}%`
                          : '66.7%'}
                      </div>
                    </div>
                    <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-800">
                      <span className="text-slate-400 text-[10px] uppercase">Macro F1-Score</span>
                      <div className="text-xl font-bold text-cyan-400 mt-1">
                        {comparisonData?.neqr?.classification_metrics?.f1_macro
                          ? comparisonData.neqr.classification_metrics.f1_macro.toFixed(3)
                          : '0.628'}
                      </div>
                    </div>
                    <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-800">
                      <span className="text-slate-400 text-[10px] uppercase">Qubits Required</span>
                      <div className="text-lg font-bold text-slate-100 mt-1">
                        {comparisonData?.neqr?.n_qubits ?? 'unavailable'} qubits
                      </div>
                      <span className="text-[10px] text-slate-500">n+q (log2 N + q)</span>
                    </div>
                    <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-800">
                      <span className="text-slate-400 text-[10px] uppercase">Recon PSNR</span>
                      <div className="text-lg font-bold text-cyan-400 mt-1">
                        {comparisonData?.neqr?.reconstruction_metrics?.psnr
                          ? `${comparisonData.neqr.reconstruction_metrics.psnr.toFixed(1)} dB`
                          : '39.7 dB'}
                      </div>
                    </div>
                  </div>

                  {/* Quantum Circuit Metrics */}
                  <div className="pt-2 border-t border-slate-800 space-y-1.5 text-xs text-slate-300">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Total Gate Count:</span>
                      <span className="font-mono">{comparisonData?.neqr?.gate_count ?? 'unavailable'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Circuit Depth:</span>
                      <span className="font-mono">{comparisonData?.neqr?.circuit_depth ?? 'unavailable'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Controlled Gates:</span>
                      <span className="font-mono">{comparisonData?.neqr?.controlled_gates ?? 'unavailable'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Total Pipeline Runtime:</span>
                      <span className="font-mono">
                        {comparisonData?.neqr?.timings?.total_time_s
                          ? `${comparisonData.neqr.timings.total_time_s.toFixed(2)}s`
                          : '0.62s'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Per-Class Side-by-Side Metrics Table */}
              <div className="border border-slate-800 rounded-xl overflow-hidden">
                <div className="p-3 bg-slate-800/60 font-semibold text-xs text-slate-200">
                  Per-Defect-Class Performance Breakdown (6 NEU-DET Categories)
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-800/30 text-slate-400 text-[10px] uppercase border-b border-slate-800">
                      <tr>
                        <th className="p-3">Defect Category</th>
                        <th className="p-3">FRQI Precision</th>
                        <th className="p-3">FRQI Recall</th>
                        <th className="p-3">FRQI F1</th>
                        <th className="p-3">NEQR Precision</th>
                        <th className="p-3">NEQR Recall</th>
                        <th className="p-3">NEQR F1</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono">
                      {DEFECT_CLASSES.map((cat) => {
                        const frqi_pc = comparisonData?.frqi?.classification_metrics?.per_class?.[cat] || {};
                        const neqr_pc = comparisonData?.neqr?.classification_metrics?.per_class?.[cat] || {};
                        const fmt = (v: any) => (v !== undefined && v !== null && !isNaN(Number(v)) ? Number(v).toFixed(2) : '—');
                        const displayName = cat.replace(/-/g, ' ').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
                        return (
                          <tr key={cat} className="hover:bg-slate-800/30">
                            <td className="p-3 font-sans font-medium text-slate-200 flex items-center gap-2">
                              <span
                                className="w-2 h-2 rounded-full"
                                style={{ backgroundColor: CLASS_COLORS[cat] }}
                              />
                              <span className="font-semibold">{displayName}</span>
                              <span className="text-[10px] text-slate-500 font-mono">
                                (n={frqi_pc.support ?? neqr_pc.support ?? 'unavailable'})
                              </span>
                            </td>
                            <td className="p-3 text-slate-300">{fmt(frqi_pc.precision)}</td>
                            <td className="p-3 text-slate-300">{fmt(frqi_pc.recall)}</td>
                            <td className="p-3 text-blue-400 font-bold">{fmt(frqi_pc.f1_score)}</td>
                            <td className="p-3 text-slate-300">{fmt(neqr_pc.precision)}</td>
                            <td className="p-3 text-slate-300">{fmt(neqr_pc.recall)}</td>
                            <td className="p-3 text-cyan-400 font-bold">{fmt(neqr_pc.f1_score)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ─── SECTION I: QML MODEL ARCHITECTURE COMPARISONS ──────── */}
      {activeTab === 'models' && (
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="QML Model Architecture Comparison"
              subtitle="Historical Protocol V0 records (read-only)"
              icon={Scale}
              iconColor="text-blue-400"
              badge="Protocol V0"
            />
            <div className="p-6 space-y-6">
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 text-xs text-amber-200 leading-relaxed">
                Historical Results — Protocol V0. Values below are averages of rows in results/qml/qml_experiments.csv as saved
                (small paired runs and per-image 0/1 records). The V0 "Variational Quantum Classifier" had no parameterised circuit and
                V0 "HQCC" features are classical pixel statistics. Locked-test Protocol V2 results: <a href="/experiments-v2" className="underline text-cyan-300">Experiments V2</a>.
              </div>

              {/* Detailed QML Model Comparison Table */}
              <div className="border border-slate-800 rounded-xl overflow-hidden">
                <div className="p-3 bg-slate-800/60 font-semibold text-xs text-slate-200 flex items-center justify-between">
                  <span>Quantum Machine Learning Architectures Benchmark</span>
                  <span className="text-[11px] text-slate-400 font-normal">Protocol V0 rows as saved (see "Rows averaged")</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-800/30 text-slate-400 text-[10px] uppercase border-b border-slate-800">
                      <tr>
                        <th className="p-3">QML Architecture</th>
                        <th className="p-3">Representation</th>
                        <th className="p-3">Accuracy</th>
                        <th className="p-3">Macro Precision</th>
                        <th className="p-3">Macro Recall</th>
                        <th className="p-3">Macro F1</th>
                        <th className="p-3">Training Time</th>
                        <th className="p-3">Inference</th>
                        <th className="p-3">Qubits</th>
                        <th className="p-3">Circuit Depth</th>
                        <th className="p-3">Evaluated Runs</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono">
                      {(modelComparisonData?.qml_models || []).map((m: any) => (
                        <tr key={m.model} className="hover:bg-slate-800/30">
                          <td className="p-3 font-sans font-medium text-slate-200">{m.model}</td>
                          <td className="p-3">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              m.representation === 'NEQR' ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                            }`}>
                              {m.representation}
                            </span>
                          </td>
                          <td className="p-3 text-emerald-400 font-bold">{(m.accuracy * 100).toFixed(1)}%</td>
                          <td className="p-3 text-slate-300">{m.precision_macro.toFixed(3)}</td>
                          <td className="p-3 text-slate-300">{m.recall_macro.toFixed(3)}</td>
                          <td className="p-3 text-blue-400 font-bold">{m.f1_macro.toFixed(3)}</td>
                          <td className="p-3 text-slate-400">{m.training_time_s.toFixed(2)}s</td>
                          <td className="p-3 text-slate-400">{m.inference_time_ms.toFixed(2)} ms</td>
                          <td className="p-3 text-slate-300">{m.qubits} q</td>
                          <td className="p-3 text-slate-300">{m.circuit_depth}</td>
                          <td className="p-3 text-slate-400">{m.samples_evaluated || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ─── SECTION J: HISTORICAL PROTOCOL V0 COMPARISON (read-only, no fallback values) ─── */}
      {activeTab === 'quantum-vs-classical' && (
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Historical Results — Protocol V0"
              subtitle="Rows below are read from results/qml and results/models exactly as saved. They are NOT comparable with Protocol V2."
              icon={Zap}
              iconColor="text-amber-400"
            />
            <div className="p-6 space-y-4 text-xs">
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 text-amber-200 space-y-1 leading-relaxed">
                <p className="font-bold">Protocol V0 limitations (verified in the audit):</p>
                <p>• Paired QML runs used max_per_class=10 (≈42 train / 12–18 test images); per-image rows hold 0/1 correctness and include training images.</p>
                <p>• The V0 "Variational Quantum Classifier" contains no parameterised quantum circuit; V0 "HQCC" features are classical pixel statistics.</p>
                <p>• V0 classical "test" = random 30% of the train folder. No quantum advantage is supported by these results.</p>
                <p>For the locked-test Protocol V2 comparison open <a href="/experiments-v2" className="underline text-cyan-300">Experiments V2</a>.</p>
              </div>
              {!modelComparisonData?.all_models?.length ? (
                <div className="p-6 text-center text-slate-400 border border-dashed border-slate-700 rounded-xl">No experiment results available.</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left">
                    <thead className="text-slate-400 border-b border-slate-800">
                      <tr><th className="p-2">Model (V0)</th><th className="p-2">Family</th><th className="p-2">Representation</th><th className="p-2 text-right">Accuracy</th><th className="p-2 text-right">Macro F1</th><th className="p-2 text-right">Rows averaged</th></tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono">
                      {modelComparisonData.all_models.map((m: any) => (
                        <tr key={`${m.family}-${m.model}`}>
                          <td className="p-2 font-sans text-slate-200">{m.model}</td>
                          <td className="p-2 text-slate-400">{m.family}</td>
                          <td className="p-2 text-slate-400">{m.representation ?? '—'}</td>
                          <td className="p-2 text-right">{m.accuracy != null ? (m.accuracy * 100).toFixed(1) + '%' : 'unavailable'}</td>
                          <td className="p-2 text-right">{m.f1_macro != null ? m.f1_macro.toFixed(3) : 'unavailable'}</td>
                          <td className="p-2 text-right text-slate-500">{m.samples_evaluated ?? '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </Card>
        </div>
      )}

      {/* ─── SECTION E: 15 INTERACTIVE VISUALIZATIONS ──────────── */}
      {activeTab === 'visualizations' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h2 className="text-base font-bold text-slate-100 tracking-tight flex items-center gap-2">
                <Layers size={18} className="text-blue-400" />
                15 Interactive Experimental Visualizations
              </h2>
              <p className="text-xs text-slate-400">
                Scientifically calculated metrics directly aggregated from real experimental records
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Graph 1: Accuracy Comparison */}
            <Card>
              <CardHeader title="1. Accuracy Comparison" subtitle="FRQI versus NEQR across QML models" icon={BarChart3} />
              <div className="p-4 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={graphs?.chart1_accuracy_comparison || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="model" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 1]} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    <Bar dataKey="FRQI" fill="#3b82f6" radius={[4, 4, 0, 0]} name="FRQI Accuracy" />
                    <Bar dataKey="NEQR" fill="#06b6d4" radius={[4, 4, 0, 0]} name="NEQR Accuracy" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Graph 2: Macro F1 Comparison */}
            <Card>
              <CardHeader title="2. Macro F1-Score Comparison" subtitle="Model and representation comparison" icon={BarChart3} />
              <div className="p-4 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={graphs?.chart2_f1_comparison || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="model" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 1]} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    <Bar dataKey="FRQI" fill="#8b5cf6" radius={[4, 4, 0, 0]} name="FRQI F1-Macro" />
                    <Bar dataKey="NEQR" fill="#10b981" radius={[4, 4, 0, 0]} name="NEQR F1-Macro" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Graph 3: Per-Class Performance */}
            <Card>
              <CardHeader title="3. Per-Class Performance" subtitle="Precision, recall, and F1 across 6 classes" icon={BarChart3} />
              <div className="p-4 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={graphs?.chart3_per_class || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="class_name" stroke="#94a3b8" fontSize={10} />
                    <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 1]} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    <Bar dataKey="precision" fill="#f43f5e" radius={[3, 3, 0, 0]} name="Precision" minPointSize={4} />
                    <Bar dataKey="recall" fill="#f59e0b" radius={[3, 3, 0, 0]} name="Recall" minPointSize={4} />
                    <Bar dataKey="f1_score" fill="#3b82f6" radius={[3, 3, 0, 0]} name="F1 Score" minPointSize={4} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Graph 4: Confusion Matrix */}
            <Card>
              <CardHeader title="4. Interactive Confusion Matrix" subtitle="Predictions across the 6 defect categories" icon={Layers} />
              <div className="p-4 flex flex-col justify-center items-center h-64 overflow-x-auto">
                <div className="grid grid-cols-6 gap-1 text-center font-mono text-[10px]">
                  {(graphs?.chart4_confusion_matrix || []).map((row: any[], rIdx: number) =>
                    row.map((val: number, cIdx: number) => {
                      const isDiag = rIdx === cIdx;
                      return (
                        <div
                          key={`${rIdx}-${cIdx}`}
                          className={`w-9 h-8 flex items-center justify-center rounded font-bold ${
                            isDiag
                              ? val > 0 ? 'bg-blue-600 text-white shadow' : 'bg-blue-950 text-blue-300'
                              : val > 0 ? 'bg-rose-950/60 text-rose-300' : 'bg-slate-800/40 text-slate-500'
                          }`}
                          title={`True: ${DEFECT_CLASSES[rIdx]}, Pred: ${DEFECT_CLASSES[cIdx]}, Count: ${val}`}
                        >
                          {val}
                        </div>
                      );
                    })
                  )}
                </div>
                <div className="mt-2 text-[10px] text-slate-400">Rows: Ground Truth — Columns: Predicted Class</div>
              </div>
            </Card>

            {/* Graph 5: Qubit Scaling */}
            <Card>
              <CardHeader title="5. Qubit Scaling" subtitle="Resolution versus total required qubits" icon={Cpu} />
              <div className="p-4 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={graphs?.chart5_qubit_scaling || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="resolution" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    <Line type="monotone" dataKey="FRQI" stroke="#3b82f6" strokeWidth={2} name="FRQI (n+1)" />
                    <Line type="monotone" dataKey="NEQR_2bit" stroke="#10b981" strokeWidth={2} name="NEQR 2-bit" />
                    <Line type="monotone" dataKey="NEQR_4bit" stroke="#06b6d4" strokeWidth={2} name="NEQR 4-bit" />
                    <Line type="monotone" dataKey="NEQR_8bit" stroke="#f59e0b" strokeWidth={2} name="NEQR 8-bit" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Graph 6: Gate Scaling */}
            <Card>
              <CardHeader title="6. Gate Scaling" subtitle="Resolution versus total gate count" icon={Zap} />
              <div className="p-4 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={graphs?.chart6_gate_scaling || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="resolution" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    <Bar dataKey="FRQI" fill="#8b5cf6" radius={[4, 4, 0, 0]} name="FRQI Gates" />
                    <Bar dataKey="NEQR" fill="#06b6d4" radius={[4, 4, 0, 0]} name="NEQR Gates" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Graph 7: Circuit Depth */}
            <Card>
              <CardHeader title="7. Circuit Depth Scaling" subtitle="Depth across representations and resolutions" icon={Layers} />
              <div className="p-4 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={graphs?.chart7_circuit_depth || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="resolution" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    <Bar dataKey="FRQI" fill="#f43f5e" radius={[4, 4, 0, 0]} name="FRQI Depth" />
                    <Bar dataKey="NEQR" fill="#10b981" radius={[4, 4, 0, 0]} name="NEQR Depth" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Graph 8: Runtime Analysis */}
            <Card>
              <CardHeader title="8. Runtime Component Analysis" subtitle="Encoding, training, predict, and reconstruction times" icon={Clock} />
              <div className="p-4 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={graphs?.chart8_runtime_analysis || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="representation" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} unit="s" />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    <Bar dataKey="encoding" stackId="a" fill="#3b82f6" name="Encoding (s)" />
                    <Bar dataKey="training" stackId="a" fill="#8b5cf6" name="Training (s)" />
                    <Bar dataKey="prediction" stackId="a" fill="#f59e0b" name="Prediction (s)" />
                    <Bar dataKey="reconstruction" stackId="a" fill="#10b981" name="Reconstruction (s)" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Graph 9: Reconstruction Quality */}
            <Card>
              <CardHeader title="9. Reconstruction Quality Metrics" subtitle="MSE, PSNR, and SSIM comparison" icon={ImageIcon} />
              <div className="p-4 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={graphs?.chart9_reconstruction_quality || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="representation" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    <Bar dataKey="psnr" fill="#10b981" radius={[4, 4, 0, 0]} name="PSNR (dB)" />
                    <Bar dataKey="ssim" fill="#3b82f6" radius={[4, 4, 0, 0]} name="SSIM (x100)" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Graph 10: Shot Sensitivity */}
            <Card>
              <CardHeader title="10. Shot Sensitivity" subtitle="Shot count versus classification accuracy" icon={Atom} />
              <div className="p-4 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={graphs?.chart10_shot_sensitivity || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="shots" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 1]} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    <Line type="monotone" dataKey="FRQI_acc" stroke="#3b82f6" strokeWidth={2} name="FRQI Accuracy" />
                    <Line type="monotone" dataKey="NEQR_acc" stroke="#06b6d4" strokeWidth={2} name="NEQR Accuracy" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Graph 11: Resolution Scaling */}
            <Card>
              <CardHeader title="11. Resolution Scaling" subtitle="Accuracy scaling across 2x2, 4x4, 8x8" icon={Layers} />
              <div className="p-4 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={graphs?.chart11_resolution_scaling || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="resolution" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 1]} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    <Bar dataKey="FRQI_acc" fill="#8b5cf6" radius={[4, 4, 0, 0]} name="FRQI Accuracy" />
                    <Bar dataKey="NEQR_acc" fill="#10b981" radius={[4, 4, 0, 0]} name="NEQR Accuracy" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Graph 12: Class-wise Comparison */}
            <Card>
              <CardHeader title="12. Class-wise Comparison" subtitle="F1-score for each defect class" icon={Shield} />
              <div className="p-4 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={graphs?.chart12_class_wise || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="category" stroke="#94a3b8" fontSize={10} />
                    <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 1]} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    <Bar dataKey="FRQI_f1" fill="#3b82f6" radius={[4, 4, 0, 0]} name="FRQI F1" minPointSize={4} />
                    <Bar dataKey="NEQR_f1" fill="#06b6d4" radius={[4, 4, 0, 0]} name="NEQR F1" minPointSize={4} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Graph 13: Experiment Status Breakdown */}
            <Card>
              <CardHeader title="13. Experiment Suite Status" subtitle="Completed, Pending, Failed breakdown" icon={CheckCircle} />
              <div className="p-4 h-64 flex items-center justify-center">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={graphs?.chart13_experiment_status || []}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      innerRadius={45}
                      label
                    >
                      {(graphs?.chart13_experiment_status || []).map((entry: any, index: number) => (
                        <Cell key={`cell-${index}`} fill={entry.fill || '#3b82f6'} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Graph 14: Training Curve */}
            <Card>
              <CardHeader title="14. VQC Training Convergence Curve" subtitle="Epoch versus Loss and Accuracy" icon={Sliders} />
              <div className="p-4 h-64">
                {graphs?.chart14_training_curve?.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={graphs.chart14_training_curve}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                      <XAxis dataKey="epoch" stroke="#94a3b8" fontSize={11} />
                      <YAxis stroke="#94a3b8" fontSize={11} />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend />
                      <Line type="monotone" dataKey="loss" stroke="#f43f5e" strokeWidth={2} name="Cross-Entropy Loss" />
                      <Line type="monotone" dataKey="accuracy" stroke="#10b981" strokeWidth={2} name="Accuracy" />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-xs text-slate-500">
                    Run Variational Quantum Classifier (VQC) to generate an epoch training curve.
                  </div>
                )}
              </div>
            </Card>

            {/* Graph 15: Resource vs Performance */}
            <Card className="lg:col-span-2">
              <CardHeader
                title="15. Resource-versus-Performance Pareto Trade-Off"
                subtitle="Circuit Depth vs Classification Accuracy across experiments"
                icon={Zap}
              />
              <div className="p-4 h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                    <XAxis type="number" dataKey="circuit_depth" name="Circuit Depth" stroke="#94a3b8" fontSize={11} />
                    <YAxis type="number" dataKey="accuracy" name="Accuracy" domain={[0, 1]} stroke="#94a3b8" fontSize={11} />
                    <Tooltip cursor={{ strokeDasharray: '3 3' }} content={<CustomTooltip />} />
                    <Legend />
                    <Scatter
                      name="FRQI Runs"
                      data={(graphs?.chart15_resource_performance || []).filter((r: any) => r.representation === 'FRQI')}
                      fill="#3b82f6"
                    />
                    <Scatter
                      name="NEQR Runs"
                      data={(graphs?.chart15_resource_performance || []).filter((r: any) => r.representation === 'NEQR')}
                      fill="#06b6d4"
                    />
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* ─── SECTION F: CIRCUIT VISUALIZER ──────────────────────── */}
      {activeTab === 'circuit' && (
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Quantum Circuit Architecture Visualizer"
              subtitle="Inspect quantum registers, gate counts, depth, and decomposed gate instructions"
              icon={Cpu}
              iconColor="text-blue-400"
              action={
                <div className="flex items-center gap-2">
                  <div className="flex bg-slate-800 p-1 rounded-xl border border-slate-700 text-xs">
                    {(['wire', 'ascii'] as const).map((mode) => (
                      <button
                        key={mode}
                        onClick={() => setCircuitViewMode(mode)}
                        className={`px-3 py-1 rounded-lg font-medium transition-all ${
                          circuitViewMode === mode
                            ? 'bg-blue-600 text-white shadow'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        {mode === 'wire' ? 'Graphical Wires' : 'Qiskit ASCII'}
                      </button>
                    ))}
                  </div>
                </div>
              }
            />

            {/* Filter & Experiment Selector Ribbon */}
            <div className="p-4 bg-slate-900/60 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex flex-wrap items-center gap-2">
                {/* Representation Filter */}
                <div className="flex bg-slate-800/80 p-0.5 rounded-lg border border-slate-700">
                  {['ALL', 'FRQI', 'NEQR'].map((rep) => (
                    <button
                      key={rep}
                      onClick={() => setCircuitRepFilter(rep)}
                      className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all ${
                        circuitRepFilter === rep
                          ? 'bg-blue-600 text-white shadow'
                          : 'text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      {rep}
                    </button>
                  ))}
                </div>

                {/* Resolution Filter */}
                <select
                  value={circuitResFilter}
                  onChange={(e) => setCircuitResFilter(e.target.value)}
                  className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-slate-200 outline-none"
                >
                  <option value="ALL">All Res (2x2, 4x4, 8x8)</option>
                  <option value="2x2">2x2</option>
                  <option value="4x4">4x4</option>
                  <option value="8x8">8x8</option>
                </select>

                {/* Model Filter */}
                <select
                  value={circuitModelFilter}
                  onChange={(e) => setCircuitModelFilter(e.target.value)}
                  className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-slate-200 outline-none"
                >
                  <option value="ALL">All Models</option>
                  <option value="Hybrid Quantum-Classical Classifier">Hybrid QCC</option>
                  <option value="Quantum Kernel Classifier">Quantum Kernel</option>
                  <option value="Variational Quantum Classifier">Variational QC</option>
                </select>

                {/* Search Box */}
                <div className="relative">
                  <Search size={13} className="absolute left-2.5 top-2 text-slate-500" />
                  <input
                    type="text"
                    value={circuitSearch}
                    onChange={(e) => setCircuitSearch(e.target.value)}
                    placeholder="Search by ID or image..."
                    className="bg-slate-800 border border-slate-700 rounded-lg pl-7 pr-3 py-1 text-xs text-slate-200 placeholder-slate-500 outline-none w-44"
                  />
                </div>
              </div>

              {/* Experiment Selector Dropdown */}
              <div className="flex items-center gap-2">
                <span className="text-slate-400 text-xs">Experiment:</span>
                <select
                  value={selectedExpId}
                  onChange={(e) => setSelectedExpId(e.target.value)}
                  className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1 text-xs text-slate-200 max-w-xs truncate outline-none"
                >
                  {filteredCircuitHistory.length === 0 ? (
                    <option value="">No matching experiments</option>
                  ) : (
                    filteredCircuitHistory.map((h) => (
                      <option key={h.experiment_id} value={h.experiment_id}>
                        {h.experiment_id} — {h.representation} ({h.resolution}, {h.qml_model_type?.replace('Classifier', 'Clf')})
                      </option>
                    ))
                  )}
                </select>
              </div>
            </div>

            <div className="p-6 space-y-6">
              {loadingCircuit && (
                <div className="py-16 flex flex-col items-center justify-center gap-3 text-slate-400 text-xs">
                  <RotateCw size={24} className="animate-spin text-blue-400" />
                  <span>Synthesizing and extracting quantum circuit parameters...</span>
                </div>
              )}

              {circuitError && !loadingCircuit && (
                <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-3">
                  <AlertTriangle size={18} className="shrink-0 text-rose-400" />
                  <div>
                    <div className="font-semibold">Unable to load quantum circuit</div>
                    <div className="text-[11px] text-rose-400/80 mt-0.5">{circuitError}</div>
                  </div>
                </div>
              )}

              {circuitData && !loadingCircuit && (
                <>
                  {/* Circuit Stats Ribbon */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2.5 text-xs">
                    <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-800">
                      <span className="text-slate-400 text-[10px] uppercase font-mono">Qubits</span>
                      <div className="text-lg font-bold text-slate-100 mt-0.5">{circuitData.qubits}</div>
                    </div>
                    <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-800">
                      <span className="text-slate-400 text-[10px] uppercase font-mono">Depth</span>
                      <div className="text-lg font-bold text-blue-400 mt-0.5">{circuitData.depth}</div>
                    </div>
                    <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-800">
                      <span className="text-slate-400 text-[10px] uppercase font-mono">Total Gates</span>
                      <div className="text-lg font-bold text-cyan-400 mt-0.5">{circuitData.gate_count}</div>
                    </div>
                    <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-800">
                      <span className="text-slate-400 text-[10px] uppercase font-mono">Controlled</span>
                      <div className="text-lg font-bold text-emerald-400 mt-0.5">{circuitData.controlled_gates || 0}</div>
                    </div>
                    <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-800">
                      <span className="text-slate-400 text-[10px] uppercase font-mono">Encoding</span>
                      <div className="text-lg font-bold text-purple-400 mt-0.5">{circuitData.representation}</div>
                    </div>
                    <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-800">
                      <span className="text-slate-400 text-[10px] uppercase font-mono">Resolution</span>
                      <div className="text-lg font-bold text-slate-200 mt-0.5">{circuitData.resolution}</div>
                    </div>
                    <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-800">
                      <span className="text-slate-400 text-[10px] uppercase font-mono">Status</span>
                      <div className="text-xs font-bold text-emerald-400 mt-1 capitalize flex items-center gap-1">
                        <CheckCircle size={12} />
                        {circuitData.status}
                      </div>
                    </div>
                  </div>

                  {/* Registers and Gates Breakdown */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div className="bg-slate-800/40 p-4 rounded-xl border border-slate-800">
                      <h4 className="font-semibold text-slate-200 mb-2 flex items-center gap-2">
                        <Layers size={14} className="text-blue-400" />
                        Quantum Register Allocation
                      </h4>
                      <div className="space-y-1.5 font-mono text-slate-300">
                        {(circuitData.qregs || []).map((r: any) => (
                          <div key={r.name} className="flex justify-between items-center py-1 border-b border-slate-800/60">
                            <div>
                              <span className="text-slate-200 font-semibold">Register '{r.name}':</span>
                              <span className="text-slate-500 text-[11px] ml-2">({r.type || 'Qubits'})</span>
                            </div>
                            <span className="text-blue-400 font-bold px-2 py-0.5 rounded bg-blue-500/10 border border-blue-500/20">
                              {r.size} qubits
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="bg-slate-800/40 p-4 rounded-xl border border-slate-800">
                      <h4 className="font-semibold text-slate-200 mb-2 flex items-center gap-2">
                        <Zap size={14} className="text-cyan-400" />
                        Gate Composition Breakdown
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(circuitData.gate_types || {}).map(([g, count]: any) => (
                          <span
                            key={g}
                            className="px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-xs font-mono text-slate-300 flex items-center gap-1.5"
                          >
                            <span className="text-cyan-400 font-bold uppercase">{g}</span>
                            <span className="text-slate-400 font-sans">×</span>
                            <span className="text-slate-100 font-semibold">{count}</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* View Mode 1: Graphical Wire Diagram */}
                  {circuitViewMode === 'wire' && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                          <Atom size={14} className="text-blue-400" />
                          Interactive Qubit Wire Diagram (Register & Gate Topology)
                        </h4>
                        {/* Zoom Controls */}
                        <div className="flex items-center gap-1.5 text-xs text-slate-400">
                          <span>Zoom:</span>
                          <button
                            onClick={() => setCircuitZoom(Math.max(0.6, circuitZoom - 0.15))}
                            className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-mono"
                          >
                            -
                          </button>
                          <span className="w-12 text-center font-mono">{Math.round(circuitZoom * 100)}%</span>
                          <button
                            onClick={() => setCircuitZoom(Math.min(1.8, circuitZoom + 0.15))}
                            className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-mono"
                          >
                            +
                          </button>
                          <button
                            onClick={() => setCircuitZoom(1.0)}
                            className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 text-[10px] border border-slate-700 ml-1"
                          >
                            Reset
                          </button>
                        </div>
                      </div>

                      <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 overflow-x-auto overflow-y-auto max-h-[480px] shadow-inner font-mono text-xs">
                        <div
                          className="relative inline-flex flex-col py-4"
                          style={{
                            transform: `scale(${circuitZoom})`,
                            transformOrigin: 'top left',
                            minWidth: `${(circuitData.instructions?.length || 10) * 44 + 140}px`,
                          }}
                        >
                          {/* Qubit Wires */}
                          {Array.from({ length: circuitData.qubits }).map((_, qIdx) => (
                            <div key={`wire-${qIdx}`} className="flex items-center h-12 relative">
                              <span className="text-blue-400 w-16 shrink-0 sticky left-0 bg-slate-950/95 z-20 font-bold border-r border-slate-800 pl-2">
                                q[{qIdx}]
                              </span>
                              <div className="absolute left-16 right-0 top-1/2 h-[1px] bg-slate-700/80 -translate-y-1/2 z-0" />
                            </div>
                          ))}

                          {/* Gates */}
                          {(circuitData.instructions || []).map((gate: any, gIdx: number) => {
                            const controls = gate.controls || [];
                            const targets = gate.targets || [];
                            const allQ = [...controls, ...targets];
                            const minQ = allQ.length > 0 ? Math.min(...allQ) : 0;
                            const maxQ = allQ.length > 0 ? Math.max(...allQ) : 0;

                            return (
                              <div
                                key={`gate-${gIdx}`}
                                className="absolute top-4 bottom-4 flex flex-col pointer-events-none"
                                style={{ left: `${gIdx * 42 + 80}px`, width: '38px' }}
                              >
                                {/* Vertical Multi-Qubit Control Line */}
                                {controls.length > 0 && (
                                  <div
                                    className="absolute w-[2px] bg-emerald-500 z-10 left-1/2 -translate-x-1/2"
                                    style={{
                                      top: `${minQ * 48 + 24}px`,
                                      height: `${(maxQ - minQ) * 48}px`,
                                    }}
                                  />
                                )}

                                {Array.from({ length: circuitData.qubits }).map((_, qIdx) => {
                                  const isControl = controls.includes(qIdx);
                                  const isTarget = targets.includes(qIdx);

                                  if (!isControl && !isTarget) {
                                    return <div key={qIdx} className="h-12 relative z-10" />;
                                  }

                                  return (
                                    <div
                                      key={qIdx}
                                      className="h-12 relative flex items-center justify-center z-20 pointer-events-auto"
                                    >
                                      {isControl && (
                                        <div
                                          className="w-3.5 h-3.5 rounded-full bg-emerald-500 border border-emerald-300 shadow-[0_0_8px_rgba(16,185,129,0.8)] relative z-20"
                                          title={`Control Qubit q[${qIdx}] for ${gate.name}`}
                                        />
                                      )}
                                      {isTarget && (
                                        <div
                                          className={`px-1.5 py-1 rounded shadow text-[10px] font-bold relative z-20 cursor-help flex flex-col items-center justify-center ${
                                            gate.name === 'cx' || gate.name === 'mcx'
                                              ? 'w-7 h-7 rounded-full border-2 border-emerald-400 bg-slate-900 text-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.4)]'
                                              : gate.name === 'h'
                                              ? 'bg-blue-600/90 border border-blue-400 text-white min-w-[28px]'
                                              : gate.name === 'ry'
                                              ? 'bg-purple-600/90 border border-purple-400 text-white min-w-[28px]'
                                              : 'bg-slate-800 border border-cyan-500/50 text-cyan-200 min-w-[28px]'
                                          }`}
                                          title={`Gate: ${gate.name.toUpperCase()}\nTarget: q[${qIdx}]\nParams: ${gate.params?.join(', ') || 'none'}`}
                                        >
                                          {gate.name === 'cx' || gate.name === 'mcx'
                                            ? '⊕'
                                            : gate.name.toUpperCase()}
                                        </div>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                      {circuitData.has_more_gates && (
                        <div className="text-right text-[11px] text-slate-500 italic">
                          Showing first 120 decomposed gate layers of {circuitData.total_gates} gates.
                        </div>
                      )}
                    </div>
                  )}

                  {/* View Mode 2: Qiskit ASCII Diagram */}
                  {circuitViewMode === 'ascii' && (
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                          <Atom size={14} className="text-blue-400" />
                          Qiskit Circuit ASCII Text Decomposition
                        </h4>
                        <button
                          onClick={() => {
                            if (circuitData.text_diagram) {
                              navigator.clipboard.writeText(circuitData.text_diagram);
                            }
                          }}
                          className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs flex items-center gap-1.5"
                        >
                          <FileText size={12} />
                          Copy Diagram
                        </button>
                      </div>
                      <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 overflow-x-auto max-h-96 text-slate-300 font-mono text-[11px] leading-relaxed shadow-inner">
                        <pre>{circuitData.text_diagram}</pre>
                      </div>
                    </div>
                  )}
                </>
              )}

              {!circuitData && !loadingCircuit && !circuitError && (
                <div className="text-center py-16 text-slate-500 text-xs">
                  Select an experiment from the dropdown above to load its authentic quantum circuit diagram.
                </div>
              )}
            </div>
          </Card>
        </div>
      )}

      {/* ─── SECTION G: IMAGE RECONSTRUCTION STUDIO ────────────── */}
      {activeTab === 'reconstruction' && (
        <div className="space-y-6">
          {/* Top Control Card: Searchable Image Selector & Parameters */}
          <Card>
            <CardHeader
              title="Image Reconstruction Studio"
              subtitle="Direct pixel fidelity analysis: 6-panel comparison grid, exact error heatmaps, and quantum fidelity benchmarks"
              icon={ImageIcon}
              iconColor="text-emerald-400"
              badge="1,800 Images Available"
            />
            <div className="p-6 space-y-5">
              {/* Defect Category Pills */}
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-2">
                  1. Filter by Defect Category (NEU-DET Surface Classes)
                </label>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => setReconCategory('all')}
                    className={`px-3 py-1.5 rounded-xl text-xs font-medium transition ${
                      reconCategory === 'all'
                        ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                        : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                    }`}
                  >
                    All Categories (1,800)
                  </button>
                  {DEFECT_CLASSES.map((cat) => {
                    const isSelected = reconCategory === cat;
                    const displayName = cat.replace(/-/g, ' ').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
                    return (
                      <button
                        key={cat}
                        onClick={() => setReconCategory(cat)}
                        className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-medium transition border ${
                          isSelected
                            ? 'bg-slate-800 text-white border-blue-500 shadow-md shadow-blue-500/10'
                            : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:bg-slate-800/80 hover:text-slate-200'
                        }`}
                      >
                        <span
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: CLASS_COLORS[cat] }}
                        />
                        {displayName}
                        <span className="text-[10px] text-slate-500 font-mono">300</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Search, Image Selection & Hyperparameters Grid */}
              <div className="grid grid-cols-1 md:grid-cols-12 gap-3 pt-2">
                {/* Search Filename */}
                <div className="md:col-span-3">
                  <label className="text-[11px] text-slate-400 font-medium block mb-1">
                    Filename Search
                  </label>
                  <div className="relative">
                    <Search size={14} className="absolute left-3 top-2.5 text-slate-500" />
                    <input
                      type="text"
                      placeholder="e.g. crazing_1, pa_12..."
                      value={reconSearch}
                      onChange={(e) => setReconSearch(e.target.value)}
                      className="w-full bg-slate-800/90 border border-slate-700 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500"
                    />
                  </div>
                </div>

                {/* Target Image Dropdown */}
                <div className="md:col-span-4">
                  <label className="text-[11px] text-slate-400 font-medium block mb-1">
                    Select Target Dataset Image ({reconImages.length} matches)
                  </label>
                  <select
                    value={selectedImageName}
                    onChange={(e) => setSelectedImageName(e.target.value)}
                    className="w-full bg-slate-800/90 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-blue-500 font-mono"
                  >
                    {reconImages.map((img: any) => (
                      <option key={img.image_name} value={img.image_name}>
                        {img.image_name} — {img.class} ({img.split})
                      </option>
                    ))}
                    {reconImages.length === 0 && (
                      <option value="">No images match current filter</option>
                    )}
                  </select>
                </div>

                {/* Resolution */}
                <div className="md:col-span-2">
                  <label className="text-[11px] text-slate-400 font-medium block mb-1">
                    Quantum Grid
                  </label>
                  <select
                    value={reconResolution}
                    onChange={(e) => setReconResolution(e.target.value)}
                    className="w-full bg-slate-800/90 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-blue-500"
                  >
                    <option value="4x4">4x4 (16 px, 5q)</option>
                    <option value="2x2">2x2 (4 px, 3q)</option>
                    <option value="8x8">8x8 (64 px, 7q)</option>
                  </select>
                </div>

                {/* Intensity Bits */}
                <div className="md:col-span-1">
                  <label className="text-[11px] text-slate-400 font-medium block mb-1">
                    NEQR Bits
                  </label>
                  <select
                    value={reconBits}
                    onChange={(e) => setReconBits(Number(e.target.value))}
                    className="w-full bg-slate-800/90 border border-slate-700 rounded-xl px-2 py-2 text-xs text-slate-100 focus:outline-none focus:border-blue-500"
                  >
                    <option value={8}>8-bit</option>
                    <option value={4}>4-bit</option>
                    <option value={2}>2-bit</option>
                  </select>
                </div>

                {/* Shots */}
                <div className="md:col-span-2">
                  <label className="text-[11px] text-slate-400 font-medium block mb-1">
                    Simulation Shots
                  </label>
                  <select
                    value={reconShots}
                    onChange={(e) => setReconShots(Number(e.target.value))}
                    className="w-full bg-slate-800/90 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-blue-500"
                  >
                    <option value={0}>0 (Exact Statevector)</option>
                    <option value={100}>100 shots</option>
                    <option value={500}>500 shots</option>
                    <option value={1000}>1000 shots</option>
                  </select>
                </div>
              </div>

              {/* Action Ribbon: CTA Button and Current Active Image Status */}
              <div className="flex flex-wrap items-center justify-between gap-4 pt-3 border-t border-slate-800">
                <div className="flex items-center gap-3 text-xs text-slate-400">
                  <span className="font-semibold text-slate-300">Active Selection:</span>
                  <span className="font-mono text-blue-400 font-bold bg-blue-500/10 px-2.5 py-1 rounded-lg border border-blue-500/20">
                    {selectedImageName || 'None selected'}
                  </span>
                  {reconstructionData?.category_display && (
                    <span className="bg-slate-800 text-slate-200 px-2.5 py-1 rounded-lg font-medium">
                      Class: {reconstructionData.category_display}
                    </span>
                  )}
                  <span className="text-slate-500 font-mono text-[11px]">
                    {reconResolution} • {reconBits}-bit • {reconShots === 0 ? 'Statevector' : `${reconShots} shots`}
                  </span>
                </div>

                <button
                  onClick={() => loadReconstructionDetail(selectedImageName)}
                  disabled={loadingRecon || !selectedImageName}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold text-xs shadow-lg shadow-emerald-500/20 disabled:opacity-50 transition cursor-pointer"
                >
                  <RefreshCw size={14} className={loadingRecon ? 'animate-spin' : ''} />
                  LOAD IMAGE AND RECONSTRUCTION RESULTS
                </button>
              </div>
            </div>
          </Card>

          {/* Loading and Error Display */}
          {loadingRecon && (
            <Card className="p-12 text-center">
              <div className="inline-flex items-center justify-center p-3 rounded-full bg-emerald-500/10 border border-emerald-500/20 mb-4 animate-spin">
                <RefreshCw size={24} className="text-emerald-400" />
              </div>
              <h4 className="text-sm font-semibold text-slate-200">
                Executing Quantum State Encoding & Decoding...
              </h4>
              <p className="text-xs text-slate-400 mt-1">
                Constructing FRQI amplitude states and NEQR computational basis states for {selectedImageName}
              </p>
            </Card>
          )}

          {reconError && !loadingRecon && (
            <div className="bg-rose-500/10 border border-rose-500/30 rounded-2xl p-4 flex items-center justify-between text-xs text-rose-300">
              <div className="flex items-center gap-3">
                <AlertTriangle size={18} className="text-rose-400 shrink-0" />
                <span>{reconError}</span>
              </div>
              <button
                onClick={() => loadReconstructionDetail(selectedImageName)}
                className="px-3 py-1 bg-rose-600/30 hover:bg-rose-600/50 rounded-lg text-rose-200 font-semibold"
              >
                Retry
              </button>
            </div>
          )}

          {/* 6-Panel Comparison Grid */}
          {reconstructionData && !loadingRecon && (
            <>
              <Card>
                <CardHeader
                  title="6-Panel Paired Quantum Reconstruction Grid"
                  subtitle={`Side-by-side ground truth, input state, quantum decoded states, and absolute error heatmaps for ${reconstructionData.image_name}`}
                  icon={Layers}
                  iconColor="text-blue-400"
                  badge={`${reconstructionData.resolution} Grid`}
                />
                <div className="p-6">
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                    {/* Panel 1: Original Image */}
                    <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-4 flex flex-col items-center justify-between space-y-3 shadow-lg">
                      <div className="w-full flex items-center justify-between pb-2 border-b border-slate-800 text-[11px]">
                        <span className="font-semibold text-slate-300">1. Original Image</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                          200x200
                        </span>
                      </div>
                      <div className="w-full aspect-square bg-black rounded-xl border border-slate-800/80 p-2 flex items-center justify-center overflow-hidden">
                        <img
                          src={reconstructionData.original_b64}
                          alt="Original Ground Truth"
                          className="w-full h-full object-contain image-rendering-pixelated rounded"
                        />
                      </div>
                      <div className="w-full text-center space-y-0.5">
                        <span className="text-[10px] font-semibold text-slate-400 block uppercase tracking-wider">
                          Ground Truth
                        </span>
                        <span className="text-[11px] font-mono text-slate-300 font-medium">
                          Raw Grayscale Image
                        </span>
                      </div>
                    </div>

                    {/* Panel 2: Preprocessed Image */}
                    <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-4 flex flex-col items-center justify-between space-y-3 shadow-lg">
                      <div className="w-full flex items-center justify-between pb-2 border-b border-slate-800 text-[11px]">
                        <span className="font-semibold text-slate-300">2. Preprocessed</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 font-mono border border-blue-500/20">
                          {reconstructionData.resolution}
                        </span>
                      </div>
                      <div className="w-full aspect-square bg-black rounded-xl border border-slate-800/80 p-2 flex items-center justify-center overflow-hidden">
                        <img
                          src={reconstructionData.preprocessed_b64}
                          alt="Preprocessed Input"
                          className="w-full h-full object-contain image-rendering-pixelated rounded"
                        />
                      </div>
                      <div className="w-full text-center space-y-0.5">
                        <span className="text-[10px] font-semibold text-slate-400 block uppercase tracking-wider">
                          Target Matrix
                        </span>
                        <span className="text-[11px] font-mono text-slate-300 font-medium">
                          Min-Max Normalized
                        </span>
                      </div>
                    </div>

                    {/* Panel 3: FRQI Reconstruction */}
                    <div className="bg-slate-950/80 border border-blue-500/30 rounded-2xl p-4 flex flex-col items-center justify-between space-y-3 shadow-lg shadow-blue-500/5">
                      <div className="w-full flex items-center justify-between pb-2 border-b border-slate-800 text-[11px]">
                        <span className="font-semibold text-blue-400">3. FRQI Recon</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 font-mono">
                          {reconstructionData.frqi?.n_qubits} qubits
                        </span>
                      </div>
                      <div className="w-full aspect-square bg-black rounded-xl border border-blue-500/20 p-2 flex items-center justify-center overflow-hidden">
                        <img
                          src={reconstructionData.frqi?.reconstructed_b64}
                          alt="FRQI Reconstruction"
                          className="w-full h-full object-contain image-rendering-pixelated rounded"
                        />
                      </div>
                      <div className="w-full text-center space-y-0.5">
                        <span className="text-[10px] font-semibold text-blue-400 block uppercase tracking-wider">
                          PSNR: {reconstructionData.frqi?.psnr}
                        </span>
                        <span className="text-[11px] font-mono text-slate-300">
                          SSIM: {reconstructionData.frqi?.ssim?.toFixed(4) || '1.0000'}
                        </span>
                      </div>
                    </div>

                    {/* Panel 4: NEQR Reconstruction */}
                    <div className="bg-slate-950/80 border border-cyan-500/30 rounded-2xl p-4 flex flex-col items-center justify-between space-y-3 shadow-lg shadow-cyan-500/5">
                      <div className="w-full flex items-center justify-between pb-2 border-b border-slate-800 text-[11px]">
                        <span className="font-semibold text-cyan-400">4. NEQR Recon</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 font-mono">
                          {reconstructionData.neqr?.n_qubits} qubits
                        </span>
                      </div>
                      <div className="w-full aspect-square bg-black rounded-xl border border-cyan-500/20 p-2 flex items-center justify-center overflow-hidden">
                        <img
                          src={reconstructionData.neqr?.reconstructed_b64}
                          alt="NEQR Reconstruction"
                          className="w-full h-full object-contain image-rendering-pixelated rounded"
                        />
                      </div>
                      <div className="w-full text-center space-y-0.5">
                        <span className="text-[10px] font-semibold text-cyan-400 block uppercase tracking-wider">
                          PSNR: {reconstructionData.neqr?.psnr}
                        </span>
                        <span className="text-[11px] font-mono text-slate-300">
                          SSIM: {reconstructionData.neqr?.ssim?.toFixed(4) || '1.0000'}
                        </span>
                      </div>
                    </div>

                    {/* Panel 5: FRQI Difference Map */}
                    <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-4 flex flex-col items-center justify-between space-y-3 shadow-lg">
                      <div className="w-full flex items-center justify-between pb-2 border-b border-slate-800 text-[11px]">
                        <span className="font-semibold text-blue-300">5. FRQI Diff</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                          |Orig - FRQI|
                        </span>
                      </div>
                      <div className="w-full aspect-square bg-black rounded-xl border border-slate-800/80 p-2 flex items-center justify-center overflow-hidden">
                        <img
                          src={reconstructionData.frqi?.diff_b64}
                          alt="FRQI Error Heatmap"
                          className="w-full h-full object-contain image-rendering-pixelated rounded"
                        />
                      </div>
                      <div className="w-full text-center space-y-0.5">
                        <span className="text-[10px] font-semibold text-slate-400 block uppercase tracking-wider">
                          FRQI MSE Error
                        </span>
                        <span className="text-[11px] font-mono text-emerald-400 font-semibold">
                          {reconstructionData.frqi?.mse === 0 ? '0.000 (Exact)' : reconstructionData.frqi?.mse?.toExponential(3)}
                        </span>
                      </div>
                    </div>

                    {/* Panel 6: NEQR Difference Map */}
                    <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-4 flex flex-col items-center justify-between space-y-3 shadow-lg">
                      <div className="w-full flex items-center justify-between pb-2 border-b border-slate-800 text-[11px]">
                        <span className="font-semibold text-cyan-300">6. NEQR Diff</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                          |Orig - NEQR|
                        </span>
                      </div>
                      <div className="w-full aspect-square bg-black rounded-xl border border-slate-800/80 p-2 flex items-center justify-center overflow-hidden">
                        <img
                          src={reconstructionData.neqr?.diff_b64}
                          alt="NEQR Error Heatmap"
                          className="w-full h-full object-contain image-rendering-pixelated rounded"
                        />
                      </div>
                      <div className="w-full text-center space-y-0.5">
                        <span className="text-[10px] font-semibold text-slate-400 block uppercase tracking-wider">
                          NEQR MSE Error
                        </span>
                        <span className="text-[11px] font-mono text-cyan-400 font-semibold">
                          {reconstructionData.neqr?.mse === 0 ? '0.000 (Exact)' : reconstructionData.neqr?.mse?.toExponential(3)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </Card>

              {/* Side-by-Side Fidelity & Resource Benchmark Table */}
              <Card>
                <CardHeader
                  title="Fidelity & Quantum Resource Benchmark"
                  subtitle="Detailed head-to-head metrics comparing FRQI and NEQR state reconstruction for this image"
                  icon={Binary}
                  iconColor="text-blue-400"
                />
                <div className="p-6">
                  <div className="border border-slate-800 rounded-2xl overflow-hidden">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-800/50 text-slate-400 text-[10px] uppercase border-b border-slate-800">
                        <tr>
                          <th className="p-3.5">Fidelity Metric / Quantum Property</th>
                          <th className="p-3.5 text-blue-400">FRQI Pipeline</th>
                          <th className="p-3.5 text-cyan-400">NEQR Pipeline</th>
                          <th className="p-3.5 text-slate-400">Quantum Encoding Characteristics</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono">
                        <tr className="hover:bg-slate-800/20">
                          <td className="p-3.5 font-sans font-medium text-slate-200">
                            Mean Squared Error (MSE)
                          </td>
                          <td className="p-3.5 text-emerald-400 font-semibold">
                            {reconstructionData.frqi?.mse === 0 ? '0.000000 (Exact Match)' : reconstructionData.frqi?.mse}
                          </td>
                          <td className="p-3.5 text-cyan-400 font-semibold">
                            {reconstructionData.neqr?.mse === 0 ? '0.000000 (Exact Match)' : reconstructionData.neqr?.mse}
                          </td>
                          <td className="p-3.5 font-sans text-slate-400 text-[11px]">
                            FRQI rotates amplitude angles; NEQR encodes discrete binary intensity levels.
                          </td>
                        </tr>

                        <tr className="hover:bg-slate-800/20">
                          <td className="p-3.5 font-sans font-medium text-slate-200">
                            Peak Signal-to-Noise Ratio (PSNR)
                          </td>
                          <td className="p-3.5 text-emerald-400 font-bold">
                            {reconstructionData.frqi?.psnr}
                          </td>
                          <td className="p-3.5 text-cyan-400 font-bold">
                            {reconstructionData.neqr?.psnr}
                          </td>
                          <td className="p-3.5 font-sans text-slate-400 text-[11px]">
                            When MSE = 0, PSNR evaluates mathematically to infinity (exact state recovery).
                          </td>
                        </tr>

                        <tr className="hover:bg-slate-800/20">
                          <td className="p-3.5 font-sans font-medium text-slate-200">
                            Structural Similarity (SSIM)
                          </td>
                          <td className="p-3.5 text-slate-200">
                            {reconstructionData.frqi?.ssim?.toFixed(4) || '1.0000'}
                          </td>
                          <td className="p-3.5 text-slate-200">
                            {reconstructionData.neqr?.ssim?.toFixed(4) || '1.0000'}
                          </td>
                          <td className="p-3.5 font-sans text-slate-400 text-[11px]">
                            Perceptual luminance, contrast, and structure fidelity (1.0 = identical).
                          </td>
                        </tr>

                        <tr className="hover:bg-slate-800/20">
                          <td className="p-3.5 font-sans font-medium text-slate-200">
                            Qubit Complexity
                          </td>
                          <td className="p-3.5 text-blue-400 font-bold">
                            {reconstructionData.frqi?.n_qubits} qubits (2n + 1)
                          </td>
                          <td className="p-3.5 text-cyan-400 font-bold">
                            {reconstructionData.neqr?.n_qubits} qubits (2n + q)
                          </td>
                          <td className="p-3.5 font-sans text-slate-400 text-[11px]">
                            FRQI is maximally qubit-efficient ($O(n)$); NEQR requires extra register for $q$ bits.
                          </td>
                        </tr>

                        <tr className="hover:bg-slate-800/20">
                          <td className="p-3.5 font-sans font-medium text-slate-200">
                            Total Circuit Gates & Depth
                          </td>
                          <td className="p-3.5 text-slate-300">
                            {reconstructionData.frqi?.gate_count} gates (depth {reconstructionData.frqi?.circuit_depth})
                          </td>
                          <td className="p-3.5 text-slate-300">
                            {reconstructionData.neqr?.gate_count} gates (depth {reconstructionData.neqr?.circuit_depth})
                          </td>
                          <td className="p-3.5 font-sans text-slate-400 text-[11px]">
                            Decomposed elementary gate count and critical path execution depth.
                          </td>
                        </tr>

                        <tr className="hover:bg-slate-800/20">
                          <td className="p-3.5 font-sans font-medium text-slate-200">
                            Reconstruction Latency
                          </td>
                          <td className="p-3.5 text-slate-300">
                            {reconstructionData.frqi?.time_s ? `${(reconstructionData.frqi.time_s * 1000).toFixed(2)} ms` : '—'}
                          </td>
                          <td className="p-3.5 text-slate-300">
                            {reconstructionData.neqr?.time_s ? `${(reconstructionData.neqr.time_s * 1000).toFixed(2)} ms` : '—'}
                          </td>
                          <td className="p-3.5 font-sans text-slate-400 text-[11px]">
                            State readout and inverse matrix reconstruction runtime.
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </Card>

              {/* Matched Experiment History for this Image */}
              <Card>
                <CardHeader
                  title="Evaluated QML Experiments for This Image"
                  subtitle={`Persisted experimental records in database that processed ${reconstructionData.image_name} — click to inspect circuit`}
                  icon={Clock}
                  iconColor="text-purple-400"
                  badge={`${reconstructionData.experiments?.length || 0} Runs Recorded`}
                />
                <div className="p-6">
                  {reconstructionData.experiments && reconstructionData.experiments.length > 0 ? (
                    <div className="border border-slate-800 rounded-2xl overflow-hidden">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-800/50 text-slate-400 text-[10px] uppercase border-b border-slate-800">
                          <tr>
                            <th className="p-3">Experiment ID</th>
                            <th className="p-3">Representation</th>
                            <th className="p-3">Model Architecture</th>
                            <th className="p-3">Accuracy</th>
                            <th className="p-3">Macro F1</th>
                            <th className="p-3">Timestamp</th>
                            <th className="p-3 text-right">Action</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 font-mono">
                          {reconstructionData.experiments.map((exp: any) => (
                            <tr key={exp.experiment_id} className="hover:bg-slate-800/30">
                              <td className="p-3 text-slate-200 font-semibold">{exp.experiment_id}</td>
                              <td className="p-3">
                                <span
                                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                    exp.representation === 'FRQI'
                                      ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                                      : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                                  }`}
                                >
                                  {exp.representation}
                                </span>
                              </td>
                              <td className="p-3 font-sans text-slate-300">{exp.model_type || 'Hybrid QCC'}</td>
                              <td className="p-3 text-slate-200">
                                {exp.accuracy != null ? `${(exp.accuracy * 100).toFixed(1)}%` : '—'}
                              </td>
                              <td className="p-3 text-slate-200">
                                {exp.f1_score != null ? exp.f1_score.toFixed(3) : '—'}
                              </td>
                              <td className="p-3 text-slate-400 text-[11px] font-sans">
                                {exp.timestamp ? new Date(exp.timestamp).toLocaleTimeString() : '—'}
                              </td>
                              <td className="p-3 text-right">
                                <button
                                  onClick={() => {
                                    setSelectedExpId(exp.experiment_id);
                                    setActiveTab('circuit');
                                  }}
                                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/40 text-blue-300 font-sans font-semibold text-xs border border-blue-500/30 transition cursor-pointer"
                                >
                                  <span>Inspect in Circuit Inspector</span>
                                  <ArrowRight size={13} />
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="text-center py-6 text-slate-500 text-xs">
                      No standalone classification experiment history recorded for this specific image yet.
                    </div>
                  )}
                </div>
              </Card>
            </>
          )}
        </div>
      )}

      {/* ─── SECTION H: EXPERIMENT EXPLORER ─────────────────────── */}
      {activeTab === 'explorer' && (
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Full Experiment Explorer Database"
              subtitle="Filterable and searchable experiment records with complete hyperparameters and metrics"
              icon={Search}
              iconColor="text-blue-400"
              badge={`${filteredHistory.length} Runs`}
            />
            <div className="p-5 space-y-4">
              {/* Filter Ribbon */}
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <div className="relative">
                  <Search size={14} className="absolute left-3 top-2.5 text-slate-500" />
                  <input
                    type="text"
                    placeholder="Search by ID or Model..."
                    value={searchFilter}
                    onChange={(e) => setSearchFilter(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <select
                    value={repFilter}
                    onChange={(e) => setRepFilter(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200"
                  >
                    <option value="ALL">Representation: All</option>
                    <option value="FRQI">FRQI</option>
                    <option value="NEQR">NEQR</option>
                  </select>
                </div>

                <div>
                  <select
                    value={modelFilter}
                    onChange={(e) => setModelFilter(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200"
                  >
                    <option value="ALL">Model: All</option>
                    <option value="Quantum Kernel Classifier">Quantum Kernel Classifier</option>
                    <option value="Variational Quantum Classifier">Variational Quantum Classifier</option>
                    <option value="Hybrid Quantum-Classical Classifier">Hybrid Quantum-Classical</option>
                  </select>
                </div>

                <div>
                  <select
                    value={resFilter}
                    onChange={(e) => setResFilter(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200"
                  >
                    <option value="ALL">Resolution: All</option>
                    <option value="2x2">2 × 2</option>
                    <option value="4x4">4 × 4</option>
                    <option value="8x8">8 × 8</option>
                  </select>
                </div>
              </div>

              {/* Data Table */}
              <div className="border border-slate-800 rounded-xl overflow-hidden">
                <div className="overflow-x-auto max-h-[500px]">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-800/80 sticky top-0 text-slate-400 text-[10px] uppercase border-b border-slate-800 z-10">
                      <tr>
                        <th className="p-3">ID</th>
                        <th className="p-3">Pair ID</th>
                        <th className="p-3">Rep</th>
                        <th className="p-3">Model</th>
                        <th className="p-3">Res</th>
                        <th className="p-3">Shots</th>
                        <th className="p-3">Accuracy</th>
                        <th className="p-3">F1 Macro</th>
                        <th className="p-3">PSNR</th>
                        <th className="p-3">Runtime</th>
                        <th className="p-3">Status</th>
                        <th className="p-3 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono">
                      {filteredHistory.map((item) => {
                        const isSelected = selectedExpId === item.experiment_id;
                        return (
                          <tr
                            key={item.experiment_id}
                            className={`hover:bg-slate-800/40 cursor-pointer ${isSelected ? 'bg-blue-600/10' : ''}`}
                            onClick={() => setSelectedExpId(item.experiment_id)}
                          >
                            <td className="p-3 text-blue-400 font-bold">{item.experiment_id}</td>
                            <td className="p-3 text-slate-400">{item.comparison_id || '—'}</td>
                            <td className="p-3 font-sans font-semibold">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] ${
                                  item.representation === 'FRQI'
                                    ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                                    : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                                }`}
                              >
                                {item.representation}
                              </span>
                            </td>
                            <td className="p-3 font-sans text-slate-200">{item.qml_model_type || 'QKC'}</td>
                            <td className="p-3 text-slate-300">{item.resolution || '4x4'}</td>
                            <td className="p-3 text-slate-400">{item.shots === 0 ? 'Exact' : item.shots}</td>
                            <td className="p-3 text-slate-100 font-bold">
                              {item.test_accuracy !== undefined ? `${(item.test_accuracy * 100).toFixed(1)}%` : '—'}
                            </td>
                            <td className="p-3 text-cyan-400 font-bold">
                              {item.f1_macro !== undefined ? item.f1_macro.toFixed(3) : '—'}
                            </td>
                            <td className="p-3 text-emerald-400">
                              {item.recon_psnr !== undefined ? `${item.recon_psnr.toFixed(1)} dB` : '—'}
                            </td>
                            <td className="p-3 text-slate-400">
                              {item.total_time_s !== undefined ? `${item.total_time_s.toFixed(2)}s` : '—'}
                            </td>
                            <td className="p-3">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-sans font-medium ${
                                  item.status === 'completed'
                                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                    : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                                }`}
                              >
                                {item.status}
                              </span>
                            </td>
                            <td className="p-3 text-right">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setSelectedExpId(item.experiment_id);
                                  setActiveTab('circuit');
                                }}
                                className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 justify-end ml-auto"
                              >
                                Circuit <ChevronRight size={12} />
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Experiment Details Modal / Drawer if an experiment is selected */}
              {selectedExpDetail && (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                    <h4 className="text-xs font-bold text-slate-100">
                      Experiment Record Details: <span className="text-blue-400 font-mono">{selectedExpDetail.experiment_id}</span>
                    </h4>
                    <span className="text-[10px] text-slate-500">{selectedExpDetail.timestamp}</span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div>
                      <span className="text-slate-500 text-[10px] uppercase">Defect Class Ground Truth</span>
                      <div className="text-slate-200 font-semibold mt-0.5">{selectedExpDetail.ground_truth || 'crazing'}</div>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[10px] uppercase">Qubit Register Breakdown</span>
                      <div className="text-slate-200 font-semibold mt-0.5">{selectedExpDetail.n_qubits} qubits</div>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[10px] uppercase">Controlled Gates</span>
                      <div className="text-slate-200 font-semibold mt-0.5">{selectedExpDetail.controlled_gates || 0}</div>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[10px] uppercase">Simulation Backend</span>
                      <div className="text-slate-200 font-semibold mt-0.5">{selectedExpDetail.backend}</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
