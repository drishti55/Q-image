import React, { useEffect, useState } from 'react';
import { Beaker, Search, ChevronLeft, ChevronRight } from 'lucide-react';

export default function Experiments() {
  const [experiments, setExperiments] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [repFilter, setRepFilter] = useState('all');
  const limit = 50;

  useEffect(() => {
    setLoading(true);
    fetch(`/api/quantum/experiments?limit=${limit}&offset=${page * limit}&representation=${repFilter}`)
      .then(r => r.json())
      .then(d => {
        setExperiments(d.experiments || []);
        setTotal(d.total || 0);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [page, repFilter]);

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-100 to-slate-400 mb-1">Experiment Lab</h1>
        <p className="text-slate-400">{total} quantum image processing experiments stored</p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="flex bg-surface border border-border rounded-lg p-1">
          {['all', 'FRQI', 'NEQR'].map(r => (
            <button key={r} onClick={() => { setRepFilter(r); setPage(0); }}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
                repFilter === r ? 'bg-blue-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
            >{r === 'all' ? 'All' : r}</button>
          ))}
        </div>
        <span className="text-sm text-slate-500 ml-auto">
          Page {page + 1} of {totalPages || 1} • Showing {experiments.length} of {total}
        </span>
      </div>

      {/* Table */}
      <div className="bg-surface border border-border rounded-2xl overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900/60 text-slate-400 font-medium border-b border-border text-xs uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3.5">ID</th>
                <th className="px-4 py-3.5">Image</th>
                <th className="px-4 py-3.5">Defect</th>
                <th className="px-4 py-3.5">Type</th>
                <th className="px-4 py-3.5">Resolution</th>
                <th className="px-4 py-3.5">Qubits</th>
                <th className="px-4 py-3.5">Gates</th>
                <th className="px-4 py-3.5">Depth</th>
                <th className="px-4 py-3.5">Shots</th>
                <th className="px-4 py-3.5">MSE</th>
                <th className="px-4 py-3.5">PSNR (dB)</th>
                <th className="px-4 py-3.5">SSIM</th>
                <th className="px-4 py-3.5">Time (s)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/30">
              {loading ? (
                Array.from({ length: 10 }).map((_, i) => (
                  <tr key={i}><td colSpan={13} className="px-4 py-3"><div className="h-4 bg-slate-800 rounded animate-pulse" /></td></tr>
                ))
              ) : experiments.length === 0 ? (
                <tr>
                  <td colSpan={13} className="px-6 py-12 text-center text-slate-500">
                    <Beaker size={32} className="mx-auto mb-3 text-slate-700" />
                    <p className="text-base font-medium">No quantum experiments yet.</p>
                    <p className="text-sm mt-1">Select an image and configuration to run your first experiment.</p>
                  </td>
                </tr>
              ) : (
                experiments.map((exp, i) => (
                  <tr key={i} className="hover:bg-slate-800/20 transition-colors text-slate-300 text-xs">
                    <td className="px-4 py-3 font-mono text-blue-400 text-[11px]">{exp.experiment_id?.substring(0, 12) || `EXP-${i}`}</td>
                    <td className="px-4 py-3 truncate max-w-[120px]" title={exp.image_name}>{exp.image_name}</td>
                    <td className="px-4 py-3 capitalize">{exp.defect_category?.replace(/[_-]/g, ' ') || '—'}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        exp.representation === 'NEQR'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                      }`}>{exp.representation}</span>
                    </td>
                    <td className="px-4 py-3 font-mono">{exp.resolution}</td>
                    <td className="px-4 py-3 font-mono">{exp.qubits}</td>
                    <td className="px-4 py-3 font-mono">{exp.gate_count}</td>
                    <td className="px-4 py-3 font-mono">{exp.circuit_depth}</td>
                    <td className="px-4 py-3 font-mono">{exp.shots}</td>
                    <td className="px-4 py-3 font-mono">{exp.mse != null ? (typeof exp.mse === 'number' ? exp.mse.toFixed(2) : exp.mse) : '—'}</td>
                    <td className="px-4 py-3 font-mono text-emerald-400">
                      {exp.psnr != null ? (exp.psnr === Infinity || exp.psnr > 999 ? '∞' : typeof exp.psnr === 'number' ? exp.psnr.toFixed(2) : exp.psnr) : '—'}
                    </td>
                    <td className="px-4 py-3 font-mono text-emerald-400">
                      {exp.ssim != null ? (typeof exp.ssim === 'number' ? exp.ssim.toFixed(4) : exp.ssim) : '—'}
                    </td>
                    <td className="px-4 py-3 font-mono">{exp.total_time != null ? (typeof exp.total_time === 'number' ? exp.total_time.toFixed(2) : exp.total_time) : '—'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
            className="p-2 rounded-lg bg-surface border border-border text-slate-400 hover:text-white disabled:opacity-30">
            <ChevronLeft size={18} />
          </button>
          <span className="text-sm text-slate-400">Page {page + 1} of {totalPages}</span>
          <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}
            className="p-2 rounded-lg bg-surface border border-border text-slate-400 hover:text-white disabled:opacity-30">
            <ChevronRight size={18} />
          </button>
        </div>
      )}
    </div>
  );
}
