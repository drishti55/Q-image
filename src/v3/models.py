"""
Protocol V3 quantum models (all simulated exactly on a CPU; no quantum hardware).

ProjectedQuantumKernelSVC (PQK; Huang et al., "Power of data in quantum machine learning", 2021)
    The same feature-map circuits as the V2 fidelity QKC (product-RY / ZZ-linear / ZZ-full). Instead of the global
    overlap |<φ(x)|φ(y)>|² — which concentrates towards 0 as qubits / bandwidth grow — each data point's state is
    projected onto its single-qubit reduced density matrices ρ_q(x), described by the Bloch vector
    (<X_q>, <Y_q>, <Z_q>). On hardware these are 3n single-qubit Pauli expectation values per image (no pairwise
    circuits). Kernel: K(x, y) = exp(−γ Σ_q ||ρ_q(x) − ρ_q(y)||_F²) = exp(−(γ/2) Σ_q ||b_q(x) − b_q(y)||²),
    then a classical SVC. The exponential is classical post-processing of measured quantum features.

VQCv3 — still the genuine V2 circuit family (RY encoding, trainable RY/RZ layers, CNOT ring, optional data
    re-uploading, exact parameter-shift gradients). Additions:
      readout "diag6" (V2): logit_c = w_c <O_c> + b_c on 6 single-qubit observables;
      readout "zall": all n single-qubit <Z_i> -> linear head (6×n + 6 classical parameters). Because a linear head can
          do classical work, every selected VQC is paired with (a) the frozen-random-circuit ablation and (b) an
          encoding-only control (L = 0: no trainable gates; <Z_i> = cos(a_i) for RY encoding).
      longer training (epochs up to 120, patience 15, best-validation checkpoint) and calibrated SPSA
          (Spall 1998: gain a chosen so the first step has a target magnitude of 0.1 rad).

EncodingKernelSVCv3 — FRQI / NEQR state kernels with
      kernel "fidelity" (V2): |<I_A|I_B>|²  ;  kernel "overlap": <I_A|I_B> (real for FRQI and NEQR states;
          measurable with a Hadamard test). Both are PSD; the overlap is not squared, which reduces concentration.
      norm "none" (V2) or "stretch": per-image min-max contrast stretch to [0, 1] before encoding
          (a fixed per-sample function; no information crosses images).
"""
from __future__ import annotations

import time
from typing import Dict, Optional

import numpy as np
from sklearn.svm import SVC

from src.v2 import qkernel as qk
from src.v2.frqi_neqr import EncodingKernelSVC, frqi_angles, neqr_quantize
from src.v2.qkernel import kernel_diagnostics
from src.v2.qsim import Sim, z_expectations
from src.v2.vqc import N_CLASSES, VQC, VQCCircuit, _softmax


# ─────────────────────────── shared helpers ───────────────────────────
_GRAM: Dict[tuple, np.ndarray] = {}
MAX_CACHE_BYTES = 400 * 2 ** 20


def _nbytes(d):
    return sum(v.nbytes for v in d.values())


def limit_state_cache():
    """Bound memory per worker: statevector and Gram caches are cleared above MAX_CACHE_BYTES."""
    if _nbytes(qk._STATE_CACHE) > MAX_CACHE_BYTES:
        qk._STATE_CACHE.clear()
    if _nbytes(_GRAM) > MAX_CACHE_BYTES:
        _GRAM.clear()


def _key(*arrays, extra=()):
    import hashlib
    h = hashlib.sha1()
    for a in arrays:
        a = np.ascontiguousarray(a, dtype=float)
        h.update(a.tobytes())
        h.update(str(a.shape).encode())
    return (h.hexdigest(),) + tuple(extra)


def spectrum_summary(K: np.ndarray) -> Dict:
    """Eigenvalue distribution of a (train) kernel: top fractions and effective dimension."""
    ev = np.clip(np.linalg.eigvalsh((K + K.T) / 2)[::-1], 0, None)
    tot = ev.sum() or 1.0
    p = ev / tot
    return {"top1_fraction": float(p[0]), "top10_fraction": float(p[:10].sum()),
            "effective_dimension": float(1.0 / np.sum(p ** 2)),
            "n_eig_for_90pct": int(np.searchsorted(np.cumsum(p), 0.9) + 1)}


