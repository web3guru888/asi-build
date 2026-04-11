"""
Quantum Systems Metrics Collector for Kenny AGI

This module provides comprehensive metrics collection for all quantum-related
components in Kenny AGI, including quantum computing interfaces, quantum
consciousness processing, quantum-classical hybrid systems, and quantum
state management.
"""

import time
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from concurrent.futures import ThreadPoolExecutor

from prometheus_client import Counter, Gauge, Histogram, Summary

from .metrics_exporter import KennyMetricsExporter, SystemComponent, MetricConfig, MetricType

logger = logging.getLogger(__name__)


class QuantumMetricType(Enum):
    """Types of quantum metrics"""
    COHERENCE = "coherence"
    ENTANGLEMENT = "entanglement" 
    FIDELITY = "fidelity"
    GATE_ERROR = "gate_error"
    DECOHERENCE = "decoherence"
    SUPERPOSITION = "superposition"
    CONSCIOUSNESS_QUANTUM = "consciousness_quantum"
    QUANTUM_ADVANTAGE = "quantum_advantage"


class QuantumSystem(Enum):
    """Quantum systems in Kenny AGI"""
    QISKIT_INTERFACE = "qiskit_interface"
    QUANTUM_SIMULATOR = "quantum_simulator"
    HYBRID_ML_PROCESSOR = "hybrid_ml_processor"
    QUANTUM_CONSCIOUSNESS = "quantum_consciousness"
    QUANTUM_HARDWARE = "quantum_hardware"
    QUANTUM_KENNY_INTEGRATION = "quantum_kenny_integration"
    QUANTUM_ML_ALGORITHMS = "quantum_ml_algorithms"
    QUANTUM_REALITY_BRIDGE = "quantum_reality_bridge"
    QUANTUM_INFORMATION_PROCESSOR = "quantum_information_processor"


@dataclass
class QuantumStateMetrics:
    """Quantum state metrics"""
    fidelity: float = 0.0
    coherence_time: float = 0.0
    entanglement_measure: float = 0.0
    superposition_degree: float = 0.0
    decoherence_rate: float = 0.0
    gate_errors: int = 0
    measurement_errors: int = 0
    quantum_volume: int = 0


@dataclass
class QuantumOperationMetrics:
    """Quantum operation metrics"""
    operation_count: int = 0
    total_duration: float = 0.0
    average_duration: float = 0.0
    success_rate: float = 0.0
    error_rate: float = 0.0
    throughput: float = 0.0


