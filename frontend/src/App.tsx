import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom';
import { Activity, Beaker, Box, Settings, Image as ImageIcon, LayoutDashboard, BarChart2, Zap, Layout, Grid } from 'lucide-react';
import React, { useEffect, useState } from 'react';

import Dashboard from './pages/Dashboard';
import DatasetExplorer from './pages/DatasetExplorer';
import MLAnalytics from './pages/MLAnalytics';
import QuantumLab from './pages/QuantumLab';
import CircuitAnalyzer from './pages/CircuitAnalyzer';
import Reconstruction from './pages/Reconstruction';
import Experiments from './pages/Experiments';
import ConfusionMatrix from './pages/ConfusionMatrix';
import SettingsPage from './pages/Settings';
import { Comparison } from './pages/Comparison';
import QuantumCompareLab from './pages/QuantumCompareLab';
const SidebarItem = ({ icon: Icon, label, to }: { icon: any; label: string; to: string }) => {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all duration-200 ${
          isActive
            ? 'bg-blue-600/15 text-blue-400 border border-blue-500/25 shadow-[0_0_12px_rgba(59,130,246,0.08)]'
            : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.03]'
        }`
      }
    >
      <Icon size={18} className="stroke-[1.5] shrink-0" />
      <span className="font-medium text-sm">{label}</span>
    </NavLink>
  );
};

const LayoutComponent = ({ children }: { children: React.ReactNode }) => {
  const location = useLocation();
  const [status, setStatus] = useState<any>(null);

  const titleMap: Record<string, string> = {
    '/': 'Dashboard',
    '/dataset': 'Dataset Explorer',
    '/ml': 'ML Analytics',
    '/quantum': 'Quantum Lab',
    '/circuit': 'Circuit Analyzer',
    '/reconstruction': 'Reconstruction Studio',
    '/experiments': 'Experiment Lab',
    '/confusion-matrix': 'Confusion Matrix',
    '/settings': 'Settings',
    '/compare': 'FRQI vs NEQR',
    '/quantum-compare-lab': 'Quantum Compare Lab',
  };

  useEffect(() => {
    fetch('/api/status')
      .then(r => r.json())
      .then(setStatus)
      .catch(() => setStatus({ backend: 'offline' }));
  }, []);

  const pageTitle = titleMap[location.pathname] || 'Dashboard';

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background font-sans">
      {/* Sidebar */}
      <div className="w-60 flex flex-col border-r border-border bg-surface shadow-xl z-20 shrink-0">
        <div className="h-14 flex items-center px-5 border-b border-border">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-blue-500/30">
              <Zap size={16} className="text-white" />
            </div>
            <span className="font-bold text-base tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">
              Q-ImageLab
            </span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto py-4 px-3 flex flex-col gap-0.5">
          <div className="px-3 mb-1.5 text-[10px] font-bold text-slate-600 uppercase tracking-[0.15em]">Overview</div>
          <SidebarItem to="/" icon={LayoutDashboard} label="Dashboard" />
          <SidebarItem to="/dataset" icon={ImageIcon} label="Dataset Explorer" />
          <SidebarItem to="/ml" icon={BarChart2} label="ML Analytics" />
          <SidebarItem to="/confusion-matrix" icon={Grid} label="Confusion Matrix" />

          <div className="px-3 mt-5 mb-1.5 text-[10px] font-bold text-slate-600 uppercase tracking-[0.15em]">Quantum Core</div>
          <SidebarItem to="/quantum" icon={Activity} label="Quantum Lab" />
          <SidebarItem to="/circuit" icon={Box} label="Circuit Analyzer" />
          <SidebarItem to="/reconstruction" icon={Layout} label="Reconstruction" />
          <SidebarItem to="/experiments" icon={Beaker} label="Experiments" />
          <SidebarItem to="/compare" icon={Activity} label="FRQI vs NEQR" />
          <SidebarItem to="/quantum-compare-lab" icon={Activity} label="Quantum Compare Lab" />
        </div>

        <div className="p-3 border-t border-border">
          <SidebarItem to="/settings" icon={Settings} label="Settings" />
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden relative min-w-0">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-blue-950/10 via-background to-background pointer-events-none z-0" />

        {/* Topbar */}
        <div className="h-14 border-b border-border/50 bg-surface/60 backdrop-blur-lg flex items-center justify-between px-6 z-10 sticky top-0 shrink-0">
          <div>
            <h1 className="font-semibold text-slate-100 text-sm">{pageTitle}</h1>
            <div className="text-[11px] text-slate-500">Q-ImageLab / {pageTitle}</div>
          </div>

          <div className="flex items-center gap-3">
            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-medium ${
              status?.backend === 'online'
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                : 'bg-red-500/10 border-red-500/20 text-red-400'
            }`}>
              <div className={`w-1.5 h-1.5 rounded-full ${status?.backend === 'online' ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`} />
              {status?.backend === 'online' ? 'Backend Online' : 'Backend Offline'}
            </div>
            {status?.dataset_available && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-[11px] font-medium text-blue-400">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                Dataset Ready
              </div>
            )}
            {status?.experiments_available && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-[11px] font-medium text-cyan-400">
                <div className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                Simulator Ready
              </div>
            )}
          </div>
        </div>

        {/* Page Content */}
        <div className="flex-1 overflow-y-auto p-6 z-10 relative">
          {children}
        </div>
      </div>
    </div>
  );
};

export default function App() {
  return (
    <BrowserRouter>
      <LayoutComponent>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/dataset" element={<DatasetExplorer />} />
          <Route path="/ml" element={<MLAnalytics />} />
          <Route path="/confusion-matrix" element={<ConfusionMatrix />} />
          <Route path="/quantum" element={<QuantumLab />} />
          <Route path="/circuit" element={<CircuitAnalyzer />} />
          <Route path="/reconstruction" element={<Reconstruction />} />
          <Route path="/experiments" element={<Experiments />} />
          <Route path="/compare" element={<Comparison />} />
          <Route path="/quantum-compare-lab" element={<QuantumCompareLab />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </LayoutComponent>
    </BrowserRouter>
  );
}
