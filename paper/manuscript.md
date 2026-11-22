# Beyond Qubit Count: Comparing FRQI and NEQR Under Practical Constraints

## Abstract
Quantum Image Processing (QIP) is a rapidly growing field that explores the representation and manipulation of image data on quantum computers. Two foundational representations are the Flexible Representation of Quantum Images (FRQI) and the Novel Enhanced Quantum Representation (NEQR). While theoretical comparisons exist, this paper presents a comprehensive empirical comparison of FRQI and NEQR under practical implementation constraints. We evaluate both algorithms across varying resolutions, intensity bit-depths, measurement shots, and image complexities using both synthetic patterns and the real-world NEU Surface Defect Database (NEU-DET). Our results indicate that while FRQI excels in minimizing spatial qubit overhead (requiring a constant 1 qubit for color), it suffers from exponential gate scaling and severe susceptibility to shot noise. In contrast, NEQR requires more qubits ($n+q$) but offers significantly shallower circuits, fewer gates, and exact deterministic readout, making it a stronger candidate for near-term noise-constrained hardware when auxiliary qubits are available.

## 1. Introduction
The advent of quantum computing has introduced novel paradigms for accelerating classical machine learning and image processing tasks. Quantum Image Processing (QIP) requires an efficient mechanism to encode classical pixel data into quantum states. FRQI (Flexible Representation of Quantum Images) encodes pixel intensities as probability amplitudes of a single auxiliary qubit, bounded by an angle $\theta$. NEQR (Novel Enhanced Quantum Representation) encodes pixel intensities as computational basis states using $q$ auxiliary qubits.

The theoretical trade-offs are widely known: FRQI is highly qubit-efficient, whereas NEQR avoids probabilistic measurements for intensity retrieval. However, actual implementations on quantum simulators reveal hidden computational costs—such as multi-controlled gate compilation depth, statevector simulation times, and statistical sampling errors under finite measurement shots. This paper empirically investigates these constraints to answer a central research question: *Is qubit count alone sufficient to compare FRQI and NEQR, or do practical factors significantly affect their performance?*

## 2. Background and Related Work

### 2.1 FRQI
FRQI represents a $2^n \times 2^n$ image using $2n$ position qubits and 1 color qubit. The intensity $C_i$ is mapped to an angle $\theta_i \in [0, \pi/2]$, and encoded via multi-controlled $R_y(\theta)$ rotations.
$$ |I(\theta)\rangle = \frac{1}{2^n} \sum_{i=0}^{2^{2n}-1} (\cos\theta_i |0\rangle + \sin\theta_i |1\rangle) \otimes |i\rangle $$

### 2.2 NEQR
NEQR maps the intensity $C_i \in [0, 2^q - 1]$ directly into the basis states of $q$ color qubits.
$$ |I\rangle = \frac{1}{2^n} \sum_{i=0}^{2^{2n}-1} |C_i\rangle \otimes |i\rangle $$
NEQR utilizes multi-controlled $X$ gates instead of rotations.

## 3. Methodology
We implemented a complete QIP pipeline utilizing Qiskit. The experiments were conducted across five dimensions:
1. **Resolution Scaling:** $2\times2$, $4\times4$, and $8\times8$ image sizes.
2. **Intensity Precision (Bit-depth):** 2-bit (4 levels), 4-bit (16 levels), and 8-bit (256 levels).
3. **Measurement Shots:** 100, 500, 1000, and 5000 shots.
4. **Image Complexity:** Uniform, gradient, checkerboard, diagonal, and random noise.
5. **Real-World Application:** NEU Surface Defect Database (NEU-DET) containing industrial steel defects (crazing, inclusion, patches, pitted surface, rolled-in scale, scratches). We utilized a massive subset of 1440 images (240 per category) to ensure robust statistical significance.

Evaluation metrics included Qubit count, Gate count, Circuit Depth, Mean Squared Error (MSE), and Peak Signal-to-Noise Ratio (PSNR). Statevector simulation was used as the ground truth, followed by shot-based sampling to model realistic quantum readouts.

