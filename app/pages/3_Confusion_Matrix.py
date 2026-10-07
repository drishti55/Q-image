"""
Confusion Matrix — Interactive Per-Model Confusion Matrices
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
from config.settings import DEFECT_CATEGORIES

st.set_page_config(page_title="Confusion Matrix | Q-ImageLab", page_icon="", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* { font-family: 'Inter', sans-serif !important; }
.material-symbols-rounded, .material-icons, [class*="stIcon"], [data-testid="stIconMaterial"], i, svg { font-family: 'Material Symbols Rounded' !important; }
.stApp { background: linear-gradient(135deg, #0a0a1a 0%, #0d1b2a 50%, #0a0f1e 100%); }
section[data-testid="stSidebar"] { background: linear-gradient(180deg,#0d1b2a,#0a1020); border-right:1px solid rgba(99,179,237,.15); }
section[data-testid="stSidebar"] * { color:#e2e8f0 !important; }
.section-header { color:#e2e8f0; font-size:1.35rem; font-weight:700; border-bottom:2px solid rgba(99,179,237,.3); padding-bottom:8px; margin:24px 0 16px 0; }
.q-divider { height:1px; background:linear-gradient(90deg,transparent,rgba(99,179,237,.3),transparent); margin:20px 0; }
[data-testid="stDataFrame"] { background: rgba(13,27,42,0.8) !important; }
[data-testid="stDataFrame"] th { background: rgba(26,41,66,0.9) !important; color: #90cdf4 !important; font-weight: 700 !important; font-size: 0.82rem !important; }
[data-testid="stDataFrame"] td { color: #e2e8f0 !important; font-size: 0.82rem !important; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 style="color:#90cdf4;font-weight:800;font-size:2rem;"> Confusion Matrix</h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#94a3b8;">Interactive confusion matrices for all trained models — actual test set predictions</p>', unsafe_allow_html=True)
st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

MODELS_PATH = PROJECT_ROOT / "results" / "models"
CLASS_DISPLAY = [c.replace("_"," ").replace("-"," ").title() for c in DEFECT_CATEGORIES]

@st.cache_data
def load_all_cm():
    cms = {}
    cm_dir = MODELS_PATH / "confusion_matrices"
    if not cm_dir.exists():
        return cms
    for f in cm_dir.glob("*.json"):
        with open(f) as fp:
            data = json.load(fp)
        model_name = data["model"]
        cms[model_name] = np.array(data["matrix"])
    return cms

@st.cache_data
def load_model_comparison():
    p = MODELS_PATH / "model_comparison.csv"
    if p.exists():
        return pd.read_csv(p)
    return pd.DataFrame()

cms = load_all_cm()
df = load_model_comparison()

if not cms:
    st.warning(" Confusion matrices not found. Run the ML pipeline first.")
    st.stop()

# Model selector
sel_model = st.selectbox("Select Model", list(cms.keys()), key="cm_model")
cm = cms[sel_model]

# Sidebar options
normalize = st.sidebar.toggle("Normalize (row-wise)", value=False)

if normalize:
    row_sums = cm.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    cm_plot = cm.astype(float) / row_sums
    fmt_text = [[f"{v:.2f}" for v in row] for row in cm_plot]
    title_extra = " (Normalized)"
    zmin, zmax = 0.0, 1.0
else:
    cm_plot = cm.astype(float)
    fmt_text = [[str(int(v)) for v in row] for row in cm]
    title_extra = " (Raw Counts)"
    zmin, zmax = 0, float(cm.max())

# ── Main Confusion Matrix Plot ─────────────────────────────────────────────────
st.markdown(f'<div class="section-header">Confusion Matrix: {sel_model}{title_extra}</div>', unsafe_allow_html=True)


def make_annotated_heatmap(z_data, x_labels, y_labels, text_matrix, colorscale="Blues", zmin=0, zmax=1):
    """
    Build an annotated heatmap using go.Heatmap + Scatter annotations.
    Replaces the removed plotly.figure_factory.create_annotated_heatmap.
    """
    n = len(z_data)
    annotations = []
    for i in range(n):
        for j in range(n):
            val = z_data[i][j]
            # Use white text on dark cells, dark text on light cells
            text_color = "#ffffff" if val < (zmax * 0.6) else "#0a0a1a"
            annotations.append(dict(
                x=j, y=i,
                text=f"<b>{text_matrix[i][j]}</b>",
                showarrow=False,
                font=dict(color=text_color, size=13, family="Inter"),
                xref="x", yref="y",
            ))

    fig = go.Figure(go.Heatmap(
        z=z_data,
        x=x_labels,
        y=y_labels,
        colorscale=colorscale,
        showscale=True,
        zmin=zmin,
        zmax=zmax,
        colorbar=dict(
            tickfont=dict(color="#e2e8f0", size=11),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(99,179,237,0.3)",
        ),
    ))
    fig.update_layout(annotations=annotations)
    return fig


fig = make_annotated_heatmap(
    z_data=cm_plot.tolist(),
    x_labels=CLASS_DISPLAY,
    y_labels=CLASS_DISPLAY,
    text_matrix=fmt_text,
    colorscale="Blues",
    zmin=zmin,
    zmax=zmax,
)
fig.update_layout(
    title=dict(
        text=f"<b>{sel_model}</b> — Test Set Confusion Matrix",
        font=dict(color="#e2e8f0", size=16),
    ),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(13,27,42,0.8)",
    font=dict(color="#e2e8f0", size=12),
    height=540,
    xaxis=dict(
        title=dict(text="<b>Predicted Label</b>", font=dict(color="#94a3b8", size=13)),
        tickangle=-25,
        gridcolor="rgba(99,179,237,.08)",
        tickfont=dict(color="#e2e8f0", size=12),
    ),
    yaxis=dict(
        title=dict(text="<b>True Label</b>", font=dict(color="#94a3b8", size=13)),
        autorange="reversed",
        gridcolor="rgba(99,179,237,.08)",
        tickfont=dict(color="#e2e8f0", size=12),
    ),
    margin=dict(l=120, r=60, t=60, b=120),
)
st.plotly_chart(fig, use_container_width=True)

# ── Derived metrics ────────────────────────────────────────────────────────────
st.markdown('<div class="section-header"> Per-Class Statistics from Confusion Matrix</div>', unsafe_allow_html=True)

rows = []
for i, cls in enumerate(DEFECT_CATEGORIES):
    tp = cm[i, i]
    fp = cm[:, i].sum() - tp
    fn = cm[i, :].sum() - tp
    tn = cm.sum() - tp - fp - fn
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0
    rec  = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1   = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
    acc_cls = (tp + tn) / cm.sum() if cm.sum() > 0 else 0
    rows.append({
        "Class": CLASS_DISPLAY[i],
        "TP": int(tp), "FP": int(fp), "FN": int(fn), "TN": int(tn),
        "Precision": f"{float(prec):.4f}",
        "Recall": f"{float(rec):.4f}",
        "F1-Score": f"{float(f1):.4f}",
    })

df_stats = pd.DataFrame(rows)
st.dataframe(
    df_stats,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Class": st.column_config.TextColumn("Class", width="medium"),
        "TP": st.column_config.NumberColumn(" TP", help="True Positives"),
        "FP": st.column_config.NumberColumn(" FP", help="False Positives"),
        "FN": st.column_config.NumberColumn(" FN", help="False Negatives"),
        "TN": st.column_config.NumberColumn(" TN", help="True Negatives"),
        "Precision": st.column_config.TextColumn("Precision"),
        "Recall": st.column_config.TextColumn("Recall"),
        "F1-Score": st.column_config.TextColumn("F1-Score"),
    }
)

st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

# ── All models side-by-side (small thumbnails) ─────────────────────────────────
st.markdown('<div class="section-header"> All Models — Quick Comparison (Normalized)</div>', unsafe_allow_html=True)
all_model_names = list(cms.keys())
thumb_cols = st.columns(len(all_model_names))
for col, mname in zip(thumb_cols, all_model_names):
    cm_m = cms[mname].astype(float)
    row_sums = cm_m.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    cm_norm = cm_m / row_sums

    # Build mini annotations
    ann_mini = []
    for i in range(len(cm_norm)):
        for j in range(len(cm_norm[i])):
            val = cm_norm[i][j]
            c = "#ffffff" if val < 0.55 else "#0a0a1a"
            ann_mini.append(dict(
                x=j, y=i,
                text=f"{val:.2f}",
                showarrow=False,
                font=dict(color=c, size=7, family="Inter"),
                xref="x", yref="y",
            ))

    fig_t = go.Figure(go.Heatmap(
        z=cm_norm.tolist(), colorscale="Blues", showscale=False,
        x=CLASS_DISPLAY, y=CLASS_DISPLAY,
        zmin=0, zmax=1,
    ))
    fig_t.update_layout(annotations=ann_mini)

    acc_str = ""
    if not df.empty:
        row = df[df["model"] == mname]
        if not row.empty:
            acc_str = f"<br><sub>{row['test_accuracy'].values[0]:.3f} test acc</sub>"
    fig_t.update_layout(
        title=dict(text=f"<b>{mname}</b>{acc_str}", font=dict(color="#e2e8f0", size=11)),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
        font=dict(color="#e2e8f0", size=8), height=320,
        xaxis=dict(tickangle=-35, tickfont=dict(size=7, color="#94a3b8")),
        yaxis=dict(autorange="reversed", tickfont=dict(size=7, color="#94a3b8")),
        margin=dict(l=70, r=10, t=55, b=70),
    )
    col.plotly_chart(fig_t, use_container_width=True)

st.caption("Q-ImageLab | Confusion Matrix | All results from actual model predictions on test set")
