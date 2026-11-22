# FRQI aur NEQR — Maths aur Circuit Level Deep Dive

> Code: `src/frqi/encoder.py`, `src/neqr/encoder.py`, `src/reconstruction/reconstructor.py`,
> `src/v2/frqi_neqr.py` (closed-form kernels), `src/v3/models.py` (overlap kernels, stretch),
> `src/v4/models.py` (patch-ensemble). Resource numbers `results/qml_v4/reconstruction_full/summary.json` se.

---

## A. FRQI — Flexible Representation of Quantum Images (Le, Dong & Hirota, 2011)

### A.1 Idea
N = 2ⁿ pixels wali image ko **n position qubits + 1 colour qubit** mein store karo. Positions uniform superposition mein;
colour qubit ko har pixel ki grey value ke hisaab se angle se ghumao:

  |I⟩ = (1/√N) Σᵢ (cos θᵢ |0⟩ + sin θᵢ |1⟩) ⊗ |i⟩,  θᵢ = (π/2)·b·xᵢ,  xᵢ ∈ [0, 1]

b = 1 original definition hai (θ ∈ [0, π/2]). Humare V2/V3/V4 kernels b = 2 ya 4 ("angle scale") bhi use karte hain
taaki milti-julti intensities alag ho jaayein; b > 1 par arcsin se wapas invert nahi hota, isliye reconstruction mein
b = 1 use hota hai.

### A.2 Code circuit kaise banata hai (`FRQIEncoder.build_circuit`)
1. `pos` register (n qubits) aur `color` register (1 qubit), sab |0⟩.
2. **Har position qubit par H** → (1/√N) Σᵢ |i⟩|0⟩.
3. Har pixel i ke liye (row-major, `image.flatten()`):
   * angle 0 ho toh skip (kaala pixel — ghumane ko kuch nahi);
   * **jin position qubits ka bit 0 hai unpar X** (q₀ = least-significant bit);
   * **multi-controlled RY(angle)**: saare position qubits controls, colour qubit target (n = 1 par `cry`, warna `mcry`).
     Code angle = xᵢ·π = 2θᵢ deta hai, kyunki RY(2θ)|0⟩ = cos θ|0⟩+sin θ|1⟩;
   * X gates wapas undo.

### A.3 Worked 2×2 example
Image (row-major) x = [0, 0.5, 1, 0.25] → θ = (π/2)x = [0, π/4, π/2, π/8]. n = 2 position qubits, total 3 qubits.

| Pixel i | bits q₁q₀ | θᵢ | cos θᵢ | sin θᵢ | P(colour = 1 \| i) = sin²θ |
|---|---|---|---|---|---|
| 0 | 00 | 0 | 1 | 0 | 0 |
| 1 | 01 | π/4 | 0.707 | 0.707 | 0.5 |
| 2 | 10 | π/2 | 0 | 1 | 1 |
| 3 | 11 | π/8 | 0.924 | 0.383 | 0.146 |

State: ½[ |0⟩|00⟩ + (0.707|0⟩+0.707|1⟩)|01⟩ + |1⟩|10⟩ + (0.924|0⟩+0.383|1⟩)|11⟩ ].
Circuit layer by layer: H(q₀) H(q₁) │ pixel 0 skip │ pixel 1: X(q₁) · MCRY(0.5π) · X(q₁) │ pixel 2: X(q₀) · MCRY(π) ·
X(q₀) │ pixel 3: MCRY(0.25π) (X nahi chahiye). Real 2×2 FRQI circuit: 3 qubits, 143 compiled gates, depth 93, 48 CX.

### A.4 Reconstruction (`FRQIReconstructor`)
* **Statevector se**: P(1 | i) = sin²θᵢ exact → θᵢ = arcsin√P → xᵢ = θᵢ/(π/2). Saari 1,800 images exact.
* **Shots se**: sab qubits measure; har position i ke liye P̂(1|i) = (colour = 1 wale shots)/(i par aaye shots);
  θ̂ = arcsin√P̂. Har position ko sirf ≈ shots/N samples milte hain, isliye resolution badhne par error badhta hai.
  Measured (1,800 images, 1,000 shots): MSE 4.2e-4 (2×2), 1.7e-3 (4×4), 8.7e-3 (8×8), 6.4e-2 (16×16);
  100,000 shots par 16×16 → 2.6e-4.

### A.5 Limitations
Har pixel par ek multi-controlled rotation → gates N·n ki tarah badhte hain: FRQI 8×8 ko 8,339 compiled gates (depth 4,878,
3,584 CX); 16×16 ko 77,307. Read-out statistical. Whole-image overlap sirf same index ke pixels compare karta hai (§D).

---

## B. NEQR — Novel Enhanced Quantum Representation (Zhang, Lu, Gao & Wang, 2013)

### B.1 Idea
Har grey value ko **q-bit binary code** ki tarah q colour qubits mein store karo:

  |I⟩ = (1/√N) Σᵢ |cᵢ⟩ ⊗ |i⟩,  cᵢ = round(xᵢ (2^q − 1))

Qubits: n + q. Intensity precision = q bits = 2^q grey levels (hum q = 2, 4, 8; V4 mein 3–6).

### B.2 Circuit (`NEQREncoder.build_circuit`)
Position qubits par H; phir har pixel aur code ke har bit j jo 1 hai: position qubits ka X-sandwich (FRQI jaisa) aur
intensity qubit j par **multi-controlled X** (`mcx`). Zero bits ko gate nahi chahiye — isliye gate count image ke content
par depend karta hai.

