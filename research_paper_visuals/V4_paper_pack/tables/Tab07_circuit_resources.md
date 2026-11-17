**Table 7. Encoder circuit resources for ONE patch state (Qiskit, transpiled)**

| Group | Qubits | Logical gates | Logical depth | Compiled gates | Compiled depth | CX (compiled) | Patches per image |
|---|---|---|---|---|---|---|---|
| FRQI patches 4×4 | 5 | 1093 | 705 | 1070 | 710 | 384 | 256 |
| FRQI patches 8×8 | 7 | 8583 | 4875 | 8339 | 4878 | 3584 | 225 |
| NEQR patches 2×2 | 6 | 20 | 15 | 150 | 99 | 55 | 1024 |
| NEQR patches 4×4 | 8 | 106 | 65 | 1998 | 1634 | 694 | 1024 |

*Basis {cx, rz, sx, x}, optimisation level 1, all-to-all coupling. A swap test between two patch states uses 2·qubits + 1 qubits.*
