"""Phase 4 validation: batched simulator vs Qiskit, feature maps vs Qiskit library, kernel checks,
shot-based kernel vs Aer and vs statevector."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from qiskit import QuantumCircuit  # noqa: E402
from qiskit.quantum_info import Statevector  # noqa: E402

from src.v2 import qkernel as qk  # noqa: E402
from src.v2.qsim import Sim, z_expectations, zz_expectations  # noqa: E402

TOL = 1e-10


def test_gates_match_qiskit():
    rng = np.random.default_rng(1)
    n = 4
    sim = Sim(1, n, record=True)
    for _ in range(3):
        for q in range(n):
            sim.h(q); sim.ry(q, rng.uniform(-3, 3)); sim.rz(q, rng.uniform(-3, 3)); sim.p(q, rng.uniform(-3, 3))
        sim.cx(0, 2); sim.cx(3, 1); sim.cx(1, 0)
    ref = Statevector(sim.qc).data
    np.testing.assert_allclose(sim.state[0], ref, atol=TOL)


def test_batched_equals_individual():
    rng = np.random.default_rng(2)
    X = rng.uniform(0, np.pi, (5, 3))
    batch = qk.encode(X, "zz_full", 2).state
    for i in range(5):
        np.testing.assert_allclose(batch[i], Statevector(qk.encode(X[i:i + 1], "zz_full", 2, record=True).qc).data,
                                   atol=TOL)


@pytest.mark.parametrize("ent,fmap", [("linear", "zz_linear"), ("full", "zz_full")])
@pytest.mark.parametrize("reps", [1, 2])
def test_zz_matches_qiskit_library(ent, fmap, reps):
    from qiskit.circuit.library import zz_feature_map
    rng = np.random.default_rng(3)
    x = rng.uniform(0, np.pi, 4)
    lib = zz_feature_map(4, reps=reps, entanglement=ent)
    ref = Statevector(lib.assign_parameters(x)).data
    ours = qk.encode(x[None, :], fmap, reps).state[0]
    # equal up to a global phase
    ov = abs(np.vdot(ref, ours))
    assert abs(ov - 1) < TOL


def test_product_ry_closed_form():
    rng = np.random.default_rng(4)
    X, Y = rng.uniform(0, np.pi, (6, 5)), rng.uniform(0, np.pi, (7, 5))
    K = qk.fidelity_kernel(qk.states(X, "product_ry", 1), qk.states(Y, "product_ry", 1))
    ref = np.prod(np.cos((X[:, None, :] - Y[None, :, :]) / 2) ** 2, axis=2)
    np.testing.assert_allclose(K, ref, atol=TOL)


@pytest.mark.parametrize("fmap,reps", [("product_ry", 1), ("zz_linear", 2), ("zz_full", 1)])
def test_kernel_properties(fmap, reps):
    rng = np.random.default_rng(5)
    X = rng.uniform(0, np.pi, (30, 6))
    y = np.arange(30) % 6
    K = qk.fidelity_kernel(qk.states(X, fmap, reps))
    d = qk.kernel_diagnostics(K, y)
    assert d["symmetry_max_abs_error"] < 1e-12
    assert abs(d["diag_min"] - 1) < 1e-10 and abs(d["diag_max"] - 1) < 1e-10
    assert d["in_unit_interval"] and d["psd_within_tol"]


def test_expectations():
    s = Sim(1, 2)
    s.ry(0, np.pi)  # |01> in qiskit order -> Z0 = -1, Z1 = +1
    np.testing.assert_allclose(z_expectations(s.state, 2, [0, 1])[0], [-1, 1], atol=TOL)
    np.testing.assert_allclose(zz_expectations(s.state, 2, [(0, 1)])[0], [-1], atol=TOL)


def test_shot_kernel_identical_inputs_is_one_on_aer():
    x = np.array([0.3, 1.1, 2.0, 2.9])
    for fmap in ("product_ry", "zz_linear"):
        assert qk.aer_kernel_entry(x, x, fmap, 2, shots=500, seed=1) == 1.0
    qc = qk.kernel_circuit(x, x, "zz_linear", 1)
    assert sum(1 for ins in qc.data if ins.operation.name == "measure") == 4  # measured exactly once


def test_shot_kernel_matches_statevector_on_aer():
    rng = np.random.default_rng(6)
    X = rng.uniform(0, np.pi, (4, 4)) * 0.5
    shots = 4000
    for i in range(3):
        exact = float(qk.fidelity_kernel(qk.states(X[i:i + 1], "zz_linear", 1),
                                         qk.states(X[i + 1:i + 2], "zz_linear", 1))[0, 0])
        est = qk.aer_kernel_entry(X[i], X[i + 1], "zz_linear", 1, shots=shots, seed=i)
        sd = np.sqrt(max(exact * (1 - exact), 1e-6) / shots)
        assert abs(est - exact) < 5 * sd + 1e-3, (exact, est)


def test_binomial_sampler_unbiased_and_diag_one():
    rng = np.random.default_rng(7)
    X = rng.uniform(0, np.pi, (40, 4)) * 0.3
    K = qk.fidelity_kernel(qk.states(X, "zz_linear", 1))
    est = np.mean([qk.sample_shot_kernel(K, 200, rng, True) for _ in range(200)], axis=0)
    assert np.all(np.diag(qk.sample_shot_kernel(K, 200, rng, True)) == 1.0)
    assert np.max(np.abs(est - K)) < 0.03


def test_legacy_frqi_shot_kernel_fixed():
    """Protocol V0 bug: shot-mode FRQI/NEQR kernels returned 0 for identical images."""
    from src.qml.frqi_qml import FRQIQMLPipeline
    from src.qml.neqr_qml import NEQRQMLPipeline
    a = np.array([[0.2, 0.4], [0.6, 0.8]])
    assert FRQIQMLPipeline((2, 2), shots=500).compute_kernel_entry(a, a) == 1.0
    assert NEQRQMLPipeline((2, 2), intensity_bits=2, shots=500).compute_kernel_entry(a, a) == 1.0
    b = np.array([[0.9, 0.1], [0.3, 0.5]])
    exact = FRQIQMLPipeline((2, 2), shots=0).compute_kernel_entry(a, b)
    est = FRQIQMLPipeline((2, 2), shots=8000).compute_kernel_entry(a, b)
    assert abs(est - exact) < 5 * np.sqrt(exact * (1 - exact) / 8000) + 1e-3


def test_qkc_estimator_runs():
    rng = np.random.default_rng(8)
    X = rng.uniform(0, np.pi, (60, 4))
    y = np.arange(60) % 6
    m = qk.QuantumKernelSVC({"feature_map": "zz_linear", "reps": 1, "bandwidth": 0.2, "C": 1.0}, 0)
    m.fit(X, y)
    assert m.predict(X[:7]).shape == (7,)
    cs = m.circuit_stats()
    assert cs["n_qubits"] == 4 and cs["cx_compiled"] >= 6 and cs["gates_compiled"] > 0
