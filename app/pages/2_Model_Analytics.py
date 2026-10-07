"""
Model Analytics — ML Classification Results for NEU-DET
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
from config.settings import DEFECT_CATEGORIES

st.set_page_config(page_title="Model Analytics | Q-ImageLab", page_icon="", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* { font-family: 'Inter', sans-serif !important; }
.material-symbols-rounded, .material-icons, [class*="stIcon"], [data-testid="stIconMaterial"], i, svg { font-family: 'Material Symbols Rounded' !important; }
.stApp { background: linear-gradient(135deg, #0a0a1a 0%, #0d1b2a 50%, #0a0f1e 100%); }
section[data-testid="stSidebar"] { background: linear-gradient(180deg,#0d1b2a,#0a1020); border-right:1px solid rgba(99,179,237,.15); }
section[data-testid="stSidebar"] * { color:#e2e8f0 !important; }
.kpi-card { background:linear-gradient(135deg,rgba(26,41,66,.9),rgba(17,25,40,.95)); border:1px solid rgba(99,179,237,.25); border-radius:16px; padding:20px; text-align:center; margin:8px 0; }
.kpi-value { font-size:2.2rem; font-weight:800; background:linear-gradient(135deg,#63b3ed,#90cdf4); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }
.kpi-label { font-size:.78rem; color:#94a3b8; text-transform:uppercase; letter-spacing:.08em; font-weight:500; margin-top:4px; }
.section-header { color:#e2e8f0; font-size:1.35rem; font-weight:700; border-bottom:2px solid rgba(99,179,237,.3); padding-bottom:8px; margin:24px 0 16px 0; }
.q-divider { height:1px; background:linear-gradient(90deg,transparent,rgba(99,179,237,.3),transparent); margin:20px 0; }
.best-badge { background:rgba(72,187,120,.15); color:#68d391; border:1px solid rgba(72,187,120,.3); padding:2px 8px; border-radius:12px; font-size:.72rem; font-weight:600; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 style="color:#90cdf4;font-weight:800;font-size:2rem;"> Model Analytics</h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#94a3b8;">Classification performance on NEU Surface Defect Database — 4 baseline models</p>', unsafe_allow_html=True)
st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

MODELS_PATH = PROJECT_ROOT / "results" / "models"
MODEL_COLORS = {"SVM": "#63b3ed", "Random Forest": "#68d391", "KNN": "#f6ad55", "Decision Tree": "#b794f4"}

@st.cache_data
def load_model_comparison():
    p = MODELS_PATH / "model_comparison.csv"
    if p.exists():
        return pd.read_csv(p)
    return pd.DataFrame()

@st.cache_data
def load_per_class():
    p = MODELS_PATH / "per_class_metrics.csv"
    if p.exists():
        return pd.read_csv(p)
    return pd.DataFrame()

@st.cache_data
def load_hp():
    p = MODELS_PATH / "hyperparameter_results.csv"
    if p.exists():
        return pd.read_csv(p)
    return pd.DataFrame()

@st.cache_data
def load_split_info():
    p = MODELS_PATH / "split_info.json"
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return {}

df = load_model_comparison()
df_pc = load_per_class()
df_hp = load_hp()
sp = load_split_info()

if df.empty:
    st.warning(" ML results not found. Run the ML pipeline first: `python3 -c \"from src.ml.trainer import run_full_ml_pipeline; run_full_ml_pipeline()\"`")
    st.stop()

CLASS_DISPLAY = {c: c.replace("_", " ").replace("-", " ").title() for c in DEFECT_CATEGORIES}

# ── KPI Cards ──────────────────────────────────────────────────────────────────
best_val  = df.loc[df["val_accuracy"].idxmax()]
best_test = df.loc[df["test_accuracy"].idxmax()]
best_f1   = df.loc[df["f1_macro"].idxmax()]

kpi_cols = st.columns(6)
kpis = [
    (f"{best_val['val_accuracy']:.4f}", f"Best Val Acc ({best_val['model']})"),
    (f"{best_test['test_accuracy']:.4f}", f"Best Test Acc ({best_test['model']})"),
    (f"{best_f1['f1_macro']:.4f}", f"Best F1 ({best_f1['model']})"),
    (len(df), "Models Evaluated"),
    (sp.get("train_samples", "—"), "Train Samples"),
    (sp.get("test_samples", "—"), "Test Samples"),
]
for col, (val, label) in zip(kpi_cols, kpis):
    col.markdown(f'<div class="kpi-card"><div class="kpi-value">{val}</div><div class="kpi-label">{label}</div></div>', unsafe_allow_html=True)

st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

# ── Model Comparison Table ─────────────────────────────────────────────────────
st.markdown('<div class="section-header"> Model Comparison Table</div>', unsafe_allow_html=True)

display_df = df[["model","train_accuracy","val_accuracy","test_accuracy",
                  "precision_macro","recall_macro","f1_macro","f1_weighted",
                  "cv_mean","cv_std","training_time_s","inference_time_per_sample_ms"]].copy()
display_df.columns = ["Model","Train Acc","Val Acc","Test Acc","Precision","Recall",
                       "F1 Macro","F1 Weighted","CV Mean","CV Std","Train Time (s)","Infer Time (ms)"]
for c in display_df.columns[1:]:
    if display_df[c].dtype == float:
        display_df[c] = display_df[c].round(4)

st.dataframe(
    display_df.style
    .highlight_max(subset=["Val Acc","Test Acc","F1 Macro"], color="rgba(99,179,237,0.3)")
    .format({c: "{:.4f}" for c in ["Train Acc","Val Acc","Test Acc","Precision","Recall","F1 Macro","F1 Weighted","CV Mean","CV Std"]}),
    use_container_width=True, hide_index=True
)
st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

# ── Accuracy comparison charts ─────────────────────────────────────────────────
st.markdown('<div class="section-header"> Accuracy Comparison</div>', unsafe_allow_html=True)
acc_col1, acc_col2 = st.columns(2)

with acc_col1:
    fig = go.Figure()
    models = df["model"].tolist()
    colors = [MODEL_COLORS.get(m, "#90cdf4") for m in models]
    for metric, name, dash in [("train_accuracy","Train","dot"),("val_accuracy","Validation","dash"),("test_accuracy","Test","solid")]:
        fig.add_trace(go.Bar(
            name=name, x=models, y=df[metric],
            text=[f"{v:.4f}" for v in df[metric]], textposition="outside",
            marker_color=[MODEL_COLORS.get(m, "#90cdf4") for m in models],
            opacity=0.7 if name!="Test" else 1.0,
        ))
    fig.update_layout(
        title="Train / Val / Test Accuracy per Model",
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
        font=dict(color="#e2e8f0"), height=380,
        xaxis=dict(gridcolor="rgba(99,179,237,.1)"),
        yaxis=dict(gridcolor="rgba(99,179,237,.1)", range=[0, 1.15]),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig)

with acc_col2:
    fig2 = go.Figure()
    for metric, color in [("precision_macro","#63b3ed"),("recall_macro","#68d391"),("f1_macro","#f6ad55"),("f1_weighted","#b794f4")]:
        fig2.add_trace(go.Bar(
            name=metric.replace("_"," ").title(), x=models, y=df[metric],
            marker_color=color, opacity=0.85,
            text=[f"{v:.3f}" for v in df[metric]], textposition="outside",
        ))
    fig2.update_layout(
        title="Precision / Recall / F1 per Model",
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
        font=dict(color="#e2e8f0"), height=380,
        xaxis=dict(gridcolor="rgba(99,179,237,.1)"),
        yaxis=dict(gridcolor="rgba(99,179,237,.1)", range=[0, 1.15]),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig2)

st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

# ── Cross-Validation Results ───────────────────────────────────────────────────
st.markdown('<div class="section-header"> 5-Fold Cross-Validation Results</div>', unsafe_allow_html=True)
fig_cv = go.Figure()
fig_cv.add_trace(go.Bar(
    x=df["model"], y=df["cv_mean"],
    error_y=dict(type="data", array=df["cv_std"], visible=True, color="rgba(255,255,255,0.6)"),
    marker_color=[MODEL_COLORS.get(m, "#90cdf4") for m in df["model"]],
    text=[f"{m:.4f}±{s:.4f}" for m, s in zip(df["cv_mean"], df["cv_std"])],
    textposition="outside",
))
fig_cv.update_layout(
    title="5-Fold CV Accuracy (mean ± std) on Training Data",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
    font=dict(color="#e2e8f0"), height=380,
    xaxis=dict(gridcolor="rgba(99,179,237,.1)"),
    yaxis=dict(gridcolor="rgba(99,179,237,.1)", range=[0, 1.15]),
)
st.plotly_chart(fig_cv)
st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

# ── Per-Class Analysis ─────────────────────────────────────────────────────────
st.markdown('<div class="section-header"> Per-Class Performance Analysis</div>', unsafe_allow_html=True)
if not df_pc.empty:
    sel_model_pc = st.selectbox("Select Model for Per-Class View", df["model"].tolist())
    df_model_pc = df_pc[df_pc["model"] == sel_model_pc].copy()
    df_model_pc["class_display"] = df_model_pc["class"].map(
        lambda c: c.replace("_"," ").replace("-"," ").title()
    )

    pc_col1, pc_col2 = st.columns(2)
    with pc_col1:
        fig_pc = go.Figure()
        for metric, color in [("precision","#63b3ed"),("recall","#68d391"),("f1","#f6ad55")]:
            fig_pc.add_trace(go.Bar(
                name=metric.title(),
                x=df_model_pc["class_display"], y=df_model_pc[metric],
                marker_color=color, opacity=0.85,
            ))
        fig_pc.update_layout(
            title=f"{sel_model_pc} — Per-Class Precision / Recall / F1",
            barmode="group",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
            font=dict(color="#e2e8f0"), height=380,
            xaxis=dict(gridcolor="rgba(99,179,237,.1)", tickangle=-20),
            yaxis=dict(gridcolor="rgba(99,179,237,.1)", range=[0, 1.1]),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_pc)

    with pc_col2:
        fig_radar = go.Figure()
        cats_display = df_model_pc["class_display"].tolist()
        for metric, color in [("precision","#63b3ed"),("recall","#68d391"),("f1","#f6ad55")]:
            vals = df_model_pc[metric].tolist()
            fig_radar.add_trace(go.Scatterpolar(
                r=vals + [vals[0]], theta=cats_display + [cats_display[0]],
                fill="toself", name=metric.title(),
                line_color=color, fillcolor=color.replace(")", ",0.15)").replace("rgb","rgba"),
            ))
        fig_radar.update_layout(
            polar=dict(
                bgcolor="rgba(13,27,42,0.8)",
                radialaxis=dict(visible=True, range=[0, 1], gridcolor="rgba(99,179,237,.2)"),
                angularaxis=dict(gridcolor="rgba(99,179,237,.2)"),
            ),
            title=f"{sel_model_pc} — Radar Chart",
            paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"), height=380,
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_radar)

    st.dataframe(
        df_model_pc[["class_display","precision","recall","f1","support"]].rename(columns={
            "class_display":"Class","precision":"Precision","recall":"Recall","f1":"F1","support":"Support"
        }).round(4),
        use_container_width=True, hide_index=True,
    )

st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

# ── Hyperparameter Comparison ──────────────────────────────────────────────────
st.markdown('<div class="section-header"> Hyperparameter Experiments</div>', unsafe_allow_html=True)
if not df_hp.empty:
    hp_model = st.selectbox("Model for Hyperparameter View", df_hp["model"].unique().tolist())
    df_hp_m = df_hp[df_hp["model"] == hp_model].copy()
    fig_hp = go.Figure()
    fig_hp.add_trace(go.Bar(
        x=df_hp_m["param"], y=df_hp_m["val_accuracy"],
        marker_color="#63b3ed",
        text=[f"{v:.4f}" for v in df_hp_m["val_accuracy"]], textposition="outside",
    ))
    fig_hp.update_layout(
        title=f"{hp_model} — Hyperparameter Validation Accuracy",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
        font=dict(color="#e2e8f0"), height=360,
        xaxis=dict(gridcolor="rgba(99,179,237,.1)", tickangle=-30),
        yaxis=dict(gridcolor="rgba(99,179,237,.1)", range=[0, 1.05]),
    )
    st.plotly_chart(fig_hp)
    st.dataframe(df_hp_m[["param","val_accuracy","f1_macro","train_time_s"]].rename(columns={
        "param":"Config","val_accuracy":"Val Accuracy","f1_macro":"F1 Macro","train_time_s":"Train Time (s)"
    }).round(4), use_container_width=True, hide_index=True)

st.caption("Q-ImageLab | Model Analytics | All results from actual model training runs")
