import React, { useEffect, useState } from 'react';
import { Activity, Database, Grid, Box, Beaker, BarChart2, Cpu, Zap } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface DashboardData {
  dataset: any;
  models: any[];
  quantum: any;
  coverage: any;
  loading: boolean;
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData>({ dataset: null, models: [], quantum: null, loading: true });
  const navigate = useNavigate();

  useEffect(() => {
    async function loadData() {
      try {
        const [ds, mods, qkpis, cov] = await Promise.all([
          fetch('/api/dataset/summary').then(r => r.json()),
          fetch('/api/models/comparison').then(r => r.json()),
          fetch('/api/quantum/kpis').then(r => r.json()),
          fetch('/api/dataset/coverage').then(r => r.json())
        ]);
        setData({ dataset: ds, models: Array.isArray(mods) ? mods : [], quantum: qkpis, coverage: cov, loading: false });
      } catch (e) {
        console.error(e);
        setData(d => ({ ...d, loading: false }));
      }
    }
    loadData();
  }, []);

  const getBestAcc = () => {
    if (!data.models.length) return '—';
    const best = Math.max(...data.models.map(m => m.test_accuracy || 0));
    return (best * 100).toFixed(2) + '%';
  };

  const getBestF1 = () => {
    if (!data.models.length) return '—';
    return Math.max(...data.models.map(m => m.f1_macro || 0)).toFixed(4);
  };

  const KPICard = ({ title, value, icon: Icon, color, onClick }: any) => (
    <div
      onClick={onClick}
      className={`bg-surface/80 backdrop-blur-md border border-border rounded-2xl p-6 hover:-translate-y-1 transition-all shadow-lg hover:shadow-${color}-500/10 group ${onClick ? 'cursor-pointer' : ''}`}
    >
      <div className="flex justify-between items-start mb-4">
        <div className={`p-2.5 bg-${color}-500/10 rounded-xl group-hover:bg-${color}-500/20 transition-colors`}>
          <Icon className={`text-${color}-400`} size={22} />
        </div>
      </div>
      <div className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400 mb-1">
        {data.loading ? <div className="h-9 w-20 bg-slate-800 rounded animate-pulse" /> : (value ?? '—')}
      </div>
      <div className="text-xs text-slate-500 font-semibold tracking-wider uppercase mt-1">{title}</div>
    </div>
  );

  const NavCard = ({ title, description, icon: Icon, color, to }: any) => (
    <div
      onClick={() => navigate(to)}
      className="bg-surface/60 border border-border rounded-2xl p-5 cursor-pointer hover:-translate-y-1 hover:border-blue-500/30 transition-all group"
    >
      <div className={`p-2.5 bg-${color}-500/10 rounded-xl w-fit mb-3 group-hover:bg-${color}-500/20 transition-colors`}>
        <Icon className={`text-${color}-400`} size={20} />
      </div>
      <h3 className="font-semibold text-slate-200 mb-1">{title}</h3>
      <p className="text-sm text-slate-500">{description}</p>
    </div>
  );

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-surface via-slate-900/80 to-blue-950/30 border border-border p-8">
        <div className="absolute top-0 right-0 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-blue-500/30">
              <Zap size={22} className="text-white" />
            </div>
            <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-cyan-400 to-emerald-400">
              Q-ImageLab
            </h1>
          </div>
          <p className="text-lg text-slate-400 max-w-2xl">
            Quantum Image Processing & Surface Defect Analytics Platform
          </p>
          <p className="text-sm text-slate-500 mt-2 max-w-3xl">
            Explore industrial surface defects using classical ML, quantum image representations (FRQI & NEQR), and quantum machine learning.
          </p>
          <div className="flex gap-2 mt-4">
            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">Qiskit</span>
            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Scikit-learn</span>
            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20">NEU-DET</span>
            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">FRQI + NEQR</span>
          </div>
        </div>
      </div>

      {/* Dataset Coverage */}
      <div className="bg-surface/60 border border-border rounded-2xl p-6 shadow-lg">
        <h2 className="text-lg font-semibold text-slate-300 mb-4 flex items-center gap-2">
          <Database size={18} className="text-purple-400" /> Dataset Coverage
        </h2>
        {data.coverage ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-4">
              <div className="flex justify-between text-sm text-slate-400">
                <span>Total images:</span><span className="font-mono text-slate-200">{data.coverage.total_images}</span>
              </div>
              <div className="flex justify-between text-sm text-slate-400">
                <span>Images evaluated:</span><span className="font-mono text-emerald-400">{data.coverage.images_evaluated}</span>
              </div>
              <div className="flex justify-between text-sm text-slate-400">
                <span>Images remaining:</span><span className="font-mono text-amber-400">{data.coverage.images_remaining}</span>
              </div>
              <div className="flex justify-between text-sm text-slate-400">
                <span>Failed:</span><span className="font-mono text-red-400">{data.coverage.failed}</span>
              </div>
              <div className="w-full bg-slate-900 rounded-full h-2 mt-2 border border-slate-700 overflow-hidden">
                <div className="bg-gradient-to-r from-emerald-500 to-cyan-500 h-full rounded-full" style={{ width: `${(data.coverage.images_evaluated / (data.coverage.total_images || 1)) * 100}%` }} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-2">
              {Object.entries(data.coverage.by_class || {}).map(([cls, stats]: [string, any]) => (
                <div key={cls} className="flex justify-between text-sm">
                  <span className="text-slate-400 capitalize">{cls.replace(/[_-]/g, ' ')}</span>
                  <span className="font-mono text-slate-300">
                    <span className={stats.evaluated === stats.total ? 'text-emerald-400' : 'text-slate-300'}>{stats.evaluated}</span> / {stats.total}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="animate-pulse h-24 bg-slate-800/50 rounded-xl"></div>
        )}
      </div>

      {/* Dataset KPIs */}
      <div>
        <h2 className="text-lg font-semibold text-slate-300 mb-4 flex items-center gap-2">
          <Database size={18} className="text-blue-400" /> Dataset Overview
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <KPICard title="Total Images" value={data.dataset?.total_images} icon={Database} color="blue" onClick={() => navigate('/dataset')} />
          <KPICard title="Defect Classes" value={data.dataset?.n_classes} icon={Grid} color="purple" />
          <KPICard title="Train Images" value={data.dataset?.train_total} icon={Database} color="emerald" />
          <KPICard title="Validation" value={data.dataset?.validation_total} icon={Database} color="cyan" />
          <KPICard title="Test Images" value={data.dataset?.test_total} icon={Database} color="amber" />
        </div>
      </div>

      {/* ML & Quantum KPIs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div>
          <h2 className="text-lg font-semibold text-slate-300 mb-4 flex items-center gap-2">
            <BarChart2 size={18} className="text-emerald-400" /> ML Performance
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <KPICard title="Models Evaluated" value={data.models.length || '—'} icon={Activity} color="emerald" onClick={() => navigate('/ml')} />
            <KPICard title="Best Test Accuracy" value={getBestAcc()} icon={BarChart2} color="blue" onClick={() => navigate('/ml')} />
            <KPICard title="Best Macro F1" value={getBestF1()} icon={Activity} color="purple" />
            <KPICard title="Best Model" value={data.models.length ? data.models.sort((a,b) => (b.test_accuracy||0)-(a.test_accuracy||0))[0]?.model : '—'} icon={Cpu} color="cyan" />
          </div>
        </div>
        <div>
          <h2 className="text-lg font-semibold text-slate-300 mb-4 flex items-center gap-2">
            <Beaker size={18} className="text-cyan-400" /> Quantum Processing
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <KPICard title="Experiments Run" value={data.quantum?.n_experiments} icon={Beaker} color="cyan" onClick={() => navigate('/experiments')} />
            <KPICard title="Avg PSNR (dB)" value={data.quantum?.avg_psnr} icon={Activity} color="emerald" />
            <KPICard title="Avg SSIM" value={data.quantum?.avg_ssim} icon={Box} color="blue" />
            <KPICard title="Encoders" value="FRQI + NEQR" icon={Zap} color="purple" onClick={() => navigate('/quantum')} />
          </div>
        </div>
      </div>

      {/* Quick Navigation */}
      <div>
        <h2 className="text-lg font-semibold text-slate-300 mb-4">Quick Navigation</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <NavCard title="Dataset Explorer" description="Browse NEU-DET defect classes and sample images" icon={Database} color="blue" to="/dataset" />
          <NavCard title="ML Analytics" description="Compare SVM, RF, KNN, DT accuracy & metrics" icon={BarChart2} color="emerald" to="/ml" />
          <NavCard title="Quantum Lab" description="Run FRQI/NEQR experiments interactively" icon={Zap} color="cyan" to="/quantum" />
          <NavCard title="Experiment History" description="Browse all stored experiment results" icon={Beaker} color="purple" to="/experiments" />
        </div>
      </div>
    </div>
  );
}
