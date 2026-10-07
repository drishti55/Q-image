import React, { useState, useRef, useEffect } from 'react';
import { Upload, Image as ImageIcon, Zap, Settings, Play, CheckCircle2, Activity, BarChart2 } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, BarChart, Bar, Legend } from 'recharts';

export default function QuantumCompareLab() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [resolution, setResolution] = useState('4x4');
  const [precision, setPrecision] = useState(8);
  const [shots, setShots] = useState(1024);
  const [isHovering, setIsHovering] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
      const reader = new FileReader();
      reader.onload = (e) => setPreview(e.target?.result as string);
      reader.readAsDataURL(selected);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsHovering(false);
    const selected = e.dataTransfer.files?.[0];
    if (selected && selected.type.startsWith('image/')) {
      setFile(selected);
      const reader = new FileReader();
      reader.onload = (e) => setPreview(e.target?.result as string);
      reader.readAsDataURL(selected);
    }
  };

  const runComparison = async () => {
    if (!file) return;
    setRunning(true);
    setError(null);
    setResults(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('resolution', resolution);
    formData.append('precision', precision.toString());
    formData.append('shots', shots.toString());

    try {
      const response = await fetch('/api/quantum/compare-custom', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      
      if (data.error) {
        setError(data.error);
      } else {
        setResults(data);
      }
    } catch (err: any) {
      setError(err.message || 'An error occurred during the experiment.');
    } finally {
      setRunning(false);
    }
  };

  const getPosQubits = (res: string) => {
    const s = parseInt(res.split('x')[0]);
    return Math.log2(s * s);
  };

  return (
    <div className="flex flex-col gap-6 w-full max-w-7xl mx-auto pb-10">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Zap className="text-yellow-400" size={32} /> Quantum Compare Lab
          </h1>
          <p className="text-slate-400 text-sm mt-2 max-w-3xl">
            Upload an image and experimentally compare FRQI and NEQR under identical processing conditions.
            Both representations are applied to the same image using the same preprocessing, resolution, and measurement settings. 
            Their quantum resources, reconstruction quality, and execution behaviour are then compared using actual experimental results.
          </p>
        </div>
      </div>

      {!results && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* STEP 1: UPLOAD */}
          <div className="bg-surface/50 border border-border/50 rounded-xl p-6 backdrop-blur-sm">
            <div className="flex items-center gap-2 mb-4 text-white font-medium">
              <span className="bg-blue-500/20 text-blue-400 text-xs px-2 py-0.5 rounded">STEP 1</span>
              Upload Your Image
            </div>
            
            {!preview ? (
              <div 
                className={`border-2 border-dashed rounded-xl p-10 flex flex-col items-center justify-center text-center transition-colors cursor-pointer ${isHovering ? 'border-blue-500 bg-blue-500/5' : 'border-slate-700 hover:border-slate-600 bg-slate-800/30'}`}
                onDragOver={(e) => { e.preventDefault(); setIsHovering(true); }}
                onDragLeave={() => setIsHovering(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input type="file" ref={fileInputRef} className="hidden" accept="image/png, image/jpeg, image/webp" onChange={handleFileChange} />
                <div className="w-12 h-12 bg-blue-500/10 rounded-full flex items-center justify-center mb-4">
                  <Upload className="text-blue-400" size={24} />
                </div>
                <h3 className="text-white font-medium mb-1">Drag & drop or choose an image</h3>
                <p className="text-slate-400 text-sm">PNG • JPG • JPEG • WEBP</p>
              </div>
            ) : (
              <div className="flex flex-col gap-4">
                <div className="relative rounded-xl overflow-hidden border border-border/50 bg-black/20 aspect-video flex items-center justify-center group">
                  <img src={preview} alt="Preview" className="max-w-full max-h-full object-contain" />
                  <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <button onClick={() => { setFile(null); setPreview(null); }} className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">
                      Remove Image
                    </button>
                  </div>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-4 text-sm flex flex-col gap-2 text-slate-300">
                  <div className="flex justify-between items-center border-b border-slate-700 pb-2">
                    <span className="text-slate-400">Filename:</span>
                    <span className="font-medium text-white truncate max-w-[200px]">{file?.name}</span>
                  </div>
                  <div className="flex justify-between items-center border-b border-slate-700 pb-2">
                    <span className="text-slate-400">File Size:</span>
                    <span className="font-medium text-white">{(file?.size! / 1024).toFixed(1)} KB</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">Source:</span>
                    <span className="font-medium text-blue-400">Custom Image</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* STEP 2: CONFIGURATION */}
          <div className={`bg-surface/50 border border-border/50 rounded-xl p-6 backdrop-blur-sm transition-opacity flex flex-col ${!file ? 'opacity-50 pointer-events-none' : ''}`}>
            <div className="flex items-center gap-2 mb-6 text-white font-medium">
              <span className="bg-purple-500/20 text-purple-400 text-xs px-2 py-0.5 rounded">STEP 2</span>
              Experiment Configuration
            </div>

            <div className="space-y-5 flex-1">
              <div>
                <label className="text-sm text-slate-400 mb-2 block font-medium">Quantum Resolution</label>
                <div className="flex gap-2">
                  {['2x2', '4x4', '8x8'].map(res => (
                    <button
                      key={res}
                      onClick={() => setResolution(res)}
                      className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${resolution === res ? 'bg-blue-500 text-white shadow-[0_0_15px_rgba(59,130,246,0.3)]' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'}`}
                    >
                      {res}
                    </button>
                  ))}
                </div>
              </div>

              <div className="bg-slate-900/40 border border-slate-800 rounded-lg p-3 text-xs text-slate-400 flex flex-col gap-1">
                <div className="flex justify-between"><span>Selected Resolution:</span> <span className="text-white">{resolution}</span></div>
                <div className="flex justify-between"><span>Pixels:</span> <span className="text-white">{parseInt(resolution.split('x')[0]) ** 2}</span></div>
                <div className="flex justify-between"><span>Position Qubits Required:</span> <span className="text-blue-400 font-medium">{getPosQubits(resolution)}</span></div>
              </div>

              <div>
                <label className="text-sm text-slate-400 mb-2 block font-medium">Intensity Precision</label>
                <div className="flex gap-2">
                  {[4, 8].map(bits => (
                    <button
                      key={bits}
                      onClick={() => setPrecision(bits)}
                      className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${precision === bits ? 'bg-purple-500 text-white shadow-[0_0_15px_rgba(168,85,247,0.3)]' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'}`}
                    >
                      {bits}-bit
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-sm text-slate-400 mb-2 block font-medium">Measurement Shots</label>
                <div className="flex gap-2">
                  {[100, 500, 1024, 4096].map(s => (
                    <button
                      key={s}
                      onClick={() => setShots(s)}
                      className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${shots === s ? 'bg-emerald-500 text-white shadow-[0_0_15px_rgba(16,185,129,0.3)]' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'}`}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>

              <div className="bg-slate-900/50 rounded-lg p-4 text-sm text-slate-300 border border-slate-800">
                <div className="flex justify-between mb-1">
                  <span>Quantum Backend:</span>
                  <span className="text-emerald-400 font-medium">Aer Simulator</span>
                </div>
              </div>
              
              <div className="pt-2">
                <button
                  onClick={runComparison}
                  disabled={running}
                  className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-medium py-4 rounded-xl flex items-center justify-center gap-2 transition-all disabled:opacity-50 text-lg shadow-[0_0_20px_rgba(59,130,246,0.3)]"
                >
                  {running ? (
                    <><Activity className="animate-spin" size={20} /> Running Real Experiments...</>
                  ) : (
                    <><Play size={20} fill="currentColor" /> RUN FRQI + NEQR COMPARISON</>
                  )}
                </button>
              </div>
              
              {error && (
                <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-lg text-sm">
                  {error}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* STEP 4: RESULTS */}
      {results && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="flex items-center justify-between border-b border-border/50 pb-4">
            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
              <CheckCircle2 className="text-emerald-400" /> FRQI vs NEQR — Experimental Comparison
            </h2>
            <button onClick={() => setResults(null)} className="text-slate-400 hover:text-white text-sm bg-slate-800 hover:bg-slate-700 px-4 py-2 rounded-lg font-medium transition-colors">
              New Experiment
            </button>
          </div>
          
          <div className="grid grid-cols-4 gap-4 mb-2">
            <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-3 text-center">
              <div className="text-slate-400 text-[10px] font-bold uppercase tracking-widest mb-1">Source</div>
              <div className="text-sm font-medium text-white truncate px-2" title={file?.name}>{file?.name}</div>
            </div>
            <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-3 text-center">
              <div className="text-slate-400 text-[10px] font-bold uppercase tracking-widest mb-1">Resolution</div>
              <div className="text-sm font-medium text-white">{resolution}</div>
            </div>
            <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-3 text-center">
              <div className="text-slate-400 text-[10px] font-bold uppercase tracking-widest mb-1">Precision</div>
              <div className="text-sm font-medium text-white">{precision}-bit</div>
            </div>
            <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-3 text-center">
              <div className="text-slate-400 text-[10px] font-bold uppercase tracking-widest mb-1">Shots</div>
              <div className="text-sm font-medium text-white">{shots}</div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            {/* Original Input */}
            <div className="bg-surface/50 border border-border/50 rounded-xl p-4 flex flex-col">
              <h3 className="text-slate-300 font-medium mb-3 text-center">Uploaded Image</h3>
              <div className="aspect-square bg-black/30 rounded-lg flex items-center justify-center overflow-hidden border border-slate-700/50 flex-1 mb-4">
                <img src={preview || ''} alt="Original Upload" className="w-full h-full object-contain" />
              </div>
              <h3 className="text-slate-400 font-medium mb-3 text-center text-sm">Quantum Input ({resolution})</h3>
              <div className="aspect-square bg-black/30 rounded-lg flex items-center justify-center overflow-hidden border border-slate-700/50">
                <img src={results.original_image} alt="Original Quantum Input" className="w-full h-full object-contain pixelated" style={{ imageRendering: 'pixelated' }} />
              </div>
            </div>
            
            {/* FRQI Reconstruction */}
            <div className="bg-surface/50 border border-blue-500/30 rounded-xl p-4 relative overflow-hidden flex flex-col lg:col-span-2">
              <div className="absolute top-0 right-0 bg-blue-500/20 text-blue-400 text-[10px] font-bold px-3 py-1.5 rounded-bl-lg shadow-sm">FRQI</div>
              <h3 className="text-white font-medium mb-3 text-center">FRQI Reconstruction</h3>
              <div className="flex gap-4 mb-4">
                <div className="flex-1 aspect-square bg-black/30 rounded-lg flex items-center justify-center overflow-hidden border border-slate-700/50 relative group">
                  <img src={results.frqi.reconstructed_image} alt="FRQI" className="w-full h-full object-contain pixelated" style={{ imageRendering: 'pixelated' }} />
                  <div className="absolute inset-0 bg-black/80 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <span className="text-xs font-medium text-white">Reconstruction</span>
                  </div>
                </div>
                <div className="flex-1 aspect-square bg-black/30 rounded-lg flex items-center justify-center overflow-hidden border border-slate-700/50 relative group">
                  <img src={results.frqi.difference_image} alt="FRQI Diff" className="w-full h-full object-contain pixelated" style={{ imageRendering: 'pixelated' }} />
                  <div className="absolute inset-0 bg-black/80 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <span className="text-xs font-medium text-white">Difference Map</span>
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center text-sm mt-auto">
                <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-2"><div className="text-slate-400 text-[10px] uppercase tracking-wider mb-1">MSE</div><div className="text-white font-bold">{results.frqi.metrics.mse.toFixed(2)}</div></div>
                <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-2"><div className="text-slate-400 text-[10px] uppercase tracking-wider mb-1">PSNR</div><div className="text-white font-bold">{results.frqi.metrics.psnr.toFixed(1)}</div></div>
                <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-2"><div className="text-slate-400 text-[10px] uppercase tracking-wider mb-1">SSIM</div><div className="text-white font-bold">{results.frqi.metrics.ssim.toFixed(3)}</div></div>
              </div>
            </div>

            {/* NEQR Reconstruction */}
            <div className="bg-surface/50 border border-purple-500/30 rounded-xl p-4 relative overflow-hidden flex flex-col lg:col-span-2">
              <div className="absolute top-0 right-0 bg-purple-500/20 text-purple-400 text-[10px] font-bold px-3 py-1.5 rounded-bl-lg shadow-sm">NEQR</div>
              <h3 className="text-white font-medium mb-3 text-center">NEQR Reconstruction</h3>
              <div className="flex gap-4 mb-4">
                <div className="flex-1 aspect-square bg-black/30 rounded-lg flex items-center justify-center overflow-hidden border border-slate-700/50 relative group">
                  <img src={results.neqr.reconstructed_image} alt="NEQR" className="w-full h-full object-contain pixelated" style={{ imageRendering: 'pixelated' }} />
                  <div className="absolute inset-0 bg-black/80 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <span className="text-xs font-medium text-white">Reconstruction</span>
                  </div>
                </div>
                <div className="flex-1 aspect-square bg-black/30 rounded-lg flex items-center justify-center overflow-hidden border border-slate-700/50 relative group">
                  <img src={results.neqr.difference_image} alt="NEQR Diff" className="w-full h-full object-contain pixelated" style={{ imageRendering: 'pixelated' }} />
                  <div className="absolute inset-0 bg-black/80 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <span className="text-xs font-medium text-white">Difference Map</span>
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center text-sm mt-auto">
                <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-2"><div className="text-slate-400 text-[10px] uppercase tracking-wider mb-1">MSE</div><div className="text-white font-bold">{results.neqr.metrics.mse.toFixed(2)}</div></div>
                <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-2"><div className="text-slate-400 text-[10px] uppercase tracking-wider mb-1">PSNR</div><div className="text-white font-bold">{results.neqr.metrics.psnr > 100 ? '∞' : results.neqr.metrics.psnr.toFixed(1)}</div></div>
                <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-2"><div className="text-slate-400 text-[10px] uppercase tracking-wider mb-1">SSIM</div><div className="text-white font-bold">{results.neqr.metrics.ssim.toFixed(3)}</div></div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-surface/50 border border-border/50 rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4">Quantum Resource Comparison</h3>
              <div className="overflow-hidden rounded-lg border border-slate-700/50">
                <table className="w-full text-sm text-left">
                  <thead className="bg-slate-800/80 text-slate-400 border-b border-slate-700/50">
                    <tr>
                      <th className="px-5 py-3 font-medium uppercase tracking-wider text-[11px]">Metric</th>
                      <th className="px-5 py-3 font-medium text-blue-400 uppercase tracking-wider text-[11px]">FRQI</th>
                      <th className="px-5 py-3 font-medium text-purple-400 uppercase tracking-wider text-[11px]">NEQR</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50 bg-slate-900/20">
                    <tr className="hover:bg-slate-800/30 transition-colors"><td className="px-5 py-3 font-medium text-slate-300">Total Qubits</td><td className="px-5 py-3 text-white font-mono">{results.frqi.num_qubits}</td><td className="px-5 py-3 text-white font-mono">{results.neqr.num_qubits}</td></tr>
                    <tr className="hover:bg-slate-800/30 transition-colors"><td className="px-5 py-3 font-medium text-slate-300">Gate Count</td><td className="px-5 py-3 text-white font-mono">{results.frqi.stats.gates}</td><td className="px-5 py-3 text-white font-mono">{results.neqr.stats.gates}</td></tr>
                    <tr className="hover:bg-slate-800/30 transition-colors"><td className="px-5 py-3 font-medium text-slate-300">Circuit Depth</td><td className="px-5 py-3 text-white font-mono">{results.frqi.stats.depth}</td><td className="px-5 py-3 text-white font-mono">{results.neqr.stats.depth}</td></tr>
                    <tr className="hover:bg-slate-800/30 transition-colors"><td className="px-5 py-3 font-medium text-slate-300">Encoding Time (s)</td><td className="px-5 py-3 text-emerald-400 font-mono">{results.frqi.stats.encoding_time.toFixed(4)}</td><td className="px-5 py-3 text-emerald-400 font-mono">{results.neqr.stats.encoding_time.toFixed(4)}</td></tr>
                    <tr className="hover:bg-slate-800/30 transition-colors"><td className="px-5 py-3 font-medium text-slate-300">Total Runtime (s)</td><td className="px-5 py-3 text-emerald-400 font-mono">{results.frqi.metrics.runtime.toFixed(3)}</td><td className="px-5 py-3 text-emerald-400 font-mono">{results.neqr.metrics.runtime.toFixed(3)}</td></tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div className="bg-surface/50 border border-border/50 rounded-xl p-6 flex flex-col">
              <h3 className="text-lg font-bold text-white mb-4">Scalability Analysis</h3>
              <div className="flex-1 min-h-[250px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={[
                    { name: 'Qubits', FRQI: results.frqi.num_qubits, NEQR: results.neqr.num_qubits },
                    { name: 'Circuit Depth', FRQI: results.frqi.stats.depth, NEQR: results.neqr.stats.depth }
                  ]} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
                    <XAxis type="number" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis dataKey="name" type="category" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} width={100} />
                    <RechartsTooltip cursor={{ fill: '#1e293b' }} contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc', borderRadius: '8px' }} />
                    <Legend />
                    <Bar dataKey="FRQI" fill="#3b82f6" radius={[0, 4, 4, 0]} barSize={20} />
                    <Bar dataKey="NEQR" fill="#a855f7" radius={[0, 4, 4, 0]} barSize={20} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
          
          <div className="bg-blue-900/20 border border-blue-500/30 rounded-xl p-6">
            <h3 className="text-lg font-bold text-blue-400 mb-4 flex items-center gap-2"><Activity size={20}/> Experimental Interpretation</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 text-sm">
              <div>
                <h4 className="font-bold text-white mb-2">Observation</h4>
                <p className="text-slate-300 leading-relaxed">
                  Under the selected configuration ({resolution}, {precision}-bit, {shots} shots), FRQI used 
                  <span className="text-blue-300 font-bold px-1">{results.frqi.num_qubits} qubits</span> and 
                  <span className="text-blue-300 font-bold px-1">{results.frqi.stats.gates} gates</span>, 
                  achieving a PSNR of <span className="text-emerald-400 font-bold">{results.frqi.metrics.psnr.toFixed(1)} dB</span>.
                  In contrast, NEQR used <span className="text-purple-300 font-bold px-1">{results.neqr.num_qubits} qubits</span> and 
                  <span className="text-purple-300 font-bold px-1">{results.neqr.stats.gates} gates</span>, achieving a PSNR of 
                  <span className="text-emerald-400 font-bold px-1">{results.neqr.metrics.psnr > 100 ? 'perfect (∞)' : results.neqr.metrics.psnr.toFixed(1)} dB</span>.
                </p>
              </div>
              <div>
                <h4 className="font-bold text-white mb-2">Trade-off Analysis</h4>
                <p className="text-slate-300 leading-relaxed">
                  FRQI is highly efficient in qubit count but struggles with precise intensity retrieval due to probabilistic measurement (shot noise). 
                  NEQR provides exact, lossless pixel retrieval (resulting in perfect SSIM and PSNR) by using dedicated computational basis states, 
                  but requires significantly deeper circuits and more multi-controlled gates.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
