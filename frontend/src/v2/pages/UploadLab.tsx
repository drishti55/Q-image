// Upload lab: encode any uploaded image with FRQI and NEQR (real Qiskit circuits, simulated), reconstruct it from the exact
// statevector and from 100 / 1,000 / 10,000 shots, and classify it with the frozen V4 FRQI and NEQR models.
// Backend: POST /api/v4/upload (src/v4/upload.py). Nothing is saved; the locked test set is not used.
import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { AlertTriangle, ImageUp, Loader2, ShieldCheck } from 'lucide-react';
import { Card, PageHeader, CLASS_LABEL } from '../ui';
import { ExplainThis } from '../learn/ExplainThis';

type Mode = { mode: string; label: string; image: number[][]; mse: number; psnr: number | null; ssim: number; exact: boolean };
type Enc = { representation: 'FRQI' | 'NEQR'; resolution: number; bits: number | null; input: number[][]; quantised: number[][] | null;
  circuit: { n_qubits: number; gates_logical: number; depth_logical: number; gates_compiled?: number; depth_compiled?: number; cx_compiled?: number };
  modes: Mode[] };
type Cls = { representation: 'FRQI' | 'NEQR'; group: string; params: Record<string, unknown>; locked_test_accuracy: { mean: number; std: number };
  input: number[][]; prediction: string; decision: { class: string; score: number }[]; class_similarity: { class: string; mean: number }[];
  nearest: { class: string; similarity: number; thumb: number[][] }[];
  ood: { max_similarity: number; percentile_vs_training: number; unusual: boolean; note: string } };
type Resp = { filename: string; original: number[][]; original_size: number; encodings: Enc[]; classifications: Cls[]; execution: string; caveat: string };

const COLOR = { FRQI: '#3a8ee6', NEQR: '#d96a30' } as const;
const label = (c: string) => CLASS_LABEL[c] ?? c.replace(/_/g, ' ');
const sci = (v: number) => (v === 0 ? '0' : v < 1e-3 ? v.toExponential(1) : v.toFixed(4));

function Gray({ data, size, caption, sub }: { data: number[][]; size: number; caption?: ReactNode; sub?: ReactNode }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const c = ref.current;
    if (!c || !data?.length) return;
    const h = data.length, w = data[0].length;
    c.width = w; c.height = h;
    const ctx = c.getContext('2d')!;
    const img = ctx.createImageData(w, h);
    data.forEach((row, y) => row.forEach((v, x) => {
      const g = Math.round(Math.max(0, Math.min(1, v)) * 255), k = (y * w + x) * 4;
      img.data[k] = img.data[k + 1] = img.data[k + 2] = g; img.data[k + 3] = 255;
    }));
    ctx.putImageData(img, 0, 0);
  }, [data]);
  return (
    <figure className="flex flex-col items-center gap-1">
      <canvas ref={ref} style={{ width: size, height: size, imageRendering: 'pixelated' }} className="rounded-md ring-1 ring-slate-700" />
      {caption && <figcaption className="text-center text-[11px] leading-tight text-slate-300">{caption}</figcaption>}
      {sub && <div className="text-center text-[10px] tabular-nums leading-tight text-slate-500">{sub}</div>}
    </figure>
  );
}

function EncodingPanel({ e }: { e: Enc }) {
  const c = e.circuit;
  return (
    <Card actions={<span className="flex flex-wrap gap-1"><ExplainThis id={e.representation === 'FRQI' ? 'frqi' : 'neqr'} /><ExplainThis id="recon-metrics" /></span>} title={<span className="inline-flex items-center gap-2"><span className="h-3 w-3 rounded-sm" style={{ background: COLOR[e.representation] }} />{e.representation} encoding and reconstruction</span>}
      subtitle={`${e.resolution}×${e.resolution} pixels${e.bits ? `, ${e.bits}-bit intensities` : ''} · ${c.n_qubits} qubits · ${c.gates_logical.toLocaleString()} logical gates (depth ${c.depth_logical.toLocaleString()})` +
        (c.gates_compiled != null ? ` · ${c.gates_compiled.toLocaleString()} compiled gates, ${c.cx_compiled?.toLocaleString()} CX` : ' · compiled counts skipped at 16×16 (slow to transpile)')}>
      <div className="flex flex-wrap items-start gap-4" data-testid={`upload-${e.representation}`}>
        <Gray data={e.input} size={112} caption="before: input" sub={`${e.resolution}×${e.resolution}`} />
        {e.quantised && <Gray data={e.quantised} size={112} caption={`quantised to ${e.bits} bits`} sub="what NEQR stores" />}
        {e.modes.map((m) => (
          <Gray key={m.mode} data={m.image} size={112} caption={`after: ${m.label}`}
            sub={<>MSE {sci(m.mse)}<br />SSIM {m.ssim.toFixed(3)}{m.exact ? ' · exact' : ''}</>} />
        ))}
      </div>
      <p className="mt-3 text-xs text-slate-400">
        {e.representation === 'FRQI'
          ? 'FRQI stores each pixel as a rotation angle of one colour qubit. The exact statevector gives the image back perfectly; with shots each pixel is estimated from how often the colour qubit reads 1 (θ = arcsin√P), so few shots look noisy.'
          : 'NEQR stores each pixel as a binary code in several qubits. The exact state gives back the quantised image (error = quantisation only); with few shots some pixels are never observed and appear black.'}
      </p>
    </Card>
  );
}

