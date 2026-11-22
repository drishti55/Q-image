# Quantum Computing from Zero (only what Q-ImageLab actually uses)

> Every gate listed in §3 is used somewhere in our code; gates we do **not** use are named as such.
> Conventions follow Qiskit (and our NumPy simulator `src/v2/qsim.py`, which is tested against Qiskit to 1e-10):
> **qubit 0 is the least-significant bit** of a basis-state index.

---

## 1. Concepts from zero

**1. Bit vs qubit.** A classical bit is 0 or 1. A *qubit* is a unit vector in a 2-dimensional complex space:
|ψ⟩ = α|0⟩ + β|1⟩ with |α|² + |β|² = 1. α and β are *amplitudes*.

**2. Superposition.** Having both α and β non-zero. It does **not** mean "the qubit is secretly 0 or 1"; it is a
single well-defined state. Analogy: an arrow pointing north-east is one direction, not "half north, half east".

**3. Measurement.** Reading a qubit gives 0 with probability |α|² and 1 with probability |β|², and the state
collapses to the observed value. One measurement gives one bit of information.

**4. Several qubits — tensor product.** Two qubits live in a 4-dimensional space with basis |00⟩,|01⟩,|10⟩,|11⟩.
For independent qubits the joint state is the *tensor product*: (a|0⟩+b|1⟩)⊗(c|0⟩+d|1⟩) = ac|00⟩+ad|01⟩+bc|10⟩+bd|11⟩.
n qubits need 2ⁿ amplitudes — this is why simulation cost doubles with each qubit.

**5. Entanglement.** A multi-qubit state that cannot be written as a tensor product, e.g. (|00⟩+|11⟩)/√2.
FRQI and NEQR states are entangled between the position register and the colour register (the colour depends on
the position).

**6. Statevector.** The list of all 2ⁿ amplitudes. *Exact statevector simulation* computes this list directly.

**7. Quantum circuit / register / gate.** A circuit is a sequence of gates (unitary matrices) applied to registers
(groups of qubits). Read left to right. FRQI uses a `pos` register and a `color` register.

**8. Unitary.** A matrix U with U†U = I. Unitaries preserve length (probabilities still sum to 1) and are reversible.

**9. Bloch sphere.** Any single-qubit state can be drawn as a point on a sphere: |0⟩ at the north pole, |1⟩ at the
south pole, (|0⟩+|1⟩)/√2 on the equator. RY rotates around the Y axis (north ↔ south through the front), RZ around
the vertical axis. V3's *projected quantum kernel* compares these Bloch vectors.

**10. Measurement probability and shots.** Hardware cannot return amplitudes; you repeat the circuit many times
("shots") and count outcomes. With M shots, a probability p is estimated with standard error √(p(1−p)/M).
Our reconstruction study uses 100, 1,000, 10,000 and 100,000 shots.

**11. Simulator vs hardware.** We use (a) Qiskit-Aer statevector + multinomial sampling of the exact distribution
(reconstruction study), and (b) our own NumPy statevector simulator (kernels, VQC). Both are **noiseless**.
Real hardware adds gate errors, decoherence and readout errors; none are modelled.

**12. Circuit depth and gate count.** Gate count = number of gates; depth = number of time-steps if gates on
different qubits run in parallel. We report both after *transpilation* to the basis {cx, rz, sx, x} at optimisation
level 1 with all-to-all connectivity (`circuit_resources` in `qsim.py`).

**13. Noise.** Not modelled. Deep circuits (e.g. FRQI 16×16: 77,307 compiled gates) would be destroyed by noise on
today's devices — a key limitation.

**14. Quantum kernel.** A function K(x, y) computed from two encoded quantum states, e.g. the fidelity
|⟨φ(x)|φ(y)⟩|², used as a similarity inside a classical SVM. See §5.

---

## 2. Mixed states and density matrices (needed for V4)

A *pure* state is a vector |ψ⟩. Its *density matrix* is ρ = |ψ⟩⟨ψ| (a D×D matrix). A *mixed state* is a
probabilistic mixture: "with probability wₖ the system is in |ψₖ⟩": ρ = Σₖ wₖ |ψₖ⟩⟨ψₖ|.
Properties: Tr ρ = 1, ρ is positive semi-definite, **purity** Tr(ρ²) = 1 for pure states and < 1 for mixtures.
The overlap of two density matrices, **Tr(ρσ)**, generalises |⟨ψ|φ⟩|² (for pure states they are equal).

> ⚠ Common confusion: averaging *density matrices* (a mixture) is **not** averaging *statevectors* (that would be a
> superposition). V4 averages density matrices.

---

## 3. Gates used in our code

Matrices in the {|0⟩, |1⟩} basis; c = cos(θ/2), s = sin(θ/2).

