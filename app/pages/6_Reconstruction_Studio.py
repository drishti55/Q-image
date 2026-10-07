"""
Reconstruction Studio — Browse and compare quantum reconstructions from saved experiments
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
from config.settings import DEFECT_CATEGORIES

st.set_page_config(page_title="Reconstruction Studio | Q-ImageLab", page_icon="", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* { font-family: 'Inter', sans-serif !important; }
.material-symbols-rounded, .material-icons, [class*="stIcon"], [data-testid="stIconMaterial"], i, svg { font-family: 'Material Symbols Rounded' !important; }
.stApp { background: linear-gradient(135deg, #0a0a1a 0%, #0d1b2a 50%, #0a0f1e 100%); }
section[data-testid="stSidebar"] { background: linear-gradient(180deg,#0d1b2a,#0a1020); border-right:1px solid rgba(99,179,237,.15); }
section[data-testid="stSidebar"] * { color:#e2e8f0 !important; }
.kpi-card { background:linear-gradient(135deg,rgba(26,41,66,.9),rgba(17,25,40,.95)); border:1px solid rgba(99,179,237,.25); border-radius:16px; padding:18px; text-align:center; margin:6px 0; }
.kpi-value { font-size:1.9rem; font-weight:800; background:linear-gradient(135deg,#63b3ed,#90cdf4); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }
.kpi-label { font-size:.75rem; color:#94a3b8; text-transform:uppercase; letter-spacing:.08em; font-weight:500; margin-top:4px; }
.section-header { color:#e2e8f0; font-size:1.35rem; font-weight:700; border-bottom:2px solid rgba(99,179,237,.3); padding-bottom:8px; margin:24px 0 16px 0; }
.q-divider { height:1px; background:linear-gradient(90deg,transparent,rgba(99,179,237,.3),transparent); margin:20px 0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 style="color:#90cdf4;font-weight:800;font-size:2rem;"> Reconstruction Studio</h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#94a3b8;">Explore quantum reconstruction quality from saved experiments — quality metrics and comparisons</p>', unsafe_allow_html=True)
st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

RESULTS_PATH = PROJECT_ROOT / "results" / "experiments"
CLASS_DISPLAY = {c: c.replace("_"," ").replace("-"," ").title() for c in DEFECT_CATEGORIES}

@st.cache_data
def load_experiment_results():
    p = RESULTS_PATH / "all_results.csv"
    if p.exists():
        df = pd.read_csv(p)
        # Clean up inf/nan
        df["psnr"] = pd.to_numeric(df["psnr"], errors="coerce").clip(0, 100)
        df["ssim"] = pd.to_numeric(df["ssim"], errors="coerce")
        df["mse"]  = pd.to_numeric(df["mse"],  errors="coerce")
        return df
    return pd.DataFrame()

df = load_experiment_results()

if df.empty:
    st.warning("No experiment results found. Run `python main.py all` to generate.")
    st.stop()

# ── KPI Overview ───────────────────────────────────────────────────────────────
frqi_df = df[df["representation"] == "FRQI"]
neqr_df = df[df["representation"] == "NEQR"]

kpi_cols = st.columns(6)
kpis = [
    (len(df), "Total Experiments"),
    (len(frqi_df), "FRQI Experiments"),
    (len(neqr_df), "NEQR Experiments"),
    (f"{df['psnr'].mean():.2f}", "Avg PSNR (dB)"),
    (f"{df['ssim'].mean():.4f}", "Avg SSIM"),
    (f"{df['mse'].mean():.6f}", "Avg MSE"),
]
for col, (val, label) in zip(kpi_cols, kpis):
    col.markdown(f'<div class="kpi-card"><div class="kpi-value" style="font-size:1.5rem;">{val}</div><div class="kpi-label">{label}</div></div>', unsafe_allow_html=True)

st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

# ── Filter Controls ────────────────────────────────────────────────────────────
st.markdown('<div class="section-header"> Filter Experiments</div>', unsafe_allow_html=True)
f_col1, f_col2, f_col3, f_col4 = st.columns(4)
with f_col1:
    f_rep = st.multiselect("Representation", ["FRQI","NEQR"], default=["FRQI","NEQR"])
with f_col2:
    avail_res = df["resolution"].dropna().unique().tolist() if "resolution" in df.columns else []
    f_res = st.multiselect("Resolution", sorted(avail_res), default=sorted(avail_res))
with f_col3:
    avail_bits = df["intensity_precision"].dropna().unique().tolist() if "intensity_precision" in df.columns else []
    f_bits = st.multiselect("Precision (bits)", sorted(avail_bits), default=sorted(avail_bits))
with f_col4:
    avail_cats = df["defect_category"].dropna().unique().tolist() if "defect_category" in df.columns else []
    f_cat = st.multiselect("Category", sorted(avail_cats), default=sorted(avail_cats))

# Apply filters
mask = pd.Series([True] * len(df))
if f_rep:
    mask &= df["representation"].isin(f_rep)
if f_res and "resolution" in df.columns:
    mask &= df["resolution"].isin(f_res)
if f_bits and "intensity_precision" in df.columns:
    mask &= df["intensity_precision"].isin(f_bits)
if f_cat and "defect_category" in df.columns:
    mask &= df["defect_category"].isin(f_cat)

df_f = df[mask].copy()
st.markdown(f'<p style="color:#94a3b8;font-size:.85rem;">Showing <b style="color:#90cdf4;">{len(df_f)}</b> of {len(df)} experiments</p>', unsafe_allow_html=True)

st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

# ── Quality Metrics Distribution ───────────────────────────────────────────────
st.markdown('<div class="section-header"> Reconstruction Quality Distribution</div>', unsafe_allow_html=True)
q_col1, q_col2, q_col3 = st.columns(3)

with q_col1:
    fig_psnr = go.Figure()
    for rep, color in [("FRQI","#63b3ed"),("NEQR","#68d391")]:
        sub = df_f[df_f["representation"]==rep]["psnr"].dropna()
        fig_psnr.add_trace(go.Histogram(x=sub, name=rep, marker_color=color, opacity=0.7, nbinsx=30))
    fig_psnr.update_layout(
        title="PSNR Distribution", barmode="overlay",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
        font=dict(color="#e2e8f0"), height=300,
        xaxis_title="PSNR (dB)", legend=dict(bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor="rgba(99,179,237,.1)"), yaxis=dict(gridcolor="rgba(99,179,237,.1)"),
    )
    st.plotly_chart(fig_psnr)

with q_col2:
    fig_ssim = go.Figure()
    for rep, color in [("FRQI","#63b3ed"),("NEQR","#68d391")]:
        sub = df_f[df_f["representation"]==rep]["ssim"].dropna()
        fig_ssim.add_trace(go.Histogram(x=sub, name=rep, marker_color=color, opacity=0.7, nbinsx=30))
    fig_ssim.update_layout(
        title="SSIM Distribution", barmode="overlay",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
        font=dict(color="#e2e8f0"), height=300,
        xaxis_title="SSIM", legend=dict(bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor="rgba(99,179,237,.1)"), yaxis=dict(gridcolor="rgba(99,179,237,.1)"),
    )
    st.plotly_chart(fig_ssim)

with q_col3:
    fig_mse = go.Figure()
    for rep, color in [("FRQI","#63b3ed"),("NEQR","#68d391")]:
        sub = df_f[df_f["representation"]==rep]["mse"].dropna()
        fig_mse.add_trace(go.Histogram(x=sub, name=rep, marker_color=color, opacity=0.7, nbinsx=30))
    fig_mse.update_layout(
        title="MSE Distribution", barmode="overlay",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
        font=dict(color="#e2e8f0"), height=300,
        xaxis_title="MSE", legend=dict(bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor="rgba(99,179,237,.1)"), yaxis=dict(gridcolor="rgba(99,179,237,.1)"),
    )
    st.plotly_chart(fig_mse)

st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

# ── Resolution vs Quality ──────────────────────────────────────────────────────
st.markdown('<div class="section-header"> Resolution vs Reconstruction Quality</div>', unsafe_allow_html=True)
if "resolution" in df_f.columns:
    rq_col1, rq_col2 = st.columns(2)
    grp = df_f.groupby(["representation","resolution"])[["psnr","ssim"]].mean().reset_index()
    with rq_col1:
        fig = px.bar(grp, x="resolution", y="psnr", color="representation",
                     barmode="group", color_discrete_map={"FRQI":"#63b3ed","NEQR":"#68d391"},
                     title="Avg PSNR by Resolution", text_auto=".2f")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
                          font=dict(color="#e2e8f0"), height=320,
                          xaxis=dict(gridcolor="rgba(99,179,237,.1)"),
                          yaxis=dict(gridcolor="rgba(99,179,237,.1)"),
                          legend=dict(bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig)
    with rq_col2:
        fig2 = px.bar(grp, x="resolution", y="ssim", color="representation",
                      barmode="group", color_discrete_map={"FRQI":"#63b3ed","NEQR":"#68d391"},
                      title="Avg SSIM by Resolution", text_auto=".4f")
        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
                           font=dict(color="#e2e8f0"), height=320,
                           xaxis=dict(gridcolor="rgba(99,179,237,.1)"),
                           yaxis=dict(gridcolor="rgba(99,179,237,.1)"),
                           legend=dict(bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig2)

# ── Shots vs Quality (if available) ────────────────────────────────────────────
shots_df = df_f[df_f["shots"] > 0] if "shots" in df_f.columns else pd.DataFrame()
if not shots_df.empty:
    st.markdown('<div class="section-header"> Measurement Shots vs Quality</div>', unsafe_allow_html=True)
    grp_s = shots_df.groupby(["representation","shots"])[["psnr","ssim"]].mean().reset_index()
    sq_col1, sq_col2 = st.columns(2)
    with sq_col1:
        fig_s = go.Figure()
        for rep, color in [("FRQI","#63b3ed"),("NEQR","#68d391")]:
            sub = grp_s[grp_s["representation"]==rep]
            fig_s.add_trace(go.Scatter(x=sub["shots"], y=sub["psnr"], mode="lines+markers",
                                       name=rep, line_color=color))
        fig_s.update_layout(title="PSNR vs Measurement Shots",
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
                            font=dict(color="#e2e8f0"), height=300,
                            xaxis=dict(title="Shots", gridcolor="rgba(99,179,237,.1)"),
                            yaxis=dict(title="PSNR (dB)", gridcolor="rgba(99,179,237,.1)"),
                            legend=dict(bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig_s)
    with sq_col2:
        fig_s2 = go.Figure()
        for rep, color in [("FRQI","#63b3ed"),("NEQR","#68d391")]:
            sub = grp_s[grp_s["representation"]==rep]
            fig_s2.add_trace(go.Scatter(x=sub["shots"], y=sub["ssim"], mode="lines+markers",
                                        name=rep, line_color=color))
        fig_s2.update_layout(title="SSIM vs Measurement Shots",
                             paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
                             font=dict(color="#e2e8f0"), height=300,
                             xaxis=dict(title="Shots", gridcolor="rgba(99,179,237,.1)"),
                             yaxis=dict(title="SSIM", gridcolor="rgba(99,179,237,.1)"),
                             legend=dict(bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig_s2)

# ── Defect Category vs Quality ─────────────────────────────────────────────────
if "defect_category" in df_f.columns:
    neu_df = df_f[df_f["defect_category"].isin(DEFECT_CATEGORIES)]
    if not neu_df.empty:
        st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-header"> NEU-DET Defect Category vs Reconstruction Quality</div>', unsafe_allow_html=True)
        grp_cat = neu_df.groupby(["representation","defect_category"])[["psnr","ssim"]].mean().reset_index()
        grp_cat["category_display"] = grp_cat["defect_category"].map(CLASS_DISPLAY).fillna(grp_cat["defect_category"])
        cat_col1, cat_col2 = st.columns(2)
        with cat_col1:
            fig_cat = px.bar(grp_cat, x="category_display", y="psnr", color="representation",
                             barmode="group", color_discrete_map={"FRQI":"#63b3ed","NEQR":"#68d391"},
                             title="Avg PSNR per Defect Category")
            fig_cat.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
                                  font=dict(color="#e2e8f0"), height=340,
                                  xaxis=dict(gridcolor="rgba(99,179,237,.1)", tickangle=-20),
                                  yaxis=dict(gridcolor="rgba(99,179,237,.1)"),
                                  legend=dict(bgcolor="rgba(0,0,0,0)"))
            st.plotly_chart(fig_cat)
        with cat_col2:
            fig_cat2 = px.bar(grp_cat, x="category_display", y="ssim", color="representation",
                              barmode="group", color_discrete_map={"FRQI":"#63b3ed","NEQR":"#68d391"},
                              title="Avg SSIM per Defect Category")
            fig_cat2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
                                   font=dict(color="#e2e8f0"), height=340,
                                   xaxis=dict(gridcolor="rgba(99,179,237,.1)", tickangle=-20),
                                   yaxis=dict(gridcolor="rgba(99,179,237,.1)"),
                                   legend=dict(bgcolor="rgba(0,0,0,0)"))
            st.plotly_chart(fig_cat2)

st.caption("Q-ImageLab | Reconstruction Studio | Results from actual quantum simulation experiments")
