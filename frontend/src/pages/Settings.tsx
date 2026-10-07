import React from 'react';
import { Settings as SettingsIcon, Save, Database, Cpu, Shield, Globe } from 'lucide-react';

export default function Settings() {
  return (
    <div className="space-y-8 animate-in fade-in duration-500 max-w-4xl">
      <div>
        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-100 to-slate-400 mb-2 flex items-center gap-3">
          <SettingsIcon className="text-slate-400" /> Settings
        </h1>
        <p className="text-slate-400">Manage application preferences and quantum backend configurations</p>
      </div>

      <div className="bg-surface border border-border rounded-2xl overflow-hidden shadow-lg">
        <div className="p-6 border-b border-border bg-card/50 flex items-center gap-3">
          <Cpu className="text-blue-400" size={20} />
          <h2 className="text-lg font-semibold text-slate-200">Quantum Simulator Backend</h2>
        </div>
        <div className="p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">Default Simulator</label>
              <select className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-slate-200 focus:outline-none focus:border-blue-500 transition-colors">
                <option value="aer_simulator">Qiskit Aer Simulator (Local CPU)</option>
                <option value="aer_simulator_gpu" disabled>Qiskit Aer Simulator (Local GPU) - Unavailable</option>
                <option value="ibmq_qasm_simulator">IBMQ QASM Simulator (Cloud)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">Simulation Precision</label>
              <select className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-slate-200 focus:outline-none focus:border-blue-500 transition-colors">
                <option value="double">Double (64-bit)</option>
                <option value="single">Single (32-bit)</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-2">IBMQ API Token</label>
            <div className="flex gap-4">
              <input 
                type="password" 
                placeholder="••••••••••••••••••••••••••••" 
                className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
              />
              <button className="px-4 py-2 bg-blue-600/20 text-blue-400 border border-blue-500/50 rounded-lg hover:bg-blue-600/30 transition-colors">
                Verify
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-surface border border-border rounded-2xl overflow-hidden shadow-lg">
        <div className="p-6 border-b border-border bg-card/50 flex items-center gap-3">
          <Database className="text-emerald-400" size={20} />
          <h2 className="text-lg font-semibold text-slate-200">Dataset & Storage</h2>
        </div>
        <div className="p-6 space-y-6">
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-2">Dataset Path</label>
            <input 
              type="text" 
              defaultValue="/data/NEU-DET" 
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-emerald-500"
            />
          </div>
          <div>
            <label className="flex items-center gap-3">
              <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-slate-700 bg-slate-900 text-emerald-500 focus:ring-emerald-500 focus:ring-offset-slate-900" />
              <span className="text-sm font-medium text-slate-300">Auto-save experiment results to CSV</span>
            </label>
          </div>
        </div>
      </div>

      <div className="flex justify-end gap-4">
        <button className="px-6 py-2.5 rounded-xl font-medium text-slate-300 hover:text-white transition-colors">
          Reset Defaults
        </button>
        <button className="px-6 py-2.5 rounded-xl font-medium bg-gradient-to-r from-blue-600 to-cyan-500 text-white shadow-lg shadow-blue-500/25 border border-blue-400/50 hover:-translate-y-0.5 transition-all flex items-center gap-2">
          <Save size={18} /> Save Settings
        </button>
      </div>
    </div>
  );
}
