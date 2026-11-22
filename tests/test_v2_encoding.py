"""Phase 6 validation: encoding/reconstruction study mechanics (tmp output only)."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.frqi.encoder import FRQIEncoder  # noqa: E402
from src.reconstruction.reconstructor import FRQIReconstructor  # noqa: E402
from src.simulation.simulator import QuantumSimulator  # noqa: E402
from src.v2 import encoding_study as es  # noqa: E402


def test_psnr_null_when_exact_and_ssim_labels():
    a = np.random.default_rng(0).random((4, 4))
    m = es.image_metrics(a, a.copy())
    assert m["exact_match"] and m["psnr"] is None and abs(m["ssim"] - 1) < 1e-12
    assert "global" in m["ssim_method"]
    assert es.image_metrics(np.random.default_rng(1).random((8, 8)), np.zeros((8, 8)))["ssim_method"] == "skimage win7"


def test_sampled_counts_match_aer_format_and_statistics():
    img = np.array([[0.1, 0.4], [0.7, 0.95]])
    qc = FRQIEncoder(img).build_circuit()
    sim = QuantumSimulator(seed=3)
    sv = sim.run_statevector(qc)
    shots = 40000
    ours = es.sample_counts(sv["probabilities"], shots, qc.num_qubits, np.random.default_rng(0))
    aer = sim.run_shots(qc, shots)["counts"]
    assert set(ours) <= {format(i, f"0{qc.num_qubits}b") for i in range(2 ** qc.num_qubits)}
    assert set(k.replace(" ", "") for k in aer) == set(ours)
    dec = FRQIReconstructor(2, (2, 2))
    r1 = dec.reconstruct_from_counts(ours, shots)["image"]
    r2 = dec.reconstruct_from_counts(aer, shots)["image"]
    assert np.max(np.abs(r1 - img)) < 0.03 and np.max(np.abs(r2 - img)) < 0.03


def test_run_config_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setenv("QIL_RESULTS_V2", str(tmp_path / "v2"))
    root = tmp_path / "ds"
    imgs = []
    rng = np.random.default_rng(0)
    for i, c in enumerate(["crazing", "inclusion"]):
        p = root / "train/images" / c / f"{c}_12.jpg"
        p.parent.mkdir(parents=True)
        Image.fromarray((rng.random((20, 20)) * 255).astype(np.uint8)).convert("RGB").save(p)
        imgs.append({"rel_path": str(p.relative_to(root)), "class": c})
    out = tmp_path / "v2" / "reconstructions"
    s_f = es.run_config("FRQI", 4, None, imgs, root, out, shots_list=(1000,), log=lambda *a: None)
    s_n = es.run_config("NEQR", 4, 4, imgs, root, out, shots_list=(1000,), log=lambda *a: None)
    # statevector decoding is exact for FRQI and for NEQR w.r.t. its quantised image
    assert s_f["statevector"]["vs_preprocessed"]["mse"]["mean"] < 1e-20
    assert s_n["statevector"]["vs_quantized"]["mse"]["mean"] < 1e-20
    assert s_n["statevector"]["vs_preprocessed"]["mse"]["mean"] > 0  # quantisation error remains
    assert s_f["shots1000"]["vs_preprocessed"]["mse"]["mean"] > 0
    st = json.loads((out / "R-NEQR-4x4-b4" / "status.json").read_text())
    assert st["status"] == "completed" and st["summary"]["n_qubits"] == 8
    assert any((out / "R-FRQI-4x4" / "images").glob("*_shots1000.png"))
    cs = json.loads((out / "R-FRQI-4x4" / "circuit_stats.json").read_text())
    assert cs["gates_compiled"] > 0 and cs["depth_compiled"] > 0 and cs["cx_compiled"] > 0
    assert cs["transpilation"]["basis_gates"] == ["cx", "rz", "sx", "x"]
