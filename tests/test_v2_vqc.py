"""Phase 5 validation: the VQC is a genuine trainable parameterized circuit."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from qiskit.quantum_info import SparsePauliOp, Statevector  # noqa: E402

from src.v2.vqc import VQC, VQCCircuit  # noqa: E402


@pytest.mark.parametrize("n,L,ent,re", [(4, 2, "ring", False), (6, 3, "linear", True), (8, 1, "ring", False)])
def test_circuit_matches_qiskit_expectations(n, L, ent, re):
    rng = np.random.default_rng(0)
    c = VQCCircuit(n, L, ent, re)
    A = rng.uniform(0, np.pi, (1, n))
    th = rng.uniform(-np.pi, np.pi, c.n_params)
    sim = c.run(A, th, record=True)
    sv = Statevector(sim.qc)
    np.testing.assert_allclose(sim.state[0], sv.data, atol=1e-10)
    E = c.expectations(A, th)[0]
    for col, (kind, q) in enumerate(c.readout):
        label = ["I"] * n
        for qi in q:
            label[n - 1 - qi] = "Z"
        ref = sv.expectation_value(SparsePauliOp("".join(label))).real
        assert abs(E[col] - ref) < 1e-10


def test_parameter_shift_matches_finite_differences():
    rng = np.random.default_rng(1)
    m = VQC({"layers": 2, "optimizer": "adam"}, 0)
    m.circ = VQCCircuit(4, 2)
    A = rng.uniform(0, np.pi, (10, 4))
    y = rng.integers(0, 6, 10)
    th, w, b = rng.uniform(-1, 1, m.circ.n_params), rng.uniform(0.5, 2, 6), rng.normal(size=6)
    _, gt, gw, gb = m.loss_and_grad(A, y, th, w, b)
    eps = 1e-6
    for p in range(m.circ.n_params):
        d = np.zeros_like(th); d[p] = eps
        fd = (m._loss(A, y, th + d, w, b) - m._loss(A, y, th - d, w, b)) / (2 * eps)
        assert abs(fd - gt[p]) < 1e-7
    for c in range(6):
        d = np.zeros(6); d[c] = eps
        assert abs((m._loss(A, y, th, w + d, b) - m._loss(A, y, th, w - d, b)) / (2 * eps) - gw[c]) < 1e-7
        assert abs((m._loss(A, y, th, w, b + d) - m._loss(A, y, th, w, b - d)) / (2 * eps) - gb[c]) < 1e-7


def test_last_layer_rz_has_zero_gradient():
    """Documented property: RZ in the final layer cannot change Z/ZZ expectations."""
    rng = np.random.default_rng(2)
    c = VQCCircuit(4, 2)
    J = c.param_shift_jacobian(rng.uniform(0, np.pi, (5, 4)), rng.uniform(-1, 1, c.n_params))
    last_rz = [1 * 2 * 4 + 2 * i + 1 for i in range(4)]
    assert np.max(np.abs(J[:, last_rz, :])) < 1e-12
    assert np.max(np.abs(J)) > 1e-3


def _toy(n=4, N=120, seed=0):
    """Same class centres for every call; `seed` only changes the sample noise."""
    centers = np.random.default_rng(123).uniform(0.3, 2.8, (6, n))
    rng = np.random.default_rng(seed)
    y = np.arange(N) % 6
    return np.clip(centers[y] + rng.normal(0, 0.15, (N, n)), 0, np.pi), y


@pytest.mark.parametrize("opt", ["adam", "cobyla", "spsa"])
def test_training_updates_parameters_and_reduces_loss(opt):
    X, y = _toy()
    Xv, yv = _toy(seed=1)
    m = VQC({"layers": 2, "optimizer": opt, "epochs": 6, "cobyla_maxiter": 300, "spsa_iters": 150}, 0)
    log = m.fit(X, y, Xv, yv)["training_log"]
    h = log["history"]
    assert m.diag["theta_change_l2"] > 1e-3            # quantum parameters actually moved
    assert min(r["val_loss"] for r in h) < h[0]["val_loss"]
    assert m.predict_proba(Xv).shape == (len(yv), 6)


def test_quantum_parameters_influence_predictions():
    X, y = _toy()
    m = VQC({"layers": 2, "optimizer": "adam", "epochs": 4}, 0)
    m.fit(X, y, X, y)
    p0 = m.predict_proba(X)
    m.theta = m.theta + 1.0
    assert np.max(np.abs(m.predict_proba(X) - p0)) > 1e-3
    cs = m.circuit_stats()
    assert cs["n_trainable_quantum_params"] == 16 and cs["cx_compiled"] >= 8
