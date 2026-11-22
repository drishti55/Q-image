"""Feature providers: turn a split seed into model inputs (train/val freely; test only when locked
stage is active — enforced by NEUData.test)."""
from __future__ import annotations

from functools import lru_cache
from typing import Dict, Optional

import numpy as np

from .dataset import NEUData
from .features import PCAFeaturizer, VectorFeaturizer, out_of_range_fraction
from .runner import FeatureProvider, FeatureSet

_DATA: Dict[int, NEUData] = {}


def neu(seed: int) -> NEUData:
    if seed not in _DATA:
        _DATA[seed] = NEUData(seed)
    return _DATA[seed]


@lru_cache(maxsize=64)
def _fitted_pca(seed: int, k: int, size: int) -> PCAFeaturizer:
    return PCAFeaturizer(k=k, random_state=seed).fit(neu(seed).train(size).X)


class PixelPCAProvider(FeatureProvider):
    """size×size pixels -> train-fitted StandardScaler -> PCA(k) -> view ('standard' | 'angle')."""

    def __init__(self, k: int, view: str, size: int = 64):
        self.k, self.view, self.size = k, view, size
        self.name = f"pixels{size}-pca{k}-{view}"

    def describe(self) -> Dict:
        return {"name": self.name, "input": f"{self.size}x{self.size} grayscale pixels", "pca_k": self.k,
                "view": self.view, "fit": "train split only"}

    def train_val(self, seed: int):
        d, f = neu(seed), _fitted_pca(seed, self.k, self.size)
        tr, va = d.train(self.size), d.val(self.size)
        Xtr, Xva = f.transform(tr.X, self.view), f.transform(va.X, self.view)
        info = {**f.info(), "view": self.view}
        if self.view == "angle":
            info["val_fraction_outside_0_pi"] = out_of_range_fraction(Xva)
        return FeatureSet(Xtr, tr.y, tr.paths), FeatureSet(Xva, va.y, va.paths), info

    def test(self, seed: int) -> FeatureSet:
        te = neu(seed).test(self.size)
        return FeatureSet(_fitted_pca(seed, self.k, self.size).transform(te.X, self.view), te.y, te.paths)


class ImageProvider(FeatureProvider):
    """Raw resized images (n, s, s) in [0, 1] — inputs for FRQI/NEQR encodings and pixel baselines."""

    def __init__(self, size: int, flatten: bool = False):
        self.size, self.flatten = size, flatten
        self.name = f"image{size}" + ("-flat" if flatten else "")

    def describe(self) -> Dict:
        return {"name": self.name, "input": f"{self.size}x{self.size} grayscale in [0,1]",
                "preprocessing": "convert('L') -> BILINEAR resize -> /255 (no learned transform)"}

    def _f(self, X):
        return X.reshape(len(X), -1) if self.flatten else X

    def train_val(self, seed: int):
        d = neu(seed)
        tr, va = d.train(self.size), d.val(self.size)
        return (FeatureSet(self._f(tr.X), tr.y, tr.paths), FeatureSet(self._f(va.X), va.y, va.paths),
                {"input": self.describe()["input"]})

    def test(self, seed: int) -> FeatureSet:
        te = neu(seed).test(self.size)
        return FeatureSet(self._f(te.X), te.y, te.paths)


class VectorProvider(FeatureProvider):
    """Precomputed per-image vectors (e.g. CNN embeddings) -> train-fitted scaler (+PCA k) -> view.
    `source` must expose train_val_vectors(seed) and test_vectors(seed)."""

    def __init__(self, source, k: Optional[int], view: str):
        self.source, self.k, self.view = source, k, view
        self.name = f"{source.name}-{'pca' + str(k) if k else 'full'}-{view}"
        self._fit: Dict[int, VectorFeaturizer] = {}

    def describe(self) -> Dict:
        return {"name": self.name, "source": self.source.describe(), "pca_k": self.k, "view": self.view,
                "fit": "train split only"}

    def _featurizer(self, seed, Ftr):
        if seed not in self._fit:
            self._fit[seed] = VectorFeaturizer(k=self.k, random_state=seed).fit(Ftr)
        return self._fit[seed]

    def train_val(self, seed: int):
        (Ftr, ytr, ptr), (Fva, yva, pva) = self.source.train_val_vectors(seed)
        f = self._featurizer(seed, Ftr)
        info = {**f.info(), "view": self.view, "source_dim": int(Ftr.shape[1]),
                "source_load_info": getattr(self.source, "load_info", None)}
        Xva = f.transform(Fva, self.view)
        if self.view == "angle":
            info["val_fraction_outside_0_pi"] = out_of_range_fraction(Xva)
        return FeatureSet(f.transform(Ftr, self.view), ytr, ptr), FeatureSet(Xva, yva, pva), info

    def test(self, seed: int) -> FeatureSet:
        Fte, yte, pte = self.source.test_vectors(seed)
        (Ftr, _, _), _ = self.source.train_val_vectors(seed)
        return FeatureSet(self._featurizer(seed, Ftr).transform(Fte, self.view), yte, pte)
