# FRQI and NEQR — Mathematical and Circuit-Level Deep Dive

> Code: `src/frqi/encoder.py`, `src/neqr/encoder.py`, `src/reconstruction/reconstructor.py`,
> `src/v2/frqi_neqr.py` (closed-form kernels), `src/v3/models.py` (overlap kernels, stretch),
> `src/v4/models.py` (patch-ensemble). Resource numbers are from `results/qml_v4/reconstruction_full/summary.json`.

---

## A. FRQI — Flexible Representation of Quantum Images (Le, Dong & Hirota, 2011)

### A.1 Idea
Store an image of N = 2ⁿ pixels in **n position qubits + 1 colour qubit**. Positions are in uniform superposition;
the colour qubit is rotated by an angle that encodes each pixel's grey value:

  |I⟩ = (1/√N) Σᵢ (cos θᵢ |0⟩ + sin θᵢ |1⟩) ⊗ |i⟩,  θᵢ = (π/2)·b·xᵢ,  xᵢ ∈ [0, 1]

b = 1 is the original definition (θ ∈ [0, π/2]). Our V2/V3/V4 kernels also use b = 2 or 4 ("angle scale") to
spread similar intensities apart; with b > 1 the encoding is no longer invertible by arcsin, so b = 1 is used for
reconstruction.

### A.2 How the code builds the circuit (`FRQIEncoder.build_circuit`)
1. `pos` register (n qubits) and `color` register (1 qubit), all |0⟩.
2. **H on every position qubit** → (1/√N) Σᵢ |i⟩|0⟩.
3. For each pixel i (row-major, `pixel_values = image.flatten()`):
   * skip if the angle is 0 (black pixel — nothing to rotate);
   * **X on every position qubit whose bit of i is 0** (q₀ = least-significant bit);
   * **multi-controlled RY(angle)** with all position qubits as controls and the colour qubit as target
     (`cry` when n = 1, `mcry` otherwise). The code passes angle = xᵢ·π = 2θᵢ, because RY(2θ)|0⟩ = cos θ|0⟩+sin θ|1⟩;
   * undo the X gates.

### A.3 Worked 2×2 example
Image (row-major) x = [0, 0.5, 1, 0.25] → θ = (π/2)x = [0, π/4, π/2, π/8]. n = 2 position qubits, 3 qubits total.

| Pixel i | bits q₁q₀ | θᵢ | cos θᵢ | sin θᵢ | P(colour = 1 \| i) = sin²θ |
|---|---|---|---|---|---|
| 0 | 00 | 0 | 1 | 0 | 0 |
| 1 | 01 | π/4 | 0.707 | 0.707 | 0.5 |
| 2 | 10 | π/2 | 0 | 1 | 1 |
| 3 | 11 | π/8 | 0.924 | 0.383 | 0.146 |