### B.3 Worked 2×2 example (q = 2)
x = [0, 0.5, 1, 0.25] → cᵢ = round(3x) = [0, 2, 3, 1] (NumPy 1.5 ko 2 karta hai) → binary [00, 10, 11, 01].
State: ½(|00⟩|00⟩ + |10⟩|01⟩ + |11⟩|10⟩ + |01⟩|11⟩) (colour ⊗ position). Gates: pixel 1 → 1 MCX; pixel 2 → 2 MCX;
pixel 3 → 1 MCX; pixel 0 → kuch nahi. Decode karne par [0, 2/3, 1, 1/3] — **quantisation error** dikhta hai
(0.5 → 0.667, 0.25 → 0.333).

### B.4 Reconstruction (`NEQRReconstructor`)
Statevector: har position par code padho (quantisation tak exact). Shots: har position par **sabse zyada** aaya code
(majority vote). Jo position kabhi observe nahi hui woh 0 (kaala) decode hoti hai — 100 shots par dikhta hai.
Measured: 4-bit floor MSE 3.68e-4; 8-bit lossless; 2-bit ≈ 9e-3.

### B.5 Limitations
q extra qubits; bahut saare MCX gates (16×16, 4-bit: 131,375 compiled gates); gate count data par depend.

---

## C. FRQI vs NEQR (humare implementation se)

| Aspect | FRQI | NEQR |
|---|---|---|
| Qubits | 2·log₂(side) + 1 | 2·log₂(side) + q |
| Intensity encoding | angle (amplitude) | binary basis state |
| Har pixel par gate | 1 MCRY (kaala ho toh skip) | har set bit par 1 MCX |
| Gates content par depend? | lagbhag nahi | bahut zyada |
| 8×8 example (compiled) | 7 qubits, 8,339 gates, depth 4,878 | 4-bit: 10 qubits, 14,531 gates, depth 10,794 |
| Exact read-out | statistical (arcsin√P) | quantisation tak exact |
| Shots behaviour | error ∝ 1/shots per position, smooth | har pixel dikhne ke baad quantisation floor par ruk jaata hai |
| Do images ka kernel (whole) | [mean cos(θA−θB)]² — smooth | [identical codes ka fraction]² — all-or-nothing |

**Dono kyun?** Yeh do sabse zyada cited QIRs hain aur do basic options represent karte hain (angle vs basis encoding),
isliye compare karke pata chalta hai kaunsa encoding type useful texture similarity rakhta hai.

**Supported resolutions.** Power-of-two pixel count wali square images: whole image 2×2, 4×4, 8×8, 16×16; V4 mein
32–128 px images ke andar 2×2/4×4/8×8 patches.

---

## D. Whole-image kernels fail kyun hote hain aur patches kaam kyun karte hain

Whole-image FRQI kernel: K(A,B) = [ (1/N) Σᵢ cos(θᵢᴬ − θᵢᴮ) ]². Image A ka pixel i sirf image B ke pixel i se compare
hota hai. Scratch 3 pixel khisak jaaye toh bahut terms badal jaate hain → lagbhag alag states. NEU classes *textures*
hain jinki position badalti rehti hai (class-average images lagbhag flat hain, report Figure 3.5). Result: best ≈ 60 %.

**V4 patch-ensemble.** (Optional stretch ke baad) image ko P patches mein kaato, size p×p, stride s,
P = ((S−p)/s + 1)². Har patch ko |ψₖ⟩ (FRQI ya NEQR) mein encode karo. Image ko represent karo:

  ρ_I = (1/P) Σₖ |ψₖ⟩⟨ψₖ|    (D×D density matrix; D = 2^(qubits per patch))

  K(A,B) = Tr(ρA ρB) = (1/(P_A P_B)) Σₖ Σₗ |⟨ψₖᴬ|ψₗᴮ⟩|²

A ka **har** patch B ke **har** patch se compare hota hai → position-independent texture similarity.
Code: `mixed_states()` ρ ko `einsum("npi,npj->nij")` se banata hai, flatten karta hai; K = R·Rᵀ.
Frozen FRQI model: 64×64, p = 8, s = 4 → P = 225 patches, har patch 7 qubits, ρ 128×128, b = 4, stretch on.
Frozen NEQR model: 128×128, p = 4, s = 4 → P = 1,024 patches, q = 4 → 8 qubits, ρ 256×256, stretch off.

**Cost trick.** Saare patch pairs: O(P²D) per image pair; ρ ek baar banana O(PD²) aur har kernel entry O(D²).
P² = 50,625 ≫ D = 128 hone se density-matrix wala tareeka 864 runs ko laptop par possible banata hai.

**Shift test** (`tests/test_v4_models.py`): 16×16 image ko ek stride roll karne par normalised patch kernel > 0.999,
jabki whole-image FRQI kernel 0.95 se neeche chala jaata hai.

**Hardware route (chalaya nahi).** A ke random patch aur B ke random patch ke beech swap test ka expected outcome
Tr(ρAρB) hai → 2 patch registers + 1 ancilla se unbiased estimate (FRQI p = 8 ke liye 15 qubits).

### Recap
FRQI = angle, NEQR = binary code; dono colour ko position se entangle karte hain; simulation mein exact par gates mein
mehnge; asli kamzori poori image ko position-by-position compare karna hai; patch states ko mix karna use theek karta hai.

### Self-check
1. x = [1, 0, 0.5, 0.5] ke FRQI amplitudes nikaalo. 2. Code RY ko xᵢ·π kyun deta hai? 3. x = 0.6, q = 3 ka NEQR code?
4. 100 shots par NEQR mein kaale pixels kyun? 5. Fixed shots par resolution ke saath FRQI error kyun badhta hai?
6. Tr(ρAρB) ko patch pairs ke sum ki tarah likho. 7. Density matrices ka average superposition kyun nahi hai?
8. NEQR ka gate count image par kyun depend karta hai?
