"""
ML Classification Trainer for NEU Surface Defect Database.

Implements a full reproducible pipeline:
  1. Load all NEU-DET images and extract features
  2. Stratified train/validation/test split (from existing train split)
  3. Train SVM, Random Forest, KNN, Decision Tree
  4. Cross-validation on training portion
  5. Hyperparameter comparison
  6. Save all results to results/models/

No results are hard-coded. All metrics come from actual model runs.
"""

import numpy as np
import json
import csv
import time
import warnings
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import (
    StratifiedShuffleSplit, cross_val_score, GridSearchCV
)
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix
)
from sklearn.pipeline import Pipeline
import joblib

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import (
    TRAIN_IMAGES_PATH, VALIDATION_IMAGES_PATH, DEFECT_CATEGORIES,
    RANDOM_SEED, PROJECT_ROOT
)

warnings.filterwarnings("ignore")

RESULTS_MODELS_PATH = PROJECT_ROOT / "results" / "models"
RESULTS_DATASET_PATH = PROJECT_ROOT / "results" / "dataset"


def ensure_ml_dirs():
    """Create ML results directories."""
    RESULTS_MODELS_PATH.mkdir(parents=True, exist_ok=True)
    (RESULTS_MODELS_PATH / "confusion_matrices").mkdir(parents=True, exist_ok=True)
    (RESULTS_MODELS_PATH / "saved_models").mkdir(parents=True, exist_ok=True)
    RESULTS_DATASET_PATH.mkdir(parents=True, exist_ok=True)


