"""
FRQI vs NEQR — Side-by-Side Quantum Representation Comparison
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from PIL import Image
import sys, time

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
from config.settings import DEFECT_CATEGORIES, TRAIN_IMAGES_PATH
from src.preprocessing.image_processor import ImageProcessor
from src.frqi.encoder import FRQIEncoder
from src.neqr.encoder import NEQREncoder
from src.simulation.simulator import QuantumSimulator
from src.reconstruction.reconstructor import FRQIReconstructor, NEQRReconstructor
from src.metrics.evaluator import MetricsEvaluator

st.set_page_config(page_title="FRQI vs NEQR | Q-ImageLab", page_icon="", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* { font-family: 'Inter', sans-serif !important; }
.material-symbols-rounded, .material-icons, [class*="stIcon"], [data-testid="stIconMaterial"], i, svg { font-family: 'Material Symbols Rounded' !important; }
.stApp { background: linear-gradient(135deg, #0a0a1a 0%, #0d1b2a 50%, #0a0f1e 100%); }
section[data-testid="stSidebar"] { background: linear-gradient(180deg,#0d1b2a,#0a1020); border-right:1px solid rgba(99,179,237,.15); }
section[data-testid="stSidebar"] * { color:#e2e8f0 !important; }
.frqi-card { background:linear-gradient(135deg,rgba(26,41,100,.85),rgba(17,25,60,.95)); border:1px solid rgba(99,179,237,.4); border-radius:16px; padding:20px; text-align:center; margin:6px 0; }
.neqr-card { background:linear-gradient(135deg,rgba(26,80,41,.85),rgba(17,50,25,.95)); border:1px solid rgba(104,211,145,.4); border-radius:16px; padding:20px; text-align:center; margin:6px 0; }
.frqi-val { font-size:1.8rem; font-weight:800; color:#63b3ed; }
.neqr-val { font-size:1.8rem; font-weight:800; color:#68d391; }
.card-label { font-size:.72rem; color:#94a3b8; text-transform:uppercase; letter-spacing:.08em; margin-top:4px; }
.section-header { color:#e2e8f0; font-size:1.35rem; font-weight:700; border-bottom:2px solid rgba(99,179,237,.3); padding-bottom:8px; margin:24px 0 16px 0; }
.q-divider { height:1px; background:linear-gradient(90deg,transparent,rgba(99,179,237,.3),transparent); margin:20px 0; }
</style>
""", unsafe_allow_html=True)

CLASS_DISPLAY = {c: c.replace("_"," ").replace("-"," ").title() for c in DEFECT_CATEGORIES}

st.markdown('<h1 style="color:#90cdf4;font-weight:800;font-size:2rem;"> FRQI vs NEQR Comparison</h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#94a3b8;">Run identical experiments on both encodings and compare all metrics side-by-side</p>', unsafe_allow_html=True)
st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

@st.cache_resource
def get_modules():
    return ImageProcessor(42), QuantumSimulator(42), MetricsEvaluator()

processor, simulator, metrics_eval = get_modules()

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.markdown("###  Comparison Configuration")
img_source = st.sidebar.radio("Image Source", ["NEU-DET Image", "Synthetic"])

raw_image = None
if img_source == "NEU-DET Image":
    cat = st.sidebar.selectbox("Category", DEFECT_CATEGORIES, format_func=lambda c: CLASS_DISPLAY[c])
    paths = sorted((TRAIN_IMAGES_PATH / cat).glob("*.jpg"))[:10]
    if paths:
        sel = st.sidebar.selectbox("Image", [p.name for p in paths])
        raw_image = np.array(Image.open(TRAIN_IMAGES_PATH / cat / sel).convert("L"))
        img_label = sel
else:
    pattern = st.sidebar.selectbox("Pattern", ["gradient","checkerboard","diagonal","uniform","random"])
    img_label = f"synthetic_{pattern}"

size_n = st.sidebar.selectbox("Resolution", [2, 4, 8, 16, 32], index=1, format_func=lambda n: f"{n}×{n}")
bits = st.sidebar.selectbox("Intensity Precision", [2, 4, 8], index=2, format_func=lambda b: f"{b}-bit")
sim_mode = st.sidebar.radio("Simulation", ["Statevector (Exact)", "Shot-based"])
shots = None
if "Shot" in sim_mode:
    shots = st.sidebar.select_slider("Shots", [100, 500, 1000, 5000], value=1000)
use_sv = "Exact" in sim_mode

compare_btn = st.sidebar.button(" RUN COMPARISON", type="primary")

# ── Saved results overview ─────────────────────────────────────────────────────
@st.cache_data
def load_saved():
    p = PROJECT_ROOT / "results" / "experiments" / "all_results.csv"
    if p.exists():
        df = pd.read_csv(p)
        df["psnr"] = pd.to_numeric(df["psnr"], errors="coerce").clip(0, 100)
        df["ssim"] = pd.to_numeric(df["ssim"], errors="coerce")
        return df
    return pd.DataFrame()

