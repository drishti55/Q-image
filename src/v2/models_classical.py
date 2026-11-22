"""Classical estimators (runner protocol: fit / predict / [predict_proba] / diagnostics)."""
from __future__ import annotations

from typing import Dict

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC


class RBFSVM:
    """sklearn SVC(kernel='rbf'). No probability calibration (it would add internal CV randomness)."""

    def __init__(self, params: Dict, seed: int):
        self.params = params
        self.m = SVC(kernel="rbf", C=params["C"], gamma=params["gamma"], random_state=seed)

    def fit(self, X, y, Xv=None, yv=None):
        self.m.fit(X, y)
        return {}

    def predict(self, X):
        return self.m.predict(X)

    def diagnostics(self):
        return {"n_support_vectors": int(self.m.n_support_.sum()),
                "support_per_class": self.m.n_support_.tolist()}


class LogReg:
    """Multinomial logistic regression (lbfgs)."""

    def __init__(self, params: Dict, seed: int):
        self.params = params
        self.m = LogisticRegression(C=params["C"], max_iter=5000, random_state=seed)

    def fit(self, X, y, Xv=None, yv=None):
        self.m.fit(X, y)
        return {}

    def predict(self, X):
        return self.m.predict(X)

    def predict_proba(self, X):
        return self.m.predict_proba(X)

    def diagnostics(self):
        return {"n_iter": int(np.max(self.m.n_iter_))}


SVM_GRID = [{"C": C, "gamma": g} for C in (0.1, 1.0, 10.0, 100.0) for g in (0.03, 0.1, 0.3, 1.0)]
LOGREG_GRID = [{"C": C} for C in (0.001, 0.01, 0.1, 1.0, 10.0, 100.0)]
