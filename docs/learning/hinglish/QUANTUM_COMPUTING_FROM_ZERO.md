# Quantum Computing zero se (sirf woh jo Q-ImageLab use karta hai)

> §3 ka har gate humare code mein kahin use hota hai; jo gates use **nahi** hote unka naam alag likha hai.
> Conventions Qiskit wale hain (aur humara NumPy simulator `src/v2/qsim.py` Qiskit se 1e-10 tak match karta hai):
> **qubit 0 basis-state index ka sabse chhota (least-significant) bit hai.**

---

## 1. Concepts zero se

**1. Bit vs qubit.** Classical bit 0 ya 1 hota hai. *Qubit* ek 2-dimensional complex space ka unit vector hai:
|ψ⟩ = α|0⟩ + β|1⟩, jahan |α|² + |β|² = 1. α aur β ko *amplitudes* kehte hain.

**2. Superposition.** Jab α aur β dono non-zero hon. Iska matlab "qubit chupke se 0 ya 1 hai" **nahi** hai; yeh ek hi
pakki state hai. Analogy: north-east ki taraf ek arrow ek hi direction hai, "aadha north aadha east" nahi.

**3. Measurement.** Qubit padhne par 0 probability |α|² se aur 1 probability |β|² se milta hai, aur state us value par
collapse ho jaati hai. Ek measurement = ek bit ki information.

**4. Kai qubits — tensor product.** Do qubits ka space 4-dimensional: |00⟩,|01⟩,|10⟩,|11⟩. Independent qubits ke liye
(a|0⟩+b|1⟩)⊗(c|0⟩+d|1⟩) = ac|00⟩+ad|01⟩+bc|10⟩+bd|11⟩. n qubits ko 2ⁿ amplitudes chahiye — isliye har naye qubit ke
saath simulation ka kharcha double hota hai.

**5. Entanglement.** Aisi multi-qubit state jo tensor product mein nahi likhi ja sakti, jaise (|00⟩+|11⟩)/√2.
FRQI aur NEQR states mein position register aur colour register entangled hote hain (colour position par depend karta hai).

**6. Statevector.** Saare 2ⁿ amplitudes ki list. *Exact statevector simulation* yahi list seedha calculate karta hai.

**7. Circuit / register / gate.** Circuit gates (unitary matrices) ka sequence hai jo registers (qubits ke groups) par
lagte hain. Left se right padho. FRQI mein `pos` aur `color` registers hain.

**8. Unitary.** Aisi matrix U jisme U†U = I. Probabilities ka total 1 hi rehta hai aur operation reversible hota hai.

**9. Bloch sphere.** Single qubit ko sphere par point ki tarah dikha sakte hain: |0⟩ north pole, |1⟩ south pole,
(|0⟩+|1⟩)/√2 equator par. RY Y-axis ke around ghumata hai, RZ vertical axis ke around. V3 ka *projected quantum kernel*
yahi Bloch vectors compare karta hai.

**10. Measurement probability aur shots.** Hardware amplitudes nahi deta; circuit ko kai baar ("shots") chala kar outcomes
gine jaate hain. M shots se probability p ki standard error √(p(1−p)/M). Reconstruction study mein 100, 1,000, 10,000 aur
100,000 shots use hue.

**11. Simulator vs hardware.** Hum (a) Qiskit-Aer statevector + exact distribution se multinomial sampling
(reconstruction), aur (b) apna NumPy statevector simulator (kernels, VQC) use karte hain. Dono **noiseless** hain.
Real hardware mein gate errors, decoherence aur readout errors hote hain — inmein se kuch bhi model nahi kiya.

**12. Circuit depth aur gate count.** Gate count = gates ki ginti; depth = time-steps ki sankhya agar alag qubits ke gates
saath chal sakein. Hum *transpilation* ke baad basis {cx, rz, sx, x}, optimisation level 1, all-to-all connectivity par
report karte hain.

**13. Noise.** Model nahi kiya. Gehre circuits (jaise FRQI 16×16: 77,307 compiled gates) aaj ke devices par noise se
barbaad ho jaayenge — badi limitation.

**14. Quantum kernel.** Do encoded quantum states se nikla function K(x, y), jaise fidelity |⟨φ(x)|φ(y)⟩|², jo classical
SVM ke andar similarity ki tarah use hota hai. §5 dekho.

---

## 2. Mixed states aur density matrices (V4 ke liye zaroori)

*Pure* state ek vector |ψ⟩ hai. Uski *density matrix* ρ = |ψ⟩⟨ψ| (D×D matrix). *Mixed state* ek probabilistic mixture
hai: "probability wₖ se system |ψₖ⟩ mein hai": ρ = Σₖ wₖ |ψₖ⟩⟨ψₖ|.
Properties: Tr ρ = 1, ρ positive semi-definite, **purity** Tr(ρ²) pure state ke liye 1 aur mixture ke liye < 1.
Do density matrices ka overlap **Tr(ρσ)**, |⟨ψ|φ⟩|² ka generalisation hai (pure states ke liye dono barabar).

> ⚠ Common confusion: *density matrices* ka average (mixture) **aur** *statevectors* ka average (superposition) alag cheezein
> hain. V4 density matrices ka average leta hai.

---

## 3. Humare code mein use hone wale gates

{|0⟩, |1⟩} basis mein matrices; c = cos(θ/2), s = sin(θ/2).

