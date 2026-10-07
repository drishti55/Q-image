"""
Central configuration for the Quantum Image Processing research project.

All experimental parameters are defined here to ensure reproducibility.
Do NOT hard-code parameters elsewhere in the codebase.
"""

import os
from pathlib import Path

# =============================================================================
# Project Paths
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DATASET_PATH = PROJECT_ROOT / "NEU-DET"
TRAIN_IMAGES_PATH = DATASET_PATH / "train" / "images"
VALIDATION_IMAGES_PATH = DATASET_PATH / "validation" / "images"

RESULTS_PATH = PROJECT_ROOT / "results"
RESULTS_IMAGES_PATH = RESULTS_PATH / "images"
RESULTS_CIRCUITS_PATH = RESULTS_PATH / "circuits"
RESULTS_TABLES_PATH = RESULTS_PATH / "tables"
RESULTS_EXPERIMENTS_PATH = RESULTS_PATH / "experiments"

DATA_SAMPLE_PATH = PROJECT_ROOT / "data" / "sample"

# =============================================================================
# Reproducibility
# =============================================================================

RANDOM_SEED = 42

# =============================================================================
# Dataset Configuration
# =============================================================================

DEFECT_CATEGORIES = [
    "crazing",
    "inclusion",
    "patches",
    "pitted_surface",
    "rolled-in_scale",
    "scratches",
]

# Number of images to select per category for experiments (None = process all dataset)
IMAGES_PER_CATEGORY = 20

# =============================================================================
# Image Preprocessing
# =============================================================================

# Quantum-compatible image resolutions (width, height)
IMAGE_SIZES = [(2, 2), (4, 4), (8, 8)]

# Default image size for quick experiments
DEFAULT_IMAGE_SIZE = (4, 4)

# Original NEU-DET image dimensions
ORIGINAL_IMAGE_SIZE = (200, 200)

# =============================================================================
# Intensity Precision
# =============================================================================

# Number of bits for intensity quantization
INTENSITY_BITS_OPTIONS = [2, 4, 8]

# Default intensity precision
DEFAULT_INTENSITY_BITS = 8

# =============================================================================
# Quantum Simulation
# =============================================================================

# Simulator backend names
STATEVECTOR_SIMULATOR = "statevector_simulator"
AER_SIMULATOR = "aer_simulator"

# Default simulator
DEFAULT_SIMULATOR = AER_SIMULATOR

# Measurement shot configurations
SHOTS_LIST = [100, 500, 1000, 5000]

# Default number of shots
DEFAULT_SHOTS = 1024

# =============================================================================
# Representations
# =============================================================================

REPRESENTATIONS = ["FRQI", "NEQR"]

# =============================================================================
# Visualization
# =============================================================================

# Figure DPI for saved plots
FIGURE_DPI = 150

# Default colormap for grayscale images
COLORMAP = "gray"

# =============================================================================
# Experiment Tracking
# =============================================================================

EXPERIMENT_CSV_FILENAME = "experiment_results.csv"
EXPERIMENT_JSON_FILENAME = "experiment_results.json"

# =============================================================================
# Helper Functions
# =============================================================================


def ensure_directories():
    """Create all required output directories if they don't exist."""
    directories = [
        RESULTS_PATH,
        RESULTS_IMAGES_PATH,
        RESULTS_CIRCUITS_PATH,
        RESULTS_TABLES_PATH,
        RESULTS_EXPERIMENTS_PATH,
        DATA_SAMPLE_PATH,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def get_category_image_dir(category: str, split: str = "train") -> Path:
    """Get the directory path for a specific defect category."""
    base = TRAIN_IMAGES_PATH if split == "train" else VALIDATION_IMAGES_PATH
    return base / category


def get_image_paths(category: str, split: str = "train", max_images: int = None) -> list:
    """Get sorted list of image paths for a category."""
    img_dir = get_category_image_dir(category, split)
    if not img_dir.exists():
        raise FileNotFoundError(f"Category directory not found: {img_dir}")

    paths = sorted([
        p for p in img_dir.iterdir()
        if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp")
    ])

    if max_images is not None:
        paths = paths[:max_images]

    return paths
