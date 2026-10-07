"""
Quantum Image Lab — Interactive FRQI/NEQR Processing on NEU-DET Images
Simulation runs in an isolated subprocess to protect the Streamlit process from
Qiskit-Aer segfaults (known issue on macOS ARM with large statevectors).
"""

import streamlit as st
import numpy as np
import json
import subprocess
import sys
import time
import plotly.graph_objects as go
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
from config.settings import DEFECT_CATEGORIES, TRAIN_IMAGES_PATH, VALIDATION_IMAGES_PATH

st.set_page_config(page_title="Quantum Lab | Q-ImageLab", page_icon="", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* { font-family: 'Inter', sans-serif !important; }
.material-symbols-rounded, .material-icons, [class*="stIcon"], [data-testid="stIconMaterial"], i, svg { font-family: 'Material Symbols Rounded' !important; }
.stApp { background: linear-gradient(135deg, #0a0a1a 0%, #0d1b2a 50%, #0a0f1e 100%); }
section[data-testid="stSidebar"] { background: linear-gradient(180deg,#0d1b2a,#0a1020); border-right:1px solid rgba(99,179,237,.15); }
section[data-testid="stSidebar"] * { color:#e2e8f0 !important; }
.kpi-card { background:linear-gradient(135deg,rgba(26,41,66,.9),rgba(17,25,40,.95)); border:1px solid rgba(99,179,237,.25); border-radius:16px; padding:20px; text-align:center; margin:8px 0; }
.kpi-value { font-size:1.8rem; font-weight:800; background:linear-gradient(135deg,#63b3ed,#90cdf4); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }
.kpi-label { font-size:.75rem; color:#94a3b8; text-transform:uppercase; letter-spacing:.08em; font-weight:500; margin-top:4px; }
.section-header { color:#e2e8f0; font-size:1.35rem; font-weight:700; border-bottom:2px solid rgba(99,179,237,.3); padding-bottom:8px; margin:24px 0 16px 0; }
.q-divider { height:1px; background:linear-gradient(90deg,transparent,rgba(99,179,237,.3),transparent); margin:20px 0; }
.pipeline-step { background:rgba(26,41,66,.7); border:1px solid rgba(99,179,237,.2); border-radius:10px; padding:12px 16px; margin:6px 0; color:#90cdf4; font-weight:600; font-size:.9rem; }
.pipeline-step.done { border-color:rgba(72,187,120,.4); color:#68d391; }
.pipeline-step.running { border-color:rgba(245,158,11,.4); color:#f6ad55; }
.warn-box { background:rgba(245,158,11,.08); border:1px solid rgba(245,158,11,.3); border-radius:10px; padding:12px 16px; color:#f6ad55; font-size:.85rem; margin:10px 0; }
</style>
""", unsafe_allow_html=True)

CLASS_DISPLAY = {c: c.replace("_"," ").replace("-"," ").title() for c in DEFECT_CATEGORIES}
WORKER_PATH = Path(__file__).parent.parent / "_quantum_worker.py"
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python3"
PYTHON_EXE = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

st.markdown('<h1 style="color:#90cdf4;font-weight:800;font-size:2rem;"> Quantum Image Lab</h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#94a3b8;">Select an NEU-DET image or upload your own, then run FRQI/NEQR quantum processing</p>', unsafe_allow_html=True)
st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

# ── Sidebar Configuration ──────────────────────────────────────────────────────
st.sidebar.markdown("###  Experiment Configuration")

img_source = st.sidebar.radio("Image Source", ["NEU-DET Dataset", "Upload Image"])

raw_image = None
image_label = "custom"
image_category = "—"

if img_source == "NEU-DET Dataset":
    category = st.sidebar.selectbox("Defect Category", DEFECT_CATEGORIES, format_func=lambda c: CLASS_DISPLAY[c])
    split = st.sidebar.radio("Split", ["train", "validation"], horizontal=True)
    base = TRAIN_IMAGES_PATH if split == "train" else VALIDATION_IMAGES_PATH
    img_paths = sorted((base / category).glob("*.jpg"))
    if img_paths:
        img_names = [p.name for p in img_paths]
        sel_name = st.sidebar.selectbox("Image", img_names)
        sel_path = base / category / sel_name
        raw_image = np.array(Image.open(sel_path).convert("L"))
        image_label = sel_name
        image_category = CLASS_DISPLAY[category]
    else:
        st.sidebar.error("No images found in this category/split")
else:
    uploaded = st.sidebar.file_uploader("Upload Image", type=["jpg","jpeg","png","bmp"])
    if uploaded:
        raw_image = np.array(Image.open(uploaded).convert("L"))
        image_label = uploaded.name

st.sidebar.markdown("---")
representation = st.sidebar.selectbox("Representation", ["FRQI", "NEQR"])
size_n = st.sidebar.selectbox("Resolution", [2, 4, 8, 16, 32], index=1, format_func=lambda n: f"{n}×{n}")
bits   = st.sidebar.selectbox("Intensity Precision", [2, 4, 8], index=2, format_func=lambda b: f"{b}-bit ({2**b} levels)")
sim_mode = st.sidebar.radio("Simulation Mode", ["Statevector (Exact)", "Shot-based"])
shots = None
if "Shot" in sim_mode:
    shots = st.sidebar.select_slider("Measurement Shots", options=[100, 500, 1000, 5000], value=1000)
use_sv = "Exact" in sim_mode

# Warn about large circuits before run
qubit_estimate = (size_n.bit_length() - 1) * 2 + 1  # rough
if use_sv and size_n >= 8:
    st.sidebar.markdown(
        f'<div class="warn-box"> <b>{size_n}×{size_n} Statevector</b>: extremely large circuit — simulation may be very slow or time out. '
        'Consider using Shot-based mode instead.</div>',
        unsafe_allow_html=True
    )

run_btn = st.sidebar.button(" RUN QUANTUM EXPERIMENT", type="primary")

# ── Main layout ────────────────────────────────────────────────────────────────
config_col, preview_col = st.columns([2, 1])

with config_col:
    st.markdown('<div class="section-header"> Experiment Configuration</div>', unsafe_allow_html=True)
    cfg_data = {
        "Representation": representation,
        "Resolution": f"{size_n}×{size_n} ({size_n**2} pixels)",
        "Intensity Precision": f"{bits}-bit ({2**bits} levels)",
        "Simulation": sim_mode,
        "Shots": shots if shots else "N/A",
        "Image": image_label,
        "Category": image_category,
    }
    for k, v in cfg_data.items():
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;padding:6px 0;'
            f'border-bottom:1px solid rgba(99,179,237,.1);">'
            f'<span style="color:#94a3b8;font-size:.85rem;">{k}</span>'
            f'<span style="color:#90cdf4;font-weight:600;font-size:.85rem;">{v}</span></div>',
            unsafe_allow_html=True
        )

with preview_col:
    if raw_image is not None:
        st.markdown('<div class="section-header"> Source Image</div>', unsafe_allow_html=True)
        st.image(raw_image, caption=f"{image_label} ({raw_image.shape[1]}×{raw_image.shape[0]})",
                 use_container_width=True, clamp=True)
    else:
        st.info("Select an image from the sidebar to begin.")

st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

# ── Run Experiment (isolated subprocess) ───────────────────────────────────────
if run_btn:
    if raw_image is None:
        st.error("Please select or upload an image first.")
        st.stop()

    st.markdown('<div class="section-header"> Pipeline Execution</div>', unsafe_allow_html=True)

    steps = [
        "Preprocessing",
        "Quantum Encoding",
        "Circuit Build",
        "Simulation",
        "Measurement / Statevector",
        "Reconstruction",
        "Quality Analysis",
    ]
    step_ph = [st.empty() for _ in steps]

    def set_step(idx, status="running"):
        css  = "running" if status == "running" else "done"
        icon = "" if status == "running" else ""
        step_ph[idx].markdown(
            f'<div class="pipeline-step {css}">{icon} {steps[idx]}</div>',
            unsafe_allow_html=True,
        )

    for i in range(3):
        set_step(i, "running")

    # Build params for subprocess
    params = {
        "representation": representation,
        "size_n": size_n,
        "bits": bits,
        "use_sv": use_sv,
        "shots": shots if shots else 1000,
        "raw_image": raw_image.tolist(),
    }

    set_step(3, "running")
    set_step(4, "running")

    progress_ph = st.empty()
    progress_ph.info(" Running quantum simulation in isolated process…")

    t_start = time.perf_counter()

    try:
        proc = subprocess.run(
            [PYTHON_EXE, str(WORKER_PATH)],
            input=json.dumps(params),
            capture_output=True,
            text=True,
            timeout=300,  # 5-minute timeout
        )

        elapsed = time.perf_counter() - t_start

        if proc.returncode != 0 and not proc.stdout.strip():
            progress_ph.error(
                f" Simulation process crashed (exit code {proc.returncode}). "
                f"This is usually a Qiskit-Aer memory limit with large circuits. "
                f"Try a smaller resolution (4×4) or Shot-based mode.\n\n"
                f"```\n{proc.stderr[-2000:]}\n```"
            )
            st.stop()

        result = json.loads(proc.stdout)

        if not result.get("ok"):
            progress_ph.error(" Simulation failed inside worker:")
            st.code(result.get("error", "Unknown error"))
            st.stop()

    except subprocess.TimeoutExpired:
        progress_ph.error(" Simulation timed out (>5 min). Use a smaller resolution or Shot-based mode.")
        st.stop()
    except Exception as e:
        progress_ph.error(f" Could not launch simulation process: {e}")
        st.stop()

    # Mark all steps done
    for i in range(len(steps)):
        set_step(i, "done")
    progress_ph.success(f" Simulation completed in {elapsed:.2f}s")

    # ── Unpack results ─────────────────────────────────────────────────────────
    stats       = result["stats"]
    quality     = result["quality"]
    enc_time    = result["enc_time"]
    sim_time    = result["sim_time"]
    meas_time   = result["meas_time"]
    rec_time    = result["rec_time"]
    resized     = np.array(result["resized"], dtype=np.uint8)
    disp_recon  = np.array(result["disp_recon"], dtype=np.uint8)
    diff_disp   = np.array(result["diff_disp"], dtype=np.uint8)

    st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-header"> Results</div>', unsafe_allow_html=True)

    # Image comparison
    img_c1, img_c2, img_c3 = st.columns(3)
    with img_c1:
        st.markdown('<p style="color:#90cdf4;font-weight:600;text-align:center;">Original (Preprocessed)</p>', unsafe_allow_html=True)
        st.image(resized, use_container_width=True, clamp=True)
        st.caption(f"Size: {size_n}×{size_n} | {bits}-bit")
    with img_c2:
        st.markdown(f'<p style="color:#90cdf4;font-weight:600;text-align:center;">{representation} Reconstructed</p>', unsafe_allow_html=True)
        st.image(disp_recon, use_container_width=True, clamp=True)
        st.caption(f"MSE: {quality['mse']:.6f} | PSNR: {quality['psnr']:.2f} dB")
    with img_c3:
        st.markdown('<p style="color:#90cdf4;font-weight:600;text-align:center;">Error / Difference</p>', unsafe_allow_html=True)
        st.image(diff_disp, use_container_width=True, clamp=True)
        st.caption(f"SSIM: {quality['ssim']:.4f}")

    st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

    # Metrics KPIs
    st.markdown('<div class="section-header"> Quantum Resource & Quality Metrics</div>', unsafe_allow_html=True)
    metric_cols = st.columns(5)
    for col, (val, label) in zip(metric_cols, [
        (stats["qubits"],           "Total Qubits"),
        (stats["gates"],            "Total Gates"),
        (stats["depth"],            "Circuit Depth"),
        (stats["controlled_gates"], "Controlled Gates"),
        (f"{enc_time:.4f}s",        "Encoding Time"),
    ]):
        col.markdown(
            f'<div class="kpi-card"><div class="kpi-value">{val}</div>'
            f'<div class="kpi-label">{label}</div></div>',
            unsafe_allow_html=True
        )

    metric_cols2 = st.columns(5)
    for col, (val, label) in zip(metric_cols2, [
        (f"{sim_time:.4f}s",         "Simulation Time"),
        (f"{meas_time:.4f}s",        "Measurement Time"),
        (f"{rec_time:.4f}s",         "Reconstruction Time"),
        (f"{quality['mse']:.6f}",    "MSE"),
        (f"{quality['psnr']:.2f} dB","PSNR"),
    ]):
        col.markdown(
            f'<div class="kpi-card"><div class="kpi-value" style="font-size:1.4rem;">{val}</div>'
            f'<div class="kpi-label">{label}</div></div>',
            unsafe_allow_html=True
        )

    st.markdown(f"""
    <div style="background:rgba(26,41,66,.6);border:1px solid rgba(99,179,237,.2);border-radius:12px;padding:16px;margin:12px 0;">
        <span style="color:#63b3ed;font-weight:700;font-size:1.1rem;">SSIM: {quality['ssim']:.6f}</span>
        <span style="color:#94a3b8;font-size:.85rem;margin-left:16px;">
        (1.0 = perfect reconstruction | 0.0 = no structural similarity)
        </span>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

    # Gate types breakdown
    st.markdown('<div class="section-header"> Gate Type Breakdown</div>', unsafe_allow_html=True)
    gate_types = stats.get("gate_types", {})
    if gate_types:
        fig_gates = go.Figure(go.Bar(
            x=list(gate_types.keys()), y=list(gate_types.values()),
            marker_color="#63b3ed",
            text=list(gate_types.values()), textposition="outside",
        ))
        fig_gates.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
            font=dict(color="#e2e8f0"), height=300,
            xaxis=dict(gridcolor="rgba(99,179,237,.1)"),
            yaxis=dict(gridcolor="rgba(99,179,237,.1)"),
            xaxis_title="Gate Type", yaxis_title="Count",
            title=f"{representation} Circuit — Gate Composition",
        )
        st.plotly_chart(fig_gates, use_container_width=True)

    # Store in session for comparison pages
    st.session_state["last_quantum_result"] = {
        "representation": representation,
        "size": size_n,
        "bits": bits,
        "shots": shots,
        "stats": stats,
        "quality": quality,
        "image_label": image_label,
        "category": image_category,
        "enc_time": enc_time,
        "sim_time": sim_time,
        "meas_time": meas_time,
        "rec_time": rec_time,
    }

elif not run_btn and raw_image is not None:
    st.info(" Configure your experiment in the sidebar and click **RUN QUANTUM EXPERIMENT**")

st.caption("Q-ImageLab | Quantum Image Lab | FRQI & NEQR quantum image processing with Qiskit Aer")