df_saved = load_saved()

if not df_saved.empty:
    st.markdown('<div class="section-header"> Aggregate Comparison (All Saved Experiments)</div>', unsafe_allow_html=True)
    agg = df_saved.groupby("representation")[["qubits","gate_count","circuit_depth",
                                               "encoding_time","simulation_time",
                                               "mse","psnr","ssim"]].mean().reset_index()
    # Side-by-side cards
    metrics_list = [
        ("qubits","Avg Qubits","{:.1f}"),
        ("gate_count","Avg Gates","{:.1f}"),
        ("circuit_depth","Avg Depth","{:.1f}"),
        ("encoding_time","Avg Enc Time (s)","{:.4f}"),
        ("simulation_time","Avg Sim Time (s)","{:.4f}"),
        ("mse","Avg MSE","{:.6f}"),
        ("psnr","Avg PSNR (dB)","{:.2f}"),
        ("ssim","Avg SSIM","{:.4f}"),
    ]
    frqi_row = agg[agg["representation"]=="FRQI"].iloc[0] if not agg[agg["representation"]=="FRQI"].empty else {}
    neqr_row = agg[agg["representation"]=="NEQR"].iloc[0] if not agg[agg["representation"]=="NEQR"].empty else {}

    n_cols = 4
    rows_m = [metrics_list[i:i+n_cols] for i in range(0, len(metrics_list), n_cols)]
    for row_m in rows_m:
        cols = st.columns(n_cols)
        for col, (field, label, fmt) in zip(cols, row_m):
            fv = fmt.format(frqi_row[field]) if field in frqi_row else "—"
            nv = fmt.format(neqr_row[field]) if field in neqr_row else "—"
            col.markdown(f"""
            <div style="background:rgba(17,25,40,.9);border:1px solid rgba(99,179,237,.2);border-radius:12px;padding:14px;text-align:center;margin:4px 0;">
                <div style="font-size:.7rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;">{label}</div>
                <div style="display:flex;justify-content:space-around;">
                    <div><div style="font-size:1rem;font-weight:700;color:#63b3ed;">{fv}</div><div style="font-size:.6rem;color:#94a3b8;">FRQI</div></div>
                    <div style="color:#4a5568;">|</div>
                    <div><div style="font-size:1rem;font-weight:700;color:#68d391;">{nv}</div><div style="font-size:.6rem;color:#94a3b8;">NEQR</div></div>
                </div>
            </div>""", unsafe_allow_html=True)

    # Charts
    st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)
    ch_col1, ch_col2 = st.columns(2)
    with ch_col1:
        chart_fields = ["qubits","gate_count","circuit_depth","psnr","ssim"]
        chart_labels = ["Qubits","Gates","Depth","PSNR","SSIM"]
        fig_bar = go.Figure()
        for rep, color in [("FRQI","#63b3ed"),("NEQR","#68d391")]:
            row = agg[agg["representation"]==rep]
            if not row.empty:
                vals_norm = []
                for f in chart_fields:
                    v = float(row[f].values[0])
                    vals_norm.append(v)
                fig_bar.add_trace(go.Bar(
                    name=rep, x=chart_labels, y=vals_norm,
                    marker_color=color, text=[f"{v:.2f}" for v in vals_norm],
                    textposition="outside",
                ))
        fig_bar.update_layout(
            title="Key Metrics Comparison (Avg)", barmode="group",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
            font=dict(color="#e2e8f0"), height=360,
            xaxis=dict(gridcolor="rgba(99,179,237,.1)"),
            yaxis=dict(gridcolor="rgba(99,179,237,.1)"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_bar)
    with ch_col2:
        if "resolution" in df_saved.columns:
            grp = df_saved.groupby(["representation","resolution"])[["qubits","gate_count"]].mean().reset_index()
            fig_line = go.Figure()
            for rep, color in [("FRQI","#63b3ed"),("NEQR","#68d391")]:
                sub = grp[grp["representation"]==rep]
                fig_line.add_trace(go.Scatter(x=sub["resolution"], y=sub["gate_count"],
                                              mode="lines+markers+text", name=rep,
                                              line_color=color, text=sub["gate_count"].round(0).astype(int),
                                              textposition="top center"))
            fig_line.update_layout(
                title="Gate Count vs Resolution",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
                font=dict(color="#e2e8f0"), height=360,
                xaxis=dict(title="Resolution", gridcolor="rgba(99,179,237,.1)"),
                yaxis=dict(title="Gates", gridcolor="rgba(99,179,237,.1)"),
                legend=dict(bgcolor="rgba(0,0,0,0)"),
            )
            st.plotly_chart(fig_line)

st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

# ── Live Comparison ────────────────────────────────────────────────────────────
if compare_btn:
    st.markdown('<div class="section-header"> Live Experiment Comparison</div>', unsafe_allow_html=True)
    size = (size_n, size_n)

    if img_source == "NEU-DET Image" and raw_image is not None:
        base_img = raw_image
    else:
        data = processor.create_synthetic_image(size, pattern if img_source=="Synthetic" else "gradient", bits)
        base_img = data["image"]

    prog = st.progress(0, text="Preprocessing...")
    resized   = processor.resize_image(base_img, size)
    quantized = processor.quantize_intensity(resized, bits)
    frqi_img  = processor.normalize_for_frqi(quantized, bits)
    neqr_img  = processor.normalize_for_neqr(quantized, bits)

    results = {}
    for i, (rep, img) in enumerate([("FRQI", frqi_img), ("NEQR", neqr_img)]):
        prog.progress(20 + i*40, text=f"Running {rep}...")
        try:
            if rep == "FRQI":
                enc = FRQIEncoder(img)
            else:
                enc = NEQREncoder(img, intensity_bits=bits)
            circ = enc.build_circuit()
            stats = enc.get_circuit_stats()
            t0 = time.perf_counter()
            if use_sv:
                sr = simulator.run_statevector(circ)
                sim_time = sr["simulation_time"]
                meas_time = 0.0
                rec_f = FRQIReconstructor(enc.n_position_qubits, img.shape) if rep=="FRQI" else \
                        NEQRReconstructor(enc.n_position_qubits, enc.n_intensity_qubits, img.shape)
                recon = rec_f.reconstruct_from_statevector(sr["statevector"])
            else:
                sr = simulator.run_shots(circ, shots)
                sim_time = sr["simulation_time"]
                meas_time = sr["measurement_time"]
                rec_f = FRQIReconstructor(enc.n_position_qubits, img.shape) if rep=="FRQI" else \
                        NEQRReconstructor(enc.n_position_qubits, enc.n_intensity_qubits, img.shape)
                recon = rec_f.reconstruct_from_counts(sr["counts"], shots)
            recon_img = recon["image"]
            if rep=="FRQI":
                quality = metrics_eval.compute_image_quality(img, recon_img, max_val=1.0)
            else:
                quality = metrics_eval.compute_image_quality(img.astype(np.float64),
                                                              recon_img.astype(np.float64),
                                                              max_val=float(2**bits-1))
            results[rep] = {"stats": stats, "quality": quality,
                            "sim_time": sim_time, "meas_time": meas_time,
                            "enc_time": stats["encoding_time"]}
        except Exception as e:
            st.error(f"{rep} failed: {e}")

    prog.progress(100, text="Complete!")

    if len(results) == 2:
        st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)
        # Comparison table
        compare_rows = [
            ("Qubits", results["FRQI"]["stats"]["qubits"], results["NEQR"]["stats"]["qubits"]),
            ("Gates", results["FRQI"]["stats"]["gates"], results["NEQR"]["stats"]["gates"]),
            ("Circuit Depth", results["FRQI"]["stats"]["depth"], results["NEQR"]["stats"]["depth"]),
            ("Controlled Gates", results["FRQI"]["stats"]["controlled_gates"], results["NEQR"]["stats"]["controlled_gates"]),
            ("Encoding Time (s)", f"{results['FRQI']['enc_time']:.4f}", f"{results['NEQR']['enc_time']:.4f}"),
            ("Simulation Time (s)", f"{results['FRQI']['sim_time']:.4f}", f"{results['NEQR']['sim_time']:.4f}"),
            ("MSE", f"{results['FRQI']['quality']['mse']:.6f}", f"{results['NEQR']['quality']['mse']:.6f}"),
            ("PSNR (dB)", f"{results['FRQI']['quality']['psnr']:.2f}", f"{results['NEQR']['quality']['psnr']:.2f}"),
            ("SSIM", f"{results['FRQI']['quality']['ssim']:.4f}", f"{results['NEQR']['quality']['ssim']:.4f}"),
        ]
        df_table = pd.DataFrame(compare_rows, columns=["Parameter","FRQI","NEQR"])
        st.dataframe(df_table, use_container_width=True, hide_index=True)

        # Visual bar comparison
        params = [r[0] for r in compare_rows]
        fig_comp = go.Figure()
        for rep, color in [("FRQI","#63b3ed"),("NEQR","#68d391")]:
            vals = [results[rep]["stats"].get(f, results[rep]["quality"].get(f, 0)) for f in
                    ["qubits","gates","depth","controlled_gates"]]
            fig_comp.add_trace(go.Bar(name=rep, x=["Qubits","Gates","Depth","Ctrl Gates"],
                                      y=vals, marker_color=color,
                                      text=[str(v) for v in vals], textposition="outside"))
        fig_comp.update_layout(
            title="FRQI vs NEQR — Resource Comparison",
            barmode="group",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
            font=dict(color="#e2e8f0"), height=340,
            xaxis=dict(gridcolor="rgba(99,179,237,.1)"),
            yaxis=dict(gridcolor="rgba(99,179,237,.1)"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_comp)

st.caption("Q-ImageLab | FRQI vs NEQR | Actual quantum circuit execution and comparison")
