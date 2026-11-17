"""
Protocol V4 models: patch-ensemble (mixed-state) FRQI / NEQR kernels and a matched classical control.

Why: FRQI / NEQR image kernels compare two images pixel-by-pixel at fixed positions, so a texture shifted by a few
pixels looks unrelated. NEU defect classes are textures. V4 encodes every p x p patch of an image (stride s) as an
FRQI or NEQR state |psi_k>, and represents the image by the *mixed state*

    rho_I = (1/P) sum_k |psi_k><psi_k|          (uniformly random patch of image I, encoded)

The kernel is the Hilbert-Schmidt overlap  K(A, B) = Tr(rho_A rho_B) = mean_{k,l} |<psi_k^A | psi_l^B>|^2,
which a swap test between one random patch state of A and one of B estimates directly (the swap test measures
Tr(rho sigma) for mixed inputs). It is translation-robust by construction.

Everything is computed exactly (statevector algebra) on a CPU; like all FRQI / NEQR kernels in this project the
overlaps have closed forms, so this is NOT a claim of quantum advantage.

FRQI patch state (N = p*p pixels):  |psi> = N^-1/2 sum_i (cos t_i |0> + sin t_i |1>) |i>,   t_i = (pi/2) * b * x_i
NEQR patch state (q bits):          |psi> = N^-1/2 sum_i |c_i>|i>,                          c_i = round(x_i (2^q - 1))
"""
from __future__ import annotations

import hashlib
from typing import Dict

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from src.v2.frqi_neqr import encoder_resources
from src.v2.qkernel import kernel_diagnostics
from src.v3.models import spectrum_summary

_RHO: Dict[str, np.ndarray] = {}   # small per-process cache: candidates that differ only in C reuse the states


def stretch(X: np.ndarray) -> np.ndarray:
    """Per-image min-max contrast stretch (uses only the image itself, no training statistics)."""
    X = np.asarray(X, float)
    lo, hi = X.min((1, 2), keepdims=True), X.max((1, 2), keepdims=True)
    return (X - lo) / np.maximum(hi - lo, 1e-9)


def patches(X: np.ndarray, p: int, s: int) -> np.ndarray:
    n, S, _ = X.shape
    return np.stack([X[:, i:i + p, j:j + p].reshape(n, -1) for i in range(0, S - p + 1, s) for j in range(0, S - p + 1, s)], 1)


def frqi_states(P: np.ndarray, b: float) -> np.ndarray:
    t = P * (np.pi / 2.0) * b
    return np.concatenate([np.cos(t), np.sin(t)], 2) / np.sqrt(P.shape[2])


def neqr_states(P: np.ndarray, bits: int) -> np.ndarray:
    mx = (1 << bits) - 1
    q = np.clip(np.round(P * mx), 0, mx).astype(np.int64)
    n, NP, N = q.shape
    psi = np.zeros((n, NP, N * (mx + 1)), np.float32)
    np.put_along_axis(psi, np.arange(N)[None, None, :] * (mx + 1) + q, 1.0 / np.sqrt(N), 2)
    return psi


def mixed_states(X: np.ndarray, p: Dict) -> np.ndarray:
    """vec(rho) for every image, shape (n, D^2). Real amplitudes, so rho is real symmetric."""
    X = np.asarray(X, float)
    key = hashlib.sha1(X.tobytes()).hexdigest() + repr(sorted((k, p[k]) for k in ("representation", "patch", "stride", "angle_scale", "bits", "norm")))
    if key in _RHO:
        return _RHO[key]
    Xp = stretch(X) if p["norm"] == "stretch" else X
    P = patches(Xp, p["patch"], p["stride"])
    psi = frqi_states(P, p["angle_scale"]) if p["representation"] == "FRQI" else neqr_states(P, p["bits"])
    psi = psi.astype(np.float32)
    R = np.einsum("npi,npj->nij", psi, psi, optimize=True) / P.shape[1]
    out = R.reshape(len(X), -1)
    if len(_RHO) >= 4:
        _RHO.pop(next(iter(_RHO)))
    _RHO[key] = out
    return out


def _sha(X) -> str:
    return hashlib.sha256(np.ascontiguousarray(X, dtype=np.float64).tobytes()).hexdigest()


class _TrainRef:
    """Keeps checkpoints small: instead of pickling training images / density matrices, store the seed, image size and
    SHA-256 of the training images; reload them from the (read-only) image cache on demand and verify the hash."""

    def _remember(self, X):
        self._xtr_sha, self._n_train = _sha(X), len(X)
        self._xtr = np.asarray(X, float)

    def _train_images(self):
        if getattr(self, "_xtr", None) is None:
            from src.v2.providers import ImageProvider
            tr, _, _ = ImageProvider(self.params["image_size"]).train_val(self.seed)
            if _sha(tr.X) != self._xtr_sha:
                raise RuntimeError("training images do not match the checkpoint hash")
            self._xtr = np.asarray(tr.X, float)
        return self._xtr

    def __getstate__(self):
        d = dict(self.__dict__)
        d["_xtr"] = None
        return d


