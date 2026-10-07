"""
Experiment Results — Browse, Filter, and Export All Stored Experiments
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
from config.settings import DEFECT_CATEGORIES

st.set_page_config(page_title="Experiment Results | Q-ImageLab", page_icon="", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* { font-family: 'Inter', sans-serif !important; }
.material-symbols-rounded, .material-icons, [class*="stIcon"], [data-testid="stIconMaterial"], i, svg { font-family: 'Material Symbols Rounded' !important; }
.stApp { background: linear-gradient(135deg, #0a0a1a 0%, #0d1b2a 50%, #0a0f1e 100%); }
section[data-testid="stSidebar"] { background: linear-gradient(180deg,#0d1b2a,#0a1020); border-right:1px solid rgba(99,179,237,.15); }
section[data-testid="stSidebar"] * { color:#e2e8f0 !important; }
.kpi-card { background:linear-gradient(135deg,rgba(26,41,66,.9),rgba(17,25,40,.95)); border:1px solid rgba(99,179,237,.25); border-radius:16px; padding:16px; text-align:center; margin:6px 0; }
.kpi-value { font-size:1.8rem; font-weight:800; background:linear-gradient(135deg,#63b3ed,#90cdf4); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }
.kpi-label { font-size:.72rem; color:#94a3b8; text-transform:uppercase; letter-spacing:.08em; font-weight:500; margin-top:4px; }
.section-header { color:#e2e8f0; font-size:1.35rem; font-weight:700; border-bottom:2px solid rgba(99,179,237,.3); padding-bottom:8px; margin:24px 0 16px 0; }
.q-divider { height:1px; background:linear-gradient(90deg,transparent,rgba(99,179,237,.3),transparent); margin:20px 0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 style="color:#90cdf4;font-weight:800;font-size:2rem;"> Experiment Results</h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#94a3b8;">Browse, filter, and export all stored quantum image processing experiments</p>', unsafe_allow_html=True)
st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

RESULTS_PATH = PROJECT_ROOT / "results" / "experiments"
CLASS_DISPLAY = {c: c.replace("_"," ").replace("-"," ").title() for c in DEFECT_CATEGORIES}

@st.cache_data
def load_all_results():
    p = RESULTS_PATH / "all_results.csv"
    if p.exists():
        df = pd.read_csv(p)
        df["psnr"] = pd.to_numeric(df["psnr"], errors="coerce").clip(0, 100)
        df["ssim"] = pd.to_numeric(df["ssim"], errors="coerce")
        df["mse"]  = pd.to_numeric(df["mse"],  errors="coerce")
        return df
    return pd.DataFrame()

df = load_all_results()

if df.empty:
    st.warning("No saved experiments found. Run `python main.py all` to generate results.")
    st.stop()

# ── KPIs ───────────────────────────────────────────────────────────────────────
kpi_cols = st.columns(6)
kpis_data = [
    (len(df), "Total Experiments"),
    (df["representation"].nunique(), "Representations"),
    (f"{df['psnr'].max():.2f} dB", "Best PSNR"),
    (f"{df['ssim'].max():.4f}", "Best SSIM"),
    (f"{df['mse'].min():.6f}", "Best MSE"),
    (df["defect_category"].nunique(), "Defect Categories"),
]
for col, (val, label) in zip(kpi_cols, kpis_data):
    col.markdown(f'<div class="kpi-card"><div class="kpi-value" style="font-size:1.5rem;">{val}</div><div class="kpi-label">{label}</div></div>', unsafe_allow_html=True)

st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

# ── Filter Controls ────────────────────────────────────────────────────────────
st.markdown('<div class="section-header"> Filter & Search</div>', unsafe_allow_html=True)

f1, f2, f3, f4, f5 = st.columns(5)
with f1:
    f_rep = st.multiselect("Representation", df["representation"].unique().tolist(), default=df["representation"].unique().tolist())
with f2:
    if "resolution" in df.columns:
        f_res = st.multiselect("Resolution", sorted(df["resolution"].dropna().unique().tolist()), default=sorted(df["resolution"].dropna().unique().tolist()))
    else:
        f_res = []
with f3:
    if "intensity_precision" in df.columns:
        f_bits = st.multiselect("Precision (bits)", sorted(df["intensity_precision"].dropna().unique().tolist()), default=sorted(df["intensity_precision"].dropna().unique().tolist()))
    else:
        f_bits = []
with f4:
    if "defect_category" in df.columns:
        cats = sorted(df["defect_category"].dropna().unique().tolist())
        f_cat = st.multiselect("Category", cats, default=cats)
    else:
        f_cat = []
with f5:
    if "dataset" in df.columns:
        f_ds = st.multiselect("Dataset", df["dataset"].unique().tolist(), default=df["dataset"].unique().tolist())
    else:
        f_ds = []

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
if f_ds and "dataset" in df.columns:
    mask &= df["dataset"].isin(f_ds)

df_f = df[mask].copy()
st.markdown(f'<p style="color:#94a3b8;font-size:.85rem;">Showing <b style="color:#90cdf4;">{len(df_f)}</b> of {len(df)} experiments</p>', unsafe_allow_html=True)

# ── Sortable Results Table ─────────────────────────────────────────────────────
st.markdown('<div class="section-header"> Experiment Records</div>', unsafe_allow_html=True)

display_cols = ["experiment_id","representation","defect_category","image_name",
                "resolution","intensity_precision","shots","qubits","gate_count",
                "circuit_depth","mse","psnr","ssim","total_time"]
avail_cols = [c for c in display_cols if c in df_f.columns]
df_display = df_f[avail_cols].copy()

sort_col = st.selectbox("Sort by", avail_cols, index=avail_cols.index("psnr") if "psnr" in avail_cols else 0)
sort_asc = st.checkbox("Ascending", value=False)
df_display = df_display.sort_values(sort_col, ascending=sort_asc)

# Round floats
for c in ["mse","psnr","ssim","total_time"]:
    if c in df_display.columns:
        df_display[c] = df_display[c].round(6)

st.dataframe(df_display, use_container_width=True, hide_index=True, height=400)

# Export
csv_export = df_f.to_csv(index=False)
st.download_button(
    label=" Download Filtered Results (CSV)",
    data=csv_export,
    file_name="q_imagelab_filtered_results.csv",
    mime="text/csv",
)

st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

# ── Summary Statistics ─────────────────────────────────────────────────────────
st.markdown('<div class="section-header"> Summary Statistics</div>', unsafe_allow_html=True)
if not df_f.empty:
    numeric_cols = ["qubits","gate_count","circuit_depth","mse","psnr","ssim","total_time","encoding_time","simulation_time"]
    avail_num = [c for c in numeric_cols if c in df_f.columns]
    grp_summary = df_f.groupby("representation")[avail_num].agg(["mean","std","min","max"]).round(4)
    st.dataframe(grp_summary)

st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

# ── Scatter plot ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header"> Interactive Scatter Plot</div>', unsafe_allow_html=True)
sc_col1, sc_col2 = st.columns(2)
num_cols = [c for c in df_f.columns if df_f[c].dtype in [float, int] and df_f[c].nunique() > 2]
with sc_col1:
    x_axis = st.selectbox("X axis", num_cols, index=num_cols.index("psnr") if "psnr" in num_cols else 0)
with sc_col2:
    y_axis = st.selectbox("Y axis", num_cols, index=num_cols.index("ssim") if "ssim" in num_cols else min(1, len(num_cols)-1))

if "representation" in df_f.columns:
    fig_sc = px.scatter(
        df_f, x=x_axis, y=y_axis, color="representation",
        color_discrete_map={"FRQI":"#63b3ed","NEQR":"#68d391"},
        hover_data=["image_name","defect_category","resolution"] if "image_name" in df_f.columns else None,
        title=f"{x_axis} vs {y_axis}",
        opacity=0.7,
    )
    fig_sc.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
        font=dict(color="#e2e8f0"), height=400,
        xaxis=dict(gridcolor="rgba(99,179,237,.1)"),
        yaxis=dict(gridcolor="rgba(99,179,237,.1)"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig_sc)

# ── Available experiment files ─────────────────────────────────────────────────
st.markdown('<div class="section-header"> Available Result Files</div>', unsafe_allow_html=True)
files_info = []
for f in sorted(RESULTS_PATH.glob("*.csv")):
    size_kb = f.stat().st_size / 1024
    try:
        row_count = sum(1 for _ in open(f)) - 1
    except:
        row_count = "?"
    files_info.append({"File": f.name, "Rows": row_count, "Size (KB)": f"{size_kb:.1f}"})

if files_info:
    st.dataframe(pd.DataFrame(files_info), use_container_width=True, hide_index=True)

st.caption("Q-ImageLab | Experiment Results | All data from real quantum simulation runs")