def bloch_vectors(state: np.ndarray, n: int) -> np.ndarray:
    """(B, 2^n) statevectors (Qiskit little-endian: qubit q = bit q of the index) -> (B, 3n) Bloch vectors
    [<X_q>, <Y_q>, <Z_q>] of every single-qubit reduced density matrix."""
    B = state.shape[0]
    psi = state.reshape((B,) + (2,) * n)  # axis 1 = most significant bit = qubit n-1
    out = np.empty((B, 3 * n))
    for q in range(n):
        ax = n - q  # axis of qubit q in psi
        a0 = np.take(psi, 0, axis=ax).reshape(B, -1)
        a1 = np.take(psi, 1, axis=ax).reshape(B, -1)
        rho01 = np.sum(a0 * a1.conj(), axis=1)
        out[:, 3 * q] = 2 * rho01.real
        out[:, 3 * q + 1] = -2 * rho01.imag
        out[:, 3 * q + 2] = np.sum(np.abs(a0) ** 2, axis=1) - np.sum(np.abs(a1) ** 2, axis=1)
    return out


# ─────────────────────────── fidelity QKC (V2 class + spectrum diagnostics) ───────────────────────────
class QuantumKernelSVCv3(qk.QuantumKernelSVC):
    """V2 fidelity QKC; exact kernels are memoised per (data, feature map, reps, bandwidth) so a sweep over C
    reuses them (pure function of the inputs). Adds the train-kernel eigenvalue summary."""

    def _gram(self, A, B=None):
        p = self.params
        k = _key(A, *(() if B is None else (B,)), extra=("fid", p["feature_map"], p["reps"], p["bandwidth"]))
        if k not in _GRAM:
            _GRAM[k] = qk.fidelity_kernel(self._states(A), None if B is None else self._states(B))
        return _GRAM[k]

    def fit(self, X, y, Xv=None, yv=None):
        limit_state_cache()
        t0 = time.perf_counter()
        self.Xtr = np.asarray(X, dtype=float)
        K = self._gram(self.Xtr)
        t_k = time.perf_counter() - t0
        if self.params["shots"]:
            K = qk.sample_shot_kernel(K, self.params["shots"], self.rng, symmetric=True)
        self._diag = {"train_kernel": kernel_diagnostics(K, np.asarray(y)), "train_kernel_time_s": t_k,
                      "train_kernel_spectrum": spectrum_summary(K),
                      "simulation": "exact statevector" if not self.params["shots"] else
                      f"statevector fidelities + Binomial({self.params['shots']}) shot sampling per entry"}
        self.svm.fit(K, y)
        self._diag["n_support_vectors"] = int(self.svm.n_support_.sum())
        return {}

    def _cross(self, X):
        K = self._gram(np.asarray(X, dtype=float), self.Xtr)
        if self.params["shots"]:
            K = qk.sample_shot_kernel(K, self.params["shots"], self.rng, symmetric=False)
        return K


