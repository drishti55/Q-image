"""
CNN components for Protocol V2 (CPU, PyTorch).

SmallCNN (E7-cnn): trained from scratch on 128×128 grayscale images.
  Augmentation (TRAIN batches only): random horizontal flip, random vertical flip (both p=0.5).
  Rotations/crops/colour jitter are not used — flips preserve defect texture and class identity.
  Early stopping: on internal-validation loss (patience), best-val-loss weights restored.

FrozenMobileNetV3 (E7-mnv3): torchvision mobilenet_v3_small, IMAGENET1K_V1 weights, all
  parameters frozen, eval mode. Features = global-average-pooled output of `features` (576-d).
  Preprocessing = the weights' own transforms: original 200×200 image -> RGB (gray replicated)
  -> resize 256 (bilinear) -> centre crop 224 -> ImageNet mean/std normalisation.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from PIL import Image

from . import dataset as ds
from .paths import v2_root

TORCH_THREADS = 4


def _set_determinism(seed: int):
    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.set_num_threads(TORCH_THREADS)
    torch.use_deterministic_algorithms(True)


class SmallCNNNet(nn.Module):
    def __init__(self, width: int = 16, n_classes: int = 6, dropout: float = 0.3):
        super().__init__()
        c = [1, width, 2 * width, 4 * width, 8 * width]
        layers = []
        for i in range(4):
            layers += [nn.Conv2d(c[i], c[i + 1], 3, padding=1), nn.BatchNorm2d(c[i + 1]), nn.ReLU(),
                       nn.MaxPool2d(2)]
        self.features = nn.Sequential(*layers)
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.head = nn.Sequential(nn.Dropout(dropout), nn.Linear(c[-1], n_classes))

    def embed(self, x):
        return self.pool(self.features(x)).flatten(1)

    def forward(self, x):
        return self.head(self.embed(x))


class SmallCNN:
    """Runner-compatible estimator. Inputs: (n, s, s) float arrays in [0, 1]."""

    def __init__(self, params: Dict, seed: int):
        self.params = {"width": 16, "lr": 1e-3, "weight_decay": 1e-4, "batch_size": 32,
                       "max_epochs": 60, "patience": 10, **params}
        self.seed = seed
        self.state = None
        self.history: List[Dict] = []

    def _net(self):
        return SmallCNNNet(width=self.params["width"])

    @staticmethod
    def _t(X):
        return torch.from_numpy(((np.asarray(X, dtype=np.float32) - 0.5) / 0.25)[:, None])

    def fit(self, X, y, Xv, yv):
        _set_determinism(self.seed)
        p = self.params
        net = self._net()
        opt = torch.optim.Adam(net.parameters(), lr=p["lr"], weight_decay=p["weight_decay"])
        lossf = nn.CrossEntropyLoss()
        Xt, yt = self._t(X), torch.from_numpy(np.asarray(y, dtype=np.int64))
        Xvt, yvt = self._t(Xv), torch.from_numpy(np.asarray(yv, dtype=np.int64))
        g = torch.Generator().manual_seed(self.seed)
        best, best_state, bad = np.inf, None, 0
        self.history = []
        for ep in range(1, p["max_epochs"] + 1):
            t0 = time.perf_counter()
            net.train()
            perm = torch.randperm(len(Xt), generator=g)
            tl, tc = 0.0, 0
            for i in range(0, len(Xt), p["batch_size"]):
                idx = perm[i:i + p["batch_size"]]
                xb, yb = Xt[idx].clone(), yt[idx]
                hf = torch.rand(len(xb), generator=g) < 0.5
                vf = torch.rand(len(xb), generator=g) < 0.5
                xb[hf] = xb[hf].flip(-1)
                xb[vf] = xb[vf].flip(-2)
                opt.zero_grad()
                out = net(xb)
                loss = lossf(out, yb)
                loss.backward()
                opt.step()
                tl += loss.item() * len(xb)
                tc += (out.argmax(1) == yb).sum().item()
            vl, va = self._eval(net, Xvt, yvt, lossf)
            self.history.append({"epoch": ep, "train_loss": tl / len(Xt), "train_acc": tc / len(Xt),
                                 "val_loss": vl, "val_acc": va, "epoch_time_s": time.perf_counter() - t0})
            if vl < best - 1e-4:
                best, bad = vl, 0
                best_state = {k: v.detach().clone() for k, v in net.state_dict().items()}
                self.best_epoch = ep
            else:
                bad += 1
                if bad >= p["patience"]:
                    break
        self.state = best_state
        return {"training_log": {"history": self.history, "best_epoch": self.best_epoch,
                                 "stopped_epoch": self.history[-1]["epoch"],
                                 "early_stopping": f"val_loss, patience={p['patience']}, best weights restored",
                                 "augmentation": "train only: random hflip p=0.5, random vflip p=0.5",
                                 "optimizer": {"name": "Adam", "lr": p["lr"], "weight_decay": p["weight_decay"],
                                               "batch_size": p["batch_size"]},
                                 "torch_threads": TORCH_THREADS, "deterministic_algorithms": True}}

    @staticmethod
    def _eval(net, X, y, lossf):
        net.eval()
        with torch.no_grad():
            out = torch.cat([net(X[i:i + 256]) for i in range(0, len(X), 256)])
            return lossf(out, y).item(), (out.argmax(1) == y).float().mean().item()

    def _loaded(self):
        net = self._net()
        net.load_state_dict(self.state)
        return net.eval()

    def predict_proba(self, X):
        net = self._loaded()
        with torch.no_grad():
            Xt = self._t(X)
            return torch.cat([net(Xt[i:i + 256]).softmax(1) for i in range(0, len(Xt), 256)]).numpy()

    def predict(self, X):
        return self.predict_proba(X).argmax(1)

    def embed(self, X):
        net = self._loaded()
        with torch.no_grad():
            Xt = self._t(X)
            return torch.cat([net.embed(Xt[i:i + 256]) for i in range(0, len(Xt), 256)]).numpy()

    def diagnostics(self):
        return {"n_parameters": int(sum(p.numel() for p in self._net().parameters())),
                "best_epoch": getattr(self, "best_epoch", None)}


# ─── frozen MobileNetV3 features ────────────────────────────────────────────
class FrozenMobileNetV3Source:
    name = "mnv3s-frozen"

    def __init__(self):
        from torchvision.models import MobileNet_V3_Small_Weights
        self.weights = MobileNet_V3_Small_Weights.IMAGENET1K_V1
        self.weight_id = str(self.weights)
        self._model = None
        self.load_info: Dict = {}
        self._vec: Dict[str, Tuple[np.ndarray, List[str]]] = {}

    def describe(self) -> Dict:
        return {"name": self.name, "architecture": "torchvision mobilenet_v3_small",
                "weights": self.weight_id, "weights_url": self.weights.url, "frozen": True,
                "feature": "global average pool of model.features (576-d)",
                "preprocessing": "PIL convert('RGB') of 200x200 gray image -> weights.transforms(): resize 256 "
                                 "bilinear, centre-crop 224, ImageNet mean/std"}

    def model(self):
        if self._model is None:
            from torchvision.models import mobilenet_v3_small
            ckpt = Path(torch.hub.get_dir()) / "checkpoints" / Path(self.weights.url).name
            cached = ckpt.exists()
            m = mobilenet_v3_small(weights=self.weights).eval()
            for p in m.parameters():
                p.requires_grad_(False)
            self.load_info = {"pretrained_loaded": True, "loaded_from_cache": cached,
                              "checkpoint_path": str(ckpt),
                              "checkpoint_sha256": hashlib.sha256(ckpt.read_bytes()).hexdigest() if ckpt.exists() else None,
                              "n_parameters": int(sum(p.numel() for p in m.parameters()))}
            self._model = m
        return self._model

    def _features(self, paths: List[str], root: Path) -> np.ndarray:
        m = self.model()
        tf = self.weights.transforms()
        torch.set_num_threads(TORCH_THREADS)
        out = []
        with torch.no_grad():
            for i in range(0, len(paths), 64):
                batch = []
                for p in paths[i:i + 64]:
                    with Image.open(root / p) as im:
                        batch.append(tf(im.convert("L").convert("RGB")))
                f = m.features(torch.stack(batch))
                out.append(f.mean(dim=(2, 3)).numpy())
        return np.concatenate(out)

    def _pool(self, tag: str, pool: List[str], data: ds.NEUData) -> Dict[str, np.ndarray]:
        """Features for a whole pool (all train-folder images, or all locked-test images), cached
        once per (manifest, weights, pool)."""
        sp = sorted(pool)
        key = hashlib.sha256(json.dumps([data.manifest["manifest_id"], self.weight_id, sp]).encode()).hexdigest()[:16]
        if (tag, key) in self._vec:
            return self._vec[(tag, key)]
        cache = v2_root() / "cache" / f"mnv3_{tag}_{key}.npz"
        self.model()  # loads weights + records load_info
        if cache.exists():
            z = np.load(cache, allow_pickle=False)
            F, names = z["F"], z["paths"].tolist()
        else:
            F, names = self._features(sp, data.root), sp
            np.savez_compressed(cache, F=F, paths=np.array(sp))
        d = {n: F[i] for i, n in enumerate(names)}
        self._vec[(tag, key)] = d
        return d

    def train_val_vectors(self, seed: int):
        from .providers import neu
        d = neu(seed)
        pool = [r["rel_path"] for r in d.manifest["records"] if r["role"] == "trainval"]
        V = self._pool("trainval", pool, d)
        out = []
        for which in ("train", "val"):
            ps = d.split[which]
            out.append((np.stack([V[p] for p in ps]), np.array([d._by_path[p]["class_idx"] for p in ps]), ps))
        return out[0], out[1]

    def test_vectors(self, seed: int):
        from .providers import neu
        if not ds._final_eval_active():
            raise ds.TestSetLockedError("MobileNet test features may only be computed in the final stage.")
        d = neu(seed)
        te = d.split["test"]
        V = self._pool("lockedtest", te, d)
        return np.stack([V[p] for p in te]), np.array([d._by_path[p]["class_idx"] for p in te]), te