function ClassifyPanel({ k }: { k: Cls }) {
  const max = Math.max(...k.decision.map((d) => d.score));
  const min = Math.min(...k.decision.map((d) => d.score));
  return (
    <Card title={`Frozen V4 ${k.representation} model says: ${label(k.prediction)}`}
      subtitle={`${k.group} · ${String(k.params.image_size)}×${String(k.params.image_size)}, ${String(k.params.patch)}×${String(k.params.patch)} patches · locked-test accuracy ${(100 * k.locked_test_accuracy.mean).toFixed(1)} ± ${(100 * k.locked_test_accuracy.std).toFixed(1)} %`}>
      <div className="grid gap-4 md:grid-cols-[auto_minmax(0,1fr)]" data-testid={`classify-${k.representation}`}>
        <Gray data={k.input} size={112} caption="model input" sub={k.params.norm === 'stretch' ? 'contrast-stretched' : 'no stretch'} />
        <div className="space-y-1.5">
          <div className="text-[11px] text-slate-500">SVM decision score per class (higher = more votes for that class)</div>
          {k.decision.map((d) => (
            <div key={d.class} className="grid grid-cols-[110px_minmax(0,1fr)_48px] items-center gap-2 text-xs">
              <span className={d.class === k.prediction ? 'font-semibold text-white' : 'text-slate-400'}>{label(d.class)}</span>
              <div className="h-2.5 rounded-full bg-slate-800">
                <div className="h-2.5 rounded-full" style={{ width: `${max > min ? (100 * (d.score - min)) / (max - min) : 100}%`, background: d.class === k.prediction ? COLOR[k.representation] : '#64748b' }} />
              </div>
              <span className="tabular-nums text-slate-400">{d.score.toFixed(2)}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="mt-4 text-[11px] text-slate-500">Most similar training images by the kernel Tr(ρ_upload ρ_train) (normalised)</div>
      <div className="mt-1 flex flex-wrap gap-3">
        {k.nearest.map((n, i) => <Gray key={i} data={n.thumb} size={64} caption={label(n.class)} sub={n.similarity.toFixed(3)} />)}
      </div>
      <div className={`mt-3 flex items-start gap-2 rounded-lg px-3 py-2 text-xs ${k.ood.unusual ? 'bg-amber-500/10 text-amber-200' : 'bg-slate-800/60 text-slate-300'}`}>
        {k.ood.unusual ? <AlertTriangle size={14} className="mt-0.5 shrink-0" /> : <ShieldCheck size={14} className="mt-0.5 shrink-0" />}
        <span>
          {k.ood.unusual ? 'This image looks unlike the NEU-DET training images, so the prediction is not meaningful. ' : ''}
          Its closest training match is more similar than {k.ood.percentile_vs_training.toFixed(0)} % of training images' own closest matches. {k.ood.note}
        </span>
      </div>
    </Card>
  );
}

export default function UploadLab() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [res, setRes] = useState(8);
  const [bits, setBits] = useState(4);
  const [reps, setReps] = useState<('FRQI' | 'NEQR')[]>(['FRQI', 'NEQR']);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [out, setOut] = useState<Resp | null>(null);
  const [drag, setDrag] = useState(false);

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);
  const pick = (f: File | undefined | null) => {
    if (!f) return;
    setFile(f); setOut(null); setErr(null);
    setPreview(URL.createObjectURL(f));
  };
  const run = async () => {
    if (!file) return;
    setBusy(true); setErr(null); setOut(null);
    const fd = new FormData();
    fd.append('file', file); fd.append('resolution', String(res)); fd.append('bits', String(bits)); fd.append('representations', reps.join(','));
    try {
      const r = await fetch('/api/v4/upload', { method: 'POST', body: fd });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(j?.detail ? String(j.detail) : `${r.status} ${r.statusText}`);
      setOut(j as Resp);
    } catch (e) {
      setErr(String((e as Error)?.message ?? e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-5">
      <PageHeader title="Upload your own image — FRQI & NEQR"
        subtitle="Encode any image with FRQI, NEQR or both on the real Qiskit circuits, see it reconstructed from the exact quantum state and from 100 / 1,000 / 10,000 measurement shots, and let the frozen V4 models classify it. Exact noiseless CPU simulation; nothing is saved." />

      <Card title="1. Choose an image and settings">
        <div className="grid gap-5 md:grid-cols-[minmax(0,1fr)_260px]">
          <label
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files?.[0]); }}
            className={`flex min-h-[180px] cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-4 py-6 text-center transition ${drag ? 'border-cyan-400 bg-cyan-500/5' : 'border-slate-700 hover:border-slate-500'}`}
            data-testid="upload-drop">
            <input type="file" accept="image/*" className="hidden" onChange={(e) => pick(e.target.files?.[0])} data-testid="upload-input" />
            {preview ? <img src={preview} alt="selected upload" className="max-h-40 rounded-md ring-1 ring-slate-700" /> : <ImageUp size={32} className="text-slate-500" />}
            <div className="text-sm text-slate-200">{file ? file.name : 'Drop an image here or click to choose'}</div>
            <div className="text-xs text-slate-500">PNG / JPG up to 10 MB · centre-cropped to a square and converted to grey · tip: try a NEU-DET image</div>
          </label>
          <div className="space-y-4">
            <div>
              <div className="mb-1 text-xs text-slate-400">Quantum representation</div>
              <div className="grid grid-cols-3 gap-1" role="radiogroup" aria-label="Quantum representation" data-testid="upload-reps">
                {([['FRQI', ['FRQI']], ['NEQR', ['NEQR']], ['Both', ['FRQI', 'NEQR']]] as const).map(([lab, r]) => {
                  const on = reps.join() === r.join();
                  return (
                    <button key={lab} type="button" role="radio" aria-checked={on} onClick={() => { setReps([...r]); setOut(null); }}
                      className={`rounded-lg px-2 py-1.5 text-xs ${on ? 'bg-cyan-500 font-semibold text-slate-950' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'}`}>{lab}</button>);
                })}
              </div>
            </div>
            <div>
              <div className="mb-1 text-xs text-slate-400">Encoding resolution (whole image)</div>
              <div className="grid grid-cols-4 gap-1">
                {[2, 4, 8, 16].map((r) => (
                  <button key={r} onClick={() => setRes(r)} aria-pressed={res === r}
                    className={`rounded-lg px-2 py-1.5 text-xs ${res === r ? 'bg-cyan-500 font-semibold text-slate-950' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'}`}>{r}×{r}</button>
                ))}
              </div>
              <div className="mt-1 text-[11px] text-slate-500">{[reps.includes('FRQI') && `FRQI ${2 * Math.log2(res) + 1} qubits`, reps.includes('NEQR') && `NEQR ${2 * Math.log2(res) + bits} qubits`].filter(Boolean).join(' · ')}</div>
            </div>
            {reps.includes('NEQR') && <div>
              <div className="mb-1 text-xs text-slate-400">NEQR intensity bits</div>
              <div className="grid grid-cols-3 gap-1">
                {[2, 4, 8].map((b) => (
                  <button key={b} onClick={() => setBits(b)} aria-pressed={bits === b}
                    className={`rounded-lg px-2 py-1.5 text-xs ${bits === b ? 'bg-cyan-500 font-semibold text-slate-950' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'}`}>{b}-bit</button>
                ))}
              </div>
            </div>}
            <button onClick={run} disabled={!file || busy} data-testid="upload-run"
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-cyan-500 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-40">
              {busy ? <><Loader2 size={16} className="animate-spin" /> Encoding & classifying…</> : `Encode with ${reps.join(' + ')}, reconstruct & classify`}
            </button>
          </div>
        </div>
        {err && <div className="mt-3 rounded-lg bg-rose-500/10 px-3 py-2 text-sm text-rose-200" role="alert">{err}</div>}
      </Card>

      {out && (
        <div className="space-y-5" data-testid="upload-results">
          <div className="flex flex-wrap items-center gap-4 rounded-xl bg-slate-900/50 p-4 ring-1 ring-slate-800">
            <Gray data={out.original} size={128} caption="your image (grey, square)" sub={`${out.original_size}×${out.original_size} px original`} />
            <div className="max-w-2xl space-y-1 text-sm text-slate-300">
              <div className="font-semibold text-white">2. Encoding and reconstruction</div>
              <p>Each image below is rebuilt from a simulated quantum state. MSE is the mean squared error against the input (0 = perfect); SSIM is structural similarity (1 = identical).</p>
              <p className="text-xs text-amber-200/90">{out.execution}</p>
            </div>
          </div>
          {out.encodings.map((e) => <EncodingPanel key={e.representation} e={e} />)}
          <div className="rounded-xl bg-slate-900/50 p-4 text-sm text-slate-300 ring-1 ring-slate-800">
            <div className="font-semibold text-white">3. Classification by the frozen V4 models</div>
            <p className="mt-1">The patch-ensemble models cut the image into small patches, encode each patch, mix them into a density matrix ρ and compare it with all 1,080 training images. {out.caveat}</p>
          </div>
          <div className={`grid gap-5 ${out.classifications.length > 1 ? 'xl:grid-cols-2' : ''}`}>{out.classifications.map((k) => <ClassifyPanel key={k.representation} k={k} />)}</div>
        </div>
      )}
    </div>
  );
}