# ─────────────────────────── projected quantum kernel ───────────────────────────
class ProjectedQuantumKernelSVC:
    """params: feature_map, reps, bandwidth, gamma, C."""

    def __init__(self, params: Dict, seed: int):
        self.params = dict(params)
        self.seed = seed
        self.svm = SVC(kernel="precomputed", C=self.params["C"], random_state=seed)
        self.Btr = None
        self._diag: Dict = {}

    def _bloch(self, A):
        p = self.params
        A = np.asarray(A, float)
        k = _key(A, extra=("bloch", p["feature_map"], p["reps"], p["bandwidth"]))
        if k not in _GRAM:
            _GRAM[k] = bloch_vectors(qk.states(A * p["bandwidth"], p["feature_map"], p["reps"]), A.shape[1])
        return _GRAM[k]

    def _K(self, BA, BB):
        d2 = (np.sum(BA ** 2, 1)[:, None] + np.sum(BB ** 2, 1)[None, :] - 2 * BA @ BB.T)
        return np.exp(-0.5 * self.params["gamma"] * np.clip(d2, 0, None))

    def fit(self, X, y, Xv=None, yv=None):
        limit_state_cache()
        t0 = time.perf_counter()
        self.n = np.asarray(X).shape[1]
        self.Btr = self._bloch(X)
        K = self._K(self.Btr, self.Btr)
        self._diag = {"train_kernel": kernel_diagnostics(K, np.asarray(y)), "train_kernel_spectrum": spectrum_summary(K),
                      "train_kernel_time_s": time.perf_counter() - t0,
                      "bloch_vector_norm_mean": float(np.mean(np.linalg.norm(self.Btr.reshape(len(self.Btr), -1, 3), axis=2))),
                      "simulation": "exact statevector -> single-qubit reduced density matrices"}
        self.svm.fit(K, y)
        self._diag["n_support_vectors"] = int(self.svm.n_support_.sum())
        return {}

    def predict(self, X):
        return self.svm.predict(self._K(self._bloch(X), self.Btr))

    def diagnostics(self):
        return self._diag

    def circuit_stats(self):
        p = self.params
        r = dict(qk._circuit_stats(p["feature_map"], p["reps"], self.n))
        r.update({"shots": 0, "execution_mode": "statevector (exact Pauli expectation values)",
                  "measurement": f"{3 * self.n} single-qubit Pauli expectations per image (X, Y, Z on each qubit)",
                  "kernel_circuit_note": "no pairwise compute-uncompute circuit is needed for the projected kernel"})
        return r


# ─────────────────────────── VQC v3 ───────────────────────────
class VQCCircuitV3(VQCCircuit):
    """V2 circuit with a configurable readout list (generic number of observables)."""

    def __init__(self, n, layers, entangler="ring", reupload=False, readout="diag6"):
        super().__init__(n, layers, entangler, reupload)
        self.readout_kind = readout
        if readout == "zall":
            self.readout = [("Z", (i,)) for i in range(n)]
        self.n_obs = len(self.readout)

    def _readout(self, st):
        return z_expectations(st, self.n, [q[0] for _, q in self.readout]) if all(k == "Z" for k, _ in self.readout) \
            else super()._readout(st)

    def param_shift_jacobian(self, A, theta):
        A = np.asarray(A, dtype=float)
        sim = Sim(len(A), self.n)
        before = {}
        for k, op in enumerate(self.tape):
            if op[2] and op[2][0] == "param":
                before[k] = sim.state.copy()
            self._apply(sim, op, A, theta)
        J = np.empty((len(A), self.n_params, self.n_obs))
        for p in range(self.n_params):
            k = self.param_pos[p]
            vals = []
            for shift in (np.pi / 2, -np.pi / 2):
                s2 = Sim(len(A), self.n)
                s2.state = before[k].copy()
                self._apply(s2, self.tape[k], A, theta, override=theta[p] + shift)
                for op in self.tape[k + 1:]:
                    self._apply(s2, op, A, theta)
                vals.append(self._readout(s2.state))
            J[:, p, :] = 0.5 * (vals[0] - vals[1])
        return J


