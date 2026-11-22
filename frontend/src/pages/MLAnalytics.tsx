import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis } from 'recharts';
import { Trophy, Activity, Clock, BarChart2 } from 'lucide-react';

export default function MLAnalytics() {
  const [models, setModels] = useState<any[]>([]);
  const [perClass, setPerClass] = useState<any[]>([]);
  const [confusionMatrices, setConfusionMatrices] = useState<any[]>([]);
  const [selectedCM, setSelectedCM] = useState<any>(null);
  const [cmData, setCmData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch('/api/models/comparison').then(r => r.json()),
      fetch('/api/models/per-class-metrics').then(r => r.json()),
      fetch('/api/models/confusion-matrices').then(r => r.json()),
    ]).then(([mods, pc, cms]) => {
      setModels(Array.isArray(mods) ? mods : []);
      setPerClass(Array.isArray(pc) ? pc : []);
      setConfusionMatrices(Array.isArray(cms) ? cms : []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const loadCM = async (name: string) => {
    setSelectedCM(name);
    const csvFile = confusionMatrices.find(f => f.name === name && f.type === '.csv');
    if (csvFile) {
      const data = await fetch(csvFile.url).then(r => r.json());
      setCmData(data);
    }
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload?.length) {
      return (
        <div className="bg-surface/95 backdrop-blur border border-border p-3 rounded-xl shadow-xl text-sm">
          <p className="font-bold text-slate-200 mb-1">{label}</p>
          {payload.map((e: any, i: number) => (
            <p key={i} style={{ color: e.color }}>{e.name}: {typeof e.value === 'number' ? e.value.toFixed(4) : e.value}</p>
          ))}
        </div>
      );
    }
    return null;
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-10 w-48 bg-surface rounded animate-pulse" />
        <div className="grid grid-cols-2 gap-6">
          <div className="h-96 bg-surface rounded-2xl animate-pulse border border-border" />
          <div className="h-96 bg-surface rounded-2xl animate-pulse border border-border" />
        </div>
      </div>
    );
  }

  if (models.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-slate-500">
        <BarChart2 size={48} className="mb-4 text-slate-700" />
        <p className="text-lg font-medium">No ML evaluation results found.</p>
        <p className="text-sm mt-1">Run the model evaluation pipeline first.</p>
      </div>
    );
  }

  const sorted = [...models].sort((a, b) => (b.test_accuracy || 0) - (a.test_accuracy || 0));

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-100 to-slate-400 mb-1">ML Analytics</h1>
        <p className="text-slate-400">{models.length} classical ML models evaluated on NEU-DET dataset</p>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-surface border border-border rounded-2xl p-6 shadow-lg">
          <h3 className="text-base font-semibold text-slate-200 mb-6 flex items-center gap-2">
            <Trophy className="text-amber-400" size={18} /> Accuracy Comparison
          </h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sorted} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis dataKey="model" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} domain={[0, 1]} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ paddingTop: 16 }} />
                <Bar dataKey="val_accuracy" name="Val Acc" fill="#3b82f6" radius={[6, 6, 0, 0]} />
                <Bar dataKey="test_accuracy" name="Test Acc" fill="#10b981" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-surface border border-border rounded-2xl p-6 shadow-lg">
          <h3 className="text-base font-semibold text-slate-200 mb-6 flex items-center gap-2">
            <Activity className="text-cyan-400" size={18} /> F1 & Precision/Recall
          </h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sorted} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis dataKey="model" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} domain={[0, 1]} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ paddingTop: 16 }} />
                <Bar dataKey="precision_macro" name="Precision" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
                <Bar dataKey="recall_macro" name="Recall" fill="#f59e0b" radius={[6, 6, 0, 0]} />
                <Bar dataKey="f1_macro" name="Macro F1" fill="#06b6d4" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Leaderboard */}
      <div className="bg-surface border border-border rounded-2xl overflow-hidden shadow-lg">
        <div className="p-5 border-b border-border">
          <h3 className="text-base font-semibold text-slate-200 flex items-center gap-2">
            <Trophy className="text-amber-400" size={18} /> Model Leaderboard
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900/60 text-slate-400 font-medium border-b border-border">
              <tr>
                <th className="px-5 py-3.5">Rank</th>
                <th className="px-5 py-3.5">Model</th>
                <th className="px-5 py-3.5">Val Acc</th>
                <th className="px-5 py-3.5">Test Acc</th>
                <th className="px-5 py-3.5">Precision</th>
                <th className="px-5 py-3.5">Recall</th>
                <th className="px-5 py-3.5">F1 Macro</th>
                <th className="px-5 py-3.5">F1 Weighted</th>
                <th className="px-5 py-3.5">CV Mean</th>
                <th className="px-5 py-3.5 flex items-center gap-1"><Clock size={14} /> Train Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/40">
              {sorted.map((m, i) => (
                <tr key={m.model} className="hover:bg-slate-800/30 transition-colors text-slate-300">
                  <td className="px-5 py-3.5 font-semibold">
                    {i === 0 ? <span className="text-amber-400 flex items-center gap-1"><Trophy size={14} /> 1st</span> :
                     i === 1 ? <span className="text-slate-300">2nd</span> :
                     i === 2 ? <span className="text-amber-700">3rd</span> :
                     `#${i + 1}`}
                  </td>
                  <td className="px-5 py-3.5 font-medium text-blue-400">{m.model}</td>
                  <td className="px-5 py-3.5">{(m.val_accuracy * 100).toFixed(2)}%</td>
                  <td className="px-5 py-3.5 text-emerald-400 font-medium">{(m.test_accuracy * 100).toFixed(2)}%</td>
                  <td className="px-5 py-3.5">{(m.precision_macro * 100).toFixed(2)}%</td>
                  <td className="px-5 py-3.5">{(m.recall_macro * 100).toFixed(2)}%</td>
                  <td className="px-5 py-3.5 font-mono">{m.f1_macro.toFixed(4)}</td>
                  <td className="px-5 py-3.5 font-mono">{m.f1_weighted.toFixed(4)}</td>
                  <td className="px-5 py-3.5 font-mono">{m.cv_mean?.toFixed(4) || '—'}</td>
                  <td className="px-5 py-3.5 font-mono text-xs">{m.training_time_s?.toFixed(3) || '—'}s</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Confusion Matrices */}
      {confusionMatrices.length > 0 && (
        <div className="bg-surface border border-border rounded-2xl p-6 shadow-lg">
          <h3 className="text-base font-semibold text-slate-200 mb-4">Confusion Matrices</h3>
          <div className="flex gap-2 mb-6">
            {confusionMatrices.filter(f => f.type === '.csv').map(f => (
              <button key={f.name} onClick={() => loadCM(f.name)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  selectedCM === f.name ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30' : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200'
                }`}>
                {f.name.replace(/_/g, ' ')}
              </button>
            ))}
          </div>
          {cmData && (
            <div className="overflow-x-auto">
              <table className="text-sm border-collapse">
                <thead>
                  <tr>
                    <th className="px-3 py-2 text-slate-500 text-xs">Pred →</th>
                    {cmData.labels.map((l: string) => (
                      <th key={l} className="px-3 py-2 text-blue-400 text-xs font-medium capitalize">{l.replace(/[_-]/g, ' ')}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {cmData.matrix.map((row: number[], ri: number) => (
                    <tr key={ri}>
                      <td className="px-3 py-2 text-blue-400 text-xs font-medium capitalize">{cmData.labels[ri].replace(/[_-]/g, ' ')}</td>
                      {row.map((val: number, ci: number) => {
                        const maxVal = Math.max(...cmData.matrix.flat());
                        const intensity = maxVal > 0 ? val / maxVal : 0;
                        return (
                          <td key={ci}
                            className="px-3 py-2 text-center font-mono text-xs border border-slate-800"
                            style={{
                              backgroundColor: ri === ci
                                ? `rgba(16, 185, 129, ${0.1 + intensity * 0.5})`
                                : `rgba(239, 68, 68, ${intensity * 0.3})`,
                              color: intensity > 0.5 ? '#fff' : '#94a3b8'
                            }}>
                            {val}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
