"""
Feature Extraction Pipeline for Quantum ML.

Extracts classical features from NEU-DET images and reduces dimensionality
for quantum circuit encoding. PCA is fit on training data only to prevent
data leakage.

Pipeline: Load image → Grayscale → Resize → Flatten → StandardScaler → PCA → MinMax [0, π]
"""

import numpy as np
from pathlib import Path
from typing import Tuple, List, Optional, Dict, Any
from PIL import Image
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.model_selection import StratifiedShuffleSplit
import joblib
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import (
    TRAIN_IMAGES_PATH, VALIDATION_IMAGES_PATH, DEFECT_CATEGORIES, RANDOM_SEED
)


class QMLFeatureExtractor:
    """
    Extracts and reduces features from NEU-DET images for quantum encoding.

    The pipeline:
      1. Load grayscale images, resize to feature_size × feature_size
      2. Flatten to 1D feature vector
      3. StandardScaler (fit on train only)
      4. PCA dimensionality reduction (fit on train only)
      5. MinMaxScaler to [0, π] for quantum angle encoding

    All transformations are fit on training data only. Validation and test
    data are transformed using the fitted objects.
    """

    CLASS_NAMES = DEFECT_CATEGORIES

    def __init__(
        self,
        n_features: int = 8,
        feature_size: int = 64,
        random_seed: int = RANDOM_SEED,
    ):
        """
        Args:
            n_features: Number of PCA components (= number of qubits for quantum kernel)
            feature_size: Image resize dimension (feature_size × feature_size)
            random_seed: For reproducibility
        """
        self.n_features = n_features
        self.feature_size = feature_size
        self.random_seed = random_seed

        self.scaler = StandardScaler()
        self.pca = PCA(n_components=n_features, random_state=random_seed)
        self.minmax = MinMaxScaler(feature_range=(0, np.pi))

        self._is_fitted = False

    def load_images(
        self,
        split: str = "train",
        max_per_class: Optional[int] = None,
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Load NEU-DET images and extract flattened pixel features.

        Args:
            split: 'train' or 'validation'
            max_per_class: Limit images per class (None = all)

        Returns:
            X: Feature matrix (n_samples, feature_size²)
            y: Integer labels (n_samples,)
            filenames: List of image filenames
        """
        base = TRAIN_IMAGES_PATH if split == "train" else VALIDATION_IMAGES_PATH
        X, y, filenames = [], [], []

        for class_idx, category in enumerate(DEFECT_CATEGORIES):
            cat_dir = base / category
            if not cat_dir.exists():
                print(f"  WARNING: {cat_dir} not found, skipping")
                continue

            paths = sorted([
                p for p in cat_dir.iterdir()
                if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp")
            ])
            if max_per_class is not None:
                paths = paths[:max_per_class]

            for p in paths:
                try:
                    img = Image.open(p).convert("L")
                    img_resized = img.resize(
                        (self.feature_size, self.feature_size)
                    )
                    arr = np.array(img_resized, dtype=np.float32).flatten() / 255.0
                    X.append(arr)
                    y.append(class_idx)
                    filenames.append(p.name)
                except Exception as e:
                    print(f"  WARNING: Could not load {p}: {e}")

        return np.array(X), np.array(y), filenames

    def prepare_splits(
        self,
        max_per_class: Optional[int] = None,
        test_size: float = 0.30,
    ) -> Dict[str, Any]:
        """
        Load dataset and create train/val/test splits with fitted transformations.

        Strategy (matches existing ML pipeline):
          - Train folder → 70% train + 30% test (stratified)
          - Validation folder → validation set

        All transformations (scaler, PCA, minmax) are fit on training data only.

        Args:
            max_per_class: Limit images per class
            test_size: Fraction of train folder to use as test

        Returns:
            Dictionary with X_train, y_train, X_val, y_val, X_test, y_test,
            and metadata about the splits and transformations.
        """
        print(f"  Loading train images (feature_size={self.feature_size})...")
        X_train_full, y_train_full, train_files = self.load_images(
            "train", max_per_class
        )

        print(f"  Loading validation images...")
        X_val_raw, y_val, val_files = self.load_images(
            "validation", max_per_class
        )

        # Stratified train/test split from train folder
        print(f"  Creating stratified test split ({test_size*100:.0f}% of train folder)...")
        splitter = StratifiedShuffleSplit(
            n_splits=1, test_size=test_size, random_state=self.random_seed
        )
        train_idx, test_idx = next(splitter.split(X_train_full, y_train_full))
        X_train_raw = X_train_full[train_idx]
        y_train = y_train_full[train_idx]
        X_test_raw = X_train_full[test_idx]
        y_test = y_train_full[test_idx]

        # Fit transformations on training data only
        print(f"  Fitting StandardScaler on training data...")
        X_train_scaled = self.scaler.fit_transform(X_train_raw)

        print(f"  Fitting PCA (n_components={self.n_features}) on training data...")
        X_train_pca = self.pca.fit_transform(X_train_scaled)

        print(f"  Fitting MinMaxScaler [0, π] on training data...")
        X_train = self.minmax.fit_transform(X_train_pca)

        # Transform val and test (no fitting)
        X_val_scaled = self.scaler.transform(X_val_raw)
        X_val_pca = self.pca.transform(X_val_scaled)
        X_val = self.minmax.transform(X_val_pca)

        X_test_scaled = self.scaler.transform(X_test_raw)
        X_test_pca = self.pca.transform(X_test_scaled)
        X_test = self.minmax.transform(X_test_pca)

        self._is_fitted = True

        explained_variance = float(np.sum(self.pca.explained_variance_ratio_))

        print(f"\n  QML Feature Extraction Summary:")
        print(f"    Raw features:         {X_train_raw.shape[1]} (flattened {self.feature_size}×{self.feature_size})")
        print(f"    PCA components:       {self.n_features}")
        print(f"    Explained variance:   {explained_variance:.4f}")
        print(f"    Output range:         [0, π] (for quantum angle encoding)")
        print(f"    Train samples:        {len(X_train)}")
        print(f"    Validation samples:   {len(X_val)}")
        print(f"    Test samples:         {len(X_test)}")

        metadata = {
            "feature_size": self.feature_size,
            "raw_feature_dim": int(X_train_raw.shape[1]),
            "n_pca_components": self.n_features,
            "explained_variance_ratio": explained_variance,
            "output_range": "[0, π]",
            "train_samples": int(len(X_train)),
            "val_samples": int(len(X_val)),
            "test_samples": int(len(X_test)),
            "n_classes": len(DEFECT_CATEGORIES),
            "classes": DEFECT_CATEGORIES,
            "random_seed": self.random_seed,
            "test_split_ratio": test_size,
        }

        return {
            "X_train": X_train,
            "y_train": y_train,
            "X_val": X_val,
            "y_val": y_val,
            "X_test": X_test,
            "y_test": y_test,
            "metadata": metadata,
        }

    def transform(self, X_raw: np.ndarray) -> np.ndarray:
        """
        Transform raw features using fitted pipeline.

        Args:
            X_raw: Raw flattened pixel features (n_samples, feature_size²)

        Returns:
            Transformed features (n_samples, n_features) in [0, π]
        """
        if not self._is_fitted:
            raise RuntimeError("Feature extractor not fitted. Call prepare_splits first.")
        X_scaled = self.scaler.transform(X_raw)
        X_pca = self.pca.transform(X_scaled)
        X_transformed = self.minmax.transform(X_pca)
        return X_transformed

    def save(self, save_dir: Path):
        """Save fitted transformers to disk."""
        save_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.scaler, save_dir / "qml_scaler.joblib")
        joblib.dump(self.pca, save_dir / "qml_pca.joblib")
        joblib.dump(self.minmax, save_dir / "qml_minmax.joblib")
        # Save config
        config = {
            "n_features": self.n_features,
            "feature_size": self.feature_size,
            "random_seed": self.random_seed,
        }
        with open(save_dir / "qml_feature_config.json", "w") as f:
            json.dump(config, f, indent=2)

    def load(self, save_dir: Path):
        """Load fitted transformers from disk."""
        self.scaler = joblib.load(save_dir / "qml_scaler.joblib")
        self.pca = joblib.load(save_dir / "qml_pca.joblib")
        self.minmax = joblib.load(save_dir / "qml_minmax.joblib")
        self._is_fitted = True
