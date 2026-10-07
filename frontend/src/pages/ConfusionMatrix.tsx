import React, { useState, useEffect } from 'react';
import { Grid, BarChart, AlertCircle } from 'lucide-react';

export default function ConfusionMatrix() {
  const [models, setModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [split, setSplit] = useState<string>('Test');
  const [displayMode, setDisplayMode] = useState<'Counts' | 'Normalized'>('Counts');
  
  const [matrixData, setMatrixData] = useState<any>(null);
  const [overallMetrics, setOverallMetrics] = useState<any>(null);
  const [perClassMetrics, setPerClassMetrics] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/ml/models')
      .then(res => res.json())
      .then(d => {
        if (d.models && d.models.length > 0) {
          setModels(d.models);
          setSelectedModel(d.models[0]);
        }
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (!selectedModel) return;
    
    setLoading(true);
    setError(null);
    
    Promise.all([
      fetch(`/api/ml/confusion-matrix/${selectedModel}`).then(res => res.ok ? res.json() : null),
      fetch('/api/ml/results').then(res => res.json()),
      fetch('/api/ml/per-class').then(res => res.json())
    ]).then(([cmData, allResults, perClassData]) => {
      if (!cmData) throw new Error("Matrix not found for this model.");
      
      setMatrixData(cmData);
      
      const overall = allResults.find((r: any) => r.model === selectedModel);
      setOverallMetrics(overall);
      
      const classData = perClassData.filter((r: any) => r.model === selectedModel);
      setPerClassMetrics(classData);
      
      setLoading(false);
    }).catch(err => {
      setError(err.message);
      setLoading(false);
    });
    
  }, [selectedModel]);

  const renderMatrix = () => {
    if (!matrixData) return null;
    
    const classes = matrixData.classes;
    const matrix = matrixData.matrix;
    
    const rowSums = matrix.map((row: number[]) => row.reduce((a, b) => a + b, 0));
    
    return (
      <div className="overflow-x-auto">
        <div className="flex flex-col min-w-max">
          <div className="flex mb-2">
            <div className="w-32"></div>
            <div className="text-center font-semibold text-slate-300 w-full mb-2">Predicted Class</div>
          </div>
          
          <div className="flex">
            <div className="w-32 flex flex-col justify-center items-end pr-4 border-r border-slate-700">
              <span className="font-semibold text-slate-300 transform -rotate-90 whitespace-nowrap">Actual Class</span>
            </div>
            
            <div className="flex flex-col">
              <div className="flex">
                <div className="w-24"></div>
                {classes.map((c: string) => (
                  <div key={c} className="w-16 md:w-20 lg:w-24 text-center text-xs text-slate-400 font-medium break-words px-1" title={c}>
                    {c.substring(0, 3).toUpperCase()}
                  </div>
                ))}
              </div>
              
              {classes.map((actualClass: string, i: number) => (
                <div key={actualClass} className="flex items-center mt-1">
                  <div className="w-24 text-right pr-4 text-xs font-medium text-slate-400" title={actualClass}>
                    {actualClass}
                  </div>
                  {classes.map((predictedClass: string, j: number) => {
                    const count = matrix[i][j];
                    const normalized = rowSums[i] > 0 ? count / rowSums[i] : 0;
                    const value = displayMode === 'Counts' ? count : normalized.toFixed(3);
                    
                    // Color intensity based on value (diagonal should be green, off-diagonal red)
                    const intensity = normalized * 100;
                    let bgColor = '';
                    let textColor = 'text-white';
                    
                    if (i === j) {
                      bgColor = `rgba(16, 185, 129, ${Math.max(0.1, intensity / 100)})`;
                    } else {
                      bgColor = `rgba(239, 68, 68, ${Math.max(0, intensity / 100)})`;
                      if (intensity < 10) textColor = 'text-slate-400';
                    }
                    
                    return (
                      <div 
                        key={`${i}-${j}`} 
                        className={`w-16 md:w-20 lg:w-24 h-12 flex items-center justify-center font-mono text-sm border border-slate-800/50 rounded-sm mx-[1px] ${textColor}`}
                        style={{ backgroundColor: bgColor }}
                        title={`Actual: ${actualClass}\nPredicted: ${predictedClass}\nCount: ${count}`}
                      >
                        {value}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500 h-full flex flex-col">
      <div className="flex flex-row justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-100 to-slate-400 mb-2">Confusion Matrix</h1>
          <p className="text-slate-400">Detailed classification performance breakdown</p>
        </div>
        
        <div className="flex gap-3 bg-surface p-2 rounded-xl border border-border">
          <select 
            value={selectedModel} 
            onChange={e => setSelectedModel(e.target.value)} 
            className="bg-slate-900 border border-border text-sm rounded-lg px-3 py-1.5 focus:border-blue-500 outline-none text-slate-200"
          >
            {models.length === 0 ? <option value="">No models available</option> : null}
            {models.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
          
          <select 
            value={split} 
            onChange={e => setSplit(e.target.value)} 
            className="bg-slate-900 border border-border text-sm rounded-lg px-3 py-1.5 focus:border-blue-500 outline-none text-slate-200"
          >
            <option value="Test">TEST Split</option>
            <option value="Validation" disabled>VALIDATION Split</option>
            <option value="Train" disabled>TRAIN Split</option>
          </select>
          
          <select 
            value={displayMode} 
            onChange={e => setDisplayMode(e.target.value as any)} 
            className="bg-slate-900 border border-border text-sm rounded-lg px-3 py-1.5 focus:border-blue-500 outline-none text-slate-200"
          >
            <option value="Counts">Counts</option>
            <option value="Normalized">Normalized</option>
          </select>
        </div>
      </div>

      {!models.length ? (
        <div className="flex-1 flex flex-col items-center justify-center bg-surface border border-border rounded-2xl p-8">
           <BarChart size={48} className="text-slate-700 mb-4" />
           <p className="text-lg font-medium text-slate-400 mb-2">No evaluation results available</p>
           <p className="text-sm text-slate-500">Run the ML model evaluation pipeline to view confusion matrices.</p>
        </div>
      ) : loading ? (
        <div className="flex-1 flex items-center justify-center">
           <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : error ? (
        <div className="flex-1 flex flex-col items-center justify-center bg-surface border border-border rounded-2xl p-8 text-red-400">
           <AlertCircle size={48} className="mb-4" />
           <p className="text-lg font-medium mb-2">Failed to load matrix</p>
           <p className="text-sm opacity-80">{error}</p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto space-y-6">
          <div className="bg-surface border border-border rounded-2xl shadow-lg p-6 overflow-hidden">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg"><Grid size={20} /></div>
              <h2 className="text-lg font-semibold text-slate-200">{selectedModel} - {split} Set Confusion Matrix</h2>
            </div>
            <div className="flex justify-center p-4 bg-slate-900/50 rounded-xl border border-slate-800/50">
              {renderMatrix()}
            </div>
          </div>
          
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="bg-surface border border-border p-4 rounded-xl text-center">
              <div className="text-2xl font-mono text-emerald-400">{overallMetrics?.test_accuracy?.toFixed(4) || '-'}</div>
              <div className="text-xs text-slate-500 uppercase mt-1">Accuracy</div>
            </div>
            <div className="bg-surface border border-border p-4 rounded-xl text-center">
              <div className="text-2xl font-mono text-blue-400">{overallMetrics?.precision_macro?.toFixed(4) || '-'}</div>
              <div className="text-xs text-slate-500 uppercase mt-1">Macro Precision</div>
            </div>
            <div className="bg-surface border border-border p-4 rounded-xl text-center">
              <div className="text-2xl font-mono text-blue-400">{overallMetrics?.recall_macro?.toFixed(4) || '-'}</div>
              <div className="text-xs text-slate-500 uppercase mt-1">Macro Recall</div>
            </div>
            <div className="bg-surface border border-border p-4 rounded-xl text-center">
              <div className="text-2xl font-mono text-purple-400">{overallMetrics?.f1_macro?.toFixed(4) || '-'}</div>
              <div className="text-xs text-slate-500 uppercase mt-1">Macro F1</div>
            </div>
            <div className="bg-surface border border-border p-4 rounded-xl text-center">
              <div className="text-2xl font-mono text-purple-400">{overallMetrics?.f1_weighted?.toFixed(4) || '-'}</div>
              <div className="text-xs text-slate-500 uppercase mt-1">Weighted F1</div>
            </div>
          </div>
          
          <div className="bg-surface border border-border rounded-2xl shadow-lg p-6">
            <h2 className="text-lg font-semibold text-slate-200 mb-4">Per-Class Metrics</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-slate-500 uppercase bg-slate-900 border-b border-border">
                  <tr>
                    <th className="px-4 py-3 font-medium">Class</th>
                    <th className="px-4 py-3 font-medium text-right">Precision</th>
                    <th className="px-4 py-3 font-medium text-right">Recall</th>
                    <th className="px-4 py-3 font-medium text-right">F1 Score</th>
                    <th className="px-4 py-3 font-medium text-right">Support</th>
                  </tr>
                </thead>
                <tbody>
                  {perClassMetrics.map((row) => (
                    <tr key={row.class} className="border-b border-slate-800/50 hover:bg-slate-800/20">
                      <td className="px-4 py-3 font-medium text-slate-300">{row.class}</td>
                      <td className="px-4 py-3 font-mono text-right text-blue-400">{row.precision?.toFixed(4)}</td>
                      <td className="px-4 py-3 font-mono text-right text-blue-400">{row.recall?.toFixed(4)}</td>
                      <td className="px-4 py-3 font-mono text-right text-purple-400">{row.f1?.toFixed(4)}</td>
                      <td className="px-4 py-3 font-mono text-right text-slate-400">{row.support}</td>
                    </tr>
                  ))}
                  {perClassMetrics.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-slate-500">No per-class metrics found.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
