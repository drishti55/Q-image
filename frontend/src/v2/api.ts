// Protocol V2 data access. Every request goes to /api/v2 (results/qml_v2 only). No fallbacks: callers get
// {data, error, loading} and must render explicit loading / error / empty states.
import { useEffect, useState } from 'react';

export const V2 = '/api/v2';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function getJSON<T = unknown>(path: string, signal?: AbortSignal): Promise<T> {
  const r = await fetch(`${V2}${path}`, { signal });
  if (!r.ok) {
    let detail = r.statusText;
    try {
      const j = await r.json();
      detail = j?.detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(r.status, `${r.status} ${detail}`);
  }
  return r.json() as Promise<T>;
}

export type Loadable<T> = { data: T | null; error: string | null; loading: boolean };

export function useV2<T = any>(path: string | null): Loadable<T> {
  const [state, setState] = useState<Loadable<T>>({ data: null, error: null, loading: !!path });
  useEffect(() => {
    if (!path) {
      setState({ data: null, error: null, loading: false });
      return;
    }
    const ctl = new AbortController();
    setState((s) => ({ ...s, loading: true, error: null }));
    getJSON<T>(path, ctl.signal)
      .then((d) => setState({ data: d, error: null, loading: false }))
      .catch((e) => {
        if (e?.name === 'AbortError') return;
        setState({ data: null, error: String(e?.message ?? e), loading: false });
      });
    return () => ctl.abort();
  }, [path]);
  return state;
}

/** Protocol V3 endpoints (/api/v3, results/qml_v3 only) — same {data, error, loading} contract. */
export function useV3<T = any>(path: string | null): Loadable<T> {
  const [state, setState] = useState<Loadable<T>>({ data: null, error: null, loading: !!path });
  useEffect(() => {
    if (!path) return;
    const ctl = new AbortController();
    setState((s) => ({ ...s, loading: true, error: null }));
    fetch(`/api/v3${path}`, { signal: ctl.signal })
      .then(async (r) => {
        if (!r.ok) {
          let detail = r.statusText;
          try { detail = (await r.json())?.detail ?? detail; } catch { /* non-JSON error body */ }
          throw new ApiError(r.status, `${r.status} ${detail}`);
        }
        return r.json() as Promise<T>;
      })
      .then((d) => setState({ data: d, error: null, loading: false }))
      .catch((e) => {
        if (e?.name === 'AbortError') return;
        setState({ data: null, error: String(e?.message ?? e), loading: false });
      });
    return () => ctl.abort();
  }, [path]);
  return state;
}

// ── types mirroring src/v2/api_models.py ──
export type MS = { mean: number | null; std: number | null; n: number };
export type SeedRow = {
  seed: number; experiment_id: string;
  val: Record<string, number> | null; test: Record<string, number> | null;
  test_ci?: { accuracy: [number, number]; f1_macro: [number, number] } | null;
  train_time_s?: number | null; test_inference_ms_per_image?: number | null;
};
export type Circuit = {
  n_qubits: number; gates_logical: number; depth_logical: number; gates_compiled: number;
  depth_compiled: number; cx_compiled: number; two_qubit_gates_compiled: number; single_qubit_gates_compiled?: number;
  note?: string;
} | null;
export type Model = {
  group: string; display_name: string; model_name: string; experiment_code: string; category: string; family: string;
  is_quantum: boolean; is_legacy_relabelled: boolean; is_ablation: boolean; feature_source: string;
  feature_extraction: string; encoding: string; n_qubits: number | null; n_layers: number | null;
  optimizer: string | null; shots: number; execution: string; params: Record<string, unknown>;
  experiment_ids: string[]; n_seeds: number; n_test: number; n_candidates: number | null;
  val_f1_macro: MS; test_accuracy: MS; test_precision_macro: MS; test_recall_macro: MS; test_f1_macro: MS;
  test_f1_weighted: MS; train_time_s: MS; test_inference_ms_per_image: MS; circuit: Circuit; per_seed: SeedRow[];
};
export type ModelsResponse = { count: number; categories: string[]; models: Model[] };

/** Protocol V4 endpoints (/api/v4) — same {data, error, loading} contract. */
export function useV4<T = any>(path: string | null): Loadable<T> {
  const [state, setState] = useState<Loadable<T>>({ data: null, error: null, loading: !!path });
  useEffect(() => {
    if (!path) { setState({ data: null, error: null, loading: false }); return; }
    const ctl = new AbortController();
    setState((s) => ({ ...s, loading: true, error: null }));
    fetch(`/api/v4${path}`, { signal: ctl.signal })
      .then(async (r) => {
        if (!r.ok) {
          let d = r.statusText;
          try { d = (await r.json())?.detail ?? d; } catch { /* non-JSON */ }
          throw new ApiError(r.status, `${r.status} ${d}`);
        }
        return r.json();
      })
      .then((d) => setState({ data: d as T, error: null, loading: false }))
      .catch((e) => { if (e?.name !== 'AbortError') setState({ data: null, error: String(e?.message ?? e), loading: false }); });
    return () => ctl.abort();
  }, [path]);
  return state;
}
