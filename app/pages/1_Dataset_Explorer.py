"""
Dataset Explorer — NEU Surface Defect Database
"""

import streamlit as st
import numpy as np
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from PIL import Image
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
from config.settings import TRAIN_IMAGES_PATH, VALIDATION_IMAGES_PATH, DEFECT_CATEGORIES

# ── Page config & shared CSS ──────────────────────────────────────────────────
st.set_page_config(page_title="Dataset Explorer | Q-ImageLab", page_icon="", layout="wide")
st.markdown(open(PROJECT_ROOT / "app" / "_style.css").read() if (PROJECT_ROOT / "app" / "_style.css").exists() else "", unsafe_allow_html=True)

# ── Inline CSS (same palette as Home) ─────────────────────────────────────────
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
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown('<h1 style="color:#90cdf4;font-weight:800;font-size:2rem;"> Dataset Explorer</h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#94a3b8;">NEU Surface Defect Database — 6 classes of steel surface defects</p>', unsafe_allow_html=True)
st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

CLASS_DISPLAY = {
    "crazing": "Crazing",
    "inclusion": "Inclusion",
    "patches": "Patches",
    "pitted_surface": "Pitted Surface",
    "rolled-in_scale": "Rolled-in Scale",
    "scratches": "Scratches",
}
CLASS_COLORS = ["#63b3ed", "#68d391", "#f6ad55", "#fc8181", "#b794f4", "#76e4f7"]

# ── Load dataset summary ───────────────────────────────────────────────────────
@st.cache_data
def load_summary():
    p = PROJECT_ROOT / "results" / "dataset" / "dataset_summary.json"
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return None

@st.cache_data
def get_class_counts():
    counts = {}
    for split, base in [("train", TRAIN_IMAGES_PATH), ("validation", VALIDATION_IMAGES_PATH)]:
        counts[split] = {}
        for cat in DEFECT_CATEGORIES:
            d = base / cat
            counts[split][cat] = len(list(d.glob("*.jpg"))) if d.exists() else 0
    return counts

@st.cache_data
def load_sample_images(category: str, split: str = "train", n: int = 5):
    base = TRAIN_IMAGES_PATH if split == "train" else VALIDATION_IMAGES_PATH
    paths = sorted((base / category).glob("*.jpg"))[:n]
    return [np.array(Image.open(p).convert("L")) for p in paths], [p.name for p in paths]

@st.cache_data
def get_intensity_stats(category: str, split: str = "train", n: int = 30):
    base = TRAIN_IMAGES_PATH if split == "train" else VALIDATION_IMAGES_PATH
    paths = sorted((base / category).glob("*.jpg"))[:n]
    all_pixels = []
    for p in paths:
        all_pixels.extend(np.array(Image.open(p).convert("L")).flatten().tolist())
    return all_pixels

summary = load_summary()
counts = get_class_counts()

# ── KPI Row ────────────────────────────────────────────────────────────────────
train_total = sum(counts["train"].values())
val_total   = sum(counts["validation"].values())
cols = st.columns(5)
kpis = [
    (train_total + val_total, "Total Images"),
    (6, "Defect Classes"),
    (train_total, "Train Images"),
    (val_total, "Validation Images"),
    ("200×200", "Image Resolution"),
]
for col, (val, label) in zip(cols, kpis):
    col.markdown(f'<div class="kpi-card"><div class="kpi-value">{val}</div><div class="kpi-label">{label}</div></div>', unsafe_allow_html=True)

st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

# ── Class Distribution ─────────────────────────────────────────────────────────
st.markdown('<div class="section-header"> Class Distribution</div>', unsafe_allow_html=True)
dist_col1, dist_col2 = st.columns([2, 1])

