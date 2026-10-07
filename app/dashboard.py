"""
Q-ImageLab — Main Dashboard Entry Point.
Interactive Quantum Image Processing & NEU Surface Defect Analytics Dashboard.

Run with:
    streamlit run app/dashboard.py
"""

import streamlit as st
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

st.set_page_config(
    page_title="Q-ImageLab",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "Q-ImageLab — Interactive Quantum Image Processing & NEU Surface Defect Analytics Dashboard",
    }
)

# CSS: Premium dark glassmorphic design
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

* { font-family: 'Inter', sans-serif !important; }
.material-symbols-rounded, .material-icons, [class*="stIcon"], [data-testid="stIconMaterial"], i, svg { 
    font-family: 'Material Symbols Rounded' !important; 
}

/* Dark background */
.stApp { background: linear-gradient(135deg, #0a0a1a 0%, #0d1b2a 50%, #0a0f1e 100%); }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1b2a 0%, #0a1020 100%);
    border-right: 1px solid rgba(99, 179, 237, 0.15);
}
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }

/* KPI Cards */
.kpi-card {
    background: linear-gradient(135deg, rgba(26,41,66,0.9) 0%, rgba(17,25,40,0.95) 100%);
    border: 1px solid rgba(99,179,237,0.25);
    border-radius: 16px;
    padding: 20px;
    text-align: center;
    margin: 8px 0;
    backdrop-filter: blur(10px);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(99,179,237,0.15);
}
.kpi-value {
    font-size: 2.4rem;
    font-weight: 800;
    background: linear-gradient(135deg, #63b3ed 0%, #90cdf4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.1;
}
.kpi-label {
    font-size: 0.8rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 500;
    margin-top: 4px;
}

/* Section headers */
.section-header {
    color: #e2e8f0;
    font-size: 1.4rem;
    font-weight: 700;
    border-bottom: 2px solid rgba(99,179,237,0.3);
    padding-bottom: 8px;
    margin: 24px 0 16px 0;
}

/* Hero */
.hero-title {
    font-size: 3rem;
    font-weight: 800;
    background: linear-gradient(135deg, #63b3ed 0%, #90cdf4 50%, #e2e8f0 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.1;
    margin-bottom: 0;
}
.hero-subtitle {
    font-size: 1.1rem;
    color: #94a3b8;
    font-weight: 400;
    margin-top: 8px;
}

/* Status badge */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
}
.badge-quantum { background: rgba(99,179,237,0.15); color: #63b3ed; border: 1px solid rgba(99,179,237,0.3); }
.badge-ml { background: rgba(154,205,50,0.12); color: #9acd32; border: 1px solid rgba(154,205,50,0.3); }
.badge-ready { background: rgba(72,187,120,0.15); color: #68d391; border: 1px solid rgba(72,187,120,0.3); }

/* Divider */
.q-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(99,179,237,0.3), transparent);
    margin: 24px 0;
}

/* Tables — force dark mode readability */
.stDataFrame { border-radius: 12px !important; overflow: hidden !important; }
.stDataFrame [data-testid="stDataFrameResizable"] { background: rgba(13,27,42,0.95) !important; }
/* DataFrame header cells */
.stDataFrame th, .stDataFrame thead th {
    background: rgba(26,41,66,0.95) !important;
    color: #90cdf4 !important;
    font-weight: 700 !important;
    font-size: 0.82rem !important;
    border-bottom: 1px solid rgba(99,179,237,0.3) !important;
    padding: 8px 12px !important;
}
/* DataFrame body cells */
.stDataFrame td, .stDataFrame tbody td {
    color: #e2e8f0 !important;
    background: rgba(13,27,42,0.8) !important;
    font-size: 0.82rem !important;
    border-bottom: 1px solid rgba(99,179,237,0.08) !important;
}
/* Streamlit select/input dark fix */
.stSelectbox label, .stRadio label, .stSlider label,
.stMultiSelect label, .stCheckbox label, .stToggle label {
    color: #94a3b8 !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
}
.stSelectbox [data-baseweb="select"] { background: rgba(26,41,66,0.8) !important; border-color: rgba(99,179,237,0.3) !important; }
.stSelectbox [data-baseweb="select"] * { color: #e2e8f0 !important; }
/* Caption text */
.stCaption { color: #64748b !important; }
/* st.metric */
[data-testid="metric-container"] label { color: #94a3b8 !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #90cdf4 !important; font-weight: 800 !important; }
/* st.info/warning/success boxes */
.stAlert { border-radius: 10px !important; }
/* Tab text */
.stTabs [data-baseweb="tab"] { color: #94a3b8 !important; }
.stTabs [aria-selected="true"] { color: #90cdf4 !important; border-bottom-color: #63b3ed !important; }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #2b6cb0, #2c5282) !important;
    color: white !important;
    border: 1px solid rgba(99,179,237,0.4) !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #3182ce, #2b6cb0) !important;
    box-shadow: 0 4px 16px rgba(49,130,206,0.4) !important;
    transform: translateY(-1px) !important;
}

/* Info boxes */
.stInfo { background: rgba(49,130,206,0.1) !important; border-color: rgba(99,179,237,0.3) !important; }
.stSuccess { background: rgba(72,187,120,0.1) !important; border-color: rgba(104,211,145,0.3) !important; }
.stWarning { background: rgba(245,158,11,0.1) !important; border-color: rgba(251,191,36,0.3) !important; }

/* Sidebar navigation */
.nav-label {
    font-size: 0.75rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 600;
    margin: 16px 0 6px 0;
    padding-left: 8px;
}
</style>
""", unsafe_allow_html=True)

# --- HOME PAGE CONTENT ---
def render_home():
    # Hero section
    st.markdown("""
    <div style="padding: 24px 0 16px 0;">
        <div class="hero-title"> Q-ImageLab</div>
        <div class="hero-subtitle">
            Interactive Quantum Image Processing &amp; NEU Surface Defect Analytics Dashboard
        </div>
        <div style="margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap;">
            <span class="badge badge-quantum">Qiskit 2.5</span>
            <span class="badge badge-ml">Scikit-learn</span>
            <span class="badge badge-ready">NEU-DET Dataset</span>
            <span class="badge badge-quantum">FRQI + NEQR</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

    # Load stats for KPIs
    import pandas as pd
    import json

    dataset_kpis = get_dataset_kpis()
    ml_kpis = get_ml_kpis()
    quantum_kpis = get_quantum_kpis()

    # --- DATASET OVERVIEW ---
    st.markdown('<div class="section-header"> Dataset Overview</div>', unsafe_allow_html=True)
    cols = st.columns(5)
    kpi_data = [
        (dataset_kpis.get("total_images", 1800), "Total Images"),
        (dataset_kpis.get("n_classes", 6), "Defect Classes"),
        (dataset_kpis.get("train_total", 1440), "Train Images"),
        (dataset_kpis.get("val_total", 360), "Validation Images"),
        (dataset_kpis.get("test_total", "N/A"), "Test Images"),
    ]
    for col, (val, label) in zip(cols, kpi_data):
        with col:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-value">{val}</div>
                <div class="kpi-label">{label}</div>
            </div>""", unsafe_allow_html=True)

    # --- ML OVERVIEW ---
    st.markdown('<div class="section-header"> ML Model Overview</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    ml_kpi_data = [
        (ml_kpis.get("n_models", 4), "Models Evaluated"),
        (ml_kpis.get("best_val_acc", "—"), "Best Val Accuracy"),
        (ml_kpis.get("best_test_acc", "—"), "Best Test Accuracy"),
        (ml_kpis.get("best_f1", "—"), "Best F1 Score"),
    ]
    for col, (val, label) in zip(cols, ml_kpi_data):
        with col:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-value">{val}</div>
                <div class="kpi-label">{label}</div>
            </div>""", unsafe_allow_html=True)

    # --- QUANTUM OVERVIEW ---
    st.markdown('<div class="section-header"> Quantum Processing Overview</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    q_kpi_data = [
        ("2", "Encoders (FRQI+NEQR)"),
        (quantum_kpis.get("n_experiments", "—"), "Experiments Run"),
        (quantum_kpis.get("avg_psnr", "—"), "Avg PSNR (dB)"),
        (quantum_kpis.get("avg_ssim", "—"), "Avg SSIM"),
    ]
    for col, (val, label) in zip(cols, q_kpi_data):
        with col:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-value">{val}</div>
                <div class="kpi-label">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

    # Navigation guide
    st.markdown('<div class="section-header"> Navigate Q-ImageLab</div>', unsafe_allow_html=True)
    nav_cols = st.columns(3)
    nav_items = [
        (" Dataset Explorer", "Explore NEU-DET classes, sample images, pixel distributions", "pages/2_Dataset_Explorer"),
        (" Model Analytics", "Compare SVM, RF, KNN, DT accuracy & metrics", "pages/3_Model_Analytics"),
        (" Confusion Matrix", "Interactive per-model confusion matrices", "pages/4_Confusion_Matrix"),
        (" Quantum Lab", "Run FRQI/NEQR on NEU images interactively", "pages/5_Quantum_Lab"),
        (" Circuit Analyzer", "Inspect quantum circuits, gates, depth", "pages/6_Circuit_Analyzer"),
        (" Reconstruction Studio", "View original vs reconstructed images", "pages/7_Reconstruction_Studio"),
        (" FRQI vs NEQR", "Side-by-side quantum comparison", "pages/8_FRQI_vs_NEQR"),
        (" Experiment Results", "Browse all stored experiment results", "pages/9_Experiment_Results"),
        (" Home", "This page", ""),
    ]
    for i, (title, desc, _) in enumerate(nav_items[:8]):
        with nav_cols[i % 3]:
            st.markdown(f"""
            <div class="kpi-card" style="text-align:left; padding:16px;">
                <div style="font-size:1.1rem; font-weight:700; color:#90cdf4;">{title}</div>
                <div style="font-size:0.82rem; color:#94a3b8; margin-top:6px;">{desc}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)
    st.caption("Q-ImageLab | Quantum Image Processing & NEU Surface Defect Analytics | All results from real experiments")


def get_dataset_kpis():
    import json
    p = PROJECT_ROOT / "results" / "dataset" / "dataset_summary.json"
    if p.exists():
        with open(p) as f:
            d = json.load(f)
        # Estimate test from split_info
        sp = PROJECT_ROOT / "results" / "models" / "split_info.json"
        test_total = "—"
        if sp.exists():
            with open(sp) as f2:
                s = json.load(f2)
            test_total = s.get("test_samples", "—")
        d["test_total"] = test_total
        return d
    return {"total_images": 1800, "n_classes": 6, "train_total": 1440, "val_total": 360, "test_total": "~432"}


def get_ml_kpis():
    import pandas as pd
    p = PROJECT_ROOT / "results" / "models" / "model_comparison.csv"
    if p.exists():
        try:
            df = pd.read_csv(p)
            best_val = f"{df['val_accuracy'].max():.4f}"
            best_test = f"{df['test_accuracy'].max():.4f}"
            best_f1 = f"{df['f1_macro'].max():.4f}"
            return {"n_models": len(df), "best_val_acc": best_val, "best_test_acc": best_test, "best_f1": best_f1}
        except:
            pass
    return {"n_models": 4, "best_val_acc": "—", "best_test_acc": "—", "best_f1": "—"}


def get_quantum_kpis():
    import pandas as pd
    p = PROJECT_ROOT / "results" / "experiments" / "all_results.csv"
    if p.exists():
        try:
            df = pd.read_csv(p)
            n_exp = len(df)
            avg_psnr = f"{df['psnr'].mean():.2f}"
            avg_ssim = f"{df['ssim'].mean():.4f}"
            return {"n_experiments": n_exp, "avg_psnr": avg_psnr, "avg_ssim": avg_ssim}
        except:
            pass
    return {"n_experiments": "—", "avg_psnr": "—", "avg_ssim": "—"}


render_home()