class VQCv3(VQC):
    DEFAULTS = {**VQC.DEFAULTS, "readout": "diag6", "epochs": 120, "patience": 15, "spsa_iters": 3000,
                "spsa_target_step": 0.1, "head_scale": 0.5}

    def __init__(self, params: Dict, seed: int):
        super().__init__({**VQCv3.DEFAULTS, **params}, seed)

    @property
    def _zall(self):
        return self.params["readout"] == "zall"

    def _logits(self, A, theta, w, b):
        E = self.circ.expectations(A, theta)
        return E @ w.T + b if self._zall else E * w + b

    def loss_and_grad(self, A, y, theta, w, b):
        if not self._zall:
            return super().loss_and_grad(A, y, theta, w, b)
        E = self.circ.expectations(A, theta)
        P = _softmax(E @ w.T + b)
        Y = np.eye(N_CLASSES)[y]
        loss = float(-np.mean(np.log(np.clip(P[np.arange(len(y)), y], 1e-12, 1))))
        G = (P - Y) / len(y)
        gw, gb = (G.T @ E).ravel(), G.sum(0)
        if self.params.get("train_quantum", True) and self.circ.n_params:
            J = self.circ.param_shift_jacobian(A, theta)
            gtheta = np.einsum("bn,bpn->p", G @ w, J)
        else:
            gtheta = np.zeros_like(theta)
        return loss, gtheta, gw, gb

    def _pack(self):
        return np.concatenate([self.theta, self.w.ravel(), self.b])

    def _unpack(self, v):
        P = self.circ.n_params
        nw = self.w.size
        return v[:P], v[P:P + nw].reshape(self.w.shape), v[P + nw:]

    def fit(self, X, y, Xv, yv):
        """Same procedure as V2 VQC.fit, with the v3 circuit (configurable readout) and head shape."""
        p = self.params
        X, Xv = np.asarray(X, float), np.asarray(Xv, float)
        y, yv = np.asarray(y, int), np.asarray(yv, int)
        self.circ = VQCCircuitV3(X.shape[1], p["layers"], p["entangler"], p["reupload"], p["readout"])
        self.theta = self.rng.uniform(-p["init_scale"], p["init_scale"], self.circ.n_params)
        if self._zall:
            self.w = np.random.default_rng(1000 + self.seed).normal(0.0, p["head_scale"], (N_CLASSES, self.circ.n_obs))
        else:
            self.w = np.full(N_CLASSES, p["head_init"])
        self.b = np.zeros(N_CLASSES)
        theta0 = self.theta.copy()
        sub = self.rng.choice(len(X), size=min(128, len(X)), replace=False)
        _, g0, _, _ = self.loss_and_grad(X[sub], y[sub], self.theta, self.w, self.b)
        L = max(p["layers"], 1)
        self.diag["init_grad"] = {"l2_norm": float(np.linalg.norm(g0)), "mean_abs": float(np.mean(np.abs(g0))) if g0.size else 0.0,
                                  "var": float(np.var(g0)) if g0.size else 0.0,
                                  "per_layer_var": [float(np.var(v)) for v in g0.reshape(L, -1)] if g0.size else []}
        if not p["train_quantum"] and p["optimizer"] != "adam":
            raise ValueError("frozen-circuit ablation is defined for the Adam optimiser only")
        t0 = time.perf_counter()
        opt = p["optimizer"]
        {"adam": self._fit_adam, "cobyla": self._fit_cobyla, "spsa": self._fit_spsa}[opt](X, y, Xv, yv)
        self.diag["train_time_s"] = time.perf_counter() - t0
        self.diag["theta_change_l2"] = float(np.linalg.norm(self.theta - theta0))
        self.diag["n_quantum_params"] = int(self.circ.n_params)
        self.diag["n_classical_params"] = int(self.w.size + self.b.size)
        self.diag["readout"] = p["readout"]
        return {"training_log": {"history": self.history, "optimizer": opt, "settings": dict(p),
                                 "best": self.diag.get("best"),
                                 "gradient_method": {"adam": "parameter-shift (exact, shift pi/2)",
                                                     "cobyla": "none (COBYLA, gradient-free)",
                                                     "spsa": "calibrated SPSA estimate"}[opt],
                                 "readout": [f"{k}{q}" for k, q in self.circ.readout],
                                 "loss": "mean cross-entropy"}}

    def _fit_spsa(self, X, y, Xv, yv):
        """Calibrated SPSA: gain a set so that the expected first update has magnitude spsa_target_step."""
        p = self.params
        A_ = 0.1 * p["spsa_iters"]
        c = p["spsa_c"]
        v = self._pack()
        mags = []
        for _ in range(10):
            idx = self.rng.choice(len(X), size=min(4 * p["batch_size"], len(X)), replace=False)
            d = self.rng.choice([-1.0, 1.0], size=v.shape)
            g = (self._loss(X[idx], y[idx], *self._unpack(v + c * d)) -
                 self._loss(X[idx], y[idx], *self._unpack(v - c * d))) / (2 * c)
            mags.append(abs(g))
        a = p["spsa_target_step"] * (A_ + 1) ** 0.602 / max(np.mean(mags), 1e-8)
        self.diag["spsa_calibrated_a"] = float(a)
        self._keep_best(self._record(0, "iteration", X, y, Xv, yv), 0)
        for k in range(1, p["spsa_iters"] + 1):
            ak, ck = a / (k + A_) ** 0.602, c / k ** 0.101
            idx = self.rng.choice(len(X), size=min(4 * p["batch_size"], len(X)), replace=False)
            d = self.rng.choice([-1.0, 1.0], size=v.shape)
            lp = self._loss(X[idx], y[idx], *self._unpack(v + ck * d))
            lm = self._loss(X[idx], y[idx], *self._unpack(v - ck * d))
            v = v - ak * (lp - lm) / (2 * ck) * d
            if k % 50 == 0:
                self.theta, self.w, self.b = self._unpack(v)
                self._keep_best(self._record(k, "iteration", X, y, Xv, yv), k)
        self.theta, self.w, self.b = self._unpack(v)
        self._restore_best()
        self.diag["converged"] = None
        self.diag["n_loss_evaluations"] = 2 * p["spsa_iters"]

    def circuit_stats(self):
        r = super().circuit_stats()
        r["readout_kind"] = self.params["readout"]
        r["n_classical_head_params"] = int(self.w.size + self.b.size)
        return r


