"""Phase 6 validation: FRQI/NEQR kernels equal overlaps of the ORIGINAL encoder circuits' statevectors."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from qiskit.quantum_info import Statevector  # noqa: E402

from src.frqi.encoder import FRQIEncoder  # noqa: E402
from src.neqr.encoder import NEQREncoder  # noqa: E402
from src.v2 import frqi_neqr as fn  # noqa: E402


def _imgs(r, n=4, seed=0):
    return np.random.default_rng(seed).random((n, r, r))


@pytest.mark.parametrize("r", [2, 4])
def test_frqi_kernel_equals_statevector_overlap(r):
    X = _imgs(r)
    S = np.array([Statevector(FRQIEncoder(x).build_circuit()).data for x in X])
    np.testing.assert_allclose(fn.frqi_kernel(X), np.abs(S.conj() @ S.T) ** 2, atol=1e-10)


@pytest.mark.parametrize("r,bits", [(2, 2), (2, 4), (4, 2), (4, 4)])
def test_neqr_kernel_equals_statevector_overlap(r, bits):
    X = _imgs(r, seed=1)
    X[1] = X[0]  # guarantee some exact pixel matches
    S = np.array([Statevector(NEQREncoder(fn.neqr_quantize(x[None], bits).reshape(r, r), bits).build_circuit()).data
                  for x in X])
    np.testing.assert_allclose(fn.neqr_kernel(X, bits=bits), np.abs(S.conj() @ S.T) ** 2, atol=1e-10)


def test_matches_legacy_v0_kernels():
    from src.qml.frqi_qml import FRQIQMLPipeline
    from src.qml.neqr_qml import NEQRQMLPipeline
    X, Y = _imgs(4, 5, 2), _imgs(4, 3, 3)
    np.testing.assert_allclose(fn.frqi_kernel(X, Y), FRQIQMLPipeline((4, 4)).compute_kernel_matrix(X, Y), atol=1e-12)
    np.testing.assert_allclose(fn.neqr_kernel(X, Y, 4),
                               NEQRQMLPipeline((4, 4), intensity_bits=4).compute_kernel_matrix(X, Y), atol=1e-12)


def test_frqi_bandwidth_variant_is_separate_and_valid():
    X = _imgs(4, 6, 4)
    K1, K4 = fn.frqi_kernel(X), fn.frqi_kernel(X, b=4.0)
    assert not np.allclose(K1, K4)
    assert np.allclose(np.diag(K4), 1) and np.allclose(K4, K4.T) and K4.min() >= 0


def test_estimators_and_resources():
    X = _imgs(4, 24, 5)
    y = np.arange(24) % 6
    for p in ({"representation": "FRQI", "C": 1.0}, {"representation": "NEQR", "C": 1.0, "bits": 4},
              {"representation": "NEQR", "C": 1.0, "bits": 2, "shots": 200}):
        m = fn.EncodingKernelSVC(p, 0)
        m.fit(X, y)
        assert m.predict(X[:5]).shape == (5,)
        cs = m.circuit_stats()
        assert cs["gates_compiled"] > 0 and cs["n_qubits"] == (5 if p["representation"] == "FRQI" else 4 + p["bits"])
