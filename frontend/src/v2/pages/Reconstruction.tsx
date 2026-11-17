import { useState } from 'react';
import { useV2, V2 } from '../api';
import { Badge, CLASS_LABEL, Card, Gate, Loading, PageHeader, Select, num } from '../ui';
import type { ReconRecord } from './Encoding';

type M = { mse: number; psnr: number | null; exact_match: boolean; ssim: number; ssim_method: string };
type ImgRow = { index: number; image: string; class: string; modes: Record<string, { vs_preprocessed: M; vs_quantized?: M; pixels_never_observed?: number; decode_time_s: number }>;
  quantization_only?: M | null };
type ImagesResp = { record_id: string; config: { representation: string; resolution: number; intensity_bits: number | null }; modes: string[]; images: ImgRow[] };

const MODE_LABEL: Record<string, string> = { statevector: 'Exact statevector', shots100: '100 shots', shots1000: '1,000 shots', shots10000: '10,000 shots', shots100000: '100,000 shots' };
const mse = (v?: number) => v === undefined ? 'unavailable' : v === 0 || v < 1e-12 ? '0 (exact)' : v.toExponential(2);
const psnr = (m?: M) => !m ? 'unavailable' : m.exact_match || m.psnr === null ? '∞ (exact match)' : `${m.psnr.toFixed(2)} dB`;

export const recordLabel = (r: { config: { representation: string; resolution: number; intensity_bits: number | null } | null; record_id: string }) =>
  r.config ? `${r.config.representation} ${r.config.resolution}×${r.config.resolution}${r.config.representation === 'NEQR' ? ` · ${r.config.intensity_bits}-bit` : ''}` : r.record_id;

function Panel({ rid, index, mode }: { rid: string; index: number; mode: string }) {
  const st = useV2<ImagesResp>(`/reconstructions/${rid}/images`);
  if (st.loading) return <Loading />;
  return (
    <Gate state={st} empty={(d) => !d.images.length}>
      {(d) => {
        const im = d.images[Math.min(index, d.images.length - 1)];
        const m = im.modes[mode];
        const neqr = d.config.representation === 'NEQR';
        return (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-base font-semibold text-slate-100">{recordLabel({ config: d.config, record_id: rid })}</h3>
              <Badge tone={mode === 'statevector' ? 'cyan' : 'amber'}>{MODE_LABEL[mode]}</Badge>
              <Badge>{CLASS_LABEL[im.class] ?? im.class}</Badge>
              <span className="text-[11px] text-slate-500 font-mono">{im.image}</span>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {(['original', 'reconstructed', 'diff'] as const).map((k) => (
                <figure key={k} className="space-y-1">
                  <img alt={`${k} ${rid} ${im.index} ${mode}`} src={`${V2}/reconstructions/${rid}/render/${im.index}/${mode}/${k}.png`}
                    className="w-full rounded-lg border border-slate-800 bg-black" style={{ imageRendering: 'pixelated' }} />
                  <figcaption className="text-center text-[11px] text-slate-400">{k === 'original' ? `Preprocessed original (${d.config.resolution}×${d.config.resolution})` : k === 'diff' ? '|original − reconstructed|' : 'Reconstructed'}</figcaption>
                </figure>
              ))}
            </div>
            {m ? (
              <table className="w-full text-xs tabular-nums">
                <thead className="text-left text-slate-500"><tr><th className="py-1">vs</th><th>MSE</th><th>PSNR</th><th>SSIM</th><th>SSIM method</th></tr></thead>
                <tbody className="divide-y divide-slate-800/60">
                  <tr><td className="py-1.5 text-slate-300">preprocessed image</td><td>{mse(m.vs_preprocessed.mse)}</td><td>{psnr(m.vs_preprocessed)}</td><td>{num(m.vs_preprocessed.ssim)}</td><td className="text-slate-500">{m.vs_preprocessed.ssim_method}</td></tr>
                  {neqr && m.vs_quantized && <tr><td className="py-1.5 text-slate-300">own {d.config.intensity_bits}-bit quantised image</td><td>{mse(m.vs_quantized.mse)}</td><td>{psnr(m.vs_quantized)}</td><td>{num(m.vs_quantized.ssim)}</td><td className="text-slate-500">{m.vs_quantized.ssim_method}</td></tr>}
                  {neqr && im.quantization_only && <tr><td className="py-1.5 text-slate-300">quantisation alone</td><td>{mse(im.quantization_only.mse)}</td><td>{psnr(im.quantization_only)}</td><td>{num(im.quantization_only.ssim)}</td><td /></tr>}
                </tbody>
              </table>
            ) : <div className="text-sm text-slate-400">No saved result for this mode.</div>}
            {m?.pixels_never_observed !== undefined && m.pixels_never_observed > 0 && (
              <p className="text-xs text-amber-300/90">{m.pixels_never_observed} pixel position(s) were never sampled at this shot count and decode as 0.</p>
            )}
            <details className="text-xs text-slate-400">
              <summary className="cursor-pointer">All modes for this image</summary>
              <table className="mt-2 w-full tabular-nums">
                <thead className="text-left text-slate-500"><tr><th>Mode</th><th>MSE</th><th>PSNR</th><th>SSIM</th></tr></thead>
                <tbody>{d.modes.map((mo) => im.modes[mo] && <tr key={mo}><td className="py-1">{MODE_LABEL[mo]}</td><td>{mse(im.modes[mo].vs_preprocessed.mse)}</td><td>{psnr(im.modes[mo].vs_preprocessed)}</td><td>{num(im.modes[mo].vs_preprocessed.ssim)}</td></tr>)}</tbody>
              </table>
            </details>
          </div>
        );
      }}
    </Gate>
  );
}