def patch_qubits(rep: str, p: int, bits: int) -> int:
    return 2 * (p.bit_length() - 1) + (1 if rep == "FRQI" else bits)


class MixedStateEncodingKernelSVC(_TrainRef):
    """params: representation (FRQI|NEQR), image_size, patch, stride, angle_scale (FRQI), bits (NEQR), norm, C."""

    def __init__(self, params: Dict, seed: int):
        self.params = {"angle_scale": 1.0, "bits": 4, "norm": "none", **params}
        self.seed = seed
        self.svm = SVC(kernel="precomputed", C=self.params["C"], random_state=seed)
        self._diag: Dict = {}

    def fit(self, X, y, Xv=None, yv=None):
        self._remember(X)
        R = mixed_states(self._xtr, self.params)
        K = (R @ R.T).astype(float)
        self._diag = {"train_kernel": kernel_diagnostics(K, np.asarray(y)), "train_kernel_spectrum": spectrum_summary(K),
                      "purity_mean": float(np.mean(np.diag(K))),
                      "kernel": "exact Hilbert-Schmidt overlap Tr(rho_A rho_B) of patch-ensemble mixed states"}
        self.svm.fit(K, y)
        self._circ = self._circuit_stats()
        self._xtr = None  # do not hold training images in memory between candidates
        return {}

    def predict(self, X):
        Rtr = mixed_states(self._train_images(), self.params)
        out = self.svm.predict((mixed_states(np.asarray(X, float), self.params) @ Rtr.T).astype(float))
        self._xtr = None
        return out

    def diagnostics(self):
        return self._diag

    def circuit_stats(self):
        return self._circ

    def _circuit_stats(self):
        p = self.params
        Xs = self._xtr[:5]
        sample = patches(stretch(Xs) if p["norm"] == "stretch" else Xs, p["patch"], p["stride"])[:, 0]
        r = encoder_resources(p["representation"], sample.reshape(-1, p["patch"], p["patch"]), bits=p["bits"] if p["representation"] == "NEQR" else 8)
        nq = patch_qubits(p["representation"], p["patch"], p["bits"])
        r.update({"n_qubits": nq, "representation": p["representation"], "patch": p["patch"], "stride": p["stride"],
                  "patches_per_image": int(patches(Xs[:1], p["patch"], p["stride"]).shape[1]),
                  "angle_scale": p["angle_scale"] if p["representation"] == "FRQI" else None,
                  "intensity_bits": p["bits"] if p["representation"] == "NEQR" else None,
                  "measurement": f"swap test on two {nq}-qubit patch states (+1 ancilla): estimates Tr(rho_A rho_B)",
                  "execution_mode": "statevector (exact overlaps)", "shots": 0,
                  "note": "resources are for encoding ONE patch; the mixed state is a uniform random choice of patch"})
        return r


class PatchMomentRBF(_TrainRef):
    """CLASSICAL control on the same patches: per-image mean patch vector + mean outer product of raw patch
    intensities (the classical analogue of rho without the quantum feature map), standardised, RBF-SVM.
    params: patch, stride, norm, gamma (multiplied by 1/n_features), C."""

    def __init__(self, params: Dict, seed: int):
        self.params = {"norm": "none", **params}
        self.seed = seed
        self.svm = SVC(kernel="rbf", C=self.params["C"], gamma=self.params["gamma"], random_state=seed)

    def _f(self, X):
        p = self.params
        X = np.asarray(X, float)
        P = patches(stretch(X) if p["norm"] == "stretch" else X, p["patch"], p["stride"])
        M2 = np.einsum("npi,npj->nij", P, P, optimize=True) / P.shape[1]
        iu = np.triu_indices(P.shape[2])
        return np.concatenate([P.mean(1), M2[:, iu[0], iu[1]]], 1)

    def fit(self, X, y, Xv=None, yv=None):
        self._remember(X)
        self._y = np.asarray(y)
        self._fit()
        self._xtr = None
        return {}

    def _fit(self):
        F = self._f(self._train_images())
        self.sc = StandardScaler().fit(F)
        self.svm.set_params(gamma=self.params["gamma"] / F.shape[1])
        self.svm.fit(self.sc.transform(F), self._y)

    def predict(self, X):
        if not hasattr(self.svm, "support_"):
            self._fit()  # checkpoint stores no support vectors: deterministic re-fit on the hash-verified training images
        return self.svm.predict(self.sc.transform(self._f(X)))

    def __getstate__(self):
        d = super().__getstate__()
        d["svm"] = SVC(kernel="rbf", C=self.params["C"], gamma=self.params["gamma"], random_state=self.seed)
        d.pop("sc", None)
        return d

    def diagnostics(self):
        return {"label_note": "classical control: no quantum circuit; closed-form patch statistics"}
