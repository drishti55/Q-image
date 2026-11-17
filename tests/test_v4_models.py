"""Protocol V4: mixed-state (patch-ensemble) FRQI / NEQR kernels."""
import os
import pickle

import numpy as np
import pytest
from qiskit.quantum_info import Statevector

from src.frqi.encoder import FRQIEncoder
from src.neqr.encoder import NEQREncoder
from src.v2 import frqi_neqr as fn
from src.v4.models import MixedStateEncodingKernelSVC, mixed_states, patches


def _brute(X, rep, p, s, bits=4):
    """Tr(rho_A rho_B) = mean over patch pairs of |<psi_k|psi_l>|^2, with states from the real Qiskit encoders."""
    P = patches(X, p, s)
    S = []
    for img in P:
        row = []
        for patch in img:
            x = patch.reshape(p, p)
            qc = FRQIEncoder(x).build_circuit() if rep == "FRQI" else NEQREncoder(fn.neqr_quantize(x[None], bits).reshape(p, p), bits).build_circuit()
            row.append(Statevector(qc).data)
        S.append(np.array(row))
    K = np.zeros((len(X), len(X)))
    for a in range(len(X)):
        for b in range(len(X)):
            K[a, b] = np.mean(np.abs(S[a].conj() @ S[b].T) ** 2)
    return K


@pytest.mark.parametrize("rep", ["FRQI", "NEQR"])
def test_mixed_state_kernel_matches_qiskit_statevectors(rep):
    rng = np.random.default_rng(0)
    X = rng.random((3, 4, 4))
    params = {"representation": rep, "patch": 2, "stride": 2, "angle_scale": 1.0, "bits": 3, "norm": "none"}
    R = mixed_states(X, params)
    np.testing.assert_allclose(R @ R.T, _brute(X, rep, 2, 2, bits=3), atol=1e-6)


def test_kernel_is_translation_robust():
    rng = np.random.default_rng(1)
    img = rng.random((1, 16, 16))
    shifted = np.roll(img, 4, axis=2)  # shift by one stride: same multiset of patches up to the wrapped border
    params = {"representation": "FRQI", "patch": 4, "stride": 4, "angle_scale": 1.0, "bits": 4, "norm": "none"}
    R = mixed_states(np.concatenate([img, shifted]), params)
    K = R @ R.T
    pixel = fn.frqi_kernel(np.concatenate([img, shifted]))
    assert K[0, 1] / np.sqrt(K[0, 0] * K[1, 1]) > 0.999          # patch-ensemble kernel: identical
    assert pixel[0, 1] < 0.95                                      # pixel-level FRQI kernel: not


def test_checkpoint_is_small_and_has_no_training_data():
    rng = np.random.default_rng(2)
    X, y = rng.random((30, 8, 8)), np.arange(30) % 3
    m = MixedStateEncodingKernelSVC({"representation": "NEQR", "image_size": 8, "patch": 4, "stride": 4, "bits": 4, "C": 1.0}, seed=0)
    m.fit(X, y)
    blob = pickle.dumps(m)
    assert len(blob) < 50_000 and m._xtr is None
    m._xtr = X  # in the real runner the images are re-loaded from the image cache and hash-verified
    assert len(m.predict(X[:5])) == 5


def test_v3_protected_when_requested(monkeypatch):
    from src.v2 import paths
    monkeypatch.setenv("QIL_PROTECT_V3", "1")
    assert paths.is_historical_path(paths.DEFAULT_V3_ROOT / "experiments" / "x.json")
    assert not paths.is_historical_path(paths.DEFAULT_V4_ROOT / "experiments" / "x.json")
    monkeypatch.delenv("QIL_PROTECT_V3")
    assert not paths.is_historical_path(paths.DEFAULT_V3_ROOT / "experiments" / "x.json")
