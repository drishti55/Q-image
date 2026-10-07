import React, { useState, useEffect } from 'react';
import { Activity, Play, Settings2, Info, CheckCircle2, CircleDashed, Zap } from 'lucide-react';

export default function QuantumLab() {
  const [images, setImages] = useState<any[]>([]);
  const [selectedImage, setSelectedImage] = useState('');
  const [selectedClass, setSelectedClass] = useState('');
  const [representation, setRepresentation] = useState('FRQI');
  const [resolution, setResolution] = useState('4');
  const [precision, setPrecision] = useState('8');
  const [shots, setShots] = useState('1024');

  const [executing, setExecuting] = useState(false);
  const [progress, setProgress] = useState(-1);
  const [result, setResult] = useState<any>(null);
  const [reconstructionData, setReconstructionData] = useState<any>(null);

  // Batch states
  const [runMode, setRunMode] = useState('single');
  const [batchTarget, setBatchTarget] = useState('all');
  const [batchRep, setBatchRep] = useState('Both');
  const [batchStatus, setBatchStatus] = useState<any>(null);

  useEffect(() => {
    let interval: any;
    interval = setInterval(() => {
      fetch('/api/quantum/batch/status')
        .then(r => r.json())
        .then(setBatchStatus)
        .catch(console.error);
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    fetch('/api/dataset/images?split=train&limit=5000')
      .then(r => r.json())
      .then(d => {
        const imgs = d.images || [];
        setImages(imgs);
        if (imgs.length > 0) {
          const firstCat = imgs[0].defect_class;
          setSelectedClass(firstCat);
          const firstImg = imgs.find((i: any) => i.defect_class === firstCat);
          if (firstImg) setSelectedImage(firstImg.name);
        }
      })
      .catch(console.error);
  }, []);

  const categories = Array.from(new Set(images.map(img => img.defect_class))).filter(Boolean) as string[];
  const availableImages = images.filter(img => img.defect_class === selectedClass);

  useEffect(() => {
    if (availableImages.length > 0 && !availableImages.find(img => img.name === selectedImage)) {
       setSelectedImage(availableImages[0].name);
    }
  }, [selectedClass, availableImages, selectedImage]);

  const handleImageChange = (name: string) => {
    setSelectedImage(name);
    const img = images.find(i => i.name === name);
    if (img) setSelectedClass(img.defect_class);
  };

  const selectedImgData = images.find(i => i.name === selectedImage);
  const res = parseInt(resolution);
  const totalPixels = res * res;
  const positionQubits = Math.ceil(Math.log2(totalPixels));
  const intensityQubits = representation === 'FRQI' ? 1 : parseInt(precision);
  const totalQubits = positionQubits + intensityQubits;

  const runExperiment = async () => {
    setExecuting(true);
    setProgress(0);
    setResult(null);

    const steps = [
      "Preparing image",
      "Building quantum circuit",
      "Encoding image data",
      "Running quantum simulation",
      "Collecting measurements",
      "Reconstructing image",
      "Calculating metrics",
      "Saving experiment"
    ];

    for (let i = 0; i < steps.length; i++) {
      setProgress(i);
      await new Promise(r => setTimeout(r, 400 + Math.random() * 400));
    }

    try {
      const res = await fetch('/api/quantum/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: selectedImage, defect_class: selectedClass, representation, resolution, precision, shots })
      });
      const data = await res.json();
      
      if (data.status === 'completed') {
         // Now fetch the reconstructed visual data
         const size = parseInt(resolution.split('x')[0]) || 4;
         const url = `/api/quantum/reconstruct?image_name=${selectedImage}&category=${selectedClass}&representation=${representation}&size=${size}&bits=${precision}&shots=${shots}`;
         const reconRes = await fetch(url);
         const reconData = await reconRes.json();
         setReconstructionData(reconData);
      }
      
      setProgress(steps.length);
      setResult(data);
    } catch (e) {
      setResult({ error: "Failed to connect to quantum backend." });
    } finally {
      setExecuting(false);
    }
  };

  const runBatchExperiment = async () => {
    await fetch('/api/quantum/batch/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mode: batchTarget === 'all' ? 'all' : 'category',
        category: batchTarget === 'all' ? 'all' : selectedClass,
        representation: batchRep,
        resolution,
        precision,
        shots
      })
    });
  };

  const stopBatchExperiment = async () => {
    await fetch('/api/quantum/batch/stop', { method: 'POST' });
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-100 to-slate-400 mb-1">Quantum Image Lab</h1>
        <p className="text-slate-400 flex items-center gap-2">
          <span>Encode</span><Zap size={14} className="text-blue-400" /><span>Simulate</span><Zap size={14} className="text-cyan-400" /><span>Measure</span><Zap size={14} className="text-emerald-400" /><span>Reconstruct</span>
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Configuration Panel */}
        <div className="space-y-5">
          <div className="bg-surface border border-border rounded-2xl p-6 shadow-lg">
            <h3 className="font-semibold text-slate-200 mb-5 flex items-center gap-2">
              <Settings2 className="text-blue-400" size={18} /> Configuration
            </h3>

            <div className="space-y-4">
              <div className="flex bg-slate-900 p-1 rounded-lg border border-slate-700">
                <button onClick={() => setRunMode('single')}
                  className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-all ${runMode === 'single' ? 'bg-blue-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'}`}>
                  Single Image
                </button>
                <button onClick={() => setRunMode('batch')}
                  className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-all ${runMode === 'batch' ? 'bg-purple-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'}`}>
                  Batch Mode
                </button>
              </div>

              {runMode === 'single' ? (
                <div className="grid grid-cols-2 gap-3 animate-in fade-in zoom-in-95">
                  <div>
                    <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Defect Type</label>
                    <select value={selectedClass} onChange={e => setSelectedClass(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue-500">
                      {categories.map(cat => <option key={cat} value={cat}>{cat}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Target Image</label>
                    <select value={selectedImage} onChange={e => handleImageChange(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue-500">
                      {availableImages.map(img => <option key={img.name} value={img.name}>{img.name}</option>)}
                    </select>
                  </div>
                </div>
              ) : (
                <div className="space-y-3 animate-in fade-in zoom-in-95">
                  <div>
                    <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Batch Target</label>
                    <select value={batchTarget} onChange={e => setBatchTarget(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-purple-500">
                      <option value="all">All Dataset Images ({images.length})</option>
                      <option value="category">Current Category Only ({availableImages.length})</option>
                    </select>
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Representation</label>
                <div className="flex bg-slate-900 p-1 rounded-lg border border-slate-700">
                  {runMode === 'single' ? (
                    <>
                      <button onClick={() => setRepresentation('FRQI')}
                        className={`flex-1 py-2 text-sm font-semibold rounded-md transition-all ${representation === 'FRQI' ? 'bg-blue-600 text-white shadow-md shadow-blue-500/30' : 'text-slate-400 hover:text-slate-200'}`}>
                        FRQI
                      </button>
                      <button onClick={() => setRepresentation('NEQR')}
                        className={`flex-1 py-2 text-sm font-semibold rounded-md transition-all ${representation === 'NEQR' ? 'bg-emerald-600 text-white shadow-md shadow-emerald-500/30' : 'text-slate-400 hover:text-slate-200'}`}>
                        NEQR
                      </button>
                    </>
                  ) : (
                    <>
                      <button onClick={() => setBatchRep('FRQI')} className={`flex-1 py-2 text-sm font-semibold rounded-md transition-all ${batchRep === 'FRQI' ? 'bg-purple-600 text-white shadow' : 'text-slate-400'}`}>FRQI</button>
                      <button onClick={() => setBatchRep('NEQR')} className={`flex-1 py-2 text-sm font-semibold rounded-md transition-all ${batchRep === 'NEQR' ? 'bg-purple-600 text-white shadow' : 'text-slate-400'}`}>NEQR</button>
                      <button onClick={() => setBatchRep('Both')} className={`flex-1 py-2 text-sm font-semibold rounded-md transition-all ${batchRep === 'Both' ? 'bg-purple-600 text-white shadow' : 'text-slate-400'}`}>Both</button>
                    </>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Resolution</label>
                  <select value={resolution} onChange={e => setResolution(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue-500">
                    <option value="2">2 × 2</option><option value="4">4 × 4</option><option value="8">8 × 8</option><option value="16">16 × 16</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Shots</label>
                  <select value={shots} onChange={e => setShots(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue-500">
                    <option value="100">100</option><option value="512">512</option><option value="1024">1024</option><option value="4096">4096</option><option value="8192">8192</option>
                  </select>
                </div>
              </div>

              {representation === 'NEQR' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Intensity Precision</label>
                  <select value={precision} onChange={e => setPrecision(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-emerald-500">
                    <option value="4">4-bit (16 levels)</option><option value="8">8-bit (256 levels)</option>
                  </select>
                </div>
              )}

              {runMode === 'single' ? (
                <button onClick={runExperiment} disabled={executing || !selectedImage || batchStatus?.is_running}
                  className={`w-full py-3 rounded-xl font-semibold flex items-center justify-center gap-2 transition-all ${
                    executing || batchStatus?.is_running ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                      : 'bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white shadow-lg shadow-blue-500/25 border border-blue-400/50 hover:-translate-y-0.5'
                  }`}>
                  {executing ? <CircleDashed className="animate-spin" size={18} /> : <Play size={18} />}
                  {executing ? 'Executing...' : 'Run Single Experiment'}
                </button>
              ) : (
                <button onClick={batchStatus?.is_running ? stopBatchExperiment : runBatchExperiment} 
                  className={`w-full py-3 rounded-xl font-semibold flex items-center justify-center gap-2 transition-all ${
                    batchStatus?.is_running 
                      ? 'bg-red-900/50 hover:bg-red-800/50 text-red-300 border border-red-500/30'
                      : 'bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white shadow-lg shadow-purple-500/25 border border-purple-400/50 hover:-translate-y-0.5'
                  }`}>
                  {batchStatus?.is_running ? <CircleDashed className="animate-spin" size={18} /> : <Play size={18} />}
                  {batchStatus?.is_running ? 'Stop Batch Execution' : 'Run Batch Execution'}
                </button>
              )}
            </div>
          </div>

          {/* Representation info */}
          <div className={`bg-surface border rounded-2xl p-5 shadow-lg ${representation === 'FRQI' ? 'border-blue-500/20' : 'border-emerald-500/20'}`}>
            <h4 className="text-sm font-bold text-slate-200 flex items-center gap-2 mb-2">
              <Info size={14} className={representation === 'FRQI' ? 'text-blue-400' : 'text-emerald-400'} />
              {representation}
            </h4>
            <p className="text-xs text-slate-400 mb-3">
              {representation === 'FRQI'
                ? 'Flexible Representation of Quantum Images — encodes pixel intensity as rotation angle on a single qubit.'
                : 'Novel Enhanced Quantum Representation — encodes exact grayscale values using computational basis states.'}
            </p>
            <div className="grid grid-cols-2 gap-3 bg-slate-900/50 p-3 rounded-lg border border-border/50 text-sm">
              <div><span className="block text-[10px] text-slate-500 uppercase">Position Qubits</span><span className="font-mono text-slate-200">{positionQubits}</span></div>
              <div><span className="block text-[10px] text-slate-500 uppercase">Intensity Qubits</span><span className="font-mono text-slate-200">{intensityQubits}</span></div>
              <div className="col-span-2 pt-2 border-t border-border/50">
                <span className="block text-[10px] text-slate-500 uppercase">Total Qubits</span>
                <span className={`font-mono font-bold text-lg ${representation === 'FRQI' ? 'text-blue-400' : 'text-emerald-400'}`}>{totalQubits}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Preview & Results */}
        <div className="lg:col-span-2 space-y-5">
          <div className="grid grid-cols-2 gap-5">
            <div className="bg-surface border border-border rounded-2xl p-5 shadow-lg">
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Original Image</h4>
              {selectedImgData ? (
                <div className="aspect-square bg-slate-900 rounded-lg overflow-hidden border border-slate-800">
                  <img src={selectedImgData.url} alt="Original" className="w-full h-full object-cover" />
                </div>
              ) : (
                <div className="aspect-square bg-slate-900 rounded-lg border border-dashed border-slate-700 flex items-center justify-center text-slate-600 text-sm">Select image</div>
              )}
              {selectedImgData && <p className="text-xs text-slate-500 mt-2 capitalize">{selectedClass.replace(/[_-]/g, ' ')} • {selectedImage}</p>}
            </div>
            <div className="bg-surface border border-border rounded-2xl p-5 shadow-lg relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-900/5 to-emerald-900/5 pointer-events-none" />
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 relative z-10">Reconstructed</h4>
              <div className="aspect-square bg-slate-900 rounded-lg border border-slate-800 flex items-center justify-center text-slate-600 relative z-10">
                <div className="aspect-square bg-slate-900 rounded-lg border border-slate-800 flex flex-col items-center justify-center text-slate-600 relative z-10 overflow-hidden">
                  {executing ? (
                    <Activity className="animate-pulse text-blue-500" size={32} />
                  ) : reconstructionData ? (
                    <img src={reconstructionData.reconstructed_image} alt="Reconstructed" className="w-full h-full object-contain p-2" style={{ imageRendering: 'pixelated' }} />
                  ) : (
                    <span className="text-sm">Run experiment</span>
                  )}
                </div>
              </div>
            </div>
            
            {(reconstructionData || result?.metrics) && (
              <div className="grid grid-cols-3 gap-4 mt-4">
                 <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl text-center">
                   <div className="text-xl font-mono text-emerald-400">{result?.metrics?.mse?.toFixed(6) || reconstructionData?.mse?.toFixed(6) || '-'}</div>
                   <div className="text-[10px] text-slate-500 uppercase mt-1">MSE</div>
                 </div>
                 <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl text-center">
                   <div className="text-xl font-mono text-blue-400">{(result?.metrics?.psnr || reconstructionData?.psnr) > 99 ? '∞' : (result?.metrics?.psnr?.toFixed(2) || reconstructionData?.psnr?.toFixed(2) || '-')}</div>
                   <div className="text-[10px] text-slate-500 uppercase mt-1">PSNR</div>
                 </div>
                 <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl text-center">
                   <div className="text-xl font-mono text-purple-400">{result?.metrics?.ssim?.toFixed(6) || reconstructionData?.ssim?.toFixed(6) || '-'}</div>
                   <div className="text-[10px] text-slate-500 uppercase mt-1">SSIM</div>
                 </div>
              </div>
            )}
          </div>

          {/* Batch execution progress */}
          {batchStatus?.is_running && (
            <div className="bg-surface border border-purple-500/30 rounded-2xl p-6 shadow-lg shadow-purple-900/10 animate-in slide-in-from-bottom-4 duration-500">
              <h3 className="font-semibold text-purple-300 mb-4 flex items-center gap-2">
                <Activity size={18} className="text-purple-400 animate-pulse" />
                Batch Execution Running
              </h3>
              <div className="flex items-center justify-between text-sm mb-2 text-slate-300">
                <span>Experiments: {batchStatus.completed} / {batchStatus.total} completed</span>
                <span className="text-red-400">{batchStatus.failed} failed</span>
              </div>
              <div className="w-full bg-slate-900 rounded-full h-2 mb-4 border border-slate-700 overflow-hidden">
                <div className="bg-gradient-to-r from-purple-500 to-pink-500 h-full rounded-full transition-all duration-500" style={{ width: `${(batchStatus.completed / batchStatus.total) * 100}%` }} />
              </div>
              <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-800 text-xs text-slate-400 font-mono">
                <div className="flex justify-between mb-1"><span>Current:</span><span className="text-blue-300">{batchStatus.current_image}</span></div>
                <div className="flex justify-between"><span>Representation:</span><span className="text-emerald-300">{batchStatus.current_representation}</span></div>
              </div>
            </div>
          )}

          {/* Execution pipeline */}
          {(executing || result) && (
            <div className="bg-surface border border-border rounded-2xl p-6 shadow-lg animate-in slide-in-from-bottom-4 duration-500">
              <h3 className="font-semibold text-slate-200 mb-4 flex items-center gap-2">
                <Activity size={18} className={executing ? "text-cyan-400 animate-pulse" : "text-emerald-400"} />
                {executing ? "Execution Pipeline" : "Experiment Complete"}
              </h3>

              {executing ? (
                <div className="space-y-2.5">
                  {["Preparing image", "Building quantum circuit", "Encoding image data", "Running quantum simulation", "Collecting measurements", "Reconstructing image", "Calculating metrics", "Saving experiment"].map((step, idx) => (
                    <div key={idx} className="flex items-center gap-3 text-sm">
                      {progress > idx ? <CheckCircle2 size={16} className="text-emerald-500 shrink-0" /> :
                       progress === idx ? <CircleDashed size={16} className="text-blue-400 animate-spin shrink-0" /> :
                       <div className="w-4 h-4 rounded-full border border-slate-700 bg-slate-900/50 shrink-0" />}
                      <span className={progress >= idx ? 'text-slate-200' : 'text-slate-600'}>{step}</span>
                    </div>
                  ))}
                  <div className="w-full bg-slate-900 rounded-full h-1.5 mt-3 border border-border overflow-hidden">
                    <div className="bg-gradient-to-r from-blue-500 to-cyan-400 h-full rounded-full transition-all duration-500" style={{ width: `${(progress / 7) * 100}%` }} />
                  </div>
                </div>
              ) : result?.error ? (
                <div className="text-red-400 bg-red-950/30 p-4 rounded-lg border border-red-900/50 text-sm">{result.error}</div>
              ) : (
                <div className="text-emerald-400 bg-emerald-950/20 p-4 rounded-lg border border-emerald-900/30 text-sm">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle2 size={16} />
                    <span className="font-semibold">Experiment Completed</span>
                  </div>
                  <div>ID: <span className="font-mono text-emerald-300">{result.experiment_id}</span></div>
                  <div className="mt-2 text-xs text-emerald-500/80">Reconstruction complete. Check visual output above.</div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
