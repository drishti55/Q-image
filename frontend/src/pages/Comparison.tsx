import React, { useState, useEffect } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  LineChart, Line
} from 'recharts';
import { Layers, Zap, Search, Activity, Camera, BarChart2, Link as LinkIcon } from 'lucide-react';
import { Link } from 'react-router-dom';

const API_BASE = '';

export function Comparison() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Filters
  const [defectClass, setDefectClass] = useState('all');
  const [resolution, setResolution] = useState('all');
  const [shots, setShots] = useState('all');
  
  // Specific image comparison
  const [selectedImagePairId, setSelectedImagePairId] = useState<string>('');
  
  const [frqiCircuit, setFrqiCircuit] = useState<any>(null);
  const [neqrCircuit, setNeqrCircuit] = useState<any>(null);

  useEffect(() => {
    fetchData();
  }, [defectClass, resolution, shots]);
  
  useEffect(() => {
    if (selectedImagePairId && data) {
      const p = data.pairs.find((x: any) => x.pair_id === selectedImagePairId);
      if (p) {
        fetch(`${API_BASE}/api/quantum/circuit?representation=FRQI&size=${p.frqi.image_width}&bits=${p.frqi.intensity_precision}`)
          .then(r => r.json()).then(setFrqiCircuit).catch(console.error);
        fetch(`${API_BASE}/api/quantum/circuit?representation=NEQR&size=${p.neqr.image_width}&bits=${p.neqr.intensity_precision}`)
          .then(r => r.json()).then(setNeqrCircuit).catch(console.error);
      }
    }
  }, [selectedImagePairId, data]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/quantum/compare?defect_class=${defectClass}&resolution=${resolution}&shots=${shots}`);
      if (!res.ok) throw new Error("Failed to fetch comparison data");
      const d = await res.json();
      if (d.error) throw new Error(d.error);
      setData(d);
      if (d.pairs && d.pairs.length > 0 && !selectedImagePairId) {
        setSelectedImagePairId(d.pairs[0].pair_id);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !data) {
    return (
      <div className="p-8 flex justify-center items-center h-full text-slate-400">
        <div className="animate-pulse flex flex-col items-center gap-4">
          <Layers className="h-10 w-10 text-cyan-500 animate-bounce" />
          <p>Crunching comparison data from backend...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-center text-red-400">
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!data || data.coverage.paired === 0) {
    return (
      <div className="p-8 max-w-4xl mx-auto space-y-6">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <Layers className="text-cyan-400" /> FRQI vs NEQR
        </h1>
        <div className="bg-slate-900 border border-slate-700 rounded-xl p-8 text-center text-slate-300">
          <p className="mb-4 text-xl">Insufficient experimental data for comparison.</p>
          <div className="grid grid-cols-3 gap-4 max-w-md mx-auto mb-6">
            <div className="bg-slate-800 p-3 rounded">
               <div className="text-xs text-slate-400">FRQI only</div>
               <div className="text-lg text-white">{data?.coverage?.frqi_only || 0}</div>
            </div>
            <div className="bg-slate-800 p-3 rounded">
               <div className="text-xs text-slate-400">NEQR only</div>
               <div className="text-lg text-white">{data?.coverage?.neqr_only || 0}</div>
            </div>
            <div className="bg-slate-800 p-3 rounded border border-cyan-500/30">
               <div className="text-xs text-cyan-400">Paired</div>
               <div className="text-lg text-white font-bold">{data?.coverage?.paired || 0}</div>
            </div>
          </div>
          <p className="mt-6 text-sm text-slate-400">
            Not enough paired FRQI/NEQR experiments for this configuration. 
            Please run missing experiments in the Quantum Lab.
          </p>
          <Link to="/quantum" className="mt-4 inline-block bg-cyan-600 hover:bg-cyan-500 text-white px-4 py-2 rounded">
            Go to Quantum Lab
          </Link>
        </div>
      </div>
    );
  }

  const selectedPair = data.pairs.find((p: any) => p.pair_id === selectedImagePairId) || data.pairs[0];

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-12">
      
      {/* Header */}
      <div className="space-y-4 text-center md:text-left">
        <h1 className="text-3xl md:text-4xl font-bold text-white flex items-center justify-center md:justify-start gap-3">
          <Layers className="text-cyan-400 h-8 w-8" />
          FRQI vs NEQR
        </h1>
        <p className="text-slate-400 text-lg">Experimental comparison of quantum image representations using NEU surface-defect images.</p>
      </div>

      {/* Coverage Widget */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <h3 className="text-sm font-semibold text-slate-400 mb-4 uppercase tracking-wider">Comparison Coverage</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-950 border border-cyan-500/30 rounded-xl p-4 text-center">
            <div className="text-cyan-400 text-sm font-medium mb-1">Paired Experiments</div>
            <div className="text-3xl font-bold text-white">{data.coverage.paired}</div>
          </div>
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 text-center">
            <div className="text-slate-500 text-sm font-medium mb-1">Total FRQI</div>
            <div className="text-2xl font-bold text-cyan-400">{data.coverage.total_frqi}</div>
          </div>
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 text-center">
            <div className="text-slate-500 text-sm font-medium mb-1">Total NEQR</div>
            <div className="text-2xl font-bold text-purple-400">{data.coverage.total_neqr}</div>
          </div>
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 text-center">
            <div className="text-slate-500 text-sm font-medium mb-1">Missing Pairs</div>
            <div className="text-2xl font-bold text-slate-400">{data.coverage.frqi_only + data.coverage.neqr_only}</div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 backdrop-blur-sm">
        <div className="flex flex-col md:flex-row gap-6 items-end">
          <div className="flex-1 space-y-2">
            <label className="text-xs font-semibold text-slate-500 uppercase">Defect Class</label>
            <select 
              value={defectClass} onChange={(e) => setDefectClass(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Classes</option>
              {data.available_filters.defect_classes.map((c: string) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="flex-1 space-y-2">
            <label className="text-xs font-semibold text-slate-500 uppercase">Resolution</label>
            <select 
              value={resolution} onChange={(e) => setResolution(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Resolutions</option>
              {data.available_filters.resolutions.map((c: string) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="flex-1 space-y-2">
            <label className="text-xs font-semibold text-slate-500 uppercase">Shots</label>
            <select 
              value={shots} onChange={(e) => setShots(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Shots</option>
              {data.available_filters.shots.map((c: string) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* Same Image Comparison */}
      {selectedPair && (
        <section className="space-y-6">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
              <Camera className="text-cyan-500" /> Same Image: FRQI vs NEQR
            </h2>
            <select 
              value={selectedImagePairId} onChange={(e) => setSelectedImagePairId(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 w-full md:w-auto"
            >
              {data.pairs.map((p: any) => (
                <option key={p.pair_id} value={p.pair_id}>
                  {p.image_name} ({p.resolution}, {p.shots} shots)
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Original */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-center space-y-4">
              <h3 className="text-lg font-semibold text-slate-300">Original</h3>
              <div className="aspect-square bg-slate-950 rounded-lg overflow-hidden border border-slate-800 flex items-center justify-center">
                <img 
                  src={`${API_BASE}/api/dataset/image/train/${selectedPair.defect_category}/${selectedPair.image_name}`}
                  alt="Original"
                  className="w-full h-full object-cover"
                />
              </div>
              <div className="text-xs text-slate-500 font-mono text-left space-y-1">
                <p>Image: {selectedPair.image_name}</p>
                <p>Class: {selectedPair.defect_category}</p>
                <p>Resolution: {selectedPair.resolution}</p>
              </div>
            </div>

            {/* FRQI */}
            <div className="bg-slate-900 border border-cyan-500/30 rounded-xl p-6 text-center space-y-4 relative">
              <div className="absolute top-0 right-0 bg-cyan-500 text-slate-950 text-xs font-bold px-3 py-1 rounded-bl-lg rounded-tr-xl">FRQI</div>
              <h3 className="text-lg font-semibold text-cyan-400">Reconstruction</h3>
              <div className="aspect-square bg-slate-950 rounded-lg overflow-hidden border border-slate-800 flex items-center justify-center">
                <img 
                  src={`${API_BASE}/api/quantum/reconstruct?image_name=${selectedPair.image_name}&category=${selectedPair.defect_category}&representation=FRQI&size=${selectedPair.frqi.image_width}&bits=${selectedPair.frqi.intensity_precision}&shots=${selectedPair.frqi.shots}`}
                  alt="FRQI Reconstruction"
                  className="w-full h-full object-contain pixelated"
                  style={{ imageRendering: 'pixelated' }}
                />
              </div>
              <div className="text-xs font-mono text-left grid grid-cols-2 gap-2 mt-4">
                <div className="bg-slate-950 p-2 rounded">
                  <span className="text-slate-500 block mb-1">MSE (lower is better)</span>
                  <span className="text-white text-sm">{selectedPair.frqi.mse.toFixed(4)}</span>
                </div>
                <div className="bg-slate-950 p-2 rounded">
                  <span className="text-slate-500 block mb-1">PSNR (higher is better)</span>
                  <span className="text-white text-sm">{selectedPair.frqi.psnr.toFixed(2)} dB</span>
                </div>
                <div className="bg-slate-950 p-2 rounded">
                  <span className="text-slate-500 block mb-1">SSIM</span>
                  <span className="text-white text-sm">{selectedPair.frqi.ssim.toFixed(4)}</span>
                </div>
                <div className="bg-slate-950 p-2 rounded">
                  <span className="text-slate-500 block mb-1">Total Time</span>
                  <span className="text-white text-sm">{selectedPair.frqi.total_time.toFixed(2)}s</span>
                </div>
              </div>
              <div className="pt-2 text-left">
                <Link to={`/reconstruction?image=${selectedPair.image_name}`} className="text-xs text-cyan-400 hover:underline flex items-center gap-1">
                  <LinkIcon size={12}/> View in Studio
                </Link>
              </div>
            </div>

            {/* NEQR */}
            <div className="bg-slate-900 border border-purple-500/30 rounded-xl p-6 text-center space-y-4 relative">
              <div className="absolute top-0 right-0 bg-purple-500 text-white text-xs font-bold px-3 py-1 rounded-bl-lg rounded-tr-xl">NEQR</div>
              <h3 className="text-lg font-semibold text-purple-400">Reconstruction</h3>
              <div className="aspect-square bg-slate-950 rounded-lg overflow-hidden border border-slate-800 flex items-center justify-center">
                <img 
                  src={`${API_BASE}/api/quantum/reconstruct?image_name=${selectedPair.image_name}&category=${selectedPair.defect_category}&representation=NEQR&size=${selectedPair.neqr.image_width}&bits=${selectedPair.neqr.intensity_precision}&shots=${selectedPair.neqr.shots}`}
                  alt="NEQR Reconstruction"
                  className="w-full h-full object-contain pixelated"
                  style={{ imageRendering: 'pixelated' }}
                />
              </div>
              <div className="text-xs font-mono text-left grid grid-cols-2 gap-2 mt-4">
                <div className="bg-slate-950 p-2 rounded">
                  <span className="text-slate-500 block mb-1">MSE (lower is better)</span>
                  <span className="text-white text-sm">{selectedPair.neqr.mse.toFixed(4)}</span>
                </div>
                <div className="bg-slate-950 p-2 rounded">
                  <span className="text-slate-500 block mb-1">PSNR (higher is better)</span>
                  <span className="text-white text-sm">{selectedPair.neqr.psnr.toFixed(2)} dB</span>
                </div>
                <div className="bg-slate-950 p-2 rounded">
                  <span className="text-slate-500 block mb-1">SSIM</span>
                  <span className="text-white text-sm">{selectedPair.neqr.ssim.toFixed(4)}</span>
                </div>
                <div className="bg-slate-950 p-2 rounded">
                  <span className="text-slate-500 block mb-1">Total Time</span>
                  <span className="text-white text-sm">{selectedPair.neqr.total_time.toFixed(2)}s</span>
                </div>
              </div>
              <div className="pt-2 text-left">
                <Link to={`/reconstruction?image=${selectedPair.image_name}`} className="text-xs text-purple-400 hover:underline flex items-center gap-1">
                  <LinkIcon size={12}/> View in Studio
                </Link>
              </div>
            </div>

          </div>
        </section>
      )}

      {/* Quantum Circuit & Resource Comparison for Selected Pair */}
      {selectedPair && (
        <section className="space-y-6">
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Zap className="text-cyan-500" /> Quantum Circuit Comparison
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* FRQI Circuit */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex flex-col">
               <div className="bg-slate-800/50 p-4 border-b border-slate-700 flex justify-between items-center">
                 <h3 className="font-semibold text-cyan-400">FRQI Resources</h3>
               </div>
               <div className="p-6 text-sm grid grid-cols-2 gap-4">
                 <div><span className="text-slate-500 block">Total Qubits</span><span className="text-white text-lg">{selectedPair.frqi.qubits}</span></div>
                 <div><span className="text-slate-500 block">Gate Count</span><span className="text-white text-lg">{selectedPair.frqi.gate_count}</span></div>
                 <div><span className="text-slate-500 block">Circuit Depth</span><span className="text-white text-lg">{selectedPair.frqi.circuit_depth}</span></div>
                 <div><span className="text-slate-500 block">Measurements</span><span className="text-white text-lg">{selectedPair.frqi.qubits}</span></div>
               </div>
               <div className="bg-slate-950 p-4 border-t border-slate-800 overflow-x-auto text-xs font-mono text-slate-300 leading-relaxed max-h-64 whitespace-pre">
                 {frqiCircuit ? frqiCircuit.qasm || frqiCircuit.visualization || 'Loading circuit...' : 'Loading...'}
               </div>
            </div>
            
            {/* NEQR Circuit */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex flex-col">
               <div className="bg-slate-800/50 p-4 border-b border-slate-700 flex justify-between items-center">
                 <h3 className="font-semibold text-purple-400">NEQR Resources</h3>
               </div>
               <div className="p-6 text-sm grid grid-cols-2 gap-4">
                 <div><span className="text-slate-500 block">Total Qubits</span><span className="text-white text-lg">{selectedPair.neqr.qubits}</span></div>
                 <div><span className="text-slate-500 block">Gate Count</span><span className="text-white text-lg">{selectedPair.neqr.gate_count}</span></div>
                 <div><span className="text-slate-500 block">Circuit Depth</span><span className="text-white text-lg">{selectedPair.neqr.circuit_depth}</span></div>
                 <div><span className="text-slate-500 block">Measurements</span><span className="text-white text-lg">{selectedPair.neqr.qubits}</span></div>
               </div>
               <div className="bg-slate-950 p-4 border-t border-slate-800 overflow-x-auto text-xs font-mono text-slate-300 leading-relaxed max-h-64 whitespace-pre">
                 {neqrCircuit ? neqrCircuit.qasm || neqrCircuit.visualization || 'Loading circuit...' : 'Loading...'}
               </div>
            </div>
          </div>
        </section>
      )}

      {/* Aggregate Charts - Reconstruction Quality */}
      <section className="space-y-6">
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          <Activity className="text-cyan-500" /> Reconstruction Quality (Averages)
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h3 className="text-slate-300 font-semibold mb-6 text-center">Mean MSE (Lower is Better)</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={[
                  { name: 'FRQI', mse: data.overall_stats.frqi?.mse?.mean || 0, fill: '#06b6d4' },
                  { name: 'NEQR', mse: data.overall_stats.neqr?.mse?.mean || 0, fill: '#a855f7' }
                ]}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="name" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc' }} />
                  <Bar dataKey="mse" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="text-xs text-center text-slate-500 mt-2">N = {data.coverage.paired}</div>
          </div>
          
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h3 className="text-slate-300 font-semibold mb-6 text-center">Mean PSNR (Higher is Better)</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={[
                  { name: 'FRQI', psnr: data.overall_stats.frqi?.psnr?.mean || 0, fill: '#06b6d4' },
                  { name: 'NEQR', psnr: data.overall_stats.neqr?.psnr?.mean || 0, fill: '#a855f7' }
                ]}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="name" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" domain={['auto', 'auto']} />
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc' }} />
                  <Bar dataKey="psnr" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="text-xs text-center text-slate-500 mt-2">N = {data.coverage.paired}</div>
          </div>
          
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h3 className="text-slate-300 font-semibold mb-6 text-center">Mean SSIM (Higher is Better)</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={[
                  { name: 'FRQI', ssim: data.overall_stats.frqi?.ssim?.mean || 0, fill: '#06b6d4' },
                  { name: 'NEQR', ssim: data.overall_stats.neqr?.ssim?.mean || 0, fill: '#a855f7' }
                ]}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="name" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" domain={[0, 1]} />
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc' }} />
                  <Bar dataKey="ssim" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="text-xs text-center text-slate-500 mt-2">N = {data.coverage.paired}</div>
          </div>
        </div>
      </section>

      {/* Resolution Scaling */}
      {data.per_resolution && data.per_resolution.length > 1 && (
        <section className="space-y-6">
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <BarChart2 className="text-cyan-500" /> Resolution Scaling
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <h3 className="text-slate-300 font-semibold mb-6 text-center">Qubits vs Resolution</h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.per_resolution}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                    <XAxis dataKey="resolution" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc' }} />
                    <Legend />
                    <Line type="monotone" dataKey="frqi.qubits" name="FRQI Qubits" stroke="#06b6d4" strokeWidth={2} />
                    <Line type="monotone" dataKey="neqr.qubits" name="NEQR Qubits" stroke="#a855f7" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <h3 className="text-slate-300 font-semibold mb-6 text-center">Gate Count vs Resolution</h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.per_resolution}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                    <XAxis dataKey="resolution" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" scale="log" domain={['auto', 'auto']} />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc' }} />
                    <Legend />
                    <Line type="monotone" dataKey="frqi.gate_count" name="FRQI Gates" stroke="#06b6d4" strokeWidth={2} />
                    <Line type="monotone" dataKey="neqr.gate_count" name="NEQR Gates" stroke="#a855f7" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Measurement Shot Analysis */}
      {data.per_shots && data.per_shots.length > 1 && (
        <section className="space-y-6">
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <BarChart2 className="text-cyan-500" /> Measurement Shot Analysis
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <h3 className="text-slate-300 font-semibold mb-6 text-center">PSNR vs Shots</h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.per_shots}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                    <XAxis dataKey="shots" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" domain={['auto', 'auto']} />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc' }} />
                    <Legend />
                    <Line type="monotone" dataKey="frqi.psnr" name="FRQI PSNR" stroke="#06b6d4" strokeWidth={2} />
                    <Line type="monotone" dataKey="neqr.psnr" name="NEQR PSNR" stroke="#a855f7" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
            
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <h3 className="text-slate-300 font-semibold mb-6 text-center">MSE vs Shots</h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.per_shots}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                    <XAxis dataKey="shots" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" domain={['auto', 'auto']} />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc' }} />
                    <Legend />
                    <Line type="monotone" dataKey="frqi.mse" name="FRQI MSE" stroke="#06b6d4" strokeWidth={2} />
                    <Line type="monotone" dataKey="neqr.mse" name="NEQR MSE" stroke="#a855f7" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Per Class Comparison */}
      <section className="space-y-6">
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          <Search className="text-cyan-500" /> Defect-Class Comparison
        </h2>
        
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300 min-w-[800px]">
            <thead className="text-xs uppercase bg-slate-800 text-slate-400">
              <tr>
                <th className="px-4 py-3 rounded-tl-lg">Defect Class</th>
                <th className="px-4 py-3">Paired Count</th>
                <th className="px-4 py-3 text-cyan-400">FRQI MSE</th>
                <th className="px-4 py-3 text-purple-400">NEQR MSE</th>
                <th className="px-4 py-3 text-cyan-400">FRQI PSNR</th>
                <th className="px-4 py-3 text-purple-400">NEQR PSNR</th>
                <th className="px-4 py-3 text-cyan-400">FRQI SSIM</th>
                <th className="px-4 py-3 text-purple-400 rounded-tr-lg">NEQR SSIM</th>
              </tr>
            </thead>
            <tbody>
              {data.per_class.map((c: any, i: number) => (
                <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-800/20">
                  <td className="px-4 py-3 font-semibold text-white capitalize">{c.class}</td>
                  <td className="px-4 py-3">{Math.min(c.frqi.count, c.neqr.count)}</td>
                  <td className="px-4 py-3 text-cyan-200">{c.frqi.mse.toFixed(4)}</td>
                  <td className="px-4 py-3 text-purple-200">{c.neqr.mse.toFixed(4)}</td>
                  <td className="px-4 py-3 text-cyan-200">{c.frqi.psnr.toFixed(2)}</td>
                  <td className="px-4 py-3 text-purple-200">{c.neqr.psnr.toFixed(2)}</td>
                  <td className="px-4 py-3 text-cyan-200">{c.frqi.ssim.toFixed(4)}</td>
                  <td className="px-4 py-3 text-purple-200">{c.neqr.ssim.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Comparison Table */}
      <section className="space-y-6">
        <h2 className="text-2xl font-bold text-white">Statistical Summary Table</h2>
        
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300 min-w-[600px]">
            <thead className="text-xs uppercase bg-slate-800 text-slate-400">
              <tr>
                <th className="px-4 py-3 rounded-tl-lg">Metric</th>
                <th className="px-4 py-3 text-cyan-400">FRQI Mean</th>
                <th className="px-4 py-3 text-purple-400">NEQR Mean</th>
                <th className="px-4 py-3 rounded-tr-lg">Experimentally Better</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-slate-800/50 hover:bg-slate-800/20">
                <td className="px-4 py-3 font-medium">Total Qubits</td>
                <td className="px-4 py-3">{data.overall_stats.frqi?.qubits?.mean.toFixed(2)}</td>
                <td className="px-4 py-3">{data.overall_stats.neqr?.qubits?.mean.toFixed(2)}</td>
                <td className="px-4 py-3 font-bold">{data.win_loss.qubits.frqi > data.win_loss.qubits.neqr ? <span className="text-cyan-400">FRQI (Lower)</span> : <span className="text-purple-400">NEQR (Lower)</span>}</td>
              </tr>
              <tr className="border-b border-slate-800/50 hover:bg-slate-800/20">
                <td className="px-4 py-3 font-medium">Gate Count</td>
                <td className="px-4 py-3">{data.overall_stats.frqi?.gate_count?.mean.toFixed(0)}</td>
                <td className="px-4 py-3">{data.overall_stats.neqr?.gate_count?.mean.toFixed(0)}</td>
                <td className="px-4 py-3 font-bold">{data.win_loss.gate_count.frqi > data.win_loss.gate_count.neqr ? <span className="text-cyan-400">FRQI (Lower)</span> : <span className="text-purple-400">NEQR (Lower)</span>}</td>
              </tr>
              <tr className="border-b border-slate-800/50 hover:bg-slate-800/20">
                <td className="px-4 py-3 font-medium">Circuit Depth</td>
                <td className="px-4 py-3">{data.overall_stats.frqi?.circuit_depth?.mean.toFixed(0)}</td>
                <td className="px-4 py-3">{data.overall_stats.neqr?.circuit_depth?.mean.toFixed(0)}</td>
                <td className="px-4 py-3 font-bold">{data.win_loss.circuit_depth.frqi > data.win_loss.circuit_depth.neqr ? <span className="text-cyan-400">FRQI (Lower)</span> : <span className="text-purple-400">NEQR (Lower)</span>}</td>
              </tr>
              <tr className="border-b border-slate-800/50 hover:bg-slate-800/20">
                <td className="px-4 py-3 font-medium">Simulation Time (s)</td>
                <td className="px-4 py-3">{data.overall_stats.frqi?.total_time?.mean.toFixed(4)}</td>
                <td className="px-4 py-3">{data.overall_stats.neqr?.total_time?.mean.toFixed(4)}</td>
                <td className="px-4 py-3 font-bold">{data.win_loss.total_time.frqi > data.win_loss.total_time.neqr ? <span className="text-cyan-400">FRQI (Lower)</span> : <span className="text-purple-400">NEQR (Lower)</span>}</td>
              </tr>
              <tr className="border-b border-slate-800/50 hover:bg-slate-800/20">
                <td className="px-4 py-3 font-medium">MSE</td>
                <td className="px-4 py-3">{data.overall_stats.frqi?.mse?.mean.toFixed(4)}</td>
                <td className="px-4 py-3">{data.overall_stats.neqr?.mse?.mean.toFixed(4)}</td>
                <td className="px-4 py-3 font-bold">{data.win_loss.mse.frqi > data.win_loss.mse.neqr ? <span className="text-cyan-400">FRQI (Lower)</span> : data.win_loss.mse.neqr > data.win_loss.mse.frqi ? <span className="text-purple-400">NEQR (Lower)</span> : <span className="text-slate-400">Similar</span>}</td>
              </tr>
              <tr className="border-b border-slate-800/50 hover:bg-slate-800/20">
                <td className="px-4 py-3 font-medium">PSNR (dB)</td>
                <td className="px-4 py-3">{data.overall_stats.frqi?.psnr?.mean.toFixed(2)}</td>
                <td className="px-4 py-3">{data.overall_stats.neqr?.psnr?.mean.toFixed(2)}</td>
                <td className="px-4 py-3 font-bold">{data.win_loss.psnr.frqi > data.win_loss.psnr.neqr ? <span className="text-cyan-400">FRQI (Higher)</span> : data.win_loss.psnr.neqr > data.win_loss.psnr.frqi ? <span className="text-purple-400">NEQR (Higher)</span> : <span className="text-slate-400">Similar</span>}</td>
              </tr>
              <tr className="border-b border-slate-800/50 hover:bg-slate-800/20">
                <td className="px-4 py-3 font-medium">SSIM</td>
                <td className="px-4 py-3">{data.overall_stats.frqi?.ssim?.mean.toFixed(4)}</td>
                <td className="px-4 py-3">{data.overall_stats.neqr?.ssim?.mean.toFixed(4)}</td>
                <td className="px-4 py-3 font-bold">{data.win_loss.ssim.frqi > data.win_loss.ssim.neqr ? <span className="text-cyan-400">FRQI (Higher)</span> : data.win_loss.ssim.neqr > data.win_loss.ssim.frqi ? <span className="text-purple-400">NEQR (Higher)</span> : <span className="text-slate-400">Similar</span>}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* Win/Loss Summary */}
      <section className="space-y-6">
        <h2 className="text-2xl font-bold text-white">Win / Loss Summary</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-slate-900 border border-cyan-500/30 rounded-xl p-6 text-center">
            <h3 className="text-cyan-400 font-bold text-xl mb-2">FRQI Better In</h3>
            <div className="text-4xl font-bold text-white">
              {[
                data.win_loss.qubits.frqi > data.win_loss.qubits.neqr,
                data.win_loss.gate_count.frqi > data.win_loss.gate_count.neqr,
                data.win_loss.circuit_depth.frqi > data.win_loss.circuit_depth.neqr,
                data.win_loss.total_time.frqi > data.win_loss.total_time.neqr,
                data.win_loss.mse.frqi > data.win_loss.mse.neqr,
                data.win_loss.psnr.frqi > data.win_loss.psnr.neqr,
                data.win_loss.ssim.frqi > data.win_loss.ssim.neqr
              ].filter(Boolean).length}
            </div>
            <div className="text-sm text-slate-500 mt-2">metrics (on average)</div>
          </div>
          <div className="bg-slate-900 border border-purple-500/30 rounded-xl p-6 text-center">
            <h3 className="text-purple-400 font-bold text-xl mb-2">NEQR Better In</h3>
            <div className="text-4xl font-bold text-white">
              {[
                data.win_loss.qubits.neqr > data.win_loss.qubits.frqi,
                data.win_loss.gate_count.neqr > data.win_loss.gate_count.frqi,
                data.win_loss.circuit_depth.neqr > data.win_loss.circuit_depth.frqi,
                data.win_loss.total_time.neqr > data.win_loss.total_time.frqi,
                data.win_loss.mse.neqr > data.win_loss.mse.frqi,
                data.win_loss.psnr.neqr > data.win_loss.psnr.frqi,
                data.win_loss.ssim.neqr > data.win_loss.ssim.frqi
              ].filter(Boolean).length}
            </div>
            <div className="text-sm text-slate-500 mt-2">metrics (on average)</div>
          </div>
          <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 text-center">
            <h3 className="text-slate-400 font-bold text-xl mb-2">Similar</h3>
            <div className="text-4xl font-bold text-white">
              {[
                data.win_loss.qubits.frqi === data.win_loss.qubits.neqr,
                data.win_loss.gate_count.frqi === data.win_loss.gate_count.neqr,
                data.win_loss.circuit_depth.frqi === data.win_loss.circuit_depth.neqr,
                data.win_loss.total_time.frqi === data.win_loss.total_time.neqr,
                data.win_loss.mse.frqi === data.win_loss.mse.neqr,
                data.win_loss.psnr.frqi === data.win_loss.psnr.neqr,
                data.win_loss.ssim.frqi === data.win_loss.ssim.neqr
              ].filter(Boolean).length}
            </div>
            <div className="text-sm text-slate-500 mt-2">metrics</div>
          </div>
        </div>
      </section>

      {/* Quantum Trade-offs & Auto-Generated Interpretation */}
      <section className="space-y-6">
        <h2 className="text-2xl font-bold text-white">Quantum Trade-offs & Analysis</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
            <h3 className="text-lg font-bold text-white mb-2">Theoretical vs Observed</h3>
            
            <div className="space-y-2">
              <h4 className="text-sm font-semibold text-slate-400 uppercase">Potential Advantage</h4>
              <p className="text-sm text-slate-300 bg-slate-950 p-3 rounded border border-slate-800">
                FRQI promises logarithmic qubit scaling for intensity representation (1 qubit), while NEQR promises exact fidelity retention by utilizing $q$ intensity qubits.
              </p>
            </div>
            
            <div className="space-y-2">
              <h4 className="text-sm font-semibold text-slate-400 uppercase">Observed Advantage</h4>
              <p className="text-sm text-slate-300 bg-slate-950 p-3 rounded border border-slate-800">
                Empirically across the {data.coverage.paired} paired images, {data.overall_stats.frqi?.gate_count?.mean < data.overall_stats.neqr?.gate_count?.mean ? "FRQI strictly verified the lower resource footprint (Gates: " + data.overall_stats.frqi?.gate_count?.mean.toFixed(0) + " vs " + data.overall_stats.neqr?.gate_count?.mean.toFixed(0) + ")." : "NEQR actually showed lower resource usage."} 
                {data.overall_stats.neqr?.psnr?.mean > data.overall_stats.frqi?.psnr?.mean ? " However, NEQR verified its claim of superior classical reconstruction fidelity." : " Surprisingly, FRQI also showed better reconstruction fidelity."}
              </p>
            </div>
            
            <div className="space-y-2">
              <h4 className="text-sm font-semibold text-slate-400 uppercase">Current Limitations</h4>
              <p className="text-sm text-slate-300 bg-red-950/20 p-3 rounded border border-red-500/20 text-red-200">
                Evaluations are strictly simulator-based (ideal conditions). The exponential gate depth of NEQR makes it highly susceptible to decoherence on real NISQ hardware, meaning practical advantage remains unverified. Current classical simulations are also constrained to heavily downscaled images ({resolution === 'all' ? 'max 8x8' : resolution}).
              </p>
            </div>
          </div>
          
          <div className="bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col h-full">
            <h3 className="text-lg font-bold text-white mb-4">What Do the Results Show?</h3>
            <div className="prose prose-invert max-w-none text-slate-300 flex-1 flex flex-col justify-center">
              <ul className="space-y-5">
                <li className="flex gap-3">
                  <div className="mt-1 h-2 w-2 rounded-full bg-cyan-500 shrink-0"></div>
                  <span className="text-sm leading-relaxed">
                    <strong>Resource Utilization:</strong> Under the tested configurations, 
                    {data.overall_stats.frqi?.qubits?.mean < data.overall_stats.neqr?.qubits?.mean ? " FRQI required significantly fewer qubits than NEQR." : " NEQR required fewer qubits than FRQI."}
                    {data.overall_stats.frqi?.gate_count?.mean < data.overall_stats.neqr?.gate_count?.mean ? " Furthermore, FRQI maintained a shallower circuit depth and lower total gate count, making it more favorable for near-term (NISQ) devices." : " Furthermore, NEQR exhibited a more compact circuit depth and lower gate count."}
                  </span>
                </li>
                <li className="flex gap-3">
                  <div className="mt-1 h-2 w-2 rounded-full bg-purple-500 shrink-0"></div>
                  <span className="text-sm leading-relaxed">
                    <strong>Reconstruction Quality:</strong> In terms of fidelity, 
                    {data.overall_stats.neqr?.psnr?.mean > data.overall_stats.frqi?.psnr?.mean ? 
                      " NEQR consistently demonstrated superior reconstruction quality. The mean PSNR for NEQR was higher, and the MSE was lower. This confirms that storing exact pixel intensities in basis states (NEQR) offers better structural retention compared to encoding intensities into a single probability amplitude (FRQI)." 
                      : " FRQI surprisingly demonstrated superior reconstruction quality under these conditions, achieving a higher PSNR and lower MSE."}
                  </span>
                </li>
                <li className="flex gap-3">
                  <div className="mt-1 h-2 w-2 rounded-full bg-orange-500 shrink-0"></div>
                  <span className="text-sm leading-relaxed">
                    <strong>Conclusion:</strong>
                    {data.overall_stats.frqi?.gate_count?.mean < data.overall_stats.neqr?.gate_count?.mean && data.overall_stats.neqr?.psnr?.mean > data.overall_stats.frqi?.psnr?.mean ? 
                      " FRQI is more resource-efficient but suffers from worse measurement variance and image quality, while NEQR provides higher fidelity at the cost of exponentially larger circuits." : 
                      " The observed results differ from theoretical expectations for these parameters."} 
                  </span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

    </div>
  );
}
