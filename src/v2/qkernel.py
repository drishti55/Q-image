"""
Quantum kernel classifier (QKC) for Protocol V2 — fidelity kernel K(x,y) = |<φ(x)|φ(y)>|².

Input: PCA "angle" features a ∈ [0, π]^k (train-fitted MinMax). Bandwidth b scales them: x = b·a.
Feature maps (every gate simulated by src.v2.qsim, Qiskit conventions; verified vs Qiskit):
  * product_ry   : RY(x_i) on each qubit. Kernel = Π_i cos²((x_i−y_i)/2). Classically computable in
                   closed form — included as a CONTROL, not as evidence of quantum benefit.
  * zz_linear    : Qiskit ZZFeatureMap convention, repeated `reps` times:
                   H on all qubits; P(2x_i); for (i, i+1): CX(i,j) P(2(π−x_i)(π−x_j)) on j CX(i,j)
  * zz_full      : same, all pairs i<j.
Classification: sklearn SVC(kernel="precomputed").

Shot-based estimation: the compute–uncompute circuit U(y)†U(x)|0> is measured once in the
computational basis; K̂ = (# all-zero outcomes)/shots. For an ideal (noiseless) simulator this count is
exactly Binomial(shots, K). `sample_shot_kernel` draws that distribution; `aer_kernel_entry` runs the
actual circuit on qiskit-aer for validation (tests + Phase 4 validation report).
"""
from __future__ import annotations

import time
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.svm import SVC

from .qsim import Sim, circuit_resources

FEATURE_MAPS = ("product_ry", "zz_linear", "zz_full")


def _pairs(n: int, fmap: str) -> List[Tuple[int, int]]:
    if fmap == "zz_linear":
        return [(i, i + 1) for i in range(n - 1)]
    if fmap == "zz_full":
        return [(i, j) for i in range(n) for j in range(i + 1, n)]
    return []


def encode(X: np.ndarray, fmap: str, reps: int, record: bool = False) -> Sim:
    """Simulate the feature-map circuit for every row of X (already bandwidth-scaled)."""
    X = np.asarray(X, dtype=float)
    B, n = X.shape
    sim = Sim(B, n, record=record)
    if fmap == "product_ry":
        for i in range(n):
            sim.ry(i, X[:, i])
        return sim
    if fmap not in ("zz_linear", "zz_full"):
        raise ValueError(fmap)
    for _ in range(reps):
        for i in range(n):
            sim.h(i)
        for i in range(n):
            sim.p(i, 2.0 * X[:, i])
        for i, j in _pairs(n, fmap):
            sim.cx(i, j)
            sim.p(j, 2.0 * (np.pi - X[:, i]) * (np.pi - X[:, j]))
            sim.cx(i, j)
    return sim


_STATE_CACHE: Dict[Tuple, np.ndarray] = {}


def states(X: np.ndarray, fmap: str, reps: int, chunk: int = 512) -> np.ndarray:
    """Encoded statevectors for every row of X. Memoised on the exact input bytes (pure function)."""
    import hashlib
    X = np.ascontiguousarray(X, dtype=float)
    key = (hashlib.sha1(X.tobytes()).hexdigest(), X.shape, fmap, reps)
    if key not in _STATE_CACHE:
        if len(_STATE_CACHE) > 64:
            _STATE_CACHE.clear()
        _STATE_CACHE[key] = np.concatenate(
            [encode(X[i:i + chunk], fmap, reps).state for i in range(0, len(X), chunk)])
    return _STATE_CACHE[key]


def fidelity_kernel(SA: np.ndarray, SB: Optional[np.ndarray] = None) -> np.ndarray:
    SB = SA if SB is None else SB
    return np.abs(SA.conj() @ SB.T) ** 2


def sample_shot_kernel(K: np.ndarray, shots: int, rng: np.random.Generator, symmetric: bool) -> np.ndarray:
    """Finite-shot estimate: each entry ~ Binomial(shots, K_ij)/shots (independent circuits)."""
    P = np.clip(K, 0.0, 1.0)
    if symmetric:
        iu = np.triu_indices(len(P), 1)
        E = np.eye(len(P))
        vals = rng.binomial(shots, P[iu]) / shots
        E[iu] = vals
        E[(iu[1], iu[0])] = vals
        # diagonal: identical inputs -> P(0...0)=1 exactly, binomial(shots, 1) = shots
        np.fill_diagonal(E, rng.binomial(shots, np.clip(np.diag(P), 0, 1)) / shots)
        return E
    return rng.binomial(shots, P) / shots


def kernel_circuit(x: np.ndarray, y: np.ndarray, fmap: str, reps: int):
    """Qiskit compute–uncompute circuit U(y)† U(x) with ONE final measurement of all qubits."""
    from qiskit import QuantumCircuit
    ux = encode(np.atleast_2d(x), fmap, reps, record=True).qc
    uy = encode(np.atleast_2d(y), fmap, reps, record=True).qc
    n = ux.num_qubits
    qc = QuantumCircuit(n, n)
    qc.compose(ux, inplace=True)
    qc.compose(uy.inverse(), inplace=True)
    qc.measure(range(n), range(n))
    return qc