| Gate | Matrix | Effect | Kahan use hua |
|---|---|---|---|
| **H** (Hadamard) | (1/√2)[[1,1],[1,−1]] | \|0⟩→(\|0⟩+\|1⟩)/√2 | FRQI/NEQR (sab position qubits); ZZ map |
| **X** (Pauli-X, NOT) | [[0,1],[1,0]] | 0↔1 flip | FRQI/NEQR "position selection" sandwich |
| **RY(θ)** | [[c,−s],[s,c]] | Y ke around rotate; RY(θ)\|0⟩ = c\|0⟩+s\|1⟩ | product-RY; VQC encoding & layers; FRQI (MCRY ke andar) |
| **RZ(θ)** | diag(e^{−iθ/2}, e^{iθ/2}) | phase rotation | VQC layers; transpiled circuits |
| **P(λ)** (phase) | diag(1, e^{iλ}) | \|1⟩ par phase | ZZ map: P(2xᵢ), P(2(π−xᵢ)(π−xⱼ)) |
| **CX / CNOT** | control = 1 ho toh target flip | entanglement banata hai | ZZ maps, VQC ring, sab transpiled circuits |
| **CRY / MCRY** | saare controls 1 hon toh target par RY | conditional rotation | FRQI (har pixel par ek) |
| **CCX / MCX** | saare controls 1 hon toh X | conditional flip | NEQR (har set bit par ek) |
| **SX** (√X), **T/T†** | basis gates | sirf transpilation/decomposition ke baad | resource counts |

**Humare implementation mein use nahi hue:** Pauli-Y aur Pauli-Z gates ki tarah, RX, CZ. (Z sirf VQC readout mein
*measured observable* ki tarah aata hai: ⟨Zᵢ⟩, ⟨ZᵢZⱼ⟩.) Swap test ke liye controlled-SWAP chahiye; woh **describe kiya,
chalaya nahi**.

### Worked example 1 — ek RY
|0⟩ par RY(π/2): c = cos(π/4) = 0.707, s = 0.707 → 0.707|0⟩ + 0.707|1⟩. Measure: 50 % / 50 %.
RY(π): c = 0, s = 1 → |1⟩. FRQI safed (white) pixel ko bilkul aise hi store karta hai.

### Worked example 2 — H phir CNOT (entanglement)
|00⟩ → qubit 0 par H → (|00⟩+|01⟩)/√2 (qubit 0 sabse right wala bit) → CX(control 0, target 1) → (|00⟩+|11⟩)/√2.
Ab dono qubits poori tarah correlated hain.

### Worked example 3 — X sandwich se position select karna (FRQI ki trick)
Do position qubits superposition mein, colour |0⟩: ½(|00⟩+|01⟩+|10⟩+|11⟩)|0⟩. Sirf position 1 (q1q0 = 01) ke liye colour
ghumana hai: q1 (jo bit 0 hai) par X lagao, toh 01 ban jaata hai 11; dono q0 aur q1 se controlled RY lagao (sirf "11"
trigger karta hai); q1 par X wapas. Result: sirf position 1 rotate hui.

---

## 4. Sequential gates = matrix multiplication
Pehle U₁ phir U₂ = U₂U₁ (algebra mein right-to-left, diagram mein left-to-right).
Example: RY(a) phir RY(b) = RY(a+b). RY(π/2)·RY(π/2) = RY(π): |0⟩ → |1⟩.

---

## 5. Humare project mein quantum kernels

**Idea.** Har data point x ko circuit U(x) se state |φ(x)⟩ mein map karo. Similarity K(x,y) = |⟨φ(x)|φ(y)⟩|²
(fidelity). Hardware ise *compute–uncompute* circuit U(y)†U(x)|0⟩ se estimate karega: sab zeros aane ki probability = K
(`kernel_circuit`). Hum ise statevectors se exact calculate karte hain (ya Binomial shot noise daalte hain).

**Teen feature maps (`src/v2/qkernel.py`).** Input = PCA/CNN/texture features jo [0, π] angles mein scale kiye gaye, aur
*bandwidth* b se multiply.
* **product-RY**: har qubit par RY(xᵢ). Koi entanglement nahi. K = Πᵢ cos²((xᵢ−yᵢ)/2) — classical closed form, isliye
  **control** ki tarah use hota hai.
* **ZZ-linear / ZZ-full** (ZZFeatureMap convention, Havlíček et al.): `reps` baar: sab par H; har par P(2xᵢ); har pair
  (i, j) — neighbours (linear) ya sab pairs (full) — ke liye CX(i,j) · j par P(2(π−xᵢ)(π−xⱼ)) · CX(i,j). Pair terms features
  ke products par depend karne wala entanglement banate hain.

**V4 ka kernel** alag hai: image patches ki *mixed* states ka Tr(ρAρB) (FRQI_NEQR_DEEP_DIVE dekho).

---

## 6. Theory vs humara implementation

| Theory | Humare project mein |
|---|---|
| Quantum computer circuit chalata hai | NumPy / Aer **simulation**, noiseless |
| Kernel shots se estimate | Exact values (V2 mein Binomial shot noise bhi) |
| Swap test Tr(ρσ) naapta hai | Exact compute; swap test sirf describe |
| Bada state space shayad help kare | Humare registers 3–16 qubits: aasaani se simulate; advantage na expected, na mila |

### Recap
Qubits amplitudes rakhte hain; gates unitary matrices hain; measurement probabilities sample karta hai; kernels encoded
states compare karte hain. Hum H, X, RY, RZ, P, CX, MCRY, MCX use karte hain — sab exact simulate.

### Self-check sawaal
1. n-qubit simulation ko 2ⁿ numbers kyun chahiye? 2. Superposition aur mixture mein kya farak? 3. RY(π)|0⟩ kya deta hai?
4. FRQI mein MCRY ke pehle aur baad X kyun? 5. Compute–uncompute circuit kya hai aur all-zero probability kya hoti hai?
6. Product-RY kernel "control" kyun hai? 7. Humare code mein kaunse gates entanglement banate hain?
8. 4,878 depth wale circuit par noise kya karega?