def load_neu_dataset(
    split: str = "train",
    max_per_class: Optional[int] = None,
    feature_size: int = 64,
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Load NEU-DET images and extract HOG-like flat features.

    Args:
        split: 'train' or 'validation'
        max_per_class: Limit images per class (None = all)
        feature_size: Resize to feature_size x feature_size before flattening

    Returns:
        X: Feature matrix (n_samples, n_features)
        y: Integer labels (n_samples,)
        filenames: List of image filenames
    """
    from PIL import Image

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
                img_resized = img.resize((feature_size, feature_size))
                arr = np.array(img_resized, dtype=np.float32).flatten() / 255.0
                X.append(arr)
                y.append(class_idx)
                filenames.append(p.name)
            except Exception as e:
                print(f"  WARNING: Could not load {p}: {e}")

    return np.array(X), np.array(y), filenames


def generate_dataset_summary() -> Dict[str, Any]:
    """
    Generate and save dataset summary statistics.
    Returns summary dict.
    """
    from PIL import Image

    print("Generating dataset summary...")
    summary = {
        "total_images": 0,
        "n_classes": len(DEFECT_CATEGORIES),
        "classes": DEFECT_CATEGORIES,
        "train": {},
        "validation": {},
        "image_type": "grayscale JPEG",
        "original_dimensions": "200x200",
        "generated_at": datetime.now().isoformat(),
    }

    class_dist = []
    for split_name, base_path in [("train", TRAIN_IMAGES_PATH), ("validation", VALIDATION_IMAGES_PATH)]:
        split_total = 0
        split_data = {}
        for category in DEFECT_CATEGORIES:
            cat_dir = base_path / category
            count = len([
                p for p in cat_dir.iterdir()
                if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp")
            ]) if cat_dir.exists() else 0
            split_data[category] = count
            split_total += count
        summary[split_name] = split_data
        summary[f"{split_name}_total"] = split_total
        summary["total_images"] += split_total
        for cat, cnt in split_data.items():
            class_dist.append({"split": split_name, "class": cat, "count": cnt})

    ensure_ml_dirs()

    # Save JSON
    json_path = RESULTS_DATASET_PATH / "dataset_summary.json"
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)

    # Save CSV
    csv_path = RESULTS_DATASET_PATH / "class_distribution.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["split", "class", "count"])
        writer.writeheader()
        writer.writerows(class_dist)

    print(f"  Dataset summary saved to {json_path}")
    return summary


class NEUClassificationTrainer:
    """
    Trains and evaluates ML models on the NEU-DET dataset.
    Implements proper train/val/test split, cross-validation, and hyperparameter search.
    """

    CLASS_NAMES = DEFECT_CATEGORIES
    LABEL_MAP = {i: c for i, c in enumerate(DEFECT_CATEGORIES)}

    def __init__(self, random_seed: int = RANDOM_SEED, feature_size: int = 64):
        self.random_seed = random_seed
        self.feature_size = feature_size
        self.scaler = StandardScaler()
        self.models = {}
        self.results = {}
        ensure_ml_dirs()

    def load_and_split(self, max_per_class: Optional[int] = None):
        """
        Load full dataset and create stratified train/val/test split.

        Strategy:
          - Existing train folder (1440 images) → split into 70% train + 30% test
          - Existing validation folder (360 images) → use as validation set
          - This gives ~1008 train / 360 val / 432 test

        All splits are stratified (equal class representation).
        """
        print("\n" + "=" * 60)
        print("LOADING & SPLITTING NEU-DET DATASET")
        print("=" * 60)

        # Load train split (will be split into train+test)
        print("  Loading train images...")
        X_train_full, y_train_full, _ = load_neu_dataset(
            "train", max_per_class, self.feature_size
        )

        # Load validation as our fixed validation set
        print("  Loading validation images...")
        X_val, y_val, _ = load_neu_dataset(
            "validation", max_per_class, self.feature_size
        )

        # Create test set from train_full using stratified split (30%)
        print("  Creating stratified test split (30% of train folder)...")
        splitter = StratifiedShuffleSplit(
            n_splits=1, test_size=0.30, random_state=self.random_seed
        )
        train_idx, test_idx = next(splitter.split(X_train_full, y_train_full))
        X_train = X_train_full[train_idx]
        y_train = y_train_full[train_idx]
        X_test = X_train_full[test_idx]
        y_test = y_train_full[test_idx]

        # Fit scaler on training data only (no leakage)
        print("  Fitting StandardScaler on training data only...")
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        X_test_scaled = self.scaler.transform(X_test)

        self.X_train = X_train_scaled
        self.y_train = y_train
        self.X_val = X_val_scaled
        self.y_val = y_val
        self.X_test = X_test_scaled
        self.y_test = y_test

        print(f"\n  Split Summary:")
        print(f"    Training:   {len(X_train):4d} samples ({len(X_train)/len(X_train_full)*100:.1f}% of train folder)")
        print(f"    Validation: {len(X_val):4d} samples (validation folder)")
        print(f"    Test:       {len(X_test):4d} samples (30% of train folder)")
        print(f"    Features:   {X_train.shape[1]}")
        print(f"    Classes:    {len(self.CLASS_NAMES)}")

        # Save split info
        split_info = {
            "random_seed": self.random_seed,
            "feature_size": self.feature_size,
            "n_features": int(X_train.shape[1]),
            "train_samples": int(len(X_train)),
            "val_samples": int(len(X_val)),
            "test_samples": int(len(X_test)),
            "n_classes": len(self.CLASS_NAMES),
            "classes": self.CLASS_NAMES,
            "train_class_distribution": {
                self.LABEL_MAP[c]: int(np.sum(y_train == c))
                for c in range(len(self.CLASS_NAMES))
            },
            "val_class_distribution": {
                self.LABEL_MAP[c]: int(np.sum(y_val == c))
                for c in range(len(self.CLASS_NAMES))
            },
            "test_class_distribution": {
                self.LABEL_MAP[c]: int(np.sum(y_test == c))
                for c in range(len(self.CLASS_NAMES))
            },
        }
        with open(RESULTS_MODELS_PATH / "split_info.json", "w") as f:
            json.dump(split_info, f, indent=2)

        return self.X_train, self.y_train, self.X_val, self.y_val, self.X_test, self.y_test

    def _evaluate_model(
        self,
        model,
        model_name: str,
        X_train, y_train, X_val, y_val, X_test, y_test,
        cv_folds: int = 5,
    ) -> Dict[str, Any]:
        """Train and fully evaluate a single model."""
        print(f"\n  [{model_name}]")

        # Training
        t0 = time.perf_counter()
        model.fit(X_train, y_train)
        train_time = time.perf_counter() - t0

        # Predictions
        y_pred_train = model.predict(X_train)
        y_pred_val = model.predict(X_val)

        t1 = time.perf_counter()
        y_pred_test = model.predict(X_test)
        infer_time = (time.perf_counter() - t1) / len(X_test)

        # Accuracy
        train_acc = accuracy_score(y_train, y_pred_train)
        val_acc = accuracy_score(y_val, y_pred_val)
        test_acc = accuracy_score(y_test, y_pred_test)

        # Classification report on test
        report = classification_report(
            y_test, y_pred_test,
            target_names=self.CLASS_NAMES,
            output_dict=True
        )

        # Cross-validation on training data
        print(f"    Running {cv_folds}-fold CV...", end=" ", flush=True)
        cv_scores = cross_val_score(
            model, X_train, y_train, cv=cv_folds,
            scoring="accuracy", n_jobs=-1
        )
        print(f"CV={cv_scores.mean():.4f}±{cv_scores.std():.4f}")

        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred_test)

        result = {
            "model_name": model_name,
            "train_accuracy": float(train_acc),
            "val_accuracy": float(val_acc),
            "test_accuracy": float(test_acc),
            "precision_macro": float(report["macro avg"]["precision"]),
            "recall_macro": float(report["macro avg"]["recall"]),
            "f1_macro": float(report["macro avg"]["f1-score"]),
            "f1_weighted": float(report["weighted avg"]["f1-score"]),
            "cv_mean": float(cv_scores.mean()),
            "cv_std": float(cv_scores.std()),
            "cv_scores": cv_scores.tolist(),
            "training_time_s": float(train_time),
            "inference_time_per_sample_ms": float(infer_time * 1000),
            "confusion_matrix": cm.tolist(),
            "per_class": {
                cls: {
                    "precision": float(report[cls]["precision"]),
                    "recall": float(report[cls]["recall"]),
                    "f1": float(report[cls]["f1-score"]),
                    "support": int(report[cls]["support"]),
                }
                for cls in self.CLASS_NAMES
            },
            "classification_report": report,
            "timestamp": datetime.now().isoformat(),
        }

        print(f"    Train: {train_acc:.4f} | Val: {val_acc:.4f} | Test: {test_acc:.4f} | "
              f"F1: {result['f1_macro']:.4f} | Time: {train_time:.2f}s")

        return result

    def train_all_models(self, cv_folds: int = 5) -> Dict[str, Any]:
        """Train all baseline models and evaluate."""
        print("\n" + "=" * 60)
        print("TRAINING ALL BASELINE MODELS")
        print("=" * 60)

        models_config = {
            "SVM": SVC(
                C=10, kernel="rbf", gamma="scale",
                random_state=self.random_seed, probability=True
            ),
            "Random Forest": RandomForestClassifier(
                n_estimators=200, max_depth=None, min_samples_split=2,
                random_state=self.random_seed, n_jobs=-1
            ),
            "KNN": KNeighborsClassifier(
                n_neighbors=5, metric="euclidean", n_jobs=-1
            ),
            "Decision Tree": DecisionTreeClassifier(
                max_depth=20, min_samples_split=2,
                random_state=self.random_seed
            ),
        }

        all_results = {}
        for name, model in models_config.items():
            result = self._evaluate_model(
                model, name,
                self.X_train, self.y_train,
                self.X_val, self.y_val,
                self.X_test, self.y_test,
                cv_folds=cv_folds,
            )
            all_results[name] = result
            self.models[name] = model

            # Save confusion matrix
            self._save_confusion_matrix(name, result["confusion_matrix"])

        self.results = all_results
        return all_results

    def run_hyperparameter_experiments(self) -> List[Dict]:
        """
        Run controlled hyperparameter comparison experiments.
        Tests multiple configurations for each model.
        """
        print("\n" + "=" * 60)
        print("HYPERPARAMETER COMPARISON EXPERIMENTS")
        print("=" * 60)

        hp_results = []

        # SVM: vary C and kernel
        print("\n  SVM hyperparameters:")
        for C in [0.1, 1, 10, 100]:
            for kernel in ["rbf", "linear"]:
                model = SVC(C=C, kernel=kernel, gamma="scale",
                            random_state=self.random_seed)
                t0 = time.perf_counter()
                model.fit(self.X_train, self.y_train)
                train_time = time.perf_counter() - t0
                val_acc = accuracy_score(self.y_val, model.predict(self.X_val))
                f1 = f1_score(self.y_val, model.predict(self.X_val), average="macro")
                hp_results.append({
                    "model": "SVM", "param": f"C={C}, kernel={kernel}",
                    "C": C, "kernel": kernel, "gamma": "scale",
                    "val_accuracy": round(float(val_acc), 4),
                    "f1_macro": round(float(f1), 4),
                    "train_time_s": round(float(train_time), 4),
                })
                print(f"    C={C}, kernel={kernel}: val_acc={val_acc:.4f}, f1={f1:.4f}")

        # Random Forest: vary n_estimators and max_depth
        print("\n  Random Forest hyperparameters:")
        for n_est in [50, 100, 200]:
            for max_d in [10, 20, None]:
                model = RandomForestClassifier(
                    n_estimators=n_est, max_depth=max_d,
                    random_state=self.random_seed, n_jobs=-1
                )
                t0 = time.perf_counter()
                model.fit(self.X_train, self.y_train)
                train_time = time.perf_counter() - t0
                val_acc = accuracy_score(self.y_val, model.predict(self.X_val))
                f1 = f1_score(self.y_val, model.predict(self.X_val), average="macro")
                hp_results.append({
                    "model": "Random Forest",
                    "param": f"n_est={n_est}, max_d={max_d}",
                    "n_estimators": n_est, "max_depth": str(max_d),
                    "val_accuracy": round(float(val_acc), 4),
                    "f1_macro": round(float(f1), 4),
                    "train_time_s": round(float(train_time), 4),
                })
                print(f"    n_est={n_est}, max_depth={max_d}: val_acc={val_acc:.4f}")

        # KNN: vary k and metric
        print("\n  KNN hyperparameters:")
        for k in [3, 5, 7, 11, 15]:
            for metric in ["euclidean", "manhattan"]:
                model = KNeighborsClassifier(n_neighbors=k, metric=metric, n_jobs=-1)
                t0 = time.perf_counter()
                model.fit(self.X_train, self.y_train)
                train_time = time.perf_counter() - t0
                val_acc = accuracy_score(self.y_val, model.predict(self.X_val))
                f1 = f1_score(self.y_val, model.predict(self.X_val), average="macro")
                hp_results.append({
                    "model": "KNN",
                    "param": f"k={k}, metric={metric}",
                    "k": k, "metric": metric,
                    "val_accuracy": round(float(val_acc), 4),
                    "f1_macro": round(float(f1), 4),
                    "train_time_s": round(float(train_time), 4),
                })
                print(f"    k={k}, metric={metric}: val_acc={val_acc:.4f}")

        # Save — use union of all keys, filling missing with ""
        hp_path = RESULTS_MODELS_PATH / "hyperparameter_results.csv"
        if hp_results:
            all_keys = list(dict.fromkeys(k for row in hp_results for k in row.keys()))
            with open(hp_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
                writer.writeheader()
                for row in hp_results:
                    padded = {k: row.get(k, "") for k in all_keys}
                    writer.writerow(padded)
        print(f"\n  Saved hyperparameter results to {hp_path}")
        return hp_results

    def save_all_results(self):
        """Save all model results to results/models/."""
        if not self.results:
            print("No results to save.")
            return

        print("\n  Saving model results...")
        ensure_ml_dirs()

        # Model comparison CSV
        comparison_rows = []
        for name, r in self.results.items():
            comparison_rows.append({
                "model": name,
                "train_accuracy": r["train_accuracy"],
                "val_accuracy": r["val_accuracy"],
                "test_accuracy": r["test_accuracy"],
                "precision_macro": r["precision_macro"],
                "recall_macro": r["recall_macro"],
                "f1_macro": r["f1_macro"],
                "f1_weighted": r["f1_weighted"],
                "cv_mean": r["cv_mean"],
                "cv_std": r["cv_std"],
                "training_time_s": r["training_time_s"],
                "inference_time_per_sample_ms": r["inference_time_per_sample_ms"],
            })
        csv_path = RESULTS_MODELS_PATH / "model_comparison.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=comparison_rows[0].keys())
            writer.writeheader()
            writer.writerows(comparison_rows)
        print(f"  Saved: {csv_path}")

        # Per-class metrics CSV
        per_class_rows = []
        for name, r in self.results.items():
            for cls_name, metrics in r["per_class"].items():
                per_class_rows.append({
                    "model": name, "class": cls_name,
                    **metrics
                })
        per_class_path = RESULTS_MODELS_PATH / "per_class_metrics.csv"
        with open(per_class_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=per_class_rows[0].keys())
            writer.writeheader()
            writer.writerows(per_class_rows)
        print(f"  Saved: {per_class_path}")

        # Full results JSON
        results_json_path = RESULTS_MODELS_PATH / "all_model_results.json"
        with open(results_json_path, "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"  Saved: {results_json_path}")

        # Save trained models
        for name, model in self.models.items():
            model_path = RESULTS_MODELS_PATH / "saved_models" / f"{name.replace(' ', '_')}.joblib"
            joblib.dump(model, model_path)
        # Save scaler
        joblib.dump(self.scaler, RESULTS_MODELS_PATH / "saved_models" / "scaler.joblib")
        print(f"  Saved trained models to results/models/saved_models/")

    def _save_confusion_matrix(self, model_name: str, cm: list):
        """Save confusion matrix as JSON."""
        cm_path = (RESULTS_MODELS_PATH / "confusion_matrices" /
                   f"{model_name.replace(' ', '_')}_cm.json")
        with open(cm_path, "w") as f:
            json.dump({
                "model": model_name,
                "classes": self.CLASS_NAMES,
                "matrix": cm,
            }, f, indent=2)

    def print_summary(self):
        """Print a summary table of all model results."""
        if not self.results:
            print("No results available.")
            return

        print("\n" + "=" * 80)
        print("MODEL COMPARISON SUMMARY")
        print("=" * 80)
        header = f"{'Model':<20} {'Train':>8} {'Val':>8} {'Test':>8} {'F1':>8} {'CV':>12}"
        print(header)
        print("-" * 80)
        for name, r in self.results.items():
            print(
                f"{name:<20} {r['train_accuracy']:>8.4f} {r['val_accuracy']:>8.4f} "
                f"{r['test_accuracy']:>8.4f} {r['f1_macro']:>8.4f} "
                f"{r['cv_mean']:>6.4f}±{r['cv_std']:.4f}"
            )
        print("=" * 80)


def run_full_ml_pipeline(
    max_per_class: Optional[int] = None,
    feature_size: int = 64,
    cv_folds: int = 5,
    run_hyperparameter: bool = True,
) -> Dict:
    """
    Run the complete ML training pipeline.

    Args:
        max_per_class: Limit images per class (None = all 240 per class)
        feature_size: Image resize for feature extraction
        cv_folds: Number of CV folds
        run_hyperparameter: Whether to run hyperparameter comparison

    Returns:
        Dictionary with all results
    """
    print("\n" + "=" * 70)
    print("Q-IMAGELAB: ML CLASSIFICATION PIPELINE")
    print("=" * 70)

    # Dataset summary
    summary = generate_dataset_summary()

    # Initialize trainer
    trainer = NEUClassificationTrainer(
        random_seed=RANDOM_SEED,
        feature_size=feature_size,
    )

    # Load and split
    trainer.load_and_split(max_per_class=max_per_class)

    # Train all models
    results = trainer.train_all_models(cv_folds=cv_folds)

    # Hyperparameter experiments
    hp_results = []
    if run_hyperparameter:
        hp_results = trainer.run_hyperparameter_experiments()

    # Save everything
    trainer.save_all_results()

    # Print summary
    trainer.print_summary()

    print("\nML Pipeline complete!")
    return {
        "model_results": results,
        "hyperparameter_results": hp_results,
        "dataset_summary": summary,
    }


if __name__ == "__main__":
    run_full_ml_pipeline(max_per_class=None)