def aer_kernel_entry(x, y, fmap: str, reps: int, shots: int, seed: int = 0) -> float:
    from qiskit import transpile
    from qiskit_aer import AerSimulator
    qc = kernel_circuit(x, y, fmap, reps)
    sim = AerSimulator(seed_simulator=seed)
    counts = sim.run(transpile(qc, sim), shots=shots).result().get_counts()
    return counts.get("0" * qc.num_qubits, 0) / shots


def kernel_diagnostics(K: np.ndarray, y: np.ndarray) -> Dict:
    n = len(K)
    off = K[~np.eye(n, dtype=bool)]
    eig = np.linalg.eigvalsh((K + K.T) / 2)
    Y = (y[:, None] == y[None, :]).astype(float) * 2 - 1
    H = np.eye(n) - 1.0 / n
    Kc, Yc = H @ K @ H, H @ Y @ H
    cka = float(np.sum(Kc * Yc) / (np.linalg.norm(Kc) * np.linalg.norm(Yc) + 1e-300))
    kta = float(np.sum(K * Y) / (np.linalg.norm(K) * np.linalg.norm(Y)))
    same = (y[:, None] == y[None, :]) & ~np.eye(n, dtype=bool)
    return {
        "n": n,
        "symmetry_max_abs_error": float(np.max(np.abs(K - K.T))),
        "diag_min": float(np.min(np.diag(K))), "diag_max": float(np.max(np.diag(K))),
        "min": float(K.min()), "max": float(K.max()),
        "in_unit_interval": bool(K.min() >= -1e-12 and K.max() <= 1 + 1e-12),
        "min_eigenvalue": float(eig[0]), "max_eigenvalue": float(eig[-1]),
        "psd_within_tol": bool(eig[0] > -1e-8 * max(1.0, eig[-1])),
        "offdiag_mean": float(off.mean()), "offdiag_std": float(off.std()), "offdiag_var": float(off.var()),
        "offdiag_quantiles": {q: float(np.quantile(off, q)) for q in (0.01, 0.25, 0.5, 0.75, 0.99)},
        "offdiag_hist": np.histogram(off, bins=20, range=(0, 1))[0].tolist(),
        "mean_same_class": float(K[same].mean()), "mean_diff_class": float(K[~same & ~np.eye(n, dtype=bool)].mean()),
        "kernel_target_alignment": kta,
        "centered_kernel_alignment": cka,
    }


@lru_cache(maxsize=8)
def _circuit_stats(fmap: str, reps: int, n: int) -> Dict:
    x = np.linspace(0.3, 2.8, n)  # structure only; gate counts do not depend on values
    qc = encode(x[None, :], fmap, reps, record=True).qc
    r = circuit_resources(qc)
    r.update({"circuit": "feature map U(x) (one encoding; kernel circuit = U(x) then U(y)† + measurement)",
              "feature_map": fmap, "reps": reps,
              "kernel_circuit_note": "compute-uncompute doubles gates/depth; measured once"})
    return r


class QuantumKernelSVC:
    """Runner estimator. params: feature_map, reps, bandwidth, C, shots (0 = exact statevector)."""

    def __init__(self, params: Dict, seed: int):
        self.params = {"shots": 0, **params}
        self.seed = seed
        self.rng = np.random.default_rng(10_000 + seed)
        self.svm = SVC(kernel="precomputed", C=self.params["C"], random_state=seed)
        self.Xtr = None
        self._diag = {}

    def _scale(self, A):
        return np.asarray(A, dtype=float) * self.params["bandwidth"]

    def _states(self, A):
        p = self.params
        return states(self._scale(A), p["feature_map"], p["reps"])

    def fit(self, X, y, Xv=None, yv=None):
        t0 = time.perf_counter()
        self.Xtr = np.asarray(X, dtype=float)
        S = self._states(self.Xtr)
        K = fidelity_kernel(S)
        t_k = time.perf_counter() - t0
        if self.params["shots"]:
            K = sample_shot_kernel(K, self.params["shots"], self.rng, symmetric=True)
        self._diag = {"train_kernel": kernel_diagnostics(K, np.asarray(y)), "train_kernel_time_s": t_k,
                      "simulation": "exact statevector" if not self.params["shots"] else
                      f"statevector fidelities + Binomial({self.params['shots']}) shot sampling per entry"}
        self.svm.fit(K, y)
        self._diag["n_support_vectors"] = int(self.svm.n_support_.sum())
        return {}

    def _cross(self, X):
        K = fidelity_kernel(self._states(X), self._states(self.Xtr))
        if self.params["shots"]:
            K = sample_shot_kernel(K, self.params["shots"], self.rng, symmetric=False)
        return K

    def predict(self, X):
        return self.svm.predict(self._cross(X))

    def diagnostics(self):
        return self._diag

    def circuit_stats(self):
        p = self.params
        r = dict(_circuit_stats(p["feature_map"], p["reps"], self.Xtr.shape[1]))
        r["shots"] = p["shots"]
        r["execution_mode"] = "statevector (exact)" if not p["shots"] else f"{p['shots']} shots (sampled)"
        return r
