// Small schematic diagrams for Explain popovers (labelled schematic — no data).
import type { ReactElement } from 'react';

const C = { wire: '#475569', teal: '#5eead4', blue: '#3987e5', orange: '#d95926', amber: '#fbbf24', text: '#94a3b8', box: '#0f172a' };
const W = 300, H = 96;
const Wire = ({ y, label }: { y: number; label: string }) => (
  <g><text x={4} y={y + 4} fontSize={9} fill={C.text}>{label}</text><line x1={30} x2={W - 8} y1={y} y2={y} stroke={C.wire} /></g>
);
const Box = ({ x, y, t, c = C.teal, w = 24 }: { x: number; y: number; t: string; c?: string; w?: number }) => (
  <g><rect x={x - w / 2} y={y - 9} width={w} height={18} rx={3} fill={C.box} stroke={c} /><text x={x} y={y + 3.5} textAnchor="middle" fontSize={8.5} fontWeight={700} fill={c}>{t}</text></g>
);
const Dot = ({ x, y, c = C.orange, open = false }: { x: number; y: number; c?: string; open?: boolean }) => <circle cx={x} cy={y} r={3.5} fill={open ? C.box : c} stroke={c} strokeWidth={1.4} />;
const Plus = ({ x, y, c = C.amber }: { x: number; y: number; c?: string }) => (
  <g><circle cx={x} cy={y} r={6} fill={C.box} stroke={c} /><line x1={x - 6} x2={x + 6} y1={y} y2={y} stroke={c} /><line x1={x} x2={x} y1={y - 6} y2={y + 6} stroke={c} /></g>
);
const V = ({ x, y1, y2, c = C.orange }: { x: number; y1: number; y2: number; c?: string }) => <line x1={x} x2={x} y1={y1} y2={y2} stroke={c} strokeWidth={1.3} />;
const Svg = ({ children, label }: { children: React.ReactNode; label: string }) => (
  <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={label}>{children}</svg>
);
const Flow = ({ items, label }: { items: string[]; label: string }) => {
  const bw = (W - 10) / items.length;
  return (
    <Svg label={label}>
      {items.map((t, i) => (
        <g key={t}>
          <rect x={4 + i * bw} y={30} width={bw - 12} height={36} rx={6} fill={C.box} stroke={i === items.length - 1 ? C.teal : C.wire} />
          <text x={4 + i * bw + (bw - 12) / 2} y={52} textAnchor="middle" fontSize={8.5} fill="#e2e8f0">{t}</text>
          {i < items.length - 1 && <path d={`M ${4 + (i + 1) * bw - 11} 48 l 8 0 m -3 -3 l 3 3 l -3 3`} stroke={C.text} fill="none" />}
        </g>))}
    </Svg>
  );
};

