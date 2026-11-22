import React, { useState, useEffect } from 'react';
import { Box, Cpu, Shuffle, Code2, AlertCircle } from 'lucide-react';

interface Gate {
  index: number;
  name: string;
  controls: number[];
  targets: number[];
  parameters: number[];
}

interface CircuitData {
  qubits: number;
  gates: number;
  depth: number;
  gate_types: Record<string, number>;
  instructions: Gate[];
}

export default function CircuitAnalyzer() {
  const [activeTab, setActiveTab] = useState('Circuit');
  const [circuitData, setCircuitData] = useState<CircuitData | null>(null);
  const [loading, setLoading] = useState(true);
  
  const [representation, setRepresentation] = useState('FRQI');
  const [size, setSize] = useState(4);
  const [bits, setBits] = useState(8);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/quantum/circuit?representation=${representation}&size=${size}&bits=${bits}`)
      .then(res => res.json())
      .then(data => {
        setCircuitData(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, [representation, size, bits]);
  
  // Create grid for rendering circuit
  // Rows = qubits, Columns = gate layers (simplified: 1 gate per column for now, though real depth packs them)
  const renderCircuit = () => {
    if (!circuitData) return null;
    
    // Limit to first 100 gates to prevent DOM overload on huge circuits
    const displayGates = circuitData.instructions.slice(0, 100);
    const hasMore = circuitData.instructions.length > 100;

    return (
      <div className="w-full h-full overflow-x-auto overflow-y-auto font-mono text-slate-400 text-sm whitespace-pre relative pb-10">
        <div className="inline-flex flex-col relative" style={{ minWidth: 'min-content' }}>
          {Array.from({ length: circuitData.qubits }).map((_, qIdx) => (
            <div key={`wire-${qIdx}`} className="flex items-center h-12 relative" style={{ width: `${displayGates.length * 60 + 100}px` }}>
              <span className="text-blue-400 w-10 shrink-0 sticky left-0 bg-surface z-10 font-bold border-r border-border">q{qIdx}</span>
              <div className="absolute left-10 right-0 top-1/2 h-[2px] bg-slate-700 -translate-y-1/2 z-0" />
            </div>
          ))}
          
          {/* Render gates */}
          {displayGates.map((gate, gIdx) => {
            const minQ = Math.min(...gate.controls, ...gate.targets);
            const maxQ = Math.max(...gate.controls, ...gate.targets);
            
            return (
              <div key={`gate-${gate.index}`} className="absolute top-0 bottom-0 flex flex-col" style={{ left: `${gIdx * 60 + 50}px`, width: '50px' }}>
                {gate.controls.length > 0 && (
                  <div 
                    className="absolute w-[2px] bg-emerald-500 z-10 left-1/2 -translate-x-1/2" 
                    style={{ 
                      top: `${minQ * 48 + 24}px`, 
                      height: `${(maxQ - minQ) * 48}px` 
                    }} 
                  />
                )}
                
                {Array.from({ length: circuitData.qubits }).map((_, qIdx) => {
                  const isControl = gate.controls.includes(qIdx);
                  const isTarget = gate.targets.includes(qIdx);
                  
                  if (!isControl && !isTarget) return <div key={qIdx} className="h-12 relative z-10" />;
                  
                  return (
                    <div key={qIdx} className="h-12 relative flex items-center justify-center z-20 group">
                      {isControl && (
                        <div className="w-3 h-3 rounded-full bg-emerald-500 relative z-20 group-hover:scale-150 transition-transform cursor-help" title={`Control for ${gate.name.toUpperCase()}`} />
                      )}
                      {isTarget && (
                        <div className={`px-2 py-1 rounded shadow-sm text-xs font-bold relative z-20 cursor-help flex flex-col items-center justify-center ${
                           gate.name.startsWith('c') ? 'w-6 h-6 rounded-full border-2 border-emerald-500 bg-surface text-emerald-500' : 'bg-blue-900/80 border border-blue-500/50 text-blue-200'
                        }`} title={`Gate: ${gate.name.toUpperCase()}\nTarget: q${qIdx}\nParams: ${gate.parameters.join(', ')}`}>
                          {gate.name.startsWith('c') && gate.name !== 'cx' ? gate.name.replace('c', '').toUpperCase() : gate.name === 'cx' || gate.name === 'mcx' ? '+' : gate.name.toUpperCase()}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
        {hasMore && (
          <div className="mt-8 text-center text-slate-500 italic">
            ... and {circuitData.instructions.length - 100} more gates not shown for performance.
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500 h-full flex flex-col">
      <div className="flex flex-row justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-100 to-slate-400 mb-2">Circuit Analyzer</h1>
          <p className="text-slate-400">Actual quantum circuit generated by the encoding implementation</p>
        </div>
        
        <div className="flex gap-3 bg-surface p-2 rounded-xl border border-border">
          <select value={representation} onChange={e => setRepresentation(e.target.value)} className="bg-slate-900 border border-border text-sm rounded-lg px-3 py-1.5 focus:border-blue-500 outline-none text-slate-200">
            <option value="FRQI">FRQI</option>
            <option value="NEQR">NEQR</option>
          </select>
          <select value={size} onChange={e => setSize(Number(e.target.value))} className="bg-slate-900 border border-border text-sm rounded-lg px-3 py-1.5 focus:border-blue-500 outline-none text-slate-200">
            <option value={2}>2x2</option>
            <option value={4}>4x4</option>
            <option value={8}>8x8</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 shrink-0">
        <div className="bg-surface border border-border p-4 rounded-xl flex items-center gap-4 relative overflow-hidden group">
          <div className="absolute inset-0 bg-blue-500/5 group-hover:bg-blue-500/10 transition-colors" />
          <div className="p-3 bg-blue-500/10 text-blue-400 rounded-lg relative"><Cpu size={24} /></div>
          <div className="relative">
            <div className="text-2xl font-mono text-slate-200">{loading ? '-' : circuitData?.qubits}</div>
            <div className="text-xs text-slate-500 uppercase font-medium">Qubits</div>
          </div>
        </div>
        <div className="bg-surface border border-border p-4 rounded-xl flex items-center gap-4 relative overflow-hidden group">
          <div className="absolute inset-0 bg-emerald-500/5 group-hover:bg-emerald-500/10 transition-colors" />
          <div className="p-3 bg-emerald-500/10 text-emerald-400 rounded-lg relative"><Code2 size={24} /></div>
          <div className="relative">
            <div className="text-2xl font-mono text-slate-200">{loading ? '-' : circuitData?.gates}</div>
            <div className="text-xs text-slate-500 uppercase font-medium">Total Gates</div>
          </div>
        </div>
        <div className="bg-surface border border-border p-4 rounded-xl flex items-center gap-4 relative overflow-hidden group">
          <div className="absolute inset-0 bg-purple-500/5 group-hover:bg-purple-500/10 transition-colors" />
          <div className="p-3 bg-purple-500/10 text-purple-400 rounded-lg relative"><Shuffle size={24} /></div>
          <div className="relative">
            <div className="text-2xl font-mono text-slate-200">{loading ? '-' : circuitData?.depth}</div>
            <div className="text-xs text-slate-500 uppercase font-medium">Circuit Depth</div>
          </div>
        </div>
        <div className="bg-surface border border-border p-4 rounded-xl flex items-center gap-4 relative overflow-hidden group">
           <div className="absolute inset-0 bg-orange-500/5 group-hover:bg-orange-500/10 transition-colors" />
          <div className="p-3 bg-orange-500/10 text-orange-400 rounded-lg relative"><AlertCircle size={24} /></div>
          <div className="relative">
            <div className="text-2xl font-mono text-slate-200">{loading ? '-' : (circuitData?.gate_types['cx'] || 0) + (circuitData?.gate_types['mcx'] || 0) + (circuitData?.gate_types['cry'] || 0)}</div>
            <div className="text-xs text-slate-500 uppercase font-medium">Controlled Gates</div>
          </div>
        </div>
      </div>

      <div className="flex-1 bg-surface border border-border rounded-2xl shadow-lg flex flex-col overflow-hidden min-h-[500px]">
        <div className="flex border-b border-border bg-slate-900/50 p-2 gap-2">
          {['Circuit', 'Gate Distribution'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab 
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-[0_0_10px_rgba(59,130,246,0.1)]' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
        
        <div className="flex-1 p-0 relative overflow-hidden flex flex-col">
          {loading ? (
             <div className="absolute inset-0 flex items-center justify-center bg-background/50 backdrop-blur-sm z-50">
               <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
             </div>
          ) : activeTab === 'Circuit' ? (
             <div className="flex-1 p-6 overflow-hidden">
               {renderCircuit()}
             </div>
          ) : (
            <div className="p-6">
              <h3 className="text-lg font-medium text-slate-200 mb-6">Gate Type Distribution</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {circuitData && Object.entries(circuitData.gate_types).map(([gate, count]) => (
                  <div key={gate} className="bg-slate-900 border border-slate-800 p-4 rounded-xl flex items-center justify-between">
                    <span className="font-mono text-slate-400 uppercase font-bold text-lg">{gate}</span>
                    <span className="font-mono text-2xl text-blue-400">{count as number}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
