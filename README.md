# Q-ImageLab
### Interactive Quantum Image Processing & NEU Surface Defect Analytics Dashboard

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![Qiskit](https://img.shields.io/badge/Qiskit-2.5-purple)](https://qiskit.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.63-red)](https://streamlit.io)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.9-orange)](https://scikit-learn.org)

---

## Overview

Q-ImageLab is a complete interactive analytics platform combining:

- **ML Classification** of NEU Surface Defect images (SVM, RF, KNN, Decision Tree)
- **Quantum Image Encoding** (FRQI and NEQR) using Qiskit Aer simulation
- **Interactive Dashboard** with 8 pages connecting dataset → ML → quantum analysis

---

## Dataset — NEU Surface Defect Database

| Split | Images | Per Class |
|-------|--------|-----------|
| Train | 1,440 | 240 |
| Validation | 360 | 60 |
| **Total** | **1,800** | **300** |

Six defect categories: **Crazing**, **Inclusion**, **Patches**, **Pitted Surface**, **Rolled-in Scale**, **Scratches**

All images are 200×200 grayscale JPEGs.

---

## ML Results (actual experimental results)

| Model | Train Acc | Val Acc | Test Acc | F1 Macro | CV Score |
|-------|----------:|--------:|----------:|---------:|----------:|
| **SVM** | 0.9395 | **0.6500** | **0.7662** | **0.7647** | 0.8105±0.0138 |
| Random Forest | 1.0000 | 0.6083 | 0.7060 | 0.7056 | 0.7620±0.0377 |
| KNN | 0.5893 | 0.4222 | 0.4977 | 0.4434 | 0.5020±0.0249 |
| Decision Tree | 1.0000 | 0.4111 | 0.5069 | 0.5054 | 0.5318±0.0362 |

- SVM (C=10, RBF kernel) achieves best test accuracy: **76.62%**
- Features: 64×64 pixel flattening (4096 features) with StandardScaler

---

## Quantum Processing

Two quantum image representations implemented with Qiskit:

### FRQI — Flexible Representation of Quantum Images
```
|I⟩ = (1/√N) Σᵢ (cos(θᵢ)|0⟩ + sin(θᵢ)|1⟩) ⊗ |i⟩
```
- **n + 1 qubits** (n position + 1 color qubit)
- Angle encoding via multi-controlled Ry gates
- Reconstruction from probability estimation

### NEQR — Novel Enhanced Quantum Representation
```
|I⟩ = (1/√N) Σᵢ |Cᵢ⟩ ⊗ |i⟩
```
- **n + q qubits** (n position + q intensity qubits)
- Binary encoding via multi-controlled X gates
- Exact reconstruction via majority vote

---

## Dashboard Pages

```
Q-ImageLab (http://localhost:8501)
│
├── 🏠 Home               — Overview KPIs for dataset, ML, and quantum
├── 🗂️ Dataset Explorer   — Class distribution, sample images, intensity analysis
├── 🤖 Model Analytics    — Comparison table, CV results, per-class metrics
├── 🧩 Confusion Matrix   — Interactive raw/normalized confusion matrices
├── ⚛️ Quantum Lab        — Interactive FRQI/NEQR experiment runner
├── 🔬 Circuit Analyzer   — Gate breakdown, resource scaling, circuit diagrams
├── 🖼️ Reconstruction     — Quality distributions and defect category analysis
├── ⚖️ FRQI vs NEQR       — Side-by-side comparison with live experiments
└── 📋 Experiment Results — Filterable table, scatter plots, CSV export
```

---

## Project Structure

```
QIP/
├── NEU-DET/                    # Dataset (1800 images, 6 classes)
│   ├── train/images/
│   └── validation/images/
│
├── src/                        # Core modules
│   ├── frqi/encoder.py         # FRQI quantum encoding
│   ├── neqr/encoder.py         # NEQR quantum encoding
│   ├── preprocessing/          # Image loading, resize, normalize
│   ├── simulation/             # Qiskit Aer statevector + shots
│   ├── reconstruction/         # FRQI arctan2, NEQR majority vote
│   ├── metrics/                # MSE, PSNR, SSIM, ExperimentResult
│   ├── experiments/            # Experiment runner (A-D + NEU-DET)
│   ├── visualization/          # Matplotlib research plots
│   └── ml/                     # NEW: ML classification pipeline
│       └── trainer.py
│
├── results/
│   ├── experiments/            # Quantum experiment CSVs (843KB+)
│   ├── models/                 # ML results: comparison, per-class, CM, HP
│   │   ├── model_comparison.csv
│   │   ├── per_class_metrics.csv
│   │   ├── confusion_matrices/
│   │   ├── hyperparameter_results.csv
│   │   └── saved_models/       # joblib-saved trained models
│   └── dataset/                # Dataset summary JSON
│
├── app/
│   ├── dashboard.py            # Main entry point (Home page)
│   └── pages/                  # 8 Streamlit pages
│
├── config/settings.py          # All configuration
├── main.py                     # CLI: demo / experiment / all / dashboard
└── requirements.txt
```

---

## Setup

```bash
pip install -r requirements.txt
```

## Usage

### Start Dashboard
```bash
streamlit run app/dashboard.py
```

### Run ML Pipeline (generates ML results)
```bash
python3 -c "from src.ml.trainer import run_full_ml_pipeline; run_full_ml_pipeline()"
```

### Run Quantum Experiments
```bash
python main.py demo --size 4 --bits 8 --shots 1000 --sv
python main.py experiment --type neu
python main.py all
```

---

## Data Integrity

- All ML metrics from actual model training — no hard-coded values
- All quantum metrics from Qiskit Aer simulation — no fabricated results
- Strict train/val/test separation — test set never seen during training or tuning
- StandardScaler fit on training data only — no leakage to val/test
- Fixed random seed (42) throughout — fully reproducible
- Stratified splits — all 6 classes equally represented in every split
