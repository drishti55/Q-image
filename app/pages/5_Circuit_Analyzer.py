"""
Circuit Analyzer — Quantum Circuit Inspection for FRQI and NEQR
Runs Qiskit logic in an isolated subprocess to prevent rust/C++ segfaults.
"""

import streamlit as st
import numpy as np
import plotly.graph_objects as go
import json
import subprocess
import sys
import time
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
from config.settings import DEFECT_CATEGORIES, TRAIN_IMAGES_PATH
from src.preprocessing.image_processor import ImageProcessor

st.set_page_config(page_title="Circuit Analyzer | Q-ImageLab", page_icon="", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* { font-family: 'Inter', sans-serif !important; }
.material-symbols-rounded, .material-icons, [class*="stIcon"], [data-testid="stIconMaterial"], i, svg { font-family: 'Material Symbols Rounded' !important; }
.stApp { background: linear-gradient(135deg, #0a0a1a 0%, #0d1b2a 50%, #0a0f1e 100%); }
section[data-testid="stSidebar"] { background: linear-gradient(180deg,#0d1b2a,#0a1020); border-right:1px solid rgba(99,179,237,.15); }
section[data-testid="stSidebar"] * { color:#e2e8f0 !important; }
.kpi-card { background:linear-gradient(135deg,rgba(26,41,66,.9),rgba(17,25,40,.95)); border:1px solid rgba(99,179,237,.25); border-radius:16px; padding:16px; text-align:center; margin:6px 0; }
.kpi-value { font-size:1.9rem; font-weight:800; background:linear-gradient(135deg,#63b3ed,#90cdf4); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }
.kpi-label { font-size:.75rem; color:#94a3b8; text-transform:uppercase; letter-spacing:.08em; font-weight:500; margin-top:4px; }
.section-header { color:#e2e8f0; font-size:1.35rem; font-weight:700; border-bottom:2px solid rgba(99,179,237,.3); padding-bottom:8px; margin:24px 0 16px 0; }
.q-divider { height:1px; background:linear-gradient(90deg,transparent,rgba(99,179,237,.3),transparent); margin:20px 0; }
.circuit-text { font-family:'Courier New',monospace !important; background:rgba(13,27,42,.9); color:#90cdf4; padding:16px; border-radius:10px; border:1px solid rgba(99,179,237,.2); font-size:.75rem; overflow-x:auto; white-space:pre; }
.formula-box { background:rgba(26,41,66,.7); border:1px solid rgba(99,179,237,.25); border-radius:12px; padding:16px; margin:10px 0; color:#e2e8f0; font-size:.88rem; }
</style>
""", unsafe_allow_html=True)

CLASS_DISPLAY = {c: c.replace("_"," ").replace("-"," ").title() for c in DEFECT_CATEGORIES}

WORKER_PATH = Path(__file__).parent.parent / "_analyzer_worker.py"
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python3"
PYTHON_EXE = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

st.markdown('<h1 style="color:#90cdf4;font-weight:800;font-size:2rem;"> Circuit Analyzer</h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#94a3b8;">Inspect FRQI and NEQR quantum circuits, gate compositions, and resource scaling</p>', unsafe_allow_html=True)
st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

@st.cache_resource
def get_processor():
    return ImageProcessor(random_seed=42)

processor = get_processor()

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.markdown("###  Circuit Parameters")
representation = st.sidebar.selectbox("Representation", ["FRQI", "NEQR", "Both"])
size_n = st.sidebar.selectbox("Resolution", [2, 4, 8, 16, 32], index=1, format_func=lambda n: f"{n}×{n}")
bits = st.sidebar.selectbox("Intensity Precision", [2, 4, 8], index=2)

# Image source
img_source = st.sidebar.radio("Image for Analysis", ["Synthetic (gradient)", "NEU-DET Image"])
raw_image = None
if img_source == "NEU-DET Image":
    cat = st.sidebar.selectbox("Category", DEFECT_CATEGORIES, format_func=lambda c: CLASS_DISPLAY[c])
    paths = sorted((TRAIN_IMAGES_PATH / cat).glob("*.jpg"))[:10]
    if paths:
        sel = st.sidebar.selectbox("Image", [p.name for p in paths])
        raw_image = np.array(Image.open(TRAIN_IMAGES_PATH / cat / sel).convert("L"))

build_btn = st.sidebar.button(" BUILD CIRCUITS", type="primary")

# ── Build circuits (Isolated Subprocess) ───────────────────────────────────────
if build_btn:
    size = (size_n, size_n)

    if raw_image is not None:
        resized = processor.resize_image(raw_image, size)
    else:
        data = processor.create_synthetic_image(size, "gradient", bits)
        resized = data["image"]

    reps_to_show = ["FRQI", "NEQR"] if representation == "Both" else [representation]

    with st.spinner(" Compiling quantum circuits in isolated process..."):
        params = {
            "representation": representation,
            "size_n": size_n,
            "bits": bits,
            "raw_image": resized.tolist()
        }

        t_start = time.perf_counter()
        try:
            proc = subprocess.run(
                [PYTHON_EXE, str(WORKER_PATH)],
                input=json.dumps(params),
                capture_output=True,
                text=True,
                timeout=120,
            )

            if proc.returncode != 0 and not proc.stdout.strip():
                st.error(f" Qiskit Rust engine crashed (exit code {proc.returncode}).")
                st.code(proc.stderr[-1000:])
                st.stop()

            result = json.loads(proc.stdout)
            if not result.get("ok"):
                st.error(" Circuit building failed:")
                st.code(result.get("error", "Unknown error"))
                st.stop()
        except subprocess.TimeoutExpired:
            st.error(" Circuit building timed out (>2 min).")
            st.stop()
        except Exception as e:
            st.error(f" Could not launch circuit worker: {e}")
            st.stop()

    circuits_info = result["circuits_info"]
    scaling = result["scaling"]

    # ── Resource KPIs ─────────────────────────────────────────────────────────
    st.markdown('<div class="section-header"> Circuit Resources</div>', unsafe_allow_html=True)

    if len(reps_to_show) == 2:
        frqi_s = circuits_info["FRQI"]["stats"]
        neqr_s = circuits_info["NEQR"]["stats"]
        kpi_cols = st.columns(5)
        resources = [
            ("Qubits", frqi_s["qubits"], neqr_s["qubits"]),
            ("Gates", frqi_s["gates"], neqr_s["gates"]),
            ("Depth", frqi_s["depth"], neqr_s["depth"]),
            ("Ctrl Gates", frqi_s["controlled_gates"], neqr_s["controlled_gates"]),
            ("Pixels", frqi_s["num_pixels"], neqr_s["num_pixels"]),
        ]
        for col, (label, fv, nv) in zip(kpi_cols, resources):
            col.markdown(f"""
            <div class="kpi-card">
                <div style="font-size:.7rem;color:#94a3b8;margin-bottom:6px;text-transform:uppercase;">{label}</div>
                <div style="display:flex;justify-content:space-around;align-items:center;">
                    <div><div style="font-size:1.2rem;font-weight:800;color:#63b3ed;">{fv}</div><div style="font-size:.65rem;color:#94a3b8;">FRQI</div></div>
                    <div style="color:#4a5568;font-size:1.2rem;">|</div>
                    <div><div style="font-size:1.2rem;font-weight:800;color:#68d391;">{nv}</div><div style="font-size:.65rem;color:#94a3b8;">NEQR</div></div>
                </div>
            </div>""", unsafe_allow_html=True)
    else:
        rep = reps_to_show[0]
        s = circuits_info[rep]["stats"]
        kpi_cols = st.columns(5)
        kpis = [
            (s["qubits"], "Total Qubits"),
            (s["gates"], "Total Gates"),
            (s["depth"], "Circuit Depth"),
            (s["controlled_gates"], "Controlled Gates"),
            (s["num_pixels"], "Pixels Encoded"),
        ]
        for col, (val, label) in zip(kpi_cols, kpis):
            col.markdown(f'<div class="kpi-card"><div class="kpi-value">{val}</div><div class="kpi-label">{label}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

    # ── Gate type analysis ────────────────────────────────────────────────────
    st.markdown('<div class="section-header"> Gate Composition</div>', unsafe_allow_html=True)
    gate_cols = st.columns(len(reps_to_show))
    for col, rep in zip(gate_cols, reps_to_show):
        s = circuits_info[rep]["stats"]
        gt = s.get("gate_types", {})
        color = "#63b3ed" if rep == "FRQI" else "#68d391"
        fig = go.Figure(go.Bar(
            x=list(gt.keys()), y=list(gt.values()),
            marker_color=color,
            text=list(gt.values()), textposition="outside",
        ))
        fig.update_layout(
            title=f"{rep} Gate Types ({size_n}×{size_n}, {bits}-bit)",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
            font=dict(color="#e2e8f0"), height=320,
            xaxis=dict(gridcolor="rgba(99,179,237,.1)"),
            yaxis=dict(gridcolor="rgba(99,179,237,.1)"),
        )
        col.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

    # ── Resource scaling analysis ──────────────────────────────────────────────
    st.markdown('<div class="section-header"> Resource Scaling — Resolution Impact</div>', unsafe_allow_html=True)

    sc_col1, sc_col2 = st.columns(2)
    with sc_col1:
        fig_sc = go.Figure()
        for rep, color in [("FRQI","#63b3ed"), ("NEQR","#68d391")]:
            fig_sc.add_trace(go.Scatter(
                x=scaling[rep]["sizes"], y=scaling[rep]["qubits"],
                mode="lines+markers+text", name=rep, line_color=color,
                text=scaling[rep]["qubits"], textposition="top center",
            ))
        fig_sc.update_layout(
            title="Qubits vs Resolution",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
            font=dict(color="#e2e8f0"), height=300,
            xaxis=dict(title="Resolution (N×N)", gridcolor="rgba(99,179,237,.1)"),
            yaxis=dict(title="Qubit Count", gridcolor="rgba(99,179,237,.1)"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_sc, use_container_width=True)

    with sc_col2:
        fig_sc2 = go.Figure()
        for rep, color in [("FRQI","#63b3ed"), ("NEQR","#68d391")]:
            fig_sc2.add_trace(go.Scatter(
                x=scaling[rep]["sizes"], y=scaling[rep]["gates"],
                mode="lines+markers+text", name=rep, line_color=color,
                text=scaling[rep]["gates"], textposition="top center",
            ))
        fig_sc2.update_layout(
            title="Gate Count vs Resolution",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.8)",
            font=dict(color="#e2e8f0"), height=300,
            xaxis=dict(title="Resolution (N×N)", gridcolor="rgba(99,179,237,.1)"),
            yaxis=dict(title="Gate Count", gridcolor="rgba(99,179,237,.1)"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_sc2, use_container_width=True)

    st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

    # ── Interactive Circuit Visualization ─────────────────────────────────────
    st.markdown('<div class="section-header"> Interactive Circuit Visualization</div>', unsafe_allow_html=True)
    
    if len(reps_to_show) == 2:
        vis_rep = st.radio("Select Representation to View", ["FRQI", "NEQR"], horizontal=True)
    else:
        vis_rep = reps_to_show[0]

    def plot_circuit(ops, num_qubits, num_clbits, title):
        fig = go.Figure()
        max_depth = max([op["depth"] for op in ops] + [0]) if ops else 0
        
        # 1. Draw horizontal wires
        for q in range(num_qubits):
            fig.add_trace(go.Scatter(
                x=[0, max_depth + 1], y=[-q, -q],
                mode='lines', line=dict(color='rgba(255,255,255,0.2)', width=1.5),
                hoverinfo='skip', showlegend=False
            ))
            # Qubit labels
            fig.add_annotation(
                x=-0.2, y=-q, text=f"q{q}", showarrow=False,
                font=dict(color="#90cdf4", size=14, family="Courier New"),
                xanchor="right"
            )
            
        for c in range(num_clbits):
            fig.add_trace(go.Scatter(
                x=[0, max_depth + 1], y=[-(num_qubits + c), -(num_qubits + c)],
                mode='lines', line=dict(color='rgba(150,150,150,0.5)', width=2, dash='dot'),
                hoverinfo='skip', showlegend=False
            ))
            fig.add_annotation(
                x=-0.2, y=-(num_qubits + c), text=f"c{c}", showarrow=False,
                font=dict(color="#a0aec0", size=14, family="Courier New"),
                xanchor="right"
            )

        # 2. Draw operations
        for op in ops:
            d = op["depth"]
            name = op["name"].upper()
            qubits = op["qubits"]
            cbits = op["cbits"]
            params = op["params"]
            
            if len(qubits) == 0 and len(cbits) == 0:
                continue
                
            param_str = f"({', '.join([f'{p:.3f}' if isinstance(p, float) else str(p) for p in params])})" if params else ""
            hover_text = f"<b>Gate:</b> {name}<br><b>Qubits:</b> {qubits}<br><b>Depth:</b> {d}"
            if params:
                hover_text += f"<br><b>Params:</b> {param_str}"

            if len(qubits) > 1 and name not in ["MEASURE", "BARRIER"]:
                controls = qubits[:-1]
                target = qubits[-1]
                
                # Vertical line
                fig.add_trace(go.Scatter(
                    x=[d, d], y=[-min(qubits), -max(qubits)],
                    mode='lines', line=dict(color='#63b3ed', width=2),
                    hoverinfo='skip', showlegend=False
                ))
                
                # Control points
                for ctrl in controls:
                    fig.add_trace(go.Scatter(
                        x=[d], y=[-ctrl], mode='markers',
                        marker=dict(symbol='circle', size=12, color='#63b3ed'),
                        text=hover_text, hoverinfo="text", showlegend=False
                    ))
                
                # Target point
                if name.endswith("X") and not name.startswith("R"):
                    # For CX, MCX, CCX, etc.
                    fig.add_trace(go.Scatter(
                        x=[d], y=[-target], mode='markers',
                        marker=dict(symbol='circle-open', size=22, color='rgba(0,0,0,0)', line=dict(color='#63b3ed', width=2)),
                        text=hover_text, hoverinfo="text", showlegend=False
                    ))
                    fig.add_trace(go.Scatter(
                        x=[d], y=[-target], mode='text', text='+',
                        textfont=dict(color='#63b3ed', size=20),
                        hoverinfo='skip', showlegend=False
                    ))
                else:
                    # For CRY, MCRY, CP, etc.
                    disp_name = name
                    if disp_name.startswith("MC"):
                        disp_name = disp_name[2:]
                    elif disp_name.startswith("C"):
                        disp_name = disp_name[1:]
                    
                    fig.add_trace(go.Scatter(
                        x=[d], y=[-target], mode='markers+text',
                        marker=dict(symbol='square', size=24, color='rgba(99,179,237,0.2)', line=dict(color='#63b3ed', width=1)),
                        text=disp_name, textfont=dict(color='#90cdf4', size=11),
                        hovertext=hover_text, hoverinfo="text", showlegend=False
                    ))
                    
            elif name == "MEASURE":
                q = qubits[0]
                c = cbits[0]
                # vertical line to classical register
                fig.add_trace(go.Scatter(
                    x=[d, d], y=[-q, -(num_qubits + c)],
                    mode='lines', line=dict(color='rgba(150,150,150,0.8)', width=1, dash='dot'),
                    hoverinfo='skip', showlegend=False
                ))
                fig.add_trace(go.Scatter(
                    x=[d], y=[-q], mode='markers+text',
                    marker=dict(symbol='square', size=26, color='rgba(255,255,255,0.1)', line=dict(color='#a0aec0', width=1)),
                    text="M", textfont=dict(color='#e2e8f0', size=12),
                    hovertext=hover_text, hoverinfo="text", showlegend=False
                ))
                
            else:
                for q in qubits:
                    disp_name = name
                    if name == "RY": disp_name = "Ry"
                    elif name == "X": disp_name = "X"
                    elif name == "H": disp_name = "H"
                        
                    fig.add_trace(go.Scatter(
                        x=[d], y=[-q], mode='markers+text',
                        marker=dict(symbol='square', size=32, color='rgba(13,27,42,0.9)', line=dict(color='#68d391', width=1.5)),
                        text=disp_name, textfont=dict(color='#e2e8f0', size=13, family="Inter, sans-serif"),
                        hovertext=hover_text, hoverinfo="text", showlegend=False
                    ))

        fig.update_layout(
            title=dict(text=title, font=dict(color='#e2e8f0', size=18)),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0.2)",
            xaxis=dict(
                title="Circuit Depth", color="#94a3b8",
                showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                zeroline=False, 
                # Limit initial view to 20 depths to avoid horizontal congestion
                range=[-1, min(max_depth + 2, 20)]
            ),
            yaxis=dict(
                showticklabels=False, showgrid=False, zeroline=False,
                range=[-(num_qubits + num_clbits) - 0.5, 0.5]
            ),
            height=max(400, (num_qubits + num_clbits) * 60 + 100), # increased vertical spacing to 60 per wire
            margin=dict(l=60, r=40, t=60, b=40),
            dragmode="pan"
        )
        return fig

    c_info = circuits_info[vis_rep]
    ops = c_info["ops"]
    num_q = c_info["num_qubits"]
    num_c = c_info["num_clbits"]
    
    single_q_gates = sum(1 for op in ops if len(op["qubits"]) == 1 and op["name"].lower() != "measure")
    multi_q_gates = sum(1 for op in ops if len(op["qubits"]) > 1)
    measurements = sum(1 for op in ops if op["name"].lower() == "measure")
    total_gates_vis = len(ops)
    depth_vis = max([op["depth"] for op in ops] + [0]) if ops else 0
    
    st.markdown(f"**{vis_rep} Circuit Statistics**")
    
    # Custom CSS for the mini-stats panel
    st.markdown("""
    <style>
    .mini-stat { background:rgba(26,41,66,.7); border:1px solid rgba(99,179,237,.2); border-radius:8px; padding:10px; text-align:center; }
    .mini-stat-val { font-size:1.4rem; font-weight:700; color:#90cdf4; }
    .mini-stat-label { font-size:0.7rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.05em; }
    </style>
    """, unsafe_allow_html=True)
    
    stat_cols = st.columns(7)
    stats_data = [
        ("Qubits", num_q), ("Cl. Bits", num_c), ("Total Gates", total_gates_vis),
        ("Depth", depth_vis), ("Single-Q", single_q_gates), 
        ("Multi-Q", multi_q_gates), ("Measure", measurements)
    ]
    for col, (label, val) in zip(stat_cols, stats_data):
        col.markdown(f'<div class="mini-stat"><div class="mini-stat-val">{val}</div><div class="mini-stat-label">{label}</div></div>', unsafe_allow_html=True)
    
    st.write("") # spacing
    
    if len(ops) > 3000:
        st.warning(f"Circuit is very large ({len(ops)} operations). Rendering visualization may take a few seconds.")
        
    fig_circ = plot_circuit(ops, num_q, num_c, f"{vis_rep} Quantum Circuit Visualization")
    st.plotly_chart(fig_circ, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': True, 'modeBarButtonsToRemove': ['lasso2d', 'select2d']})

    st.markdown('<div class="q-divider"></div>', unsafe_allow_html=True)

elif not build_btn:
    st.info(" Configure your circuit parameters in the sidebar and click **BUILD CIRCUITS**")

# ── Educational explanations ──────────────────────────────────────────────
st.markdown('<div class="section-header"> How It Works</div>', unsafe_allow_html=True)
exp_col1, exp_col2 = st.columns(2)
with exp_col1:
    st.markdown("""
    <div class="formula-box">
        <div style="color:#63b3ed;font-weight:700;margin-bottom:8px;"> FRQI — Flexible Representation</div>
        <div style="font-family:'Courier New',monospace;font-size:.82rem;color:#90cdf4;margin-bottom:8px;">
        |I⟩ = (1/√N) Σᵢ (cos(θᵢ)|0⟩ + sin(θᵢ)|1⟩) ⊗ |i⟩
        </div>
        <div style="color:#94a3b8;font-size:.82rem;">
        • <b style="color:#e2e8f0;">n + 1 qubits</b> (n position + 1 color)<br>
        • Intensity encoded as rotation angle θ ∈ [0, π/2]<br>
        • Multi-controlled Ry gate per pixel<br>
        • Reconstruction requires statistical sampling
        </div>
    </div>""", unsafe_allow_html=True)
with exp_col2:
    st.markdown("""
    <div class="formula-box">
        <div style="color:#68d391;font-weight:700;margin-bottom:8px;"> NEQR — Novel Enhanced Representation</div>
        <div style="font-family:'Courier New',monospace;font-size:.82rem;color:#90cdf4;margin-bottom:8px;">
        |I⟩ = (1/√N) Σᵢ |Cᵢ⟩ ⊗ |i⟩
        </div>
        <div style="color:#94a3b8;font-size:.82rem;">
        • <b style="color:#e2e8f0;">n + q qubits</b> (n position + q intensity)<br>
        • Intensity stored as binary string |Cᵢ⟩<br>
        • Multi-controlled X gate per set intensity bit<br>
        • Exact reconstruction via majority vote
        </div>
    </div>""", unsafe_allow_html=True)

st.caption("Q-ImageLab | Circuit Analyzer | Live circuit generation using Qiskit")