# ─────────────────────────── FRQI / NEQR v3 ───────────────────────────
def stretch(X: np.ndarray) -> np.ndarray:
    F = np.asarray(X, float).reshape(len(X), -1)
    lo, hi = F.min(1, keepdims=True), F.max(1, keepdims=True)
    return ((F - lo) / np.where(hi - lo < 1e-9, 1.0, hi - lo)).reshape(np.shape(X))


def frqi_overlap(XA, XB=None, b: float = 1.0) -> np.ndarray:
    A = frqi_angles(XA, b)
    B = A if XB is None else frqi_angles(XB, b)
    return (np.cos(A) @ np.cos(B).T + np.sin(A) @ np.sin(B).T) / A.shape[1]


def neqr_overlap(XA, XB=None, bits: int = 4) -> np.ndarray:
    qa = neqr_quantize(XA, bits)
    qb = qa if XB is None else neqr_quantize(XB, bits)
    M = np.zeros((len(qa), len(qb)))
    for level in range(1 << bits):
        a, c = (qa == level).astype(np.float32), (qb == level).astype(np.float32)
        if a.any() and c.any():
            M += a @ c.T
    return M / qa.shape[1]


class EncodingKernelSVCv3(EncodingKernelSVC):
    """params: representation, C, bits, angle_scale, kernel (fidelity|overlap), norm (none|stretch)."""

    def __init__(self, params: Dict, seed: int):
        super().__init__({"kernel": "fidelity", "norm": "none", **params}, seed)

    def _prep(self, A):
        return stretch(A) if self.params["norm"] == "stretch" else np.asarray(A, float)

    def _K(self, A, B=None):
        p = self.params
        A = self._prep(A)
        B = None if B is None else self._prep(B)
        if p["representation"] == "FRQI":
            ov = frqi_overlap(A, B, p["angle_scale"])
        else:
            ov = neqr_overlap(A, B, p["bits"])
        return np.clip(ov ** 2, 0, 1) if p["kernel"] == "fidelity" else ov

    def predict(self, X):
        # Xtr is stored raw; _K applies the same per-image normalisation to both sides
        return self.svm.predict(self._K(np.asarray(X, float), self.Xtr))

    def fit(self, X, y, Xv=None, yv=None):
        out = super().fit(X, y, Xv, yv)
        self._diag["train_kernel_spectrum"] = spectrum_summary(self._K(self.Xtr))
        self._diag["kernel_variant"] = {"kernel": self.params["kernel"], "norm": self.params["norm"]}
        return out

    def circuit_stats(self):
        r = super().circuit_stats()
        r["kernel_variant"] = self.params["kernel"]
        r["measurement"] = ("swap / compute-uncompute test (fidelity)" if self.params["kernel"] == "fidelity"
                            else "Hadamard test (real part of the overlap)")
        return r
