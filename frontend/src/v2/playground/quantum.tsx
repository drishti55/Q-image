/* eslint-disable @typescript-eslint/no-explicit-any */
// Quantum walkthroughs. Values from the V3 playground data (real FRQIEncoder / NEQREncoder / feature-map / VQC code,
// simulated exactly on a CPU). No classifier output is shown for the artificial grid.
import { useState } from 'react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { MiniCircuit, Note, PixelGrid, ValueBars, Vec, fx } from './widgets';
import type { Gate } from './widgets';
import type { Algo, Ctx, Step } from './types';
import { f4 } from './types';
import { NO_PRED } from './classical';

const SUB = '₀₁₂₃₄₅₆₇';
const obs = (r: string) => r.replace(/^Z+\(([\d, ]+)\)$/, (_m, q: string) => q.split(',').filter((x) => x.trim()).map((x) => `Z${SUB[Number(x)]}`).join(''));
const SIM = <Note tone="cyan">Noiseless statevector simulation on a classical CPU (Qiskit conventions) — not quantum hardware.</Note>;
const pos = (c: Ctx) => 4 * c.px.r + c.px.c;
const frqiRow = (c: Ctx) => (c.d.frqi.positions as any[]).find((p) => p.position === pos(c));
const neqrP = (c: Ctx) => c.d.neqr.precisions[c.o.bits ?? '4'];
const neqrRow = (c: Ctx) => (neqrP(c).pixels as any[]).find((p) => p.row === c.px.r && p.col === c.px.c);
const ad4 = (c: Ctx) => c.d.pixel_traces[c.sel].pca4_angle_delta as number[];
const l2 = (v: number[]) => Math.sqrt(v.reduce((a, b) => a + b * b, 0));

function Registers({ n, extra, active }: { n: number; extra: string; active?: 'pos' | 'int' }) {
  return (
    <div className="flex flex-wrap gap-2 text-xs">
      {Array.from({ length: n }, (_, q) => <span key={q} className={`rounded-md px-2 py-1 ring-1 transition ${active === 'pos' ? 'bg-blue-500/25 text-blue-100 ring-blue-400' : 'bg-blue-500/10 text-blue-200 ring-blue-500/30'}`}>q{q} position</span>)}
      <span className={`rounded-md px-2 py-1 ring-1 transition ${active === 'int' ? 'bg-violet-500/25 text-violet-100 ring-violet-400' : 'bg-violet-500/10 text-violet-200 ring-violet-500/30'}`}>{extra}</span>
    </div>
  );
}

/** Logical gate block for one pixel: X gates select the position, a multi-controlled gate writes the intensity. */
function PixelBlock({ n, xq, target, label }: { n: number; xq: number[]; target: number[]; label: string }) {
  const H = 26, W = 300, T = 14, L = 74;
  const cols = [L + 30, L + 130, L + 230];
  return (
    <svg viewBox={`0 0 ${W + 20} ${T + n * H}`} className="w-full max-w-lg rounded-xl bg-[#050913] ring-1 ring-slate-800" role="img" aria-label="pixel gate block">
      {Array.from({ length: n }, (_, q) => (
        <g key={q}><text x={4} y={T + q * H + 4} fontSize={10} fill="#94a3b8" fontFamily="ui-monospace, SFMono-Regular, Menlo, monospace">{q < 4 ? `q${q} pos` : `q${q} ${n === 5 ? 'colour' : 'int'}`}</text>
          <line x1={L - 6} x2={W + 10} y1={T + q * H} y2={T + q * H} stroke="#334155" /></g>))}
      {[cols[0], cols[2]].map((x, k) => xq.map((q) => (
        <g key={`${k}-${q}`}><rect x={x - 11} y={T + q * H - 9} width={22} height={18} rx={3} fill="#7f1d1d" /><text x={x} y={T + q * H + 4} fontSize={9} fill="#fff" textAnchor="middle">X</text></g>)))}
      <line x1={cols[1]} x2={cols[1]} y1={T} y2={T + Math.max(3, ...target) * H} stroke="#22d3ee" strokeWidth={1.5} />
      {[0, 1, 2, 3].map((q) => <circle key={q} cx={cols[1]} cy={T + q * H} r={4} fill="#22d3ee" />)}
      {target.map((q) => <g key={q}><rect x={cols[1] - 22} y={T + q * H - 10} width={44} height={20} rx={4} fill="#0e7490" stroke="#22d3ee" /><text x={cols[1]} y={T + q * H + 4} fontSize={9} fill="#e2e8f0" textAnchor="middle">{label}</text></g>)}
    </svg>
  );
}

