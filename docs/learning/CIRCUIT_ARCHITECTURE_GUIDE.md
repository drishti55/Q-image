# Circuit Architecture Guide

> Every circuit below was checked in its construction code. Resource numbers: transpiled to {cx, rz, sx, x},
> optimisation level 1, all-to-all coupling (`src/v2/qsim.py::circuit_resources`), taken from
> `results/qml_v4/reconstruction_full/summary.json` and V4 `circuit_stats.json`.

---

## 1. How to read a circuit diagram
* Each **horizontal wire** is a qubit; time flows **left → right**. Qiskit labels them q₀, q₁… (q₀ = least-significant
  bit of the state index). Registers group wires (e.g. `pos`, `color`).
* A **box** on a wire is a single-qubit gate (H, X, RY(θ)…). A **dot** connected by a vertical line to a box means
  "apply the box only if the dotted qubit is |1⟩" (controlled gate); ⊕ is the target of a CNOT/MCX.
* A **barrier** (dashed line) only separates stages visually.
* A **meter** symbol means measurement into a classical bit.
* Depth = number of columns after packing parallel gates; gate count = number of boxes (after transpilation into
  basis gates, multi-controlled gates expand into many CX/RZ/SX).

---

## 2. FRQI encoder (`src/frqi/encoder.py`)
Wires: n position qubits + 1 colour qubit. Stage 1: H on every position qubit. Stage 2: for each non-black pixel:
X on position qubits whose bit is 0 → MCRY(xᵢπ) controlled by all position qubits, target colour → same X's again.
Trainable parameters: none. Measurement: all qubits (reconstruction) or none (statevector kernels).

| Size | Qubits | Compiled gates | Depth | CX |
|---|---|---|---|---|
| 2×2 | 3 | 143 | 93 | 48 |
| 4×4 | 5 | 1,070 | 710 | 384 |
| 8×8 (= V4 FRQI patch) | 7 | 8,339 | 4,878 | 3,584 |
| 16×16 | 9 | 77,307 | 57,352 | 26,624 |

Expected output: the FRQI state; measuring gives P(colour = 1 | i) = sin²θᵢ.

## 3. NEQR encoder (`src/neqr/encoder.py`)
Wires: n position + q intensity qubits. H on position qubits; for each pixel and each set bit j: X-sandwich + MCX onto
intensity qubit j. Data-dependent size:

| Size, bits | Qubits | Compiled gates | Depth |
|---|---|---|---|
| 2×2, 4-bit | 6 | 132 | 87 |
| 4×4, 4-bit | 8 | 1,031 | 804 |
| 8×8, 4-bit | 10 | 14,531 | 10,794 |
| 16×16, 4-bit | 12 | 131,375 | 66,614 |
| 16×16, 8-bit | 16 | 174,963 | 158,453 |

V4 NEQR 4×4 patch (8 qubits): 1,998 compiled gates in the V4 group statistics (sample patches of training images)
vs 2,901 in the reconstruction study (other images) — same circuit family, different data.

## 4. Product-RY feature map (`qkernel.encode`, "product_ry")
k wires, one RY(b·aᵢ) per wire, nothing else. No entanglement. Kernel = Πᵢ cos²((xᵢ−yᵢ)/2) — computable classically
in closed form; included as a **control**. In V2 E5 and V3 it was nevertheless the best feature map (93.2 % and
95.3 %), showing the features, not entanglement, mattered.

## 5. ZZ feature maps ("zz_linear", "zz_full")
Per repetition: H on all wires; P(2xᵢ) on each wire; for each pair (i, j): CX(i→j), P(2(π−xᵢ)(π−xⱼ)) on j, CX(i→j).
Linear: pairs (i, i+1) → k−1 pairs. Full: all i < j → k(k−1)/2 pairs (28 for k = 8). reps ∈ {1, 2}.
These follow the Qiskit ZZFeatureMap convention (Havlíček et al.).

## 6. Kernel estimation circuit (`qkernel.kernel_circuit`)
U(x) followed by U(y)† on the same k wires, measure all; P(000…0) = |⟨φ(y)|φ(x)⟩|². Used for an Aer cross-check
(`aer_kernel_entry`); bulk kernels are computed from statevectors.

## 7. VQC (`src/v2/vqc.py`, V3 `VQCCircuitV3`)
k wires. Encoding: RY(aᵢ). Then L layers: [re-upload RY(aᵢ) if enabled] → RY(θ) and RZ(θ) on every wire →
CNOT ring (i → i+1 mod k). Trainable parameters: 2·k·L (e.g. 48 for k = 8, L = 3). Readout: exact ⟨Z₀⟩…⟨Z₅⟩
(k ≥ 6) or Z₀…Z₃, Z₀Z₁, Z₂Z₃ (k = 4); V3 "zall" uses all ⟨Zᵢ⟩ with a linear head. Gradients: parameter shift
∂⟨O⟩/∂θ = [⟨O⟩(θ+π/2) − ⟨O⟩(θ−π/2)]/2.

## 8. Projected quantum kernel (V3)
Same ZZ/product circuits; instead of the global overlap, each state is reduced to single-qubit Bloch vectors
(⟨X⟩,⟨Y⟩,⟨Z⟩ per qubit) and K = exp(−(γ/2)Σ_q‖b_q(x) − b_q(y)‖²). On hardware: 3k Pauli expectations per image.

## 9. V4 patch encoder and the (described) swap test
Patch encoder = FRQI (2·log₂p + 1 qubits) or NEQR (2·log₂p + q) circuit on one patch. The kernel Tr(ρAρB) would be
estimated by a **swap test**: ancilla H → controlled-SWAP of two patch registers → ancilla H → measure;
P(0) = ½(1 + Tr(ρσ)). For FRQI p = 8: 2·7 + 1 = 15 qubits. **Not executed** — the dashboard's swap-test drawing is a
schematic.

## 10. How the frontend shows circuits
* **Circuits page** (`/circuits`, V2): `scripts/v2/build_circuit_artifacts.py` rebuilds each selected model's circuit
  from its saved checkpoint (first training image; trained VQC parameters) and stores instructions, resources and the
  Qiskit text diagram; the page draws the instruction list as SVG. → real circuits.
* **How it works** page: draws a per-patch FRQI encoding illustration with the real computed angles and a schematic
  swap-test animation.
* **Encoding page**: measured costs (qubits, compiled gates, MSE at 1,000 shots) from saved records.

### Why one circuit over another
FRQI: fewest qubits, smooth similarity. NEQR: exact read-out, more qubits, data-dependent gates. Product-RY: honest
classical-equivalent control. ZZ: introduces feature products/entanglement (tests whether entanglement helps — it did
not beat product-RY here). VQC: tests trainable circuits (weak, hard to optimise). Patch encoders: keep registers at
5–8 qubits regardless of image size.
