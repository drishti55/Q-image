"""
Genuine Variational Quantum Classifier (E4) — simulated with the batched statevector simulator.

Circuit on n = k qubits (k = number of input features):
  encoding    : RY(a_i) on qubit i, a ∈ [0, π] (train-fitted MinMax PCA/CNN features)
  layer l=1..L: [re-upload encoding if data_reuploading] ; RY(θ_{l,i,0}) RZ(θ_{l,i,1}) on every qubit ;
                CNOT entangler: ring (i -> i+1 mod n) or linear (i -> i+1)
  readout     : exact expectation values of 6 observables (one per class)
                n >= 6 : Z_0 .. Z_5           n = 4 : Z_0, Z_1, Z_2, Z_3, Z_0Z_1, Z_2Z_3
  classical output layer: logit_c = w_c * <O_c> + b_c  (6 scales + 6 biases; diagonal — it cannot
                mix observables, so class separation must come from the quantum circuit)
  loss        : mean cross-entropy (softmax over the 6 logits)

Gradients of quantum parameters: parameter-shift rule, exact for RY/RZ (generator ±1/2 eigenvalues):
  ∂<O>/∂θ = ( <O>(θ+π/2) − <O>(θ−π/2) ) / 2.   Classical-head gradients are analytic.
Optimisers: Adam (parameter-shift gradients, mini-batches), COBYLA (scipy, gradient-free, full batch),
SPSA (own implementation, Spall's standard gain schedule, mini-batches).
Model selection / early stopping uses internal-validation loss only; best-validation parameters are kept.
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

import numpy as np

from .qsim import Sim, circuit_resources, z_expectations, zz_expectations

N_CLASSES = 6


def readout_spec(n: int):
    if n >= 6:
        return [("Z", (i,)) for i in range(6)]
    if n == 4:
        return [("Z", (0,)), ("Z", (1,)), ("Z", (2,)), ("Z", (3,)), ("ZZ", (0, 1)), ("ZZ", (2, 3))]
    raise ValueError("VQC readout defined for n = 4 or n >= 6 qubits")


def entangler_pairs(n: int, kind: str):
    if kind == "ring":
        return [(i, (i + 1) % n) for i in range(n)]
    if kind == "linear":
        return [(i, i + 1) for i in range(n - 1)]
    raise ValueError(kind)


class VQCCircuit:
    """The circuit is compiled to a gate tape [(kind, qubit(s), angle-source)] where angle-source is
    ("data", column) for encoding gates or ("param", index) for trainable gates. The same tape drives the
    batched simulation, the Qiskit recording and the parameter-shift evaluation."""

    def __init__(self, n: int, layers: int, entangler: str = "ring", reupload: bool = False):
        self.n, self.L, self.ent, self.reupload = n, layers, entangler, reupload
        self.n_params = layers * n * 2
        self.readout = readout_spec(n)
        tape = [("ry", i, ("data", i)) for i in range(n)]
        for l in range(layers):
            if reupload and l > 0:
                tape += [("ry", i, ("data", i)) for i in range(n)]
            for i in range(n):
                tape.append(("ry", i, ("param", (l * n + i) * 2)))
                tape.append(("rz", i, ("param", (l * n + i) * 2 + 1)))
            tape += [("cx", (c, t), None) for c, t in entangler_pairs(n, entangler)]
        self.tape = tape
        self.param_pos = {src[1]: k for k, (_, _, src) in enumerate(tape) if src and src[0] == "param"}

    def _apply(self, sim: Sim, op, A, theta, override=None):
        kind, q, src = op
        if kind == "cx":
            sim.cx(*q)
            return
        ang = A[:, src[1]] if src[0] == "data" else (theta[src[1]] if override is None else override)
        (sim.ry if kind == "ry" else sim.rz)(q, ang)

    def run(self, A: np.ndarray, theta: np.ndarray, record: bool = False) -> Sim:
        A = np.asarray(A, dtype=float)
        sim = Sim(len(A), self.n, record=record)
        for op in self.tape:
            self._apply(sim, op, A, theta)
        return sim

    def _readout(self, st: np.ndarray) -> np.ndarray:
        cols = []
        for kind, q in self.readout:
            cols.append(z_expectations(st, self.n, [q[0]])[:, 0] if kind == "Z"
                        else zz_expectations(st, self.n, [q])[:, 0])
        return np.stack(cols, axis=1)

    def expectations(self, A: np.ndarray, theta: np.ndarray) -> np.ndarray:
        return self._readout(self.run(A, theta).state)

    def param_shift_jacobian(self, A: np.ndarray, theta: np.ndarray) -> np.ndarray:
        """d<O_c>/dθ_p for every sample, shape (B, n_params, 6), by the parameter-shift rule
        ( <O>(θ_p+π/2) − <O>(θ_p−π/2) ) / 2. Each shifted circuit is evaluated exactly; the gates before
        the shifted gate are identical for both shifts, so their output state is computed once and reused."""
        A = np.asarray(A, dtype=float)
        sim = Sim(len(A), self.n)
        before = {}
        for k, op in enumerate(self.tape):
            if op[2] and op[2][0] == "param":
                before[k] = sim.state.copy()
            self._apply(sim, op, A, theta)
        J = np.empty((len(A), self.n_params, N_CLASSES))
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


def _softmax(z):
    z = z - z.max(1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(1, keepdims=True)


class VQC:
    """Runner estimator. params: layers, optimizer (adam|cobyla|spsa), entangler, reupload, lr,
    epochs/maxiter, batch_size, patience."""

    DEFAULTS = {"entangler": "ring", "reupload": False, "lr": 0.05, "epochs": 40, "batch_size": 64,
                "patience": 8, "cobyla_maxiter": 1500, "spsa_iters": 600, "spsa_a": 0.2, "spsa_c": 0.1,
                "init_scale": 0.1, "head_init": 2.0, "train_quantum": True}

    def __init__(self, params: Dict, seed: int):
        self.params = {**self.DEFAULTS, **params}
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.circ: Optional[VQCCircuit] = None
        self.theta = self.w = self.b = None
        self.history: List[Dict] = []
        self.diag: Dict = {}

    # ── model ──
    def _logits(self, A, theta, w, b):
        return self.circ.expectations(A, theta) * w + b

    def _loss(self, A, y, theta, w, b):
        P = _softmax(self._logits(A, theta, w, b))
        return float(-np.mean(np.log(np.clip(P[np.arange(len(y)), y], 1e-12, 1))))

    def loss_and_grad(self, A, y, theta, w, b):
        E = self.circ.expectations(A, theta)
        P = _softmax(E * w + b)
        Y = np.eye(N_CLASSES)[y]
        loss = float(-np.mean(np.log(np.clip(P[np.arange(len(y)), y], 1e-12, 1))))
        G = (P - Y) / len(y)                 # dL/dlogits
        gw = np.sum(G * E, axis=0)
        gb = np.sum(G, axis=0)
        if self.params.get("train_quantum", True):
            J = self.circ.param_shift_jacobian(A, theta)      # (B, P, 6)
            gtheta = np.einsum("bc,bpc->p", G * w, J)
        else:  # ablation: circuit frozen at its random initialisation, only the head is trained
            gtheta = np.zeros_like(theta)
        return loss, gtheta, gw, gb

    def _pack(self):
        return np.concatenate([self.theta, self.w, self.b])

    def _unpack(self, v):
        P = self.circ.n_params
        return v[:P], v[P:P + N_CLASSES], v[P + N_CLASSES:]

    # ── training ──
    def fit(self, X, y, Xv, yv):
        p = self.params
        X, Xv = np.asarray(X, float), np.asarray(Xv, float)
        y, yv = np.asarray(y, int), np.asarray(yv, int)
        self.circ = VQCCircuit(X.shape[1], p["layers"], p["entangler"], p["reupload"])
        self.theta = self.rng.uniform(-p["init_scale"], p["init_scale"], self.circ.n_params)
        self.w = np.full(N_CLASSES, p["head_init"])
        self.b = np.zeros(N_CLASSES)
        theta0 = self.theta.copy()
        # gradient statistics at initialisation (barren-plateau check), on a fixed train subset
        sub = self.rng.choice(len(X), size=min(128, len(X)), replace=False)
        _, g0, _, _ = self.loss_and_grad(X[sub], y[sub], self.theta, self.w, self.b)
        self.diag["init_grad"] = {"l2_norm": float(np.linalg.norm(g0)), "mean_abs": float(np.mean(np.abs(g0))),
                                  "var": float(np.var(g0)),
                                  "per_layer_var": [float(np.var(v)) for v in g0.reshape(p["layers"], -1)]}
        if not p["train_quantum"] and p["optimizer"] != "adam":
            raise ValueError("frozen-circuit ablation is defined for the Adam optimiser only")
        t0 = time.perf_counter()
        opt = p["optimizer"]
        if opt == "adam":
            self._fit_adam(X, y, Xv, yv)
        elif opt == "cobyla":
            self._fit_cobyla(X, y, Xv, yv)
        elif opt == "spsa":
            self._fit_spsa(X, y, Xv, yv)
        else:
            raise ValueError(opt)
        self.diag["train_time_s"] = time.perf_counter() - t0
        self.diag["theta_change_l2"] = float(np.linalg.norm(self.theta - theta0))
        self.diag["n_quantum_params"] = int(self.circ.n_params)
        self.diag["n_classical_params"] = 2 * N_CLASSES
        return {"training_log": {"history": self.history, "optimizer": opt,
                                 "settings": {k: v for k, v in p.items()},
                                 "best": self.diag.get("best"),
                                 "gradient_method": "parameter-shift (exact, shift pi/2)" if opt == "adam"
                                 else ("none (COBYLA, gradient-free)" if opt == "cobyla"
                                       else "SPSA simultaneous-perturbation estimate"),
                                 "readout": [f"{k}{q}" for k, q in self.circ.readout],
                                 "loss": "mean cross-entropy"}}

    def _record(self, step, unit, X, y, Xv, yv, extra=None):
        tl, vl = self._loss(X, y, self.theta, self.w, self.b), self._loss(Xv, yv, self.theta, self.w, self.b)
        ta = float(np.mean(self.predict(X) == y))
        va = float(np.mean(self.predict(Xv) == yv))
        row = {unit: step, "train_loss": tl, "val_loss": vl, "train_acc": ta, "val_acc": va, **(extra or {})}
        self.history.append(row)
        return vl

    def _keep_best(self, vl, step):
        if vl < self.diag.get("best", {}).get("val_loss", np.inf):
            self.diag["best"] = {"val_loss": vl, "step": step}
            self._best = (self.theta.copy(), self.w.copy(), self.b.copy())
            return True
        return False

    def _restore_best(self):
        self.theta, self.w, self.b = self._best

    def _fit_adam(self, X, y, Xv, yv):
        p = self.params
        v = self._pack()
        m1, m2 = np.zeros_like(v), np.zeros_like(v)
        b1, b2, eps, t = 0.9, 0.999, 1e-8, 0
        bad = 0
        self._keep_best(self._record(0, "epoch", X, y, Xv, yv), 0)
        for ep in range(1, p["epochs"] + 1):
            perm = self.rng.permutation(len(X))
            gnorms = []
            for i in range(0, len(X), p["batch_size"]):
                idx = perm[i:i + p["batch_size"]]
                _, gt, gw, gb = self.loss_and_grad(X[idx], y[idx], self.theta, self.w, self.b)
                g = np.concatenate([gt, gw, gb])
                gnorms.append(float(np.linalg.norm(gt)))
                t += 1
                m1 = b1 * m1 + (1 - b1) * g
                m2 = b2 * m2 + (1 - b2) * g * g
                v = v - p["lr"] * (m1 / (1 - b1 ** t)) / (np.sqrt(m2 / (1 - b2 ** t)) + eps)
                self.theta, self.w, self.b = self._unpack(v)
            vl = self._record(ep, "epoch", X, y, Xv, yv, {"quantum_grad_norm_mean": float(np.mean(gnorms)),
                                                          "quantum_grad_norm_std": float(np.std(gnorms))})
            if self._keep_best(vl, ep):
                bad = 0
            else:
                bad += 1
                if bad >= p["patience"]:
                    break
        self._restore_best()
        self.diag["converged"] = bad >= p["patience"]
        self.diag["stopped_at"] = self.history[-1]["epoch"]

    def _fit_cobyla(self, X, y, Xv, yv):
        from scipy.optimize import minimize
        p = self.params
        state = {"n": 0}
        self._keep_best(self._record(0, "evaluation", X, y, Xv, yv), 0)

        def f(v):
            th, w, b = self._unpack(v)
            state["n"] += 1
            L = self._loss(X, y, th, w, b)
            if state["n"] % 50 == 0:
                self.theta, self.w, self.b = th, w, b
                self._keep_best(self._record(state["n"], "evaluation", X, y, Xv, yv), state["n"])
            return L

        res = minimize(f, self._pack(), method="COBYLA", options={"maxiter": p["cobyla_maxiter"], "rhobeg": 0.3})
        self.theta, self.w, self.b = self._unpack(res.x)
        self._keep_best(self._record(state["n"], "evaluation", X, y, Xv, yv), state["n"])
        self._restore_best()
        self.diag["converged"] = bool(res.success)
        self.diag["optimizer_message"] = str(res.message)
        self.diag["n_function_evaluations"] = int(state["n"])

    def _fit_spsa(self, X, y, Xv, yv):
        p = self.params
        a, c, A_ = p["spsa_a"], p["spsa_c"], 0.1 * p["spsa_iters"]
        v = self._pack()
        self._keep_best(self._record(0, "iteration", X, y, Xv, yv), 0)
        for k in range(1, p["spsa_iters"] + 1):
            ak, ck = a / (k + A_) ** 0.602, c / k ** 0.101
            idx = self.rng.choice(len(X), size=min(4 * p["batch_size"], len(X)), replace=False)
            d = self.rng.choice([-1.0, 1.0], size=v.shape)
            lp = self._loss(X[idx], y[idx], *self._unpack(v + ck * d))
            lm = self._loss(X[idx], y[idx], *self._unpack(v - ck * d))
            v = v - ak * (lp - lm) / (2 * ck) * d
            if k % 25 == 0:
                self.theta, self.w, self.b = self._unpack(v)
                self._keep_best(self._record(k, "iteration", X, y, Xv, yv), k)
        self.theta, self.w, self.b = self._unpack(v)
        self._restore_best()
        self.diag["converged"] = None
        self.diag["n_loss_evaluations"] = 2 * p["spsa_iters"]

    # ── inference ──
    def predict_proba(self, X):
        return _softmax(self._logits(np.asarray(X, float), self.theta, self.w, self.b))

    def predict(self, X):
        return self.predict_proba(X).argmax(1)

    def diagnostics(self):
        return self.diag

    def circuit_stats(self):
        A = np.full((1, self.circ.n), 0.7)
        qc = self.circ.run(A, self.theta, record=True).qc
        r = circuit_resources(qc)
        r.update({"circuit": "encoding + variational layers (measurement: exact expectation values)",
                  "n_layers": self.circ.L, "entangler": self.circ.ent, "data_reuploading": self.circ.reupload,
                  "n_trainable_quantum_params": self.circ.n_params, "readout": [f"{k}{q}" for k, q in self.circ.readout],
                  "shots": 0, "execution_mode": "statevector (exact expectation values)"})
        return r
