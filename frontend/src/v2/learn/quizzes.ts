// Knowledge-check questions (concepts only; no results).
export type Question = { q: string; options: string[]; answer: number; why: string; topic?: string };

export const QUIZZES: Record<string, Question[]> = {
  pipeline: [
    { q: 'What is the main purpose of PCA in the hybrid pipeline?', options: ['Increase image resolution', 'Reduce the number of features', 'Create entanglement', 'Measure qubits'], answer: 1, why: '576 CNN numbers → k numbers, one per qubit.', topic: 'pca' },
    { q: 'Why is MobileNetV3 kept frozen?', options: ['To save GPU memory', 'So every model gets identical features and nothing is tuned on steel images', 'Because it cannot be trained', 'To make it quantum'], answer: 1, why: 'Same 576 features for quantum and classical models → fair comparison.', topic: 'mobilenet' },
    { q: 'Which part actually picks the defect class?', options: ['The quantum circuit', 'The measurement', 'A classical SVM using the kernel values', 'PCA'], answer: 2, why: 'The circuit only supplies similarities; the SVM decides.', topic: 'qkc' },
    { q: 'A shifted scratch looks “different” to whole-image FRQI. What did V4 do?', options: ['Used more shots', 'Compared small patches (mixed state)', 'Added more qubits', 'Removed PCA'], answer: 1, why: 'Patch states are mixed into ρ, so position no longer matters.', topic: 'density' },
  ],
  encoding: [
    { q: 'How many qubits does FRQI need for a 4×4 image?', options: ['16', '5', '8', '4'], answer: 1, why: '2·log₂4 = 4 position qubits + 1 colour qubit.', topic: 'frqi' },
    { q: 'NEQR stores a pixel’s brightness as…', options: ['A rotation angle', 'Binary bits in colour qubits', 'A phase', 'A probability only'], answer: 1, why: 'q colour qubits hold the q-bit code exactly.', topic: 'neqr' },
    { q: 'What do the Hadamard gates on the position qubits do?', options: ['Measure the pixels', 'Put all pixel positions in superposition at once', 'Rotate the colour qubit', 'Undo the encoding'], answer: 1, why: 'Every position gets equal weight, then each pixel is written in.', topic: 'qubit' },
    { q: 'Why does NEQR need many more gates than FRQI?', options: ['It uses more shots', 'One controlled-NOT per 1-bit of every pixel', 'It has no Hadamards', 'It uses PCA'], answer: 1, why: 'Each 1-bit is a multi-controlled X; FRQI needs one rotation per pixel.', topic: 'neqr' },
  ],
  cnn: [
    { q: 'What does one feature map show?', options: ['The whole image in colour', 'Where one filter found its pattern', 'The final class', 'A quantum state'], answer: 1, why: 'Bright = that filter fired there.', topic: 'cnn' },
    { q: 'Where do the 576 numbers come from?', options: ['576 pixels', 'Averaging each of the 576 final maps', '576 qubits', 'PCA'], answer: 1, why: 'Global average pooling: one number per final map.', topic: 'cnn' },
    { q: 'With the same CNN features, how do quantum and classical classifiers compare here?', options: ['Quantum is far better', 'Classical is far better', 'They land within about a point of each other', 'Quantum cannot use CNN features'], answer: 2, why: 'The CNN does most of the work; see the hybrid vs classical chart.', topic: 'qkc' },
  ],
  playground: [
    { q: 'A pixel of value 255 has FRQI angle θ =', options: ['0°', '45°', '90°', '180°'], answer: 2, why: 'θ = (π/2)·255/255 = 90°: the colour qubit is fully |1⟩.', topic: 'frqi' },
    { q: 'Going from 8-bit to 2-bit NEQR…', options: ['Adds qubits', 'Removes 6 colour qubits but rounds brightness to 4 shades', 'Changes nothing', 'Removes position qubits'], answer: 1, why: 'Fewer bits → fewer qubits, coarser image.', topic: 'neqr' },
    { q: 'What makes ZZ-Full different from Product-RY?', options: ['It has no rotations', 'It links every pair of qubits (entanglement)', 'It uses fewer qubits', 'It is classical'], answer: 1, why: 'Product-RY has no two-qubit gates; ZZ-Full couples all pairs.', topic: 'zz-full' },
    { q: 'A kernel value of 1 between two images means…', options: ['Completely different', 'Identical quantum states', 'Half similar', 'Measurement failed'], answer: 1, why: '|⟨φ(x)|φ(y)⟩|² = 1 only when the states are the same.', topic: 'kernel' },
  ],
  algorithms: [
    { q: 'What does a quantum kernel measure?', options: ['How many qubits an image needs', 'How similar two encoded images are (state overlap)', 'The training time', 'The image resolution'], answer: 1, why: 'K = |⟨φ(x)|φ(y)⟩|²: 1 = identical states, 0 = totally different.', topic: 'kernel' },
    { q: 'How is PQK different from QKC?', options: ['It uses no circuit', 'It compares each qubit separately (Bloch vectors) instead of whole states', 'It trains the circuit', 'It uses more shots'], answer: 1, why: 'Projected onto single-qubit states, then a classical RBF kernel.', topic: 'pqk' },
    { q: 'What is trained in a VQC?', options: ['The CNN', 'The rotation angles θ inside the circuit', 'The PCA', 'Nothing'], answer: 1, why: 'Parameter-shift gradients + an optimiser update θ.', topic: 'vqc' },
    { q: 'Which feature map has no entanglement?', options: ['ZZ-Full', 'ZZ-Linear', 'Product-RY', 'All of them have it'], answer: 2, why: 'Product-RY has only single-qubit rotations — no CX gates.', topic: 'product-ry' },
    { q: 'Why is the classical RBF-SVM on the same features important?', options: ['It is faster to draw', 'It shows whether the quantum part adds anything', 'It replaces PCA', 'It is required by Qiskit'], answer: 1, why: 'Same inputs, only the kernel differs → a fair test of the quantum kernel.', topic: 'qkc' },
  ],
  results: [
    { q: 'Why were the 360 test images opened only once?', options: ['To save time', 'So settings could not be tuned on them (no cheating)', 'Because they were too large', 'Qiskit limits it'], answer: 1, why: 'Settings are frozen on validation data, then tested once.', topic: 'kernel-matrix' },
    { q: 'A quantum model and a classical SVM on the same features differ by less than one point. What do we conclude?', options: ['Quantum advantage', 'About the same — no evidence of quantum benefit', 'Classical is broken', 'Quantum is 10× better'], answer: 1, why: 'Less than a point apart on the same inputs; the features do the work.', topic: 'qkc' },
    { q: 'Why report results over 3 seeds?', options: ['To get a bigger number', 'To show how stable a model is', 'Because there are 3 classes', 'To use 3 qubits'], answer: 1, why: 'Mean ± std over seeds shows run-to-run variation.' },
    { q: 'What improved FRQI/NEQR from ~60% to over 80% in V4?', options: ['More shots', 'Encoding small patches and mixing them into one state', 'Real quantum hardware', 'A bigger CNN'], answer: 1, why: 'Patch mixtures make the kernel insensitive to where a texture sits.', topic: 'density' },
  ],
  reconstruction: [
    { q: 'MSE = 0 means…', options: ['The image is black', 'The rebuilt image equals the original exactly', 'No shots were used', 'The circuit failed'], answer: 1, why: 'Mean squared error between original and rebuilt pixels.', topic: 'recon-metrics' },
    { q: 'Higher PSNR means…', options: ['Worse reconstruction', 'Better reconstruction', 'More qubits', 'Fewer pixels'], answer: 1, why: 'PSNR = 10·log₁₀(1/MSE): smaller error → higher PSNR.', topic: 'recon-metrics' },
    { q: 'Why does FRQI need many shots to rebuild an image?', options: ['It stores bits', 'Each brightness is an angle estimated from counts', 'It has no Hadamards', 'It uses PCA'], answer: 1, why: 'θ is estimated from how often the colour qubit reads 1.', topic: 'shots' },
  ],
};
