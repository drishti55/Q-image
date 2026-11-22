"""
Protocol V3 feature pipelines. Every learned transform is fitted on the TRAIN split only (per seed).

New compared with V2 (motivated by results/qml_v3/reports/QUANTUM_PERFORMANCE_AUDIT.md):
  * "cdf" view: z = train-fitted StandardScaler(scores);  angle = π · Φ(z)  (Φ = standard normal CDF).
    Smooth, monotone, maps every real value into (0, π) without clipping, and is not dominated by
    training outliers the way MinMax[0, π] is. Views "standard" and "angle" are identical to V2.
  * per-image intensity normalisation ("image" norm): each image's pixels are z-scored with that image's own
    mean / std before the global pipeline (a fixed per-sample function: no information crosses images).
  * TextureSource: non-learned texture descriptors computed per image from the 128×128 preprocessed image
    (the same convert('L') + bilinear resize as V2):
        LBP (uniform)  P/R = 8/1, 16/2, 24/3   -> normalised histograms (10 + 18 + 26 = 54)
        GLCM (32 grey levels after per-image min-max stretch), distances 1/2/4, averaged over 0/45/90/135°:
             contrast, dissimilarity, homogeneity, energy, correlation, ASM            -> 18
        intensity std, Sobel gradient-magnitude mean / std, Laplacian variance           -> 4   (total 76)
    Mean brightness is deliberately excluded (illumination nuisance). No parameter is fitted.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Optional

import numpy as np
from scipy.special import ndtr
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from src.v2 import dataset as ds
from src.v2.features import out_of_range_fraction
from src.v2.paths import v2_root
from src.v2.providers import neu
from src.v2.runner import FeatureProvider, FeatureSet

VIEWS = ("standard", "angle", "cdf")


def per_image_normalize(X: np.ndarray) -> np.ndarray:
    F = X.reshape(len(X), -1).astype(float)
    mu, sd = F.mean(1, keepdims=True), F.std(1, keepdims=True)
    return ((F - mu) / np.where(sd < 1e-9, 1.0, sd)).reshape(X.shape)


@dataclass
class Featurizer:
    """input -> StandardScaler -> optional PCA(k) -> view. Fitted on train only."""
    k: Optional[int] = None
    random_state: int = 0
    fitted_n: int = 0
    _in: StandardScaler = field(default_factory=StandardScaler)
    _pca: Optional[PCA] = None
    _std: StandardScaler = field(default_factory=StandardScaler)
    _ang: MinMaxScaler = field(default_factory=lambda: MinMaxScaler(feature_range=(0.0, np.pi)))

    def fit(self, F: np.ndarray) -> "Featurizer":
        Z = self._in.fit_transform(F)
        if self.k is not None:
            self._pca = PCA(n_components=self.k, svd_solver="full", random_state=self.random_state)
            Z = self._pca.fit_transform(Z)
        self._std.fit(Z)
        self._ang.fit(Z)
        self.fitted_n = len(F)
        return self

    def transform(self, F: np.ndarray, view: str) -> np.ndarray:
        Z = self._in.transform(F)
        if self._pca is not None:
            Z = self._pca.transform(Z)
        if view == "standard":
            return self._std.transform(Z)
        if view == "angle":
            return self._ang.transform(Z)
        if view == "cdf":
            return np.pi * ndtr(self._std.transform(Z))
        raise ValueError(view)

    def info(self) -> Dict:
        d = {"pipeline": "StandardScaler" + (f" -> PCA({self.k})" if self.k else ""), "fitted_on_n_train": self.fitted_n}
        if self._pca is not None:
            d["explained_variance_total"] = float(self._pca.explained_variance_ratio_.sum())
            d["explained_variance_ratio"] = [float(v) for v in self._pca.explained_variance_ratio_]
        return d


class _Provider(FeatureProvider):
    """Generic provider over a per-seed raw-matrix source with train/val/test accessors."""

    def __init__(self, k: Optional[int], view: str):
        assert view in VIEWS
        self.k, self.view = k, view
        self._fit: Dict[int, Featurizer] = {}

    def _raw(self, seed: int, which: str):  # -> (F, y, paths)
        raise NotImplementedError

    def _featurizer(self, seed: int) -> Featurizer:
        if seed not in self._fit:
            F, _, _ = self._raw(seed, "train")
            self._fit[seed] = Featurizer(k=self.k, random_state=seed).fit(F)
        return self._fit[seed]

    def train_val(self, seed: int):
        f = self._featurizer(seed)
        (Ftr, ytr, ptr), (Fva, yva, pva) = self._raw(seed, "train"), self._raw(seed, "val")
        Xtr, Xva = f.transform(Ftr, self.view), f.transform(Fva, self.view)
        info = {**self.describe(), **f.info(), "input_dim": int(Ftr.shape[1])}
        if self.view in ("angle", "cdf"):
            info["val_fraction_outside_0_pi"] = out_of_range_fraction(Xva)
        return FeatureSet(Xtr, ytr, ptr), FeatureSet(Xva, yva, pva), info

    def test(self, seed: int) -> FeatureSet:
        F, y, p = self._raw(seed, "test")
        return FeatureSet(self._featurizer(seed).transform(F, self.view), y, p)


class PixelProvider(_Provider):
    """size×size pixels (optionally per-image normalised) -> scaler -> PCA(k) -> view."""

    def __init__(self, k: int, view: str, size: int = 64, norm: str = "none"):
        super().__init__(k, view)
        self.size, self.norm = size, norm
        self.name = f"pixels{size}{'-imgnorm' if norm == 'image' else ''}-pca{k}-{view}"

    def describe(self) -> Dict:
        return {"name": self.name, "input": f"{self.size}x{self.size} grayscale pixels",
                "per_image_normalisation": self.norm, "pca_k": self.k, "view": self.view, "fit": "train split only"}

    def _raw(self, seed, which):
        d = neu(seed)
        a = getattr(d, which)(self.size)
        X = per_image_normalize(a.X) if self.norm == "image" else a.X
        return X.reshape(len(X), -1), a.y, a.paths


# ── texture descriptors ──
def texture_features(img: np.ndarray) -> np.ndarray:
    """img: (s, s) float in [0, 1]. Returns the 76-d descriptor described in the module docstring."""
    from scipy import ndimage
    from skimage.feature import graycomatrix, graycoprops, local_binary_pattern
    u8 = np.clip(np.round(img * 255), 0, 255).astype(np.uint8)
    feats: List[float] = []
    for P, R in ((8, 1), (16, 2), (24, 3)):
        lbp = local_binary_pattern(u8, P, R, method="uniform")
        h, _ = np.histogram(lbp, bins=np.arange(P + 3), density=True)
        feats += h.tolist()
    lo, hi = img.min(), img.max()
    st = (img - lo) / (hi - lo) if hi - lo > 1e-9 else np.zeros_like(img)
    q = np.clip((st * 32).astype(np.uint8), 0, 31)
    glcm = graycomatrix(q, distances=[1, 2, 4], angles=[0, np.pi / 4, np.pi / 2, 3 * np.pi / 4], levels=32,
                        symmetric=True, normed=True)
    for prop in ("contrast", "dissimilarity", "homogeneity", "energy", "correlation", "ASM"):
        feats += graycoprops(glcm, prop).mean(axis=1).tolist()
    gx, gy = ndimage.sobel(img, 0), ndimage.sobel(img, 1)
    g = np.hypot(gx, gy)
    feats += [float(img.std()), float(g.mean()), float(g.std()), float(ndimage.laplace(img).var())]
    return np.nan_to_num(np.asarray(feats, dtype=float))


TEXTURE_DIM = 76
TEXTURE_SIZE = 128


class TextureSource:
    """Per-image texture descriptors for whole pools, cached under <root>/cache. Locked-test descriptors can only
    be computed inside final_evaluation_stage (the image arrays themselves are locked)."""
    name = "texture-lbp-glcm-76"

    def __init__(self):
        self._mem: Dict[str, Dict[str, np.ndarray]] = {}

    def describe(self) -> Dict:
        return {"name": self.name, "image": f"{TEXTURE_SIZE}x{TEXTURE_SIZE} grayscale (V2 preprocessing)",
                "descriptor": "LBP uniform (8,1)(16,2)(24,3) histograms + GLCM(32 levels, d=1,2,4, 4 angles) "
                              "6 props + std + Sobel mean/std + Laplacian var", "learned": False, "dim": TEXTURE_DIM}

    def _pool(self, seed: int, which: str) -> Dict[str, np.ndarray]:
        d = neu(seed)
        if which == "test":
            a = d.test(TEXTURE_SIZE)  # raises outside the final stage
            tag = "lockedtest"
        else:  # the whole train-folder pool once (identical for every seed)
            pool = sorted(r["rel_path"] for r in d.manifest["records"] if r["role"] == "trainval")
            a = d._arrays(pool, TEXTURE_SIZE, "trainval")
            tag = "trainval"
        key = hashlib.sha256(json.dumps([d.manifest["manifest_id"], sorted(a.paths), self.name]).encode()).hexdigest()[:16]
        mk = f"{tag}-{key}"
        if mk not in self._mem:
            cache = v2_root() / "cache" / f"texture_{tag}_{key}.npz"
            if cache.exists():
                z = np.load(cache, allow_pickle=False)
                F, names = z["F"], z["paths"].tolist()
            else:
                order = np.argsort(a.paths)
                names = [a.paths[i] for i in order]
                F = np.stack([texture_features(a.X[i]) for i in order])
                np.savez_compressed(cache, F=F, paths=np.array(names))
            self._mem[mk] = {n: F[i] for i, n in enumerate(names)}
        return self._mem[mk]

    def vectors(self, seed: int, which: str):
        d = neu(seed)
        paths = d.split[which]
        V = self._pool(seed, which)
        return np.stack([V[p] for p in paths]), np.array([d._by_path[p]["class_idx"] for p in paths]), list(paths)


@lru_cache(maxsize=1)
def texture_source() -> TextureSource:
    return TextureSource()


class TextureProvider(_Provider):
    def __init__(self, k: Optional[int], view: str):
        super().__init__(k, view)
        self.name = f"texture76-{'pca' + str(k) if k else 'full'}-{view}"

    def describe(self) -> Dict:
        return {"name": self.name, "source": texture_source().describe(), "pca_k": self.k, "view": self.view,
                "fit": "train split only"}

    def _raw(self, seed, which):
        return texture_source().vectors(seed, which)


class MobileNetProvider(_Provider):
    """Frozen MobileNetV3-small 576-d features (V2 source, cached) -> scaler -> PCA(k) -> view."""

    def __init__(self, k: Optional[int], view: str):
        super().__init__(k, view)
        self.name = f"mnv3s-frozen-{'pca' + str(k) if k else 'full'}-{view}"

    @staticmethod
    @lru_cache(maxsize=1)
    def _src():
        from src.v2.cnn import FrozenMobileNetV3Source
        return FrozenMobileNetV3Source()

    def describe(self) -> Dict:
        return {"name": self.name, "source": self._src().describe(), "pca_k": self.k, "view": self.view,
                "fit": "train split only"}

    def _raw(self, seed, which):
        s = self._src()
        if which == "test":
            return s.test_vectors(seed)
        tr, va = s.train_val_vectors(seed)
        return tr if which == "train" else va


def _is_locked() -> bool:
    return not ds._final_eval_active()