const D: Record<string, () => ReactElement> = {
  frqi: () => (
    <Svg label="FRQI circuit schematic">
      <Wire y={20} label="pos" /><Wire y={44} label="pos" /><Wire y={72} label="colour" />
      <Box x={48} y={20} t="H" /><Box x={48} y={44} t="H" />
      {[96, 150, 204, 258].map((x, i) => (
        <g key={x}><V x={x} y1={20} y2={72} /><Dot x={x} y={20} open={!(i & 1)} /><Dot x={x} y={44} open={!(i & 2)} /><Box x={x} y={72} t={`RY θ${i}`} c={C.orange} w={38} /></g>))}
    </Svg>),
  neqr: () => (
    <Svg label="NEQR circuit schematic">
      <Wire y={14} label="pos" /><Wire y={32} label="pos" /><Wire y={54} label="bit1" /><Wire y={76} label="bit0" />
      <Box x={48} y={14} t="H" /><Box x={48} y={32} t="H" />
      {[[96, [54]], [150, [76]], [204, [54, 76]], [258, [54]]].map(([x, ts], i) => (
        <g key={i}><V x={x as number} y1={14} y2={Math.max(...(ts as number[]))} c={C.amber} /><Dot x={x as number} y={14} c={C.amber} open={!(i & 1)} /><Dot x={x as number} y={32} c={C.amber} open={!(i & 2)} />
          {(ts as number[]).map((y) => <Plus key={y} x={x as number} y={y} />)}</g>))}
    </Svg>),
  'product-ry': () => (
    <Svg label="Product-RY schematic">
      {[16, 40, 64, 88].map((y, i) => <g key={y}><Wire y={y - 4} label={`q${i}`} /><Box x={120} y={y - 4} t={`RY x${i}`} w={40} /></g>)}
      <text x={190} y={50} fontSize={9} fill={C.text}>no links between qubits</text>
    </Svg>),
  'zz-linear': () => (
    <Svg label="ZZ-linear schematic">
      {[14, 36, 58, 80].map((y, i) => <g key={y}><Wire y={y} label={`q${i}`} /><Box x={46} y={y} t="H" /><Box x={78} y={y} t="P" /></g>)}
      {[[14, 36], [36, 58], [58, 80]].map(([a, b], k) => <g key={k}><V x={130 + k * 50} y1={a} y2={b} c={C.teal} /><Dot x={130 + k * 50} y={a} c={C.teal} /><Plus x={130 + k * 50} y={b} c={C.teal} /></g>)}
      <text x={276} y={50} fontSize={8.5} fill={C.text} textAnchor="end">neighbours</text>
    </Svg>),
  'zz-full': () => (
    <Svg label="ZZ-full schematic">
      {[14, 36, 58, 80].map((y, i) => <g key={y}><Wire y={y} label={`q${i}`} /><Box x={46} y={y} t="H" /><Box x={74} y={y} t="P" /></g>)}
      {[[14, 36], [14, 58], [14, 80], [36, 58], [36, 80], [58, 80]].map(([a, b], k) => <g key={k}><V x={104 + k * 32} y1={a} y2={b} c={C.teal} /><Dot x={104 + k * 32} y={a} c={C.teal} /><Plus x={104 + k * 32} y={b} c={C.teal} /></g>)}
    </Svg>),
  vqc: () => (
    <Svg label="VQC schematic">
      {[14, 36, 58, 80].map((y, i) => <g key={y}><Wire y={y} label={`q${i}`} /><Box x={50} y={y} t="RY x" w={30} c={C.blue} /><Box x={100} y={y} t="RY θ" w={30} /><Box x={136} y={y} t="RZ θ" w={30} /><Box x={250} y={y} t="⟨Z⟩" w={26} c={C.amber} /></g>)}
      {[[14, 36], [36, 58], [58, 80]].map(([a, b], k) => <g key={k}><V x={170 + k * 20} y1={a} y2={b} c={C.teal} /><Dot x={170 + k * 20} y={a} c={C.teal} /><Plus x={170 + k * 20} y={b} c={C.teal} /></g>)}
      <rect x={84} y={2} width={140} height={90} rx={6} fill="none" stroke={C.teal} strokeDasharray="3 3" /><text x={154} y={-1} fontSize={8} fill={C.teal} textAnchor="middle" dy={10}>trained layer × L</text>
    </Svg>),
  kernel: () => <Flow label="kernel schematic" items={['image A → |φ(A)⟩', 'image B → |φ(B)⟩', 'overlap', 'K ∈ [0, 1]']} />,
  qkc: () => <Flow label="QKC schematic" items={['features', 'circuit |φ(x)⟩', 'K table', 'SVM']} />,
  pqk: () => <Flow label="PQK schematic" items={['circuit |φ(x)⟩', 'Bloch vector per qubit', 'RBF on vectors', 'SVM']} />,
  cnn: () => <Flow label="CNN schematic" items={['224×224 photo', '16 maps 112²', '48 maps 14²', '576 maps 7²', '576 numbers']} />,
  mobilenet: () => <Flow label="MobileNetV3 schematic" items={['grey → RGB', 'frozen MobileNetV3', 'average each map', '576 numbers']} />,
  pca: () => <Flow label="PCA schematic" items={['576 numbers', 'scale', 'PCA top k', 'k angles → k qubits']} />,
  density: () => <Flow label="mixed state schematic" items={['image', 'patches', '|ψₖ⟩ per patch', 'ρ = average', 'Tr(ρσ)']} />,
  'recon-metrics': () => <Flow label="reconstruction schematic" items={['image', 'encode', 'measure (shots)', 'decode', 'compare: MSE · PSNR · SSIM']} />,
  'kernel-matrix': () => (
    <Svg label="kernel matrix schematic">
      {Array.from({ length: 36 }, (_, k) => { const i = Math.floor(k / 6), j = k % 6, same = Math.floor(i / 2) === Math.floor(j / 2);
        return <rect key={k} x={20 + j * 13} y={8 + i * 13} width={12} height={12} fill={C.blue} fillOpacity={i === j ? 1 : same ? 0.7 : 0.15} />; })}
      <text x={110} y={30} fontSize={9} fill="#e2e8f0">bright blocks = same class look alike</text>
      <text x={110} y={48} fontSize={9} fill={C.text}>diagonal = image vs itself (1)</text>
      <text x={110} y={66} fontSize={9} fill={C.text}>all dark = kernel concentration</text>
    </Svg>),
};

export function TopicDiagram({ id }: { id: string }) {
  const F = D[id];
  return F ? <div className="rounded-lg bg-slate-950/70 p-2 ring-1 ring-slate-800"><F /><div className="text-right text-[9px] text-slate-600">schematic</div></div> : null;
}
