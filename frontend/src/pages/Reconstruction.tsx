import React, { useState, useEffect } from 'react';
import { Image as ImageIcon, Zap, Activity, AlertCircle } from 'lucide-react';

interface Experiment {
  experiment_id: string;
  image_name: string;
  defect_category: string;
  representation: string;
  resolution: string;
  intensity_precision: number;
  shots: number;
  mse: number;
  psnr: number;
  ssim: number;
}

export default function Reconstruction() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedRepresentation, setSelectedRepresentation] = useState<string>('FRQI');
  const [selectedImageName, setSelectedImageName] = useState<string>('');
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<any>(null);
  const [viewMode, setViewMode] = useState<'single' | 'gallery'>('single');
  const [selectedResolution, setSelectedResolution] = useState<string>('4x4');

  useEffect(() => {
    fetch('/api/quantum/experiments?limit=5000')
      .then(res => res.json())
      .then(d => {
        if (d.experiments) {
          setExperiments(d.experiments);
          // Set initial category if available
          const categories = Array.from(new Set(d.experiments.map((e: any) => e.defect_category)));
          if (categories.length > 0 && !selectedCategory) {
             setSelectedCategory(categories[0] as string);
          }
        }
      })
      .catch(console.error);
  }, []);

  // Get unique categories and resolutions
  const categories = Array.from(new Set(experiments.map(e => e.defect_category))).filter(Boolean) as string[];
  const resolutions = Array.from(new Set(experiments.map(e => e.resolution))).filter(Boolean) as string[];
  
  // Filter available images based on category and representation
  const availableImages = Array.from(new Set(
    experiments
      .filter(e => e.defect_category === selectedCategory && e.representation === selectedRepresentation && e.resolution === selectedResolution)
      .map(e => e.image_name)
  )).filter(Boolean) as string[];
  
  // Automatically select the first available image when category or rep changes
  useEffect(() => {
    if (availableImages.length > 0 && !availableImages.includes(selectedImageName)) {
      setSelectedImageName(availableImages[0]);
    } else if (availableImages.length === 0) {
      setSelectedImageName('');
    }
  }, [selectedCategory, selectedRepresentation, selectedResolution, availableImages]);

  const handlePrevImage = () => {
    const idx = availableImages.indexOf(selectedImageName);
    if (idx > 0) setSelectedImageName(availableImages[idx - 1]);
  };

  const handleNextImage = () => {
    const idx = availableImages.indexOf(selectedImageName);
    if (idx < availableImages.length - 1) setSelectedImageName(availableImages[idx + 1]);
  };

  useEffect(() => {
    if (!selectedCategory || !selectedRepresentation || !selectedImageName) return;
    
    // Find the specific experiment to get its exact parameters (like resolution, shots)
    const exp = experiments.find(e => 
      e.defect_category === selectedCategory && 
      e.representation === selectedRepresentation && 
      e.resolution === selectedResolution &&
      e.image_name === selectedImageName
    );
    
    if (!exp) return;

    setLoading(true);
    setError(null);
    setData(null);
    
    // Parse resolution "4x4" -> size = 4
    const size = parseInt(exp.resolution.split('x')[0]) || 4;

    const url = `/api/quantum/reconstruct?image_name=${exp.image_name}&category=${exp.defect_category}&representation=${exp.representation}&size=${size}&bits=${exp.intensity_precision}&shots=${exp.shots}`;
    
    fetch(url)
      .then(async (res) => {
        if (!res.ok) {
          const e = await res.json().catch(() => ({}));
          throw new Error(e.detail || 'Failed to fetch reconstruction');
        }
        return res.json();
      })
      .then(d => {
        setData(d);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [selectedCategory, selectedRepresentation, selectedImageName, experiments]);

  return (
    <div className="space-y-8 animate-in fade-in duration-500 h-full flex flex-col">
      <div className="flex flex-row justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-100 to-slate-400 mb-2">Reconstruction Studio</h1>
          <p className="text-slate-400">Visual comparison of original and quantum reconstructed images</p>
        </div>
        
        <div className="flex gap-3 bg-surface p-2 rounded-xl border border-border">
          <select 
            value={selectedCategory} 
            onChange={e => setSelectedCategory(e.target.value)} 
            className="bg-slate-900 border border-border text-sm rounded-lg px-3 py-1.5 focus:border-blue-500 outline-none text-slate-200"
          >
            <option value="">Select Type...</option>
            {categories.map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
          
          <select 
            value={selectedRepresentation} 
            onChange={e => setSelectedRepresentation(e.target.value)} 
            className="bg-slate-900 border border-border text-sm rounded-lg px-3 py-1.5 focus:border-blue-500 outline-none text-slate-200"
          >
            <option value="FRQI">FRQI</option>
            <option value="NEQR">NEQR</option>
          </select>

          <select 
            value={selectedResolution} 
            onChange={e => setSelectedResolution(e.target.value)} 
            className="bg-slate-900 border border-border text-sm rounded-lg px-3 py-1.5 focus:border-blue-500 outline-none text-slate-200"
          >
            {resolutions.map(res => (
              <option key={res} value={res}>{res}</option>
            ))}
          </select>

          <select 
            value={selectedImageName} 
            onChange={e => setSelectedImageName(e.target.value)} 
            className="bg-slate-900 border border-border text-sm rounded-lg px-3 py-1.5 focus:border-blue-500 outline-none text-slate-200 min-w-[150px]"
            disabled={!selectedCategory || availableImages.length === 0}
          >
            <option value="">Select Image...</option>
            {availableImages.map(img => (
              <option key={img} value={img}>{img}</option>
            ))}
          </select>

          <div className="flex bg-slate-900 rounded-lg p-1 border border-border">
            <button onClick={() => setViewMode('single')} className={`px-3 py-1 text-sm rounded-md ${viewMode === 'single' ? 'bg-blue-600 text-white' : 'text-slate-400'}`}>Single</button>
            <button onClick={() => setViewMode('gallery')} className={`px-3 py-1 text-sm rounded-md ${viewMode === 'gallery' ? 'bg-blue-600 text-white' : 'text-slate-400'}`}>Gallery</button>
          </div>
        </div>
      </div>

      <div className="flex-1 flex flex-col bg-surface border border-border rounded-2xl shadow-lg relative overflow-hidden p-8">
        <div className="absolute inset-0 bg-gradient-to-b from-blue-900/5 to-transparent pointer-events-none"></div>
        
        {viewMode === 'gallery' ? (
          <div className="w-full h-full overflow-y-auto">
            <h2 className="text-xl font-semibold mb-4 text-slate-200">Reconstruction Gallery ({experiments.filter(e => e.defect_category === selectedCategory && e.representation === selectedRepresentation && e.resolution === selectedResolution).length} results)</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {experiments.filter(e => e.defect_category === selectedCategory && e.representation === selectedRepresentation && e.resolution === selectedResolution).map(exp => (
                <div key={exp.experiment_id} className="bg-background border border-border p-4 rounded-xl flex flex-col items-center shadow-lg">
                   <div className="text-xs font-mono text-slate-500 mb-2 truncate w-full text-center">EXP: {exp.experiment_id} • {exp.image_name}</div>
                   <div className="grid grid-cols-2 gap-2 mb-3">
                     <div className="text-center"><span className="text-[10px] text-slate-500">MSE</span><div className="text-emerald-400 font-mono text-sm">{typeof exp.mse === 'number' ? exp.mse.toFixed(4) : exp.mse}</div></div>
                     <div className="text-center"><span className="text-[10px] text-slate-500">PSNR</span><div className="text-blue-400 font-mono text-sm">{typeof exp.psnr === 'number' ? (exp.psnr > 99 ? '∞' : exp.psnr.toFixed(2)) : exp.psnr}</div></div>
                   </div>
                   <button onClick={() => { setViewMode('single'); setSelectedImageName(exp.image_name); }} className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded-md w-full">View Details</button>
                </div>
              ))}
            </div>
          </div>
        ) : !selectedImageName ? (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-500">
            <ImageIcon size={48} className="text-slate-700 mb-4" />
            <p className="text-lg font-medium text-slate-400 mb-2">No image selected</p>
            <p className="text-sm">Select a defect type and image to view reconstruction analysis.</p>
          </div>
        ) : loading ? (
          <div className="flex-1 flex flex-col items-center justify-center">
            <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4" />
            <p className="text-blue-400">Reconstructing quantum circuit execution...</p>
          </div>
        ) : error ? (
           <div className="flex-1 flex flex-col items-center justify-center text-red-400">
             <AlertCircle size={48} className="mb-4" />
             <p className="text-lg font-medium mb-2">Reconstruction Failed</p>
             <p className="text-sm opacity-80">{error}</p>
           </div>
        ) : data ? (
          <div className="flex-1 flex flex-col items-center justify-center w-full max-w-5xl mx-auto">
            <div className="w-full flex justify-between items-center mb-6">
              <button onClick={handlePrevImage} disabled={availableImages.indexOf(selectedImageName) <= 0} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 rounded-lg text-sm font-semibold transition-colors">← Previous Image</button>
              <div className="text-sm font-mono text-slate-400 text-center">
                Experiment ID: <span className="text-blue-400">{experiments.find(e => e.image_name === selectedImageName && e.defect_category === selectedCategory && e.representation === selectedRepresentation)?.experiment_id}</span>
                <div className="text-[10px] mt-1 text-slate-500">{availableImages.indexOf(selectedImageName) + 1} of {availableImages.length}</div>
              </div>
              <button onClick={handleNextImage} disabled={availableImages.indexOf(selectedImageName) >= availableImages.length - 1} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 rounded-lg text-sm font-semibold transition-colors">Next Image →</button>
            </div>

            <div className="flex items-center justify-between gap-4 mb-8 relative w-full">
              <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-slate-700 to-transparent -z-10"></div>
              
              <div className="flex flex-col items-center bg-background p-4 rounded-xl border border-slate-800 shadow-xl">
                <span className="text-xs font-semibold text-slate-400 mb-2">ORIGINAL IMAGE</span>
                <img src={data.original_image} alt="Original" className="w-40 h-40 object-contain rounded-lg border border-slate-700 rendering-pixelated" style={{ imageRendering: 'pixelated' }} />
              </div>
              
              <div className="flex flex-col items-center">
                 <Zap className="text-blue-500 mb-2 animate-pulse" />
                 <span className="text-xs text-blue-500 font-mono">ENCODE</span>
              </div>
              
              <div className="flex flex-col items-center bg-background p-4 rounded-xl border border-slate-800 shadow-xl relative overflow-hidden group">
                <div className="absolute inset-0 bg-blue-500/10 group-hover:bg-blue-500/20 transition-colors pointer-events-none" />
                <span className="text-xs font-semibold text-slate-400 mb-2">QUANTUM STATE</span>
                <div className="w-40 h-40 bg-slate-900 rounded-lg border border-blue-900 flex flex-col items-center justify-center text-blue-500 font-mono shadow-[0_0_15px_rgba(59,130,246,0.2)]">
                  <span className="text-3xl">|Ψ⟩</span>
                </div>
              </div>

              <div className="flex flex-col items-center">
                 <Activity className="text-emerald-500 mb-2 animate-pulse" />
                 <span className="text-xs text-emerald-500 font-mono">MEASURE</span>
              </div>
              
              <div className="flex flex-col items-center bg-background p-4 rounded-xl border border-slate-800 shadow-xl relative overflow-hidden group">
                <div className="absolute inset-0 bg-emerald-500/10 group-hover:bg-emerald-500/20 transition-colors pointer-events-none" />
                <span className="text-xs font-semibold text-slate-400 mb-2">RECONSTRUCTED</span>
                <img src={data.reconstructed_image} alt="Reconstructed" className="w-40 h-40 object-contain rounded-lg border border-emerald-900 shadow-[0_0_15px_rgba(16,185,129,0.2)]" style={{ imageRendering: 'pixelated' }} />
              </div>
            </div>
            
            <div className="grid grid-cols-4 gap-6 w-full">
              <div className="bg-background border border-slate-800 p-4 rounded-xl text-center">
                <div className="text-2xl font-mono text-emerald-400">{data.mse.toFixed(6)}</div>
                <div className="text-xs text-slate-500 uppercase mt-1">MSE</div>
              </div>
              <div className="bg-background border border-slate-800 p-4 rounded-xl text-center">
                <div className="text-2xl font-mono text-emerald-400">
                  {data.psnr > 99 ? '∞' : data.psnr.toFixed(2)}
                </div>
                <div className="text-xs text-slate-500 uppercase mt-1">PSNR (dB)</div>
              </div>
              <div className="bg-background border border-slate-800 p-4 rounded-xl text-center">
                <div className="text-2xl font-mono text-emerald-400">{data.ssim.toFixed(6)}</div>
                <div className="text-xs text-slate-500 uppercase mt-1">SSIM</div>
              </div>
              
              <div className="flex flex-row items-center justify-center gap-4 bg-background border border-slate-800 p-2 rounded-xl text-center">
                 <div className="flex flex-col items-center">
                    <span className="text-xs text-slate-500 mb-1">DIFF</span>
                    <img src={data.difference_image} alt="Difference" className="w-16 h-16 rounded border border-red-900" style={{ imageRendering: 'pixelated' }} />
                 </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
