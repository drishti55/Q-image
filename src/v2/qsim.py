"""
Batched statevector simulator (NumPy) for small circuits (≤ ~12 qubits), used to evaluate quantum
feature maps and variational circuits over whole datasets at once.

Conventions match Qiskit exactly: qubit 0 is the least-significant bit of the basis-state index,
gate matrices are Qiskit's (RY(θ)=[[c,-s],[s,c]] with c=cos θ/2, RZ(θ)=diag(e^{-iθ/2}, e^{iθ/2}),
P(λ)=diag(1, e^{iλ}), H, CX(control, target)). Correctness is checked against
qiskit.quantum_info.Statevector in tests/test_v2_qsim.py (tolerance 1e-10).

Every gate application can also be mirrored into a qiskit.QuantumCircuit (`Recorder`) so the circuit
that was simulated is the circuit whose resources are reported.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

SQ2 = 1.0 / np.sqrt(2.0)
H_MAT = np.array([[SQ2, SQ2], [SQ2, -SQ2]], dtype=complex)


def zero_state(batch: int, n: int) -> np.ndarray:
    s = np.zeros((batch, 2 ** n), dtype=complex)
    s[:, 0] = 1.0
    return s


def _apply_1q(state: np.ndarray, n: int, q: int, U: np.ndarray) -> np.ndarray:
    """U: (2,2) shared by the batch, or (B,2,2) per sample. Elementwise update of the amplitude pairs
    differing in bit q (exactly the same arithmetic as the matrix product, without einsum overhead)."""
    B = state.shape[0]
    v = state.reshape(B, 2 ** (n - q - 1), 2, 2 ** q)
    v0, v1 = v[:, :, 0, :], v[:, :, 1, :]
    if U.ndim == 2:
        a, b, c, d = U[0, 0], U[0, 1], U[1, 0], U[1, 1]
    else:
        a, b, c, d = (U[:, i, j][:, None, None] for i, j in ((0, 0), (0, 1), (1, 0), (1, 1)))
    out = np.empty_like(v)
    out[:, :, 0, :] = a * v0 + b * v1
    out[:, :, 1, :] = c * v0 + d * v1
    return out.reshape(B, 2 ** n)


def ry_mats(theta: np.ndarray) -> np.ndarray:
    c, s = np.cos(theta / 2), np.sin(theta / 2)
    M = np.empty(theta.shape + (2, 2), dtype=complex)
    M[..., 0, 0], M[..., 0, 1], M[..., 1, 0], M[..., 1, 1] = c, -s, s, c
    return M


def rz_mats(theta: np.ndarray) -> np.ndarray:
    M = np.zeros(theta.shape + (2, 2), dtype=complex)
    M[..., 0, 0], M[..., 1, 1] = np.exp(-0.5j * theta), np.exp(0.5j * theta)
    return M


def p_mats(lam: np.ndarray) -> np.ndarray:
    M = np.zeros(lam.shape + (2, 2), dtype=complex)
    M[..., 0, 0], M[..., 1, 1] = 1.0, np.exp(1j * lam)
    return M


class Sim:
    """Applies gates to a batch of states; optionally records a Qiskit circuit for one sample."""

    def __init__(self, batch: int, n: int, record: bool = False):
        self.n = n
        self.state = zero_state(batch, n)
        self.qc = None
        if record:
            from qiskit import QuantumCircuit
            self.qc = QuantumCircuit(n)

    @staticmethod
    def _theta(theta):
        return np.asarray(theta, dtype=float)  # 0-d (shared angle) or (B,) per-sample angles

    @staticmethod
    def _first(t):
        return float(t) if t.ndim == 0 else float(t[0])

    def h(self, q):
        self.state = _apply_1q(self.state, self.n, q, H_MAT)
        if self.qc is not None:
            self.qc.h(q)

    def ry(self, q, theta):
        t = self._theta(theta)
        self.state = _apply_1q(self.state, self.n, q, ry_mats(t))
        if self.qc is not None:
            self.qc.ry(self._first(t), q)

    def rz(self, q, theta):
        t = self._theta(theta)
        self.state = _apply_1q(self.state, self.n, q, rz_mats(t))
        if self.qc is not None:
            self.qc.rz(self._first(t), q)

    def p(self, q, lam):
        t = self._theta(lam)
        self.state = _apply_1q(self.state, self.n, q, p_mats(t))
        if self.qc is not None:
            self.qc.p(self._first(t), q)

    def cx(self, c, t):
        idx = np.arange(2 ** self.n)
        flip = ((idx >> c) & 1) == 1
        perm = idx.copy()
        perm[flip] = idx[flip] ^ (1 << t)
        self.state = self.state[:, perm]
        if self.qc is not None:
            self.qc.cx(c, t)


def z_expectations(state: np.ndarray, n: int, qubits) -> np.ndarray:
    """<Z_q> for each q in `qubits`, batch-wise. Returns (B, len(qubits))."""
    probs = np.abs(state) ** 2
    idx = np.arange(2 ** n)
    out = []
    for q in qubits:
        sign = 1.0 - 2.0 * ((idx >> q) & 1)
        out.append(probs @ sign)
    return np.stack(out, axis=1)


def zz_expectations(state: np.ndarray, n: int, pairs) -> np.ndarray:
    probs = np.abs(state) ** 2
    idx = np.arange(2 ** n)
    out = []
    for a, b in pairs:
        sign = (1.0 - 2.0 * ((idx >> a) & 1)) * (1.0 - 2.0 * ((idx >> b) & 1))
        out.append(probs @ sign)
    return np.stack(out, axis=1)


def circuit_resources(qc, basis=("cx", "rz", "sx", "x"), optimization_level: int = 1,
                      seed: Optional[int] = 0) -> dict:
    """Logical counts of `qc` and counts after transpilation to a fixed basis (consistent method used
    for every circuit in v2)."""
    from qiskit import transpile
    logical = dict(qc.count_ops())
    t = transpile(qc, basis_gates=list(basis), optimization_level=optimization_level, seed_transpiler=seed)
    comp = dict(t.count_ops())
    two_q_log = sum(1 for ins in qc.data if ins.operation.num_qubits == 2)
    two_q = sum(1 for ins in t.data if ins.operation.num_qubits == 2)
    return {
        "n_qubits": qc.num_qubits,
        "gates_logical": int(sum(logical.values())), "depth_logical": int(qc.depth()),
        "gate_counts_logical": {k: int(v) for k, v in logical.items()},
        "two_qubit_gates_logical": int(two_q_log),
        "gates_compiled": int(sum(comp.values())), "depth_compiled": int(t.depth()),
        "gate_counts_compiled": {k: int(v) for k, v in comp.items()},
        "single_qubit_gates_compiled": int(sum(v for k, v in comp.items() if k in ("rz", "sx", "x"))),
        "two_qubit_gates_compiled": int(two_q), "cx_compiled": int(comp.get("cx", 0)),
        "transpilation": {"basis_gates": list(basis), "optimization_level": optimization_level,
                          "seed_transpiler": seed, "coupling_map": "none (all-to-all)"},
    }
