# Q-ImageLab
### Beyond Qubit Count: Comparing FRQI and NEQR Under Practical Constraints

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![Qiskit](https://img.shields.io/badge/Qiskit-2.5-purple)](https://qiskit.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.103+-teal)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2+-blue)](https://react.dev)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.9-orange)](https://scikit-learn.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📄 Paper

> **Beyond Qubit Count: Comparing FRQI and NEQR Under Practical Constraints**
>
> This repository contains the complete source code, datasets, experiments, and interactive dashboard accompanying our research paper on empirical comparison of FRQI and NEQR quantum image representations.

**Key Finding:** While FRQI is qubit-efficient (n+1 qubits), NEQR is overwhelmingly superior for practical implementations — offering drastically shallower circuits, fewer gates, and deterministic noise-resilient readout at the cost of linear auxiliary qubits.

---

## Overview

Q-ImageLab is a comprehensive quantum image processing research platform that includes:

- **Quantum Image Encoding** — FRQI and NEQR implementations using Qiskit Aer simulation
- **ML Classification** — SVM, Random Forest, KNN, and Decision Tree on the NEU Surface Defect Database
- **Interactive Dashboard** — Full-stack React/Vite + FastAPI analytics platform
- **Reproducible Experiments** — Parameterized benchmarks across resolution, bit-depth, shot count, and image complexity

---

## Quantum Representations

### FRQI — Flexible Representation of Quantum Images
$$|I(\theta)\rangle = \frac{1}{2^n} \sum_{i=0}^{2^{2n}-1} (\cos\theta_i |0\rangle + \sin\theta_i |1\rangle) \otimes |i\rangle$$
- **n + 1 qubits** (n position + 1 color qubit)
- Angle encoding via multi-controlled Ry gates
- Probabilistic reconstruction from measurement statistics

### NEQR — Novel Enhanced Quantum Representation
$$|I\rangle = \frac{1}{2^n} \sum_{i=0}^{2^{2n}-1} |C_i\rangle \otimes |i\rangle$$
- **n + q qubits** (n position + q intensity qubits)
- Binary encoding via multi-controlled X gates
- Exact deterministic reconstruction via majority vote

---

## Key Results

### Quantum Encoding Comparison (4×4, 8-bit)

| Metric | FRQI | NEQR |
|--------|-----:|-----:|
| Qubits | 5 | 12 |
| Gates | 1,092 | 128 |
| MSE (100 shots) | 0.032 | **0.00** |
| PSNR (100 shots) | 14.89 dB | **∞** |
| MSE (5000 shots) | 0.0003 | **0.00** |

### ML Classification on NEU-DET

| Model | Test Acc | F1 Macro | CV Score |
|-------|----------:|---------:|----------:|
| **SVM (RBF, C=10)** | **76.62%** | **0.7647** | 0.8105±0.0138 |
| Random Forest | 70.60% | 0.7056 | 0.7620±0.0377 |
| Decision Tree | 50.69% | 0.5054 | 0.5318±0.0362 |
| KNN | 49.77% | 0.4434 | 0.5020±0.0249 |

---

## Dataset — NEU Surface Defect Database

| Split | Images | Per Class |
|-------|--------:|----------:|
| Train | 1,440 | 240 |
| Validation | 360 | 60 |
| **Total** | **1,800** | **300** |

Six defect categories: **Crazing**, **Inclusion**, **Patches**, **Pitted Surface**, **Rolled-in Scale**, **Scratches**

All images are 200×200 grayscale JPEGs.

---

## Dashboard

```
Q-ImageLab (http://localhost:5173 → API at http://localhost:8000)
│
├── 🏠 Home               — Overview KPIs for dataset, ML, and quantum
├── 🗂️ Dataset Explorer   — Class distribution, sample images, intensity analysis
├── 🤖 Model Analytics    — Comparison table, CV results, per-class metrics
├── 🧩 Confusion Matrix   — Interactive raw/normalized confusion matrices
├── ⚛️ Quantum Lab        — Interactive FRQI/NEQR experiment runner
├── 🔬 Circuit Analyzer   — Gate breakdown, resource scaling, circuit diagrams
├── 🖼️ Reconstruction     — Quality distributions and defect category analysis
├── 📋 Experiment Results — Filterable table, scatter plots
└── ⚖️ Quantum Compare    — Direct FRQI vs NEQR side-by-side analysis
```

---

## Project Structure

```
QIP/
├── paper/                      # Research paper manuscript
├── NEU-DET/                    # Dataset (1800 images, 6 classes)
├── src/                        # Core Python modules
│   ├── frqi/encoder.py         # FRQI quantum encoding
│   ├── neqr/encoder.py         # NEQR quantum encoding
│   ├── preprocessing/          # Image loading, resize, normalize
│   ├── simulation/             # Qiskit Aer statevector + shots
│   ├── reconstruction/         # FRQI arctan2, NEQR majority vote
│   ├── metrics/                # MSE, PSNR, SSIM, ExperimentResult
│   ├── experiments/            # Experiment runner (A-D + NEU-DET)
│   ├── visualization/          # Matplotlib research plots
│   ├── ml/                     # ML classification pipeline
│   └── qml/                    # Quantum ML modules
│
├── research_paper_visuals/     # Publication-ready figures and tables
├── results/                    # Dataset JSONs, ML results, and plots
├── frontend/                   # React + Vite frontend app
│   ├── src/pages/              # React page components
│   └── vite.config.ts          # Vite config with API proxy
│
├── tests/                      # Test suite
├── api_main.py                 # FastAPI application server
├── config/settings.py          # Backend configuration
├── main.py                     # CLI: demo / experiment / all
└── requirements.txt            # Python dependencies
```

---

## Setup & Usage

### 1. Backend (FastAPI)
```bash
# Install dependencies
pip install -r requirements.txt

# Start API server on port 8000
python api_main.py
```

### 2. Frontend (React/Vite)
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### 3. CLI — Quantum Experiments
```bash
# Run a demo experiment
python main.py demo --size 4 --bits 8 --shots 1000 --sv

# Run all experiments
python run_all_experiments.py
```

### 4. ML Pipeline
```bash
python3 -c "from src.ml.trainer import run_full_ml_pipeline; run_full_ml_pipeline()"
```

---

## Reproducibility

- All ML metrics from actual model training — no hard-coded values
- All quantum metrics from Qiskit Aer simulation — no fabricated results
- Strict train/val/test separation — test set never seen during training or tuning
- StandardScaler fit on training data only — no data leakage
- Fixed random seed (42) throughout — fully reproducible
- Stratified splits — all 6 classes equally represented in every split

---

## References

1. P. Q. Le, F. Dong, and K. Hirota, "A flexible representation of quantum images for complex background," *Quantum Information Processing*, 2011.
2. Y. Zhang, K. Lu, and Y. Gao, "NEQR: A novel enhanced quantum representation of digital images," *Quantum Information Processing*, 2013.
3. NEU Surface Defect Database, Northeastern University.