class QuantumMetricsCollector:
    """
    Comprehensive quantum metrics collector for Kenny AGI
    
    Collects and exposes metrics for:
    - Quantum circuit execution
    - Quantum state management
    - Quantum-classical hybrid processing
    - Quantum consciousness interfaces
    - Quantum hardware status
    - Quantum algorithm performance
    """
    
    def __init__(self, exporter: KennyMetricsExporter):
        """
        Initialize quantum metrics collector
        
        Args:
            exporter: Kenny AGI metrics exporter instance
        """
        self.exporter = exporter
        self.metrics: Dict[str, Any] = {}
        self.quantum_states: Dict[str, QuantumStateMetrics] = {}
        self.operation_metrics: Dict[str, QuantumOperationMetrics] = {}
        
        # Threading for concurrent metric collection
        self.collection_lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="QuantumMetrics")
        
        # Monitoring state
        self.monitoring_active = False
        self.last_collection_time = 0.0
        
        # Initialize quantum metrics
        self._initialize_quantum_metrics()
        
        # Register with exporter
        self.exporter.register_collector(SystemComponent.QUANTUM, self.collect_all_metrics)
        
        logger.info("Quantum metrics collector initialized")

    def _initialize_quantum_metrics(self):
        """Initialize all quantum-related metrics"""
        
        # Quantum state metrics
        self.metrics['quantum_fidelity'] = self.exporter.register_metric(MetricConfig(
            name='kenny_quantum_fidelity',
            help_text='Quantum state fidelity (0-1)',
            labels=['system', 'qubit_id', 'state_type'],
            metric_type=MetricType.GAUGE,
            component=SystemComponent.QUANTUM
        ))
        
        self.metrics['quantum_coherence_time'] = self.exporter.register_metric(MetricConfig(
            name='kenny_quantum_coherence_time_seconds',
            help_text='Quantum coherence time in seconds',
            labels=['system', 'qubit_id'],
            metric_type=MetricType.GAUGE,
            component=SystemComponent.QUANTUM
        ))
        
        self.metrics['quantum_entanglement'] = self.exporter.register_metric(MetricConfig(
            name='kenny_quantum_entanglement_measure',
            help_text='Quantum entanglement measure',
            labels=['system', 'qubit_pair', 'entanglement_type'],
            metric_type=MetricType.GAUGE,
            component=SystemComponent.QUANTUM
        ))
        
        self.metrics['quantum_superposition'] = self.exporter.register_metric(MetricConfig(
            name='kenny_quantum_superposition_degree',
            help_text='Degree of quantum superposition (0-1)',
            labels=['system', 'qubit_id'],
            metric_type=MetricType.GAUGE,
            component=SystemComponent.QUANTUM
        ))
        
        # Quantum operation metrics
        self.metrics['quantum_operations_total'] = self.exporter.register_metric(MetricConfig(
            name='kenny_quantum_operations_total',
            help_text='Total quantum operations executed',
            labels=['system', 'operation_type', 'status'],
            metric_type=MetricType.COUNTER,
            component=SystemComponent.QUANTUM
        ))
        
        self.metrics['quantum_operation_duration'] = self.exporter.register_metric(MetricConfig(
            name='kenny_quantum_operation_duration_seconds',
            help_text='Quantum operation execution duration',
            labels=['system', 'operation_type'],
            metric_type=MetricType.HISTOGRAM,
            buckets=[0.001, 0.01, 0.1, 1.0, 10.0, 60.0, 300.0],
            component=SystemComponent.QUANTUM
        ))
        
        self.metrics['quantum_gate_errors'] = self.exporter.register_metric(MetricConfig(
            name='kenny_quantum_gate_errors_total',
            help_text='Total quantum gate errors',
            labels=['system', 'gate_type', 'error_type'],
            metric_type=MetricType.COUNTER,
            component=SystemComponent.QUANTUM
        ))
        
        self.metrics['quantum_measurement_errors'] = self.exporter.register_metric(MetricConfig(
            name='kenny_quantum_measurement_errors_total',
            help_text='Total quantum measurement errors',
            labels=['system', 'measurement_type'],
            metric_type=MetricType.COUNTER,
            component=SystemComponent.QUANTUM
        ))
        
        # Quantum hardware metrics
        self.metrics['quantum_hardware_status'] = self.exporter.register_metric(MetricConfig(
            name='kenny_quantum_hardware_status',
            help_text='Quantum hardware status (1=active, 0=inactive)',
            labels=['hardware_type', 'device_id', 'location'],
            metric_type=MetricType.GAUGE,
            component=SystemComponent.QUANTUM
        ))
        
        self.metrics['quantum_hardware_temperature'] = self.exporter.register_metric(MetricConfig(
            name='kenny_quantum_hardware_temperature_kelvin',
            help_text='Quantum hardware temperature in Kelvin',
            labels=['hardware_type', 'device_id', 'sensor_location'],
            metric_type=MetricType.GAUGE,
            component=SystemComponent.QUANTUM
        ))
        
        self.metrics['quantum_error_rate'] = self.exporter.register_metric(MetricConfig(
            name='kenny_quantum_error_rate',
            help_text='Quantum operation error rate (0-1)',
            labels=['system', 'operation_type'],
            metric_type=MetricType.GAUGE,
            component=SystemComponent.QUANTUM
        ))
        
        # Quantum-classical hybrid metrics
        self.metrics['quantum_classical_sync'] = self.exporter.register_metric(MetricConfig(
            name='kenny_quantum_classical_sync_latency_seconds',
            help_text='Quantum-classical synchronization latency',
            labels=['interface_type'],
            metric_type=MetricType.HISTOGRAM,
            buckets=[0.001, 0.01, 0.1, 1.0, 10.0],
            component=SystemComponent.QUANTUM
        ))
        
        self.metrics['quantum_advantage_factor'] = self.exporter.register_metric(MetricConfig(
            name='kenny_quantum_advantage_factor',
            help_text='Quantum advantage factor over classical computation',
            labels=['algorithm', 'problem_size'],
            metric_type=MetricType.GAUGE,
            component=SystemComponent.QUANTUM
        ))
        
        # Quantum consciousness metrics
        self.metrics['quantum_consciousness_level'] = self.exporter.register_metric(MetricConfig(
            name='kenny_quantum_consciousness_level',
            help_text='Quantum consciousness processing level (0-100)',
            labels=['consciousness_type', 'quantum_system'],
            metric_type=MetricType.GAUGE,
            component=SystemComponent.QUANTUM
        ))
        
        self.metrics['quantum_consciousness_coherence'] = self.exporter.register_metric(MetricConfig(
            name='kenny_quantum_consciousness_coherence',
            help_text='Quantum consciousness coherence measure (0-1)',
            labels=['consciousness_module'],
            metric_type=MetricType.GAUGE,
            component=SystemComponent.QUANTUM
        ))
        
        # Quantum volume and capability metrics
        self.metrics['quantum_volume'] = self.exporter.register_metric(MetricConfig(
            name='kenny_quantum_volume',
            help_text='Quantum volume of the system',
            labels=['system', 'measurement_method'],
            metric_type=MetricType.GAUGE,
            component=SystemComponent.QUANTUM
        ))
        
        self.metrics['quantum_circuit_depth'] = self.exporter.register_metric(MetricConfig(
            name='kenny_quantum_circuit_depth',
            help_text='Quantum circuit depth',
            labels=['circuit_type', 'optimization_level'],
            metric_type=MetricType.GAUGE,
            component=SystemComponent.QUANTUM
        ))
        
        # Quantum algorithm performance
        self.metrics['quantum_algorithm_success_rate'] = self.exporter.register_metric(MetricConfig(
            name='kenny_quantum_algorithm_success_rate',
            help_text='Quantum algorithm success rate (0-1)',
            labels=['algorithm', 'problem_type'],
            metric_type=MetricType.GAUGE,
            component=SystemComponent.QUANTUM
        ))
        
        self.metrics['quantum_speedup'] = self.exporter.register_metric(MetricConfig(
            name='kenny_quantum_speedup_factor',
            help_text='Quantum speedup factor compared to classical',
            labels=['algorithm', 'problem_size'],
            metric_type=MetricType.GAUGE,
            component=SystemComponent.QUANTUM
        ))

    def update_quantum_state_metrics(self, 
                                   system: str, 
                                   qubit_id: str, 
                                   state_metrics: QuantumStateMetrics):
        """
        Update quantum state metrics for a specific system and qubit
        
        Args:
            system: Quantum system identifier
            qubit_id: Qubit identifier
            state_metrics: Quantum state metrics
        """
        with self.collection_lock:
            try:
                # Update fidelity
                self.metrics['quantum_fidelity'].labels(
                    system=system,
                    qubit_id=qubit_id,
                    state_type='current'
                ).set(state_metrics.fidelity)
                
                # Update coherence time
                self.metrics['quantum_coherence_time'].labels(
                    system=system,
                    qubit_id=qubit_id
                ).set(state_metrics.coherence_time)
                
                # Update superposition degree
                self.metrics['quantum_superposition'].labels(
                    system=system,
                    qubit_id=qubit_id
                ).set(state_metrics.superposition_degree)
                
                # Update error metrics
                if state_metrics.gate_errors > 0:
                    self.metrics['quantum_gate_errors'].labels(
                        system=system,
                        gate_type='generic',
                        error_type='execution'
                    ).inc(state_metrics.gate_errors)
                
                if state_metrics.measurement_errors > 0:
                    self.metrics['quantum_measurement_errors'].labels(
                        system=system,
                        measurement_type='z_basis'
                    ).inc(state_metrics.measurement_errors)
                
                # Store for later aggregation
                key = f"{system}_{qubit_id}"
                self.quantum_states[key] = state_metrics
                
            except Exception as e:
                logger.error(f"Error updating quantum state metrics: {e}")

    def update_entanglement_metrics(self, 
                                  system: str, 
                                  qubit_pair: str, 
                                  entanglement_measure: float,
                                  entanglement_type: str = "bipartite"):
        """
        Update quantum entanglement metrics
        
        Args:
            system: Quantum system identifier
            qubit_pair: Qubit pair identifier (e.g., "0-1")
            entanglement_measure: Entanglement measure value
            entanglement_type: Type of entanglement
        """
        try:
            self.metrics['quantum_entanglement'].labels(
                system=system,
                qubit_pair=qubit_pair,
                entanglement_type=entanglement_type
            ).set(entanglement_measure)
            
        except Exception as e:
            logger.error(f"Error updating entanglement metrics: {e}")

    def record_quantum_operation(self, 
                               system: str, 
                               operation_type: str, 
                               duration: float, 
                               success: bool = True):
        """
        Record quantum operation execution
        
        Args:
            system: Quantum system identifier
            operation_type: Type of operation (gate, measurement, etc.)
            duration: Operation duration in seconds
            success: Whether operation was successful
        """
        try:
            # Increment operation counter
            status = "success" if success else "error"
            self.metrics['quantum_operations_total'].labels(
                system=system,
                operation_type=operation_type,
                status=status
            ).inc()
            
            # Record duration
            self.metrics['quantum_operation_duration'].labels(
                system=system,
                operation_type=operation_type
            ).observe(duration)
            
            # Update operation metrics
            key = f"{system}_{operation_type}"
            if key not in self.operation_metrics:
                self.operation_metrics[key] = QuantumOperationMetrics()
            
            metrics = self.operation_metrics[key]
            metrics.operation_count += 1
            metrics.total_duration += duration
            metrics.average_duration = metrics.total_duration / metrics.operation_count
            
            if success:
                metrics.success_rate = (metrics.success_rate * (metrics.operation_count - 1) + 1.0) / metrics.operation_count
            else:
                metrics.success_rate = (metrics.success_rate * (metrics.operation_count - 1)) / metrics.operation_count
            
            metrics.error_rate = 1.0 - metrics.success_rate
            
            # Update error rate metric
            self.metrics['quantum_error_rate'].labels(
                system=system,
                operation_type=operation_type
            ).set(metrics.error_rate)
            
        except Exception as e:
            logger.error(f"Error recording quantum operation: {e}")

    def update_hardware_metrics(self, 
                              hardware_type: str, 
                              device_id: str, 
                              temperature: float, 
                              status: bool,
                              location: str = "default"):
        """
        Update quantum hardware metrics
        
        Args:
            hardware_type: Type of quantum hardware
            device_id: Device identifier
            temperature: Temperature in Kelvin
            status: Hardware status (active/inactive)
            location: Hardware location
        """
        try:
            # Hardware status
            self.metrics['quantum_hardware_status'].labels(
                hardware_type=hardware_type,
                device_id=device_id,
                location=location
            ).set(1 if status else 0)
            
            # Temperature
            self.metrics['quantum_hardware_temperature'].labels(
                hardware_type=hardware_type,
                device_id=device_id,
                sensor_location="primary"
            ).set(temperature)
            
        except Exception as e:
            logger.error(f"Error updating hardware metrics: {e}")

    def update_consciousness_metrics(self, 
                                   consciousness_type: str, 
                                   quantum_system: str, 
                                   level: float, 
                                   coherence: float):
        """
        Update quantum consciousness metrics
        
        Args:
            consciousness_type: Type of consciousness processing
            quantum_system: Quantum system involved
            level: Consciousness level (0-100)
            coherence: Consciousness coherence (0-1)
        """
        try:
            self.metrics['quantum_consciousness_level'].labels(
                consciousness_type=consciousness_type,
                quantum_system=quantum_system
            ).set(level)
            
            self.metrics['quantum_consciousness_coherence'].labels(
                consciousness_module=consciousness_type
            ).set(coherence)
            
        except Exception as e:
            logger.error(f"Error updating consciousness metrics: {e}")

    def update_quantum_advantage_metrics(self, 
                                       algorithm: str, 
                                       problem_size: str, 
                                       advantage_factor: float, 
                                       speedup_factor: float):
        """
        Update quantum advantage and speedup metrics
        
        Args:
            algorithm: Quantum algorithm name
            problem_size: Size of the problem
            advantage_factor: Quantum advantage factor
            speedup_factor: Speedup compared to classical
        """
        try:
            self.metrics['quantum_advantage_factor'].labels(
                algorithm=algorithm,
                problem_size=problem_size
            ).set(advantage_factor)
            
            self.metrics['quantum_speedup'].labels(
                algorithm=algorithm,
                problem_size=problem_size
            ).set(speedup_factor)
            
        except Exception as e:
            logger.error(f"Error updating quantum advantage metrics: {e}")

    def simulate_quantum_metrics(self):
        """
        Simulate quantum metrics for demonstration
        (This would be replaced with actual quantum system integration)
        """
        try:
            current_time = time.time()
            
            # Simulate quantum systems
            systems = ['qiskit_simulator', 'quantum_hardware', 'hybrid_processor']
            
            for system in systems:
                # Simulate qubit metrics
                for qubit_id in range(5):  # 5 qubits
                    qubit_str = f"q{qubit_id}"
                    
                    # Generate realistic quantum metrics
                    fidelity = 0.85 + 0.1 * np.sin(current_time + qubit_id)
                    coherence_time = 50e-6 + 10e-6 * np.random.random()  # 50-60 microseconds
                    superposition = abs(np.sin(current_time * 2 + qubit_id))
                    
                    state_metrics = QuantumStateMetrics(
                        fidelity=max(0, min(1, fidelity)),
                        coherence_time=coherence_time,
                        superposition_degree=superposition,
                        decoherence_rate=1/coherence_time,
                        gate_errors=np.random.poisson(0.1),
                        measurement_errors=np.random.poisson(0.05)
                    )
                    
                    self.update_quantum_state_metrics(system, qubit_str, state_metrics)
                
                # Simulate entanglement
                for i in range(2):  # 2 entangled pairs
                    pair = f"{i}-{i+1}"
                    entanglement = 0.7 + 0.2 * np.sin(current_time + i)
                    self.update_entanglement_metrics(system, pair, entanglement)
                
                # Simulate operations
                operations = ['hadamard', 'cnot', 'measurement', 'reset']
                for op in operations:
                    # Random operation timing
                    if np.random.random() < 0.3:  # 30% chance of operation
                        duration = 1e-6 + 5e-6 * np.random.random()  # 1-6 microseconds
                        success = np.random.random() > 0.05  # 95% success rate
                        self.record_quantum_operation(system, op, duration, success)
                
                # Simulate hardware metrics
                if system == 'quantum_hardware':
                    temp = 0.015 + 0.002 * np.sin(current_time)  # ~15mK
                    status = True
                    self.update_hardware_metrics('superconducting', 'device_001', temp, status)
                
                # Simulate consciousness metrics
                consciousness_level = 50 + 25 * np.sin(current_time)
                coherence = 0.8 + 0.15 * np.sin(current_time * 1.5)
                self.update_consciousness_metrics('quantum_aware', system, consciousness_level, coherence)
                
                # Simulate quantum advantage
                algorithms = ['shor', 'grover', 'qaoa', 'vqe']
                for algo in algorithms:
                    if np.random.random() < 0.1:  # 10% chance
                        advantage = 2 ** np.random.randint(1, 10)  # Exponential advantage
                        speedup = advantage * (0.8 + 0.4 * np.random.random())
                        self.update_quantum_advantage_metrics(algo, 'medium', advantage, speedup)
            
        except Exception as e:
            logger.error(f"Error simulating quantum metrics: {e}")

    def collect_all_metrics(self):
        """Collect all quantum metrics"""
        try:
            start_time = time.time()
            
            # In a real system, this would interface with actual quantum systems
            # For now, we simulate the metrics
            self.simulate_quantum_metrics()
            
            # Calculate aggregate metrics
            self._calculate_aggregate_metrics()
            
            collection_time = time.time() - start_time
            self.last_collection_time = collection_time
            
            logger.debug(f"Quantum metrics collection completed in {collection_time:.3f}s")
            
        except Exception as e:
            logger.error(f"Error in quantum metrics collection: {e}")

    def _calculate_aggregate_metrics(self):
        """Calculate aggregate quantum metrics"""
        try:
            if not self.quantum_states:
                return
            
            # Calculate average fidelity across all qubits
            total_fidelity = sum(state.fidelity for state in self.quantum_states.values())
            avg_fidelity = total_fidelity / len(self.quantum_states)
            
            # Update aggregate metrics
            self.metrics['quantum_fidelity'].labels(
                system='aggregate',
                qubit_id='all',
                state_type='average'
            ).set(avg_fidelity)
            
            # Calculate total quantum volume (simplified)
            total_qubits = len(self.quantum_states)
            if total_qubits > 0:
                quantum_volume = min(total_qubits, int(avg_fidelity * 100))
                self.metrics['quantum_volume'].labels(
                    system='aggregate',
                    measurement_method='simplified'
                ).set(quantum_volume)
            
        except Exception as e:
            logger.error(f"Error calculating aggregate metrics: {e}")

    def get_quantum_state_summary(self) -> Dict[str, Any]:
        """Get summary of quantum state metrics"""
        try:
            if not self.quantum_states:
                return {}
            
            fidelities = [state.fidelity for state in self.quantum_states.values()]
            coherence_times = [state.coherence_time for state in self.quantum_states.values()]
            
            return {
                'total_qubits': len(self.quantum_states),
                'average_fidelity': np.mean(fidelities),
                'min_fidelity': np.min(fidelities),
                'max_fidelity': np.max(fidelities),
                'average_coherence_time': np.mean(coherence_times),
                'total_gate_errors': sum(state.gate_errors for state in self.quantum_states.values()),
                'total_measurement_errors': sum(state.measurement_errors for state in self.quantum_states.values())
            }
            
        except Exception as e:
            logger.error(f"Error getting quantum state summary: {e}")
            return {}

    def shutdown(self):
        """Shutdown the quantum metrics collector"""
        try:
            self.monitoring_active = False
            self.executor.shutdown(wait=True)
            logger.info("Quantum metrics collector shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during quantum metrics collector shutdown: {e}")


# Integration function for easy setup
def setup_quantum_metrics(exporter: KennyMetricsExporter) -> QuantumMetricsCollector:
    """
    Set up quantum metrics collection for Kenny AGI
    
    Args:
        exporter: Kenny AGI metrics exporter
        
    Returns:
        Configured quantum metrics collector
    """
    collector = QuantumMetricsCollector(exporter)
    logger.info("Quantum metrics collection setup complete")
    return collector