with dist_col1:
    cats = list(CLASS_DISPLAY.keys())
    train_vals = [counts["train"][c] for c in cats]
    val_vals   = [counts["validation"][c] for c in cats]
    display_names = [CLASS_DISPLAY[c] for c in cats]

    fig = go.Figure()
    fig.add_bar(name="Train", x=display_names, y=train_vals, marker_color="#63b3ed",
                text=train_vals, textposition="outside")
    fig.add_bar(name="Validation", x=display_names, y=val_vals, marker_color="#68d391",
                text=val_vals, textposition="outside")
    fig.update_layout(
        title="Images per Class per Split",
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
        font=dict(color="#e2e8f0"), height=380,
        xaxis=dict(gridcolor="rgba(99,179,237,.1)"),
        yaxis=dict(gridcolor="rgba(99,179,237,.1)"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig)

with dist_col2:
    fig2 = go.Figure(go.Pie(
        labels=display_names,
        values=train_vals,
        hole=0.42,
        marker_colors=CLASS_COLORS,
        textinfo="percent+label",
        textfont_size=11,
    ))
    fig2.update_layout(
        title="Train Split Distribution",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0"), height=380,
        showlegend=False,
    )
    st.plotly_chart(fig2)

st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

# ── Train / Val / Test Split info ─────────────────────────────────────────────
sp_path = PROJECT_ROOT / "results" / "models" / "split_info.json"
if sp_path.exists():
    st.markdown('<div class="section-header"> Train / Validation / Test Split</div>', unsafe_allow_html=True)
    with open(sp_path) as f:
        sp = json.load(f)

    sp_cols = st.columns(3)
    for col, (split_name, n_samples, color) in zip(sp_cols, [
        ("Training", sp["train_samples"], "#63b3ed"),
        ("Validation", sp["val_samples"], "#68d391"),
        ("Test", sp["test_samples"], "#f6ad55"),
    ]):
        pct = n_samples / (sp["train_samples"] + sp["val_samples"] + sp["test_samples"]) * 100
        col.markdown(f"""
        <div class="kpi-card" style="border-color:{color}44;">
            <div class="kpi-value" style="background:linear-gradient(135deg,{color},{color}aa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">{n_samples}</div>
            <div class="kpi-label">{split_name} Samples ({pct:.1f}%)</div>
        </div>""", unsafe_allow_html=True)

    # Per-class split table
    rows = []
    for cat in DEFECT_CATEGORIES:
        rows.append({
            "Class": CLASS_DISPLAY[cat],
            "Train": sp["train_class_distribution"].get(cat, "—"),
            "Validation": sp["val_class_distribution"].get(cat, "—"),
            "Test": sp["test_class_distribution"].get(cat, "—"),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

# ── Sample Image Browser ───────────────────────────────────────────────────────
st.markdown('<div class="section-header"> Sample Image Browser</div>', unsafe_allow_html=True)
sel_col1, sel_col2 = st.columns([1, 3])
with sel_col1:
    selected_cat = st.selectbox(
        "Select Defect Category",
        DEFECT_CATEGORIES,
        format_func=lambda c: CLASS_DISPLAY[c]
    )
    selected_split = st.radio("Split", ["train", "validation"])
    n_show = st.slider("Images to show", 3, 10, 6)

with sel_col2:
    imgs, names = load_sample_images(selected_cat, selected_split, n_show)
    img_cols = st.columns(min(n_show, 6))
    for i, (img, name) in enumerate(zip(imgs, names)):
        with img_cols[i % 6]:
            st.image(img, caption=name[:18], use_container_width=True, clamp=True)

st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

# ── Pixel Intensity Analysis ───────────────────────────────────────────────────
st.markdown('<div class="section-header"> Pixel Intensity Analysis</div>', unsafe_allow_html=True)
int_col1, int_col2 = st.columns(2)

with int_col1:
    # Histogram per class
    fig_hist = go.Figure()
    for i, cat in enumerate(DEFECT_CATEGORIES):
        pixels = get_intensity_stats(cat, "train", 15)
        fig_hist.add_trace(go.Histogram(
            x=pixels, name=CLASS_DISPLAY[cat],
            opacity=0.6, nbinsx=50,
            marker_color=CLASS_COLORS[i],
        ))
    fig_hist.update_layout(
        title="Pixel Intensity Distribution by Class",
        barmode="overlay",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
        font=dict(color="#e2e8f0"), height=380,
        xaxis_title="Pixel Intensity (0–255)",
        yaxis_title="Count",
        xaxis=dict(gridcolor="rgba(99,179,237,.1)"),
        yaxis=dict(gridcolor="rgba(99,179,237,.1)"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig_hist)

with int_col2:
    # Box plot of mean intensities per class
    means_data = []
    for cat in DEFECT_CATEGORIES:
        base = TRAIN_IMAGES_PATH
        paths = sorted((base / cat).glob("*.jpg"))[:50]
        means = [np.array(Image.open(p).convert("L")).mean() for p in paths]
        for m in means:
            means_data.append({"Class": CLASS_DISPLAY[cat], "Mean Intensity": m})
    df_means = pd.DataFrame(means_data)
    fig_box = px.box(df_means, x="Class", y="Mean Intensity",
                     color="Class", color_discrete_sequence=CLASS_COLORS,
                     title="Mean Pixel Intensity per Class (train, 50 images)")
    fig_box.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
        font=dict(color="#e2e8f0"), height=380, showlegend=False,
        xaxis=dict(gridcolor="rgba(99,179,237,.1)", tickangle=-20),
        yaxis=dict(gridcolor="rgba(99,179,237,.1)"),
    )
    st.plotly_chart(fig_box)

st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

# ── Average Image per Class ────────────────────────────────────────────────────
st.markdown('<div class="section-header"> Average Image per Class</div>', unsafe_allow_html=True)
avg_cols = st.columns(6)
for i, cat in enumerate(DEFECT_CATEGORIES):
    paths = sorted((TRAIN_IMAGES_PATH / cat).glob("*.jpg"))[:30]
    if paths:
        avg_img = np.mean([np.array(Image.open(p).convert("L"), dtype=np.float32) for p in paths], axis=0).astype(np.uint8)
        avg_cols[i].image(avg_img, caption=CLASS_DISPLAY[cat], use_container_width=True, clamp=True)

st.caption("Q-ImageLab | Dataset Explorer | All images from NEU Surface Defect Database")