// ─── FRQI ───
export const frqi: Algo = {
  id: 'frqi', family: 'quantum', name: 'FRQI', blurb: 'Brightness as a rotation angle of one qubit',
  options: [{ key: 'shots', label: 'Shots', def: '1000', values: [['100', '100'], ['1000', '1,000'], ['10000', '10,000']] }],
  trace: (c) => {
    const p = frqiRow(c);
    const rec = c.d.frqi.shots[c.o.shots ?? '1000'].reconstructed_255[c.px.r][c.px.c];
    return [
      { key: 'pix', label: 'pixel', value: `${c.px.v} at #${pos(c)}`, short: `${c.px.v}` },
      { key: 'norm', label: 'intensity', value: f4(p.intensity), short: p.intensity.toFixed(3) },
      { key: 'theta', label: 'angle θ', value: `${f4(p.theta)} rad = ${p.theta_deg.toFixed(2)}°`, short: `θ${p.theta.toFixed(2)}` },
      { key: 'pos', label: 'position', value: `|${p.pos_bits_q3q2q1q0}⟩`, short: p.pos_bits_q3q2q1q0 },
      { key: 'rot', label: 'rotation', value: `MCRY(2θ = ${f4(2 * p.theta)})`, short: 'RY' },
      { key: 'amp', label: 'amplitudes', value: `${f4(p.amp_colour0)}|0⟩ + ${f4(p.amp_colour1)}|1⟩`, short: 'ψ' },
      { key: 'meas', label: 'P(colour=1)', value: f4(p.p_colour1_given_position), short: `P${p.p_colour1_given_position.toFixed(2)}` },
      { key: 'rec', label: 'reconstructed', value: `${Math.round(c.d.frqi.reconstructed_exact_255[c.px.r][c.px.c])} (exact) · ${Math.round(rec)} (${Number(c.o.shots ?? 1000).toLocaleString()} shots)`, short: `${Math.round(rec)}` },
    ];
  },
  steps: (c): Step[] => {
    const f = c.d.frqi;
    const p = frqiRow(c);
    const blk = (f.blocks as any[]).find((b) => b.position === pos(c));
    const shots = c.o.shots ?? '1000';
    const crop = (m: number[][]) => m.slice(0, 3).map((r) => r.slice(0, 3).map((v) => Math.round(v)));
    return [
      { title: 'Pixel selection', stage: 'pix', grid: 'padded', hl: 'selected',
        explain: `Pixel ${c.px.v} (row ${c.px.r + 1}, column ${c.px.c + 1}) is followed through the encoding. FRQI needs 2ⁿ pixels, so the 3×3 grid is placed in a 4×4 grid with zero padding; this pixel becomes position #${pos(c)}.`,
        why: 'FRQI stores every pixel in one quantum state; following one pixel shows how its position and brightness are stored.',
        formula: <>position i = 4 · row + column</>, out: <>pixel {c.px.v} → position #{pos(c)}</>,
        interp: 'Quantum: the whole image becomes one state of 5 qubits; each pixel is one term of a superposition.',
        body: <Note>Click another image pixel on the left to follow it instead. Padding pixels (hatched) carry no information and add no gates.</Note> },
      { title: 'Intensity normalisation', stage: 'norm', grid: 'padded', hl: 'selected',
        explain: 'The pixel is scaled to 0–1.', why: 'The angle formula maps the range 0–1 onto 0–90°.',
        formula: <>I = pixel / 255</>, out: <>{c.px.v} / 255 = <b>{f4(p.intensity)}</b></>,
        interp: 'Classical step before the quantum part (same as for the classical models).',
        body: <ValueBars max={1} items={(c.d.pixel_traces as any[]).map((t, i) => ({ label: `pixel ${t.value}`, value: t.normalized, strong: i === c.sel }))} digits={4} /> },
      { title: 'Angle calculation', stage: 'theta', grid: 'padded', hl: 'given',
        explain: 'Each normalised intensity becomes an angle between 0 and 90°. All nine cells of the 3×3 image are listed; the five padding cells get θ = 0.',
        why: 'A rotation angle is how a single qubit can store a continuous brightness value.',
        formula: <>θᵢ = (π/2) · (pixelᵢ / 255)</>,
        out: <>θ = (π/2)·{f4(p.intensity)} = <b>{f4(p.theta)} rad = {p.theta_deg.toFixed(2)}°</b></>,
        interp: 'Quantum: brightness is stored in the amplitude, through cos θ and sin θ.',
        body: <table className="text-sm tabular-nums"><thead className="text-left text-xs text-slate-500"><tr><th className="pr-4">cell</th><th className="pr-4">pixel</th><th className="pr-4">θ (rad)</th><th className="pr-4">θ (°)</th><th>kind</th></tr></thead>
          <tbody>{[0, 1, 2].flatMap((r) => [0, 1, 2].map((cc) => {
            const q = (f.positions as any[]).find((x) => x.position === 4 * r + cc);
            const on = r === c.px.r && cc === c.px.c;
            return <tr key={`${r}${cc}`} className={on ? 'bg-cyan-500/15 text-cyan-100' : q.pixel ? 'text-white' : 'text-slate-500'}><td className="pr-4">({r + 1},{cc + 1})</td><td className="pr-4">{q.pixel}</td><td className="pr-4 font-mono">{f4(q.theta)}</td><td className="pr-4 font-mono">{q.theta_deg.toFixed(2)}°</td><td>{r < 2 && cc < 2 ? 'pixel' : 'padding'}</td></tr>;
          }))}</tbody></table> },
      { title: 'Position encoding', stage: 'pos', grid: 'padded', hl: 'selected',
        explain: `16 positions need 4 position qubits. Position #${pos(c)} is the basis state |${p.pos_bits_q3q2q1q0}⟩ (q3 q2 q1 q0).`,
        why: 'Position qubits label which pixel each part of the state belongs to.',
        formula: <>|i⟩ = |q3 q2 q1 q0⟩,  i = {pos(c)} → |{p.pos_bits_q3q2q1q0}⟩</>, out: <>|{p.pos_bits_q3q2q1q0}⟩</>,
        interp: 'Quantum: positions are basis states — binary labels, not angles.',
        body: <Registers n={4} extra="q4 colour" active="pos" /> },
      { title: 'Quantum state preparation', stage: 'pos', grid: 'padded', hl: 'given',
        explain: 'Hadamard gates on the 4 position qubits create an equal superposition of all 16 positions; the colour qubit starts in |0⟩.',
        why: 'Superposition lets one state hold all 16 pixels at once.', formula: <>H⊗4 |0000⟩ = ¼ Σᵢ |i⟩</>,
        out: <>16 positions, amplitude 1/4 each</>, interp: 'Quantum: superposition — there is no classical analogue of one register holding 16 positions.',
        body: <MiniCircuit n={5} labels={['q0 pos', 'q1 pos', 'q2 pos', 'q3 pos', 'q4 colour']} gates={[0, 1, 2, 3].map((q) => ({ name: 'h', qubits: [q], params: [] }))} /> },
      { title: 'Position and intensity qubits', stage: 'pos', grid: 'padded', hl: 'selected',
        explain: `${f.n_qubits} qubits in total: 4 say WHERE (position), 1 says HOW BRIGHT (colour).`,
        why: 'Separating position and intensity is what makes the image recoverable.', formula: <>|I⟩ = ¼ Σᵢ (cos θᵢ |0⟩ + sin θᵢ |1⟩) ⊗ |i⟩</>,
        out: <>5 qubits for 16 pixels</>, interp: 'Quantum: n position qubits address 2ⁿ pixels — exponentially compact.',
        body: <Registers n={4} extra="q4 colour (intensity)" active="int" /> },
      { title: 'Controlled rotation for this pixel', stage: 'rot', grid: 'padded', hl: 'selected',
        explain: `X gates flip the position qubits that are 0 in |${p.pos_bits_q3q2q1q0}⟩, so the control fires only for position #${pos(c)}; a multi-controlled RY then rotates the colour qubit by 2θ; the X gates are undone.`,
        why: 'Only the selected position may receive this pixel\'s angle.',
        formula: <>MCRY(2θ) = MCRY({f4(2 * p.theta)})</>,
        out: <>{blk ? (blk.x_on_qubits.length ? `X on q${blk.x_on_qubits.join(', q')}` : 'no X') : 'no gates (zero pixel)'} → MCRY({f4(2 * p.theta)}) on q4</>,
        interp: `Quantum: Qiskit expands the four multi-controlled rotations into ${f.logical_gates} basic gates (depth ${f.depth}).`,
        body: blk ? <PixelBlock n={5} xq={blk.x_on_qubits} target={[4]} label={`RY ${(2 * p.theta).toFixed(2)}`} /> : <Note>This pixel is 0: no gates are added.</Note> },
      { title: 'Resulting quantum state', stage: 'amp', grid: 'padded', hl: 'selected',
        explain: 'Amplitudes read from the simulated statevector of the real circuit; the brightness lives in how the amplitude splits between colour |0⟩ and |1⟩.',
        why: 'This is the actual quantum representation of the image.',
        formula: <>amp(|0⟩|i⟩) = cos θᵢ / 4,  amp(|1⟩|i⟩) = sin θᵢ / 4</>,
        out: <>{f4(p.amp_colour0)} |0⟩|{p.pos_bits_q3q2q1q0}⟩ + {f4(p.amp_colour1)} |1⟩|{p.pos_bits_q3q2q1q0}⟩</>,
        interp: 'Quantum: amplitude encoding — the value is in the amplitudes, which cannot be read directly.',
        body: <><table className="text-xs tabular-nums"><thead className="text-left text-slate-500"><tr><th className="pr-4">position</th><th className="pr-4">pixel</th><th className="pr-4">amp |0⟩</th><th className="pr-4">amp |1⟩</th><th>P(1 | position)</th></tr></thead>
          <tbody>{(f.positions as any[]).filter((x) => x.pixel > 0 || x.position === 2).map((x) => <tr key={x.position} className={x.position === pos(c) ? 'bg-cyan-500/15 text-cyan-100' : x.pixel ? 'text-white' : 'text-slate-500'}><td className="pr-4">#{x.position}</td><td className="pr-4">{x.pixel}</td><td className="pr-4 font-mono">{f4(x.amp_colour0)}</td><td className="pr-4 font-mono">{f4(x.amp_colour1)}</td><td className="font-mono">{f4(x.p_colour1_given_position)}</td></tr>)}</tbody></table>
          <Note>Statevector vs formula: max difference {Number(f.statevector_formula_max_abs_error).toExponential(1)}.</Note>{SIM}</> },
      { title: 'Measurement', stage: 'meas', grid: 'padded', hl: 'selected',
        explain: `Each shot returns one position and one colour bit. Most frequent outcomes for ${Number(shots).toLocaleString()} shots (switch above).`,
        why: 'Measurement is the only way to get classical numbers out of a quantum state; it destroys the superposition.',
        formula: <>P(colour = 1 | position) = sin²θ</>, out: <>exact P(1 | #{pos(c)}) = sin²({f4(p.theta)}) = <b>{f4(p.p_colour1_given_position)}</b></>,
        interp: 'Quantum: results are probabilistic; more shots → better estimates.',
        body: <><ValueBars items={(f.shots[shots].top_counts as [string, number][]).map(([b, n]) => ({ label: `colour ${b[0]} · pos #${parseInt(b.slice(1), 2)}`, value: n, strong: parseInt(b.slice(1), 2) === pos(c) }))} digits={0} /><Note>Bit order: colour qubit first, then q3…q0.</Note></> },
      { title: 'Reconstruction', stage: 'rec', grid: 'demo', hl: 'selected',
        explain: 'Each pixel is recovered from P(colour = 1 | position): θ = arcsin √P, pixel = θ/(π/2)·255. Exact with the statevector; noisy with finite shots.',
        why: 'Checks that the encoding really stored the image.', formula: <>pixel = (2/π) · arcsin √P · 255</>,
        out: <>{c.px.v} → {Math.round(f.reconstructed_exact_255[c.px.r][c.px.c])} (exact) · {Math.round(f.shots[shots].reconstructed_255[c.px.r][c.px.c])} ({Number(shots).toLocaleString()} shots)</>,
        interp: 'Quantum: FRQI is exactly invertible in simulation, but needs many shots on hardware.',
        body: <div className="flex flex-wrap gap-6"><PixelGrid label="original" values={c.d.grid} size={52} padding={(r, cc) => !(r < 2 && cc < 2)} />
          <PixelGrid label="statevector (exact)" values={crop(f.reconstructed_exact_255)} size={52} />
          <PixelGrid label={`${Number(shots).toLocaleString()} shots`} values={crop(f.shots[shots].reconstructed_255)} size={52} /></div> },
    ];
  },
};

// ─── NEQR ───
export const neqr: Algo = {
  id: 'neqr', family: 'quantum', name: 'NEQR', blurb: 'Brightness as a binary number in qubits',
  options: [{ key: 'bits', label: 'Precision', def: '4', values: [['2', '2-bit'], ['4', '4-bit'], ['8', '8-bit']] }],
  trace: (c) => {
    const p = neqrP(c), x = neqrRow(c);
    return [
      { key: 'pix', label: 'pixel', value: `${c.px.v}`, short: `${c.px.v}` },
      { key: 'q', label: 'quantised', value: `${c.px.v}/255·${p.levels - 1} = ${x.scaled.toFixed(3)} → ${x.quantized}`, short: `${x.quantized}` },
      { key: 'bin', label: 'binary', value: x.binary_msb_first, short: x.binary_msb_first },
      { key: 'pos', label: 'position', value: `|${(pos(c)).toString(2).padStart(4, '0')}⟩`, short: (pos(c)).toString(2).padStart(4, '0') },
      { key: 'mcx', label: 'MCX targets', value: (p.blocks as any[]).find((b) => b.position === pos(c))?.mcx_targets.map((q: number) => `q${q}`).join(', ') || 'none', short: 'X' },
      { key: 'meas', label: 'basis state', value: `|${x.binary_msb_first}⟩|${(pos(c)).toString(2).padStart(4, '0')}⟩`, short: '|C⟩|i⟩' },
      { key: 'rec', label: 'reconstructed', value: `${x.represented_255.toFixed(1)} (error ${x.error_255 > 0 ? '+' : ''}${x.error_255.toFixed(1)})`, short: `${Math.round(x.represented_255)}` },
    ];
  },
  steps: (c): Step[] => {
    const b = c.o.bits ?? '4';
    const p = neqrP(c), x = neqrRow(c);
    const blk = (p.blocks as any[]).find((k) => k.position === pos(c));
    const bs = (p.basis_states as any[]).find((s) => s.position === pos(c));
    const crop = (m: number[][]) => m.slice(0, 3).map((r) => r.slice(0, 3).map((v) => Math.round(v)));
    const fr = frqiRow(c);
    return [
      { title: 'Original pixel value', stage: 'pix', grid: 'demo', hl: 'selected', explain: `Pixel ${c.px.v} will be stored as a ${b}-bit binary number (switch precision above).`,
        why: 'NEQR stores intensity exactly as bits, unlike FRQI which uses an angle.', out: <>{c.px.v}</>,
        interp: 'Quantum: NEQR is a basis-state (digital) encoding.', body: <Note>Try 2, 4 and 8 bits and watch the binary code and the reconstruction error change.</Note> },
      { title: `Intensity quantisation (${b}-bit)`, stage: 'q', grid: 'demo', hl: 'given',
        explain: `Each pixel is rounded to one of ${p.levels} levels.`, why: 'A fixed number of qubits can only hold a fixed number of brightness levels.',
        formula: <>q = round(pixel / 255 · {p.levels - 1})</>, out: <>{c.px.v}/255·{p.levels - 1} = {x.scaled.toFixed(3)} → q = <b>{x.quantized}</b></>,
        interp: 'Quantisation is a classical rounding step; it is where precision is lost.',
        body: <table className="text-sm tabular-nums"><thead className="text-left text-xs text-slate-500"><tr><th className="pr-4">pixel</th><th className="pr-4">scaled</th><th className="pr-4">q</th><th className="pr-4">represented</th><th>error</th></tr></thead>
          <tbody>{(p.pixels as any[]).map((y) => <tr key={`${y.row}${y.col}`} className={y.row === c.px.r && y.col === c.px.c ? 'bg-cyan-500/15 text-cyan-100' : ''}><td className="pr-4">{y.pixel}</td><td className="pr-4 font-mono">{y.scaled.toFixed(3)}</td><td className="pr-4">{y.quantized}</td><td className="pr-4">{y.represented_255.toFixed(1)}</td><td className={Math.abs(y.error_255) > 0.5 ? 'text-amber-300' : 'text-emerald-300'}>{y.error_255 > 0 ? '+' : ''}{y.error_255.toFixed(1)}</td></tr>)}</tbody></table> },
      { title: 'Binary conversion', stage: 'bin', grid: 'demo', hl: 'selected',
        explain: `q = ${x.quantized} written with ${b} bits (most significant bit first).`, why: 'Each bit will be one qubit: 0 = |0⟩, 1 = |1⟩.',
        formula: <>q = Σₖ bₖ · 2ᵏ</>, out: <>{x.quantized} = <b className="font-mono">{x.binary_msb_first}</b>₂</>,
        interp: 'Quantum: the intensity qubits are set to exactly these bit values.',
        body: <><div className="flex gap-1.5" data-testid="neqr-bits">{x.binary_msb_first.split('').map((bit: string, i: number) => <div key={i} className={`grid h-12 w-10 place-items-center rounded-lg font-mono text-lg ring-1 transition ${bit === '1' ? 'bg-violet-500/30 text-white ring-violet-400' : 'bg-slate-900 text-slate-500 ring-slate-700'}`}>{bit}</div>)}</div>
          {b === '2' && <Note tone="amber">At 2 bits, 19 and 20 both round to 0 and become indistinguishable from the black padding.</Note>}</> },
      { title: 'Amplitude encoding vs basis-state encoding', stage: 'bin', grid: 'demo', hl: 'selected',
        explain: 'FRQI stores brightness in amplitudes (an angle on one qubit). NEQR stores it in basis states (a binary number on several qubits).',
        why: 'The two choices trade qubits for precision and readability.',
        out: <>FRQI: {f4(fr.amp_colour0)}|0⟩ + {f4(fr.amp_colour1)}|1⟩ on 1 qubit · NEQR: |{x.binary_msb_first}⟩ on {b} qubits</>,
        interp: 'Quantum: amplitude encoding is compact but needs many measurements to read; basis encoding is read exactly from one measurement per position.',
        body: <div className="grid gap-3 sm:grid-cols-2"><div className="rounded-xl bg-slate-900/60 p-3 ring-1 ring-slate-800"><div className="text-xs font-semibold text-cyan-200">FRQI · amplitude</div><div className="mt-1 font-mono text-sm text-white">cos θ|0⟩ + sin θ|1⟩</div><div className="mt-1 text-xs text-slate-400">1 intensity qubit · continuous · read statistically</div></div>
          <div className="rounded-xl bg-slate-900/60 p-3 ring-1 ring-slate-800"><div className="text-xs font-semibold text-violet-200">NEQR · basis state</div><div className="mt-1 font-mono text-sm text-white">|{x.binary_msb_first}⟩</div><div className="mt-1 text-xs text-slate-400">{b} intensity qubits · discrete · read exactly</div></div></div> },
      { title: 'Position encoding', stage: 'pos', grid: 'padded', hl: 'selected',
        explain: `As in FRQI, the grid sits in a 4×4 grid; position #${pos(c)} is |${pos(c).toString(2).padStart(4, '0')}⟩ on qubits q0–q3.`,
        why: 'Each intensity must be attached to its position.', formula: <>|i⟩ = |q3 q2 q1 q0⟩</>, out: <>|{pos(c).toString(2).padStart(4, '0')}⟩</>,
        interp: 'Quantum: identical position register to FRQI.', body: <Registers n={4} extra={`q4–q${3 + Number(b)} intensity`} active="pos" /> },
      { title: 'Intensity register', stage: 'mcx', grid: 'padded', hl: 'selected',
        explain: `${b} intensity qubits (least-significant bit on q4) — ${p.n_qubits} qubits in total.`, why: 'More bits = more qubits = finer brightness.',
        formula: <>|I⟩ = ¼ Σᵢ |Cᵢ⟩ ⊗ |i⟩</>, out: <>{p.n_qubits} qubits ({b} intensity + 4 position)</>,
        interp: 'Quantum: qubit count grows with precision (FRQI always uses one).', body: <Registers n={4} extra={`q4–q${3 + Number(b)} intensity (${b} bits)`} active="int" /> },
      { title: 'State preparation: controlled operations', stage: 'mcx', grid: 'padded', hl: 'selected',
        explain: `H on the position qubits creates all 16 positions; then, for this pixel, X gates select position #${pos(c)} and multi-controlled X gates flip exactly the intensity qubits whose bit is 1.`,
        why: 'Writes the binary intensity into the right position only.',
        out: <>{blk ? `${blk.x_on_qubits.length ? `X on q${blk.x_on_qubits.join(', q')}` : 'no X'} → MCX onto ${blk.mcx_targets.length ? `q${blk.mcx_targets.join(', q')}` : 'nothing'}` : 'q = 0: no gates'}</>,
        interp: `Quantum: real circuit has ${p.logical_gates} gates (depth ${p.depth}).`,
        body: blk && blk.mcx_targets.length ? <PixelBlock n={4 + Number(b)} xq={blk.x_on_qubits} target={blk.mcx_targets} label="X" /> : <Note>This pixel quantises to 0 at {b} bits: no gates are added.</Note> },
      { title: 'Measurement', stage: 'meas', grid: 'padded', hl: 'selected',
        explain: 'Every outcome is one basis state: a position plus its exact binary intensity, each with probability 1/16.',
        why: 'One measurement per position returns the stored bits exactly.', formula: <>P(|Cᵢ⟩|i⟩) = 1/16</>,
        out: <>{bs ? <>|{bs.bitstring}⟩ amplitude {fx(bs.amplitude, 3)}</> : 'not in the non-zero list'}</>, interp: 'Quantum: deterministic bits per position, unlike FRQI\'s probabilities.',
        body: <div className="max-h-64 overflow-auto"><table className="text-xs tabular-nums"><thead className="text-left text-slate-500"><tr><th className="pr-4">basis state</th><th className="pr-4">position</th><th className="pr-4">intensity q</th><th>amplitude</th></tr></thead>
          <tbody>{(p.basis_states as any[]).map((s) => <tr key={s.index} className={s.position === pos(c) ? 'bg-cyan-500/15 text-cyan-100' : s.intensity_value ? 'text-white' : 'text-slate-500'}><td className="pr-4 font-mono">|{s.bitstring}⟩</td><td className="pr-4">#{s.position}</td><td className="pr-4">{s.intensity_value}</td><td className="font-mono">{fx(s.amplitude, 3)}</td></tr>)}</tbody></table></div> },
      { title: 'Reconstruction', stage: 'rec', grid: 'demo', hl: 'selected',
        explain: 'Reading each position\'s bits gives the quantised image back exactly; the only error is the rounding.',
        why: 'Shows the precision cost of each bit depth.', formula: <>pixel = q / {p.levels - 1} · 255</>,
        out: <>{c.px.v} → <b>{x.represented_255.toFixed(1)}</b> (error {x.error_255 > 0 ? '+' : ''}{x.error_255.toFixed(1)})</>,
        interp: 'Higher precision reconstructs better, yet in the real experiments 8-bit NEQR kernels classified worse than 4-bit: their overlap only rewards exactly equal intensities, which become rare at 256 levels.',
        body: <div className="flex flex-wrap gap-6"><PixelGrid label="original" values={c.d.grid} size={52} padding={(r, cc) => !(r < 2 && cc < 2)} /><PixelGrid label={`NEQR ${b}-bit decoded`} values={crop(p.reconstructed_exact_255)} size={52} /></div> },
    ];
  },
};

// ─── QKC ───
const FM: Record<string, string> = { product_ry: 'Product-RY', zz_linear: 'ZZ-linear', zz_full: 'ZZ-full' };
const STRUCT: Record<string, string> = {
  product_ry: 'RY(xᵢ) on each qubit only — no entanglement. Its kernel has a closed classical form, so it is a classical control.',
  zz_linear: 'H and P(2xᵢ) on each qubit, then CX–P(2(π−xᵢ)(π−xⱼ))–CX on neighbouring pairs (0-1, 1-2, 2-3): entanglement along a chain.',
  zz_full: 'H and P(2xᵢ) on each qubit, then CX–P(2(π−xᵢ)(π−xⱼ))–CX on every pair (6 pairs): all-to-all entanglement.',
};

function KernelExplorer({ m, labels }: { m: number[][]; labels: string[] }) {
  const [cell, setCell] = useState<[number, number]>([0, 1]);
  const [i, j] = cell;
  return (
    <div>
      <div className="overflow-x-auto"><table className="text-[10px] tabular-nums" aria-label="kernel matrix">
        <thead><tr><th />{labels.map((l) => <th key={l} className="w-11 px-0.5 pb-1 font-normal text-slate-400">{l.slice(0, 6)}</th>)}</tr></thead>
        <tbody>{m.map((row, a) => (<tr key={a}><th className="whitespace-nowrap pr-1.5 text-right font-normal text-slate-400">{labels[a]}</th>
          {row.map((v, b) => <td key={b} data-testid={`k-${a}-${b}`} onClick={() => setCell([a, b])} className={`h-9 w-11 cursor-pointer text-center text-slate-100 ${a === i && b === j ? 'ring-2 ring-white' : 'ring-1 ring-slate-900'}`} style={{ background: `rgba(25,158,112,${0.08 + 0.85 * Math.max(0, Math.min(1, v))})` }}>{v.toFixed(2)}</td>)}</tr>))}</tbody></table></div>
      <div className="mt-2 rounded-lg bg-slate-900/60 p-2 text-xs text-slate-200 ring-1 ring-slate-800" data-testid="kernel-entry">
        K({labels[i]}, {labels[j]}) = <b>{m[i][j].toFixed(4)}</b> — {i === j ? 'a state overlaps perfectly with itself (1).' : `the squared overlap of the two quantum states: ${m[i][j] > 0.5 ? 'similar' : m[i][j] > 0.15 ? 'partly similar' : 'nearly orthogonal (very different)'}.`} Click any cell.
      </div>
    </div>
  );
}

export const qkc: Algo = {
  id: 'qkc', family: 'quantum', name: 'Quantum kernel (QKC)', blurb: 'Similarity from overlapping quantum states',
  options: [{ key: 'fmap', label: 'Feature map', def: 'zz_full', values: [['product_ry', 'Product-RY'], ['zz_linear', 'ZZ-linear'], ['zz_full', 'ZZ-full']] }],
  trace: (c) => {
    const m = c.d.qkc.maps[c.o.fmap ?? 'zz_full'];
    return [
      { key: 'in', label: 'feature change', value: `Δa = [${ad4(c).map((v) => v.toFixed(3)).join(', ')}]`, short: `Δ${l2(ad4(c)).toFixed(2)}` },
      { key: 'scale', label: 'gate angles', value: `x = ${m.params.bandwidth} · a`, short: 'x' },
      { key: 'fmap', label: 'feature map', value: `${FM[c.o.fmap ?? 'zz_full']}, ${m.n_gates} gates`, short: 'U(x)' },
      { key: 'state', label: 'state', value: '16 amplitudes', short: 'ψ' },
      { key: 'k', label: 'overlap', value: '|⟨φ(x)|φ(y)⟩|²', short: 'K' },
      { key: 'svm', label: 'classical SVM', value: `C = ${m.params.C}`, short: 'SVM' },
    ];
  },
  steps: (c): Step[] => {
    const q = c.d.qkc;
    const fm = c.o.fmap ?? 'zz_full';
    const m = q.maps[fm];
    return [
      { title: 'Input features', stage: 'in', hl: 'selected',
        explain: `The image is reduced to 4 numbers (real seed-0 PCA-4 of the resized image) scaled to angles in [0, π]. Bars: how much pixel ${c.px.v} moves each angle.`,
        why: 'Four features → four qubits keeps the circuit readable.', out: <><Vec v={q.features} digits={3} /> (Δ from this pixel: <Vec v={ad4(c)} digits={3} />)</>,
        interp: 'Classical preprocessing feeding a quantum circuit.', body: <ValueBars signed items={ad4(c).map((v, i) => ({ label: `Δ angle ${i + 1}`, value: v }))} digits={3} /> },
      { title: 'Feature scaling (bandwidth)', stage: 'scale', hl: 'none',
        explain: `Angles are multiplied by the bandwidth chosen on validation (${m.params.bandwidth}).`, why: 'Too large angles make every pair of states nearly orthogonal ("kernel concentration"); too small makes them all alike.',
        formula: <>x = bandwidth · a</>, out: <Vec v={m.x_scaled} digits={3} />, interp: 'Quantum: the bandwidth controls how spread out the states are.',
        body: q.features.some((a: number) => a < 0 || a > Math.PI) ? <Note tone="amber">One angle falls slightly outside [0, π]: the scaler was fitted on training images and the demo grid is unlike any of them.</Note> : <Note>All angles inside [0, π].</Note> },
      { title: `Quantum feature map: ${FM[fm]}`, stage: 'fmap', hl: 'none', explain: STRUCT[fm],
        why: 'The feature map turns numbers into a quantum state; its entanglement decides which feature interactions the kernel can see.',
        formula: fm === 'product_ry' ? <>U(x) = ⊗ᵢ RY(xᵢ)</> : <>U(x) = [⊗ H] · Πᵢ P(2xᵢ) · Π₍ᵢ,ⱼ₎ CX P(2(π−xᵢ)(π−xⱼ)) CX</>,
        out: <>{m.n_gates} gates, depth {m.depth}</>, interp: 'Quantum: entangling gates create correlations between qubits that a product map cannot express.',
        body: <MiniCircuit n={4} gates={m.circuit as Gate[]} /> },
      { title: 'Circuit execution', stage: 'state', hl: 'none', explain: 'Running the circuit gives a 16-amplitude state |φ(x)⟩ (magnitudes from the exact simulation).',
        why: 'Each image gets its own quantum state.', out: <>{(m.statevector_abs as number[]).filter((v) => v > 1e-6).length} non-zero amplitudes</>,
        interp: 'Quantum: 4 qubits → 2⁴ = 16 amplitudes.',
        body: <><ValueBars max={1} items={(m.statevector_abs as number[]).map((v, i) => ({ label: `|${i.toString(2).padStart(4, '0')}⟩`, value: v }))} />{SIM}</> },
      { title: 'State overlap', stage: 'k', hl: 'none', explain: 'Two images are similar when their states overlap. Bars: the most similar training images.',
        why: 'The overlap is the quantum similarity measure used in place of the RBF kernel.', formula: <>K(x, y) = |⟨φ(x)|φ(y)⟩|²</>,
        out: <>largest overlap with a training image: {fx(Math.max(...(m.kernel_top_train as any[]).map((t) => t.K)), 4)}</>,
        interp: 'Quantum: on hardware K is estimated by running U(x) then U(y)† and counting all-zero outcomes.',
        body: <ValueBars max={1} items={(m.kernel_top_train as any[]).map((t, i) => ({ label: `training image #${i + 1}`, value: t.K }))} digits={4} /> },
      { title: 'Kernel matrix', stage: 'k', hl: 'none',
        explain: 'All pairwise overlaps of the demo image and one training image per class. Click any entry to read it.',
        why: 'The SVM only ever sees this matrix of similarities.', formula: <>Kᵢⱼ = |⟨φ(xᵢ)|φ(xⱼ)⟩|²</>,
        out: <>mean off-diagonal value on the training kernel: {fx(m.train_kernel_offdiag_mean, 3)}</>, interp: 'Quantum similarity, classical matrix.',
        body: <KernelExplorer m={m.kernel_heatmap} labels={m.heatmap_labels} /> },
      { title: 'Classical SVM training', stage: 'svm', hl: 'none',
        explain: 'A completely classical SVM finds the decision boundary from the kernel matrix (C chosen on validation).',
        why: 'The quantum part only computes similarities; optimisation is classical and convex.',
        formula: <>f(x) = Σⱼ αⱼ yⱼ K(x, xⱼ) + b</>, out: <>C = {m.params.C}</>, interp: 'QKC = quantum feature map + classical optimiser.',
        body: <Note>On real images, the class with the largest one-vs-one vote is the prediction.</Note> },
      { title: 'Output', stage: 'svm', hl: 'none', explain: 'For a NEU-DET image the SVM outputs one of six classes. For this artificial grid no class is shown.',
        why: 'An answer for a non-steel image would be meaningless.', out: <>see Quantum vs Classical for real test accuracy</>,
        interp: 'Simulated quantum kernel; no quantum hardware and no claimed advantage.', body: <>{NO_PRED}{SIM}</> },
    ];
  },
};

// ─── VQC ───
export const vqc: Algo = {
  id: 'vqc', family: 'quantum', name: 'Variational classifier (VQC)', blurb: 'A trainable quantum circuit',
  trace: (c) => {
    const v = c.d.vqc;
    return [
      { key: 'in', label: 'feature change', value: `Δa = [${ad4(c).map((x) => x.toFixed(3)).join(', ')}]`, short: `Δ${l2(ad4(c)).toFixed(2)}` },
      { key: 'enc', label: 'encoding', value: `RY(a₁) … RY(a₄)`, short: 'RY' },
      { key: 'par', label: 'trainable gates', value: `${v.theta_trained.length} angles`, short: 'θ' },
      { key: 'ent', label: 'entanglement', value: 'CNOT ring', short: 'CX' },
      { key: 'meas', label: 'measurement', value: `${v.readout.length} expectation values`, short: '⟨Z⟩' },
      { key: 'train', label: 'training', value: 'parameter-shift + Adam', short: '∇' },
    ];
  },
  steps: (c): Step[] => {
    const v = c.d.vqc;
    const n = v.n_qubits;
    const ro: string[] = v.readout.map(obs);
    const ps = v.parameter_shift, ad = v.illustrative_adam_step;
    const enc = (v.circuit_trained as Gate[]).filter((g) => g.name === 'ry').slice(0, n);
    let k = 0;
    const updated = (v.circuit_trained as Gate[]).map((g, i) => (i >= n && (g.name === 'ry' || g.name === 'rz')) ? { ...g, params: [Number(ad.theta_after[k++].toFixed(4))] } : g);
    const dth = (ad.theta_after as number[]).map((t, i) => t - v.theta_trained[i]);
    return [
      { title: 'Input features', stage: 'in', hl: 'selected', explain: 'The same 4 PCA angles as the quantum kernel.',
        why: 'One angle per qubit.', out: <><Vec v={v.features} digits={3} /></>, interp: 'Classical preprocessing.',
        body: <ValueBars signed items={ad4(c).map((x, i) => ({ label: `Δ angle ${i + 1} (pixel ${c.px.v})`, value: x }))} digits={3} /> },
      { title: 'Data encoding', stage: 'enc', hl: 'none', explain: 'Each feature rotates one qubit: RY(aᵢ).', why: 'Loads the data into the circuit.',
        formula: <>|ψ₀⟩ = ⊗ᵢ RY(aᵢ)|0⟩</>, out: <>{enc.map((g) => `RY(${g.params[0]})`).join(' ')}</>, interp: 'Quantum: angle encoding.', body: <MiniCircuit n={n} gates={enc} /> },
      { title: 'Parameterised gates', stage: 'par', hl: 'none', explain: `${v.layers} layers of RY(θ) and RZ(θ) on every qubit: ${v.theta_trained.length} trainable angles (trained values).`,
        why: 'These angles are what training adjusts.', out: <>θ₀ = {fx(v.theta_trained[0], 4)} … ({v.theta_trained.length} values)</>,
        interp: 'Quantum: the "weights" of the model are rotation angles.',
        body: <ValueBars signed items={(v.theta_trained as number[]).map((t, i) => ({ label: `θ${i} ${i % 2 ? 'RZ' : 'RY'} q${Math.floor(i / 2) % n}`, value: t }))} /> },
      { title: 'Entanglement', stage: 'ent', hl: 'none', explain: 'CNOT gates in a ring (q0→q1→q2→q3→q0) after each layer. The full trained circuit:',
        why: 'Entanglement lets the measured values depend on combinations of features.', out: <>{(v.circuit_trained as Gate[]).filter((g) => g.name === 'cx').length} CNOTs</>,
        interp: 'Quantum: entangled qubits cannot be described one at a time.', body: <MiniCircuit n={n} gates={v.circuit_trained as Gate[]} /> },
      { title: 'Measurement', stage: 'meas', hl: 'none', explain: `Six expectation values, one per class: ${ro.join(', ')} (each between −1 and +1), trained vs untrained circuit.`,
        why: 'Measurements turn the state into numbers a classifier can use.', formula: <>⟨O⟩ = ⟨ψ|O|ψ⟩</>,
        out: <>trained: <Vec v={v.trained.expectations} digits={3} /></>, interp: 'Quantum: exact expectations here; on hardware they are averages over shots.',
        body: <div className="grid gap-4 lg:grid-cols-2"><div><div className="mb-1 text-xs text-slate-400">untrained (initial θ)</div><ValueBars signed max={1} items={(v.untrained.expectations as number[]).map((e, i) => ({ label: `⟨${ro[i]}⟩`, value: e }))} /></div>
          <div><div className="mb-1 text-xs text-slate-400">trained</div><ValueBars signed max={1} items={(v.trained.expectations as number[]).map((e, i) => ({ label: `⟨${ro[i]}⟩`, value: e }))} /></div></div> },
      { title: 'Loss calculation', stage: 'train', hl: 'none',
        explain: `Each expectation gets a learned scale and bias, softmax turns them into probabilities, and cross-entropy measures the error for the true class. Illustration: if the true class were class ${ad.target_class + 1}, the loss would be ${fx(ad.loss_before, 3)}.`,
        why: 'Training needs one number to minimise.', formula: <>logit_c = w_c·⟨O_c⟩ + b_c;  loss = −log softmax(logit)_true</>,
        out: <>illustrative loss = {fx(ad.loss_before, 4)}</>, interp: 'Classical post-processing of quantum measurements.',
        body: <Note tone="amber">Illustrative: a pretend label for the demo grid, used only to show the arithmetic of one training step.</Note> },
      { title: 'Parameter-shift gradient', stage: 'train', hl: 'none',
        explain: 'Gradients are measured by running the circuit twice with one angle shifted by ±π/2 — exact for these gates.',
        why: 'Back-propagation is impossible on quantum hardware; parameter-shift needs only extra circuit runs.',
        formula: <>∂⟨O⟩/∂θ = [⟨O⟩(θ + π/2) − ⟨O⟩(θ − π/2)] / 2</>, out: <>∂⟨{ro[0]}⟩/∂θ{ps.param_index} = {fx(ps.dE_dtheta[0], 4)}</>,
        interp: 'Quantum: a hardware-compatible gradient rule.',
        body: <table className="text-xs tabular-nums"><thead className="text-left text-slate-500"><tr><th className="pr-4">observable</th><th className="pr-4">θ{ps.param_index}+π/2</th><th className="pr-4">θ{ps.param_index}−π/2</th><th>derivative</th></tr></thead>
          <tbody>{ro.map((r, i) => <tr key={r}><td className="pr-4">⟨{r}⟩</td><td className="pr-4 font-mono">{fx(ps.E_plus[i], 4)}</td><td className="pr-4 font-mono">{fx(ps.E_minus[i], 4)}</td><td className="font-mono text-cyan-200">{fx(ps.dE_dtheta[i], 4)}</td></tr>)}</tbody></table> },
      { title: 'Adam parameter update', stage: 'train', hl: 'none',
        explain: `One Adam step on this single example with the illustrative label (real code, not part of the recorded run). Real training used mini-batches of 64 images.`,
        why: 'Adam adapts the step size per parameter for stable training.', formula: <>θ ← θ − lr · m̂ / (√v̂ + ε),  lr = {ad.lr}</>,
        out: <>loss {fx(ad.loss_before, 3)} → {fx(ad.loss_after, 3)}</>, interp: 'Classical optimiser driving quantum parameters.',
        body: <ValueBars signed items={dth.map((x, i) => ({ label: `Δθ${i}`, value: x }))} digits={3} /> },
      { title: 'Updated circuit', stage: 'train', hl: 'none', explain: 'The same circuit with the updated angles (hover a gate to read its angle).',
        why: 'Training only changes rotation angles; the circuit structure stays fixed.', out: <>θ₀: {fx(v.theta_trained[0], 4)} → {fx(ad.theta_after[0], 4)}</>,
        interp: 'Quantum: a VQC is a fixed circuit with tunable angles.', body: <MiniCircuit n={n} gates={updated} /> },
      { title: 'Output: trained vs untrained behaviour', stage: 'train', hl: 'none',
        explain: 'The recorded training run of this model (per-epoch loss). Per-step angles were not recorded; the curve below is real.',
        why: 'Shows that training moved the circuit from random to useful behaviour on NEU-DET.', out: <>best validation loss {fx(v.best?.val_loss, 3)} at epoch {v.best?.step}</>,
        interp: 'Simulated VQC; compare with its frozen-circuit ablation on the comparison page.',
        body: <><div className="h-48"><ResponsiveContainer><LineChart data={v.training_history}><CartesianGrid strokeDasharray="3 3" stroke="#1e293b" /><XAxis dataKey="epoch" tick={{ fontSize: 10, fill: '#94a3b8' }} /><YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} /><Tooltip contentStyle={{ background: '#0b1220', border: '1px solid #334155', fontSize: 12 }} />
          <Line dataKey="train_loss" name="train loss" stroke="#3987e5" strokeWidth={2} dot={false} /><Line dataKey="val_loss" name="validation loss" stroke="#d95926" strokeWidth={2} strokeDasharray="6 4" dot={false} /></LineChart></ResponsiveContainer></div>
          <div className="text-[11px] text-slate-500">Blue: train loss · Orange dashed: validation loss ({v.experiment_id})</div>{NO_PRED}</> },
    ];
  },
};

export const QUANTUM: Algo[] = [frqi, neqr, qkc, vqc];
