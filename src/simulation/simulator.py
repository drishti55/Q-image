"""
Quantum Simulation Module.

Provides a unified interface for running quantum circuits using Qiskit simulators:
  - StatevectorSimulator: Exact simulation (no measurement noise)
  - AerSimulator: Shot-based measurement simulation with configurable shot count

All simulation calls are timed consistently using time.perf_counter().
"""

import time
import numpy as np
from typing import Dict, Any, Optional, Tuple
from copy import deepcopy

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator, StatevectorSimulator


class QuantumSimulator:
    """
    Manages quantum circuit simulation for FRQI and NEQR experiments.
    
    Supports both exact statevector simulation and shot-based measurement.
    """

    def __init__(self, seed: int = 42):
        """
        Initialize the quantum simulator.
        
        Args:
            seed: Random seed for shot-based simulation reproducibility.
        """
        self.seed = seed
        self._statevector_sim = AerSimulator(method="statevector")
        self._aer_sim = AerSimulator(method="automatic", seed_simulator=seed)

    def run_statevector(self, circuit: QuantumCircuit) -> Dict[str, Any]:
        """
        Run exact statevector simulation (no measurement noise).
        
        This provides the ground-truth quantum state without sampling noise.
        Useful for validation and as a baseline for shot-based experiments.
        
        Args:
            circuit: Quantum circuit to simulate (without measurement gates).
            
        Returns:
            Dictionary with:
                - 'statevector': Complex numpy array of amplitudes
                - 'probabilities': Real numpy array of measurement probabilities
                - 'simulation_time': Time for simulation (seconds)
        """
        # Make a copy to avoid modifying the original
        sim_circuit = circuit.copy()

        # Check if save_statevector or save_state is already in the circuit
        has_save = any(
            instr.operation.name in ("save_statevector", "save_state") 
            for instr in sim_circuit.data
        )
        if not has_save:
            sim_circuit.save_statevector()

        start_time = time.perf_counter()
        result = self._statevector_sim.run(sim_circuit).result()
        simulation_time = time.perf_counter() - start_time

        try:
            statevector = np.array(result.get_statevector())
        except Exception as e:
            # If for some reason we still can't get it, try another way
            raise ValueError(f"Could not get statevector: {e}")
        probabilities = np.abs(statevector) ** 2

        return {
            "statevector": statevector,
            "probabilities": probabilities,
            "simulation_time": simulation_time,
        }

    def run_shots(
        self, circuit: QuantumCircuit, shots: int = 1024
    ) -> Dict[str, Any]:
        """
        Run shot-based measurement simulation.
        
        Adds measurement gates to all qubits and runs the specified
        number of shots. Returns measurement count statistics.
        
        Args:
            circuit: Quantum circuit to simulate (without measurement gates).
            shots: Number of measurement shots.
            
        Returns:
            Dictionary with:
                - 'counts': Dict mapping bitstring → count
                - 'shots': Number of shots used
                - 'simulation_time': Time for simulation (seconds)
                - 'measurement_time': Time for measurement extraction (seconds)
        """
        # Create circuit with measurements
        meas_circuit = self.add_measurements(circuit)

        start_time = time.perf_counter()
        result = self._aer_sim.run(meas_circuit, shots=shots).result()
        simulation_time = time.perf_counter() - start_time

        meas_start = time.perf_counter()
        counts = result.get_counts()
        measurement_time = time.perf_counter() - meas_start

        return {
            "counts": counts,
            "shots": shots,
            "simulation_time": simulation_time,
            "measurement_time": measurement_time,
        }

    def add_measurements(self, circuit: QuantumCircuit) -> QuantumCircuit:
        """
        Add measurement gates to all qubits in the circuit.
        
        Args:
            circuit: Quantum circuit (without measurements).
            
        Returns:
            New circuit with measurement gates appended.
        """
        meas_circuit = circuit.copy()
        meas_circuit.measure_all()
        return meas_circuit

    def run_both(
        self, circuit: QuantumCircuit, shots: int = 1024
    ) -> Dict[str, Any]:
        """
        Run both statevector and shot-based simulation.
        
        Useful for comparing exact results with measurement-based results.
        
        Args:
            circuit: Quantum circuit to simulate.
            shots: Number of measurement shots.
            
        Returns:
            Dictionary with 'statevector_result' and 'shots_result' sub-dicts.
        """
        sv_result = self.run_statevector(circuit)
        shots_result = self.run_shots(circuit, shots)

        return {
            "statevector_result": sv_result,
            "shots_result": shots_result,
        }
