"""
FRQI / NEQR classification under Protocol V2 (E1 / E2) using the ORIGINAL encodings
(src/frqi/encoder.py, src/neqr/encoder.py).

Kernels are the exact state overlaps of the encoded images, K(A,B) = |<I_A|I_B>|²:
  FRQI : |I> = N^{-1/2} Σ_i (cos θ_i |0> + sin θ_i |1>) ⊗ |i>,  θ_i = b · I_i · π/2
         K = [ N^{-1} Σ_i cos(θ_i^A − θ_i^B) ]²       (b = 1 is the original encoding)
  NEQR : |I> = N^{-1/2} Σ_i |C_i> ⊗ |i>, C_i = round(I_i (2^q − 1))  (original quantisation)
         K = [ N^{-1} Σ_i δ(C_i^A, C_i^B) ]²
The closed forms are verified against Statevector overlaps of the actual encoder circuits in
tests/test_v2_frqi_neqr.py. Shot-based kernels: Binomial(shots, K)/shots per entry (ideal
compute–uncompute measurement; the legacy Aer circuit path is validated separately).

Also re-run under V2, with HONEST labels:
  EncodingStatsLogReg  — classical logistic regression on statistics computed in closed form from the
                         pixels (legacy "HQCC"; no circuit is executed or measured).
  LegacyFixedSoftmax   — the V0 "Variational Quantum Classifier": 15-step softmax regression on the same
                         classical statistics; contains NO parameterised quantum circuit.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Dict

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from .qkernel import kernel_diagnostics, sample_shot_kernel
from .qsim import circuit_resources


def frqi_angles(X: np.ndarray, b: float = 1.0) -> np.ndarray:
    return np.asarray(X, float).reshape(len(X), -1) * (np.pi / 2.0) * b


def frqi_kernel(XA, XB=None, b: float = 1.0) -> np.ndarray:
    A = frqi_angles(XA, b)
    B = A if XB is None else frqi_angles(XB, b)
    ov = (np.cos(A) @ np.cos(B).T + np.sin(A) @ np.sin(B).T) / A.shape[1]
    return np.clip(ov ** 2, 0.0, 1.0)


def neqr_quantize(X: np.ndarray, bits: int) -> np.ndarray:
    mx = (1 << bits) - 1
    return np.clip(np.round(np.asarray(X, float) * mx), 0, mx).astype(np.int64).reshape(len(X), -1)


def neqr_kernel(XA, XB=None, bits: int = 4) -> np.ndarray:
    qa = neqr_quantize(XA, bits)
    qb = qa if XB is None else neqr_quantize(XB, bits)
    M = np.zeros((len(qa), len(qb)))
    for level in range(1 << bits):
        a, b = (qa == level).astype(np.float32), (qb == level).astype(np.float32)
        if a.any() and b.any():
            M += a @ b.T
    return np.clip((M / qa.shape[1]) ** 2, 0.0, 1.0)


@lru_cache(maxsize=64)
def _encoder_resources(rep: str, r: int, bits: int, sample_key: bytes) -> Dict:
    from src.frqi.encoder import FRQIEncoder
    from src.neqr.encoder import NEQREncoder
    img = np.frombuffer(sample_key, dtype=np.float64).reshape(r, r)
    if rep == "FRQI":
        qc = FRQIEncoder(img).build_circuit()
    else:
        qc = NEQREncoder(neqr_quantize(img[None], bits).reshape(r, r), intensity_bits=bits).build_circuit()
    return circuit_resources(qc)


def encoder_resources(rep: str, images: np.ndarray, bits: int = 8, n: int = 5) -> Dict:
    """Resources of the original encoder circuits for n sample images (NEQR depends on pixel bits)."""
    rows = [_encoder_resources(rep, images.shape[1], bits, np.ascontiguousarray(im, dtype=np.float64).tobytes())
            for im in images[:n]]
    out = dict(rows[0])
    for key in ("gates_logical", "depth_logical", "gates_compiled", "depth_compiled", "cx_compiled",
                "two_qubit_gates_compiled"):
        v = [r[key] for r in rows]
        out[key] = int(round(np.mean(v)))
        out[key + "_range"] = [int(min(v)), int(max(v))]
    out["n_sample_images"] = len(rows)
    out["note"] = ("encoding circuit of one image; values are means over sample training images "
                   "(NEQR gate count depends on pixel bit patterns)")
    return out


class EncodingKernelSVC:
    """params: representation (FRQI|NEQR), C, bits (NEQR), angle_scale (FRQI), shots."""

    def __init__(self, params: Dict, seed: int):
        self.params = {"shots": 0, "angle_scale": 1.0, "bits": 8, **params}
        self.rng = np.random.default_rng(20_000 + seed)
        self.svm = SVC(kernel="precomputed", C=self.params["C"], random_state=seed)
        self._diag: Dict = {}

    def _K(self, A, B=None):
        p = self.params
        if p["representation"] == "FRQI":
            return frqi_kernel(A, B, p["angle_scale"])
        return neqr_kernel(A, B, p["bits"])

    def fit(self, X, y, Xv=None, yv=None):
        self.Xtr = np.asarray(X, float)
        K = self._K(self.Xtr)
        if self.params["shots"]:
            K = sample_shot_kernel(K, self.params["shots"], self.rng, symmetric=True)
        self._diag = {"train_kernel": kernel_diagnostics(K, np.asarray(y)),
                      "kernel": "exact closed-form state overlap (verified vs encoder statevectors)"
                      if not self.params["shots"] else f"Binomial({self.params['shots']}) sampled overlaps"}
        self.svm.fit(K, y)
        return {}

    def predict(self, X):
        K = self._K(np.asarray(X, float), self.Xtr)
        if self.params["shots"]:
            K = sample_shot_kernel(K, self.params["shots"], self.rng, symmetric=False)
        return self.svm.predict(K)

    def diagnostics(self):
        return self._diag

    def circuit_stats(self):
        p = self.params
        r = encoder_resources(p["representation"], self.Xtr, bits=p["bits"])
        r.update({"representation": p["representation"], "shots": p["shots"],
                  "angle_scale": p["angle_scale"] if p["representation"] == "FRQI" else None,
                  "intensity_bits": p["bits"] if p["representation"] == "NEQR" else None,
                  "execution_mode": "statevector overlap (exact)" if not p["shots"] else f"{p['shots']} shots (sampled)"})
        return r


def _legacy_pipeline(rep: str, r: int, bits: int):
    from src.qml.frqi_qml import FRQIQMLPipeline
    from src.qml.neqr_qml import NEQRQMLPipeline
    return FRQIQMLPipeline((r, r)) if rep == "FRQI" else NEQRQMLPipeline((r, r), intensity_bits=bits)


class EncodingStatsLogReg:
    """Legacy 'HQCC' features (closed-form classical statistics of the encodings) + logistic regression."""

    def __init__(self, params: Dict, seed: int):
        self.params = {"bits": 4, **params}
        self.seed = seed
        self.sc = StandardScaler()
        self.m = LogisticRegression(C=self.params["C"], max_iter=5000, random_state=seed)

    def _F(self, X):
        X = np.asarray(X, float)
        pipe = _legacy_pipeline(self.params["representation"], X.shape[1], self.params["bits"])
        return np.array([pipe.extract_quantum_features(x) for x in X])

    def fit(self, X, y, Xv=None, yv=None):
        F = self._F(X)
        self.n_constant = int((F.std(0) < 1e-12).sum())
        self.m.fit(self.sc.fit_transform(F), y)
        return {}

    def predict(self, X):
        return self.m.predict(self.sc.transform(self._F(X)))

    def predict_proba(self, X):
        return self.m.predict_proba(self.sc.transform(self._F(X)))

    def diagnostics(self):
        return {"n_constant_features": self.n_constant,
                "label_note": "No quantum circuit is executed; features are closed-form pixel statistics."}


class LegacyFixedSoftmax:
    """The unchanged V0 'VariationalQuantumClassifier' (src/qml/models.py), re-run under Protocol V2."""

    def __init__(self, params: Dict, seed: int):
        self.params = {"bits": 4, **params}
        self.seed = seed

    def fit(self, X, y, Xv=None, yv=None):
        from src.qml.models import VariationalQuantumClassifier
        r = np.asarray(X).shape[1]
        self.m = VariationalQuantumClassifier(representation=self.params["representation"], resolution=(r, r),
                                              intensity_bits=self.params["bits"], epochs=15, learning_rate=0.05,
                                              seed=self.seed)
        self.m.fit(np.asarray(X, float), np.asarray(y, int))
        return {"training_log": {"history": self.m.training_history, "optimizer": "full-batch gradient descent",
                                 "settings": {"epochs": 15, "lr": 0.05},
                                 "label_note": "classical softmax regression; formerly labelled VQC in V0"}}

    def predict(self, X):
        return self.m.predict(np.asarray(X, float))