## 4. Results and Analysis

### 4.1 Resolution and Gate Complexity
As resolution scales from $2\times2$ to $4\times4$, the qubit counts remain small for FRQI (5 qubits total for $4\times4$: 4 for position, 1 for color). NEQR requires 12 qubits (4 for position, 8 for intensity). However, FRQI requires **1,092 gates** to encode an 8-bit $4\times4$ image, heavily relying on $mcry$ (multi-controlled $R_y$) gates which decompose inefficiently. NEQR requires only **128 gates** for the same configuration, showcasing a massive advantage in circuit compilation depth.

### 4.2 Impact of Intensity Bit-Depth
When modifying the intensity depth from 2-bit to 8-bit:
- **FRQI** maintains a constant 5-qubit requirement, as the single color qubit simply takes on finer rotation angles. However, the gate count scales from 812 (2-bit) to 1,092 (8-bit) due to the dense angle distribution.
- **NEQR**'s qubit requirement scales linearly with bit-depth ($n+q$), requiring 6 qubits at 2-bit and 12 qubits at 8-bit. Interestingly, NEQR's gate count scales much more favorably, requiring only 60 gates at 2-bit and 128 gates at 8-bit.

### 4.3 Statistical Shot Noise in Reconstruction
The most dramatic difference arises during quantum measurement:
- **FRQI** is highly vulnerable to shot noise because intensity is stored as a probability amplitude. At 100 shots, FRQI achieves an MSE of 0.032 and a PSNR of 14.89 dB. At 5000 shots, it achieves an MSE of 0.0003 and a PSNR of 34.62 dB.
- **NEQR**, by contrast, stores intensities as deterministic basis states. NEQR achieves an MSE of **0.00** and infinite PSNR regardless of the number of measurement shots, provided all basis states are sampled.

### 4.4 NEU-DET Defect Dataset Evaluation
Under ideal statevector simulation, both FRQI and NEQR achieved perfect reconstruction (MSE = 0.0) across all 6 defect categories in the NEU-DET dataset (evaluated rigorously over 1440 distinct defect instances). This proves both representations are mathematically sound for complex industrial defect features (crazing, rolled-in scales). The choice between them for real hardware deployment will depend entirely on the physical error rates of the hardware.

## 5. Discussion
The empirical evidence strictly challenges the notion that FRQI is "better" simply due to its lower qubit count. 
1. **NISQ Hardware Constraints:** In the Noisy Intermediate-Scale Quantum (NISQ) era, circuit depth is often the primary bottleneck due to short coherence times. FRQI's deep, multi-controlled rotation circuits are highly likely to decohere before completion. NEQR's shallower, multi-controlled NOT structures are far more hardware-friendly, provided the QPU has sufficient qubits.
2. **Readout Efficiency:** FRQI requires exponential measurement shots to accurately approximate the probability amplitudes $\sin^2(\theta_i)$. NEQR offers a discrete, robust readout.

## 6. Conclusion
In this study, we built a comprehensive, parameterized quantum image processing framework to benchmark FRQI and NEQR. We conclude that while FRQI is optimal for theoretical frameworks constrained strictly by qubit capacity, **NEQR is overwhelmingly superior for practical implementations**. NEQR's linear scaling of auxiliary qubits is a negligible price to pay for its drastically shallower circuit depths and deterministic, noise-resilient measurement outcomes. Future work should investigate these representations directly on physical hardware and assess their integration into Quantum Convolutional Neural Networks (QCNNs) for defect classification.

## References
[1] P. Q. Le, F. Dong, and K. Hirota, "A flexible representation of quantum images for complex background," *Quantum Information Processing*, 2011.
[2] Y. Zhang, K. Lu, and Y. Gao, "NEQR: A novel enhanced quantum representation of digital images," *Quantum Information Processing*, 2013.
[3] NEU Surface Defect Database, Northeastern University.
