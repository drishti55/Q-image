# Q-ImageLab
### Interactive Quantum Image Processing & NEU Surface Defect Analytics Dashboard

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.103+-teal)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2+-blue)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-4.4+-purple)](https://vitejs.dev/)
[![Qiskit](https://img.shields.io/badge/Qiskit-2.5-purple)](https://qiskit.org)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.9-orange)](https://scikit-learn.org)

---

## Overview

Q-ImageLab is a complete interactive analytics platform combining:

- **ML Classification** of NEU Surface Defect images (SVM, RF, KNN, Decision Tree)
- **Quantum Image Encoding** (FRQI and NEQR) using Qiskit Aer simulation
- **Interactive Dashboard** with a fully decoupled **React/Vite Frontend** and **FastAPI Backend**

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

## ML Results

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
Q-ImageLab (http://localhost:5173 -> API at http://localhost:8000)
│
├── 🏠 Home               — Overview KPIs for dataset, ML, and quantum
├── 🗂️ Dataset Explorer   — Class distribution, sample images, intensity analysis
├── 🤖 Model Analytics    — Comparison table, CV results, per-class metrics
├── 🧩 Confusion Matrix   — Interactive raw/normalized confusion matrices
├── ⚛️ Quantum Lab        — Interactive FRQI/NEQR experiment runner
├── 🔬 Circuit Analyzer   — Gate breakdown, resource scaling, circuit diagrams
├── 🖼️ Reconstruction     — Quality distributions and defect category analysis
├── 📋 Experiment Results — Filterable table, scatter plots
└── ⚖️ Quantum Compare Lab— Custom module for direct FRQI vs NEQR side-by-side analysis
```

---

## Project Structure

```
QIP/
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
│   └── ml/                     # ML classification pipeline
│
├── results/                    # Dataset JSONs, ML Results, and Plot Images
├── frontend/                   # React + Vite Frontend App
│   ├── src/pages/              # React Page Components
│   └── vite.config.ts          # Vite Configuration with API proxy
│
├── api_main.py                 # FastAPI Application Server (Replacing Streamlit)
├── config/settings.py          # Backend configuration
├── main.py                     # CLI: demo / experiment / all
└── requirements.txt            # Python Dependencies
```

---

## Setup & Usage

### 1. Backend Setup (FastAPI)
```bash
# Install Python dependencies
pip install -r requirements.txt

# Start the FastAPI server on port 8000
python api_main.py
```
*The backend API will be available at `http://localhost:8000`*

### 2. Frontend Setup (React/Vite)
Open a new terminal window:
```bash
# Navigate to the frontend directory
cd frontend

# Install Node dependencies
npm install

# Start the Vite development server
npm run dev
```
*The frontend application will be available at `http://localhost:5173`*

### 3. CLI Scripts
```bash
# Run ML Pipeline (generates ML results)
python3 -c "from src.ml.trainer import run_full_ml_pipeline; run_full_ml_pipeline()"

# Run Quantum Experiments manually
python main.py demo --size 4 --bits 8 --shots 1000 --sv
```

---

## Data Integrity

- All ML metrics from actual model training — no hard-coded values
- All quantum metrics from Qiskit Aer simulation — no fabricated results
- Strict train/val/test separation — test set never seen during training or tuning
- StandardScaler fit on training data only — no leakage to val/test
- Fixed random seed (42) throughout — fully reproducible
- Stratified splits — all 6 classes equally represented in every split