| Gate | Matrix | Effect | Where used |
|---|---|---|---|
| **H** (Hadamard) | (1/√2)[[1,1],[1,−1]] | \|0⟩→(\|0⟩+\|1⟩)/√2 | FRQI/NEQR (all position qubits); ZZ feature map |
| **X** (Pauli-X, NOT) | [[0,1],[1,0]] | flips 0↔1 | FRQI/NEQR "position selection" sandwiches |
| **RY(θ)** | [[c,−s],[s,c]] | rotates about Y; RY(θ)\|0⟩ = c\|0⟩+s\|1⟩ | product-RY map; VQC encoding & layers; FRQI (inside MCRY) |
| **RZ(θ)** | diag(e^{−iθ/2}, e^{iθ/2}) | phase rotation | VQC trainable layers; transpiled circuits |
| **P(λ)** (phase) | diag(1, e^{iλ}) | adds phase to \|1⟩ | ZZ feature map: P(2xᵢ), P(2(π−xᵢ)(π−xⱼ)) |
| **CX / CNOT** | flips target if control = 1 | creates entanglement | ZZ maps, VQC ring, all transpiled circuits |
| **CRY / MCRY** | RY on target iff all controls = 1 | conditional rotation | FRQI (one per pixel) |
| **CCX / MCX** (Toffoli / multi-controlled X) | X on target iff all controls = 1 | conditional flip | NEQR (one per set bit), decompositions |
| **SX** (√X), **T/T†** | basis gates | appear only after transpilation/decomposition | resource counts |

**Not used in our implementation:** Pauli-Y and Pauli-Z as gates, RX, CZ. (Z appears only as a *measured
observable* in the VQC readout: ⟨Zᵢ⟩, ⟨ZᵢZⱼ⟩.) The swap test needs a controlled-SWAP; it is **described, not
executed**.

### Worked example 1 — a single RY
Start |0⟩, apply RY(π/2): c = cos(π/4) = 0.707, s = 0.707 → 0.707|0⟩ + 0.707|1⟩. Measure: 50 % / 50 %.
RY(π): c = 0, s = 1 → |1⟩. This is exactly how FRQI stores a white pixel.

### Worked example 2 — H then CNOT (entanglement)
|00⟩ → H on qubit 0 → (|00⟩+|01⟩)/√2 (qubit 0 is the right-most bit) → CX(control 0, target 1) →
(|00⟩+|11⟩)/√2. The two qubits are now perfectly correlated.

### Worked example 3 — position selection with X sandwiches (the FRQI trick)
Two position qubits in superposition, colour qubit |0⟩: ½(|00⟩+|01⟩+|10⟩+|11⟩)|0⟩. To rotate the colour qubit
**only** for position 1 (binary q1q0 = 01): apply X to q1 (the bit that is 0), so position 01 becomes 11; apply
RY controlled by both q0 and q1 (only "11" triggers it); undo X on q1. Net effect: only position 1 got rotated.

---

## 4. Sequential gates = matrix products
Applying U₁ then U₂ gives U₂U₁ (right-to-left in algebra, left-to-right in the diagram).
Example: RY(a) then RY(b) = RY(a+b). RY(π/2)·RY(π/2) = RY(π): |0⟩ → |1⟩.

---

## 5. Quantum kernels in our project

**Idea.** Map each data point x to a state |φ(x)⟩ with a circuit U(x). Define similarity
K(x,y) = |⟨φ(x)|φ(y)⟩|² (fidelity). Hardware would estimate it with the *compute–uncompute* circuit U(y)†U(x)|0⟩:
the probability of measuring all zeros equals K (`kernel_circuit` in `qkernel.py`). We compute it exactly from
statevectors (or draw Binomial shot noise).

**Our three feature maps (`src/v2/qkernel.py`).** Inputs are PCA/CNN/texture features scaled to angles in [0, π],
multiplied by a *bandwidth* b.

* **product-RY**: RY(xᵢ) on each qubit. No entanglement. K = Πᵢ cos²((xᵢ−yᵢ)/2) — a classical closed form,
  used as a **control**.
* **ZZ-linear / ZZ-full** (ZZFeatureMap convention, Havlíček et al.): repeat `reps` times: H on all qubits;
  P(2xᵢ) on each; for each pair (i, j) — neighbours (linear) or all pairs (full): CX(i,j) · P(2(π−xᵢ)(π−xⱼ)) on j ·
  CX(i,j). The pair terms create entanglement that depends on products of features.

**V4's kernel** is different: Tr(ρAρB) between *mixed* states of image patches (see FRQI_NEQR_DEEP_DIVE.md).

---

## 6. Theory vs our implementation

| Theoretical claim | In our project |
|---|---|
| Quantum computer runs the circuit | NumPy / Aer **simulation**, noiseless |
| Kernel estimated from shots | Exact values (V2 also simulates Binomial shot noise) |
| Swap test measures Tr(ρσ) | Computed exactly; swap test only described |
| Exponential state space may help | Our registers are 3–16 qubits: trivially simulable; no advantage expected or found |

### Recap
Qubits hold amplitudes; gates are unitary matrices; measurement samples probabilities; kernels compare encoded
states. Our project uses H, X, RY, RZ, P, CX, MCRY, MCX — all simulated exactly.

### Self-check questions
1. Why does an n-qubit simulation need 2ⁿ numbers? 2. What is the difference between a superposition and a
mixture? 3. What does RY(π)|0⟩ give? 4. Why are X gates placed before and after the MCRY in FRQI? 5. What is the
compute–uncompute circuit and what does its all-zero probability equal? 6. Why is the product-RY kernel a "control"?
7. Which gates in our code create entanglement? 8. What would noise do to a 4,878-depth circuit?