State: ½[ |0⟩|00⟩ + (0.707|0⟩+0.707|1⟩)|01⟩ + |1⟩|10⟩ + (0.924|0⟩+0.383|1⟩)|11⟩ ].
Circuit, layer by layer: H(q₀) H(q₁) │ pixel 0 skipped │ pixel 1: X(q₁) · MCRY(0.5π) · X(q₁) │ pixel 2: X(q₀) ·
MCRY(π) · X(q₀) │ pixel 3: MCRY(0.25π) (no X needed). Real counts for a 2×2 FRQI circuit: 3 qubits, 143 compiled
gates, depth 93, 48 CX (logical: 8 X, 8 RY, 8 CCX, 2 H after Qiskit's MCRY decomposition).

### A.4 Reconstruction (`FRQIReconstructor`)
* **From the statevector**: P(1 | i) = sin²θᵢ exactly → θᵢ = arcsin√P → xᵢ = θᵢ/(π/2). Exact for all 1,800 images.
* **From shots**: measure all qubits; for each position i, P̂(1|i) = (#shots with colour = 1 at i)/(#shots at i);
  θ̂ = arcsin√P̂. Each position receives only ≈ shots/N samples, so error grows with resolution.
  Measured (all 1,800 images, 1,000 shots): MSE 4.2e-4 (2×2), 1.7e-3 (4×4), 8.7e-3 (8×8), 6.4e-2 (16×16);
  with 100,000 shots 16×16 reaches 2.6e-4.

### A.5 Limitations
One multi-controlled rotation per pixel → gates grow like N·n: FRQI 8×8 needs 8,339 compiled gates (depth 4,878,
3,584 CX); 16×16 needs 77,307 gates. Read-out is statistical. Whole-image overlap compares pixels at the same
index only (§D).

---

## B. NEQR — Novel Enhanced Quantum Representation (Zhang, Lu, Gao & Wang, 2013)

### B.1 Idea
Store each grey value as a **q-bit binary code** in q colour qubits:

  |I⟩ = (1/√N) Σᵢ |cᵢ⟩ ⊗ |i⟩,  cᵢ = round(xᵢ (2^q − 1))

Qubits: n + q. Intensity precision = q bits = 2^q grey levels (we use q = 2, 4, 8; V4 uses 3–6).

### B.2 Circuit (`NEQREncoder.build_circuit`)
H on all position qubits; then for every pixel and every bit j of cᵢ that equals 1: X-sandwich the position qubits
(as in FRQI) and apply a **multi-controlled X** (`mcx`) onto intensity qubit j. Zero bits need no gate — so the gate
count depends on the image content.

### B.3 Worked 2×2 example (q = 2)
x = [0, 0.5, 1, 0.25] → cᵢ = round(3x) = [0, 2, 3, 1] (NumPy rounds 1.5 to 2) → binary [00, 10, 11, 01].
State: ½(|00⟩|00⟩ + |10⟩|01⟩ + |11⟩|10⟩ + |01⟩|11⟩) (colour ⊗ position). Gates: pixel 1 → 1 MCX; pixel 2 → 2 MCX;
pixel 3 → 1 MCX; pixel 0 → none. Decoding gives back [0, 2/3, 1, 1/3] — note **quantisation error**
(0.5 → 0.667, 0.25 → 0.333).

### B.4 Reconstruction (`NEQRReconstructor`)
Statevector: read the code at each position (exact up to quantisation). Shots: for each position, take the
**majority** observed code. A position never observed decodes as 0 (black) — visible at 100 shots.
Measured: 4-bit floor MSE 3.68e-4; 8-bit lossless; 2-bit ≈ 9e-3.

### B.5 Limitations
Needs q extra qubits; many MCX gates (16×16, 4-bit: 131,375 compiled gates); gate count data-dependent.

---

## C. FRQI vs NEQR (from our implementation)

| Aspect | FRQI | NEQR |
|---|---|---|
| Qubits | 2·log₂(side) + 1 | 2·log₂(side) + q |
| Intensity encoding | angle (amplitude) | binary basis state |
| Gate per pixel | 1 MCRY (skipped if black) | 1 MCX per set bit |
| Content dependence of gates | almost none | strong |
| 8×8 example (compiled) | 7 qubits, 8,339 gates, depth 4,878 | 4-bit: 10 qubits, 14,531 gates, depth 10,794 |
| Exact read-out | statistical (arcsin√P) | exact up to quantisation |
| Shot behaviour | error ∝ 1/shots per position, smooth | saturates at quantisation floor once every pixel seen |
| Kernel between images (whole) | [mean cos(θA−θB)]² — smooth | [fraction of identical codes]² — all-or-nothing |

**Why both?** They are the two most cited QIRs and represent the two basic options (angle vs basis encoding), so
comparing them tells us which kind of encoding carries useful texture similarity.

**Resolutions supported.** Square images with power-of-two pixel counts: 2×2, 4×4, 8×8, 16×16 for whole images
(classification and reconstruction), patches 2×2/4×4/8×8 inside 32–128 px images in V4.

---

## D. Why whole-image kernels fail and patches work

Whole-image FRQI kernel: K(A,B) = [ (1/N) Σᵢ cos(θᵢᴬ − θᵢᴮ) ]². Pixel i of A is compared only with pixel i of B.
A scratch shifted by 3 pixels changes many terms → nearly unrelated states. NEU classes are *textures* whose
position varies (class-average images are almost flat, see report Figure 3.5). Result: ≈ 60 % at best.

**V4 patch-ensemble.** Cut the (optionally stretched) image into P patches of p×p with stride s,
P = ((S−p)/s + 1)². Encode each patch as |ψₖ⟩ (FRQI or NEQR). Represent the image by

  ρ_I = (1/P) Σₖ |ψₖ⟩⟨ψₖ|    (a D×D density matrix; D = 2^(qubits per patch))

  K(A,B) = Tr(ρA ρB) = (1/(P_A P_B)) Σₖ Σₗ |⟨ψₖᴬ|ψₗᴮ⟩|²

Every patch of A is compared with **every** patch of B → position-independent texture similarity.
Code: `mixed_states()` computes ρ with `einsum("npi,npj->nij")`, flattened; K = R·Rᵀ.
Frozen FRQI model: 64×64, p = 8, s = 4 → P = 225 patches, 7 qubits per patch, ρ is 128×128, b = 4, stretch on.
Frozen NEQR model: 128×128, p = 4, s = 4 → P = 1,024 patches, q = 4 → 8 qubits, ρ is 256×256, no stretch.

**Cost trick.** All patch pairs cost O(P²D) per image pair; forming ρ once costs O(PD²) and each kernel entry
O(D²). With P² = 50,625 ≫ D = 128, the density-matrix route made 864 runs feasible on a laptop.

**Shift test** (`tests/test_v4_models.py`): rolling a 16×16 image by one stride gives normalised patch kernel
> 0.999 while the whole-image FRQI kernel drops below 0.95.

**Hardware route (not executed).** A swap test between a random patch of A and a random patch of B has expected
outcome Tr(ρAρB) → unbiased estimate with 2 patch registers + 1 ancilla (15 qubits for FRQI p = 8).

### Recap
FRQI = angle, NEQR = binary code; both entangle colour with position; both are exact in simulation but expensive
in gates; comparing whole images position-by-position is the real weakness; mixing patch states fixes it.

### Self-check
1. Derive the FRQI amplitudes for x = [1, 0, 0.5, 0.5]. 2. Why does the code pass xᵢ·π to RY? 3. NEQR code for
x = 0.6 with q = 3? 4. Why does NEQR show black pixels at 100 shots? 5. Why does FRQI error grow with resolution
at fixed shots? 6. Write Tr(ρAρB) as a sum over patch pairs. 7. Why is averaging density matrices not a
superposition? 8. Why is NEQR's gate count image-dependent?