export default function ReconstructionPage() {
  const recs = useV2<{ count: number; records: ReconRecord[] }>('/reconstructions');
  const [a, setA] = useState<string>('');
  const [b, setB] = useState<string>('none');
  const [index, setIndex] = useState(0);
  const [mode, setMode] = useState('shots1000');
  const done0 = (recs.data?.records ?? []).filter((r) => r.status === 'completed');
  const cur = a || (done0.find((r) => r.record_id === 'R-FRQI-8x8') ?? done0[0])?.record_id || '';
  const imgs = useV2<ImagesResp>(cur ? `/reconstructions/${cur}/images` : null);
  return (
    <div className="space-y-5">
      <PageHeader title="Reconstruction Studio"
        subtitle="FRQI / NEQR encode → simulate → decode on 30 fixed training-folder images (5 per class; the locked test set is never used). Images are rendered from the saved reconstruction arrays." />
      <Card>
        <div className="grid gap-3 text-sm text-slate-400 md:grid-cols-2">
          <p><b className="text-slate-200">Exact statevector reconstruction</b> reads the amplitudes of the simulated state directly. It is exact for both encodings — a consistency check of encoder and decoder, not a measure of practical quality.</p>
          <p><b className="text-slate-200">Finite-shot reconstruction</b> decodes from sampled measurement outcomes (Multinomial over |ψ|², equivalent to an ideal measure-all). FRQI estimates each pixel from P(colour=1 | position) and needs many shots; NEQR is exact at every position sampled at least once.</p>
        </div>
      </Card>
      <Gate state={recs} empty={(d) => !d.records.filter((r) => r.status === 'completed').length}>
        {(d) => {
          const done = d.records.filter((r) => r.status === 'completed');
          const opts = done.map((r) => [r.record_id, recordLabel(r)] as [string, string]);
          return (
            <>
              <Card>
                <div className="flex flex-wrap items-end gap-3">
                  <Select label="Reconstruction record" value={cur} onChange={(v) => setA(v)} options={opts} all={false} />
                  <Select label="Compare with" value={b} onChange={setB} options={[['none', '— none —'], ...opts.filter(([id]) => id !== cur)]} all={false} />
                  <Select label="Image" value={String(index)} onChange={(v) => setIndex(Number(v))} all={false}
                    options={(imgs.data?.images ?? []).map((im) => [String(im.index), `#${im.index + 1} · ${CLASS_LABEL[im.class] ?? im.class} · ${im.image.split('/').pop()}`] as [string, string])} />
                  <Select label="Measurement" value={mode} onChange={setMode} all={false} options={Object.entries(MODE_LABEL)} />
                </div>
                {done.length < d.count && <p className="mt-2 text-xs text-amber-300">{d.count - done.length} record(s) not completed are hidden.</p>}
              </Card>
              <div className={`grid gap-5 ${b !== 'none' ? 'xl:grid-cols-2' : ''}`}>
                <Card><Panel key={`${cur}-${index}-${mode}`} rid={cur} index={index} mode={mode} /></Card>
                {b !== 'none' && <Card><Panel key={`${b}-${index}-${mode}`} rid={b} index={index} mode={mode} /></Card>}
              </div>
            </>
          );
        }}
      </Gate>
    </div>
  );
}
