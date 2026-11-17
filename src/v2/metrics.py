"""Classification metrics for Protocol V2 (always computed over all six labels)."""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support,
)

from .dataset import CLASSES

LABELS = list(range(len(CLASSES)))


def classification_metrics(y_true: Sequence[int], y_pred: Sequence[int]) -> Dict:
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=LABELS, zero_division=0)
    pm, rm, fm, _ = precision_recall_fscore_support(y_true, y_pred, labels=LABELS, average="macro",
                                                    zero_division=0)
    fw = f1_score(y_true, y_pred, labels=LABELS, average="weighted", zero_division=0)
    return {
        "n": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(pm),
        "recall_macro": float(rm),
        "f1_macro": float(fm),
        "f1_weighted": float(fw),
        "per_class": {
            CLASSES[i]: {"precision": float(p[i]), "recall": float(r[i]), "f1": float(f[i]),
                         "support": int(s[i])}
            for i in LABELS
        },
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=LABELS).tolist(),
        "labels": CLASSES,
    }


def bootstrap_ci(y_true: Sequence[int], y_pred: Sequence[int], n_boot: int = 2000, seed: int = 0,
                 alpha: float = 0.05) -> Dict:
    """Percentile bootstrap CIs (resampling test images) for accuracy and macro-F1."""
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    rng = np.random.default_rng(seed)
    n = len(y_true)
    accs, f1s = np.empty(n_boot), np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        accs[b] = np.mean(y_true[idx] == y_pred[idx])
        f1s[b] = f1_score(y_true[idx], y_pred[idx], labels=LABELS, average="macro", zero_division=0)
    lo, hi = 100 * alpha / 2, 100 * (1 - alpha / 2)
    return {
        "method": f"percentile bootstrap over test images, n_boot={n_boot}, seed={seed}",
        "accuracy": [float(np.percentile(accs, lo)), float(np.percentile(accs, hi))],
        "f1_macro": [float(np.percentile(f1s, lo)), float(np.percentile(f1s, hi))],
        "level": 1 - alpha,
    }


def cross_entropy(probs: np.ndarray, y: Sequence[int]) -> float:
    y = np.asarray(y, dtype=int)
    return float(-np.mean(np.log(np.clip(probs[np.arange(len(y)), y], 1e-12, 1.0))))


def summarize_seeds(values: List[float]) -> Dict[str, Optional[float]]:
    v = np.asarray([x for x in values if x is not None], dtype=float)
    if len(v) == 0:
        return {"mean": None, "std": None, "n": 0}
    return {"mean": float(v.mean()), "std": float(v.std(ddof=1)) if len(v) > 1 else 0.0, "n": int(len(v))}
