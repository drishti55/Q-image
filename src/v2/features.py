"""
Feature pipelines for Protocol V2. Every learned transform is fitted on the TRAIN split only.

PCAFeaturizer (pixels):
    image (s×s, [0,1]) -> flatten -> StandardScaler (per pixel, train-fitted)
    -> PCA(k, train-fitted) -> two views:
       * "standard": StandardScaler on PCA scores (train-fitted)  — classical models
       * "angle":    MinMaxScaler to [0, π] (train-fitted)          — quantum angle encoding
    Validation/test angles may fall slightly outside [0, π]; they are NOT clipped (the fraction is
    reported) because clipping would be a data-dependent transform not applied to training data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler, StandardScaler


@dataclass
class PCAFeaturizer:
    k: int
    random_state: int = 0
    fitted_n: int = 0
    _pix: StandardScaler = field(default_factory=StandardScaler)
    _pca: Optional[PCA] = None
    _std: StandardScaler = field(default_factory=StandardScaler)
    _ang: MinMaxScaler = field(default_factory=lambda: MinMaxScaler(feature_range=(0.0, np.pi)))

    @staticmethod
    def _flat(X: np.ndarray) -> np.ndarray:
        return X.reshape(len(X), -1)

    def fit(self, X_train: np.ndarray) -> "PCAFeaturizer":
        Z = self._pix.fit_transform(self._flat(X_train))
        self._pca = PCA(n_components=self.k, svd_solver="full", random_state=self.random_state)
        S = self._pca.fit_transform(Z)
        self._std.fit(S)
        self._ang.fit(S)
        self.fitted_n = len(X_train)
        return self

    def scores(self, X: np.ndarray) -> np.ndarray:
        if self._pca is None:
            raise RuntimeError("PCAFeaturizer not fitted")
        return self._pca.transform(self._pix.transform(self._flat(X)))

    def transform(self, X: np.ndarray, view: str = "standard") -> np.ndarray:
        S = self.scores(X)
        if view == "standard":
            return self._std.transform(S)
        if view == "angle":
            return self._ang.transform(S)
        raise ValueError(view)

    def info(self) -> Dict:
        return {
            "method": "pixels -> StandardScaler -> PCA",
            "k": self.k,
            "fitted_on_n_train": self.fitted_n,
            "explained_variance_ratio": [float(v) for v in self._pca.explained_variance_ratio_],
            "explained_variance_total": float(self._pca.explained_variance_ratio_.sum()),
        }


@dataclass
class VectorFeaturizer:
    """For precomputed feature vectors (e.g. CNN embeddings): StandardScaler -> optional PCA(k)
    -> standard / angle views. All fitted on train only."""
    k: Optional[int] = None
    random_state: int = 0
    fitted_n: int = 0
    _in: StandardScaler = field(default_factory=StandardScaler)
    _pca: Optional[PCA] = None
    _std: StandardScaler = field(default_factory=StandardScaler)
    _ang: MinMaxScaler = field(default_factory=lambda: MinMaxScaler(feature_range=(0.0, np.pi)))

    def fit(self, F: np.ndarray) -> "VectorFeaturizer":
        Z = self._in.fit_transform(F)
        if self.k is not None:
            self._pca = PCA(n_components=self.k, svd_solver="full", random_state=self.random_state)
            Z = self._pca.fit_transform(Z)
        self._std.fit(Z)
        self._ang.fit(Z)
        self.fitted_n = len(F)
        return self

    def _z(self, F):
        Z = self._in.transform(F)
        return self._pca.transform(Z) if self._pca is not None else Z

    def transform(self, F: np.ndarray, view: str = "standard") -> np.ndarray:
        Z = self._z(F)
        return self._std.transform(Z) if view == "standard" else self._ang.transform(Z)

    def info(self) -> Dict:
        d = {"method": "StandardScaler" + (" -> PCA" if self.k else ""), "k": self.k,
             "fitted_on_n_train": self.fitted_n}
        if self._pca is not None:
            d["explained_variance_total"] = float(self._pca.explained_variance_ratio_.sum())
        return d


def out_of_range_fraction(A: np.ndarray, lo: float = 0.0, hi: float = np.pi) -> float:
    return float(np.mean((A < lo - 1e-12) | (A > hi + 1e-12)))
