# Circuit Architecture Guide

> Neeche ka har circuit uske construction code mein check kiya gaya. Resource numbers: {cx, rz, sx, x} mein transpile,
> optimisation level 1, all-to-all coupling, `reconstruction_full/summary.json` aur V4 `circuit_stats.json` se.

---

## 1. Circuit diagram kaise padhein
* Har **horizontal line (wire)** ek qubit hai; time **left → right** chalta hai. Qiskit inhe q₀, q₁… kehta hai (q₀ = index
  ka least-significant bit). Registers wires ko group karte hain (`pos`, `color`).
* Wire par **box** = single-qubit gate (H, X, RY(θ)…). **Dot** jo vertical line se box se juda ho = "box tabhi lagao jab dot
  wala qubit |1⟩ ho" (controlled gate); ⊕ CNOT/MCX ka target.
* **Barrier** (dashed line) sirf stages alag dikhata hai.
* **Meter** symbol = measurement classical bit mein.
* Depth = parallel gates pack karne ke baad columns; gate count = boxes (transpile ke baad multi-controlled gates bahut saare
  CX/RZ/SX mein toot jaate hain).

---

## 2. FRQI encoder (`src/frqi/encoder.py`)
Wires: n position qubits + 1 colour qubit. Stage 1: har position qubit par H. Stage 2: har non-black pixel ke liye: jin
position qubits ka bit 0 hai unpar X → saare position qubits se controlled MCRY(xᵢπ), target colour → same X wapas.
Trainable parameters: koi nahi. Measurement: sab qubits (reconstruction) ya koi nahi (statevector kernels).

| Size | Qubits | Compiled gates | Depth | CX |
|---|---|---|---|---|
| 2×2 | 3 | 143 | 93 | 48 |
| 4×4 | 5 | 1,070 | 710 | 384 |
| 8×8 (= V4 FRQI patch) | 7 | 8,339 | 4,878 | 3,584 |
| 16×16 | 9 | 77,307 | 57,352 | 26,624 |

Expected output: FRQI state; measure karne par P(colour = 1 | i) = sin²θᵢ.

## 3. NEQR encoder (`src/neqr/encoder.py`)
Wires: n position + q intensity qubits. Position qubits par H; har pixel aur har set bit j ke liye: X-sandwich + intensity
qubit j par MCX. Size data par depend karta hai:

| Size, bits | Qubits | Compiled gates | Depth |
|---|---|---|---|
| 2×2, 4-bit | 6 | 132 | 87 |
| 4×4, 4-bit | 8 | 1,031 | 804 |
| 8×8, 4-bit | 10 | 14,531 | 10,794 |
| 16×16, 4-bit | 12 | 131,375 | 66,614 |
| 16×16, 8-bit | 16 | 174,963 | 158,453 |

V4 NEQR 4×4 patch (8 qubits): V4 group statistics mein 1,998 compiled gates (training images ke sample patches) vs
reconstruction study mein 2,901 (doosri images) — same circuit family, alag data.

## 4. Product-RY feature map
k wires, har wire par ek RY(b·aᵢ), aur kuch nahi. Koi entanglement nahi. Kernel = Πᵢ cos²((xᵢ−yᵢ)/2) — classically closed form,
isliye **control**. Phir bhi V2 E5 aur V3 mein yahi best feature map tha (93.2 % aur 95.3 %) — matlab features matter kiye,
entanglement nahi.

## 5. ZZ feature maps ("zz_linear", "zz_full")
Har repetition: sab par H; har wire par P(2xᵢ); har pair (i, j) ke liye: CX(i→j), j par P(2(π−xᵢ)(π−xⱼ)), CX(i→j).
Linear: pairs (i, i+1) → k−1 pairs. Full: sab i < j → k(k−1)/2 pairs (k = 8 par 28). reps ∈ {1, 2}.
Qiskit ZZFeatureMap convention follow karta hai (Havlíček et al.).

## 6. Kernel estimation circuit (`qkernel.kernel_circuit`)
Same k wires par U(x) phir U(y)†, sab measure; P(000…0) = |⟨φ(y)|φ(x)⟩|². Aer cross-check ke liye use (`aer_kernel_entry`);
bade kernels statevectors se.

## 7. VQC (`src/v2/vqc.py`, V3 `VQCCircuitV3`)
k wires. Encoding: RY(aᵢ). Phir L layers: [re-upload on ho toh RY(aᵢ)] → har wire par RY(θ) aur RZ(θ) → CNOT ring
(i → i+1 mod k). Trainable parameters: 2·k·L (k = 8, L = 3 par 48). Readout: exact ⟨Z₀⟩…⟨Z₅⟩ (k ≥ 6) ya Z₀…Z₃, Z₀Z₁, Z₂Z₃
(k = 4); V3 "zall" saare ⟨Zᵢ⟩ + linear head. Gradients: parameter shift ∂⟨O⟩/∂θ = [⟨O⟩(θ+π/2) − ⟨O⟩(θ−π/2)]/2.

## 8. Projected quantum kernel (V3)
Same ZZ/product circuits; global overlap ki jagah har state ko single-qubit Bloch vectors (har qubit ka ⟨X⟩,⟨Y⟩,⟨Z⟩) mein
reduce karo aur K = exp(−(γ/2)Σ_q‖b_q(x) − b_q(y)‖²). Hardware par: har image ke 3k Pauli expectations.

## 9. V4 patch encoder aur (describe kiya) swap test
Patch encoder = ek patch par FRQI (2·log₂p + 1 qubits) ya NEQR (2·log₂p + q) circuit. Kernel Tr(ρAρB) ko **swap test** se
estimate karte: ancilla H → do patch registers ka controlled-SWAP → ancilla H → measure; P(0) = ½(1 + Tr(ρσ)).
FRQI p = 8 ke liye: 2·7 + 1 = 15 qubits. **Chalaya nahi** — dashboard ka swap-test drawing sirf schematic hai.

## 10. Frontend circuits kaise dikhata hai
* **Circuits page** (`/circuits`, V2): `scripts/v2/build_circuit_artifacts.py` har selected model ka circuit uske saved
  checkpoint se dobara banata hai (pehli training image; trained VQC parameters) aur instructions, resources aur Qiskit text
  diagram save karta hai; page instruction list ko SVG mein draw karta hai → real circuits.
* **How it works** page: real computed angles ke saath per-patch FRQI encoding illustration aur schematic swap-test animation.
* **Encoding page**: saved records se measured costs (qubits, compiled gates, 1,000 shots par MSE).

### Ek circuit doosre ke upar kyun
FRQI: sabse kam qubits, smooth similarity. NEQR: exact read-out, zyada qubits, data-dependent gates. Product-RY: imaandaar
classical-equivalent control. ZZ: feature products/entanglement laata hai (test karta hai ki entanglement help karta hai
ya nahi — yahan product-RY ko beat nahi kiya). VQC: trainable circuits test karta hai (kamzor, optimise karna mushkil).
Patch encoders: image size kuch bhi ho, registers 5–8 qubits par rehte hain.
