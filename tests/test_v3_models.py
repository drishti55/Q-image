"""Protocol V3 model / feature / protection tests. Pure computation; nothing is written to results/."""
import os
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.v2 import paths  # noqa: E402
from src.v2.qkernel import encode, fidelity_kernel, states  # noqa: E402
from src.v3.features import Featurizer, per_image_normalize, texture_features  # noqa: E402
from src.v3.models import (EncodingKernelSVCv3, ProjectedQuantumKernelSVC, VQCCircuitV3, VQCv3,  # noqa: E402
                           bloch_vectors, frqi_overlap, neqr_overlap, spectrum_summary, stretch)
from src.v2.frqi_neqr import frqi_kernel, neqr_kernel  # noqa: E402

PAULI = {"X": np.array([[0, 1], [1, 0]]), "Y": np.array([[0, -1j], [1j, 0]]), "Z": np.diag([1, -1])}


def reduced(state, n, q):
    psi = state.reshape((2,) * n)          # axis 0 = qubit n-1
    ax = n - 1 - q
    psi = np.moveaxis(psi, ax, 0).reshape(2, -1)
    return psi @ psi.conj().T


def test_bloch_vectors_match_partial_trace():
    rng = np.random.default_rng(0)
    X = rng.uniform(0, np.pi, (3, 4))
    S = encode(X, "zz_full", 1).state
    B = bloch_vectors(S, 4)
    for b in range(3):
        for q in range(4):
            rho = reduced(S[b], 4, q)
            for j, P in enumerate("XYZ"):
                assert B[b, 3 * q + j] == pytest.approx(np.real(np.trace(rho @ PAULI[P])), abs=1e-10)


def test_pqk_is_valid_kernel_and_trains():
    rng = np.random.default_rng(1)
    X = rng.uniform(0, np.pi, (60, 4))
    y = np.repeat(np.arange(6), 10)
    m = ProjectedQuantumKernelSVC({"feature_map": "zz_linear", "reps": 1, "bandwidth": 1.0, "gamma": 1.0, "C": 10}, 0)
    m.fit(X, y)
    d = m.diagnostics()["train_kernel"]
    assert d["psd_within_tol"] and d["symmetry_max_abs_error"] < 1e-12 and d["diag_min"] == pytest.approx(1.0)
    assert m.predict(X).shape == (60,)
    assert m.circuit_stats()["n_qubits"] == 4


def test_vqc_zall_parameter_shift_matches_finite_difference():
    rng = np.random.default_rng(2)
    A = rng.uniform(0, np.pi, (5, 6))
    c = VQCCircuitV3(6, 2, "ring", True, "zall")
    th = rng.uniform(-1, 1, c.n_params)
    J = c.param_shift_jacobian(A, th)
    eps = 1e-6
    for p in (0, 7, c.n_params - 1):
        d = np.zeros_like(th)
        d[p] = eps
        fd = (c.expectations(A, th + d) - c.expectations(A, th - d)) / (2 * eps)
        assert np.allclose(J[:, p, :], fd, atol=1e-6)
    assert J.shape == (5, c.n_params, 6)


def test_vqc_v3_trains_and_encoding_only_control():
    rng = np.random.default_rng(3)
    X = rng.uniform(0, np.pi, (72, 6))
    y = np.repeat(np.arange(6), 12)
    for params in ({"layers": 1, "optimizer": "adam", "readout": "zall", "reupload": True, "epochs": 3},
                   {"layers": 1, "optimizer": "adam", "readout": "diag6", "epochs": 3},
                   {"layers": 0, "optimizer": "adam", "readout": "zall", "epochs": 3},
                   {"layers": 1, "optimizer": "spsa", "readout": "zall", "spsa_iters": 60}):
        m = VQCv3(params, 0)
        m.fit(X[:48], y[:48], X[48:], y[48:])
        assert m.predict_proba(X).shape == (72, 6)
        assert np.allclose(m.predict_proba(X).sum(1), 1)
    m0 = VQCv3({"layers": 0, "optimizer": "adam", "readout": "zall", "epochs": 1}, 0)
    m0.fit(X[:48], y[:48], X[48:], y[48:])
    assert np.allclose(m0.circ.expectations(X, m0.theta), np.cos(X))  # encoding-only: <Z_i> = cos(a_i)


def test_overlap_kernels_are_square_roots_of_fidelity():
    rng = np.random.default_rng(4)
    X = rng.uniform(0, 1, (8, 4, 4))
    assert np.allclose(frqi_overlap(X) ** 2, frqi_kernel(X))
    assert np.allclose(neqr_overlap(X, bits=3) ** 2, neqr_kernel(X, bits=3))
    for kern in ("fidelity", "overlap"):
        m = EncodingKernelSVCv3({"representation": "NEQR", "C": 1.0, "bits": 3, "kernel": kern, "norm": "stretch"}, 0)
        K = m._K(X)
        assert np.linalg.eigvalsh(K).min() > -1e-9
    S = stretch(X)
    assert np.allclose(S.reshape(8, -1).min(1), 0) and np.allclose(S.reshape(8, -1).max(1), 1)


def test_cdf_view_and_per_image_norm():
    rng = np.random.default_rng(5)
    F = rng.standard_t(2, (200, 10)) * 5
    f = Featurizer(k=4).fit(F[:150])
    A = f.transform(F[150:], "cdf")
    assert A.min() > 0 and A.max() < np.pi
    Z = per_image_normalize(rng.uniform(0, 1, (5, 8, 8)))
    assert np.allclose(Z.reshape(5, -1).mean(1), 0) and np.allclose(Z.reshape(5, -1).std(1), 1)


def test_texture_descriptor_shape_and_illumination_robustness():
    img = np.random.default_rng(6).uniform(0.2, 0.6, (64, 64))
    f1, f2 = texture_features(img), texture_features(img * 0.5 + 0.1)
    assert f1.shape == (76,) and np.all(np.isfinite(f1))
    assert np.allclose(f1[:54], f2[:54], atol=0.02)  # LBP histograms ~invariant to monotone intensity change


def test_spectrum_summary():
    K = fidelity_kernel(states(np.random.default_rng(7).uniform(0, np.pi, (30, 3)), "zz_linear", 1))
    s = spectrum_summary(K)
    assert 0 < s["top1_fraction"] <= 1 and s["effective_dimension"] >= 1


def test_v2_root_protected_when_requested(monkeypatch):
    v2 = paths.DEFAULT_V2_ROOT / "experiments" / "x.json"
    v3 = paths.DEFAULT_V3_ROOT / "experiments" / "x.json"
    monkeypatch.delenv("QIL_PROTECT_V2", raising=False)
    monkeypatch.delenv("QIL_ALLOW_V0_WRITES", raising=False)
    assert not paths.is_historical_path(v2) and not paths.is_historical_path(v3)
    monkeypatch.setenv("QIL_PROTECT_V2", "1")
    assert paths.is_historical_path(v2) and not paths.is_historical_path(v3)
    with pytest.raises(paths.HistoricalWriteError):
        paths.assert_writable(v2)
    assert paths.is_historical_path(paths.HISTORICAL_RESULTS_ROOT / "qml" / "a.csv")
